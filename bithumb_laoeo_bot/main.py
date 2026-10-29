import time, threading
from b_core import *
from b_ui import *

wait_state = {"mode": None}

# ---------------------------------------------------------------- v4.2.0 SMA법 재작업 초안 (승인 전 주문 잠금)
# ---------------------------------------------------------------- v4.1.0 관찰 전용 추세 신호 (매매 동작은 그대로)
# 매일 09:00 KST 이후 코인별 첫 회차에만 갱신하고, 실패해도 매수·매도는 그대로 진행한다.
# ---------------------------------------------------------------- v4.0.4 재생 로그 도우미 (매매 동작은 그대로)
import os, signal

def _decide(coin, decision, outcome, reason=None, aref=None, daily=False, **kw):
    """매매 판단 1줄. daily=True 면 같은 코인·같은 이유는 하루 1번만 (60초마다 같은 줄 방지)"""
    if daily and not RL.once(f"{coin}|{decision}|{reason}"):
        RL.count(f"skip:{reason}"); return
    RL.ev("decision", decision, outcome, reason, actor="scheduler", coin_ref=RL.ref(coin), audit_ref=aref, **kw)

def _snap(coin, **vals):
    return RL.audit("decision_input", coin=coin, **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in vals.items()})

def _on_stop(signum, frame):
    RL.new_cid("svc", "stop"); RL.ev("state_change", "service_stop", "ok", None, signal=signum)
    RL._maybe_flush(force=True); os._exit(0)   # 예전처럼 바로 종료 (기록만 먼저 남김)

def handle_callback(cb):
    if str(cb.get("message", {}).get("chat", {}).get("id", "")) != str(CHAT_ID): RL.count("tg_other_chat"); return
    cb_id, data, msg_id = cb["id"], cb.get("data", ""), cb.get("message", {}).get("message_id")
    RL.ev("user_event", "tg_button", "ok", None, actor="user", button=RL.button(data), seen_message_id=msg_id)
    wait_state["mode"] = None; tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
    if data == "balance": send_panel(*(build_balance_board()), msg_id)
    elif data == "control": send_panel(*(build_control_view()), msg_id)
    elif data == "main": send_panel(*(build_main_view()), msg_id)
    elif data == "history": send_panel(f"📝 [최근 거래내역 ({BOT_VERSION})]\n\n" + ("\n".join(history[-15:]) if history else "내역 없음"), [[{"text": "💰 상황판", "callback_data": "balance"}, {"text": "🔙 메인 메뉴", "callback_data": "main"}]], msg_id)
    elif data == "toggle_power":
        config["power"] = not config.get("power", True); save_json(CONFIG_FILE, config)
        RL.ev("state_change", "master_power", "ok", None, actor="user", before=not config["power"], after=config["power"])
        send_panel(*(build_control_view()), msg_id)
    elif data.startswith("prof_"):
        _, tp, sr = data.split("_"); before = [config.get("target_profit_pct"), config.get("sell_ratio_pct")]
        config["target_profit_pct"], config["sell_ratio_pct"] = float(tp), float(sr); save_json(CONFIG_FILE, config)
        RL.ev("state_change", "take_profit_rule", "ok", None, actor="user", before=before, after=[float(tp), float(sr)])
        send_panel(*(build_control_view()), msg_id)
    elif data.startswith("method_coin_"):
        coin = data.removeprefix("method_coin_")
        send_panel(*(build_coin_sma_view(coin)), msg_id)
    elif data.startswith("method_choose_"):
        coin = data.removeprefix("method_choose_")
        send_panel(*(build_coin_method_choice(coin)), msg_id)
    elif data.startswith("method_set_"):
        parts = data.split("_")
        if len(parts) == 4 and parts[2] in TREND_PERIOD and parts[2] in config.get("coins", {}) and parts[3] in ("1", "2"):
            coin, method = parts[2], int(parts[3])
            config.setdefault("coin_methods", {})[coin] = method
            config.setdefault("method2_approved", {})[coin] = False  # switching either direction revokes approval
            # A method switch must not trigger a retrospective crossover order.
            state.setdefault("method2_last_processed", {}).pop(coin, None)
            state.setdefault("method2_selected_on", {}).pop(coin, None)
            save_json(CONFIG_FILE, config); save_json(STATE_FILE, state)
            RL.ev("state_change", "coin_method", "ok", None, actor="user", coin_ref=RL.ref(coin), method=method)
            send_panel(*(build_coin_sma_view(coin)), msg_id)
    elif data.startswith("method_approve_"):
        coin = data.removeprefix("method_approve_")
        if coin not in TREND_PERIOD or coin not in config.get("coins", {}) or coin_method(coin) != 2:
            send_panel("❌ 해당 코인에서 SMA법을 먼저 선택하세요.",
                       [[{"text":"🔙 제어반", "callback_data":"control"}]], msg_id)
        elif coin not in config.get("method2_sell_ratios", {}) or method2_ratio(coin) is None:
            config.setdefault("method2_approved", {})[coin] = False
            save_json(CONFIG_FILE, config)
            RL.ev("decision", "method2_approval", "skipped", "ratio_required",
                  actor="user", coin_ref=RL.ref(coin))
            send_panel(f"❌ {coin} 매도비율이 저장되지 않았습니다.\n먼저 매도비율을 저장한 후 승인하세요.",
                       [[{"text":"📝 매도비율 설정", "callback_data":f"method_ratio_{coin}"}],
                        [{"text":"🔙 제어반", "callback_data":"control"}]], msg_id)
        elif coin not in config.get("sma_buy_amounts", {}) or sma_buy_amount(coin) is None:
            config.setdefault("method2_approved", {})[coin] = False
            save_json(CONFIG_FILE, config)
            RL.ev("decision", "method2_approval", "skipped", "buy_amount_required",
                  actor="user", coin_ref=RL.ref(coin))
            send_panel(f"❌ {coin} SMA법 매수금액이 저장되지 않았습니다. 먼저 금액을 설정하세요.",
                       [[{"text":"📝 SMA법 매수금액 설정", "callback_data":f"method_buy_{coin}"}],
                        [{"text":"🔙 제어반", "callback_data":"control"}]], msg_id)
        else:
            config.setdefault("method2_approved", {})[coin] = True
            save_json(CONFIG_FILE, config)
            RL.ev("state_change", "method2_approval", "ok", None,
                  actor="user", coin_ref=RL.ref(coin), approved=True)
            send_panel(f"✅ {coin} SMA법 승인됨. 설정된 신호에 따라 자동주문이 가능해집니다.",
                       [[{"text":"🔙 코인 설정", "callback_data":f"method_coin_{coin}"}]], msg_id)
    elif data.startswith("method_buy_"):
        coin = data.removeprefix("method_buy_")
        if coin in TREND_PERIOD and coin in config.get("coins", {}):
            wait_state["mode"] = "set_sma_buy"; wait_state["coin"] = coin
            send_panel(f"💵 {coin} SMA 매수금액을 숫자로 입력하세요.\n예: 100000 (원)\n시드와 별개이며 5,000원 이상입니다.",
                       [[{"text":"🔙 제어반", "callback_data":"control"}]], msg_id)
    elif data.startswith("method_ratio_"):
        coin = data.removeprefix("method_ratio_")
        if coin in TREND_PERIOD and coin in config.get("coins", {}):
            wait_state["mode"] = "set_method2_ratio"; wait_state["coin"] = coin
            send_panel(f"📉 {coin} SMA 매도비율을 숫자로 입력하세요.\n예: 50 (50% 매도)\n1~100 사이로 입력하세요.", [[{"text":"🔙 제어반", "callback_data":"control"}]], msg_id)
    elif data == "ask_buy": wait_state["mode"] = "setbuy"; send_panel("💵 [코인 시드 설정] 예: BTC 20000 / 삭제: BTC 0", [[{"text": "🔙 제어반", "callback_data": "control"}]], msg_id)
    elif data == "ask_day": wait_state["mode"] = "setday"; send_panel("🔢 [코인 매수일수 보정] 예: BTC 5 또는 ETH 6", [[{"text": "🔙 제어반", "callback_data": "control"}]], msg_id)
    elif data == "ask_custom": wait_state["mode"] = "setcustom"; send_panel("🎯 [1차익절% 매도비율%] 예: 10 20", [[{"text": "🔙 제어반", "callback_data": "control"}]], msg_id)

def handle_message(msg):
    if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID): return
    text = msg.get("text", "").strip()
    if not text: return
    RL.ev("user_event", "tg_message", "ok", None, actor="user", text_len=len(text),
          input_kind="command" if text.startswith("/") else ("menu_word" if text in ["메뉴", "상황판", "잔고", "제어반", "취소"] else (wait_state.get("mode") or "other")))
    if text.startswith("/") or text in ["메뉴", "상황판", "잔고", "제어반", "취소"]:
        wait_state["mode"] = None
        if text in ["/balance", "상황판", "잔고"]: send_panel(*(build_balance_board()))
        elif text in ["/control", "제어반"]: send_panel(*(build_control_view()))
        else: send_panel(*(build_main_view()))
        return
    if wait_state["mode"] == "set_sma_buy":
        coin = wait_state.get("coin")
        try:
            amount = int(text.replace(",", "").replace("원", "").strip())
            if coin not in TREND_PERIOD or coin not in config.get("coins", {}) or amount < 5000:
                raise ValueError("invalid SMA amount")
            config.setdefault("sma_buy_amounts", {})[coin] = amount
            # Any changed financial setting requires a new explicit approval.
            config.setdefault("method2_approved", {})[coin] = False
            save_json(CONFIG_FILE, config)
            RL.ev("state_change", "sma_buy_amount", "ok", None, actor="user",
                  coin_ref=RL.ref(coin), audit_ref=RL.audit("sma_buy_amount", coin=coin, amount=amount))
            wait_state["mode"] = None
            send_panel(*(build_coin_sma_view(coin)))
        except (ValueError, TypeError):
            send_panel("❌ SMA법 매수금액은 5,000원 이상의 정수로 입력하세요.",
                       [[{"text":"🔙 제어반", "callback_data":"control"}]])
        return
    if wait_state["mode"] == "set_method2_ratio":
        coin = wait_state.get("coin")
        try:
            ratio = float(text.replace("%", "").strip())
            if coin not in TREND_PERIOD or coin not in config.get("coins", {}) or not (float("-inf") < ratio < float("inf") and 0 < ratio <= 100):
                raise ValueError("invalid ratio")
            config.setdefault("method2_sell_ratios", {})[coin] = ratio
            config.setdefault("method2_approved", {})[coin] = False
            save_json(CONFIG_FILE, config)
            RL.ev("state_change", "method2_ratio", "ok", None, actor="user", coin_ref=RL.ref(coin), audit_ref=RL.audit("method2_ratio", coin=coin, ratio=ratio))
            wait_state["mode"] = None
            send_panel(*(build_coin_sma_view(coin)))
        except (ValueError, TypeError):
            send_panel("❌ 1~100 사이 숫자를 입력하세요.", [[{"text":"🔙 제어반", "callback_data":"control"}]])
        return
    if wait_state["mode"] == "setday":
        parts = text.split()
        try:
            coin = parts[0].upper(); d = max(0, int(parts[1].replace("일", "").replace("차", "")))
            RL.ev("state_change", "buy_day_manual", "ok", None, actor="user", coin_ref=RL.ref(coin), day_before=state.get("buy_days", {}).get(coin), day_after=d)
            state.setdefault("buy_days", {})[coin] = d; save_json(STATE_FILE, state); wait_state["mode"] = None
            send_panel(*(build_control_view()))
        except: RL.ev("user_event", "bad_input", "failed", "bad_format", actor="user", wait_mode="setday"); send_panel("❌ 예: BTC 5", [[{"text": "🔙 제어반", "callback_data": "control"}]])
        return
    if wait_state["mode"] == "setbuy":
        parts = text.split()
        try:
            coin = "BTC" if len(parts) == 1 else parts[0].upper()
            amt = int((parts[0] if len(parts) == 1 else parts[1]).replace(",", "").replace("원", ""))
            aref = RL.audit("coin_seed_change", coin=coin, before=config["coins"].get(coin), after=amt)
            if amt <= 0: config["coins"].pop(coin, None)
            else: config["coins"][coin] = amt
            save_json(CONFIG_FILE, config); wait_state["mode"] = None
            RL.ev("state_change", "coin_seed", "ok", None, actor="user", coin_ref=RL.ref(coin), removed=amt <= 0, audit_ref=aref)
            send_panel(*(build_control_view()))
        except: RL.ev("user_event", "bad_input", "failed", "bad_format", actor="user", wait_mode="setbuy"); send_panel("❌ 예: BTC 20000", [[{"text": "🔙 제어반", "callback_data": "control"}]])
        return
    elif wait_state["mode"] == "setcustom":
        parts = text.split()
        try:
            before = [config.get("target_profit_pct"), config.get("sell_ratio_pct")]
            config["target_profit_pct"] = float(parts[0])
            if len(parts) >= 2: config["sell_ratio_pct"] = float(parts[1])
            save_json(CONFIG_FILE, config); wait_state["mode"] = None
            RL.ev("state_change", "take_profit_rule", "ok", None, actor="user", before=before, after=[config["target_profit_pct"], config["sell_ratio_pct"]])
            send_panel(*(build_control_view()))
        except: RL.ev("user_event", "bad_input", "failed", "bad_format", actor="user", wait_mode="setcustom"); send_panel("❌ 예: 10 20", [[{"text": "🔙 제어반", "callback_data": "control"}]])
        return
    send_panel(*(build_main_view()))

def telegram_polling_loop():
    offset = None
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates", params={"timeout": 20, "offset": offset} if offset else {"timeout": 20}, timeout=25)
            if r.status_code == 200:
                RL.count("tg_poll_ok")
                for upd in r.json().get("result", []):
                    offset = upd["update_id"] + 1
                    RL.new_cid("tg", upd["update_id"])   # 버튼/메시지 → 보낸 메시지까지 같은 ID
                    try:
                        if "callback_query" in upd: handle_callback(upd["callback_query"])
                        elif "message" in upd: handle_message(upd["message"])
                    except Exception as he:
                        RL.err("tg_update_handle", he, event_type="user_event"); he._rl_logged = True; raise
                    finally: RL.set_cid("")
            else:
                RL.err("tg_poll", RuntimeError(f"HTTP {r.status_code}"), reason=f"tg_http_{r.status_code}")
                time.sleep(5)   # 토큰 충돌(409)·인증 오류 시 초당 수천 번 재접속 방지
        except Exception as pe:
            if not getattr(pe, "_rl_logged", False): RL.err("tg_poll", pe)
            time.sleep(3)

def method2_daily_step(coin, krw_bal, acc, today_str):
    """One decision per completed candle; method 2 never falls through to method 1.
    The draft is non-trading until user assumptions and review are confirmed.
    """
    if sma_buy_amount(coin) is None:
        _decide(coin, "method2", "skipped", "buy_amount_required", daily=True)
        return krw_bal
    if method2_ratio(coin) is None:
        _decide(coin, "method2", "skipped", "ratio_required", daily=True)
        return krw_bal
    if not method2_ready(coin):
        _decide(coin, "method2", "skipped", "approval_required", daily=True)
        return krw_bal
    # Persisted per-candle idempotency; no replay after restart.
    if state.setdefault("method2_last_processed", {}).get(coin) == today_str:
        return krw_bal
    period = TREND_PERIOD.get(coin)
    closes = get_daily_closes(coin, period + 1) if period else []
    if len(closes) < period + 1:
        _decide(coin, "method2", "skipped", "unknown_signal", daily=True)
        return krw_bal
    direction = daily_crossover(closes, period)
    if direction == "unknown":
        _decide(coin, "method2", "skipped", "unknown_signal", daily=True)
        return krw_bal
    # A newly selected method establishes a baseline without retroactive orders.
    selected_on = state.setdefault("method2_selected_on", {}).get(coin)
    if selected_on is None:
        state["method2_selected_on"][coin] = today_str
        state["method2_last_processed"][coin] = today_str
        save_json(STATE_FILE, state)
        _decide(coin, "method2", "skipped", "baseline_initialized", daily=True)
        return krw_bal
    if direction == "none":
        state["method2_last_processed"][coin] = today_str
        save_json(STATE_FILE, state)
        return krw_bal
    if state.get("last_action_date", {}).get(coin) == today_str:
        _decide(coin, "method2", "skipped", "done_today", daily=True)
        return krw_bal
    if direction == "up":
        size = sma_buy_amount(coin)  # User-entered SMA법 amount ONLY; never seed or method-1 multiplier
        if krw_bal < size:
            _decide(coin, "method2", "skipped", "krw_insufficient", daily=True)
            return krw_bal
        side, quantity, ord_type = "bid", size, "price"
    else:
        ratio = method2_ratio(coin)
        if ratio is None:
            _decide(coin, "method2", "skipped", "invalid_sell_ratio", daily=True)
            return krw_bal
        # Use available balance only; never sell locked coins.
        available = float(acc.get("balance", 0))
        quantity = round(available * ratio / 100, 8)
        if quantity <= 0 or quantity * closes[-1] < 5000:
            _decide(coin, "method2", "skipped", "below_min_order", daily=True)
            return krw_bal
        side, ord_type = "ask", "market"
    # Mark BEFORE sending to avoid reorders after timeout/restart.
    state["method2_last_processed"][coin] = today_str
    state.setdefault("last_action_date", {})[coin] = today_str
    state.setdefault("last_action_type", {})[coin] = "확인필요"
    save_json(STATE_FILE, state)
    _decide(coin, "method2", "ok", None, _snap(coin, quantity=quantity, direction=direction))
    ok, result = place_order(coin, side, quantity, ord_type)
    if ok:
        state["last_action_type"][coin] = "SMA매수" if direction == "up" else "SMA매도"
        save_json(STATE_FILE, state)
        send_panel(f"{coin} SMA법 {('매수' if direction == 'up' else '매도')} 접수", [[{"text":"💰 상황판","callback_data":"balance"}]])
        if direction == "up":
            krw_bal -= size
    else:
        _decide(coin, "method2_order", "failed", "order_failed_or_unknown", daily=True)
        send_panel(f"{coin} SMA법 주문 결과 확인 필요. 재주문하지 않습니다.", [[{"text":"💰 상황판","callback_data":"balance"}]])
    return krw_bal

def trading_monitor_loop():
    while True:
        RL.count("scheduler_tick"); RL.tick()
        try:
            if not config.get("power", True) and RL.once("power_off"):
                RL.new_cid("sch", datetime.now(KST).strftime("%Y-%m-%d"), runtime_info.get("count", 0))
                RL.ev("decision", "market_pass", "skipped", "master_off", actor="scheduler")
            if config.get("power", True):
                now = datetime.now(KST); today_str = now.strftime("%Y-%m-%d")
                if runtime_info.get("date") != today_str: runtime_info["date"] = today_str; runtime_info["count"] = 0
                RL.new_cid("sch", today_str, runtime_info.get("count", 0))
                # v4.1.0 관찰 전용: 빗썸 일봉 마감(09:00 KST) 후 하루 1회만 갱신.
                # 봇이 오전에 기동되어도 미마감 일봉을 쓰거나 당일 갱신을 놓치지 않는다.
                if now.hour >= 9:
                    for _coin in list(config.get("coins", {}).keys()):
                        if _coin in TREND_PERIOD and trend_signals.get(_coin, {}).get("date") != today_str:
                            try:
                                update_trend_signal(_coin)
                            except Exception as _te:
                                trend_signals[_coin] = {"signal": "unknown", "sma": None, "close": None,
                                                        "date": today_str, "reason": "update_failed"}
                                RL.err("trend_update", _te, reason="trend_update_failed")
                accs = {a["currency"]: a for a in get_accounts() if isinstance(a, dict) and "currency" in a}
                if "KRW" not in accs:
                    # 잔고 조회 실패 시 이번 회차는 매수·매도·익절단계 초기화를 모두 건너뜀 (가짜 잔액부족 알림·중복 익절 방지)
                    raise RuntimeError("빗썸 잔고 조회 실패 · 이번 회차 건너뜀")
                krw_bal = float(accs.get("KRW", {}).get("balance", 0))
                req_krw, _ = calc_today_required_krw(accs)
                if req_krw > 0 and krw_bal < req_krw and (time.time() - float(state.get("last_low_bal_ts", 0)) >= 1800):
                    state["last_low_bal_ts"] = time.time(); save_json(STATE_FILE, state)
                    RL.ev("decision", "low_krw_alert", "ok", None, actor="scheduler", audit_ref=RL.audit("low_krw", need=req_krw, have=krw_bal))
                    send_panel(f"⚠️ [빗썸 잔액 부족 ({BOT_VERSION})]\n• 필요: {req_krw:,.0f}원 / 보유: {krw_bal:,.0f}원", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                tp1, sr = float(config.get("target_profit_pct", 10.0)), float(config.get("sell_ratio_pct", 20.0))
                for coin, base_amt in list(config.get("coins", {}).items()):
                    if base_amt <= 0 and coin_method(coin) != 2: continue
                    t = get_ticker(coin)
                    if not t: _decide(coin, "coin_step", "skipped", "ticker_unavailable"); continue
                    cur_p = float(t["trade_price"]); acc = accs.get(coin, {})
                    bal, avg_p = float(acc.get("balance", 0)), float(acc.get("avg_buy_price", 0))
                    prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and bal > 0 else 0.0
                    if coin_method(coin) == 2:
                        if now.hour >= 9:
                            krw_bal = method2_daily_step(coin, krw_bal, acc, today_str)
                        else:
                            _decide(coin, "method2", "skipped", "before_candle_close", daily=True)
                        continue  # Never execute method 1 rules for a method 2 coin.
                    if prof_pct < tp1 and state["sold_stage"].get(coin, 0) != 0: state["sold_stage"][coin] = 0; save_json(STATE_FILE, state)
                    sold_stg = int(state["sold_stage"].get(coin, 0))
                    target_stg = 1 if (tp1 <= prof_pct < tp1*2 and sold_stg < 1) else (2 if (tp1*2 <= prof_pct < tp1*3 and sold_stg < 2) else 0)
                    if bal > 0 and avg_p > 0 and target_stg > 0:
                        sell_vol = round(bal * (sr / 100.0), 8)
                        if sell_vol * cur_p < 5000: _decide(coin, "take_profit", "skipped", "below_min_order", daily=True, stage=target_stg)
                        if sell_vol * cur_p >= 5000:
                            _decide(coin, "take_profit", "ok", None, _snap(coin, cur_price=cur_p, avg_price=avg_p, balance=bal, profit_pct=prof_pct, sell_volume=sell_vol), stage=target_stg)
                            ok, sell_res = place_order(coin, "ask", sell_vol, "market")
                            if not ok and isinstance(sell_res, str):
                                # 통신 오류(응답 없음)는 체결됐을 수 있으므로 같은 단계를 다시 매도하지 않음
                                state["sold_stage"][coin] = target_stg; state["last_action_date"][coin] = today_str; state["last_action_type"][coin] = "확인필요"
                                save_json(STATE_FILE, state); add_history(coin, f"⚠️{target_stg}차익절 응답없음", sell_res[:60])
                                send_panel(f"⚠️ [{coin} {target_stg}차 익절 주문 응답 없음]\n• 체결됐을 수 있어 다시 주문하지 않습니다.\n• 빗썸 앱에서 체결 여부를 확인해 주세요.\n• 사유: {sell_res[:120]}", [[{"text": "💰 상황판", "callback_data": "balance"}]]); continue
                            if ok:
                                state["sold_stage"][coin] = target_stg; state["last_action_date"][coin] = today_str; state["last_action_type"][coin] = f"{target_stg}차익절"
                                save_json(STATE_FILE, state); add_history(coin, f"🎯{target_stg}차익절", f"{prof_pct:+.2f}% ({sr:.0f}% 매도)")
                                send_panel(f"🎉 [{coin} {target_stg}차 익절 완료] {prof_pct:+.2f}%", [[{"text": "💰 상황판", "callback_data": "balance"}]]); continue
                    if state["last_action_date"].get(coin) == today_str: _decide(coin, "buy", "skipped", "done_today", daily=True)
                    elif now.hour < config.get("buy_hour", 19): _decide(coin, "buy", "skipped", "before_buy_hour", daily=True, buy_hour=config.get("buy_hour", 19))
                    if state["last_action_date"].get(coin) != today_str and now.hour >= config.get("buy_hour", 19):
                        buy_amt = max(5000, base_amt if (avg_p == 0 or bal == 0) else (int(base_amt / 2) if prof_pct >= 1.0 else base_amt))
                        if krw_bal >= buy_amt:
                            _decide(coin, "buy", "ok", None, _snap(coin, cur_price=cur_p, avg_price=avg_p, balance=bal, profit_pct=prof_pct, buy_krw=buy_amt, krw_balance=krw_bal), half=buy_amt < base_amt)
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
                                RL.ev("state_change", "buy_day", "ok", None, actor="scheduler", coin_ref=RL.ref(coin), day_after=state["buy_days"][coin], cycle_day_after=s_days[coin])
                                send_panel(f"✅ [{coin} 19:00 정기매수 완료 ({state['buy_days'][coin]}일차)] {buy_amt:,.0f}원 ({prof_pct:+.2f}%)", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                            elif isinstance(res_json, str):
                                # 통신 오류(응답 없음)는 체결됐을 수 있으므로 오늘은 다시 매수하지 않음 (중복 매수 방지)
                                state["last_action_date"][coin], state["last_action_type"][coin] = today_str, "확인필요"
                                save_json(STATE_FILE, state); add_history(coin, "⚠️정기매수 응답없음", f"{buy_amt:,.0f}원 · {res_json[:60]}")
                                RL.ev("state_change", "no_reorder_today", "ok", None, actor="scheduler", coin_ref=RL.ref(coin), why="order_no_response")
                                send_panel(f"⚠️ [{coin} 정기매수 주문 응답 없음] {buy_amt:,.0f}원\n• 체결됐을 수 있어 오늘은 다시 주문하지 않습니다.\n• 빗썸 앱에서 체결 여부를 확인해 주세요. (체결 안 됐으면 내일 정상 매수)\n• 사유: {res_json[:120]}", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                            else:
                                fk = f"fail_{today_str}_{coin}"
                                if not state.get(fk): state[fk] = True; save_json(STATE_FILE, state); send_panel(f"🚨 [{coin} 매수 실패] {res_json}", [[{"text": "💰 상황판", "callback_data": "balance"}]])
                        elif now.minute >= 15:
                            _decide(coin, "buy", "skipped", "krw_insufficient", _snap(coin, buy_krw=buy_amt, krw_balance=krw_bal) if RL.once(f"{coin}|krw_snap") else None, daily=True)
                            fk = f"fail_{today_str}_{coin}"
                            if not state.get(fk): state[fk] = True; save_json(STATE_FILE, state); send_panel(f"🚨 [{coin} 매수 미진행] 원화 부족", [[{"text": "💰 상황판", "callback_data": "balance"}]])
        except Exception as e: RL.err("scheduler_pass", e, event_type="decision", reason="accounts_unavailable" if "잔고 조회 실패" in str(e) else None)
        finally: RL.set_cid("")
        runtime_info["count"] += 1; time.sleep(60)

if __name__ == "__main__":
    RL.new_cid("svc", "start")
    RL.ev("state_change", "service_start", "ok", None, buy_hour_kst=config.get("buy_hour", 19), loop_sec=60, power=config.get("power", True))
    signal.signal(signal.SIGTERM, _on_stop)
    t, kb = build_control_view()
    send_panel(f"✨ [빗썸 봇 {BOT_VERSION} 모듈 분리 및 자동백업 완료!]\n\n" + t, kb)
    RL.set_cid("")
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    trading_monitor_loop()

# BOT_OFFICE_APPROVAL_CHECK_V1
