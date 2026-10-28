from t_core import *
from t_ui import *

wait_state = {"mode": None, "sym": None}

STEP_KEYS = ("s_day", "s_mode", "s_target_days", "last_exec_date", "sold_stage", "has_held")

# ---------------------------------------------------------------- v4.3.5 재생 로그 도우미 (매매 동작은 그대로)
import re, signal
CB_PREFIX = ("trade_on_", "trade_off_", "detail_", "setday_", "setamt_", "next_pause_", "next_sell_", "next_buy2_", "slist_")

def _snap(sym, s, **vals):
    """판단 입력 스냅샷(가격·평단·수량·수익률 등) → 감사 로그에만. 일반 로그에는 audit_ref 로 연결"""
    return RL.audit("decision_input", sym=sym, mode=s.get("s_mode"), day=s.get("s_day"), target=s.get("s_target_days"),
                    sold_stage=s.get("sold_stage"), base_amount=s.get("base_amount"),
                    **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in vals.items()})

def _decide(sym, decision, outcome, reason=None, s=None, aref=None, daily=False, **kw):
    """매매 판단 1줄. daily=True 면 같은 종목·같은 이유는 하루 1번만 (50초마다 같은 줄 방지)"""
    if daily and not RL.once(f"{sym}|{decision}|{reason}"):
        RL.count(f"skip:{reason}"); return
    s = s or {}
    RL.ev("decision", decision, outcome, reason, actor="scheduler", sym_ref=RL.ref(sym),
          mode=s.get("s_mode"), day=s.get("s_day"), target=s.get("s_target_days"), audit_ref=aref, **kw)

def _broker_id(res):
    """주문 응답에서 토스 주문 식별자 찾기 (형식이 확정되지 않아 흔한 키 이름을 차례로 봄)"""
    for d in (res.get("result") if isinstance(res, dict) else None, res):
        if isinstance(d, dict):
            for k in ("orderId", "order_id", "orderNo", "order_no", "id"):
                if d.get(k): return str(d[k])
    return None

async def _order(kind, sym, side, size, ord_id, coro):
    """주문 1건 = 체인 ID 1개. 결과·예외는 원래대로 돌려줌/던짐 (기록만 추가)"""
    chain = "ord-" + (RL.ref(ord_id) or "x"); t0 = time.time()
    try:
        res = await coro
    except Exception as e:
        no_resp = "API HTTP" not in str(e)
        aref = RL.audit("order_submit_failed", chain=chain, sym=sym, side=side, size=size, client_order_id=ord_id, error=str(e)[:300])
        RL.ev("external_call", "order_submit", "failed", "no_response_maybe_filled" if no_resp else RL.reason_of(e),
              actor="scheduler", level="ERROR", chain=chain, kind=kind, side=side, sym_ref=RL.ref(sym),
              ms=int((time.time() - t0) * 1000), audit_ref=aref)
        raise
    bid = _broker_id(res)
    aref = RL.audit("order_submit", chain=chain, sym=sym, side=side, size=size, client_order_id=ord_id, broker_order_id=bid, response=res)
    RL.ev("external_call", "order_submit", "ok", None, actor="scheduler", chain=chain, kind=kind, side=side,
          sym_ref=RL.ref(sym), broker_ref=RL.ref(bid), broker_id_found=bool(bid), fill_check="not_available",
          ms=int((time.time() - t0) * 1000), audit_ref=aref)
    return res

def _cb_parts(data):
    for p in CB_PREFIX:
        if data.startswith(p): return p.rstrip("_"), data[len(p):]
    if data.startswith("browse|"): return "browse", None
    return data[:20], None
async def save_merged(cfg: dict, sym: str, drop: bool = False):
    """매매 진행 상태만 최신 설정 파일에 덮어씀 → 매매 중 텔레그램에서 바꾼 시드·전원·종목 설정이 사라지지 않음"""
    fresh = await DcaConfigManager.load(); fs = fresh.setdefault("stocks", {})
    if drop: fs.pop(sym, None)
    elif sym in fs:
        src = cfg.get("stocks", {}).get(sym, {})
        for k in STEP_KEYS:
            if k in src: fs[sym][k] = src[k]
    await DcaConfigManager.save(fresh)


async def stock_trade_allowed(sym):
    latest = await DcaConfigManager.load()
    return (
        latest.get("is_master_active", True)
        and sym in latest.get("stocks", {})
        and bool(latest["stocks"][sym].get("enabled", True))
    )

async def execute_100day_step(client: TossApiClient, is_kr_market: bool):
    cfg = await sync_holdings_from_toss(client)
    if not cfg.get("is_master_active", True):
        if RL.once(f"master_off|{is_kr_market}"): RL.ev("decision", "market_pass", "skipped", "master_off", actor="scheduler", market="KR" if is_kr_market else "US")
        return
    stocks = cfg.get("stocks", {})
    today_str = datetime.now(KST_TZ if is_kr_market else EST_TZ).strftime("%Y-%m-%d")
    alert_k = "last_fail_alert_kr" if is_kr_market else "last_fail_alert_us"
    if cfg.get(alert_k) == today_str and (time.time() - runtime_info.get("last_retry_ts", 0.0) < 900):
        RL.count("skip:fail_alert_cooldown"); return
    runtime_info["last_retry_ts"] = time.time()
    logs, completed_syms = [], []
    tp1, sr = float(cfg.get("tp1_pct", 10.0)), float(cfg.get("sr_pct", 20.0))

    for sym, s in list(stocks.items()):
        if ((s.get("currency") == "KRW") != is_kr_market): continue
        if not s.get("enabled", True): RL.count("skip:stock_disabled"); continue
        if s.get("last_exec_date") == today_str: _decide(sym, "stock_step", "skipped", "done_today", s, daily=True); continue
        is_kr = (s.get("currency") == "KRW"); ensure_stock_cycle(s, is_kr)
        s_mode, s_day, s_target = s["s_mode"], int(s["s_day"]), int(s["s_target_days"])
        if s_mode == "decision": _decide(sym, "stock_step", "skipped", "awaiting_user_decision", s, daily=True); continue
        if s_mode == "pause":
            s["s_day"] = s_day + 1; s["last_exec_date"] = today_str
            if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"⏸ 정지 대기({s_target}일) 완료"))
            _decide(sym, "pause_day", "ok", None, s)
            await save_merged(cfg, sym); continue

        base_amt = float(s.get("base_amount", 100000.0 if is_kr else 40.0))
        try:
            fresh = await DcaConfigManager.load()   # 도중에 텔레그램에서 끈 전원·종목 설정을 바로 반영
            if not fresh.get("is_master_active", True): _decide(sym, "stock_step", "skipped", "master_turned_off", s); break
            if sym not in fresh.get("stocks", {}) or not fresh["stocks"][sym].get("enabled", True): _decide(sym, "stock_step", "skipped", "stock_turned_off", s); continue
            cur_p = float(await client.get_current_price(sym) or 0.0)
            hold = await client.get_symbol_holdings(sym); avg_p, qty = 0.0, 0.0
            if isinstance(hold, dict):
                for k in ["avg_price", "avg_buy_price", "average_price", "buy_avg_price", "pchs_avg_pric"]:
                    if hold.get(k): avg_p = float(hold[k]); break
                for k in ["qty", "quantity", "holding_qty", "balance", "hold_qty", "ord_psbl_qty", "sellable_qty"]:
                    if hold.get(k): qty = float(hold[k]); break
            if qty == 0.0: qty = float(await client.get_sellable_quantity(sym) or 0.0)
            if qty > 0: s["has_held"] = True
            elif s.get("has_held") and qty <= 0:
                RL.ev("state_change", "stock_removed", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), why="holding_zero", audit_ref=_snap(sym, s, cur_price=cur_p, qty=qty))
                stocks.pop(sym, None); await save_merged(cfg, sym, drop=True); continue
            prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
            sold_stg = int(s.get("sold_stage", 0))
            if prof_pct < tp1: sold_stg = 0; s["sold_stage"] = 0
            target_stg = 1 if (tp1 <= prof_pct < tp1*2 and sold_stg < 1) else (2 if (tp1*2 <= prof_pct < tp1*3 and sold_stg < 2) else 0)
            if qty > 0 and avg_p > 0 and target_stg > 0:
                sell_q = min(int(qty), max(1, int(round(qty * (sr / 100.0))))) if is_kr else round(qty * (sr / 100.0), 4)
                if sell_q > 0:
                    if not await stock_trade_allowed(sym): _decide(sym, "take_profit", "skipped", "trade_not_allowed", s); continue
                    aref = _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, profit_pct=prof_pct, stage=target_stg, sell_qty=sell_q)
                    _decide(sym, "take_profit", "ok", None, s, aref, stage=target_stg)
                    oid = f"tp{target_stg}_{today_str}_{sym}"
                    if is_kr: await _order("take_profit", sym, "sell", sell_q, oid, client.place_kr_integer_order(sym, "sell", sell_q, oid))
                    else: await _order("take_profit", sym, "sell", sell_q, oid, client.place_us_fractional_sell(sym, sell_q, oid))
                    s["sold_stage"] = target_stg; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                    logs.append(f"🎯 {sym}: {target_stg}차 익절 ({prof_pct:+.2f}% / {sell_q}주)"); await save_merged(cfg, sym); continue
            if not is_kr and s_mode in ["buy_1", "buy_2"]:
                # 달러 부족 검사는 익절 판단 뒤에 함 (달러가 없어도 익절 매도는 진행되도록)
                usd_bal = float(await client.get_buying_power("USD") or 0.0)
                need_amt = (base_amt / 2.0) if (avg_p > 0 and qty > 0 and prof_pct >= 1.0) else base_amt
                if usd_bal < need_amt:
                    fail_reasons[sym] = f"달러 부족 (필요 ${need_amt:.2f} / 보유 ${usd_bal:.2f})"
                    if RL.once(f"{sym}|buy|usd_insufficient"):
                        _decide(sym, "buy", "skipped", "usd_insufficient", s, _snap(sym, s, usd_need=need_amt, usd_balance=usd_bal, profit_pct=prof_pct))
                    else: RL.count("skip:usd_insufficient")
                    continue
            if s_mode in ["buy_1", "buy_2"]:
                buy_amt = (base_amt / 2.0) if (avg_p > 0 and qty > 0 and prof_pct >= 1.0) else base_amt
                ord_id = f"b_{today_str}_{sym}"   # 같은 날 같은 종목은 같은 주문번호 → 재시도해도 중복 체결 방지
                try:
                    if is_kr:
                        buy_q = max(1, int(buy_amt // cur_p)) if cur_p > 0 else 1
                        if not await stock_trade_allowed(sym): _decide(sym, "buy", "skipped", "trade_not_allowed", s); continue
                        _decide(sym, "buy", "ok", None, s, _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, profit_pct=prof_pct, buy_amount=buy_amt, buy_qty=buy_q), half=buy_amt < base_amt)
                        await _order("buy", sym, "buy", buy_q, ord_id, client.place_kr_integer_order(sym, "buy", buy_q, ord_id)); logs.append(f"🛒 {sym}: {buy_q}주 매수 ({s_day+1}/{s_target}일차)")
                    else:
                        if not await stock_trade_allowed(sym): _decide(sym, "buy", "skipped", "trade_not_allowed", s); continue
                        _decide(sym, "buy", "ok", None, s, _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, profit_pct=prof_pct, buy_amount=buy_amt), half=buy_amt < base_amt)
                        await _order("buy", sym, "buy", buy_amt, ord_id, smart_us_buy(client, sym, buy_amt, cur_p, ord_id)); logs.append(f"🛒 {sym}: ${buy_amt:.2f} 매수 ({s_day+1}/{s_target}일차)")
                except Exception as oe:
                    if "API HTTP" in str(oe): raise   # 토스가 거절한 주문(체결 안 됨) → 기존처럼 실패 알림 후 재시도
                    # 응답이 끊긴 주문은 체결됐을 수 있으므로 오늘은 다시 주문하지 않음 (일차는 올리지 않음)
                    s["last_exec_date"] = today_str; fail_reasons.pop(sym, None); await save_merged(cfg, sym)
                    RL.ev("state_change", "no_reorder_today", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), why="order_no_response", day_unchanged=s_day)
                    send_panel(f"⚠️ [{sym} 매수 주문 응답 없음]\n• 체결됐을 수 있어 오늘은 다시 주문하지 않습니다.\n• 토스 앱에서 체결 여부를 확인해 주세요. (일차는 그대로 두었으니 체결됐다면 관제탑에서 일차 보정)\n• 사유: {str(oe)[:120]}", [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
                    continue
                s["s_day"] = s_day + 1; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"🛒 분할매수({s_target}일) 완료"))
                RL.ev("state_change", "step_day", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), day_before=s_day, day_after=s["s_day"], mode_after=s["s_mode"])
                await save_merged(cfg, sym)
            elif s_mode == "sell" and qty > 0:
                rem_days = max(1, s_target - s_day)
                sq = min(int(qty), max(1, int(round(qty / rem_days)))) if is_kr else (qty if (qty / rem_days * cur_p < 1.0 or rem_days == 1) else round(qty / rem_days, 4))
                if not await stock_trade_allowed(sym): _decide(sym, "split_sell", "skipped", "trade_not_allowed", s); continue
                _decide(sym, "split_sell", "ok", None, s, _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, sell_qty=sq, remain_days=rem_days))
                oid = f"s_{today_str}_{sym}"
                if is_kr: await _order("split_sell", sym, "sell", sq, oid, client.place_kr_integer_order(sym, "sell", sq, oid))
                else: await _order("split_sell", sym, "sell", sq, oid, client.place_us_fractional_sell(sym, sq, oid))
                s["s_day"] = s_day + 1; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                RL.ev("state_change", "step_day", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), day_before=s_day, day_after=s["s_day"], mode_after=s["s_mode"] if s["s_day"] < s_target else "decision")
                logs.append(f"📤 {sym}: 분할매도 ({sq}주 / {s['s_day']}/{s_target}일차)")
                if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"📤 분할매도({s_target}일) 완료"))
                await save_merged(cfg, sym)
            elif s_mode == "sell": _decide(sym, "split_sell", "skipped", "no_holding", s, daily=True)
        except Exception as e:
            fail_reasons[sym] = str(e)
            RL.err("stock_step", e, event_type="decision", sym_ref=RL.ref(sym), mode=s.get("s_mode"))
    if logs: send_panel("✅ [금일 정기 매매 체결 보고]\n" + "\n".join(logs), [[{"text": "📋 보유종목 확인", "callback_data": "stock_list"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
    for c_sym, c_title in completed_syms:
        t, kb = await build_stock_detail_view(client, c_sym)
        send_panel(f"🎉 [{c_sym} {c_title} 및 자동 정지!]\n아래에서 다음 단계를 선택해 주세요!\n\n" + t, kb)
async def check_missed_trades_alert(client: TossApiClient, is_kr_market: bool):
    cfg = await ensure_cycle_fields()
    if not cfg.get("is_master_active", True): return
    today_str = datetime.now(KST_TZ if is_kr_market else EST_TZ).strftime("%Y-%m-%d")
    alert_key = "last_fail_alert_kr" if is_kr_market else "last_fail_alert_us"
    if cfg.get(alert_key) == today_str: return
    missed = [f"• {sym}: {fail_reasons.get(sym, '잔고/거래시간 확인 필요')}" for sym, s in cfg.get("stocks", {}).items() if s.get("enabled", True) and ((s.get("currency") == "KRW") == is_kr_market) and s.get("s_mode") not in ["decision", "pause"] and s.get("last_exec_date") != today_str]
    if missed:
        RL.ev("decision", "missed_trade_alert", "ok", None, actor="scheduler", market="KR" if is_kr_market else "US", count=len(missed))
        cfg[alert_key] = today_str; await DcaConfigManager.save(cfg)
        send_panel(f"🚨 [매매 미진행/실패 알람 - {'🇰🇷 한국장' if is_kr_market else '🇺🇸 미국장'}]\n\n" + "\n".join(missed), [[{"text": "🎛 관제탑", "callback_data": "panel"}]])

async def handle_callback(cb: dict, client: TossApiClient):
    if str(cb.get("message", {}).get("chat", {}).get("id", "")) != str(CHAT_ID): RL.count("tg_other_chat"); return
    cb_id, data, msg_id = cb["id"], cb.get("data", ""), cb.get("message", {}).get("message_id")
    _act, _sym = _cb_parts(data)
    RL.ev("user_event", "tg_button", "ok", None, actor="user", button=_act, sym_ref=RL.ref(_sym), seen_message_id=msg_id)
    wait_state["mode"] = None; tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
    cfg = await ensure_cycle_fields()

    # 종목별 매매 버튼 v1
    if data.startswith(("trade_on_", "trade_off_")):
        turn_on = data.startswith("trade_on_")
        sym = data.split("_", 2)[2].strip().upper()
        latest = await DcaConfigManager.load()
        stocks = latest.get("stocks", {})
        if sym not in stocks:
            send_panel("종목이 목록에 없습니다. 보유종목을 새로고침해 주세요.",
                       [[{"text": "보유종목", "callback_data": "stock_list"}]], msg_id)
            return
        before = stocks[sym].get("enabled", True)
        stocks[sym]["enabled"] = turn_on
        await DcaConfigManager.save(latest)
        RL.ev("state_change", "stock_enabled", "ok", None, actor="user", sym_ref=RL.ref(sym), before=before, after=turn_on, master_on=latest.get("is_master_active", True))
        text, kb = await build_stock_detail_view(client, sym)
        notice = ("▶️ 해당 종목 자동매매를 시작했습니다."
                  if turn_on else "⏸ 해당 종목의 신규 자동주문을 중지했습니다.")
        if turn_on and not latest.get("is_master_active", True):
            notice += "\n전체 매매가 중지돼 있어 전체 시작 후 실행됩니다."
        send_panel(notice + "\n\n" + text, kb, msg_id)
        return
    if data.startswith("browse|"):
        parts = data.split("|")
        if len(parts) != 5 or parts[1] not in ("all", "kr", "us") or parts[2] not in ("all", "on", "off") or not parts[3].isdigit() or parts[4] not in ("0", "1"):
            return
        send_panel(*(await build_stock_list_view(client, int(parts[3]), parts[1], parts[2],
                    None if parts[4] == "1" else "")), msg_id)
        return
    if data == "stock_search":
        wait_state["mode"] = "stock_search"
        send_panel("🔎 보유종목 이름 또는 티커를 입력하세요. (예: 나이키, NKE, QLD)\n검색은 전체 시장·전체 상태에서 진행합니다.",
                   [[{"text": "🔙 목록으로", "callback_data": stock_list_callback()}]], msg_id)
        return
    if data == "panel": send_panel(*(await build_panel_view(client)), msg_id)
    elif data == "stock_list": send_panel(*(await build_stock_list_view(client, STOCK_LIST_CONTEXT["page"])), msg_id)
    elif data.startswith("slist_"): send_panel(*(await build_stock_list_view(client, int(data.split("_")[1]))), msg_id)
    elif data.startswith("detail_"): send_panel(*(await build_stock_detail_view(client, data.split("_", 1)[1])), msg_id)
    elif data.startswith("setday_"):
        sym = data.split("_", 1)[1]; wait_state["mode"], wait_state["sym"] = "day_sym", sym
        send_panel(f"🔢 [{sym}] 실제 매수 진행 일수(1~100)를 숫자로 입력해 주세요.", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
    elif data.startswith("setamt_"):
        sym = data.split("_", 1)[1]; wait_state["mode"], wait_state["sym"] = "amt_sym", sym
        is_kr = (cfg.get("stocks", {}).get(sym, {}).get("currency") == "KRW")
        send_panel(f"💰 [{sym}] 1회 기준 매수금액을 입력해 주세요.\n• 예: {'100000' if is_kr else '40'}", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
    elif data.startswith("next_pause_"):
        sym = data.split("_", 2)[-1]; wait_state["mode"], wait_state["sym"] = "next_pause", sym
        send_panel(f"⏸ [{sym}] 몇 일 동안 정지 상태로 기다릴지 숫자를 입력하세요. (예: 30)", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
    elif data.startswith("next_sell_"):
        sym = data.split("_", 2)[-1]; wait_state["mode"], wait_state["sym"] = "next_sell", sym
        send_panel(f"📤 [{sym}] 몇 일 동안 나눠서 매도할지 숫자를 입력하세요. (예: 100)", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
    elif data.startswith("next_buy2_"):
        sym = data.split("_", 2)[-1]; wait_state["mode"], wait_state["sym"] = "next_buy2", sym
        send_panel(f"🛒 [{sym}] 몇 일 동안 2차 매수할지 숫자를 입력하세요. (예: 100)", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
    elif data == "toggle_master":
        cfg["is_master_active"] = not cfg.get("is_master_active", True); await DcaConfigManager.save(cfg)
        RL.ev("state_change", "master_power", "ok", None, actor="user", before=not cfg["is_master_active"], after=cfg["is_master_active"])
        send_panel(*(await build_panel_view(client)), msg_id)
    elif data == "ask_tp": wait_state["mode"] = "tp"; send_panel("🎯 [1차익절% 매도비율%] 입력 (예: 10 20)", [[{"text": "🔙 취소", "callback_data": "panel"}]], msg_id)

async def handle_message(msg: dict, client: TossApiClient):
    if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID): return
    text = msg.get("text", "").strip()
    if not text: return
    _kind = "command" if text.startswith("/") else ("menu_word" if text in ["메뉴", "관제탑", "취소", "종목"] else (wait_state.get("mode") or "search"))
    RL.ev("user_event", "tg_message", "ok", None, actor="user", input_kind=_kind, text_len=len(text))
    cfg = await ensure_cycle_fields()   # 아래 종목 이름 확인에서 쓰므로 먼저 불러옴 (/start 무응답 오류 수정)
    if text.startswith("/") or text in ["메뉴", "관제탑", "취소", "종목"]:
        wait_state["mode"] = None
        if text in ["종목"]: send_panel(*(await build_stock_list_view(client, 0)))
        elif text.upper() in cfg.get("stocks", {}): send_panel(*(await build_stock_detail_view(client, text.upper())))
        else: send_panel(*(await build_panel_view(client)))
        return
    stocks = cfg.get("stocks", {}); m, sym = wait_state.get("mode"), wait_state.get("sym")
    if m == "stock_search":
        wait_state["mode"] = None
        send_panel(*(await build_stock_list_view(client, 0, "all", "all", text)))
        return
    if m == "day_sym" and sym in stocks:
        try:
            d = max(0, min(100, int("".join(ch for ch in text if ch.isdigit()))))
            RL.ev("state_change", "step_day_manual", "ok", None, actor="user", sym_ref=RL.ref(sym), day_before=stocks[sym].get("s_day"), day_after=d)
            stocks[sym]["s_day"] = d
            stocks[sym]["s_mode"] = "decision" if d >= int(stocks[sym].get("s_target_days", 100)) else "buy_1"
            await DcaConfigManager.save(cfg); wait_state["mode"] = None
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 진행 일수가 {d}일차로 반영되었습니다!\n\n" + t, kb)
        except: RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode="day_sym"); send_panel("❌ 숫자만 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    if m == "amt_sym" and sym in stocks:
        try:
            val = float("".join(ch for ch in text if ch.isdigit() or ch == "."))
            aref = RL.audit("base_amount_change", sym=sym, before=stocks[sym].get("base_amount"), after=val)
            stocks[sym]["base_amount"] = val; await DcaConfigManager.save(cfg); wait_state["mode"] = None
            RL.ev("state_change", "base_amount", "ok", None, actor="user", sym_ref=RL.ref(sym), audit_ref=aref)
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 1회 기준 매수금액 변경 완료!\n\n" + t, kb)
        except: RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode="amt_sym"); send_panel("❌ 숫자를 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    elif m in ["next_pause", "next_sell", "next_buy2"] and sym in stocks:
        try:
            days = max(1, int("".join(ch for ch in text if ch.isdigit())))
            mode_before = stocks[sym].get("s_mode")
            stocks[sym]["s_day"], stocks[sym]["s_target_days"] = 0, days
            stocks[sym]["s_mode"] = "pause" if m == "next_pause" else ("sell" if m == "next_sell" else "buy_2")
            RL.ev("state_change", "next_stage", "ok", None, actor="user", sym_ref=RL.ref(sym), mode_before=mode_before, mode_after=stocks[sym]["s_mode"], target=days)
            await DcaConfigManager.save(cfg); wait_state["mode"] = None
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 다음 단계({days}일) 가동 시작!\n\n" + t, kb)
        except: RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode=m); send_panel("❌ 일수를 숫자로 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    elif m == "tp":
        try:
            pts = text.split(); tp_before = (cfg.get("tp1_pct"), cfg.get("sr_pct")); cfg["tp1_pct"] = float(pts[0])
            if len(pts) >= 2: cfg["sr_pct"] = float(pts[1])
            for s in stocks.values(): s["target_profit_pct"], s["sell_ratio_pct"] = cfg["tp1_pct"], cfg["sr_pct"]
            RL.ev("state_change", "take_profit_rule", "ok", None, actor="user", before=list(tp_before), after=[cfg["tp1_pct"], cfg["sr_pct"]])
            await DcaConfigManager.save(cfg); wait_state["mode"] = None; send_panel(*(await build_panel_view(client)))
        except: RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode="tp"); send_panel("❌ 예: 10 20", [[{"text": "🔙 관제탑", "callback_data": "panel"}]])
        return
    # 설정값 입력 처리를 마친 일반 메시지는 보유종목 검색으로 처리.
    matches = select_stock_items(stocks, query=text)
    exact = [sym for sym, info in matches if text.casefold() in
             (sym.casefold(), str(info.get("name", sym)).casefold())]
    if len(exact) == 1:
        send_panel(*(await build_stock_detail_view(client, exact[0])))
    else:
        send_panel(*(await build_stock_list_view(client, 0, "all", "all", text)))

async def polling_loop(client: TossApiClient):
    tg_api("deleteWebhook", {"drop_pending_updates": False}); offset = None
    while True:
        try:
            res = await asyncio.to_thread(requests.get, f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates", params={"timeout": 20, "offset": offset} if offset else {"timeout": 20}, timeout=25)
            if res.status_code == 200:
                RL.count("tg_poll_ok")
                for upd in res.json().get("result", []):
                    offset = upd["update_id"] + 1
                    RL.new_cid("tg", upd["update_id"])   # 버튼/메시지 → 판단 → 보낸 메시지까지 같은 ID
                    try:
                        if "callback_query" in upd: await handle_callback(upd["callback_query"], client)
                        elif "message" in upd: await handle_message(upd["message"], client)
                    except Exception as he:
                        RL.err("tg_update_handle", he, event_type="user_event"); he._rl_logged = True; raise
                    finally: RL.set_cid("")
            else:
                RL.err("tg_poll", RuntimeError(f"HTTP {res.status_code}"), reason=f"tg_http_{res.status_code}")
                await asyncio.sleep(5)   # 토큰 충돌(409)·인증 오류 시 초당 수천 번 재접속 방지
        except Exception as pe:
            if not getattr(pe, "_rl_logged", False): RL.err("tg_poll", pe)
            await asyncio.sleep(3)

async def scheduler_loop(client: TossApiClient):
    last_fx, last_hol = "", ""
    n_pass = 0
    while True:
        n_pass += 1; RL.count("scheduler_tick"); RL.tick()
        try:
            now_kst, now_est = datetime.now(KST_TZ), datetime.now(EST_TZ)
            if runtime_info.get("date") != now_kst.strftime("%Y-%m-%d"):
                runtime_info["date"] = now_kst.strftime("%Y-%m-%d"); runtime_info["count"] = 0
            t_kst, hm_kst, hm_est = now_kst.strftime("%Y-%m-%d"), now_kst.strftime("%H:%M"), now_est.strftime("%H:%M")
            is_hol, reason = check_holiday()
            if is_hol and hm_kst == "09:00" and last_hol != t_kst: last_hol = t_kst; send_panel(f"🛑 [시스템 대기] {reason}", [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
            if now_kst.weekday() < 5 and "11:00" <= hm_kst <= "15:00":
                RL.new_cid("sch", "kr", t_kst, n_pass)
                await execute_100day_step(client, is_kr_market=True)
                if hm_kst >= "11:15": await check_missed_trades_alert(client, is_kr_market=True)
            if now_est.weekday() < 5 and "11:30" <= hm_est <= "15:50":
                RL.new_cid("sch", "us", now_est.strftime("%Y-%m-%d"), n_pass)
                await execute_100day_step(client, is_kr_market=False)
                if hm_est >= "11:45": await check_missed_trades_alert(client, is_kr_market=False)
        except Exception as e: RL.err("scheduler_pass", e, event_type="decision")
        finally: RL.set_cid("")
        await asyncio.sleep(50)

def _on_stop(signum, frame):
    RL.new_cid("svc", "stop"); RL.ev("state_change", "service_stop", "ok", None, signal=signum)
    RL._maybe_flush(force=True); os._exit(0)   # 예전처럼 바로 종료 (기록만 먼저 남김)

def _wrap_api(client):
    """토스 API 호출: 성공은 세기만, 실패는 오류 기록 (경로 속 종목은 가림). 호출 결과·예외는 그대로"""
    orig = client._request
    async def _req(method, endpoint, *a, **k):
        t0 = time.time()
        try:
            r = await orig(method, endpoint, *a, **k); RL.count("toss_api_ok"); return r
        except Exception as e:
            ep = re.sub(r"/[A-Z0-9.]{1,12}(?=/|$)", "/<sym>", str(endpoint).split("?")[0])
            RL.err("toss_api", e, endpoint=ep, method=method, ms=int((time.time() - t0) * 1000)); raise
    client._request = _req

async def main():
    RL.new_cid("svc", "start")
    RL.ev("state_change", "service_start", "ok", None, kr_window="11:00-15:00 KST", us_window="11:30-15:50 America/New_York", poll_sec=50)
    signal.signal(signal.SIGTERM, _on_stop)
    client = TossApiClient(client_id=TOSS_ID, client_secret=TOSS_SECRET)
    _wrap_api(client)
    t, kb = await build_panel_view(client)
    send_panel(f"✨ [토스 적립봇 {BOT_VERSION} 종목별 리스트 및 상세 제어판 적용 완료!]\n\n" + t, kb)
    RL.set_cid("")
    await asyncio.gather(polling_loop(client), scheduler_loop(client))

if __name__ == "__main__":
    asyncio.run(main())
