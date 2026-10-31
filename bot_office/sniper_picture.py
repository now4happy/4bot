#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/sniper_picture.py   (초안 · 버전 번호는 Muse 가 기존 표기에 맞춰 부여)
# 2번 토스 스나이퍼 매매 그림 데이터 (/api/sniper-picture · 로그인 필요 · 보기 전용)
#  · 주문·승인·설정 변경·리셋 기능 없음. 원장 JSON 을 '읽기만' 한다 (쓰기·삭제 없음).
#  · /api/board 와 섞지 않는다 (첫 화면의 '금액·수량 원문 없음' 규칙 유지). 이 데이터는 /sniper-picture 전용.
#  · 계산을 새로 만들지 않는다: toss_sniper/quant_engine.py 의 원본 함수를 그대로 부른다.
#      summarize_stratum_portfolio · evaluate_multi_grid_sell_targets · (내부적으로) compute_upper_2_to_12_moving_avg
#    주의: quant_engine 은 `import toss_api` 를 하는데, toss_api 는 불러오는 순간 .env/secrets 를 환경변수로 읽는다
#    (toss_api.py 285행). 웹서버 프로세스에 스나이퍼 비밀값이 섞이면 안 되므로 toss_api 를 import 하지 않고,
#    toss_api.py 소스에서 safe_float·safe_int 와 숫자 상수만 AST 로 꺼내 가짜 toss_api 를 잠깐 끼워 quant_engine 을 읽는다.
#    (원본 소스 그대로 · 실행되는 것은 그 함수·상수뿐 · 네트워크·파일 쓰기 없음)
#  · 읽는 곳: <스나이퍼 폴더>/soxl_stratum_ledger_<폴더명>.json  (기본 /home/gieokkim/toss_sniper, 환경변수 SNIPER_PICTURE_DIR 로 변경)
#            선택: <스나이퍼 폴더>/sniper_snapshot.json (현재가 — 스나이퍼 main 루프가 60초마다 씀, 사무실이 이미 읽을 수 있음)
#            선택(구 경로): /var/lib/bot-office/sniper_snapshot.json (스나이퍼 폴더 파일이 없을 때만 확인)
#  · 없는 것은 지어내지 않는다: 과거 매도 목록(원장에 없음) · 환율(서버 파일에 없음) · 실시간 현재가(메모리에만 있음)
# ==========================================================
import ast, importlib.util, json, math, os, sys, time, types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(os.environ.get("OFFICE_ROOT", "/"))
SNIPER_DIR = Path(os.environ.get("SNIPER_PICTURE_DIR", "/home/gieokkim/toss_sniper"))
SNAPSHOT = R / "var/lib/bot-office/sniper_snapshot.json"
SNAPSHOT_SNIPER = SNIPER_DIR / "sniper_snapshot.json"
SNAPSHOT_MAX_AGE = 180            # 초 — 이보다 오래된 현재가는 '미확인' 으로 본다
KST = timezone(timedelta(hours=9))
EST_TZ = ZoneInfo("America/New_York")
_CACHE = {"at": 0.0, "data": None}
_ENGINE = {}

_NEEDED_NAMES = {"DEFAULT_INITIAL_SEED_USD", "PORTION_RATIO_LOCKED", "REANCHOR_NET_BUFFER_MULT",
                 "ROUND_TRIP_FEE_RATE_PCT", "MAX_GRID_TIERS_7"}


def _engine():
    """quant_engine 원본을 비밀값 로딩 없이 읽는다. 실패하면 None (그림 API 는 engine_unavailable 로 답함)."""
    if "qe" in _ENGINE:
        return _ENGINE["qe"]
    qe = None
    try:
        src_api = (SNIPER_DIR / "toss_api.py").read_text(encoding="utf-8")
        tree = ast.parse(src_api)
        keep = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in ("safe_float", "safe_int"):
                keep.append(node)
            elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") in _NEEDED_NAMES:
                keep.append(node)
            elif isinstance(node, ast.Assign) and any(getattr(t, "id", "") in _NEEDED_NAMES for t in node.targets):
                keep.append(node)
        stub = types.ModuleType("toss_api")
        stub.__dict__.update({"math": math, "Any": object, "Dict": dict, "List": list, "Optional": object})
        exec(compile(ast.Module(body=keep, type_ignores=[]), "toss_api(subset)", "exec"), stub.__dict__)
        if not (hasattr(stub, "safe_float") and hasattr(stub, "safe_int")):
            raise ImportError("safe_* missing")
        spec = importlib.util.spec_from_file_location("sniper_quant_engine", SNIPER_DIR / "quant_engine.py")
        qe = importlib.util.module_from_spec(spec)
        prev = sys.modules.get("toss_api")
        sys.modules["toss_api"] = stub
        sys.modules["sniper_quant_engine"] = qe      # @dataclass 가 자기 모듈을 sys.modules 에서 찾는다
        try:
            spec.loader.exec_module(qe)
        finally:
            if prev is None:
                sys.modules.pop("toss_api", None)    # 가짜 toss_api 는 바로 치운다 (진짜 toss_api 와 섞이지 않게)
            else:
                sys.modules["toss_api"] = prev
    except Exception:
        sys.modules.pop("sniper_quant_engine", None)
        qe = None
    _ENGINE["qe"] = qe
    return qe


def _find_ledger():
    """원장 파일 찾기: 폴더 고유 원장(soxl_stratum_ledger_<폴더명>.json) 우선, 없으면 *ledger*.json 중 SOXL/buckets 가 있는 최신 파일.
    (ledger_backups 하위 폴더는 보지 않는다 — 백업은 현재 상태가 아님)"""
    try:
        files = [f for f in SNIPER_DIR.glob("*.json") if "ledger" in f.name.lower()]
    except OSError:
        return None, "ledger_unreadable"
    if not files:
        return None, "ledger_not_found"
    slug = "".join(c if (c.isalnum() or c in "._-") else "_" for c in SNIPER_DIR.name).strip("._-") or "default_bot"
    own = SNIPER_DIR / f"soxl_stratum_ledger_{slug}.json"
    ordered = sorted(files, key=lambda f: (f != own, -_mtime(f)))
    for f in ordered:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("SOXL"), dict):
            data = data["SOXL"]
        if isinstance(data, dict) and ("buckets" in data or "initial_seed_usd" in data):
            return (f, data), ""
    return None, "ledger_unreadable"


def _mtime(f):
    try:
        return f.stat().st_mtime
    except OSError:
        return 0.0


def _snapshot_price(now_ts):
    """스나이퍼가 남긴 현재가 스냅샷(선택). 없거나 오래됐으면 (None, 이유).
    확인 순서: 스나이퍼 폴더 파일 먼저, 없으면 구 경로(/var/lib) 파일. 둘 다 오래됐으면 오래된 쪽 이유를 돌려준다."""
    last_note = "no_snapshot"
    for path in (SNAPSHOT_SNIPER, SNAPSHOT):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            p, at = float(d.get("live_price")), float(d.get("at"))
        except (OSError, ValueError, TypeError):
            continue
        if not (p > 0) or not math.isfinite(p):
            last_note = "bad_snapshot"
            continue
        age = now_ts - at
        if age > SNAPSHOT_MAX_AGE or age < -30:
            last_note = "stale_snapshot"
            continue
        return round(p, 4), ""
    return None, last_note


def _session(now_est):
    """세션 이름. 매도 잠금 규칙은 sniper_exit_plugin.py 와 같다: 04:07~16:00 ET 밖이면 '밤'(애프터·데이장)."""
    hm = now_est.hour * 100 + now_est.minute
    wd = now_est.weekday()
    closed = (wd == 4 and hm >= 1700) or wd == 5 or (wd == 6 and hm < 2000)   # toss_api.is_sniper_weekend_closed 와 같음
    if closed:
        name = "주말휴장"
    elif hm >= 2000 or hm < 400:
        name = "데이장"
    elif hm <= 406:
        name = "프리장 준비"
    elif hm <= 929:
        name = "프리장"
    elif hm <= 1600:
        name = "정규장"
    else:
        name = "애프터장"
    return {"name": name, "overnight": not (407 <= hm <= 1600), "weekend_closed": closed, "hm": f"{now_est.hour:02d}:{now_est.minute:02d}"}


def _ceil_target(price, pct):
    """tg_ui_plugin.py 가 개별 익절가를 보여 줄 때 쓰는 식 그대로 (quant_engine 은 상단 개별가를 함수로 내놓지 않음)."""
    return round(math.ceil((price * (1.0 + pct / 100.0) - 1e-9) * 100.0) / 100.0, 2)


def build(state, live_price=None, now_est=None, price_note=""):
    """원장 상태 dict + (선택)현재가 → 그림용 데이터. 테스트에서 가짜 원장·가짜 현재가로 직접 부른다."""
    qe = _engine()
    if qe is None:
        return {"ok": False, "error": "engine_unavailable"}
    now_est = (now_est or datetime.now(EST_TZ)).astimezone(EST_TZ)
    sess = _session(now_est)
    lp = float(live_price) if (live_price and live_price > 0) else 0.0
    known = lp > 0
    summary = qe.summarize_stratum_portfolio(state, live_price=lp)
    buckets = summary.get("buckets") or []
    active_l1 = bool(summary.get("has_active_l1")) and bool(buckets)
    rise_l1 = float(summary.get("rise_sell_l1_pct") or 1.5)
    rise_up = float(summary.get("rise_sell_l2_pct") or 1.0)
    has_upper = len(buckets) > (1 if active_l1 else 0)
    lock_indiv = bool(sess["overnight"] and has_upper)          # 밤에는 개별 매도 잠김 · 통합이평 졸업만 가능 (quant_engine 과 같은 규칙)

    tiers, targets = [], []
    for i, b in enumerate(buckets):
        is_l1 = active_l1 and i == 0
        no = (i + 1) if active_l1 else (i + 2)
        pct = rise_l1 if is_l1 else rise_up
        tgt = summary.get("l1_target_price") if is_l1 else _ceil_target(b.book_price, rise_up)
        tiers.append({"tier": no, "kind": "l1" if is_l1 else "upper", "qty": int(b.qty), "price": round(b.book_price, 4),
                      "lot_count": int(b.lot_count), "lot_type": b.lot_type, "target": tgt, "target_pct": pct})
    upper = [t for t in tiers if t["kind"] == "upper"]
    if active_l1 and tiers:
        t = tiers[0]
        targets.append({"kind": "l1", "price": t["target"], "pct": rise_l1, "tiers": [t["tier"]], "locked": lock_indiv})
    if len(upper) == 1:
        # 상단이 1개층이면 개별 목표와 통합이평 목표가 같다 → 한 줄로 합쳐 보여 줌 (통합이평은 졸업 때 1층도 본전 이상이면 같이 판다)
        # 밤에는 개별 매도가 잠기므로 locked도 lock_indiv를 따른다 (이전에는 False 고정이라 밤에 도달로 보였다)
        targets.append({"kind": "indiv", "price": upper[0]["target"], "pct": rise_up, "tiers": [upper[0]["tier"]], "locked": lock_indiv,
                        "also_wma": True, "wma_only": lock_indiv})
    elif len(upper) > 1:
        wma_t = float(summary.get("upper_wma_target_price") or 0.0)
        for t in upper:
            targets.append({"kind": "indiv", "price": t["target"], "pct": rise_up, "tiers": [t["tier"]], "locked": lock_indiv})
        if wma_t > 0:
            targets.append({"kind": "wma", "price": wma_t, "pct": rise_up, "tiers": [t["tier"] for t in upper], "locked": False,
                            "avg_price": float(summary.get("upper_wma_price") or 0.0)})
    for t in targets:
        t["reached"] = bool(known and t["price"] > 0 and lp >= t["price"])
        t["unlock_hm"] = "04:07" if t["locked"] else ""
    for t in tiers:
        t["reached"] = bool(known and t["target"] and lp >= t["target"])

    engine = None
    if known and buckets:
        ev = qe.evaluate_multi_grid_sell_targets(buckets, lp, rise_l1_pct=rise_l1, rise_upper_pct=rise_up,
                                                 is_overnight_session=bool(sess["overnight"]))
        engine = {"should_sell": bool(ev.get("should_sell")), "reason_tag": ev.get("reason_tag"),
                  "sell_tiers": [tiers[k]["tier"] for k in ev.get("sold_indices", []) if k < len(tiers)],
                  "overnight_indiv_locked": bool(ev.get("overnight_indiv_locked"))}

    held = int(summary.get("held_shares") or 0)
    holding = {"shares": held, "tiers_count": len(buckets), "has_active_l1": active_l1,
               "avg_price": round(float(summary.get("actual_avg_price") or 0.0), 4) if held else None,
               "invested_usd": round(float(summary.get("actual_invested_usd") or 0.0), 2) if held else None,
               # 현재가를 모르면 미실현 손익은 계산하지 않는다 (quant_engine 은 모르면 평단으로 대신 계산해 0 이 나옴 → 거짓 0 방지)
               "unrealized_usd": round(float(summary.get("unrealized_pnl_usd") or 0.0), 2) if (held and known) else None,
               "unrealized_pct": round(float(summary.get("unrealized_rate_pct") or 0.0), 2) if (held and known) else None}
    realized = {"cumulative_net_usd": round(float(summary.get("cumulative_realized_net_usd") or 0.0), 2),
                "sell_events": int(state.get("total_sell_events") or 0), "win_events": int(state.get("win_sell_events") or 0),
                "sold_shares": int(state.get("total_sold_shares") or 0), "daily_net_usd": round(float(state.get("daily_realized_net_usd") or 0.0), 2),
                # 원장에는 누적 숫자만 있고 '언제·어느 층·얼마에 팔았나' 목록은 없다 → 복원하지 않는다
                "history_available": False, "history": []}
    return {"ok": True, "symbol": "SOXL", "read_only": True,
            "observed_kst": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"), "est_time": now_est.strftime("%m-%d %H:%M ET"),
            "session": sess, "is_active": bool(state.get("is_active", True)),
            "price": {"live": round(lp, 4) if known else None, "note": "" if known else (price_note or "no_snapshot")},
            "tiers": tiers, "targets": targets, "holding": holding, "realized": realized, "engine": engine,
            "fx": {"krw_per_usd": None, "note": "환율 미확인 · 달러만 표시"}}


def picture():
    """/api/sniper-picture 본체 (15초 캐시)."""
    if _CACHE["data"] and time.monotonic() - _CACHE["at"] < 15:
        return _CACHE["data"]
    found, err = _find_ledger()
    if not found:
        data = {"ok": False, "error": err, "read_only": True}
    else:
        f, state = found
        lp, note = _snapshot_price(time.time())
        data = build(state, live_price=lp, price_note=note)
        if data.get("ok"):
            data["ledger"] = {"file": f.name, "updated_kst": datetime.fromtimestamp(_mtime(f), KST).strftime("%m-%d %H:%M:%S")}
    _CACHE.update(at=time.monotonic(), data=data)
    return data


if __name__ == "__main__":
    print(json.dumps(picture(), ensure_ascii=False, indent=1))
