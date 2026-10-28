#!/usr/bin/env python3
# BOT_UPDATER_V2 — GitHub에 올라온 수정(main 이외의 브랜치)을 감지 → 텔레그램 [✅ 업데이트] 버튼 → 안전 확인 후 적용
#  · Gemini/Jules/딥시크 등 누가 올려도 main 이 아닌 브랜치면 감지 (main 은 서버가 적용한 결과만 올라가는 곳)
#  · 1~4번 봇 + 5번 사무실 비서(저장소 bot_office/ → 서버 /opt/bot-office) · 업데이트 비서 자신도 업데이트(실패 시 2분 뒤 자동 복구)
#  · 적용: 보유·매매시간 확인 → 병합 → 문법 검사 → 해당 봇만 재시작 → 실패 시 원래 코드로 자동 복구 → 버전 기록 → main 업로드
#  · 사무실 v1.0.43 (2026-10-28): 사무실에 새로 추가되는 파일은 server.py 와 같은 주인·그룹·권한으로 복사 (있던 파일은 원래 권한 유지)
#  · 사무실 v1.0.44 (2026-10-28): 되돌림 감지 — 올라온 파일이 최근 14일 안의 다른 수정을 지우거나 버전이 더 낮으면 알림에 경고
#  · 사무실 v1.0.46 (2026-10-28): 저장소 맨 위 STATUS.md 자동 작성 — 업데이트 적용 때마다 + 하루 1번(06:10 KST, 대기 중인 업로드 없을 때)
#                       봇별 버전·서비스 상태·최근 적용·대기 업데이트. 사람·AI 는 읽기만 (손으로 고치지 않음)
#                       · 버전 표기 통일: 이 파일의 변경 기록도 텔레그램·CHANGELOG 와 같은 '사무실 vX.Y.Z' 번호를 씀
#  · 사무실 v1.0.47 (2026-10-28): 버전 자동 기입 — 올린 파일에 'v'+'NEXT'(붙여 쓴 글자)를 적어 두면 승인 때 정해진 실제 번호(예: v1.0.48)로 바꿔 기록
#                       (승인 순서에 따라 번호가 밀려도 파일 머리말·CHANGELOG·텔레그램 번호가 항상 같음)
#  · 사무실 v1.0.48 (2026-10-28): office_url.py(사무실 주소 관리)가 바뀌면 7번 비서도 재시작
#  · 사무실 v1.0.49 (2026-10-28): ① 2번 원작자 새 버전 알림 다시 켬 (sniper_upstream.py · 알림 전용, 자동 합치기 없음)
#                       ② 버전 자동 기입 고침 — v1.0.48 적용 때 이 파일 속 표시 글자까지 바뀌어 기능이 꺼져 있었음
#                          (표시 글자를 코드에 직접 쓰지 않고 조립해서 다시는 안 바뀌게)
#                       ③ sniper_upstream.py 가 바뀌면 업데이트 비서만 재시작 (사무실 서비스는 재시작 안 함)
#  · 사무실 v1.0.54 (2026-10-28): ① 한글 파일명 문서가 '허용되지 않은 파일'로 거부되던 것 고침 (git 경로 따옴표·8진수 표기 끔)
#                       ② GitHub main 에 서버를 거치지 않은 수정이 있으면 알림 1번 + 그 수정이 빠진 브랜치는 적용 전에 멈춤
#                       ③ 충돌 정리 '서버 HEAD≠main' 안내를 main 앞섬/서버 앞섬/갈라짐으로 나눠 할 일까지 표시 (update_conflicts.py)
#  · 사무실 vNEXT (2026-10-28): ① 사무실 파일 읽기 권한 자동 정리 — 이미 있던 파일도 웹서버(server.py 와 같은 그룹)가 읽을 수 있게
#                          (pixel_office.html 이 관리자 전용 권한으로 남아 로그인 뒤 첫 화면이 끊김 · pc_monitor.py 502 와 같은 원인)
#                          주인은 바꾸지 않고, 그룹 쓰기 권한은 주지 않음 · 적용 때마다 /opt/bot-office 전체를 한 번 훑어 고침
#                       ② STATUS.md 를 쓸 때 사무실 상황판용 복사본 /var/lib/bot-office/status.md (읽기 전용 0644) 도 남김
#  · 2번 스나이퍼: 원작자 새 버전 하루 1번(09:02 KST) 확인 → 🔴 중요 알림 (sniper_upstream.py · 알림 전용) · 6. Update 에 '원작 확인'
import json, os, pwd, re, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
 
REPO = os.environ.get("U_REPO", "/home/gieokkim")
TG_CFG = os.environ.get("U_TG", "/etc/bot-office/telegram.json")
TARGETS = os.environ.get("U_TARGETS", "/var/lib/bot-office-deploy/targets.json")
STATE = os.environ.get("U_STATE", "/var/lib/bot-updater/state.json")
OFFICE_DIR = os.environ.get("U_OFFICE", "/opt/bot-office")
OFFICE_UNIT, SELF_UNIT, SELF_FILE = "bot-office.service", "bot-updater.service", "bot_updater.py"
# 사무실 폴더(/opt/bot-office)에서 따로 도는 상시 서비스 — 그 파일이 바뀌면 이 서비스도 다시 시작해야 새 코드가 반영됨
SECRETARY_UNIT, FANDING_UNIT = "bot-office-secretary.service", "bot-office-fanding.service"
OFFICE_EXTRA = {SECRETARY_UNIT: ("office_secretary.py", "office_briefing.py", "price_watch.py", "gemini_usage.py", "meritz_client.py", "fanding_trade.py", "toss_token_share.py", "pc_monitor.py", "office_url.py"),
                FANDING_UNIT: ("fanding_trade.py", "fanding_vr6.py", "meritz_client.py", "gemini_usage.py")}
OFFICE_EXT = (".py", ".html", ".css", ".js")
SYSTEMCTL = os.environ.get("U_SYSTEMCTL", "systemctl")
TG_API = os.environ.get("U_TG_API", "https://api.telegram.org")
CHECK_EVERY = int(os.environ.get("U_EVERY", "300"))
KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
NAMES = {"han4384tubot.service": "1번 한투 라오어", "toss_sniper.service": "2번 토스 스나이퍼",
         "toss_dca.service": "3번 토스 적립", "bithumb_bot.service": "4번 빗썸 적립", OFFICE_UNIT: "5번 사무실 비서"}
SECRET_RE = re.compile(r"(\d{8,10}:[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,})")
OWNER = pwd.getpwuid(os.stat(REPO).st_uid)
try:   # 2번 스나이퍼 원작자 새 버전 알림 부품 (알림 전용 · 없어도 비서는 정상 작동)
    import sniper_upstream as SU
except Exception as _e:   # 파일이 없거나 오류면 알림만 끔
    print("원작 알림 부품 없음:", type(_e).__name__, _e, flush=True)
    SU = None

import deployment_control as DC
try:
    import update_conflicts as UC
except ImportError:
    UC = None

 
 
def sh(*a, timeout=120):
    try:
        r = subprocess.run(list(a), capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"
 
 
def git(*a, timeout=120):
    cmd = ["env", f"HOME={OWNER.pw_dir}", "GIT_TERMINAL_PROMPT=0", "git", "-c", "core.quotepath=false", "-C", REPO, *a]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    return sh(*cmd, timeout=timeout)
 
 
def git_raw(*a):
    cmd = ["env", f"HOME={OWNER.pw_dir}", "git", "-c", "core.quotepath=false", "-C", REPO, *a]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout
 
 
def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d
 
 
def save(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
 
 
CFG = load(TG_CFG, {})
 
 
def tg(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(f"{TG_API}/bot{CFG.get('token')}/{method}", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except Exception as e:
        print("텔레그램 오류:", type(e).__name__, flush=True)
        return {}
 
 
def say(text, rows=None, keyboard=None):
    p = {"chat_id": CFG.get("chat_id"), "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
    if rows:
        p["reply_markup"] = {"inline_keyboard": rows}
    elif keyboard:   # 채팅창 아래에 계속 떠 있는 버튼
        p["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": True}
    return tg("sendMessage", **p)
 
 
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
 
 
# ---------------------------------------------------------------- 어떤 봇이 바뀌는지
def targets():
    t = load(TARGETS, {}).get("targets", {})
    out = {u: os.path.realpath(v["root"]) for u, v in t.items() if isinstance(v, dict) and v.get("root")}
    out[OFFICE_UNIT] = os.path.realpath(os.path.join(REPO, "bot_office"))   # 5번 비서: 저장소 bot_office/ ↔ 서버 /opt/bot-office
    return out
 
 
def classify(files):
    """바뀐 파일 → (봇별 파일, 거부 사유)"""
    roots, units, bad = targets(), {}, []
    for f in files:
        absf = os.path.realpath(os.path.join(REPO, f)); d = os.path.dirname(absf); name = os.path.basename(f)
        unit = next((u for u, r in roots.items() if r == d), None)
        if name.endswith(".md"):
            if unit: units.setdefault(unit, [])
            continue
        if unit == OFFICE_UNIT and name.endswith(OFFICE_EXT):
            units.setdefault(unit, []).append(f)
        elif unit and unit != OFFICE_UNIT and name.endswith(".py") and not name.startswith(("bot_office_", "test_")):
            units.setdefault(unit, []).append(f)
        else:
            bad.append(f)
    return units, bad
 
 
# ---------------------------------------------------------------- 매매 중인지 확인
def busy_reason(unit, pause_verified=False):
    if pause_verified:
        return ""
    now_k, now_e = datetime.now(KST), datetime.now(ET)
    k, e = now_k.hour * 100 + now_k.minute, now_e.hour * 100 + now_e.minute
    if unit == "toss_sniper.service":
        # 현 장부(인피니트 스노우볼 soxl_stratum_ledger*.json, {"SOXL": {...}}): 매수·매도 주문이 걸려 있으면 보류.
        # (스노우볼은 원래 보유를 다음 날로 넘기는 전략이라 '보유 중'만으로는 막지 않음 · 재시작하면 장부·잔고로 이어서 관리)
        import glob
        root = targets().get(unit, "")
        for p in glob.glob(os.path.join(root, "soxl_stratum_ledger*.json")):
            d = load(p, {})
            L = d.get("SOXL", d) if isinstance(d, dict) else {}
            if isinstance(L, dict) and (str(L.get("buy_order_id") or "").strip() or str(L.get("sell_order_id") or "").strip()):
                return "스나이퍼(SOXL) 주문이 걸려 있음 (체결·취소 뒤 다시 눌러 주세요)"
    if unit == "toss_dca.service":
        # 각 시장의 현지 요일을 사용: 한국 토요일 새벽의 미국 금요일 장은 보호.
        kr_busy = now_k.weekday() < 5 and 1050 <= k <= 1510
        us_busy = now_e.weekday() < 5 and 1120 <= e <= 1600
        # 3번 설정에 켜진 한국/미국 종목이 없으면 그 시장 보호 시간은 건너뜀 (설정을 못 읽으면 예전처럼 보호)
        cfg = load(os.path.join(targets().get(unit, ""), "dca_config.json"), None)
        if isinstance(cfg, dict) and isinstance(cfg.get("stocks"), dict):
            on = [v for v in cfg["stocks"].values() if isinstance(v, dict) and v.get("enabled", True)] if cfg.get("is_master_active", True) else []
            kr_busy = kr_busy and any(v.get("currency") == "KRW" for v in on)
            us_busy = us_busy and any(v.get("currency") != "KRW" for v in on)
        if kr_busy or us_busy:
            markets = []
            if kr_busy:
                markets.append("한국장 평일 10:50~15:10 KST")
            if us_busy:
                markets.append("미국장 평일 11:20~16:00 뉴욕시간")
            return "3번 봇 매매 보호 시간 (" + " · ".join(markets) + ")"
    if unit == "bithumb_bot.service" and 1850 <= k <= 1925:
        return "4번 봇 19:00 정기 매수 시간"
    if unit == "han4384tubot.service" and 925 <= e <= 1605 and now_e.weekday() < 5:
        return "1번 봇 미국 정규장 시간"
    if unit == FANDING_UNIT and now_e.weekday() < 5 and 750 <= e <= 835:
        return "5번 팬딩 예약주문 마감 전후 (08:30 ET 전후)"
    return ""
 
 
def gate_installed(unit):
    """업데이트용 신규 주문 차단 부품(deployment_gate.py)이 그 봇 폴더에 있는지"""
    return os.path.isfile(os.path.join(targets().get(unit, ""), "deployment_gate.py"))


# ---------------------------------------------------------------- 새 업데이트 찾기
def scan(st, force=False):
    rc, out = git("fetch", "-q", "--prune", "origin")
    if rc:
        if st.get("fetch_err") != out[:80]:
            st["fetch_err"] = out[:80]; say("⚠️ <b>[업데이트 비서] GitHub 확인 실패</b>\n▫️ " + esc(out[-200:]))
        return
    st["fetch_err"] = ""
    main_ahead_notice(st)
    rc, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    live = {}   # 지금 GitHub에 실제로 있고 아직 반영 안 된 브랜치 → 최신 SHA
    for line in refs.splitlines():
        ref, sha = line.split()
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if br in ("main", "HEAD") or ref == "origin":
            continue
        if git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue   # 이미 반영된 브랜치
        live[br] = sha
        seen = st.setdefault("seen", {})
        if seen.get(br) == sha and not force:
            continue
        seen[br] = sha
        offer(st, br, sha)
    prune(st, live)


def main_ahead_notice(st):
    """GitHub main 에 서버를 거치지 않은 수정(웹에서 main 에 바로 올림 등)이 있으면 같은 main 마다 1번만 알림.
    그대로 두면 서버 HEAD≠main 이라 충돌 정리·STATUS 기록이 멈추고, 다음 승인 때 main 업로드가 실패한다."""
    rc_m, main = git("rev-parse", "origin/main")
    if rc_m or not main or git("merge-base", "--is-ancestor", main, "HEAD")[0] == 0:
        st.pop("main_ahead", None)
        return
    if st.get("main_ahead") == main:
        return
    st["main_ahead"] = main
    _, subj = git("log", "--format=%s", "HEAD..origin/main", "-n", "3")
    _, fs = git("diff", "--name-only", "HEAD...origin/main")
    fs = [f for f in fs.splitlines() if f.strip()]
    say("⚠️ <b>[업데이트 비서] GitHub main 에 서버를 거치지 않은 수정이 있습니다</b>\n"
        "▫️ 수정: " + esc(" / ".join(subj.splitlines()) or "-") + "\n"
        "▫️ 파일: " + esc(", ".join(fs[:6]) + (" 외" if len(fs) > 6 else "")) + "\n"
        "▫️ 이대로면 충돌 정리·STATUS 기록이 멈춥니다.\n"
        "→ GitHub 에서 <b>main 기준 새 브랜치</b>를 만들면 업데이트 알림이 뜹니다. 그 알림을 ✅ 승인하면 서버와 main 이 다시 같아집니다.")


def prune(st, live):
    """지난 알림 정리: 브랜치가 지워졌거나 새 커밋으로 바뀐(또는 이미 반영된) 알림·정리화면을 지운다.
    예전 알림 버튼을 누르면 '최신 업데이트 알림에서 다시 눌러 주세요'로 안내된다. 지운 개수 반환."""
    offers = st.setdefault("offers", {})
    removed = 0
    for k, o in list(offers.items()):
        if live.get(o.get("branch")) != o.get("sha"):
            offers.pop(k, None); removed += 1
    # 같은 브랜치·같은 SHA 알림이 여러 개면 가장 최근 것 하나만 남김
    keep = {}
    for k, o in sorted(offers.items(), key=lambda kv: kv[1].get("at", 0)):
        if o["branch"] in keep:
            offers.pop(keep[o["branch"]], None); removed += 1
        keep[o["branch"]] = k
    for br in list(st.get("seen", {})):
        if br not in live:
            st["seen"].pop(br, None)
    plans = st.get("conflict_plans", {})
    for t, pl in list(plans.items()):
        if pl.get("offer_key") not in offers:
            plans.pop(t, None)
    return removed


def live_branches():
    """GitHub에 지금 있고 아직 main에 반영 안 된 브랜치 → 최신 SHA. 확인 실패 시 None."""
    rc, out = git("fetch", "-q", "--prune", "origin")
    if rc:
        return None
    _, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    live = {}
    for line in refs.splitlines():
        ref, sha = line.split()
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if br in ("main", "HEAD") or ref == "origin":
            continue
        if git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue
        live[br] = sha
    return live
 
 
REVERT_DAYS, REVERT_SKIP = 14, ("CHANGELOG.md",)
_VER_RES = (re.compile(r"""^\s*(?:BOT_|UPDATER_)?VERSION\s*=\s*["']v?(\d+(?:\.\d+)+)""", re.M),
            re.compile(r"_V(\d+(?:\.\d+)+)\)"))


def _ver(text):
    for rx in _VER_RES:
        m = rx.search(text or "")
        if m:
            return tuple(int(x) for x in m.group(1).split("."))
    return None


def revert_check(sha, files):
    """되돌림 감지: 이 업로드가 최근 main 수정을 지우는지 · 버전이 더 낮은지. 경고 문장 목록 (확인 실패는 조용히 넘어감)
    · 업로드 브랜치가 이미 가진 최근 커밋(C)이 추가한 줄이 지금 main 에는 있는데 업로드 파일에는 없으면 → 지워지는 것
      (브랜치가 C 를 모르면 병합이 C 를 지켜 주거나 충돌로 멈추므로 검사 안 함)"""
    out = []
    for f in files[:25]:
        if os.path.basename(f) in REVERT_SKIP or not f.endswith((".py", ".md", ".html", ".js", ".css", ".json", ".sh")):
            continue
        rc_h, head_txt = git("show", f"HEAD:{f}")
        if rc_h:
            continue                                   # main 에 없던 새 파일
        rc_n, new_txt = git("show", f"{sha}:{f}")
        if rc_n:
            out.append(f"🗑 <code>{esc(f)}</code> 파일을 지웁니다"); continue
        hv, nv = _ver(head_txt), _ver(new_txt)
        if hv and nv and nv < hv:
            out.append(f"🔻 <code>{esc(f)}</code> 버전이 더 낮아요: 지금 {'.'.join(map(str, hv))} → 올린 것 {'.'.join(map(str, nv))}")
        new_lines = {l.strip() for l in new_txt.splitlines()}
        head_lines = {l.strip() for l in head_txt.splitlines()}
        _, log = git("log", f"--since={REVERT_DAYS}.days", "--no-merges", "-n", "12", "--format=%H\t%ad\t%s",
                     "--date=format:%m/%d %H:%M", "HEAD", "--", f)
        for row in log.splitlines():
            parts = row.split("\t", 2)
            if len(parts) < 3 or parts[2].startswith("버전 기록"):
                continue
            c, when, subj = parts
            if git("merge-base", "--is-ancestor", c, sha)[0] != 0:
                continue
            _, patch = git("show", "--format=", "-U0", c, "--", f)
            added = {l[1:].strip() for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")}
            added = {l for l in added if len(l) >= 8 and l in head_lines}     # 지금도 main 에 살아 있는 의미 있는 줄
            lost = [l for l in added if l not in new_lines]
            if added and len(lost) >= max(2, len(added) * 0.3):
                out.append(f"⚠️ <code>{esc(f)}</code>: {esc(when)} 수정 '<b>{esc(subj[:40])}</b>'의 {len(lost)}/{len(added)}줄이 사라져요"
                           f"\n    예) <code>{esc(sorted(lost, key=len, reverse=True)[0][:70])}</code>")
    return out


def offer(st, br, sha):
    _, files = git("diff", "--name-only", f"HEAD...{sha}")
    files = [f for f in files.splitlines() if f.strip()]
    units, bad = classify(files)
    _, log = git("log", "--format=%an · %s", f"HEAD..{sha}", "-n", "5")
    key = sha[:12]
    st.setdefault("offers", {})[key] = {"branch": br, "sha": sha, "at": time.time()}
    bots = ", ".join(NAMES.get(u, u) for u, fs in units.items() if fs) or "봇 코드 없음(문서만)"
    warn = ("\n⛔ <b>허용되지 않은 파일</b>: " + esc(", ".join(bad[:5])) + " → 이 업데이트는 적용할 수 없습니다") if bad else ""
    try:
        reverts = revert_check(sha, files)
    except Exception as e:
        print("되돌림 감지 실패:", type(e).__name__, e, flush=True); reverts = []
    if reverts:
        warn += ("\n\n🚨 <b>덮어쓰기 의심</b> (예전 파일을 기준으로 고친 것 같아요)\n" + "\n".join(reverts[:6])
                 + ("\n…외 " + str(len(reverts) - 6) + "건" if len(reverts) > 6 else "")
                 + "\n→ 최신 main 파일을 받아 다시 고쳐 올리는 걸 추천해요. 알고 올린 거면 그대로 승인해도 돼요.")
        st["offers"][key]["reverts"] = len(reverts)
    rows = [[{"text": "🔍 바뀐 내용 보기", "callback_data": f"df:{key}"}, {"text": "❌ 무시", "callback_data": f"ig:{key}"}]]
    if UC:
        rows.append([{"text": "🧹 이전 변경·충돌 정리", "callback_data": "cp:" + key}])
    if not bad:
        rows.insert(0, [{"text": "⚠️ 알고 있음 · 그래도 업데이트" if reverts else "✅ 업데이트", "callback_data": f"up:{key}"}])
    gated = {u for u in DC.UNITS.values() if units.get(u) and gate_installed(u)}   # 차단 부품이 설치된 봇만 일시중지 버튼
    if not bad and gated:
        rows.append([{'text':'⏸ 이번 업데이트 대상 전체 중지 대기','callback_data':'pa:'+key},
                     {'text':'▶️ 이번 대상 거래 재개','callback_data':'ra:'+key}])
    for number, unit in DC.UNITS.items():
        if unit in gated:
            rows.append([{ "text": "⏸ " + NAMES[unit] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + number}])
    say(f"📦 <b>[업데이트 비서] 새 수정이 올라왔어요</b>\n▫️ 대상: {esc(bots)}\n▫️ 브랜치: <code>{esc(br)}</code>\n"
        f"▫️ 파일: {esc(', '.join(files[:8]))}{' 외' if len(files) > 8 else ''}\n▫️ 내용:\n{esc(log[:600])}{warn}\n\n"
        "✅를 누르면 매매 중인지 확인 → 적용 → 재시작 확인(실패 시 자동 복구) → 버전 기록 → GitHub main 업로드까지 진행합니다.", rows)
 
 
# ---------------------------------------------------------------- STATUS.md (자동 현재 상태)
STATUS_FILE = "STATUS.md"
EXTRA_UNITS = {SECRETARY_UNIT: "7번 비서(브리핑·PC감시)", FANDING_UNIT: "5번 팬딩 가격표", "bot-office-tunnel.service": "사무실 터널",
               SELF_UNIT: "6번 업데이트 비서"}
_CL_RE = re.compile(r"^## (\S+) · ([\d-]+ [\d:]+) \(KST\)\n((?:- .*\n?)*)", re.M)


def _changelog(root, n=3):
    """봇 폴더 CHANGELOG.md 의 최근 n건 → [(버전, 시각, 파일, 내용)]"""
    try:
        text = open(os.path.join(root, "CHANGELOG.md"), encoding="utf-8").read()
    except OSError:
        return []
    out = []
    for m in _CL_RE.finditer(text):
        info = dict(re.findall(r"^- ([^:]+): (.*)$", m.group(3), re.M))
        out.append((m.group(1), m.group(2), info.get("파일", ""), info.get("내용", "")))
        if len(out) >= n:
            break
    return out


def _svc(unit):
    _, out = sh(SYSTEMCTL, "show", unit, "-p", "ActiveState", "-p", "ActiveEnterTimestamp", "--value")
    lines = (out.splitlines() + ["", ""])[:2]
    state, since = lines[0].strip(), lines[1].strip()
    m = re.search(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) (\w+)", since)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc) if m.group(2) == "UTC" else dt.replace(tzinfo=KST if m.group(2) == "KST" else None)
            since = dt.astimezone(KST).strftime("%m-%d %H:%M") if dt.tzinfo else dt.strftime("%m-%d %H:%M")
        except ValueError:
            since = m.group(1)[5:16]
    mark = "🟢 실행 중" if state == "active" else ("⚪ 꺼짐" if state == "inactive" else f"🔴 {state or '확인 불가'}")
    return mark, since


def _cell(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def build_status(reason):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    roots = targets()
    L = ["# STATUS — 서버가 자동으로 쓰는 현재 상태", "",
         "> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).",
         "> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.", "",
         f"- 갱신: {now} (KST) · 계기: {_cell(reason)}", ""]
    L += ["## 봇별 현재 상태", "", "| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |", "|---|---|---|---|---|---|"]
    recent = []
    for u, name in NAMES.items():
        mark, since = _svc(u)
        cl = _changelog(roots.get(u, ""), 10) if roots.get(u) else []
        ver, when, _, what = cl[0] if cl else ("-", "-", "", "-")
        L.append(f"| {name} | `{u.replace('.service', '')}` | {mark}{' (' + since + ' KST부터)' if since and mark.startswith('🟢') else ''} | {ver} | {when} | {_cell(what)[:60]} |")
        recent += [(w, name, v, f, t) for v, w, f, t in cl]
    L += ["", "## 사무실 상시 서비스", ""]
    for u, name in EXTRA_UNITS.items():
        mark, since = _svc(u)
        L.append(f"- {name} `{u.replace('.service', '')}`: {mark}{' (' + since + ' KST부터)' if since and mark.startswith('🟢') else ''}")
    _, failed = sh(SYSTEMCTL, "list-units", "--failed", "--plain", "--no-legend", "--no-pager")
    failed = [ln.split()[0] for ln in failed.splitlines() if ln.split()]
    L.append(f"- 실패 상태로 남은 서비스·타이머: {', '.join('`' + f + '`' for f in failed) if failed else '없음'}")
    try:
        du = shutil.disk_usage(REPO)
        L.append(f"- 디스크 사용: {du.used / du.total * 100:.0f}% (남은 {du.free / 1e9:.1f}GB)")
    except OSError:
        pass
    L += ["", "## 최근 적용 10건", ""]
    for w, name, v, f, t in sorted(recent, reverse=True)[:10]:
        L.append(f"- {w} · {name} {v} · {_cell(f)[:60]} · {_cell(t)[:60]}")
    L += ["", "## 대기 중인 업로드 (아직 승인 안 됨)", ""]
    _, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    pend = []
    for line in refs.splitlines():
        ref, sha = (line.split() + [""])[:2]
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if not sha or br in ("main", "HEAD") or ref == "origin" or git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue
        _, fs = git("diff", "--name-only", f"HEAD...{sha}")
        fs = [x for x in fs.splitlines() if x.strip()]
        pend.append(f"- `{br}`: {', '.join(fs[:6])}{' 외' if len(fs) > 6 else ''}")
    L += pend or ["- 없음"]
    L += ["", "## AI·사람 작업 순서 (요약)", "",
          "1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).",
          "2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).",
          "3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.",
          "4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).", ""]
    return "\n".join(L)


STATUS_COPY = os.environ.get("U_STATUS_COPY", "/var/lib/bot-office/status.md")


def _status_copy(text):
    """사무실 상황판(웹서버 bot-office 계정)이 읽는 STATUS.md 복사본 · 모두 읽기 0644 (비밀값 없음 — STATUS.md 와 같은 내용)"""
    try:
        os.makedirs(os.path.dirname(STATUS_COPY), exist_ok=True)
        tmp = STATUS_COPY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, STATUS_COPY)
    except OSError as e:
        print("상황판용 STATUS 복사 실패:", type(e).__name__, flush=True)


def write_status(reason):
    """STATUS.md 를 쓰고, '갱신' 줄 말고 실제 내용이 바뀌었으면 True"""
    path = os.path.join(REPO, STATUS_FILE)
    new = build_status(reason)
    _status_copy(new)
    strip = lambda t: re.sub(r"^- 갱신: .*$", "", t, flags=re.M)
    try:
        old = open(path, encoding="utf-8").read()
    except OSError:
        old = ""
    if strip(old) == strip(new):
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    try:
        os.chown(path, OWNER.pw_uid, OWNER.pw_gid)
    except OSError:
        pass
    return True


def status_daily(st, force=False):
    """하루 1번(06:10 KST 이후) STATUS.md 갱신 → main·staging 업로드. 대기 중인 업로드가 있으면 다음 날로 (staging 을 건드리지 않음)"""
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    if not force and (now.hour * 100 + now.minute < 610 or st.get("status_day") == today):
        return None
    st["status_day"] = today
    if git("status", "--porcelain", "--untracked-files=no")[1].strip():
        return "서버에 저장 안 된 변경이 있어 건너뜀"
    _, head = git("rev-parse", "HEAD")
    rc_m, main = git("rev-parse", "origin/main")
    rc_s, stg = git("rev-parse", "origin/staging")
    if rc_m or main != head:
        return "서버와 GitHub main 이 달라 건너뜀"
    if rc_s == 0 and stg != head:
        return "staging 에 대기 중인 업로드가 있어 건너뜀"
    if not write_status("매일 점검" if not force else "수동 기록"):
        return "바뀐 내용 없음"
    git("add", "-f", "--", STATUS_FILE)
    git("commit", "-qm", "상태 기록: STATUS.md")
    rc, out = git("push", "-q", "origin", "HEAD:main", "HEAD:staging")
    if rc:
        return "GitHub 업로드 실패: " + out[-120:]
    return "STATUS.md 갱신·업로드 완료"


# ---------------------------------------------------------------- 적용
def _office_perm(existing):
    """복사할 파일의 주인·그룹·권한. 주인은 그대로, 그룹·읽기 권한은 server.py 와 같게 (웹서버 bot-office 계정이 읽을 수 있게)
    (예전엔 새 파일을 root 전용 640 으로 만들어 pc_monitor.py 502, 있던 파일은 권한을 그대로 둬서 pixel_office.html 첫 화면 끊김)"""
    try:
        ref = os.stat(os.path.join(OFFICE_DIR, "server.py"))
    except OSError:
        ref = None
    try:
        st = os.stat(existing) if existing else None
    except OSError:
        st = None
    if not ref and not st:
        return 0, 0, 0o644
    base = st or ref
    uid, gid, mode = base.st_uid, base.st_gid, base.st_mode & 0o777
    if not st:
        mode &= ~0o111                        # 새 파일엔 실행 권한은 빼고
    if ref:
        if gid != ref.st_gid:                 # 그룹을 웹서버 그룹으로 바꿀 땐 그룹 쓰기 권한은 주지 않음
            gid = ref.st_gid
            mode &= ~0o020
        mode |= ref.st_mode & 0o044           # server.py 가 그룹·모두에게 읽기를 열어 둔 만큼 똑같이
    return uid, gid, mode | 0o400             # 주인은 항상 읽을 수 있게


def office_perm_repair():
    """/opt/bot-office 의 .py·.html·.css·.js 중 server.py 기준 읽기 권한이 빠진 파일만 고침 → 고친 파일 이름 목록"""
    fixed = []
    try:
        names = sorted(os.listdir(OFFICE_DIR))
    except OSError:
        return fixed
    for name in names:
        p = os.path.join(OFFICE_DIR, name)
        if not name.endswith(OFFICE_EXT) or not os.path.isfile(p) or os.path.islink(p):
            continue
        try:
            st = os.stat(p)
            uid, gid, mode = _office_perm(p)
            if (st.st_gid, st.st_mode & 0o777) != (gid, mode):
                os.chown(p, uid, gid); os.chmod(p, mode); fixed.append(name)
        except OSError as e:
            print("사무실 파일 권한 정리 실패:", name, type(e).__name__, flush=True)
    if fixed:
        print("사무실 파일 읽기 권한 고침:", ", ".join(fixed), flush=True)
    return fixed


def office_deploy(files):
    """저장소 bot_office/ 의 바뀐 파일을 서버 /opt/bot-office 로 복사 (덮어쓰기 전 파일은 백업) → 백업 목록 반환"""
    bk_dir = os.path.join(OFFICE_DIR, "_backups", "updater_" + datetime.now(KST).strftime("%Y%m%d_%H%M%S"))
    os.makedirs(bk_dir, exist_ok=True)
    saved = []
    for f in files:
        name = os.path.basename(f); src = os.path.join(REPO, f); dst = os.path.join(OFFICE_DIR, name)
        existed = os.path.exists(dst)
        if existed:
            subprocess.run(["cp", "-p", dst, os.path.join(bk_dir, name)], check=True)
            if name == SELF_FILE:
                subprocess.run(["cp", "-p", dst, os.path.join(OFFICE_DIR, "bot_updater.prev.py")], check=True)
        saved.append((dst, os.path.join(bk_dir, name) if existed else None))
        if os.path.exists(src):
            uid, gid, mode = _office_perm(dst if existed else None)
            tmp = dst + ".updtmp"
            subprocess.run(["cp", src, tmp], check=True); os.chmod(tmp, mode); os.chown(tmp, uid, gid); os.replace(tmp, dst)
        elif existed:
            os.remove(dst)
    return saved
 
 
def office_restore(saved):
    for dst, bk in saved:
        if bk:
            subprocess.run(["cp", "-p", bk, dst])
        elif os.path.exists(dst):
            os.remove(dst)
 
 
def bump_versions(units, old_head):
    """3·4번처럼 BOT_VERSION 이 있는 봇은 이번 수정에서 안 올렸으면 자동으로 한 칸 (v4.3 → v4.3.1)"""
    out = {}
    roots = targets()
    for u in units:
        root = roots.get(u, "")
        for f in sorted(os.listdir(root)) if root else []:
            if not (f.endswith("_core.py") or f == "averaging_plugin.py"):   # 2번 스나이퍼 버전은 averaging_plugin.py
                continue
            p = os.path.join(root, f); src = open(p, encoding="utf-8").read()
            m = re.search(r"""^(BOT_VERSION\s*=\s*["'])v?(\d+)\.(\d+)(?:\.(\d+))?(["'])""", src, re.M)
            if not m:
                continue
            rel = os.path.relpath(p, REPO)
            rc, old = git("show", f"{old_head}:{rel}")
            om = re.search(r"""BOT_VERSION\s*=\s*["']([^"']+)""", old) if rc == 0 else None
            cur = f"v{m.group(2)}.{m.group(3)}" + (f".{m.group(4)}" if m.group(4) else "")
            if om and om.group(1) == cur:
                cur = f"v{m.group(2)}.{m.group(3)}.{int(m.group(4) or 0) + 1}"
                open(p, "w", encoding="utf-8").write(src[:m.start()] + m.group(1) + cur + m.group(5) + src[m.end():])
            out[u] = cur
    return out
 
 
VNEXT = "v" + "NEXT"   # 버전 자동 기입 표시 글자 (코드에 붙여 쓰면 적용 때 이 줄까지 바뀌므로 조립)


def fill_vnext(files, ver, office=False):
    """올린 파일 속 VNEXT 표시 글자 → 이번에 정해진 버전 (저장소 파일 + 사무실이면 /opt/bot-office 복사본도). 실패해도 업데이트는 계속"""
    for f in files:
        paths = [os.path.join(REPO, f)] + ([os.path.join(OFFICE_DIR, os.path.basename(f))] if office else [])
        for p in paths:
            try:
                with open(p, encoding="utf-8") as fh:
                    src = fh.read()
                if VNEXT not in src:
                    continue
                st = os.stat(p)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(re.sub(r"\b" + VNEXT + r"\b", ver, src))
                os.chown(p, st.st_uid, st.st_gid)
            except Exception as e:
                print("버전 자동 기입 실패:", p, type(e).__name__, flush=True)


def next_tag(prefix):
    _, tags = git("tag", "-l", f"{prefix}-v*")
    nums = [tuple(map(int, m.groups())) for t in tags.split() if (m := re.fullmatch(re.escape(prefix) + r"-v(\d+)\.(\d+)\.(\d+)", t))]
    x, y, z = max(nums, default=(1, 0, 0))
    return f"v{x}.{y}.{z + 1}"
 
 
def healthy(unit):
    _, n0 = sh(SYSTEMCTL, "show", unit, "-p", "NRestarts", "--value")
    for _ in range(4):
        time.sleep(float(os.environ.get("U_WAIT", "4")))
        if sh(SYSTEMCTL, "is-active", unit)[1] != "active":
            return False
    return sh(SYSTEMCTL, "show", unit, "-p", "NRestarts", "--value")[1] == n0
 
 
def apply(st, key):
    o = st.get("offers", {}).get(key)
    if not o:
        return say("⚠️ 이 업데이트 정보를 찾지 못했습니다. GitHub에 다시 올리면 새로 알려 드려요.")
    br, sha = o["branch"], o["sha"]
    git("fetch", "-q", "origin")
    rc, now_sha = git("rev-parse", f"origin/{br}")
    if rc or now_sha != sha:
        return say("⚠️ 그사이 브랜치가 바뀌었거나 사라졌습니다. 새 알림의 버튼을 눌러 주세요.")
    _, files = git("diff", "--name-only", f"HEAD...{sha}")
    files = [f for f in files.splitlines() if f.strip()]
    units, bad = classify(files)
    if bad:
        return say("⛔ 허용되지 않은 파일이 있어 적용하지 않았습니다: " + esc(", ".join(bad[:5])))
    units = {u: fs for u, fs in units.items() if fs}   # 문서(.md)만 바뀐 봇은 재시작·버전 기록 안 함
    _, added = git("diff", f"HEAD...{sha}")
    if SECRET_RE.search("\n".join(l for l in added.splitlines() if l.startswith("+"))):
        return say("⛔ 바뀐 내용에 비밀키로 보이는 값이 있어 적용하지 않았습니다. GitHub에서 그 내용을 지우고 키는 새로 발급해 주세요.")
    pause_verified = set()
    for unit in units:
        root = targets().get(unit)
        if unit in DC.UNITS.values() and DC.state_path(root).exists():
            try:
                state = DC.read(DC.state_path(root))
            except Exception:
                return say("⛔ 중지 상태 파일을 확인할 수 없습니다. 적용하지 않았습니다.")
            if state.get('phase') == 'paused':
                transport = 'kis_api_client.py' if unit == DC.UNITS['1'] else 'b_core.py' if unit == DC.UNITS['4'] else 'toss_api.py'
                relative = os.path.relpath(root, REPO)
                marker = 'with gate():' if unit == DC.UNITS['4'] else '@__import__("deployment_gate").transport'
                rc, source = git('show', sha + ':' + relative + '/' + transport)
                rc_gate, gate_source = git('show', sha + ':' + relative + '/deployment_gate.py')
                if rc or rc_gate or marker not in source or 'VERSION = 1' not in gate_source:
                    return say('⛔ 업데이트 코드에 신규 주문 차단 연결이 없습니다. 차단 부품을 보존한 수정본이 필요합니다.')
            if state.get('phase') not in ('running','waiting','paused'):
                return say('⛔ 일시중지 상태 값이 잘못돼 적용하지 않았습니다.')
            if state.get('phase') in ('waiting','paused'):
                if not DC.ready(sys.modules[__name__],unit):
                    return say("⏳ " + NAMES[unit] + " 보유/미체결 또는 실행 차단 확인 대기 중입니다. 적용하지 않았습니다.", DC.resume_rows(unit))
                pause_verified.add(unit)
    busy = [f"{NAMES.get(u, u)}: {r}" for u in units if (r := busy_reason(u, u in pause_verified))]
    if {os.path.basename(f) for f in units.get(OFFICE_UNIT, [])} & set(OFFICE_EXTRA[FANDING_UNIT]) and (r := busy_reason(FANDING_UNIT)):
        busy.append("5번 팬딩: " + r)
    if busy:
        return say("⏸ <b>지금은 적용하지 않았습니다</b>\n▫️ " + "\n▫️ ".join(esc(b) for b in busy) + "\n▫️ 나중에 같은 알림의 ✅를 다시 눌러 주세요.",
                   [[{"text": "✅ 다시 시도", "callback_data": f"up:{key}"}]] +
                   [[{"text": "⏸ " + NAMES[u] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + n}] for n,u in DC.UNITS.items() if u in units and gate_installed(u)])
    if git("status", "--porcelain", "--untracked-files=no")[1].strip() or git("diff", "--cached", "--name-only")[1].strip():
        return say("⛔ 서버에 저장 안 된 변경이 있어 멈췄습니다. Claude나 Gemini에게 확인을 요청해 주세요.")
    rc_m, main_sha = git("rev-parse", "origin/main")
    if rc_m == 0 and git("merge-base", "--is-ancestor", main_sha, "HEAD")[0] and git("merge-base", "--is-ancestor", main_sha, sha)[0]:
        return say("⛔ GitHub main 에 서버를 거치지 않은 수정이 있고, 이 브랜치는 그 수정을 포함하지 않아 적용하지 않았습니다.\n"
                   "▫️ 그대로 적용하면 main 업로드가 실패하고 서버·main 이 더 어긋납니다.\n"
                   "→ main 기준 새 브랜치로 먼저 승인하거나, 이 브랜치를 최신 main 기준으로 다시 올려 주세요.")
    _, old_head = git("rev-parse", "HEAD")
    say(f"⏳ 업데이트 적용 중… ({esc(', '.join(NAMES.get(u, u) for u in units) or '문서')})")
    rc, out = git("merge", "--no-edit", "-m", f"update: {br}", sha)
    if rc:
        git("merge", "--abort")
        return say("⛔ 서버 코드와 업데이트 브랜치가 충돌해 적용하지 않았습니다. 이미 처리한 이전 변경만 선택해 정리한 뒤 새 알림으로 승인하세요.",
                   [[{"text": "🧹 이전 변경·충돌 정리", "callback_data": "cp:" + key}]] if UC else None)
    bad_py = [f for fs in units.values() for f in fs if f.endswith(".py") and os.path.exists(os.path.join(REPO, f)) and sh(sys.executable, "-m", "py_compile", os.path.join(REPO, f))[0]]
    if bad_py:
        git("reset", "-q", "--hard", old_head)
        return say("⛔ 문법 오류가 있어 원래대로 되돌렸습니다: " + esc(", ".join(bad_py)))
    vers = bump_versions([u for u in units if u != OFFICE_UNIT], old_head)
    office_files = units.get(OFFICE_UNIT, [])
    saved = office_deploy(office_files) if office_files else []
    perm_fixed = office_perm_repair() if office_files else []
    self_update = any(os.path.basename(f) in (SELF_FILE, "update_conflicts.py", "sniper_upstream.py") for f in office_files)
    restart = [u for u in units if u != OFFICE_UNIT]
    if any(os.path.basename(f) not in (SELF_FILE, "bot_updater_guard.py", "update_conflicts.py", "sniper_upstream.py") for f in office_files):
        restart.append(OFFICE_UNIT)   # 비서 화면·브리핑 등이 바뀌면 사무실 서비스 다시 시작
    names_changed = {os.path.basename(f) for f in office_files}
    for xu, xfiles in OFFICE_EXTRA.items():   # 비서·팬딩 상시 서비스도 관련 파일이 바뀌었으면 재시작 (설치돼 있을 때만)
        if names_changed & set(xfiles) and sh(SYSTEMCTL, "is-active", xu)[1].strip() == "active":   # 지금 실행 중인 것만 (비서는 disabled 지만 실행 중)
            restart.append(xu)
    failed = []
    for u in restart:
        sh(SYSTEMCTL, "restart", u)
        if not healthy(u):
            failed.append(u)
    if failed:
        git("reset", "-q", "--hard", old_head)
        office_restore(saved)
        for u in restart:
            sh(SYSTEMCTL, "restart", u)
        return say("🚨 <b>업데이트 후 봇이 정상 실행되지 않아 원래 코드로 되돌렸습니다</b>\n▫️ " + esc(", ".join(NAMES.get(u, u) for u in failed)) + "\n▫️ 봇은 이전 버전으로 다시 켜졌습니다.")
    # 버전 기록 (봇 폴더 CHANGELOG.md) → 커밋 → 태그 → main 업로드
    _, msgs = git("log", "--format=%s", f"{old_head}..{sha}", "-n", "8")
    tags, roots, now = [], targets(), datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    for u in units:
        prefix = u.replace(".service", ""); ver = vers.get(u) or next_tag(prefix)
        if not ver.count(".") == 2:
            ver = next_tag(prefix)
        if git("rev-parse", "-q", "--verify", f"refs/tags/{prefix}-{ver}")[0] == 0:
            ver = next_tag(prefix)
        fill_vnext(units[u], ver, u == OFFICE_UNIT)
        log = os.path.join(roots[u], "CHANGELOG.md"); head = f"# {NAMES.get(u, u)} 변경 기록\n\n"
        old = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
        body = old[len(head):] if old.startswith(head) else old
        fl = ", ".join(os.path.basename(f) for f in units[u]) or "문서"
        open(log, "w", encoding="utf-8").write(head + f"## {ver} · {now} (KST)\n- 파일: {fl}\n- 내용: {msgs.splitlines()[0] if msgs else br}\n- 브랜치: {br}\n\n" + body)
        os.chown(log, OWNER.pw_uid, OWNER.pw_gid)
        tags.append(f"{prefix}-{ver}")
    if units:   # 적용 전 작업 폴더가 깨끗했으므로, 바뀐 건 이번 수정·버전 올림·CHANGELOG 뿐
        git("add", "-u", "--", *{os.path.relpath(roots[u], REPO) for u in units})
        git("add", "-f", "--", *{os.path.join(os.path.relpath(roots[u], REPO), "CHANGELOG.md") for u in units})
    try:   # 현재 상태 파일도 같은 기록에 함께 (실패해도 업데이트는 계속)
        if write_status(f"업데이트 적용 ({br}: {msgs.splitlines()[0] if msgs else ''})"):
            git("add", "-f", "--", STATUS_FILE)
    except Exception as e:
        print("STATUS.md 작성 실패:", type(e).__name__, e, flush=True)
    if git("diff", "--cached", "--name-only")[1].strip():
        git("commit", "-qm", ("버전 기록: " + ", ".join(tags)) if tags else "상태 기록: STATUS.md")
    for t in tags:
        git("tag", t)
    rc, out = git("push", "-q", "origin", "HEAD:main", *tags)
    if rc == 0 and br != "staging":
        git("push", "-q", "origin", "--delete", br)
    git("push", "-q", "-f", "origin", "HEAD:staging")   # 다음 수정은 항상 최신 main 기준 staging 에서
    st.setdefault("seen", {}).pop(br, None)
    done = ", ".join(NAMES.get(u, u) + " " + t.rsplit("-", 1)[-1] for u, t in zip(units, tags)) or "문서만 반영"
    say(f"🎉 <b>업데이트 완료</b>\n▫️ {esc(done)}\n"
        + (f"▫️ 사무실 파일 읽기 권한 고침: {esc(', '.join(perm_fixed))}\n" if perm_fixed else "")
        + f"▫️ 재시작 정상 확인 · GitHub main {'업로드 완료' if rc == 0 else '업로드 실패(봇은 새 코드로 정상 실행 중): ' + esc(out[-150:])}"
        + ("\n▫️ 업데이트 비서 자신도 바뀌어 지금 새 버전으로 다시 시작합니다. (2분 안에 정상 신호가 없으면 자동으로 이전 버전 복구)" if self_update else ""))
    for unit in units:
        root = targets().get(unit)
        if unit in DC.UNITS.values() and DC.state_path(root).exists() and DC.read(DC.state_path(root)).get('phase') == 'paused':
            say("⏸ " + NAMES[unit] + " 업데이트용 차단은 유지 중입니다. 준비되면 재개하세요.", DC.resume_rows(unit))
    if self_update:
        st["self_pending"] = {"since": time.time()}
        save(STATE, st)
        sh(SYSTEMCTL, "restart", SELF_UNIT)
 
 
def show_diff(st, key):
    o = st.get("offers", {}).get(key)
    if not o:
        return say("⚠️ 이 업데이트 정보를 찾지 못했습니다.")
    _, stat = git("diff", "--stat", f"HEAD...{o['sha']}")
    _, d = git("diff", "-U1", f"HEAD...{o['sha']}", "--", "*.py")
    lines = [l for l in d.splitlines() if l.startswith(("+", "-", "@@")) and not l.startswith(("+++", "---"))]
    say(f"🔍 <b>바뀐 내용</b> (<code>{esc(o['branch'])}</code>)\n<pre>{esc(stat[-800:])}</pre>\n<pre>{esc(chr(10).join(lines)[:2600])}</pre>",
        [[{"text": "✅ 업데이트", "callback_data": f"up:{key}"}, {"text": "❌ 무시", "callback_data": f"ig:{key}"}]])
 
 
# ---------------------------------------------------------------- 하단 버튼 메뉴 (/start 로 뜸)
# 버튼은 기존 글자 명령과 똑같이 처리된다. 승인·코드 보기·무시·일시중지·재개는 업데이트 알림 안의 버튼으로 이미 처리한다.
MENU_ALIAS = {"🔄 업데이트 확인": "업데이트 확인", "⏸ 거래 상태": "거래 상태", "🔎 원작 확인": "원작 확인", "❓ 도움말": "/help", "🧹 충돌 정리": "충돌 정리"}
HELP_TEXT = ("🛠 <b>업데이트 비서 사용법</b>\n"
             "▫️ <b>🔄 업데이트 확인</b> : GitHub에 올라온 수정 확인 → 새 알림의 버튼(✅ 적용 · 🔍 코드 보기 · 🗑 무시)\n"
             "▫️ <b>🧹 충돌 정리</b> : 이전 변경 파일 선택 → 확인 → 원래 브랜치를 백업 후 정리 → 별도 업데이트 승인\n"
             "▫️ <b>⏸ 거래 상태</b> : 업데이트용 일시중지·대기 중인 봇 보기 → ▶ 재개 버튼\n"
             "▫️ <b>🔎 원작 확인</b> : 2번 스나이퍼 원작자 새 버전 지금 확인 (평소엔 매일 09:02 자동 · 알림 전용)\n"
             "▫️ <b>상태 기록</b> (글자로) : 저장소 STATUS.md 를 지금 갱신 (평소엔 적용 때·매일 06:10 자동)\n"
             "▫️ 일시중지·재개·승인은 업데이트 알림 아래 버튼으로 진행합니다.")


def menu_keyboard():
    rows = [["🔄 업데이트 확인", "⏸ 거래 상태"], ["🔎 원작 확인", "❓ 도움말"] if SU else ["❓ 도움말"]]
    if UC:
        rows.insert(1, ["🧹 충돌 정리"])
    return [[{"text": t} for t in r] for r in rows]


# ---------------------------------------------------------------- 텔레그램 버튼 받기
def handle(st, upd):
    cb = upd.get("callback_query")
    msg = upd.get("message")
    if cb:
        if str(cb.get("message", {}).get("chat", {}).get("id")) != str(CFG.get("chat_id")):
            return
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        act, _, key = (cb.get("data") or "").partition(":")
        if act == "cp" and UC:
            return UC.preview(sys.modules[__name__], st, key)
        elif act in ("ct", "cc", "cr", "cx") and UC:
            return UC.handle(sys.modules[__name__], st, act, key)
        elif act == "pa":
            offer_data = st.get('offers',{}).get(key)
            if not offer_data:
                return say('⚠️ 최신 업데이트 알림에서 다시 눌러 주세요.')
            git('fetch','-q','origin')
            rc, sha = git('rev-parse','origin/'+offer_data['branch'])
            if rc or sha != offer_data['sha']:
                return say('⚠️ 브랜치가 바뀌었습니다. 새 알림에서 눌러 주세요.')
            _, files = git('diff','--name-only','HEAD...'+sha)
            units,bad = classify(files.splitlines())
            if bad:
                return say('⛔ 허용되지 않은 파일이 있어 중지를 요청하지 않았습니다.')
            for unit in DC.UNITS.values():
                if units.get(unit):
                    DC.request(sys.modules[__name__],unit,key)
        elif act == 'ra':
            for unit, root in targets().items():
                if unit not in DC.UNITS.values() or not DC.state_path(root).exists():
                    continue
                state = DC.read(DC.state_path(root))
                if state.get('offer_key') == key and state.get('phase') in ('waiting','paused'):
                    DC.resume(sys.modules[__name__],unit)
        elif act == "ps":
            offer_key, _, number = key.partition(":")
            unit = DC.UNITS.get(number)
            offer_data = st.get("offers", {}).get(offer_key)
            if not unit or not offer_data:
                return say("⚠️ 최신 업데이트 알림에서 다시 눌러 주세요.")
            git("fetch", "-q", "origin")
            rc, sha = git("rev-parse", "origin/" + offer_data['branch'])
            if rc or sha != offer_data['sha']:
                return say("⚠️ 브랜치가 바뀌었습니다. 업데이트 확인 후 새 버튼을 눌러 주세요.")
            _, files = git("diff", "--name-only", "HEAD..." + sha)
            units, bad = classify(files.splitlines())
            if bad or not units.get(unit):
                return say("⛔ 해당 업데이트 대상 봇만 중지할 수 있습니다.")
            DC.request(sys.modules[__name__], unit, offer_key)
        elif act == "rs":
            if key in DC.UNITS:
                DC.resume(sys.modules[__name__], DC.UNITS[key])
        elif act == "up":
            apply(st, key)
        elif act == "df":
            show_diff(st, key)
        elif act == "ig":
            st.get("offers", {}).pop(key, None); say("🗑 이 업데이트는 무시했습니다. (봇 그대로)")
        elif act in ("um", "ud", "ui") and SU:   # 2번 스나이퍼 원작 새 버전 (합치기 / 보기 / 무시)
            {"um": SU.merge, "ud": SU.show, "ui": SU.ignore}[act](sys.modules[__name__], st, key)
    elif msg and str(msg.get("chat", {}).get("id")) == str(CFG.get("chat_id")):
        txt = (msg.get("text") or "").strip()
        txt = MENU_ALIAS.get(txt, txt)   # 하단 버튼 글자 → 같은 명령
        if txt in ("/start", "/help", "도움말", "메뉴", "/menu", "?"):
            say(HELP_TEXT, keyboard=menu_keyboard())
        elif txt in ("충돌 정리", "/conflicts") and UC:
            live = live_branches()
            if live is None:
                return say('⚠️ GitHub 확인에 실패했습니다. 잠시 후 다시 눌러 주세요. (아무것도 지우지 않았습니다)')
            removed = prune(st, live)
            offers = st.setdefault('offers', {})
            missing = [b for b in live if b not in {o['branch'] for o in offers.values()}]
            if missing:   # 최신 알림이 지워졌거나 없던 브랜치는 새 알림을 다시 만든다
                for b in missing:
                    st.setdefault('seen', {})[b] = live[b]
                    offer(st, b, live[b])
            head = ('🗑 반영 안 된 지난 알림 ' + str(removed) + '개를 지웠습니다.\n') if removed else ''
            if not offers:
                return say(head + '✅ 정리할 업데이트가 없습니다. (GitHub에 대기 중인 수정 없음)')
            rows = [[{'text': '🧹 ' + o['branch'] + ' (' + o['sha'][:7] + ')', 'callback_data': 'cp:' + k}]
                    for k, o in offers.items()]
            return say(head + '현재 대기 중인 업데이트입니다. 정리할 브랜치를 선택하세요. 아직 파일은 변경하지 않습니다.', rows)
        elif txt in ("상태 기록", "상태기록", "/status"):
            say("📝 STATUS.md: " + esc(status_daily(st, force=True) or "확인 안 함"))
        elif txt in ("원작 확인", "원작 업데이트", "원작업데이트", "/upstream") and SU:
            say("🔄 원작 스나이퍼 저장소를 확인합니다…")
            SU.check(sys.modules[__name__], st, force=True)
        elif txt in ("거래 상태", "일시중지 상태", "/pause_status"):
            found = False
            for unit, root in targets().items():
                if unit not in DC.UNITS.values() or not DC.state_path(root).exists():
                    continue
                try:
                    state = DC.read(DC.state_path(root))
                except Exception:
                    say("⚠️ " + NAMES[unit] + " 중지 상태 파일 확인 필요")
                    continue
                if state.get('phase') in ('waiting', 'paused'):
                    found = True
                    say("⏸ " + NAMES[unit] + ": " + ('일시중지' if state['phase']=='paused' else '잔고 0 대기') + "\n" + esc(state.get('reason','확인 중')), DC.resume_rows(unit))
            if not found:
                say("✅ 업데이트용 일시중지/대기 중인 봇이 없습니다.")
        elif txt in ("업데이트", "업데이트 확인", "/update"):
            say("🔄 GitHub를 확인합니다…"); before = len(st.get("offers", {}))
            scan(st, force=True)
            if len(st.get("offers", {})) == before:
                say("✅ 새로 올라온 수정이 없습니다.")
 
 
def main():
    st = load(STATE, {})
    if git("rev-parse", "-q", "--verify", "refs/remotes/origin/staging")[0]:
        git("push", "-q", "origin", "HEAD:staging")   # 처음 한 번: staging 브랜치 만들기
    DC.monitor(sys.modules[__name__])
    last = 0.0
    offset = st.get("offset")
    while True:
        if time.time() - last >= CHECK_EVERY:
            last = time.time()
            try:
                scan(st)
            except Exception as e:
                print("확인 오류:", e, flush=True)
            try:
                r = status_daily(st)
                if r:
                    print("STATUS.md:", r, flush=True)
            except Exception as e:
                print("STATUS.md 오류:", type(e).__name__, e, flush=True)
            if SU:
                try:
                    SU.check(sys.modules[__name__], st)   # 하루 1번(09:02 KST) 원작 스나이퍼 새 버전 확인
                except Exception as e:
                    print("원작 확인 오류:", e, flush=True)
            save(STATE, st)
        r = tg("getUpdates", timeout=25, offset=offset, allowed_updates=["message", "callback_query"]) if offset else tg("getUpdates", timeout=25, allowed_updates=["message", "callback_query"])
        if not r.get("ok"):
            time.sleep(10); continue
        if st.pop("self_pending", None):
            cl = _changelog(os.path.join(REPO, "bot_office"), 1)
            save(STATE, st); say(f"✅ 업데이트 비서 새 버전{' (사무실 ' + cl[0][0] + ')' if cl else ''} 정상 작동 확인", keyboard=menu_keyboard())
        for upd in r.get("result", []):
            offset = upd["update_id"] + 1; st["offset"] = offset
            try:
                handle(st, upd)
            except Exception as e:
                print("처리 오류:", e, flush=True); say("🚨 업데이트 비서 처리 오류: " + esc(str(e)[:200]))
            save(STATE, st)
        if os.environ.get("U_ONCE"):
            break
 
 
if __name__ == "__main__":
    main()
