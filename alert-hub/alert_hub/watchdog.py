"""감시 담당. cron 으로 10분마다 실행하세요.

하는 일
  1) 전송 실패로 밀린 긴급 알림 다시 보내기
  2) 하트비트가 끊긴 봇 찾기 -> 긴급 알림 (한 번 보내고, HUB_REMIND_HOURS 마다 재알림)
  3) 다시 살아난 봇 -> 복구 알림
  4) 오래된 기록 정리 (HUB_KEEP_DAYS)
"""
from __future__ import annotations

import time
from contextlib import closing

from .config import load
from .db import connect
from .notify import flush_pending, notify
from .util import fmt_dur


def run_watchdog(now=None) -> dict:
    cfg = load()
    now = time.time() if now is None else now
    result = {"flushed": 0, "stale": [], "recovered": [], "purged": 0}

    with closing(connect(cfg.db_path)) as conn:
        result["flushed"] = flush_pending(cfg, conn, now)
        hb = {r["bot"]: r for r in conn.execute("SELECT bot, ts, alerted FROM heartbeats")}

        for bot, stale_min in cfg.bots.items():
            row = hb.get(bot)
            if row is None:
                # 처음 보는 봇: 지금부터 유예 시간을 시작합니다 (설치 직후 오경보 방지)
                conn.execute(
                    "INSERT INTO heartbeats(bot, ts, alerted) VALUES (?,?,0)", (bot, now)
                )
                conn.commit()
                continue

            age = now - row["ts"]
            if age > stale_min * 60:
                if now - (row["alerted"] or 0) >= cfg.remind_hours * 3600:
                    conn.execute("UPDATE heartbeats SET alerted=? WHERE bot=?", (now, bot))
                    conn.commit()
                    notify(
                        "watchdog", "critical",
                        f"{bot} 소식이 {fmt_dur(age)}째 없습니다 (기준 {fmt_dur(stale_min * 60)}). "
                        "봇이 멈췄을 수 있어요.",
                        wait=True, now=now,
                    )
                    result["stale"].append(bot)
            elif row["alerted"]:
                conn.execute("UPDATE heartbeats SET alerted=0 WHERE bot=?", (bot,))
                conn.commit()
                notify("watchdog", "info", f"{bot} 하트비트가 다시 들어오기 시작했습니다 (복구).",
                       push=True, wait=True, now=now)
                result["recovered"].append(bot)

        cutoff = now - cfg.keep_days * 86400
        cur = conn.execute("DELETE FROM events WHERE ts<?", (cutoff,))
        conn.commit()
        result["purged"] = cur.rowcount or 0
    return result
