#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/live_board.py   (사무실 vNEXT)
# 신규: 시세 직접받기 — 토스 API(SOXL·TQQQ 현재가 + 환율)로 1분마다 자산 평가액을 계산해서
#       보드용 live_board.json 을 전용 브랜치 live-board 에 올린다 (main·staging 에는 절대 안 올림).
#  - 시트(26년 계획 · 입력정리)는 읽기만 한다 (spreadsheets.readonly · asset_board.py 의 서명·토큰 부품 재사용).
#  - 토스는 스나이퍼와 같은 TossApiClient(base_dir=/home/gieokkim/toss_sniper) 를 읽기 전용으로만 쓴다
#    (현재가 배치 1회 + 환율 1회 · 주문·계좌 호출 없음 · 스나이퍼 코드 수정 없음).
#  - 장 시간(ET 09:30–16:00, 휴장일 제외)에만 API 를 부른다. 장이 닫히면 market_open 만 한 번 false 로 바꾼다.
#  - JSON 에는 시세·환율·행별 평가액(만원)·합계만 넣는다. 키·토큰·계좌번호·원금은 넣지 않는다.
#  - 실패하면 {"ok": false, "error": 코드, "as_of_kst"} 를 원자적으로 쓰고 0 이 아닌 코드로 끝낸다.
#  - git: 작업트리 /var/lib/bot-office/live-board (브랜치 live-board) 에서만 커밋·푸시. force-push 없음.
#    저장소에 음수 refspec(^refs/heads/live-board)이 없으면 푸시하지 않는다
#    (업데이트 비서가 live-board 를 '새 업데이트'로 1분마다 알리는 것을 막기 위함 · VERIFY.md 참고).
# 사용:
#   python3 live_board.py             # 타이머가 부르는 것 (계산 → 쓰기 → 바뀌었으면 커밋+푸시)
#   python3 live_board.py --check     # 쓰지 않고 계산한 JSON 을 화면에만 출력 (푸시 없음)
#   python3 live_board.py --dry-run   # 쓰지 않고 한 줄 요약만 출력 (푸시 없음)
# ==========================================================
import argparse, asyncio, json, os, pwd, re, subprocess, sys, tempfile, time, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
WORKTREE = os.environ.get("LB_WORKTREE", "/var/lib/bot-office/live-board")
BRANCH = os.environ.get("LB_BRANCH", "live-board")
OUT_NAME = "live_board.json"
TOSS_DIR = os.environ.get("LB_TOSS_DIR", "/home/gieokkim/toss_sniper")
PUSHED_REF = f"refs/live-board/pushed"          # 마지막으로 푸시 성공한 커밋 (refs/remotes 밖이라 업데이트 비서가 안 봄)
SHEET_RANGE = "'입력정리'!A14:F55"
FIRST_ROW = 14
COLS = "ABCDEF"
TIME_KEYS = ("as_of_kst", "as_of_et")             # 내용 비교 때 빼는 칸 (시각만 바뀐 것은 '안 바뀜')


# ---------------- 미국 휴장일 — fanding_trade.py 246·258행 발췌 그대로 (원본 sha256 8d8c3b3f0b50)
# 미국 정규장 휴장일 (조기 마감일은 장이 열린 날이라 넣지 않음)
# 출처: NYSE Group 2026·2027·2028 Holiday and Early Closings Calendar (2025-12-23 발표),
#       https://www.nyse.com/markets/hours-calendars — office_briefing.py 의 US_CLOSED 와 같은 표
# 2029년 이후는 표 확장이 필요하다 (표에 없는 연도는 주말만 건너뜀)
US_CLOSED = {
    2026: "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    2027: "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    2028: "01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25",
}


def is_trading_day(d):
    """미국 정규장이 열리는 날: 월~금이면서 휴장일 표에 없는 날"""
    if d.weekday() >= 5:
        return False
    return d.strftime("%m-%d") not in US_CLOSED.get(d.year, "").split()
# ---------------- 발췌 끝


class LiveError(RuntimeError):
    """JSON error 칸에 들어가는 짧은 코드만 담는다 (비밀·식별자 없음)"""


def is_market_open(now_utc):
    e = now_utc.astimezone(ET)
    hm = e.hour * 100 + e.minute
    return is_trading_day(e.date()) and 930 <= hm < 1600


def stamps(now_utc):
    return (now_utc.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S"),
            now_utc.astimezone(ET).strftime("%Y-%m-%d %H:%M:%S"))


# ---------------- 시트 (읽기 전용)
def read_sheet_values(http=None):
    """입력정리!A14:F55 한 범위만 읽음 → [[칸...], ...] (asset_board.py 의 토큰·HTTP 부품 그대로)"""
    import asset_board as AB
    http = http or AB.urllib_http
    tok, _email = AB.google_token(AB.SA_FILE, http)
    q = [("ranges", SHEET_RANGE), ("valueRenderOption", "UNFORMATTED_VALUE"),
         ("dateTimeRenderOption", "FORMATTED_STRING")]
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{AB.SHEET_ID}/values:batchGet?"
           + urllib.parse.urlencode(q))
    st, _, d = http("GET", url, {"authorization": "Bearer " + tok}, None)
    if st != 200:
        raise LiveError(f"sheet_http_{st}")
    vr = d.get("valueRanges") or []
    if len(vr) != 1:
        raise LiveError("sheet_bad_response")
    return vr[0].get("values") or []


def cell(values, ref):
    """'D27' → 시트 원래 값 (비었으면 None)"""
    col, row = COLS.index(ref[0]), int(ref[1:])
    i = row - FIRST_ROW
    if i < 0 or i >= len(values) or col >= len(values[i]):
        return None
    v = values[i][col]
    return None if v is None or (isinstance(v, str) and not v.strip()) else v


def num(values, ref):
    """숫자 칸 → float · 빈칸 → None · 글자(#N/A 등) → 오류"""
    v = cell(values, ref)
    if v is None:
        return None
    if isinstance(v, bool):
        raise LiveError(f"sheet_not_number_{ref}")
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[,\s]", "", str(v))
    try:
        return float(s)
    except ValueError:
        raise LiveError(f"sheet_not_number_{ref}") from None


def num0(values, ref):
    v = num(values, ref)
    return 0.0 if v is None else v


# ---------------- 계산 (API 와 분리 · 시트 수식과 같은 식)
# 행 → (수량 칸, 시세 키) · 시세 키 None = 달러 그대로(환율만)
QTY_ROWS = {27: "tqqq", 28: "soxl", 29: "soxl", 30: "tqqq", 33: None, 34: "soxl", 35: None}
STATIC_C = (26, 31, 32, 36, 39, 40, 41, 46, 47, 48, 49, 50, 54)   # 정적 값 (C열)
STATIC_E = (37, 38)                                                 # v1: 시트 E값 그대로 (BTC·ETH)
OUT_ROWS = (27, 28, 29, 30, 33, 34, 35, 37, 38)


def compute(values, soxl, tqqq, fx):
    """→ (E값 dict{행: 만원, 반올림 전}, rows{str행: 만원 2자리}, totals)"""
    for k, v in (("soxl", soxl), ("tqqq", tqqq), ("usdkrw", fx)):
        if not isinstance(v, (int, float)) or not v > 0:
            raise LiveError(f"bad_price_{k}")
    px = {"soxl": float(soxl), "tqqq": float(tqqq)}
    E = {r: num0(values, f"C{r}") for r in STATIC_C}
    for r in STATIC_E:
        E[r] = num0(values, f"E{r}")
    for r, key in QTY_ROWS.items():
        q = num(values, f"D{r}")
        if q is None:   # 시트 IF(D="",F,...) 와 같은 폴백: 시트 E값 → 없으면 F값
            fb = num(values, f"E{r}")
            E[r] = fb if fb is not None else num0(values, f"F{r}")
        elif key is None:
            E[r] = q * fx / 10000 + (num0(values, "C35") if r == 35 else 0.0)
        else:
            E[r] = q * px[key] * fx / 10000
    api_sum = sum(E[r] for r in range(26, 42))                                  # E42 = SUM(E26:E41)
    cash = sum(E[r] for r in (26, 39, 31, 32, 33, 36, 46, 40, 54))              # B83
    manual = sum(E[r] for r in (46, 47, 48, 49, 50, 54))                        # E51 = SUM(E46:E50,E54)
    rows = {str(r): r2(E[r]) for r in OUT_ROWS}
    totals = {"api_sum": r2(api_sum), "cash": r2(cash), "total_assets": r2(api_sum + manual)}
    return E, rows, totals


def r2(x):
    v = round(float(x) + 0.0, 2)
    return int(v) if v.is_integer() else v


def build_ok(now_utc, soxl, tqqq, fx, rows, totals):
    k, e = stamps(now_utc)
    return {"ok": True, "as_of_kst": k, "as_of_et": e, "market_open": True, "source": "toss",
            "prices": {"soxl": soxl, "tqqq": tqqq, "btc": None, "eth": None, "usdkrw": fx},
            "rows": rows, "totals": totals}


def build_fail(now_utc, code):
    return {"ok": False, "error": str(code)[:80], "as_of_kst": stamps(now_utc)[0]}


# ---------------- 토스 (읽기 전용 2회)
def _load_toss():
    if TOSS_DIR not in sys.path:
        sys.path.insert(0, TOSS_DIR)
    import toss_api
    if os.path.dirname(os.path.abspath(toss_api.__file__)) != os.path.abspath(TOSS_DIR):
        raise LiveError("toss_module_path")
    return toss_api


async def _quotes(client, default_fx=None):
    p = await client.get_current_prices_batch(("SOXL", "TQQQ"))
    fx = await client.get_usd_krw_rate()
    soxl, tqqq = float((p or {}).get("SOXL") or 0), float((p or {}).get("TQQQ") or 0)
    if soxl <= 0 or tqqq <= 0:
        raise LiveError("price_unavailable")   # 클라이언트는 실패하면 0.0 을 돌려줌
    # 클라이언트는 환율 실패 때 기본값(KRW_PER_USD_DEFAULT)을 조용히 돌려줌 → 성공 표시(_fx_cache_mono)로 구분
    fx = float(fx or 0)
    if fx <= 100 or getattr(client, "_fx_cache_mono", 1.0) <= 0 or (default_fx and fx == default_fx):
        raise LiveError("fx_unavailable")
    return soxl, tqqq, fx


def fetch_quotes():
    mod = _load_toss()
    client = mod.TossApiClient(base_dir=TOSS_DIR)

    async def run():
        try:
            return await asyncio.wait_for(_quotes(client, getattr(mod, "KRW_PER_USD_DEFAULT", None)), 40)
        except asyncio.TimeoutError:
            raise LiveError("toss_timeout") from None
        finally:
            try:
                await client.close()
            except Exception:
                pass
    return asyncio.run(run())


def token_share_active():
    try:
        return getattr(_load_toss(), "_TTS", None) is not None
    except Exception:
        return False


# ---------------- 파일 · git
def owner():
    return pwd.getpwuid(os.stat(WORKTREE).st_uid)


def git(*a, timeout=60):
    """bot_updater.py git() 과 같은 방식 (root 면 저장소 주인으로 · -C 작업트리) · 환경변수는 최소만 넘김"""
    o = owner()
    cmd = ["env", f"HOME={o.pw_dir}", "GIT_TERMINAL_PROMPT=0", "git", "-c", "core.quotepath=false", "-C", WORKTREE, *a]
    if os.geteuid() == 0 and o.pw_uid != 0:
        cmd = ["runuser", "-u", o.pw_name, "--"] + cmd
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}   # .env 에서 읽힌 키가 git 으로 안 넘어가게
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"


def out_path():
    return os.path.join(WORKTREE, OUT_NAME)


def load_current():
    try:
        with open(out_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def same_content(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    strip = lambda d: {k: v for k, v in d.items() if k not in TIME_KEYS}
    return strip(a) == strip(b)


def write_atomic(data):
    """임시 파일 + os.replace · 0644 · 저장소 주인 소유 (bot_updater.write_sniper_tiers 와 같은 방식)"""
    path, tmp = out_path(), None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=WORKTREE,
                                         prefix=".live_board_", suffix=".tmp", delete=False) as out:
            tmp = out.name
            json.dump(data, out, ensure_ascii=False, allow_nan=False, indent=2)
            out.write("\n")
        os.chmod(tmp, 0o644)
        try:
            o = owner()
            os.chown(tmp, o.pw_uid, o.pw_gid)
        except OSError:
            pass
        os.replace(tmp, path)
        tmp = None
        return True
    except Exception as exc:
        print("live_board.json 기록 실패:", type(exc).__name__, str(exc)[:120], flush=True)
        return False
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def commit(msg):
    rc, out = git("add", "--", OUT_NAME)
    if rc:
        print("git add 실패:", out[-200:], flush=True)
        return False
    if git("diff", "--cached", "--quiet", "--", OUT_NAME)[0] == 0:
        return True   # 바뀐 것 없음
    rc, out = git("-c", "user.name=bot-office live-board", "-c", "user.email=live-board@localhost",
                  "commit", "-q", "-m", msg, "--", OUT_NAME)
    if rc:
        print("git commit 실패:", out[-200:], flush=True)
    return rc == 0


def refspec_guard_ok():
    """저장소 remote.origin.fetch 에 ^refs/heads/<브랜치> 가 있어야 푸시 (업데이트 비서 알림 폭주 방지)"""
    _, out = git("config", "--get-all", "remote.origin.fetch")
    return f"^refs/heads/{BRANCH}" in out.split()


def push_if_needed():
    """푸시 안 된 커밋이 있으면 푸시 · 실패는 로그만 (다음 분에 다시) · force 없음 → 0=정상, 2=설정 안 됨"""
    rc, head = git("rev-parse", "-q", "--verify", "HEAD")
    if rc or not head:
        return 0   # 아직 커밋 없음
    _, pushed = git("rev-parse", "-q", "--verify", PUSHED_REF)
    if pushed == head:
        return 0
    if not refspec_guard_ok():
        print(f"푸시 안 함: remote.origin.fetch 에 ^refs/heads/{BRANCH} 없음 (VERIFY.md 설치 2단계)", flush=True)
        return 2
    rc, out = git("push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}", timeout=60)
    if rc:
        print("git push 실패 (다음 분에 다시):", out[-200:], flush=True)
        return 0
    git("update-ref", PUSHED_REF, head)
    # 혹시 남은 추적 ref 가 있으면 지움 (업데이트 비서는 refs/remotes/origin 만 봄)
    if git("rev-parse", "-q", "--verify", f"refs/remotes/origin/{BRANCH}")[0] == 0:
        git("update-ref", "-d", f"refs/remotes/origin/{BRANCH}")
    return 0


def publish(data, msg):
    if not write_atomic(data):
        return False
    commit(msg)
    return True


# ---------------- 실행
def run(argv=None, now=None, sheet_reader=None, quote_fetcher=None, out=print):
    ap = argparse.ArgumentParser(description="토스 시세 → live_board.json (live-board 브랜치)")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 계산한 JSON 출력")
    ap.add_argument("--dry-run", action="store_true", help="쓰지 않고 한 줄 요약만")
    a = ap.parse_args(argv)
    readonly = a.check or a.dry_run
    now_utc = (now or (lambda: datetime.now(ZoneInfo("UTC"))))()
    sheet_reader = sheet_reader or read_sheet_values
    quote_fetcher = quote_fetcher or fetch_quotes

    if not readonly and not os.path.isdir(WORKTREE):
        out(f"작업트리 없음: {WORKTREE} (VERIFY.md 설치 3단계)")
        return 3

    if not is_market_open(now_utc):
        cur = None if readonly else load_current()
        if readonly:
            out(json.dumps({"market_open": False, "note": "장 닫힘 — API 안 부름 · 기존 JSON 의 market_open 만 false 로"},
                           ensure_ascii=False))
            return 0
        if isinstance(cur, dict) and cur.get("market_open") is True:
            cur["market_open"] = False   # 시세·행·합계는 마지막 장중 값 그대로
            publish(cur, f"live_board: 장 마감 {stamps(now_utc)[0]} KST")
        return push_if_needed()

    try:
        values = sheet_reader()
        soxl, tqqq, fx = quote_fetcher()
        _, rows, totals = compute(values, soxl, tqqq, fx)
        data, code = build_ok(now_utc, soxl, tqqq, fx, rows, totals), 0
    except LiveError as exc:
        data, code = build_fail(now_utc, str(exc)), 1
    except Exception as exc:   # 시트 토큰·네트워크 등 — 코드만 남김 (메시지에 계정 이메일이 들어갈 수 있음)
        name = type(exc).__name__
        data, code = build_fail(now_utc, ("sheet_error" if name == "SheetError" else "error_" + name)), 1

    if a.check:
        out(json.dumps(data, ensure_ascii=False, indent=2))
        out(f"(토큰 공유 hook: {'켜짐' if token_share_active() else '꺼짐/미확인'})")
        return code
    if a.dry_run:
        out(("ok" if data["ok"] else "실패 " + data["error"]) + " · 쓰지 않음")
        return code

    if not same_content(load_current(), data):
        publish(data, f"live_board {data['as_of_kst']} KST" + ("" if data["ok"] else " (실패)"))
    print(("ok" if data["ok"] else "실패 " + data["error"]), flush=True)
    rc = push_if_needed()
    return code or rc


if __name__ == "__main__":
    sys.exit(run())
