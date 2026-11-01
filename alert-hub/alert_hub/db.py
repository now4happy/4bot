"""SQLite 저장소. 여러 봇이 동시에 써도 안전하도록 WAL 모드를 사용합니다."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL    NOT NULL,
    bot     TEXT    NOT NULL,
    level   TEXT    NOT NULL,
    message TEXT    NOT NULL,
    sent    INTEGER NOT NULL DEFAULT 0   -- 0=미전송, 1=전송됨, 2=중복/폭주로 생략
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS heartbeats (
    bot     TEXT PRIMARY KEY,
    ts      REAL NOT NULL,
    alerted REAL NOT NULL DEFAULT 0      -- 마지막으로 '무소식' 경고를 보낸 시각 (0=경고 없음)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA)
    return conn


def meta_get(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(conn, key, value) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
