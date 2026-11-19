# =====================================================================
# FILE: toss_token_share.py   (🔗 토스 토큰 공유 · 사용자 추가 모듈 v1.0.0)
# 같은 토스 API 키를 쓰는 2번 스나이퍼 · 3번 토스 적립 · 사무실 브리핑이
# 각자 토큰을 새로 발급하면 서로의 토큰이 무효(HTTP 401)가 될 수 있어,
# 서버 안에서 키별로 토큰 1개를 같이 쓰도록 맞춥니다.
#
#  · 저장 위치: /home/gieokkim/.toss_token_share/token_<키 해시>.json (권한 600 · 키 원문 저장 안 함)
#  · 파일 잠금(flock)으로 동시에 둘이 발급하지 않음 → 먼저 받은 쪽 토큰을 나머지가 그대로 사용
#  · 401 이 나면: 실패한 토큰이 아직 공유 토큰이면 그때만 새로 발급, 이미 다른 봇이 새로 받아 두었으면 그걸 사용
#  · 폴더 권한 문제 등으로 공유가 안 되면 None 을 돌려줘 각 봇이 예전처럼 직접 발급 (매매는 멈추지 않음)
#  · 같은 파일을 toss_sniper / toss_dca_bot / bot_office 세 곳에 똑같이 둡니다.
# =====================================================================
import fcntl
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.0"
SHARE_DIR = os.environ.get("TOSS_TOKEN_SHARE_DIR", "/home/gieokkim/.toss_token_share")
MIN_LEFT_SEC = 300          # 남은 시간이 5분 미만이면 새로 발급
DEFAULT_BASE = "https://openapi.tossinvest.com"


def _owner():
    try:
        st = os.stat(os.path.dirname(SHARE_DIR.rstrip("/")) or "/")
        return st.st_uid, st.st_gid
    except OSError:
        return None


def _prepare_dir():
    os.makedirs(SHARE_DIR, mode=0o700, exist_ok=True)
    if os.geteuid() == 0:   # root 로 도는 봇이 만들어도 다른 봇(일반 계정)이 읽을 수 있게 홈 주인에게 맞춤
        own = _owner()
        if own:
            try:
                os.chown(SHARE_DIR, *own)
            except OSError:
                pass


def _paths(client_id):
    h = hashlib.sha256(str(client_id or "").encode()).hexdigest()[:16]
    return os.path.join(SHARE_DIR, f"token_{h}.json"), os.path.join(SHARE_DIR, f"token_{h}.lock")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write(path, data):
    tmp = f"{path}.tmp.{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    if os.geteuid() == 0:
        own = _owner()
        if own:
            try:
                os.chown(tmp, *own)
            except OSError:
                pass
    os.replace(tmp, path)


def _issue(base_url, client_id, client_secret, timeout=10.0):
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": client_id,
                                   "client_secret": client_secret}).encode()
    req = urllib.request.Request(f"{(base_url or DEFAULT_BASE).rstrip('/')}/oauth2/token", data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    try:
        payload = json.loads(raw.decode("utf-8", "replace") or "{}")
    except Exception:
        payload = {}
    return status, payload if isinstance(payload, dict) else {}


def try_acquire(base_url, client_id, client_secret, force=False, bad_token="", who=""):
    """
    반환: ("ok", 토큰, 남은초) · ("fail", HTTP상태, 응답) · None(공유 불가 → 각자 예전 방식)
    force=True 는 401 등으로 토큰이 거절됐을 때. bad_token 은 거절된 그 토큰.
    """
    if not client_id or not client_secret:
        return None
    try:
        _prepare_dir()
        path, lock = _paths(client_id)
        lf = open(lock, "a+")
    except OSError:
        return None
    try:
        fcntl.flock(lf, fcntl.LOCK_EX)
        d, now = _read(path), time.time()
        tok, exp = str(d.get("token") or ""), float(d.get("expires_at") or 0)
        usable = bool(tok) and exp - now > MIN_LEFT_SEC
        if usable and (not force or (bad_token and tok != bad_token)):
            return "ok", tok, exp - now      # 다른 봇이 이미 받아 둔(또는 새로 갱신한) 토큰
        status, payload = _issue(base_url, client_id, client_secret)
        new = str(payload.get("access_token") or "").strip()
        if status != 200 or not new:
            return "fail", status, payload
        try:
            left = max(300.0, float(payload.get("expires_in") or 86400))
        except (TypeError, ValueError):
            left = 86400.0
        _write(path, {"token": new, "expires_at": now + left, "issued_at": now, "by": who or str(os.getpid())})
        return "ok", new, left
    except OSError:
        return None
    finally:
        try:
            fcntl.flock(lf, fcntl.LOCK_UN)
            lf.close()
        except Exception:
            pass
