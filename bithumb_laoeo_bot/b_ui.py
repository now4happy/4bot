from datetime import datetime
from b_core import *

# 버전 기록은 봇 폴더의 CHANGELOG.md 로 통합 (사무실 업데이트 때 자동으로 쌓임)

def calc_today_required_krw(accs):
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    total_req, details = 0, []
    for coin, base_amt in config.get("coins", {}).items():
        if base_amt <= 0 or state["last_action_date"].get(coin) == today_str: continue
        t = get_ticker(coin); cur_p = float(t["trade_price"]) if t else 0
        acc = accs.get(coin, {}); bal, avg_p = float(acc.get("balance", 0)), float(acc.get("avg_buy_price", 0))
        prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
        req = max(5000, base_amt if (avg_p == 0 or bal == 0 or cur_p == 0) else (int(base_amt / 2) if prof_pct >= 1.0 else base_amt))
        total_req += req; details.append(f"{coin}({req:,.0f}원)")
    return total_req, details

def build_balance_board():
    accs = {a["currency"]: a for a in get_accounts() if isinstance(a, dict) and "currency" in a}
    krw_bal = float(accs.get("KRW", {}).get("balance", 0))
    req_krw, req_details = calc_today_required_krw(accs)
    shortfall = max(0, req_krw - krw_bal)
    lines = [
        f"💰 [빗썸 자산 상황판 ({BOT_VERSION})]", f"💵 보유 현금(KRW): {krw_bal:,.0f}원",
        f"🛒 금일 매수 필요액: {req_krw:,.0f}원 " + (f"({', '.join(req_details)})" if req_details else "(금일 완료)"),
        f"🚨 잔액 상태: " + (f"⚠️ {shortfall:,.0f}원 부족!" if shortfall > 0 else "✅ 잔액 충분"), "─────────────────", "📦 [보유 코인 현황]"
    ]
    total_eval, has_coin = krw_bal, False
    for cur in list(config.get("coins", {}).keys()):
        a = accs.get(cur, {}); bal = float(a.get("balance", 0)) + float(a.get("locked", 0))
        if bal <= 0: continue
        has_coin = True; avg_p = float(a.get("avg_buy_price", 0))
        t = get_ticker(cur); cur_p = float(t["trade_price"]) if t else avg_p
        eval_krw = bal * cur_p; total_eval += eval_krw
        prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 else 0.0
        base_amt = float(config.get("coins", {}).get(cur, 10000))
        if state.get("buy_days", {}).get(cur, 0) == 0 and bal > 0 and avg_p > 0 and base_amt > 0:
            state.setdefault("buy_days", {})[cur] = max(1, int(round((bal * avg_p) / base_amt)))
            save_json(STATE_FILE, state)
        b_days = int(state.get("buy_days", {}).get(cur, 0))
        lines.append(f"🪙 {cur} [{'1/2배 대상' if prof_pct >= 1.0 else '1배 대상'} | ⏳ {b_days}일차]\n • 수량: {bal:.6f} | 평가: {eval_krw:,.0f}원 ({prof_pct:+.2f}%)\n • 평단/현재: {avg_p:,.0f}원 / {cur_p:,.0f}원")
    if not has_coin: lines.append(" • 현재 보유 중인 코인이 없습니다.")
    lines.extend(["─────────────────", f"🏦 총 추정 자산: {total_eval:,.0f}원\n⏱ 갱신: {datetime.now(KST).strftime('%H:%M:%S')}"])
    kb = [[{"text": "🔄 새로고침", "callback_data": "balance"}, {"text": "⚙️ 전술 제어반", "callback_data": "control"}], [{"text": "📝 거래내역", "callback_data": "history"}, {"text": "🔙 메인 메뉴", "callback_data": "main"}]]
    return "\n".join(lines), kb

def get_bithumb_schedule_status() -> str:
    now = datetime.now(KST)
    today_str = now.strftime("%Y-%m-%d")
    buy_h = int(config.get("buy_hour", 19))
    coins = [c for c, amt in config.get("coins", {}).items() if amt > 0]
    all_done = all(state.get("last_action_date", {}).get(c) == today_str for c in coins) if coins else True
    if all_done:
        return f"💤 금일 정기매수 종료 (절전 대기 | 내일 {buy_h:02d}:00 시작)"
    if now.hour < buy_h:
        return f"⏳ 대기 중 (오늘 {buy_h:02d}:00 정기매수 시작)"
    return f"🟢 금일 {buy_h:02d}:00 정기매수 진행/점검 중"

def build_control_view():
    pwr_On = config.get("power", True)
    coins_str = ", ".join([f"{k}: {v:,}원({state.get('buy_days', {}).get(k, 0)}일차)" for k, v in config.get("coins", {}).items()]) or "없음"
    tp1, sr = float(config.get("target_profit_pct", 10.0)), float(config.get("sell_ratio_pct", 20.0))
    text = (
        f"⚙️ [스마트 적립 전술 제어반 ({BOT_VERSION})]\n"
        f"▫️ 마스터 전원: {'🟢 ON (가동 중)' if pwr_On else '🔴 OFF (일시정지)'}\n▫️ 현재 기준시드: {coins_str}\n"
        f"▫️ 정기 매수시각: 매일 오후 {config.get('buy_hour', 19)}:00 KST\n▫️ 매수 배율규칙: 수익률 +1.0% 이상 시 1/2배 (그 외 1배)\n─────────────────\n"
        f"📊 [수익률 구간별 매도 계획]\n • {tp1:.0f}% 수익 도달 시 ➔ 잔고의 {sr:.0f}% 매도\n • {tp1*2:.0f}% 수익 도달 시 ➔ 잔고의 {sr:.0f}% 매도\n • {tp1*3:.0f}% 이상 수익 도달 시 ➔ 미정 (매도 없음)\n⏱ 조회: {datetime.now(KST).strftime('%H:%M:%S')}"
    )
    kb = [
        [{"text": "🔴 스마트 적립 정지" if pwr_On else "🟢 스마트 적립 가동", "callback_data": "toggle_power"}],
        [{"text": ("✅ " if tp1==10.0 and sr==20.0 else "") + "🎯 10%·20% (잔고 20%매도)", "callback_data": "prof_10_20"}, {"text": ("✅ " if tp1==5.0 and sr==20.0 else "") + "🎯 5%·10% (잔고 20%매도)", "callback_data": "prof_5_20"}],
        [{"text": "💵 코인 시드 설정", "callback_data": "ask_buy"}, {"text": "🔢 코인 일수 보정", "callback_data": "ask_day"}],
        [{"text": "🎯 익절/매도비율 직접입력", "callback_data": "ask_custom"}],
        [{"text": "💰 내 자산 상황판", "callback_data": "balance"}, {"text": "🔙 메인 메뉴", "callback_data": "main"}]
    ]
    return text, kb

def build_main_view():
    text = f"🤖 [빗썸 스마트 적립 모듈형 관제탑 ({BOT_VERSION})]\n\n• 매일 19:00 정기 매수 (+1.0%↑ 시 1/2배, 그 외 1배)\n• 10% / 20% 도달 시 잔고의 20% 분할매도 (30%↑ 미정)\n• ⚡ 스케줄 상태: {get_bithumb_schedule_status()}"
    kb = [[{"text": "💰 내 자산 상황판", "callback_data": "balance"}], [{"text": "⚙️ 전술 제어반", "callback_data": "control"}], [{"text": "📝 거래내역", "callback_data": "history"}]]
    return text, kb
