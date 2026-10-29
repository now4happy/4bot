from datetime import datetime
from b_core import *

# v4.3.1: 자산 상황판의 코드 블록 제거 — 텔레그램 기본 글씨 크기 사용

# v4.2.0 (draft): unified SMA법 with independent amount, ratio, and approval lock.
# v4.1.0 (2026-10-29): 상황판에 관찰 전용 추세 신호 한 줄 추가 — 매수·매도 동작 변경 없음.

# 버전 기록은 봇 폴더의 CHANGELOG.md 로 통합 (사무실 업데이트 때 자동으로 쌓임)

def calc_today_required_krw(accs):
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    total_req, details = 0, []
    for coin, base_amt in config.get("coins", {}).items():
        if base_amt <= 0 or coin_method(coin) == 2 or state["last_action_date"].get(coin) == today_str: continue
        t = get_ticker(coin); cur_p = float(t["trade_price"]) if t else 0
        acc = accs.get(coin, {}); bal, avg_p = float(acc.get("balance", 0)), float(acc.get("avg_buy_price", 0))
        prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
        req = max(5000, base_amt if (avg_p == 0 or bal == 0 or cur_p == 0) else (int(base_amt / 2) if prof_pct >= 1.0 else base_amt))
        total_req += req; details.append(f"{coin}({req:,.0f}원)")
    return total_req, details

def build_balance_board():
    """Compact fixed-width board. No account changes, only presentation."""
    accs = {a["currency"]: a for a in get_accounts() if isinstance(a, dict) and "currency" in a}
    krw_bal = float(accs.get("KRW", {}).get("balance", 0))
    req_krw, _ = calc_today_required_krw(accs)
    shortfall = max(0, req_krw - krw_bal)
    total_eval = krw_bal
    rows = []
    for cur in ("BTC", "ETH"):
        if cur not in config.get("coins", {}):
            continue
        a = accs.get(cur, {})
        bal = float(a.get("balance", 0)) + float(a.get("locked", 0))
        avg_p = float(a.get("avg_buy_price", 0))
        t = get_ticker(cur)
        cur_p = float(t["trade_price"]) if t else avg_p
        eval_krw = bal * cur_p
        total_eval += eval_krw
        prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 else 0.0
        base_amt = float(config.get("coins", {}).get(cur, 10000))
        if state.get("buy_days", {}).get(cur, 0) == 0 and bal > 0 and avg_p > 0 and base_amt > 0:
            state.setdefault("buy_days", {})[cur] = max(1, int(round((bal * avg_p) / base_amt)))
            save_json(STATE_FILE, state)
        if coin_method(cur) == 2:
            method = f"SMA{TREND_PERIOD[cur]}"
            status = "매매가능" if method2_ready(cur) else "설정필요·주문잠금"
        else:
            method = "스마트적립"
            status = f"{int(state.get('buy_days', {}).get(cur, 0))}일차"
        rows.append((cur, method, status, bal, eval_krw, prof_pct, avg_p, cur_p))
    # Monospace code blocks use a smaller font on mobile.
    # Plain text restores the user's normal Telegram chat font size.
    lines = [
        f"💰 빗썸 자산 상황판  {BOT_VERSION}",
        f"💵 현금: {krw_bal:,.0f}원",
        f"🛒 오늘 필요: {req_krw:,.0f}원",
        f"💳 잔액: {'부족 ' + format(shortfall, ',.0f') + '원' if shortfall else '충분'}",
        f"🔌 전체 전원: {'ON' if config.get('power', True) else 'OFF'}",
    ]
    for cur, method, status, bal, ev, profit, avg, current in rows:
        lines.extend([
            "──────────────",
            f"🪙 {cur} · {method} · {status}",
            f"수량: {bal:.6f}",
            f"평가액: {ev:,.0f}원",
            f"수익률: {profit:+.2f}%",
            f"평단가: {avg:,.0f}원",
            f"현재가: {current:,.0f}원",
        ])
    if not rows:
        lines.append("설정된 BTC/ETH가 없습니다")
    lines.extend([
        "──────────────",
        f"🏦 총 추정자산: {total_eval:,.0f}원",
        f"📈 완성 일봉 추세: {trend_line()}",
        f"⏱ {datetime.now(KST).strftime('%H:%M:%S')} 기준",
    ])
    kb = [[{"text": "🔄 새로고침", "callback_data": "balance"}, {"text": "⚙️ 제어반", "callback_data": "control"}],
          [{"text": "📝 거래내역", "callback_data": "history"}, {"text": "🔙 메인", "callback_data": "main"}]]
    return "\n".join(lines), kb

def get_bithumb_schedule_status() -> str:
    now = datetime.now(KST)
    today_str = now.strftime("%Y-%m-%d")
    buy_h = int(config.get("buy_hour", 19))
    coins = [c for c, amt in config.get("coins", {}).items() if amt > 0 and coin_method(c) == 1]
    all_done = all(state.get("last_action_date", {}).get(c) == today_str for c in coins) if coins else True
    if all_done:
        return f"💤 금일 정기매수 종료 (절전 대기 | 내일 {buy_h:02d}:00 시작)"
    if now.hour < buy_h:
        return f"⏳ 대기 중 (오늘 {buy_h:02d}:00 정기매수 시작)"
    return f"🟢 금일 {buy_h:02d}:00 정기매수 진행/점검 중"


def build_coin_sma_view(coin):
    if coin not in TREND_PERIOD or coin not in config.get("coins", {}):
        return "❌ 등록된 BTC·ETH만 설정할 수 있습니다.", [[{"text":"🔙 제어반", "callback_data":"control"}]]
    method = coin_method(coin)
    if method == 1:
        return build_smart_settings(coin)
    amount = sma_buy_amount(coin)
    ratio = method2_ratio(coin)
    ready = method2_ready(coin)
    text = (f"🪙 {coin} | SMA{TREND_PERIOD[coin]} 매매 설정\n\n"
            f"상태: {'🟢 자동주문 가능' if ready else '🔒 설정 부족 · 주문 잠금'}\n"
            f"매수금액: {f'{amount:,.0f}원' if amount is not None else '미설정'}\n"
            f"매도비율: {f'{ratio:g}%' if ratio is not None else '미설정'}\n\n"
            "SMA법 선택 = 승인입니다.\n"
            "금액·비율이 모두 유효하면 별도 승인 없이 다음 신호부터 주문 가능합니다.\n"
            "SMA법 선택 중에는 기존 정기매수·분할익절이 중단됩니다.")
    kb = [
        [{"text":"📊 매매법 변경", "callback_data":f"method_choose_{coin}"}],
        [{"text":"💵 SMA 매수금액", "callback_data":f"method_buy_{coin}"}],
        [{"text":"📉 SMA 매도비율", "callback_data":f"method_ratio_{coin}"}],
        [{"text":"🔙 제어반", "callback_data":"control"}],
    ]
    return text, kb


def build_smart_settings(coin):
    if coin not in TREND_PERIOD or coin not in config.get("coins", {}):
        return "❌ 코인 설정을 확인하세요.", [[{"text":"🔙 제어반", "callback_data":"control"}]]
    pwr = config.get("power", True)
    tp = float(config.get("target_profit_pct", 10.0))
    sr = float(config.get("sell_ratio_pct", 20.0))
    text = (f"🪙 {coin} | 1번 스마트 적립\n\n"
            f"시드: {config['coins'][coin]:,.0f}원\n"
            f"진행: {state.get('buy_days', {}).get(coin, 0)}일차\n"
            f"익절: {tp:g}% / {tp*2:g}% → {sr:g}% 매도\n"
            f"전체 전원: {'🟢 ON' if pwr else '🔴 OFF'}\n\n"
            "⚠️ 전원·익절 규칙은 BTC/ETH 공통 설정입니다.\n"
            "전체 전원을 끄면 SMA법 주문도 중단됩니다.")
    kb = [
        [{"text":"📊 매매법 변경", "callback_data":f"method_choose_{coin}"}],
        [{"text":"🔴 전체 매매 정지" if pwr else "🟢 전체 매매 가동", "callback_data":"toggle_power"}],
        [{"text":("✅ " if tp==10 and sr==20 else "")+"10%·20% / 20% 매도", "callback_data":"prof_10_20"},
         {"text":("✅ " if tp==5 and sr==20 else "")+"5%·10% / 20% 매도", "callback_data":"prof_5_20"}],
        [{"text":"💵 코인 시드 설정", "callback_data":"ask_buy"}, {"text":"🔢 매수일수 보정", "callback_data":"ask_day"}],
        [{"text":"🎯 익절·매도비율 입력 (공통)", "callback_data":"ask_custom"}],
        [{"text":"🔙 제어반", "callback_data":"control"}],
    ]
    return text, kb


def build_coin_method_choice(coin):
    if coin not in TREND_PERIOD or coin not in config.get("coins", {}):
        return "❌ 등록된 BTC·ETH만 설정할 수 있습니다.", [[{"text":"🔙 제어반", "callback_data":"control"}]]
    current = coin_method(coin)
    return (f"🪙 {coin} 매매법 선택\n\n"
            "① 스마트 적립 — 기존 정기매수·분할익절\n"
            f"② SMA법 — SMA{TREND_PERIOD[coin]} 기준\n\n"
            "⚠️ SMA법 선택이 곧 승인입니다.\n"
            "금액·비율이 저장되어 있으면 즉시 주문 가능 상태가 됩니다.\n"
            "설정이 없으면 주문은 잠깁니다.",
            [[{"text":("✅ " if current==1 else "")+"1번 스마트 적립", "callback_data":f"method_set_{coin}_1"}],
             [{"text":("✅ " if current==2 else "")+f"SMA법 (SMA{TREND_PERIOD[coin]})", "callback_data":f"method_set_{coin}_2"}],
             [{"text":"🔙 제어반", "callback_data":"control"}]])


def build_control_view():
    text = (f"⚙️ 매매법 제어반 ({BOT_VERSION})\n\n"
            f"전체 전원: {'🟢 ON' if config.get('power', True) else '🔴 OFF'}\n"
            "BTC 또는 ETH를 선택해 매매법과 해당 설정을 관리하세요.\n"
            "SMA법은 선택 즉시 승인되며 금액·비율이 유효하면 자동주문이 가능합니다.")
    kb = [[{"text":"🪙 BTC 설정", "callback_data":"method_coin_BTC"},
           {"text":"🪙 ETH 설정", "callback_data":"method_coin_ETH"}],
          [{"text":"💰 자산 상황판", "callback_data":"balance"},
           {"text":"🔙 메인", "callback_data":"main"}]]
    return text, kb

def build_main_view():
    text = f"🤖 [빗썸 스마트 적립 모듈형 관제탑 ({BOT_VERSION})]\n\n• 매일 19:00 정기 매수 (+1.0%↑ 시 1/2배, 그 외 1배)\n• 10% / 20% 도달 시 잔고의 20% 분할매도 (30%↑ 미정)\n• ⚡ 스케줄 상태: {get_bithumb_schedule_status()}"
    kb = [[{"text": "💰 내 자산 상황판", "callback_data": "balance"}], [{"text": "⚙️ 전술 제어반", "callback_data": "control"}], [{"text": "📝 거래내역", "callback_data": "history"}]]
    return text, kb
