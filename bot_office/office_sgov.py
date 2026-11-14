# ==========================================================
# FILE: /opt/bot-office/office_sgov.py   (OFFICE_SGOV — 새 파일)
# 사무실 vNEXT (2026-11-14): 비서봇 SGOV 메뉴 (상황판·현황·자금·시드·분배금·건너뜀 모드·게이트 확인)
#  - 읽기만: meritz_dca_bot 이 만든 상태 스냅샷 <bridge>/snapshot.json
#  - 명령(시드 변경·건너뜀·분배금·게이트·자동환전)은 요청 파일만 씀: <bridge>/requests/req_<id>.json
#    → meritz_dca_bot(bridge.py·main.bridge_handle)이 검증·실행하고 <bridge>/results/res_<id>.json 을 씀 → 여기서 읽어 보여 줌
#  - 이 파일은 메리츠 API·키·토큰(meritz_token.json)·SGOV 설정(/etc/meritz-accum/settings.json)·장부(dca_config*.json)를
#    읽지도 쓰지도 않음. meritz_dca_bot 코드를 import 하지 않음.
#  - <bridge> 기본값 /var/lib/meritz-dca/bridge (환경변수 OFFICE_MERITZ_BRIDGE 로 바꿀 수 있음)
# ==========================================================
import html, json, os, re, time, uuid
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
BRIDGE = Path(os.environ.get("OFFICE_MERITZ_BRIDGE", str(R / "var/lib/meritz-dca/bridge")))
SNAP_STALE_SEC = 900        # 제안값(근거 없음): meritz_dca_bot 스냅샷 간격 300초의 3배 넘게 지나면 '미확인'
RESULT_TIMEOUT_SEC = 120    # 제안값: 이 시간 안에 결과가 없으면 '미확인' (meritz_dca_bot 은 60초 지난 요청을 실행하지 않음)
LATE_KEEP_SEC = 600         # 제안값: '미확인' 뒤에도 늦은 결과를 이만큼 더 확인, 그 뒤 내 요청 파일 정리
AWAIT_SEC = 600             # 숫자 입력 기다림 (기존 비서봇 안내 "10분 안"과 같음)
CONFIRM_SEC = 120           # 자동환전 [실행] 확인 유효 시간 (제안값)
MAX_PENDING = 5

CHART, MENU_OPEN = "📈 상황판", "☰ 메뉴"
SGOV_MENU_ROWS = [["🪙 SGOV 현황", "💰 자금·SGOV"], ["⚙️ 시드·SGOV", "💵 분배금 기록"], ["🛠 도구", "❓ 도움말"], ["🏠 처음 화면"]]
SGOV_TOOLS_ROWS = [["건너뜀 모드", "게이트 확인"], ["🔙 메뉴"]]
FX_RUN, FX_CANCEL, REFRESH = "실행", "취소", "🔄 새로고침"
SG_ON, SG_OFF = "▶️ SGOV 켜기", "⏸ SGOV 끄기"
REVIEW_OK = "✅ 재점검 완료 · 다음 회차부터 다시 판단"
# meritz_dca_bot/main.py SEED_FIELDS 의 SGOV 그룹 글자와 같음 (키 → 화면 글자)
SEED_LABELS = {"target_usd_total": "SGOV 총 목표", "tranche_usd": "SGOV 회차 금액", "first_tranche_usd": "SGOV 1회차 금액",
               "tranches_total": "SGOV 총 회차 수", "interval_days": "SGOV 회차 간격(일)"}
SEED_BY_LABEL = {v: k for k, v in SEED_LABELS.items()}
FIXED = {CHART, "🪙 SGOV 현황", "💰 자금·SGOV", "⚙️ 시드·SGOV", "💵 분배금 기록", "🛠 도구", "🏠 처음 화면",
         "🔙 메뉴", "건너뜀 모드", "게이트 확인", "자동환전 실행", REFRESH, SG_ON, SG_OFF, REVIEW_OK, *SEED_LABELS.values()}
X_RE = re.compile(r"^(?:✅ )?X ([0-9]+(?:\.[0-9]+)?)%$")
HELP = "\n".join([
    "❓ SGOV 메뉴 사용법 (비서봇)",
    "▫️ 맨밑 첫 줄: 📈 상황판 (SGOV 상황판) · ☰ 메뉴 (SGOV 메뉴)",
    "▫️ ☰ 메뉴: 🪙 SGOV 현황 · 💰 자금·SGOV · ⚙️ 시드·SGOV · 💵 분배금 기록 · 🛠 도구 · ❓ 도움말 · 🏠 처음 화면",
    "▫️ 🛠 도구: 건너뜀 모드 (X% · 연속 건너뜀 규칙 · 재점검 완료) · 게이트 확인 · 🔙 메뉴",
    "▫️ 🏢 사무실 메뉴: 💰 잔액 · 🖥 PC 상태 · 🏢 사무실 · ❓ 도움말 · 🏠 메인 메뉴 (예전 메뉴 그대로)",
    "▫️ 값은 메리츠 적립봇(4번)이 만든 스냅샷을 읽기만 해요. 바꾸는 일은 요청만 보내고, 4번이 검사·실행한 결과를 보여 줘요.",
    "▫️ 자동환전은 주식분 + SGOV분 합산 부족분으로 한 번만 해요 (4번에서 눌러도 같은 실행 1개). 주식분은 4번 자금에서.",
])


# ---------------------------------------------------------- 파일 (스냅샷·결과는 읽기만, 요청은 이 파일만 씀)
def _read(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def snapshot(now=None):
    """(스냅샷 dict 또는 None, 오래됨 여부, 몇 초 전)"""
    now = time.time() if now is None else now
    s = _read(BRIDGE / "snapshot.json")
    if not isinstance(s, dict) or not isinstance(s.get("ts"), (int, float)):
        return None, True, None
    age = now - float(s["ts"])
    return s, age > SNAP_STALE_SEC or age < -60, age


def send_request(st, rtype, args=None, label=""):
    """요청 파일 1개 (원자적: .tmp 로 쓰고 이름 바꿈). → id 또는 None(대기 중 요청이 너무 많음·쓰기 실패)"""
    pend = st.setdefault("sgov_req", {})
    if len([1 for v in pend.values() if not v.get("timed_out")]) >= MAX_PENDING:
        return None
    rid = uuid.uuid4().hex
    req = {"id": rid, "ts": time.time(), "type": rtype, "args": args or {}, "from": "office_secretary"}
    d = BRIDGE / "requests"
    try:
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f"req_{rid}.json.tmp"
        tmp.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, d / f"req_{rid}.json")
    except OSError as e:
        print("SGOV 요청 파일 쓰기 실패:", type(e).__name__, flush=True)
        return None
    pend[rid] = {"type": rtype, "ts": req["ts"], "label": label}
    return rid


def _drop_request(rid):
    try:
        (BRIDGE / "requests" / f"req_{rid}.json").unlink()
    except OSError:
        pass


# ---------------------------------------------------------- 화면
def _esc(t):
    return html.escape(str(t), quote=False)


def kb(rows):
    return [[{"text": t} for t in row] for row in rows]


def main_kb(*extra):
    return kb([[CHART, MENU_OPEN], *extra])


def _m(v):
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "미확인"


def _i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _snap_line(snap, stale, age):
    if not snap:
        return "🕒 스냅샷: 미확인 (메리츠 적립봇 상태 파일 없음)"
    mins = int((age or 0) // 60)
    return f"🕒 스냅샷: {snap.get('ts_kst', '-')} KST ({mins}분 전)" + (" · ⚠️ 오래됨 → 미확인" if stale else "")


def _bar(pct):
    n = max(0, min(10, int(float(pct) / 10 + 0.5)))
    return "🟨" * n + "⬜" * (10 - n)


def chart_text(snap, stale, age):
    if not snap:
        return "🟨 [SGOV 상황판]\n" + _snap_line(snap, stale, age)
    sg = snap.get("sgov") or {}
    lg = sg.get("ledger") or {}
    done, total = _i(sg.get("tranches_done")), _i(sg.get("tranches_total"))
    pct = min(100, 100 * done / total) if total > 0 else 0
    q, pr = float(lg.get("qty") or 0), float(lg.get("principal") or 0)
    ld = sg.get("last_decision") or {}
    act = {"buy": "매수", "skip_a": "건너뜀 (a 평균 환율)", "skip_b": "건너뜀 (b 7일 상승)"}.get(ld.get("action"), "-")
    lines = ["🟨 [SGOV 상황판]", _snap_line(snap, stale, age)]
    if stale:
        lines.append("⚠️ 아래 값은 마지막 스냅샷 기준이라 미확인이에요. 🔄 새로고침을 눌러 주세요.")
    lines += [
        f"▫️ 상태: {'🟢 켜짐' if sg.get('enabled') else '⚪ 꺼짐'}" + (" · 🛑 재점검 대기 (매수 멈춤)" if sg.get("review_hold") else ""),
        f"▫️ 진행률: {_bar(pct)} {pct:.0f}% ({done}/{total}회 완료)",
        f"▫️ 총 목표 {_m(sg.get('target_usd_total'))} · 회차 금액 {_m(sg.get('tranche_usd'))} · 1회차 금액 {_m(sg.get('first_tranche_usd'))}",
        f"▫️ 다음 예정일: {sg.get('next_due_date') or '-'} (미국 동부) · 이번 회차 {_m(snap.get('sgov_tranche_now'))}",
        f"▫️ 연속 건너뜀: {_i(sg.get('skip_streak'))}회 (7일 상승 연속 {_i(sg.get('skip_streak_b'))}회)",
        f"▫️ 최근 판단: {ld.get('date') or '-'} {act}",
        "📒 [SGOV 장부]",
        f" • 보유 {q:g}주 · 원금 {_m(pr)} · 평단 {_m(pr / q if q > 1e-9 else 0)}",
        f" • 분배금 누적 {_m(lg.get('distributions_usd'))} · SGOV 대기 달러 {_m(sg.get('wait_usd'))}",
    ]
    for p in (snap.get("sgov_problems") or [])[:5]:
        lines.append("⛔ 설정 확인 필요: " + str(p))
    return "\n".join(lines)


def funds_text(snap, stale, age):
    lines = ["💰 [자금 · SGOV]", _snap_line(snap, stale, age)]
    if not snap:
        return "\n".join(lines + ["보유 달러: 미확인", "오늘 필요 (SGOV분): 미확인"])
    md, sg = snap.get("mode") or {}, snap.get("sgov") or {}
    usd = "미확인" if stale or snap.get("usd") is None else _m(snap.get("usd"))
    lines += [f"보유 달러: {usd}",
              "매매: " + ("자동" if md.get("enabled") else "중지") + " / " + ("모의" if md.get("dry_run", True) else "실전"),
              "자동환전: " + ("켜짐" if md.get("auto_fx_on") else "꺼짐"),
              f"SGOV 시드: 총 {_m(sg.get('target_usd_total'))} · {_i(sg.get('tranches_total'))}회",
              "─────────────────", "환전: SGOV분 (이 화면)"]
    if stale or snap.get("need_sgov") is None:
        lines.append("오늘 필요 (SGOV분): 미확인" + (f" ({snap.get('need_error')})" if snap.get("need_error") and not stale else ""))
        lines.append("환전할 금액 (SGOV분 기준): 미확인")
    else:
        lines.append(f"오늘 필요 (SGOV분): {_m(snap.get('need_sgov'))}")
        a = snap.get("fx_amount_sgov_side")
        lines.append(f"환전할 금액 (SGOV분 기준): {_m(a)}" if a is not None else "환전할 금액 없음 (SGOV분 기준)")
    lines.append(f"보유 USD: {usd}")
    lines += ["ℹ️ 주식분은 4번 자금에서",
              "ℹ️ [자동환전 실행]은 (주식 필요 + SGOV 필요) − 보유 달러 합산 부족분으로 한 번만 해요 (메리츠 적립봇이 실행)"]
    return "\n".join(lines)


def seed_text(snap, stale, age):
    sg = (snap or {}).get("sgov") or {}
    lines = ["⚙️ [시드 · SGOV — 입력만으로 주문·환전 없음]", _snap_line(snap, stale, age)]
    for k, label in SEED_LABELS.items():
        lines.append(f"• {label}: {sg.get(k) if snap else '미확인'}")
    lines.append("바꿀 항목을 누르고 숫자를 보내 주세요. 메리츠 적립봇이 기존 검사(총 목표 99~101% 등)를 다시 하고 저장해요.")
    return "\n".join(lines)


def skip_rows(snap):
    sg = (snap or {}).get("sgov") or {}
    x, mode = float(sg.get("skip_jump_pct") or 1.5), sg.get("skip_cap_mode", "review")
    xs = (snap or {}).get("skip_x_choices") or []
    lab = lambda v: ("✅ " if abs(float(v) - x) < 1e-9 else "") + f"X {float(v):g}%"
    rows = [[lab(v) for v in xs[:3]], [lab(v) for v in xs[3:]]]
    rows += [[("✅ " if m == mode else "") + t] for m, t in ((snap or {}).get("cap_modes") or {}).items()]
    if sg.get("review_hold"):
        rows.append([REVIEW_OK])
    rows.append(["🔙 메뉴"])
    return [r for r in rows if r]


def skip_text(snap, stale, age):
    sg = (snap or {}).get("sgov") or {}
    x, mode = float(sg.get("skip_jump_pct") or 1.5), sg.get("skip_cap_mode", "review")
    cm = (snap or {}).get("cap_modes") or {}
    return "\n".join(["⚙️ [건너뜀 모드 — 다음 회차 판단부터 적용, 바꿔도 바로 사지 않음]", _snap_line(snap, stale, age),
                      f" • (a) 회차 날 적용환율이 최근 {_i(sg.get('fx_avg_months') or 36)}개월 평균보다 낮아야 매수",
                      f" • (b) 7일 전보다 {x:g}% 이상 오르면 건너뜀 (X = {x:g}%)",
                      f" • 연속 건너뜀: {cm.get(mode, mode)}",
                      " • 건너뛴 회차는 맨 뒤로 붙임 (다음 회차에 몰아 사지 않음)"])


def _send(tg, text, rows):
    tg.send(_esc(text), keyboard=rows)


def show_chart(tg, st, notice=""):
    snap, stale, age = snapshot()
    on = bool(((snap or {}).get("sgov") or {}).get("enabled"))
    _send(tg, (notice + "\n\n" if notice else "") + chart_text(snap, stale, age), main_kb([REFRESH, SG_OFF if on else SG_ON]))


def show_menu(tg, st):
    st["menu_ctx"] = "sgov"
    _send(tg, "☰ SGOV 메뉴 · 아래 버튼을 눌러 주세요", kb(SGOV_MENU_ROWS))


# ---------------------------------------------------------- 버튼·입력 처리 (등록된 채팅방 확인은 office_secretary.main 이 이미 함)
def _expired(rec, sec, now):
    return not rec or now - float(rec.get("ts") or 0) > sec


def _req(tg, st, rtype, args=None, label=""):
    rid = send_request(st, rtype, args, label)
    if not rid:
        _send(tg, "⚠️ 요청을 보내지 못했어요 (대기 중 요청이 많거나 파일 쓰기 실패). 잠시 뒤 다시 해 주세요.", main_kb())
    else:
        _send(tg, f"📨 {label or rtype} 요청을 메리츠 적립봇에 보냈어요. 결과가 오면 알려 드릴게요 (최대 {RESULT_TIMEOUT_SEC}초).", main_kb())
    return rid


def handle(tg, st, raw, other_labels=()):
    """SGOV 메뉴 글자면 처리하고 True. 아니면 False (기존 비서봇 처리로 넘어감)"""
    now = time.time()
    aw = st.get("sgov_await")
    # 숫자 입력 대기 중: 버튼 글자가 아니면 입력으로 처리 (버튼을 누르면 입력 대기 해제)
    if aw and raw not in FIXED and raw not in other_labels and raw not in (FX_RUN, FX_CANCEL, MENU_OPEN) \
            and not raw.startswith("/") and not X_RE.match(raw) and raw not in _cap_labels():
        st.pop("sgov_await", None)
        if _expired(aw, AWAIT_SEC, now):
            _send(tg, "⏱ 입력 시간이 지났어요. 다시 눌러 주세요.", kb(SGOV_MENU_ROWS)); return True
        if aw.get("kind") == "seed" and aw.get("key") in SEED_LABELS:
            _req(tg, st, "sgov_seed", {"key": aw["key"], "value": raw}, f"{SEED_LABELS[aw['key']]} 변경")
        elif aw.get("kind") == "dist":
            _req(tg, st, "sgov_dist", {"amount": raw}, "분배금 기록")
        return True
    if raw in FIXED or raw in other_labels or raw in (FX_RUN, FX_CANCEL, MENU_OPEN) or raw.startswith("/") \
            or X_RE.match(raw) or raw in _cap_labels():
        st.pop("sgov_await", None)
    snap, stale, age = snapshot(now)
    if raw == CHART:
        show_chart(tg, st); return True
    if raw == MENU_OPEN or raw == "🔙 메뉴":
        show_menu(tg, st); return True
    if raw == "🛠 도구":
        st["menu_ctx"] = "sgov"
        _send(tg, "🛠 도구 · 가끔 쓰는 기능이에요", kb(SGOV_TOOLS_ROWS)); return True
    if raw == "❓ 도움말" and st.get("menu_ctx") == "sgov":
        _send(tg, HELP, kb(SGOV_MENU_ROWS)); return True
    if raw == "🪙 SGOV 현황":
        body = (snap or {}).get("sgov_view_text") or "SGOV 현황: 미확인"
        _send(tg, _snap_line(snap, stale, age) + ("\n⚠️ 아래 값은 미확인 (오래된 스냅샷)" if stale and snap else "") + "\n" + body, main_kb()); return True
    if raw == "💰 자금·SGOV":
        _send(tg, funds_text(snap, stale, age), main_kb(["자동환전 실행", "⚙️ 시드·SGOV"], ["🔙 메뉴"])); return True
    if raw == "⚙️ 시드·SGOV":
        _send(tg, seed_text(snap, stale, age), main_kb(*[[l] for l in SEED_LABELS.values()], ["🔙 메뉴"])); return True
    if raw in SEED_BY_LABEL:
        key = SEED_BY_LABEL[raw]
        st["sgov_await"] = {"kind": "seed", "key": key, "ts": now}
        _send(tg, f"💰 {raw} 새 값을 숫자로 보내 주세요. (주문·환전 없음 · 10분 안 · 다른 버튼을 누르면 취소)", main_kb(["🔙 메뉴"])); return True
    if raw == "💵 분배금 기록":
        st["sgov_await"] = {"kind": "dist", "ts": now}
        _send(tg, "💵 [SGOV 분배금 기록]\n• 들어온 분배금(달러)을 숫자로 보내 주세요. 예: 12.34\n"
                  "• SGOV 장부·대기 달러에만 더하고 다음 회차에 재투자합니다 (NKE/QLD 와 따로).", main_kb(["🔙 메뉴"])); return True
    if raw == "건너뜀 모드":
        st["menu_ctx"] = "sgov"
        if not snap:
            _send(tg, "건너뜀 모드: 미확인 (메리츠 적립봇 상태 파일 없음)", kb(SGOV_TOOLS_ROWS)); return True
        _send(tg, skip_text(snap, stale, age), main_kb(*skip_rows(snap))); return True
    if raw == "게이트 확인":
        _req(tg, st, "sgov_gate", {}, "게이트 확인"); return True
    m = X_RE.match(raw)
    if m:
        _req(tg, st, "sgov_x", {"x": float(m.group(1))}, f"X {float(m.group(1)):g}% 변경"); return True
    mode = _cap_labels(snap).get(raw)
    if mode:
        _req(tg, st, "sgov_mode", {"mode": mode}, "연속 건너뜀 규칙 변경"); return True
    if raw == REVIEW_OK:
        _req(tg, st, "sgov_review_ok", {}, "재점검 완료"); return True
    if raw in (SG_ON, SG_OFF):
        _req(tg, st, "sgov_enable", {"on": raw == SG_ON}, "SGOV " + ("켜기" if raw == SG_ON else "끄기")); return True
    if raw == REFRESH:
        _req(tg, st, "snapshot", {}, "새로고침"); return True
    if raw == "자동환전 실행":
        _req(tg, st, "fx_preview", {}, "자동환전 금액 확인"); return True
    if raw == FX_RUN and "sgov_fx_confirm" in st:
        rec = st.pop("sgov_fx_confirm")
        if _expired(rec, CONFIRM_SEC, now):
            _send(tg, "⏱ 확인 시간이 지났어요. 💰 자금·SGOV → 자동환전 실행을 다시 눌러 주세요.", main_kb()); return True
        _req(tg, st, "fx_run", {}, "자동환전 실행"); return True
    if raw == FX_CANCEL and ("sgov_fx_confirm" in st or aw):
        st.pop("sgov_fx_confirm", None)
        show_menu(tg, st); return True
    if raw == "🏠 처음 화면":
        return False   # 처음 화면은 office_secretary 가 MENU_KB 로 보여 줌
    return False


def _cap_labels(snap=None):
    if snap is None:
        snap = snapshot()[0]
    out = {}
    for m, t in ((snap or {}).get("cap_modes") or {}).items():
        out[t] = m; out["✅ " + t] = m
    return out


def tick(tg, st, now=None):
    """결과 파일 확인 → 보여 줌. 시간이 지나면 '미확인'. → 아직 기다리는 요청 수"""
    now = time.time() if now is None else now
    pend = st.get("sgov_req") or {}
    for rid in list(pend):
        rec = pend[rid]
        res = _read(BRIDGE / "results" / f"res_{rid}.json")
        final = isinstance(res, dict) and res.get("status") not in (None, "processing") and str(res.get("id")) == rid
        label = rec.get("label") or rec.get("type")
        if final:
            pend.pop(rid, None); _drop_request(rid)
            head = ("🕓 늦게 도착한 결과 · " if rec.get("timed_out") else "") + f"[{label}] "
            txt = head + {"ok": "", "rejected": "실행 안 함 · ", "expired": "미확인 · ", "invalid": "실행 안 함 · ",
                          "error": "오류 · "}.get(res.get("status"), "") + str(res.get("text") or "")
            if res.get("type") == "fx_preview" and res.get("status") == "ok" and (res.get("data") or {}).get("amount"):
                st["sgov_fx_confirm"] = {"ts": now}
                _send(tg, txt, main_kb([FX_RUN, FX_CANCEL]))
            elif res.get("type") == "snapshot" and res.get("status") == "ok":
                show_chart(tg, st, "🔄 새로고침 완료")
            else:
                _send(tg, txt, main_kb())
            continue
        age = now - float(rec.get("ts") or 0)
        if not rec.get("timed_out") and age > RESULT_TIMEOUT_SEC:
            rec["timed_out"] = True
            _send(tg, f"⏳ [{label}] 결과 미확인 — {RESULT_TIMEOUT_SEC}초 동안 메리츠 적립봇 응답이 없어요. "
                      "실행됐는지 알 수 없으니 📈 상황판으로 다시 확인해 주세요.", main_kb())
        elif rec.get("timed_out") and age > RESULT_TIMEOUT_SEC + LATE_KEEP_SEC:
            pend.pop(rid, None); _drop_request(rid)
    if not pend:
        st.pop("sgov_req", None)
    return len([1 for v in pend.values() if not v.get("timed_out")])
