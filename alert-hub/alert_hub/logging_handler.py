"""파이썬 logging 과 연결하는 핸들러.

이미 logging 을 쓰는 봇이라면 한 줄로 연결됩니다:

    import logging
    from alert_hub import HubLogHandler
    logging.getLogger().addHandler(HubLogHandler("매매봇1"))

ERROR 이상 -> critical (즉시 알림), WARNING -> warning, 그 외 -> info
기본값(min_level=WARNING)에서는 INFO/DEBUG 로그는 허브로 보내지 않습니다.
"""
from __future__ import annotations

import logging

from .notify import notify


class HubLogHandler(logging.Handler):
    def __init__(self, bot: str, min_level: int = logging.WARNING):
        super().__init__(level=min_level)
        self.bot = bot

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno >= logging.ERROR:
                level = "critical"
            elif record.levelno >= logging.WARNING:
                level = "warning"
            else:
                level = "info"
            notify(self.bot, level, self.format(record)[:1000])
        except Exception:
            pass  # 로깅 핸들러가 봇을 죽이면 안 됨
