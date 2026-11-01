"""텔레그램 전송 (표준 라이브러리만 사용 — 추가 설치 불필요)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def _log(msg: str) -> None:
    print(f"[alert_hub] {msg}", file=sys.stderr)


def split_text(text: str, limit: int = 4000) -> list:
    """텔레그램 1건 최대 길이(4096자)를 넘지 않게 줄 단위로 나눕니다."""
    if len(text) <= limit:
        return [text]
    chunks: list = []
    cur = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks


def send(text: str, token: str, chat_id: str, timeout: float = 5.0) -> bool:
    """성공하면 True. 토큰은 로그에 절대 찍지 않습니다."""
    if not token or not chat_id:
        _log("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 설정되지 않았습니다 (.env 확인)")
        return False
    for chunk in split_text(text):
        body = json.dumps(
            {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    _log(f"텔레그램 전송 실패: HTTP {resp.status}")
                    return False
        except urllib.error.HTTPError as e:
            _log(f"텔레그램 전송 실패: HTTP {e.code}")
            return False
        except Exception as e:  # 네트워크 오류 등
            _log(f"텔레그램 전송 실패: {type(e).__name__}")
            return False
    return True
