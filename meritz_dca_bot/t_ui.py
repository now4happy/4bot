# =====================================================================
# FILE: meritz_dca_bot/t_ui.py   (MERITZ_DCA v1.1.0)
# 텔레그램 조작판 화면. 3번 toss_dca_bot/t_ui.py(v4.3.8)에서 옮김.
# v1.0.0 (2026-11-08): 첫 버전.
#   - 그대로: 관제탑·종목 목록(시장/상태 필터·검색·5개씩 페이지)·종목 상세·버튼 이름과 callback_data
#   - 바꿈: 미국주식만 · 매매 시각 미국 동부 10:05~15:40 · 수량은 봇 장부(입고 평단 안 씀) + 증권사 잔고 함께 표시
#   - 더함: ➕ 종목 추가 버튼(add_symbol) · 주문 모드 표시(꺼짐/모의/실주문 + 막힌 이유) · 이월 금액 표시
#   - 뺌: 환전 필요액 화면(build_fx_view, 3번에서도 버튼 없음) · 한국주식 표시
# v1.1.0 (2026-11-13): 관제탑에 SGOV 회차 적립 요약 1줄 + 🪙 SGOV 적립 버튼 (화면은 sgov.build_sgov_view)
# v1.2.0 (2026-11-13): 진행률·자금 패널·오늘 적립 예상
# =====================================================================
from t_core import *
from sgov import sgov_panel_line, sgov_block
from decimal import Decimal


def ensure_stock_cycle(s: dict, is_kr: bool = False):
    if "s_mode" not in s: s["s_mode"] = "buy_1"
    if "s_day" not in s: s["s_day"] = 0
    if "s_target_days" not in s: s["s_target_days"] = 100
    if "base_amount" not in s: s["base_amount"] = 40.0
    if s["s_mode"] == "decision" and int(s.get("s_day", 0)) < int(s.get("s_target_days", 100)):
        s["s_mode"], s["s_target_days"] = "buy_1", 100


def mode_lines():
    """주문 모드 + 실주문을 막는 이유 (화면용)"""
    if not SETTINGS.get("enabled", False):
        head = "▫️ 주문 모드: ⚪ 꺼짐 (enabled=false · 판단·주문 없음)"
    elif RUN.get("dry", True):
        head = "▫️ 주문 모드: 🧪 모의 실행 (주문 안 냄 · 모의 장부에만 기록)"
    else:
        head = "▫️ 주문 모드: 🔴 실주문"
    lines = [head]
    gate = [g for g in RUN.get("gate", []) if g]
    if gate and SETTINGS.get("enabled", False) and not RUN.get("dry", True):
        lines += ["   ⛔ 실주문 막힘: " + g for g in gate[:4]]
    elif gate and SETTINGS.get("enabled", False):
        lines.append(f"   · 실주문 전 남은 확인 {len(gate)}개 (모의에는 영향 없음)")
    return lines


def get_toss_schedule_status(stocks: dict) -> str:
    now_est = datetime.now(EST_TZ)
    t0, t1 = SETTINGS.get("order_time_et", "10:05"), SETTINGS.get("order_deadline_et", "15:40")
    if now_est.weekday() >= 5:
        return f"💤 주말 휴장 (월요일 {t0} 미국 동부 시작)"
    t_est, hm_est = now_est.strftime("%Y-%m-%d"), now_est.strftime("%H:%M")
    us_stocks = [s for s in stocks.values() if s.get("enabled", True) and s.get("s_mode") not in ["decision", "pause"]]
    us_done = all(s.get("last_exec_date") == t_est for s in us_stocks) if us_stocks else True
    if us_done:
        return f"💤 금일 매매 종료 (다음 시작: {t0} 미국 동부)"
    if hm_est < t0:
        return f"⏳ 대기 중 (오늘 {t0} 미국 동부 시작)"
    if t0 <= hm_est <= t1:
        return "🟢 정기 매매 시간대 가동 중 (하루 1번, 끝나면 자동 휴면)"
    return f"💤 금일 매매시간 종료 (다음 시작: {t0} 미국 동부)"


# 설정파일에 기록하지 않는 패널 보기 상태
PANEL_VIEW_CONTEXT = {"mode": "now"}

def progress_bar(pct, icon):
    count = max(0, min(10, int(float(pct) / 10 + 0.5)))
    return icon * count + "⬜" * (10-count)

def progress_lines(cfg, usd, need, mode="now"):
    assets = []
    for sym, icon in (("NKE", "🟦"), ("QLD", "🟪")):
        st = cfg.get("stocks", {}).get(sym)
        if st is None: continue
        day, target = int(st.get("s_day") or 0), int(st.get("s_target_days") or 100)
        value = float(ledger_of(st)[0]) * ledger_avg(st)
        if mode == "done": day, value = target, float(st.get("base_amount") or 0) * target
        pct = min(100, 100*day/target) if target > 0 else 0
        assets.append((value, sym, f"{progress_bar(pct, icon)} {sym} {pct:.0f}% ({day}/{target}일 · ${value:,.0f})"))
    sg = sgov_block(cfg)
    done, total = int(sg.get("tranches_done") or 0), int(sg.get("tranches_total") or 0)
    value = float((sg.get("ledger") or {}).get("principal") or 0)
    if mode == "done": done, value = total, float(sg.get("target_usd_total") or 0)
    pct = min(100, 100*done/total) if total > 0 else 0
    assets.append((value, "SGOV", f"{progress_bar(pct, '🟨')} SGOV {pct:.0f}% ({done}/{total}회 · ${value:,.0f})"))
    pct = min(100, 100*usd/need) if need > 0 else (100 if usd > 0 else 0)
    assets.append((usd, "현금", f"{progress_bar(pct, '🟩')} 현금 {pct:.0f}% (오늘 필요 ${need:,.0f} · ${usd:,.0f})"))
    assets.sort(key=lambda item: item[0], reverse=True)
    lines = ["📊 [시드 대비 진행률 — " + ("완성 시 예상" if mode == "done" else "지금") + "]"]
    if mode == "done": lines.append("완성 시 예상 — 적립 금액은 가격 따라 달라져요")
    lines.extend(item[2] for item in assets)
    lines.append("금액 기준: " + " · ".join(f"{name} ${value:,.0f}" for value,name,_ in assets))
    return lines

async def today_funding(client, cfg):
    # main의 기존 환전 계획을 재사용하여 적립+SGOV 필요액을 구한다.
    # 순환 import를 피하기 위해 실행 시에만 접근한다.
    from main import dca_fx_plan
    return await dca_fx_plan(client, cfg)

async def stock_today_estimate(client, cfg):
    from sgov import sgov_fx_need
    need = await today_funding(client, cfg)
    sg_need = await sgov_fx_need(client, cfg, datetime.now(KST_TZ).strftime("%Y-%m-%d"))
    return max(0, need - sg_need)

async def build_funds_view(client, notice=""):
    from main import fx_auto_amount, FxNoPrice
    cfg = await DcaConfigManager.load()
    sg = sgov_block(cfg)
    usd = float(await asyncio.to_thread(client.api.usd_estimated))
    need, error = None, None
    try: need = await today_funding(client, cfg)
    except FxNoPrice as e: error = f"참고가 조회 불가: {e}"
    except Exception as e: error = f"환전 계획 조회 실패: {type(e).__name__}"
    amount = fx_auto_amount(Decimal(str(need)) - Decimal(str(usd))) if need is not None else None
    stocks = cfg.get("stocks", {})
    lines = ["💰 [자금 · 매매 상황판]", f"보유 달러: ${usd:,.2f}",
             "매매: " + ("자동" if SETTINGS.get("enabled") else "중지") + " / " + ("모의" if RUN.get("dry", True) else "실전"),
             "자동환전: " + ("켜짐" if SETTINGS.get("auto_fx", {}).get("on") else "꺼짐"),
             "적립 시드 (100일): " + " · ".join(f"{sym} ${float(stocks[sym].get('base_amount') or 0):,.2f}/회" for sym in ("NKE","QLD") if sym in stocks),
             f"SGOV 시드: 총 ${float(sg.get('target_usd_total') or 0):,.2f} · {int(sg.get('tranches_total') or 0)}회",
             "─────────────────", "환전: 적립 + SGOV 합산"]
    lines.append(f"오늘 필요: ${need:,.2f}" if need is not None else f"오늘 필요: 미확인 ({error})")
    lines.append(f"보유 USD: ${usd:,.2f}")
    lines.append(f"환전할 금액: ${amount:,.2f}" if amount is not None else "환전할 금액 없음")
    lines.extend(["─────────────────", "⚙️ 시드 설정",
                  f"SGOV 회차 금액 ${float(sg.get('tranche_usd') or 0):,.2f} · 1회차 ${float(sg.get('first_tranche_usd') or 0):,.2f} · 간격 {int(sg.get('interval_days') or 0)}일"])
    if notice: lines.insert(0, notice)
    kb = []
    if amount is not None: kb.append([{"text":"자동환전 실행", "callback_data":"funds_fx"}])
    kb += [[{"text":"시드 설정", "callback_data":"funds_seed"}],
           [{"text":"🔄 새로고침", "callback_data":"funds"}, {"text":"🔙 관제탑", "callback_data":"panel"}]]
    return "\n".join(lines), kb

async def build_panel_view(client):
    cfg = await sync_holdings_from_meritz(client)
    cfg["cycle_mode"] = "buy_1"
    stocks = cfg.get("stocks", {})
    for sym, s in stocks.items(): ensure_stock_cycle(s)
    await DcaConfigManager.save(cfg)
    total_cnt = len(stocks)
    is_master = cfg.get("is_master_active", False)
    is_hol, hol_reason = check_holiday()
    tp1, sr = float(cfg.get("tp1_pct", 10.0)), float(cfg.get("sr_pct", 20.0))
    decision_syms = [sym for sym, s in stocks.items() if s.get("s_mode") == "decision"]
    t0, t1 = SETTINGS.get("order_time_et", "10:05"), SETTINGS.get("order_deadline_et", "15:40")
    lines = [
        f"🎛 [메리츠 적립 관제탑 ({BOT_VERSION})]",
        f"▫️ 시스템 전원: {'🟢 가동 중 (ON)' if is_master else '🔴 정지됨 (OFF)'}",
        *mode_lines(),
        f"▫️ 시장 상태: {'🛑 ' if is_hol else '🟢 '}{hol_reason}",
        f"▫️ 운용 종목수: 📦 총 {total_cnt}종목 (미국주식만)",
        "▫️ 시작 상태: " + (f"주입됨 ({cfg.get('start_injected')})" if cfg.get("start_injected") else "주입 전 (--inject-start)"),
        "─────────────────",
        "⏳ [운용 규칙 요약]",
        " • 기본 사이클: 종목별 100일 분할매수 (고정)",
        f" • 매매 시각: 🇺🇸 {t0}~{t1} 미국 동부 시장가 즉시주문 · 하루 1번",
        " • 매수 배율: 수익률 +1.0%↑ 시 1/2배 (그 외 1배)",
        " • 정수 주문: " + ("남은 금액은 다음 날로 이월 (평균 = 기준금액)" if SETTINGS.get("us_int_buy_mode", "carry") != "min1" else "금액이 1주보다 작아도 최소 1주"),
        *n7_status_lines(cfg),
        sgov_panel_line(cfg),
        " • 100일 종료 시: [N일 정지 / N일 분할매도 / N일 2차매수] 선택", "─────────────────",
        "📊 [수익률 구간별 매도 계획]",
        f" • {tp1:.0f}% 수익 도달 시 ➔ 잔고의 {sr:.0f}% 매도",
        f" • {tp1*2:.0f}% 수익 도달 시 ➔ 잔고의 {sr:.0f}% 매도",
        f" • {tp1*3:.0f}% 이상 수익 도달 시 ➔ 미정 (매도 없음)",
        " • 단계는 위로만: 이미 판 단계는 다시 팔지 않음 (보유 0주·진행일수 0 입력 때만 초기화)",
        " • 정지·결정 대기 중: 익절 구간 도달 시 알림만 (자동 매도 아님)",
        " • 평단: 봇 장부 기준 (입고 평단 안 씀)",
        f"⏱ 조회: {datetime.now(KST_TZ).strftime('%H:%M:%S')} KST",
        f"⚡ 스케줄 상태: {get_toss_schedule_status(stocks)}"
    ]
    try:
        usd = float(await asyncio.to_thread(client.api.usd_estimated))
        need = await today_funding(client, cfg)
        lines.extend(["─────────────────", *progress_lines(cfg, usd, need, PANEL_VIEW_CONTEXT["mode"])])
    except Exception as e:
        lines.append(f"📊 시드 대비 진행률: 조회 실패 ({type(e).__name__})")
    if decision_syms: lines.append(f"\n🚨 [기간 완료 종목: {', '.join(decision_syms)}] 아래 보유종목 리스트에서 다음 단계를 선택하세요!")
    # v1.2.3: 관제탑 패널은 전체 현황 + 자금 + 전원 + 새로고침만. 주식·SGOV로 옮길 수 있는 버튼은 그쪽 패널로 이동.
    #   보유종목 리스트·종목 추가는 주식 패널에 이미 있음, SGOV 적립은 하단 SGOV 버튼으로, 익절/매도비율·지수 배수는 주식 패널로.
    kb = [
        [{"text": "지금", "callback_data": "panel_view_now"}, {"text": "완성 시 예상", "callback_data": "panel_view_done"}],
        [{"text": "💰 자금", "callback_data": "funds"}],
        [{"text": "🔴 전체 전원 끄기" if is_master else "🟢 전체 전원 켜기", "callback_data": "toggle_master"}],
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


async def build_stock_list_view(client, page: int = 0, market=None, status=None, query=None):
    ctx = STOCK_LIST_CONTEXT
    market = market if market in ("all", "kr", "us") else ctx["market"]
    status = status if status in ("all", "on", "off") else ctx["status"]
    query = ctx["query"] if query is None else query.strip()[:80]
    cfg = await sync_holdings_from_meritz(client)
    stocks = cfg.get("stocks", {})
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
    if not cfg.get("is_master_active", False):
        lines.append("🔴 전체 전원 OFF · 모든 종목 자동주문 정지")
    try:
        lines.append(f"💵 오늘 적립 예상: ${await stock_today_estimate(client, cfg):,.2f} (장 열릴 때 확정)")
    except Exception: lines.append("💵 오늘 적립 예상: 조회 불가 (장 열릴 때 확정)")
    if query:
        lines.append(f"🔎 검색: {query} · {len(items)}종목")
    lines += ["• 종목명·티커를 입력하거나 아래 종목을 선택하세요.", "─────────────────"]
    def btn(text, m=market, st=status, pg=0, keep=True):
        return {"text": text, "callback_data": stock_list_callback(m, st, pg, keep)}
    kb = [[btn("전체", st="all"), btn("🟢 매매 켜짐", st="on"), btn("⏸ 대기·중지", st="off")]]
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
    kb.append([{"text": "🔎 종목 검색", "callback_data": "stock_search"}, {"text": "➕ 종목 추가", "callback_data": "add_symbol"}])
    # v1.2.3: 관제탑에서 옮겨온 주식 적립 설정 (익절/매도비율·지수 연동 배수).
    kb.append([{"text": "🎯 익절/매도비율 변경", "callback_data": "ask_tp"},
               {"text": "📐 지수 연동 배수 끄기" if cfg.get("n7_enabled", False) else "📐 지수 연동 배수 켜기", "callback_data": "toggle_n7"}])
    kb.append([btn("🔄 새로고침", pg=page)])
    if query:
        kb.append([btn("검색 해제", keep=False)])
    kb.append([{"text": "🔙 관제탑 메인으로", "callback_data": "panel"}])
    return "\n".join(lines), kb


async def build_stock_detail_view(client, sym: str):
    cfg = await ensure_cycle_fields(); stocks = cfg.get("stocks", {})
    if sym not in stocks: return await build_stock_list_view(client, STOCK_LIST_CONTEXT["page"])
    s = stocks[sym]; ensure_stock_cycle(s); await DcaConfigManager.save(cfg)
    cur_p, broker_q = 0.0, None
    qty, avg_p = ledger_of(s)[0], ledger_avg(s)
    try:
        cur_p = float(await asyncio.wait_for(client.get_current_price(sym), timeout=6.0) or 0.0)
        broker_q = float((await asyncio.wait_for(client.get_symbol_holdings(sym), timeout=6.0)).get("qty") or 0.0)
    except Exception: pass
    if (int(s.get("s_day", 0)) == 0 and qty > 0 and s.get("s_mode") == "buy_1" and not s.get("day_set")
            and (s.get("ledger") or {}).get("source") == "broker_avg"):
        # 3번은 일차 0 + 보유 있으면 단계와 상관없이 추정해 덮어씀 → 분할매도·정지·0일 재시작 직후에도 일차가 바뀌는 문제.
        # 여기서는 자동 등록된(증권사 평단) 종목의 1차 매수에서 한 번만 추정 (사용자 입력·주입 뒤에는 추정 안 함)
        s["s_day"] = await auto_detect_cycle_days(client, sym, False, float(s.get("base_amount", 40.0)), avg_p, qty)
        s["day_set"] = True
        await DcaConfigManager.save(cfg)
    prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
    amt = float(s.get("base_amount", 40.0))
    amt_str = f"${amt:.2f} (+1%↑ 시 1/2: ${amt/2:.2f})"
    p_str = f"현재가: ${cur_p:.2f} | 평단가(장부): ${avg_p:.4f} ({prof_pct:+.2f}% / {qty:g}주)"
    bq = "조회 실패" if broker_q is None else f"{broker_q:g}주" + ("" if abs(broker_q - qty) < 1e-6 else " ⚠️ 장부와 다름")
    s_mode, s_day, s_target = s["s_mode"], int(s["s_day"]), int(s["s_target_days"])
    m_desc = {"buy_1": f"🛒 1차 분할매수 ({s_day}/100일 고정)", "pause": f"⏸ 정지 대기 중 ({s_day}/{s_target}일)", "buy_2": f"🛒 2차 분할매수 ({s_day}/{s_target}일)", "sell": f"📤 분할매도 ({s_day}/{s_target}일)", "decision": f"🚨 기간({s_target}일) 완료! 결정 대기(정지)"}
    src = (s.get("ledger") or {}).get("source", "")
    lines = [f"🇺🇸 미국주식 · [{s.get('name', sym)} ({sym}) 상세 설정]", "─────────────────", f"📈 {p_str}",
             f"🏦 메리츠 잔고: {bq}" + (" · ⚠️ 평단=증권사 값(자동 등록)" if src == "broker_avg" else ""),
             f"💰 1회 기준 매수금: {amt_str}", f"↪️ 이월 금액(정수 주문 남은 돈): ${float(s.get('buy_carry') or 0):.2f}",
             f"⏳ 진행 거래일수: {m_desc.get(s_mode, s_mode)}", f"🕒 최근 실행일: {s.get('last_exec_date') or '대기 중'}"]
    try:
        lines.append(f"💵 오늘 적립 예상: ${await stock_today_estimate(client, cfg):,.2f} (장 열릴 때 확정)")
    except Exception: lines.append("💵 오늘 적립 예상: 조회 불가 (장 열릴 때 확정)")
    idx = n7_index_of(s); etf, _, idx_name = N7_INDEX[idx]
    n7_on = bool(cfg.get("n7_enabled", False)); n7_m = float(((cfg.get("n7_state") or {}).get(idx) or {}).get("mult", 1.0))
    lines.append(f"📐 기준 지수: {idx_name} ({etf}) · " + (f"지수 배수 {n7_m:.1f}배 (켜짐)" if n7_on else "지수 연동 배수 꺼짐"))
    lines.append(f"🎯 익절 진행 단계: {int(s.get('sold_stage', 0))}차까지 완료 (위로만, 다시 팔지 않음)")
    kb = [[{"text": f"💰 [{sym}] 기준금액 변경", "callback_data": f"setamt_{sym}"}, {"text": f"🔢 [{sym}] 진행일수 보정", "callback_data": f"setday_{sym}"}]]
    kb.append([{"text": f"📐 기준 지수 바꾸기 ({idx_name} → {N7_INDEX[[k for k in N7_CHOICES['US'] if k != idx][0]][2]})", "callback_data": f"idx_{sym}"}])
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
