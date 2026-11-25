# ==========================================================
# FILE: meritz_laoer/config.py   (MERITZ_LAOER v2.7.0 · 판 39 v2.12.0)
# v2.13.0 (2026-11-24, 판 40): sniper_tick_sec(기본 1.5)·sniper_book_sec(기본 10) 추가 + validate_settings 검사. sync_time_et 는 '하루 기록 마감 시각'이고 스나이퍼 틱 끝 시각이 아님 (틱은 매도·매수 창이 정함)
# v2.12.0 (2026-11-24, 판 39): sniper_portion_pct·tower_remaining_seed_usd·sniper_first_anchor_usd 검사 삭제(옛 키는 남아 있어도 무시) · compound_enabled(복리 모드) 검사 추가 · 기본 sync_time_et 16:10 → 20:00
# v2.10.0 (2026-11-23, 판 36 Case 113): 기본 sniper_tp_l1_pct 1.5 → 1.0 · sniper_breakout_portion_pct 검사 삭제(옛 키는 남아 있어도 무시)
# v2.9.0 6차 (2026-11-22, 판 33): validate_settings 에 trade_mode(sniper|tower)·tower_buy_gap_usd(1~10 정수) 검사 추가 (없으면 통과 = 기본값)
# v2.7.0 (2026-11-21, 판 27): 층 간격 설정(tower_gap_usd) 검사 제거 — 간격은 내부 고정값 GAP_USD=5로만 씀 (tower_strategy.params). 설정 파일에 tower_gap_usd가 남아 있어도 통과함 (무시).
# v2.6.0 (2026-11-21, 판 26): validate_settings 에 sniper_portion_pct 검사 (없으면 통과·기본 8, 있으면 0 초과 100 이하 숫자)
# v2.2.20 (2026-11-21, 판 22 듀얼 모드): SAFE_DEFAULTS 에 trading_mode("tower" 기본 | "sniper") · sniper_tp_l1_pct(1.5) · sniper_tp_upper_pct(1.0) 추가. validate_settings 가 trading_mode 값(sniper|tower)·익절 % (0 초과 50 이하)를 검사하고, 스나이퍼 모드는 order_type=LIMIT · intraday_sell_check_sec>=30 이어야 통과(탑쌓기 모드는 예전 그대로). 나머지는 그대로
# v2.2.17 (2026-11-20, 판 20 하루 매수·매도 층 수 설정): validate_settings 에 tower_max_buy_layers_per_day · tower_max_sell_layers_per_day 검사 추가 — 없으면 통과(기본 1), 있으면 1~3 정수만 (0·4 이상·소수·글자·true/false 는 문제 목록에 넣어 주문 전에 막음). DEFAULTS 에는 안 넣음(없을 때 코드가 1 로 읽음). 나머지는 그대로
# v2.2.9 (2026-11-20, audit-fix 7번 3차 — 풀이님 결정 10:14): 사다리 삭제로 탑쌓기 전용 — credit_problems·CHOICES(unit_base·first_buy_mode)·ladder_levels·적립 상태(accum_state.json: get_accum/save_accum/accum_or_start)·사다리 설정 키·start.mode/filled_levels/rebuy_*/first_round_credit_usd 제거. validate_settings(s) 는 사다리 값을 안 보고, tower_gap_usd(1 이상 정수)·tower_floor_usd(>0)·tower_floors(1 이상 정수) 와 strategy("tower" 가 아니면 차단)를 검사. order_type(LOC|LIMIT) 검사는 그대로
# v2.2.6 (2026-11-20, 판 16 본격): ① intraday_sell_check_sec 기본 120 → 30 (코드 검증 하한 — 체결 알림 간격과 같게) ② apply_fill: 같은 체결(exec_id)을 장부 파일(position.json)의 applied_ids 로도 막고(원금·수량이 먼저 저장돼 중복·누락이 안 생김),
#   매도 때 F별 매도의 '뺀 원가'(cost_removed)를 받으면 평단 비례 대신 그 값을 씀 (F 합계와 장부 원금이 어긋나지 않게). 호출 형식은 그대로(새 인자는 선택)
# v2.2.1 (2026-11-19, audit-fix 7-1): credit_problems 추가 + validate_settings(s, fx=None) — 환율을 알면 start.first_round_credit_usd < 1회차 단위액(total_krw÷split_count÷환율) 검사. 그 외 검증은 그대로
# v2.0.3 (2026-11-18): 설정 intraday_sell_check_sec 추가(당일 매도 확인 간격 초, 기본 120, 0 이면 끔) + validate_settings 에 그 값 검사 한 줄. 나머지 검증·장부 함수는 그대로
# 메리츠 속쓸 적립봇(SOXL 분할매수·부분매도) — 설정·장부
# v2.0.1 (2026-11-18): update_settings 추가 (텔레그램 설정 메뉴용 — 설정 파일 일부 키만 바꿔 저장), _merge 분리. 검증·장부·기존 함수는 그대로
# v2.0.0 (2026-11-18): 적립봇 전환. 설정 키 추가(total_krw·ladder_*·sell_*·rebuy_drop_usd·unit_base·first_buy_mode·max_rounds_per_day·
#   order_type·allow_consecutive_sell, start.mode·filled_levels·rebuy_anchor_usd·rebuy_k), validate_settings 새로 씀,
#   적립 상태 파일 data/accum_state.json (get_accum/save_accum), inject_start 가 상태도 같이 시작.
#   장부(position·ledger)·apply_fill·add_shares·halt 와 V14 용 함수들은 그대로(V14 함수는 이제 안 불림)
# v1.0.2 (2026-11-08): add_shares 추가 — 사용자가 직접 산 주식을 지정 평단으로 장부에 더함 (기존 장부 형식 그대로)
# v1.0.0 (2026-11-08): 첫 버전. hantu_laoer/config.py 에서 V14 가 쓰는 함수만 같은 이름·같은 동작으로 옮김
#   - 옮긴 함수(동작 그대로): get_reverse_state, set_reverse_state, apply_reverse_daily_settlement,
#     increment_reverse_day, get_seed/set_seed, get_split_count, get_target_profit, get_fee, get_compound_rate
#   - 다른 점: 분할수·시드는 기본값 없음(설정 파일 필수). 시작 원금·수량·평단은 설정값으로 주입(입고 평단 안 믿음)
#   - hantu_laoer 는 수정하지 않음 (이 폴더는 독립)
# 설정 파일: /etc/meritz-laoer/settings.json (GitHub 에 올리지 않음, 예시는 settings.example.json)
# 장부 폴더: 설정 state_dir (기본 /var/lib/meritz-laoer) 아래 data/
# ==========================================================
import datetime
import json
import math
import os
import tempfile
from zoneinfo import ZoneInfo

from global_throttle import GlobalThrottle

SETTINGS_PATH = os.environ.get("MERITZ_LAOER_SETTINGS", "/etc/meritz-laoer/settings.json")
EST = ZoneInfo("America/New_York")

# 기본값은 안전한 쪽만 둔다. 금액·분할수는 기본값 없음(설정 필수).
SAFE_DEFAULTS = {
    "enabled": False,                      # 기본 꺼짐. 토스 전량 입고 확인 뒤 승인하고 켬
    "dry_run": True,                       # 모의 실행 (주문 API 를 부르지 않음)
    "transfer_confirmed": False,           # 입고 확인 (사람이 확인 후 true)
    "toss_sniper_stopped_confirmed": False,  # 토스 스나이퍼 정지·미체결 0건 확인 (사람이 확인 후 true)
    "symbol": "SOXL",
    "price_market": "AX",                  # 메리츠 시세 조회용 거래소 구분 (bot_office/fanding_trade.py 와 같음)
    "exch_id": "",                         # 주문용 거래소 번호. 비우면 잔고 행에서 찾음
    "split_count": None,                   # 적립봇: 10 (총 투자금을 10 등분). 비어 있으면 주문 안 함
    "seed_usd": None,                      # (V14 용, 적립봇은 안 씀)
    # ---- 적립봇 (노션 '메리츠 속쓸 적립봇' 2026-11-18)
    "total_krw": None,                     # 총 투자금(원). 금액은 기본값 없음 — 설정 필수
    "tower_floor1_start_usd": 0,           # 탑쌓기 맨 위 F 시작가 (v2.2.4). 0 = 안 정함 — 평단 기준. 정하면 맨 위 F 칸이 시작가 기준
    "sell_profit_pct": 10,                 # 평단 대비 평가 이익 이 % 에 매도
    "sell_fraction_pct": 50,               # 보유의 이 % 매도 (정수 주 내림)
    "order_type": None,                    # 노션 Q5: LOC | LIMIT — 비어 있으면 주문 안 함
    "allow_consecutive_sell": None,        # 노션 Q6: true | false — 비어 있으면 주문 안 함
    "trading_mode": "tower",               # v2.2.20 판 22: "tower"(탑쌓기, 기본) | "sniper"(스나이퍼). 바꾸면 다음 매매 판단부터 적용 (이미 낸 주문은 안 건드림). F 장부는 두 모드가 같이 씀
    "sniper_tp_l1_pct": 1.0,               # v2.2.20 스나이퍼 1층(공격 층 = 평단 가장 낮은 F) 익절 % (F 평단 +이 % 에 그 F 전량)
    "sniper_tp_upper_pct": 1.0,            # v2.2.20 스나이퍼 상단층 익절 %
    "sniper_tick_sec": 1.5,                # v2.13.0 판 40 할 일 1: 스나이퍼 틱 간격(초, 1.5~3600). 되돌리기: API·서버 부하 문제가 보이면 30 으로 (코드 수정 없이 설정만 — VERIFY.md '되돌리기 조건'). 서버 설정 파일 값이 우선
    "assassin_live_unlock": True,          # 판 41 할 일 1: 암살자 실전 루프 연결됨 → 승격 잠금 해제 (되돌리기: false). 승격은 텔레그램 2단계 확인 그대로
    "sniper_book_sec": 10,                 # v2.13.0 판 40: 1.5초 틱 사이에 체결·잔고·미체결·예수금 조회를 다시 쓰는 시간(초, 1~60). 주문을 낸 직후엔 즉시 다시 조회
    "intraday_sell_check_sec": 30,         # v2.0.3 당일 매도 (v2.2.6 기본 120→30): 장중 이 간격(초)마다 매도 조건·체결(알림) 확인. 0 이면 끄고 예전처럼 아침 주문만. LIMIT 주문일 때만 동작. 서버 설정 파일에 값이 있으면 그 값이 우선
    # ---- 자동환전 (사용자 요청 2026-11-18). 기본 꺼짐. 켜려면 아래 두 값도 설정 필수 (노션 Q11)
    "auto_fx_enabled": False,              # true 면 오늘 매수에 달러가 모자랄 때 원화→달러 환전 신청 (실주문 모드에서만)
    "auto_fx_buffer_pct": None,            # 부족 달러에 더할 여유 % (환율·체결가 변동 대비)
    "auto_fx_max_usd_per_day": None,       # 하루 환전 상한 (달러, 정수)
    # 익절 %: hantu_laoer/config.py DEFAULT_TARGET["SOXL"] (main c53f8d4 기준). 서버 data/profit_config.json 값은 확인 필요
    "target_profit_pct": 12.0,
    # 복리 %: hantu_laoer/config.py DEFAULT_COMPOUND["SOXL"] (익절 이익 중 다음 시드에 더하는 비율)
    "compound_rate_pct": 70.0,
    "fee_pct": 0.07,                       # Super365 미국주식 0.07%
    "start": {"qty": None, "principal_usd": None, "avg_usd": None},
    "key_file": "/etc/meritz-laoer/meritz_keys.json",      # 새 메리츠 3번 계좌 키 (P·VR6 키 재사용 금지)
    "expected_key_fp": "",                 # main.py --fingerprint 로 확인한 지문. 다르면 정지
    "forbid_key_files": ["/etc/bot-office/meritz.json", "/etc/bot-office/meritz_vr6.json"],
    "telegram_file": "/etc/meritz-laoer/telegram.json",    # 새 텔레그램 봇 토큰 {"token":..., "chat_id":...}
    "forbid_telegram_files": [],           # 다른 봇 토큰 파일 경로(같은 토큰이면 정지)
    "state_dir": "/var/lib/meritz-laoer",
    "order_time_et": "10:05",              # 주문 시각 (미국 동부). 이 시각~order_deadline_et 사이 1회
    "order_deadline_et": "15:40",          # LOC 접수 마감(15:50) 전
    "sync_time_et": "20:00",               # 체결 확인 시각 (미국 동부) — v2.12.0 판 39: 16:10 → 20:00 (애프터마켓 매도 체결까지 기다림)
}


def _merge(user):
    """설정 파일 내용(user) 위에 기본값을 깐 전체 설정"""
    s = json.loads(json.dumps(SAFE_DEFAULTS))
    for k, v in user.items():
        if k == "start" and isinstance(v, dict):
            s["start"].update(v)
        else:
            s[k] = v
    return s


def load_settings(path=None):
    p = path or SETTINGS_PATH
    with open(p, "r", encoding="utf-8") as f:
        user = json.load(f)
    if not isinstance(user, dict):
        raise ValueError("설정 파일 형식 오류 (JSON 객체 아님)")
    return _merge(user)


def _f(v):
    try:
        x = float(str(v if v is not None else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def update_settings(changes, path=None, dry=False):
    """v2.0.1 텔레그램 메뉴용: 설정 파일(JSON)에서 changes 의 키만 바꿔 저장 → {키: (이전 값, 새 값)}.
    - 파일에 적힌 키만 건드림 (기본값을 섞어 쓰지 않음). 바꾼 뒤 validate_settings 에 '새로 생기는' 문제가 있으면 ValueError (저장 안 함)
    - dry=True 면 검사만 하고 쓰지 않음
    - 원자적 저장(같은 폴더 임시 파일 → replace, 권한 유지). 폴더 쓰기 권한이 없으면 파일 자체에 덮어씀. 둘 다 안 되면 OSError
    - 저장 전 원본을 state_dir/data/settings_before_change.json 에 복사, 바꾼 내용을 data/settings_change_log.json 에 기록 (실패해도 무시)"""
    p = path or SETTINGS_PATH
    with GlobalThrottle.get_file_lock(p):
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("설정 파일 형식 오류 (JSON 객체 아님)")
        before = _merge(raw)
        new_raw = dict(raw)
        new_raw.update(changes)
        after = _merge(new_raw)
        old_bad = validate_settings(before)
        new_bad = [b for b in validate_settings(after) if b not in old_bad]
        if new_bad:
            raise ValueError("; ".join(new_bad))
        result = {k: (before.get(k), after.get(k)) for k in changes}
        if dry:
            return result
        data = json.dumps(new_raw, ensure_ascii=False, indent=2) + "\n"
        sd = str(after.get("state_dir") or "")
        try:
            os.makedirs(os.path.join(sd, "data"), exist_ok=True)
            with open(os.path.join(sd, "data", "settings_before_change.json"), "w", encoding="utf-8") as f:
                f.write(text)
            lp = os.path.join(sd, "data", "settings_change_log.json")
            try:
                with open(lp, "r", encoding="utf-8") as f:
                    log = json.load(f)
                if not isinstance(log, list):
                    log = []
            except (OSError, ValueError):
                log = []
            log.append({"at": datetime.datetime.now(EST).isoformat(), "changes": {k: {"old": o, "new": n} for k, (o, n) in result.items()}})
            with open(lp, "w", encoding="utf-8") as f:
                json.dump(log[-200:], f, ensure_ascii=False, indent=2)
        except (OSError, ValueError):
            pass
        try:
            d = os.path.dirname(os.path.abspath(p))
            fd, tmp = tempfile.mkstemp(dir=d, text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                st = os.stat(p)
                os.chmod(tmp, st.st_mode & 0o7777)
                try:
                    os.chown(tmp, st.st_uid, st.st_gid)
                except OSError:
                    pass
                os.replace(tmp, p)
            except Exception:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
        except PermissionError:
            with open(p, "w", encoding="utf-8") as f:     # 폴더는 못 써도 파일은 쓸 수 있는 경우
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        return result


def validate_settings(s):
    """주문 전에 꼭 있어야 하는 값 검사 → 문제 목록 (빈 목록이면 통과). v2.2.9: 탑쌓기 전용 — 사다리 값(회차·시작가·간격·재매수·하루 회차 등)은 검사하지 않음"""
    bad = []
    if str(s.get("strategy") or "").strip().lower() not in ("", "tower"):
        bad.append("strategy 값이 남아 있음 — 7번은 탑쌓기만 써요 (사다리 삭제). 설정 파일에서 strategy 를 지우거나 \"tower\" 로 고쳐 주세요")
    if s.get("total_krw") is None or _f(s.get("total_krw")) <= 0:
        bad.append("total_krw 없음 (총 투자금, 원)")
    if _f(s.get("tower_floor1_start_usd")) < 0:
        bad.append("tower_floor1_start_usd 는 0 이상 (0 = 안 정함)")
    for k in ("sell_profit_pct",):
        if _f(s.get(k)) <= 0:
            bad.append(f"{k} 0 이하 또는 없음")
    fu = s.get("tower_floor_usd")
    if fu is not None and (isinstance(fu, bool) or _f(fu) <= 0):
        bad.append("tower_floor_usd 는 0 보다 큰 숫자 (F 완성 기준 금액, 달러)")
    for k, nm in (("tower_box_seed_usd", "버킷 시드, 달러"),):      # v2.12.0 판 39: 남은 시드·첫 기준가 키 삭제      # v2.5.0: 없으면 기본(15000 · 120000 · 안 정함), 있으면 0 보다 큰 숫자
        v = s.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or _f(v) <= 0):
            bad.append(f"{k} 는 0 보다 큰 숫자 ({nm})")
    # v2.10.0 판 36 D4: sniper_breakout_portion_pct(돌파 매수 비율)는 돌파 폐기로 안 씀 — 설정 파일에 남아 있어도 검사·사용 없이 무시
    # v2.12.0 판 39: sniper_portion_pct(눌림 매수%) 삭제 — 비율은 모드(복리 8·단리 10)로만 정함. 설정 파일에 남아 있어도 검사·사용 없이 무시
    ce = s.get("compound_enabled")      # v2.12.0 판 39: 복리 모드 — 없으면 꺼짐(단리), 있으면 true/false 만
    if ce is not None and not isinstance(ce, bool):
        bad.append("compound_enabled 는 true 또는 false (복리 모드)")
    tm = s.get("trade_mode")      # v2.9.0 6차 판 33: 매매 모드 — 없으면 sniper(하이브리드 스나이퍼), 있으면 sniper | tower 만
    if tm is not None and tm not in ("sniper", "tower"):
        bad.append("trade_mode 는 sniper 또는 tower (매매 모드)")
    bg = s.get("tower_buy_gap_usd")      # 탑쌓기 매매 매수 간격 — 없으면 5, 있으면 1~10 정수
    if bg is not None and (isinstance(bg, bool) or not isinstance(bg, (int, float)) or not (1 <= _f(bg) <= 10) or _f(bg) != int(_f(bg))):
        bad.append("tower_buy_gap_usd 는 1~10 정수 (탑쌓기 매매 매수 간격, 달러)")
    fl = s.get("tower_floors")
    if fl is not None and (isinstance(fl, bool) or _f(fl) < 1 or _f(fl) != int(_f(fl))):
        bad.append("tower_floors 는 1 이상 정수 (F 수)")
    for k, nm in (("tower_max_buy_layers_per_day", "하루 매수 F 수"), ("tower_max_sell_layers_per_day", "하루 매도 F 수")):      # v2.2.17: 없으면 기본 1, 있으면 1~3 정수만
        v = s.get(k)
        if v is not None and (isinstance(v, bool) or not (1 <= _f(v) <= 3) or _f(v) != int(_f(v))):
            bad.append(f"{k} 는 1~3 정수 ({nm})")
    if not (0 < _f(s.get("sell_fraction_pct")) < 100):
        bad.append("sell_fraction_pct 는 0 초과 100 미만")
    if s.get("order_type") not in ("LOC", "LIMIT"):
        bad.append("order_type 미정 (LOC | LIMIT 중 Muse 결정 필요 — 노션 질문)")
    if not isinstance(s.get("allow_consecutive_sell"), bool):
        bad.append("allow_consecutive_sell 미정 (true | false, Muse 결정 필요 — 노션 질문)")
    isec = s.get("intraday_sell_check_sec")
    if isinstance(isec, bool) or not isinstance(isec, (int, float)) or not (isec == 0 or 30 <= isec <= 3600):
        bad.append("intraday_sell_check_sec 는 0(끔) 또는 30~3600 (초)")
    for k, lo, hi in (("sniper_tick_sec", 1.5, 3600), ("sniper_book_sec", 1, 60)):      # v2.13.0 판 40: 없으면 기본값 (SAFE_DEFAULTS)
        v = s.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not (lo <= v <= hi)):
            bad.append(f"{k} 는 {lo:g}~{hi:g} (초)")
    tm = s.get("trading_mode")      # v2.2.20: 없으면 탑쌓기 (예전 동작)
    if tm is not None and str(tm).strip().lower() not in ("sniper", "tower"):
        bad.append("trading_mode 는 sniper | tower")
    for k in ("sniper_tp_l1_pct", "sniper_tp_upper_pct"):
        v = s.get(k)
        if v is not None and (isinstance(v, bool) or not (0 < _f(v) <= 50)):
            bad.append(f"{k} 는 0 초과 50 이하 (익절 %)")
    if str(tm or "tower").strip().lower() == "sniper":
        if s.get("order_type") != "LIMIT":
            bad.append("스나이퍼 모드는 order_type=LIMIT 이어야 해요 (장중 지정가 매매)")
        if isinstance(isec, bool) or not isinstance(isec, (int, float)) or isec < 30:
            bad.append("스나이퍼 모드는 intraday_sell_check_sec 30 이상이어야 해요 (0=끔 불가)")
    if not isinstance(s.get("auto_fx_enabled"), bool):
        bad.append("auto_fx_enabled 는 true | false")
    elif s.get("auto_fx_enabled"):
        if s.get("auto_fx_buffer_pct") is None or _f(s.get("auto_fx_buffer_pct")) < 0:
            bad.append("auto_fx_enabled=true 인데 auto_fx_buffer_pct 없음 (0 이상, 노션 질문 Q11)")
        if s.get("auto_fx_max_usd_per_day") is None or _f(s.get("auto_fx_max_usd_per_day")) <= 0:
            bad.append("auto_fx_enabled=true 인데 auto_fx_max_usd_per_day 없음 (0 초과, 노션 질문 Q11)")
    st = s.get("start") or {}
    q, pr, av = st.get("qty"), st.get("principal_usd"), st.get("avg_usd")
    if q is None or int(_f(q)) < 0 or _f(q) != int(_f(q)):
        bad.append("start.qty 없음 (0 이상 정수)")
    if pr is None or _f(pr) < 0:
        bad.append("start.principal_usd 없음 (0 이상)")
    if q is not None and int(_f(q)) > 0 and (pr is None or _f(pr) <= 0):
        bad.append("start.qty > 0 인데 principal_usd 가 0 이하")
    if q and pr and av is not None and _f(av) > 0 and int(_f(q)) > 0:
        if abs(_f(pr) / int(_f(q)) - _f(av)) > 0.01:
            bad.append("start.avg_usd 가 principal_usd ÷ qty 와 0.01 넘게 다름 — 숫자 확인")
    if str(s.get("symbol", "")).upper() != "SOXL":
        bad.append("이 봇은 SOXL 전용")
    return bad


class ConfigManager:
    """strategy_v14.V14Strategy 가 부르는 함수만 제공. 파일은 현재 작업 폴더 기준 data/ (main 이 state_dir 로 chdir)"""

    def __init__(self, settings):
        self.s = settings
        self.FILES = {
            "SEED_CFG": "data/seed_config.json",
            "REVERSE_CFG": "data/reverse_config.json",
            "LEDGER": "data/manual_ledger.json",
            "HISTORY": "data/manual_history.json",
            "POSITION": "data/position.json",
            "HALT": "data/halt.json",
        }
        os.makedirs("data", exist_ok=True)

    # ---------------- 파일 입출력 (원자적 저장)
    def _safe_float(self, v):
        return _f(v)

    def _load_json(self, path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return json.loads(json.dumps(default))

    def _save_json(self, path, data):
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    # ---------------- 설정값 (분할수·익절·수수료·복리)
    def get_split_count(self, t):
        return _f(self.s.get("split_count"))          # 하드코딩 없음 — 설정값만

    def get_target_profit(self, t):
        return _f(self.s.get("target_profit_pct"))

    def get_fee(self, t):
        return _f(self.s.get("fee_pct"))

    def get_compound_rate(self, t):
        return _f(self.s.get("compound_rate_pct"))

    def get_version(self, t):
        return "V14"

    def get_manual_vwap_mode(self, t):
        return False

    # ---------------- 시드: 처음엔 설정 seed_usd, 익절 뒤 복리로 늘어난 값은 장부에 저장
    def get_seed(self, t):
        with GlobalThrottle.get_file_lock(self.FILES["SEED_CFG"]):
            d = self._load_json(self.FILES["SEED_CFG"], {})
            if t in d:
                return _f(d[t])
            return _f(self.s.get("seed_usd"))

    def set_seed(self, t, v):
        with GlobalThrottle.get_file_lock(self.FILES["SEED_CFG"]):
            d = self._load_json(self.FILES["SEED_CFG"], {})
            d[t] = _f(v)
            self._save_json(self.FILES["SEED_CFG"], d)

    # ---------------- 리버스 상태 (hantu_laoer/config.py 와 같은 동작)
    def get_reverse_state(self, ticker):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            val = d.get(ticker)
            if not isinstance(val, dict):
                return {
                    "is_active": False, "day_count": 0, "exit_target": 0.0,
                    "last_update_date": "", "dynamic_t": 0.0, "rem_cash": 0.0, "is_day_one": True,
                    "last_t_update_date": ""
                }
            val.setdefault("dynamic_t", 0.0)
            val.setdefault("rem_cash", 0.0)
            val.setdefault("is_day_one", val.get("day_count", 0) == 0)
            val.setdefault("last_t_update_date", val.get("last_update_date", ""))
            return val

    def set_reverse_state(self, ticker, is_active, day_count, exit_target=0.0, last_update_date=None, dynamic_t=0.0, rem_cash=0.0, is_day_one=None):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            if last_update_date is None:
                last_update_date = datetime.datetime.now(EST).strftime('%Y-%m-%d')
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            d[ticker] = {
                "is_active": is_active,
                "day_count": day_count,
                "exit_target": _f(exit_target),
                "last_update_date": last_update_date,
                "last_t_update_date": last_update_date,
                "dynamic_t": _f(dynamic_t),
                "rem_cash": _f(rem_cash),
                "is_day_one": (day_count == 0) if is_day_one is None else bool(is_day_one)
            }
            self._save_json(self.FILES["REVERSE_CFG"], d)

    def apply_reverse_daily_settlement(self, ticker):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            state = d.get(ticker)
            if not isinstance(state, dict) or not state.get("is_active", False):
                return
            today_str = datetime.datetime.now(EST).strftime('%Y-%m-%d')
            last_t_update_date = state.get("last_t_update_date", "") or state.get("last_update_date", "")
            if last_t_update_date == today_str:
                return
            split = self.get_split_count(ticker)
            dynamic_t = _f(state.get("dynamic_t", 0.0))
            rem_cash = _f(state.get("rem_cash", 0.0))
            with GlobalThrottle.get_file_lock(self.FILES["LEDGER"]):
                ledger = self._load_json(self.FILES["LEDGER"], [])
            if not isinstance(ledger, list):
                ledger = []
            target_recs = [
                r for r in ledger
                if isinstance(r, dict) and r.get("ticker") == ticker and r.get("is_reverse", False)
                and last_t_update_date <= str(r.get("date", ""))[:10] < today_str
            ]
            buy_sum = sell_sum = 0.0
            had_buy = had_sell = False
            for r in target_recs:
                amt = int(_f(r.get("qty", 0))) * _f(r.get("price", 0.0))
                if r.get("side") == "BUY":
                    buy_sum += amt
                    had_buy = True
                elif r.get("side") == "SELL":
                    sell_sum += amt
                    had_sell = True
            if had_buy or had_sell:
                rem_cash = max(0.0, rem_cash + sell_sum - buy_sum)
                if had_sell:
                    if split <= 20:
                        dynamic_t *= 0.9
                    else:
                        dynamic_t *= 0.95
                if had_buy:
                    dynamic_t += (split - dynamic_t) * 0.25
            state["rem_cash"] = round(rem_cash, 2)
            state["dynamic_t"] = round(dynamic_t, 4)
            state["last_t_update_date"] = today_str
            d[ticker] = state
            self._save_json(self.FILES["REVERSE_CFG"], d)

    def increment_reverse_day(self, ticker):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            state = d.get(ticker)
            if not isinstance(state, dict):
                return False
            if state.get("is_active"):
                today_est_str = datetime.datetime.now(EST).strftime('%Y-%m-%d')
                if state.get("last_update_date") != today_est_str:
                    state["day_count"] = state.get("day_count", 0) + 1
                    state["last_update_date"] = today_est_str
                    state["is_day_one"] = False
                    d[ticker] = state
                    self._save_json(self.FILES["REVERSE_CFG"], d)
                    return True
        return False

    # ---------------- 보유 장부 (원금·수량은 봇 장부가 기준. 메리츠 입고 평단은 쓰지 않음)
    def get_position(self):
        return self._load_json(self.FILES["POSITION"], None)

    def inject_start(self, overwrite=False):
        """설정 start 값으로 장부 시작 (입고 평단 덮어쓰기). 이미 있으면 overwrite=True 일 때만"""
        with GlobalThrottle.get_file_lock(self.FILES["POSITION"]):
            cur = self.get_position()
            if cur and not overwrite:
                return cur, False
            st = self.s["start"]
            qty, principal = int(_f(st["qty"])), round(_f(st["principal_usd"]), 2)
            pos = {"ticker": self.s["symbol"], "qty": qty, "principal": principal,
                   "cycle_buy_total": principal, "cycle_sell_total": 0.0, "cycle_start": datetime.datetime.now(EST).strftime('%Y-%m-%d'),
                   "source": "settings.start (입고 평단 미사용)"}
            self._save_json(self.FILES["POSITION"], pos)
            return pos, True

    def add_shares(self, qty, avg, date_et):
        """사용자가 직접 추가한 주식을 지정 평단으로 장부에 더함 → (변경 전, 변경 후).
        수량 += qty, 원금 += qty × avg, 평단 = 원금 ÷ 수량 (avg_price 와 같은 4자리 규칙). 입고 평단은 쓰지 않음"""
        qty, avg = int(qty), _f(avg)
        if qty < 1 or avg <= 0:
            raise ValueError("qty 는 1 이상 정수, avg 는 0 보다 커야 함")
        with GlobalThrottle.get_file_lock(self.FILES["POSITION"]):
            pos = self.get_position()
            if not pos:
                raise RuntimeError("장부 없음 (start 주입 전)")
            before = dict(pos)
            amt = qty * avg
            pos["qty"] = int(pos["qty"]) + qty
            pos["principal"] = round(_f(pos["principal"]) + amt, 4)
            pos["cycle_buy_total"] = round(_f(pos.get("cycle_buy_total")) + amt, 4)
            ledger = self._load_json(self.FILES["LEDGER"], [])
            ledger.append({"id": len(ledger) + 1, "date": date_et, "ticker": pos["ticker"], "side": "BUY",
                           "price": avg, "qty": qty, "avg_price": self.avg_price(before),
                           "exec_id": f"add_{datetime.datetime.now(EST).strftime('%Y%m%dT%H%M%S')}",
                           "is_reverse": bool(self.get_reverse_state(pos["ticker"]).get("is_active"))})
            self._save_json(self.FILES["LEDGER"], ledger)
            self._save_json(self.FILES["POSITION"], pos)
            return before, pos

    def avg_price(self, pos):
        q = int(_f((pos or {}).get("qty")))
        return round(_f(pos.get("principal")) / q, 4) if q > 0 else 0.0

    def apply_fill(self, side, qty, price, date_et, is_reverse, exec_id, cost_removed=None):
        """체결 1건 반영 → (새 장부, 끝난 사이클 기록 또는 None). 같은 exec_id 는 한 번만.
        v2.2.6: 한 번 반영한 exec_id 는 position.json 의 applied_ids 에 함께 저장 (원금·수량과 한 파일이라 같이 저장됨) — 원금·수량을 먼저, 거래 기록을 나중에 쓰므로
        중간에 멈춰도 다시 부르면 빠진 쪽만 채움 (원금·수량은 두 번 안 바뀜). cost_removed: 매도 때 줄일 원가 (F별 매도가 계산한 값. 없으면 예전처럼 평단 × 수량)"""
        with GlobalThrottle.get_file_lock(self.FILES["POSITION"]):
            pos = self.get_position()
            if not pos:
                raise RuntimeError("장부 없음 (start 주입 전)")
            ledger = self._load_json(self.FILES["LEDGER"], [])
            in_ledger = any(isinstance(r, dict) and r.get("exec_id") == exec_id for r in ledger)
            ids = pos.get("applied_ids") if isinstance(pos.get("applied_ids"), list) else []
            qty, price = int(qty), _f(price)
            if qty <= 0 or price <= 0:
                return pos, None
            avg = self.avg_price(pos)
            if exec_id in ids or in_ledger:                          # 이미 반영됨 (새 코드는 원금·수량을 먼저 저장하므로 거래 기록이 있으면 원금·수량도 반영된 것. 예전 장부는 applied_ids 가 없어 거래 기록으로 판단)
                if not in_ledger:                                    # 원금·수량은 저장됐는데 거래 기록만 빠진 경우 (중간에 멈춤) → 기록만 채움
                    ledger.append({"id": len(ledger) + 1, "date": date_et, "ticker": pos["ticker"], "side": side,
                                   "price": price, "qty": qty, "avg_price": avg, "exec_id": exec_id, "is_reverse": bool(is_reverse), "late_record": True})
                    self._save_json(self.FILES["LEDGER"], ledger)
                return pos, None
            if side == "BUY":
                pos["qty"] += qty
                pos["principal"] = round(pos["principal"] + qty * price, 4)
                pos["cycle_buy_total"] = round(pos["cycle_buy_total"] + qty * price, 4)
            else:
                if qty > pos["qty"]:
                    raise RuntimeError(f"매도 체결 {qty}주가 장부 {pos['qty']}주보다 많음")
                pos["qty"] -= qty
                out = qty * avg if cost_removed is None else _f(cost_removed)
                pos["principal"] = round(max(0.0, pos["principal"] - out), 4) if pos["qty"] > 0 else 0.0
                pos["cycle_sell_total"] = round(pos["cycle_sell_total"] + qty * price, 4)
            pos["applied_ids"] = (ids + [exec_id])[-300:]
            self._save_json(self.FILES["POSITION"], dict(pos))        # 원금·수량 먼저 (exec_id 와 같은 파일)
            ledger.append({"id": len(ledger) + 1, "date": date_et, "ticker": pos["ticker"], "side": side,
                           "price": price, "qty": qty, "avg_price": avg, "exec_id": exec_id, "is_reverse": bool(is_reverse)})
            self._save_json(self.FILES["LEDGER"], ledger)
            done = None
            if pos["qty"] == 0:
                done = self._close_cycle(pos, date_et)
                pos = {"ticker": pos["ticker"], "qty": 0, "principal": 0.0, "cycle_buy_total": 0.0,
                       "cycle_sell_total": 0.0, "cycle_start": date_et, "source": "새출발"}
            self._save_json(self.FILES["POSITION"], pos)
            return pos, done

    def _close_cycle(self, pos, end_date):
        """hantu_laoer/config.py 졸업 정산과 같은 계산: 수수료 반영 이익 × 복리% 를 시드에 더함"""
        t = pos["ticker"]
        fee = self.get_fee(t) / 100.0
        net_in = pos["cycle_buy_total"] * (1.0 + fee)
        net_out = pos["cycle_sell_total"] * (1.0 - fee)
        profit = math.ceil((net_out - net_in) * 100) / 100.0
        yld = math.ceil(((profit / net_in * 100) if net_in > 0 else 0.0) * 100) / 100.0
        rate = self.get_compound_rate(t) / 100.0
        added = 0
        if profit > 0 and rate > 0:
            added = math.floor(profit * rate)
            self.set_seed(t, self.get_seed(t) + added)
        self.set_reverse_state(t, False, 0, 0.0)
        hist = self._load_json(self.FILES["HISTORY"], [])
        rec = {"id": len(hist) + 1, "ticker": t, "start_date": pos.get("cycle_start"), "end_date": end_date,
               "invested": net_in, "revenue": net_out, "profit": profit, "yield": yld, "added_seed": added}
        hist.append(rec)
        self._save_json(self.FILES["HISTORY"], hist)
        return rec

    # ---------------- 정지 표시 (장부·잔고 불일치 등). 사람이 --clear-halt 로 풂
    def halt(self, reason):
        self._save_json(self.FILES["HALT"], {"reason": str(reason), "at": datetime.datetime.now(EST).isoformat()})

    def get_halt(self):
        return self._load_json(self.FILES["HALT"], None)

    def clear_halt(self):
        try:
            os.remove(self.FILES["HALT"])
        except OSError:
            pass
