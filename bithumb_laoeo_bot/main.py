import time, threading
from b_core import *
from b_ui import *

wait_state = {"mode": None}

def handle_callback(cb):
    if str(cb.get("message", {}).get("chat", {}).get("id", "")) != str(CHAT_ID): return
    cb_id, data, msg_id = cb["id"], cb.get("data", ""), cb.get("message", {}).get("message_id")
    wait_state["mode"] = None; tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
    if data == "balance": send_panel(*(build_balance_board()), msg_id)
    elif data == "control": send_panel(*(build_control_view()), msg_id)
    elif data == "main": send_panel(*(build_main_view()), msg_id)
    elif data == "ver_history": send_panel(*(build_ver_history_view()), msg_id)
    elif data == "history": send_panel(f"📝 [최근 거래내역 ({BOT_VERSION})]\n\n" + ("\n".join(history[-15:]) if history else "내역 없음"), [[{"text": "💰 상황판", "callback_data": "balance"}, {"text": "🔙 메인 메뉴", "callback_data": "main"}]], msg_id)
    elif data == "toggle_power": config["power"] = not config.get("power", True); save_json(CONFIG_FILE, config); send_panel(*(build_control_view()), msg_id)
    elif data.startswith("prof_"): _, tp, sr = data.split("_"); config["target_profit_pct"], config["sell_ratio_pct"] = float(tp), float(sr); save_json(CONFIG_FILE, config); send_panel(*(build_control_view()), msg_id)
    elif data == "ask_buy": wait_state["mode"] = "setbuy"; send_panel("💵 [코인 시드 설정] 예: BTC 20000 / 삭제: BTC 0", [[{"text": "🔙 제어반", "callback_data": "control"}]], msg_id)
    elif data == "ask_day": wait_state["mode"] = "setday"; send_panel("🔢 [코인 매수일수 보정] 예: BTC 5 또는 ETH 6", [[{"text": "🔙 제어반", "callback_data": "control"}]], msg_id)
    elif data == "ask_custom": wait_state["mode"] = "setcustom"; send_panel("🎯 [1차익절% 매도비율%] 예: 10 20", [[{"text": "🔙 제어반", "callback_data": "control"}]], msg_id)

def handle_message(msg):
    if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID): return
    text = msg.get("text", "").strip()
    if not text: return
    if text.startswith("/") or text in ["메뉴", "상황판", "잔고", "제어반", "취소", "히스토리", "history"]:
        wait_state["mode"] = None
        if text in ["/balance", "상황판", "잔고"]: send_panel(*(build_balance_board()))
        elif text in ["/control", "제어반"]: send_panel(*(build_control_view()))
        elif text in ["/history", "히스토리", "history"]: send_panel(*(build_ver_history_view()))
        else: send_panel(*(build_main_view()))
        return
    if wait_state["mode"] == "setday":
        parts = text.split()
        try:
            coin = parts[0].upper(); d = max(0, int(parts[1].replace("일", "").replace("차", "")))
            state.setdefault("buy_days", {})[coin] = d; save_json(STATE_FILE, state); wait_state["mode"] = None
            send_panel(*(build_control_view()))
        except: send_panel("❌ 예: BTC 5", [[{"text": "🔙 제어반", "callback_data": "control"}]])
        return
    if wait_state["mode"] == "setbuy":
        parts = text.split()
        try:
            coin = "BTC" if len(parts) == 1 else parts[0].upper()
            amt = int((parts[0] if len(parts) == 1 else parts[1]).replace(",", "").replace("원", ""))
            if amt <= 0: config["coins"].pop(coin, None)
            else: config["coins"][coin] = amt
            save_json(CONFIG_FILE, config); wait_state["mode"] = None; send_panel(*(build_control_view()))
        except: send_panel("❌ 예: BTC 20000", [[{"text": "🔙 제어반", "callback_data": "control"}]])
        return
    elif wait_state["mode"] == "setcustom":
        parts = text.split()
        try:
            config["target_profit_pct"] = float(parts[0])
            if len(parts) >= 2: config["sell_ratio_pct"] = float(parts[1])
            save_json(CONFIG_FILE, config); wait_state["mode"] = None; send_panel(*(build_control_view()))
        except: send_panel("❌ 예: 10 20", [[{"text": "🔙 제어반", "callback_data": "control"}]])
        return
    send_panel(*(build_main_view()))

def telegram_polling_loop():
    offset = None
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates", params={"timeout": 20, "offset": offset} if offset else {"timeout": 20}, timeout=25)
            if r.status_code == 200:
                for upd in r.json().get("result", []):
                    offset = upd["update_id"] + 1
                    if "callback_query" in upd: handle_callback(upd["callback_query"])
                    elif "message" in upd: handle_message(upd["message"])
        except: time.sleep(3)

def trading_monitor_loop():
    while True:
        try:
            if config.get("power", True):
                now = datetime.now(KST); today_str = now.strftime("%Y-%m-%d")
                if runtime_info.get("date") != today_str: runtime_info["date"] = today_str; runtime_info["count"] = 0
                accs = {a["currency"]: a for a in get_accounts() if isinstance(a, dict) and "currency" in a}
                krw_bal = float(accs.get("KRW", {}).get("balance", 0))
                req_krw, _ = calc_today_required_krw(accs)
                if req_krw > 0 and krw_bal < req_krw and (time.time() - float(state.get("last_low_bal_ts", 0)) >= 1800):
                    state["last_low_bal_ts"] = time.time(); save_json(STATE_FILE, state)
                    send_panel(f"⚠️ [빗썸 잔액 부족 ({BOT_VERSION})]\n• 필요: {req_krw:,.0f}원 / 보유: {krw_bal:,.0f}원", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                tp1, sr = float(config.get("target_profit_pct", 10.0)), float(config.get("sell_ratio_pct", 20.0))
                for coin, base_amt in list(config.get("coins", {}).items()):
                    if base_amt <= 0: continue
                    t = get_ticker(coin)
                    if not t: continue
                    cur_p = float(t["trade_price"]); acc = accs.get(coin, {})
                    bal, avg_p = float(acc.get("balance", 0)), float(acc.get("avg_buy_price", 0))
                    prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and bal > 0 else 0.0
                    if prof_pct < tp1 and state["sold_stage"].get(coin, 0) != 0: state["sold_stage"][coin] = 0; save_json(STATE_FILE, state)
                    sold_stg = int(state["sold_stage"].get(coin, 0))
                    target_stg = 1 if (tp1 <= prof_pct < tp1*2 and sold_stg < 1) else (2 if (tp1*2 <= prof_pct < tp1*3 and sold_stg < 2) else 0)
                    if bal > 0 and avg_p > 0 and target_stg > 0:
                        sell_vol = round(bal * (sr / 100.0), 8)
                        if sell_vol * cur_p >= 5000:
                            ok, _ = place_order(coin, "ask", sell_vol, "market")
                            if ok:
                                state["sold_stage"][coin] = target_stg; state["last_action_date"][coin] = today_str; state["last_action_type"][coin] = f"{target_stg}차익절"
                                save_json(STATE_FILE, state); add_history(coin, f"🎯{target_stg}차익절", f"{prof_pct:+.2f}% ({sr:.0f}% 매도)")
                                send_panel(f"🎉 [{coin} {target_stg}차 익절 완료] {prof_pct:+.2f}%", [[{"text": "💰 상황판", "callback_data": "balance"}]]); continue
                    if state["last_action_date"].get(coin) != today_str and now.hour >= config.get("buy_hour", 19):
                        buy_amt = max(5000, base_amt if (avg_p == 0 or bal == 0) else (int(base_amt / 2) if prof_pct >= 1.0 else base_amt))
                        if krw_bal >= buy_amt:
                            ok, res_json = place_order(coin, "bid", buy_amt, "price")
                            if ok:
                                krw_bal -= buy_amt; state["last_action_date"][coin], state["last_action_type"][coin] = today_str, "매수완료"
                                state.setdefault("buy_days", {})[coin] = int(state.get("buy_days", {}).get(coin, 0)) + 1
                                s_days = state.get("cycle_days", {})
                                if not isinstance(s_days, dict): s_days = {}
                                cur_d = s_days.get(coin, 0)
                                if cur_d == 0:
                                    acc_t = accs.get(coin, {})
                                    cur_d = get_coin_cycle_day(coin, float(acc_t.get("avg_buy_price", 0)), float(acc_t.get("balance", 0)), buy_amt)
                                s_days[coin] = min(100, cur_d + 1)
                                state["cycle_days"] = s_days
                                save_json(STATE_FILE, state); add_history(coin, "🛒정기매수", f"{buy_amt:,.0f}원 ({prof_pct:+.2f}%)")
                                send_panel(f"✅ [{coin} 19:00 정기매수 완료 ({state['buy_days'][coin]}일차)] {buy_amt:,.0f}원", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                            else:
                                fk = f"fail_{today_str}_{coin}"
                                if not state.get(fk): state[fk] = True; save_json(STATE_FILE, state); send_panel(f"🚨 [{coin} 매수 실패] {res_json}", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                        elif now.minute >= 15:
                            fk = f"fail_{today_str}_{coin}"
                            if not state.get(fk): state[fk] = True; save_json(STATE_FILE, state); send_panel(f"🚨 [{coin} 매수 미진행] 원화 부족", [[{"text": "💰 상황판", "callback_data": "balance"}]])
        except Exception as e: print("Loop Error:", e)
        runtime_info["count"] += 1; time.sleep(60)

if __name__ == "__main__":
    t, kb = build_control_view()
    send_panel(f"✨ [빗썸 봇 {BOT_VERSION} 모듈 분리 및 자동백업 완료!]\n\n" + t, kb)
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    trading_monitor_loop()

# BOT_OFFICE_APPROVAL_CHECK_V1
