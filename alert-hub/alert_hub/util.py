"""시간 표시용 작은 도우미들."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def tz_of(cfg):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(cfg.tz_name)
    except Exception:
        return timezone(timedelta(hours=9))  # 서버에 tz 데이터가 없으면 한국시간으로


def fmt_ts(ts: float, tz, fmt: str = "%m/%d %H:%M") -> str:
    return datetime.fromtimestamp(ts, tz).strftime(fmt)


def fmt_dur(seconds: float) -> str:
    minutes = max(0, int(seconds)) // 60
    if minutes < 1:
        return "1분 미만"
    if minutes < 60:
        return f"{minutes}분"
    hours, rest = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}시간 {rest}분" if rest else f"{hours}시간"
    days, hours = divmod(hours, 24)
    return f"{days}일 {hours}시간" if hours else f"{days}일"


def fmt_ago(seconds: float) -> str:
    text = fmt_dur(seconds)
    return "방금" if text == "1분 미만" else f"{text} 전"
