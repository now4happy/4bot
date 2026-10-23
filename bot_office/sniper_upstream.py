#!/usr/bin/env python3
# =====================================================================
# FILE: bot_office/sniper_upstream.py   (업데이트 비서 부품 · 2번 스나이퍼 원작 업데이트 + 💧물타기 자동 합치기)
#
#  흐름: 하루 1번(아침 브리핑 직후 09:02 KST) 원작 저장소(pipios4006-boop/pipiosToss_bot) 확인 · 비서에게 '원작 확인' 이면 즉시
#        → 새 커밋이면 임시 폴더에서 '원작 새 파일 + 내 물타기(averaging_plugin.py) + HOOK 자동 적용 + 문법·불러오기 검사'를 미리 해 보고
#        → 텔레그램 알림 (원작 제목·버전, 자동 합치기 가능 여부)
#        → [🔀 물타기 합쳐서 올리기] 누르면: 백업 태그 2개 → GitHub staging 업로드 → 평소처럼 📦 알림의 ✅ 로 적용
#  백업: backup/toss_sniper-날짜시각 (합치기 직전 내 봇 전체) · upstream/pipiosToss_bot-커밋 (원작 원본)
#  bot_updater.py 가 이 파일을 불러 씁니다 (u = bot_updater 모듈: git·say·esc·REPO·OWNER·scan 사용).
# =====================================================================
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

UPSTREAM_URL = os.environ.get("U_SNIPER_UPSTREAM", "https://github.com/pipios4006-boop/pipiosToss_bot.git")
UPSTREAM_NAME = "pipiosToss_bot"
FOLDER = "toss_sniper"
CHECK_AT = os.environ.get("U_SNIPER_AT", "09:02")   # 하루 1번 확인 시각 (KST) — 아침 브리핑(09:00) 바로 뒤
WORK = os.environ.get("U_SNIPER_WORK", "/var/lib/bot-updater/sniper_upstream")
KEEP = ("averaging_plugin.py", "averaging_merge.py")
KST = ZoneInfo("Asia/Seoul")


def _run(cmd, cwd=None, timeout=180, env=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"
    except Exception as e:
        return 1, str(e)


def _slot(st):
    return st.setdefault("sniper_up", {"last_day": "", "seen": {}, "offers": {}})


def current_base(u):
    try:
        src = open(os.path.join(u.REPO, FOLDER, "averaging_plugin.py"), encoding="utf-8").read()
        m = re.search(r'^UPSTREAM_COMMIT = "([0-9a-f]*)"', src, re.M)
        t = re.search(r'^BASE_VERSION = "([^"]*)"', src, re.M)
        return (m.group(1) if m else ""), (t.group(1) if t else "")
    except Exception:
        return "", ""


def remote_head():
    rc, out = _run(["git", "ls-remote", UPSTREAM_URL, "HEAD"], timeout=60)
    if rc or not out:
        return ""
    return out.split()[0]


def _upstream_repo(sha):
    """원작 저장소를 WORK/up 에 받아 두고 sha 로 맞춤 → 폴더 경로"""
    os.makedirs(WORK, exist_ok=True)
    up = os.path.join(WORK, "up")
    if not os.path.isdir(os.path.join(up, ".git")):
        shutil.rmtree(up, ignore_errors=True)
        rc, out = _run(["git", "clone", "-q", UPSTREAM_URL, up], timeout=300)
        if rc:
            raise RuntimeError("원작 저장소 받기 실패: " + out[-200:])
    else:
        _run(["git", "-C", up, "fetch", "-q", "--prune", "origin"], timeout=300)
    rc, out = _run(["git", "-C", up, "checkout", "-q", "--force", "--detach", sha])
    if rc:
        raise RuntimeError("원작 커밋 찾기 실패: " + out[-200:])
    return up


def _prepare(u, sha):
    """임시 폴더에서 합치기를 미리 해 봄 → (성공?, 보고, 폴더)"""
    up = _upstream_repo(sha)
    build = os.path.join(WORK, "build")
    shutil.rmtree(build, ignore_errors=True)
    os.makedirs(build)
    _, tracked = u.git("ls-files", FOLDER)
    for rel in tracked.splitlines():
        src = os.path.join(u.REPO, rel)
        if os.path.isfile(src) and os.path.dirname(rel) == FOLDER:
            shutil.copy2(src, os.path.join(build, os.path.basename(rel)))
    if not os.path.exists(os.path.join(build, "averaging_plugin.py")):
        return False, {"ok": False, "fail": ["서버에 averaging_plugin.py 가 없음 (물타기 모듈 먼저 설치 필요)"], "warn": [], "applied": []}, build
    for f in os.listdir(build):   # 예전 원작 코드는 지우고 (물타기 파일·문서는 유지)
        if f.endswith(".py") and f not in KEEP:
            os.remove(os.path.join(build, f))
    for f in os.listdir(up):      # 원작 새 코드 + 원작 매뉴얼
        if (f.endswith(".py") and f not in KEEP) or f == "README.md":
            shutil.copy2(os.path.join(up, f), os.path.join(build, f))
    rc, out = _run([sys.executable, os.path.join(build, "averaging_merge.py"), build, "--commit", sha], cwd=build)
    rep = {"ok": False, "fail": ["합치기 도구 결과 없음: " + out[-200:]], "warn": [], "applied": []}
    for ln in out.splitlines():
        if ln.startswith("RESULT "):
            try:
                rep = json.loads(ln[7:])
            except Exception:
                pass
    if rc != 0 or not rep.get("ok"):
        rep["ok"] = False
        return False, rep, build
    # 서버 실제 패키지로 '불러오기' 시험 (새 원작이 서버에 없는 패키지를 쓰는지 등)
    env = dict(os.environ, TOSS_CLIENT_ID="x", TOSS_CLIENT_SECRET="x", TELEGRAM_BOT_TOKEN="1:x", TELEGRAM_CHAT_ID="1")
    py = _bot_python(u)
    rc, out = _run([py, "-c", "import sys; sys.path.insert(0, '.'); import averaging_plugin, tg_ui_plugin, main; print('IMPORT_OK')"],
                   cwd=build, timeout=120, env=env)
    if "IMPORT_OK" not in out:
        rep["ok"] = False
        tail = [l for l in out.splitlines() if l.strip()][-3:]
        rep.setdefault("fail", []).append("합친 봇 불러오기 시험 실패 (새 패키지 필요 등): " + " | ".join(tail)[-300:])
        return False, rep, build
    rep.setdefault("applied", []).append("합친 봇 불러오기 시험 통과 (서버 패키지 기준)")
    return True, rep, build


def _bot_python(u):
    """2번 봇이 쓰는 파이썬 (systemd ExecStart 에서 찾고, 없으면 지금 파이썬)"""
    rc, out = _run([u.SYSTEMCTL, "show", "toss_sniper.service", "-p", "ExecStart", "--value"], timeout=20)
    m = re.search(r"path=(\S+python[\d.]*)", out or "") or re.search(r"(/\S+python[\d.]*)", out or "")
    return m.group(1) if m and os.path.exists(m.group(1)) else sys.executable


def _rep_text(u, rep):
    lines = []
    for x in rep.get("fail", [])[:4]:
        lines.append("⛔ " + u.esc(x)[:350])
    for x in rep.get("warn", [])[:3]:
        lines.append("⚠️ " + u.esc(x)[:200])
    return "\n".join(lines)


# ---------------------------------------------------------------- 1) 새 버전 확인
def check(u, st, force=False):
    sl = _slot(st)
    if not force:
        now = datetime.now(KST)
        today = now.strftime("%Y-%m-%d")
        if sl.get("last_day") == today or now.strftime("%H:%M") < CHECK_AT:
            return
        sl["last_day"] = today
    head = remote_head()
    if not head:
        if force:
            u.say("⚠️ 원작 저장소를 확인하지 못했습니다 (인터넷/GitHub 문제). 잠시 뒤 다시 시도해 주세요.")
        return
    for k, o in list(sl["offers"].items()):   # 더 새 버전이 나와 지난 알림은 정리
        if o.get("sha") != head:
            sl["offers"].pop(k, None)
    if not force and head in sl["seen"] and head[:12] in sl["offers"] and sl["offers"][head[:12]].get("msg"):
        o = sl["offers"][head[:12]]   # 아직 🔀/❌ 안 누른 원작 새 버전 → 매일 아침 다시 알림
        return u.say("🔁 <b>[다시 알림]</b> 아직 처리하지 않았어요\n\n" + o["msg"], o.get("rows"))
    base, base_title = current_base(u)
    if base and head.startswith(base[:12]):
        if force:
            u.say(f"✅ 원작 새 버전이 없습니다.\n▫️ 지금 합쳐진 원작: <code>{u.esc(base_title)}</code> (<code>{base[:7]}</code>)")
        return
    if head in sl["seen"] and not force:
        return
    sl["seen"][head] = time.time()
    try:
        good, rep, _ = _prepare(u, head)
    except Exception as e:
        good, rep = False, {"fail": [str(e)], "warn": [], "title": ""}
    up = os.path.join(WORK, "up")
    _, when = _run(["git", "-C", up, "log", "-1", "--format=%cd", "--date=format:%m-%d %H:%M", head])
    stat = ""
    if base:
        rc, stat = _run(["git", "-C", up, "diff", "--stat", "--stat-width=60", f"{base}..{head}", "--", "*.py"])
        stat = "\n".join(stat.splitlines()[-8:]) if rc == 0 else ""
    key = head[:12]
    rows = [[{"text": "🔍 원작 변경 보기", "callback_data": f"ud:{key}"}, {"text": "❌ 이번 버전 무시", "callback_data": f"ui:{key}"}]]
    if good:
        rows.insert(0, [{"text": "🔀 물타기 합쳐서 staging에 올리기", "callback_data": f"um:{key}"}])
    msg = (
        "🔴🔴 <b>[중요 · 꼭 확인] 2번 스나이퍼 원작자 새 버전</b> 🔴🔴\n"
        f"▫️ 원작: <b>{u.esc(rep.get('title') or '제목 미확인')}</b> (<code>{head[:7]}</code> · {u.esc(when)} KST)\n"
        f"▫️ 지금 내 봇: <code>{u.esc(base_title or '알 수 없음')}</code> (<code>{base[:7] or '-'}</code>) + 💧물타기\n"
        + (f"<pre>{u.esc(stat)}</pre>\n" if stat else "")
        + (f"▫️ 💧 물타기 자동 합치기: <b>✅ 가능</b> (HOOK 적용·문법·불러오기 시험 통과)\n" if good else
           f"▫️ 💧 물타기 자동 합치기: <b>⛔ 불가</b>\n{_rep_text(u, rep)}\n"
           "▫️ 원작 구조가 크게 바뀐 경우예요. 이 알림 내용을 Claude 에게 보여 주고 'averaging_merge.py / averaging_plugin.py 를 새 원작에 맞춰 줘'라고 요청하세요.\n")
        + "⚠️ 원작자가 매매 전략 자체를 바꾸는 경우가 있어요. <b>위 원작 제목·버전을 꼭 확인</b>하고 진행하세요.\n"
        "▫️ 🔀 또는 ❌ 를 누를 때까지 매일 아침 브리핑 뒤에 다시 알려 드려요.")
    sl["offers"][key] = {"sha": head, "title": rep.get("title", ""), "ok": good, "at": time.time(), "msg": msg, "rows": rows}
    u.say(msg, rows)


# ---------------------------------------------------------------- 2) 원작 변경 보기
def show(u, st, key):
    o = _slot(st)["offers"].get(key)
    if not o:
        return u.say("⚠️ 이 원작 버전 정보를 찾지 못했습니다. 비서에게 '원작 확인'이라고 보내 주세요.")
    base, _ = current_base(u)
    up = os.path.join(WORK, "up")
    _, log = _run(["git", "-C", up, "log", "--format=%cd · %s", "--date=format:%m-%d %H:%M", "-n", "8", f"{base}..{o['sha']}" if base else o["sha"]])
    _, readme = _run(["git", "-C", up, "show", f"{o['sha']}:README.md"])
    head = "\n".join(l for l in readme.splitlines()[:6] if l.strip())[:900]
    rows = [[{"text": "🔀 물타기 합쳐서 staging에 올리기", "callback_data": f"um:{key}"}]] if o.get("ok") else None
    u.say(f"🔍 <b>원작 변경 내역</b> (<code>{o['sha'][:7]}</code>)\n<pre>{u.esc(log[-900:])}</pre>\n📘 <b>원작 매뉴얼 첫 부분</b>\n<pre>{u.esc(head)}</pre>", rows)


def ignore(u, st, key):
    _slot(st)["offers"].pop(key, None)
    u.say("🗑 이 원작 버전은 무시했습니다. (봇 그대로 · 원작이 또 바뀌면 다시 알려 드려요)")


# ---------------------------------------------------------------- 3) 합쳐서 staging 에 올리기
def merge(u, st, key):
    sl = _slot(st)
    o = sl["offers"].get(key)
    if not o:
        return u.say("⚠️ 이 원작 버전 정보를 찾지 못했습니다. 비서에게 '원작 확인'이라고 보내 주세요.")
    sha = o["sha"]
    u.say(f"⏳ 원작 <code>{sha[:7]}</code> + 💧물타기 합치는 중… (백업 → 합치기 → 검사 → staging 업로드)")
    try:
        good, rep, build = _prepare(u, sha)
    except Exception as e:
        return u.say("🚨 합치기 준비 실패: " + u.esc(str(e)[:300]))
    if not good:
        return u.say("⛔ <b>자동 합치기 실패</b> — 아무것도 올리지 않았습니다.\n" + _rep_text(u, rep))

    # ① 백업 태그 (GitHub 에 영구 보관)
    ts = datetime.now(KST).strftime("%Y%m%d-%H%M")
    u.git("fetch", "-q", "origin")
    notes = []
    t1 = f"backup/{FOLDER}-{ts}"
    if u.git("tag", t1, "origin/main")[0] == 0 and u.git("push", "-q", "origin", t1)[0] == 0:
        notes.append(f"<code>{t1}</code> (합치기 직전 내 봇 전체)")
    t2 = f"upstream/{UPSTREAM_NAME}-{sha[:7]}"
    if u.git("rev-parse", "-q", "--verify", f"refs/tags/{t2}")[0] != 0:
        if u.git("fetch", "-q", "--no-tags", UPSTREAM_URL, sha, timeout=300)[0] == 0:
            u.git("tag", t2, sha)
    if u.git("push", "-q", "origin", t2)[0] == 0:
        notes.append(f"<code>{t2}</code> (원작 원본)")

    # ② 깨끗한 작업 공간(worktree)에서 staging 커밋 만들기 (서버에서 돌고 있는 봇 폴더는 건드리지 않음)
    wt = os.path.join(u.OWNER.pw_dir, ".sniper_merge_wt")
    u.git("worktree", "remove", "--force", wt)
    shutil.rmtree(wt, ignore_errors=True)
    u.git("worktree", "prune")
    rc, out = u.git("worktree", "add", "-q", "--detach", wt, "origin/main")
    if rc:
        return u.say("🚨 작업 공간 만들기 실패: " + u.esc(out[-300:]))
    try:
        dst = os.path.join(wt, FOLDER)
        new_files = {f for f in os.listdir(build) if f.endswith(".py") or f == "README.md"}
        for f in os.listdir(dst):
            if f.endswith(".py") and f not in new_files:
                os.remove(os.path.join(dst, f))     # 원작에서 없어진 파일
        for f in new_files:
            shutil.copy2(os.path.join(build, f), os.path.join(dst, f))
            os.chown(os.path.join(dst, f), u.OWNER.pw_uid, u.OWNER.pw_gid)
        g = lambda *a, **k: u.git("-C", wt, *a, **k)
        g("add", "-A", "--", FOLDER)
        if not g("diff", "--cached", "--name-only")[1].strip():
            return u.say("ℹ️ 합쳐 봤지만 지금 봇과 달라진 코드가 없습니다.")
        title = rep.get("title") or o.get("title") or "원작 새 버전"
        rc, out = g("commit", "-q", "-m", f"2번 스나이퍼: {title} ({sha[:7]}) + 💧물타기 자동 합치기")
        if rc:
            return u.say("🚨 커밋 실패: " + u.esc(out[-300:]))
        rc, out = g("push", "-q", "origin", "HEAD:staging", timeout=180)
        if rc:
            return u.say("⛔ staging 업로드 실패 — staging 에 아직 처리 안 한 다른 수정이 있을 수 있어요.\n"
                         "▫️ 먼저 그 📦 알림을 ✅ 또는 ❌ 로 처리한 뒤, 이 알림의 🔀 를 다시 눌러 주세요.\n" + u.esc(out[-200:]))
    finally:
        u.git("worktree", "remove", "--force", wt)
        u.git("worktree", "prune")

    sl["offers"].pop(key, None)
    u.say("✅ <b>원작 새 버전 + 💧물타기 합치기 완료 → GitHub staging 업로드</b>\n"
          + ("▫️ 백업: " + " · ".join(notes) + "\n" if notes else "▫️ ⚠️ 백업 태그 업로드는 실패했습니다 (합치기는 정상)\n")
          + "\n".join("▫️ " + u.esc(x) for x in rep.get("applied", [])[:8])
          + "\n▫️ 곧 오는 📦 '새 수정' 알림에서 <b>✅ 업데이트</b>를 누르면 적용됩니다. (스나이퍼가 주식을 들고 있지 않을 때)")
    try:
        u.scan(st, force=True)
    except Exception:
        pass
