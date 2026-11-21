# ==========================================================
# FILE: order_executor.py
# ==========================================================
# 🚨 MODIFIED: [Thundering Herd 영구 소각] 파편화된 await asyncio.sleep(0.06) 땜질 전면 삭제.
# 🚨 MODIFIED: [중앙 통제소 위임] 모든 API 지연을 GlobalThrottle(중앙 통제소)로 100% 위임하여 이벤트 루프 교착 상태 완벽 방어.
# 🚨 MODIFIED: [자본 잠김 패러독스 파기] 자본 잠김(is_capital_locked) 시 매수(BUY) 주문만 애프터장으로 지연 이관하고, 매도(SELL) 주문은 100% 정상적으로 정규장 슬라이싱/지정가 타격을 강행하도록 매도 탈출망 디커플링 결속 완료.
# 🚨 v1.0.4 (2026-11-19): [audit-fix 1-2] 타임아웃/통신오류 후 재시도 전에 미체결·체결·예약 원장을 조회해 같은 주문이 이미 나갔는지 확인. 이미 나갔으면 재전송하지 않고, 상태를 알 수 없으면 blind 재시도 없이 '확인 필요'로 기록(다음 회차에 재확인).
# ==========================================================
import asyncio
import logging
import html
import math
from state_io_manager import save_slice_state_sync, save_aftermarket_state_sync

# audit-fix 1-2: 타임아웃 직후 늦게 도착하는 주문이 원장에 반영될 시간을 주는 대기(초). 시험에서는 0 으로 낮춘다.
ORDER_CHECK_SETTLE_SEC = 3.0
# '확인 필요' 표식 접미사 — successful_orders_cache(set[str]) 안에 같이 넣어 바깥 재시도 루프에서도 유지된다.
UNVERIFIED_SUFFIX = "::UNVERIFIED"

def _row_qty(row, keys):
    for k in keys:
        v = row.get(k)
        if v not in (None, ''):
            return int(_safe_float(v))
    return 0

async def _fetch_order_snapshot(broker, ticker, is_market_active_now, today_str):
    """audit-fix 1-2: 이 종목의 현재 주문 원장 스냅샷. 조회가 하나라도 실패하면 None (= 상태를 알 수 없음).
    반환: {'ids': set(odno), 'rows': [{'odno','side','qty','price','kind'}]}"""
    d_str = str(today_str).replace('-', '')
    rows = []
    try:
        if is_market_active_now:
            unfilled = await asyncio.wait_for(asyncio.to_thread(broker.get_unfilled_orders_detail, ticker), timeout=45.0)
            if unfilled is False or unfilled is None or not isinstance(unfilled, list):
                return None
            for it in unfilled:
                if not isinstance(it, dict): continue
                rows.append({'odno': str(it.get('odno') or ''), 'side': str(it.get('sll_buy_dvsn_cd') or ''),
                             'qty': _row_qty(it, ('ft_ord_qty', 'ord_qty', 'nccs_qty')),
                             'price': _safe_float(it.get('ft_ord_unpr3') or it.get('ovrs_ord_unpr') or it.get('ord_unpr')), 'kind': 'unfilled'})
            execs = await asyncio.wait_for(asyncio.to_thread(broker.get_execution_history, ticker, d_str, d_str, True), timeout=45.0)
            if execs is None or not isinstance(execs, list):
                return None
            for it in execs:
                if not isinstance(it, dict): continue
                rows.append({'odno': str(it.get('odno') or ''), 'side': str(it.get('sll_buy_dvsn_cd') or ''),
                             'qty': _row_qty(it, ('ft_ord_qty', 'ft_ccld_qty')), 'price': 0.0, 'kind': 'executed'})
        else:
            resv = await asyncio.wait_for(asyncio.to_thread(broker.get_reservation_orders, ticker, d_str, d_str, True), timeout=45.0)
            if resv is None or not isinstance(resv, list):
                return None
            for it in resv:
                if not isinstance(it, dict): continue
                rows.append({'odno': str(it.get('ovrs_rsvn_odno') or it.get('odno') or ''), 'side': str(it.get('sll_buy_dvsn_cd') or ''),
                             'qty': _row_qty(it, ('ft_ord_qty', 'ord_qty')),
                             'price': _safe_float(it.get('ft_ord_unpr3') or it.get('ovrs_ord_unpr') or it.get('ord_unpr')), 'kind': 'reservation'})
    except Exception as e:
        logging.warning(f"[{ticker}] 주문 원장 스냅샷 조회 실패: {type(e).__name__}: {e}")
        return None
    return {'ids': {r['odno'] for r in rows if r['odno']}, 'rows': rows}

def _find_new_match(snapshot, baseline_ids, o_side, o_qty, o_price):
    """audit-fix 1-2: 전송 전 스냅샷(baseline_ids)에 없던 새 주문 중 같은 방향·수량(·가격)인 것의 주문번호를 돌려준다.
    없으면 None. 체결 행(executed)은 평균체결가가 지정가와 다를 수 있어 가격 비교를 하지 않는다."""
    side_cd = '02' if str(o_side).upper() == 'BUY' else '01'
    for r in snapshot['rows']:
        if r['odno'] and r['odno'] in baseline_ids: continue
        if r['side'] != side_cd: continue
        if r['kind'] == 'executed':
            if r['qty'] <= 0 or r['qty'] > o_qty: continue
        else:
            if r['qty'] != o_qty: continue
            if o_price > 0 and r['price'] > 0 and abs(r['price'] - o_price) > 0.005: continue
        return r['odno'] or 'UNKNOWN_ODNO'
    return None

def _safe_float(val):
    try:
        f_val = float(str(val or 0.0).replace(',', ''))
        if math.isnan(f_val) or math.isinf(f_val): return 0.0
        return f_val
    except Exception:
        return 0.0

async def execute_order_list(broker, ticker, orders_list, successful_orders_cache, is_market_active_now, today_str, is_capital_locked=False, order_category="1차 필수"):
    msgs = ""
    all_success = True
    loop_fail_reason = ""

    if not isinstance(orders_list, list):
        return False, "🚨 <b>스냅샷 오염: 주문 리스트 결측</b>\n", "주문 리스트 타입 에러"

    for o in orders_list:
        try:
            if not isinstance(o, dict): continue

            o_type = str(o.get('type', 'LOC'))
            o_side = str(o.get('side', 'BUY'))
            o_qty = int(_safe_float(o.get('qty')))
            o_price = _safe_float(o.get('price'))
            
            if o_qty <= 0:
                msgs += f"⚠️ {order_category}: 수량 0주 산출로 타격 바이패스 (안전 격리)\n"
                continue
            
            o_desc = html.escape(str(o.get('desc', '주문')))

            order_key = f"{ticker}_{o_desc}"
            if order_key in successful_orders_cache:
                msgs += f"└ {order_category}: {o_desc} {o_qty}주 (${o_price}): ✅(기장전 보존)\n"
                continue

            res = {}
            
            # audit-fix 1-2: 실제 증권사로 나가는 주문(로컬 VWAP·애프터 이관 제외)만 중복 방어 대상
            is_real_send = not (is_capital_locked and o_side == 'BUY') and o_type != 'VWAP'
            unverified_key = order_key + UNVERIFIED_SUFFIX
            baseline = None
            skip_send = False
            
            if is_real_send:
                if unverified_key in successful_orders_cache:
                    # 이전 회차에서 '확인 필요'로 남긴 주문 — 다시 내기 전에 먼저 원장에서 확인
                    snap0 = await _fetch_order_snapshot(broker, ticker, is_market_active_now, today_str)
                    if snap0 is None:
                        res = {'rt_cd': '998', 'msg1': '확인 필요: 이전 시도 주문의 접수 여부를 조회하지 못함 (재전송 보류)'}
                        skip_send = True
                    else:
                        found0 = _find_new_match(snap0, set(), o_side, o_qty, o_price)
                        if found0:
                            successful_orders_cache.discard(unverified_key)
                            res = {'rt_cd': '0', 'msg1': '이전 시도 주문 접수 확인 (중복 전송 생략)', 'odno': found0}
                            skip_send = True
                        else:
                            successful_orders_cache.discard(unverified_key)
                            baseline = snap0
                else:
                    baseline = await _fetch_order_snapshot(broker, ticker, is_market_active_now, today_str)
            
            for attempt in range(3):
                if skip_send: break
                try:
                    # 🚨 MODIFIED: [매도 탈출망 확보] 자본이 잠기더라도 매도(SELL) 주문은 애프터장으로 날리지 않고 정규장 엔진(VWAP 등)으로 정상 인계
                    if is_capital_locked and o_side == 'BUY':
                        slice_info = {"ticker": ticker, "side": o_side, "total_qty": o_qty, "filled_qty": 0, "target_price": o_price, "desc": o_desc, "status": "PENDING"}
                        await asyncio.wait_for(asyncio.to_thread(save_aftermarket_state_sync, ticker, today_str, slice_info), timeout=10.0)
                        res = {'rt_cd': '0', 'msg1': '애프터장 매수 지연 이관 완료', 'odno': f'AFTERMARKET_{id(o)}'}
                        
                    elif o_type == 'VWAP':
                        slice_info = {"ticker": ticker, "side": o_side, "total_qty": o_qty, "filled_qty": 0, "target_price": o_price, "desc": o_desc, "status": "PENDING"}
                        await asyncio.wait_for(asyncio.to_thread(save_slice_state_sync, ticker, today_str, slice_info), timeout=10.0)
                        res = {'rt_cd': '0', 'msg1': '로컬 자체 VWAP 엔진 위임 완료', 'odno': f'LOCAL_VWAP_{id(o)}'}
                        
                    elif is_market_active_now:
                        res = await asyncio.wait_for(asyncio.to_thread(broker.send_order, ticker, o_side, o_qty, o_price, o_type), timeout=15.0)
                    else:
                        res = await asyncio.wait_for(asyncio.to_thread(broker.send_reservation_order, ticker, o_side, o_qty, o_price, o_type), timeout=15.0)

                    break
                    
                except (asyncio.TimeoutError, Exception) as e:
                    is_timeout = isinstance(e, asyncio.TimeoutError)
                    fail_res = {'rt_cd': '999', 'msg1': 'API 통신 타임아웃 (10~15초 초과)'} if is_timeout else {'rt_cd': '999', 'msg1': f'통신/I/O 오류: {str(e)}'}
                    
                    if not is_real_send:
                        # 로컬 저장 경로는 증권사로 나가지 않으므로 기존 재시도 유지
                        if attempt < 2: await asyncio.sleep(1.0 * (2 ** attempt))
                        else: res = fail_res
                        continue
                    
                    # audit-fix 1-2: 첫 시도가 이미 나갔는데 응답만 늦었을 수 있다 → 재시도 전에 원장 확인
                    if ORDER_CHECK_SETTLE_SEC > 0:
                        await asyncio.sleep(ORDER_CHECK_SETTLE_SEC)
                    snap = await _fetch_order_snapshot(broker, ticker, is_market_active_now, today_str)
                    if snap is None or baseline is None:
                        # 상태를 알 수 없음 → blind 재시도 금지, '확인 필요'로 기록
                        successful_orders_cache.add(unverified_key)
                        res = {'rt_cd': '998', 'msg1': f"확인 필요: 주문 접수 여부 불명 ({'타임아웃' if is_timeout else '통신오류'} 후 원장 조회 불가) — 재전송 보류"}
                        logging.error(f"🚨 [{ticker}] {o_desc} {o_side} {o_qty}주 접수 여부 불명 — blind 재시도 중단(확인 필요)")
                        break
                    found = _find_new_match(snap, baseline['ids'], o_side, o_qty, o_price)
                    if found:
                        res = {'rt_cd': '0', 'msg1': '타임아웃 후 주문 접수 확인 (중복 재전송 생략)', 'odno': found}
                        logging.warning(f"⚠️ [{ticker}] {o_desc} 첫 시도가 이미 접수됨(odno={found}) — 재전송 생략")
                        break
                    # 원장에 없음 = 안 나갔음이 확인됨 → 재시도 가능
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                    else:
                        res = fail_res

            safe_res = res if isinstance(res, dict) else {}
            is_success = safe_res.get('rt_cd') == '0'
            err_msg = html.escape(str(safe_res.get('msg1') or '오류/잔금패스'))

            if is_success:
                successful_orders_cache.add(order_key)
            else:
                all_success = False
                loop_fail_reason = f"[{ticker}] {order_category} 거절: {err_msg}"

            status_icon = '✅' if is_success else f'❌({err_msg})'
            msgs += f"└ {order_category}: {o_desc} {o_qty}주 (${o_price}): {status_icon}\n"
            
            await asyncio.sleep(0.2)

        except Exception as e:
            all_success = False
            loop_fail_reason = f"[{ticker}] {order_category} 치명적 오류"
            logging.error(f"🚨 [{ticker}] execute_order_list 개별 덫 처리 오류: {e}")
            msgs += f"└ {order_category} 시스템 오류: {html.escape(str(e))}\n"

    return all_success, msgs, loop_fail_reason
