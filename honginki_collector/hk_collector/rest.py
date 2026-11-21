"""키움 REST 조회 클라이언트 (직접 작성, 조회 전용). 토큰·키는 저장·출력하지 않는다."""
import json
import os
import stat
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, deque
from datetime import datetime

from . import config as C

KEY_FIELD_CANDIDATES = (("appkey", "secretkey"), ("app_key", "app_secret"),
                        ("app_key", "secret_key"), ("appKey", "secretKey"))


def load_keys(path):
    mode = os.stat(path).st_mode
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    for a, s in KEY_FIELD_CANDIDATES:
        if d.get(a) and d.get(s):
            return d[a], d[s], bool(mode & (stat.S_IRWXG | stat.S_IRWXO))
    # 값은 절대 출력하지 않고 필드 이름만 알린다
    raise RuntimeError(f"키 파일 필드명을 못 찾음. 있는 필드: {sorted(d)}")


def parse_code(text):
    try:
        j = json.loads(text)
    except (ValueError, TypeError):
        return None, None
    if not isinstance(j, dict):
        return None, None
    rc = j.get("return_code")
    try:
        rc = int(rc) if rc is not None else None
    except (ValueError, TypeError):
        pass
    return rc, j.get("return_msg")


class Rest:
    def __init__(self, store, appkey, secret):
        self._k = (appkey, secret)
        self._token = None
        self._exp = 0.0
        self.store = store
        self._lock = threading.Lock()
        self._last = 0.0
        self._hist = deque(maxlen=2000)
        self.codes = Counter()

    def _http(self, api_id, body, token=None, next_key=None):
        path = C.ALLOWED_TR.get(api_id)
        if path is None:
            raise PermissionError(f"허용 안 된 TR: {api_id}")
        h = {"Content-Type": "application/json;charset=UTF-8", "api-id": api_id,
             "User-Agent": C.UA}
        if token:
            h["authorization"] = "Bearer " + token
        if next_key:
            h["cont-yn"] = "Y"
            h["next-key"] = next_key
        req = urllib.request.Request(C.REST_BASE + path, data=json.dumps(body).encode(),
                                     headers=h, method="POST")
        with self._lock:
            wait = self._last + C.REST_MIN_GAP_S - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self._hist.append(self._last)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                status, text, rh = r.status, r.read().decode("utf-8", "replace"), r.headers
        except urllib.error.HTTPError as e:
            status, text, rh = e.code, e.read().decode("utf-8", "replace"), e.headers
        return status, text, {"cont-yn": rh.get("cont-yn"), "next-key": rh.get("next-key")}

    def _rate(self):
        t = time.monotonic()
        return {"calls_1s": sum(1 for x in self._hist if t - x <= 1),
                "calls_60s": sum(1 for x in self._hist if t - x <= 60)}

    def invalidate_token(self):
        self._token = None

    def token(self):
        if self._token and time.time() < self._exp - 600:
            return self._token
        status, text, _ = self._http("au10001", {"grant_type": "client_credentials",
                                                 "appkey": self._k[0], "secretkey": self._k[1]})
        rc, msg = parse_code(text)
        # 응답 원문은 토큰이 들어 있어 저장하지 않는다
        self.store.event("token", status=status, return_code=rc, return_msg=msg,
                         blocked=("Request Blocked" in text) if rc is None else False)
        j = json.loads(text) if rc is not None else {}
        if rc != 0 or not j.get("token"):
            raise RuntimeError(f"토큰 발급 실패 status={status} code={rc} msg={msg}")
        self._token = j["token"]
        try:
            exp = datetime.strptime(j["expires_dt"], "%Y%m%d%H%M%S").replace(tzinfo=C.KST)
            self._exp = exp.timestamp()
        except (KeyError, ValueError):
            self._exp = time.time() + 3600  # 만료일 없으면 1시간 뒤 재발급 (보수적 임시값)
        return self._token

    def call(self, api_id, body, max_pages=1, tag=None):
        """조회 1건. 페이지별 원문을 rest_<TR>.jsonl에 저장. [(code, text)] 반환."""
        out, nk = [], None
        for page in range(max_pages):
            code, text, h = None, "", {}
            for attempt in range(5):
                tok = self.token()
                status, text, h = self._http(api_id, body, tok, nk)
                code, msg = parse_code(text)
                self.codes[str(code)] += 1
                self.store.write(f"rest_{api_id}", {"req": body, "page": page, "attempt": attempt,
                                                    "status": status, "hdr": h, "tag": tag,
                                                    "raw": text})
                if code in C.RATE_CODES:
                    self.store.event("rate_limit", api_id=api_id, code=code, msg=msg,
                                     gap_s=C.REST_MIN_GAP_S, **self._rate())
                    time.sleep(2 ** attempt)
                    continue
                if code in C.TOKEN_RETRY_CODES or status == 401:
                    self.store.event("token_retry", api_id=api_id, code=code, msg=msg)
                    self.invalidate_token()
                    continue
                if code not in (0, None):
                    self.store.event("rest_code", api_id=api_id, code=code, msg=msg)
                break
            out.append((code, text))
            if h.get("cont-yn") != "Y" or not h.get("next-key"):
                break
            nk = h["next-key"]
        return out
