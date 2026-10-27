#!/usr/bin/env python3
# =====================================================================
# FILE: bot_office/sniper_upstream.py   (업데이트 비서 부품 · 2번 스나이퍼 원작자 새 버전 '알림 전용')
#
#  사무실 v1.0.49 (2026-10-28): 알림 전용으로 다시 켬 — 자동 합치기·자동 업로드 없음
#   · 하루 1번(아침 브리핑 직후 09:02 KST) 원작 저장소(pipios4006-boop/pipiosToss_bot) 확인 · 6. Update 에 '원작 확인'이면 즉시
#   · 내 2번 봇이 바탕으로 삼은 원작 커밋(기준) 이후 새 커밋이 있으면 🔴 [중요] 알림 (바뀐 파일·쌓인 수정 수·원작 매뉴얼 제목)
#   · [🔍 변경 보기] 커밋별 바뀐 파일 · [✅ 반영 완료] 기준을 이 버전으로 옮기고 원작 원본을 GitHub 태그로 백업 · [🔕 이번 버전 무시]
#   · ✅ 또는 🔕 를 누를 때까지 매일 아침 다시 알림. 원작이 또 바뀌면 새로 알림.
#   · 내 봇에는 원작 위에 데이장 매매·토스 토큰 공유·업데이트 범위 제한이 붙어 있어 그대로 덮어쓰면 안 됨
#     → 알림 내용을 AI 에게 보여 주고 '원작 최신에 내 수정 다시 붙여서 staging 파일로' 요청 → 평소처럼 📦 알림 ✅ 로 적용
#  bot_updater.py 가 이 파일을 불러 씁니다 (u = bot_updater 모듈: git·say·esc 사용). 함수 이름 check/show/merge/ignore 는 그대로 유지.
# =====================================================================
import os
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

UPSTREAM_URL = os.environ.get("U_SNIPER_UPSTREAM", "https://github.com/pipios4006-boop/pipiosToss_bot.git")
UPSTREAM_NAME = "pipiosToss_bot"
CHECK_AT = os.environ.get("U_SNIPER_AT", "09:02")   # 하루 1번 확인 시각 (KST) — 아침 브리핑(09:00) 바로 뒤
WORK = os.environ.get("U_SNIPER_WORK", "/var/lib/bot-updater/sniper_upstream")
# 2026-10-28 비교 결과: 2번 봇(v1.0.7 이후)은 원작 2e23df2 (10-24 11:54 KST) 와 가장 같음 → 처음 기준
BASE_DEFAULT = "2e23df2ede063e4db6d14e57b3cd833938c15395"
KST = ZoneInfo("Asia/Seoul")


def _run(cmd, cwd=None, timeout=120):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0", TZ="Asia/Seoul"))
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"
    except Exception as e:
        return 1, str(e)


def _g(*a, timeout=120):
    return _run(["git", "-c", "core.quotePath=false", "-C", os.path.join(WORK, "up"), *a], timeout=timeout)


def _slot(st):
    sl = st.setdefault("sniper_up", {})
    for k, v in (("last_day", ""), ("offers", {}), ("ignored", ""), ("base", ""), ("prev_base", "")):
        sl.setdefault(k, v)
    return sl


def _base(sl):
    return sl.get("base") or BASE_DEFAULT


def remote_head():
    rc, out = _run(["git", "ls-remote", UPSTREAM_URL, "HEAD"], timeout=60)
    return out.split()[0] if rc == 0 and out else ""


def _sync(sha):
    """원작 저장소를 WORK/up 에 받아 두고 최신으로 (작업 폴더는 쓰지 않음)"""
    os.makedirs(WORK, exist_ok=True)
    up = os.path.join(WORK, "up")
    if not os.path.isdir(os.path.join(up, ".git")):
        rc, out = _run(["git", "clone", "-q", "--no-checkout", UPSTREAM_URL, up], timeout=300)
        if rc:
            raise RuntimeError("원작 저장소 받기 실패: " + out[-200:])
    else:
        _g("fetch", "-q", "--prune", "origin", timeout=300)
    if _g("cat-file", "-e", sha + "^{commit}")[0]:
        raise RuntimeError("원작 커밋을 찾지 못함: " + sha[:7])


def _when(sha):
    return _g("log", "-1", "--format=%cd", "--date=format-local:%m-%d %H:%M", sha)[1] if sha else ""


def _title(sha):
    rc, readme = _g("show", f"{sha}:README.md")
    if rc:
        return ""
    for ln in readme.splitlines():
        if ln.strip().startswith("#"):
            return ln.strip("# ").strip()[:120]
    return ""


def _summary(base, head):
    """기준 → 최신 사이: 커밋 수, 바뀐 파일 표, 새로 생긴/없어진 파일"""
    if _g("cat-file", "-e", base + "^{commit}")[0]:
        return "?", "", [], []
    n = _g("rev-list", "--count", f"{base}..{head}")[1] or "?"
    rc, stat = _g("diff", "--stat=60", f"{base}..{head}")
    stat = "\n".join(stat.splitlines()[-12:]) if rc == 0 else ""
    added, gone = [], []
    for ln in _g("diff", "--name-status", f"{base}..{head}")[1].splitlines():
        p = ln.split("\t")
        if len(p) >= 2 and p[0] == "A":
            added.append(p[-1])
        elif len(p) >= 2 and p[0] == "D":
            gone.append(p[-1])
    return n, stat, added, gone


# ---------------------------------------------------------------- 1) 새 버전 확인 (하루 1번 · '원작 확인'이면 바로)
def check(u, st, force=False):
    sl = _slot(st)
    if not force:
        now = datetime.now(KST)
        today = now.strftime("%Y-%m-%d")
        if sl["last_day"] == today or now.strftime("%H:%M") < CHECK_AT:
            return
        sl["last_day"] = today
    head = remote_head()
    if not head:
        if force:
            u.say("⚠️ 원작 저장소를 확인하지 못했습니다 (인터넷/GitHub 문제). 잠시 뒤 다시 '원작 확인'을 눌러 주세요.")
        else:
            sl["last_day"] = ""   # 다음 확인 때 다시 시도
        return
    base = _base(sl)
    try:
        _sync(head)
    except Exception as e:
        if force:
            u.say("⚠️ " + u.esc(str(e)[:300]))
        else:
            sl["last_day"] = ""
        return
    if head == base:
        sl["offers"].clear()
        if force:
            u.say(f"✅ 원작 새 버전이 없습니다.\n▫️ 내 2번 봇의 기준 원작: <code>{base[:7]}</code> ({u.esc(_when(base))} KST)")
        return
    if head == sl["ignored"] and not force:
        return
    key = head[:12]
    for k in list(sl["offers"]):   # 더 새 버전이 나와 지난 알림은 정리
        if k != key:
            sl["offers"].pop(k, None)
    o = sl["offers"].get(key)
    if o and not force:   # 아직 ✅/🔕 안 누른 같은 버전 → 매일 아침 다시 알림
        return u.say("🔁 <b>[다시 알림]</b> 아직 처리하지 않았어요\n\n" + o["msg"], o["rows"])
    n, stat, added, gone = _summary(base, head)
    files = ""
    if added:
        files += "▫️ 새 파일: " + u.esc(", ".join(added[:6])) + "\n"
    if gone:
        files += "▫️ 없어진 파일: " + u.esc(", ".join(gone[:6])) + "\n"
    msg = ("🔴🔴 <b>[중요 · 꼭 확인] 2번 스나이퍼 원작자 새 버전</b> 🔴🔴\n"
           f"▫️ 원작 최신: <code>{head[:7]}</code> ({u.esc(_when(head))} KST)\n"
           f"▫️ 원작 매뉴얼: <b>{u.esc(_title(head) or '제목 미확인')}</b>\n"
           f"▫️ 내 2번 봇의 기준 원작: <code>{base[:7]}</code> ({u.esc(_when(base))} KST) → 그 뒤 원작 수정 <b>{u.esc(n)}개</b>\n"
           + (f"<pre>{u.esc(stat)}</pre>\n" if stat else "")
           + files
           + "⚠️ 원작자가 매매 전략 자체를 바꾸는 경우가 있어요. 위 매뉴얼 제목·바뀐 파일을 꼭 확인하세요.\n"
           "▫️ 내 봇에는 데이장 매매·토스 토큰 공유·업데이트 범위 제한이 붙어 있어 <b>원작으로 그냥 덮으면 안 돼요</b>.\n"
           "▫️ 반영하려면 이 알림을 AI 에게 보여 주고 '원작 최신에 내 수정 다시 붙여서 staging 파일로 만들어 줘'라고 요청 → 평소처럼 📦 알림 ✅\n"
           "▫️ 반영을 마쳤으면 <b>✅ 반영 완료</b>, 이번 버전을 건너뛰려면 <b>🔕 무시</b>. 누를 때까지 매일 아침 다시 알려 드려요.")
    rows = [[{"text": "🔍 변경 보기", "callback_data": f"ud:{key}"}],
            [{"text": "✅ 반영 완료 (기준 갱신)", "callback_data": f"um:{key}"}, {"text": "🔕 이번 버전 무시", "callback_data": f"ui:{key}"}]]
    sl["offers"][key] = {"sha": head, "at": time.time(), "msg": msg, "rows": rows}
    u.say(msg, rows)


# ---------------------------------------------------------------- 2) 변경 보기 (커밋별 바뀐 파일)
def show(u, st, key):
    sl = _slot(st)
    o = sl["offers"].get(key)
    if not o:
        return u.say("⚠️ 이 원작 버전 정보를 찾지 못했습니다. 6. Update 에 '원작 확인'이라고 보내 주세요.")
    base = _base(sl)
    rc, log = _g("log", "--format=■ %h %cd", "--date=format-local:%m-%d %H:%M", "--name-only", "-n", "15", f"{base}..{o['sha']}")
    if rc:
        rc, log = _g("log", "--format=■ %h %cd", "--date=format-local:%m-%d %H:%M", "--name-only", "-n", "15", o["sha"])
    log = "\n".join(l for l in log.splitlines() if l.strip())
    u.say(f"🔍 <b>원작 변경 내역</b> (최근 15개 · 기준 <code>{base[:7]}</code> → <code>{o['sha'][:7]}</code>)\n"
          f"<pre>{u.esc(log[:2800])}</pre>\n▫️ 원작자는 커밋 제목을 'Add files via upload'로 올려서 파일 이름으로만 구분돼요.",
          [o["rows"][1]])


# ---------------------------------------------------------------- 3) 반영 완료 → 기준을 이 버전으로 (+ 원작 원본 백업 태그)
def merge(u, st, key):
    sl = _slot(st)
    if key == "back":   # 잘못 눌렀을 때 되돌리기
        if not sl["prev_base"]:
            return u.say("⚠️ 되돌릴 이전 기준이 없습니다.")
        sl["base"], sl["prev_base"] = sl["prev_base"], ""
        sl["last_day"] = ""
        return u.say(f"↩️ 기준을 <code>{sl['base'][:7]}</code> 로 되돌렸습니다. 6. Update 에 '원작 확인'을 보내면 다시 알려 드려요.")
    o = sl["offers"].get(key)
    if not o:
        return u.say("⚠️ 이 원작 버전 정보를 찾지 못했습니다. 6. Update 에 '원작 확인'이라고 보내 주세요.")
    sha = o["sha"]
    sl["prev_base"], sl["base"] = _base(sl), sha
    sl["offers"].pop(key, None)
    sl["ignored"] = ""
    tag, note = f"upstream/{UPSTREAM_NAME}-{sha[:7]}", ""
    try:   # 원작 원본을 내 저장소 태그로 보관 (실패해도 기준 갱신은 유지)
        if u.git("rev-parse", "-q", "--verify", f"refs/tags/{tag}")[0] != 0:
            if u.git("fetch", "-q", "--no-tags", UPSTREAM_URL, sha, timeout=300)[0] == 0:
                u.git("tag", tag, sha)
        note = (f"▫️ 원작 원본 백업: <code>{tag}</code>\n" if u.git("push", "-q", "origin", tag, timeout=180)[0] == 0
                else "▫️ ⚠️ 원작 원본 백업 태그 업로드는 실패했습니다 (기준 갱신은 완료)\n")
    except Exception as e:
        note = "▫️ ⚠️ 백업 태그 오류: " + u.esc(str(e)[:120]) + "\n"
    u.say(f"✅ <b>반영 완료로 표시했습니다</b>\n▫️ 내 2번 봇의 기준 원작 → <code>{sha[:7]}</code>\n" + note
          + "▫️ 원작이 또 바뀌면 다음 아침에 다시 알려 드려요.",
          [[{"text": "↩️ 잘못 눌렀어요 (되돌리기)", "callback_data": "um:back"}]])


def ignore(u, st, key):
    sl = _slot(st)
    o = sl["offers"].pop(key, None)
    if o:
        sl["ignored"] = o["sha"]
    u.say("🔕 이 원작 버전은 알림을 끕니다. (봇 그대로 · 원작이 또 바뀌면 다시 알려 드려요)")
