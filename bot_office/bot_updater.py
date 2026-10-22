#!/usr/bin/env python3
# BOT_UPDATER_V2 — GitHub에 올라온 수정(main 이외의 브랜치)을 감지 → 텔레그램 [✅ 업데이트] 버튼 → 안전 확인 후 적용
#  · Gemini/Jules/딥시크 등 누가 올려도 main 이 아닌 브랜치면 감지 (main 은 서버가 적용한 결과만 올라가는 곳)
#  · 1~4번 봇 + 5번 사무실 비서(저장소 bot_office/ → 서버 /opt/bot-office) · 업데이트 비서 자신도 업데이트(실패 시 2분 뒤 자동 복구)
#  · 적용: 보유·매매시간 확인 → 병합 → 문법 검사 → 해당 봇만 재시작 → 실패 시 원래 코드로 자동 복구 → 버전 기록 → main 업로드
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
 
 
def say(text, rows=None):
    p = {"chat_id": CFG.get("chat_id"), "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
    if rows:
        p["reply_markup"] = {"inline_keyboard": rows}
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
def busy_reason(unit):
    now_k, now_e = datetime.now(KST), datetime.now(ET)
    k, e = now_k.hour * 100 + now_k.minute, now_e.hour * 100 + now_e.minute
    if unit == "toss_sniper.service":
        L = load(os.path.join(targets().get(unit, ""), "AssassinLedger_SOXS.json"), {})
        b = [x for x in ("buy_order_id", "sell_order_id") if L.get(x)] + [x for x in ("buy_count", "last_buy_price", "target_sell_price") if float(L.get(x) or 0) > 0]
        if b:
            return "스나이퍼가 주식을 들고 있거나 주문 중 (강제 청산 뒤 다시 눌러 주세요)"
    if unit == "toss_dca.service" and (1050 <= k <= 1510 or 1120 <= e <= 1600):
        return "3번 봇 매매 시간 (한국장 11시 · 미국장 11:30 EST 전후)"
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
    if not bad:
        rows.insert(0, [{"text": "✅ 업데이트", "callback_data": f"up:{key}"}])
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
            if not f.endswith("_core.py"):
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
    busy = [f"{NAMES.get(u, u)}: {r}" for u in units if (r := busy_reason(u))]
    if busy:
        return say("⏸ <b>지금은 적용하지 않았습니다</b>\n▫️ " + "\n▫️ ".join(esc(b) for b in busy) + "\n▫️ 나중에 같은 알림의 ✅를 다시 눌러 주세요.",
                   [[{"text": "✅ 다시 시도", "callback_data": f"up:{key}"}]])
    if git("status", "--porcelain", "--untracked-files=no")[1].strip() or git("diff", "--cached", "--name-only")[1].strip():
        return say("⛔ 서버에 저장 안 된 변경이 있어 멈췄습니다. Claude나 Gemini에게 확인을 요청해 주세요.")
    _, old_head = git("rev-parse", "HEAD")
    say(f"⏳ 업데이트 적용 중… ({esc(', '.join(NAMES.get(u, u) for u in units) or '문서')})")
    rc, out = git("merge", "--no-edit", "-m", f"update: {br}", sha)
    if rc:
        git("merge", "--abort")
        return say("⛔ 지금 서버 코드와 겹치는 부분이 있어 합치지 못했습니다(충돌). Gemini에게 '최신 main 기준으로 다시 올려 줘'라고 요청해 주세요.\n" + esc(out[-300:]))
    bad_py = [f for fs in units.values() for f in fs if f.endswith(".py") and os.path.exists(os.path.join(REPO, f)) and sh(sys.executable, "-m", "py_compile", os.path.join(REPO, f))[0]]
    if bad_py:
        git("reset", "-q", "--hard", old_head)
        return say("⛔ 문법 오류가 있어 원래대로 되돌렸습니다: " + esc(", ".join(bad_py)))
    vers = bump_versions([u for u in units if u != OFFICE_UNIT], old_head)
    office_files = units.get(OFFICE_UNIT, [])
    saved = office_deploy(office_files) if office_files else []
    self_update = any(os.path.basename(f) == SELF_FILE for f in office_files)
    restart = [u for u in units if u != OFFICE_UNIT]
    if any(os.path.basename(f) not in (SELF_FILE, "bot_updater_guard.py") for f in office_files):
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
 
 
# ---------------------------------------------------------------- 텔레그램 버튼 받기
def handle(st, upd):
    cb = upd.get("callback_query")
    msg = upd.get("message")
    if cb:
        if str(cb.get("message", {}).get("chat", {}).get("id")) != str(CFG.get("chat_id")):
            return
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        act, _, key = (cb.get("data") or "").partition(":")
        if act == "up":
            apply(st, key)
        elif act == "df":
            show_diff(st, key)
        elif act == "ig":
            st.get("offers", {}).pop(key, None); say("🗑 이 업데이트는 무시했습니다. (봇 그대로)")
    elif msg and str(msg.get("chat", {}).get("id")) == str(CFG.get("chat_id")):
        if (msg.get("text") or "").strip() in ("업데이트", "업데이트 확인", "/update"):
            say("🔄 GitHub를 확인합니다…"); before = len(st.get("offers", {}))
            scan(st, force=True)
            if len(st.get("offers", {})) == before:
                say("✅ 새로 올라온 수정이 없습니다.")
 
 
def main():
    st = load(STATE, {})
    if git("rev-parse", "-q", "--verify", "refs/remotes/origin/staging")[0]:
        git("push", "-q", "origin", "HEAD:staging")   # 처음 한 번: staging 브랜치 만들기
    last = 0.0
    offset = st.get("offset")
    while True:
        if time.time() - last >= CHECK_EVERY:
            last = time.time()
            try:
                scan(st)
            except Exception as e:
                print("확인 오류:", e, flush=True)
            save(STATE, st)
        r = tg("getUpdates", timeout=25, offset=offset, allowed_updates=["message", "callback_query"]) if offset else tg("getUpdates", timeout=25, allowed_updates=["message", "callback_query"])
        if not r.get("ok"):
            time.sleep(10); continue
        if st.pop("self_pending", None):
            save(STATE, st); say("✅ 업데이트 비서 새 버전 정상 작동 확인")
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
