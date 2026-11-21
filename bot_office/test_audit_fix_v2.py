# audit-fix-v2 사무실(bot_office) 시험: 4번 팬딩 가격표(4-1·4-2·4-3), 8번 비서, 9번 업데이트 비서, SGOV(office_sgov) 항목은 아래 섹션별.
# 실행: python3 -I -m pytest -q test_audit_fix_v2.py  (이 파일이 있는 폴더에서)
import contextlib, os, sys, types
from datetime import datetime, timedelta, timezone
from unittest import mock
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KST = timezone(timedelta(hours=9))


# ============================================================ 4번 팬딩 가격표 (fanding_fetch_server.py)
@pytest.fixture()
def ffs():
    import fanding_fetch_server as f
    return f

def test_4_2_logged_out_text_detected(ffs):
    assert ffs.looks_logged_out_text("로그인하고 팬딩을 시작하세요 익명의 팬") is True
    assert ffs.looks_logged_out_text("로그인하고 ... 로그아웃") is False
    assert ffs.looks_logged_out_text("가격표 2026-11-20") is False

def test_4_1_title_rule_rejects_non_price_post(ffs):
    sc = dict(ffs.DEFAULTS, post_title_regex=r"가격표")
    ok, why = ffs.judge_post("공지사항", "본문", sc, datetime(2026, 11, 20).date())
    assert ok is False and "제목" in why
    ok, _ = ffs.judge_post("11/20 가격표", "본문", sc, datetime(2026, 11, 20).date())
    assert ok is True

def test_4_1_default_rules_keep_old_behavior(ffs):
    ok, _ = ffs.judge_post("아무 제목", "2020-01-01", dict(ffs.DEFAULTS), datetime(2026, 11, 20).date())
    assert ok is True

def test_4_1_stale_date_rejected_when_configured(ffs):
    sc = dict(ffs.DEFAULTS, post_max_age_days=3)
    ok, why = ffs.judge_post("t", "작성 2026.11.01", sc, datetime(2026, 11, 20).date())
    assert ok is False and "오래" in why
    ok, _ = ffs.judge_post("t", "날짜 없음", sc, datetime(2026, 11, 20).date())
    assert ok is True      # 날짜를 못 읽으면 통과 (기록만)

def test_4_1_image_ambiguity_warns_and_aspect_filters(ffs):
    sc = dict(ffs.DEFAULTS)
    best, warn = ffs.pick_price_image([{"w": 1000, "h": 2000}, {"w": 1000, "h": 1900}], sc)
    assert best["h"] == 2000 and "비슷" in warn
    best, warn = ffs.pick_price_image([{"w": 1000, "h": 2000}, {"w": 500, "h": 500}], sc)
    assert warn == ""
    sc2 = dict(ffs.DEFAULTS, image_aspect_max=1.0)       # 세로가 더 긴 이미지만
    best, _ = ffs.pick_price_image([{"w": 3000, "h": 1000}, {"w": 800, "h": 1200}], sc2)
    assert (best["w"], best["h"]) == (800, 1200)

def test_4_1_fetch_once_falls_through_to_next_candidate(ffs):
    sc = dict(ffs.DEFAULTS)
    @contextlib.contextmanager
    def fake_browser(sc_): yield object()
    calls = []
    def fake_largest(ctx, sc_, post):
        calls.append(post)
        return (None, "skip:제목이 가격표 글 형식이 아님") if post.endswith("/10") else (b"IMG", "")
    with mock.patch.object(ffs, "browser", fake_browser), \
         mock.patch.object(ffs, "find_posts", lambda ctx, sc_: ({10: "u/10", 9: "u/9"}, {})), \
         mock.patch.object(ffs, "largest_image", fake_largest):
        r = ffs.fetch_once(5, sc)
    assert r["kind"] == "ok" and r["post_id"] == 9, r

def _routine(ffs, now_dt, expected):
    clock = {"t": now_dt}
    fetch_calls = []
    def now(): return clock["t"]
    def sleep(s): clock["t"] += timedelta(seconds=s)
    def fetch(k): fetch_calls.append(k); return {"kind": "no_new"}
    st = {"last_post_id": 5}
    res = ffs.routine(st, now=now, sleep=sleep, fetch=fetch, send=lambda *a: None, note=lambda *a: None, paused=lambda: False,
                      expected=expected, deadline=now_dt.replace(hour=11, minute=0), retry_at=now_dt.replace(hour=9, minute=0), poll_s=300)
    return res, fetch_calls, st

def test_4_3_no_skip_day_weekend_still_polls(ffs):
    # 풀이님 결정(2026-11-20): '가격표 안 받는 날' 개념 없음 — 금요일 표(2026-11-20)도 토요일 아침에 접속한다
    res, calls, st = _routine(ffs, datetime(2026, 11, 21, 8, 0, tzinfo=KST), "2026-11-20")
    assert len(calls) > 0 and res == "deadline" and "last_skip" not in st

def test_4_3_no_skip_day_function_removed(ffs):
    assert not hasattr(ffs, "table_due_date")


# ============================================================ 5-7 SGOV 알림 (office_sgov.alerts_pass)
import json, time as _time
from pathlib import Path

def _mk_alert(bridge, aid, ts, kind="calendar_range"):
    (bridge / "alerts").mkdir(parents=True, exist_ok=True)
    a = {"id": aid, "from": "meritz_dca_bot", "text": "원문 " + aid[:4], "ts": ts, "kind": kind, "ts_kst": "2026-11-18 09:00"}
    (bridge / "alerts" / f"alert_{aid}.json").write_text(json.dumps(a), encoding="utf-8")

class _TG:
    def __init__(self, ok=True): self.ok, self.sent = ok, []
    def send(self, text, *a, **k):
        self.sent.append(text)
        return {"message_id": 7} if self.ok else None

def test_5_7_stale_alert_is_resent_as_summary_not_dropped_silently(tmp_path):
    import office_sgov as osg
    aid = "a" * 32
    _mk_alert(tmp_path, aid, _time.time() - 3 * 86400)
    tg = _TG(ok=True)
    with mock.patch.object(osg, "BRIDGE", tmp_path):
        osg.alerts_pass(tg, now=_time.time())
    assert len(tg.sent) == 1 and "넘게 못 갔어요" in tg.sent[0]            # 요약 재알림 1번
    mark = json.loads((tmp_path / "alerts_sent" / f"sent_{aid}.json").read_text())
    assert mark.get("status") == "expired" or "expired" in json.dumps(mark)

def test_5_7_summary_send_failure_keeps_alert_for_next_tick(tmp_path):
    import office_sgov as osg
    aid = "b" * 32
    _mk_alert(tmp_path, aid, _time.time() - 3 * 86400)
    with mock.patch.object(osg, "BRIDGE", tmp_path):
        osg.alerts_pass(_TG(ok=False), now=_time.time())
        assert not (tmp_path / "alerts_sent" / f"sent_{aid}.json").exists()  # 못 보냈으면 표시 안 함
        tg2 = _TG(ok=True)
        osg.alerts_pass(tg2, now=_time.time())
    assert len(tg2.sent) == 1

def test_5_7_fresh_alert_still_sent_normally(tmp_path):
    import office_sgov as osg
    aid = "c" * 32
    _mk_alert(tmp_path, aid, _time.time() - 60)
    tg = _TG()
    with mock.patch.object(osg, "BRIDGE", tmp_path):
        n = osg.alerts_pass(tg, now=_time.time())
    assert n == 1 and tg.sent == ["원문 cccc"]


# ============================================================ 8번 비서 · 브리핑 (office_briefing.py · office_secretary.py)
import json as _json
from datetime import date as _date

@pytest.fixture()
def ob():
    import office_briefing as o
    return o

def _sgov_env(tmp_path, ob, **sg):
    (tmp_path / "etc/meritz-accum").mkdir(parents=True)
    (tmp_path / "etc/meritz-accum/settings.json").write_text(_json.dumps({"enabled": True, "dry_run": False, "state_dir": "/var/lib/meritz-dca"}))
    d = tmp_path / "var/lib/meritz-dca"; d.mkdir(parents=True)
    base = {"enabled": True, "tranches_done": 1, "tranches_total": 10, "tranche_usd": 100.0, "first_tranche_usd": 100.0,
            "next_due_date": "2026-11-19", "wait_usd": 0.0}
    base.update(sg)
    (d / "dca_config.json").write_text(_json.dumps({"sgov": base}))
    return mock.patch.object(ob, "R", tmp_path)

_NOW = datetime(2026, 11, 18, 9, 0, tzinfo=KST)

def test_8_1_sgov_need_includes_wait_usd(tmp_path, ob):
    with _sgov_env(tmp_path, ob, wait_usd=5.0):
        line = ob._sgov_need_line(_NOW, 50.0, "off")
    assert line is not None and abs(line["need"] - 105.0) < 1e-9, line

def test_8_1_without_wait_usd_unchanged(tmp_path, ob):
    with _sgov_env(tmp_path, ob):
        assert abs(ob._sgov_need_line(_NOW, 50.0, "off")["need"] - 100.0) < 1e-9

def test_8_2_none_first_tranche_does_not_crash(tmp_path, ob):
    with _sgov_env(tmp_path, ob, tranches_done=0, first_tranche_usd=None):
        assert ob._sgov_need_line(_NOW, 50.0, "off") is None          # TypeError 로 멈추지 않음

def test_8_2_none_wait_usd_ok(tmp_path, ob):
    with _sgov_env(tmp_path, ob, wait_usd=None):
        assert abs(ob._sgov_need_line(_NOW, 50.0, "off")["need"] - 100.0) < 1e-9

def test_8_3_calendar_known_and_need_warning(ob):
    assert ob.calendar_known(_date(2027, 5, 3)) and not ob.calendar_known(_date(2029, 1, 3))
    toss = types.SimpleNamespace(buying_power=lambda c: 0.0)
    def sdc(now, info): info.update(toss=toss, usd=0.0, total=0.0, master=False, krw_need=0.0)
    with mock.patch.object(ob, "section_dollar_check", sdc), mock.patch.object(ob, "barbell_seed_line", lambda *a: None), \
         mock.patch.object(ob, "meritz_fetch", lambda: []), mock.patch.object(ob, "_sgov_need_line", lambda *a: None), \
         mock.patch.object(ob, "kis_balances", lambda: {}), mock.patch.object(ob, "_hantu_need", lambda: None), \
         mock.patch.object(ob, "bithumb_accounts", lambda: {}), mock.patch.object(ob, "_bithumb_need", lambda *a: None):
        out_in = ob.need_data(datetime(2026, 11, 18, 9, 0, tzinfo=KST))
        out_out = ob.need_data(datetime(2029, 1, 3, 9, 0, tzinfo=KST))
    assert "warnings" not in out_in and out_out.get("warnings") and "2029" in out_out["warnings"][0]


def test_8_5_handler_error_keeps_offset_then_skips_after_retries():
    import office_secretary as sec
    tg = types.SimpleNamespace(chat="1")
    ups = [{"update_id": 10, "message": {"chat": {"id": 1}}}, {"update_id": 11, "message": {"chat": {"id": 1}}}]
    calls = []
    def boom(tg_, st, m):
        calls.append(1); raise RuntimeError("x")
    fails = {}
    with mock.patch.object(sec, "handle_message", boom):
        off, retry = sec.process_updates(tg, {}, ups, 10, fails)
        assert (off, retry) == (10, True) and len(calls) == 1             # offset 유지 · 뒤 입력은 이번에 처리 안 함
        sec.process_updates(tg, {}, ups, 10, fails)
        off, retry = sec.process_updates(tg, {}, ups, 10, fails)           # 3번째 오류 → 건너뜀
        assert off == 11 and retry is True                                  # 10 건너뛰고 11 도 오류 → 11 에서 멈춤

def test_8_5_success_advances_offset():
    import office_secretary as sec
    tg = types.SimpleNamespace(chat="1")
    ups = [{"update_id": 10, "message": {"chat": {"id": 1}}}, {"update_id": 11, "message": {"chat": {"id": 1}}}]
    with mock.patch.object(sec, "handle_message", lambda *a: None):
        assert sec.process_updates(tg, {}, ups, None, {}) == (12, False)


# ============================================================ 9번 업데이트 비서 (bot_updater.py)
import inspect

@pytest.fixture()
def bu(tmp_path, monkeypatch):
    monkeypatch.setenv("U_REPO", str(tmp_path))
    sys.modules.pop("bot_updater", None)
    import bot_updater
    yield bot_updater
    sys.modules.pop("bot_updater", None)

def test_9_1_changelog_failure_returns_error_and_keeps_old_file(bu, tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# 옛 변경 기록\n\n## v1.0.0 · x (KST)\n- 파일: a\n", encoding="utf-8")
    with mock.patch.object(bu.os, "chown", side_effect=PermissionError("no")):
        err = bu.write_changelog(str(tmp_path), "테스트봇", "v1.0.1", "2026-11-20 10:00", ["a.py"], "msg", "staging")
    assert err and "PermissionError" in err
    assert "## v1.0.0" in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") and "v1.0.1" not in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert not (tmp_path / "CHANGELOG.md.tmp").exists()

def test_9_1_changelog_success_prepends_entry(bu, tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# 옛 변경 기록\n\n## v1.0.0 · x (KST)\n- 파일: a\n", encoding="utf-8")
    with mock.patch.object(bu.os, "chown", lambda *a: None):
        assert bu.write_changelog(str(tmp_path), "테스트봇", "v1.0.1", "2026-11-20 10:00", ["a.py"], "msg", "staging") is None
    t = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert t.startswith("# 테스트봇 변경 기록\n\n## v1.0.1") and "## v1.0.0" in t

def test_9_2_staging_not_pushed_when_main_push_fails(bu):
    calls = []
    def g(*a):
        calls.append(a); return (1, "rejected") if "HEAD:main" in a else (0, "")
    rc, out, staged = bu.push_main_then_staging(["t-v1"], "fix/x", False, False, git_fn=g)
    assert rc == 1 and staged is False
    assert not any("HEAD:staging" in c for c in calls), calls

def test_9_2_staging_pushed_after_main_success_and_branch_deleted(bu):
    calls = []
    def g(*a):
        calls.append(a); return 0, ""
    rc, out, staged = bu.push_main_then_staging(["t-v1"], "fix/x", False, False, git_fn=g)
    assert rc == 0 and staged is True
    assert any("--delete" in c for c in calls) and calls[-1][-1] == "HEAD:staging"

def test_9_apply_uses_the_new_helpers(bu):
    src = inspect.getsource(bu.apply)
    assert "write_changelog(" in src and "push_main_then_staging(" in src
    assert 'git("push", "-q", "-f", "origin", "HEAD:staging")' not in src
