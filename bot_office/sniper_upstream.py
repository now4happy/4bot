#!/usr/bin/env python3
# =====================================================================
# FILE: bot_office/sniper_upstream.py   (업데이트 비서 부품 · 2번 스나이퍼 원작자 새 버전 알림 + 자동 업뎃)
#
#  사무실 vNEXT (2026-11-19, 방 updater-redesign-sniper-separate 판 2): 원작자 알림이 오면 2번 자동 업뎃 — 원작 직접 동기화(빨리감기만) → 스나이퍼만 재시작(항상, 장 시간 구분 없음) → 건강 확인 ①~④
#                       · 조건이 하나라도 안 맞으면 하지 않고 알림만(사유 표시) · 실패하면 적용 전 모습으로 자동 되돌림 + 그 원작 커밋은 사람이 풀 때까지 자동 중단 · [↩️ 되돌리기] 버튼
#                       · 자동 범위 밖: staging 코드 변경, 다른 봇 재시작, targets.json·환경·설정 변경, 병합 충돌, 새 설정 항목이 필요한 원작 업뎃
#                       · 동기화 명령 기본값 = 스나이퍼 자체 CLI: python3 <스나이퍼 폴더>/plugin_updater.py --base-dir <스나이퍼 폴더> (원작 HEAD 는 그 CLI 가 'upstream' 리모트에서 직접 읽음 · 원작 14개 파일만 가져와 'sniper: upstream <sha7> direct sync' 로 커밋)
#                         U_SNIPER_SYNC_CMD 로 바꿀 수 있고(같은 CLI 모양), U_REPO·U_UPSTREAM_SHA·U_UPSTREAM_BASE 환경변수는 동기화 명령에 넘기지 않음(안 씀) · 성공 판정은 종료 코드가 아니라 건강 확인 ②(커밋 제목 대조)
#                         장부 일치 확인 명령은 U_SNIPER_RECONCILE_CMD · 스나이퍼 폴더에 plugin_updater.py 가 없으면(기본값 사용 시) 자동 업뎃은 하지 않고 알림만
#  사무실 v1.8.6 (2026-11-14): 봇 이름·번호 새 1~9번 목록으로 표시 문자열만 정리 (전략·종목·금액·enabled 그대로)
#  사무실 v1.5.3 (2026-11-10): 매일 09:02 자동 확인 기본 꺼짐 (U_SNIPER_AUTO=1일 때만) — 원작 체크는 Muse 일일 체크로 이관 · 수동 '원작 확인'(force=True)은 그대로
#  사무실 v1.0.49 (2026-10-28): 알림 전용으로 다시 켬 — 자동 합치기·자동 업로드 없음
#   · 하루 1번(아침 브리핑 직후 09:02 KST) 원작 저장소(pipios4006-boop/pipiosToss_bot) 확인 · 6. Update 에 '원작 확인'이면 즉시
#   · 내 2번 봇이 바탕으로 삼은 원작 커밋(기준) 이후 새 커밋이 있으면 🔴 [중요] 알림 (바뀐 파일·쌓인 수정 수·원작 매뉴얼 제목)
#   · [🔍 변경 보기] 커밋별 바뀐 파일 · [✅ 반영 완료] 기준을 이 버전으로 옮기고 원작 원본을 GitHub 태그로 백업 · [🔕 이번 버전 무시]
#   · ✅ 또는 🔕 를 누를 때까지 매일 아침 다시 알림. 원작이 또 바뀌면 새로 알림.
#   · 내 봇에는 원작 위에 데이장 매매·토스 토큰 공유·업데이트 범위 제한이 붙어 있어 그대로 덮어쓰면 안 됨
#     → 알림 내용을 AI 에게 보여 주고 '원작 최신에 내 수정 다시 붙여서 staging 파일로' 요청 → 평소처럼 📦 알림 ✅ 로 적용
#  bot_updater.py 가 이 파일을 불러 씁니다 (u = bot_updater 모듈: git·say·esc 사용). 함수 이름 check/show/merge/ignore 는 그대로 유지.
# =====================================================================
import glob
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

UPSTREAM_URL = os.environ.get("U_SNIPER_UPSTREAM", "https://github.com/pipios4006-boop/pipiosToss_bot.git")
UPSTREAM_NAME = "pipiosToss_bot"
CHECK_AT = os.environ.get("U_SNIPER_AT", "09:02")   # 하루 1번 확인 시각 (KST) — 아침 브리핑(09:00) 바로 뒤
AUTO_CHECK = os.environ.get("U_SNIPER_AUTO", "0") == "1"  # 자동 확인 기본 꺼짐 (2026-11-10: 원작 체크는 Muse 일일 체크로 이관, 수동 확인은 유지)
WORK = os.environ.get("U_SNIPER_WORK", "/var/lib/bot-updater/sniper_upstream")
# 2026-10-28 비교 결과: 2번 봇(v1.0.7 이후)은 원작 2e23df2 (10-24 11:54 KST) 와 가장 같음 → 처음 기준
BASE_DEFAULT = "2e23df2ede063e4db6d14e57b3cd833938c15395"
KST = ZoneInfo("Asia/Seoul")
# --- 자동 업뎃 (사무실 vNEXT) — 장 시간 게이트 없음: 언제 업뎃하든 스나이퍼는 항상 재시작 (결정 2026-11-19) ---
AUTO_UPDATE = os.environ.get("U_SNIPER_AUTO_UPDATE", "1") != "0"                 # 0 이면 자동 업뎃 끔 (알림만)
SYNC_CMD = os.environ.get("U_SNIPER_SYNC_CMD", "").strip()                      # 원작 직접 동기화 실행 명령 (서버 설정 · 비어 있으면 기본값 = plugin_updater CLI, _sync_cmd 참고). U_REPO·U_UPSTREAM_SHA·U_UPSTREAM_BASE 환경변수는 안 쓰고 넘기지도 않음 — 원작 HEAD 는 CLI 가 직접 읽음
RECONCILE_CMD = os.environ.get("U_SNIPER_RECONCILE_CMD", "").strip()            # 잔고·장부 일치 확인 명령 (선택 · 종료코드 0 = 일치)
HOLD_FILE = os.environ.get("U_SNIPER_HOLD", "/var/lib/bot-updater/sniper_auto_hold")   # 이 파일이 있으면 자동 업뎃 안 함 (이체·임시 수정·모의 등 사람이 잠시 막을 때)
OBS_SECONDS = float(os.environ.get("U_SNIPER_OBS", "60"))                       # 재시작 뒤 오류 로그를 지켜보는 시간(초)
JOURNALCTL = os.environ.get("U_JOURNALCTL", "journalctl")
SYNC_TIMEOUT = int(os.environ.get("U_SNIPER_SYNC_TIMEOUT", "600"))
# 원작이 설정 항목을 새로 요구할 가능성이 있는 파일 이름 (추정 — 설정 샘플·예시·환경 파일이 바뀌면 자동으로 하지 않고 수동)
CONFIG_FILE_RE = re.compile(r"(example|sample|template|\.env|requirements)|^(config|settings)", re.I)


def _sniper_dir(u):
    """스나이퍼 폴더 절대 경로: 서버 targets.json 의 스나이퍼 root, 없으면 <저장소>/toss_sniper"""
    try:
        root = u.targets().get(u.SNIPER_UNIT)
    except Exception:
        root = None
    return root or os.path.join(u.REPO, u.SNIPER_DIR)


def _sync_cmd(u):
    """동기화 명령 문자열. U_SNIPER_SYNC_CMD 가 있으면 그대로, 없으면 plugin_updater CLI 기본값:
    python3 <스나이퍼 폴더>/plugin_updater.py --base-dir <스나이퍼 폴더>  (toss_sniper/plugin_updater.py _cli_main)"""
    if SYNC_CMD:
        return SYNC_CMD
    d = _sniper_dir(u)
    return f"python3 {shlex.quote(os.path.join(d, 'plugin_updater.py'))} --base-dir {shlex.quote(d)}"


def _sync_cmd_ready(u):
    """기본값을 쓸 때는 plugin_updater.py 가 실제로 있어야 함 (없으면 예전처럼 자동 업뎃 안 하고 알림만). 직접 지정한 명령은 그대로 믿음"""
    return bool(SYNC_CMD) or os.path.isfile(os.path.join(_sniper_dir(u), "plugin_updater.py"))


def _run(cmd, cwd=None, timeout=120, extra_env=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0", TZ="Asia/Seoul", **(extra_env or {})))
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"
    except Exception as e:
        return 1, str(e)


def _g(*a, timeout=120):
    return _run(["git", "-c", "core.quotePath=false", "-C", os.path.join(WORK, "up"), *a], timeout=timeout)


def _slot(st):
    sl = st.setdefault("sniper_up", {})
    for k, v in (("last_day", ""), ("offers", {}), ("ignored", ""), ("base", ""), ("prev_base", ""),
                 ("auto_day", ""), ("auto_failed", {}), ("auto_last", {})):   # 뒤 3개: 자동 업뎃 (하루 1회 · 실패한 원작 커밋 · 마지막 결과)
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
        if not AUTO_CHECK:
            return
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
        u.say("🔁 <b>[다시 알림]</b> 아직 처리하지 않았어요\n\n" + o["msg"], o["rows"])
        return _auto_safe(u, st, head, key)   # 사무실 vNEXT: 알림이 간 뒤 조건이 맞으면 자동 업뎃 (조건이 풀리는 날 다시 시도)
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
    if not force:   # 사무실 vNEXT: 수동 '원작 확인'은 알림만 · 매일 자동 확인에서 새 원작 커밋 알림이 간 뒤 자동 업뎃을 시도
        _auto_safe(u, st, head, key)


# ---------------------------------------------------------------- 2) 변경 보기 (커밋별 바뀐 파일)
def show(u, st, key):
    sl = _slot(st)
    o = sl["offers"].get(key)
    if not o:
        return u.say("⚠️ 이 원작 버전 정보를 찾지 못했습니다. 9. Update 에 '원작 확인'이라고 보내 주세요.")
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
        return u.say(f"↩️ 기준을 <code>{sl['base'][:7]}</code> 로 되돌렸습니다. 9. Update 에 '원작 확인'을 보내면 다시 알려 드려요.")
    o = sl["offers"].get(key)
    if not o:
        return u.say("⚠️ 이 원작 버전 정보를 찾지 못했습니다. 9. Update 에 '원작 확인'이라고 보내 주세요.")
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


# ---------------------------------------------------------------- 4) 자동 업뎃 (사무실 vNEXT)
# 범위: 원작 새 커밋 알림 → 원작 직접 동기화(빨리감기만) → 스나이퍼만 재시작(항상) → 건강 확인 ①~④ → 실패하면 적용 전 모습으로 되돌림.
# 자동 범위 밖(항상 수동): staging 코드 변경 · 다른 봇 재시작 · targets.json·환경·설정 변경 · 병합 충돌 · 원작이 새 설정 항목을 요구하는 업뎃.
def _today():
    return datetime.now(KST).strftime("%Y-%m-%d")


def _auto_safe(u, st, head, key):
    """자동 업뎃 시도 — 어떤 오류도 알림 흐름(check)을 깨지 않게 가둠"""
    try:
        auto_update(u, st, head, key)
    except Exception as e:
        try:
            u.say("⚠️ 자동 업뎃 처리 중 오류로 멈췄습니다: " + u.esc(type(e).__name__ + " " + str(e)[:160]) + "\n▫️ 스나이퍼 코드가 바뀌었는지 서버에서 확인해 주세요.")
        except Exception:
            pass


def _scrub(u, text):
    return u.SECRET_RE.sub("***", text or "")


def _ledger_snapshot(u):
    """장부 파일별 (읽힘, 내용 있음) — 동기화 전후 비교용 (이체 중인 SOXL 이 빈 장부에 다시 들어간 사고 재발 방지)"""
    out = {}
    root = u.targets().get(u.SNIPER_UNIT, "")
    for p in (sorted(glob.glob(os.path.join(root, "soxl_stratum_ledger*.json"))) if root else []):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            L = d.get("SOXL", d) if isinstance(d, dict) else d
            out[os.path.basename(p)] = (True, bool(L))
        except Exception:
            out[os.path.basename(p)] = (False, False)
    return out


def _dirty_names(u):
    """작업 폴더에서 저장 안 된 변경 파일 이름 집합 (추적 파일만)"""
    return {line.split()[-1] for line in u.git("status", "--porcelain", "--untracked-files=no")[1].splitlines() if line.split()}


def _auto_blockers(u, sl, base, head):
    """자동 업뎃을 막는 사유 목록 (비어 있으면 진행). 하나라도 있으면 하지 않고 알림만 보낸다."""
    why = []
    if _g("merge-base", "--is-ancestor", base, head)[0] != 0:
        why.append("빨리감기(fast-forward)가 아닙니다 — 기준 원작 커밋이 새 커밋의 조상이 아님 (병합·되감기는 자동 범위 밖)")
    if head in sl["auto_failed"]:
        why.append("같은 원작 커밋으로 자동 업뎃이 실패한 적이 있어 중단 중입니다 (풀려면 '원작 자동 재개')")
    if sl.get("auto_day") == _today():
        why.append("오늘 이미 자동 업뎃을 시도했습니다 (하루 최대 1회)")
    if os.path.exists(HOLD_FILE):
        why.append("운영자 보류 표시 파일이 있습니다 (이체·임시 수정·모의 등으로 사람이 막아 둠)")
    phase = u.sniper_pause_phase()
    if phase in ("waiting", "paused"):
        why.append("스나이퍼가 일시중지·대기 상태입니다")
    elif phase == "unreadable":
        why.append("스나이퍼 일시중지 상태를 읽지 못했습니다 (안전하게 자동 업뎃 보류)")
    dirty = u.sniper_dirty_files()
    if dirty:
        why.append("서버 스나이퍼 폴더에 저장 안 된 변경이 있습니다 (임시 수정 등): " + ", ".join(os.path.basename(d) for d in dirty[:4]))
    r = u.sniper_orders_open()
    if r:
        why.append(r.split(" (")[0])   # '스나이퍼(SOXL) 주문이 걸려 있음'
    cfg = [f for f in _g("diff", "--name-only", f"{base}..{head}")[1].splitlines() if CONFIG_FILE_RE.search(os.path.basename(f))]
    if cfg:
        why.append("원작이 설정 관련 파일을 바꿨습니다 (새 설정 항목 가능성 · 수동): " + ", ".join(cfg[:4]))
    return why


def auto_update(u, st, head, key):
    """새 원작 커밋 알림이 간 뒤 호출. 켜져 있고(U_SNIPER_AUTO_UPDATE) 동기화 명령을 쓸 수 있을 때만 동작 (기본값 = plugin_updater CLI).
    조건이 하나라도 안 맞으면 하지 않고 사유와 함께 알림만 보낸다 (다음 확인 때 다시 판정)."""
    if not AUTO_UPDATE or not _sync_cmd_ready(u):
        return
    sl = _slot(st)
    base = _base(sl)
    why = _auto_blockers(u, sl, base, head)
    if why:
        u.say("⏸ <b>자동 업뎃을 하지 않았습니다 (알림만)</b> — 원작 <code>" + head[:7] + "</code>\n" + "\n".join("▫️ " + u.esc(w) for w in why)
              + "\n▫️ 반영하려면 위 알림을 AI 에게 보여 주고 평소처럼 진행해 주세요.")
        return
    sl["auto_day"] = _today()   # 시도한 날로 센다 (성공·실패 모두 · 하루 최대 1회)
    _auto_run(u, sl, base, head, key)


def _health(u, unit, head, snap, since):
    """적용 뒤 건강 확인 ①~④ → (실패 사유 '' 이면 통과, 통과 항목 메모)"""
    notes = []
    if not u.healthy(unit):                                                   # ① 서비스 active (재시작 직후 안정까지)
        return "① 서비스가 정상 실행되지 않았습니다 (재시작 확인 실패)", notes
    notes.append("① 서비스 실행 중")
    sniper_paths = [p.rstrip("/") for p in u._sniper_prefixes()]               # ② 서버 커밋 = 알림 커밋
    subjects = u.git("log", "-n", "8", "--format=%s", "--", *sniper_paths)[1].splitlines()
    got = next((m.group(1) for m in (re.match(r"^sniper: upstream ([0-9a-f]{7,40}) direct sync$", s.strip()) for s in subjects) if m), "")
    if not got or not head.startswith(got):
        return f"② 서버 스나이퍼 최신 동기화 커밋({got[:7] or '없음'})이 알림 원작 커밋({head[:7]})과 다릅니다", notes
    notes.append("② 서버 커밋 = 알림 커밋")
    if OBS_SECONDS > 0:                                                       # ③ 기동 뒤 오류 로그 없음
        time.sleep(OBS_SECONDS)
    try:
        rc, out = u.sh(JOURNALCTL, "-u", unit, "--since", since, "-p", "err", "-q", "--no-pager")
    except Exception as e:
        rc, out = 127, type(e).__name__
    if rc == 0 and out.strip():
        return "③ 재시작 뒤 오류 로그가 있습니다: " + _scrub(u, out.strip().splitlines()[-1])[:160], notes
    notes.append("③ 오류 로그 없음" if rc == 0 else "③ 오류 로그 확인 불가(미확인)")
    after = _ledger_snapshot(u)                                               # ④ 장부 일치
    for name, (ok, nonempty) in snap.items():
        a = after.get(name)
        if not a or not a[0]:
            return f"④ 장부 파일을 읽을 수 없습니다: {name}", notes
        if nonempty and not a[1]:
            return f"④ 장부가 비어 버렸습니다: {name}", notes
    if RECONCILE_CMD:
        try:
            rc4, out4 = _run(shlex.split(RECONCILE_CMD), timeout=300)
        except ValueError as e:
            rc4, out4 = 1, str(e)
        if rc4:
            return "④ 잔고·장부 일치 확인 실패: " + _scrub(u, out4[-160:]), notes
        notes.append("④ 장부·잔고 일치")
    else:
        notes.append("④ 장부 파일 확인 · 잔고 일치 확인 명령 미설정(미확인)")
    return "", notes


def _revert_sniper_files(u, prev_head, files, subject):
    """files 를 prev_head 때 모습으로 되돌리고 새 커밋 1개로 남김 (장부 파일은 건드리지 않음 · files 밖의 저장 안 된 변경은 안 지움). → (성공, 설명)"""
    files = [f for f in files if not os.path.basename(f).startswith("soxl_stratum_ledger")]
    if not files:
        return True, "되돌릴 변경 없음"
    u._restore_paths(prev_head, files)
    rc, out = u.git("commit", "-qm", subject, "--", *files)
    if rc and "nothing" not in (out or "").lower():
        return False, "되돌림 커밋 실패: " + _scrub(u, (out or "")[-120:])
    return True, f"파일 {len(files)}개를 적용 전 모습으로 되돌림"


def _auto_run(u, sl, base, head, key):
    unit = u.SNIPER_UNIT
    sniper_paths = [p.rstrip("/") for p in u._sniper_prefixes()]
    prev_head = u.git("rev-parse", "HEAD")[1]
    snap, dirty_before = _ledger_snapshot(u), _dirty_names(u)
    was_active = u.sh(u.SYSTEMCTL, "is-active", unit)[1].strip() == "active"
    since = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    u.say(f"🔄 <b>원작 새 커밋 자동 업뎃 시작</b> — <code>{base[:7]}</code> → <code>{head[:7]}</code> (스나이퍼만 · 재시작 포함)")
    fail, notes = "", []
    try:
        rc, out = _run(shlex.split(_sync_cmd(u)), timeout=SYNC_TIMEOUT)   # 실제 CLI: 원작 HEAD 는 CLI 가 'upstream' 리모트에서 직접 읽음 (환경변수로 안 넘김)
    except ValueError as e:
        rc, out = 1, "명령 형식 오류: " + str(e)
    if rc:
        fail = "원작 직접 동기화 실행 실패: " + _scrub(u, out[-200:])
    else:   # 자동 범위: 스나이퍼 폴더 안 변경만. 밖(설정·targets·다른 봇 등)이 바뀌었으면 실패로 보고 되돌림
        pre = u._sniper_prefixes()
        names = set(u.git("diff", "--name-only", prev_head, "HEAD")[1].split()) | (_dirty_names(u) - dirty_before)
        outside = sorted(n for n in names if not n.startswith(pre) and n not in (u.NEED_FILE, u.SNIPER_TIERS_FILE))
        if outside:
            fail = "자동 범위 밖 파일이 바뀌었습니다: " + ", ".join(outside[:4])
    if not fail:
        u.restart_service(unit, was_active)   # 재시작은 언제나 포함 (장 시간 구분 없음)
        fail, notes = _health(u, unit, head, snap, since)
    key12 = head[:12]
    if fail:
        # 동기화가 바꾼 것 전부(커밋 + 작업 폴더 변경)를 적용 전 모습으로. 시작 전부터 있던 저장 안 된 변경·상태 파일은 건드리지 않음
        changed = set(u.git("diff", "--name-only", prev_head)[1].split()) - dirty_before - {u.NEED_FILE, u.SNIPER_TIERS_FILE}
        ok_rb, rb_note = _revert_sniper_files(u, prev_head, sorted(changed), f"sniper: auto-update rollback {head[:7]}")
        u.restart_service(unit, was_active)   # 되돌린 코드로 스나이퍼만 다시 시작
        back_ok = u.healthy(unit)
        sl["auto_failed"][head] = fail[:140]
        sl["auto_last"] = {"head": head, "prev_head": prev_head, "result": "실패·되돌림" if ok_rb else "실패·되돌림 못 함", "when": datetime.now(KST).strftime("%m-%d %H:%M"), "key": key12}
        text = (f"⚠️ <b>자동 업뎃 실패</b> — 원작 <code>{head[:7]}</code>\n▫️ 이유: {u.esc(fail)}\n▫️ 되돌림: {u.esc(rb_note)}"
                f"\n▫️ 스나이퍼: {'이전 코드로 다시 정상 실행 중' if back_ok else '⚠️ 정상 실행 확인 안 됨 — 지금 확인해 주세요'}"
                "\n▫️ 이 원작 커밋은 사람이 풀 때까지 자동 업뎃을 하지 않습니다.")
        u.say(text, [[{"text": "🔓 자동 업뎃 다시 켜기", "callback_data": "ur:" + key12}]])
        if getattr(u, "_hub_alert", None):
            u._hub_alert("2번 토스 스나이퍼", "critical", "자동 업뎃 실패: " + fail[:120])
        return
    post_head = u.git("rev-parse", "HEAD")[1]
    files = sorted(n for n in u.git("diff", "--name-only", prev_head, post_head, "--", *sniper_paths)[1].split())
    sl["prev_base"], sl["base"] = base, head   # 기준 원작을 새 커밋으로 (수동 '반영 완료'와 같은 효과)
    sl["offers"].pop(key, None)
    sl["ignored"] = ""
    sl["auto_last"] = {"head": head, "prev_head": prev_head, "post_head": post_head, "prev_base": base, "files": files, "result": "성공",
                       "when": datetime.now(KST).strftime("%m-%d %H:%M"), "key": key12}
    u.say(f"✅ <b>자동 업뎃 완료</b> — 원작 <code>{head[:7]}</code>\n" + "\n".join("▫️ " + u.esc(n) for n in notes)
          + "\n▫️ 서버 커밋은 서버에만 있습니다 (GitHub 반영은 매일 STATUS 기록 때 빨리감기로)",
          [[{"text": "↩️ 되돌리기 (적용 전 코드로)", "callback_data": "ub:" + key12}]])


def rollback(u, st, key):
    """[↩️ 되돌리기] — 마지막 자동 업뎃이 바꾼 스나이퍼 파일만 적용 전 모습으로 (그 뒤 같은 파일이 또 바뀌었으면 하지 않음)"""
    sl = _slot(st)
    last = sl.get("auto_last") or {}
    if last.get("result") != "성공" or last.get("rolled_back") or key != last.get("key"):
        return u.say("⚠️ 되돌릴 자동 업뎃 기록이 없거나 이미 되돌렸습니다.")
    pre = u._sniper_prefixes()
    paths = [p.rstrip("/") for p in pre]
    later = set(u.git("diff", "--name-only", last["post_head"], "HEAD", "--", *paths)[1].split())
    if later & set(last.get("files", [])):
        return u.say("⚠️ 자동 업뎃 뒤에 같은 파일이 또 바뀌어 자동으로 되돌리지 않았습니다: " + u.esc(", ".join(sorted(later & set(last['files']))[:4])) + "\n▫️ 사람이 확인해 주세요.")
    ok, note = _revert_sniper_files(u, last["prev_head"], last.get("files", []), f"sniper: auto-update rollback (manual) {last['head'][:7]}")
    was_active = u.sh(u.SYSTEMCTL, "is-active", u.SNIPER_UNIT)[1].strip() == "active"
    u.restart_service(u.SNIPER_UNIT, was_active)
    back_ok = u.healthy(u.SNIPER_UNIT)
    if ok:
        sl["base"], sl["prev_base"] = last.get("prev_base") or _base(sl), ""
        sl["auto_failed"][last["head"]] = "수동 되돌림"
        last["rolled_back"] = True
        last["result"] = "수동 되돌림"
    u.say(("↩️ <b>되돌렸습니다</b>" if ok else "⚠️ <b>되돌리지 못했습니다</b>") + f"\n▫️ {u.esc(note)}"
          + f"\n▫️ 스나이퍼: {'이전 코드로 정상 실행 중' if back_ok else '⚠️ 정상 실행 확인 안 됨 — 지금 확인해 주세요'}"
          + ("\n▫️ 이 원작 커밋은 사람이 풀 때까지 자동 업뎃을 하지 않습니다." if ok else ""))


def release(u, st, key):
    """자동 업뎃 중단을 풀어 줌 — key 가 'all' 이면 전부, 아니면 그 원작 커밋(앞 12자)만. 다음 확인 때 조건이 맞으면 다시 시도"""
    sl = _slot(st)
    gone = [h for h in list(sl["auto_failed"]) if key == "all" or h.startswith(key)]
    for h in gone:
        sl["auto_failed"].pop(h, None)
    sl["auto_day"] = ""
    u.say("🔓 자동 업뎃 중단을 풀었습니다: " + (", ".join("<code>" + h[:7] + "</code>" for h in gone) if gone else "풀 항목 없음")
          + "\n▫️ 다음 원작 확인 때 조건이 맞으면 다시 시도합니다.")
