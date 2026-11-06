#!/usr/bin/env python3
"""사무실 비서 정기 브리핑 (평일 09:00 · 16:30 KST, systemd timer)
- 읽기 전용: 주문·설정 변경 없음. 잔고 조회만 합니다.
- 시장분석실 점수 / 오늘 필요한 달러·원화 / 봇 상태 / 결재·리스크 현황을 사무실 비서 텔레그램으로 보냅니다.
- 사무실 v1.0.47 (2026-10-28): ① 토스 토큰 공유 연결 복구(10/27 다른 업로드로 지워졌던 것) — 2·3번 봇과 같은 토큰 사용
  ② 스나이퍼 현 장부 {"SOXL": {...}} 읽기 복구 ③ 간결 브리핑에 '토스 달러 확인'(2번 다음 1회분 + 3번 미국 적립 vs 보유 달러)
  ④ 봇 5개·서버 상태 한 줄 요약 (이상 있으면 기존처럼 상세)
- 사무실 v1.1.4 (2026-11-02): '토스 달러 확인'을 현재 매매법 기준으로 다시 계산 (읽기 전용 · 주문·환전 없음)
  ① 2번 스나이퍼 다음 1회 = 주수 × 매수가 (1회분 예산 그대로가 아님). toss_sniper 코드와 같은 식:
     1회분 예산·Case 67 이중 캡핑(compute_golden8_quota_qty), 장부 가용현금·왕복 수수료(resolve_affordable_buy_qty),
     0주 첫 진입 / 1층 공석 재장전 / 신저가 추매 갈래(sniper_plugin), 매수가능금액 0.2% 안전버퍼
  ② 3번 적립은 실제 주문하는 main.py 규칙(+1%↑ ½, 오늘 완료·익절일 매수 없음)  ③ 조회 실패·가동 OFF는 0으로 두지 않고 '합산 제외' 표시
  ④ 부족하면 내역(2번·3번 분리·보유 달러·부족액)과 함께 🚨 표시, 스나이퍼 당일 추가 매수 상한은 따로 (부족 판정 제외)
- 사무실 v1.1.5 (2026-11-03): '토스 달러 확인'을 2번 v2.0.0(원작 d7b3a66) 매매법으로 다시 계산 (읽기 전용 · 주문·환전 없음)
  ① 본 그리드 1회분 = 순수 코어 자산(가용현금+본·서브·골든포켓 원가−예비수혈금, 기준시드 하한) × 8%, 수수료는 원장 계좌 수수료
  ② 서브 그리드 1회분(4%, 본 0.5회분 보호예수 뒤 유휴현금, 최대 4회분) — 대상이 아니면 '대상 아님'으로 따로 표시
  ③ 예비수혈은 필요액에 더하지 않고 경고로만 (2·3번 같은 계좌) · 골든포켓은 모드가 켜졌을 때만 조건부 표시
- 사무실 v1.1.8 (2026-11-04): 브리핑 간결화 — 형식만 변경 (계산·주문·조회 로직 그대로)
  ① 통합 잔액 블록 대신 '필요 금액' 표 1개 (고정폭 <pre>, 머리말 계좌·보유·필요 1번, 숫자+아이콘, 범례 1번)
  ② 토스(달러·원화)·메리츠(P·VR6)는 이름 1번에 두 줄로 묶음 · 메리츠 보유는 추정 달러만, 필요는 '–'
  ③ 시장 일정은 평일 휴장일만 표시 (진행 중·예정 문구 없음) · 조회 실패는 휴장으로 단정하지 않고 전달 노트로
- 사무실 v1.2.7 (2026-11-05): 스나이퍼 v2.2.0(원작 골든포켓 폐기 + 기존 골든 → 지하층 보관) 대응 — 달러 계산 부분만
  ① 골든 필요 달러 조건 줄(모드 ≠ NONE) 제거 · 상수 목록에서 DEFAULT_GOLDEN_ALLIN_MODE 제거(원작에서 삭제된 상수)
  ② 순수 코어 자산 = max(기준시드, 가용현금 + 본·서브 투입원가 − 예비수혈금) — 골든/지하층 원가는 넣지 않음 (sniper_plugin core_equity 와 같음)
  ③ 지하층(basement_pocket)이 원장에 있을 때만 참고 1줄(수량·비용) — 필요 달러·코어 자산·보유 차감 어디에도 넣지 않음, 없으면 줄 없음
- 사무실 v1.3.2 (2026-11-05): '필요 금액' 표 한투에 USD 줄 추가 (USD 먼저·KRW 다음, 필요 '-', USD 조회 실패는 0 아님 + 노트) — kis_balances() 1번 호출, 그 밖 로직 그대로
- 사무실 v1.3.3 (2026-11-06): 스나이퍼 v2.3.0(원작 a4b4790 Case 91) 대응 — 달러 계산 부분만, 형식 그대로
  ① 원장 portion_mode 가 단리(SIMPLE_08PCT 등)일 때만 1회분 예산 기준 = 초기 시드 고정 (본 8%·서브 4%·서브 보호예수 0.5회분)
     복리 또는 portion_mode 없음(구 원장) = 기존 공식 그대로 (순수 코어 자산)
  ② 시멘트추가(예비시드) 무제한: 참고 1줄(현재 회분·금액·총 횟수)만 — 필요 달러 계산에는 넣지 않음 · 표시 문구 '수혈'→'시멘트추가'
  ③ 지하층 참고 줄·보유 차감 1회·실패 조회 제외 목록 그대로
"""
# 2026-10-30: 메리츠 P·VR6 2계좌 분리 조회 및 독립 토큰 캐시 (브리핑 전용, 버전은 업데이트 비서 부여)
import base64, hashlib, hmac, html, json, math, os, subprocess, sys, time, urllib.parse, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:  # [🔗토스 토큰 공유 HOOK] 2·3번 봇과 같은 토큰 사용 (새로 발급해 봇 토큰을 끊지 않음)
    import toss_token_share as _TTS
except Exception:
    _TTS = None

R = Path(os.environ.get("OFFICE_ROOT", "/"))
HOME = R / "home/gieokkim"
TOSS_DIR, SNIPER_DIR, BITHUMB_DIR = HOME / "toss_dca_bot", HOME / "toss_sniper", HOME / "bithumb_laoeo_bot"
TELEGRAM_CFG = R / "etc/bot-office/telegram.json"
OFFICE_URL = R / "etc/bot-office/office_url"
MARKET = R / "var/lib/bot-office/market-manual/score.json"
RISK = R / "var/lib/bot-office/risk_report.json"
CASES = R / "var/lib/bot-office/pipeline/cases.json"
TOSS_API = os.environ.get("BRIEF_TOSS_API", "https://openapi.tossinvest.com")
BITHUMB_API = os.environ.get("BRIEF_BITHUMB_API", "https://api.bithumb.com")
TELEGRAM_API = os.environ.get("BRIEF_TELEGRAM_API", "https://api.telegram.org")
KST, EST = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
UNITS = [("1번 한투 라오어", "han4384tubot.service"), ("2번 토스 스나이퍼", "toss_sniper.service"),
         ("3번 토스 적립", "toss_dca.service"), ("4번 빗썸 적립", "bithumb_bot.service"),
         ("5번 팬딩", "bot-office-fanding.service")]


SEP = "━━━━━━━━━━━━━━━"   # 항목 구분선


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def read_env(p):
    env = {}
    try:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def http(method, url, headers=None, data=None, timeout=12):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        endpoint = urllib.parse.urlsplit(url).path
        detail = ""
        try:
            body = json.loads(e.read(2000) or b"{}")
            body = body.get("error") if isinstance(body.get("error"), dict) else body
            detail = str(body.get("code") or body.get("errorCode") or body.get("message") or "")[:60]
        except Exception:
            pass
        raise RuntimeError(f"API {endpoint}: HTTP {e.code}" + (f" ({detail})" if detail else "")) from None
    with response as r:
        return json.loads(r.read(2_000_000) or b"{}")


def money(v, cur):
    return f"${v:,.2f}" if cur == "USD" else f"{v:,.0f}원"


def balance_value(value):
    """Missing/malformed API values are unavailable, never zero."""
    if value is None or isinstance(value, bool) or not str(value).strip():
        raise ValueError("잔액 값 누락")
    result = float(str(value).replace(",", ""))
    if not math.isfinite(result):
        raise ValueError("잔액 값 오류")
    return result


# ------------------------------------------------------------------ 토스 (읽기 전용)
class Toss:
    def __init__(self, directory=None):
        env = read_env((directory or TOSS_DIR) / ".env")
        self.cid, self.sec = env.get("TOSS_CLIENT_ID", ""), env.get("TOSS_CLIENT_SECRET", "")
        self.token = self.acc = None

    def _get(self, path, account=True):
        """401(토큰 만료/교체 가능성)이면 새 토큰으로 딱 1회만 다시 시도한다."""
        try:
            return self._get_once(path, account)
        except RuntimeError as e:
            if "HTTP 401" not in str(e):
                raise
            self._bad = self.token or ""   # [🔗토스 토큰 공유 HOOK] 거절된 토큰 기억
            self.token = None
            time.sleep(1)
            return self._get_once(path, account)

    def _get_once(self, path, account=True):
        if not self.token and _TTS is not None:   # [🔗토스 토큰 공유 HOOK]
            try:
                sh = _TTS.try_acquire(TOSS_API, self.cid, self.sec, bool(getattr(self, "_bad", "")), getattr(self, "_bad", ""), "브리핑")
            except Exception:
                sh = None
            if sh and sh[0] == "ok":
                self.token = sh[1]
        if not self.token:
            d = http("POST", f"{TOSS_API}/oauth2/token", {"Content-Type": "application/x-www-form-urlencoded"},
                     urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": self.cid, "client_secret": self.sec}).encode())
            self.token = d.get("access_token")
            if not self.token:
                raise RuntimeError("토스 인증 실패")
        h = {"Authorization": f"Bearer {self.token}"}
        if account:
            if not self.acc:
                accs = (http("GET", f"{TOSS_API}/api/v1/accounts", h).get("result") or [])
                pick = [a for a in accs if isinstance(a, dict) and a.get("accountType") == "BROKERAGE"] or [a for a in accs if isinstance(a, dict)]
                self.acc = pick[0].get("accountSeq") if pick else None
            if self.acc is None:
                raise RuntimeError("토스 조회 계좌 없음")
            h["X-Tossinvest-Account"] = str(self.acc)
        return http("GET", f"{TOSS_API}{path}", h).get("result")

    def buying_power(self, cur):
        return balance_value((self._get(f"/api/v1/buying-power?currency={cur}") or {}).get("cashBuyingPower"))

    def holding(self, sym):
        items = (self._get(f"/api/v1/holdings?symbol={urllib.parse.quote(sym)}") or {}).get("items") or []
        it = items[0] if items and isinstance(items[0], dict) else {}
        return float(it.get("quantity") or 0), float(it.get("averagePurchasePrice") or 0), float(it.get("lastPrice") or 0)

    def price(self, sym):
        """현재가 — 3번 적립 toss_api.get_current_price 와 같은 /api/v1/prices. 값이 없으면 오류 (0으로 바꾸지 않음)"""
        rows = self._get(f"/api/v1/prices?symbols={urllib.parse.quote(sym)}", account=False) or []
        p = num(rows[0].get("lastPrice")) if isinstance(rows, list) and rows and isinstance(rows[0], dict) else 0.0
        if p <= 0:
            raise ValueError("현재가 없음")
        return p


# ------------------------------------------------------------------ 빗썸 (읽기 전용)
def bithumb_accounts():
    env = read_env(BITHUMB_DIR / ".env_vars")
    ak, sk = env.get("BITHUMB_ACCESS_KEY", ""), env.get("BITHUMB_SECRET_KEY", "")
    if not ak or not sk:
        raise RuntimeError("빗썸 키를 찾지 못함")
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=")
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps({"access_key": ak, "nonce": str(uuid.uuid4()), "timestamp": round(time.time() * 1000)}, separators=(",", ":")).encode())
    sig = b64(hmac.new(sk.encode(), head + b"." + body, hashlib.sha256).digest())
    res = http("GET", f"{BITHUMB_API}/v1/accounts", {"Authorization": "Bearer " + (head + b"." + body + b"." + sig).decode()})
    if not isinstance(res, list):
        raise RuntimeError("빗썸 잔액 응답 오류")
    return {a["currency"]: a for a in res if isinstance(a, dict) and "currency" in a}


def bithumb_price(coin):
    res = http("GET", f"{BITHUMB_API}/v1/ticker?markets=KRW-{coin}")
    return float(res[0]["trade_price"]) if isinstance(res, list) and res else 0.0


# ------------------------------------------------------------------ 한국투자: 기존 봇 토큰으로 GET 조회만
def kis_balances():
    result = {"KRW": None, "USD": None}
    try:
        env = read_env(Path(os.environ.get("BRIEF_KIS_ENV", str(HOME / ".env"))))
        key, secret, cano = (os.environ.get(k) or env.get(k, "") for k in ("APP_KEY", "APP_SECRET", "CANO"))
        product = os.environ.get("ACNT_PRDT_CD") or env.get("ACNT_PRDT_CD", "01")
        if not key or not secret or not cano or not cano.isdigit() or len(cano) != 8:
            return result
        # No token issuance, refresh, deletion, or changes to the trading bot.
        token_path = Path(os.environ.get("BRIEF_KIS_TOKEN", str(HOME / "data" / f"token_{cano}.dat")))
        token = load(token_path, {}).get("token")
        if not token:
            return result
        headers = {"authorization": "Bearer " + token, "appkey": key, "appsecret": secret,
                   "content-type": "application/json; charset=utf-8", "custtype": "P"}
        common = {"CANO": cano, "ACNT_PRDT_CD": product}
        requests = [
            ("KRW", "TTTC8434R", "/uapi/domestic-stock/v1/trading/inquire-balance",
             dict(common, AFHR_FLPR_YN="N", OFL_YN="", INQR_DVSN="01", UNPR_DVSN="01",
                  FUND_STTL_ICLD_YN="N", FNCG_AMT_AUTO_RDPT_YN="N", PRCS_DVSN="00",
                  CTX_AREA_FK100="", CTX_AREA_NK100="")),
            ("USD", "CTRP6504R", "/uapi/overseas-stock/v1/trading/inquire-present-balance",
             dict(common, WCRC_FRCR_DVSN_CD="02", NATN_CD="840", TR_MKET_CD="00", INQR_DVSN_CD="00")),
        ]
        for currency, tr_id, path, params in requests:
            try:
                response = http("GET", "https://openapi.koreainvestment.com:9443" + path
                                + "?" + urllib.parse.urlencode(params), dict(headers, tr_id=tr_id))
                if response.get("rt_cd") != "0":
                    continue
                rows = response.get("output2")
                rows = [rows] if isinstance(rows, dict) else rows
                if not isinstance(rows, list):
                    continue
                if currency == "USD":
                    # Select by currency, never assume the first row is USD or sum currencies.
                    rows = [row for row in rows if isinstance(row, dict) and row.get("crcy_cd") == "USD"]
                if len(rows) != 1 or not isinstance(rows[0], dict):
                    continue
                field = "dnca_tot_amt" if currency == "KRW" else "frcr_dncl_amt_2"
                result[currency] = balance_value(rows[0].get(field))
            except Exception:
                # Isolate KRW/USD failures and never expose authenticated URLs or keys.
                continue
    except Exception:
        pass
    return result


def balance_lines(kis, usd, krw_toss, krw_b):
    def amount(value, currency):
        return money(value, currency) if value is not None else "조회 불가"
    return ["💰 <b>통합 잔액 · 계좌별 조회</b>",
            f"🏦 한국투자 예수금: {amount(kis.get('KRW'), 'KRW')} / {amount(kis.get('USD'), 'USD')}",
            f"🔷 토스 조회 계좌 · 현금 주문가능금액: {amount(krw_toss, 'KRW')} / {amount(usd, 'USD')}",
            f"🪙 빗썸 사용가능 원화: {amount(krw_b, 'KRW')}",
            "ℹ️ RP 미포함",
            "⚖️ 조회 항목 기준이 달라 합산하지 않음 · 부족액은 해당 계좌에서 보충"]


def sniper_balance_lines(toss):
    """Check identity before reporting 2/3 as one account; never sum duplicated cash."""
    other = Toss(SNIPER_DIR)
    if not other.cid or not other.sec:
        return ["🔷 토스 추가 인증: 조회 설정 확인 필요"]
    if other.cid == toss.cid and other.sec == toss.sec:
        return ["ℹ️ 같은 토스 인증을 쓰는 봇이 여럿이라 금액 중복표시 생략"]
    values = {}
    for currency in ("KRW", "USD"):
        try:
            values[currency] = money(other.buying_power(currency), currency)
        except Exception:
            values[currency] = "조회 불가"
    if other.acc is not None and toss.acc is not None and str(other.acc) == str(toss.acc):
        return ["ℹ️ 동일 토스 계좌 확인 · 금액 중복표시 생략"]
    return [f"🔷 토스 추가 인증 계좌 · 현금 주문가능금액: {values['KRW']} / {values['USD']}"]


def _meritz_brief_token_cache(label, shared_token, keys_path):
    """브리핑 전용 캐시. 팬딩 P/VR6 토큰은 읽기만 하며 절대 쓰지 않는다."""
    import stat
    import tempfile
    base = Path(tempfile.gettempdir()) / f"bot-office-meritz-brief-{os.getuid()}"
    try:
        base.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = base.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise PermissionError("브리핑 전용 토큰 폴더 권한 오류")
    private = base / f"{label.lower()}_token.json"
    if private.exists() or private.is_symlink():
        state = private.lstat()
        if (not stat.S_ISREG(state.st_mode) or state.st_uid != os.getuid()
                or stat.S_IMODE(state.st_mode) & 0o077):
            raise PermissionError("브리핑 전용 토큰 파일 권한 오류")

    # 기존 팬딩 유효 토큰을 전용 캐시에 복사해서 재발급을 줄인다. 원본에는 쓰지 않는다.
    try:
        saved = json.loads(Path(shared_token).read_text(encoding="utf-8"))
        key_data = json.loads(Path(keys_path).read_text(encoding="utf-8"))
        prefix = key_data["app_key"].strip()[:6]
        exp = float(saved["exp"])
        if (not isinstance(saved.get("token"), str) or not saved["token"]
                or saved.get("key") != prefix or not math.isfinite(exp)
                or exp <= time.time() + 120):
            raise ValueError("사용 가능한 공유 토큰 없음")
        local = load(private, {})
        try:
            local_exp = float(local.get("exp", 0))
        except (TypeError, ValueError, AttributeError):
            local_exp = 0
        if exp > local_exp:
            fd, tmp = tempfile.mkstemp(prefix="token_", dir=str(base))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump({"token": saved["token"], "exp": exp, "key": prefix}, f)
                os.replace(tmp, private)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"[MERITZ_BRIEF] {label}: 공유 토큰 사용 불가, 계좌별 전용 캐시 사용 ({type(e).__name__})", file=sys.stderr)
    return private


def meritz_fetch():
    """메리츠 P·VR6 별도 외화잔고 조회 (읽기 전용) [MERITZ_BAL_V4].
    → [(label, by_currency dict | None, 실패 사유 | None)] · 계좌/통화 합산 금지."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    result = []
    accounts = (
        ("P", R / "etc/bot-office/meritz.json",
         R / "var/lib/bot-office/fanding/meritz_token.json"),
        ("VR6", R / "etc/bot-office/meritz_vr6.json",
         R / "var/lib/bot-office/fanding/meritz_vr6_token.json"),
    )
    for label, keys_path, shared_token in accounts:
        try:
            if not keys_path.is_file():
                result.append((label, None, "계좌 키 없음"))
                continue
            import meritz_client
            private_token = _meritz_brief_token_cache(label, shared_token, keys_path)
            # 키와 토큰을 둘 다 명시한다. 인자 없는 Meritz()는 VR6에서 절대 금지.
            response = meritz_client.Meritz(keys_path, token_cache=private_token)._call(
                "GET", "/accounts/v1/me/overseas/currencies")
            rows = response.get("data")
            if not isinstance(rows, list):
                raise ValueError("외화잔고 응답 형식 오류")
            by_currency = {}
            for item in rows:
                if isinstance(item, dict):
                    cur = str(item.get("crcd", "")).strip().upper()
                    if cur in ("USD", "KRW") and cur not in by_currency:
                        by_currency[cur] = item
            result.append((label, by_currency, None))
        except Exception as e:
            # API 에러 응답에는 키·토큰 내용이 섞일 수 있어 메시지는 버리고 형식만 쓴다.
            if isinstance(e, PermissionError):
                reason = "토큰/키 접근 권한 오류"
            elif isinstance(e, ValueError):
                reason = "잔고 응답 형식 오류"
            else:
                reason = f"조회 오류 ({type(e).__name__})"
            result.append((label, None, reason))
    return result


def _meritz_amount(by_currency, cur, field):
    try:
        return balance_value(by_currency[cur][field])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None


def meritz_lines(fetched=None):
    """💰 잔액 메뉴용 표시 (문구는 v1.1.5 그대로). USD 추정(estm_frcr_amt)과 예수금(frcr_amt) 모두 표시."""
    result = []
    for label, by_currency, reason in (meritz_fetch() if fetched is None else fetched):
        prefix = f"🏛 메리츠 {label}"
        if by_currency is None:
            result.append(f"{prefix} | 조회 불가 ({html.escape(reason[:80])})")
            continue

        def amount(cur, field):
            v = _meritz_amount(by_currency, cur, field)
            return money(v, cur) if v is not None else "조회 불가"

        estimated, deposited = amount("USD", "estm_frcr_amt"), amount("USD", "frcr_amt")
        result.append(f"{prefix} | 추정 예수금 USD {estimated} (앱 기준) · 예수금 {deposited}")
        if "KRW" in by_currency:
            result.append(f"   ↳ KRW {amount('KRW', 'frcr_amt')}")
    return result


def toss_account_lines():
    toss = Toss()
    values = {}
    for cur in ("USD", "KRW"):
        try:
            values[cur] = money(toss.buying_power(cur), cur)
        except Exception:
            values[cur] = "조회 불가"
    return [f"🔷 토스 | USD {values['USD']} · KRW {values['KRW']}"]


def section_balances(now=None, which="all"):
    """계좌별 현금 잔액만 표시. 시간·주문 필요액·추가 안내는 출력하지 않는다."""
    names = {"kis": "한국투자", "toss": "토스", "meritz": "메리츠", "bithumb": "빗썸", "all": "전체"}
    which = which if which in names else "all"
    out = ["💰 <b>통합 잔액</b>" if which == "all" else f"💰 <b>잔액 · {names[which]}</b>"]

    if which in ("toss", "all"):
        out.extend(toss_account_lines())

    if which in ("meritz", "all"):
        out.extend(meritz_lines())

    if which in ("kis", "all"):
        try:
            kis = kis_balances()
        except Exception:
            kis = {"KRW": None, "USD": None}
        usd = money(kis.get("USD"), "USD") if kis.get("USD") is not None else "조회 불가"
        krw = money(kis.get("KRW"), "KRW") if kis.get("KRW") is not None else "조회 불가"
        out.append(f"🏦 한국투자 | USD {usd} · KRW {krw}")

    if which in ("bithumb", "all"):
        try:
            krw = money(balance_value(bithumb_accounts().get("KRW", {}).get("balance")), "KRW")
        except Exception:
            krw = "조회 불가"
        # 빗썸 현금 계정은 KRW 기준이며 USD 현금 잔액은 제공하지 않는다.
        out.append(f"🪙 빗썸 | USD — · KRW {krw}")

    return "\n".join(out)


def next_weekday(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def us_session(now_est, end_hm="15:50"):
    d = now_est.date() if now_est.strftime("%H:%M") <= end_hm else now_est.date() + timedelta(days=1)
    return next_weekday(d)


def kr_session(now_kst):
    d = now_kst.date() if now_kst.strftime("%H:%M") <= "15:00" else now_kst.date() + timedelta(days=1)
    return next_weekday(d)


# ------------------------------------------------------------------ 브리핑 구성
def section_market():
    m = load(MARKET, {})
    items, total = m.get("items") or [], m.get("total")
    if total is None:
        return ["📊 <b>시장분석실</b>", "▫️ 점수 미입력 · 사무실 시장분석실에서 금리·물가·시장심리 점수를 넣어 주세요"], None
    sig = json.dumps([total, [[x.get("name"), x.get("score")] for x in items if isinstance(x, dict)]], ensure_ascii=False)
    if load(SEEN, {}).get("market") == sig:
        return ["📊 <b>시장분석실</b> · 변동 없음"], total
    _NEW_SEEN["market"] = sig
    tag = "🟢 우호" if total >= 70 else ("🟡 중립" if total >= 40 else "🔴 주의")
    parts = " · ".join(f"{html.escape(str(x.get('name')))} {x.get('score')}" for x in items if isinstance(x, dict))
    hist = [h for h in (m.get("history") or []) if isinstance(h, dict) and h.get("total") is not None]
    diff = ""
    if len(hist) >= 2:
        d = float(hist[-1]["total"]) - float(hist[-2]["total"])
        diff = f" (직전 대비 {d:+.1f})" if abs(d) >= 0.05 else " (직전과 같음)"
    lines = ["📊 <b>시장분석실</b>", f"📈 종합 <b>{total:.1f}점</b> / 100 {tag}{diff}", f"🧮 {parts}"]
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(m["updated_at"])
        if age > timedelta(days=3):
            lines.append(f"▫️ ⏰ 마지막 입력 {age.days}일 전 · 점수 갱신 권장")
    except (KeyError, ValueError, TypeError):
        pass
    return lines, float(total)


def num(value, default=0.0):
    try:
        v = float(str(value).replace(",", ""))
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def sniper_ledger():
    """toss_sniper 원장(JSON) 중 v6.0 항목(free_cash_usd/initial_seed_usd)이 있는 가장 최근 파일."""
    best = None
    try:
        files = [f for f in SNIPER_DIR.glob("*.json") if "ledger" in f.name.lower()]
    except OSError:
        files = []
    for f in files:
        data = load(f, {})
        if isinstance(data, dict) and isinstance(data.get("SOXL"), dict):   # 현 장부 형식 {"SOXL": {...}}
            data = data["SOXL"]
        if isinstance(data, dict) and ("free_cash_usd" in data or "initial_seed_usd" in data):
            try:
                mt = f.stat().st_mtime
            except OSError:
                mt = 0
            if best is None or mt > best[0]:
                best = (mt, f, data)
    return (best[1], best[2]) if best else (None, {})


# ------------------------------------------------------------------ 2번 스나이퍼 다음 1회 (v2.0.0 매매법 · 원장 읽기 전용)
# 사무실 v1.1.5 (2026-11-03): main toss_sniper v2.0.0(원작 d7b3a66) 식을 그대로 옮김. 원장 파일은 읽기만 한다.
#  · 순수 코어 자산 = max(기준시드, 가용현금 + 본·서브 투입원가 − 예비수혈금)  (sniper_plugin 매수 게이트의 core_equity · 사무실 v1.2.7: 골든/지하층 제외)
#  · 본 1회분 = quant_engine.compute_golden8_quota_qty (8% · Case 67 이중 캡핑) / 서브 1회분 = compute_sub4_quota_qty (4%)
#  · 매수 주수 = quant_engine.resolve_affordable_buy_qty (예산 상한 → 현금 → 매수가×(1+왕복 수수료))
#  · 왕복 수수료 = quant_engine.resolve_effective_round_trip_fee_rate_pct (원장 round_trip_fee_rate_pct → us_commission_rate×200 → 상수)
#  · 30% 가드·예비수혈 = quant_engine.evaluate_guard30_and_reserve_injection (최대 MAX_RESERVE_PORTIONS회분)
#  · 와이드 단차 = quant_engine.get_golden8_prog_thresholds (회차 = max(보유 회차, cycle_ratchet_max_lots))
#  · 1층 공석 재장전 = quant_engine.evaluate_l2_only_hybrid_reentry_signal (±1%, 2층 단가 이하만 · Case 73·84)
#  · 서브 가용 유휴현금 = quant_engine.compute_sub_grid_available_idle_cash (본 0.5회분 보호예수 차감)
#  · 토스 매수가능금액 0.2% 안전버퍼 = sniper_plugin (raw_bp × 0.998)
# 필요 달러는 '주수 × 매수가'(수수료·버퍼 포함 보유액 기준). 예비수혈은 새 돈이 아니라 계좌 달러 용도 전환이라 더하지 않는다.
SNIPER_BP_BUFFER_PCT = 0.2
SNIPER_CONST_FALLBACK = {   # main 2026-11-03 toss_sniper v2.0.0 값 (toss_api.py · quant_engine.py) · 사무실 v1.3.3: v2.3.0 무제한 시멘트추가 → MAX_RESERVE_PORTIONS 999999
    "ROUND_TRIP_FEE_RATE_PCT": 0.14, "PORTION_RATIO_LOCKED": 0.08, "SUB_PORTION_RATIO_4PCT": 0.04,
    "SUB_RESERVE_MAIN_PORTIONS": 0.5, "SUB_FROZEN_DAYS_TRIGGER": 5, "SUB_MAX_TOTAL_LOTS_4": 4,
    "MAX_RESERVE_PORTIONS": 999999, "MIN_DIP_BUDGET_RATIO": 0.30, "MIN_DIP_VS_L1_RATIO": 0.30,
    "DEFAULT_INITIAL_SEED_USD": 10000.0, "REENTRY_PULLBACK_DROP_PCT": -1.0, "REENTRY_BREAKOUT_RISE_PCT": 1.0,
}


def sniper_constants():
    """toss_sniper/toss_api.py · quant_engine.py 상수를 실행하지 않고 글자로만 읽는다 → (값, 안내). 못 읽은 값은 main 기준값 + 안내."""
    import ast
    vals = {}
    for fname in ("toss_api.py", "quant_engine.py"):
        try:
            body = ast.parse((SNIPER_DIR / fname).read_text(encoding="utf-8")).body
        except (OSError, SyntaxError, ValueError):
            body = []
        for node in body:
            tgt = node.target if isinstance(node, ast.AnnAssign) else (
                node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
            if (isinstance(tgt, ast.Name) and tgt.id in SNIPER_CONST_FALLBACK and tgt.id not in vals
                    and node.value is not None):
                try:
                    v = ast.literal_eval(node.value)
                except (ValueError, TypeError, SyntaxError):
                    continue
                want = SNIPER_CONST_FALLBACK[tgt.id]
                if isinstance(want, str) and isinstance(v, str):
                    vals[tgt.id] = v
                elif not isinstance(want, str) and isinstance(v, (int, float)) and not isinstance(v, bool):
                    vals[tgt.id] = float(v)
    missing = [k for k in SNIPER_CONST_FALLBACK if k not in vals]
    note = "" if not missing else f"스나이퍼 상수 {len(missing)}개 확인 실패 → main 기준값 사용"
    return {k: vals.get(k, v) for k, v in SNIPER_CONST_FALLBACK.items()}, note


def _int(value):
    """toss_api.safe_int 과 같음: 정수 근처면 반올림, 아니면 내림"""
    f = num(value)
    return int(round(f)) if abs(f - round(f)) < 1e-6 else int(math.floor(f))


def _cents_floor(p):
    return math.floor((p + 1e-9) * 100.0) / 100.0


# 사무실 v1.3.3 · Case 91: = quant_engine.is_simple_income_mode (단리 표기). 서브 단리는 SIMPLE_04PCT.
SNIPER_SIMPLE_MODES = ("SIMPLE_08PCT", "FIXED_800", "SIMPLE", "INCOME", "SIMPLE_04PCT")


def sniper_is_simple(led):
    """원장 portion_mode 가 단리(인출형)인지. 필드가 없으면(구 원장) 복리로 취급."""
    return isinstance(led, dict) and str(led.get("portion_mode") or "COMP_08PCT").upper().strip() in SNIPER_SIMPLE_MODES


def golden8_target_qty(anchor_price, equity, seed, mode, exec_price, ratio):
    """= quant_engine.compute_golden8_quota_qty → (목표 주수, 1회분 예산). equity 에는 순수 코어 자산을 넣는다.
    COMP_08PCT/SUB_04PCT(복리): 예산 = max(기준시드, 코어 자산) × 비율 / 단리(SIMPLE_08PCT·SIMPLE_04PCT·FIXED_800): 예산 = 기준시드 × 비율"""
    seed = max(100.0, seed)
    budget = round((seed if mode in SNIPER_SIMPLE_MODES else max(seed, equity)) * ratio, 4)
    qty = max(1, int(math.floor((budget + 1e-9) / max(0.01, anchor_price))))
    if exec_price is not None and exec_price > 0:   # Case 67: 실제 매수가 기준 예산 상한 주수로 한 번 더 캡핑
        qty = min(max(1, int(math.floor((budget + 1e-9) / max(0.01, exec_price)))), qty)
    return qty, budget


def affordable_buy_qty(target_qty, price, free_cash, broker_bp, budget, fee_pct):
    """= quant_engine.resolve_affordable_buy_qty → (매수 주수, 주수 × 매수가). 수수료 포함 1주 값보다 현금이 적으면 0주."""
    qty = max(0, int(target_qty))
    if qty <= 0 or price <= 0:
        return 0, 0.0
    if budget is not None and budget > 0:
        qty = min(max(1, int(math.floor((budget + 1e-9) / price))), qty)
    cash = max(0.0, free_cash)
    if broker_bp is not None and broker_bp >= 0:
        cash = min(cash, broker_bp)
    unit = price * (1.0 + fee_pct / 100.0)
    if cash < unit:
        return 0, 0.0
    qty = max(0, min(qty, int(math.floor((cash + 1e-9) / unit))))
    return qty, (round(qty * price, 4) if qty > 0 else 0.0)


def _drop_pct(lots, ratchet):
    """= quant_engine.get_golden8_prog_thresholds (WIDE_RUNWAY): 회차 = max(1, 보유 회차, 사이클 최고 회차)"""
    n = max(1, lots, max(0, ratchet))
    return -1.0 if n <= 4 else (-2.0 if n <= 8 else (-3.5 if n <= 10 else -5.5))


def _sniper_buckets(raw):
    """= quant_engine.StratumBucket.from_dict (순수 원가: 단가 = 실제 원가 ÷ 주수). 앞쪽(0번)이 1층.
    upper = quant_engine.is_upper_grid_tier (본 2~7층 · 서브 2~3층 · 합병층)"""
    out = []
    for b in raw if isinstance(raw, list) else []:
        if not isinstance(b, dict) or _int(b.get("qty")) <= 0:
            continue
        q = _int(b.get("qty"))
        p = num(b.get("book_price"), num(b.get("buy_price"), 0.0))
        cost = num(b.get("actual_cost_usd"), num(b.get("book_invested_usd"), q * max(0.0, p)))
        if cost <= 0 and p > 0:
            cost = q * p
        if cost <= 0:
            continue
        cost, tag = round(cost, 4), str(b.get("lot_type") or "QUOTA_L1").upper().strip()
        upper = (tag in ("MERGED_UPPER", "SUB_MERGED") or (tag.startswith("GRID_L") and tag != "GRID_L1")
                 or (tag.startswith("SUB_L") and tag != "SUB_L1"))
        out.append({"qty": q, "cost": cost, "price": round(cost / q, 4), "lots": max(1, _int(b.get("lot_count"))),
                    "upper": upper})
    return out


def sniper_fee(led, consts):
    """= quant_engine.resolve_effective_round_trip_fee_rate_pct(state_dict=원장) → 왕복 수수료(%)"""
    rt = num(led.get("round_trip_fee_rate_pct"))
    if 0.0 < rt <= 2.0:
        return round(rt, 4)
    one = num(led.get("us_commission_rate"))
    if 0.0 < one <= 0.01:
        return round(one * 200.0, 4)
    return consts["ROUND_TRIP_FEE_RATE_PCT"]


def sniper_core(led, consts):
    """원장에서 공통 값: 기준시드·가용현금·수혈금·본/서브 층·순수 코어 자산·수수료 (지하층은 참고값만 · 계산 제외)"""
    seed = max(100.0, num(led.get("initial_seed_usd"), consts["DEFAULT_INITIAL_SEED_USD"]))
    free = max(0.0, num(led.get("free_cash_usd")))
    inj = max(0.0, num(led.get("injected_reserve_usd")))
    main_b, sub_b = _sniper_buckets(led.get("buckets")), _sniper_buckets(led.get("sub_buckets"))
    invested = sum(b["cost"] for b in main_b) + sum(b["cost"] for b in sub_b)   # 사무실 v1.2.7: 골든/지하층 원가 제외
    core = max(seed, free + invested - inj)   # sniper_plugin.execute_seed_protected_buy_gate_plugin 의 core_equity
    return {"seed": seed, "free": free, "inj": inj, "main": main_b, "sub": sub_b,
            "core": round(core, 4), "fee": sniper_fee(led, consts),
            "used_res": max(0, _int(led.get("used_reserve_portions_cnt")))}


def _need_with_buffer(qty, price, fee):
    """스나이퍼가 이 주수를 사려면: 매수가능금액 × (1 − 0.2%) ≥ 주수 × 매수가 × (1 + 왕복 수수료)
    (+0.0001: 버퍼 적용 금액을 소수 4자리로 반올림하는 만큼 — 1센트 경계에서 1주 모자라는 것 방지)"""
    need = (qty * price * (1.0 + fee / 100.0) + 0.0001) / (1.0 - SNIPER_BP_BUFFER_PCT / 100.0)
    return math.ceil(need * 100.0 - 1e-6) / 100.0


def _guard30(free, price, budget, fee, l1_cost, is_dip, used_res, consts):
    """= quant_engine.evaluate_guard30_and_reserve_injection (장부 현금만 보는 부분)
    → ('normal'|'reserve'|'deposit', 최소 필요 현금, 수혈 회분, 수혈 금액). 실제 수혈은 토스 여유 달러가 있을 때만 일어난다."""
    unit = price * (1.0 + fee / 100.0)
    min_req = max(unit, budget * consts["MIN_DIP_BUDGET_RATIO"])
    if is_dip:
        min_req = max(min_req, l1_cost * consts["MIN_DIP_VS_L1_RATIO"])
    if free >= min_req:
        return "normal", min_req, 0, 0.0
    portions = max(1, int(math.ceil((min_req - free - 1e-9) / max(0.01, budget))))
    if int(consts["MAX_RESERVE_PORTIONS"]) - used_res >= portions:
        return "reserve", min_req, portions, round(portions * budget, 4)
    return "deposit", min_req, portions, 0.0


def sniper_next_buy(led, live_price, consts):
    """2번 스나이퍼 본 그리드 '다음 1회' 매수 계산. led = 원장 SOXL dict(읽기만), live_price = SOXL 현재가(실패면 None).
    state: ok | no_cash | deposit_wait(수혈 한도 소진 → 입금 대기) | off | pending | unavailable
    ok 에 guard='reserve' 면 장부 현금이 30% 가드 미만이라 계좌 여유 달러에서 수혈받아 산다 (필요액에 수혈을 따로 더하지 않음).
    갈래가 조건부(재장전·추매)면 조건이 맞는 순간의 가격으로 계산하고, 두 갈래가 가능하면 큰 쪽을 쓴다."""
    if not isinstance(led, dict) or not led:
        return {"state": "unavailable", "why": "원장(JSON) 없음"}
    if not bool(led.get("is_active", True)):
        return {"state": "off"}
    if "initial_seed_usd" not in led or "free_cash_usd" not in led:
        return {"state": "unavailable", "why": "원장에 기준시드·가용현금 없음"}
    c = sniper_core(led, consts)
    ratio, fee, free, buckets = consts["PORTION_RATIO_LOCKED"], c["fee"], c["free"], c["main"]
    # 사무실 v1.3.3 · Case 91: 단리면 SIMPLE_08PCT(초기 시드 고정), 아니면(없음 포함) COMP_08PCT(기존 공식)
    simple = sniper_is_simple(led)
    mode = "SIMPLE_08PCT" if simple else "COMP_08PCT"
    base = {"free": round(free, 2), "fee": fee, "core": c["core"], "seed": c["seed"], "simple": simple,
            "inj": c["inj"], "used_res": c["used_res"], "note": ""}
    if str(led.get("buy_order_id") or "").strip():   # 이미 낸 주문이 '다음 1회' (따로 또 세지 않음)
        q, p = max(1, _int(led.get("ordered_qty"))), num(led.get("buy_price"))
        tag = str(led.get("pending_lot_type") or "").upper()
        return dict(base, state="pending", qty=q, price=p, order_usd=round(q * p, 2), sub=tag.startswith("SUB_"))
    live = _cents_floor(live_price) if live_price and live_price > 0 else None
    anchor = num(led.get("anchor_price"))
    pull_pct, brk_pct = consts["REENTRY_PULLBACK_DROP_PCT"], consts["REENTRY_BREAKOUT_RISE_PCT"]
    is_dip, l1_cost, topup = False, 0.0, None
    if not buckets:   # 분기 A: 0주 → 현재가 지정가 첫 1층 (15:30~16:00 ET 엔 새 사이클 진입 안 함)
        if live is None:
            return dict(base, state="unavailable", why="SOXL 현재가 조회 불가")
        branch, cond = "첫 1층 진입", f"0주 → 현재가 ${live:,.2f} 지정가"
        cands = [(max(0.01, live), anchor if anchor > 0 else max(0.01, live))]
    elif buckets[0]["upper"]:   # 분기 B-1: 1층 공석 → 기준가 ±1% (현재가 ≤ 상단 최저 단가일 때만 · 돌파는 15:30 이후 제외)
        ceil_p = min(b["price"] for b in buckets)
        ref = round(anchor if anchor > 0 else ceil_p, 4)
        pull = round(ref * (1.0 + pull_pct / 100.0), 2)
        brk = round(ref * (1.0 + brk_pct / 100.0), 2)
        branch = "1층 재장전"
        chg = (live_price - ref) / ref * 100.0 if live is not None and ref > 0 else 0.0
        if live is not None and live <= ceil_p + 1e-6 and (chg <= pull_pct or chg >= brk_pct):
            cands, cond = [(max(0.01, live), ref)], f"현재가 ${live:,.2f}가 이미 조건 충족 ({chg:+.2f}%)"
        else:
            cands = [(pull, ref)] + ([(brk, ref)] if brk <= ceil_p + 1e-6 else [])
            cond = (f"조건부: ${pull:,.2f} 이하" + (f" 또는 ${brk:,.2f} 이상" if brk <= ceil_p + 1e-6 else "")
                    + f" (상단 최저 단가 ${ceil_p:,.2f} 이하만 · 돌파는 15:30~16:00 ET 제외)")
    else:
        l1 = buckets[0]
        l1_target = max(l1["qty"], _int(led.get("l1_target_quota_qty")))
        if l1_target > l1["qty"]:   # 분기 B-0: 1층 미체결 잔량 보충 (1층 단가 재도래 때 · 수혈 없음)
            rem, l1p = l1_target - l1["qty"], round(l1["price"], 2)
            px = max(0.01, min(live, l1p)) if live is not None and live <= l1p + 1e-6 else l1p
            topup = {"rem": rem, "budget": round(rem * l1p, 4)}
            branch, cond = "1층 잔량 보충", f"조건부: 1층 단가 ${l1p:,.2f} 이하 재도래 (잔량 {rem}주)"
            cands = [(px, l1p)]
        else:   # 분기 B-2: 활성 1층 → 기억저가 대비 4단 와이드 신저가 추매 (지정가 = min(현재가, 조건가))
            lots = sum(b["lots"] for b in buckets)
            ratchet = max(lots, _int(led.get("cycle_ratchet_max_lots")))
            drop = _drop_pct(lots, ratchet)
            a = num(led.get("anchor_price"), l1["price"])
            ref = min([x for x in (l1["price"], a, num(led.get("cycle_min_buy_price"))) if x > 0] or [l1["price"]])
            trig = _cents_floor(ref * (1.0 + drop / 100.0))
            branch, is_dip, l1_cost = "신저가 추매", True, l1["cost"]
            chg = (live_price - ref) / ref * 100.0 if live is not None and ref > 0 else 0.0
            if live is not None and chg <= drop:
                cands, cond = [(max(0.01, min(live, trig)), ref)], f"현재가 ${live:,.2f}가 이미 조건 충족 ({chg:+.2f}%)"
            else:
                cands = [(max(0.01, trig), ref)]
                cond = (f"조건부: ${trig:,.2f} 이하 (기억저가 ${ref:,.2f}의 {drop:.1f}% · 회차 {lots}"
                        + (f" · 사이클 최고 {ratchet}회차 잠금" if ratchet > lots else "") + ")")
    best = None
    for px, ref_p in cands:
        if topup:
            tq, budget, guard = topup["rem"], topup["budget"], ("normal", 0.0, 0, 0.0)
        else:
            tq, budget = golden8_target_qty(ref_p, c["core"], c["seed"], mode, px, ratio)
            guard = _guard30(free, px, budget, fee, l1_cost, is_dip, c["used_res"], consts)
        cash = free + guard[3] if guard[0] == "reserve" else free   # 수혈되면 장부 현금이 그만큼 늘어난 뒤 주수 계산
        q, spent = affordable_buy_qty(tq, px, cash, None, budget, fee)
        cur = {"qty": q, "price": px, "anchor": ref_p, "budget": budget, "target": tq, "order_usd": round(spent, 2),
               "guard": guard[0], "min_req": round(guard[1], 2), "inj_portions": guard[2], "inj_usd": round(guard[3], 2),
               "cash_used": round(cash, 2)}
        if best is None or (cur["order_usd"], px) > (best["order_usd"], best["price"]):
            best = cur
    res = dict(base, branch=branch, cond=cond, **best)
    if best["guard"] == "deposit":
        return dict(res, state="deposit_wait")
    if best["qty"] <= 0:
        return dict(res, state="no_cash", unit=round(best["price"] * (1.0 + fee / 100.0), 2))
    return dict(res, state="ok", need_usd=_need_with_buffer(best["qty"], best["price"], fee))


def sniper_sub_next_buy(led, live_price, consts):
    """2번 서브 그리드 '다음 1회' (= sniper_plugin._execute_sub_grid_buy_engine_plugin, 원장 읽기 전용).
    state: ok | target_no(대상 아님 — why 에 코드 조건) | no_cash(유휴현금 부족) | unavailable.
    서브는 예비수혈·입금 알림을 쓰지 않고 '본 0.5회분 보호예수를 뺀 유휴 현금' 안에서만 산다."""
    if not isinstance(led, dict) or not led or "free_cash_usd" not in led:
        return {"state": "unavailable", "why": "원장 없음"}
    if not bool(led.get("is_active", True)):
        return {"state": "target_no", "why": "가동 OFF"}
    if str(led.get("buy_order_id") or "").strip() or str(led.get("sell_order_id") or "").strip():
        return {"state": "target_no", "why": "본·서브 미체결 주문 진행 중"}
    c = sniper_core(led, consts)
    if not c["main"]:
        return {"state": "target_no", "why": "본 그리드 0주 (서브는 본 그리드 보유 중에만)"}
    frozen = max(0, _int(led.get("main_consec_frozen_days")))
    need_days = int(consts["SUB_FROZEN_DAYS_TRIGGER"])
    sub = c["sub"]
    if not sub and frozen < need_days:
        return {"state": "target_no", "why": f"본 그리드 무매매 {frozen}일 < {need_days}일"}
    lots = sum(b["lots"] for b in sub)
    cap = max(1, _int(led.get("sub_max_total_lots")) or int(consts["SUB_MAX_TOTAL_LOTS_4"]))
    fee = c["fee"]
    # = compute_sub_grid_available_idle_cash (코어 자산 하한 DEFAULT_INITIAL_SEED_USD · 본 1회분 × 0.5 보호예수)
    c_eq = max(consts["DEFAULT_INITIAL_SEED_USD"], c["core"])
    simple = sniper_is_simple(led)   # 사무실 v1.3.3 · Case 91: 단리면 보호예수 기준도 초기 시드
    base_eq = c["seed"] if simple else c_eq
    reserved = round(round(base_eq * consts["PORTION_RATIO_LOCKED"], 4) * consts["SUB_RESERVE_MAIN_PORTIONS"], 4)
    idle = round(max(0.0, c["free"] - reserved), 4)
    base = {"free": round(c["free"], 2), "fee": fee, "reserved": round(reserved, 2), "idle": round(idle, 2),
            "lots": lots, "cap": cap}
    live = _cents_floor(live_price) if live_price and live_price > 0 else None
    sub_anchor = num(led.get("sub_anchor_price"))
    pull_pct, brk_pct = consts["REENTRY_PULLBACK_DROP_PCT"], consts["REENTRY_BREAKOUT_RISE_PCT"]
    topup = None
    if not sub:   # S-A: 서브 0주 → 현재가 지정가 서브 1층 (15:30~16:00 ET 제외)
        if live is None:
            return dict(base, state="unavailable", why="SOXL 현재가 조회 불가")
        branch, cond = "서브 첫 1층", f"본 무매매 {frozen}일 → 현재가 ${live:,.2f} 지정가"
        cands = [(max(0.01, live), sub_anchor if sub_anchor > 0 else max(0.01, live))]
    elif sub[0]["upper"]:   # S-B1: 서브 1층 공석 → ±1% 재장전
        if lots >= cap:
            return dict(base, state="target_no", why=f"서브 상한 {cap}회분 도달")
        ceil_p = min(b["price"] for b in sub)
        ref = round(sub_anchor if sub_anchor > 0 else ceil_p, 4)
        pull, brk = round(ref * (1.0 + pull_pct / 100.0), 2), round(ref * (1.0 + brk_pct / 100.0), 2)
        branch = "서브 1층 재장전"
        cands = [(pull, ref)] + ([(brk, ref)] if brk <= ceil_p + 1e-6 else [])
        cond = f"조건부: ${pull:,.2f} 이하" + (f" 또는 ${brk:,.2f} 이상" if brk <= ceil_p + 1e-6 else "")
    else:
        l1 = sub[0]
        tgt = max(l1["qty"], _int(led.get("sub_l1_target_quota_qty")))
        if tgt > l1["qty"]:   # S-B0: 서브 1층 잔량 보충
            rem, l1p = tgt - l1["qty"], round(l1["price"], 2)
            topup = {"rem": rem, "budget": round(rem * l1p, 4)}
            branch, cond = "서브 1층 잔량 보충", f"조건부: 서브 1층 단가 ${l1p:,.2f} 이하 (잔량 {rem}주)"
            cands = [(l1p, l1p)]
        else:   # S-B2: 서브 활성 1층 → 와이드 신저가 (서브 회차·서브 최고 회차)
            if lots >= cap:
                return dict(base, state="target_no", why=f"서브 상한 {cap}회분 도달")
            ratchet = max(lots, _int(led.get("sub_ratchet_max_lots")))
            drop = _drop_pct(lots, ratchet)
            a = num(led.get("sub_anchor_price"), l1["price"])
            ref = min([x for x in (l1["price"], a, num(led.get("sub_cycle_min_buy_price"))) if x > 0] or [l1["price"]])
            trig = _cents_floor(ref * (1.0 + drop / 100.0))
            branch, cond = "서브 신저가 추매", f"조건부: ${trig:,.2f} 이하 (서브 기억저가 ${ref:,.2f}의 {drop:.1f}%)"
            if live is not None and live <= trig:
                cands = [(max(0.01, min(live, trig)), ref)]
            else:
                cands = [(max(0.01, trig), ref)]
    best = None
    for px, ref_p in cands:
        if topup:
            tq, budget = topup["rem"], topup["budget"]
        else:   # = compute_sub4_quota_qty (4% · Case 67 이중 캡핑)
            tq, budget = golden8_target_qty(ref_p, c["core"], c["seed"], "SIMPLE_04PCT" if simple else "SUB_04PCT", px, consts["SUB_PORTION_RATIO_4PCT"])
        min_req = max(px * (1.0 + fee / 100.0), budget * consts["MIN_DIP_BUDGET_RATIO"])
        q, spent = affordable_buy_qty(tq, px, idle, idle, budget, fee) if idle >= min_req or topup else (0, 0.0)
        cur = {"qty": q, "price": px, "budget": budget, "target": tq, "order_usd": round(spent, 2), "min_req": round(min_req, 2)}
        if best is None or (cur["order_usd"], px) > (best["order_usd"], best["price"]):
            best = cur
    res = dict(base, branch=branch, cond=cond, **best)
    if best["qty"] <= 0:
        return dict(res, state="no_cash")
    return dict(res, state="ok", need_usd=_need_with_buffer(best["qty"], best["price"], fee))


def sniper_qty_with_bp(sn, usd):
    """지금 토스 매수가능금액(usd)으로 스나이퍼가 실제 살 주수 (sniper_plugin 과 같이 0.2% 버퍼 적용)"""
    bp = round(max(0.0, usd) * (1.0 - SNIPER_BP_BUFFER_PCT / 100.0), 4)
    cash = sn.get("cash_used", sn["free"])
    return affordable_buy_qty(sn["target"], sn["price"], cash, bp, sn["budget"], sn["fee"])[0]


def sniper_plan():
    """(호환용 — 지금 브리핑 build() 는 쓰지 않는 section_money 전용) → (다음 1회 필요, 장부 가용현금까지, 상세 줄).
    계산은 sniper_next_buy() 와 같다. 계산 못 하면 0이 아니라 '합산 제외'라고 줄에 적는다."""
    _, led = sniper_ledger()
    consts, _ = sniper_constants()
    try:
        live = Toss().price("SOXL")
    except Exception:
        live = None
    sn = sniper_next_buy(led, live, consts)
    if sn["state"] != "ok":
        return 0.0, 0.0, [f"↳ 2번 다음 1회 계산 안 됨({html.escape(str(sn.get('why') or sn['state']))}) → 합산 제외"]
    return sn["need_usd"], max(sn["need_usd"], sn["free"]), [
        f"↳ {sn['branch']} {sn['qty']}주 × ${sn['price']:,.2f} = ${sn['order_usd']:,.2f} ({sn['cond']})"]


SEEN = R / "var/lib/bot-office/briefing-calendar/seen.json"
_NEW_SEEN = {}


def commit_seen():
    """정기 전송이 성공했을 때만 '마지막으로 보여 준 값'을 저장한다(수동 미리보기는 저장 안 함)."""
    if not _NEW_SEEN:
        return
    data = load(SEEN, {})
    data.update(_NEW_SEEN)
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    tmp = SEEN.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(SEEN)
    _NEW_SEEN.clear()


def section_money(now):
    """필요 달러/원화 계산. (lines, 조언 목록)"""
    now_kst, now_est = now.astimezone(KST), now.astimezone(EST)
    lines, tips = [], []
    toss, toss_err = Toss(), ""
    us_day, kr_day = us_session(now_est), kr_session(now_kst)

    sn_min, sn_max, sn_lines = sniper_plan()
    pre_day = next_weekday(now_est.date() if now_est.strftime("%H:%M") <= "09:29" else now_est.date() + timedelta(days=1))

    # 3번 적립: 다음 세션 매수 예정
    cfg = load(TOSS_DIR / "dca_config.json", {})
    us_need, kr_need, us_det, kr_det = 0.0, 0.0, [], []
    if cfg.get("is_master_active", True):
        for sym, s in (cfg.get("stocks") or {}).items():
            if not isinstance(s, dict) or not s.get("enabled", True) or s.get("s_mode", "buy_1") not in ("buy_1", "buy_2"):
                continue
            is_kr = s.get("currency") == "KRW"
            day = (kr_day if is_kr else us_day).isoformat()
            if s.get("last_exec_date") == day:
                continue
            base = float(s.get("base_amount") or (100000.0 if is_kr else 40.0))
            half, price = False, 0.0
            try:
                q, avg, price = toss.holding(sym)
                half = q > 0 and avg > 0 and price > 0 and (price / avg - 1) * 100 >= 1.0
            except Exception as e:
                toss_err = toss_err or str(e)[:80]
            amt = base / 2 if half else base
            if is_kr:
                cost = max(1, int(amt // price)) * price if price > 0 else amt
                kr_need += cost; kr_det.append(f"{sym} {cost:,.0f}원{'(½)' if half else ''}")
            else:
                us_need += amt; us_det.append(f"{sym} ${amt:,.0f}{'(½)' if half else ''}")

    try:
        usd = toss.buying_power("USD")
    except Exception as e:
        usd, toss_err = None, toss_err or str(e)[:80]
    try:
        krw_toss = toss.buying_power("KRW")
    except Exception as e:
        krw_toss, toss_err = None, toss_err or str(e)[:80]

    need_min, need_max = sn_min + us_need, sn_max + us_need
    lines.append("💵 <b>토스 달러 (미국장)</b>")
    lines.append(f"🎯 2번 스나이퍼 {pre_day.strftime('%m/%d')} 프리장 (SOXL)")
    lines += sn_lines
    lines.append(f"🔁 3번 적립 {us_day.strftime('%m/%d')} 미국장: ${us_need:,.2f}" + (f" [{', '.join(us_det)}]" if us_det else " (예정 없음)"))
    lines.append(f"🧾 필요 합계: 1회분만 <b>${need_min:,.2f}</b> · 장부 전액까지 <b>${need_max:,.2f}</b>")
    if usd is None:
        lines.append("💵 보유 달러: 조회 실패")
    else:
        lines.append(f"💵 보유 달러: ${usd:,.2f}")
        if usd < need_min:
            lines.append(f"🚨 <b>${need_min - usd:,.2f} 부족</b> (1회분도 모자람)")
            tips.append(f"환전 필요: 최소 ${need_min - usd:,.0f} · 최대 매수까지 ${need_max - usd:,.0f}")
        elif usd < need_max:
            lines.append(f"⚠️ 장부 가용현금 전액까지는 <b>${need_max - usd:,.2f} 부족</b> (1회분은 충분)")
            tips.append(f"스나이퍼 추가 매수까지 하려면 ${need_max - usd:,.0f} 환전 권장")
        else:
            lines.append("✅ 장부 전액까지 충분")

    lines.append("")
    lines.append("🇰🇷 <b>원화</b>")
    if kr_need > 0:
        bal = f" / 토스 원화 {krw_toss:,.0f}원" if krw_toss is not None else ""
        lines.append(f"🔁 3번 적립 {kr_day.strftime('%m/%d')} 11:00 국내장: {kr_need:,.0f}원 [{', '.join(kr_det)}]{bal}")
        if krw_toss is not None and krw_toss < kr_need:
            tips.append(f"토스 원화 {kr_need - krw_toss:,.0f}원 부족 (국내 적립)")
    else:
        lines.append("🔁 3번 적립 국내장: 예정 없음")

    # 4번 빗썸: 오늘(또는 내일) 19:00 정기매수
    bcfg = load(BITHUMB_DIR / "bot_config.json", {})
    bst = load(BITHUMB_DIR / "bot_state.json", {})
    buy_h = int(bcfg.get("buy_hour", 19))
    b_day = now_kst.date()   # 빗썸은 매일(주말 포함) buy_hour 이후 자정 전까지 매수
    done_map = bst.get("last_action_date") or {}
    try:
        accs, berr = bithumb_accounts(), ""
    except Exception as e:
        accs, berr = None, str(e)[:80]
    b_need, b_det = 0.0, []
    if bcfg.get("power", True):
        for coin, base in (bcfg.get("coins") or {}).items():
            try:
                base = float(base)
            except (TypeError, ValueError):
                continue
            if base <= 0:
                continue
            if done_map.get(coin) == b_day.isoformat():
                b_det.append(f"{coin} ✅완료"); continue
            half = False
            if accs:
                a = accs.get(coin, {})
                bal, avg = float(a.get("balance") or 0), float(a.get("avg_buy_price") or 0)
                try:
                    cur = bithumb_price(coin)
                except Exception:
                    cur = 0.0
                half = bal > 0 and avg > 0 and cur > 0 and (cur / avg - 1) * 100 >= 1.0
            amt = max(5000, int(base / 2) if half else base)
            b_need += amt; b_det.append(f"{coin} {amt:,.0f}원{'(½)' if half else ''}")
    try:
        krw_b = balance_value((accs or {}).get("KRW", {}).get("balance"))
    except (TypeError, ValueError):
        krw_b = None
    when = "오늘" if b_day == now_kst.date() else "내일"
    lines.append("")
    lines.append("🪙 <b>빗썸 (원화)</b>")
    lines.append(f"🔁 4번 빗썸 {when} {buy_h:02d}:00: {b_need:,.0f}원" + (f" [{', '.join(b_det)}]" if b_det else " (예정 없음)")
                 + (f" / 빗썸 원화 {krw_b:,.0f}원" if krw_b is not None else f" / 잔고 조회 실패"))
    if krw_b is not None and krw_b < b_need:
        tips.append(f"빗썸 원화 {b_need - krw_b:,.0f}원 입금 필요 ({when} {buy_h:02d}:00 전)")
    errs = [e for e in (toss_err and f"토스 {toss_err}", berr and f"빗썸 {berr}") if e]
    if errs:
        lines.append("⚠️ 조회 오류: " + html.escape(" / ".join(errs)))
    summary = balance_lines(kis_balances(), usd, krw_toss, krw_b) + sniper_balance_lines(toss)
    return summary + [""] + lines, tips


def dca_plan(toss, cfg, us_day, kr_day):
    """3번 적립 다음 세션 매수 예정 — 실제 주문하는 toss_dca_bot/main.py execute_100day_step 과 같은 규칙.
    (dca_engine.evaluate_dca_decision·profit_lock 경로는 tg_controller.py 전용이고 main.py 는 부르지 않음)
    · 전체 전원 OFF / 종목 OFF / 오늘 완료(last_exec_date) / pause·sell·decision → 매수 없음
    · 익절 구간(tp1 이상 1차 · tp1×2 이상 2차, 아직 안 했으면)이면 그날은 익절 매도만 하고 매수 없음
    · 수익률 +1.0% 이상(평단·보유 있음) → 기준금액 ½, 그 외 1배. 국내는 max(1, 금액÷현재가)주 × 현재가
    · 잔고·가격 조회 실패 종목은 0으로 두지 않고 fail 로 빼서 표시
    → {"master": bool, "USD": {...}, "KRW": {...}} — 통화마다 need(합계) · buy · skip · fail · note"""
    out = {c: {"need": 0.0, "buy": [], "skip": [], "fail": [], "note": []} for c in ("USD", "KRW")}
    out["master"] = bool(cfg.get("is_master_active", True))
    if not out["master"]:
        return out
    tp1, sr = num(cfg.get("tp1_pct", 10.0), 10.0), num(cfg.get("sr_pct", 20.0), 20.0)
    for sym, s in (cfg.get("stocks") or {}).items():
        if not isinstance(s, dict) or not s.get("enabled", True):
            continue
        is_kr = s.get("currency") == "KRW"
        cur_code = "KRW" if is_kr else "USD"
        o, day = out[cur_code], (kr_day if is_kr else us_day).isoformat()
        sym_t = html.escape(str(sym))
        if s.get("last_exec_date") == day:
            o["skip"].append(f"{sym_t} 완료")
            continue
        mode = s.get("s_mode", "buy_1")
        if mode == "decision" and _int(s.get("s_day", 0)) < _int(s.get("s_target_days", 100)):
            mode = "buy_1"   # main.py ensure_stock_cycle 과 같음
        if mode not in ("buy_1", "buy_2"):
            continue
        base = num(s.get("base_amount", 100000.0 if is_kr else 40.0))
        try:
            qty, avg, cur = toss.holding(sym)
            if is_kr and cur <= 0:
                cur = toss.price(sym)
        except Exception:
            o["fail"].append(f"{sym_t} 잔고 조회 불가(1배면 {money(base, cur_code)})")
            continue
        if qty <= 0 and s.get("has_held"):
            o["skip"].append(f"{sym_t} 잔고 0주(목록 제외 예정)")
            continue
        prof = (cur - avg) / avg * 100 if avg > 0 and cur > 0 else 0.0
        sold = _int(s.get("sold_stage", 0)) if prof >= tp1 else 0
        stage = 1 if (tp1 <= prof < tp1 * 2 and sold < 1) else (2 if (tp1 * 2 <= prof < tp1 * 3 and sold < 2) else 0)
        sell_q = (min(int(qty), max(1, int(round(qty * sr / 100.0)))) if is_kr else round(qty * sr / 100.0, 4)) if stage else 0
        if qty > 0 and avg > 0 and stage and sell_q > 0:
            o["skip"].append(f"{sym_t} 익절 {stage}차 예정({prof:+.1f}%)")
            continue
        half = avg > 0 and qty > 0 and prof >= 1.0
        amt = base / 2.0 if half else base
        cost = max(1, int(amt // cur)) * cur if is_kr else amt
        o["need"] += cost
        o["buy"].append(f"{sym_t} {money(cost, cur_code)}({'½' if half else '1배'})")
        if s.get("profit_lock"):
            o["note"].append(sym_t)
    return out


def section_dollar_check(now=None, info=None):
    """토스 달러 확인 — 2번 스나이퍼 다음 1회 + 3번 미국 적립 예정 vs 토스 USD 매수가능금액 (읽기 전용, 주문·환전 없음)
    · 부족 = (2번 다음 1회[수수료·0.2% 안전버퍼 포함] + 3번 미국 적립) − 토스 USD 매수가능금액. 2·3번이 같은 계좌면 보유 달러는 1번만 뺀다.
    · 조회 불가·가동 OFF 항목은 0으로 두지 않고 합산에서 빼며 그 사실을 표시한다.
    · 2번 당일 추가 매수(재장전·추매는 조건 충족 때만)는 상한만 따로 보여 주고 부족 판정에 넣지 않는다.
    · 예상 매도 대금은 넣지 않는다 (체결돼 원장·잔고에 반영된 현금만)."""
    now = now or datetime.now(timezone.utc)
    toss, other, excluded = Toss(), Toss(SNIPER_DIR), []
    us_day, kr_day = us_session(now.astimezone(EST)), kr_session(now.astimezone(KST))
    try:
        usd = toss.buying_power("USD")
    except Exception as e:
        usd = None
        excluded.append(f"토스 보유 달러({html.escape(type(e).__name__)})")
    # 2·3번은 같은 토스 키·같은 BROKERAGE 계좌를 쓰는 구조(toss_token_share.py). 다르면 경고만 하고 같은 계좌로 합산
    acct = ("" if other.cid and other.cid == toss.cid and other.sec == toss.sec else
            " · ⚠️ 2번 토스 인증 확인 불가 — 같은 계좌로 보고 합산" if not other.cid else
            " · ⚠️ 2번·3번 토스 인증이 달라 같은 계좌 합산이 맞는지 확인 필요")
    lines = [f"💵 <b>토스 달러 확인</b> · 미국장 {us_day.strftime('%m/%d')}" + acct]
    warn, state, note = [], [], []   # v1.1.8: 간결 표 아래에 쓸 줄 (문구·계산은 그대로, 위치만 분류)

    def _keep(bucket, text):
        lines.append(text)
        bucket.append(text)

    # 2번 스나이퍼 다음 1회 — 본 그리드 + 서브 그리드 (v2.0.0)
    consts, const_note = sniper_constants()
    _, led = sniper_ledger()
    live = None
    if led and bool(led.get("is_active", True)):
        try:
            live = toss.price("SOXL")
        except Exception:
            live = None
    sn = sniper_next_buy(led, live, consts)
    sb = sniper_sub_next_buy(led, live, consts)
    sn_need = sb_need = 0.0
    max_res = int(consts["MAX_RESERVE_PORTIONS"])
    if sn["state"] == "ok":
        sn_need = sn["need_usd"]
        lines.append(f"🎯 2번 본 그리드 다음 1회 · {sn['branch']}: {sn['qty']}주 × ${sn['price']:,.2f} = ${sn['order_usd']:,.2f}")
        lines.append(f"   ↳ {sn['cond']}" + (" · 현재가 조회 불가→조건가 기준" if live is None else ""))
        lines.append(f"   ↳ 1회분 예산 ${sn['budget']:,.2f} " + (f"(인출형·단리 · 초기 시드 ${sn['seed']:,.2f} 고정)" if sn.get("simple") else f"(순수 코어 자산 ${sn['core']:,.2f})") + f" · 수수료 {sn['fee']:.2f}%·안전버퍼 포함 필요 ${sn_need:,.2f}")
        if sn["guard"] == "reserve":
            unalloc = (usd - sn["free"]) if usd is not None else None
            _keep(warn, f"   ↳ 💉 장부 가용현금 ${sn['free']:,.2f} < 30% 가드 ${sn['min_req']:,.2f} → 계좌 여유 달러에서 +{sn['inj_portions']}회분"
                         f"(${sn['inj_usd']:,.2f}) 시멘트추가 후 매수 (시멘트추가는 필요액에 따로 더하지 않음)"
                         + ("" if unalloc is None or unalloc > 0 else " · 지금 계좌 여유 달러 없음 → 입금 전엔 매수 보류"))
        if usd is not None:
            now_q = sniper_qty_with_bp(sn, usd)
            if now_q < sn["qty"]:
                lines.append("   ↳ 지금 보유 달러로는 " + (f"{now_q}주만 가능" if now_q else "매수 불가(0주)"))
    elif sn["state"] == "deposit_wait":
        unalloc = max(0.0, usd - sn["free"]) if usd is not None else 0.0
        rec = max(sn["budget"], sn["inj_portions"] * sn["budget"] - unalloc)
        _keep(state, f"🎯 2번 본 그리드: 시드고갈 · 계좌 여유 달러 부족(시멘트추가 {sn['used_res']}회 사용 중) → 입금 대기 (매수 없음 · 합산 제외)")
        _keep(state, f"   ↳ {sn['branch']} 최소 필요 현금 ${sn['min_req']:,.2f} · 스나이퍼 권장 입금 약 ${rec:,.2f}")
    elif sn["state"] == "no_cash":
        _keep(state, f"🎯 2번 본 그리드 다음 1회: 매수 불가 — 장부 가용현금 ${sn['free']:,.2f}가 수수료 포함 1주 ${sn['unit']:,.2f}보다 적음"
                     " (합산 제외)")
    elif sn["state"] == "off":
        _keep(state, "🎯 2번 스나이퍼: 가동 OFF → 매수 없음 (합산 제외)")
    elif sn["state"] == "pending":
        _keep(state, f"🎯 2번{' 서브' if sn.get('sub') else ''}: 미체결 매수 {sn['qty']}주 × ${sn['price']:,.2f} = ${sn['order_usd']:,.2f} 진행 중")
        excluded.append("2번 미체결 주문(보유 달러에서 이미 빠졌을 수 있음)")
    else:
        _keep(state, "🎯 2번 본 그리드 다음 1회: 계산 불가")
        excluded.append(f"2번 {html.escape(str(sn.get('why') or '계산 불가'))}")
    if sn["state"] not in ("off", "pending"):
        if sb["state"] == "ok":
            sb_need = sb["need_usd"]
            lines.append(f"🧩 2번 서브 그리드 다음 1회 · {sb['branch']}: {sb['qty']}주 × ${sb['price']:,.2f} = ${sb['order_usd']:,.2f}")
            lines.append(f"   ↳ {sb['cond']} · 서브 1회분 ${sb['budget']:,.2f} · 유휴현금 ${sb['idle']:,.2f}"
                         f"(본 0.5회분 ${sb['reserved']:,.2f} 보호) · 서브 {sb['lots']}/{sb['cap']}회분 · 필요 ${sb_need:,.2f}")
        elif sb["state"] == "target_no":
            lines.append(f"🧩 2번 서브 그리드: 대상 아님 ({html.escape(sb['why'])})")
        elif sb["state"] == "no_cash":
            _keep(note, f"🧩 2번 서브 그리드 · {sb['branch']}: 유휴현금 ${sb['idle']:,.2f}이 최소 ${sb['min_req']:,.2f}보다 적어 매수 없음 (합산 제외)")
        else:
            excluded.append(f"2번 서브 {html.escape(str(sb.get('why') or '계산 불가'))}")
    if led and bool(led.get("is_active", True)):
        # 사무실 v1.3.3 · Case 91: 시멘트추가(예비시드)는 무제한 — 참고 1줄(수량·금액)만, 필요 달러 계산 제외
        used = max(0, int(num(led.get("used_reserve_portions_cnt"))))
        tot_cnt = max(used, int(num(led.get("total_reserve_injected_cnt"))))
        _keep(warn, f"⚠️ 2번 시멘트추가: 현재 {used}회분 ${num(led.get('injected_reserve_usd')):,.2f} (총 {tot_cnt}회 · 0주 졸업 때 상환)"
                     " · 시드 고갈 때 토스 계좌 여유 달러를 횟수 제한 없이 씀 — 2·3번 같은 계좌라 3번 적립용 달러까지 쓸 수 있음 (필요 달러 계산 제외)")
    # 사무실 v1.2.7: 지하층(옛 골든포켓 보관분) 참고 1줄 — 원장에 있을 때만. 필요 달러·코어 자산·보유 차감에 넣지 않음.
    bp = led.get("basement_pocket") if isinstance(led, dict) and isinstance(led.get("basement_pocket"), dict) else {}
    if _int(bp.get("qty")) > 0 and num(bp.get("actual_cost_usd")) > 0:
        _keep(state, f"🏚️ 2번 지하층(참고): {_int(bp.get('qty'))}주 · 비용 ${num(bp.get('actual_cost_usd')):,.2f}"
                     " · 새로 사지 않음 · 필요 달러 계산 제외")
    for n in (sn.get("note"), const_note):
        if n:
            _keep(note, "   ↳ " + html.escape(n))

    # 3번 적립
    cfg = load(TOSS_DIR / "dca_config.json", None)
    if isinstance(cfg, dict):
        dca = dca_plan(toss, cfg, us_day, kr_day)
    else:
        dca = {"master": True, **{c: {"need": 0.0, "buy": [], "skip": [], "fail": [], "note": []} for c in ("USD", "KRW")}}
        excluded.append("3번 적립 설정 파일 읽기 실패")
    U, K = dca["USD"], dca["KRW"]
    if not dca["master"]:
        _keep(state, "🔁 3번 적립: 전체 전원 OFF → 매수 없음 (합산 제외)")
    else:
        lines.append(f"🔁 3번 적립 미국 {len(U['buy'])}종목: ${U['need']:,.2f}"
                     + (f" [{', '.join(U['buy'])}]" if U["buy"] else " (예정 없음)"))
        if U["skip"]:
            _keep(note, "   ↳ 매수 없음: " + ", ".join(U["skip"]))
        if U["note"]:
            _keep(note, "   ↳ profit_lock 표시(" + ", ".join(U["note"]) + ")는 실제 주문 코드가 읽지 않아 매수로 셈")
        excluded += [f"3번 {f}" for f in U["fail"]]

    total = round(sn_need + sb_need + U["need"], 2)
    sn_part = (f"2번 ${sn_need:,.2f}" if sn["state"] == "ok" else
               {"off": "2번 OFF", "no_cash": "2번 매수 불가", "deposit_wait": "2번 입금 대기"}.get(sn["state"], "2번 합산 제외"))
    sn_part += (f" + 2번 서브 ${sb_need:,.2f}" if sb_need > 0 else "")
    dca_part = f"3번 ${U['need']:,.2f}" if dca["master"] else "3번 OFF"
    lines.append(f"🧾 당일 예정 합계 ${total:,.2f} ({sn_part} + {dca_part}) · 보유 "
                 + (f"${usd:,.2f}" if usd is not None else "조회 불가"))
    if usd is None:
        lines.append("❔ 보유 달러를 몰라 부족 여부 판정 보류")
    elif usd + 0.005 < total:
        lines.append(f"🚨 <b>토스 달러 ${total - usd:,.2f} 부족</b> — 미국장 전에 토스에서 환전해 주세요")
    else:
        lines.append(("✅ 계산된 항목 기준 충분" if excluded else "✅ 토스 달러 충분") + f" (여유 ${usd - total:,.2f})")
    if sn["state"] == "ok":
        extra = max(0.0, sn["free"] + U["need"] - usd) if usd is not None else 0.0
        lines.append(f"➕ 2번 당일 추가 매수(조건 충족 때만 · 부족 판정 제외): 본 1회당 최대 ${sn['budget']:,.2f}"
                     f" · 장부 가용현금 ${sn['free']:,.2f}까지" + (f" → 다 쓰려면 약 ${extra:,.2f} 더" if extra > 0.005 else ""))

    # 국내 적립 (원화 — 달러 합산에 넣지 않음)
    if dca["master"] and (K["buy"] or K["fail"]):
        line = f"🇰🇷 3번 국내 적립 {kr_day.strftime('%m/%d')}: {K['need']:,.0f}원" + (f" [{', '.join(K['buy'])}]" if K["buy"] else "")
        if K["need"] > 0:
            try:
                krw = toss.buying_power("KRW")
                line += f" · 토스 원화 {K['need'] - krw:,.0f}원 부족" if krw < K["need"] else " · 원화 충분"
            except Exception:
                line += " · 원화 잔액 조회 불가"
        lines.append(line + " (달러 합산 제외)")
        excluded += [f"3번 {f}" for f in K["fail"]]
    if excluded:
        lines.append("⚠️ 합산 제외(조회 불가 등): " + "; ".join(excluded) + " → 실제 필요액은 더 클 수 있음")
    if info is not None:   # v1.1.8 표시용 — 위에서 계산한 값을 그대로 넘김 (새 계산 없음)
        info.update(usd=usd, total=total, sn_part=sn_part, dca_part=dca_part, master=dca["master"],
                    krw_need=K["need"], acct=acct.strip(" ·"), warn=warn, state=state, note=note,
                    excluded=list(excluded), toss=toss)
    return lines


def status_one_line():
    """봇 5개·서버 한 줄 요약"""
    ok = 0
    for _, unit in UNITS:
        try:
            ok += subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=5).stdout.strip() == "active"
        except Exception:
            pass
    try:
        import shutil
        du = shutil.disk_usage("/")
        disk = f"디스크 {du.used / du.total * 100:.0f}%"
    except Exception:
        disk = "디스크 확인 불가"
    try:
        out = subprocess.run(["systemctl", "list-units", "--failed", "--plain", "--no-legend", "--no-pager"],
                             capture_output=True, text=True, timeout=5).stdout
        failed = len([l for l in out.splitlines() if l.strip()])
    except Exception:
        failed = -1
    fail_txt = "실패 서비스 없음" if failed == 0 else (f"실패 서비스 {failed}개" if failed > 0 else "실패 서비스 확인 불가")
    return f"{'🤖' if ok == len(UNITS) else '⚠️'} 봇 {ok}/{len(UNITS)} 정상 · {disk} · {fail_txt}"


def section_bots():
    """이상이 있는 봇만 표시한다. 모두 정상이면 섹션을 생략한다."""
    problems = []
    for name, unit in UNITS:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True, text=True, timeout=5
            )
            status = result.stdout.strip() or "확인 불가"
            if result.returncode != 0 and status == "active":
                status = "확인 불가"
        except Exception:
            status = "확인 불가"
        if status != "active":
            problems.append(f"🔴 {name} · {html.escape(status)}")

    if not problems:
        return [], []
    return ["⚠️ <b>이상 봇</b>"] + problems, [line for line in problems]


def section_office():
    lines, tips = ["🏢 <b>사무실</b>"], []
    cases = (load(CASES, {}).get("cases") or {}).values()
    cnt = lambda *st: sum(1 for c in cases if isinstance(c, dict) and c.get("stage") in st)
    wait, fail, found = cnt("awaiting_approval"), cnt("apply_failed", "push_failed"), cnt("found", "drafting", "draft_failed", "verify_failed", "manual")
    lines.append(f"📝 결재 대기 {wait}건 · 확인 필요 {found}건 · 실패 {fail}건")
    if wait:
        tips.append(f"결재 대기 {wait}건 → 사무실 결재함 확인")
    if fail:
        tips.append(f"적용/업로드 실패 {fail}건 → 업무 흐름판 확인")
    rep = load(RISK, {})
    reps = [r for r in (rep.get("reports") or []) if isinstance(r, dict)]
    crit = [r for r in reps if r.get("level") == "critical"]
    warn = [r for r in reps if r.get("level") == "warning"]
    lines.append(f"🛡 리스크실: 확인 필요 {len(crit)} · 주의 {len(warn)}"
                 + (" · " + html.escape(str((crit or warn)[0].get("title", ""))[:40]) if (crit or warn) else ""))
    for r in crit[:2]:
        tips.append("리스크: " + str(r.get("title", ""))[:50])
    return lines, tips



def section_server_care():
    import subprocess
    import shutil
    import html
    from pathlib import Path
    lines = ["🛠<b>서버 관리 · 매일 08:55</b>"]
    try:
        r = subprocess.run(
            ["systemctl", "show", "bot-server-care.service",
             "-p", "ExecMainStartTimestamp", "-p", "Result",
             "-p", "ActiveState", "-p", "ExecMainStatus"],
            capture_output=True, text=True, timeout=5, check=True)
        d = dict(x.split("=", 1) for x in r.stdout.splitlines() if "=" in x)
        started = d.get("ExecMainStartTimestamp", "")
        if not started:
            status = "첫 실행 대기"
        elif d.get("ActiveState") == "activating":
            status = "관리 진행 중"
        elif d.get("Result") == "success" and d.get("ExecMainStatus") == "0":
            status = "최근 실행 성공"
        else:
            status = "최근 실행 실패 · 확인 필요"
        lines.append("🧰 관리 결과: " + status)
        if started:
            lines.append("⏰ 실행 시각: " + html.escape(started))
    except Exception:
        lines.append("🧰 관리 결과: 조회 실패")

    disk = shutil.disk_usage("/")
    lines.append(
        f"💾 현재 디스크: {disk.used/disk.total:.0%} 사용"
        f" · 여유 {disk.free/1024**3:.2f}GB")
    mem = {}
    for row in Path("/proc/meminfo").read_text().splitlines():
        key, value = row.split(":", 1)
        mem[key] = int(value.split()[0])
    lines.append(
        f"🧠 현재 가용 메모리: {mem['MemAvailable']/1024:.0f}MB"
        f" · 스왑 사용 {(mem['SwapTotal']-mem['SwapFree'])/1024:.0f}MB")
    try:
        r = subprocess.run(
            ["systemctl", "--failed", "--no-legend", "--plain", "--no-pager"],
            capture_output=True, text=True, timeout=5, check=True)
        count = len([x for x in r.stdout.splitlines() if x.strip()])
        lines.append(f"🚨 실패한 서비스: {count}개")
    except Exception:
        lines.append("🚨 실패한 서비스: 조회 실패")
    return lines

def with_separators(lines):
    """섹션 사이 빈 줄을 구분선으로 바꾼다(연속/처음/끝 구분선 제거)."""
    out = []
    for line in lines:
        line = SEP if line == "" else line
        if line == SEP and (not out or out[-1] == SEP):
            continue
        out.append(line)
    while out and out[-1] == SEP:
        out.pop()
    return "\n".join(out)


# ------------------------------------------------------------------ v1.1.8 필요 금액 표 (형식만)
ICON_NEED, ICON_OK = "🚨", "😌"   # 범례: 🚨 충전 필요 / 😌 충분
DASH = "-"   # 고정폭 표 안에서는 ASCII 하이픈 (en dash '–'는 글꼴마다 폭이 달라 줄이 어긋남)


def disp_width(text, hangul=2.0):
    """고정폭 칸 수: 전각(W/F) hangul 칸(기본 2), 나머지 1칸, 결합 문자 0칸.
    hangul 값을 바꿔 폰 글꼴(한글 ≈1.5~1.9칸)에서도 줄이 맞는지 검증할 때 쓴다."""
    import unicodedata
    w = 0.0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        w += hangul if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _pad(text, width, right=False):
    gap = " " * max(0, int(round(width - disp_width(text))))
    return gap + text if right else text + gap


def _cell(value, cur):
    """표 칸은 ASCII 만 (한글 폭이 폰마다 달라 숫자 열이 어긋나지 않게). 통화는 구분 칸(USD·KRW)에 적는다."""
    if value is None:
        return DASH
    return f"${value:,.2f}" if cur == "USD" else f"{value:,.0f}"


def _icon(have, need):
    if have is None or need is None:
        return ""
    return ICON_NEED if have + 0.005 < need else ICON_OK


def need_table(groups):
    """groups = [(계좌, [(구분, 보유 칸, 필요 칸, 아이콘), ...]), ...] → 고정폭 줄 목록 (HTML 이스케이프 전).
    · 머리말 '계좌 보유 필요'는 맨 위 1번. 계좌 이름은 묶음마다 1번, 그 아래 구분 줄(USD·KRW·P·VR6)을 묶는다.
    · 숫자 줄은 왼쪽부터 ASCII 만 써서 어느 글꼴에서도 열이 맞는다. 아이콘은 줄 끝(정렬 밖)."""
    rows = [(sub, have, need, icon) for _, items in groups for sub, have, need, icon in items]
    w_sub = max([len(r[0]) for r in rows] + [0])
    w_label = max(int(disp_width("계좌")), 2 + w_sub)
    w_have = max([len(r[1]) for r in rows] + [int(disp_width("보유"))])
    w_need = max([len(r[2]) for r in rows] + [int(disp_width("필요"))])
    # 머리말 여백은 한글 1.75칸 기준(폰 ≈1.5칸 ~ PC 2칸의 가운데)으로 잡아 어느 글꼴에서도 어긋남을 줄인다.
    h = 1.75
    end_have = w_label + 1 + w_have
    end_need = end_have + 1 + w_need
    gap1 = max(1, int(round(end_have - 2 * h - 2 * h)))
    gap2 = max(1, int(round(end_need - end_have - 2 * h)))
    out = ["계좌" + " " * gap1 + "보유" + " " * gap2 + "필요"]
    for name, items in groups:
        out.append(name)
        for sub, have, need, icon in items:
            out.append(("  " + sub.ljust(w_label - 2) + " " + have.rjust(w_have) + " " + need.rjust(w_need)
                        + (" " + icon if icon else "")).rstrip())
    return out


def _lt(text):
    """태그 없는 문장의 < > 만 이스케이프 (이미 들어간 &amp; 등은 그대로)."""
    return str(text).replace("<", "&lt;").replace(">", "&gt;")


def section_need(now, notes):
    """💰 필요 금액 — 토스 달러 필요액은 section_dollar_check(v1.1.5 계산) 결과를 그대로 쓴다."""
    info = {}
    section_dollar_check(now, info)
    toss = info["toss"]
    usd, total = info["usd"], info["total"]
    if usd is None:
        notes.append("토스 달러 보유 조회 실패 → 충전 필요 판정 보류")
    try:
        krw = toss.buying_power("KRW")
    except Exception as e:
        krw = None
        notes.append(f"토스 원화 보유 조회 실패({html.escape(type(e).__name__)})")
    krw_need = info["krw_need"] if info["master"] else None
    groups = [("토스", [("USD", _cell(usd, "USD"), _cell(total, "USD"), _icon(usd, total)),
                        ("KRW", _cell(krw, "KRW"), _cell(krw_need, "KRW"), _icon(krw, krw_need))])]

    meritz = []
    for label, by_currency, reason in meritz_fetch():
        est = _meritz_amount(by_currency, "USD", "estm_frcr_amt") if by_currency is not None else None
        if est is None:
            notes.append(f"메리츠 {label} 보유 조회 실패" + (f"({html.escape(str(reason)[:60])})" if reason else ""))
        meritz.append((label, _cell(est, "USD"), DASH, ""))
    groups.append(("메리츠", meritz))
    notes.append("메리츠 필요: 계산식 없음 → '-' (지어내지 않음)")

    try:
        kis = kis_balances()   # v1.3.2: 1번만 호출해 KRW·USD 둘 다 받는다
    except Exception:
        kis = {}
    kis_krw, kis_usd = kis.get("KRW"), kis.get("USD")
    if kis_usd is None:
        notes.append("한투 달러: 잔고를 못 받아 조회 불가로 표시")
    if kis_krw is None:
        notes.append("한투 원화: 잔고를 못 받아 0원으로 표시 (표의 KRW 0)")
    groups.append(("한투", [("USD", _cell(kis_usd, "USD"), DASH, ""),
                           ("KRW", _cell(kis_krw or 0.0, "KRW"), DASH, "")]))

    try:
        bt = balance_value(bithumb_accounts().get("KRW", {}).get("balance"))
    except Exception:
        bt = None
        notes.append("빗썸 원화 보유 조회 실패")
    groups.append(("빗썸", [("KRW", _cell(bt, "KRW"), DASH, "")]))

    table = need_table(groups)
    out = ["💰 <b>필요 금액</b>", "<pre>" + "\n".join(html.escape(x, quote=False) for x in table) + "</pre>",
           f"{ICON_NEED} 충전 필요 · {ICON_OK} 충분 · KRW 단위 원",
           "🧾 토스 달러 필요 = " + info["sn_part"] + " + " + info["dca_part"]]
    out += [_lt(x.strip()) for x in info["state"] + info["warn"]]
    if info["acct"]:
        notes.append(info["acct"])
    notes += [_lt(x.strip().removeprefix("↳ ")) for x in info["note"]]
    if info["excluded"]:
        notes.append("토스 달러 합산 제외: " + "; ".join(info["excluded"]) + " → 실제 필요액은 더 클 수 있음")
    return out


def build(now=None, notes=None):
    """간결 브리핑 (v1.1.8): 필요 금액 표 · 봇 한 줄 · 이상 봇 · 전달 노트."""
    notes = list(notes or [])
    try:
        out = section_need(now, notes)
    except Exception as e:
        out = ["💰 <b>필요 금액</b>", "계산 실패"]
        notes.append(f"필요 금액 계산 실패({html.escape(type(e).__name__)})")
    try:
        out += ["", status_one_line()]
        bot_lines, _ = section_bots()
        if bot_lines:
            out.extend(bot_lines)
    except Exception:
        out.extend(["", "⚠️ <b>봇 상태</b>", "🔴 상태 조회 실패"])
    if notes:
        out += ["", "📝 <b>전달 노트</b>"] + ["· " + n for n in notes]
    return with_separators(out)


def message_chunks(text, limit=3500):
    """Keep complete formatted lines; exceptionally long lines become escaped text."""
    def length(value):
        return len(value.encode("utf-16-le")) // 2
    # v1.1.8: <pre>…</pre> 고정폭 블록은 한 덩어리로 다룬다 (메시지 사이에서 끊기면 HTML 이 깨짐).
    # 한 블록이 limit 를 넘으면 줄 단위로 나눠 각 조각을 다시 <pre>…</pre> 로 감싼다.
    units, block = [], None
    for line in text.splitlines():
        if block is None and line.startswith("<pre>") and not line.endswith("</pre>"):
            block = [line]
        elif block is not None:
            block.append(line)
            if line.endswith("</pre>"):
                units.append(block)
                block = None
        else:
            units.append(line)
    if block is not None:   # 닫히지 않은 블록은 평소 줄로 되돌림
        units.extend(block)
    lines = []
    for unit in units:
        if isinstance(unit, list):
            whole = "\n".join(unit)
            if length(whole) <= limit:
                lines.append(whole)
                continue
            body = "\n".join(unit)[len("<pre>"):-len("</pre>")].split("\n")
            piece = []
            for row in body:
                trial = "<pre>" + "\n".join(piece + [row]) + "</pre>"
                if piece and length(trial) > limit:
                    lines.append("<pre>" + "\n".join(piece) + "</pre>")
                    piece = []
                piece.append(row[:limit - 11])
            if piece:
                lines.append("<pre>" + "\n".join(piece) + "</pre>")
            continue
        line = unit
        if length(line) <= limit:
            lines.append(line)
            continue
        from html.parser import HTMLParser
        class Plain(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.parts = []
            def handle_data(self, data):
                self.parts.append(data)
        parser = Plain()
        parser.feed(line)
        fragment = ""
        size = 0
        for char in "".join(parser.parts):
            escaped = html.escape(char)
            width = length(escaped)
            if size + width > limit:
                lines.append(fragment)
                fragment, size = "", 0
            fragment += escaped
            size += width
        if fragment:
            lines.append(fragment)
    chunks, current = [], ""
    for line in lines:
        candidate = current + "\n" + line if current else line
        if length(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def send(text):
    cfg = load(TELEGRAM_CFG, {})
    token, chat = cfg.get("token"), cfg.get("chat_id")
    if not token or not chat:
        print(text); print("\n(사무실 비서 텔레그램 설정이 없어 화면에만 출력)"); return False
    payload = {"chat_id": chat, "parse_mode": "HTML", "disable_web_page_preview": True}
    url = OFFICE_URL.read_text().strip() if OFFICE_URL.exists() else ""
    if url.startswith("https://"):
        payload["reply_markup"] = {"inline_keyboard": [[{"text": "🏢 사무실 열기", "url": url}]]}
    try:
        for chunk in message_chunks(text):
            payload["text"] = chunk
            if not http("POST", f"{TELEGRAM_API}/bot{token}/sendMessage", {"Content-Type": "application/json"}, json.dumps(payload).encode()).get("ok", False):
                return False
        return True
    except Exception as e:
        print("텔레그램 전송 실패:", e); return False



# Official NYSE full-day calendar, reviewed 2026-10-25. Early closes are open.
# https://www.nyse.com/trade/hours-calendars
US_CLOSED = {
    2026: "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    2027: "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    2028: "01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25",
}


def korean_session(day):
    """Read existing KIS token only. Never infer open from missing data."""
    try:
        env = read_env(Path(os.environ.get("BRIEF_KIS_ENV", str(HOME / ".env"))))
        key, secret, cano = (os.environ.get(k) or env.get(k, "") for k in ("APP_KEY", "APP_SECRET", "CANO"))
        if not key or not secret or not cano.isdigit() or len(cano) != 8:
            return None
        token = load(Path(os.environ.get("BRIEF_KIS_TOKEN", str(HOME / "data" / f"token_{cano}.dat"))), {}).get("token")
        if not token:
            return None
        params = {"BASS_DT": day.strftime("%Y%m%d"), "CTX_AREA_FK": "", "CTX_AREA_NK": ""}
        result = http("GET", "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/chk-holiday?" + urllib.parse.urlencode(params),
                      {"authorization": "Bearer " + token, "appkey": key, "appsecret": secret,
                       "tr_id": "CTCA0903R", "custtype": "P"})
        if result.get("rt_cd") != "0":
            return None
        rows = result.get("output", [])
        rows = [rows] if isinstance(rows, dict) else rows
        matches = [r for r in rows if isinstance(r, dict) and r.get("bass_dt") == params["BASS_DT"]]
        if len(matches) == 1 and matches[0].get("opnd_yn") in ("Y", "N"):
            return matches[0]["opnd_yn"] == "Y"
    except Exception:
        pass
    return None


def kr_label(kr, now_kst):
    if kr is False:
        return "휴장"
    if kr is None:
        return "일정 확인 불가 (한국투자 조회)"
    hm = now_kst.strftime("%H:%M")
    if hm < "09:00":
        return "개장일 · 09:00 정규장 시작 예정"
    if hm < "15:30":
        return "개장일 · 정규장 진행 중 (09:00~15:30)"
    return "개장일 · 정규장 마감 (15:30)"


def scheduled_run(now=None):
    """Scheduled delivery only; manual balances and preview remain available."""
    import fcntl
    now = (now or datetime.now(KST)).astimezone(KST)
    day = now.date()
    if day.weekday() >= 5:
        print("주말 정기 브리핑 생략 (KST)")
        return
    folder = R / "var/lib/bot-office/briefing-calendar"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = folder / "state.json"
        cache = load(path, {})
        if cache.get("date") != day.isoformat():
            # Cache even a failed query: KIS asks for at most one daily lookup.
            cache = {"date": day.isoformat(), "kr": korean_session(day), "notice_sent": False}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache), encoding="utf-8")
            tmp.replace(path)
        kr = cache.get("kr")
        # Same calendar date as KST: the US session opening tonight, not NY's previous day.
        us = None if day.year not in US_CLOSED else day.strftime("%m-%d") not in US_CLOSED[day.year].split()
        # v1.1.8: 평일 휴장일만 알린다 (진행 중·예정 문구 없음). 조회 실패는 휴장으로 단정하지 않고 전달 노트로.
        closed = (["🇰🇷 한국장 휴장"] if kr is False else []) + (["🇺🇸 미국장 휴장 (오늘 밤 정규장)"] if us is False else [])
        notes = (["한국장 일정 조회 실패(한국투자) → 휴장 여부 미확인"] if kr is None else []) + \
                (["미국장 일정 확인 불가(달력 갱신 필요) → 휴장 여부 미확인"] if us is None else [])
        lines = (["📅 <b>휴장 · " + day.isoformat() + "</b>"] + closed) if closed else []
        if closed and not cache.get("notice_sent"):
            if send("\n".join(lines)):
                cache["notice_sent"] = True
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(cache), encoding="utf-8")
                tmp.replace(path)
        if kr is False and us is False:
            print("양 시장 휴장: 일반 브리핑 생략")
            return
        text = ("\n".join(lines) + "\n" + SEP + "\n" if lines else "") + build(notes=notes)
        sent = send(text)
        print("전송 결과:", sent)
        if sent:
            commit_seen()



if __name__ == "__main__":
    if "--balances" in sys.argv:
        i = sys.argv.index("--balances")
        which = sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--") else "all"
        text = section_balances(which=which)
        print(text) if "--print" in sys.argv else send(text)
    elif "--print" in sys.argv:
        print(build())
    else:
        scheduled_run()
