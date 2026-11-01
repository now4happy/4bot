"""명령줄 도구.  사용법:  python -m alert_hub <명령>

  test                 텔레그램 연결 테스트 (테스트 메시지 1건 전송)
  status               봇별 하트비트/최근 24시간 건수 보기
  notify 봇 등급 메시지  쉘 스크립트 등에서 알림 남기기
  heartbeat 봇          하트비트 남기기
  briefing             일일 브리핑 전송 (--no-send: 화면에만 출력, --no-ai, --hours N)
  watchdog             무소식 봇 점검 (cron 10분마다)
"""
from __future__ import annotations

import argparse
import time
from contextlib import closing

from . import telegram
from .config import load
from .db import connect
from .util import fmt_ago, tz_of


def cmd_test(args) -> int:
    cfg = load()
    print(f"DB 위치      : {cfg.db_path}")
    print(f"토큰 설정     : {'있음' if cfg.token else '없음  ← .env 의 TELEGRAM_BOT_TOKEN 확인'}")
    print(f"채팅ID 설정   : {'있음' if cfg.chat_id else '없음  ← .env 의 TELEGRAM_CHAT_ID 확인'}")
    print(f"감시 대상 봇   : {', '.join(cfg.bots) or '(없음 — HUB_BOT_NAMES 설정 필요)'}")
    print(f"AI 요약       : {'켜짐 (' + cfg.ai_model + ')' if cfg.api_key else '꺼짐 (ANTHROPIC_API_KEY 없음)'}")
    with closing(connect(cfg.db_path)):
        pass
    print("DB 열기       : OK")
    ok = telegram.send("✅ alert_hub 연결 테스트 — 이 메시지가 보이면 성공입니다.",
                       cfg.token, cfg.chat_id, timeout=10)
    print("텔레그램 전송  :", "OK (텔레그램을 확인하세요)" if ok else "실패 (위 메시지/토큰/채팅ID 확인)")
    return 0 if ok else 1


def cmd_status(args) -> int:
    cfg = load()
    now = time.time()
    with closing(connect(cfg.db_path)) as conn:
        hb = {r["bot"]: r for r in conn.execute("SELECT bot, ts, alerted FROM heartbeats")}
        counts: dict = {}
        for r in conn.execute(
            "SELECT bot, level, COUNT(*) c FROM events WHERE ts>? GROUP BY bot, level",
            (now - 86400,),
        ):
            counts.setdefault(r["bot"], {})[r["level"]] = r["c"]
    names = list(cfg.bots) + [b for b in list(hb) + list(counts) if b not in cfg.bots]
    print(f"{'봇':<14}{'마지막 하트비트':<18}{'24h 긴급/경고/일반'}")
    for n in names:
        h = hb.get(n)
        beat = fmt_ago(now - h["ts"]) if h else "기록 없음"
        c = counts.get(n, {})
        warn = " ⚠️무소식" if (n in cfg.bots and (not h or now - h["ts"] > cfg.bots[n] * 60)) else ""
        print(f"{n:<14}{beat:<18}{c.get('critical', 0)}/{c.get('warning', 0)}/{c.get('info', 0)}{warn}")
    _ = tz_of(cfg)
    return 0


def cmd_notify(args) -> int:
    from .notify import notify
    ok = notify(args.bot, args.level, args.message, push=args.push, wait=True)
    return 0 if ok else 1


def cmd_heartbeat(args) -> int:
    from .notify import heartbeat
    return 0 if heartbeat(args.bot) else 1


def cmd_briefing(args) -> int:
    from .briefing import run_briefing
    ok = run_briefing(send=not args.no_send, use_ai=not args.no_ai, hours=args.hours)
    return 0 if ok else 1


def cmd_watchdog(args) -> int:
    from .watchdog import run_watchdog
    r = run_watchdog()
    print(f"밀린 알림 재전송 {r['flushed']}건 · 무소식 경고 {r['stale']} · 복구 {r['recovered']} · 정리 {r['purged']}건")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="alert_hub", description="봇 알림 허브")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("test").set_defaults(fn=cmd_test)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    n = sub.add_parser("notify")
    n.add_argument("bot")
    n.add_argument("level")
    n.add_argument("message")
    n.add_argument("--push", action="store_true", help="등급과 상관없이 즉시 텔레그램 전송")
    n.set_defaults(fn=cmd_notify)
    h = sub.add_parser("heartbeat")
    h.add_argument("bot")
    h.set_defaults(fn=cmd_heartbeat)
    b = sub.add_parser("briefing")
    b.add_argument("--no-send", action="store_true", help="전송하지 않고 화면에 출력")
    b.add_argument("--no-ai", action="store_true", help="AI 요약 없이 숫자 브리핑만")
    b.add_argument("--hours", type=float, default=None, help="최근 N시간 (지정하면 '마지막 브리핑 시각'은 갱신 안 함)")
    b.set_defaults(fn=cmd_briefing)
    sub.add_parser("watchdog").set_defaults(fn=cmd_watchdog)
    args = p.parse_args(argv)
    return args.fn(args)
