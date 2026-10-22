#!/usr/bin/env python3
# 사무실 V2 설치: 1~4번 봇 결재 · 텔레그램 말 요청/승인 버튼 · 여러 파일 수정 · Claude 수정 등록
#   설치:  sudo python3 install_v2.py <압축 푼 폴더>
#   되돌리기: sudo python3 /opt/bot-office/install_v2.py --rollback
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

OPT = Path("/opt/bot-office")
DEPLOY = Path("/var/lib/bot-office-deploy")
FILES = ["office_package.py", "office_pipeline.py", "apply_deploy.py", "office_secretary.py", "office_submit.py", "office_pipeline_api.py"]
UNITS = [("han4384tubot.service", "1번 한투 라오어"), ("toss_sniper.service", "2번 토스 스나이퍼"),
         ("toss_dca.service", "3번 토스 적립"), ("bithumb_bot.service", "4번 빗썸 적립")]
SECRETARY_UNIT = """[Unit]
Description=Bot office secretary (Telegram chat & approvals)
After=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/bot-office/office_secretary.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""


def sh(*a, check=False):
    return subprocess.run(list(a), capture_output=True, text=True, check=check)


def show(unit, prop):
    return sh("systemctl", "show", unit, "-p", prop, "--value").stdout.strip()


def rollback():
    backs = sorted(OPT.glob("backup_v2_*"))
    if not backs:
        raise SystemExit("🛑 되돌릴 백업이 없습니다")
    b = backs[-1]
    sh("systemctl", "disable", "--now", "bot-office-secretary.service")
    for f in FILES:
        if (b / f).exists():
            shutil.copy2(b / f, OPT / f)
        elif (OPT / f).exists() and f in ("office_package.py", "office_secretary.py", "office_submit.py"):
            (OPT / f).unlink()
    for name in ("targets.json", "tested-helper.sha256"):
        if (b / name).exists():
            shutil.copy2(b / name, DEPLOY / name)
    sh("systemctl", "restart", "bot-office.service")
    print("✅ 이전 상태로 되돌렸습니다 ·", b.name)


def main():
    if os.geteuid() != 0:
        raise SystemExit("🛑 sudo 로 실행해 주세요")
    if "--rollback" in sys.argv:
        return rollback()
    src = Path(sys.argv[1])
    for f in FILES:
        if not (src / f).is_file():
            raise SystemExit(f"🛑 설치 파일 누락: {f}")
        compile((src / f).read_bytes(), f, "exec")
    if not (OPT / "office_pipeline.py").exists() or not (DEPLOY / "targets.json").exists():
        raise SystemExit("🛑 기존 사무실 업무 흐름(V1)이 설치되어 있지 않습니다")
    print("1) 백업")
    b = OPT / time.strftime("backup_v2_%Y%m%d_%H%M%S")
    b.mkdir(mode=0o700)
    for f in FILES:
        if (OPT / f).exists():
            shutil.copy2(OPT / f, b / f)
    for name in ("targets.json", "tested-helper.sha256"):
        if (DEPLOY / name).exists():
            shutil.copy2(DEPLOY / name, b / name)
    print("   →", b)

    print("2) 프로그램 설치")
    for f in FILES:
        dst = OPT / f
        mode, uid, gid = 0o644, 0, 0
        if dst.exists():
            st = dst.stat(); mode, uid, gid = st.st_mode & 0o777, st.st_uid, st.st_gid
        elif f in ("office_secretary.py", "office_submit.py", "office_package.py"):
            mode = 0o750
        shutil.copyfile(src / f, dst)
        os.chown(dst, uid, gid); os.chmod(dst, mode)
        print("   ✓", f)
    shutil.copyfile(Path(__file__), OPT / "install_v2.py"); os.chmod(OPT / "install_v2.py", 0o750)
    # 적용 담당(apply_deploy)이 바뀌었으므로 검증 지문 갱신 (deploy_worker 는 이 지문이 맞을 때만 실행)
    (DEPLOY / "tested-helper.sha256").write_text(hashlib.sha256((OPT / "apply_deploy.py").read_bytes()).hexdigest() + "\n")
    os.chmod(DEPLOY / "tested-helper.sha256", 0o600)

    print("3) 결재 대상 봇 등록 (1~4번)")
    cfg = json.loads((DEPLOY / "targets.json").read_text())
    tg = cfg.setdefault("targets", {})
    for unit, name in UNITS:
        wd, user, active = show(unit, "WorkingDirectory"), show(unit, "User"), sh("systemctl", "is-active", unit).stdout.strip()
        if unit not in tg:
            if not wd or not Path(wd).is_dir():
                print(f"   ⚠️ {name}: 작업 폴더(WorkingDirectory)가 없어 등록하지 못함"); continue
            files = sorted(p.name for p in Path(wd).glob("*.py")
                           if p.is_file() and not p.is_symlink() and not p.name.startswith(("bot_office_", "test_")))
            tg[unit] = {"root": wd, "files": files}
            print(f"   + {name}: {wd} · 파이썬 파일 {len(files)}개 등록")
        else:
            print(f"   = {name}: 기존 등록 유지 ({tg[unit]['root']} · {len(tg[unit]['files'])}개)")
        warn = []
        if user in ("", "root", "0"):
            warn.append("root 로 실행 → 자동 적용 안전장치 때문에 적용 거부됨")
        if wd != tg[unit]["root"]:
            warn.append(f"작업 폴더 불일치({wd})")
        if active != "active":
            warn.append(f"현재 상태 {active}")
        if warn:
            print("     ⚠️ " + " / ".join(warn))
    tmp = DEPLOY / "targets.json.tmp"
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2)); os.chmod(tmp, 0o600)
    os.replace(tmp, DEPLOY / "targets.json")

    print("4) 텔레그램 대화 담당(사무실 비서) 시작")
    Path("/etc/systemd/system/bot-office-secretary.service").write_text(SECRETARY_UNIT)
    sh("systemctl", "daemon-reload")
    sh("systemctl", "enable", "--now", "bot-office-secretary.service")
    sh("systemctl", "restart", "bot-office-secretary.service")
    print("5) 사무실 웹 다시 시작 (새 기능 반영)")
    sh("systemctl", "restart", "bot-office.service")
    time.sleep(3)
    sh("systemctl", "start", "bot-office-pipeline.service")
    states = {u: sh("systemctl", "is-active", u).stdout.strip() for u in ("bot-office-secretary.service", "bot-office.service")}
    print("   상태:", states)
    sys.path.insert(0, str(OPT))
    try:
        import office_pipeline as P
        P.notify("🏢 <b>[사무실 비서] 이제 대화로 일할 수 있어요</b>\n"
                 "▫️ 고칠 내용을 평소 말투로 보내면 어느 봇인지 확인하고 접수합니다. (1~4번 봇 모두)\n"
                 "▫️ 결재 요청에는 <b>✅ 승인 / ❌ 반려 / 🔍 바뀐 코드 보기</b> 버튼이 붙어요.\n"
                 "▫️ <b>도움말</b>, <b>브리핑</b>, <b>현황</b> 이라고 보내 보세요.", button=False)
    except Exception as e:
        print("   (안내 메시지 전송 실패:", e, ")")
    if all(v == "active" for v in states.values()):
        print("✅ 사무실 V2 설치 완료")
    else:
        print("⚠️ 설치는 끝났지만 서비스 상태 확인이 필요합니다. 이 화면을 보내주세요.")


if __name__ == "__main__":
    main()
