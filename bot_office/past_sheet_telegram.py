#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/past_sheet_telegram.py   (PAST_SHEET_TELEGRAM_V1.0.0)
# 1.0.0 (사무실 vNEXT, 2026-11-05): 과거 가격표 숫자 파일을 5번 팬딩 봇 텔레그램으로 보냄 (전달 통로 C)
#   · 보내는 것: /var/lib/bot-office/fanding/past_sheet_numbers.jsonl 파일 1개 (문서로)
#   · 보내는 때: 자동 추출이 그 파일을 '오늘(KST)' 새로 썼고, 내용이 지난번 보낸 것과 다를 때 → 그날 1번만
#     (같은 날 다시 갱신돼도 안 보냄 · 원본이 안 바뀌어 파일 내용이 같으면 안 보냄 · 10분마다 반복 안 함)
#   · 보내기 전 검사: 줄마다 종가일·종가·매수·매도·글 주소 5칸만 있는지 → 다른 칸이 있으면 안 보냄
#   · 텔레그램 설정은 fanding_trade 의 TG(팬딩 전용 봇 telegram_fanding.json) 그대로 · 새 비밀값 없음
#     팬딩 전용 봇이 아니면(비서 봇으로 대체 중이면) 보내지 않음
#   · 매매·주문·판독·알림 흐름과 무관 · 실패해도 예외를 밖으로 내지 않음 · 토큰은 로그에 안 남김
# ==========================================================
import hashlib, json, os, tempfile, time, urllib.request, uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "1.0.0"
KST = ZoneInfo("Asia/Seoul")
FILE_NAME = "past_sheet_numbers.jsonl"
STATE_NAME = "past_sheet_telegram.json"
FIELDS = {"종가일", "종가", "매수", "매도", "글 주소"}
LEVEL_FIELDS = {"price", "qty"}
CHECK_EVERY = 600            # 10분에 한 번만 파일 확인
MAX_TRIES_PER_DAY = 3        # 전송 실패 시 그날 최대 3번까지 (10분 간격)
MAX_BYTES = 45 * 1024 * 1024 # 텔레그램 봇 문서 한도(50MB)보다 작게
MEM = {"checked": 0.0}


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


def check_content(raw):
    """(통과 여부, 줄 수). 줄마다 정해진 5칸·매수/매도는 price·qty 만"""
    n = 0
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or set(row) != FIELDS:
            return False, n
        for side in ("매수", "매도"):
            if not isinstance(row[side], list) or any(not isinstance(x, dict) or set(x) != LEVEL_FIELDS for x in row[side]):
                return False, n
        n += 1
    return True, n


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


def tick(tg, home, now=None, log=print):
    """상시 루프에서 매 바퀴 불러도 됨 (10분에 한 번만 확인). 보냈으면 'sent', 아니면 사유 문자열/None"""
    now = now or datetime.now(KST)
    if time.time() - MEM["checked"] < CHECK_EVERY:
        return None
    MEM["checked"] = time.time()
    try:
        home = Path(home)
        src, state_file = home / FILE_NAME, home / STATE_NAME
        if not src.exists():
            return "no_file"
        today = now.date().isoformat()
        st = _load(state_file)
        if st.get("sent_day") == today:
            return "already_sent_today"
        if datetime.fromtimestamp(src.stat().st_mtime, KST).date().isoformat() != today:
            return "not_updated_today"
        raw = src.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha == st.get("sent_sha"):
            return "same_content"            # 원본이 안 바뀌어 같은 내용으로 다시 쓰인 날
        if len(raw) > MAX_BYTES:
            return "too_big"
        ok, rows = check_content(raw)
        if not ok:
            log("과거 숫자 파일: 정해진 칸 밖의 내용이 있어 텔레그램으로 보내지 않음", flush=True)
            return "bad_content"
        if not getattr(tg, "own", False) or not getattr(tg, "token", None) or not getattr(tg, "chat", ""):
            return "no_fanding_bot"
        tries = st.get("tries", {}) if isinstance(st.get("tries"), dict) else {}
        if int(tries.get(today, 0)) >= MAX_TRIES_PER_DAY:
            return "give_up_today"
        tries = {today: int(tries.get(today, 0)) + 1}
        st["tries"] = tries
        _save(state_file, st)                 # 시도 횟수를 먼저 기록 → 재시작해도 하루 3번 넘지 않음
        if not send_document(tg, raw, f"🗂 과거 가격표 숫자 파일 · {rows}줄"):
            return "send_failed"
        st.update(sent_day=today, sent_sha=sha, sent_at=now.isoformat(timespec="seconds"), rows=rows)
        _save(state_file, st)
        return "sent"
    except Exception as e:                    # 매매 루프를 멈추지 않음 · 예외 종류만 남김
        log("과거 숫자 파일 텔레그램 전송 오류:", type(e).__name__, flush=True)
        return "error"
