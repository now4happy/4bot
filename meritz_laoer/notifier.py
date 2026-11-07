# ==========================================================
# FILE: meritz_laoer/notifier.py   (MERITZ_LAOER v1.0.0)
# 새 텔레그램 봇으로 알림만 보냄 (명령·버튼 없음). 토큰 파일: 설정 telegram_file {"token": "...", "chat_id": "..."}
# v1.0.0 (2026-11-08): 첫 버전. 다른 봇 토큰 재사용 검사 함수 포함. 토큰 원문은 출력하지 않음
# ==========================================================
import hashlib
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path


def _read_token(path):
    """JSON {"token": ...} 또는 토큰 한 줄짜리 파일 → 토큰 문자열 (없으면 "")"""
    try:
        raw = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    try:
        d = json.loads(raw)
        if isinstance(d, dict):
            return str(d.get("token") or d.get("bot_token") or "").strip()
    except ValueError:
        pass
    return raw.splitlines()[0].strip() if raw else ""


def token_fp(tok):
    return hashlib.sha256(tok.encode()).hexdigest()[:12] if tok else ""


class Notifier:
    def __init__(self, telegram_file, dry_run=True):
        self.ok = False
        self.dry_run = dry_run
        try:
            d = json.loads(Path(telegram_file).read_text(encoding="utf-8"))
            self.token, self.chat_id = str(d["token"]).strip(), str(d["chat_id"]).strip()
            self.ok = bool(self.token and self.chat_id)
        except (OSError, ValueError, KeyError) as e:
            logging.warning(f"텔레그램 설정 없음/오류 → 로그로만 남김: {type(e).__name__}")

    def send(self, text):
        msg = ("🧪[모의] " if self.dry_run else "") + "🟦메리츠 무매 SOXL\n" + str(text)
        logging.info(msg.replace("\n", " | "))
        if not self.ok:
            return False
        try:
            body = urllib.parse.urlencode({"chat_id": self.chat_id, "text": msg[:3900]}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{self.token}/sendMessage", data=body, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status == 200
        except Exception as e:   # 알림 실패로 봇이 멈추지 않게
            logging.warning(f"텔레그램 전송 실패: {type(e).__name__}")
            return False
