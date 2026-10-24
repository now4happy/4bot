from t_core import *

# 버전 기록은 봇 폴더의 CHANGELOG.md 로 통합 (사무실 업데이트 때 자동으로 쌓임)
# 환전 필요액 계산은 사무실 비서 브리핑(07:00 · 19:00 KST)이 대신함

def ensure_stock_cycle(s: dict, is_kr: bool):
    if "s_mode" not in s: s["s_mode"] = "buy_1"
    if "s_day" not in s: s["s_day"] = 0
    if "s_target_days" not in s: s["s_target_days"] = 100
    if "base_amount" not in s: s["base_amount"] = 100000.0 if is_kr else 40.0
    if s["s_mode"] == "decision" and int(s.get("s_day", 0)) < int(s.get("s_target_days", 100)):
        s["s_mode"], s["s_target_days"] = "buy_1", 100

async def build_fx_view(client: TossApiClient):
    cfg = await ensure_cycle_fields()
    sniper_usd = get_sniper_seed()
    dca_usd_req, dca_krw_req, kr_cnt, us_cnt, usd_details = 0.0, 0.0, 0, 0, []
    for sym, info in cfg.get("stocks", {}).items():
        if not info.get("enabled", True): continue
        is_kr = (info.get("currency") == "KRW")
        ensure_stock_cycle(info, is_kr)
        amt = float(info.get("base_amount", 100000.0 if is_kr else 40.0))
        prof_pct = 0.0
        try:
            cur_p = float(await asyncio.wait_for(client.get_current_price(sym), timeout=3.0) or 0.0)
            hold = await asyncio.wait_for(client.get_symbol_holdings(sym), timeout=3.0)
            avg_p = 0.0
            if isinstance(hold, dict):
                for k in ["avg_price", "avg_buy_price", "average_price", "buy_avg_price", "pchs_avg_pric"]:
                    if hold.get(k): avg_p = float(hold[k]); break
            if avg_p > 0 and cur_p > 0: prof_pct = ((cur_p - avg_p) / avg_p) * 100
        except Exception: pass
        use_amt = (amt / 2.0) if prof_pct >= 1.0 else amt
        if is_kr:
            kr_cnt += 1
            if info["s_mode"] in ["buy_1", "buy_2"]: dca_krw_req += use_amt
        else:
            us_cnt += 1
            if info["s_mode"] in ["buy_1", "buy_2"]:
                dca_usd_req += use_amt
                usd_details.append(f"{sym} ${use_amt:.0f}({'1/2배' if prof_pct >= 1.0 else '1배'})")
    cur_usd = 0.0
    try: cur_usd = float(await asyncio.wait_for(client.get_buying_power("USD"), timeout=3.0) or 0.0)
    except Exception: pass
    tot_req = sniper_usd + dca_usd_req; final_need = max(0.0, tot_req - cur_usd)
    is_hol, hol_reason = check_holiday()
    d_str = f" [{', '.join(usd_details)}]" if usd_details else ""
    lines = [
        f"💱 [토스 당일 필요 달러 브리핑 ({BOT_VERSION})]", f"▫️ 시장 상태: {'🛑 ' if is_hol else '🟢 '}{hol_reason}", "─────────────────",
        f"🔫 [1] 토스 스나이퍼 시드: ${sniper_usd:,.2f}", f"📈 [2] 스마트 적립 ({us_cnt}개 미국종목): ${dca_usd_req:,.2f}{d_str}",
    ]
    if kr_cnt > 0: lines.append(f"🇰🇷 [국내주식 {kr_cnt}개 종목 소요액]: {dca_krw_req:,.0f}원")
    lines.extend([
        "─────────────────", f"💵 현재 계좌 보유 달러: ${cur_usd:,.2f}", f"📊 당일 매매 총 소요액: ${tot_req:,.2f}",
        f"✅ 최종 추가 필요 달러: $0.00 (충분!)" if final_need <= 0 else f"🚨 최종 추가 필요 달러: ${final_need:,.2f}",
        f"⏱ 갱신: {datetime.now(KST_TZ).strftime('%H:%M:%S KST')}"
    ])
    return "\n".join(lines), [[{"text": "🔄 새로고침", "callback_data": "fx"}], [{"text": "🔙 관제탑으로", "callback_data": "panel"}]]
def get_toss_schedule_status(stocks: dict) -> str:
    now_kst, now_est = datetime.now(KST_TZ), datetime.now(EST_TZ)
    if now_kst.weekday() >= 5:
        return "💤 주말 휴장 종료 (월요일 11:00 KST / 11:30 EST 시작)"
    t_kst, t_est = now_kst.strftime("%Y-%m-%d"), now_est.strftime("%Y-%m-%d")
    hm_kst, hm_est = now_kst.strftime("%H:%M"), now_est.strftime("%H:%M")
    us_stocks = [s for s in stocks.values() if s.get("enabled", True) and s.get("currency") != "KRW" and s.get("s_mode") not in ["decision", "pause"]]
    kr_stocks = [s for s in stocks.values() if s.get("enabled", True) and s.get("currency") == "KRW" and s.get("s_mode") not in ["decision", "pause"]]
    us_done = all(s.get("last_exec_date") == t_est for s in us_stocks) if us_stocks else True
    kr_done = all(s.get("last_exec_date") == t_kst for s in kr_stocks) if kr_stocks else True
    if us_done and kr_done:
        nxt = "11:00 KST" if kr_stocks else "11:30 EST (00:30 KST)"
        return f"💤 금일 매매 종료 (절전 휴면 중 | 다음 시작: {nxt})"
    if not kr_done and hm_kst < "11:00":
        return "⏳ 대기 중 (오늘 11:00 KST 한국장 매매 시작)"
    if not us_done and hm_est < "11:30":
        return "⏳ 대기 중 (오늘 11:30 EST / 00:30 KST 미국장 시작)"
    if ("11:00" <= hm_kst <= "15:00" and not kr_done) or ("11:30" <= hm_est <= "15:50" and not us_done):
        return "🟢 정기 매매 시간대 가동 중 (체결 확인 후 자동 종료)"
    return "💤 금일 매매시간 종료 (다음 시작: 11:30 EST / 00:30 KST)"

async def build_panel_view(client: TossApiClient):
    cfg = await sync_holdings_from_toss(client)
    cfg["cycle_mode"] = "buy_1"
    stocks = cfg.get("stocks", {})
    for sym, s in stocks.items(): ensure_stock_cycle(s, s.get("currency") == "KRW")
    await DcaConfigManager.save(cfg)
    total_cnt = len(stocks); kr_cnt = sum(1 for s in stocks.values() if s.get("currency") == "KRW"); us_cnt = total_cnt - kr_cnt
    is_master = cfg.get("is_master_active", True)
    is_hol, hol_reason = check_holiday()
    tp1, sr = float(cfg.get("tp1_pct", 10.0)), float(cfg.get("sr_pct", 20.0))
    decision_syms = [sym for sym, s in stocks.items() if s.get("s_mode") == "decision"]
    lines = [
        f"🎛 [토스 모듈형 초경량 관제탑 ({BOT_VERSION})]",
        f"▫️ 시스템 전원: {'🟢 가동 중 (ON)' if is_master else '🔴 정지됨 (OFF)'}",
        f"▫️ 시장 상태: {'🛑 ' if is_hol else '🟢 '}{hol_reason}",
        f"▫️ 운용 종목수: 📦 총 {total_cnt}종목 (국내 {kr_cnt} / 미국 {us_cnt})", "─────────────────",
        "⏳ [운용 규칙 요약]",
        " • 기본 사이클: 종목별 100일 분할매수 (고정)",
        " • 매매 시각: 🇰🇷 11:00 KST | 🇺🇸 11:30 EST (개장 2시간 뒤)",
        " • 매수 배율: 수익률 +1.0%↑ 시 1/2배 (그 외 1배)",
        " • 100일 종료 시: [N일 정지 / N일 분할매도 / N일 2차매수] 선택", "─────────────────",
        "📊 [수익률 구간별 매도 계획]",
        f" • {tp1:.0f}% 수익 도달 시 ➔ 잔고의 {sr:.0f}% 매도",
        f" • {tp1*2:.0f}% 수익 도달 시 ➔ 잔고의 {sr:.0f}% 매도",
        f" • {tp1*3:.0f}% 이상 수익 도달 시 ➔ 미정 (매도 없음)",
        f"⏱ 조회: {datetime.now(KST_TZ).strftime('%H:%M:%S')}",
        f"⚡ 스케줄 상태: {get_toss_schedule_status(stocks)}"
    ]
    if decision_syms: lines.append(f"\n🚨 [기간 완료 종목: {', '.join(decision_syms)}] 아래 보유종목 리스트에서 다음 단계를 선택하세요!")
    kb = [
        [{"text": "📋 보유종목 리스트 & 개별 금액/상태 설정", "callback_data": "stock_list"}],
        [{"text": "🔴 전체 전원 끄기" if is_master else "🟢 전체 전원 켜기", "callback_data": "toggle_master"}, {"text": "🎯 익절/매도비율 변경", "callback_data": "ask_tp"}],
        [{"text": "🔄 새로고침", "callback_data": "panel"}]
    ]
    return "\n".join(lines), kb

# 현재 허용된 단일 텔레그램 채팅의 목록 위치. 매매 설정과 별도로 메모리에만 저장.
STOCK_LIST_CONTEXT = {"market": "all", "status": "all", "page": 0, "query": ""}


def stock_market(info):
    return "kr" if info.get("currency") == "KRW" else "us"


def stock_list_callback(market=None, status=None, page=None, keep_query=True):
    ctx = STOCK_LIST_CONTEXT
    return "browse|{}|{}|{}|{}".format(
        market if market is not None else ctx["market"],
        status if status is not None else ctx["status"],
        page if page is not None else ctx["page"], int(keep_query))


def select_stock_items(stocks, market="all", status="all", query=""):
    query = query.strip().casefold()
    items = []
    for sym, info in stocks.items():
        if market != "all" and stock_market(info) != market:
            continue
        enabled = bool(info.get("enabled", True))
        if status == "on" and not enabled:
            continue
        if status == "off" and enabled:
            continue
        if query and query not in str(sym).casefold() and query not in str(info.get("name", sym)).casefold():
            continue
        items.append((sym, info))
    return sorted(items, key=lambda item: (
        0 if item[1].get("s_mode") == "decision" else 1,
        str(item[1].get("name", item[0])).casefold(), item[0]))


async def build_stock_list_view(client: TossApiClient, page: int = 0,
                                market=None, status=None, query=None):
    ctx = STOCK_LIST_CONTEXT
    market = market if market in ("all", "kr", "us") else ctx["market"]
    status = status if status in ("all", "on", "off") else ctx["status"]
    query = ctx["query"] if query is None else query.strip()[:80]
    cfg = await sync_holdings_from_toss(client)
    stocks = cfg.get("stocks", {})
    # 목록은 가격/개별 잔고를 종목마다 요청하거나 진행 일수를 추정·저장하지 않음.
    market_items = select_stock_items(stocks, market)
    items = select_stock_items(stocks, market, status, query)
    max_page = max(0, (len(items)-1)//5)
    page = max(0, min(int(page), max_page))
    ctx.update(market=market, status=status, query=query, page=page)
    title = {"all": "전체 주식", "kr": "🇰🇷 한국주식", "us": "🇺🇸 미국주식"}[market]
    status_title = {"all": "전체", "on": "🟢 매매 켜짐", "off": "⏸ 대기·중지"}[status]
    on_count = sum(bool(info.get("enabled", True)) for _, info in market_items)
    lines = [f"📋 [{title} · 총 {len(market_items)}종목]",
             f"🟢 매매 켜짐 {on_count} · ⏸ 대기·중지 {len(market_items)-on_count}",
             f"필터: {status_title} · {page+1}/{max_page+1}페이지"]
    if not cfg.get("is_master_active", True):
        lines.append("🔴 전체 전원 OFF · 모든 종목 자동주문 정지")
    if query:
        lines.append(f"🔎 검색: {query} · {len(items)}종목")
    lines += ["• 종목명·티커를 입력하거나 아래 종목을 선택하세요.", "─────────────────"]
    def btn(text, m=market, st=status, pg=0, keep=True):
        return {"text": text, "callback_data": stock_list_callback(m, st, pg, keep)}
    kb = [[btn("전체시장", "all", keep=False), btn("🇰🇷 한국", "kr", keep=False), btn("🇺🇸 미국", "us", keep=False)],
          [btn("전체", st="all"), btn("🟢 매매 켜짐", st="on"), btn("⏸ 대기·중지", st="off")]]
    for idx, (sym, info) in enumerate(items[page*5:(page+1)*5], page*5+1):
        icon = "🟢" if info.get("enabled", True) else "⏸"
        label = f"{icon} {info.get('name', sym)} ({sym})"
        if info.get("s_mode") == "decision":
            label += " · 결정 대기"
        lines.append(f"{idx}. {label}")
        kb.append([{"text": label[:100], "callback_data": f"detail_{sym}"}])
    if not items:
        lines.append("조건에 맞는 종목이 없습니다.")
    nav = []
    if page > 0:
        nav.append(btn("◀ 이전", pg=page-1))
    if page < max_page:
        nav.append(btn("다음 ▶", pg=page+1))
    if nav:
        kb.append(nav)
    kb.append([{"text": "🔎 종목 검색", "callback_data": "stock_search"},
               btn("🔄 새로고침", pg=page)])
    if query:
        kb.append([btn("검색 해제", keep=False)])
    kb.append([{"text": "🔙 관제탑 메인으로", "callback_data": "panel"}])
    return "\n".join(lines), kb


async def build_stock_detail_view(client: TossApiClient, sym: str):
    cfg = await ensure_cycle_fields(); stocks = cfg.get("stocks", {})
    if sym not in stocks: return await build_stock_list_view(client, STOCK_LIST_CONTEXT["page"])
    s = stocks[sym]; is_kr = (s.get("currency") == "KRW"); ensure_stock_cycle(s, is_kr); await DcaConfigManager.save(cfg)
    cur_p, avg_p, qty = 0.0, 0.0, 0.0
    try:
        cur_p = float(await asyncio.wait_for(client.get_current_price(sym), timeout=3.0) or 0.0)
        hold = await asyncio.wait_for(client.get_symbol_holdings(sym), timeout=3.0)
        if isinstance(hold, dict):
            for k in ["avg_price", "avg_buy_price", "average_price", "buy_avg_price", "pchs_avg_pric"]:
                if hold.get(k): avg_p = float(hold[k]); break
            for k in ["qty", "quantity", "holding_qty", "balance", "hold_qty", "ord_psbl_qty", "sellable_qty"]:
                if hold.get(k): qty = float(hold[k]); break
        if qty == 0.0: qty = float(await asyncio.wait_for(client.get_sellable_quantity(sym), timeout=3.0) or 0.0)
        if int(s.get("s_day", 0)) == 0 and qty > 0:
            amt_tmp = float(s.get("base_amount", 100000.0 if is_kr else 40.0))
            s["s_day"] = await auto_detect_cycle_days(client, sym, is_kr, amt_tmp, avg_p, qty)
            await DcaConfigManager.save(cfg)
    except Exception: pass
    prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
    amt = float(s.get("base_amount", 100000.0 if is_kr else 40.0))
    amt_str = f"{amt:,.0f}원 (+1%↑ 시 1/2: {amt/2:,.0f}원)" if is_kr else f"${amt:.2f} (+1%↑ 시 1/2: ${amt/2:.2f})"
    p_str = f"현재가: {cur_p:,.0f}원 | 평단가: {avg_p:,.0f}원 ({prof_pct:+.2f}% / {qty:.0f}주)" if is_kr else f"현재가: ${cur_p:.2f} | 평단가: ${avg_p:.2f} ({prof_pct:+.2f}% / {qty:.4f}주)"
    s_mode, s_day, s_target = s["s_mode"], int(s["s_day"]), int(s["s_target_days"])
    m_desc = {"buy_1": f"🛒 1차 분할매수 ({s_day}/100일 고정)", "pause": f"⏸ 정지 대기 중 ({s_day}/{s_target}일)", "buy_2": f"🛒 2차 분할매수 ({s_day}/{s_target}일)", "sell": f"📤 분할매도 ({s_day}/{s_target}일)", "decision": f"🚨 기간({s_target}일) 완료! 결정 대기(정지)"}
    lines = [f"{'🇰🇷 한국주식' if is_kr else '🇺🇸 미국주식'} · [{s.get('name', sym)} ({sym}) 상세 설정]", "─────────────────", f"📈 {p_str}", f"💰 1회 기준 매수금: {amt_str}", f"⏳ 진행 거래일수: {m_desc.get(s_mode, s_mode)}", f"🕒 최근 실행일: {s.get('last_exec_date', '대기 중')}"]
    kb = [[{"text": f"💰 [{sym}] 기준금액 변경", "callback_data": f"setamt_{sym}"}, {"text": f"🔢 [{sym}] 진행일수 보정", "callback_data": f"setday_{sym}"}]]
    if s_mode == "decision":
        lines.append("\n🚨 [기간이 완료되었습니다! 다음 진행 방향을 선택하세요]")
        kb.append([{"text": "⏸ 몇 일 정지하며 기다릴지 설정", "callback_data": f"next_pause_{sym}"}])
        kb.append([{"text": "📤 몇 일 동안 나눠서 매도할지 설정", "callback_data": f"next_sell_{sym}"}])
        kb.append([{"text": "🛒 몇 일 동안 2차 매수할지 설정", "callback_data": f"next_buy2_{sym}"}])
    kb.append([{"text": "🔄 새로고침", "callback_data": f"detail_{sym}"}, {"text": "📋 종목 리스트로", "callback_data": stock_list_callback()}])
    kb.append([{"text": "🔙 관제탑 메인으로", "callback_data": "panel"}])

    # 종목별 매매 버튼 v1
    trade_enabled = bool(s.get("enabled", True))
    lines.append("• 자동매매: " + ("🟢 실행 중" if trade_enabled else "⏸ 대기 / 중지"))
    kb.insert(0, [
        {"text": "▶️ 매매 시작", "callback_data": f"trade_on_{sym}"},
        {"text": "⏸ 매매 중지", "callback_data": f"trade_off_{sym}"}
    ])
    return "\n".join(lines), kb
