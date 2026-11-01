"""셀프 테스트 (네트워크 불필요 — 텔레그램 전송은 가짜로 대체).

실행:  python3 -m unittest discover -s tests -v
"""
import logging
import os
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alert_hub import HubLogHandler, briefing, heartbeat, notify, telegram, watchdog  # noqa: E402
from alert_hub.config import load  # noqa: E402
from alert_hub.db import connect, meta_get  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = dict(os.environ)
        os.environ.update({
            "HUB_ENV_FILE": str(Path(self.tmp.name) / "none.env"),
            "HUB_DB_PATH": str(Path(self.tmp.name) / "hub.db"),
            "TELEGRAM_BOT_TOKEN": "T",
            "TELEGRAM_CHAT_ID": "1",
            "HUB_SYNC": "1",
            "ANTHROPIC_API_KEY": "",
            "HUB_BOT_NAMES": "봇A:60,봇B",
            "HUB_STALE_MINUTES": "180",
        })
        self.sent = []
        self.ok = True
        self._orig_send = telegram.send

        def fake(text, token, chat_id, timeout=5.0):
            if self.ok:
                self.sent.append(text)
            return self.ok

        telegram.send = fake

    def tearDown(self):
        telegram.send = self._orig_send
        os.environ.clear()
        os.environ.update(self._env)
        self.tmp.cleanup()


class TestNotify(Base):
    def test_critical_is_pushed_info_and_warning_are_stored(self):
        notify("봇A", "critical", "주문 실패")
        notify("봇A", "info", "BTC 체결")
        notify("봇A", "warning", "잔고 부족 임박")
        self.assertEqual(len(self.sent), 1)
        self.assertIn("🔴", self.sent[0])
        self.assertIn("[봇A]", self.sent[0])
        with closing(connect(load().db_path)) as c:
            n = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertEqual(n, 3)

    def test_push_flag_sends_info(self):
        notify("봇A", "info", "중요한 일반 알림", push=True)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("🟢", self.sent[0])

    def test_duplicate_critical_is_suppressed(self):
        notify("봇A", "critical", "API 오류")
        notify("봇A", "critical", "API 오류")
        notify("봇A", "critical", "다른 오류")
        self.assertEqual(len(self.sent), 2)

    def test_flood_protection(self):
        os.environ["HUB_FLOOD_LIMIT"] = "3"
        for i in range(8):
            notify("봇A", "critical", f"오류 {i}")
        # 개별 3건 + 폭주 안내 1건
        self.assertEqual(len(self.sent), 4)
        self.assertIn("넘었습니다", self.sent[-1])

    def test_unknown_level_is_treated_as_critical(self):
        notify("봇A", "critcal", "오타 등급")
        self.assertEqual(len(self.sent), 1)
        self.assertIn("인식불가", self.sent[0])

    def test_failed_send_is_retried_by_watchdog(self):
        self.ok = False
        notify("봇A", "critical", "텔레그램 장애 중 발생")
        self.assertEqual(self.sent, [])
        self.ok = True
        result = watchdog.run_watchdog()
        self.assertEqual(result["flushed"], 1)
        self.assertIn("지연 전송", self.sent[0])
        # 이미 보냈으니 다시 보내지 않는다
        self.assertEqual(watchdog.run_watchdog()["flushed"], 0)

    def test_notify_never_raises(self):
        os.environ["HUB_DB_PATH"] = "/proc/nonexistent/dir/hub.db"
        self.assertFalse(notify("봇A", "critical", "DB 못 여는 상황"))
        self.assertFalse(heartbeat("봇A"))

    def test_async_mode_delivers(self):
        import importlib
        notify_mod = importlib.import_module("alert_hub.notify")
        os.environ["HUB_SYNC"] = "0"
        notify("봇A", "critical", "백그라운드 전송")
        notify_mod.wait_all()
        self.assertEqual(len(self.sent), 1)


class TestWatchdog(Base):
    def test_stale_alert_reminder_and_recovery(self):
        t0 = 1_000_000.0
        heartbeat("봇A", now=t0)  # 기준 60분
        heartbeat("봇B", now=t0)  # 기준 180분

        watchdog.run_watchdog(now=t0 + 10 * 60)
        self.assertEqual(self.sent, [])

        watchdog.run_watchdog(now=t0 + 61 * 60)  # 봇A만 초과
        self.assertEqual(len(self.sent), 1)
        self.assertIn("봇A", self.sent[0])

        watchdog.run_watchdog(now=t0 + 70 * 60)  # 같은 장애는 재알림 시간 전엔 조용
        self.assertEqual(len(self.sent), 1)

        watchdog.run_watchdog(now=t0 + 8 * 3600)  # 봇A 재알림 + 봇B 첫 알림
        self.assertEqual(len(self.sent), 3)

        heartbeat("봇A", now=t0 + 8 * 3600 + 30)
        watchdog.run_watchdog(now=t0 + 8 * 3600 + 120)
        self.assertEqual(len(self.sent), 4)
        self.assertIn("복구", self.sent[-1])

    def test_heartbeat_is_throttled(self):
        def last_ts():
            with closing(connect(load().db_path)) as c:
                return c.execute("SELECT ts FROM heartbeats WHERE bot='봇A'").fetchone()[0]

        heartbeat("봇A", now=100.0)
        heartbeat("봇A", now=110.0)  # 30초 안 -> 기록 생략
        self.assertEqual(last_ts(), 100.0)
        heartbeat("봇A", now=131.0)
        self.assertEqual(last_ts(), 131.0)

    def test_first_seen_bot_gets_grace_period(self):
        t0 = 2_000_000.0
        watchdog.run_watchdog(now=t0)  # 하트비트가 한 번도 없는 신규 설치
        self.assertEqual(self.sent, [])
        watchdog.run_watchdog(now=t0 + 30 * 60)
        self.assertEqual(self.sent, [])
        watchdog.run_watchdog(now=t0 + 61 * 60)  # 봇A 기준 60분 경과
        self.assertEqual(len(self.sent), 1)


class TestBriefing(Base):
    def test_counts_and_marks_done(self):
        notify("봇A", "info", "체결 1")
        notify("봇A", "info", "체결 2")
        notify("봇B", "info", "체결 3")
        notify("봇A", "warning", "잔고 적음")
        notify("봇B", "critical", "주문 실패")
        heartbeat("봇A")
        self.sent.clear()

        self.assertTrue(briefing.run_briefing(use_ai=False))
        text = self.sent[-1]
        self.assertIn("🔴 긴급 1 · 🟡 경고 1 · 🟢 일반 3", text)
        self.assertIn("봇A: 🔴0 🟡1 🟢2", text)
        self.assertIn("봇B: 🔴1 🟡0 🟢1", text)
        self.assertIn("주문 실패", text)
        with closing(connect(load().db_path)) as c:
            self.assertIsNotNone(meta_get(c, "last_briefing_ts"))

    def test_failed_send_does_not_mark_done(self):
        notify("봇A", "info", "체결")
        self.ok = False
        self.assertFalse(briefing.run_briefing(use_ai=False))
        with closing(connect(load().db_path)) as c:
            self.assertIsNone(meta_get(c, "last_briefing_ts"))

    def test_second_briefing_only_covers_new_events(self):
        notify("봇A", "info", "아침 체결")
        briefing.run_briefing(use_ai=False)
        self.sent.clear()
        briefing.run_briefing(use_ai=False)
        self.assertIn("🟢 일반 0", self.sent[-1])

    def test_never_reported_bot_is_flagged(self):
        briefing.run_briefing(use_ai=False)
        self.assertIn("⚠️ 봇A", self.sent[-1])
        self.assertIn("하트비트 기록 없음", self.sent[-1])

    def test_payload_marks_messages_as_data_and_is_bounded(self):
        for i in range(100):
            notify("봇A", "info", "x" * 500 + str(i))
        cfg = load()
        with closing(connect(cfg.db_path)) as c:
            rows = briefing._collect(c, 0, 9e12)
        payload = briefing.build_payload(cfg, rows, {}, 0, 9e12)
        self.assertLessEqual(len(payload), 24000)


class TestMisc(Base):
    def test_split_text(self):
        text = "\n".join("줄" * 100 for _ in range(200))
        chunks = telegram.split_text(text, 4000)
        self.assertTrue(all(len(c) <= 4000 for c in chunks))
        self.assertEqual("\n".join(chunks), text)

    def test_log_handler(self):
        logger = logging.getLogger("hub_test")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handler = HubLogHandler("봇A")
        logger.addHandler(handler)
        try:
            logger.info("무시됨")
            logger.warning("경고만 기록")
            logger.error("터짐")
        finally:
            logger.removeHandler(handler)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("터짐", self.sent[0])
        with closing(connect(load().db_path)) as c:
            levels = [r[0] for r in c.execute("SELECT level FROM events ORDER BY id")]
        self.assertEqual(levels, ["warning", "critical"])

    def test_env_file_parsing(self):
        env = Path(self.tmp.name) / "x.env"
        env.write_text('# 주석\nTELEGRAM_CHAT_ID="999"\nHUB_BOT_NAMES=가:30, 나\n', encoding="utf-8")
        os.environ["HUB_ENV_FILE"] = str(env)
        del os.environ["TELEGRAM_CHAT_ID"]
        del os.environ["HUB_BOT_NAMES"]
        cfg = load()
        self.assertEqual(cfg.chat_id, "999")
        self.assertEqual(cfg.bots, {"가": 30.0, "나": 180.0})


if __name__ == "__main__":
    unittest.main()
