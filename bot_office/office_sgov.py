# ==========================================================
# FILE: /opt/bot-office/office_sgov.py   (OFFICE_SGOV — 새 파일)
# 사무실 v1.9.8 (2026-11-26, 판50 SGOV 레이더): 상황판을 📡 [SGOV 레이더] 형식으로 바꿈 (토스 스나이퍼 레이더 기준). 스냅샷에 있는 값만 씀.
# 사무실 v1.9.7 (2026-11-26, 판49 처음 화면 고침): 예전 키보드의 이모티콘 없는 "처음 화면"도 처음 화면으로 받음.
# 사무실 v1.9.6 (2026-11-26, 판48 최소 UI): SGOV 메뉴 전부 제거 — 상황판 + [자동환전 실행]·[새로고침]만 남김.
#   설정(시드·건너뜀·분배금·게이트·SGOV 켜기/끄기)은 텔레그램 버튼이 아니라 뮤즈랑 대화로 바꿈 (같은 bridge 요청 파일을 씀).
#   매일 09:00 KST 상황판 자동 발송은 office_secretary.main 에서 show_chart 를 부름.
#   옛 메뉴 버튼(폰에 남은 예전 키보드)은 안내만 보여 주고 메뉴는 안 엶.
# 사무실 v1.9.5 (2026-11-20, audit-fix-v2 5-1·5-2·5-7): 총 회차 수 증가 문구·관문 출처 주의 문구·24시간 넘은 알림은 요약 재알림 1번(보낸 뒤에만 expired 표시)
# 사무실 v1.8.3 (2026-11-14): 비서봇 SGOV 메뉴 (상황판·현황·자금·시드·분배금·건너뜀 모드·게이트 확인)
#  - 읽기만: meritz_dca_bot 이 만든 상태 스냅샷 <bridge>/snapshot.json
#  - 명령(자동환전)은 요청 파일만 씀: <bridge>/requests/req_<id>.json
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
CONFIRM_SEC = 120           # 자동환전 [실행] 확인 유효 시간 (제안값)
MAX_PENDING = 5

CHART = "상황판"
FX_RUN, FX_CANCEL, REFRESH = "실행", "취소", "새로고침"
FX_PREVIEW = "자동환전 실행"
# 옛 메뉴 버튼 글자 (폰에 남은 예전 키보드를 눌렀을 때 안내만 보여 주고 메뉴는 안 엶)
OLD_MENU_LABELS = {"메뉴", "자금", "환율 규칙", "SGOV 현황", "도움말", "시드·SGOV", "자금·SGOV",
                   "분배금 기록", "건너뜀 % 바꾸기", "건너뜀 모드", "게이트 확인", "SGOV 켜기", "SGOV 끄기",
                   "재점검 완료 · 다음 회차부터 다시 판단", "변경 확인", "도구", "SGOV 총 목표", "SGOV 회차 금액",
                   "SGOV 1회차 금액", "SGOV 총 회차 수", "SGOV 회차 간격(일)"}
MENU_GONE = "메뉴는 없어졌어요. 상황판이랑 자동환전만 남아요. 설정(시드·건너뜀·분배금·SGOV 켜기/끄기)은 뮤즈랑 대화로 바꿔 주세요."
X_RE = re.compile(r"^(?:\[선택\] )?X ([0-9]+(?:\.[0-9]+)?)%$")   # 옛 건너뜀 % 버튼 글자도 알아봄 (예전 키보드가 남아 있을 때)
_EMO = re.compile("(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u25A0-\u25FF\u2300-\u23FF\u2900-\u297F\uFE0F\u200D])+ ?")


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
    return kb([[CHART], *extra])


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


def radar_text(snap, stale, age):
    """📡 [SGOV 레이더] — 토스 스나이퍼 레이더 형식. 스냅샷에 있는 값만 씀 (없는 값은 빼).
    판50: 상황판(B2)을 레이더(D1) 형식으로 바꿈. SGOV 현재가는 스냅샷에 없어서 빼고 분배금 누적만 씀.
    [이번 회차]는 마지막으로 끝난 회차(최근 판단), [다음 회차]는 다음 예정일."""
    if not snap:
        return "[SGOV 레이더]\n" + _snap_line(snap, stale, age)
    sg = snap.get("sgov") or {}
    lg = sg.get("ledger") or {}
    done, total = _i(sg.get("tranches_done")), _i(sg.get("tranches_total"))
    q, pr = float(lg.get("qty") or 0), float(lg.get("principal") or 0)
    ld = sg.get("last_decision") or {}
    act = {"buy": "관문 통과 (매수)", "skip_a": "건너뜀 (a 평균 환율)", "skip_b": "건너뜀 (b 7일 상승)"}.get(ld.get("action"), "-")
    next_due = sg.get("next_due_date") or "-"
    lines = ["📡 [SGOV 레이더] (" + ("🟢 가동중" if sg.get("enabled") else "🔴 꺼짐") + f" · 다음 회차 {next_due})"]
    if stale:
        lines.append("아래 값은 마지막 스냅샷 기준이라 미확인이에요. 새로고침을 눌러 주세요.")
    lines += [
        f"💵 분배금 누적 {_m(lg.get('distributions_usd'))}",
        f"🔄 [이번 회차] 회차 {done} · {_m(sg.get('tranche_usd'))} · {act}" + (f" ({ld.get('date')})" if ld.get("date") else ""),
        f"🏛️ [보유] {q:g}주 · 원금 {_m(pr)}",
        f"🎯 [다음 회차] {next_due} · {_m(snap.get('sgov_tranche_now'))}",
        f"💰 [대기 달러] {_m(sg.get('wait_usd'))}",
        f"🕐 {snap.get('ts_kst', '-') or '-'} KST",
    ]
    for p in (snap.get("sgov_problems") or [])[:5]:
        lines.append("설정 확인 필요: " + str(p))
    return "\n".join(lines)


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


def _send(tg, text, rows):
    tg.send(_esc(text), keyboard=rows)


def show_chart(tg, st, notice=""):
    snap, stale, age = snapshot()
    _send(tg, (notice + "\n\n" if notice else "") + radar_text(snap, stale, age), main_kb([FX_PREVIEW, REFRESH]))


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


def _cap_labels(snap=None):
    if snap is None:
        snap = snapshot()[0]
    out = {}
    for m, t in ((snap or {}).get("cap_modes") or {}).items():
        out[t] = m; out["[선택] " + t] = m
    return out


def handle(tg, st, raw, other_labels=()):
    """SGOV 상황판·자동환전 글자면 처리하고 True. 아니면 False (기존 비서봇 처리로 넘어감)"""
    raw = _EMO.sub("", raw or "").strip()   # 예전 키보드(이모티콘 글자)가 폰에 남아 있어도 같은 버튼으로 읽음
    now = time.time()
    if raw in other_labels:
        return False   # 비서봇 버튼(처음 화면·도움말)은 건드리지 않음
    snap, stale, age = snapshot(now)
    if raw == CHART:
        show_chart(tg, st); return True
    if raw == FX_PREVIEW:
        _req(tg, st, "fx_preview", {}, "자동환전 금액 확인"); return True
    if raw == FX_RUN and "sgov_fx_confirm" in st:
        rec = st.pop("sgov_fx_confirm")
        if _expired(rec, CONFIRM_SEC, now):
            _send(tg, "확인 시간이 지났어요. 상황판 → 자동환전 실행을 다시 눌러 주세요.", main_kb()); return True
        _req(tg, st, "fx_run", {}, "자동환전 실행"); return True
    if raw == FX_CANCEL and "sgov_fx_confirm" in st:
        st.pop("sgov_fx_confirm", None)
        show_chart(tg, st); return True
    if raw == REFRESH:
        _req(tg, st, "snapshot", {}, "새로고침"); return True
    if raw == "처음 화면":
        return False   # 처음 화면은 office_secretary 가 MENU_KB 로 보여 줌
    # 옛 메뉴 버튼 (폰에 남은 예전 키보드) — 안내만 보여 주고 메뉴는 안 엶
    if raw in OLD_MENU_LABELS or X_RE.match(raw) or raw in _cap_labels(snap):
        _send(tg, MENU_GONE, main_kb()); return True
    return False


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
                         "• 원문은 이미 낡아서 보내지 않았어요. 상황판에서 지금 상태를 확인해 주세요."))
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
