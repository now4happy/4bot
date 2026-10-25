#!/usr/bin/env python3
"""사무실 비서 정기 브리핑 (매일 07:00 · 19:00 KST, systemd timer)
- 읽기 전용: 주문·설정 변경 없음. 잔고 조회만 합니다.
- 시장분석실 점수 / 오늘 필요한 달러·원화 / 봇 상태 / 결재·리스크 현황을 사무실 비서 텔레그램으로 보냅니다.
"""
import base64, hashlib, hmac, html, json, os, subprocess, sys, time, urllib.parse, urllib.request, uuid
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
         ("3번 토스 적립", "toss_dca.service"), ("4번 빗썸 적립", "bithumb_bot.service")]


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
        raise RuntimeError(f"API {endpoint}: HTTP {e.code}") from None
    with response as r:
        return json.loads(r.read(2_000_000) or b"{}")


def money(v, cur):
    return f"${v:,.2f}" if cur == "USD" else f"{v:,.0f}원"


# ------------------------------------------------------------------ 토스 (읽기 전용)
class Toss:
    def __init__(self):
        env = read_env(TOSS_DIR / ".env")
        self.cid, self.sec = env.get("TOSS_CLIENT_ID", ""), env.get("TOSS_CLIENT_SECRET", "")
        self.token = self.acc = None

    def _get(self, path, account=True):
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
            h["X-Tossinvest-Account"] = str(self.acc)
        return http("GET", f"{TOSS_API}{path}", h).get("result")

    def buying_power(self, cur):
        return float((self._get(f"/api/v1/buying-power?currency={cur}") or {}).get("cashBuyingPower") or 0.0)

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
    return {a["currency"]: a for a in res if isinstance(a, dict) and "currency" in a} if isinstance(res, list) else {}


def bithumb_price(coin):
    res = http("GET", f"{BITHUMB_API}/v1/ticker?markets=KRW-{coin}")
    return float(res[0]["trade_price"]) if isinstance(res, list) and res else 0.0


# ------------------------------------------------------------------ 다음 매매 세션 날짜
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
    tag = "🟢 우호" if total >= 70 else ("🟡 중립" if total >= 40 else "🔴 주의")
    parts = " · ".join(f"{html.escape(str(x.get('name')))} {x.get('score')}" for x in items if isinstance(x, dict))
    hist = [h for h in (m.get("history") or []) if isinstance(h, dict) and h.get("total") is not None]
    diff = ""
    if len(hist) >= 2:
        d = float(hist[-1]["total"]) - float(hist[-2]["total"])
        diff = f" (직전 대비 {d:+.1f})" if abs(d) >= 0.05 else " (직전과 같음)"
    lines = ["📊 <b>시장분석실</b>", f"▫️ 종합 <b>{total:.1f}점</b> / 100 {tag}{diff}", f"▫️ {parts}"]
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(m["updated_at"])
        if age > timedelta(days=3):
            lines.append(f"▫️ ⏰ 마지막 입력 {age.days}일 전 · 점수 갱신 권장")
    except (KeyError, ValueError, TypeError):
        pass
    return lines, float(total)


def section_money(now):
    """필요 달러/원화 계산. (lines, 조언 목록)"""
    now_kst, now_est = now.astimezone(KST), now.astimezone(EST)
    lines, tips = [], []
    toss, toss_err = Toss(), ""
    us_day, kr_day = us_session(now_est), kr_session(now_kst)

    # 2번 스나이퍼: 다음 프리장 필요 달러 (1회 금액 × 최대 횟수)
    led = load(SNIPER_DIR / "AssassinLedger_SOXS.json", {})
    seed = float(led.get("budget") or 100.0)
    try:
        max_b = max(1, min(10, int(led.get("max_buy_count", 5))))
    except (TypeError, ValueError):
        max_b = 5
    holding_now = float(led.get("last_buy_price") or 0) > 0
    cnt = int(led.get("buy_count") or 0) if holding_now else 0
    remain = max(0, max_b - cnt)
    if not led.get("is_active", True):
        sn_min = sn_max = 0.0
        sn_desc = "가동 OFF → 0"
    else:
        sn_min, sn_max = (seed if remain else 0.0), seed * remain
        sn_desc = f"1회 ${seed:,.2f} × 최대 {remain}회" + (f" (보유 중 {cnt}/{max_b}회)" if cnt else "")
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
        krw_toss = toss.buying_power("KRW") if kr_need > 0 else None
    except Exception as e:
        krw_toss, toss_err = None, toss_err or str(e)[:80]

    need_min, need_max = sn_min + us_need, sn_max + us_need
    lines.append("💵 <b>토스 달러 (미국장)</b>")
    lines.append(f"▫️ 2번 스나이퍼 {pre_day.strftime('%m/%d')} 프리장: {sn_desc}")
    lines.append(f"▫️ 3번 적립 {us_day.strftime('%m/%d')} 미국장: ${us_need:,.2f}" + (f" [{', '.join(us_det)}]" if us_det else " (예정 없음)"))
    lines.append(f"▫️ 필요 합계: 1회만 사면 <b>${need_min:,.2f}</b> · 최대로 사면 <b>${need_max:,.2f}</b>")
    if usd is None:
        lines.append("▫️ 보유 달러: 조회 실패")
    else:
        lines.append(f"▫️ 보유 달러: ${usd:,.2f}")
        if usd < need_min:
            lines.append(f"▫️ 🚨 <b>${need_min - usd:,.2f} 부족</b> (1회 매수도 모자람)")
            tips.append(f"환전 필요: 최소 ${need_min - usd:,.0f} · 최대 매수까지 ${need_max - usd:,.0f}")
        elif usd < need_max:
            lines.append(f"▫️ ⚠️ 최대 매수까지 <b>${need_max - usd:,.2f} 부족</b> (1회 매수는 충분)")
            tips.append(f"스나이퍼 추가 매수까지 하려면 ${need_max - usd:,.0f} 환전 권장")
        else:
            lines.append("▫️ ✅ 최대로 사도 충분")

    lines.append("")
    lines.append("🇰🇷 <b>원화</b>")
    if kr_need > 0:
        bal = f" / 토스 원화 {krw_toss:,.0f}원" if krw_toss is not None else ""
        lines.append(f"▫️ 3번 적립 {kr_day.strftime('%m/%d')} 11:00 국내장: {kr_need:,.0f}원 [{', '.join(kr_det)}]{bal}")
        if krw_toss is not None and krw_toss < kr_need:
            tips.append(f"토스 원화 {kr_need - krw_toss:,.0f}원 부족 (국내 적립)")
    else:
        lines.append(f"▫️ 3번 적립 국내장: 예정 없음")

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
    krw_b = float((accs or {}).get("KRW", {}).get("balance") or 0) if accs is not None else None
    when = "오늘" if b_day == now_kst.date() else "내일"
    lines.append(f"▫️ 4번 빗썸 {when} {buy_h:02d}:00: {b_need:,.0f}원" + (f" [{', '.join(b_det)}]" if b_det else " (예정 없음)")
                 + (f" / 빗썸 원화 {krw_b:,.0f}원" if krw_b is not None else f" / 잔고 조회 실패"))
    if krw_b is not None and krw_b < b_need:
        tips.append(f"빗썸 원화 {b_need - krw_b:,.0f}원 입금 필요 ({when} {buy_h:02d}:00 전)")
    errs = [e for e in (toss_err and f"토스 {toss_err}", berr and f"빗썸 {berr}") if e]
    if errs:
        lines.append("▫️ ⚠️ 조회 오류: " + html.escape(" / ".join(errs)))
    return lines, tips


def section_bots():
    lines, tips = ["🤖 <b>봇 상태</b>"], []
    row = []
    for name, unit in UNITS:
        try:
            st = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=5).stdout.strip() or "확인 불가"
        except Exception:
            st = "확인 불가"
        row.append(f"{'🟢' if st == 'active' else '🔴'} {name}")
        if st != "active":
            tips.append(f"{name} 봇 상태 확인 필요 ({st})")
    lines.append("▫️ " + " · ".join(row[:2]))
    lines.append("▫️ " + " · ".join(row[2:]))
    led = load(SNIPER_DIR / "AssassinLedger_SOXS.json", {})
    if float(led.get("last_buy_price") or 0) > 0:
        tgt = float(led.get("target_sell_price") or 0)
        lines.append(f"▫️ 스나이퍼 SOXS 보유 중 · 평단 ${float(led['last_buy_price']):,.2f}" + (f" → 익절 ${tgt:,.2f}" if tgt else "")
                     + f" · {int(led.get('buy_count') or 0)}회 매수")
    return lines, tips


def section_office():
    lines, tips = ["🏢 <b>사무실</b>"], []
    cases = (load(CASES, {}).get("cases") or {}).values()
    cnt = lambda *st: sum(1 for c in cases if isinstance(c, dict) and c.get("stage") in st)
    wait, fail, found = cnt("awaiting_approval"), cnt("apply_failed", "push_failed"), cnt("found", "drafting", "draft_failed", "verify_failed", "manual")
    lines.append(f"▫️ 결재 대기 {wait}건 · 확인 필요 {found}건 · 실패 {fail}건")
    if wait:
        tips.append(f"결재 대기 {wait}건 → 사무실 결재함 확인")
    if fail:
        tips.append(f"적용/업로드 실패 {fail}건 → 업무 흐름판 확인")
    rep = load(RISK, {})
    reps = [r for r in (rep.get("reports") or []) if isinstance(r, dict)]
    crit = [r for r in reps if r.get("level") == "critical"]
    warn = [r for r in reps if r.get("level") == "warning"]
    lines.append(f"▫️ 리스크실: 확인 필요 {len(crit)} · 주의 {len(warn)}"
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
        lines.append("• 관리 결과: " + status)
        if started:
            lines.append("• 실행 시각: " + html.escape(started))
    except Exception:
        lines.append("• 관리 결과: 조회 실패")

    disk = shutil.disk_usage("/")
    lines.append(
        f"• 현재 디스크: {disk.used/disk.total:.0%} 사용"
        f" · 여유 {disk.free/1024**3:.2f}GB")
    mem = {}
    for row in Path("/proc/meminfo").read_text().splitlines():
        key, value = row.split(":", 1)
        mem[key] = int(value.split()[0])
    lines.append(
        f"• 현재 가용 메모리: {mem['MemAvailable']/1024:.0f}MB"
        f" · 스왑 사용 {(mem['SwapTotal']-mem['SwapFree'])/1024:.0f}MB")
    try:
        r = subprocess.run(
            ["systemctl", "--failed", "--no-legend", "--plain", "--no-pager"],
            capture_output=True, text=True, timeout=5, check=True)
        count = len([x for x in r.stdout.splitlines() if x.strip()])
        lines.append(f"• 실패한 서비스: {count}개")
    except Exception:
        lines.append("• 실패한 서비스: 조회 실패")
    return lines

def build(now=None):
    now = now or datetime.now(timezone.utc)
    kst = now.astimezone(KST)
    title = "🌅 아침 브리핑" if kst.hour < 12 else "🌙 저녁 브리핑"
    out = [f"🏢 <b>[사무실 비서] {title}</b> · {kst.strftime('%m/%d (%a) %H:%M')} KST", ""]
    if kst.hour < 12:
        try:
            out += section_server_care() + ['']
        except Exception:
            out += ['🛠 서버 상태 조회 실패', '']
    tips = []
    m_lines, score = section_market()
    out += m_lines + [""]
    for fn in (section_money, ):
        try:
            l, t = fn(now); out += l + [""]; tips += t
        except Exception as e:
            out += [f"💵 자금 계산 실패: {html.escape(str(e)[:120])}", ""]
    for fn in (section_bots, section_office):
        try:
            l, t = fn(); out += l + [""]; tips += t
        except Exception as e:
            out += [f"⚠️ {html.escape(str(e)[:120])}", ""]
    try:
        import gemini_usage
        out += [gemini_usage.report(), ""]
    except Exception:
        out += ["💳 Gemini 판독 사용 기록 조회 실패", ""]
    if score is not None and score < 40:
        tips.append("시장 점수 '주의' 구간 → 스나이퍼 최대 매수 횟수를 줄이는 것도 고려")
    out.append("📝 <b>오늘 할 일</b>")
    out += [f"▫️ {html.escape(t)}" for t in tips] if tips else ["▫️ 특별히 챙길 일 없음 ✅"]
    out.append("\n<i>읽기 전용 브리핑 · 주문/설정은 바꾸지 않습니다</i>")
    return "\n".join(out)


def send(text):
    cfg = load(TELEGRAM_CFG, {})
    token, chat = cfg.get("token"), cfg.get("chat_id")
    if not token or not chat:
        print(text); print("\n(사무실 비서 텔레그램 설정이 없어 화면에만 출력)"); return False
    payload = {"chat_id": chat, "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
    url = OFFICE_URL.read_text().strip() if OFFICE_URL.exists() else ""
    if url.startswith("https://"):
        payload["reply_markup"] = {"inline_keyboard": [[{"text": "🏢 사무실 열기", "url": url}]]}
    try:
        return http("POST", f"{TELEGRAM_API}/bot{token}/sendMessage", {"Content-Type": "application/json"}, json.dumps(payload).encode()).get("ok", False)
    except Exception as e:
        print("텔레그램 전송 실패:", e); return False


if __name__ == "__main__":
    text = build()
    if "--print" in sys.argv:
        print(text)
    else:
        print("전송 결과:", send(text))
