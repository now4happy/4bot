# =====================================================================
# FILE: meritz_dca_bot/bridge.py   (MERITZ_DCA v1.2.6 — 새 파일)
# 비서봇(bot_office/office_sgov.py) ↔ 메리츠 적립봇(meritz_dca_bot) 요청·결과·상태 스냅샷 파일 (표준 라이브러리만).
# v1.2.6 (2026-11-14): 첫 버전.
#   - SGOV 설정·장부의 주인은 meritz_dca_bot 하나뿐. 비서봇은 설정(/etc/meritz-accum/settings.json)·장부(dca_config*.json)를 쓰지 않음.
#   - 파일마다 쓰는 쪽은 하나만:
#       <bridge>/snapshot.json        meritz_dca_bot 만 씀 (비서봇은 읽기만)
#       <bridge>/requests/req_<id>.json  비서봇만 씀 (meritz_dca_bot 은 읽기만 · 지우지도 않음)
#       <bridge>/results/res_<id>.json   meritz_dca_bot 만 씀 (비서봇은 읽기만)
#   - <bridge> 기본값: settings.bridge_dir, 없으면 state_dir/bridge (= /var/lib/meritz-dca/bridge)
#   - 같은 요청 두 번 실행 막기: 결과 파일이 있으면(처리 중 'processing' 포함) 다시 실행하지 않음. 실행 전에 'processing' 결과를 먼저 씀.
#   - 오래된 요청(REQ_TTL_SEC 초과)·미래 시각·형식 오류는 실행하지 않고 그 사유를 결과에 씀.
#   - 키·토큰은 이 파일들에 넣지 않음.
# v1.2.7 (2026-11-14): SGOV 알림 파일 추가 — <bridge>/alerts/alert_<id>.json (meritz_dca_bot 만 씀, 비서봇은 읽기만).
#   비서봇이 보낸 뒤 남기는 표시 <bridge>/alerts_sent/sent_<id>.json 은 비서봇만 씀 (여기서는 읽지도 쓰지도 않음).
#   기존 snapshot.json·requests/·results/ 의 형식·동작은 그대로.
# =====================================================================
import hashlib
import json
import os
import re
import time

REQ_RE = re.compile(r"^req_([0-9a-f]{32})\.json$")
REQ_TTL_SEC = 60            # 제안값(근거 파일에 없음): 비서봇 결과 기다림(OFFICE_SGOV 120초)보다 짧게 → 비서봇이 '미확인'이라 한 뒤 실행되는 일 없음
FUTURE_SKEW_SEC = 10        # 제안값: 요청 시각이 이만큼 넘게 미래면 거부
MAX_REQ_BYTES = 4096        # 제안값: 요청 파일 크기 상한
RESULT_KEEP_SEC = 86400     # 제안값: 결과 파일은 하루 뒤 meritz_dca_bot 이 지움 (자기 파일만)
FILE_MODE = 0o644           # 비서봇(다른 서비스)이 읽을 수 있게. 서비스 사용자·그룹은 미확인 → VERIFY.md 질문
REQ_TYPES = ("snapshot", "fx_preview", "fx_run", "sgov_seed", "sgov_dist", "sgov_x", "sgov_mode",
             "sgov_review_ok", "sgov_enable", "sgov_gate")
FROM = "office_secretary"


def bridge_dir(settings: dict) -> str:
    return str(settings.get("bridge_dir") or os.path.join(settings.get("state_dir") or "/var/lib/meritz-dca", "bridge"))


def snapshot_path(base): return os.path.join(base, "snapshot.json")
def requests_dir(base): return os.path.join(base, "requests")
def results_dir(base): return os.path.join(base, "results")
def result_path(base, rid): return os.path.join(results_dir(base), f"res_{rid}.json")


def write_json_atomic(path, data, mode=FILE_MODE):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def validate_request(rid: str, req, now: float):
    """요청 1개 검사 → (상태, 사유). 상태 None = 실행해도 됨"""
    if not isinstance(req, dict): return "invalid", "형식 오류 (JSON 객체 아님)"
    if str(req.get("id")) != rid: return "invalid", "id 가 파일 이름과 다름"
    if req.get("from") != FROM: return "invalid", "보낸 곳이 비서봇이 아님"
    if req.get("type") not in REQ_TYPES: return "invalid", f"모르는 요청 종류 ({str(req.get('type'))[:20]})"
    if not isinstance(req.get("args", {}), dict): return "invalid", "args 형식 오류"
    try: ts = float(req.get("ts"))
    except (TypeError, ValueError): return "invalid", "시각(ts) 없음"
    if ts - now > FUTURE_SKEW_SEC: return "invalid", "요청 시각이 미래임"
    if now - ts > REQ_TTL_SEC: return "expired", f"요청이 {int(now - ts)}초 지나 실행 안 함 (기준 {REQ_TTL_SEC}초)"
    return None, ""


def pending_requests(base: str, now: float = None):
    """아직 결과가 없는 요청 → [(id, 요청 dict 또는 None, 거부 상태, 사유)] (오래된 순). 읽기만 함"""
    now = time.time() if now is None else now
    rd = requests_dir(base)
    try: names = sorted(os.listdir(rd))
    except OSError: return []
    out = []
    for n in names:
        m = REQ_RE.match(n)
        if not m: continue                      # .tmp 등은 무시 (비서봇이 쓰는 중)
        rid = m.group(1)
        if os.path.exists(result_path(base, rid)): continue
        p = os.path.join(rd, n)
        try:
            if os.path.getsize(p) > MAX_REQ_BYTES:
                out.append((rid, None, "invalid", "요청 파일이 너무 큼")); continue
            with open(p, "r", encoding="utf-8") as f: req = json.load(f)
        except (OSError, ValueError):
            out.append((rid, None, "invalid", "요청 파일을 읽지 못함")); continue
        st, why = validate_request(rid, req, now)
        out.append((rid, req, st, why))
    out.sort(key=lambda x: float((x[1] or {}).get("ts") or 0) if isinstance(x[1], dict) else 0)
    return out


def write_result(base, rid, rtype, status, text, data=None):
    """결과 파일 (meritz_dca_bot 만 씀). status: processing / ok / rejected / expired / invalid / error"""
    write_json_atomic(result_path(base, rid), {"id": rid, "type": rtype, "status": status, "text": str(text)[:3500],
                                               "data": data or {}, "ts": time.time()})


def write_snapshot(base, snap: dict):
    write_json_atomic(snapshot_path(base), snap)


def cleanup_results(base, now=None):
    """하루 지난 결과 파일만 지움 (meritz_dca_bot 이 쓴 자기 파일만. 요청 파일은 건드리지 않음)"""
    now = time.time() if now is None else now
    rd = results_dir(base)
    try: names = os.listdir(rd)
    except OSError: return 0
    n = 0
    for name in names:
        if not (name.startswith("res_") and name.endswith(".json")): continue
        p = os.path.join(rd, name)
        try:
            if now - os.path.getmtime(p) > RESULT_KEEP_SEC: os.remove(p); n += 1
        except OSError: pass
    return n


# ---------------------------------------------------------------- v1.2.7 SGOV 알림 파일 (meritz_dca_bot 만 씀)
ALERT_KEEP_SEC = 3 * 86400      # 제안(초안): 알림 파일 보관 3일 (비서봇 표시 파일 보관 4일보다 짧게 — 표시가 먼저 지워져 다시 가는 일 없게)
ALERT_PRUNE_EVERY = 3600        # 제안(초안): 정리는 알림을 쓸 때 최대 1시간에 1번
_ALERT_PRUNE = {"ts": 0.0}


def alerts_dir(base): return os.path.join(base, "alerts")
def alert_path(base, aid): return os.path.join(alerts_dir(base), f"alert_{aid}.json")


def alert_id(kind: str, day: str, text: str) -> str:
    """같은 날(미국 동부)·같은 종류·같은 문구 = 같은 id → 같은 알림을 두 번 써도 파일 1개 (비서봇은 id 로 1번만 보냄)"""
    return hashlib.sha256(f"{kind}|{day}|{text}".encode("utf-8")).hexdigest()[:32]


def write_alert(base, kind: str, day: str, text: str, now=None):
    """알림 1개 → alerts/alert_<id>.json (원자적). 이미 있으면 다시 쓰지 않음 (처음 쓴 시각 유지) → (id, 새로 썼는지)"""
    now = time.time() if now is None else now
    aid = alert_id(kind, day, text)
    p = alert_path(base, aid)
    if os.path.exists(p):
        return aid, False
    write_json_atomic(p, {"v": 1, "id": aid, "kind": str(kind), "day": str(day), "ts": now,
                          "ts_kst": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now + 9 * 3600)),
                          "text": str(text), "from": "meritz_dca_bot"})
    if now - _ALERT_PRUNE["ts"] >= ALERT_PRUNE_EVERY:
        _ALERT_PRUNE["ts"] = now
        cleanup_alerts(base, now)
    return aid, True


def cleanup_alerts(base, now=None):
    """보관 기간 지난 알림 파일만 지움 (meritz_dca_bot 이 쓴 자기 파일만. alerts_sent/ 는 건드리지 않음)"""
    now = time.time() if now is None else now
    d = alerts_dir(base)
    try: names = os.listdir(d)
    except OSError: return 0
    n = 0
    for name in names:
        if not (name.startswith("alert_") and name.endswith(".json")): continue
        p = os.path.join(d, name)
        try:
            if now - os.path.getmtime(p) > ALERT_KEEP_SEC: os.remove(p); n += 1
        except OSError: pass
    return n
