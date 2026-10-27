#!/usr/bin/env python3
"""사무실 비서 정기 브리핑 (평일 09:00 · 16:30 KST, systemd timer)
- 읽기 전용: 주문·설정 변경 없음. 잔고 조회만 합니다.
- 시장분석실 점수 / 오늘 필요한 달러·원화 / 봇 상태 / 결재·리스크 현황을 사무실 비서 텔레그램으로 보냅니다.
"""
import base64, hashlib, hmac, html, json, math, os, subprocess, sys, time, urllib.parse, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
            self.token = None
            time.sleep(1)
            return self._get_once(path, account)

    def _get_once(self, path, account=True):
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


def meritz_lines():
    """메리츠 해외계좌 외화 예수금 (읽기 전용 · meritz_client.py 사용) [MERITZ_BAL_V2]
    frcr_amt=예수금, estm_frcr_amt=추정(미결제 포함). 서로 대신 쓰지 않고 둘 다 표시."""
    try:
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        import meritz_client
        c = meritz_client.TOKEN_CACHE
        if c.exists() and not os.access(c, os.R_OK | os.W_OK):
            import tempfile
            meritz_client.TOKEN_CACHE = Path(tempfile.gettempdir()) / f"meritz_token_brief_{os.getuid()}.json"
        rows = meritz_client.Meritz()._call("GET", "/accounts/v1/me/overseas/currencies").get("data")
        if not isinstance(rows, list):
            raise ValueError("외화잔고 형식 확인 필요")
        found, est = {}, None
        for row in rows:
            if isinstance(row, dict):
                cur = str(row.get("crcd", "")).strip().upper()
                if cur in ("USD", "KRW") and cur not in found:
                    found[cur] = balance_value(row.get("frcr_amt"))
                    if cur == "USD":
                        try:
                            est = balance_value(row.get("estm_frcr_amt"))
                        except Exception:
                            est = None
        usd = money(found["USD"], "USD") if "USD" in found else "조회 불가"
        krw = money(found["KRW"], "KRW") if "KRW" in found else "—"
        out = [f"🏛 메리츠 | USD {usd} · KRW {krw}"]
        if est is not None and abs(est - found.get("USD", est)) >= 0.01:
            out.append(f"   ↳ 추정 예수금(미결제 포함) USD {money(est, 'USD')}")
        return out
    except Exception as e:
        why = html.escape(f"{type(e).__name__}: {e}"[:80])
        return [f"🏛 메리츠 | 조회 불가 ({why})"]


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
        if isinstance(data, dict) and ("free_cash_usd" in data or "initial_seed_usd" in data):
            try:
                mt = f.stat().st_mtime
            except OSError:
                mt = 0
            if best is None or mt > best[0]:
                best = (mt, f, data)
    return (best[1], best[2]) if best else (None, {})


def sniper_plan():
    """인피니트 스노우볼 v6.0(SOXL 순수 롱) 기준 필요 달러 → (최소, 최대, 상세 줄).
    1회분 = 코어자산의 8%, 코어자산 = max(기준시드, 가용현금+투입원가-예비수혈금). 예비수혈은 최대 +6회분.
    추매는 10분 게이트·신저가 조건이라 하루 횟수 상한이 없어 '최대'는 장부 가용현금 전액으로 본다."""
    _, led = sniper_ledger()
    if not led:
        return 0.0, 0.0, ["↳ 스나이퍼 원장(JSON)을 찾지 못해 계산 보류 · 확인 필요"]
    if led.get("is_active") is False:
        return 0.0, 0.0, ["↳ 가동 OFF → 0"]
    seed, free = num(led.get("initial_seed_usd")), num(led.get("free_cash_usd"))
    invested, injected = num(led.get("actual_invested_usd")), num(led.get("injected_reserve_usd"))
    left = max(0, 6 - int(num(led.get("used_reserve_portions_cnt"))))
    core = max(seed, free + invested - injected)
    portion = round(core * 0.08, 4)
    if portion <= 0:
        return 0.0, 0.0, ["↳ 기준시드/원장 값 없음 → 계산 보류 · 확인 필요"]
    lines = [f"↳ 1회분 <b>${portion:,.2f}</b> (코어자산 ${core:,.2f}의 8%)",
             f"↳ 장부 가용현금 ${free:,.2f} · 기준시드 ${seed:,.2f}"]
    if free < portion * 0.30:
        lines.append("↳ 🚨 가용현금이 1회분의 30% 미만 → 시드고갈, 자투리 매수 차단")
        need_min = need_max = 0.0
    else:
        need_min, need_max = min(portion, free), free
    lines.append(f"↳ 예비 수혈 +{left}회분 가능 (최대 ${left * portion:,.2f} · 토스 계좌에 입금돼 있으면 자동)")
    return need_min, need_max, lines


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


def build(now=None):
    """간결 브리핑: 계좌별 USD/KRW 잔액과 이상 봇만 표시한다."""
    out = section_balances().splitlines()
    try:
        bot_lines, _ = section_bots()
        if bot_lines:
            out.append("")
            out.extend(bot_lines)
    except Exception:
        out.extend(["", "⚠️ <b>봇 상태</b>", "🔴 상태 조회 실패"])
    return with_separators(out)


def message_chunks(text, limit=3500):
    """Keep complete formatted lines; exceptionally long lines become escaped text."""
    def length(value):
        return len(value.encode("utf-16-le")) // 2
    lines = []
    for line in text.splitlines():
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
        lines = ["📅 <b>주식시장 일정 · " + day.isoformat() + "</b>"]
        lines += ["🇰🇷 한국장: " + kr_label(kr, now),
                  "🇺🇸 미국장: " + ("휴장" if us is False else "정규장 예정" if us is True else "일정 확인 불가 (달력 갱신 필요)"),
                  "▫️ 미국장은 오늘 밤 시작할 미국 현지 같은 날짜의 정규장 기준",
                  "▫️ 정규장 일정 안내 · 거래봇/빗썸 실행 조건은 변경하지 않음"]
        if (kr is not True or us is not True) and not cache.get("notice_sent"):
            if send("\n".join(lines)):
                cache["notice_sent"] = True
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(cache), encoding="utf-8")
                tmp.replace(path)
        if kr is False and us is False:
            print("양 시장 휴장: 일반 브리핑 생략")
            return
        text = "\n".join(lines[:3]) + "\n" + SEP + "\n" + build()
        sent = send(text)
        print("전송 결과:", sent)
        if sent:
            commit_seen()
        if sent and 8 <= now.hour < 12:
            try:
                import price_watch
                price_watch.launch()
            except Exception as error:
                print("가격 추적 시작 실패:", type(error).__name__)


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
