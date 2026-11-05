#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/past_sheet_telegram.py   (PAST_SHEET_TELEGRAM_V1.1.0)
# 1.1.0 (사무실 v1.3.1, 2026-11-05): 매일 자동 전송 중단 → 🛠 도구의 [📥 과거자료 다운] 버튼을 눌렀을 때만 send_now() 로 1번
#   · tick() 은 남겨 두지만 아무것도 안 함 (옛 fanding_trade 1.14.2 가 먼저 돌아도 자동 전송 없음)
#   · 5칸 검사 강화: 종가일(YYYY-MM-DD)·종가(>0)·매수/매도({price>0, qty 양의 정수} 목록 1칸씩)·글 주소(글자) 만,
#     다른 칸·깨진 줄이 하나라도 있으면 안 보냄
#   · 보낸 뒤 줄 수·날짜 범위·빠진 매매일(export_past_sheet.coverage) 을 돌려줌 → fanding_trade 가 답장
#   · 같은 버튼을 30초 안에 또 누르면 다시 안 보냄 (두 번 눌림 방지)
#   · 텔레그램 설정은 fanding_trade 의 TG(팬딩 전용 봇) 그대로 · 새 비밀값 없음 · 실패해도 예외 안 냄 · 오류는 종류만 로그
# 1.0.0 (사무실 v1.3.0, 2026-11-05): 과거 가격표 숫자 파일을 5번 팬딩 봇 텔레그램으로 보냄 (전달 통로 C) — 매일 자동
# ==========================================================
import hashlib, importlib.util, json, os, re, tempfile, time, urllib.request, uuid
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "1.1.0"
KST = ZoneInfo("Asia/Seoul")
FILE_NAME = "past_sheet_numbers.jsonl"
STATE_NAME = "past_sheet_telegram.json"
FIELDS = {"종가일", "종가", "매수", "매도", "글 주소"}
LEVEL_FIELDS = {"price", "qty"}
MAX_BYTES = 45 * 1024 * 1024 # 텔레그램 봇 문서 한도(50MB)보다 작게
DEBOUNCE = 30                # 초
MEM = {"sent": 0.0}


def _load(path):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path, data):
    """같은 폴더 임시 파일 → 교체 (중간에 끊겨도 깨진 파일 없음)"""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".past_sheet_telegram.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _pos_num(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and v == v and v not in (float("inf"),) and v > 0


def _levels_ok(v):
    return isinstance(v, list) and all(
        isinstance(x, dict) and set(x) == LEVEL_FIELDS and _pos_num(x["price"])
        and not isinstance(x["qty"], bool) and isinstance(x["qty"], int) and x["qty"] > 0 for x in v)


def check_content(raw):
    """(통과 여부, 줄 수, 종가일 목록). 줄마다 정해진 5칸만 · 매수/매도는 {price, qty} 목록 1칸씩"""
    n, days = 0, []
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return False, 0, []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return False, n, days
        if not isinstance(row, dict) or set(row) != FIELDS:
            return False, n, days
        d = row["종가일"]
        if not isinstance(d, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            return False, n, days
        try:
            date.fromisoformat(d)
        except ValueError:
            return False, n, days
        if not _pos_num(row["종가"]) or not _levels_ok(row["매수"]) or not _levels_ok(row["매도"]):
            return False, n, days
        if not isinstance(row["글 주소"], str) or not row["글 주소"].strip():
            return False, n, days
        n += 1
        days.append(d)
    return True, n, days


def send_document(tg, data, caption):
    """sendDocument (multipart). 성공하면 True. 오류 내용에 주소(토큰)를 남기지 않음"""
    api = os.environ.get("OFFICE_TELEGRAM_API", "https://api.telegram.org")
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
             for k, v in {"chat_id": tg.chat, "caption": caption[:900]}.items()]
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="document"; filename="{FILE_NAME}"\r\n'
                 f'Content-Type: application/x-ndjson\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"{api}/bot{tg.token}/sendDocument", data=b"".join(parts), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return bool(json.load(r).get("ok"))


def _exporter():
    """같은 폴더의 export_past_sheet.py 를 매번 새로 읽음 (빠진 날짜 계산용, 쓰기 없음)"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_past_sheet.py")
    spec = importlib.util.spec_from_file_location("export_past_sheet", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def missing_summary(days, limit=3000):
    """종가일 목록 → (빠진 날짜 글, coverage dict). 실패하면 ('', {})"""
    try:
        mod = _exporter()
        cov = mod.coverage(days)
        return mod.missing_text(cov, limit=limit), cov
    except Exception as e:
        print("빠진 날짜 계산 오류:", type(e).__name__, flush=True)
        return "", {}


def send_now(tg, home, now=None, log=print):
    """[📥 과거자료 다운] 버튼 = 숫자 파일 1개를 5번 팬딩 봇으로 1번 보냄.
    돌려줌: {'status': 'sent'|사유, 'rows', 'first', 'last', 'missing'(글)}. 예외를 밖으로 내지 않음"""
    now = now or datetime.now(KST)
    try:
        home = Path(home)
        src, state_file = home / FILE_NAME, home / STATE_NAME
        if not src.exists():
            return {"status": "no_file"}
        if time.time() - MEM["sent"] < DEBOUNCE:
            return {"status": "just_sent"}
        raw = src.read_bytes()
        if len(raw) > MAX_BYTES:
            return {"status": "too_big"}
        ok, rows, days = check_content(raw)
        if not ok:
            log("과거 숫자 파일: 정해진 5칸 밖의 내용이 있어 텔레그램으로 보내지 않음", flush=True)
            return {"status": "bad_content", "rows": rows}
        if rows == 0:
            return {"status": "empty"}
        if not getattr(tg, "own", False) or not getattr(tg, "token", None) or not getattr(tg, "chat", ""):
            return {"status": "no_fanding_bot"}
        first, last = min(days), max(days)
        MEM["sent"] = time.time()
        if not send_document(tg, raw, f"🗂 과거 가격표 숫자 파일 · {rows}줄 · {first} ~ {last}"):
            MEM["sent"] = 0.0
            return {"status": "send_failed"}
        try:
            st = _load(state_file)
            st.update(sent_at=now.isoformat(timespec="seconds"), sent_sha=hashlib.sha256(raw).hexdigest(), rows=rows)
            _save(state_file, st)
        except OSError as e:
            log("과거 숫자 파일 전송 기록 실패:", type(e).__name__, flush=True)
        text, _ = missing_summary(days)
        return {"status": "sent", "rows": rows, "first": first, "last": last, "missing": text}
    except Exception as e:                    # 매매 루프를 멈추지 않음 · 예외 종류만 남김
        MEM["sent"] = 0.0
        log("과거 숫자 파일 텔레그램 전송 오류:", type(e).__name__, flush=True)
        return {"status": "error"}


def tick(*_args, **_kw):
    """1.1.0: 자동 전송 없음 (버튼으로만). 옛 호출이 남아 있어도 아무것도 하지 않음"""
    return None
