# ==========================================================
# FILE: meritz_laoer/barbell_adapter.py   (MERITZ_LAOER v2.15.0 · 판 41)
# 파일 이름은 옛 바벨 어댑터 그대로 (main·tg_menu 가 BB 로 부름). 바벨(금고·SGOV·60/30/10)은 판 41 할 일 5 에서 전부 삭제 — 남은 것은 암살자 쪽뿐.
# 암살자 모드(모의/0주 예약/실전)의 기준 = 원작 AssassinSimLedger(orig_sniper/assassin_plugin.py) 한 개 (프로세스 안에서 공유). 원작 코드는 한 줄도 안 고침.
# 1분 봉: 메리츠 1분봉 API 가 40봉 고정이라 직접 못 받음 → 폴링으로 종가만 쌓아 400봉 유지 (시·고·저=종가, 거래량 0 — 근사. 원작 지표와 값이 다를 수 있음)
# ==========================================================
import datetime
import json
import os
import sys

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig_sniper")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import assassin_plugin as AP         # noqa: E402  원작 복사본 (orig_sniper/)
import quant_indicators_plugin as QI  # noqa: E402  암살자 1분 지표 원작 함수

MODE_SIM, MODE_ARMED, MODE_LIVE = AP.ASSASSIN_MODE_SIMULATED, AP.ASSASSIN_MODE_ARMED_ON_ZERO, AP.ASSASSIN_MODE_LIVE
MODE_KO = {MODE_SIM: "모의", MODE_ARMED: "0주 졸업 때 실전 예약", MODE_LIVE: "실전"}
_LEDGERS = {}


def _rw(path, default=None, data=None):
    """작은 JSON 파일 읽기/쓰기 (원자적)"""
    if data is None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return data


def assassin_base_dir(state_dir):
    return os.path.join(state_dir, "data", "assassin")


def assassin_ledger(state_dir, seed_usd=0.0):
    """원작 AssassinSimLedger — state_dir 마다 한 개를 프로세스 안에서 공유 (모드 바꾼 것이 틱에 바로 보이게)"""
    key = os.path.abspath(state_dir)
    if key not in _LEDGERS:
        os.makedirs(assassin_base_dir(state_dir), exist_ok=True)
        _LEDGERS[key] = AP.AssassinSimLedger(base_dir=assassin_base_dir(state_dir), sniper_seed_usd=float(seed_usd or AP.DEFAULT_INITIAL_SEED_USD))
    return _LEDGERS[key]


def assassin_mode(state_dir):
    """저장된 execution_mode (없거나 모르는 값 = 모의)"""
    m = str(assassin_ledger(state_dir).get_state().get("execution_mode") or MODE_SIM).upper().strip()
    return m if m in AP.VALID_ASSASSIN_MODES else MODE_SIM


def assassin_set_mode(state_dir, mode, **extra):
    """execution_mode 저장 (원작 원장에). 모르는 값이면 ValueError"""
    mode = str(mode).upper().strip()
    if mode not in AP.VALID_ASSASSIN_MODES:
        raise ValueError(f"모르는 암살자 모드 {mode}")
    return assassin_ledger(state_dir).update_state_sync(execution_mode=mode, **extra)


def assassin_blocks(state_dir):
    """암살자가 실전(LIVE)이면 하이브리드는 새 매매를 안 냄 (원작 is_assassin_live_mode_state)"""
    return bool(AP.is_assassin_live_mode_state({"execution_mode": assassin_mode(state_dir)}))


def assassin_promote_plan(cur_mode, want_live, held_qty, open_orders, verified, unlocked):
    """원작 toggle_assassin_live_promotion 규칙 (계산만, 저장 안 함) → {"to": 새 모드 또는 None, "demote_after_exit": bool, "msg": 글자}.
    승격(want_live): 보유 확인이 안 되면 거절 · SOXL 0주이고 미체결 없음 → LIVE · 보유 중 → 0주 졸업 때 실전 예약(ARMED_ON_ZERO).
    복귀: 예약이면 바로 모의 · 실전이면 (포지션 없으면) 바로 모의, 포지션이 있으면 당일 청산 뒤 자동 복귀 예약.
    unlocked=False 면 승격을 막음 (판 41: 기본 True — 실전 루프 연결됨)"""
    cur = str(cur_mode or MODE_SIM).upper().strip()
    if want_live:
        if cur in (MODE_LIVE, MODE_ARMED):
            return {"to": None, "demote_after_exit": False, "msg": f"이미 {MODE_KO[cur]} 상태예요"}
        if not unlocked:
            return {"to": None, "demote_after_exit": False, "msg": "승격 잠금 중 (설정 assassin_live_unlock 이 false). 모의 그대로예요"}
        if not verified:
            return {"to": None, "demote_after_exit": False, "msg": "SOXL 보유·미체결을 확인하지 못해 승격하지 않아요 (모의 그대로)"}
        if int(held_qty or 0) == 0 and not open_orders:
            return {"to": MODE_LIVE, "demote_after_exit": False, "msg": "SOXL 0주·미체결 없음 → 실전(LIVE)으로 바꿔요. 실전이면 하이브리드 매매는 멈추고 암살자가 단독으로 SOXL 을 운용해요 (보유 SGOV 는 자동으로 팔지 않아요 — 직접 매도)"}
        return {"to": MODE_ARMED, "demote_after_exit": False, "msg": "SOXL 보유 중이라 0주로 졸업하면 실전으로 바뀌도록 예약해요 (그때까지 모의)"}
    if cur == MODE_ARMED:
        return {"to": MODE_SIM, "demote_after_exit": False, "msg": "실전 예약을 취소하고 모의로 돌아가요"}
    if cur == MODE_LIVE:
        if int(held_qty or 0) > 0:
            return {"to": MODE_LIVE, "demote_after_exit": True, "msg": "실전 포지션이 있어 당일 청산 뒤 자동으로 모의로 돌아가도록 예약해요"}
        return {"to": MODE_SIM, "demote_after_exit": False, "msg": "포지션이 없어 바로 모의로 돌아가요"}
    return {"to": None, "demote_after_exit": False, "msg": "이미 모의예요"}


# ---- Q9: 30초 틱 → 1분 종가 봉 (VWAP 안 만듦, 시가·고가·저가도 종가와 같게)
def bars_add(state_dir, symbol, price, now=None, keep=400):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    key = now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:00+00:00")
    p = os.path.join(state_dir, "data", "assassin", f"bars_{symbol}.json")
    bars = _rw(p, []) or []
    if bars and bars[-1]["timestamp"] == key:
        bars[-1]["closePrice"] = round(float(price), 4)
    else:
        bars.append({"timestamp": key, "closePrice": round(float(price), 4)})
    bars = bars[-keep:]
    _rw(p, data=bars)
    return bars


def bars_candles(bars):
    """원작 지표 함수가 읽는 모양(open=high=low=close, 거래량 0)"""
    return [{"timestamp": b["timestamp"], "openPrice": b["closePrice"], "highPrice": b["closePrice"], "lowPrice": b["closePrice"],
             "closePrice": b["closePrice"], "volume": 0.0, "currency": "USD"} for b in bars]


def assassin_sim_metrics(state_dir, soxl_bars, qqq_bars, soxl_px, qqq_px, now_est=None):
    """암살자 모의 지표 = 원작 quant_indicators_plugin 의 1분 지표 함수 그대로. 결과는 assassin_sim.json 에 기록 (모의, 주문 없음)"""
    sm = QI.compute_soxl_quant_metrics_1m(bars_candles(soxl_bars), live_price=float(soxl_px), now_est=now_est)
    qm = QI.compute_qqq_macro_metrics_1m(bars_candles(qqq_bars), live_price=float(qqq_px), now_est=now_est)
    keep = {k: sm.get(k) for k in ("vel_1m_pct", "vel_3m_pct", "vel_5m_pct", "rsi_14", "live_price")}
    keep.update({k: qm.get(k) for k in ("qqq_vel_1m_pct", "qqq_vel_3m_pct", "qqq_vel_5m_pct")})
    _rw(os.path.join(state_dir, "data", "assassin", "assassin_metrics.json"),
        data={"execution_mode": assassin_mode(state_dir), "bars_soxl": len(soxl_bars), "bars_qqq": len(qqq_bars), "metrics": keep,
              "at": datetime.datetime.now().isoformat()})
    return keep
