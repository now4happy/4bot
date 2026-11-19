import time, threading
from b_core import *
from b_ui import *

wait_state = {"mode": None}

# ---------------------------------------------------------------- v4.3.6 하단 키보드 [🪙 BTC 설정][🪙 ETH 설정] + 코인별 상황판·거래내역 (콜백은 항상 새 메시지)
# ---------------------------------------------------------------- v4.3.0 coin method-first UI and selection-is-approval
# ---------------------------------------------------------------- v4.2.0 SMA법 재작업 초안 (승인 전 주문 잠금)
# ---------------------------------------------------------------- v4.1.0 관찰 전용 추세 신호 (매매 동작은 그대로)
# 매일 09:00 KST 이후 코인별 첫 회차에만 갱신하고, 실패해도 매수·매도는 그대로 진행한다.
# ---------------------------------------------------------------- v4.0.4 재생 로그 도우미 (매매 동작은 그대로)
import os, signal

# --- alert-hub: 기존 전송은 그대로, 자율 알림만 hub DB에 복사 (실패해도 봇은 계속) ---
try:
    import sys as _hub_sys
    _HUB_ROOT = "/home/gieokkim/alert-hub"
    if _HUB_ROOT not in _hub_sys.path:
        _hub_sys.path.insert(0, _HUB_ROOT)
    from alert_hub.notify import heartbeat as _hub_heartbeat, notify as _hub_notify
except Exception:
    _hub_heartbeat = None
    _hub_notify = None

def _hub_beat(bot):
    try:
        if _hub_heartbeat:
            _hub_heartbeat(bot)
    except Exception:
        pass

def _hub_alert(bot, level, text):
    try:
        if _hub_notify:
            import re as _hub_re
            _hub_notify(bot, level, _hub_re.sub(r"<[^>]+>", "", str(text)))
    except Exception:
        pass

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

BOTTOM_COIN_BUTTONS = {"BTC 설정": "BTC", "ETH 설정": "ETH"}   # 하단 키보드 글자 → 코인 (v4.3.6)
MENU_WORDS = ["메뉴", "상황판", "잔고", "제어반", "취소", "전체 상황판", "도움말"] + list(BOTTOM_COIN_BUTTONS)

import re as _re
_EMOJI_RE = _re.compile("(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u25A0-\u25FF\u2300-\u23FF\u2900-\u297F\uFE0F\u200D])+ ?")
def _plain(t):
    """v4.4.0: 예전 하단 키보드(이모티콘 글자)가 폰에 남아 있어도 같은 버튼으로 읽도록 이모티콘만 뺀다."""
    return _EMOJI_RE.sub("", t or "").strip()

# v4.4.0: 값을 바꾸기 전 '지금 값 → 새 값' 확인 (60초). 주문은 안 나가고 설정 값만 바뀐다.
pending = {"apply": None, "ts": 0.0}
CONFIRM_SEC = 60
def ask_confirm(title, before, after, apply_fn):
    pending["apply"], pending["ts"] = apply_fn, time.time()
    send_panel(f"[{title}] 바꿀까요?\n지금 값 → 새 값\n{before} → {after}\n"
               f"{CONFIRM_SEC}초 안에 [변경 확인]을 눌러 주세요. 주문은 나가지 않고 설정 값만 바뀌어요.",
               [[{"text": "변경 확인", "callback_data": "cfm_yes"}, {"text": "취소", "callback_data": "cfm_no"}]])

def explain(name, now, rng, meaning, effect, example):
    """공통 설명 틀 (채팅 본문)"""
    return (f"[{name}]\n지금 값: {now}\n넣을 수 있는 값: {rng}\n무슨 뜻: {meaning}\n"
            f"바꾸면: {effect} (주문은 바로 나가지 않아요)\n새 값을 숫자로 보내 주세요. 예: {example}")

def pct_ok(x):
    return isfinite(x) and 0 < x <= 100   # Q1: 익절·매도비율 0 초과 100 이하

def handle_callback(cb):
    if str(cb.get("message", {}).get("chat", {}).get("id", "")) != str(CHAT_ID): RL.count("tg_other_chat"); return
    cb_id, data, seen_mid = cb["id"], cb.get("data", ""), cb.get("message", {}).get("message_id")
    RL.ev("user_event", "tg_button", "ok", None, actor="user", button=RL.button(data), seen_message_id=seen_mid)
    wait_state["mode"] = None; tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
    # v4.3.6: 예전 메시지 버튼도 메시지를 고치지 않고 같은 화면을 새 메시지로 보낸다
    if data.startswith(("method_coin_", "smart_settings_", "method_choose_", "coin_board_", "coin_history_")):
        wait_state["coin"] = data.rsplit("_", 1)[-1]
    if data == "balance": send_panel(*(build_balance_board()))
    elif data == "control": send_panel(*(build_main_view()))   # 옛 메시지의 control 버튼 호환 (v4.3.5)
    elif data == "main": send_panel(*(build_main_view()))
    elif data == "history": send_panel(f"[최근 거래내역 ({BOT_VERSION})]\n\n" + ("\n".join(history[-15:]) if history else "내역 없음"))
    elif data.startswith("coin_board_"):
        coin = data.removeprefix("coin_board_")
        send_panel(*(build_coin_board(coin) if coin in TREND_PERIOD and coin in config.get("coins", {}) else build_main_view()))
    elif data.startswith("coin_history_"):
        coin = data.removeprefix("coin_history_")
        send_panel(*(build_coin_history(coin) if coin in TREND_PERIOD and coin in config.get("coins", {}) else build_main_view()))
    elif data == "toggle_power":
        config["power"] = not config.get("power", True); save_json(CONFIG_FILE, config)
        RL.ev("state_change", "master_power", "ok", None, actor="user", before=not config["power"], after=config["power"])
        send_panel(*(build_smart_settings(wait_state.get("coin")) if wait_state.get("coin") in TREND_PERIOD else build_main_view()))
    elif data == "cfm_yes":
        fn = pending.get("apply"); pending["apply"] = None
        if fn and time.time() - pending.get("ts", 0) <= CONFIRM_SEC: fn()
        else: send_panel("확인 시간이 지났거나 바꿀 값이 없어요. 처음부터 다시 눌러 주세요.", [[{"text": "처음 화면", "callback_data": "main"}]])
    elif data == "cfm_no":
        pending["apply"] = None; send_panel("취소했어요. 값은 그대로예요.", [[{"text": "처음 화면", "callback_data": "main"}]])
    elif data.startswith("method_coin_"):
        coin = data.removeprefix("method_coin_")
        send_panel(*(build_coin_method_choice(coin)))
    elif data.startswith("smart_settings_"):
        coin = data.removeprefix("smart_settings_")
        send_panel(*(build_smart_settings(coin)))
    elif data.startswith("method_choose_"):
        coin = data.removeprefix("method_choose_")
        send_panel(*(build_coin_method_choice(coin)))
    elif data.startswith("method_set_"):
        parts = data.split("_")
        if len(parts) == 4 and parts[2] in TREND_PERIOD and parts[2] in config.get("coins", {}) and parts[3] in ("1", "2"):
            coin, method = parts[2], int(parts[3])
            if coin_method(coin) == method:
                send_panel(*(build_coin_sma_view(coin)))
                return
            config.setdefault("coin_methods", {})[coin] = method
            # Preserve prior processed signal when the same method is reselected.
            # Switching methods must not create retrospective crossover orders.
            state.setdefault("method2_last_processed", {}).pop(coin, None)
            state.setdefault("method2_selected_on", {}).pop(coin, None)
            save_json(CONFIG_FILE, config); save_json(STATE_FILE, state)
            RL.ev("state_change", "coin_method", "ok", None, actor="user", coin_ref=RL.ref(coin), method=method)
            send_panel(*(build_coin_sma_view(coin)))
    elif data.startswith("method_buy_"):
        coin = data.removeprefix("method_buy_")
        if coin in TREND_PERIOD and coin in config.get("coins", {}):
            wait_state["mode"] = "set_sma_buy"; wait_state["coin"] = coin
            send_panel(explain(f"{coin} SMA 매수금액", (f"{sma_buy_amount(coin):,.0f}원" if sma_buy_amount(coin) is not None else "미설정"),
                               "5,000원 이상 정수 (원, 상한 없음)", "SMA 신호로 살 때 1회에 쓰는 금액이에요. 시드와는 따로예요.",
                               "다음 SMA 매수 신호부터 이 금액으로 사요", "100000"),
                       [[{"text":"메인", "callback_data":"main"}]])
    elif data.startswith("method_ratio_"):
        coin = data.removeprefix("method_ratio_")
        if coin in TREND_PERIOD and coin in config.get("coins", {}):
            wait_state["mode"] = "set_method2_ratio"; wait_state["coin"] = coin
            send_panel(explain(f"{coin} SMA 매도비율", (f"{method2_ratio(coin):g}%" if method2_ratio(coin) is not None else "미설정"),
                               "0 초과 100 이하 (%)", "SMA 매도 신호가 올 때 가진 수량 중 파는 비율이에요.",
                               "다음 SMA 매도 신호부터 이 비율로 팔아요", "50"), [[{"text":"메인", "callback_data":"main"}]])
    elif data == "ask_buy": wait_state["mode"] = "setbuy"; send_panel(explain("코인 시드 설정", ", ".join(f"{c} {a:,.0f}원" for c, a in config.get("coins", {}).items()) or "없음",
                              "코인 이름과 정수 금액 (원). 0 이하는 그 코인 삭제. 상한 없음", "시드는 스마트 적립이 매일 사는 기준 금액이에요.",
                              "다음 정기매수부터 이 금액이 기준이 돼요. 0을 넣으면 그 코인 적립을 지워요", "BTC 20000  (삭제: BTC 0)"), [[{"text": "스마트 적립", "callback_data": f"smart_settings_{wait_state.get('coin', 'BTC')}"}]])
    elif data == "ask_day": wait_state["mode"] = "setday"; send_panel(explain("코인 매수일수 보정(진행일수 보정)", ", ".join(f"{c} {int(state.get('buy_days', {}).get(c, 0))}일차" for c in config.get("coins", {})) or "없음",
                              "코인 이름과 0 이상 정수 (일, 음수는 0, 상한 없음)", "지금까지 실제로 산 날 수를 맞춰 적어요.",
                              "상황판의 진행 일수가 바뀌어요", "BTC 5  또는  ETH 6"), [[{"text": "스마트 적립", "callback_data": f"smart_settings_{wait_state.get('coin', 'BTC')}"}]])
    elif data == "ask_custom": wait_state["mode"] = "setcustom"; send_panel(explain("익절 % · 매도비율 % (BTC·ETH 공통)", f"익절 {float(config.get('target_profit_pct', 10.0)):g}% / 매도 {float(config.get('sell_ratio_pct', 20.0)):g}%",
                              "두 숫자 모두 0 초과 100 이하 (%). 숫자 1개만 보내면 익절 %만 바뀌어요", "익절은 이익이 이 %에 닿으면 파는 기준(2차는 2배)이고, 매도비율은 그때 파는 분할매도 비율이에요.",
                              "다음 익절 판단부터 새 기준을 써요", "10 20"), [[{"text": "스마트 적립", "callback_data": f"smart_settings_{wait_state.get('coin', 'BTC')}"}]])

def handle_message(msg):
    if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID): return
    text = _plain(msg.get("text", ""))
    if not text: return
    RL.ev("user_event", "tg_message", "ok", None, actor="user", text_len=len(text),
          input_kind="command" if text.startswith("/") else ("menu_word" if text in MENU_WORDS else (wait_state.get("mode") or "other")))
    if text.startswith("/") or text in MENU_WORDS:
        wait_state["mode"] = None   # 숫자 입력 대기 중 하단 버튼이 와도 대기를 풀고 해당 화면으로 (v4.3.6)
        if text in BOTTOM_COIN_BUTTONS:
            wait_state["coin"] = BOTTOM_COIN_BUTTONS[text]
            send_panel(*(build_coin_method_choice(BOTTOM_COIN_BUTTONS[text])))
        elif text in ["/balance", "상황판", "전체 상황판", "잔고"]: send_panel(*(build_balance_board()))
        elif text in ["도움말", "/help"]: send_panel(HELP_TEXT, None)
        elif text in ["/control", "제어반"]: send_panel(*(build_main_view()))   # 옛 습관 입력 호환 (v4.3.5)
        else: send_panel(*(build_main_view()))
        return
    if wait_state["mode"] == "set_sma_buy":
        coin = wait_state.get("coin")
        try:
            amount = int(text.replace(",", "").replace("원", "").strip())
            if coin not in TREND_PERIOD or coin not in config.get("coins", {}) or amount < 5000:
                raise ValueError("invalid SMA amount")
            wait_state["mode"] = None
            def _apply(coin=coin, amount=amount):
                config.setdefault("sma_buy_amounts", {})[coin] = amount
                save_json(CONFIG_FILE, config)
                RL.ev("state_change", "sma_buy_amount", "ok", None, actor="user",
                      coin_ref=RL.ref(coin), audit_ref=RL.audit("sma_buy_amount", coin=coin, amount=amount))
                send_panel(*(build_coin_sma_view(coin)))
            _old = sma_buy_amount(coin)
            ask_confirm(f"{coin} SMA 매수금액", (f"{_old:,.0f}원" if _old is not None else "미설정"), f"{amount:,.0f}원", _apply)
        except (ValueError, TypeError):
            send_panel("SMA 매수금액은 5,000원 이상의 정수로 입력하세요. (상한 없음)",
                       [[{"text":"메인", "callback_data":"main"}]])
        return
    if wait_state["mode"] == "set_method2_ratio":
        coin = wait_state.get("coin")
        try:
            ratio = float(text.replace("%", "").strip())
            if coin not in TREND_PERIOD or coin not in config.get("coins", {}) or not (float("-inf") < ratio < float("inf") and 0 < ratio <= 100):
                raise ValueError("invalid ratio")
            wait_state["mode"] = None
            def _apply(coin=coin, ratio=ratio):
                config.setdefault("method2_sell_ratios", {})[coin] = ratio
                save_json(CONFIG_FILE, config)
                RL.ev("state_change", "method2_ratio", "ok", None, actor="user", coin_ref=RL.ref(coin), audit_ref=RL.audit("method2_ratio", coin=coin, ratio=ratio))
                send_panel(*(build_coin_sma_view(coin)))
            _old = method2_ratio(coin)
            ask_confirm(f"{coin} SMA 매도비율", (f"{_old:g}%" if _old is not None else "미설정"), f"{ratio:g}%", _apply)
        except (ValueError, TypeError):
            send_panel("0 초과 100 이하의 숫자를 입력하세요. (%)", [[{"text":"메인", "callback_data":"main"}]])
        return
    if wait_state["mode"] == "setday":
        parts = text.split()
        try:
            coin = parts[0].upper(); d = max(0, int(parts[1].replace("일", "").replace("차", "")))
            if coin not in config.get("coins", {}): raise ValueError("coin")
            wait_state["mode"] = None
            def _apply(coin=coin, d=d):
                RL.ev("state_change", "buy_day_manual", "ok", None, actor="user", coin_ref=RL.ref(coin), day_before=state.get("buy_days", {}).get(coin), day_after=d)
                state.setdefault("buy_days", {})[coin] = d; save_json(STATE_FILE, state)
                send_panel(*(build_smart_settings(coin)) if coin in TREND_PERIOD else build_main_view())
            ask_confirm(f"{coin} 매수일수 보정", f"{int(state.get('buy_days', {}).get(coin, 0))}일차", f"{d}일차", _apply)
        except: RL.ev("user_event", "bad_input", "failed", "bad_format", actor="user", wait_mode="setday"); send_panel("코인 이름과 0 이상 정수를 띄어 써 주세요. 예: BTC 5", [[{"text": "메인", "callback_data": "main"}]])
        return
    if wait_state["mode"] == "setbuy":
        parts = text.split()
        try:
            coin = "BTC" if len(parts) == 1 else parts[0].upper()
            amt = int((parts[0] if len(parts) == 1 else parts[1]).replace(",", "").replace("원", ""))
            wait_state["mode"] = None
            def _apply(coin=coin, amt=amt):
                aref = RL.audit("coin_seed_change", coin=coin, before=config["coins"].get(coin), after=amt)
                if amt <= 0: config["coins"].pop(coin, None)
                else: config["coins"][coin] = amt
                save_json(CONFIG_FILE, config)
                RL.ev("state_change", "coin_seed", "ok", None, actor="user", coin_ref=RL.ref(coin), removed=amt <= 0, audit_ref=aref)
                send_panel(*(build_smart_settings(coin)) if coin in TREND_PERIOD else build_main_view())
            _old = config["coins"].get(coin)
            ask_confirm(f"{coin} 시드", (f"{_old:,.0f}원" if _old else "없음"), ("삭제" if amt <= 0 else f"{amt:,.0f}원"), _apply)
        except: RL.ev("user_event", "bad_input", "failed", "bad_format", actor="user", wait_mode="setbuy"); send_panel("코인 이름과 정수 금액(원)을 띄어 써 주세요. 0 이하는 삭제예요. 예: BTC 20000", [[{"text": "메인", "callback_data": "main"}]])
        return
    elif wait_state["mode"] == "setcustom":
        parts = text.split()
        try:
            before = [config.get("target_profit_pct"), config.get("sell_ratio_pct")]
            new_tp = float(parts[0]); new_sr = float(parts[1]) if len(parts) >= 2 else float(config.get("sell_ratio_pct", 20.0))
            if len(parts) > 2 or not pct_ok(new_tp) or not pct_ok(new_sr): raise ValueError("range")   # Q1: 0 초과 100 이하
            wait_state["mode"] = None
            def _apply(new_tp=new_tp, new_sr=new_sr, before=before):
                config["target_profit_pct"], config["sell_ratio_pct"] = new_tp, new_sr
                save_json(CONFIG_FILE, config)
                RL.ev("state_change", "take_profit_rule", "ok", None, actor="user", before=before, after=[new_tp, new_sr])
                send_panel(*(build_main_view()))
            ask_confirm("익절 % · 매도비율 %", f"익절 {float(before[0] or 10.0):g}% / 매도 {float(before[1] or 20.0):g}%", f"익절 {new_tp:g}% / 매도 {new_sr:g}%", _apply)
        except: RL.ev("user_event", "bad_input", "failed", "bad_format", actor="user", wait_mode="setcustom"); send_panel("두 숫자 모두 0 초과 100 이하(%)로 띄어 써 주세요. 예: 10 20", [[{"text": "메인", "callback_data": "main"}]])
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
        send_panel(f"{coin} SMA법 {('매수' if direction == 'up' else '매도')} 접수"); _hub_alert("3번 빗썸 적립", "info", f"{coin} SMA법 {('매수' if direction == 'up' else '매도')} 접수")
        if direction == "up":
            krw_bal -= size
    else:
        _decide(coin, "method2_order", "failed", "order_failed_or_unknown", daily=True)
        send_panel(f"{coin} SMA법 주문 결과 확인 필요. 재주문하지 않습니다."); _hub_alert("3번 빗썸 적립", "critical", f"{coin} SMA법 주문 결과 확인 필요. 재주문하지 않습니다.")
    return krw_bal

def trading_monitor_loop():
    while True:
        RL.count("scheduler_tick"); RL.tick()
        _hub_beat('3번 빗썸 적립')
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
                    send_panel(f"[빗썸 잔액 부족 ({BOT_VERSION})]\n• 필요: {req_krw:,.0f}원 / 보유: {krw_bal:,.0f}원"); _hub_alert("3번 빗썸 적립", "critical", f"빗썸 잔액 부족: 필요 {req_krw:,.0f}원 / 보유 {krw_bal:,.0f}원")
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
                                save_json(STATE_FILE, state); add_history(coin, f"{target_stg}차익절 응답없음", sell_res[:60])
                                send_panel(f"[{coin} {target_stg}차 익절 주문 응답 없음]\n• 체결됐을 수 있어 다시 주문하지 않습니다.\n• 빗썸 앱에서 체결 여부를 확인해 주세요.\n• 사유: {sell_res[:120]}"); _hub_alert("3번 빗썸 적립", "critical", f"{coin} {target_stg}차 익절 주문 응답 없음"); continue
                            if ok:
                                state["sold_stage"][coin] = target_stg; state["last_action_date"][coin] = today_str; state["last_action_type"][coin] = f"{target_stg}차익절"
                                save_json(STATE_FILE, state); add_history(coin, f"{target_stg}차익절", f"{prof_pct:+.2f}% ({sr:.0f}% 매도)")
                                send_panel(f"[{coin} {target_stg}차 익절 완료] {prof_pct:+.2f}%"); _hub_alert("3번 빗썸 적립", "info", f"{coin} {target_stg}차 익절 완료 {prof_pct:+.2f}%"); continue
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
                                save_json(STATE_FILE, state); add_history(coin, "정기매수", f"{buy_amt:,.0f}원 ({prof_pct:+.2f}%)")
                                RL.ev("state_change", "buy_day", "ok", None, actor="scheduler", coin_ref=RL.ref(coin), day_after=state["buy_days"][coin], cycle_day_after=s_days[coin])
                                send_panel(f"[{coin} 19:00 정기매수 완료 ({state['buy_days'][coin]}일차)] {buy_amt:,.0f}원 ({prof_pct:+.2f}%)"); _hub_alert("3번 빗썸 적립", "info", f"{coin} 19:00 정기매수 완료 {buy_amt:,.0f}원 ({prof_pct:+.2f}%)")
                            elif isinstance(res_json, str):
                                # 통신 오류(응답 없음)는 체결됐을 수 있으므로 오늘은 다시 매수하지 않음 (중복 매수 방지)
                                state["last_action_date"][coin], state["last_action_type"][coin] = today_str, "확인필요"
                                save_json(STATE_FILE, state); add_history(coin, "정기매수 응답없음", f"{buy_amt:,.0f}원 · {res_json[:60]}")
                                RL.ev("state_change", "no_reorder_today", "ok", None, actor="scheduler", coin_ref=RL.ref(coin), why="order_no_response")
                                send_panel(f"[{coin} 정기매수 주문 응답 없음] {buy_amt:,.0f}원\n• 체결됐을 수 있어 오늘은 다시 주문하지 않습니다.\n• 빗썸 앱에서 체결 여부를 확인해 주세요. (체결 안 됐으면 내일 정상 매수)\n• 사유: {res_json[:120]}"); _hub_alert("3번 빗썸 적립", "critical", f"{coin} 정기매수 주문 응답 없음 {buy_amt:,.0f}원")
                            else:
                                fk = f"fail_{today_str}_{coin}"
                                if not state.get(fk): state[fk] = True; save_json(STATE_FILE, state); send_panel(f"[{coin} 매수 실패] {res_json}"); _hub_alert("3번 빗썸 적립", "critical", f"{coin} 매수 실패")
                        elif now.minute >= 15:
                            _decide(coin, "buy", "skipped", "krw_insufficient", _snap(coin, buy_krw=buy_amt, krw_balance=krw_bal) if RL.once(f"{coin}|krw_snap") else None, daily=True)
                            fk = f"fail_{today_str}_{coin}"
                            if not state.get(fk): state[fk] = True; save_json(STATE_FILE, state); send_panel(f"[{coin} 매수 미진행] 원화 부족"); _hub_alert("3번 빗썸 적립", "critical", f"{coin} 매수 미진행 원화 부족")
        except Exception as e: RL.err("scheduler_pass", e, event_type="decision", reason="accounts_unavailable" if "잔고 조회 실패" in str(e) else None)
        finally: RL.set_cid("")
        runtime_info["count"] += 1; time.sleep(60)

if __name__ == "__main__":
    RL.new_cid("svc", "start")
    RL.ev("state_change", "service_start", "ok", None, buy_hour_kst=config.get("buy_hour", 19), loop_sec=60, power=config.get("power", True))
    signal.signal(signal.SIGTERM, _on_stop)
    t, kb = build_main_view()
    send_panel(f"[빗썸 봇 {BOT_VERSION} 모듈 분리 및 자동백업 완료!]\n\n" + t, kb)
    RL.set_cid("")
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    trading_monitor_loop()

# BOT_OFFICE_APPROVAL_CHECK_V1
