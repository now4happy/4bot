"""설정 읽기. 우선순위: 환경변수 > .env 파일 > 기본값.

.env 위치: 기본은 프로젝트 폴더의 .env (HUB_ENV_FILE 로 바꿀 수 있음).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_env_file(path: Path) -> dict:
    out: dict = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def _num(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    token: str
    chat_id: str
    db_path: Path
    bots: dict  # 봇 이름 -> 무소식 기준(분)
    dedup_minutes: float
    flood_limit: int
    remind_hours: float
    keep_days: float
    tz_name: str
    api_key: str
    ai_model: str
    sync: bool


def load() -> Config:
    env_file = Path(os.environ.get("HUB_ENV_FILE", str(ROOT / ".env")))
    file_vals = _read_env_file(env_file)

    def get(key: str, default: str = "") -> str:
        return os.environ.get(key, file_vals.get(key, default))

    default_stale = _num(get("HUB_STALE_MINUTES", "180"), 180.0)
    bots: dict = {}
    for part in get("HUB_BOT_NAMES", "").split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, minutes = part.rsplit(":", 1)
            bots[name.strip()] = _num(minutes, default_stale)
        else:
            bots[part] = default_stale

    raw_db = get("HUB_DB_PATH", "").strip()
    db_path = Path(raw_db).expanduser() if raw_db else ROOT / "data" / "hub.db"

    return Config(
        token=get("TELEGRAM_BOT_TOKEN").strip(),
        chat_id=get("TELEGRAM_CHAT_ID").strip(),
        db_path=db_path,
        bots=bots,
        dedup_minutes=_num(get("HUB_DEDUP_MINUTES", "10"), 10.0),
        flood_limit=int(_num(get("HUB_FLOOD_LIMIT", "5"), 5)),
        remind_hours=_num(get("HUB_REMIND_HOURS", "6"), 6.0),
        keep_days=_num(get("HUB_KEEP_DAYS", "30"), 30.0),
        tz_name=get("HUB_TZ", "Asia/Seoul").strip() or "Asia/Seoul",
        api_key=get("ANTHROPIC_API_KEY").strip(),
        ai_model=get("HUB_AI_MODEL", "claude-sonnet-5-5").strip() or "claude-sonnet-5-5",
        sync=get("HUB_SYNC", "0").strip() in ("1", "true", "True", "yes"),
    )
