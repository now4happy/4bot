from t_core import *
from t_ui import *

wait_state = {"mode": None, "sym": None}

async def execute_100day_step(client: TossApiClient, is_kr_market: bool):
    cfg = await sync_holdings_from_toss(client)
    if not cfg.get("is_master_active", True): return
    stocks = cfg.get("stocks", {})
    today_str = datetime.now(KST_TZ if is_kr_market else EST_TZ).strftime("%Y-%m-%d")
    alert_k = "last_fail_alert_kr" if is_kr_market else "last_fail_alert_us"
    if cfg.get(alert_k) == today_str and (time.time() - runtime_info.get("last_retry_ts", 0.0) < 900): return
    runtime_info["last_retry_ts"] = time.time()
    logs, completed_syms = [], []
    tp1, sr = float(cfg.get("tp1_pct", 10.0)), float(cfg.get("sr_pct", 20.0))

    for sym, s in list(stocks.items()):
        if not s.get("enabled", True) or ((s.get("currency") == "KRW") != is_kr_market) or s.get("last_exec_date") == today_str: continue
        is_kr = (s.get("currency") == "KRW"); ensure_stock_cycle(s, is_kr)
        s_mode, s_day, s_target = s["s_mode"], int(s["s_day"]), int(s["s_target_days"])
        if s_mode == "decision": continue
        if s_mode == "pause":
            s["s_day"] = s_day + 1; s["last_exec_date"] = today_str
            if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"⏸ 정지 대기({s_target}일) 완료"))
            await DcaConfigManager.save(cfg); continue

        base_amt = float(s.get("base_amount", 100000.0 if is_kr else 40.0))
        try:
            cur_p = float(await client.get_current_price(sym) or 0.0)
            hold = await client.get_symbol_holdings(sym); avg_p, qty = 0.0, 0.0
            if isinstance(hold, dict):
                for k in ["avg_price", "avg_buy_price", "average_price", "buy_avg_price", "pchs_avg_pric"]:
                    if hold.get(k): avg_p = float(hold[k]); break
                for k in ["qty", "quantity", "holding_qty", "balance", "hold_qty", "ord_psbl_qty", "sellable_qty"]:
                    if hold.get(k): qty = float(hold[k]); break
            if qty == 0.0: qty = float(await client.get_sellable_quantity(sym) or 0.0)
            if qty > 0: s["has_held"] = True
            elif s.get("has_held") and qty <= 0: stocks.pop(sym, None); await DcaConfigManager.save(cfg); continue
            prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
            if not is_kr and s_mode in ["buy_1", "buy_2"]:
                usd_bal = float(await client.get_buying_power("USD") or 0.0)
                need_amt = (base_amt / 2.0) if (avg_p > 0 and qty > 0 and prof_pct >= 1.0) else base_amt
                if usd_bal < need_amt: fail_reasons[sym] = f"달러 부족 (필요 ${need_amt:.2f} / 보유 ${usd_bal:.2f})"; continue
            sold_stg = int(s.get("sold_stage", 0))
            if prof_pct < tp1: sold_stg = 0; s["sold_stage"] = 0
            target_stg = 1 if (tp1 <= prof_pct < tp1*2 and sold_stg < 1) else (2 if (tp1*2 <= prof_pct < tp1*3 and sold_stg < 2) else 0)
            if qty > 0 and avg_p > 0 and target_stg > 0:
                sell_q = min(int(qty), max(1, int(round(qty * (sr / 100.0))))) if is_kr else round(qty * (sr / 100.0), 4)
                if sell_q > 0:
                    if is_kr: await client.place_kr_integer_order(sym, "sell", sell_q, f"tp{target_stg}_{today_str}_{sym}")
                    else: await client.place_us_fractional_sell(sym, sell_q, f"tp{target_stg}_{today_str}_{sym}")
                    s["sold_stage"] = target_stg; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                    logs.append(f"🎯 {sym}: {target_stg}차 익절 ({prof_pct:+.2f}% / {sell_q}주)"); await DcaConfigManager.save(cfg); continue
            if s_mode in ["buy_1", "buy_2"]:
                buy_amt = (base_amt / 2.0) if (avg_p > 0 and qty > 0 and prof_pct >= 1.0) else base_amt
                ord_id = f"b_{today_str}_{sym}_{int(time.time())}"
                if is_kr:
                    buy_q = max(1, int(buy_amt // cur_p)) if cur_p > 0 else 1
                    await client.place_kr_integer_order(sym, "buy", buy_q, ord_id); logs.append(f"🛒 {sym}: {buy_q}주 매수 ({s_day+1}/{s_target}일차)")
                else:
                    await smart_us_buy(client, sym, buy_amt, cur_p, ord_id); logs.append(f"🛒 {sym}: ${buy_amt:.2f} 매수 ({s_day+1}/{s_target}일차)")
                s["s_day"] = s_day + 1; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"🛒 분할매수({s_target}일) 완료"))
                await DcaConfigManager.save(cfg)
            elif s_mode == "sell" and qty > 0:
                rem_days = max(1, s_target - s_day)
                sq = min(int(qty), max(1, int(round(qty / rem_days)))) if is_kr else (qty if (qty / rem_days * cur_p < 1.0 or rem_days == 1) else round(qty / rem_days, 4))
                if is_kr: await client.place_kr_integer_order(sym, "sell", sq, f"s_{today_str}_{sym}")
                else: await client.place_us_fractional_sell(sym, sq, f"s_{today_str}_{sym}")
                s["s_day"] = s_day + 1; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                logs.append(f"📤 {sym}: 분할매도 ({sq}주 / {s['s_day']}/{s_target}일차)")
                if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"📤 분할매도({s_target}일) 완료"))
                await DcaConfigManager.save(cfg)
        except Exception as e: fail_reasons[sym] = str(e)
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
        cfg[alert_key] = today_str; await DcaConfigManager.save(cfg)
        send_panel(f"🚨 [매매 미진행/실패 알람 - {'🇰🇷 한국장' if is_kr_market else '🇺🇸 미국장'}]\n\n" + "\n".join(missed), [[{"text": "🎛 관제탑", "callback_data": "panel"}]])

async def handle_callback(cb: dict, client: TossApiClient):
    if str(cb.get("message", {}).get("chat", {}).get("id", "")) != str(CHAT_ID): return
    cb_id, data, msg_id = cb["id"], cb.get("data", ""), cb.get("message", {}).get("message_id")
    wait_state["mode"] = None; tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
    cfg = await ensure_cycle_fields()
    if data == "panel": send_panel(*(await build_panel_view(client)), msg_id)
    elif data == "stock_list": send_panel(*(await build_stock_list_view(client, 0)), msg_id)
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
    elif data == "toggle_master": cfg["is_master_active"] = not cfg.get("is_master_active", True); await DcaConfigManager.save(cfg); send_panel(*(await build_panel_view(client)), msg_id)
    elif data == "ask_tp": wait_state["mode"] = "tp"; send_panel("🎯 [1차익절% 매도비율%] 입력 (예: 10 20)", [[{"text": "🔙 취소", "callback_data": "panel"}]], msg_id)

async def handle_message(msg: dict, client: TossApiClient):
    if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID): return
    text = msg.get("text", "").strip()
    if not text: return
    cfg = await ensure_cycle_fields()   # 아래 종목 이름 확인에서 쓰므로 먼저 불러옴 (/start 무응답 오류 수정)
    if text.startswith("/") or text in ["메뉴", "관제탑", "취소", "종목"]:
        wait_state["mode"] = None
        if text in ["종목"]: send_panel(*(await build_stock_list_view(client, 0)))
        elif text.upper() in cfg.get("stocks", {}): send_panel(*(await build_stock_detail_view(client, text.upper())))
        else: send_panel(*(await build_panel_view(client)))
        return
    stocks = cfg.get("stocks", {}); m, sym = wait_state.get("mode"), wait_state.get("sym")
    if m == "day_sym" and sym in stocks:
        try:
            d = max(0, min(100, int("".join(ch for ch in text if ch.isdigit()))))
            stocks[sym]["s_day"] = d
            stocks[sym]["s_mode"] = "decision" if d >= int(stocks[sym].get("s_target_days", 100)) else "buy_1"
            await DcaConfigManager.save(cfg); wait_state["mode"] = None
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 진행 일수가 {d}일차로 반영되었습니다!\n\n" + t, kb)
        except: send_panel("❌ 숫자만 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    if m == "amt_sym" and sym in stocks:
        try:
            val = float("".join(ch for ch in text if ch.isdigit() or ch == "."))
            stocks[sym]["base_amount"] = val; await DcaConfigManager.save(cfg); wait_state["mode"] = None
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 1회 기준 매수금액 변경 완료!\n\n" + t, kb)
        except: send_panel("❌ 숫자를 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    elif m in ["next_pause", "next_sell", "next_buy2"] and sym in stocks:
        try:
            days = max(1, int("".join(ch for ch in text if ch.isdigit())))
            stocks[sym]["s_day"], stocks[sym]["s_target_days"] = 0, days
            stocks[sym]["s_mode"] = "pause" if m == "next_pause" else ("sell" if m == "next_sell" else "buy_2")
            await DcaConfigManager.save(cfg); wait_state["mode"] = None
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 다음 단계({days}일) 가동 시작!\n\n" + t, kb)
        except: send_panel("❌ 일수를 숫자로 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    elif m == "tp":
        try:
            pts = text.split(); cfg["tp1_pct"] = float(pts[0])
            if len(pts) >= 2: cfg["sr_pct"] = float(pts[1])
            for s in stocks.values(): s["target_profit_pct"], s["sell_ratio_pct"] = cfg["tp1_pct"], cfg["sr_pct"]
            await DcaConfigManager.save(cfg); wait_state["mode"] = None; send_panel(*(await build_panel_view(client)))
        except: send_panel("❌ 예: 10 20", [[{"text": "🔙 관제탑", "callback_data": "panel"}]])
        return
    send_panel(*(await build_panel_view(client)))

async def polling_loop(client: TossApiClient):
    tg_api("deleteWebhook", {"drop_pending_updates": False}); offset = None
    while True:
        try:
            res = await asyncio.to_thread(requests.get, f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates", params={"timeout": 20, "offset": offset} if offset else {"timeout": 20}, timeout=25)
            if res.status_code == 200:
                for upd in res.json().get("result", []):
                    offset = upd["update_id"] + 1
                    if "callback_query" in upd: await handle_callback(upd["callback_query"], client)
                    elif "message" in upd: await handle_message(upd["message"], client)
        except: await asyncio.sleep(3)

async def scheduler_loop(client: TossApiClient):
    last_fx, last_hol = "", ""
    while True:
        try:
            now_kst, now_est = datetime.now(KST_TZ), datetime.now(EST_TZ)
            if runtime_info.get("date") != now_kst.strftime("%Y-%m-%d"):
                runtime_info["date"] = now_kst.strftime("%Y-%m-%d"); runtime_info["count"] = 0
            t_kst, hm_kst, hm_est = now_kst.strftime("%Y-%m-%d"), now_kst.strftime("%H:%M"), now_est.strftime("%H:%M")
            is_hol, reason = check_holiday()
            if is_hol and hm_kst == "09:00" and last_hol != t_kst: last_hol = t_kst; send_panel(f"🛑 [시스템 대기] {reason}", [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
            if now_kst.weekday() < 5 and "11:00" <= hm_kst <= "15:00":
                await execute_100day_step(client, is_kr_market=True)
                if hm_kst >= "11:15": await check_missed_trades_alert(client, is_kr_market=True)
            if now_est.weekday() < 5 and "11:30" <= hm_est <= "15:50":
                await execute_100day_step(client, is_kr_market=False)
                if hm_est >= "11:45": await check_missed_trades_alert(client, is_kr_market=False)
        except Exception as e: print("Scheduler Error:", e)
        await asyncio.sleep(50)

async def main():
    client = TossApiClient(client_id=TOSS_ID, client_secret=TOSS_SECRET)
    t, kb = await build_panel_view(client)
    send_panel(f"✨ [토스 적립봇 {BOT_VERSION} 종목별 리스트 및 상세 제어판 적용 완료!]\n\n" + t, kb)
    await asyncio.gather(polling_loop(client), scheduler_loop(client))

if __name__ == "__main__":
    asyncio.run(main())
