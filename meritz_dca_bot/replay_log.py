# -*- coding: utf-8 -*-
# =====================================================================
# FILE: replay_log.py   (3번 toss_dca_bot · 4번 bithumb_laoeo_bot 공통 · 두 폴더에 같은 파일)
# 버전: replay_log 1.0.0 (2026-10-28) — 3번 v4.3.5 · 4번 v4.0.4 와 함께 추가
#
# 목적: 저장소 start.md 규칙대로 "사용자가 한 일 → 판단 → 외부 호출 → 결과 → 사용자에게 보인 것"을
#       로그만으로 다시 재생(replay)할 수 있게 한 줄 JSON 으로 남긴다.
#
#  · 일반 로그  logs/events-YYYY-MM-DD.jsonl (UTC 날짜, 14일 보관) + 같은 내용 한 줄 요약을 stdout(서버 저널)
#      - 종목·수량·가격·금액·잔고·채팅 식별자·토큰은 넣지 않는다. 종목/주문번호는 이 서버에서만 풀리는 짧은 참조값(ref)
#  · 감사 로그  logs/audit-YYYY-MM-DD.jsonl (권한 600, 14일 보관)
#      - 돈과 관련된 판단 입력·주문 내용·보낸 메시지 본문은 여기에만. 일반 로그에는 audit_ref 로 연결
#  · 폴링·스케줄러 같은 반복 성공은 카운터로 모아 10분마다 1줄 요약 (start.md 3절)
#  · 같은 오류는 1시간 안에 처음 1번만 트레이스백 전문, 이후는 횟수 요약
#  · 실패해도 봇 동작에는 영향 없음 (로그 쓰기 오류는 조용히 무시)
#
#  재생 (서버에서):  python3 replay_log.py --last 30          최근 30줄 (일반 로그)
#                    python3 replay_log.py <correlation_id>   그 ID 의 흐름 (일반 + 감사)
#                    python3 replay_log.py --scan             일반 로그에 금지 값(토큰·긴 숫자·경로)이 없는지 검사
# =====================================================================
import contextvars
import glob
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

RL_VERSION = "1.0.0"
KST = timezone(timedelta(hours=9))
KEEP_DAYS = 14
MAX_FILE_BYTES = 20 * 1024 * 1024
SUMMARY_EVERY = 600          # 카운터 요약 주기(초)
ERROR_WINDOW = 3600          # 같은 오류 묶음 시간(초)

_lock = threading.Lock()
_cid = contextvars.ContextVar("replay_cid", default="")
_S = {"service": "", "version": "", "dir": "", "base": "", "salt": b"", "ready": False,
      "counts": {}, "last_flush": time.time(), "errors": {}, "once": {}, "once_day": "",
      "last_ok": {}, "cleaned": ""}

# 일반 로그에 들어가면 안 되는 필드 이름 (값이 있어도 버림)
_DENY = {"chat_id", "chat", "token", "secret", "password", "authorization", "access_key", "secret_key", "api_key",
         "account", "account_seq", "balance", "amount", "qty", "quantity", "price", "volume", "avg", "avg_price",
         "cur_price", "profit", "pnl", "krw", "usd", "text", "sym", "symbol", "coin", "client_order_id",
         "broker_order_id", "order_id", "response", "error_text"}
_SECRET_RE = [
    (re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_-]{30,}"), "<tg-token>"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer <hidden>"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"), "<jwt>"),
    (re.compile(r"(?i)(token|secret|password|access_key|secret_key|api_key|authorization)(\W{1,3})[^\s\"',}]+"), r"\1\2<hidden>"),
]
_PATH_RE = re.compile(r"(/home|/opt|/var|/etc|/root|/usr|/tmp)/[^\s\"',)]+")
_LONGNUM_RE = re.compile(r"(?<![\w.])\d[\d,]{6,}(?:\.\d+)?")     # 7자리 이상 숫자 (채팅 ID·계좌·금액)


def _now():
    return datetime.now(timezone.utc)


def setup(service, version, base_dir):
    """봇 시작 때 1번. 로그 폴더·참조값용 비밀 소금(이 서버에만) 준비."""
    try:
        d = os.path.join(base_dir, "logs")
        os.makedirs(d, exist_ok=True)
        salt_p = os.path.join(d, ".replay_salt")
        if not os.path.exists(salt_p):
            fd = os.open(salt_p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(16))
        _S.update(service=service, version=version, dir=d, base=base_dir,
                  salt=open(salt_p, encoding="utf-8").read().strip().encode(), ready=True)
        _cleanup()
    except Exception:
        _S["ready"] = False


def ref(value):
    """종목·주문번호 등 → 이 서버에서만 같은 값이 나오는 8자리 참조값 (원값은 감사 로그에만)."""
    if value in (None, ""):
        return None
    return "r" + hashlib.sha256(_S["salt"] + str(value).encode()).hexdigest()[:8]   # 숫자만 나와 가림에 걸리지 않게 글자로 시작


# ---------------------------------------------------------------- correlation_id
def new_cid(kind, *parts):
    tail = "-".join(str(p) for p in parts if p not in (None, ""))
    cid = f"{kind}-{tail}" if tail else f"{kind}-{_now().strftime('%H%M%S')}-{secrets.token_hex(2)}"
    _cid.set(cid)
    return cid


def set_cid(cid):
    _cid.set(cid or "")


def cid():
    return _cid.get()


# ---------------------------------------------------------------- 값 정리
def _clean_str(s, general=True):
    s = str(s)
    for r, rep in _SECRET_RE:
        s = r.sub(rep, s)
    if _S["base"]:
        s = s.replace(_S["base"], "<bot>")
    s = _PATH_RE.sub("<path>", s)
    if general:
        s = _LONGNUM_RE.sub("<num>", s)
    return s[:300]


def _clean(v, general=True, depth=0):
    if depth > 3:
        return "<deep>"
    if isinstance(v, dict):
        out = {}
        for k, x in list(v.items())[:40]:
            if general and str(k).lower() in _DENY:
                continue
            out[str(k)[:40]] = _clean(x, general, depth + 1)
        return out
    if isinstance(v, (list, tuple)):
        return [_clean(x, general, depth + 1) for x in list(v)[:30]]
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        if general and abs(v) >= 1_000_000:
            return "<num>"
        return v
    return _clean_str(v, general)


def _write(kind, rec):
    if not _S["ready"]:
        return
    day = rec["ts_utc"][:10]
    p = os.path.join(_S["dir"], f"{kind}-{day}.jsonl")
    line = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
    with _lock:
        try:
            if os.path.exists(p) and os.path.getsize(p) > MAX_FILE_BYTES and rec.get("level") not in ("ERROR", "WARN"):
                return
            new = not os.path.exists(p)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
            if new and kind == "audit":
                os.chmod(p, 0o600)
        except Exception:
            pass


def _base(event_type, event, outcome, reason, actor, level):
    t = _now()
    return {"ts_utc": t.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "ts_kst": t.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S"),
            "correlation_id": cid() or "none", "service": _S["service"], "actor": actor,
            "event_type": event_type, "event": event, "outcome": outcome, "reason": reason,
            "version": _S["version"], "level": level}


# ---------------------------------------------------------------- 기록
def ev(event_type, event, outcome="ok", reason=None, actor="system", level="INFO", **data):
    """일반 로그 1줄. event_type: user_event / decision / external_call / state_change / user_visible"""
    try:
        if outcome in ("failed", "skipped", "partial", "cancelled") and not reason:
            reason = "unspecified"   # 이유 없는 실패·건너뜀은 start.md 상 버그 → 표시해 둠
        rec = _base(event_type, event, outcome, reason, actor, level)
        if data:
            rec["data"] = _clean(data, general=True)
        _write("events", rec)
        if level != "DEBUG":
            extra = " ".join(f"{k}={v}" for k, v in (rec.get("data") or {}).items() if not isinstance(v, (dict, list)))[:220]
            print(f"[{level}] {event_type}.{event} {outcome}" + (f" reason={reason}" if reason else "")
                  + f" cid={rec['correlation_id']}" + (f" {extra}" if extra else ""), flush=True)
        if outcome == "ok":
            _S["last_ok"][event_type] = rec["ts_utc"]
        _maybe_flush()
    except Exception:
        pass


def audit(event, **data):
    """감사 로그 1줄 (금액·종목·주문 내용·메시지 본문). 일반 로그에 넣을 audit_ref 를 돌려줌."""
    try:
        rec = _base("audit", event, "ok", None, "system", "INFO")
        rec["audit_ref"] = "a" + secrets.token_hex(4)   # 글자로 시작 (숫자 가림에 안 걸리게)
        rec["data"] = _clean(data, general=False)
        _write("audit", rec)
        return rec["audit_ref"]
    except Exception:
        return None


def count(name, n=1):
    """반복 성공(폴링·스케줄러 틱 등)은 세기만 하고 10분마다 요약."""
    try:
        with _lock:
            _S["counts"][name] = _S["counts"].get(name, 0) + n
        _maybe_flush()
    except Exception:
        pass


def once(key):
    """오늘(UTC) 처음이면 True — 같은 건너뜀 이유를 50초마다 찍지 않기 위해."""
    day = _now().strftime("%Y-%m-%d")
    with _lock:
        if _S["once_day"] != day:
            _S["once_day"], _S["once"] = day, {}
        if key in _S["once"]:
            return False
        _S["once"][key] = 1
        return True


def err(event, exc, reason=None, event_type="external_call", **data):
    """오류: 같은 종류는 1시간에 처음 1번만 트레이스백 전문, 이후는 횟수만 (요약은 flush 때)."""
    try:
        reason = reason or reason_of(exc)
        sig = f"{event}|{type(exc).__name__}|{_clean_str(str(exc))[:80]}"
        nowt = time.time()
        with _lock:
            e = _S["errors"].get(sig)
            first = e is None or nowt - e["first"] > ERROR_WINDOW
            if first:
                _S["errors"][sig] = {"first": nowt, "last": nowt, "n": 1, "event": event, "reason": reason,
                                     "event_type": event_type, "cid": cid()}
            else:
                e["n"] += 1
                e["last"] = nowt
        if first:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-1500:]
            ev(event_type, event, "failed", reason, level="ERROR", error=f"{type(exc).__name__}: {exc}",
               trace=tb, **data)
        else:
            count(f"error_repeat:{event}")
    except Exception:
        pass


def reason_of(exc):
    s = str(exc)
    m = re.search(r"API HTTP (\d{3})", s)
    if m:
        return f"api_http_{m.group(1)}"
    if "timeout" in s.lower() or "timed out" in s.lower() or type(exc).__name__ in ("TimeoutError", "ReadTimeout"):
        return "timeout"
    if "connect" in s.lower():
        return "connection_error"
    return type(exc).__name__.lower()


def tick():
    _maybe_flush()


def _maybe_flush(force=False):
    if not force and time.time() - _S["last_flush"] < SUMMARY_EVERY:
        return
    with _lock:
        counts, _S["counts"] = _S["counts"], {}
        span = int(time.time() - _S["last_flush"])
        _S["last_flush"] = time.time()
        reps = []
        for sig, e in list(_S["errors"].items()):
            if e["n"] > 1:
                reps.append(e.copy())
                e["n"] = 1
            if time.time() - e["last"] > ERROR_WINDOW:
                _S["errors"].pop(sig, None)
    rec = _base("state_change", "periodic_summary", "ok", None, "system", "INFO")
    rec["data"] = {"window_sec": span, "counts": counts, "last_ok": dict(_S["last_ok"])}
    _write("events", rec)
    print(f"[INFO] summary {span}s counts={json.dumps(counts, ensure_ascii=False)[:300]}", flush=True)
    for e in reps:
        r = _base(e["event_type"], e["event"], "failed", e["reason"], "system", "WARN")
        r["correlation_id"] = e["cid"] or "none"
        r["data"] = {"repeat_count": e["n"] - 1,
                     "first_utc": datetime.fromtimestamp(e["first"], timezone.utc).isoformat(timespec="seconds"),
                     "last_utc": datetime.fromtimestamp(e["last"], timezone.utc).isoformat(timespec="seconds")}
        _write("events", r)
        print(f"[WARN] {e['event']} 같은 오류 {e['n'] - 1}회 더 (reason={e['reason']})", flush=True)
    _cleanup()


def _cleanup():
    day = _now().strftime("%Y-%m-%d")
    if _S["cleaned"] == day or not _S["dir"]:
        return
    _S["cleaned"] = day
    cut = (_now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for p in glob.glob(os.path.join(_S["dir"], "events-*.jsonl")) + glob.glob(os.path.join(_S["dir"], "audit-*.jsonl")):
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.jsonl$", p)
        if m and m.group(1) < cut:
            try:
                os.remove(p)
            except Exception:
                pass


# ---------------------------------------------------------------- 텔레그램 기록 도우미
def tg_result(method, payload, res, ms=None):
    """텔레그램 호출 결과 → user_visible (보낸 본문은 감사 로그에만)."""
    try:
        if method in ("sendMessage", "editMessageText", "deleteMessage"):
            ok = bool(res and res.get("ok"))
            desc = str((res or {}).get("description", ""))
            not_mod = "not modified" in desc
            mid = ((res or {}).get("result") or {}).get("message_id") if isinstance((res or {}).get("result"), dict) else None
            mid = mid or (payload or {}).get("message_id")
            text = str((payload or {}).get("text", ""))
            kb = (payload or {}).get("reply_markup", {}).get("inline_keyboard", []) if isinstance((payload or {}).get("reply_markup"), dict) else []
            buttons = [button(b.get("callback_data", "")) for row in kb for b in row if isinstance(b, dict)]
            aref = audit("tg_" + method, message_id=mid, text=text[:1500], ok=ok, description=desc[:200])
            ev("user_visible", {"sendMessage": "tg_send", "editMessageText": "tg_edit", "deleteMessage": "tg_delete"}[method],
               "ok" if ok else ("skipped" if not_mod else "failed"),
               None if ok else ("not_modified" if not_mod else (f"tg_{(res or {}).get('error_code', 'no_response')}")),
               level="INFO" if ok or not_mod else "WARN",
               message_id=mid, title=_title(text), text_len=len(text), text_sha=hashlib.sha256(text.encode()).hexdigest()[:10],
               buttons=sorted(set(buttons))[:12], ms=ms, audit_ref=aref)
        elif method == "answerCallbackQuery":
            count("tg_answer_callback" if res and res.get("ok") else "tg_answer_callback_fail")
        else:
            count(f"tg_{method}")
    except Exception:
        pass


def button(data):
    """버튼 콜백 → 동작 이름만 (종목·숫자 부분은 뺌). 예: trade_on_QLD → trade_on, prof_10_20 → prof, ask_buy → ask_buy"""
    keep = []
    for part in re.split(r"[_|]", str(data or "")):
        if not re.fullmatch(r"[a-z]+[a-z0-9]*", part) or re.fullmatch(r"\d+", part):
            break
        keep.append(part)
    return "_".join(keep)[:30] or "other"


def _title(text):
    """메시지 첫 줄의 [제목]만 (숫자·종목 섞이면 가림)."""
    first = (text or "").strip().split("\n", 1)[0]
    m = re.search(r"\[([^\]]{1,40})\]", first)
    t = m.group(1) if m else first[:30]
    t = re.sub(r"\b[A-Z]{2,6}\b|\d+", "#", t)
    return t[:40]


# ---------------------------------------------------------------- 재생 도구 (서버에서 직접 실행)
def _load(kind, days=2):
    out = []
    files = sorted(glob.glob(os.path.join(_S["dir"], f"{kind}-*.jsonl")))[-days:]
    for p in files:
        try:
            for ln in open(p, encoding="utf-8"):
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
        except Exception:
            pass
    return out


def _fmt(r):
    d = r.get("data") or {}
    keys = " ".join(f"{k}={v}" for k, v in d.items() if k not in ("trace", "text") and not isinstance(v, (dict, list)))
    return (f"{r.get('ts_kst', '')} KST [{r.get('level', '')}] {r.get('event_type')}.{r.get('event')} "
            f"{r.get('outcome')}{' reason=' + str(r['reason']) if r.get('reason') else ''} cid={r.get('correlation_id')} {keys}")[:400]


def _scan():
    bad = 0
    pats = [re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_-]{30,}"), re.compile(r"(?i)bearer\s+\w"),
            _PATH_RE, re.compile(r"(?<![\w.<])\d{7,}(?![\w>])")]
    for r in _load("events", days=KEEP_DAYS):
        s = json.dumps(r, ensure_ascii=False)
        s = s.replace(r.get("ts_utc", ""), "").replace(r.get("ts_kst", ""), "")
        for p in pats:
            if p.search(s):
                bad += 1
                print("⚠️", p.pattern[:30], "→", _fmt(r)[:200])
                break
    print("✅ 일반 로그 금지 값 검사 통과" if bad == 0 else f"⛔ 금지 값 의심 {bad}줄")
    return bad


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    _S.update(dir=os.path.join(here, "logs"), base=here)
    try:
        _S["salt"] = open(os.path.join(_S["dir"], ".replay_salt"), encoding="utf-8").read().strip().encode()
    except Exception:
        pass
    a = sys.argv[1:]
    if not a or a[0] == "--last":
        n = int(a[1]) if len(a) > 1 else 30
        for r in _load("events")[-n:]:
            print(_fmt(r))
    elif a[0] == "--scan":
        sys.exit(1 if _scan() else 0)
    else:
        want = a[0]
        rows = [("·", r) for r in _load("events") if r.get("correlation_id") == want]
        rows += [("$", r) for r in _load("audit") if r.get("correlation_id") == want]
        rows.sort(key=lambda x: x[1].get("ts_utc", ""))
        for mark, r in rows:
            print(mark, _fmt(r) if mark == "·" else f"{r.get('ts_kst')} KST [감사] {r.get('event')} ref={r.get('audit_ref')} "
                  + json.dumps(r.get("data"), ensure_ascii=False)[:300])
        if not rows:
            print("해당 ID 기록 없음")
