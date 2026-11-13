#!/usr/bin/env python3
# =====================================================================
# FILE: meritz_dca_bot/main.py   (MERITZ_DCA v1.1.1)
# 메리츠 적립 봇 (서비스 meritz_dca) — 3번 toss_dca_bot/main.py(v4.3.8) 엔진을 옮기고 토스 API 만 메리츠로 바꿈
# v1.0.0 (2026-11-08): 첫 버전.
#   - 그대로: 100일 사이클(buy_1/pause/buy_2/sell/decision) · +1%↑ ½ 매수 · 익절 10%/20% 구간 20% 매도(단계는 위로만)
#     · 정지·결정 중 익절 구간 알림만 · 가격 0/거래정지 가드 · N7 지수 배수 · 달러 부족이어도 익절 먼저
#     · 응답 끊긴 주문은 그날 재주문 안 함 · save_merged(텔레그램 변경 보존) · 주문 직전 전원/종목 재확인 · 텔레그램 조작판
#   - 바꿈: 미국주식만 · 미국 동부 10:05~15:40 · 메리츠 시장가 즉시주문(정수 주) · 평단/수량은 봇 장부(체결 내역으로 갱신)
#   - 안전장치: 기본 enabled=false·dry_run=true · 입고 확인(transfer_confirmed) · 키 지문 일치 + P/VR6/3번 키면 정지
#     · 시작 상태 주입(--inject-start) 전 실주문 없음 · 장부≠잔고면 그 종목 주문 안 함 · 체결 대기 중 재주문 안 함
#     · toss_dca 서비스가 살아 있으면 텔레그램 폴링 안 함 (같은 토큰) · USD 행 없는 빈 계좌 = $0 (멈추지 않음)
# v1.0.2 (2026-11-13): 낮 자동환전 참고가 fallback — 장 닫힌 낮에 시세 0이면 전일 종가로 환전 규모 계산, 없으면 no_price로 그날 종료 (토큰 핫픽스: t_core.TG_TOKEN 참조)
# v1.1.0 (2026-11-13): SGOV 회차 적립 (판단은 sgov.py, 같은 4번 계좌·같은 봇). NKE/QLD 동작은 그대로.
#   - 미국 단계: SGOV 회차를 먼저 판단·예약 → 적립 매수는 (USD 예수금 − SGOV 몫)으로만 달러 검사
#   - 체결 반영: kind=sgov 주문은 SGOV 장부에만 · 아침 환전 금액에 SGOV 회차 몫 더함 · 관제탑 🪙 SGOV 메뉴 · --check 미리보기
# v1.1.1 (2026-11-13): 버튼·메시지 무응답 수정 — 채팅방 검사가 `from t_core import *` 로 복사된 CHAT_ID("")를 보던 것을
#   t_core.CHAT_ID(실제 읽은 값)로 바꿈 (TG_TOKEN 핫픽스와 같은 종류). 다른 채팅방/메시지 없는 콜백은 받은 채팅방 ID·data 를
#   감사 로그에만 남김 (진단). 폴링·매매·SGOV 판단 로직은 그대로.
# v1.2.0 (2026-11-13): 하단 메뉴·자금/시드/진행률 화면 및 수동 환전 확인
# v1.2.2 (2026-11-13): 시드 설정을 2개 메뉴로 나눔 (적립 / SGOV). 저장 뒤에는 같은 그룹 메뉴로 돌아감.
# v1.2.3 (2026-11-13): 관제탑 버튼 정리 — 익절/매도비율·지수 배수를 주식 패널로 이동 (바꾼 뒤에도 주식 패널로 돌아감).
# v1.2.4 (2026-11-13): 관제탑 지금/완성 시 예상 토글 제거 (내용은 t_ui.py에).
# 사용:
#   python3 main.py --fingerprint     키 지문만 출력 (expected_key_fp 에 넣을 값)
#   python3 main.py --check           주문 없이 점검 + 종목별 오늘 판단 미리보기
#   python3 main.py --inject-start    입고 확인 뒤 시작 상태 주입 (settings.start → 실주문 장부)
#   python3 main.py --dry-reset       모의 장부 지우기 (다음 실행 때 실주문 장부/설정에서 다시 만듦)
#   python3 main.py                   상시 실행 (서비스용)
# =====================================================================
import argparse, copy, os, re, signal, subprocess, sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from zoneinfo import ZoneInfo

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)   # 실행 위치와 상관없이 이 폴더의 부품을 씀 (meritz_laoer 와 같음)
from t_core import *
import t_core  # TG_TOKEN live global (from-import copy goes stale)
from t_ui import *
import dca_engine
import sgov as SG
from dca_engine import load_settings, config_path
from meritz_api import MeritzApi, MeritzDcaClient, MeritzError, WarnNeeded, key_fingerprint

wait_state = {"mode": None, "sym": None}

STEP_KEYS = ("s_day", "s_mode", "s_target_days", "last_exec_date", "sold_stage", "has_held", "tp_alert_date", "ledger", "buy_carry")
_HOLD_WATCH_DAY = {}   # 정지·결정 중 보유 점검을 종목별 하루 1번만 (메모리)
_MKT = {"ts": 0.0, "code": ""}
_POLL = {"ts": 0.0, "blocked": False}

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
CB_PREFIX = ("trade_on_", "trade_off_", "detail_", "setday_", "setamt_", "next_pause_", "next_sell_", "next_buy2_", "slist_", "sgovx_", "sgovmode_")


class GateBlocked(Exception):
    """실주문 안전장치에 걸림 → 주문을 보내지 않음 (체결 없음 확정)"""


# ---------------------------------------------------------------- 설정·안전장치
def key_problems(s):
    """(문제 목록, 키 지문). 지문이 기대값과 다르거나 P/VR6/3번 키와 같으면 문제"""
    bad, fp = [], ""
    kf = s.get("key_file")
    if not kf or not os.path.isfile(kf):
        return ["메리츠 4번 키 파일 없음 (key_file)"], ""
    try:
        fp = key_fingerprint(kf)
    except Exception:
        return ["키 파일 형식 오류 (app_key/app_secret)"], ""
    exp = str(s.get("expected_key_fp") or "").strip()
    if not exp:
        bad.append("expected_key_fp 비어 있음 (--fingerprint 값 입력)")
    elif fp != exp:
        bad.append("키 지문 불일치 — 메리츠 4번 계좌 키가 아님")
    if fp in {str(x).strip() for x in (s.get("forbid_key_fps") or []) if str(x).strip()}:
        bad.append("P·VR6·3번 키와 같은 지문 — 재사용 금지")
    for other in s.get("forbid_key_files") or []:
        try:
            if os.path.realpath(other) == os.path.realpath(kf):
                bad.append("key_file 이 다른 봇 키 파일과 같은 경로 — 재사용 금지")
            elif os.path.isfile(other) and key_fingerprint(other) == fp:
                bad.append("다른 봇 키와 같은 키 — 재사용 금지")
        except Exception:
            pass
    return bad, fp


def start_problems(s):
    """settings.start 검사 → 문제 목록"""
    st = s.get("start") or {}
    bad = []
    stocks = st.get("stocks") or {}
    if not isinstance(stocks, dict) or not stocks:
        return ["start.stocks 없음"]
    for sym, v in stocks.items():
        if not is_us_symbol(sym):
            bad.append(f"{sym}: 미국 티커 아님 (한국주식 제외)"); continue
        try:
            q, pr = float(v.get("qty")), float(v.get("principal_usd"))
        except (TypeError, ValueError):
            bad.append(f"{sym}: qty/principal_usd 숫자 아님"); continue
        if q <= 0 or q != int(q): bad.append(f"{sym}: qty 는 1 이상 정수")
        if pr <= 0: bad.append(f"{sym}: principal_usd 0 이하")
        av = v.get("avg_usd")
        if av is not None and q > 0 and abs(pr / q - float(av)) > 0.01:
            bad.append(f"{sym}: avg_usd 가 principal_usd ÷ qty 와 0.01 넘게 다름")
        d = v.get("s_day", 0)
        if not isinstance(d, int) or not 0 <= d <= 100: bad.append(f"{sym}: s_day 0~100 정수")
        if v.get("sold_stage", 0) not in (0, 1, 2): bad.append(f"{sym}: sold_stage 0/1/2")
        if float(v.get("base_amount", 0) or 0) <= 0: bad.append(f"{sym}: base_amount 없음")
    for k in ("tp1_pct", "sr_pct"):
        if float(st.get(k, 0) or 0) <= 0: bad.append(f"start.{k} 없음")
    return bad


def build_start_config(s, base=None, source="settings.start"):
    """settings.start → 상태 파일 내용. base 의 다른 종목은 보존"""
    st = s.get("start") or {}
    cfg = copy.deepcopy(base) if base else copy.deepcopy(DcaConfigManager.DEFAULT_CONFIG)
    cfg.setdefault("stocks", {})
    cfg["tp1_pct"], cfg["sr_pct"] = float(st["tp1_pct"]), float(st["sr_pct"])
    cfg["n7_enabled"] = bool(st.get("n7_enabled", False))
    if isinstance(st.get("n7_state"), dict): cfg["n7_state"] = copy.deepcopy(st["n7_state"])
    cfg["is_master_active"] = bool(st.get("master_active", False))
    cfg.setdefault("pending_orders", [])
    for sym, v in (st.get("stocks") or {}).items():
        sym = sym.strip().upper(); q = float(v["qty"]); pr = round(float(v["principal_usd"]), 4)
        e = new_stock_entry(sym, v.get("name", sym), q, pr, source, float(v["base_amount"]), cfg["tp1_pct"], cfg["sr_pct"])
        e.update(enabled=bool(v.get("enabled", True)), s_mode=v.get("s_mode", "buy_1"), s_day=int(v.get("s_day", 0)),
                 s_target_days=int(v.get("s_target_days", 100)), sold_stage=int(v.get("sold_stage", 0)),
                 has_held=False, last_exec_date="", index_ref=v.get("index_ref", "SP500"), day_set=True)
        cfg["stocks"][sym] = e
    cfg["start_injected"] = datetime.now(EST_TZ).strftime("%Y-%m-%d") + ("" if source == "settings.start" else f" ({source})")
    return cfg


def live_gate(cfg=None):
    """실주문 전 통과해야 하는 조건 → 문제 목록 (빈 목록 = 통과)"""
    s = SETTINGS
    bad = []
    if not s.get("enabled"): bad.append("enabled=false")
    if s.get("dry_run", True): bad.append("dry_run=true (모의)")
    if not s.get("transfer_confirmed"): bad.append("입고 확인 전 (transfer_confirmed=false)")
    bad += key_problems(s)[0]
    real = DcaConfigManager.read_sync(config_path(s, dry=False))
    if not real.get("start_injected"): bad.append("시작 상태 주입 전 (--inject-start)")
    return bad


def refresh_settings():
    """설정 파일을 다시 읽고 모드(실주문/모의)에 맞는 상태 파일을 고름. 모의 장부가 없으면 만들어 둠"""
    s = load_settings()
    SETTINGS.clear(); SETTINGS.update(s)
    RUN["dry"] = bool(s.get("dry_run", True))
    os.makedirs(s["state_dir"], exist_ok=True)
    path = config_path(s)
    if RUN["dry"] and not os.path.exists(path):
        real = DcaConfigManager.read_sync(config_path(s, dry=False))
        if real.get("start_injected"):
            seed = real
        elif not start_problems(s):
            seed = build_start_config(s, source="모의: 입고 확인 없이 settings.start")
        else:
            seed = copy.deepcopy(DcaConfigManager.DEFAULT_CONFIG)
        DcaConfigManager.write_sync(seed, path)
    DcaConfigManager.use(path)
    kb, _ = key_problems(s)
    RUN["key_ok"] = not kb
    RUN["gate"] = live_gate()
    return s


# ---------------------------------------------------------------- 재생 로그 도우미 (3번과 같음)
def _snap(sym, s, **vals):
    return RL.audit("decision_input", sym=sym, mode=s.get("s_mode"), day=s.get("s_day"), target=s.get("s_target_days"),
                    sold_stage=s.get("sold_stage"), base_amount=s.get("base_amount"),
                    **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in vals.items()})

def _decide(sym, decision, outcome, reason=None, s=None, aref=None, daily=False, **kw):
    if daily and not RL.once(f"{sym}|{decision}|{reason}"):
        RL.count(f"skip:{reason}"); return
    s = s or {}
    RL.ev("decision", decision, outcome, reason, actor="scheduler", sym_ref=RL.ref(sym),
          mode=s.get("s_mode"), day=s.get("s_day"), target=s.get("s_target_days"), audit_ref=aref, **kw)

def _rejected(e) -> bool:
    """증권사가 거절한 주문(체결 안 됨)인지. 메리츠 오류는 'API 코드' 로 시작. 응답 끊김·시간초과는 False"""
    return isinstance(e, (GateBlocked, WarnNeeded)) or (isinstance(e, MeritzError) and str(e).startswith("API "))

async def _order(kind, sym, side, size, ord_id, client, cur_p):
    """주문 1건. 보내기 바로 전에 안전장치를 다시 봄. 모의면 주문 API 를 부르지 않고 현재가 체결로 가정.
    접수되면 체결 대기 목록(pending_orders)에 남김 → 체결 내역으로 장부 갱신."""
    chain = "ord-" + (RL.ref(ord_id) or "x"); t0 = time.time()
    dry = RUN.get("dry", True)
    try:
        if not dry:
            gate = live_gate()
            if gate: raise GateBlocked("; ".join(gate))
            res = await client.market_order("BUY" if side == "buy" else "SELL", sym, int(size))
        else:
            res = {"no": f"DRY-{ord_id}", "dry_fill": [float(size), round(float(size) * float(cur_p), 4)]}
    except Exception as e:
        aref = RL.audit("order_submit_failed", chain=chain, sym=sym, side=side, size=size, client_order_id=ord_id, error=str(e)[:300])
        RL.ev("external_call", "order_submit", "failed", RL.reason_of(e) if _rejected(e) else "no_response_maybe_filled",
              actor="scheduler", level="ERROR", chain=chain, kind=kind, side=side, sym_ref=RL.ref(sym),
              ms=int((time.time() - t0) * 1000), audit_ref=aref)
        raise
    bid = str(res.get("no") or "")
    aref = RL.audit("order_submit", chain=chain, sym=sym, side=side, size=size, client_order_id=ord_id, broker_order_id=bid, dry=dry)
    RL.ev("external_call", "order_submit", "ok", None, actor="scheduler", chain=chain, kind=kind, side=side,
          sym_ref=RL.ref(sym), broker_ref=RL.ref(bid), broker_id_found=bool(bid), fill_check="pending_orders",
          dry=dry, ms=int((time.time() - t0) * 1000), audit_ref=aref)
    fresh = await DcaConfigManager.load()
    fresh.setdefault("pending_orders", []).append({
        "oid": ord_id, "no": bid, "sym": sym, "side": "BUY" if side == "buy" else "SELL", "qty": float(size),
        "kind": kind, "date": datetime.now(EST_TZ).strftime("%Y-%m-%d"), "ts": time.time(),
        "applied_q": 0.0, "applied_amt": 0.0, "dry_fill": res.get("dry_fill")})
    await DcaConfigManager.save(fresh)
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
        latest.get("is_master_active", False)
        and sym in latest.get("stocks", {})
        and bool(latest["stocks"][sym].get("enabled", True))
    )

async def _read_position(client, sym, s):
    """현재가 + 봇 장부(평단·수량). 조회만, 주문 없음"""
    cur_p = float(await client.get_current_price(sym) or 0.0)
    q, _ = ledger_of(s)
    return cur_p, ledger_avg(s), q

async def _hold_watch(client, cfg, sym, s, tp1, today_str):
    """정지·결정 중에도 익절 구간 도달 여부만 보고 알림 1회(하루 1번). 매수·매도 주문은 절대 하지 않음. (3번 R2 그대로)"""
    if s.get("tp_alert_date") == today_str or _HOLD_WATCH_DAY.get(sym) == today_str: return
    _HOLD_WATCH_DAY[sym] = today_str
    try:
        cur_p, avg_p, qty = await _read_position(client, sym, s)
    except Exception as e:
        RL.err("hold_watch", e, event_type="decision", sym_ref=RL.ref(sym)); return
    if cur_p <= 0 or avg_p <= 0 or qty <= 0: return
    prof_pct = (cur_p - avg_p) / avg_p * 100
    stg = tp_sell_stage(prof_pct, tp1, int(s.get("sold_stage", 0)))
    if stg <= 0: return
    s["tp_alert_date"] = today_str; await save_merged(cfg, sym)
    _decide(sym, "hold_watch", "ok", "tp_zone_alert_only", s, _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, profit_pct=prof_pct, stage=stg))
    mode_txt = "정지 대기" if s.get("s_mode") == "pause" else "기간 완료·결정 대기"
    send_panel(f"🔔 [{sym} {stg}차 익절 구간 도달 알림]\n• 현재 {mode_txt} 중입니다. 수익률 {prof_pct:+.2f}%\n"
               f"• 정지 중 알림이며 자동 매도가 아닙니다. 아무 주문도 내지 않았습니다.\n• 팔지 여부는 직접 결정해 주세요. (같은 종목은 하루 1번만 알림)",
               [[{"text": f"📄 {sym} 상세", "callback_data": f"detail_{sym}"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])


# ---------------------------------------------------------------- 체결 반영 (봇 장부 = 체결 내역 기준)
def _hm(s, default):
    s = str(s or default)
    return s if re.fullmatch(r"\d{2}:\d{2}", s) else default

async def sync_fills(client):
    """체결 대기 주문을 체결 내역으로 확인 → 장부(수량·원금) 반영. 늘어난 체결분만 더함(같은 체결 두 번 안 셈).
    sync_time_et 가 지나도(또는 다음 날이 돼도) 안 끝난 주문은 있는 만큼만 반영하고 목록에서 뺌 + 알림."""
    cfg = await DcaConfigManager.load()
    pend = list(cfg.get("pending_orders") or [])
    if not pend: return 0
    now = datetime.now(EST_TZ); today = now.strftime("%Y-%m-%d"); past_sync = now.strftime("%H:%M") >= _hm(SETTINGS.get("sync_time_et"), "16:10")
    fills = {}
    real = [p for p in pend if not str(p.get("no", "")).startswith("DRY-")]
    if real:
        d0 = min(p["date"] for p in real).replace("-", ""); d1 = now.strftime("%Y%m%d")
        try: fills = await client.fills(d0, d1)
        except Exception as e:
            RL.err("fill_sync", e, event_type="external_call"); return 0
    lines, keep, changed = [], [], False
    for p in pend:
        if str(p.get("no", "")).startswith("DRY-"):
            fq, famt = (p.get("dry_fill") or [0.0, 0.0])
            side = p["side"]
        else:
            side, fq, famt = fills.get(str(p.get("no")), (p["side"], 0.0, 0.0))
        dq, damt = round(float(fq) - float(p.get("applied_q", 0)), 6), float(famt) - float(p.get("applied_amt", 0))
        s = cfg.get("sgov") if p.get("kind") == "sgov" else cfg.get("stocks", {}).get(p["sym"])   # SGOV 체결은 SGOV 장부에만
        if dq > 1e-9 and s is not None:
            ledger_apply_fill(s, p["side"], dq, damt)
            if p["side"] == "BUY" and ledger_of(s)[0] > 0 and p.get("kind") != "sgov": s["has_held"] = True
            p["applied_q"], p["applied_amt"] = round(float(fq), 6), round(float(famt), 4); changed = True
            px = damt / dq if dq else 0.0
            lines.append(f"• {p['sym']} {'매수' if p['side'] == 'BUY' else '매도'} {dq:g}주 @ ${px:.2f} → 장부 {ledger_of(s)[0]:g}주 · 평단 ${ledger_avg(s):.4f}")
            RL.ev("state_change", "ledger_fill", "ok", None, actor="scheduler", sym_ref=RL.ref(p["sym"]), side=p["side"],
                  audit_ref=RL.audit("ledger_fill", sym=p["sym"], side=p["side"], fill_qty=dq, fill_amt=round(damt, 4), ledger=s.get("ledger")))
        done = float(p.get("applied_q", 0)) >= float(p["qty"]) - 1e-9
        expired = p["date"] < today or past_sync
        if done or expired:
            changed = True
            if not done:
                lines.append(f"⚠️ {p['sym']} {'매수' if p['side'] == 'BUY' else '매도'} 주문 {p['qty']:g}주 중 {float(p.get('applied_q', 0)):g}주만 체결 확인 — 앱에서 확인해 주세요")
            continue
        keep.append(p)
    if changed:
        fresh = await DcaConfigManager.load()
        for sym, s in cfg.get("stocks", {}).items():
            if sym in fresh.get("stocks", {}):
                for k in ("ledger", "has_held"):
                    if k in s: fresh["stocks"][sym][k] = s[k]
        if isinstance(cfg.get("sgov"), dict) and isinstance(fresh.get("sgov"), dict):
            fresh["sgov"]["ledger"] = cfg["sgov"].get("ledger", fresh["sgov"].get("ledger"))
        done_oids = {p["oid"] for p in pend} - {p["oid"] for p in keep}
        fresh["pending_orders"] = [p for p in (fresh.get("pending_orders") or []) if p["oid"] not in done_oids]
        for p in fresh["pending_orders"]:
            for k in keep:
                if k["oid"] == p["oid"]: p.update(applied_q=k["applied_q"], applied_amt=k["applied_amt"])
        await DcaConfigManager.save(fresh)
    if lines:
        send_panel("🧾 [체결 반영 · 봇 장부]\n" + "\n".join(lines), [[{"text": "📋 보유종목 확인", "callback_data": "stock_list"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
    return len(lines)


async def us_market_open(client) -> bool:
    """메리츠 장운영 코드 "004"(정규장) 일 때만 True. 5분 캐시. 조회 실패 = 오늘 이 회차는 쉼"""
    if time.time() - _MKT["ts"] < 300: return _MKT["code"] == "004"
    try: code = str(await client.us_market_status())
    except Exception as e:
        RL.err("market_status", e, event_type="external_call"); return False
    _MKT.update(ts=time.time(), code=code)
    if code != "004" and RL.once(f"market|{code}"):
        RL.ev("decision", "market_pass", "skipped", "not_regular_session", actor="scheduler", code=code)
    return code == "004"


# ---------------------------------------------------------------- 하루 매매 (3번 execute_100day_step 미국 부분)
async def execute_us_step(client):
    live = not RUN.get("dry", True)
    if live and RUN.get("gate"):
        # 실주문 모드인데 안전장치가 막힘 → 판단·주문·일차 진행 모두 안 함 (하루 1번 알림)
        if RL.once("live_gate_blocked"):
            RL.ev("decision", "market_pass", "skipped", "live_gate_blocked", actor="scheduler", count=len(RUN["gate"]))
            send_panel("⛔ [실주문 안전장치에 걸려 오늘 주문 안 함]\n" + "\n".join("• " + g for g in RUN["gate"]),
                       [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
        return
    cfg = await sync_holdings_from_meritz(client)
    if not cfg.get("is_master_active", False):
        if RL.once("master_off|us"): RL.ev("decision", "market_pass", "skipped", "master_off", actor="scheduler", market="US")
        return
    if not await us_market_open(client): return
    await sync_fills(client)
    cfg = await ensure_cycle_fields()
    stocks = cfg.get("stocks", {})
    today_str = datetime.now(EST_TZ).strftime("%Y-%m-%d")
    alert_k = "last_fail_alert_us"
    if cfg.get(alert_k) == today_str and (time.time() - runtime_info.get("last_retry_ts", 0.0) < 900):
        RL.count("skip:fail_alert_cooldown"); return
    runtime_info["last_retry_ts"] = time.time()
    logs, completed_syms = [], []
    tp1, sr = float(cfg.get("tp1_pct", 10.0)), float(cfg.get("sr_pct", 20.0))
    pending_syms = {p.get("sym") for p in (cfg.get("pending_orders") or [])}
    n7_mults = await n7_market_multipliers(client, cfg, False)   # N7: 꺼짐이면 {} → 모든 배수 1.0
    # v1.1.0 SGOV: 회차를 먼저 판단·예약 (sgov_step 은 예외를 밖으로 내지 않음 → 적립 매수를 막지 않음)
    sg_res = await SG.sgov_step(client, _order, today_str, live)
    sgov_reserve = round(float(sg_res.get("reserve") or 0.0), 2)
    logs += sg_res.get("logs") or []

    for sym, s in list(stocks.items()):
        if s.get("currency") == "KRW": continue                       # 한국주식은 이 봇 대상 아님
        if not s.get("enabled", True): RL.count("skip:stock_disabled"); continue
        if s.get("last_exec_date") == today_str: _decide(sym, "stock_step", "skipped", "done_today", s, daily=True); continue
        ensure_stock_cycle(s)
        s_mode, s_day, s_target = s["s_mode"], int(s["s_day"]), int(s["s_target_days"])
        if s_mode == "decision":
            _decide(sym, "stock_step", "skipped", "awaiting_user_decision", s, daily=True)
            await _hold_watch(client, cfg, sym, s, tp1, today_str); continue
        if s_mode == "pause":
            s["s_day"] = s_day + 1; s["last_exec_date"] = today_str
            if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"⏸ 정지 대기({s_target}일) 완료"))
            _decide(sym, "pause_day", "ok", None, s)
            await save_merged(cfg, sym)
            await _hold_watch(client, cfg, sym, s, tp1, today_str); continue

        base_amt = float(s.get("base_amount", 40.0))
        try:
            fresh = await DcaConfigManager.load()   # 도중에 텔레그램에서 끈 전원·종목 설정을 바로 반영
            if not fresh.get("is_master_active", False): _decide(sym, "stock_step", "skipped", "master_turned_off", s); break
            if sym not in fresh.get("stocks", {}) or not fresh["stocks"][sym].get("enabled", True): _decide(sym, "stock_step", "skipped", "stock_turned_off", s); continue
            if sym in pending_syms:
                fail_reasons[sym] = "이전 주문 체결 확인 대기 중"
                _decide(sym, "stock_step", "skipped", "fill_pending", s, daily=True); continue
            price_err = None
            try: cur_p = float(await client.get_current_price(sym) or 0.0)
            except Exception as pe: cur_p, price_err = 0.0, str(pe)[:120]
            hold = await client.get_symbol_holdings(sym)
            broker_q, sellable = float(hold.get("qty") or 0.0), float(hold.get("sellable") or 0.0)
            qty, avg_p = ledger_of(s)[0], ledger_avg(s)
            if abs(broker_q - qty) > 1e-6:
                # 봇 장부와 메리츠 잔고가 다름 → 실주문이면 이 종목은 오늘 주문 안 함 (입고 전·수동 매매·체결 누락)
                why = f"장부 {qty:g}주 ≠ 메리츠 잔고 {broker_q:g}주"
                if live:
                    fail_reasons[sym] = why
                    if RL.once(f"{sym}|ledger_mismatch"):
                        _decide(sym, "stock_step", "skipped", "ledger_mismatch", s, _snap(sym, s, ledger_qty=qty, broker_qty=broker_q))
                        send_panel(f"⛔ [{sym} 오늘 주문 안 함]\n• {why}\n• 입고·수동 매매·체결 누락을 확인해 주세요. 진행 일차는 그대로입니다.",
                                   [[{"text": f"📄 {sym} 상세", "callback_data": f"detail_{sym}"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
                    continue
                if RL.once(f"{sym}|ledger_mismatch_dry"):
                    _decide(sym, "stock_step", "ok", "ledger_mismatch_dry_ignored", s, _snap(sym, s, ledger_qty=qty, broker_qty=broker_q))
                sellable = qty                                   # 모의는 장부 수량 기준으로 계속
            if qty > 0: s["has_held"] = True
            elif s.get("has_held") and qty <= 0:
                RL.ev("state_change", "stock_removed", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), why="holding_zero", audit_ref=_snap(sym, s, cur_price=cur_p, qty=qty))
                stocks.pop(sym, None); await save_merged(cfg, sym, drop=True); continue
            if qty <= 0 and int(s.get("sold_stage", 0)) != 0:
                # 3번 R1 리셋 ①: 보유 0주일 때만 익절 단계 초기화 (즉시 저장)
                RL.ev("state_change", "sold_stage_reset", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), why="holding_zero", stage_before=s.get("sold_stage"))
                s["sold_stage"] = 0; await save_merged(cfg, sym)
            halted = False
            if cur_p > 0:
                try: halted = stock_looks_halted(await client.get_stock_info(sym))
                except Exception: halted = False   # 상태 조회 실패만으로는 정지로 보지 않음
            if cur_p <= 0 or halted:
                # 가격 0·조회 실패·거래정지: 그날 매수·익절·분할매도 안 함 (일차 그대로) + 알림 하루 1번
                why = "halted" if halted else ("price_error" if price_err else "price_zero")
                why_txt = {"halted": "거래정지·상장폐지 상태로 보임", "price_error": "현재가 조회 실패", "price_zero": "현재가 0"}[why]
                fail_reasons[sym] = why_txt
                s["last_exec_date"] = today_str; await save_merged(cfg, sym)
                _decide(sym, "stock_step", "skipped", why, s)
                if RL.once(f"{sym}|guard|{why}"):
                    send_panel(f"⚠️ [{sym} 오늘 주문 안 함]\n• 사유: {why_txt}{(' (' + price_err + ')') if price_err else ''}\n"
                               f"• 오늘은 매수·익절·분할매도를 하지 않습니다. 진행 일차는 그대로 두었습니다.\n• 다음 거래일에 다시 확인합니다.",
                               [[{"text": f"📄 {sym} 상세", "callback_data": f"detail_{sym}"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
                continue
            prof_pct = ((cur_p - avg_p) / avg_p) * 100 if avg_p > 0 and cur_p > 0 else 0.0
            sold_stg = int(s.get("sold_stage", 0))
            # 3번 R1: 단계는 위로만. 이미 판 단계는 다시 팔지 않음, 여러 단계를 넘으면 가장 높은 새 단계 1회만, 3차(30%) 이상 매도 없음
            target_stg = tp_sell_stage(prof_pct, tp1, sold_stg)
            if qty > 0 and avg_p > 0 and target_stg > 0:
                sell_q = min(int_sell_qty(qty, sr), int(math.floor(sellable + 1e-9)))
                if sell_q > 0:
                    if not await stock_trade_allowed(sym): _decide(sym, "take_profit", "skipped", "trade_not_allowed", s); continue
                    aref = _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, profit_pct=prof_pct, stage=target_stg, sell_qty=sell_q)
                    _decide(sym, "take_profit", "ok", None, s, aref, stage=target_stg)
                    oid = f"tp{target_stg}_{today_str}_{sym}"
                    await _order("take_profit", sym, "sell", sell_q, oid, client, cur_p)
                    s["sold_stage"] = target_stg; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                    logs.append(f"🎯 {sym}: {target_stg}차 익절 ({prof_pct:+.2f}% / {sell_q}주 시장가)"); await save_merged(cfg, sym); continue
                _decide(sym, "take_profit", "skipped", "no_sellable_qty", s, daily=True)
            n7m = float(n7_mults.get(n7_index_of(s), 1.0)) if s_mode in ["buy_1", "buy_2"] else 1.0
            half_buy = bool(avg_p > 0 and qty > 0 and prof_pct >= 1.0)
            buy_amt_today = calc_buy_amount(base_amt, n7m, half_buy)   # 달러 부족 검사와 실제 주문이 같은 값
            if s_mode in ["buy_1", "buy_2"]:
                buy_q, new_carry = int_buy_qty(buy_amt_today, float(s.get("buy_carry") or 0.0), cur_p, SETTINGS.get("us_int_buy_mode", "carry"))
                if buy_q > 0:
                    # 달러 부족 검사는 익절 판단 뒤에 함 (달러가 없어도 익절 매도는 진행되도록)
                    usd_bal = float(await client.get_buying_power("USD") or 0.0)
                    if sgov_reserve > 0: usd_bal = usd_bal - sgov_reserve        # (ii) SGOV 몫을 먼저 떼고 남은 달러만
                    need_amt = round(buy_q * cur_p * (1 + float(SETTINGS.get("buy_cash_buffer_pct", 1.0)) / 100.0), 2)
                    if usd_bal < need_amt:
                        fail_reasons[sym] = f"달러 부족 (필요 ${need_amt:.2f} / 보유 ${usd_bal:.2f}" + (f" · SGOV 몫 ${sgov_reserve:.2f} 제외" if sgov_reserve > 0 else "") + ")"
                        if RL.once(f"{sym}|buy|usd_insufficient"):
                            _decide(sym, "buy", "skipped", "usd_insufficient", s, _snap(sym, s, usd_need=need_amt, usd_balance=usd_bal, profit_pct=prof_pct, sgov_reserve=sgov_reserve))
                        else: RL.count("skip:usd_insufficient")
                        continue
                ord_id = f"b_{today_str}_{sym}"
                try:
                    if buy_q > 0:
                        if not await stock_trade_allowed(sym): _decide(sym, "buy", "skipped", "trade_not_allowed", s); continue
                        _decide(sym, "buy", "ok", None, s, _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, profit_pct=prof_pct, buy_amount=buy_amt_today, buy_qty=buy_q, carry_before=s.get("buy_carry"), carry_after=new_carry), half=half_buy, n7_mult=n7m)
                        await _order("buy", sym, "buy", buy_q, ord_id, client, cur_p)
                        logs.append(f"🛒 {sym}: {buy_q}주 시장가 매수 (오늘 ${buy_amt_today:.2f}{'' if not s.get('buy_carry') else ' + 이월'} · {s_day+1}/{s_target}일차)" + (f" · 지수 {n7m:.1f}배" if n7m != 1.0 else ""))
                    else:
                        _decide(sym, "buy", "ok", "carry_no_order", s, _snap(sym, s, cur_price=cur_p, buy_amount=buy_amt_today, carry_after=new_carry))
                        logs.append(f"↪️ {sym}: 1주 가격(${cur_p:.2f})보다 적어 주문 없이 이월 ${new_carry:.2f} ({s_day+1}/{s_target}일차)")
                except Exception as oe:
                    if _rejected(oe):
                        if isinstance(oe, (WarnNeeded, GateBlocked)):   # 사람이 봐야 하는 거절 → 오늘은 다시 시도하지 않음 (일차 그대로)
                            s["last_exec_date"] = today_str; await save_merged(cfg, sym)
                            send_panel(f"⛔ [{sym} 매수 안 함]\n• {'증권사 경고(자동 확인 안 함)' if isinstance(oe, WarnNeeded) else '실주문 안전장치'}: {str(oe)[:160]}\n• 진행 일차는 그대로입니다.", [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
                            continue
                        raise   # 증권사가 거절한 주문(체결 안 됨) → 3번처럼 실패 알림 후 재시도
                    # 응답이 끊긴 주문은 체결됐을 수 있으므로 오늘은 다시 주문하지 않음 (일차는 올리지 않음)
                    s["last_exec_date"] = today_str; fail_reasons.pop(sym, None); await save_merged(cfg, sym)
                    RL.ev("state_change", "no_reorder_today", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), why="order_no_response", day_unchanged=s_day)
                    send_panel(f"⚠️ [{sym} 매수 주문 응답 없음]\n• 체결됐을 수 있어 오늘은 다시 주문하지 않습니다.\n• 메리츠 앱에서 체결 여부를 확인해 주세요. (일차·장부는 그대로 — 체결됐다면 관제탑에서 일차 보정, 장부는 Muse 확인)\n• 사유: {str(oe)[:120]}", [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
                    continue
                s["buy_carry"] = new_carry
                s["s_day"] = s_day + 1; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"🛒 분할매수({s_target}일) 완료"))
                RL.ev("state_change", "step_day", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), day_before=s_day, day_after=s["s_day"], mode_after=s["s_mode"])
                await save_merged(cfg, sym)
            elif s_mode == "sell" and qty > 0:
                rem_days = max(1, s_target - s_day)
                sq = min(int_split_sell_qty(qty, rem_days), int(math.floor(sellable + 1e-9)))
                if sq <= 0: _decide(sym, "split_sell", "skipped", "no_sellable_qty", s, daily=True); continue
                if not await stock_trade_allowed(sym): _decide(sym, "split_sell", "skipped", "trade_not_allowed", s); continue
                _decide(sym, "split_sell", "ok", None, s, _snap(sym, s, cur_price=cur_p, avg_price=avg_p, qty=qty, sell_qty=sq, remain_days=rem_days))
                oid = f"s_{today_str}_{sym}"
                await _order("split_sell", sym, "sell", sq, oid, client, cur_p)
                s["s_day"] = s_day + 1; s["last_exec_date"] = today_str; fail_reasons.pop(sym, None)
                RL.ev("state_change", "step_day", "ok", None, actor="scheduler", sym_ref=RL.ref(sym), day_before=s_day, day_after=s["s_day"], mode_after=s["s_mode"] if s["s_day"] < s_target else "decision")
                logs.append(f"📤 {sym}: 분할매도 ({sq}주 / {s['s_day']}/{s_target}일차)")
                if s["s_day"] >= s_target: s["s_mode"] = "decision"; completed_syms.append((sym, f"📤 분할매도({s_target}일) 완료"))
                await save_merged(cfg, sym)
            elif s_mode == "sell": _decide(sym, "split_sell", "skipped", "no_holding", s, daily=True)
        except Exception as e:
            fail_reasons[sym] = str(e)[:200]
            RL.err("stock_step", e, event_type="decision", sym_ref=RL.ref(sym), mode=s.get("s_mode"))
    if logs:
        send_panel("✅ [금일 정기 매매 " + ("계획(모의)" if RUN.get("dry", True) else "주문 접수") + " 보고]\n" + "\n".join(logs),
                   [[{"text": "📋 보유종목 확인", "callback_data": "stock_list"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
        _hub_alert(HUB_NAME, "info", "\n".join(logs))
    for c_sym, c_title in completed_syms:
        t, kb = await build_stock_detail_view(client, c_sym)
        send_panel(f"🎉 [{c_sym} {c_title} 및 자동 정지!]\n아래에서 다음 단계를 선택해 주세요!\n\n" + t, kb)
    await sync_fills(client)   # 모의 체결·즉시 체결은 바로 장부에


async def check_missed_trades_alert(client):
    cfg = await ensure_cycle_fields()
    if not cfg.get("is_master_active", False): return
    today_str = datetime.now(EST_TZ).strftime("%Y-%m-%d")
    alert_key = "last_fail_alert_us"
    if cfg.get(alert_key) == today_str: return
    if _MKT["code"] and _MKT["code"] != "004": return            # 휴장일에는 미진행 알림 없음
    missed = [f"• {sym}: {fail_reasons.get(sym, '잔고/거래시간 확인 필요')}" for sym, s in cfg.get("stocks", {}).items() if s.get("enabled", True) and s.get("currency") != "KRW" and s.get("s_mode") not in ["decision", "pause"] and s.get("last_exec_date") != today_str]
    if missed:
        RL.ev("decision", "missed_trade_alert", "ok", None, actor="scheduler", market="US", count=len(missed))
        cfg[alert_key] = today_str; await DcaConfigManager.save(cfg)
        txt = "🚨 [매매 미진행/실패 알람 - 🇺🇸 미국장]\n\n" + "\n".join(missed)
        send_panel(txt, [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
        _hub_alert(HUB_NAME, "critical", txt)


# ---------------------------------------------------------------- 텔레그램 버튼·메시지 (3번과 같음 + ➕ 종목 추가)
async def add_symbol_from_text(client, text):
    sym = text.strip().upper()
    if not is_us_symbol(sym):
        return None, "❌ 미국 티커(영문)만 넣어 주세요. 예: NKE, QLD (한국주식은 이 봇에서 안 함)"
    cfg = await DcaConfigManager.load()
    if sym == SG.sgov_symbol(cfg):
        return None, f"ℹ️ {sym} 는 일반 종목이 아니라 🪙 SGOV 회차 적립 메뉴에서 관리합니다."
    if sym in cfg.get("stocks", {}):
        return sym, f"ℹ️ {sym} 는 이미 목록에 있습니다."
    try:
        info = await client.get_stock_info(sym)
    except Exception as e:
        return None, f"❌ {sym} 를 메리츠에서 찾지 못했습니다. ({str(e)[:80]})"
    q, bavg = 0.0, 0.0
    try:
        h = await client.get_symbol_holdings(sym); q, bavg = float(h.get("qty") or 0), float(h.get("broker_avg") or 0)
    except Exception: pass
    fresh = await DcaConfigManager.load()
    fresh.setdefault("stocks", {})[sym] = new_stock_entry(sym, info.get("name", sym), q, q * bavg, "broker_avg" if q > 0 else "new",
                                                         tp1=float(fresh.get("tp1_pct", 10.0)), sr=float(fresh.get("sr_pct", 20.0)))
    await DcaConfigManager.save(fresh)
    RL.ev("state_change", "stock_added_by_user", "ok", None, actor="user", sym_ref=RL.ref(sym), enabled=False, held=q > 0)
    return sym, f"✅ {info.get('name', sym)} ({sym}) 추가 완료 — ⏸ 중지 상태로 등록했습니다. 기준금액 확인 후 ▶️ 매매 시작을 눌러 주세요." + (
        f"\n⚠️ 메리츠에 이미 {q:g}주가 있어 증권사 평단으로 장부를 시작했습니다." if q > 0 else "")


def _live_chat_id() -> str:
    """v1.1.1: t_core.CHAT_ID (load_telegram 이 채운 값). `from t_core import *` 로 받은 CHAT_ID 는 import 때의 "" 로 남음"""
    return str(t_core.CHAT_ID or "").strip()


def _other_chat_diag(cb: dict, m, got: str, want: str):
    """v1.1.1 진단: 버린 콜백의 받은 채팅방 ID·data 를 서버 로그에만 남김 (어디에도 보내지 않음, 답장·answerCallbackQuery 없음).
    원값은 감사 로그(audit-*.jsonl, 권한 600)에만 · 일반 로그/저널에는 참조값·이유만 (replay_log 규칙: 일반 로그에 채팅 식별자 금지)."""
    RL.count("tg_other_chat")   # 10분 요약 카운터는 그대로
    reason = "no_message" if m is None else ("chat_id_not_loaded" if not want else "chat_mismatch")
    data = str(cb.get("data", ""))
    ctype = str(((m or {}).get("chat") or {}).get("type", "")) or None
    aref = RL.audit("tg_other_chat", reason=reason, received_chat_id=got or None, received_chat_type=ctype,
                    callback_data=data[:64], has_inline_message_id=bool(cb.get("inline_message_id")))
    RL.ev("user_event", "tg_other_chat", "skipped", reason, actor="user", level="WARN", button=RL.button(data),
          chat_type=ctype, received_ref=RL.ref(got), configured=bool(want), has_message=m is not None, audit_ref=aref)


SEED_FIELDS = {
    "NKE": ("NKE 1회 금액", "stock"), "QLD": ("QLD 1회 금액", "stock"),
    "target_usd_total": ("SGOV 총 목표", "float"),
    "tranche_usd": ("SGOV 회차 금액", "float"),
    "first_tranche_usd": ("SGOV 1회차 금액", "float"),
    "tranches_total": ("SGOV 총 회차 수", "int"),
    "interval_days": ("SGOV 회차 간격(일)", "int"),
}

# 자동환전 결과 코드 → 사용자에게 보이는 한글 문구 (Muse 직접 수정, 2026-11-13)
# maybe_auto_fx의 반환값은 내부 코드라서 그대로 보여주면 알아보기 어렵다.
FX_RESULT_KO = {
    "ok": "환전 완료",
    "outside_hours": "낮 시간(09:00–15:30 KST)이 아니어서 환전하지 않았습니다",
    "us_holiday": "미국 휴장일이라 환전하지 않았습니다",
    "disabled": "자동환전이 꺼져 있습니다",
    "key_bad": "메리츠 키 확인이 필요합니다",
    "gate_blocked": "실주문 안전장치로 환전하지 않았습니다",
    "already_done": "오늘 이미 환전했습니다",
    "master_off": "전체 전원이 꺼져 있습니다",
    "no_price": "환율 시세가 없어 환전하지 않았습니다",
    "no_gap": "환전할 금액이 없습니다",
    "rate_error": "환율 조회 오류로 환전하지 않았습니다",
    "krw_short": "원화 잔고가 부족합니다",
    "rate_changed": "환율이 1% 이상 변해 환전을 중단했습니다",
    "dry_run": "모의 모드라 실제 환전하지 않았습니다",
    "stop": "환전을 중단했습니다",
    "uncertain": "환전 결과를 확인할 수 없습니다",
    "error": "환전 오류가 발생했습니다",
}

def seed_group(key):
    # 시드 항목이 어느 그룹인지: 적립(NKE/QLD) / SGOV(나머지)
    return "stock" if SEED_FIELDS[key][1] == "stock" else "sgov"


def build_seed_menu(cfg):
    # v1.2.2: 시드 설정을 2개 메뉴로 나눔 (적립 / SGOV). 한 번에 7개가 보여서 섞이지 않게.
    sg = SG.sgov_block(cfg)
    stocks = cfg.get("stocks", {})
    lines = ["⚙️ [시드 설정 — 입력만으로 주문·환전 없음]",
             "• 적립: " + " · ".join(f"{sym} ${float(stocks[sym].get('base_amount') or 0):,.2f}/회" for sym in ("NKE", "QLD") if sym in stocks),
             f"• SGOV: 총 ${float(sg.get('target_usd_total') or 0):,.2f} · {int(sg.get('tranches_total') or 0)}회 · 회차 ${float(sg.get('tranche_usd') or 0):,.2f}"]
    kb = [[{"text": "📈 적립 시드", "callback_data": "funds_seed_stock"}],
          [{"text": "🪙 SGOV 시드", "callback_data": "funds_seed_sgov"}],
          [{"text": "🔙 자금", "callback_data": "funds"}]]
    return "\n".join(lines), kb


def build_seed_group_menu(cfg, group):
    sg = SG.sgov_block(cfg)
    stocks = cfg.get("stocks", {})
    if group == "stock":
        title = "📈 [적립 시드 — 입력만으로 주문·환전 없음]"
        keys = ["NKE", "QLD"]
    else:
        title = "🪙 [SGOV 시드 — 입력만으로 주문·환전 없음]"
        keys = ["target_usd_total", "tranche_usd", "first_tranche_usd", "tranches_total", "interval_days"]
    lines = [title]
    kb = []
    for key in keys:
        label, kind = SEED_FIELDS[key]
        if kind == "stock" and key not in stocks: continue
        val = stocks[key].get("base_amount") if kind == "stock" else sg.get(key)
        lines.append(f"• {label}: {val}")
        kb.append([{"text": label, "callback_data": f"funds_seed_{key}"}])
    kb.append([{"text": "🔙 시드 설정", "callback_data": "funds_seed"}])
    return "\n".join(lines), kb

def parse_seed_value(key, raw):
    if not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)", raw.strip()):
        raise ValueError("양수 숫자만 입력하세요")
    val = Decimal(raw.strip())
    if not val.is_finite() or val <= 0: raise ValueError("0보다 커야 합니다")
    if SEED_FIELDS[key][1] == "int":
        if val != val.to_integral_value(): raise ValueError("정수를 입력하세요")
        return int(val)
    return float(val)

def validate_seed_change(sg):
    # 기존 sgov_problems는 enabled=false에서 검사를 생략하므로, 시드 수정에는 강제 검사.
    proposed = copy.deepcopy(sg)
    proposed["enabled"] = True
    problems = SG.sgov_problems(proposed)
    principal = float((sg.get("ledger") or {}).get("principal") or 0)
    total = float(sg.get("target_usd_total") or 0)
    if total < principal: problems.append("새 총 목표가 이미 매수한 장부 원금보다 작습니다")
    done = int(sg.get("tranches_done") or 0)
    n = int(sg.get("tranches_total") or 0)
    if n < done: problems.append("총 회차가 완료 회차보다 작습니다")
    # 기존 회차의 원금은 그대로 유지하고, 남은 회차만 계산.
    remaining = max(0, n - done)
    future = remaining * float(sg.get("tranche_usd") or 0)
    if done == 0 and remaining > 0:
        future += float(sg.get("first_tranche_usd") or 0) - float(sg.get("tranche_usd") or 0)
    if principal + future > total * 1.01:
        problems.append("이미 산 원금 + 남은 회차 합계가 총 목표의 101%를 초과합니다")
    if principal + future < total * 0.99:
        problems.append("남은 회차로 남은 목표를 채울 수 없습니다")
    return problems

async def save_seed_value(cfg, key, value):
    latest = await DcaConfigManager.load()
    if key in ("NKE", "QLD"):
        if key not in latest.get("stocks", {}): raise ValueError("해당 종목이 없습니다")
        latest["stocks"][key]["base_amount"] = value
    else:
        sg = SG.sgov_block(latest)
        candidate = copy.deepcopy(sg)
        candidate[key] = value
        problems = validate_seed_change(candidate)
        if problems: raise ValueError("; ".join(problems))
        # 기존 매수 회차·원금·next_due_date는 변경하지 않는다.
        latest["sgov"] = candidate
    await DcaConfigManager.save(latest)

async def show_fx_confirmation(client, msg_id):
    cfg = await DcaConfigManager.load()
    try:
        need = await dca_fx_plan(client, cfg)
        usd = await asyncio.to_thread(client.api.usd_estimated)
        amount = fx_auto_amount(Decimal(str(need)) - Decimal(str(usd)))
    except Exception as e:
        send_panel(f"환전 계획 확인 실패: {type(e).__name__}", [[{"text":"자금", "callback_data":"funds"}]], msg_id)
        return
    if amount is None:
        send_panel("환전할 금액 없음", [[{"text":"자금", "callback_data":"funds"}]], msg_id)
        return
    send_panel(f"이 금액만큼 자동환전할까요? ~${amount:,.2f} · 적립 + SGOV 합산분\n기존 낮 자동환전 안전장치 및 시간 제한 적용",
               [[{"text":"실행", "callback_data":"funds_fx_confirm"}, {"text":"취소", "callback_data":"funds"}]], msg_id)

async def handle_callback(cb: dict, client):
    _m = cb.get("message") if isinstance(cb.get("message"), dict) else None   # 인라인 메시지 콜백 등은 message 가 없음
    got, want = str(((_m or {}).get("chat") or {}).get("id", "")).strip(), _live_chat_id()
    if not want or got != want: _other_chat_diag(cb, _m, got, want); return
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
        RL.ev("state_change", "stock_enabled", "ok", None, actor="user", sym_ref=RL.ref(sym), before=before, after=turn_on, master_on=latest.get("is_master_active", False))
        text, kb = await build_stock_detail_view(client, sym)
        notice = ("▶️ 해당 종목 자동매매를 시작했습니다."
                  if turn_on else "⏸ 해당 종목의 신규 자동주문을 중지했습니다.")
        if turn_on and not latest.get("is_master_active", False):
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
        send_panel("🔎 보유종목 이름 또는 티커를 입력하세요. (예: NKE, QLD)\n검색은 전체 상태에서 진행합니다.",
                   [[{"text": "🔙 목록으로", "callback_data": stock_list_callback()}]], msg_id)
        return
    if data == "add_symbol":
        wait_state["mode"] = "add_sym"
        send_panel("➕ [새 종목 추가 — 미국주식만]\n• 모아갈 미국 티커(영문)를 입력해 주세요. 예: NKE, QLD, SPY\n• 추가하면 ⏸ 중지 상태로 등록됩니다 (기준금액 $40).",
                   [[{"text": "🔙 취소", "callback_data": "panel"}]], msg_id)
        return
    if data == "sgov" or data.startswith(("sgovx_", "sgovmode_", "sgov_")):
        await handle_sgov_callback(data, msg_id); return
    if data in ("panel_view_now", "panel_view_done"):
        PANEL_VIEW_CONTEXT["mode"] = "done" if data.endswith("done") else "now"
        send_panel(*(await build_panel_view(client)), msg_id); send_bottom_menu()
    elif data == "funds": send_panel(*(await build_funds_view(client)), msg_id)
    elif data == "funds_seed": send_panel(*build_seed_menu(await DcaConfigManager.load()), msg_id)
    elif data == "funds_seed_stock": send_panel(*build_seed_group_menu(await DcaConfigManager.load(), "stock"), msg_id)
    elif data == "funds_seed_sgov": send_panel(*build_seed_group_menu(await DcaConfigManager.load(), "sgov"), msg_id)
    elif data.startswith("funds_seed_"):
        key = data[len("funds_seed_"):]
        if key in SEED_FIELDS:
            wait_state.update(mode="funds_seed", sym=key)
            send_panel(f"💰 {SEED_FIELDS[key][0]} 새 값을 숫자로 입력하세요. (주문·환전 없음)",
                       [[{"text": "취소", "callback_data": f"funds_seed_{seed_group(key)}"}]], msg_id)
    elif data == "funds_fx":
        await show_fx_confirmation(client, msg_id)
    elif data == "funds_fx_confirm":
        result = await maybe_auto_fx(client)
        send_panel(*(await build_funds_view(client, f"자동환전 결과: {FX_RESULT_KO.get(result, result)}")), msg_id)
    elif data == "panel": send_panel(*(await build_panel_view(client)), msg_id); send_bottom_menu()
    elif data == "stock_list": send_panel(*(await build_stock_list_view(client, STOCK_LIST_CONTEXT["page"])), msg_id)
    elif data.startswith("slist_"): send_panel(*(await build_stock_list_view(client, int(data.split("_")[1]))), msg_id)
    elif data.startswith("detail_"): send_panel(*(await build_stock_detail_view(client, data.split("_", 1)[1])), msg_id)
    elif data.startswith("setday_"):
        sym = data.split("_", 1)[1]; wait_state["mode"], wait_state["sym"] = "day_sym", sym
        send_panel(f"🔢 [{sym}] 실제 매수 진행 일수(1~100)를 숫자로 입력해 주세요.\n• 0 입력 = 새 1차 매수를 처음부터 시작 (익절 단계도 0으로 초기화)", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
    elif data.startswith("setamt_"):
        sym = data.split("_", 1)[1]; wait_state["mode"], wait_state["sym"] = "amt_sym", sym
        send_panel(f"💰 [{sym}] 1회 기준 매수금액(달러)을 입력해 주세요.\n• 예: 40", [[{"text": "🔙 취소", "callback_data": f"detail_{sym}"}]], msg_id)
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
        cfg["is_master_active"] = not cfg.get("is_master_active", False); await DcaConfigManager.save(cfg)
        RL.ev("state_change", "master_power", "ok", None, actor="user", before=not cfg["is_master_active"], after=cfg["is_master_active"])
        send_panel(*(await build_panel_view(client)), msg_id)
    elif data == "toggle_n7":
        latest = await DcaConfigManager.load(); before = bool(latest.get("n7_enabled", False))
        latest["n7_enabled"] = not before; await DcaConfigManager.save(latest)
        RL.ev("state_change", "n7_enabled", "ok", None, actor="user", before=before, after=latest["n7_enabled"])
        # v1.2.3: 지수 배수 버튼이 주식 패널로 옮겨서, 바꾼 뒤에도 주식 패널로 돌아간다.
        send_panel(*(await build_stock_list_view(client, STOCK_LIST_CONTEXT["page"])), msg_id)
    elif data.startswith("idx_"):
        sym = data.split("_", 1)[1].strip().upper()
        latest = await DcaConfigManager.load(); stocks = latest.get("stocks", {})
        if sym in stocks:
            cur = n7_index_of(stocks[sym]); a, b = N7_CHOICES["US"]
            stocks[sym]["index_ref"] = b if cur == a else a; await DcaConfigManager.save(latest)
            RL.ev("state_change", "n7_index_ref", "ok", None, actor="user", sym_ref=RL.ref(sym), before=cur, after=stocks[sym]["index_ref"])
        send_panel(*(await build_stock_detail_view(client, sym)), msg_id)
    elif data == "ask_tp": wait_state["mode"] = "tp"; send_panel("🎯 [1차익절% 매도비율%] 입력 (예: 10 20)", [[{"text": "🔙 주식 목록", "callback_data": "stock_list"}]], msg_id)

async def handle_sgov_callback(data, msg_id):
    """SGOV 메뉴 버튼. 설정만 바꾸고 화면을 다시 보여 줌 — 어떤 버튼도 주문·환전을 하지 않음 (다음 회차 판단부터 적용)"""
    notice = ""
    if data.startswith("sgovx_"):
        try: v = float(data.split("_", 1)[1])
        except ValueError: v = None
        if v in SG.SKIP_X_CHOICES:
            await SG.sgov_menu_set("skip_jump_pct", v)
            notice = f"✅ 7일 상승 건너뜀 기준을 {v:g}% 로 바꿨습니다. 다음 회차 판단부터 적용 (지금 매수 없음)."
    elif data.startswith("sgovmode_"):
        m = data.split("_", 1)[1]
        if m in SG.CAP_MODES:
            await SG.sgov_menu_set("skip_cap_mode", m)
            notice = f"✅ 연속 건너뜀 규칙: {SG.CAP_MODES[m]} — 다음 회차 판단부터 적용 (지금 매수 없음)."
    elif data == "sgov_review_ok":
        await SG.sgov_menu_set("review_hold", False)
        notice = "✅ 재점검 완료 — 다음 예정일에 다시 판단합니다 (지금 매수 없음)."
    elif data == "sgov_toggle":
        latest = await DcaConfigManager.load(); on = not bool(SG.sgov_block(latest).get("enabled"))
        await SG.sgov_menu_set("enabled", on)
        notice = "▶️ SGOV 회차 적립을 켰습니다. 예정일이 되면 판단합니다 (지금 매수 없음)." if on else "⏸ SGOV 회차 적립을 껐습니다."
    elif data == "sgov_dist":
        wait_state["mode"] = "sgov_dist"
        send_panel("💵 [SGOV 분배금 기록]\n• 들어온 분배금(달러)을 숫자로 입력해 주세요. 예: 12.34\n• SGOV 장부·대기 달러에만 더하고 다음 회차에 재투자합니다 (NKE/QLD 와 따로).",
                   [[{"text": "🔙 취소", "callback_data": "sgov"}]], msg_id)
        return
    send_panel(*SG.build_sgov_view(await DcaConfigManager.load(), notice), msg_id)


async def handle_message(msg: dict, client):
    _want = _live_chat_id()
    if not _want or str(msg.get("chat", {}).get("id", "")).strip() != _want: return   # v1.1.1: live CHAT_ID (동작은 그대로 — 조용히 무시)
    text = msg.get("text", "").strip()
    if not text: return
    menu_words = {"메뉴", "관제탑", "취소", "종목", "주식", "SGOV", "자금", "보유종목", "종목 추가", "설정"}
    _kind = "command" if text.startswith("/") else (wait_state.get("mode") or ("menu_word" if text in menu_words else "search"))
    RL.ev("user_event", "tg_message", "ok", None, actor="user", input_kind=_kind, text_len=len(text))
    cfg = await ensure_cycle_fields()
    # 입력 대기 중에는 메뉴 텍스트도 입력으로 처리. 취소만 대기 해제.
    if text == "취소":
        wait_state.update(mode=None, sym=None)
        send_panel(*(await build_panel_view(client))); send_bottom_menu()
        return
    if wait_state.get("mode") is None and (text.startswith("/") or text in menu_words):
        if text in ("주식", "보유종목", "종목"):
            send_panel(*(await build_stock_list_view(client, 0)))
        elif text == "SGOV": send_panel(*SG.build_sgov_view(cfg))
        elif text in ("자금", "설정"): send_panel(*(await build_funds_view(client)))
        elif text == "종목 추가":
            wait_state["mode"] = "add_sym"
            send_panel("➕ 미국 티커를 입력하세요 (예: NKE)", [[{"text":"취소", "callback_data":"panel"}]])
        else:
            send_panel(*(await build_panel_view(client))); send_bottom_menu()
        return
    stocks = cfg.get("stocks", {}); m, sym = wait_state.get("mode"), wait_state.get("sym")
    if m == "funds_seed":
        key = wait_state.get("sym")
        if key not in SEED_FIELDS: return
        try:
            value = parse_seed_value(key, text)
            await save_seed_value(cfg, key, value)
        except (ValueError, TypeError) as e:
            send_panel(f"❌ 저장 거부: {e}", [[{"text": "시드 설정", "callback_data": f"funds_seed_{seed_group(key)}"}]])
            return
        wait_state.update(mode=None, sym=None)
        cfg2 = await DcaConfigManager.load()
        menu_text, kb = build_seed_group_menu(cfg2, seed_group(key))
        send_panel("✅ 시드 변경 저장 (주문·환전 없음)\n\n" + menu_text, kb)
        return
    if m == "sgov_dist":
        wait_state["mode"] = None
        try:
            val = round(float("".join(ch for ch in text if ch.isdigit() or ch == ".")), 4)
            if val <= 0: raise ValueError
        except Exception:
            RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode="sgov_dist")
            send_panel("❌ 숫자(달러)를 입력해 주세요. 예: 12.34", [[{"text": "💵 다시 입력", "callback_data": "sgov_dist"}, {"text": "🪙 SGOV", "callback_data": "sgov"}]])
            return
        send_panel(*SG.build_sgov_view(await SG.sgov_add_distribution(val), f"✅ 분배금 ${val:.2f} 기록 — SGOV 대기 달러로 다음 회차에 재투자합니다."))
        return
    if m == "stock_search":
        wait_state["mode"] = None
        send_panel(*(await build_stock_list_view(client, 0, "all", "all", text)))
        return
    if m == "add_sym":
        wait_state["mode"] = None
        new_sym, note = await add_symbol_from_text(client, text)
        if new_sym:
            t, kb = await build_stock_detail_view(client, new_sym); send_panel(note + "\n\n" + t, kb)
        else:
            send_panel(note, [[{"text": "➕ 다시 입력", "callback_data": "add_symbol"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
        return
    if m == "day_sym" and sym in stocks:
        try:
            d = max(0, min(100, int("".join(ch for ch in text if ch.isdigit()))))
            RL.ev("state_change", "step_day_manual", "ok", None, actor="user", sym_ref=RL.ref(sym), day_before=stocks[sym].get("s_day"), day_after=d)
            stocks[sym]["s_day"] = d; stocks[sym]["day_set"] = True
            stocks[sym]["s_mode"] = "decision" if d >= int(stocks[sym].get("s_target_days", 100)) else "buy_1"
            if d == 0 and int(stocks[sym].get("sold_stage", 0)) != 0:
                # 3번 R1 리셋 ②: 진행일수 0 입력 = 새 1차 매수를 명시적으로 시작 → 익절 단계 초기화
                RL.ev("state_change", "sold_stage_reset", "ok", None, actor="user", sym_ref=RL.ref(sym), why="new_cycle_day0", stage_before=stocks[sym].get("sold_stage"))
                stocks[sym]["sold_stage"] = 0
            if d == 0: stocks[sym]["buy_carry"] = 0.0
            await DcaConfigManager.save(cfg); wait_state["mode"] = None
            t, kb = await build_stock_detail_view(client, sym); send_panel(f"✅ [{sym}] 진행 일수가 {d}일차로 반영되었습니다!\n\n" + t, kb)
        except: RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode="day_sym"); send_panel("❌ 숫자만 입력해 주세요.", [[{"text": "🔙 돌아가기", "callback_data": f"detail_{sym}"}]])
        return
    if m == "amt_sym" and sym in stocks:
        try:
            val = float("".join(ch for ch in text if ch.isdigit() or ch == "."))
            if val <= 0: raise ValueError
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
            stocks[sym]["s_day"], stocks[sym]["s_target_days"], stocks[sym]["day_set"] = 0, days, True
            stocks[sym]["s_mode"] = "pause" if m == "next_pause" else ("sell" if m == "next_sell" else "buy_2")
            stocks[sym]["buy_carry"] = 0.0
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
            # v1.2.3: 익절/매도비율 버튼이 주식 패널로 옮겨서, 저장 뒤에도 주식 패널로 돌아간다.
            await DcaConfigManager.save(cfg); wait_state["mode"] = None; send_panel(*(await build_stock_list_view(client, STOCK_LIST_CONTEXT["page"])))
        except: RL.ev("user_event", "bad_input", "failed", "not_a_number", actor="user", wait_mode="tp"); send_panel("❌ 예: 10 20", [[{"text": "🔙 주식 목록", "callback_data": "stock_list"}]])
        return
    # 설정값 입력 처리를 마친 일반 메시지는 보유종목 검색으로 처리.
    matches = select_stock_items(stocks, query=text)
    exact = [sym for sym, info in matches if text.casefold() in
             (sym.casefold(), str(info.get("name", sym)).casefold())]
    if len(exact) == 1:
        send_panel(*(await build_stock_detail_view(client, exact[0])))
    else:
        send_panel(*(await build_stock_list_view(client, 0, "all", "all", text)))


# ---------------------------------------------------------------- 반복 (폴링·스케줄러)
def poll_blocked() -> bool:
    """같은 텔레그램 토큰을 쓰는 toss_dca 가 살아 있으면 True (60초 캐시). systemctl 이 없으면 막지 않음"""
    if time.time() - _POLL["ts"] < 60: return _POLL["blocked"]
    unit = str(SETTINGS.get("poll_block_service") or "").strip()
    blocked = False
    if unit:
        try: blocked = subprocess.run(["systemctl", "is-active", "--quiet", unit], timeout=5).returncode == 0
        except Exception: blocked = False
    if blocked != _POLL["blocked"] or _POLL["ts"] == 0.0:
        RL.ev("state_change", "tg_polling", "skipped" if blocked else "ok", "same_token_service_active" if blocked else None, unit=unit)
    _POLL.update(ts=time.time(), blocked=blocked)
    return blocked

async def polling_loop(client):
    offset, hooked = None, False
    while True:
        try:
            if not t_core.TG_TOKEN or poll_blocked():
                await asyncio.sleep(30); continue
            if not hooked: tg_api("deleteWebhook", {"drop_pending_updates": False}); hooked = True
            res = await asyncio.to_thread(requests.get, f"https://api.telegram.org/bot{t_core.TG_TOKEN}/getUpdates", params={"timeout": 20, "offset": offset} if offset else {"timeout": 20}, timeout=25)
            if res.status_code == 200:
                RL.count("tg_poll_ok")
                for upd in res.json().get("result", []):
                    offset = upd["update_id"] + 1
                    RL.new_cid("tg", upd["update_id"])
                    try:
                        if "callback_query" in upd: await handle_callback(upd["callback_query"], client)
                        elif "message" in upd: await handle_message(upd["message"], client)
                    except Exception as he:
                        RL.err("tg_update_handle", he, event_type="user_event"); he._rl_logged = True; raise
                    finally: RL.set_cid("")
            else:
                RL.err("tg_poll", RuntimeError(f"HTTP {res.status_code}"), reason=f"tg_http_{res.status_code}")
                await asyncio.sleep(5)   # 토큰 충돌(409)·인증 오류 시 과다 재접속 방지
        except Exception as pe:
            if not getattr(pe, "_rl_logged", False): RL.err("tg_poll", pe)
            await asyncio.sleep(3)


# FX: only the daytime scheduler calls this; no new timer or US market-status gate.
FX_KRW_SHORT_WORDS = ("부족", "가능금액", "가능 금액", "예수금", "잔고", "잔액")
FX_KST = ZoneInfo("Asia/Seoul")

def fx_auto_amount(gap):
    g = Decimal(str(gap))
    if not g.is_finite() or g <= 0: return None
    if g < 10: return Decimal(100)
    return (g / 10).quantize(Decimal(1), rounding=ROUND_CEILING) * 10

class FxNoPrice(Exception):
    """낮 환전 계획: 라이브 시세·전일 종가 모두 없음 → 그날 환전 안 함 (no_price 기록). 2026-11-13 추가"""

async def dca_fx_plan(client, cfg):
    """Same buy-quantity and 1% cash buffer as execute_us_step; no orders.
    참고가: 라이브 시세 > 0 이면 그대로, 아니면 전일 종가 (get_reference_price, 낮 환전 규모 계산 전용)."""
    stocks = cfg.get("stocks") or {}
    pending = {p.get("sym") for p in (cfg.get("pending_orders") or [])}
    n7 = await n7_market_multipliers(client, cfg, False)
    total = 0.0
    for sym, s in stocks.items():
        if not s.get("enabled", True) or sym in pending or s.get("currency") == "KRW": continue
        if s.get("s_mode", "buy_1") not in ("buy_1", "buy_2"): continue
        if s.get("last_exec_date") == datetime.now(EST_TZ).strftime("%Y-%m-%d"): continue
        p, _src = await client.get_reference_price(sym)
        p = float(p or 0)
        if p <= 0: raise FxNoPrice(sym)
        qty, _ = ledger_of(s)
        avg = ledger_avg(s)
        half = avg > 0 and qty > 0 and (p - avg) / avg * 100 >= 1.0
        mult = float(n7.get(n7_index_of(s), 1.0))
        budget = calc_buy_amount(float(s.get("base_amount", 40)), mult, half)
        q, _ = int_buy_qty(budget, float(s.get("buy_carry") or 0), p, SETTINGS.get("us_int_buy_mode", "carry"))
        total += round(q * p * (1 + float(SETTINGS.get("buy_cash_buffer_pct", 1.0))/100), 2)
    # v1.1.0: 오늘 밤 SGOV 회차(관문 통과 시) 몫도 아침 환전에 포함 (실패하면 0 → 적립 몫 환전은 그대로)
    total += await SG.sgov_fx_need(client, cfg, datetime.now(FX_KST).strftime("%Y-%m-%d"))
    return round(total, 2)

def _fx_record_path(day):
    return Path(SETTINGS["state_dir"]) / ("auto_fx_" + day + ".json")

def _fx_mark(day, result, detail=""):
    p = _fx_record_path(day)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f:
        json.dump({"date_kst":day,"result":result,"detail":detail},f,ensure_ascii=False)

async def maybe_auto_fx(client, now=None):
    """Daytime-only FX decision. Dry-run NEVER calls fx_exchange."""
    now = (now or datetime.now(FX_KST)).astimezone(FX_KST)
    day = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H:%M")
    if now.weekday() >= 5 or not ("09:00" <= hm <= "15:30"): return "outside_hours"
    if not is_trading_day(now.date()):
        RL.ev("decision", "auto_fx", "skipped", "us_holiday", actor="scheduler")
        return "us_holiday"
    if not SETTINGS.get("enabled") or not SETTINGS.get("auto_fx",{}).get("on",False): return "disabled"
    if not RUN.get("key_ok"): return "key_bad"
    if not RUN.get("dry") and live_gate(): return "gate_blocked"
    if _fx_record_path(day).exists(): return "already_done"
    cfg = await DcaConfigManager.load()
    if not cfg.get("is_master_active",False): return "master_off"
    try:
        try:
            need = await dca_fx_plan(client,cfg)
        except FxNoPrice as e:
            _fx_mark(day,"no_price",str(e))
            RL.ev("decision","auto_fx","skipped","no_price",actor="scheduler",level="WARN",symbol=str(e))
            return "no_price"
        usd = Decimal(str(await asyncio.to_thread(client.api.usd_estimated)))
        amount = fx_auto_amount(Decimal(str(need))-usd)
        if amount is None:
            RL.ev("decision","auto_fx","skipped","no_gap",actor="scheduler",need_usd=need)
            return "no_gap"
        r1 = await asyncio.to_thread(client.api.fx_applied_rate)
        rate1 = Decimal(str(r1["rate"]))
        if not rate1.is_finite() or rate1 <= 0: return "rate_error"
        try: krw = Decimal(str(await asyncio.to_thread(client.api.krw_cash)))
        except Exception: krw = None
        krw_need = amount * rate1
        if krw is not None and krw < krw_need:
            _fx_mark(day,"stop","krw_short")
            return "krw_short"
        r2 = await asyncio.to_thread(client.api.fx_applied_rate)
        rate2 = Decimal(str(r2["rate"]))
        if not rate2.is_finite() or rate2 <= 0 or abs(rate2-rate1)/rate1 >= Decimal("0.01"):
            _fx_mark(day,"stop","rate_changed")
            return "rate_changed"
        RL.ev("decision","auto_fx","ok","dry_run" if RUN.get("dry") else "live",actor="scheduler",need_usd=need,amount_usd=float(amount),rate=float(rate2),krw_required=float(amount*rate2))
        if RUN.get("dry"):
            _fx_mark(day,"dry_run",str(amount))
            return "dry_run"
        # Persist before POST. Uncertain network results MUST NOT be retried.
        _fx_mark(day,"uncertain","before_exchange")
        try:
            await asyncio.to_thread(client.api.fx_exchange, f"{amount:.2f}", str(rate2), str(r2.get("exrt_stnd_time") or ""))
        except MeritzError as e:
            msg = str(e)
            if not msg.startswith("HTTP ") and "토큰" not in msg and any(w in msg for w in FX_KRW_SHORT_WORDS):
                return "stop"
            return "uncertain"
        except Exception:
            return "uncertain"
        _fx_record_path(day).write_text(json.dumps({"date_kst":day,"result":"ok"}),encoding="utf-8")
        return "ok"
    except Exception as e:
        RL.err("auto_fx",e,event_type="decision")
        return "error"

async def scheduler_loop(client):
    n_pass = 0
    while True:
        n_pass += 1; RL.count("scheduler_tick"); RL.tick()
        _hub_beat(HUB_NAME)
        try:
            refresh_settings()
            await maybe_auto_fx(client)
            if SETTINGS.get("enabled", False) and RUN.get("key_ok"):
                await SG.sgov_daily_refresh(client)            # 조회만: 공개 환율 자료 + 메리츠 적용환율 기록 (하루 1번)
            now_est = datetime.now(EST_TZ)
            if runtime_info.get("date") != now_est.strftime("%Y-%m-%d"):
                runtime_info["date"] = now_est.strftime("%Y-%m-%d"); runtime_info["count"] = 0
            hm_est = now_est.strftime("%H:%M")
            if not SETTINGS.get("enabled", False):
                if RL.once("disabled"): RL.ev("decision", "scheduler", "skipped", "enabled_false", actor="scheduler")
            elif not RUN.get("key_ok"):
                if RL.once("key_bad"): RL.ev("decision", "scheduler", "skipped", "key_check_failed", actor="scheduler", level="ERROR")
            else:
                t0, t1 = _hm(SETTINGS.get("order_time_et"), "10:05"), _hm(SETTINGS.get("order_deadline_et"), "15:40")
                if now_est.weekday() < 5 and t0 <= hm_est <= t1:
                    RL.new_cid("sch", "us", now_est.strftime("%Y-%m-%d"), n_pass)
                    await execute_us_step(client)
                    if hm_est >= _hm(SETTINGS.get("missed_alert_et"), "10:20"): await check_missed_trades_alert(client)
                elif (DcaConfigManager.read_sync().get("pending_orders") or []):
                    await sync_fills(client)                       # 시간 밖이어도 체결 대기분은 정리
        except Exception as e: RL.err("scheduler_pass", e, event_type="decision")
        finally: RL.set_cid("")
        await asyncio.sleep(50)

def _on_stop(signum, frame):
    RL.new_cid("svc", "stop"); RL.ev("state_change", "service_stop", "ok", None, signal=signum)
    RL._maybe_flush(force=True); os._exit(0)

def _wrap_api(api):
    """메리츠 호출: 성공은 세기만, 실패는 오류 기록 (경로 속 값은 가림). 호출 결과·예외는 그대로"""
    orig = api._call
    def _call(method, path, *a, **k):
        t0 = time.time()
        try:
            r = orig(method, path, *a, **k); RL.count("meritz_api_ok"); return r
        except Exception as e:
            RL.err("meritz_api", e, endpoint=str(path).split("?")[0], method=method, ms=int((time.time() - t0) * 1000)); raise
    api._call = _call


class _NoKeyClient:
    """키 확인 실패 시: 메리츠를 한 번도 부르지 않음 (모든 호출이 예외)"""
    def __getattr__(self, name):
        async def _fail(*a, **k): raise MeritzError("키 확인 실패 — 메리츠 호출 안 함")
        return _fail
    def cached_market(self, symbol): return (None, None)


def make_client(s):
    bad, _ = key_problems(s)
    if bad: return _NoKeyClient(), bad
    api = MeritzApi(s["key_file"], os.path.join(s["state_dir"], "meritz_token.json"))
    _wrap_api(api)
    hint = lambda sym: (((s.get("markets") or {}).get(sym) or {}).get("mrkt"), ((s.get("markets") or {}).get(sym) or {}).get("exch_id"))
    return MeritzDcaClient(api, hint), []


async def run_service():
    s = refresh_settings()
    RL.setup("meritz_dca", BOT_VERSION, s["state_dir"])
    RL.new_cid("svc", "start")
    load_telegram(s.get("telegram_env_file", ""))
    client, bad = make_client(s)
    RL.ev("state_change", "service_start", "ok", None, us_window=f"{s.get('order_time_et')}-{s.get('order_deadline_et')} America/New_York",
          poll_sec=50, enabled=bool(s.get("enabled")), dry_run=bool(s.get("dry_run", True)), key_ok=not bad, tg_ok=bool(t_core.TG_TOKEN))
    signal.signal(signal.SIGTERM, _on_stop)
    if bad:
        txt = "⛔ [메리츠 적립 키 확인 실패 — 메리츠 호출·주문 안 함]\n" + "\n".join("• " + b for b in bad)
        _hub_alert(HUB_NAME, "critical", txt)
        if not poll_blocked(): send_panel(txt, [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
    elif not poll_blocked():
        t, kb = await build_panel_view(client)
        send_panel(f"✨ [메리츠 적립봇 {BOT_VERSION} 시작]\n\n" + t, kb); send_bottom_menu()
    RL.set_cid("")
    await asyncio.gather(polling_loop(client), scheduler_loop(client))


# ---------------------------------------------------------------- 명령줄 (주문 없음)
async def cmd_check():
    s = refresh_settings()
    print(f"MERITZ_DCA {BOT_VERSION} 점검 (주문 없음)")
    print(f"- enabled={s.get('enabled')} dry_run={s.get('dry_run')} transfer_confirmed={s.get('transfer_confirmed')} 상태파일={os.path.basename(config_path(s))}")
    kb, fp = key_problems(s)
    print(f"- 키 지문: {fp or '-'} ({'OK' if not kb else '문제 있음'})")
    for b in kb: print("  ✗", b)
    print(f"- 텔레그램(3번 토큰 재사용): {'읽음' if load_telegram(s.get('telegram_env_file', '')) else '못 읽음'} · 폴링 막힘({s.get('poll_block_service')} 실행 중): {poll_blocked()}")
    sp = start_problems(s)
    print(f"- settings.start: {'OK' if not sp else '문제 있음'}")
    for b in sp: print("  ✗", b)
    real = DcaConfigManager.read_sync(config_path(s, dry=False))
    print(f"- 실주문 장부: {'주입됨 ' + str(real.get('start_injected')) if real.get('start_injected') else '주입 전'}")
    gate = live_gate()
    print("- 실주문 안전장치: " + ("통과" if not gate else "막힘"))
    for g in gate: print("  ·", g)
    if kb: return 1
    client, _ = make_client(s)
    try: print(f"- USD 예수금: ${await client.get_buying_power('USD'):,.2f} (USD 행 없으면 $0)")
    except Exception as e: print(f"  ✗ USD 조회 실패: {e}")
    try: print(f"- 장운영 코드: {await client.us_market_status()} (004 = 정규장)")
    except Exception as e: print(f"  ✗ 장운영 조회 실패: {e}")
    cfg = await DcaConfigManager.load()
    if not cfg.get("stocks") and not sp: cfg = build_start_config(s, source="미리보기")
    tp1, sr = float(cfg.get("tp1_pct", 10)), float(cfg.get("sr_pct", 20))
    for sym, st in cfg.get("stocks", {}).items():
        try:
            m, ex, _ = await client.resolve(sym)
            cur = await client.get_current_price(sym); h = await client.get_symbol_holdings(sym)
        except Exception as e:
            print(f"  ✗ {sym}: 조회 실패 {e}"); continue
        q, avg = ledger_of(st)[0], ledger_avg(st)
        pp = (cur / avg - 1) * 100 if avg > 0 else 0.0
        stg = tp_sell_stage(pp, tp1, int(st.get("sold_stage", 0)))
        bq, _c = int_buy_qty(calc_buy_amount(float(st.get("base_amount", 40)), 1.0, q > 0 and pp >= 1.0), float(st.get("buy_carry") or 0), cur, s.get("us_int_buy_mode", "carry"))
        plan = f"{stg}차 익절 {int_sell_qty(q, sr)}주 매도" if (q > 0 and stg) else (f"매수 {bq}주 (이월 ${_c:.2f})" if st.get("s_mode") in ("buy_1", "buy_2") else st.get("s_mode"))
        print(f"  {sym}: 거래소 {m}/{ex} · 현재가 ${cur:.2f} · 장부 {q:g}주 평단 ${avg:.4f} ({pp:+.2f}%) · 메리츠 {float(h.get('qty') or 0):g}주"
              f" · {st.get('s_mode')} {st.get('s_day')}/{st.get('s_target_days')} · 익절단계 {st.get('sold_stage')} → 오늘 계획: {plan} (N7 배수 미반영)")
    try:
        for line in await SG.sgov_preview_lines(client, cfg, datetime.now(EST_TZ).strftime("%Y-%m-%d")): print(line)
    except Exception as e: print(f"  ✗ SGOV 미리보기 실패: {e}")
    return 0


async def cmd_inject(overwrite=False):
    s = refresh_settings()
    bad = start_problems(s) + key_problems(s)[0]
    if not s.get("transfer_confirmed"): bad.append("transfer_confirmed=false (입고 확인 먼저)")
    real_path = config_path(s, dry=False)
    real = DcaConfigManager.read_sync(real_path)
    if real.get("start_injected") and not overwrite: bad.append(f"이미 주입됨 ({real.get('start_injected')}) — 다시 하려면 --overwrite")
    if bad:
        print("✗ 주입 안 함:\n" + "\n".join("- " + b for b in bad)); return 1
    client, _ = make_client(s)
    for sym, v in s["start"]["stocks"].items():
        h = await client.get_symbol_holdings(sym.upper())
        if abs(float(h.get("qty") or 0) - float(v["qty"])) > 1e-6:
            print(f"✗ {sym}: 메리츠 잔고 {float(h.get('qty') or 0):g}주 ≠ 시작 수량 {float(v['qty']):g}주 — 입고 미완료 또는 다른 계좌"); return 1
    cfg = build_start_config(s, base=real)
    for sym in s["start"]["stocks"]: cfg["stocks"][sym.upper()]["has_held"] = True
    DcaConfigManager.write_sync(cfg, real_path)
    for sym, st in cfg["stocks"].items():
        if sym in {k.upper() for k in s["start"]["stocks"]}:
            print(f"장부 시작: {sym} {ledger_of(st)[0]:g}주 원금 ${ledger_of(st)[1]:.2f} 평단 ${ledger_avg(st):.4f} · {st['s_mode']} {st['s_day']}/{st['s_target_days']} · 익절단계 {st['sold_stage']}")
    print(f"전체 전원: {'ON' if cfg['is_master_active'] else 'OFF'} · N7: {'켜짐' if cfg.get('n7_enabled') else '꺼짐'}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="메리츠 적립 봇 (meritz_dca)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fingerprint", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--inject-start", action="store_true")
    g.add_argument("--dry-reset", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="--inject-start 때 기존 장부 덮어쓰기")
    a = ap.parse_args(argv)
    if a.fingerprint:
        print(key_fingerprint(load_settings()["key_file"])); return 0
    if a.check: return asyncio.run(cmd_check())
    if a.inject_start: return asyncio.run(cmd_inject(a.overwrite))
    if a.dry_reset:
        s = load_settings(); p = config_path(s, dry=True)
        if os.path.exists(p): os.remove(p)
        print("모의 장부 지움 (다음 실행 때 다시 만듦)"); return 0
    asyncio.run(run_service()); return 0


if __name__ == "__main__":
    sys.exit(main())
