# ==========================================================
# FILE: callback_order_handler.py
# ==========================================================
# 🚨 MODIFIED: [단일 지층 팽창 패러독스 궁극 수술 (Parameter Amnesia)] 1회분 수동 매수/매도(MANUAL_PORTION) 타격 시 로컬 큐 장부를 원자적으로 업데이트(`add_lot`, `pop_lots`)할 때, 지층 분할(Split)에 필수적인 `prev_close`와 `portion_budget`을 타격 직전 실시간으로 연산하여 100% 무결성으로 주입 완료.
# 🚨 MODIFIED: [지층 독립성 팽창 패러독스 자가 치유 수술] MANUAL_PORTION(수동 1회분 매수) 기원을 "VREV_VWAP_BUY"로 일원화(통합)하여 1층 지층 팽창(2회분 중복 저장)을 완벽히 방어함.
# ==========================================================
import logging
import datetime
from zoneinfo import ZoneInfo
import os
import math
import asyncio
import yfinance as yf
import html
import glob
import tempfile
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from global_throttle import GlobalThrottle

class CallbackOrderHandler:
    def __init__(self, config, broker, strategy, queue_ledger, sync_engine, view, tx_lock):
        self.cfg = config
        self.broker = broker
        self.strategy = strategy
        self.queue_ledger = queue_ledger
        self.sync_engine = sync_engine
        self.view = view
        self.tx_lock = tx_lock

    def _safe_float(self, val):
        try:
            f_val = float(str(val or 0.0).replace(',', ''))
            if math.isnan(f_val) or math.isinf(f_val):
                return 0.0
            return f_val
        except Exception:
            return 0.0

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, controller, action: str, sub: str, data: list):
        query = update.callback_query
        chat_id = update.effective_chat.id

        if action == "EMERGENCY_REQ":
            ticker = sub
            status_code, _ = await controller.commands_handler._get_market_status()
            if status_code not in ["PRE", "REG"]:
                await query.answer("❌ [격발 차단] 현재 장운영시간(정규장/프리장)이 아닙니다.", show_alert=True)
                return
                
            if not getattr(self, 'queue_ledger', None):
                from queue_ledger import QueueLedger
                self.queue_ledger = await asyncio.wait_for(asyncio.to_thread(QueueLedger), timeout=5.0)
            
            q_data = await asyncio.wait_for(asyncio.to_thread(self.queue_ledger.get_queue, ticker), timeout=10.0) or []
            valid_q_data = [item for item in q_data if isinstance(item, dict)]
            
            total_q = sum(int(self._safe_float(item.get("qty"))) for item in valid_q_data)
            
            if total_q == 0 or not valid_q_data:
                await query.answer("⚠️ 큐(Queue)가 텅 비어있어 수혈할 잔여 물량이 없습니다.", show_alert=True)
                return
            
            try:
                await query.answer()
            except Exception:
                pass
                
            emergency_qty = int(self._safe_float(valid_q_data[-1].get('qty'))) 
            emergency_price = self._safe_float(valid_q_data[-1].get('price'))
            
            msg, markup = self.view.get_emergency_moc_confirm_menu(ticker, emergency_qty, emergency_price)
            try:
                await query.edit_message_text(msg, reply_markup=markup, parse_mode='HTML')
            except Exception:
                pass

        elif action == "EMERGENCY_EXEC":
            ticker = sub
            trigger_sync = False
            status_code, _ = await controller.commands_handler._get_market_status()
            
            if status_code not in ["PRE", "REG"]:
                await query.answer("❌ [격발 차단] 현재 장운영시간(정규장/프리장)이 아닙니다.", show_alert=True)
                return
             
            if not getattr(self, 'queue_ledger', None):
                from queue_ledger import QueueLedger
                self.queue_ledger = await asyncio.wait_for(asyncio.to_thread(QueueLedger), timeout=5.0)
     
            q_data = await asyncio.wait_for(asyncio.to_thread(self.queue_ledger.get_queue, ticker), timeout=10.0) or []
            valid_q_data = [item for item in q_data if isinstance(item, dict)]
            
            if not valid_q_data:
                await query.answer("⚠️ 큐(Queue)가 텅 비어있어 수혈할 잔여 물량이 없습니다.", show_alert=True)
                return
            
            try:
                await query.answer("⏳ KIS 서버에 수동 긴급 수혈(MOC) 명령을 격발합니다...", show_alert=False)
            except Exception:
                pass
            
            emergency_qty = int(self._safe_float(valid_q_data[-1].get('qty'))) 
            
            if emergency_qty > 0:
                await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                
                # 🚨 MODIFIED: [단일 지층 팽창 자가 치유를 위해 파라미터 무결성 주입 결속]
                safe_prev_c = 0.0
                for attempt in range(3):
                    try:
                        await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                        p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_previous_close, ticker), timeout=10.0)
                        safe_prev_c = self._safe_float(p_val)
                        if safe_prev_c > 0: break
                    except Exception:
                        if attempt == 2: pass
                        else: await asyncio.sleep(1.0 * (2 ** attempt))

                safe_seed = self._safe_float(await asyncio.wait_for(asyncio.to_thread(self.cfg.get_seed, ticker), timeout=10.0))
                portion_budget = safe_seed * 0.15
                
                async with self.tx_lock:
                    try:
                        res = await asyncio.wait_for(
                            asyncio.to_thread(self.broker.send_order, ticker, "SELL", emergency_qty, 0.0, "MOC"),
                            timeout=10.0
                        )
                    except Exception as e:
                        logging.error(f"🚨 긴급수혈 통신 에러/타임아웃: {e}")
                        res = None
                    
                    if isinstance(res, dict) and str(res.get('rt_cd', '')) == '0':
                        await asyncio.wait_for(
                            asyncio.to_thread(self.queue_ledger.pop_lots, ticker, emergency_qty, 0.0, prev_close=safe_prev_c, portion_budget=portion_budget),
                            timeout=10.0
                        )
                        
                        def _nuke_snapshot_and_state_emg():
                            for f in glob.glob(f"data/daily_snapshot_*_{ticker}.json"):
                                with GlobalThrottle.get_file_lock(f):
                                    try: os.remove(f)
                                    except OSError: pass
                            for f in glob.glob(f"data/vwap_state_*_{ticker}.json"):
                                with GlobalThrottle.get_file_lock(f):
                                    try: os.remove(f)
                                    except OSError: pass
                                    
                            est_now = datetime.datetime.now(ZoneInfo('America/New_York'))
                            today_str = est_now.strftime('%Y-%m-%d')
                            empty_state = {"date": today_str, "hijacked": True, "orders": []}
                            
                            for f_path in [f"data/vrev_slice_state_{ticker}.json", f"data/vrev_aftermarket_state_{ticker}.json"]:
                                with GlobalThrottle.get_file_lock(f_path):
                                    dir_name = os.path.dirname(f_path) or '.'
                                    try: os.makedirs(dir_name, exist_ok=True)
                                    except OSError: pass
                                    try:
                                        fd, tmp_path = tempfile.mkstemp(dir=dir_name, text=True)
                                        with os.fdopen(fd, 'w', encoding='utf-8') as f_out:
                                            json.dump(empty_state, f_out, ensure_ascii=False, indent=4)
                                            f_out.flush()
                                            os.fsync(f_out.fileno())
                                        os.replace(tmp_path, f_path)
                                    except Exception: pass
                                    
                        await asyncio.wait_for(asyncio.to_thread(_nuke_snapshot_and_state_emg), timeout=10.0)
                        
                        trigger_sync = True
                        
                        msg = f"🚨 <b>[{html.escape(str(ticker))}] 수동 긴급 수혈 (Emergency MOC) 격발 완료!</b>\n"
                        msg += f"▫️ 포트폴리오 매니저의 승인 하에 최근 로트 <b>{emergency_qty}주</b>를 시장가(MOC)로 강제 청산했습니다.\n"
                        msg += "▫️ 큐(Queue) 장부에 원자적으로 동기화 반영되었으며 스냅샷이 소각되었습니다."
                        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
                        
                        new_q_data = await asyncio.wait_for(asyncio.to_thread(self.queue_ledger.get_queue, ticker), timeout=10.0) or []
                        new_msg, markup = self.view.get_queue_management_menu(ticker, new_q_data)
                        try:
                            await query.edit_message_text(new_msg, reply_markup=markup, parse_mode='HTML')
                        except Exception:
                            pass
                    else:
                        err_msg = html.escape(str(res.get('msg1') or '알 수 없는 에러')) if isinstance(res, dict) else '응답 없음/통신 장애'
                        try:
                            await query.edit_message_text(f"❌ <b>[{html.escape(str(ticker))}] 수동 긴급 수혈 실패:</b> {err_msg}", parse_mode='HTML')
                        except Exception:
                            pass

            if trigger_sync:
                if ticker not in self.sync_engine.sync_locks:
                    self.sync_engine.sync_locks[ticker] = asyncio.Lock()
                if not self.sync_engine.sync_locks[ticker].locked():
                    await self.sync_engine.process_auto_sync(ticker, chat_id, context, silent_ledger=True)

        elif action == "EXEC":
            t = sub
            ver = str(await asyncio.wait_for(asyncio.to_thread(self.cfg.get_version, t), timeout=10.0) or "")

            try:
                await query.answer()
                await query.edit_message_text(f"🚀 {html.escape(str(t))} 수동 강제 전송 시작 (최신 잔고 스냅샷 강제 갱신 중)...")
            except Exception:
                pass
            
            holdings = None
            cash = 0.0
            for attempt in range(3):
                try:
                    await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                    res = await asyncio.wait_for(asyncio.to_thread(self.broker.get_account_balance), timeout=10.0)
                    cash, holdings = self._safe_float(res[0]) if isinstance(res, (list, tuple)) and len(res) > 0 else 0.0, res[1] if isinstance(res, (list, tuple)) and len(res) > 1 else {}
                    break
                except Exception:
                    if attempt == 2: holdings = None
                    else: await asyncio.sleep(1.0 * (2 ** attempt))
                
            if holdings is None:
                try:
                    await query.edit_message_text("❌ API 통신 오류로 잔고를 확인할 수 없어 실행을 차단합니다. 잠시 후 다시 시도해 주세요.")
                except Exception:
                    pass
                return

            try:
                from scheduler_core import get_budget_allocation
                active_tickers_list = await asyncio.wait_for(asyncio.to_thread(self.cfg.get_active_tickers), timeout=10.0) or []
                _, alloc_cash_dict = await asyncio.wait_for(asyncio.to_thread(get_budget_allocation, cash, active_tickers_list, self.cfg), timeout=10.0)
                alloc_cash_dict = alloc_cash_dict or {}
                allocated_budget = self._safe_float(alloc_cash_dict.get(t))
            except Exception as e:
                logging.error(f"🚨 예산 할당 모듈 로드 실패 (N빵 강제 분할 폴백): {e}")
                try:
                    active_tickers_list = await asyncio.wait_for(asyncio.to_thread(self.cfg.get_active_tickers), timeout=10.0) or []
                    div_count = max(1, len(active_tickers_list))
                except Exception:
                    div_count = 1
                allocated_budget = self._safe_float(cash) / div_count  
            
            if not isinstance(holdings, dict):
                holdings = {}
            h = holdings.get(t) or {'qty':0, 'avg':0}
            
            curr_p, prev_c = 0.0, 0.0
            for attempt in range(3):
                try:
                    await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                    curr_p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_current_price, t), timeout=10.0)
                    curr_p = self._safe_float(curr_p_val)
                    prev_c_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_previous_close, t), timeout=10.0)
                    prev_c = self._safe_float(prev_c_val)
                    break
                except Exception:
                    if attempt == 2: pass
                    else: await asyncio.sleep(1.0 * (2 ** attempt))
                    
            safe_avg = self._safe_float(h.get('avg')) 
            safe_qty = max(0, int(self._safe_float(h.get('qty'))))
            
            status_code, _ = await controller.commands_handler._get_market_status()
            if status_code in ["AFTER", "CLOSE", "PRE"]:
                try:
                    def get_exact_prev_close(ticker_name):
                        GlobalThrottle.wait_api_sync()
                        df = yf.Ticker(ticker_name).history(period="5d", interval="1m", prepost=True, timeout=5)
                        if not df.empty and 'Close' in df.columns:
                            tz_est = ZoneInfo('America/New_York')
                            tz_now = datetime.datetime.now(tz_est)
                            cutoff_date = tz_now.date()
                            if tz_now.time() <= datetime.time(16, 0, 30):
                                cutoff_date -= datetime.timedelta(days=1)
                            
                            if df.index.tzinfo is None:
                                df.index = df.index.tz_localize('UTC').tz_convert(tz_est)
                            else:
                                df.index = df.index.tz_convert(tz_est)
                                
                            past_df = df[df.index.date <= cutoff_date].copy()
                            if not past_df.empty:
                                past_df['Close'] = past_df['Close'].ffill().bfill()
                                regular_past = past_df.between_time('09:30', '15:59')
                                if not regular_past.empty:
                                    val = float(regular_past['Close'].iloc[-1])
                                else:
                                    val = float(past_df['Close'].iloc[-1])
                                return val if not math.isnan(val) else None
                        return None
                    
                    yf_close = None
                    for attempt in range(3):
                        try:
                            yf_close = await asyncio.wait_for(asyncio.to_thread(get_exact_prev_close, t), timeout=10.0)
                            break
                        except Exception:
                            if attempt == 2: pass
                            else: await asyncio.sleep(1.0 * (2 ** attempt))
                    
                    if yf_close and yf_close > 0:
                        prev_c = yf_close
                except Exception as e:
                    logging.debug(f"YF 정규장 종가 롤오버 스캔 실패 ({t}): {e}")
                
                if status_code == "CLOSE":
                    curr_p = prev_c
          
            ma_5day = 0.0
            for attempt in range(3):
                try:
                    await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                    ma_5day_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_5day_ma, t), timeout=10.0)
                    ma_5day = self._safe_float(ma_5day_val)
                    break
                except Exception:
                    if attempt == 2: ma_5day = 0.0
                    else: await asyncio.sleep(1.0 * (2 ** attempt))
                    
            is_manual_vwap = await asyncio.wait_for(asyncio.to_thread(getattr(self.cfg, 'get_manual_vwap_mode', lambda x: False), t), timeout=10.0)
            
            try:
                plan = await asyncio.wait_for(asyncio.to_thread(self.strategy.get_plan, t, curr_p, safe_avg, safe_qty, prev_c, ma_5day=ma_5day, market_type="REG", available_cash=allocated_budget, is_simulation=True, is_snapshot_mode=False), timeout=10.0)
            except Exception as e:
                logging.error(f"🚨 [{t}] 수동 전송 플랜 생성 에러 (샌드박스 방어): {e}")
                plan = {}
            
            if not isinstance(plan, dict):
                plan = {}

            icon = "⚖️" if ver == "V_REV" else "💎"
            title = f"{icon} <b>[{html.escape(str(t))}] 예방적 덫 수동 주문 실행</b>\n"
            msg = title
            all_success = True
       
            target_orders = plan.get('core_orders') or plan.get('orders') or []
            if not isinstance(target_orders, list): target_orders = []
            
            is_market_active_now = status_code in ["PRE", "REG", "AFTER"]
            
            est_z = ZoneInfo('America/New_York')
            kst_z = ZoneInfo('Asia/Seoul')
            curr_est = datetime.datetime.now(est_z)
            
            b_start = curr_est.replace(hour=15, minute=26, second=0, microsecond=0)
            s_start = curr_est + datetime.timedelta(minutes=3)
            a_start = max(b_start, s_start)
            b_end = curr_est.replace(hour=15, minute=56, second=0, microsecond=0)
            
            dyn_start_t = a_start.astimezone(kst_z).strftime("%H%M%S")
            dyn_end_t = b_end.astimezone(kst_z).strftime("%H%M%S")

            for o in target_orders:
                if not isinstance(o, dict): continue
                try:
                    await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                    if str(o.get('type', '')) == 'VWAP' or is_market_active_now:
                        async with self.tx_lock:
                            res = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.broker.send_order, 
                                    t, str(o.get('side', '')), int(self._safe_float(o.get('qty'))), self._safe_float(o.get('price')), str(o.get('type', '')),
                                    start_time=dyn_start_t if str(o.get('type', '')) == 'VWAP' else None,
                                    end_time=dyn_end_t if str(o.get('type', '')) == 'VWAP' else None
                                ),
                                timeout=10.0
                            )
                    else:
                        async with self.tx_lock:
                            res = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.broker.send_reservation_order, 
                                    t, str(o.get('side', '')), int(self._safe_float(o.get('qty'))), self._safe_float(o.get('price')), str(o.get('type', ''))
                                ),
                                timeout=10.0
                            )
                except Exception as e:
                    logging.error(f"🚨 V14/VREV 1차 덫 장전 통신 에러/타임아웃: {e}")
                    res = None
            
                is_success = isinstance(res, dict) and str(res.get('rt_cd', '')) == '0'
                if not is_success:
                    all_success = False
                
                err_msg = html.escape(str(res.get('msg1') or '오류')) if isinstance(res, dict) else '응답 없음/통신 장애'
                status_icon = '✅' if is_success else f'❌({err_msg})'
                msg += f"└ 1차 필수: {html.escape(str(o.get('desc', '')))} {int(self._safe_float(o.get('qty')))}주: {status_icon}\n"
            
            target_bonus = plan.get('bonus_orders') or []
            if not isinstance(target_bonus, list): target_bonus = []
            
            for o in target_bonus:
                if not isinstance(o, dict): continue
                try:
                    await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                    if str(o.get('type', '')) == 'VWAP' or is_market_active_now:
                        async with self.tx_lock:
                            res = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.broker.send_order, 
                                    t, str(o.get('side', '')), int(self._safe_float(o.get('qty'))), self._safe_float(o.get('price')), str(o.get('type', '')),
                                    start_time=dyn_start_t if str(o.get('type', '')) == 'VWAP' else None,
                                    end_time=dyn_end_t if str(o.get('type', '')) == 'VWAP' else None
                                ),
                                timeout=10.0
                            )
                    else:
                        async with self.tx_lock:
                            res = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.broker.send_reservation_order, 
                                    t, str(o.get('side', '')), int(self._safe_float(o.get('qty'))), self._safe_float(o.get('price')), str(o.get('type', ''))
                                ),
                                timeout=10.0
                            )
                except Exception as e:
                    logging.error(f"🚨 V14/VREV 2차 보너스 덫 장전 통신 에러/타임아웃: {e}")
                    res = None
        
                is_success = isinstance(res, dict) and str(res.get('rt_cd', '')) == '0'
                err_msg = html.escape(str(res.get('msg1') or '잔금패스')) if isinstance(res, dict) else '응답 없음/통신 장애'
                status_icon = '✅' if is_success else f'❌({err_msg})'
                msg += f"└ 2차 보너스: {html.escape(str(o.get('desc', '')))} {int(self._safe_float(o.get('qty')))}주: {status_icon}\n"
            
            if len(target_orders) == 0 and len(target_bonus) == 0:
                 msg += "\n💤 <b>장전할 주문이 없습니다 (관망/예산소진)</b>"
            elif all_success and len(target_orders) > 0:
                await asyncio.wait_for(asyncio.to_thread(self.cfg.set_lock, t, "REG"), timeout=10.0)
                msg += "\n🔒 <b>필수 주문 전송 완료 (잠금 설정됨)</b>"
            else:
                msg += "\n⚠️ <b>일부 필수 주문 실패 (매매 잠금 보류)</b>"

            await context.bot.send_message(chat_id, msg, parse_mode='HTML')

        elif action == "CANCEL_EXEC":
            t = sub
            try:
                await query.answer()
                await query.edit_message_text(f"🛑 <b>[{html.escape(str(t))}] 수동 매매(일반/예약 덫) 취소 집행 중...</b>", parse_mode='HTML')
            except Exception:
                pass
            
            nuked_count = 0
            err_count = 0
            
            try:
                est_now = datetime.datetime.now(ZoneInfo('America/New_York'))
                d_str = est_now.strftime('%Y%m%d')
                
                resv_orders = []
                for attempt in range(3):
                    try:
                        await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                        resv_orders = await asyncio.wait_for(
                            asyncio.to_thread(self.broker.get_reservation_orders, t, d_str, d_str),
                            timeout=10.0
                        )
                        break
                    except Exception:
                        if attempt == 2: resv_orders = []
                        else: await asyncio.sleep(1.0 * (2 ** attempt))
                
                if resv_orders and isinstance(resv_orders, list):
                    for req in resv_orders:
                        if not isinstance(req, dict): continue
                        odno = str(req.get('ovrs_rsvn_odno') or req.get('odno') or '')
                        ord_dt = str(req.get('rsvn_ord_rcit_dt') or req.get('ord_dt') or d_str)
                        if odno:
                            try:
                                await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                                async with self.tx_lock:
                                    await asyncio.wait_for(
                                        asyncio.to_thread(self.broker.cancel_reservation_order, ord_dt, odno),
                                        timeout=10.0
                                    )
                                nuked_count += 1
                            except Exception as e:
                                logging.error(f"🚨 [{t}] 수동 예약 덫 취소 실패: {e}")
                                err_count += 1
            except Exception as e:
                err_count += 1

            try:
                unfilled = []
                for attempt in range(3):
                    try:
                        await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                        unfilled = await asyncio.wait_for(
                            asyncio.to_thread(self.broker.get_unfilled_orders_detail, t),
                            timeout=10.0
                        )
                        break
                    except Exception:
                        if attempt == 2: unfilled = []
                        else: await asyncio.sleep(1.0 * (2 ** attempt))
                        
                if unfilled and isinstance(unfilled, list):
                    for uo in unfilled:
                        if not isinstance(uo, dict): continue
                        u_odno = str(uo.get('odno') or '')
                        if u_odno:
                            try:
                                await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                                async with self.tx_lock:
                                    await asyncio.wait_for(
                                        asyncio.to_thread(self.broker.cancel_order, t, u_odno),
                                        timeout=10.0
                                    )
                                nuked_count += 1
                            except Exception as e:
                                logging.error(f"🚨 [{t}] 수동 일반 덫 취소 실패: {e}")
                                err_count += 1
            except Exception as e:
                err_count += 1

            if nuked_count > 0:
                await asyncio.wait_for(asyncio.to_thread(self.cfg.reset_lock_for_ticker, t), timeout=10.0)

            if err_count > 0:
                await context.bot.send_message(chat_id, f"⚠️ <b>[{html.escape(str(t))}] 수동 취소 완료 (일부 오류 발생)</b>\n▫️ 총 <b>{nuked_count}건</b>의 덫을 파기하고 매매 잠금을 해제했으나, {err_count}건의 오류가 발생했습니다.", parse_mode='HTML')
            elif nuked_count > 0:
                await context.bot.send_message(chat_id, f"🛑 <b>[{html.escape(str(t))}] 수동 취소 팩트 집행 완료</b>\n▫️ 총 <b>{nuked_count}건</b>의 미체결 및 예약 덫을 100% 파기(Nuke)하고 당일 매매 잠금을 <b>해제(Unlock)</b>했습니다.", parse_mode='HTML')
            else:
                await context.bot.send_message(chat_id, f"ℹ️ <b>[{html.escape(str(t))}] 수동 취소 결과</b>\n▫️ 취소할 덫이 없습니다.", parse_mode='HTML')

        elif action == "MANUAL_PORTION":
            side = sub
            ticker = data[2] if len(data) > 2 else ""
            is_exec = (len(data) > 3 and data[3] == "EXEC")

            version = str(await asyncio.wait_for(asyncio.to_thread(self.cfg.get_version, ticker), timeout=10.0) or "")
            if version != "V_REV":
                try: await query.answer("❌ [격발 차단] V-REV 모드 전용 기능입니다. 오리지널 모드에서는 사용할 수 없습니다.", show_alert=True)
                except Exception: pass
                return

            status_code, _ = await controller.commands_handler._get_market_status()
            if status_code not in ["PRE", "REG", "AFTER"]:
                try: await query.answer("❌ [격발 차단] 현재 장운영시간(프리/정규/애프터장)이 아닙니다.", show_alert=True)
                except Exception: pass
                return

            if not is_exec:
                try: await query.answer(f"⏳ [{ticker}] 1회분 수동 {side} 타점 계산 중...", show_alert=False)
                except Exception: pass

                try:
                    seed = self._safe_float(await asyncio.wait_for(asyncio.to_thread(self.cfg.get_seed, ticker), timeout=10.0))
                    budget = seed * 0.15 

                    if not getattr(self, 'queue_ledger', None):
                        from queue_ledger import QueueLedger
                        self.queue_ledger = await asyncio.wait_for(asyncio.to_thread(QueueLedger), timeout=5.0)

                    cash = 0.0
                    for attempt in range(3):
                        try:
                            await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                            res_bal = await asyncio.wait_for(asyncio.to_thread(self.broker.get_account_balance), timeout=10.0)
                            cash = self._safe_float(res_bal[0]) if isinstance(res_bal, (list, tuple)) and len(res_bal) > 0 else 0.0
                            break
                        except Exception:
                            if attempt == 2: pass
                            else: await asyncio.sleep(1.0 * (2 ** attempt))

                    exec_price = 0.0
                    for attempt in range(3):
                        try:
                            await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                            if side == "BUY":
                                p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_ask_price, ticker), timeout=10.0)
                            else:
                                p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_bid_price, ticker), timeout=10.0)
                            exec_price = self._safe_float(p_val)
                            if exec_price > 0: break
                        except Exception:
                            if attempt == 2: pass
                            else: await asyncio.sleep(1.0 * (2 ** attempt))

                    if exec_price <= 0.0:
                        for attempt in range(3):
                            try:
                                await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                                c_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_current_price, ticker), timeout=10.0)
                                exec_price = self._safe_float(c_val)
                                if exec_price > 0: break
                            except Exception:
                                if attempt == 2: pass
                                else: await asyncio.sleep(1.0 * (2 ** attempt))

                    if exec_price <= 0.0:
                        try: await query.answer("❌ 실시간 호가 스캔 실패", show_alert=True)
                        except Exception: pass
                        return

                    target_qty = math.floor(budget / exec_price)

                    if side == "BUY":
                        max_buy_qty = math.floor(cash / exec_price)
                        final_qty = min(target_qty, max_buy_qty)
                    else:
                        q_data = await asyncio.wait_for(asyncio.to_thread(self.queue_ledger.get_queue, ticker), timeout=10.0) or []
                        total_q = sum(int(self._safe_float(item.get("qty"))) for item in q_data if isinstance(item, dict))
                        final_qty = min(target_qty, total_q)

                    if final_qty <= 0:
                        try: await query.answer("⚠️ 예산 부족 또는 잔고/큐 수량이 부족하여 0주 산출됨.", show_alert=True)
                        except Exception: pass
                        return

                    action_kr = "매수" if side == "BUY" else "매도"
                    safe_t = html.escape(str(ticker))
                    
                    msg = f"🚨 <b>[{safe_t} 수동 1회분 {action_kr} 승인 대기]</b> 🚨\n\n"
                    msg += f"▫️ 타격 예정 수량: <b>{final_qty}주</b>\n"
                    msg += f"▫️ 타격 예상 단가: <b>${exec_price:.2f}</b> (LIMIT)\n\n"
                    msg += "⚠️ <b>포트폴리오 매니저 경고:</b>\n"
                    msg += "하단 승인 버튼 클릭 시, KIS 서버로 실시간 API가 즉시 발사되며 취소할 수 없습니다. 정말 전송하시겠습니까?"

                    keyboard = [
                        [InlineKeyboardButton(f"🔥 [{safe_t}] {final_qty}주 {action_kr} 최종 격발", callback_data=f"MANUAL_PORTION:{side}:{ticker}:EXEC")],
                        [InlineKeyboardButton("❌ 작전 취소 (장부 대시보드 복귀)", callback_data=f"REC:VIEW:{ticker}")]
                    ]
                    markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(msg, reply_markup=markup, parse_mode='HTML')

                except Exception as e:
                    logging.error(f"🚨 수동 1회분 예상 타점 연산 에러: {e}")
                    try: await query.answer(f"❌ 오류: {e}", show_alert=True)
                    except Exception: pass

            else:
                try: await query.answer(f"⏳ [{ticker}] 1회분 수동 {side} 전송 중...", show_alert=False)
                except Exception: pass

                trigger_sync = False
                
                try:
                    seed = self._safe_float(await asyncio.wait_for(asyncio.to_thread(self.cfg.get_seed, ticker), timeout=10.0))
                    budget = seed * 0.15

                    if not getattr(self, 'queue_ledger', None):
                        from queue_ledger import QueueLedger
                        self.queue_ledger = await asyncio.wait_for(asyncio.to_thread(QueueLedger), timeout=5.0)

                    cash = 0.0
                    for attempt in range(3):
                        try:
                            await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                            res_bal = await asyncio.wait_for(asyncio.to_thread(self.broker.get_account_balance), timeout=10.0)
                            cash = self._safe_float(res_bal[0]) if isinstance(res_bal, (list, tuple)) and len(res_bal) > 0 else 0.0
                            break
                        except Exception:
                            if attempt == 2: pass
                            else: await asyncio.sleep(1.0 * (2 ** attempt))

                    exec_price = 0.0
                    for attempt in range(3):
                        try:
                            await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                            if side == "BUY":
                                p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_ask_price, ticker), timeout=10.0)
                            else:
                                p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_bid_price, ticker), timeout=10.0)
                            exec_price = self._safe_float(p_val)
                            if exec_price > 0: break
                        except Exception:
                            if attempt == 2: pass
                            else: await asyncio.sleep(1.0 * (2 ** attempt))

                    if exec_price <= 0.0:
                        for attempt in range(3):
                            try:
                                await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                                c_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_current_price, ticker), timeout=10.0)
                                exec_price = self._safe_float(c_val)
                                if exec_price > 0: break
                            except Exception:
                                if attempt == 2: pass
                                else: await asyncio.sleep(1.0 * (2 ** attempt))

                    if exec_price <= 0.0:
                        try: await query.edit_message_text("❌ 실시간 호가 스캔 실패. 취소되었습니다.", parse_mode='HTML')
                        except Exception: pass
                        return

                    target_qty = math.floor(budget / exec_price)

                    if side == "BUY":
                        max_buy_qty = math.floor(cash / exec_price)
                        final_qty = min(target_qty, max_buy_qty)
                    else:
                        q_data = await asyncio.wait_for(asyncio.to_thread(self.queue_ledger.get_queue, ticker), timeout=10.0) or []
                        total_q = sum(int(self._safe_float(item.get("qty"))) for item in q_data if isinstance(item, dict))
                        final_qty = min(target_qty, total_q)

                    if final_qty <= 0:
                        try: await query.edit_message_text("⚠️ 예산 부족 또는 잔고/큐 수량이 부족하여 취소되었습니다.", parse_mode='HTML')
                        except Exception: pass
                        return

                    # 🚨 MODIFIED: [단일 지층 팽창 자가 치유를 위해 파라미터 무결성 주입 결속]
                    safe_prev_c = 0.0
                    for attempt in range(3):
                        try:
                            await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                            p_val = await asyncio.wait_for(asyncio.to_thread(self.broker.get_previous_close, ticker), timeout=10.0)
                            safe_prev_c = self._safe_float(p_val)
                            if safe_prev_c > 0: break
                        except Exception:
                            if attempt == 2: pass
                            else: await asyncio.sleep(1.0 * (2 ** attempt))

                    await asyncio.to_thread(GlobalThrottle.wait_api_sync)
                    async with self.tx_lock:
                        res = await asyncio.wait_for(
                            asyncio.to_thread(self.broker.send_order, ticker, side, final_qty, exec_price, "LIMIT"),
                            timeout=10.0
                        )

                        if isinstance(res, dict) and str(res.get('rt_cd', '')) == '0':
                            if side == "BUY":
                                # 🚨 MODIFIED: [지층 팽창 붕괴 자가 치유] 수동 1회분 기원을 VREV_VWAP_BUY로 일원화 락온
                                await asyncio.wait_for(asyncio.to_thread(self.queue_ledger.add_lot, ticker, final_qty, exec_price, "VREV_VWAP_BUY", prev_close=safe_prev_c, portion_budget=budget), timeout=10.0)
                            else:
                                await asyncio.wait_for(
                                    asyncio.to_thread(self.queue_ledger.pop_lots, ticker, final_qty, exec_price, prev_close=safe_prev_c, portion_budget=budget),
                                    timeout=10.0
                                )

                            await asyncio.wait_for(asyncio.to_thread(self.cfg.set_lock, ticker, "REG"), timeout=10.0)

                            def _nuke_snapshot_and_state_man():
                                for f in glob.glob(f"data/daily_snapshot_*_{ticker}.json"):
                                    with GlobalThrottle.get_file_lock(f):
                                        try: os.remove(f)
                                        except OSError: pass
                                for f in glob.glob(f"data/vwap_state_*_{ticker}.json"):
                                    with GlobalThrottle.get_file_lock(f):
                                        try: os.remove(f)
                                        except OSError: pass
                                
                                est_now = datetime.datetime.now(ZoneInfo('America/New_York'))
                                today_str = est_now.strftime('%Y-%m-%d')
                                empty_state = {"date": today_str, "hijacked": True, "orders": []}
                                
                                for f_path in [f"data/vrev_slice_state_{ticker}.json", f"data/vrev_aftermarket_state_{ticker}.json"]:
                                    with GlobalThrottle.get_file_lock(f_path):
                                        dir_name = os.path.dirname(f_path) or '.'
                                        try: os.makedirs(dir_name, exist_ok=True)
                                        except OSError: pass
                                        try:
                                            fd, tmp_path = tempfile.mkstemp(dir=dir_name, text=True)
                                            with os.fdopen(fd, 'w', encoding='utf-8') as f_out:
                                                json.dump(empty_state, f_out, ensure_ascii=False, indent=4)
                                                f_out.flush()
                                                os.fsync(f_out.fileno())
                                            os.replace(tmp_path, f_path)
                                        except Exception: pass
                                        
                            await asyncio.wait_for(asyncio.to_thread(_nuke_snapshot_and_state_man), timeout=10.0)

                            action_kr = "매수" if side == "BUY" else "매도"
                            msg = f"✅ <b>[{html.escape(str(ticker))}] 수동 1회분 {action_kr} 체결 완료!</b>\n"
                            msg += f"▫️ 팩트 타격 수량: <b>{final_qty}주</b>\n"
                            msg += f"▫️ 팩트 체결 단가: <b>${exec_price:.2f}</b> (LIMIT)\n"
                            msg += "▫️ 큐(Queue) 장부에 원자적으로 동기화 반영되었으며 스냅샷이 소각되었습니다.\n"
                            msg += "▫️ <b>당일 스케줄러 자동 매매 잠금(REG Lock)이 안전하게 락온되었습니다.</b>"
                            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')

                            trigger_sync = True
                        else:
                            err_msg = html.escape(str(res.get('msg1') or '알 수 없는 에러')) if isinstance(res, dict) else '통신 장애'
                            try: await query.edit_message_text(f"❌ <b>[{html.escape(str(ticker))}] 1회분 {side} 실패:</b> {err_msg}", parse_mode='HTML')
                            except Exception: pass

                except Exception as e:
                    logging.error(f"🚨 1회분 수동 제어 실제 격발 에러: {e}")
                    try: await query.edit_message_text(f"❌ 오류: {html.escape(str(e))}", parse_mode='HTML')
                    except Exception: pass

                if trigger_sync:
                    if ticker not in self.sync_engine.sync_locks:
                        self.sync_engine.sync_locks[ticker] = asyncio.Lock()
                    if not self.sync_engine.sync_locks[ticker].locked():
                        await self.sync_engine.process_auto_sync(ticker, chat_id, context, silent_ledger=False)
