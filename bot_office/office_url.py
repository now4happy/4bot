#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_url.py   (사무실 v1.0.48 · 2026-10-28)
# 사무실 주소(office_url) 한 곳 관리 — 지금은 임시 터널 주소(trycloudflare), 나중에 고정 도메인으로 쉽게 이동
#
#  · 서버 파일 /etc/bot-office/office_url 이 '사무실 주소'의 기준 (브리핑·비서·팬딩 안내가 이 값을 씀)
#  · 임시 터널 모드: 7번 비서가 5분마다 터널 기록에서 현재 주소를 찾아, 바뀌었으면
#      ① 서버 파일을 새 주소로 고치고 ② 텔레그램으로 새 주소 + 한국 PC 주소 바꾸는 PowerShell 한 줄을 보냄
#  · 고정 도메인 모드: /주소변경 https://office.내도메인.com → 그 주소로 고정 (터널 기록으로 덮어쓰지 않음)
#      → 한국 PC 에 붙여넣을 한 줄도 함께 보냄. 다시 임시 주소로: /주소변경 자동
#  · 명령(7번 비서): /주소 (지금 주소·PC 명령) · /주소변경 <주소|자동> · /도메인안내 (고정 도메인 이동 순서)
# ==========================================================
import json, os, re, subprocess, time
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
URL_FILE = R / "etc/bot-office/office_url"
MODE_FILE = R / "etc/bot-office/office_url.mode"        # 내용 'fixed' 면 고정 도메인 (없으면 자동=임시 터널 추적)
TUNNEL_UNIT = "bot-office-tunnel.service"
QUICK_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
CHECK_EVERY = 300
_LAST = {"at": 0.0}


def current():
    try:
        return URL_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def mode():
    try:
        return "fixed" if MODE_FILE.read_text(encoding="utf-8").strip() == "fixed" else "auto"
    except OSError:
        return "auto"


def _write(path, text):
    """원자적 저장 · 이미 있던 파일의 주인·권한 유지 (웹서버 등 다른 계정이 계속 읽을 수 있게)"""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = path.stat(); own, perm = (st.st_uid, st.st_gid), st.st_mode & 0o777
    except FileNotFoundError:
        own, perm = None, 0o644
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.chmod(tmp, perm)
    if own:
        try:
            os.chown(tmp, *own)
        except PermissionError:
            pass
    os.replace(tmp, path)


def tunnel_url():
    """임시 터널(cloudflared --url) 기록에서 가장 최근 trycloudflare 주소. 못 찾으면 ''"""
    try:   # 지금 켜져 있는 터널 실행분의 기록만 (예전 실행의 주소와 섞이지 않게)
        inv = subprocess.run(["systemctl", "show", TUNNEL_UNIT, "-p", "InvocationID", "--value"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        cmd = ["journalctl", "-o", "cat", "--no-pager"] + ([f"_SYSTEMD_INVOCATION_ID={inv}"] if inv else ["-u", TUNNEL_UNIT, "-n", "5000"])
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""
    found = QUICK_RE.findall(out)
    return found[-1] if found else ""


def pc_command(url):
    """한국 Windows PC 의 C:\\fanding\\config.json 주소만 바꾸는 PowerShell 한 줄 (BOM 없는 UTF-8 로 저장)"""
    return ("$f='C:\\fanding\\config.json'; $c=Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json; "
            f"$c.office_url='{url}'; [IO.File]::WriteAllText($f, ($c | ConvertTo-Json -Depth 5), "
            "(New-Object Text.UTF8Encoding $false)); Write-Host '✅ PC 사무실 주소 변경 완료'")


def _notice(url, head):
    import html
    return (f"{head}\n<code>{html.escape(url)}</code>\n\n"
            "🖥 <b>한국 PC</b> 원격 접속 → PowerShell 에 아래 한 줄을 붙여넣으세요 (팬딩 수집기·PC 감시가 새 주소로 연결):\n"
            f"<code>{html.escape(pc_command(url))}</code>\n"
            "▫️ 붙여넣은 뒤 1~2분 안에 /진단 · 📊 조회 → 🖥 PC 상태 에서 연결 확인")


def tick(tg, now=None):
    """7번 비서 루프에서 호출. 5분마다 임시 터널 주소 변경 확인 → 바뀌었으면 서버 파일 갱신 + 알림"""
    now = now or time.time()
    if now - _LAST["at"] < CHECK_EVERY:
        return None
    _LAST["at"] = now
    if mode() == "fixed":
        return None
    new = tunnel_url()
    if not new or new == current():
        return None
    old = current()
    _write(URL_FILE, new + "\n")
    tg.send(_notice(new, "🔗 <b>사무실 주소가 바뀌었어요</b> (임시 터널이 다시 켜짐)"
                    + (f"\n이전: <code>{old}</code>" if old else "")))
    return new


GUIDE = ("🧭 <b>고정 도메인으로 옮기는 순서</b> (도메인을 산 뒤 · 총 15분)\n"
         "1) Cloudflare 가입 → 도메인 구입(또는 연결)\n"
         "2) Cloudflare 화면 <b>Zero Trust → Networks → Tunnels → Create a tunnel</b> → 이름 <code>bot-office</code>\n"
         "3) 설치 명령 화면에서 <b>토큰</b>(eyJ… 로 시작하는 긴 글자)만 복사 — 토큰은 채팅에 붙여넣지 마세요\n"
         "4) <b>Public Hostname</b> 추가: 하위 이름 <code>office</code> · 도메인 선택 · 서비스 <code>HTTP</code> · <code>127.0.0.1:8765</code>\n"
         "5) Claude 에게 '고정 터널 전환 명령' 요청 → 서버에 한 번 붙여넣기 (터널 서비스를 토큰 방식으로 바꿈)\n"
         "6) 여기서 <code>/주소변경 https://office.내도메인.com</code> → 오는 한 줄을 한국 PC PowerShell 에 붙여넣기\n"
         "▫️ 되돌리기: <code>/주소변경 자동</code> + 서버 터널을 예전 명령으로")


def handle_text(tg, text):
    """/주소 · /주소변경 처리. 처리했으면 True"""
    t = text.strip()
    if t in ("/주소", "주소", "/office_url"):
        url = current() or "(아직 없음)"
        tg.send(_notice(url, f"🔗 <b>지금 사무실 주소</b> · 모드: {'고정 도메인' if mode() == 'fixed' else '임시 터널 자동 추적'}")
                + "\n\n▫️ 고정 도메인 이동 순서: /도메인안내\n▫️ 옮긴 뒤: <code>/주소변경 https://office.내도메인.com</code> · 다시 자동: <code>/주소변경 자동</code>")
        return True
    if t in ("/도메인안내", "도메인안내"):
        tg.send(GUIDE)
        return True
    m = re.fullmatch(r"/주소변경\s+(\S+)", t)
    if not m:
        return False
    arg = m.group(1).strip()
    if arg in ("자동", "auto"):
        _write(MODE_FILE, "auto\n")
        _LAST["at"] = 0
        tg.send("🔁 사무실 주소를 다시 <b>임시 터널 자동 추적</b>으로 바꿨어요. 5분 안에 터널 주소를 확인해 알려 드려요.")
        return True
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+(:\d+)?/?", arg):
        tg.send("주소는 <code>https://office.내도메인.com</code> 처럼 https 로 시작하는 주소만 받아요.")
        return True
    url = arg.rstrip("/")
    _write(URL_FILE, url + "\n")
    _write(MODE_FILE, "fixed\n")
    tg.send(_notice(url, "📌 <b>사무실 주소를 고정 도메인으로 바꿨어요</b>")
            + "\n\n⚠️ 서버 터널이 이 도메인으로 연결돼 있어야 해요. 순서는 /도메인안내")
    return True
