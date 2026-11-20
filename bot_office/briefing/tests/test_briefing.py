# briefing 시험 — 실서버·네트워크 없이 도는 범위. 숫자는 전부 자리표시자(실제 금액 아님).
# 실행: cd bot_office && python3 -m unittest briefing.tests.test_briefing -v
import datetime as dt
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

from briefing import need_table, portfolio, render, run, state, tg_send
from briefing.sources import SourceError, kiwoom, normalize_holdings, toss

TODAY = "2026-11-19"
NOW = "2026-11-19T02:30:00"          # 02:30 UTC = 09:30 CST = 10:30 KST


_SEED_DIR = tempfile.mkdtemp()
SEED_FILE = os.path.join(_SEED_DIR, "settings.json")
with open(SEED_FILE, "w", encoding="utf-8") as _f:
    json.dump({"total_krw": 1000, "split_count": 10}, _f)          # 자리표시자 숫자 (실제 설정값 아님)


def cfg():
    c = run.load_config()
    c["need"]["soxl3_seed"]["path"] = SEED_FILE                  # 서버의 /etc/... 대신 시험용 파일
    return c


def need_doc(null_holding=False, skipped=None, as_of="2026-11-19 09:05 KST", barbell=True):
    """Q16 모양: 계좌 name 은 토스·메리츠·한투·빗썸, line 의 label 은 바벨 씨드·P·VR6·3번 (토스 본 line·한투·빗썸은 label 없음)."""
    toss_lines = [{"currency": "USD", "holding": 100.0, "need": 250.0, "sufficient": False, "auto_fx": "on"},
                  {"currency": "KRW", "holding": 5000.0, "need": 4000.0, "sufficient": True, "auto_fx": "off"}]
    if barbell:
        toss_lines.append({"label": "바벨 씨드", "currency": "USD", "holding": 10.0, "need": 40.0,
                           "sufficient": False, "auto_fx": "on"})
    m4 = {"label": "3번", "currency": "USD", "holding": None if null_holding else 50.0, "need": 70.0,
          "sufficient": False, "auto_fx": "off"}
    if skipped:
        m4["skipped"] = skipped
    return {"ok": True, "as_of_kst": as_of, "total_need_usd": 0.0, "total_need_krw": 0.0,
            "accounts": [
                {"name": "토스", "lines": toss_lines},
                {"name": "메리츠", "lines": [
                    {"label": "P", "currency": "USD", "holding": 30.0, "need": 30.0, "sufficient": True, "auto_fx": "off"},
                    {"label": "VR6", "currency": "USD", "holding": 8.0, "need": 18.0, "sufficient": False, "auto_fx": "off"},
                    m4]},
                {"name": "한투", "lines": [{"currency": "USD", "holding": 7.0, "need": 3.0, "sufficient": True, "auto_fx": "off"}]},
                {"name": "빗썸", "lines": [{"currency": "KRW", "holding": 100.0, "need": 100.0, "sufficient": True, "auto_fx": "off"}]},
            ]}


def write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


class Width(unittest.TestCase):
    def test_widths(self):
        self.assertEqual(render.dw("메리츠 4번"), 10)
        self.assertEqual(render.dw("메리츠 SOXL 3번"), 15)
        self.assertEqual(render.dw("확인 불가 ⚠️"), 12)
        self.assertEqual(render.pad("가", 4, "r"), "  가")
        self.assertEqual(render.pad("ab", 5, "c"), " ab  ")


class NeedTable(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "need.json")

    def test_rows_and_totals(self):
        rows, totals = need_table.build_rows(need_doc(skipped=["QLD"]), cfg()["need"],
                                             seed_reader=lambda c: {"total": 1000.0, "day": 20.0})
        labels = [r["label"] for r in rows]
        self.assertEqual(labels, ["토스", "토스", "메리츠 P", "메리츠 VR6", "메리츠 4번", "메리츠 SOXL 3번",
                                  "한투", "빗썸"])
        # USD: 토스 150 + VR6 10 + 4번 20 (한투 0), 바벨·SOXL3 제외 / KRW: 토스 0 (보유가 더 큼), 빗썸 0
        self.assertAlmostEqual(totals["USD"], 150.0 + 10.0 + 20.0)
        self.assertNotIn("KRW", totals)
        self.assertEqual(rows[0]["barbell_ref"]["shortage"], 30.0)
        self.assertNotIn("barbell_ref", rows[1])                 # 바벨 참고는 첫 줄에만
        self.assertEqual(rows[4]["kind"], "meritz4")
        self.assertEqual(rows[4]["skipped"], ["QLD"])
        self.assertEqual(rows[5]["kind"], "soxl3")
        self.assertEqual(rows[5]["soxl"], {"total": 1000.0, "day": 20.0})

    def test_barbell_matches_label_key_only(self):
        d = need_doc()
        d["accounts"][0]["lines"][0]["name"] = "바벨 씨드"       # name 키는 보지 않는다 (Q16: label 키)
        rows, _ = need_table.build_rows(d, cfg()["need"])
        self.assertEqual(rows[0]["shortage"], 150.0)
        self.assertEqual(rows[0]["barbell_ref"]["shortage"], 30.0)

    def test_unknown_meritz_label_falls_back(self):
        d = need_doc()
        d["accounts"][1]["lines"].append({"label": "Z9", "currency": "USD", "holding": 1.0, "need": 5.0,
                                          "sufficient": False, "auto_fx": "off"})
        rows, _ = need_table.build_rows(d, cfg()["need"])
        self.assertIn("메리츠 Z9", [r["label"] for r in rows])

    def test_soxl3_seed_from_settings(self):
        p = os.path.join(tempfile.mkdtemp(), "settings.json")
        write(p, {"total_key_placeholder": 1, "total_krw": 1000, "split_count": 10})   # 자리표시자 숫자
        seed = need_table.read_soxl3_seed({"path": p, "total_key": "total_krw", "split_key": "split_count"})
        self.assertEqual(seed, {"total": 1000.0, "day": 100.0})                       # 당일 = 전체 / 분할 수
        write(p, {"total_krw": 1000, "split_count": 0})
        self.assertIsNone(need_table.read_soxl3_seed({"path": p, "total_key": "total_krw", "split_key": "split_count"}))
        self.assertIsNone(need_table.read_soxl3_seed({"path": "/nonexistent/x.json", "total_key": "a", "split_key": "b"}))
        # 설정 못 읽으면 SOXL 3번 줄만 '확인 불가', 다른 줄은 정상
        rows, _ = need_table.build_rows(need_doc(), cfg()["need"], seed_reader=lambda c: None)
        soxl = [r for r in rows if r["kind"] == "soxl3"][0]
        self.assertEqual(soxl["status"], "unavailable")
        self.assertEqual(render.row_lines(soxl)[1], [render.UNAVAIL])
        self.assertEqual(rows[0]["status"], "ok")

    def test_skipped_absent_and_null_need(self):
        d = need_doc()
        d["accounts"][1]["lines"][2]["need"] = None            # 메리츠 3번 line
        rows, totals = need_table.build_rows(d, cfg()["need"], seed_reader=lambda c: None)
        r = [x for x in rows if x["label"] == "메리츠 4번"][0]
        self.assertEqual(r["status"], "need_null")
        self.assertNotIn("skipped", r)
        short, hold = render.row_lines(r)
        self.assertEqual(short, ["계산 불가"])

    def test_holding_null_reissue_then_ok(self):
        write(self.p, need_doc(null_holding=True))
        calls = []

        def reissue():
            calls.append(1)
            write(self.p, need_doc())
            return True, ""
        slept = []
        res = need_table.collect(cfg(), TODAY, self.p, reissue, sleep=slept.append)
        self.assertEqual(calls, [1])
        self.assertEqual(slept, [])                      # Q21: 동기식이라 기본 대기 없음 (wait_sec=0)
        self.assertTrue(res["null_cause"])
        self.assertFalse(res.get("unavailable"))
        self.assertEqual(res["status"], "ok")

    def test_holding_null_persists(self):
        write(self.p, need_doc(null_holding=True))
        res = need_table.collect(cfg(), TODAY, self.p, lambda: (True, ""), sleep=lambda s: None)
        self.assertTrue(res["unavailable"])
        self.assertEqual(res["status"], "degraded")
        msg = render.need_message(res, TODAY, "t1")
        self.assertIn("일부 계좌 확인 불가 — 문제 있음", msg)
        self.assertIn("확인 불가 ⚠️", msg)

    def test_reissue_failure_runs_once_and_continues(self):
        write(self.p, need_doc(null_holding=True))
        n = []
        res = need_table.collect(cfg(), TODAY, self.p, lambda: (n.append(1) or (False, "권한")),
                                 sleep=lambda s: None)
        self.assertEqual(len(n), 1)
        self.assertEqual(res["status"], "degraded")
        self.assertIn("재발행 실패", render.need_message(res, TODAY, "t1"))

    def test_stale(self):
        write(self.p, need_doc(as_of="2026-11-18 16:30 KST"))
        res = need_table.collect(cfg(), TODAY, self.p, lambda: (False, "x"), sleep=lambda s: None)
        self.assertTrue(res["stale"])
        self.assertIn("2026-11-18 16:30 KST 기준 (오늘 아님)", render.need_message(res, TODAY, "t1"))

    def test_missing_and_broken(self):
        res = need_table.collect(cfg(), TODAY, self.p, lambda: (False, "x"), sleep=lambda s: None)
        self.assertEqual(res["status"], "failed")
        self.assertIsNone(res["null_cause"])
        self.assertIn("need.json 읽기 실패 — 문제 있음", render.need_failed_message(TODAY, "t1"))
        with open(self.p, "w") as f:
            f.write("{broken")
        data, err = need_table.load_need(self.p)
        self.assertIsNone(data)

    def test_table_render_sample(self):
        res = {"status": "ok", "as_of": "2026-11-19 09:05 KST", "stale": False, "totals": {"USD": 170.0},
               "rows": need_table.build_rows(need_doc(skipped=["QLD"]), cfg()["need"],
                                             seed_reader=lambda c: {"total": 1000.0, "day": 20.0})[0]}
        text = render.render_need_table(res["rows"])
        print("\n" + text)
        self.assertIn("바벨 참고", text)
        self.assertIn("QLD 오늘 매수 없음", text)
        self.assertIn("전체", text)
        self.assertIn("당일", text)
        # 계좌명은 줄바꿈 없이 한 줄에 들어간다
        self.assertTrue(any("메리츠 SOXL 3번" in l for l in text.split("\n")))
        # 열 정렬: 모든 줄의 '|' 위치가 같다 (span 줄 제외)
        self.assertLessEqual(render.table_width(text), 46)      # 40칸 + 구분자 2개(3칸씩)


class Streak(unittest.TestCase):
    def test_streak_three_then_resolved(self):
        d = tempfile.mkdtemp()
        st = state.State(d)
        sent = []
        deliver = lambda kind, text: (sent.append((kind, text)) or "sent")
        for i, day in enumerate(["2026-11-17", "2026-11-18", "2026-11-19"]):
            run._update_streak(st, day, {"null_cause": True}, deliver, "r")
        self.assertEqual(st.load_state()["null_reissue_streak"], 3)
        self.assertEqual([k for k, _ in sent], ["streak"])
        run._update_streak(st, "2026-11-19", {"null_cause": True}, deliver, "r")     # 같은 날 재실행: 안 셈
        self.assertEqual(st.load_state()["null_reissue_streak"], 3)
        run._update_streak(st, "2026-11-20", {"null_cause": True}, deliver, "r")     # 4회째: 반복 알림 없음
        self.assertEqual(len(sent), 1)
        run._update_streak(st, "2026-11-23", {"null_cause": False}, deliver, "r")
        self.assertEqual(st.load_state()["null_reissue_streak"], 0)
        self.assertEqual([k for k, _ in sent], ["streak", "streak_resolved"])

    def test_initial_zero_and_unreadable_day(self):
        st = state.State(tempfile.mkdtemp())
        self.assertEqual(st.load_state()["null_reissue_streak"], 0)
        run._update_streak(st, TODAY, {"null_cause": None}, lambda k, t: "sent", "r")
        self.assertEqual(st.load_state()["null_reissue_streak"], 0)


class StateFiles(unittest.TestCase):
    def test_atomic_and_history(self):
        d = tempfile.mkdtemp()
        st = state.State(d)
        st.save_latest({"a": 1}, TODAY)
        self.assertEqual(st.read_latest(), {"a": 1})
        self.assertTrue(os.path.exists(os.path.join(d, "history", TODAY + ".json")))
        self.assertEqual([n for n in os.listdir(d) if n.startswith(".tmp_")], [])

    def test_prev_snapshot_skips_weekend(self):
        st = state.State(tempfile.mkdtemp())
        st.save_snapshot("2026-11-13", {"date": "2026-11-13"})
        st.save_snapshot("2026-11-16", {"date": "2026-11-16"})
        self.assertEqual(st.prev_snapshot("2026-11-17")["date"], "2026-11-16")
        self.assertIsNone(st.prev_snapshot("2026-11-13"))

    def test_prune_90_days(self):
        st = state.State(tempfile.mkdtemp())
        st.save_snapshot("2026-01-01", {})
        st.save_snapshot("2026-11-18", {})
        st.prune(TODAY, 90)
        self.assertIsNone(st.load_snapshot("2026-01-01"))
        self.assertIsNotNone(st.load_snapshot("2026-11-18"))


class Sources(unittest.TestCase):
    def test_toss_retry_max_once(self):
        n = []

        def bad():
            n.append(1)
            raise SourceError("401")
        r = toss.fetch(cfg(), get_holdings=bad)
        self.assertEqual(len(n), 2)                    # 최초 1회 + 재시도 1회, 그 이상 없음
        self.assertEqual(r["status"], "unavailable")

    def test_toss_ok_and_formats(self):
        r = toss.fetch(cfg(), get_holdings=lambda: [{"symbol": "AAA", "quantity": 3}])
        self.assertEqual(r["accounts"]["토스"]["holdings"], {"AAA": 3.0})
        with self.assertRaises(SourceError):
            normalize_holdings("이상한 값")

    def test_kiwoom_fixed_missing_is_failure(self):
        c = cfg()
        c["paths"]["kiwoom_fixed"] = "/nonexistent/kiwoom_fixed.json"
        r = kiwoom.fetch(c, TODAY)
        self.assertEqual(r["status"], "unavailable")

    def test_kiwoom_fixed_ok_and_elapsed(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "kf.json")
        write(p, {"000001": 5, "000002": 7})
        c = cfg()
        c["paths"]["kiwoom_fixed"] = p
        r = kiwoom.fetch(c, TODAY)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["meta"]["elapsed_days"], 13)
        write(p, {"A000001": 5})                          # 6자리 아님 → 실패
        self.assertEqual(kiwoom.fetch(c, TODAY)["status"], "unavailable")

    def test_kiwoom_api_falls_back_to_last_api_not_fixed(self):
        d = tempfile.mkdtemp()
        st = state.State(d)
        c = cfg()
        c["kiwoom"]["mode"] = "api"
        ok = kiwoom.fetch(c, "2026-12-10", st, api_fetch=lambda: {"A000001": 4})
        self.assertEqual(ok["accounts"]["키움"]["holdings"], {"000001": 4.0})

        def bad():
            raise SourceError("down")
        r = kiwoom.fetch(c, "2026-12-11", st, api_fetch=bad)
        self.assertEqual(r["status"], "partial")
        self.assertEqual(r["meta"]["stale_api_date"], "2026-12-10")
        st2 = state.State(tempfile.mkdtemp())
        self.assertEqual(kiwoom.fetch(c, "2026-12-11", st2, api_fetch=bad)["status"], "unavailable")


def ok_result(h, mode=None):
    r = {"status": "ok", "accounts": {k: {"status": "ok", "holdings": v, "note": ""} for k, v in h.items()}}
    if mode:
        r["meta"] = {"mode": mode, "as_of": "2026-11-06", "elapsed_days": 13, "fixed_sha": "aa"}
    return r


class Portfolio(unittest.TestCase):
    def snap(self, date, toss_h, laoer_h, kw=None, mode="fixed", prices=None, sha="aa"):
        res = {"toss": ok_result({"토스": toss_h}),
               "meritz": ok_result({"메리츠 적립": {}, "메리츠 속쓸": laoer_h}),
               "kiwoom": ok_result({"키움": kw or {"000001": 5.0}}, mode)}
        res["kiwoom"]["meta"]["fixed_sha"] = sha
        return res, portfolio.build_snapshot(date, "g", res, prices)

    def test_diff_changes_and_incomparable(self):
        _, prev = self.snap("2026-11-18", {"AAA": 3.0}, {"SOXL": 63.0})
        res, _ = self.snap("2026-11-19", {"AAA": 5.0}, {"SOXL": 63.0})
        res["meritz"]["accounts"]["메리츠 속쓸"] = {"status": "unavailable", "holdings": {}, "note": "x"}
        res["meritz"]["status"] = "partial"
        sec, snap = portfolio.collect(cfg(), "2026-11-19", "g", prev, res, None)
        self.assertEqual(sec["changes"], [{"account": "토스", "ticker": "AAA", "prev_qty": 3.0,
                                           "today_qty": 5.0, "delta": 2.0}])
        self.assertEqual(sec["incomparable"], ["메리츠 속쓸"])
        self.assertEqual(sec["status"], "degraded")
        msg = render.portfolio_message(sec, "t1")
        print("\n" + msg)
        self.assertIn("(+2주)", msg)
        self.assertIn("비교 불가 ⚠️", msg)
        self.assertIn("키움    고정(2026-11-06) — 변동 비교 안 함", msg)
        self.assertIn("(목표 미확정)", msg)

    def test_first_snapshot_and_no_change(self):
        res, _ = self.snap("2026-11-19", {"AAA": 3.0}, {"SOXL": 63.0})
        sec, _ = portfolio.collect(cfg(), "2026-11-19", "g", None, res, None)
        self.assertTrue(sec["first_snapshot"])
        self.assertIn("첫 기준 스냅샷", render.portfolio_message(sec, "t1"))
        _, prev = self.snap("2026-11-18", {"AAA": 3.0}, {"SOXL": 63.0})
        sec2, _ = portfolio.collect(cfg(), "2026-11-19", "g", prev, res, None)
        self.assertEqual(sec2["changes"], [])
        self.assertIn("변동 없음", render.portfolio_message(sec2, "t1"))

    def test_kiwoom_recapture_flag(self):
        _, prev = self.snap("2026-11-18", {"AAA": 3.0}, {}, sha="aa")
        res, _ = self.snap("2026-11-19", {"AAA": 3.0}, {}, sha="bb")
        sec, _ = portfolio.collect(cfg(), "2026-11-19", "g", prev, res, None)
        self.assertTrue(sec["kiwoom"]["recaptured"])
        self.assertIn("캡처 갱신으로 바뀐 값", render.portfolio_message(sec, "t1"))

    def targets(self):
        return {"targets_pct": {"gold": 10, "stock": 90}, "ticker_to_bucket": {"AAA": "stock", "GLD": "gold"},
                "kiwoom_default_bucket": "stock", "kiwoom_gold_tickers": ["000009"], "confirmed": False}

    def test_buckets_dash_without_prices(self):
        res, _ = self.snap("2026-11-19", {"AAA": 3.0}, {})
        _, prev = self.snap("2026-11-18", {"AAA": 3.0}, {})
        sec, _ = portfolio.collect(cfg(), "2026-11-19", "g", prev, res, self.targets())
        self.assertTrue(all(b["today_pct"] is None for b in sec["buckets"]))
        self.assertIn("버킷 %는 가격·일부 소스 미확인으로 생략", render.portfolio_message(sec, "t1"))

    def test_buckets_with_prices_when_complete(self):
        c = cfg()
        c["portfolio"]["denominator_complete"] = True
        c["portfolio"]["bucket_highlight_pp"] = 3
        px = {"AAA": 10.0, "GLD": 10.0, "000001": 10.0, "000009": 10.0}
        res, _ = self.snap("2026-11-19", {"AAA": 3.0, "GLD": 1.0}, {}, kw={"000001": 6.0}, prices=px)
        res2, prev = self.snap("2026-11-18", {"AAA": 3.0, "GLD": 1.0}, {}, kw={"000001": 3.0}, prices=px)
        sec, _ = portfolio.collect(c, "2026-11-19", "g", prev, res, self.targets(), px)
        by = {b["key"]: b for b in sec["buckets"]}
        self.assertAlmostEqual(by["gold"]["today_pct"], 10.0, places=3)
        self.assertAlmostEqual(by["gold"]["prev_pct"], 10 / 70 * 100, places=3)
        self.assertTrue(by["gold"]["highlight"])

    def test_targets_missing_ok(self):
        self.assertIsNone(portfolio.load_targets("/nonexistent/x.json"))


class Tg(unittest.TestCase):
    def test_split_keeps_pre_balanced(self):
        body = "\n".join("행 %d %s" % (i, "가" * 30) for i in range(200))
        text = "머리\n<pre>" + body + "</pre>\n꼬리"
        parts = tg_send.split_message(text, limit=1000)
        self.assertGreater(len(parts), 1)
        for p in parts:
            self.assertLessEqual(len(p), 1000)
            self.assertEqual(p.count("<pre>"), p.count("</pre>"))

    def test_send_retries_three_times_then_fails(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "t.json")
        write(p, {"token": "T", "chat_id": 1})
        calls, naps = [], []

        def opener(req, timeout=0):
            calls.append(1)
            raise OSError("net")
        self.assertFalse(tg_send.send("hi", p, opener=opener, sleep=naps.append))
        self.assertEqual(len(calls), 4)
        self.assertEqual(naps, [2, 5, 10])
        self.assertFalse(tg_send.send("hi", os.path.join(d, "none.json")))


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.need = os.path.join(self.d, "need.json")
        write(self.need, need_doc(skipped=["QLD"]))
        self.sd = os.path.join(self.d, "state")
        self.kf = os.path.join(self.d, "kf.json")
        write(self.kf, {"000001": 5})
        cfgp = os.path.join(self.d, "config.json")
        c = cfg()
        c["paths"]["kiwoom_fixed"] = self.kf
        write(cfgp, c)
        self.cfgp = cfgp
        self.sent = []
        self.fetchers = {"toss": lambda: ok_result({"토스": {"AAA": 3.0}}),
                         "meritz": lambda: ok_result({"메리츠 적립": {}, "메리츠 속쓸": {"SOXL": 1.0}}),
                         "kiwoom": lambda: kiwoom.fetch(c, TODAY)}
        self.deps = {"send": lambda t: (self.sent.append(t) or True), "run_id": "abc123",
                     "sleep": lambda s: None, "reissue": lambda: (True, ""), "fetchers": self.fetchers}

    def args(self, *extra):
        return ["all", "--config", self.cfgp, "--state-dir", self.sd, "--need-json", self.need,
                "--now", NOW] + list(extra)

    def test_dry_no_side_effects(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run.main(self.args("--dry"), self.deps)
        self.assertEqual(code, 0)
        self.assertEqual(self.sent, [])
        self.assertFalse(os.path.exists(self.sd))
        out = buf.getvalue()
        self.assertIn("필요 달러", out)
        self.assertIn("포트폴리오 전환", out)
        self.assertIn('"schema_version": 1', out)

    def test_real_run_sends_two_messages_and_writes_latest(self):
        self.assertEqual(run.main(self.args(), self.deps), 0)
        self.assertEqual(len(self.sent), 2)                    # 필요 달러 / 포트폴리오 두 메시지
        latest = json.load(open(os.path.join(self.sd, "briefing_latest.json"), encoding="utf-8"))
        self.assertEqual(latest["telegram"], {"need": "sent", "portfolio": "sent"})
        self.assertEqual(latest["schema_version"], 1)
        self.assertEqual(latest["need"]["status"], "ok")
        self.assertTrue(os.path.exists(os.path.join(self.sd, "history", TODAY + ".json")))
        self.assertTrue(os.path.exists(os.path.join(self.sd, "snapshots", TODAY + ".json")))
        # 같은 날 재실행: 마커로 막힘 → 전송 추가 없음
        run.main(self.args(), self.deps)
        self.assertEqual(len(self.sent), 2)
        # --force 는 허용
        run.main(self.args("--force"), self.deps)
        self.assertEqual(len(self.sent), 4)

    def test_telegram_failure_pending_then_late_failed(self):
        self.deps["send"] = lambda t: False
        run.main(self.args(), self.deps)
        latest = json.load(open(os.path.join(self.sd, "briefing_latest.json"), encoding="utf-8"))
        self.assertEqual(latest["telegram"]["need"], "pending")
        late_args = ["all", "--config", self.cfgp, "--state-dir", self.sd, "--need-json", self.need,
                     "--now", "2026-11-19T04:30:00"]       # 12:30 CST
        run.main(late_args, self.deps)
        latest = json.load(open(os.path.join(self.sd, "briefing_latest.json"), encoding="utf-8"))
        self.assertEqual(latest["telegram"]["need"], "failed")

    def test_late_message_marker(self):
        late_args = ["need", "--config", self.cfgp, "--state-dir", self.sd, "--need-json", self.need,
                     "--now", "2026-11-19T04:30:00"]
        run.main(late_args, self.deps)
        self.assertIn("오늘 브리핑 늦음", self.sent[0])

    def test_source_failure_does_not_block_need(self):
        def boom():
            raise RuntimeError("x")
        self.fetchers["toss"] = boom
        self.fetchers["meritz"] = boom
        run.main(self.args(), self.deps)
        latest = json.load(open(os.path.join(self.sd, "briefing_latest.json"), encoding="utf-8"))
        self.assertEqual(latest["need"]["status"], "ok")
        self.assertEqual(latest["portfolio"]["status"], "degraded")

    def test_need_failure_does_not_block_portfolio(self):
        os.unlink(self.need)
        self.deps["reissue"] = lambda: (False, "권한")
        run.main(self.args(), self.deps)
        latest = json.load(open(os.path.join(self.sd, "briefing_latest.json"), encoding="utf-8"))
        self.assertEqual(latest["need"]["status"], "failed")
        self.assertEqual(latest["portfolio"]["status"], "ok")
        self.assertIn("need.json 읽기 실패", self.sent[0])


class Reissue(unittest.TestCase):
    """Q21 정정: --print stdout JSON 을 받아 need.json 에 직접 쓴다. systemctl start 는 쓰지 않는다."""
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.need = os.path.join(self.d, "need.json")
        self.stub = os.path.join(self.d, "stub_print.py")

    def cfg_with(self, body):
        with open(self.stub, "w", encoding="utf-8") as f:
            f.write(body)
        c = cfg()
        c["reissue"] = {"cmd": [sys.executable, self.stub, "--print"], "wait_sec": 0, "timeout_sec": 10}
        return c

    def sha(self):
        with open(self.need, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def test_default_cmd_is_print_without_systemctl_or_sudo(self):
        cmd = cfg()["reissue"]["cmd"]
        self.assertEqual(cmd[1:], ["/opt/bot-office/office_briefing.py", "--print"])
        self.assertNotIn("systemctl", " ".join(cmd))
        self.assertNotIn("sudo", cmd)
        self.assertEqual(cfg()["reissue"]["wait_sec"], 0)

    def test_valid_stdout_is_written_to_need_json(self):
        write(self.need, need_doc(as_of="2026-11-18 16:30 KST", null_holding=True))
        c = self.cfg_with("import json,sys\nprint(json.dumps(%r))\n" % need_doc())
        os.chmod(self.need, 0o640)
        ok, msg = run.reissue_cmd(c, self.need)
        self.assertTrue(ok, msg)
        data, err = need_table.load_need(self.need)
        self.assertIsNone(err)
        self.assertEqual(data["as_of_kst"], "2026-11-19 09:05 KST")
        self.assertFalse(need_table.has_null_holding(data))
        self.assertEqual(os.stat(self.need).st_mode & 0o777, 0o640)          # 기존 권한 유지
        self.assertEqual([n for n in os.listdir(self.d) if n.startswith(".tmp_")], [])

    def test_broken_json_is_not_written(self):
        write(self.need, need_doc(null_holding=True))
        before = self.sha()
        ok, msg = run.reissue_cmd(self.cfg_with("print('{broken')\n"), self.need)
        self.assertFalse(ok)
        self.assertIn("JSON", msg)
        self.assertEqual(self.sha(), before)

    def test_wrong_structure_and_nonzero_exit_not_written(self):
        write(self.need, need_doc())
        before = self.sha()
        ok, msg = run.reissue_cmd(self.cfg_with("print('{\"ok\": true}')\n"), self.need)
        self.assertFalse(ok)
        self.assertIn("구조 이상", msg)
        ok, msg = run.reissue_cmd(self.cfg_with("import sys\nprint('{\"accounts\": []}')\nsys.exit(3)\n"), self.need)
        self.assertFalse(ok)
        self.assertIn("종료코드 3", msg)
        self.assertEqual(self.sha(), before)

    def test_timeout_and_missing_command(self):
        write(self.need, need_doc())
        before = self.sha()
        c = self.cfg_with("import time\ntime.sleep(5)\n")
        c["reissue"]["timeout_sec"] = 1
        self.assertEqual(run.reissue_cmd(c, self.need), (False, "시간초과"))
        c["reissue"]["cmd"] = ["/nonexistent/python3", "x"]
        ok, msg = run.reissue_cmd(c, self.need)
        self.assertFalse(ok)
        self.assertEqual(self.sha(), before)

    def test_end_to_end_stale_reissue_then_fresh(self):
        write(self.need, need_doc(as_of="2026-11-18 16:30 KST"))
        c = self.cfg_with("import json\nprint(json.dumps(%r))\n" % need_doc())
        res = need_table.collect(c, TODAY, self.need, lambda: run.reissue_cmd(c, self.need), sleep=lambda s: None)
        self.assertTrue(res["reissued"] and res["reissue_ok"])
        self.assertFalse(res["stale"])
        self.assertEqual(res["status"], "ok" if not res.get("unavailable") else "degraded")


class TossAdapter(unittest.TestCase):
    """Q18: TossApiClient(base_dir=...) · await 호출 · await client.close(). try_acquire 를 직접 부르지 않는다."""
    def make_module(self, body):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "toss_api.py"), "w", encoding="utf-8") as f:
            f.write(body)
        sys.modules.pop("toss_api", None)
        self.addCleanup(lambda: sys.modules.pop("toss_api", None))
        self.addCleanup(lambda: sys.path.remove(d) if d in sys.path else None)
        c = cfg()
        c["paths"]["toss_dir"] = d
        return c, d

    def test_async_holdings_close_and_base_dir(self):
        c, d = self.make_module(
            "CLOSED = []\nBASE = []\n"
            "class TossApiClient:\n"
            "    def __init__(self, base_dir=None):\n        BASE.append(base_dir)\n"
            "    async def get_holdings(self):\n        return {'AAA': 3}\n"
            "    async def close(self):\n        CLOSED.append(1)\n")
        r = toss.fetch(c)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["accounts"]["토스"]["holdings"], {"AAA": 3.0})
        import toss_api
        self.assertEqual(toss_api.BASE, [d])
        self.assertEqual(toss_api.CLOSED, [1])

    def test_failure_still_closes_and_retries_once(self):
        c, d = self.make_module(
            "CLOSED = []\nCALLS = []\n"
            "class TossApiClient:\n"
            "    def __init__(self, base_dir=None):\n        pass\n"
            "    async def get_holdings(self):\n        CALLS.append(1)\n        raise RuntimeError('401')\n"
            "    async def close(self):\n        CLOSED.append(1)\n")
        r = toss.fetch(c)
        self.assertEqual(r["status"], "unavailable")
        import toss_api
        self.assertEqual(len(toss_api.CALLS), 2)                 # 최초 1회 + 재시도 1회
        self.assertEqual(len(toss_api.CLOSED), 2)

    def test_missing_get_holdings_is_source_failure(self):
        c, d = self.make_module(
            "class TossApiClient:\n    def __init__(self, base_dir=None):\n        pass\n"
            "    async def close(self):\n        pass\n")
        r = toss.fetch(c)
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("get_holdings", r["accounts"]["토스"]["note"])

    def test_no_try_acquire_in_adapter(self):
        with open(toss.__file__, encoding="utf-8") as f:
            code = [l for l in f.read().split("\n") if not l.lstrip().startswith("#")]
        self.assertNotIn("try_acquire", "\n".join(code))
        self.assertNotIn("toss_token_share", "\n".join(code))


class TargetsFile(unittest.TestCase):
    """Q19: portfolio_targets.json — 금 버킷 키 gold, targets_pct 는 % 단위 (5 = 5%), confirmed=false."""
    def path(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for p in (os.path.join(here, "portfolio_targets.json"),
                  os.path.join(here, "..", "..", "sources", "portfolio_targets.json")):
            if os.path.exists(p):
                return p
        self.skipTest("portfolio_targets.json 없음 (Muse 가 staging 때 올린다)")

    def test_loads_and_gold_key(self):
        t = portfolio.load_targets(self.path())
        self.assertIsNotNone(t)
        self.assertIn(cfg()["portfolio"]["gold_bucket_key"], t["targets_pct"])
        self.assertEqual(cfg()["portfolio"]["gold_bucket_key"], "gold")
        self.assertIs(t["confirmed"], False)
        tp = t["targets_pct"]
        # % 단위: 생활비 분리(living_expense_separate)를 뺀 나머지 합이 100. 파일 전체 합은 101 (Muse 확인 요청, VERIFY 5절)
        self.assertAlmostEqual(sum(v for k, v in tp.items() if k != "living_expense_separate"), 100.0)
        self.assertAlmostEqual(sum(tp.values()), 101.0)
        self.assertEqual(t["ticker_to_bucket"]["IAU"], "gold")
        self.assertIsNone(cfg()["portfolio"]["bucket_highlight_pp"])             # Q20

    def test_kiwoom_gold_ticker_is_code(self):
        """Q26: 키움 금현물(ACE KRX금현물 ETF)은 6자리 종목코드 411060 으로 금 버킷에 간다 (이름 ACE_KRX_GOLD 는 주석에만)."""
        with open(self.path(), encoding="utf-8") as fh:
            t = json.load(fh)
        self.assertIn("411060", t["kiwoom_gold_tickers"])
        self.assertNotIn("ACE_KRX_GOLD", t["kiwoom_gold_tickers"])
        self.assertTrue(all(isinstance(x, str) and len(x) == 6 and x.isdigit() for x in t["kiwoom_gold_tickers"]))

    def test_gold_bucket_percent_calc(self):
        t = portfolio.load_targets(self.path())
        snap = {"accounts": {"토스": {"source": "toss", "status": "ok", "holdings": {"IAU": 1.0, "SOXL": 3.0}, "note": ""}},
                "prices": {"IAU": 100.0, "SOXL": 100.0}}
        vals, complete = portfolio.bucket_values(snap, t, "gold")
        self.assertTrue(complete)
        pc = portfolio.pcts(vals, complete, True)
        self.assertAlmostEqual(pc["gold"], 25.0)
        self.assertAlmostEqual(pc["stock"], 75.0)


if __name__ == "__main__":
    unittest.main()
