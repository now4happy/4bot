#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_url.py   (사무실 v1.0.55 · 2026-10-28)
# 사무실 주소(office_url) 한 곳 관리 — 지금은 임시 터널 주소(trycloudflare), 나중에 고정 도메인으로 쉽게 이동
#
#  · 서버 파일 /etc/bot-office/office_url 이 '사무실 주소'의 기준 (브리핑·비서·팬딩 안내가 이 값을 씀)
#  · 임시 터널 모드: 7번 비서가 5분마다 터널 기록에서 현재 주소를 찾아, 바뀌었으면
#      ① 서버 파일을 새 주소로 고치고 ② 텔레그램으로 새 주소 + 한국 PC 주소 바꾸는 PowerShell 한 줄을 보냄
#  · 고정 도메인 모드: /주소변경 https://office.내도메인.com → 그 주소로 고정 (터널 기록으로 덮어쓰지 않음)
#      → 한국 PC 에 붙여넣을 한 줄도 함께 보냄. 다시 임시 주소로: /주소변경 자동
#  · 사무실 v1.0.55: ① 터널 주소를 터널 프로그램(cloudflared 내부 창구 /quicktunnel)에 먼저 물어봄
#                     (오래 켜진 터널은 처음 찍힌 주소 줄이 기록에서 밀려나 못 찾던 문제 · 기록은 보조)
#                   ② 바깥 접속 감시: 5분마다 사무실 내부(127.0.0.1:8765/healthz)와 바깥 주소(/login)를 열어 봄
#                     2번 연속 실패하면 7번 비서로 원인(사무실 서버 / 터널)과 할 일을 1번 알림, 되살아나면 복구 알림 1번
#                     결과는 /var/lib/bot-office/office_health.json (상황판이 읽음) · 한 줄 JSON 기록은 상태가 바뀔 때만
#  · 명령(7번 비서): /주소 (지금 주소·PC 명령) · /주소변경 <주소|자동> · /도메인안내 (고정 도메인 이동 순서)
# ==========================================================
import json, os, re, subprocess, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
URL_FILE = R / "etc/bot-office/office_url"
MODE_FILE = R / "etc/bot-office/office_url.mode"        # 내용 'fixed' 면 고정 도메인 (없으면 자동=임시 터널 추적)
TUNNEL_UNIT = "bot-office-tunnel.service"
QUICK_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
CHECK_EVERY = 300
_LAST = {"at": 0.0}
HEALTH_FILE = R / "var/lib/bot-office/office_health.json"
INSIDE_URL = "http://127.0.0.1:8765/healthz"
METRICS_PORTS = range(20241, 20246)          # cloudflared 내부 창구 기본 포트 (127.0.0.1 만)
FAIL_ALERT = 2                               # 연속 실패 몇 번째에 알릴지 (5분 × 2 = 약 10분)
VERSION = "v1.0.55"
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 서버 안 주소는 프록시 없이


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


def _quicktunnel():
    """cloudflared 내부 창구(127.0.0.1:2024x/quicktunnel)가 알려 주는 임시 터널 주소. 못 찾으면 ''"""
    for port in METRICS_PORTS:
        try:
            with _DIRECT.open(f"http://127.0.0.1:{port}/quicktunnel", timeout=3) as r:
                host = (json.loads(r.read().decode("utf-8", "replace")) or {}).get("hostname") or ""
        except Exception:
            continue
        if re.fullmatch(r"[a-z0-9-]+\.trycloudflare\.com", host):
            return "https://" + host
    return ""


def _journal_url():
    try:   # 지금 켜져 있는 터널 실행분의 기록만 (예전 실행의 주소와 섞이지 않게)
        inv = subprocess.run(["systemctl", "show", TUNNEL_UNIT, "-p", "InvocationID", "--value"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        cmd = ["journalctl", "-o", "cat", "--no-pager"] + ([f"_SYSTEMD_INVOCATION_ID={inv}"] if inv else ["-u", TUNNEL_UNIT, "-n", "5000"])
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""
    found = QUICK_RE.findall(out)
    return found[-1] if found else ""


def tunnel_url():
    """임시 터널 현재 주소: 터널 프로그램에 먼저 묻고, 안 되면 터널 기록에서. 못 찾으면 ''"""
    return _quicktunnel() or _journal_url()


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


def _times(now):
    u = datetime.fromtimestamp(now, timezone.utc)
    return u.isoformat(timespec="seconds"), u.astimezone(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def _log(now, event_type, event, outcome, reason="", **extra):
    """start.md 2절 형식 한 줄 JSON (주소·비밀값·식별자는 넣지 않음)"""
    ts_utc, ts_kst = _times(now)
    rec = {"ts_utc": ts_utc, "ts_kst": ts_kst, "correlation_id": f"office-health-{int(now // CHECK_EVERY)}",
           "service": "office-health", "actor": "scheduler", "event_type": event_type, "event": event,
           "outcome": outcome, "reason": reason, "version": VERSION, **extra}
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def _probe(url, timeout):
    """HTTP 상태 코드 (연결 자체가 안 되면 0) · 3xx 는 따라가지 않고 그대로"""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}) if url.startswith("http://127.") else urllib.request.ProxyHandler())
    try:
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "bot-office-health"}), timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def health_state():
    try:
        return json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def health_check(tg, now):
    """사무실 내부·바깥 주소를 열어 보고 연속 실패·복구를 알림. 결과 dict"""
    url = current()
    inside = _probe(INSIDE_URL, 5)
    outside = _probe(url + "/login", 15) if url else 0
    ok = inside == 200 and outside == 200
    prev = health_state()
    fails = 0 if ok else int(prev.get("fails", 0)) + 1
    alerted = bool(prev.get("alerted"))
    cause = ("" if ok else "inside_down" if inside != 200 else "no_url" if not url else "tunnel_down")
    ts_utc, ts_kst = _times(now)
    st = {"checked_utc": ts_utc, "checked_kst": ts_kst, "inside": inside, "outside": outside, "ok": ok,
          "fails": fails, "cause": cause, "alerted": alerted, "mode": mode(), "version": VERSION,
          "last_ok_utc": ts_utc if ok else prev.get("last_ok_utc", ""),
          "last_ok_kst": ts_kst if ok else prev.get("last_ok_kst", "")}
    if prev.get("ok", True) != ok or prev.get("cause", "") != cause:
        _log(now, "decision", "office_health_changed", "ok" if ok else "failed", cause, inside=inside, outside=outside, fails=fails)
    msg = None
    if not ok and fails >= FAIL_ALERT and not alerted:
        what = {"inside_down": ("사무실 서버(bot-office)가 응답하지 않아요.",
                                "<code>sudo systemctl restart bot-office</code>"),
                "no_url": ("저장된 사무실 주소가 없어요.", "7번 비서에 /주소 → 안 나오면 터널 재시작"),
                "tunnel_down": ("사무실 서버는 정상인데 바깥 주소(임시 터널)가 끊겼어요.",
                                "<code>sudo systemctl restart bot-office-tunnel</code>\n▫️ 재시작하면 주소가 바뀌고, 5분 안에 새 주소와 한국 PC 한 줄을 보내 드려요")}[cause]
        msg = (f"🚨 <b>사무실 접속 안 됨</b> (약 {fails * CHECK_EVERY // 60}분째)\n▫️ {what[0]}\n"
               f"▫️ 확인 결과: 내부 {inside or '응답없음'} · 바깥 {outside or '응답없음'}\n"
               f"▫️ 할 일 (SSH 창에 붙여넣기): {what[1]}\n▫️ 매매 봇은 사무실과 따로 돌아가므로 영향 없음")
        st["alerted"] = True
    elif ok and alerted:
        msg = f"✅ <b>사무실 접속 복구</b> · 내부 {inside} · 바깥 {outside}"
        st["alerted"] = False
    if msg:
        try:
            tg.send(msg)
            _log(now, "user_visible", "office_health_notice", "ok", cause or "recovered")
        except Exception as e:
            st["alerted"] = alerted   # 못 보냈으면 다음 확인 때 다시 시도
            _log(now, "user_visible", "office_health_notice", "failed", type(e).__name__)
    try:
        _write(HEALTH_FILE, json.dumps(st, ensure_ascii=False, indent=1) + "\n")
    except OSError as e:
        _log(now, "state_change", "office_health_save", "failed", type(e).__name__)
    return st


def tick(tg, now=None):
    """7번 비서 루프에서 호출. 5분마다 ① 임시 터널 주소 변경 확인(자동 모드) ② 사무실 바깥 접속 감시"""
    now = now or time.time()
    if now - _LAST["at"] < CHECK_EVERY:
        return None
    _LAST["at"] = now
    new = None
    if mode() != "fixed":
        found = tunnel_url()
        if found and found != current():
            old = current()
            _write(URL_FILE, found + "\n")
            new = found
            _log(now, "state_change", "office_url_changed", "ok", "tunnel_restarted")
            tg.send(_notice(found, "🔗 <b>사무실 주소가 바뀌었어요</b> (임시 터널이 다시 켜짐)"
                            + (f"\n이전: <code>{old}</code>" if old else "")))
    try:
        health_check(tg, now)
    except Exception as e:
        _log(now, "decision", "office_health_check", "failed", type(e).__name__)
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
        h = health_state()
        hl = ("" if not h else f"\n▫️ 마지막 접속 확인: {h.get('checked_kst', '')[11:16]} KST · "
              + ("정상" if h.get("ok") else f"실패 {h.get('fails')}회째 (내부 {h.get('inside')} · 바깥 {h.get('outside')})"))
        tg.send(_notice(url, f"🔗 <b>지금 사무실 주소</b> · 모드: {'고정 도메인' if mode() == 'fixed' else '임시 터널 자동 추적'}{hl}")
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
