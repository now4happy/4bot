#!/usr/bin/env python3
# 2번 스나이퍼 봇이 켜지기 직전에 실행 (systemd ExecStartPre)
# 원작자 업데이트로 추가 매수 기능이 지워졌으면 저장해 둔 패치로 자동 복구 → 문법 검사 → GitHub 업로드
import json, os, pwd, subprocess, sys, urllib.parse, urllib.request

REPO = os.environ.get("KEEP_REPO", "/home/gieokkim")
PATCH = os.environ.get("KEEP_PATCH", "/opt/bot-office/patches/sniper_add_buy.diff")
MARK = "execute_premarket_rsi_add_buy_plugin"
FILES = ["main.py", "sniper_plugin.py", "quant_engine.py", "tg_router.py", "tg_ui_plugin.py"]
SN = os.path.join(REPO, "toss_sniper")
OWNER = pwd.getpwuid(os.stat(REPO).st_uid)


def git(*args, timeout=60):
    cmd = ["env", f"HOME={OWNER.pw_dir}", "GIT_TERMINAL_PROMPT=0", "git", "-C", REPO, *args]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"


def tg(text):
    env = {}
    try:
        for line in open(os.path.join(SN, ".env"), encoding="utf-8"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
        data = urllib.parse.urlencode({"chat_id": env["TELEGRAM_CHAT_ID"], "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/sendMessage", data=data, timeout=10)
    except Exception as e:
        print("텔레그램 알림 실패:", type(e).__name__)


def undo():
    git("reset", "-q", "--", "toss_sniper")
    git("checkout", "--", "toss_sniper")


def main():
    try:
        if MARK in open(os.path.join(SN, "sniper_plugin.py"), encoding="utf-8").read():
            print("추가 매수 기능 있음 · 할 일 없음")
            return
    except OSError as e:
        print("스나이퍼 파일을 읽지 못함:", e)
        return
    if not os.path.exists(PATCH):
        tg("⚠️ [스나이퍼] 추가 매수 기능이 빠져 있는데 복구용 패치 파일이 없습니다. 원작자 기본 동작(1회 매수)으로 시작합니다.")
        return
    rc, out = git("status", "--porcelain", "toss_sniper")
    if out:
        tg("⚠️ [스나이퍼] 추가 매수 기능이 빠져 있지만, 저장 안 된 다른 변경이 있어 자동 복구를 건너뜁니다. 원작자 기본 동작으로 시작합니다.")
        return
    rc, out = git("apply", "--check", PATCH)
    if rc == 0:
        rc, out = git("apply", PATCH)
    else:
        rc, out = git("apply", "--3way", PATCH)   # 원작자가 근처 코드를 바꿨으면 3-way 병합 시도
    if rc != 0:
        undo()
        tg("⚠️ [스나이퍼] 원작자 업데이트로 코드가 많이 바뀌어 추가 매수 기능을 자동으로 다시 넣지 못했습니다.\n"
           "봇은 원작자 기본 동작(1회 매수)으로 시작합니다. Claude에게 '추가 매수 기능 다시 맞춰줘'라고 요청하세요.")
        print("패치 적용 실패:", out[-300:])
        return
    bad = []
    for f in FILES:
        p = os.path.join(SN, f)
        if os.path.exists(p) and subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True).returncode:
            bad.append(f)
    if bad or MARK not in open(os.path.join(SN, "sniper_plugin.py"), encoding="utf-8").read():
        undo()
        tg(f"⚠️ [스나이퍼] 추가 매수 기능을 다시 넣었지만 문법 검사에 실패해 되돌렸습니다 ({', '.join(bad) or '표시 없음'}).\n"
           "봇은 원작자 기본 동작(1회 매수)으로 시작합니다.")
        return
    git("add", "--", "toss_sniper")
    rc, out = git("commit", "-q", "-m", "auto: 원작자 업데이트 후 스나이퍼 추가 매수 기능 자동 복구")
    if rc != 0:
        undo()
        tg("⚠️ [스나이퍼] 추가 매수 기능 복구 커밋에 실패해 되돌렸습니다. 원작자 기본 동작으로 시작합니다.")
        print(out[-300:])
        return
    rc, out = git("push", "origin", "HEAD:main", timeout=60)
    if rc == 0:
        tg("♻️ [스나이퍼] 원작자 업데이트 감지 → 추가 매수 기능 자동 복구 + GitHub 업로드 완료.\n"
           "원작자 변경과 함께 잘 동작하는지 /settlement 화면에서 한 번 확인해 주세요.")
    else:
        tg("♻️ [스나이퍼] 추가 매수 기능은 자동 복구했지만 GitHub 업로드에 실패했습니다.\n"
           "다음 자동 업데이트 때 다시 지워지면 또 자동 복구됩니다. 서버에서 'git -C /home/gieokkim push origin main'을 한 번 실행해 주세요.")
    print("복구 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # 어떤 경우에도 봇 시작을 막지 않음
        print("자동 복구 중 오류:", e)
