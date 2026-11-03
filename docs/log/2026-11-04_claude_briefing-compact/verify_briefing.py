#!/usr/bin/env python3
"""office_briefing.py vNEXT 검증 (가짜 잔고 · 네트워크 차단 · 실주문/환전 없음)
사용: python3 -I verify_briefing.py <main 원본 office_briefing.py> <vNEXT office_briefing.py> [출력폴더]
- 모든 http() 호출을 막고(호출되면 실패로 기록) 토스·한투·빗썸·메리츠 조회는 가짜 값으로 바꾼다.
- 텔레그램 send 는 화면 캡처용 가짜로 바꾼다 (실제 전송 없음).
"""
import importlib.util, json, os, re, sys, tempfile, types
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ORIG, NEW = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3] if len(sys.argv) > 3 else tempfile.mkdtemp()).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(tempfile.mkdtemp(prefix="brief_root_"))
FAKE_SECRET = "FAKE-SECRET-ZZ9"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


# ---------- 가짜 서버 폴더 (비밀값은 모두 가짜 문자열)
home = ROOT / "home/gieokkim"
for d in ("toss_dca_bot", "toss_sniper", "bithumb_laoeo_bot", "data"):
    (home / d).mkdir(parents=True, exist_ok=True)
for d in ("toss_dca_bot", "toss_sniper"):
    (home / d / ".env").write_text(f"TOSS_CLIENT_ID=fakeid\nTOSS_CLIENT_SECRET={FAKE_SECRET}\n")
(home / "bithumb_laoeo_bot/.env_vars").write_text(f"BITHUMB_ACCESS_KEY=a\nBITHUMB_SECRET_KEY={FAKE_SECRET}\n")
(home / "toss_dca_bot/dca_config.json").write_text(json.dumps({"is_master_active": True, "stocks": {
    "QQQ": {"enabled": True, "s_mode": "buy_1", "base_amount": 40, "currency": "USD"},
    "SCHD": {"enabled": True, "s_mode": "buy_1", "base_amount": 30, "currency": "USD"},
    "005930": {"enabled": True, "s_mode": "buy_1", "base_amount": 100000, "currency": "KRW"}}}))
(home / "toss_sniper/AssassinLedger_SOXL.json").write_text(json.dumps({"SOXL": {
    "is_active": True, "free_cash_usd": 2400.0, "initial_seed_usd": 3000.0, "lots": [],
    "used_reserve_portions_cnt": 0, "injected_reserve_usd": 0, "golden_allin_mode": "NONE"}}))
etc = ROOT / "etc/bot-office"
etc.mkdir(parents=True, exist_ok=True)
for f in ("meritz.json", "meritz_vr6.json"):
    (etc / f).write_text(json.dumps({"app_key": "FAKEKEY123", "app_secret": FAKE_SECRET}))
os.environ["OFFICE_ROOT"] = str(ROOT)
os.environ["BRIEF_KIS_ENV"] = str(ROOT / "none.env")

# 가짜 meritz_client (네트워크 없음)
MERITZ = {"P": {"estm": "1532.40", "frcr": "1500.00"}, "VR6": {"estm": "987.65", "frcr": "900.00"}}
fake_mc = types.ModuleType("meritz_client")


class FakeMeritz:
    def __init__(self, keys_path, token_cache=None):
        self.label = "VR6" if "vr6" in str(keys_path) else "P"

    def _call(self, method, path):
        v = MERITZ.get(self.label)
        if v is None:
            raise RuntimeError("fake down")
        return {"data": [{"crcd": "USD", "estm_frcr_amt": v["estm"], "frcr_amt": v["frcr"]}]}


fake_mc.Meritz = FakeMeritz
sys.modules["meritz_client"] = fake_mc


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


old, new = load_mod(ORIG, "brief_old"), load_mod(NEW, "brief_new")
net_calls = []
STATE = {}


def install(m):
    def blocked_http(method, url, *a, **k):
        net_calls.append(url.split("?")[0])
        raise RuntimeError("network blocked in verify")
    m.http = blocked_http
    m._TTS = None

    def bp(self, cur):
        v = STATE["toss"].get(cur)
        if v is None:
            raise RuntimeError("fake toss fail")
        return v
    m.Toss.buying_power = bp
    m.Toss.holding = lambda self, sym: STATE["hold"].get(sym, (0.0, 0.0, 0.0))
    m.Toss.price = lambda self, sym: STATE["price"]
    m.kis_balances = lambda: dict(STATE["kis"])

    def bt():
        if STATE["bithumb"] is None:
            raise RuntimeError("fake bithumb fail")
        return {"KRW": {"balance": str(STATE["bithumb"])}}
    m.bithumb_accounts = bt


for m in (old, new):
    install(m)

SCEN = {
    "부족": dict(toss={"USD": 150.0, "KRW": 50000.0}, kis={"KRW": 1234567.0, "USD": 10.0}, bithumb=88000,
                 price=31.25, hold={"QQQ": (1, 500.0, 498.0), "SCHD": (2, 27.0, 28.0), "005930": (1, 60000, 61000)}),
    "충분": dict(toss={"USD": 9876.54, "KRW": 2500000.0}, kis={"KRW": None, "USD": None}, bithumb=1200000,
                 price=31.25, hold={"QQQ": (1, 500.0, 498.0), "SCHD": (2, 27.0, 28.0), "005930": (1, 60000, 61000)}),
    "조회실패": dict(toss={"USD": None, "KRW": None}, kis={"KRW": None, "USD": None}, bithumb=None,
                    price=31.25, hold={}),
}
NOW = datetime(2026, 11, 4, 0, 0, tzinfo=timezone.utc)   # 09:00 KST
rendered = {}
for name, sc in SCEN.items():
    STATE.clear()
    STATE.update(sc)
    MERITZ["VR6"] = None if name == "조회실패" else {"estm": "987.65", "frcr": "900.00"}
    # 1) 계산·문구 불변: section_dollar_check 출력이 main 과 같아야 함
    a, b = old.section_dollar_check(NOW), new.section_dollar_check(NOW)
    check(f"[{name}] 토스 달러 계산·문구 main 과 동일", a == b, "" if a == b else f"\nmain={a}\nnew={b}")
    # 2) 💰 잔액 메뉴(메리츠 포함) 출력 불변
    for w in ("all", "meritz", "toss", "kis", "bithumb"):
        x, y = old.section_balances(which=w), new.section_balances(which=w)
        check(f"[{name}] 잔액 메뉴 --balances {w} main 과 동일", x == y, "" if x == y else f"\n{x}\n---\n{y}")
    rendered[name] = new.build(NOW)
    (OUT / f"brief_{name}.txt").write_text(rendered[name], encoding="utf-8")

# 3) 형식 규칙
NAMES = ("토스", "메리츠", "한투", "빗썸")
ICONS = ("🚨", "😌")
cut = lambda r: r[:-2].rstrip() if r.endswith(ICONS) else r
for name, text in rendered.items():
    pre = re.findall(r"<pre>(.*?)</pre>", text, re.S)
    check(f"[{name}] 고정폭 <pre> 블록 1개", len(pre) == 1)
    if not pre:
        continue
    rows = pre[0].split("\n")
    data = [r for r in rows[1:] if r not in NAMES]
    check(f"[{name}] 머리말 계좌·보유·필요 맨 위 1번", rows[0].split() == ["계좌", "보유", "필요"]
          and not any(w in r for r in rows[1:] for w in ("보유", "필요", "충분", "충전")))
    check(f"[{name}] 계좌 이름 1번씩 (토스·메리츠·한투·빗썸)", all(pre[0].count(n) == 1 for n in NAMES))
    check(f"[{name}] 묶음: 토스=USD·KRW, 메리츠=P·VR6, 한투=KRW, 빗썸=KRW",
          [r.split()[0] for r in rows[1:]] == ["토스", "USD", "KRW", "메리츠", "P", "VR6", "한투", "KRW", "빗썸", "KRW"])
    m_rows = rows[5:7]
    check(f"[{name}] 메리츠: 달러만·필요 '-'·'예수금' 없음",
          all(cut(r).endswith(" -") and (r.split()[1].startswith("$") or r.split()[1] == "-") for r in m_rows)
          and "예수금" not in text)
    han = rows[8]
    check(f"[{name}] 한투 KRW · 필요 '-' · '조회 불가' 없음", cut(han).endswith(" -") and "조회 불가" not in text.split("📝")[0])
    if name != "부족":
        check(f"[{name}] 한투 원화 실패 → 0 표시 + 노트", han.split()[1] == "0" and "한투 원화: 잔고를 못 받아 0원" in text)
    check(f"[{name}] 범례 1번", text.count("🚨 충전 필요 · 😌 충분") == 1)
    check(f"[{name}] 통합 잔액 블록 없음 · '필요 금액' 제목", "통합 잔액" not in text and "💰 <b>필요 금액</b>" in text)
    check(f"[{name}] 날조 금지: 메리츠 계산식 없음 노트", "메리츠 필요: 계산식 없음" in text)
    check(f"[{name}] 숫자 줄은 아이콘 앞까지 ASCII 만", all(cut(r).isascii() for r in data))
    # 폰 글꼴에서 한글은 1.5~2칸으로 그려진다 → 비율을 바꿔도 숫자 줄 열 끝이 같아야 한다
    for ratio in (1.5, 1.67, 1.84, 2.0):
        W = lambda t: new.disp_width(t, ratio)
        ends = {W(cut(r)) for r in data}
        haves = {W(cut(r)[: len(cut(r)) - len(cut(r).split()[-1])].rstrip()) for r in data}
        check(f"[{name}] 한글 {ratio}칸 글꼴: 숫자 줄 보유·필요 열 끝 일치", len(ends) == 1 and len(haves) == 1,
              f"{ends} {haves}")
    devs = []
    for r in (1.5, 1.67, 1.84, 2.0):
        d0 = cut(data[0])
        have_end = new.disp_width(d0[: len(d0) - len(d0.split()[-1])].rstrip(), r)
        devs.append(abs(new.disp_width(rows[0].rsplit("필요", 1)[0].rstrip(), r) - have_end))
        devs.append(abs(new.disp_width(rows[0], r) - new.disp_width(d0, r)))
    check(f"[{name}] 머리말(보유·필요) 어긋남 ≤ 2칸 (한글 1.5~2칸 글꼴, 숫자 줄은 0칸)", max(devs) <= 2, str(max(devs)))
    check(f"[{name}] 휴대폰 폭: 표 줄 ≤ 32칸", max(new.disp_width(r) for r in rows) <= 32,
          str(max(new.disp_width(r) for r in rows)))

first = lambda t: re.search(r"<pre>(.*?)</pre>", t, re.S).group(1).split("\n")[2]
check("[부족] 토스 USD 🚨", first(rendered["부족"]).endswith("🚨"))
check("[충분] 토스 USD 😌", first(rendered["충분"]).endswith("😌"))
check("[조회실패] 토스 USD 보유 '-'·아이콘 없음", not first(rendered["조회실패"]).endswith(ICONS)
      and first(rendered["조회실패"]).split()[1] == "-" and "토스 달러 보유 조회 실패" in rendered["조회실패"])

# 4) 실제 글꼴로 그려서 픽셀 정렬 확인 (Noto Sans Mono CJK KR · DejaVu Sans Mono) + PNG 저장
try:
    from PIL import Image, ImageDraw, ImageFont
    import html as _h
    fonts = []
    for path in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"):
        if Path(path).exists():
            for idx in range(12):
                try:
                    f = ImageFont.truetype(path, 28, index=idx)
                except OSError:
                    break
                if f.getname()[0] == "Noto Sans Mono CJK KR":
                    fonts.append(f)
                    break
        if fonts:
            break
    dj = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    if Path(dj).exists():
        fonts.append(ImageFont.truetype(dj, 28))
    rows = [_h.unescape(r) for r in re.search(r"<pre>(.*?)</pre>", rendered["부족"], re.S).group(1).split("\n")]
    data = [r for r in rows[1:] if r not in NAMES]
    for f in fonts:
        ends = {round(f.getlength(cut(r)), 2) for r in data}
        haves = {round(f.getlength(cut(r)[: len(cut(r)) - len(cut(r).split()[-1])].rstrip()), 2) for r in data}
        check(f"픽셀 정렬({f.getname()[0]}): 숫자 줄 보유·필요 열 끝", len(ends) == 1 and len(haves) == 1, f"{ends} {haves}")
    f = fonts[0]
    img = Image.new("RGB", (int(max(f.getlength(cut(r)) for r in rows)) + 40, 40 * len(rows) + 20), "white")
    d = ImageDraw.Draw(img)
    for i, r in enumerate(rows):
        d.text((20, 10 + 40 * i), cut(r), font=f, fill="black")
    img.save(OUT / "table_render.png")
except Exception as e:
    check("픽셀 정렬 렌더링", False, f"{type(e).__name__}: {e}")

# 5) 메시지 분할 3500자 · <pre> 가 나뉘지 않음
big = rendered["부족"] + "\n" + "\n".join("· 긴 노트 " + "가" * 60 for _ in range(80))
chunks = new.message_chunks("\n".join("앞줄 " + "나" * 70 for _ in range(45)) + "\n" + big)
L16 = lambda s: len(s.encode("utf-16-le")) // 2
check("분할: 모든 조각 ≤ 3500 (UTF-16)", all(L16(c) <= 3500 for c in chunks), str([L16(c) for c in chunks]))
check("분할: 조각마다 <pre> 열고 닫음 짝 맞음", all(c.count("<pre>") == c.count("</pre>") for c in chunks))
check("분할: 표 전체가 한 조각에", sum(1 for c in chunks if "<pre>계좌" in c and "빗썸" in c) == 1)
huge = "<pre>" + "\n".join(f"줄{i:03d} " + "x" * 80 for i in range(120)) + "</pre>"
hc = new.message_chunks(huge)
check("분할: 3500 넘는 <pre> 는 줄 단위로 나눠 각각 <pre>", len(hc) > 1 and all(
    c.startswith("<pre>") and c.endswith("</pre>") and L16(c) <= 3500 for c in hc))

# 6) 정기 실행: 평일 휴장일만 표시, 진행 중/예정 문구 없음, 양 시장 휴장 생략, 조회 실패 → 노트
sent = []
new.send = lambda text: sent.append(text) or True
new.commit_seen = lambda: None
STATE.clear(); STATE.update(SCEN["충분"]); MERITZ["VR6"] = {"estm": "987.65", "frcr": "900.00"}
sys.modules["price_watch"] = types.SimpleNamespace(launch=lambda: None)
KST = ZoneInfo("Asia/Seoul")
cases = [("평일 개장", datetime(2026, 11, 4, 9, 0, tzinfo=KST), True),
         ("미국 휴장(추수감사절)", datetime(2026, 11, 26, 9, 0, tzinfo=KST), True),
         ("한국 휴장", datetime(2026, 11, 5, 16, 30, tzinfo=KST), False),
         ("한국 조회 실패", datetime(2026, 11, 6, 9, 0, tzinfo=KST), None),
         ("양 시장 휴장", datetime(2026, 12, 25, 9, 0, tzinfo=KST), False)]
for label, when, kr in cases:
    sent.clear()
    new.korean_session = lambda day, kr=kr: kr
    for f in (ROOT / "var/lib/bot-office/briefing-calendar").glob("state.json"):
        f.unlink()
    new.scheduled_run(when)
    joined = "\n".join(sent)
    check(f"[일정·{label}] 진행 중/예정/일정 안내 문구 없음",
          not any(w in joined for w in ("진행 중", "시작 예정", "정규장 예정", "정규장 일정 안내")))
    if label == "평일 개장":
        check(f"[일정·{label}] 일정 줄 없음 · 브리핑 1통", len(sent) == 1 and "휴장" not in sent[0])
    if label == "미국 휴장(추수감사절)":
        check(f"[일정·{label}] 미국장 휴장 표시", "🇺🇸 미국장 휴장" in sent[-1] and "한국장" not in sent[-1])
    if label == "한국 휴장":
        check(f"[일정·{label}] 한국장 휴장 표시", "🇰🇷 한국장 휴장" in sent[-1])
    if label == "한국 조회 실패":
        check(f"[일정·{label}] 휴장 단정 없음 · 전달 노트", "휴장 · " not in sent[-1]
              and "한국장 일정 조회 실패" in sent[-1] and "📝" in sent[-1])
    if label == "양 시장 휴장":
        check(f"[일정·{label}] 휴장 알림만, 일반 브리핑 생략", len(sent) == 1 and "필요 금액" not in sent[0])
    (OUT / f"scheduled_{label}.txt").write_text("\n=====\n".join(sent), encoding="utf-8")

# 7) 비밀·네트워크
all_out = "\n".join(rendered.values()) + "\n".join(sent)
check("가짜 비밀값이 출력에 0건", FAKE_SECRET not in all_out and "FAKEKEY" not in all_out)
check("네트워크 호출 0건(모두 가짜로 대체)", not net_calls, str(sorted(set(net_calls))))

ok = all(r[1] for r in results)
with open(OUT / "verify_result.txt", "w", encoding="utf-8") as f:
    for n, good, det in results:
        f.write(f"{'PASS' if good else 'FAIL'}  {n}{(' · ' + det) if det and not good else ''}\n")
    f.write(f"\n합계: {sum(r[1] for r in results)}/{len(results)} 통과\n")
print(open(OUT / "verify_result.txt", encoding="utf-8").read())
sys.exit(0 if ok else 1)
