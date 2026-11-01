"""모든 봇이 공용으로 쓰는 notify() / heartbeat().

핵심 약속: 이 함수들은 **절대 예외를 밖으로 던지지 않습니다.**
알림 시스템이 고장나도 매매 봇은 멈추면 안 되기 때문입니다.

등급
  critical : 즉시 텔레그램 전송 (+ DB 기록)
  warning  : DB 기록만. 브리핑에서 따로 강조
  info     : DB 기록만. 브리핑에서 요약
"""
from __future__ import annotations

import sys
import threading
import time
from contextlib import closing

from . import telegram
from .config import load
from .db import connect, meta_get, meta_set

ICONS = {"critical": "🔴", "warning": "🟡", "info": "🟢"}
_ALIASES = {
    "critical": "critical", "crit": "critical", "error": "critical",
    "urgent": "critical", "fatal": "critical", "긴급": "critical",
    "warning": "warning", "warn": "warning", "경고": "warning",
    "info": "info", "debug": "info", "일반": "info",
}
_threads: list = []


def _log(msg: str) -> None:
    print(f"[alert_hub] {msg}", file=sys.stderr)


def wait_all(timeout: float = 15.0) -> None:
    """백그라운드 전송이 끝날 때까지 기다립니다 (테스트/종료 직전용)."""
    for t in list(_threads):
        t.join(timeout)
    _threads[:] = [t for t in _threads if t.is_alive()]


def notify(bot, level, message, push: bool = False, wait=None, now=None) -> bool:
    """알림 기록/전송. 기록에 성공하면 True.

    push=True 면 info/warning 도 즉시 텔레그램으로 보냅니다.
    wait=True 면 전송이 끝날 때까지 기다립니다 (기본: 백그라운드 전송).
    """
    try:
        return _notify(str(bot), level, message, push, wait, now)
    except Exception as e:  # 무슨 일이 있어도 봇을 멈추지 않는다
        _log(f"notify 실패(무시하고 계속): {type(e).__name__}: {e}")
        return False


def _notify(bot, level, message, push, wait, now) -> bool:
    cfg = load()
    raw = str(level).strip().lower()
    lvl = _ALIASES.get(raw)
    msg = str(message).strip()
    if lvl is None:  # 오타로 알림을 놓치느니 시끄러운 쪽이 낫다
        lvl = "critical"
        msg = f"(level='{level}' 인식불가 → 긴급 처리) {msg}"
    if len(msg) > 2000:
        msg = msg[:1990] + "…(잘림)"
    now = time.time() if now is None else now
    wait = cfg.sync if wait is None else wait

    with closing(connect(cfg.db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO events(ts, bot, level, message, sent) VALUES (?,?,?,?,0)",
            (now, bot, lvl, msg),
        )
        event_id = cur.lastrowid
        conn.commit()

        if lvl != "critical" and not push:
            return True

        text = f"{ICONS[lvl]} [{bot}] {msg}"
        track_id = event_id
        if lvl == "critical":
            action, override = _throttle(conn, cfg, bot, msg, event_id, now)
            if action == "skip":
                return True
            if override:  # 폭주 안내문은 별도 메시지로
                text, track_id = override, None
    _deliver(cfg, track_id, text, wait)
    return True


def _throttle(conn, cfg, bot, msg, event_id, now):
    """같은 알림 반복/폭주를 막습니다. -> ('send'|'skip', 대체문구|None)"""
    dup = conn.execute(
        "SELECT 1 FROM events WHERE bot=? AND level='critical' AND message=? "
        "AND ts>? AND id<? LIMIT 1",
        (bot, msg, now - cfg.dedup_minutes * 60, event_id),
    ).fetchone()
    if dup:
        conn.execute("UPDATE events SET sent=2 WHERE id=?", (event_id,))
        conn.commit()
        return "skip", None

    recent = conn.execute(
        "SELECT COUNT(*) FROM events WHERE bot=? AND level='critical' "
        "AND sent IN (0,1) AND ts>? AND id<?",
        (bot, now - 600, event_id),
    ).fetchone()[0]
    if recent >= cfg.flood_limit:
        conn.execute("UPDATE events SET sent=2 WHERE id=?", (event_id,))
        last = float(meta_get(conn, f"flood:{bot}", 0) or 0)
        if now - last >= 600:
            meta_set(conn, f"flood:{bot}", now)
            conn.commit()
            return "send", (
                f"🔴 [{bot}] 긴급 알림이 10분에 {cfg.flood_limit}건을 넘었습니다. "
                "이후 알림은 개별 전송을 멈추고 브리핑에 모아둡니다. 로그를 확인하세요."
            )
        conn.commit()
        return "skip", None
    return "send", None


def _deliver(cfg, event_id, text, wait) -> None:
    def job() -> None:
        ok = telegram.send(text, cfg.token, cfg.chat_id)
        if ok and event_id is not None:
            try:
                with closing(connect(cfg.db_path)) as c:
                    c.execute("UPDATE events SET sent=1 WHERE id=?", (event_id,))
                    c.commit()
            except Exception as e:
                _log(f"전송 기록 갱신 실패: {type(e).__name__}")

    if wait:
        job()
    else:  # 매매 루프가 네트워크 때문에 지연되지 않도록 백그라운드에서 전송
        t = threading.Thread(target=job, name="alert_hub_send")
        t.start()
        _threads.append(t)
        _threads[:] = [x for x in _threads if x.is_alive()]


def flush_pending(cfg, conn, now=None, max_items: int = 20) -> int:
    """전송에 실패해 남아 있는 긴급 알림을 다시 보냅니다 (watchdog 이 호출)."""
    from .util import fmt_ts, tz_of

    now = time.time() if now is None else now
    rows = conn.execute(
        "SELECT id, ts, bot, message FROM events WHERE level='critical' AND sent=0 "
        "AND ts>? ORDER BY ts LIMIT ?",
        (now - 86400, max_items),
    ).fetchall()
    tz = tz_of(cfg)
    done = 0
    for r in rows:
        text = f"🔴 [{r['bot']}] (지연 전송 · 발생 {fmt_ts(r['ts'], tz)}) {r['message']}"
        if telegram.send(text, cfg.token, cfg.chat_id):
            conn.execute("UPDATE events SET sent=1 WHERE id=?", (r["id"],))
            conn.commit()
            done += 1
        else:
            break  # 아직 텔레그램이 안 되는 상태면 다음 기회에
    return done


_last_beat: dict = {}


def heartbeat(bot, now=None, min_interval: float = 30.0) -> bool:
    """'나 살아있어요' 신호. 메인 루프에서 마음껏 호출해도 됩니다.

    너무 자주 불려도 DB에는 min_interval(기본 30초)에 한 번만 기록합니다.
    """
    try:
        cfg = load()
        now = time.time() if now is None else now
        key = (str(cfg.db_path), str(bot))
        last = _last_beat.get(key)
        if last is not None and 0 <= now - last < min_interval:
            return True
        with closing(connect(cfg.db_path)) as conn:
            conn.execute(
                "INSERT INTO heartbeats(bot, ts, alerted) VALUES (?,?,0) "
                "ON CONFLICT(bot) DO UPDATE SET ts=excluded.ts",
                (str(bot), now),
            )
            conn.commit()
        _last_beat[key] = now
        return True
    except Exception as e:
        _log(f"heartbeat 실패(무시하고 계속): {type(e).__name__}: {e}")
        return False
