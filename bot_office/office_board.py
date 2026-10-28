#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_board.py   (사무실 vNEXT · 2026-10-28)
#  · 사무실 vNEXT: 신호등에 이름·켜진 시각 · 매매방·미팅룸 제외 · 팬딩룸에 과거 가격표 수·저장 위치 · 서버 정리(bot-server-care) 상태
# 사무실 상황판 데이터 (/api/board · 로그인 필요 · 보기 전용)
#  · 주문·승인·설정 변경 기능 없음 — 웹에서 하는 일은 '서버 정리 실행' 요청 하나뿐 (server.py /api/server-care)
#  · 금액·잔고·수량·계좌·토큰·주소 원문은 넣지 않음 (상태 글자·시각·버전만)
#  · 읽는 곳: systemctl show(서비스 상태) · /var/lib/bot-office/status.md(업데이트 비서가 쓰는 STATUS 복사본)
#            · 팬딩/PC 감시 상태 파일 · office_health.json(바깥 접속 감시) · /proc(메모리·스왑)
#  · 한계: 웹서버 계정은 서버 기록(journal)을 못 읽어 '마지막으로 실제 일한 시각' 대신 '실행 시작 시각'을 보여 줌
# ==========================================================
import json, os, re, shutil, subprocess, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

VERSION = "vNEXT"
R = Path(os.environ.get("OFFICE_ROOT", "/"))
STATUS_COPY = R / "var/lib/bot-office/status.md"
KST = timezone(timedelta(hours=9))

# (방, 번호·이름, 서비스)
SERVICES = [
    ("trade", "1번 한투 라오어", "han4384tubot.service"),
    ("trade", "2번 토스 스나이퍼", "toss_sniper.service"),
    ("trade", "3번 토스 적립", "toss_dca.service"),
    ("trade", "4번 빗썸 적립", "bithumb_bot.service"),
    ("office", "5번 사무실 비서", "bot-office.service"),
    ("office", "5번 팬딩 가격표", "bot-office-fanding.service"),
    ("office", "6번 업데이트 비서", "bot-updater.service"),
    ("office", "7번 비서(브리핑·PC감시)", "bot-office-secretary.service"),
    ("office", "사무실 터널", "bot-office-tunnel.service"),
]
CARE_UNIT, CARE_TIMER, CARE_PATH = "bot-server-care.service", "bot-server-care.timer", "bot-server-care-request.path"
CARE_REQUEST = R / "var/lib/bot-office/care/request"
CARE_GAP = 600                                  # 정리 요청 간격 (초)
PC_STAGES = {"idle": "대기", "connecting": "사이트 접속", "listing": "글 목록 탐색", "images": "이미지 다운로드",
             "uploading": "서버 전송", "parsing": "서버 판독 대기", "history": "과거 자료 수집", "sent": "전송 완료",
             "daily_done": "하루 작업 완료", "daily_stopped": "종료 시각 도달", "logged_out": "로그인 필요",
             "no_posts": "글 목록 없음", "no_image": "이미지 없음", "error": "PC 수집 오류", "server_error": "서버 연결 오류"}
SHEET_STATUS = {"submitted": "주문 접수 완료", "partial": "일부 주문", "submitting": "주문 중"}
_CACHE = {"at": 0.0, "data": None}


def _kst(dt):
    return dt.astimezone(KST).strftime("%m-%d %H:%M") if dt else ""


def _systemd_time(text):
    """'Wed 2026-10-28 02:48:01 UTC' → datetime (UTC 외 표기는 서버 기준이 UTC 라 UTC 로 봄)"""
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text or "")
    return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if m else None


def _show(unit, *props):
    try:
        p = subprocess.run(["systemctl", "show", unit, "--no-pager"] + [x for k in props for x in ("-p", k)],
                           capture_output=True, text=True, timeout=3)
        return dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    except (subprocess.SubprocessError, OSError):
        return {}


def services():
    out = []
    for room, name, unit in SERVICES:
        f = _show(unit, "LoadState", "ActiveState", "SubState", "ActiveEnterTimestamp", "NRestarts")
        if f.get("LoadState") == "not-found":
            continue
        since = _systemd_time(f.get("ActiveEnterTimestamp"))
        out.append({"room": room, "name": name, "unit": unit.replace(".service", ""),
                    "active": f.get("ActiveState", "unknown"), "sub": f.get("SubState", ""),
                    "since_kst": _kst(since) if f.get("ActiveState") == "active" else "",
                    "restarts": int(f["NRestarts"]) if f.get("NRestarts", "").isdigit() else None})
    return out


def status_md():
    """STATUS 복사본 → 버전·마지막 적용·최근 적용·대기 업로드 (없으면 빈 값)"""
    try:
        text = STATUS_COPY.read_text(encoding="utf-8")
    except OSError:
        return {"ok": False}
    rows, recent, pending, sec = {}, [], [], ""
    for line in text.splitlines():
        if line.startswith("## "):
            sec = line[3:]
            continue
        if line.startswith("- 갱신:"):
            rows["_updated"] = line[len("- 갱신:"):].strip()
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) >= 6 and cells[1].startswith("`"):
            rows[cells[1].strip("`")] = {"version": cells[3], "applied": cells[4], "what": cells[5][:80]}
        elif sec.startswith("최근 적용") and line.startswith("- "):
            recent.append(line[2:][:160])
        elif sec.startswith("대기 중인 업로드") and line.startswith("- ") and line.strip() != "- 없음":
            pending.append(line[2:][:160])
    return {"ok": True, "updated": rows.pop("_updated", ""), "bots": rows, "recent": recent[:10], "pending": pending}


def fanding():
    try:
        import fanding_trade as ft
        expected = ft.last_session_date().isoformat()
        sheet = (ft.load(ft.STATE, {}).get("sheets") or {}).get(expected) or {}
        pc = (ft.load(ft.BRIDGE, {}).get("pc")) or {}
        age = int(time.time() - pc["at"]) if pc.get("at") else None
        status = str(sheet.get("status") or "")
        past = {"count": int(ft.load(ft.STATE, {}).get("past_count", 0) or 0), "folder": str(ft.HISTORY.parent),
                "file": ft.HISTORY.name, "dates": None, "latest": "", "size_kb": None, "readable": True}
        try:
            dates = set()
            with open(ft.HISTORY, encoding="utf-8") as fh:
                for line in fh:
                    if '"past_sheet"' in line:
                        d = re.search(r'"date":\s*"(\d{4}-\d{2}-\d{2})"', line)
                        if d:
                            dates.add(d.group(1))
            past.update(dates=len(dates), latest=max(dates) if dates else "", size_kb=round(ft.HISTORY.stat().st_size / 1024))
        except FileNotFoundError:
            past.update(dates=0)
        except OSError:
            past["readable"] = False
        return {"past": past, "ok": True, "expected": expected, "have_sheet": bool(sheet), "ready": ft.sheet_ready(sheet),
                "status": SHEET_STATUS.get(status, status or "미확보"),
                "pc_age_min": age // 60 if age is not None else None,
                "pc_stage": PC_STAGES.get(pc.get("stage"), "미확인"), "pc_version": str(pc.get("version") or "")[:20]}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


def pc_watch():
    try:
        import pc_monitor as pm
        now = datetime.now(pm.KST)
        cur = pm.load(pm.STATE, {}); pc = cur.get("pc") or {}; c = pm.config()
        active, _, _ = pm.schedule(now, c)
        age = int(now.timestamp() - pc["at"]) if pc.get("at") else None
        return {"ok": True, "watching": active, "hours": f"평일 {c['start']}~{c['end']}",
                "age_min": age // 60 if age is not None else None,
                "magic": {"running": "실행 중", "stopped": "미실행"}.get(pc.get("magic_status"), "미확인")}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


def office_health():
    try:
        import office_url
        h = office_url.health_state()
        return {"ok": True, "mode": "고정 도메인" if office_url.mode() == "fixed" else "임시 터널",
                "checked_kst": h.get("checked_kst", "")[5:16].replace("T", " "),
                "healthy": h.get("ok"), "inside": h.get("inside"), "outside": h.get("outside"),
                "fails": h.get("fails", 0), "last_ok_kst": h.get("last_ok_kst", "")[5:16].replace("T", " ")}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


def care():
    """서버 정리(bot-server-care): 마지막 실행·결과·다음 자동 실행·버튼 사용 가능 여부"""
    d = _show(CARE_UNIT, "LoadState", "ActiveState", "Result", "ExecMainStatus", "ExecMainStartTimestamp", "ExecMainExitTimestamp")
    if d.get("LoadState") in (None, "not-found"):
        return {"ok": False, "installed": False}
    t = _show(CARE_TIMER, "NextElapseUSecRealtime")
    btn = _show(CARE_PATH, "ActiveState").get("ActiveState") == "active"
    started = _systemd_time(d.get("ExecMainStartTimestamp"))
    if d.get("ActiveState") == "activating":
        state = "running"
    elif not started:
        state = "never"
    else:
        state = "ok" if d.get("Result") == "success" and d.get("ExecMainStatus") == "0" else "failed"
    try:
        wait = max(0, int(CARE_GAP - (time.time() - CARE_REQUEST.stat().st_mtime)))
    except OSError:
        wait = 0
    return {"ok": True, "installed": True, "state": state, "last_kst": _kst(started),
            "next_kst": _kst(_systemd_time(t.get("NextElapseUSecRealtime"))), "button": btn, "wait_sec": wait}


def server():
    mem = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            mem[k] = int(v.split()[0]) * 1024
    except (OSError, ValueError):
        pass
    d = shutil.disk_usage("/")
    pct = lambda used, total: round(used * 100 / total) if total else None
    out = {"disk_pct": pct(d.used, d.total), "disk_free_gb": round(d.free / 1e9, 1),
           "mem_pct": pct(mem.get("MemTotal", 0) - mem.get("MemAvailable", 0), mem.get("MemTotal", 0)),
           "mem_total_mb": mem.get("MemTotal", 0) // 1048576,
           "swap_pct": pct(mem.get("SwapTotal", 0) - mem.get("SwapFree", 0), mem.get("SwapTotal", 0)),
           "load_1m": round(os.getloadavg()[0], 2)}
    why = []   # 정리를 권할 만큼 나쁜 이유
    if (out["disk_pct"] or 0) >= 80: why.append(f"디스크 {out['disk_pct']}%")
    if (out["mem_pct"] or 0) >= 85: why.append(f"메모리 {out['mem_pct']}%")
    if (out["swap_pct"] or 0) >= 50: why.append(f"스왑 {out['swap_pct']}%")
    out["bad"] = why
    return out


def todo(svc, st, fd, pcw, hl, sv, cr=None):
    """오늘 할 일: (bad|warn|ok, 글자)"""
    t = []
    for s in svc:
        if s["active"] != "active":
            t.append(("bad", f"{s['name']} 멈춤 ({s['active']}) — 6. Update 상태 확인 또는 SSH 로 재시작"))
    for p in st.get("pending", []):
        t.append(("warn", "6. Update 승인 대기: " + p))
    if hl.get("ok") and hl.get("healthy") is False:
        t.append(("bad", f"사무실 바깥 접속 실패 {hl.get('fails')}회째 — 7번 비서 알림의 명령 실행"))
    if fd.get("ok"):
        if fd["ready"]:
            t.append(("ok", f"팬딩 가격표 {fd['expected']} 종가분: {fd['status'] if fd['have_sheet'] else '확보'}"))
        else:
            t.append(("warn", f"팬딩 가격표 {fd['expected']} 종가분: {fd['status']} — 팬딩 봇 /진단"))
    if pcw.get("ok") and pcw["watching"] and (pcw["age_min"] is None or pcw["age_min"] >= 10):
        t.append(("warn", "하남 컴 연결 " + ("기록 없음" if pcw["age_min"] is None else f"{pcw['age_min']}분째 없음") + " — 전원·감시 프로그램 확인"))
    if sv.get("bad"):
        t.append(("warn", "서버 상태 나쁨 (" + ", ".join(sv["bad"]) + ") — 서버실 '서버 정리 실행'"))
    if cr and cr.get("ok") and cr.get("state") == "failed":
        t.append(("bad", f"서버 정리 최근 실행 실패 ({cr.get('last_kst')} KST) — SSH 로 확인 필요"))
    if not st.get("ok"):
        t.append(("warn", "STATUS 복사본 없음 — 다음 업데이트 적용(또는 매일 06:10 KST) 뒤 표시"))
    return [{"level": a, "text": b} for a, b in t]


def board():
    if _CACHE["data"] and time.monotonic() - _CACHE["at"] < 15:
        return _CACHE["data"]
    svc, st, fd, pcw, hl, sv, cr = services(), status_md(), fanding(), pc_watch(), office_health(), server(), care()
    for s in svc:
        b = (st.get("bots") or {}).get(s["unit"]) or {}
        s["version"], s["applied"], s["what"] = b.get("version", ""), b.get("applied", ""), b.get("what", "")
    data = {"version": VERSION, "observed_kst": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
            "read_only": True, "services": svc, "todo": todo(svc, st, fd, pcw, hl, sv, cr), "care": cr,
            "status_updated": st.get("updated", ""), "recent": st.get("recent", []), "pending": st.get("pending", []),
            "fanding": fd, "pc": pcw, "health": hl, "server": sv}
    _CACHE.update(at=time.monotonic(), data=data)
    return data


if __name__ == "__main__":
    print(json.dumps(board(), ensure_ascii=False, indent=1))
