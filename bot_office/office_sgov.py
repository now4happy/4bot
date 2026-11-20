# ==========================================================
# FILE: /opt/bot-office/office_sgov.py   (OFFICE_SGOV — 새 파일)
# 사무실 v1.9.5 (2026-11-20, audit-fix-v2 5-1·5-2·5-7): 총 회차 수 증가 문구·관문 출처 주의 문구·24시간 넘은 알림은 요약 재알림 1번(보낸 뒤에만 expired 표시)
# 사무실 v1.8.3 (2026-11-14): 비서봇 SGOV 메뉴 (상황판·현황·자금·시드·분배금·건너뜀 모드·게이트 확인)
#  - 읽기만: meritz_dca_bot 이 만든 상태 스냅샷 <bridge>/snapshot.json
#  - 명령(시드 변경·건너뜀·분배금·게이트·자동환전)은 요청 파일만 씀: <bridge>/requests/req_<id>.json
#    → meritz_dca_bot(bridge.py·main.bridge_handle)이 검증·실행하고 <bridge>/results/res_<id>.json 을 씀 → 여기서 읽어 보여 줌
#  - 이 파일은 메리츠 API·키·토큰(meritz_token.json)·SGOV 설정(/etc/meritz-accum/settings.json)·장부(dca_config*.json)를
#    읽지도 쓰지도 않음. meritz_dca_bot 코드를 import 하지 않음.
#  - <bridge> 기본값 /var/lib/meritz-dca/bridge (환경변수 OFFICE_MERITZ_BRIDGE 로 바꿀 수 있음)
# 사무실 v1.8.4 (2026-11-14): SGOV 회차 알림 — tick() 이 <bridge>/alerts/alert_<id>.json(4번이 씀)을 읽어 이 방으로 1번 보내고, 보낸 뒤 <bridge>/alerts_sent/sent_<id>.json(이 파일만 씀) 표시
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

CHART, MENU_OPEN = "상황판", "메뉴"
# v1.9.0 (2026-11-19): 첫 화면 4칸 [자금][환율 규칙][SGOV 현황][도움말] (+ 기존 이동 버튼 [처음 화면]).
#   자금 = 자금 현황·시드·분배금·자동환전 / 환율 규칙 = 건너뜀 %·연속 건너뜀 규칙·재점검 완료·게이트 확인.
#   건너뜀 % 6개 버튼 → 입력창(0.5~3.0, 0.5 단위), 시드·분배금·건너뜀 % 는 '지금 값 → 새 값' 확인 뒤에 요청 파일을 보냄. 매매 판단·요청 형식은 그대로.
SGOV_MENU_ROWS = [["자금", "환율 규칙"], ["SGOV 현황", "도움말"], ["처음 화면"]]
SGOV_TOOLS_ROWS = SGOV_MENU_ROWS      # 옛 '도구' 화면 호환
SK_ASK = "건너뜀 % 바꾸기"
CFM_OK = "변경 확인"
CTX_LABELS = {"자금", "환율 규칙", "도움말"}   # 다른 메뉴와 글자가 겹칠 수 있어 SGOV 메뉴 안(menu_ctx=sgov)에서만 버튼으로 읽음
SKIP_X_MIN, SKIP_X_MAX = 0.5, 3.0
FX_RUN, FX_CANCEL, REFRESH = "실행", "취소", "새로고침"
SG_ON, SG_OFF = "SGOV 켜기", "SGOV 끄기"
REVIEW_OK = "재점검 완료 · 다음 회차부터 다시 판단"
# meritz_dca_bot/main.py SEED_FIELDS 의 SGOV 그룹 글자와 같음 (키 → 화면 글자)
SEED_LABELS = {"target_usd_total": "SGOV 총 목표", "tranche_usd": "SGOV 회차 금액", "first_tranche_usd": "SGOV 1회차 금액",
               "tranches_total": "SGOV 총 회차 수", "interval_days": "SGOV 회차 간격(일)"}
SEED_BY_LABEL = {v: k for k, v in SEED_LABELS.items()}
FIXED = {CHART, "SGOV 현황", "자금·SGOV", "시드·SGOV", "분배금 기록", "도구", "처음 화면",
         "메뉴", "건너뜀 모드", "게이트 확인", "자동환전 실행", REFRESH, SG_ON, SG_OFF, REVIEW_OK, SK_ASK, CFM_OK, *SEED_LABELS.values()}
X_RE = re.compile(r"^(?:\[선택\] )?X ([0-9]+(?:\.[0-9]+)?)%$")   # 옛 6개 버튼 글자도 알아봄 (예전 키보드가 남아 있을 때)
HELP = "\n".join([
    "[도움말 · SGOV 메뉴 (비서봇)]",
    "· 맨밑 첫 줄: 상황판 (SGOV 상황판) · 메뉴 (SGOV 메뉴)",
    "· 메뉴 4칸: 자금 · 환율 규칙 · SGOV 현황 · 도움말",
    "· 자금: 보유 달러와 필요 금액, 자동환전, 시드(총 목표·회차 금액·1회차 금액·총 회차 수·회차 간격), 분배금 기록",
    "· 환율 규칙: 건너뜀 모드(건너뜀 %는 0.5~3.0, 0.5 단위로 입력), 연속 건너뜀 규칙, 재점검 완료, 게이트 확인",
    "· 시드: SGOV 회차 적립의 금액 기준이에요. 분배금: SGOV가 준 돈이에요. 장부에 더하고 다음 회차에 재투자해요.",
    "· 건너뜀 모드: 7일 전보다 설정 % 이상 오르면 그 회차를 건너뛰어요. 게이트는 실주문 전 안전 확인이에요.",
    "· 값은 메리츠 적립봇(6번)이 만든 스냅샷을 읽기만 해요. 바꾸는 일은 '지금 값 → 새 값' 확인 뒤 요청만 보내고, 6번이 검사·실행한 결과를 보여 줘요.",
    "· 자동환전은 주식분 + SGOV분 합산 부족분으로 한 번만 해요 (6번에서 눌러도 같은 실행 1개). 주식분은 6번 자금에서.",
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
        return "스냅샷: 미확인 (메리츠 적립봇 상태 파일 없음)"
    mins = int((age or 0) // 60)
    return f"스냅샷: {snap.get('ts_kst', '-')} KST ({mins}분 전)" + (" · 오래됨 → 미확인" if stale else "")


def _bar(pct):
    n = max(0, min(10, int(float(pct) / 10 + 0.5)))
    return "[" + "#" * n + "-" * (10 - n) + "]"


def chart_text(snap, stale, age):
    if not snap:
        return "[SGOV 상황판]\n" + _snap_line(snap, stale, age)
    sg = snap.get("sgov") or {}
    lg = sg.get("ledger") or {}
    done, total = _i(sg.get("tranches_done")), _i(sg.get("tranches_total"))
    pct = min(100, 100 * done / total) if total > 0 else 0
    q, pr = float(lg.get("qty") or 0), float(lg.get("principal") or 0)
    ld = sg.get("last_decision") or {}
    act = {"buy": "매수", "skip_a": "건너뜀 (a 평균 환율)", "skip_b": "건너뜀 (b 7일 상승)"}.get(ld.get("action"), "-")
    lines = ["[SGOV 상황판]", _snap_line(snap, stale, age)]
    if stale:
        lines.append("아래 값은 마지막 스냅샷 기준이라 미확인이에요. 새로고침을 눌러 주세요.")
    lines += [
        f"· 상태: {'켜짐' if sg.get('enabled') else '꺼짐'}" + (" · 재점검 대기 (매수 멈춤)" if sg.get("review_hold") else ""),
        f"· 진행률: {_bar(pct)} {pct:.0f}% ({done}/{total}회 완료)",
        f"· 총 목표 {_m(sg.get('target_usd_total'))} · 회차 금액 {_m(sg.get('tranche_usd'))} · 1회차 금액 {_m(sg.get('first_tranche_usd'))}",
        f"· 다음 예정일: {sg.get('next_due_date') or '-'} (미국 동부) · 이번 회차 {_m(snap.get('sgov_tranche_now'))}",
        f"· 연속 건너뜀: {_i(sg.get('skip_streak'))}회 (7일 상승 연속 {_i(sg.get('skip_streak_b'))}회)",
        f"· 최근 판단: {ld.get('date') or '-'} {act}",
        "[SGOV 장부]",
        f" • 보유 {q:g}주 · 원금 {_m(pr)} · 평단 {_m(pr / q if q > 1e-9 else 0)}",
        f" • 분배금 누적 {_m(lg.get('distributions_usd'))} · SGOV 대기 달러 {_m(sg.get('wait_usd'))}",
    ]
    for p in (snap.get("sgov_problems") or [])[:5]:
        lines.append("설정 확인 필요: " + str(p))
    return "\n".join(lines)


def funds_text(snap, stale, age):
    lines = ["[자금 · SGOV]", _snap_line(snap, stale, age)]
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
    lines += ["주식분은 4번 자금에서",
              "[자동환전 실행]은 (주식 필요 + SGOV 필요) − 보유 달러 합산 부족분으로 한 번만 해요 (메리츠 적립봇이 실행)"]
    return "\n".join(lines)


def seed_text(snap, stale, age):
    sg = (snap or {}).get("sgov") or {}
    lines = ["[시드 · SGOV — 입력만으로 주문·환전 없음]", _snap_line(snap, stale, age)]
    for k, label in SEED_LABELS.items():
        lines.append(f"• {label}: {sg.get(k) if snap else '미확인'}")
    lines.append("총 회차 수: 환율 규칙으로 건너뛴 회차는 맨 뒤에 붙어서, 총 매수 횟수가 계획보다 늘어납니다 (건너뛸 때마다 총 회차 수 +1).")
    lines.append("바꿀 항목을 누르고 숫자를 보내 주세요. 메리츠 적립봇이 기존 검사(총 목표 99~101% 등)를 다시 하고 저장해요.")
    return "\n".join(lines)


def skip_rows(snap):
    sg = (snap or {}).get("sgov") or {}
    mode = sg.get("skip_cap_mode", "review")
    rows = [[SK_ASK]]
    rows += [[("[선택] " if m == mode else "") + t] for m, t in ((snap or {}).get("cap_modes") or {}).items()]
    if sg.get("review_hold"):
        rows.append([REVIEW_OK])
    rows.append(["게이트 확인"])
    rows.append(["메뉴"])
    return [r for r in rows if r]


def skip_text(snap, stale, age):
    sg = (snap or {}).get("sgov") or {}
    x, mode = float(sg.get("skip_jump_pct") or 1.5), sg.get("skip_cap_mode", "review")
    cm = (snap or {}).get("cap_modes") or {}
    return "\n".join(["[환율 규칙 · 건너뜀 모드 — 다음 회차 판단부터 적용, 바꿔도 바로 사지 않음]", _snap_line(snap, stale, age),
                      f" • (a) 회차 날 적용환율이 최근 {_i(sg.get('fx_avg_months') or 36)}개월 평균보다 낮아야 매수 (적용환율=메리츠 API 값, 평균=FRED USD/KRW 일별 종가 평균 — 출처·기준이 달라 같은 잣대가 아님)",
                      f" • (b) 7일 전보다 {x:g}% 이상 오르면 건너뜀 (건너뜀 % = {x:g}%, 넣을 수 있는 값 0.5~3.0, 0.5 단위)",
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
    _send(tg, "SGOV 메뉴 · 아래 버튼을 눌러 주세요", kb(SGOV_MENU_ROWS))


# ---------------------------------------------------------- 버튼·입력 처리 (등록된 채팅방 확인은 office_secretary.main 이 이미 함)
def _expired(rec, sec, now):
    return not rec or now - float(rec.get("ts") or 0) > sec


def _req(tg, st, rtype, args=None, label=""):
    rid = send_request(st, rtype, args, label)
    if not rid:
        _send(tg, "요청을 보내지 못했어요 (대기 중 요청이 많거나 파일 쓰기 실패). 잠시 뒤 다시 해 주세요.", main_kb())
    else:
        _send(tg, f"{label or rtype} 요청을 메리츠 적립봇에 보냈어요. 결과가 오면 알려 드릴게요 (최대 {RESULT_TIMEOUT_SEC}초).", main_kb())
    return rid


def _explain(name, now, rng, meaning, effect, example):
    return (f"[{name}]\n지금 값: {now}\n넣을 수 있는 값: {rng}\n무슨 뜻: {meaning}\n"
            f"바꾸면: {effect} (주문·환전은 바로 나가지 않아요)\n새 값을 숫자로 보내 주세요. 예: {example}\n"
            "(10분 안 · 다른 버튼을 누르면 취소)")


_EMO = re.compile("(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u25A0-\u25FF\u2300-\u23FF\u2900-\u297F\uFE0F\u200D])+ ?")


def _num(raw):
    """숫자 글자 → float 또는 None (쉼표·$ 허용, 무한·NaN 거부)"""
    t = raw.replace(",", "").replace("$", "").strip()
    if not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)", t):
        return None
    return float(t)


def _ask_confirm(tg, st, rtype, args, label, before, after, now):
    st["sgov_cfm"] = {"type": rtype, "args": args, "label": label, "ts": now}
    _send(tg, f"[{label}] 바꿀까요?\n지금 값 → 새 값\n{before} → {after}\n"
              f"{CONFIRM_SEC}초 안에 [{CFM_OK}]를 눌러 주세요. 주문·환전은 나가지 않고 설정 값만 바뀌어요.", main_kb([CFM_OK, FX_CANCEL]))


def show_funds(tg, st, snap, stale, age):
    _send(tg, funds_text(snap, stale, age), main_kb(["자동환전 실행", "시드·SGOV"], ["분배금 기록", "메뉴"]))


def show_rules(tg, st, snap, stale, age):
    st["menu_ctx"] = "sgov"
    if not snap:
        _send(tg, "환율 규칙: 미확인 (메리츠 적립봇 상태 파일 없음)", kb(SGOV_MENU_ROWS)); return
    _send(tg, skip_text(snap, stale, age), main_kb(*skip_rows(snap)))


def handle(tg, st, raw, other_labels=()):
    """SGOV 메뉴 글자면 처리하고 True. 아니면 False (기존 비서봇 처리로 넘어감)"""
    raw = _EMO.sub("", raw or "").strip()   # 예전 키보드(이모티콘 글자)가 폰에 남아 있어도 같은 버튼으로 읽음
    now = time.time()
    if raw in CTX_LABELS and st.get("menu_ctx") != "sgov":
        return False   # 다른 메뉴의 같은 글자 버튼은 건드리지 않음
    aw = st.get("sgov_await")
    snap_now = snapshot(now)
    # 숫자 입력 대기 중: 버튼 글자가 아니면 입력으로 처리 (버튼을 누르면 입력 대기 해제)
    if aw and raw not in FIXED and raw not in other_labels and raw not in (FX_RUN, FX_CANCEL, MENU_OPEN) \
            and raw not in CTX_LABELS and not raw.startswith("/") and not X_RE.match(raw) and raw not in _cap_labels():
        st.pop("sgov_await", None)
        if _expired(aw, AWAIT_SEC, now):
            _send(tg, "입력 시간이 지났어요. 다시 눌러 주세요.", kb(SGOV_MENU_ROWS)); return True
        v = _num(raw)
        if aw.get("kind") == "seed" and aw.get("key") in SEED_LABELS:
            key = aw["key"]; is_int = key in ("tranches_total", "interval_days")
            if v is None or v <= 0 or (is_int and v != int(v)):
                _send(tg, f"{SEED_LABELS[key]}: " + ("0보다 큰 정수만 넣을 수 있어요." if is_int else "0보다 큰 숫자만 넣을 수 있어요.") + " 다시 눌러 주세요.", main_kb(["메뉴"])); return True
            sgv = (snap_now[0] or {}).get("sgov") or {}
            _ask_confirm(tg, st, "sgov_seed", {"key": key, "value": raw}, f"{SEED_LABELS[key]} 변경", sgv.get(key, "미확인"), raw, now)
        elif aw.get("kind") == "dist":
            if v is None or v <= 0:
                _send(tg, "분배금은 0보다 큰 달러 숫자만 넣을 수 있어요. 다시 눌러 주세요.", main_kb(["메뉴"])); return True
            _ask_confirm(tg, st, "sgov_dist", {"amount": raw}, "분배금 기록", "장부에 아직 없음", f"{raw} 달러 추가", now)
        elif aw.get("kind") == "skipx":
            ok = v is not None and SKIP_X_MIN <= v <= SKIP_X_MAX and abs(v * 2 - round(v * 2)) < 1e-9
            if not ok:
                _send(tg, "건너뜀 %는 0.5~3.0 사이, 0.5 단위로만 넣을 수 있어요. (예: 1.5) 다시 눌러 주세요.", main_kb(["메뉴"])); return True
            cur = float((((snap_now[0] or {}).get("sgov") or {}).get("skip_jump_pct")) or 1.5)
            _ask_confirm(tg, st, "sgov_x", {"x": v}, "건너뜀 % 변경", f"{cur:g}%", f"{v:g}%", now)
        return True
    if raw in FIXED or raw in other_labels or raw in (FX_RUN, FX_CANCEL, MENU_OPEN) or raw in CTX_LABELS or raw.startswith("/") \
            or X_RE.match(raw) or raw in _cap_labels():
        st.pop("sgov_await", None)
    snap, stale, age = snapshot(now)
    if raw == CHART:
        show_chart(tg, st); return True
    if raw == MENU_OPEN or raw == "메뉴":
        show_menu(tg, st); return True
    if raw in ("도구", "환율 규칙", "건너뜀 모드"):
        st["menu_ctx"] = "sgov"
        show_rules(tg, st, snap, stale, age); return True
    if raw == "도움말" and st.get("menu_ctx") == "sgov":
        _send(tg, HELP, kb(SGOV_MENU_ROWS)); return True
    if raw in ("자금", "자금·SGOV"):
        st["menu_ctx"] = "sgov"
        show_funds(tg, st, snap, stale, age); return True
    if raw == "SGOV 현황":
        body = (snap or {}).get("sgov_view_text") or "SGOV 현황: 미확인"
        _send(tg, _snap_line(snap, stale, age) + ("\n아래 값은 미확인 (오래된 스냅샷)" if stale and snap else "") + "\n" + body, main_kb()); return True
    if raw == "시드·SGOV":
        _send(tg, seed_text(snap, stale, age), main_kb(*[[l] for l in SEED_LABELS.values()], ["메뉴"])); return True
    if raw in SEED_BY_LABEL:
        key = SEED_BY_LABEL[raw]
        st["sgov_await"] = {"kind": "seed", "key": key, "ts": now}
        sgv = (snap or {}).get("sgov") or {}
        rng = "0보다 큰 정수 (상한 없음)" if key in ("tranches_total", "interval_days") else "0보다 큰 달러 숫자 (개별 상한 없음)"
        _send(tg, _explain(raw, sgv.get(key, "미확인") if snap else "미확인", rng,
                           "SGOV 회차 적립의 금액·횟수 기준(시드)이에요. 저장할 때 6번이 1회차 ≤ 회차 금액, 합계가 총 목표의 99~101% 같은 검사를 다시 해요.",
                           "다음 회차 판단부터 새 시드로 계산해요. 검사에 걸리면 이유와 함께 저장하지 않아요", "100"), main_kb(["메뉴"])); return True
    if raw == "분배금 기록":
        st["sgov_await"] = {"kind": "dist", "ts": now}
        sg0 = (snap or {}).get("sgov") or {}
        _send(tg, _explain("SGOV 분배금 기록", "누적 " + _m(((sg0.get("ledger") or {}).get("distributions_usd"))) if snap else "미확인",
                           "0보다 큰 달러 숫자 (상한 없음)", "SGOV가 준 분배금이에요. 들어온 금액을 장부에 적어요.",
                           "SGOV 장부·대기 달러에만 더하고 다음 회차에 재투자해요 (NKE/QLD 와 따로). 장부가 바뀌어요", "12.34"), main_kb(["메뉴"])); return True
    if raw == SK_ASK:
        sgx = (snap or {}).get("sgov") or {}
        cur = float(sgx.get("skip_jump_pct") or 1.5)
        st["sgov_await"] = {"kind": "skipx", "ts": now}
        _send(tg, _explain("건너뜀 %", f"{cur:g}%", "0.5~3.0 사이, 0.5 단위",
                           "7일 전보다 이 % 이상 오르면 그 회차를 건너뛰는 건너뜀 모드 기준이에요.",
                           "다음 회차 판단부터 새 기준을 써요. 건너뛴 회차는 맨 뒤로 붙어요", "1.5"), main_kb(["메뉴"])); return True
    if raw == CFM_OK:
        rec = st.pop("sgov_cfm", None)
        if _expired(rec, CONFIRM_SEC, now):
            _send(tg, "확인 시간이 지났거나 바꿀 값이 없어요. 처음부터 다시 눌러 주세요.", main_kb()); return True
        _req(tg, st, rec["type"], rec["args"], rec["label"]); return True
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
            _send(tg, "확인 시간이 지났어요. 자금·SGOV → 자동환전 실행을 다시 눌러 주세요.", main_kb()); return True
        _req(tg, st, "fx_run", {}, "자동환전 실행"); return True
    if raw == FX_CANCEL and ("sgov_fx_confirm" in st or "sgov_cfm" in st or aw):
        st.pop("sgov_fx_confirm", None); st.pop("sgov_cfm", None)
        show_menu(tg, st); return True
    if raw == "처음 화면":
        return False   # 처음 화면은 office_secretary 가 MENU_KB 로 보여 줌
    return False


def _cap_labels(snap=None):
    if snap is None:
        snap = snapshot()[0]
    out = {}
    for m, t in ((snap or {}).get("cap_modes") or {}).items():
        out[t] = m; out["[선택] " + t] = m
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
            head = ("늦게 도착한 결과 · " if rec.get("timed_out") else "") + f"[{label}] "
            txt = head + {"ok": "", "rejected": "실행 안 함 · ", "expired": "미확인 · ", "invalid": "실행 안 함 · ",
                          "error": "오류 · "}.get(res.get("status"), "") + str(res.get("text") or "")
            if res.get("type") == "fx_preview" and res.get("status") == "ok" and (res.get("data") or {}).get("amount"):
                st["sgov_fx_confirm"] = {"ts": now}
                _send(tg, txt, main_kb([FX_RUN, FX_CANCEL]))
            elif res.get("type") == "snapshot" and res.get("status") == "ok":
                show_chart(tg, st, "새로고침 완료")
            else:
                _send(tg, txt, main_kb())
            continue
        age = now - float(rec.get("ts") or 0)
        if not rec.get("timed_out") and age > RESULT_TIMEOUT_SEC:
            rec["timed_out"] = True
            _send(tg, f"[{label}] 결과 미확인 — {RESULT_TIMEOUT_SEC}초 동안 메리츠 적립봇 응답이 없어요. "
                      "실행됐는지 알 수 없으니 상황판으로 다시 확인해 주세요.", main_kb())
        elif rec.get("timed_out") and age > RESULT_TIMEOUT_SEC + LATE_KEEP_SEC:
            pend.pop(rid, None); _drop_request(rid)
    if not pend:
        st.pop("sgov_req", None)
    waiting = len([1 for v in pend.values() if not v.get("timed_out")])
    try:
        alerts_pass(tg, now)     # 요청 결과 확인을 다 한 뒤에 (결과 확인을 늦추거나 막지 않게)
    except Exception as e:
        print("SGOV 알림 확인 오류:", type(e).__name__, flush=True)
    return waiting


# ---------------------------------------------------------- SGOV 회차 알림 (meritz_dca_bot 이 alerts/ 에 씀 → 여기서 이 방으로 보냄)
ALERT_RE = re.compile(r"^alert_([0-9a-f]{32})\.json$")
ALERT_MAX_AGE = 86400        # 제안(초안): 만든 지 24시간 넘은 알림은 보내지 않고 'expired' 표시만 (비서봇이 오래 꺼져 있던 경우)
SENT_KEEP_SEC = 4 * 86400    # 제안(초안): 표시 파일 보관 4일 (4번의 알림 파일 보관 3일보다 길게)
ALERTS_PER_TICK = 5          # 제안(초안): tick 1번에 최대 5개 (텔레그램 대기·결과 확인 지연 방지)
MAX_ALERT_BYTES = 8192
_PRUNE = {"ts": 0.0}


def _mark(aid, status, extra=None):
    """보냈다/만료 표시 (이 비서봇만 씀 · 원자적: .tmp 로 쓰고 이름 바꿈)"""
    d = BRIDGE / "alerts_sent"
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"sent_{aid}.json.tmp"
    tmp.write_text(json.dumps(dict({"id": aid, "status": status, "ts": time.time()}, **(extra or {})), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, d / f"sent_{aid}.json")


def alerts_pass(tg, now=None):
    """새 알림을 만든 순서대로 보냄 → 보낸 개수. 보내기가 성공한 뒤에만 표시를 남김 (표시가 있으면 다시 보내지 않음)"""
    now = time.time() if now is None else now
    try:
        names = sorted(os.listdir(BRIDGE / "alerts"))
    except OSError:
        names = []
    todo = []
    for n in names:
        m = ALERT_RE.match(n)
        if not m or (BRIDGE / "alerts_sent" / f"sent_{m.group(1)}.json").exists():
            continue
        p = BRIDGE / "alerts" / n
        try:
            if p.stat().st_size > MAX_ALERT_BYTES:
                continue
        except OSError:
            continue
        a = _read(p)
        if not isinstance(a, dict) or str(a.get("id")) != m.group(1) or a.get("from") != "meritz_dca_bot" \
                or not isinstance(a.get("text"), str) or not isinstance(a.get("ts"), (int, float)):
            continue
        todo.append(a)
    todo.sort(key=lambda a: float(a["ts"]))
    sent = 0
    # audit-fix 5-7: 24시간 넘은 알림을 말없이 버리지 않는다 — 요약 재알림 1번을 보낸 뒤에만 'expired' 표시 (못 보내면 다음 tick 에 다시)
    stale = [a for a in todo if now - float(a["ts"]) > ALERT_MAX_AGE]
    if stale:
        kinds = ", ".join(sorted({str(a.get("kind") or "?") for a in stale}))
        oldest = min(stale, key=lambda a: float(a["ts"]))
        r = tg.send(_esc(f"[SGOV 알림 {len(stale)}건이 {int(ALERT_MAX_AGE // 3600)}시간 넘게 못 갔어요]\n• 종류: {kinds}\n• 가장 오래된 알림: {oldest.get('ts_kst') or '-'} KST\n"
                         "• 원문은 이미 낡아서 보내지 않았어요. SGOV 현황·자금 화면에서 지금 상태를 확인해 주세요."))
        if isinstance(r, dict) and r.get("message_id"):
            for a in stale: _mark(a["id"], "expired", {"resent_summary": True})
        todo = [a for a in todo if a not in stale]
    for a in todo:
        if sent >= ALERTS_PER_TICK:
            break
        r = tg.send(_esc(a["text"]))          # 알림 문구 그대로 (html.escape 만) · 버튼 없음 · 이 비서봇의 방
        if not (isinstance(r, dict) and r.get("message_id")):
            break                             # 못 보냄 → 표시 안 함 → 다음 tick 에 다시 (순서 유지)
        _mark(a["id"], "sent", {"message_id": r.get("message_id")})
        sent += 1
    if now - _PRUNE["ts"] >= 3600:
        _PRUNE["ts"] = now
        _prune_marks(now)
    return sent


def _prune_marks(now):
    """보관 기간 지난 표시 파일만 지움 (이 비서봇이 쓴 자기 파일만. alerts/ 는 건드리지 않음)"""
    d = BRIDGE / "alerts_sent"
    try:
        names = os.listdir(d)
    except OSError:
        return 0
    n = 0
    for name in names:
        if not (name.startswith("sent_") and name.endswith(".json")):
            continue
        try:
            if now - (d / name).stat().st_mtime > SENT_KEEP_SEC:
                (d / name).unlink(); n += 1
        except OSError:
            pass
    return n
