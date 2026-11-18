#!/usr/bin/env python3
# ==========================================================
# FILE: meritz_laoer/main.py   (MERITZ_LAOER v2.0.5)
# v2.0.5 (2026-11-19): 정규장 외(장전 003·장후 005) 장중 매도는 '004 아니면 건너뜀' 유지 — 공식 openapi.json 에 연장 시간 주문·체결 근거가 없어 미확인(주석·테스트만 추가, 동작 변경 없음). BOT_VERSION v2.0.5. 체결 내역 심볼 필드 수정은 meritz_api.py
# v2.0.4 (2026-11-19, 판 5 점검 보완 + 판 6): ① 현금 부분 매수(accum_strategy.make_plan) — 계획·--check·텔레그램에 부분 매수 수량 표시
#   ② 주문 응답 유실 자동처리: 주문 전에 '시도' 기록(attempts)을 먼저 저장 → 응답을 못 받으면(시간 초과·연결 끊김·주문번호 없음) 멈추지 않고
#      그 주문을 다시 내지 않은 채 체결 내역(fills_rows)에서 같은 방향·수량·가격 조건의 주문번호를 찾아 이어 붙임(주문 직후 3번, 마감 뒤 체결 반영 때 한 번 더).
#      못 찾으면 '체결 안 된 것'으로 두고 마지막 잔고=장부 확인이 안전망(어긋나면 예전처럼 정지). 서버가 오류 코드로 분명히 거절한 주문은 '안 들어감'으로 처리
#   ③ 텔레그램 chat_id 필수: 비어 있거나 숫자가 아니면 점검(--check·--add-shares·주문 전 확인)에서 막음 — 하루 기록은 안 써서 고치면 같은 날 다시 시도
#   ④ 판 5 보완 포함: 거래소 번호·적용환율 일시 오류는 하루 기록 없이 5분 뒤 재시도, 자동환전 뒤 달러 반영 최대 90초 대기, 장중 매도는 장이 열려 있을 때만
# 메리츠 속쓸 적립봇 (SOXL 분할매수·부분매도) — 실행·안전장치
# v2.0.3 (2026-11-18): ① 당일 매도 — 오늘 산 주식이 평단(오늘 체결 반영) +목표% 에 닿으면 그날 바로 매도 비중만큼 매도.
#     장중 intraday_sell_check_sec(기본 120초)마다 run_intraday_sell 이 확인 (실거래·LIMIT 주문일 때만). 매수는 하루 1회차 그대로(장중 재매수 없음),
#     하루 매도 주문은 1건 (이미 오늘 매도 주문이 있으면 안 냄), 연속 매도 금지(sell_block)는 make_plan 규칙 그대로 (오늘 체결된 매수가 있으면 풀림).
#     오늘 매수 주문이 있는 날은 아침 계획에서 매도 주문을 빼고 장중 확인으로 넘김(defer_sell) — 오늘 체결로 평단이 바뀌는데 메리츠 API 에 주문 취소가 없어 낡은 평단의 매도 주문이 남기 때문.
#     장부·적립 상태는 장중에 안 바꿈 (체결 반영은 기존 run_sync). 0 으로 두면 예전 동작(아침 주문만).
#   ② 화면 글자: 영어 변수 이름 제거(notifier.to_korean), 속쓸 가격(현재가·평단·매도 목표·사다리·체결 단가)만 소수점, 달러 금액·환율은 정수.
#   v2.0.2(따로 적용 안 함)의 내용 포함. 주문 계산(accum_strategy.py)은 안 바뀜
# v2.0.1 (2026-11-18): BOT_VERSION 만 (텔레그램 메뉴 개편은 tg_menu.py·config.py)
# v2.0.1 (2026-11-18): BOT_VERSION 만 (텔레그램 메뉴 개편은 tg_menu.py·config.py)
# v2.0.0 (2026-11-18): 무한매수(V14) → 적립봇 전환. 계획은 accum_strategy.make_plan (순수 계산), 체결 뒤 적립 상태(data/accum_state.json) 갱신.
#   - 그대로: 키 지문·P/VR6 키·다른 봇 토큰 금지·입고/토스 정지 확인·장부=잔고·정지(halt)·하루 1회 표시 파일·텔레그램 메뉴·--inject-start
#   - 바뀜: market_inputs(현재가·전일종가·메리츠 적용환율), build_plan·plan_head 인자 바뀜, fit_orders 없앰(달러·매도가능 검사는 make_plan 안),
#     t_and_target → sell_target, run_order_day·run_sync·cmd_check·cmd_add_shares, --add-shares 에 --credit 추가
#   - 자동환전 auto_fx(기본 꺼짐): 오늘 매수에 필요한 달러(필요달러)가 예수금보다 모자라면 부족분+여유%만큼 원→달러 환전 신청.
#     실주문 모드에서만·하루 한 번·하루 상한·원화 예수금 확인·신청 전 표시 파일(중복 신청 방지). 모의는 계산만
#   - --add-shares --qty N --avg X --credit: 직접 산(또는 입고된) N주를 평단 반영 + N×X 달러를 1회차 매수 때 한 번 차감
# v1.0.4 (2026-11-14): BOT_VERSION만 (봇 번호 정리 — 표시 이름 '7번 메리츠 무매'는 tg_menu.py·notifier.py)
# v1.0.3 (2026-11-14): 텔레그램 메뉴(tg_menu.py) — 상황판·맨밑 메뉴·도구. 기다리는 자리(time.sleep)에서 같은 스레드로 순서대로 처리
#   - 주문·체결 반영·전략·안전장치는 그대로. --inject-start 본문은 cmd_inject_start() 로 옮김 (CLI·메뉴가 같은 함수)
# v1.0.2 (2026-11-08): --add-shares --qty N --avg X 추가 (직접 산 주식을 지정 평단으로 장부 반영)
#   - 메리츠 잔고 == 장부 + N 일 때만 · enabled=true·미국장 주문 시간이면 거부 · 주문 없음 · 전후 로그·텔레그램
# v1.0.0 (2026-11-08): 첫 버전
#   - (v1.0.x 옛 설명) 전략: strategy_v14.py — v2.0.0 부터 main 이 안 부름(파일은 그대로 둠, 지울지는 Muse 결정)
#   - 주문: 메리츠 즉시주문 (LOC·MOC·지정가). 미국 동부 order_time_et~order_deadline_et 에 하루 1번
#   - 체결 반영: sync_time_et 이후 주문번호로 체결 내역을 읽어 봇 장부(원금·수량)를 갱신
#   - 안전장치: 기본 enabled=false · dry_run(모의) · 입고 확인 · 토스 스나이퍼 정지 확인 · 키 지문 일치
#     · P/VR6 키·다른 봇 텔레그램 토큰 재사용 금지 · 장부≠잔고면 정지(halt) · 하루 1회 표시 파일
# 사용:
#   python3 main.py --fingerprint      키 지문만 출력 (expected_key_fp 에 넣을 값)
#   python3 main.py --check            주문 없이 점검 + 오늘 주문 계획 미리보기 (enabled 와 무관)
#   python3 main.py --inject-start     입고 확인 뒤 장부 시작 (settings.start 로 원금·수량 덮어쓰기)
#   python3 main.py --clear-halt       정지 표시 해제 (원인 확인 후)
#   python3 main.py --add-shares --qty N --avg X [--credit]   직접 산 N주를 평단 $X 로 장부에 더함 (주문 없음). --credit: 원가를 1회차 때 차감
#   python3 main.py                    상시 실행 (서비스용)
# ==========================================================
import argparse
import contextlib
import copy
import re
import datetime
import json
import logging
import math
import os
import shutil
import sys
import time
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import config as cfgmod                      # noqa: E402
from accum_strategy import make_plan, apply_fill_to_state, ceil2   # noqa: E402
from config import ConfigManager, load_settings, validate_settings   # noqa: E402
from meritz_api import MeritzApi, MeritzError, WarnNeeded, key_fingerprint   # noqa: E402
from notifier import Notifier, _read_chat, _read_token, token_fp, to_korean   # noqa: E402
import tg_menu                                # noqa: E402  v1.0.3 텔레그램 메뉴 (폴링은 idle() 안에서만)

BOT_VERSION = "v2.0.5"
EST = ZoneInfo("America/New_York")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def now_et():
    return datetime.datetime.now(EST)


def _hm(s, default):
    try:
        h, m = str(s).split(":")
        return datetime.time(int(h), int(m))
    except (ValueError, AttributeError):
        return default


@contextlib.contextmanager
def in_dir(path):
    old = os.getcwd()
    os.makedirs(path, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def sandbox_dir(state_dir):
    """모의·미리보기용: 실제 장부(data/)를 복사한 임시 폴더. 실제 장부는 바뀌지 않음"""
    sb = os.path.join(state_dir, "_sandbox")
    shutil.rmtree(sb, ignore_errors=True)
    src = os.path.join(state_dir, "data")
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(sb, "data"), ignore=shutil.ignore_patterns("meritz_token.json"))
    else:
        os.makedirs(os.path.join(sb, "data"), exist_ok=True)
    return sb


# ---------------------------------------------------------------- 점검 (주문 없음)
CHAT_BAD = "텔레그램 방 번호"      # check_identity 문제 글자의 머리 (화면 글자라 영어 이름 없이 — notifier.to_korean 이 chat_id 를 '설정값' 으로 바꿔 버림). run_order_day 가 방 번호만 문제면 하루 기록 없이 다시 시도


def check_identity(s):
    """키·토큰 점검 → (문제 목록, 키 지문)"""
    bad, fp = [], ""
    kf = s.get("key_file")
    if not kf or not os.path.isfile(kf):
        bad.append("새 메리츠 키 파일 없음 (key_file)")
    else:
        try:
            fp = key_fingerprint(kf)
        except Exception:
            bad.append("키 파일 형식 오류 (app_key/app_secret)")
        for other in s.get("forbid_key_files") or []:
            if os.path.realpath(other) == os.path.realpath(kf):
                bad.append("key_file 이 P/VR6 키 파일과 같은 경로 — 재사용 금지")
            elif fp and os.path.isfile(other):
                try:
                    if key_fingerprint(other) == fp:
                        bad.append("새 키가 P/VR6 키와 같음 — 재사용 금지")
                except Exception:
                    pass
        exp = str(s.get("expected_key_fp") or "").strip()
        if not exp:
            bad.append("expected_key_fp 비어 있음 (--fingerprint 값 입력 필요)")
        elif fp and fp != exp:
            bad.append("키 지문 불일치 — 3번 계좌 키가 아님 (정지)")
    tf = s.get("telegram_file")
    tok = _read_token(tf) if tf else ""
    if not tok:
        bad.append("새 텔레그램 토큰 파일 없음 (telegram_file)")
    else:
        for other in s.get("forbid_telegram_files") or []:
            if os.path.realpath(other) == os.path.realpath(tf) or token_fp(_read_token(other)) == token_fp(tok):
                bad.append("텔레그램 토큰이 다른 봇과 같음 — 재사용 금지")
        chat = _read_chat(tf)                  # v2.0.4: chat_id 가 없으면 알림도 메뉴도 안 됨 → 비지 않게 막음
        if not chat:
            bad.append(CHAT_BAD + "가 비어 있음 — 알림·메뉴가 안 돼요 (텔레그램 설정 파일에 방 번호가 있어야 해요)")
        elif not re.fullmatch(r"-?\d+", chat):
            bad.append(CHAT_BAD + "는 숫자여야 해요 — 메뉴가 등록된 방으로 못 알아봐요 (텔레그램 설정 파일의 방 번호 확인)")
    return bad, fp


def gate_problems(s, cfg, live):
    """실주문 전 통과해야 하는 조건 → 문제 목록"""
    bad = validate_settings(s)
    bad += check_identity(s)[0]
    if not s.get("transfer_confirmed"):
        bad.append("입고 확인 전 (transfer_confirmed=false)")
    if not s.get("toss_sniper_stopped_confirmed"):
        bad.append("토스 스나이퍼 정지·미체결 0건 확인 전 (toss_sniper_stopped_confirmed=false)")
    if cfg.get_halt():
        bad.append(f"정지 상태: {cfg.get_halt().get('reason')}")
    if live and not cfg.get_position():
        bad.append("장부 시작 전 (--inject-start 필요)")
    return bad


def market_inputs(s, api):
    """(현재가, 전일종가, 메리츠 적용환율[매수 기준, 못 읽으면 0.0]). 조회만"""
    p = api.price(s["symbol"], s["price_market"])
    try:
        fx = api.fx_applied_rate()
    except MeritzError as e:
        logging.warning(f"적용환율 조회 실패: {e}")
        fx = 0.0
    return p["price"], p["prev_close"], fx


def build_plan(s, cfg, price, fx, cash, qty, principal, sellable, ignore_auto_fx=False):
    """오늘 계획 (장부·상태를 바꾸지 않음) → {"orders", "notes", "info"}. info 에 필요달러(need_usd)·부족달러(shortfall_usd)"""
    return defer_sell(s, make_plan(s, cfg.accum_or_start(), qty, principal, price, fx, cash, sellable, ignore_auto_fx))


def auto_fx(s, api, cfg, plan, live, d):
    """부족 달러만큼 원→달러 환전. 부족 없거나 꺼져 있으면 None. live=False 면 신청 없이 계산만.
    → {"short", "want", "capped", "rate", "krw_est", "status", "done"(bool), "error"(없으면 None)}"""
    i = plan["info"]
    short = float(i.get("shortfall_usd") or 0)
    if not s.get("auto_fx_enabled") or short <= 0:
        return None
    raw = math.ceil(short * (1 + float(s["auto_fx_buffer_pct"]) / 100.0))
    want = min(raw, int(float(s["auto_fx_max_usd_per_day"])))
    r = {"short": round(short, 2), "want": want, "capped": want < raw, "rate": None, "krw_est": None,
         "status": "", "done": False, "error": None}
    try:
        rate, tm = api.fx_applied()
    except MeritzError as e:
        r.update(status="환전 안 함", error=f"적용환율 조회 실패: {e}")
        return r
    r["rate"], r["krw_est"] = rate, int(round(want * rate))
    if not live:
        r["status"] = "모의 — 신청 안 함 (계산만)"
        return r
    marker = os.path.join(s["state_dir"], "data", f"fx_{d}.json")
    if os.path.exists(marker):
        r.update(status="오늘 이미 환전을 신청한 기록이 있어 다시 안 함 (확인 필요)")
        return r
    try:
        krw = api.krw_cash()
    except MeritzError as e:
        r.update(status="환전 안 함", error=f"원화 예수금 조회 실패: {e}")
        return r
    if krw < r["krw_est"]:
        r.update(status="환전 안 함", error=f"원화 예수금 부족 (필요 약 ₩{r['krw_est']:,} > 보유 ₩{int(krw):,})")
        return r
    cfg._save_json(marker, {"date": d, "usd": want, "rate": rate, "krw_est": r["krw_est"], "result": "신청 전 기록 (이 파일이 있으면 오늘 다시 신청하지 않음)"})
    try:
        api.fx_exchange(want, rate, tm)
    except MeritzError as e:
        cfg._save_json(marker, {"date": d, "usd": want, "rate": rate, "result": f"실패 또는 불확실: {str(e)[:120]}"})
        r.update(status="환전 신청 실패 또는 불확실 — 오늘 다시 신청 안 함", error=str(e)[:160])
        return r
    cfg._save_json(marker, {"date": d, "usd": want, "rate": rate, "krw_est": r["krw_est"], "result": "신청 완료"})
    r.update(status="환전 신청 완료", done=True)
    return r


def fx_lines(r):
    if not r:
        return ""
    t = (f"💱 환전: 부족 ${math.ceil(r['short']):,} → 신청 ${r['want']:,}" + (" (하루 상한 적용)" if r["capped"] else "")
         + (f" · 약 ₩{r['krw_est']:,} (환율 {r['rate']:,.0f})" if r.get("rate") else "") + f" · {r['status']}")
    return t + (f"\n⚠️ {r['error']}" if r.get("error") else "") + "\n"


SIDE_KO = {"BUY": "매수", "SELL": "매도"}
TYPE_KO = {"LIMIT": "지정가", "LOC": "종가 조건", "MOC": "종가 시장가"}


_LVL_RE = re.compile(r"사다리 \$([\d.]+) (?=회차)")    # 사다리 가격은 속쓸 가격이라 소수 2자리


def fmt_orders(orders):
    return "\n".join(f"- {SIDE_KO.get(o['side'], o['side'])} {o['qty']}주 @ {'시장가' if o['type'] == 'MOC' else '$%.2f' % float(o['price'])} "
                     f"({TYPE_KO.get(o['type'], o['type'])}) {_LVL_RE.sub(lambda m: '사다리 $%.2f ' % float(m.group(1)), o.get('desc', ''))}".rstrip()
                     for o in orders) or "- (주문 없음)"


def plan_head(plan, s):
    i = plan["info"]
    pl = f" ({i['profit_pct']:+.2f}%)" if i.get("profit_pct") is not None else ""
    return (f"{'재매수' if i['mode'] == 'rebuy' else '사다리'} 단계 · 현재가 ${i['price']:.2f} · 평단 ${i['avg']:.2f}{pl} · 채운 회차 {len(i['filled'])}/{len(i['levels'])}\n"
            f"매도 목표 ${i['sell_target']:.2f} · 회차 금액 ${i.get('unit_usd', 0):,.0f}"
            + (f" · 1회차 차감 ${i['credit_usd']:,.0f}" if i.get("credit_usd") else "")
            + (f" · 환율 {i['fx']:,.0f}" if i.get("fx") else "")
            + (f"\n필요 달러 ${i['need_usd']:,.0f} · 예수금 ${i['usd_cash']:,.0f}" + (f" · 부족 ${math.ceil(i['shortfall_usd']):,}" if i.get("shortfall_usd") else "")
               if i.get("need_usd") is not None else ""))


# ---------------------------------------------------------------- v2.0.3 당일 매도
_INTRA = {"last": 0.0, "err_day": ""}


def intraday_on(s):
    """당일 매도 확인을 쓰는지: 확인 간격 > 0 이고 주문 방식이 지정가(LIMIT)일 때만. (LOC 는 종가에만 체결돼서 장중 확인이 의미 없음 → 예전 동작)"""
    try:
        sec = float(s.get("intraday_sell_check_sec") or 0)
    except (TypeError, ValueError):
        return False
    return sec > 0 and s.get("order_type") == "LIMIT"


def defer_sell(s, plan):
    """오늘 매수 주문이 있으면 아침 계획에서 매도 주문을 뺌 → 장중 확인(run_intraday_sell)이 오늘 체결을 반영한 평단으로 판단.
    (오늘 매수가 체결되면 평단이 바뀌는데, 아침에 낸 매도 주문은 취소할 수 없어 낡은 평단 기준으로 남기 때문) 매수 주문이 없는 날은 그대로"""
    if not intraday_on(s):
        return plan
    orders = plan["orders"]
    if any(o.get("side") == "BUY" for o in orders) and any(o.get("kind") == "sell" for o in orders):
        plan["orders"] = [o for o in orders if o.get("kind") != "sell"]
        plan["notes"].append("매도는 장중에 확인해서 내요 (오늘 산 주식이 체결되면 평단이 바뀌어서)")
        plan["info"]["sell_deferred"] = True
    return plan


def _warn_once(cfg, mark, m, key, note, text):
    """같은 이유의 알림은 하루 한 번만 (주문 기록 파일에 남김)"""
    w = m.setdefault("intraday_warn", [])
    if key in w:
        return
    w.append(key)
    cfg._save_json(mark, m)
    note.send(text)


def run_intraday_sell(s, api, note):
    """당일 매도 확인 (실거래만, loop 가 주문 시간대에 부름). 오늘 주문 기록이 있고 체결 반영 전인 동안 intraday_sell_check_sec 마다:
    오늘 체결된 매수까지 반영한 평단의 +목표% 에 현재가가 닿았는지 보고, 닿으면 보유의 매도 비중을 지정가로 한 번 매도.
    매수는 안 함 · 하루 매도 주문 1건 · 장부·적립 상태는 안 바꿈 (체결 반영은 run_sync 가 그대로) → 상태 글자"""
    if s.get("dry_run", True):
        return "모의"
    if not intraday_on(s):
        return "꺼짐"
    now_t = time.time()
    if now_t - _INTRA["last"] < float(s["intraday_sell_check_sec"]):
        return "대기"
    _INTRA["last"] = now_t
    d = now_et().strftime("%Y-%m-%d")
    mark = os.path.join(s["state_dir"], "data", f"orders_{d}.json")
    cfg = ConfigManager(s)
    m = cfg._load_json(mark, None)
    if not isinstance(m, dict) or m.get("skipped") or m.get("synced", True) or not isinstance(m.get("orders"), list):
        return "해당 없음"
    if m.get("sell_attempt") or any(o.get("kind") == "sell" for o in m["orders"]):
        return "오늘 매도 주문 있음"              # 중복 매도 방지: 아침 주문이든 장중 주문이든 오늘 매도 주문이 있으면 더 안 냄
    bad = gate_problems(s, cfg, live=True)
    if bad:
        logging.warning("당일 매도 확인 건너뜀: " + "; ".join(bad)[:200])
        return "차단"
    pos = cfg.get_position()
    q0, pr0 = int(pos["qty"]), float(pos["principal"])
    buys = [o for o in m["orders"] if o.get("side") == "BUY"]
    pct = float(s["sell_profit_pct"])
    # 시세 한 번만 보고 거를 수 있는 가장 낮은 목표가: 평균은 구성 값(기존 평단·오늘 낼 매수가) 중 가장 낮은 값보다 낮아질 수 없음
    cands = ([cfg.avg_price(pos)] if q0 > 0 else []) + [float(o["price"]) for o in buys if float(o.get("price") or 0) > 0]
    if not cands:
        return "해당 없음"
    try:
        px = float(api.price(s["symbol"], s["price_market"])["price"])
    except MeritzError as e:
        logging.warning(f"당일 매도 확인: 시세 조회 실패 {e}")
        return "시세 실패"
    if px < ceil2(min(cands) * (1 + pct / 100.0)):
        return "목표 아래"
    dt = datetime.date.fromisoformat(d)
    fills = api.fills((dt - datetime.timedelta(days=1)).strftime("%Y%m%d"), (dt + datetime.timedelta(days=2)).strftime("%Y%m%d"))
    q, pr = q0, pr0
    st = copy.deepcopy(cfg.accum_or_start())
    for o in buys:                                   # 오늘 체결된 매수를 '메모리 안에서만' 반영 (장부 파일은 그대로)
        f = fills.get(str(o.get("no")))
        if not f or f[0] != "BUY" or int(f[1]) < 1:
            continue
        apply_fill_to_state(st, o, (pr / q) if q > 0 else 0.0, bool(s.get("allow_consecutive_sell")))
        q += int(f[1])
        pr += float(f[2])
    hold, sellable, exch_vid = api.holding(s["symbol"])
    if hold != q:
        _warn_once(cfg, mark, m, "hold", note, f"오늘 체결 반영 뒤 예상 {q}주 ≠ 메리츠 잔고 {hold}주 — 당일 매도 확인을 보류하고 계속 확인해요 (체결 조회가 늦은 것일 수 있음)")
        return "잔고 불일치"
    plan = make_plan(s, st, q, round(pr, 4), px, 0.0, 0.0, sellable)       # 환율 0 → 매수 계산 없이 매도 규칙만 (make_plan 의 매도 규칙 그대로)
    info = plan["info"]
    if not info.get("profit_reached"):
        return "목표 아래"                                                   # 오늘 체결로 평단이 올라 목표가 더 높아진 경우
    sells = [o for o in plan["orders"] if o.get("kind") == "sell"]
    if not sells:
        why = "; ".join(n for n in plan["notes"] if n.startswith("매도")) or "매도 조건 미충족"
        _warn_once(cfg, mark, m, "block", note, f"🎯 평가 이익 +{pct:g}% 에 닿았지만 매도 안 함: {why}")
        return "매도 보류"
    exch = str(s.get("exch_id") or exch_vid or "")
    if not exch:
        _warn_once(cfg, mark, m, "exch", note, "⛔ 거래소 번호를 알 수 없어 당일 매도를 못 냄 — 설정에 거래소 번호를 넣어 주세요")
        return "거래소"
    # v2.0.5: 정규장("004") 아니면 건너뜀을 유지. 003 프리마켓·005 애프터마켓에 지정가 매도가 접수·체결되는지는 공식 openapi.json 에 없음(주문 API 에 연장 시간 구분 필드 없음) → 미확인, 실거래 시험은 사용자 결정 필요
    if str(api.us_market_status()) != "004":      # 조기폐장일(13:00 ET)·장 마감 뒤에는 장중 매도를 안 냄 (order_deadline_et 만으로는 못 거름)
        return "장 닫힘"
    if any(str(r.get("seln_byov_clcd")) == "1" for r in api.open_orders_today(s["symbol"])):
        _warn_once(cfg, mark, m, "open_sell", note, "이 계좌에 SOXL 매도 미체결 주문이 이미 있어 당일 매도를 안 냄 (수동 확인)")
        return "매도 미체결 있음"
    o = dict(sells[0], desc="당일 매도 · " + sells[0].get("desc", ""))
    m["sell_attempt"] = {"at": now_et().isoformat(), "qty": o["qty"], "price": o["price"],
                         "status": "접수 시도 (이 기록이 있으면 오늘 다시 매도 주문을 내지 않음)"}
    cfg._save_json(mark, m)                          # 주문 전에 먼저 기록 → 응답이 불확실해도 중복 주문 없음
    errs = []
    res = send_order(s, api, cfg, mark, m, o, exch, errs, intraday=True)     # v2.0.4: 응답을 못 받으면 attempts 에 남겨 마감 뒤 자동으로 찾음
    err = (errs[0] if errs else None)
    if res == "ok":
        m["sell_attempt"].update(status="접수 완료", no=m["orders"][-1]["no"])
    else:
        m["sell_attempt"]["status"] = ("증권사가 거절 — 오늘 다시 안 냄: " if res == "rejected" else "응답 못 받음 — 오늘 다시 안 냄, 체결 내역에서 자동으로 찾음: ") + (err or "")[:100]
    cfg._save_json(mark, m)
    head = (f"🎯 당일 매도 {'접수' if res == 'ok' else ('실패' if res == 'rejected' else '응답 못 받음')}\n오늘 체결 반영 평단 ${info['avg']:.2f} (보유 {q}주) → 목표 ${info['sell_target']:.2f} · 현재가 ${px:.2f}\n")
    note.send(head + fmt_orders([o]) + (f"\n⚠️ {err}\n오늘은 다시 시도하지 않아요. 내일 아침 계획에서 다시 판단해요." if err else ""))
    return {"ok": "매도 접수", "rejected": "매도 실패"}.get(res, "매도 응답 유실")


# ---------------------------------------------------------------- 하루 주문
# 판 5 점검 보완: '그날 주문 기록(표시 파일)을 써 버리면 같은 날 다시 못 낸다' 는 문제 — 설정·일시 오류로 못 낸 경우엔 기록을 안 쓰고 다시 시도
_RETRY = {}                       # 이유별 {"day": 알린 날, "next": 다시 시도할 시각}
FX_WAIT_TRIES, FX_WAIT_SEC = 9, 10   # 환전 신청 직후 예수금 반영을 기다리는 횟수·간격(초) — 최대 약 90초


def _retry_later(note, d, key, text, sec=300):
    """표시 파일을 안 쓰고 sec 초 뒤 다시 시도 (설정을 고치거나 일시 오류가 풀리면 같은 날 주문이 나감). 같은 이유의 알림은 하루 한 번"""
    r = _RETRY.setdefault(key, {"day": "", "next": 0.0})
    if r["day"] != d:
        r["day"] = d
        note.send(text)
    r["next"] = time.time() + sec


def _retry_wait(d):
    return any(r["day"] == d and time.time() < r["next"] for r in _RETRY.values())


# ---------------------------------------------------------------- v2.0.4 주문 응답 유실 자동처리
RECON_TRIES, RECON_SEC = 3, 5      # 주문 직후 체결 내역에서 찾아보는 횟수·간격(초)


def _known_nos(cfg, state):
    """이 봇이 이미 장부 기록(표시 파일)에 올려 둔 주문번호 전부 — 다른 날 주문을 잘못 이어 붙이지 않게 제외"""
    out = set()
    for mp in pending_syncs(state):
        m = cfg._load_json(mp, {})
        if isinstance(m, dict):
            out.update(str(o.get("no")) for o in (m.get("orders") or []) if isinstance(o, dict) and o.get("no"))
    return out


def reconcile_attempts(s, api, cfg, m, final):
    """주문 응답을 못 받은 주문(m['attempts'])을 체결 내역에서 찾아 주문번호를 붙임 (다시 주문하지 않음). m 을 직접 바꿈 → (찾은 수, 남은 수).
    조건: 심볼(응답에 있으면)·방향이 같고, 아직 어느 기록에도 없는 주문번호이며, 체결 평균가가 주문가 범위 안(매수 ≤ 주문가, 매도 ≥ 주문가).
    final=False(주문 직후): 체결수량이 주문수량과 같은 것만. final=True(마감 뒤): 주문수량 이하(부분 체결 포함). 후보가 딱 1건일 때만 붙임 — 0건·2건 이상이면 그대로 둠"""
    att = [a for a in (m.get("attempts") or []) if isinstance(a, dict)]
    if not att:
        return 0, 0
    fr = getattr(api, "fills_rows", None)
    if fr is None:
        return 0, len(att)
    dt = datetime.date.fromisoformat(m["date"])
    rows = fr((dt - datetime.timedelta(days=1)).strftime("%Y%m%d"), (dt + datetime.timedelta(days=2)).strftime("%Y%m%d"))
    known = _known_nos(cfg, s["state_dir"]) | {str(o.get("no")) for o in (m.get("orders") or []) if isinstance(o, dict) and o.get("no")}
    sym = str(s["symbol"]).upper()
    cands = [r for r in rows if r["no"] not in known and (not r.get("sym") or r["sym"] == sym)]
    found, rest = 0, []
    for a in att:
        lim, q = float(a.get("price") or 0), int(a.get("qty") or 0)

        def fit(r):
            if r["side"] != a.get("side") or r["qty"] < 1 or r["qty"] > q or (not final and r["qty"] != q):
                return False
            if lim <= 0 or a.get("type") == "MOC":
                return True
            px = r["amt"] / r["qty"]
            return px <= lim + 0.005 if a["side"] == "BUY" else px >= lim - 0.005
        hit = [r for r in cands if fit(r)]
        if len(hit) == 1:
            cands.remove(hit[0])
            m.setdefault("orders", []).append(dict({k: v for k, v in a.items() if k != "status"}, no=hit[0]["no"], recovered=True))
            found += 1
        else:
            rest.append(a)
    m["attempts"] = rest
    return found, len(rest)


def send_order(s, api, cfg, mark, m, o, exch, errors, intraday=False):
    """주문 1건. 주문 전에 '시도'를 표시 파일에 먼저 저장하고(→ 응답이 안 와도 같은 날 다시 안 냄), 결과에 따라
    성공: m['orders'] 에 번호와 함께 · 서버가 분명히 거절/경고: errors 에만 · 응답을 못 받음/번호 없음: m['attempts'] 에 남김(나중에 자동으로 찾음). → 'ok'|'rejected'|'unsure'"""
    a = dict(o, status="접수 시도 (응답 확인 전)")
    m.setdefault("attempts", []).append(a)
    cfg._save_json(mark, m)
    out, why = "unsure", ""
    try:
        r = api.order(o["side"], s["symbol"], exch, o["type"], o["qty"], o["price"])
        if str(r.get("no") or "").strip():
            m["attempts"].remove(a)
            m.setdefault("orders", []).append(dict(o, no=str(r["no"]).strip(), **({"intraday": True} if intraday else {})))
            out = "ok"
        else:
            why = "주문 응답에 주문번호가 없음"
    except WarnNeeded as e:
        out, why = "rejected", f"증권사 경고(자동 확인 안 함) {e}"
    except MeritzError as e:
        out, why = ("rejected" if e.definite else "unsure"), str(e)[:160]
    except Exception as e:                      # 시간 초과 등 — 주문이 들어갔는지 모름
        why = f"주문 응답을 못 받음 ({type(e).__name__})"
    if out == "rejected":
        m["attempts"].remove(a)
        errors.append(f"{o.get('desc')}: {why}")
    elif out == "unsure":
        a["status"] = "응답 못 받음 — 다시 안 내고 체결 내역에서 찾음: " + why[:100]
        errors.append(f"{o.get('desc')}: {why} (응답을 못 받았어요 — 다시 주문하지 않고 자동으로 확인해요)")
    cfg._save_json(mark, m)
    return out


def run_order_day(s, api, note, live):
    state = s["state_dir"]
    d = now_et().strftime("%Y-%m-%d")
    mark = os.path.join(state, "data", f"{'orders' if live else 'dry_orders'}_{d}.json")
    if os.path.exists(mark):
        return "이미 함"
    if live and _retry_wait(d):
        return "대기"
    cfg = ConfigManager(s)
    if live:
        bad = gate_problems(s, cfg, live=True)
        if bad and all(b.startswith(CHAT_BAD) for b in bad):      # chat_id 만 문제면 하루 기록을 안 써서, 고치면 같은 날 5분 안에 다시 시도 (알림은 chat_id 가 없어 로그로만 남음)
            _retry_later(note, d, "chat", "⛔ 오늘 주문 안 함\n" + "\n".join("- " + b for b in bad) + "\n(고치면 오늘도 5분 안에 다시 시도해요)")
            return "chat_id"
        if bad:
            note.send("⛔ 오늘 주문 안 함\n" + "\n".join("- " + b for b in bad))
            cfg._save_json(mark, {"skipped": bad})
            return "차단"
    status = api.us_market_status()
    if status != "004":
        cfg._save_json(mark, {"skipped": f"장운영 코드 {status} (휴장 또는 정규장 아님)"})
        note.send(f"오늘은 정규장 아님 (코드 {status}) — 주문 없음")
        return "휴장"
    hold, sellable, exch_vid = api.holding(s["symbol"])
    exch = str(s.get("exch_id") or exch_vid or "")
    pos = cfg.get_position()
    if not pos and not live:     # 모의: 장부 시작 전이면 설정 start 로 가정
        st = s["start"]
        pos = {"qty": int(float(st.get("qty") or 0)), "principal": float(st.get("principal_usd") or 0)}
    qty = int(pos["qty"])
    avg = cfg.avg_price(pos)
    warn = []
    if hold != qty:
        warn.append(f"잔고 {hold}주 ≠ 장부 {qty}주")
        if live:
            cfg.halt(warn[-1])
            note.send("⛔ 정지: " + warn[-1] + "\n확인한 뒤 텔레그램 🛠 기타 → ⛔ 정지 해제")
            cfg._save_json(mark, {"skipped": warn})
            return "정지"
    if live and api.open_orders_today(s["symbol"]):
        note.send("⛔ 이 계좌에 SOXL 미체결 주문이 이미 있음 — 오늘 주문 안 함 (수동 확인)")
        cfg._save_json(mark, {"skipped": "기존 미체결 있음"})
        return "미체결"
    if live and not exch:      # 보유 0주면 잔고에서 거래소 번호를 못 얻음 — 표시 파일을 안 써서, 설정을 고치면 같은 날 다시 시도
        _retry_later(note, d, "exch", "⛔ 거래소 번호를 알 수 없음 — 설정에 거래소 번호를 넣어 주세요 (고치면 오늘도 5분 안에 다시 시도해요)")
        return "거래소"
    price, prev_close, fx = market_inputs(s, api)
    if live and not (fx and fx > 0):      # 적용환율 일시 오류로 오늘 매수가 통째로 빠지지 않게 (market_inputs 는 실패를 0.0 으로 삼킴)
        _retry_later(note, d, "fx", "⚠️ 적용환율을 못 읽어 오늘 매수 계획을 못 세웠어요 — 5분 뒤 다시 시도해요")
        return "환율 실패"
    cash = api.usd_cash()
    if live:      # 맨 위 가격 이상을 본 적 있음 표시 (first_buy_mode=wait_top 용). 모의에서는 저장하지 않음
        ast = cfg.accum_or_start()
        if not ast.get("armed") and price >= float(s["ladder_top_usd"]):
            ast["armed"] = True
            cfg.save_accum(ast)
    sell_q = sellable if live else qty
    plan = build_plan(s, cfg, price, fx, cash, qty, float(pos["principal"]), sell_q)
    fxres = auto_fx(s, api, cfg, plan, live, d)
    if live and s.get("auto_fx_enabled"):
        if fxres and fxres.get("done"):      # 환전 신청 직후엔 예수금 반영이 늦을 수 있어 잠깐 기다림 (환전은 다시 신청하지 않음)
            need = float(plan["info"].get("need_usd") or 0)
            for _ in range(FX_WAIT_TRIES):
                if api.usd_cash() >= need:
                    break
                time.sleep(FX_WAIT_SEC)
        cash = api.usd_cash()          # 환전 뒤(또는 안 한 뒤) 실제 예수금으로 다시 계획 — 모자라면 그만큼 매수가 줄어듦
        plan = build_plan(s, cfg, price, fx, cash, qty, float(pos["principal"]), sell_q, ignore_auto_fx=True)
    orders, notes = plan["orders"], plan["notes"]
    errors, recovered = [], 0
    m = {"date": d, "prev_close": prev_close, "price": price, "fx": fx, "auto_fx": fxres,
         "qty": qty, "avg": avg, "cash": round(cash, 2), "orders": [] if live else orders, "attempts": [],
         "errors": errors, "synced": False if live else True, "sell_deferred": bool(plan["info"].get("sell_deferred"))}
    if live:
        cfg._save_json(mark, m)                      # 주문 전에 하루 기록부터 → 도중에 멈춰도 같은 날 다시 주문하지 않음 (v2.0.4)
        for o in orders:
            send_order(s, api, cfg, mark, m, o, exch, errors)
            time.sleep(0.3)
        for i in range(RECON_TRIES if m["attempts"] else 0):      # 응답 못 받은 주문 자동 확인 (다시 주문하지 않음)
            try:
                f, _ = reconcile_attempts(s, api, cfg, m, final=False)
                recovered += f
            except Exception as e:
                logging.warning(f"주문 응답 유실 자동 확인 실패: {type(e).__name__}")
            if not m["attempts"]:
                break
            if i < RECON_TRIES - 1:
                time.sleep(RECON_SEC)
    placed = m["orders"] if live else orders
    if m["attempts"]:
        notes = notes + [f"주문 응답을 못 받은 주문 {len(m['attempts'])}건 — 다시 주문하지 않아요. 마감 뒤 체결 반영 때 체결 내역에서 한 번 더 찾아 이어 붙여요 (멈추지 않음)"]
    if recovered:
        notes = notes + [f"응답은 못 받았지만 체결 내역에서 주문번호를 찾아 이어 붙인 주문 {recovered}건"]
    cfg._save_json(mark, m)
    reached = plan["info"].get("profit_reached")
    note.send(f"{d} 주문 {'접수' if live else '계획'} · 보유 {qty}주 평단 ${avg:.2f}\n{plan_head(plan, s)}\n"
              + (f"🎯 평가 이익 +{float(s['sell_profit_pct']):g}% 도달 (현재가 ${price:.2f} ≥ 목표 ${plan['info']['sell_target']:.2f})\n" if reached else "")
              + fx_lines(fxres)
              + fmt_orders(placed)
              + ("\n" + "\n".join("ℹ️ " + n for n in notes + warn) if notes or warn else "")
              + ("\n⚠️ 실패\n" + "\n".join("- " + e for e in errors) if errors else ""))
    return "완료"


# ---------------------------------------------------------------- 체결 반영
def run_sync(s, api, note, mark_path):
    cfg = ConfigManager(s)
    m = cfg._load_json(mark_path, {})
    if m.get("synced", True) or not (m.get("orders") or m.get("attempts")):
        if m and not m.get("synced", True):
            m["synced"] = True
            cfg._save_json(mark_path, m)
        return "없음"
    d = m["date"]
    dt = datetime.date.fromisoformat(d)
    lost = 0
    if m.get("attempts"):                           # v2.0.4 응답 못 받은 주문: 마감 뒤 체결 내역에서 한 번 더 찾아 이어 붙임 (못 찾으면 체결 안 된 것으로 보고, 아래 잔고=장부 확인이 안전망)
        try:
            reconcile_attempts(s, api, cfg, m, final=True)
        except Exception as e:
            logging.warning(f"주문 응답 유실 자동 확인 실패: {type(e).__name__}")
        lost = len(m.get("attempts") or [])
        cfg._save_json(mark_path, m)
    fills = api.fills((dt - datetime.timedelta(days=1)).strftime("%Y%m%d"), (dt + datetime.timedelta(days=2)).strftime("%Y%m%d"))
    lines, done = [], None
    for o in m["orders"]:
        f = fills.get(str(o.get("no")))
        if not f:
            continue
        side, q, amt = f
        px = amt / q if q else 0.0
        avg0 = cfg.avg_price(cfg.get_position())
        pos, closed = cfg.apply_fill(side, q, px, d, False, f"{d}_{o['no']}")
        ast = cfg.accum_or_start()
        apply_fill_to_state(ast, o, avg0, bool(s.get("allow_consecutive_sell")))    # 같은 체결을 다시 반영해도 결과가 같음
        cfg.save_accum(ast)
        lines.append(f"- {SIDE_KO.get(side, side)} {q}주 @ ${px:.2f} ({o.get('desc', '')})")
        if o.get("kind") == "sell":
            lines.append(f"  🎯 매도 체결 → 재매수 단계 시작 (기준 평단 ${avg0:.2f}, 첫 재매수 ${avg0 - float(s['rebuy_drop_usd']):.2f})")
        done = closed or done
    hold, _, _ = api.holding(s["symbol"])
    pos = cfg.get_position()
    m["synced"] = True
    cfg._save_json(mark_path, m)
    msg = f"{d} 체결 반영\n" + ("\n".join(lines) if lines else "- 체결 없음") + f"\n장부 {pos['qty']}주 평단 ${cfg.avg_price(pos):.2f}"
    if lost:
        msg += f"\nℹ️ 주문 응답을 못 받은 주문 {lost}건은 체결 내역에서 못 찾았어요 (체결 안 된 것으로 봄 — 아래 잔고 확인이 맞는지 검사)"
    if done:
        msg += "\n⚠️ 보유 0주가 되어 사이클 종료 처리됨 — 이 봇의 매도 규칙으로는 생기지 않는 상황, 확인 필요"
    if hold != pos["qty"]:
        cfg.halt(f"체결 반영 뒤 잔고 {hold}주 ≠ 장부 {pos['qty']}주")
        msg += f"\n⛔ 정지: 잔고 {hold}주 ≠ 장부 {pos['qty']}주 (확인한 뒤 ⛔ 정지 해제)"
    note.send(msg)
    return "완료"


def pending_syncs(state):
    dd = os.path.join(state, "data")
    try:
        names = sorted(n for n in os.listdir(dd) if n.startswith("orders_") and n.endswith(".json"))
    except OSError:
        return []
    return [os.path.join(dd, n) for n in names]


# ---------------------------------------------------------------- 상시 실행
# ---------------------------------------------------------------- v1.0.3 기다리는 시간 = 텔레그램 메뉴 처리
_MENU = {"bot": None}


def idle(seconds):
    """loop() 의 time.sleep 자리. 그 시간 동안 텔레그램 메뉴를 이 스레드에서 순서대로 처리 (주문·체결 반영과 동시에 돌지 않음).
    메뉴가 안 되면(토큰 없음·다른 봇 토큰·오류) 그냥 기다림. 걸리는 시간은 seconds 와 같게 맞춤"""
    t_end = time.time() + float(seconds)
    try:
        if _MENU["bot"] is None:
            _MENU["bot"] = tg_menu.MenuBot(sys.modules[__name__])
        _MENU["bot"].idle(load_settings(), t_end)
    except Exception as e:
        logging.warning(f"텔레그램 메뉴 처리 오류: {type(e).__name__} {getattr(e, 'code', '')}".strip())     # HTTPError 면 번호(409 충돌·401 토큰·404 등)까지
    left = t_end - time.time()
    if left > 0:
        time.sleep(left)


def loop():
    last_idle = 0
    while True:
        try:
            s = load_settings()
            state = s["state_dir"]
            os.makedirs(os.path.join(state, "data"), exist_ok=True)
            os.chdir(state)
            if not s.get("enabled"):
                if time.time() - last_idle > 3600:
                    logging.info("enabled=false — 대기 (주문 없음)")
                    last_idle = time.time()
                idle(60)
                continue
            live = not s.get("dry_run", True)
            if not os.path.isfile(str(s.get("key_file") or "")):
                if time.time() - last_idle > 3600:
                    logging.warning("새 메리츠 키 파일 없음 — 대기 (주문 없음)")
                    last_idle = time.time()
                idle(60)
                continue
            note = Notifier(s["telegram_file"], dry_run=not live)
            n = now_et()
            api = None
            if n.weekday() < 5 and _hm(s["order_time_et"], datetime.time(10, 5)) <= n.time() <= _hm(s["order_deadline_et"], datetime.time(15, 40)):
                api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                run_order_day(s, api, note, live)
                if live:                                    # v2.0.3 당일 매도 확인 (실패해도 주문·체결 반영 흐름은 계속)
                    try:
                        run_intraday_sell(s, api, note)
                    except Exception as e:
                        logging.exception(f"당일 매도 확인 중 오류: {type(e).__name__}")
                        if _INTRA["err_day"] != n.strftime("%Y-%m-%d"):
                            _INTRA["err_day"] = n.strftime("%Y-%m-%d")
                            note.send(f"⚠️ 당일 매도 확인 중 오류가 났어요 ({type(e).__name__}) — 이미 낸 주문은 그대로예요. 서버 로그를 확인해 주세요.")
            if live:
                today = n.strftime("%Y-%m-%d")
                for mp in pending_syncs(state):
                    md = os.path.basename(mp)[7:17]
                    if md < today or n.time() >= _hm(s["sync_time_et"], datetime.time(16, 10)):
                        m = ConfigManager(s)._load_json(mp, {})
                        if (m.get("orders") or m.get("attempts")) and not m.get("synced", True):
                            api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                            run_sync(s, api, note, mp)
        except Exception as e:
            logging.exception(f"반복 중 오류: {type(e).__name__}")
            try:
                Notifier(load_settings()["telegram_file"]).send(f"⚠️ 봇에 오류가 났어요 ({type(e).__name__}): {str(e)[:200]}")
            except Exception:
                pass
            idle(120)
        idle(30)


def cmd_check(s):
    print(f"속쓸 적립봇 {BOT_VERSION} 점검 (주문 없음)")
    bad = validate_settings(s)
    idb, fp = check_identity(s)
    print(f"- 봇 {'켜짐' if s.get('enabled') else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'} · "
          f"입고 확인 {'됨' if s.get('transfer_confirmed') else '전'} · 토스 스나이퍼 정지 확인 {'됨' if s.get('toss_sniper_stopped_confirmed') else '전'}")
    print(f"- 키 지문: {fp or '-'} (기대값 {'있음' if s.get('expected_key_fp') else '없음'})")
    for b in bad + idb:
        print("  ✗", to_korean(b))
    state = s["state_dir"]
    os.makedirs(os.path.join(state, "data"), exist_ok=True)
    with in_dir(state):
        cfg = ConfigManager(s)
        pos = cfg.get_position()
        print(f"- 장부: {('%d주 · 원금 $%s · 평단 $%.2f' % (pos['qty'], format(int(round(pos['principal'])), ','), cfg.avg_price(pos))) if pos else '시작 전'}")
        print(f"- 정지 표시: {(cfg.get_halt() or {}).get('reason') or '없음'}")
    if bad or "새 메리츠 키 파일 없음 (key_file)" in idb or "키 파일 형식 오류 (app_key/app_secret)" in idb:
        print("→ 설정을 채운 뒤 다시 점검")
        return 1
    api = MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
    hold, sellable, exch = api.holding(s["symbol"])
    price, prev_close, fx = market_inputs(s, api)
    cash = api.usd_cash()
    print(f"- 메리츠 잔고 {s['symbol']} {hold}주 (매도가능 {sellable}) · 거래소 번호 {exch or '-'} · 달러 예수금 ${cash:,.0f}")
    print(f"- 현재가 ${price:.2f} · 전일종가 ${prev_close:.2f} · 적용환율 {('{:,.0f}원/$'.format(fx)) if fx else '미확인'} · 장운영 코드 {api.us_market_status()}")
    st = s["start"]
    q = int(pos["qty"]) if pos else int(float(st["qty"]))
    principal = float(pos["principal"]) if pos else float(st["principal_usd"])
    with in_dir(state):
        plan = build_plan(s, ConfigManager(s), price, fx, cash, q, principal, sellable)
    orders, notes = plan["orders"], plan["notes"]
    print("- 오늘 계획 (미리보기·주문 안 냄):\n  " + to_korean(plan_head(plan, s)).replace("\n", "\n  "))
    print("  " + to_korean(fmt_orders(orders)).replace("\n", "\n  "))
    for n in notes:
        print("  ℹ️", to_korean(n))
    with in_dir(state):
        r = auto_fx(s, api, ConfigManager(s), plan, False, now_et().strftime("%Y-%m-%d"))
    print("  " + (fx_lines(r).strip().replace("\n", "\n  ") if r else "💱 환전: 필요 없음 또는 자동환전 꺼짐"))
    if hold != q:
        print(f"  ⚠️ 잔고 {hold}주 ≠ 장부/시작 {q}주 → 입고 전이거나 다른 계좌")
    return 0


# ---------------------------------------------------------------- 추가 투입 (주문 없음)
def sell_target(s, cfg, pos):
    """표시용: (채운 회차 수, 매도 목표가 = 평단 × (1+매도%) 올림)"""
    avg = cfg.avg_price(pos)
    n = len(cfg.accum_or_start().get("filled_levels") or [])
    return n, (ceil2(avg * (1 + float(s["sell_profit_pct"]) / 100.0)) if avg > 0 else 0.0)


def cmd_add_shares(s, qty, avg, api=None, credit=False):
    """메리츠 잔고 == 장부 + qty 일 때만 장부 갱신 → 0(성공)/1(거부).
    credit=True: qty×avg 달러를 1회차 매수 때 한 번 차감하도록 적립 상태에 더함 (1회차 전·사다리 모드일 때만)"""
    bad = []
    if qty is None or qty < 1:
        bad.append("수량은 1 이상 정수")
    if avg is None or not (avg > 0) or avg != avg or avg == float("inf"):
        bad.append("평단은 0 보다 큰 숫자")
    if s.get("enabled"):
        bad.append("봇이 켜져 있음 — 봇을 끄고 다시 실행")
    n = now_et()
    if n.weekday() < 5 and _hm(s["order_time_et"], datetime.time(10, 5)) <= n.time() <= _hm(s["order_deadline_et"], datetime.time(15, 40)):
        bad.append(f"미국장 주문 시간 (미 동부 {s['order_time_et']}~{s['order_deadline_et']}) — 끝난 뒤 다시 실행")
    bad += validate_settings(s) + check_identity(s)[0]
    state = s["state_dir"]
    os.makedirs(os.path.join(state, "data"), exist_ok=True)
    with in_dir(state):
        cfg = ConfigManager(s)
        pos = cfg.get_position()
        if not pos:
            bad.append("장부 시작 전 (먼저 🛠 기타 → 📥 장부 시작)")
        if credit:
            ast0 = cfg.accum_or_start()
            if ast0.get("mode") != "ladder" or ast0.get("filled_levels"):
                bad.append("1회차 차감 불가: 이미 사다리 매수가 시작됐거나 재매수 모드")
        if bad:
            print("✗ 추가 투입 반영 안 함:\n" + "\n".join("- " + to_korean(b) for b in bad))
            return 1
        api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
        hold, _, _ = api.holding(s["symbol"])
        want = int(pos["qty"]) + qty
        note = Notifier(s["telegram_file"], dry_run=s.get("dry_run", True))
        if hold != want:
            msg = f"✗ 추가 투입 반영 안 함: 메리츠 잔고 {hold}주 ≠ 장부 {pos['qty']}주 + {qty}주 = {want}주 (주문 없음)"
            print(msg)
            logging.warning(msg)
            note.send("⛔ " + msg[2:])
            return 1
        t0, g0 = sell_target(s, cfg, pos)
        before, after = cfg.add_shares(qty, avg, n.strftime("%Y-%m-%d"))
        t1, g1 = sell_target(s, cfg, after)
        a0, a1 = cfg.avg_price(before), cfg.avg_price(after)
        cr_txt = ""
        if credit:
            ast = cfg.accum_or_start()
            ast["credit_usd"] = round(float(ast.get("credit_usd") or 0) + qty * avg, 2)
            cfg.save_accum(ast)
            cr_txt = f"\n1회차 매수 때 차감: +${qty * avg:,.0f} (합계 ${ast['credit_usd']:,.0f})"
        msg = (f"➕ 추가 투입 반영 {qty}주 @ ${avg:.2f} (주문 없음)\n"
               f"전: {before['qty']}주 · 원금 ${before['principal']:,.0f} · 평단 ${a0:.2f} · 회차 {t0} · 매도 목표 ${g0:.2f}\n"
               f"후: {after['qty']}주 · 원금 ${after['principal']:,.0f} · 평단 ${a1:.2f} · 회차 {t1} · 매도 목표 ${g1:.2f}" + cr_txt)
        hist = cfg._load_json("data/add_shares_log.json", [])
        hist.append({"at": n.isoformat(), "qty": qty, "avg": avg, "hold": hold, "credit": bool(credit),
                     "before": {"qty": before["qty"], "principal": before["principal"], "avg": a0},
                     "after": {"qty": after["qty"], "principal": after["principal"], "avg": a1}})
        cfg._save_json("data/add_shares_log.json", hist)
        logging.info(msg.replace("\n", " | "))
        print(msg)
        if cfg.get_halt():
            print(f"ℹ️ 정지 표시는 그대로 있음: {cfg.get_halt().get('reason')} (확인한 뒤 ⛔ 정지 해제)")
        note.send(msg)
    return 0


def cmd_inject_start(s, overwrite=False, api=None):
    """--inject-start (v1.0.2 main() 안의 본문 그대로 옮김 — CLI·텔레그램 메뉴가 같은 함수) → 0/1"""
    state = s["state_dir"]
    os.makedirs(os.path.join(state, "data"), exist_ok=True)
    bad = validate_settings(s) + check_identity(s)[0]
    if not s.get("transfer_confirmed"):
        bad.append("입고 확인 전 (먼저 입고를 확인해 주세요)")
    if bad:
        print("✗ 장부 시작 안 함:\n" + "\n".join("- " + to_korean(b) for b in bad))
        return 1
    api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
    hold, _, _ = api.holding(s["symbol"])
    want = int(float(s["start"]["qty"]))
    if hold != want:
        print(f"✗ 메리츠 잔고 {hold}주 ≠ 시작 수량 {want}주 — 입고 미완료 또는 다른 계좌")
        return 1
    with in_dir(state):
        cfg = ConfigManager(s)
        pos, wrote = cfg.inject_start(overwrite=overwrite)
        print(("장부 시작: " if wrote else "이미 장부 있음 (덮어쓰려면 덮어쓰기 확인): ")
              + f"{pos['qty']}주 · 원금 ${pos['principal']:,.0f} · 평단 ${cfg.avg_price(pos):.2f}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="메리츠 속쓸 적립봇")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fingerprint", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--inject-start", action="store_true")
    g.add_argument("--clear-halt", action="store_true")
    g.add_argument("--add-shares", action="store_true", help="직접 산 주식을 지정 평단으로 장부 반영 (--qty N --avg X)")
    ap.add_argument("--overwrite", action="store_true", help="--inject-start 때 기존 장부 덮어쓰기")
    ap.add_argument("--qty", type=int, help="--add-shares: 추가한 주식 수 (1 이상)")
    ap.add_argument("--avg", type=float, help="--add-shares: 추가한 주식의 평단 (달러)")
    ap.add_argument("--credit", action="store_true", help="--add-shares: 추가한 주식의 원가(수량×평단)를 1회차 매수 때 한 번 차감")
    a = ap.parse_args(argv)
    s = load_settings()
    if a.fingerprint:
        print(key_fingerprint(s["key_file"]))
        return 0
    if a.check:
        return cmd_check(s)
    if a.add_shares:
        return cmd_add_shares(s, a.qty, a.avg, credit=a.credit)
    state = s["state_dir"]
    os.makedirs(os.path.join(state, "data"), exist_ok=True)
    if a.clear_halt:
        with in_dir(state):
            ConfigManager(s).clear_halt()
        print("정지 표시 해제")
        return 0
    if a.inject_start:
        return cmd_inject_start(s, a.overwrite)
    loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
