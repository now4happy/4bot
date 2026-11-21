# briefing/sources/kiwoom.py — 모드 fixed | api_shadow | api, 반환 형식은 모두 {종목코드 6자리: 수량}.
# fixed: kiwoom_fixed.json 읽기만. 파일이 없거나 깨지면 소스 실패.
# api_shadow: API 로 조회하되 메시지에는 고정값을 쓰고, 불일치 종목 수만 로그에 남긴다.
# api: API 값 사용. 실패 시 '마지막 성공 API 스냅샷' + ⚠️ (옛 고정 파일로 조용히 되돌아가지 않는다).
# 보유는 국내주식만으로 가정 (kt00018 국내주식 기준, Q11). 키움 토큰 정책(매도 자동화와 공유 시 끊김)은 미확인 →
# 공유 토큰 경유가 기본 원칙이지만 API 호출 자체는 입국 뒤(2026-12-03 이후) 구현한다.
import datetime as dt
import hashlib
import re

from .. import state as _state
from . import SourceError, acct_fail, acct_ok

ACCOUNT = "키움"
_CODE = re.compile(r"^\d{6}$")


def normalize_code(code):
    """API 응답의 'A005930' 형태(접두어 A, 숫자 0 채움)를 6자리로."""
    c = str(code).strip()
    if c[:1].upper() == "A":
        c = c[1:]
    if c.isdigit() and len(c) < 6:
        c = c.zfill(6)
    return c


def read_fixed(path):
    """(holdings, sha256) — 없음/깨짐/형식 이상은 SourceError."""
    p = _state.expand(path)
    try:
        with open(p, "rb") as f:
            raw = f.read()
    except OSError:
        raise SourceError("고정 파일 없음")
    sha = hashlib.sha256(raw).hexdigest()
    try:
        import json
        d = json.loads(raw.decode("utf-8"))
    except ValueError:
        raise SourceError("고정 파일 JSON 깨짐")
    if not isinstance(d, dict) or not d:
        raise SourceError("고정 파일 형식 이상")
    out = {}
    for k, v in d.items():
        if not _CODE.match(str(k)) or isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise SourceError("고정 파일 항목 이상: %s" % k)
        out[str(k)] = float(v)
    return out, sha


def _api_fetch(cfg):
    raise SourceError("키움 API 미구현 (입국 뒤 구현 예정)")


def fetch(cfg, today, state_obj=None, api_fetch=None):
    kcfg = cfg.get("kiwoom", {})
    mode = kcfg.get("mode", "fixed")
    as_of = kcfg.get("fixed_as_of")
    elapsed = None
    if as_of:
        try:
            elapsed = (dt.date.fromisoformat(today) - dt.date.fromisoformat(as_of)).days
        except ValueError:
            elapsed = None
    meta = {"mode": mode, "as_of": as_of, "elapsed_days": elapsed, "fixed_sha": None, "shadow_mismatch": None}
    api = api_fetch or (lambda: _api_fetch(cfg))

    fixed, sha, ferr = None, None, None
    if mode in ("fixed", "api_shadow"):
        try:
            fixed, sha = read_fixed(cfg["paths"]["kiwoom_fixed"])
            meta["fixed_sha"] = sha
        except SourceError as e:
            ferr = str(e)

    if mode == "fixed":
        if fixed is None:
            return {"status": "unavailable", "accounts": {ACCOUNT: acct_fail(ferr)}, "meta": meta}
        return {"status": "ok", "accounts": {ACCOUNT: acct_ok(fixed)}, "meta": meta}

    if mode == "api_shadow":
        try:
            live = {normalize_code(k): float(v) for k, v in api().items()}
            if fixed is not None:
                keys = set(live) | set(fixed)
                meta["shadow_mismatch"] = sum(1 for k in keys if abs(live.get(k, 0) - fixed.get(k, 0)) > 1e-9)
        except Exception:
            meta["shadow_mismatch"] = None  # 조회 실패도 메시지에는 영향 없음 (고정값 사용)
        if fixed is None:
            return {"status": "unavailable", "accounts": {ACCOUNT: acct_fail(ferr)}, "meta": meta}
        return {"status": "ok", "accounts": {ACCOUNT: acct_ok(fixed)}, "meta": meta}

    if mode == "api":
        try:
            live = {normalize_code(k): float(v) for k, v in api().items()}
            if state_obj is not None:
                _state.atomic_write_json(state_obj.root + "/kiwoom_last_api.json",
                                         {"date": today, "holdings": live}, mode=0o600)
            return {"status": "ok", "accounts": {ACCOUNT: acct_ok(live)}, "meta": meta}
        except Exception as e:
            last = _state.read_json(state_obj.root + "/kiwoom_last_api.json", None) if state_obj else None
            if isinstance(last, dict) and isinstance(last.get("holdings"), dict):
                meta["stale_api_date"] = last.get("date")
                a = acct_ok(last["holdings"], "마지막 성공 API 값(%s) ⚠️" % last.get("date"))
                return {"status": "partial", "accounts": {ACCOUNT: a}, "meta": meta}
            return {"status": "unavailable", "accounts": {ACCOUNT: acct_fail("API 실패: %s" % e)}, "meta": meta}

    return {"status": "unavailable", "accounts": {ACCOUNT: acct_fail("모드 이상: %s" % mode)}, "meta": meta}
