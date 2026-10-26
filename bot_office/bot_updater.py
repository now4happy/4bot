#!/usr/bin/env python3
# BOT_UPDATER_V2 — GitHub에 올라온 수정(main 이외의 브랜치)을 감지 → 텔레그램 [✅ 업데이트] 버튼 → 안전 확인 후 적용
#  · Gemini/Jules/딥시크 등 누가 올려도 main 이 아닌 브랜치면 감지 (main 은 서버가 적용한 결과만 올라가는 곳)
#  · 1~4번 봇 + 5번 사무실 비서(저장소 bot_office/ → 서버 /opt/bot-office) · 업데이트 비서 자신도 업데이트(실패 시 2분 뒤 자동 복구)
#  · 적용: 보유·매매시간 확인 → 병합 → 문법 검사 → 해당 봇만 재시작 → 실패 시 원래 코드로 자동 복구 → 버전 기록 → main 업로드
#  · 2번 스나이퍼: 원작자 새 버전 하루 1번(아침 브리핑 뒤) 확인 + 💧물타기 자동 합치기 (sniper_upstream.py) · 비서에게 '원작 확인'
import json, os, pwd, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
 
REPO = os.environ.get("U_REPO", "/home/gieokkim")
TG_CFG = os.environ.get("U_TG", "/etc/bot-office/telegram.json")
TARGETS = os.environ.get("U_TARGETS", "/var/lib/bot-office-deploy/targets.json")
STATE = os.environ.get("U_STATE", "/var/lib/bot-updater/state.json")
OFFICE_DIR = os.environ.get("U_OFFICE", "/opt/bot-office")
OFFICE_UNIT, SELF_UNIT, SELF_FILE = "bot-office.service", "bot-updater.service", "bot_updater.py"
OFFICE_EXT = (".py", ".html", ".css", ".js")
SYSTEMCTL = os.environ.get("U_SYSTEMCTL", "systemctl")
TG_API = os.environ.get("U_TG_API", "https://api.telegram.org")
CHECK_EVERY = int(os.environ.get("U_EVERY", "300"))
KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
NAMES = {"han4384tubot.service": "1번 한투 라오어", "toss_sniper.service": "2번 토스 스나이퍼",
         "toss_dca.service": "3번 토스 적립", "bithumb_bot.service": "4번 빗썸 적립", OFFICE_UNIT: "5번 사무실 비서"}
SECRET_RE = re.compile(r"(\d{8,10}:[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,})")
OWNER = pwd.getpwuid(os.stat(REPO).st_uid)
try:   # 2번 스나이퍼 원작 업데이트 + 💧물타기 자동 합치기 부품 (없어도 비서는 정상 작동)
    import sniper_upstream as SU
except Exception as _e:
    SU = None
    print("sniper_upstream 불러오기 실패:", _e, flush=True)

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
    cmd = ["env", f"HOME={OWNER.pw_dir}", "GIT_TERMINAL_PROMPT=0", "git", "-C", REPO, *a]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    return sh(*cmd, timeout=timeout)
 
 
def git_raw(*a):
    cmd = ["env", f"HOME={OWNER.pw_dir}", "git", "-C", REPO, *a]
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
        root = targets().get(unit, "")
        for sym in ("SOXS", "SOXL"):   # 듀얼 스나이퍼: 두 종목 장부 모두 확인
            L = load(os.path.join(root, f"AssassinLedger_{sym}.json"), {})
            b = [x for x in ("sell_order_id",) if L.get(x)] + [x for x in ("last_buy_price", "target_sell_price") if float(L.get(x) or 0) > 0]
            if L.get("buy_order_id") and not float(L.get("last_buy_price") or 0) > 0 and L.get("entry_session") not in ("", "CANCELED_MACRO"):
                b.append("buy_order_id")
            if b:
                return f"스나이퍼가 {sym} 을 들고 있거나 주문 중 (청산 뒤 다시 눌러 주세요)"
        A = load(os.path.join(root, "Averaging_state.json"), {})
        if any(isinstance(v, dict) and v.get("order_id") for v in A.values()):
            return "스나이퍼 💧물타기 추가 매수 주문 진행 중"
    if unit == "toss_dca.service":
        # 각 시장의 현지 요일을 사용: 한국 토요일 새벽의 미국 금요일 장은 보호.
        kr_busy = now_k.weekday() < 5 and 1050 <= k <= 1510
        us_busy = now_e.weekday() < 5 and 1120 <= e <= 1600
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
    return ""
 
 
# ---------------------------------------------------------------- 새 업데이트 찾기
def scan(st, force=False):
    rc, out = git("fetch", "-q", "--prune", "origin")
    if rc:
        if st.get("fetch_err") != out[:80]:
            st["fetch_err"] = out[:80]; say("⚠️ <b>[업데이트 비서] GitHub 확인 실패</b>\n▫️ " + esc(out[-200:]))
        return
    st["fetch_err"] = ""
    rc, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    for line in refs.splitlines():
        ref, sha = line.split()
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if br in ("main", "HEAD") or ref == "origin":
            continue
        if git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue   # 이미 반영된 브랜치
        seen = st.setdefault("seen", {})
        if seen.get(br) == sha and not force:
            continue
        seen[br] = sha
        offer(st, br, sha)
 
 
def offer(st, br, sha):
    _, files = git("diff", "--name-only", f"HEAD...{sha}")
    files = [f for f in files.splitlines() if f.strip()]
    units, bad = classify(files)
    _, log = git("log", "--format=%an · %s", f"HEAD..{sha}", "-n", "5")
    key = sha[:12]
    st.setdefault("offers", {})[key] = {"branch": br, "sha": sha, "at": time.time()}
    bots = ", ".join(NAMES.get(u, u) for u, fs in units.items() if fs) or "봇 코드 없음(문서만)"
    warn = ("\n⛔ <b>허용되지 않은 파일</b>: " + esc(", ".join(bad[:5])) + " → 이 업데이트는 적용할 수 없습니다") if bad else ""
    rows = [[{"text": "🔍 바뀐 내용 보기", "callback_data": f"df:{key}"}, {"text": "❌ 무시", "callback_data": f"ig:{key}"}]]
    if UC:
        rows.append([{"text": "🧹 이전 변경·충돌 정리", "callback_data": "cp:" + key}])
    if not bad:
        rows.insert(0, [{"text": "✅ 업데이트", "callback_data": f"up:{key}"}])
    if not bad and any(units.get(unit) for unit in DC.UNITS.values()):
        rows.append([{'text':'⏸ 이번 업데이트 대상 전체 중지 대기','callback_data':'pa:'+key},
                     {'text':'▶️ 이번 대상 거래 재개','callback_data':'ra:'+key}])
    for number, unit in DC.UNITS.items():
        if units.get(unit):
            rows.append([{ "text": "⏸ " + NAMES[unit] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + number}])
    say(f"📦 <b>[업데이트 비서] 새 수정이 올라왔어요</b>\n▫️ 대상: {esc(bots)}\n▫️ 브랜치: <code>{esc(br)}</code>\n"
        f"▫️ 파일: {esc(', '.join(files[:8]))}{' 외' if len(files) > 8 else ''}\n▫️ 내용:\n{esc(log[:600])}{warn}\n\n"
        "✅를 누르면 매매 중인지 확인 → 적용 → 재시작 확인(실패 시 자동 복구) → 버전 기록 → GitHub main 업로드까지 진행합니다.", rows)
 
 
# ---------------------------------------------------------------- 적용
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
            mode = os.stat(dst).st_mode & 0o777 if existed else 0o640
            tmp = dst + ".updtmp"
            subprocess.run(["cp", src, tmp], check=True); os.chmod(tmp, mode); os.chown(tmp, 0, 0); os.replace(tmp, dst)
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
    if busy:
        return say("⏸ <b>지금은 적용하지 않았습니다</b>\n▫️ " + "\n▫️ ".join(esc(b) for b in busy) + "\n▫️ 나중에 같은 알림의 ✅를 다시 눌러 주세요.",
                   [[{"text": "✅ 다시 시도", "callback_data": f"up:{key}"}]] +
                   [[{"text": "⏸ " + NAMES[u] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + n}] for n,u in DC.UNITS.items() if u in units])
    if git("status", "--porcelain", "--untracked-files=no")[1].strip() or git("diff", "--cached", "--name-only")[1].strip():
        return say("⛔ 서버에 저장 안 된 변경이 있어 멈췄습니다. Claude나 Gemini에게 확인을 요청해 주세요.")
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
    self_update = any(os.path.basename(f) in (SELF_FILE, "update_conflicts.py") for f in office_files)
    restart = [u for u in units if u != OFFICE_UNIT]
    if any(os.path.basename(f) not in (SELF_FILE, "bot_updater_guard.py", "update_conflicts.py") for f in office_files):
        restart.append(OFFICE_UNIT)   # 비서 화면·브리핑 등이 바뀌면 사무실 서비스 다시 시작
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
    if git("diff", "--cached", "--name-only")[1].strip():
        git("commit", "-qm", "버전 기록: " + ", ".join(tags))
    for t in tags:
        git("tag", t)
    rc, out = git("push", "-q", "origin", "HEAD:main", *tags)
    if rc == 0 and br != "staging":
        git("push", "-q", "origin", "--delete", br)
    git("push", "-q", "-f", "origin", "HEAD:staging")   # 다음 수정은 항상 최신 main 기준 staging 에서
    st.setdefault("seen", {}).pop(br, None)
    done = ", ".join(NAMES.get(u, u) + " " + t.rsplit("-", 1)[-1] for u, t in zip(units, tags)) or "문서만 반영"
    say(f"🎉 <b>업데이트 완료</b>\n▫️ {esc(done)}\n"
        f"▫️ 재시작 정상 확인 · GitHub main {'업로드 완료' if rc == 0 else '업로드 실패(봇은 새 코드로 정상 실행 중): ' + esc(out[-150:])}"
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
             "▫️ <b>🔎 원작 확인</b> : 2번 스나이퍼 원작 새 버전 확인 (연결돼 있을 때만)\n"
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
            offers = st.get('offers', {})
            if not offers:
                return say('정리할 알림이 없습니다. 업데이트 확인을 먼저 눌러 주세요.')
            rows = [[{'text': '🧹 ' + o['branch'], 'callback_data': 'cp:' + k}]
                    for k, o in offers.items()]
            return say('정리할 업데이트 브랜치를 선택하세요. 아직 파일은 변경하지 않습니다.', rows)
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
            save(STATE, st); say("✅ 업데이트 비서 새 버전 정상 작동 확인", keyboard=menu_keyboard())
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
