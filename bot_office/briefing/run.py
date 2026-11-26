# briefing/run.py — 진입점: python3 -m briefing.run [need|all] [--force] [--dry]
# 한 번 실행이 briefing_latest.json 을 만든다 (설계 6절). 보내는 건 필요 달러(need·streak 알림)뿐이다.
# 포트폴리오 전환 브리핑은 2026-11-26에 삭제됐다 (풀이님 결정: 메시지 중단 + 코드 삭제).
# 텔레그램 방: 필요 달러 = paths.telegram_need_cfg (새 봇·새 전용 방). 9번 설정(paths.telegram_cfg)은
# 새 봇과 같은 방인지 가드 대조용으로만 쓴다 (make_need_sender). 두 설정은 섞지 않는다.
# --dry: 텔레그램 전송·재발행 실행·상태/마커 저장을 하지 않고 화면에 출력만 한다.
# 시험용 보조 옵션(설계에 없음, 기본 동작 불변): --config --state-dir --need-json --now
import argparse
import datetime as dt
import json
import os
import secrets
import subprocess
import sys
import time

from . import need_table, render, state as st_mod, tg_send
from .state import State, expand

KST = dt.timezone(dt.timedelta(hours=9))
CST = dt.timezone(dt.timedelta(hours=8))   # CST = Asia/Taipei (UTC+8, 서머타임 없음, Q3)


def load_config(path=None):
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="briefing.run")
    ap.add_argument("stage", nargs="?", default="all", choices=["need", "all"])   # all = need (포트폴리오 삭제됨)
    ap.add_argument("--force", action="store_true", help="sent 마커를 무시하고 다시 보냄")
    ap.add_argument("--dry", action="store_true", help="전송·저장·재발행 없이 출력만")
    ap.add_argument("--config")
    ap.add_argument("--state-dir")
    ap.add_argument("--need-json")
    ap.add_argument("--now", help="시험용 현재 시각(ISO, UTC 기준)")
    return ap.parse_args(argv)


FANDING_PREFIX = "[FANDING_NEED]"      # office_briefing._fanding_state 가 stderr 에 남기는 원인 줄 머리말


class ReissueResult(tuple):
    """(ok, 실패 이유) 2-튜플 그대로 (풀기·비교 호환) + 진단용 fanding_causes (원인 줄 목록)."""

    def __new__(cls, ok, msg, fanding_causes=None):
        self = super().__new__(cls, (ok, msg))
        self.fanding_causes = list(fanding_causes or [])
        return self


def fanding_cause_lines(stderr):
    """stderr 에서 [FANDING_NEED] 로 시작하는 줄만 고른다 (같은 줄은 한 번). 다른 stderr 줄은 저장하지 않는다."""
    if not stderr:
        return []
    out = []
    for line in stderr.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith(FANDING_PREFIX) and line not in out:
            out.append(line)
    return out


def reissue_cmd(cfg, need_path):
    """재발행 (Q21 정정) = office_briefing.py --print 를 실행해 stdout JSON 을 받고, 그 JSON 을 우리가 need.json 에 직접 쓴다.
    --print 는 need.json 을 다시 쓰지 않는다(Muse 서버 확인: 실행 전후 타임스탬프·SHA-256 동일). stdout 으로만 새 데이터를 낸다.
    systemctl start 는 쓰지 않는다 (텔레그램 중복 알림).
    stdout 이 올바른 JSON(구조 포함)이 아니면 파일을 건드리지 않고 재발행 실패로 처리한다. 쓰기는 임시파일→rename 이라
    중간에 죽어도 옛 need.json 이 남는다. 반환: ReissueResult — (ok, 실패 이유) 2-튜플,
    stderr 의 [FANDING_NEED] 줄은 .fanding_causes 에 담는다 (진단용, need.json 에는 안 넣음)."""
    rc = cfg.get("reissue", {})
    try:
        r = subprocess.run(rc["cmd"], capture_output=True, timeout=rc.get("timeout_sec", 120))
    except subprocess.TimeoutExpired as e:
        return ReissueResult(False, "시간초과", fanding_cause_lines(e.stderr))
    except Exception as e:
        return ReissueResult(False, type(e).__name__)
    causes = fanding_cause_lines(r.stderr)
    ok, msg = _apply_reissue_output(r, need_path)
    return ReissueResult(ok, msg, causes)


def _apply_reissue_output(r, need_path):
    """재발행 프로세스 결과를 검증해 need.json 에 쓴다. 반환: (ok, 실패 이유)."""
    if r.returncode != 0:
        return False, "종료코드 %s (실행 권한·경로 확인 필요)" % r.returncode
    try:
        data = json.loads(r.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False, "--print 출력이 올바른 JSON 아님"
    bad = need_table.validate_need(data)
    if bad:
        return False, "--print 출력 %s" % bad
    path = expand(need_path)
    try:
        mode = os.stat(path).st_mode & 0o777          # 기존 파일 권한을 그대로 이어 간다 (없으면 0644)
    except OSError:
        mode = 0o644
    try:
        st_mod.atomic_write_json(path, data, mode=mode)
    except Exception as e:
        return False, "need.json 쓰기 실패: %s" % type(e).__name__
    return True, ""


def make_need_sender(cfg, tg_cfg):
    """필요 달러 메시지 전송 함수. 새 봇 설정(paths.telegram_need_cfg)으로만 보낸다.
    키가 없으면 보내지 않는다 (옛 9번 설정으로 대신 보내지 않음 — 섞임 방지).
    새 설정이 옛 9번 설정과 같은 봇 토큰이거나 같은 방이면 보내지 않는다. 비밀값은 출력하지 않는다."""
    need_cfg = cfg.get("paths", {}).get("telegram_need_cfg")

    def _send(text):
        if not need_cfg:
            print("need: paths.telegram_need_cfg 없음 — 보내지 않음", file=sys.stderr)
            return False
        if tg_cfg and os.path.abspath(expand(need_cfg)) == os.path.abspath(expand(tg_cfg)):
            print("need: 새 봇 설정 경로가 9번 설정 경로와 같음 — 보내지 않음", file=sys.stderr)
            return False
        why = tg_send.same_bot_or_room(expand(need_cfg), expand(tg_cfg)) if tg_cfg else None
        if why:
            print("need: 새 봇 설정이 9번 설정과 %s — 보내지 않음" % why, file=sys.stderr)
            return False
        return tg_send.send(text, expand(need_cfg))
    return _send


def _cutoff_minutes(cfg):
    h, m = cfg.get("schedule", {}).get("late_cutoff_cst", "12:00").split(":")
    return int(h) * 60 + int(m)


def main(argv=None, deps=None):
    args = parse_args(argv)
    deps = deps or {}
    cfg = load_config(args.config)
    now = dt.datetime.fromisoformat(args.now).replace(tzinfo=dt.timezone.utc) if args.now \
        else dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(KST).strftime("%Y-%m-%d")            # as_of_kst 와 같은 기준(KST)
    cst = now.astimezone(CST)
    late = (cst.hour * 60 + cst.minute) >= _cutoff_minutes(cfg) and cst.strftime("%Y-%m-%d") == today
    state_dir = args.state_dir or cfg["paths"]["state_dir"]
    st = State(state_dir)
    need_path = args.need_json or cfg["paths"]["need_json"]
    tg_cfg = cfg["paths"]["telegram_cfg"]
    send_need_fn = deps.get("send_need") or deps.get("send") or make_need_sender(cfg, tg_cfg)   # 필요 달러 (새 방)
    reissue = deps.get("reissue") or (lambda: reissue_cmd(cfg, need_path))
    sleep = deps.get("sleep") or time.sleep
    run_id = deps.get("run_id") or secrets.token_hex(3)
    gen = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    dry = args.dry
    send_cfg = cfg.get("send", {})
    if not isinstance(send_cfg, dict):
        send_cfg = {}
    send_need = send_cfg.get("need", True)          # true = 새 봇 방으로 보냄. 되돌리기 = false (VERIFY.md)

    latest = st.read_latest() or {}
    out = {"schema_version": 1, "run_id": run_id, "generated_at": gen,
           "need": latest.get("need"),
           "telegram": latest.get("telegram") or {"need": None}}
    exit_code = 0

    def deliver(kind, text):
        """텔레그램 상태: sent / failed(마감 이후) / pending(마감 안, 다음 실행에서 재시도) / dry."""
        if dry:
            print("----- [dry] %s 메시지 -----\n%s\n" % (kind, text))
            return "dry"
        sender = send_need_fn      # need·streak 알림은 새 방으로만 보낸다
        if sender(text):
            st.mark_sent(today, kind)
            return "sent"
        return "failed" if late else "pending"

    do_need = args.stage in ("need", "all")

    if do_need:
        if not dry and not send_need:
            print("need: 발송 꺼짐 (send.need=false) — 보내지 않음")
            out["need"] = {"status": "disabled", "run_id": run_id, "generated_at": gen}
            out["telegram"]["need"] = "disabled"
        elif not dry and not args.force and st.is_sent(today, "need"):
            print("need: 오늘 이미 전송됨 (--force 로만 재실행)")
        else:
            try:
                res = need_table.collect(cfg, today, need_path, reissue, sleep, dry)
                text = (render.need_failed_message(today, run_id, late) if res["status"] == "failed"
                        else render.need_message(res, today, run_id, late))
                res_json = {"status": res["status"], "as_of": res["as_of"], "accounts": res["rows"],
                            "totals": res["totals"], "notes": res["notes"], "error": res.get("error"),
                            "stale": res.get("stale"), "reissued": res.get("reissued"),
                            "reissue_ok": res.get("reissue_ok"), "run_id": run_id, "generated_at": gen}
                if res.get("fanding_causes"):      # 원인이 있을 때만 (진단용, 메시지에는 안 보임)
                    res_json["fanding_causes"] = res["fanding_causes"]
                out["need"] = res_json
                out["telegram"]["need"] = deliver("need", text)
                if not dry:
                    _update_streak(st, today, res, deliver, run_id)
            except Exception as e:
                out["need"] = {"status": "failed", "error": "예외: %s" % type(e).__name__,
                               "run_id": run_id, "generated_at": gen}
                print("need 단계 예외: %r" % e, file=sys.stderr)
                exit_code = 1

    if dry:
        print("----- [dry] briefing_latest.json -----\n" + json.dumps(out, ensure_ascii=False, indent=2))
    else:
        try:
            st.save_latest(out, today)
            st.prune(today, cfg.get("schedule", {}).get("retention_days", 90))
        except Exception as e:
            print("latest 저장 실패: %r" % e, file=sys.stderr)
            exit_code = 1
    return exit_code


def _update_streak(st, today, res, deliver, run_id):
    """null_reissue_streak: holding null 때문에 재발행이 필요했던 날 +1, 필요 없던 날 0 (설계 7절).
    같은 날짜 재실행(--force)은 두 번 세지 않는다. need.json 자체를 못 읽은 날(null_cause=None)은 건드리지 않는다."""
    s = st.load_state()
    cause = res.get("null_cause")
    if cause is None or s.get("last_streak_date") == today:
        return
    if cause:
        s["null_reissue_streak"] += 1
    else:
        s["null_reissue_streak"] = 0
    s["last_streak_date"] = today
    if s["null_reissue_streak"] >= 3 and not s["streak_alerted"]:
        if deliver("streak", render.streak_alert_message(s["null_reissue_streak"])) == "sent":
            s["streak_alerted"] = True              # 같은 메시지를 매일 반복하지 않는다
    elif s["null_reissue_streak"] == 0 and s["streak_alerted"]:
        deliver("streak_resolved", render.streak_resolved_message())
        s["streak_alerted"] = False                 # 해소 1회
    st.save_state(s)


if __name__ == "__main__":
    sys.exit(main())
