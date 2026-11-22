# ==========================================================
# FILE: meritz_laoer/sniper_adapter.py   (MERITZ_LAOER v2.9.0 — 판 29, 구조 1차)
# 원작 스나이퍼 순수 판정 함수(orig_sniper/ 안 원작 복사본, 한 줄도 안 고침)를 하이브리드 상태(층·F)에 맞춰 부르는 얇은 어댑터.
# 규칙: ① 원작 로직은 orig_sniper/ 에만 있다 (여기서 다시 쓰지 않음) ② 이 파일은 데이터 모양 바꾸기(층 → StratumBucket)와 호출뿐
#       ③ 원작 코드가 메리츠 코드를 부르지 않는다 (test_hybrid_v290.py 가 검사) ④ 브로커 호출·텔레그램 문구·계좌 경로는 여기에도 안 둠
# 지금 상태: 아직 sniper_mode.py·main.py 에 연결하지 않음 (판 29 1차 — 연결 범위는 Muse 결정 대기, 질문란 참고). 하이브리드 매매 동작은 v2.7.0 과 같다.
# 용어: 층 = 스나이퍼 매매 단위(8%, 예전 박스) · F = 탑쌓기 매매 단위(예전 floor, 시드 $15,000)
# ==========================================================
import json
import os
import sys

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig_sniper")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import quant_engine as QE            # noqa: E402  원작 복사본 (orig_sniper/)
import quant_engine_core as QC       # noqa: E402
import toss_api_core as TC           # noqa: E402

MODE_DEFAULT = TC.PORTION_MODE_SIMPLE        # 하이브리드는 단리 고정 (모드 전환 UI 는 다음 판)


def origin():
    """원작 복사본 출처(저장소·커밋·파일 해시) — orig_sniper/ORIGIN.json"""
    with open(os.path.join(_DIR, "ORIGIN.json"), encoding="utf-8") as fh:
        return json.load(fh)


def smart_pullback_pct(mode=MODE_DEFAULT):
    """Case 111 모드별 눌림 % (바벨 -1.0 · 단리 -1.5 · 복리 -2.0) — 원작 resolve_smart_pullback_drop_pct 그대로"""
    return TC.resolve_smart_pullback_drop_pct(mode)


def wide_runway_drop(held_layers, ratchet_layers=0):
    """와이드 활주로 눌림 % (층 수 1~4 -1.0 · 5~8 -2.0 · 9~10 -3.5 · 그 위 -5.5, 사이클 최고 층수 잠금). 층 수 = 회차 수 (Muse 결정 2026-11-22: 원작 회차 = 하이브리드 층)"""
    return QC.get_golden8_prog_thresholds(held_lots=max(1, int(held_layers)), threshold_mode="WIDE_RUNWAY", cycle_ratchet_max_lots=max(0, int(ratchet_layers)))[0]


def layers_to_buckets(layers):
    """층 목록 [{"qty", "cost"}, ...] → 원작 StratumBucket 목록 (평단 오름차순 = 원작 순서, [0] = 가장 싼 층 = 1층). 수량 0 이하는 뺌"""
    out = []
    for r in sorted((x for x in layers or [] if int(TC.safe_float(x.get("qty"))) > 0), key=lambda x: TC.safe_float(x.get("cost")) / max(1, int(TC.safe_float(x.get("qty"))))):
        q, c = int(TC.safe_float(r.get("qty"))), round(TC.safe_float(r.get("cost")), 4)
        out.append(QC.StratumBucket(qty=q, book_price=round(c / q, 4), book_invested_usd=c, actual_cost_usd=c, lot_count=1, lot_type="QUOTA_L1"))
    return out


def layers_of(st):
    """하이브리드 상태(tower_strategy 장부)에서 스나이퍼 층 목록 — 완성·잠긴 F 는 탑쌓기 몫이라 뺌, 미완성 F 의 층(boxes_view)만. [{"qty","cost","floor_id","layer_id"}]"""
    import tower_strategy as TW
    rows = []
    for f in TW.top_down(st if isinstance(st, dict) else {}):
        if int(TW._f(f.get("qty"))) <= 0 or TW.is_tower(f):
            continue
        for b in TW.boxes_view(f):
            rows.append({"qty": b["qty"], "cost": b["cost"], "floor_id": int(TW._f(f.get("id"))), "layer_id": int(b["id"])})
    return rows


def reentry_signal(price, anchor, lowest_layer_price, rsi=None, late_cutoff=False, mode=MODE_DEFAULT, hm=None, pullback_drop_pct=None):
    """원작 evaluate_l2_only_hybrid_reentry_signal 호출 (눌림 % 는 Case 111 모드값, 돌파 +1% · RSI 50 · 15:30 차단 · 상한 가드 = 가장 낮은 층 평단).
    분봉 HA·세션 VWAP·기억 저가 입력은 메리츠 API 에 분봉이 없어 None (원작도 None 이면 그 필터를 건너뜀). RSI None = 모름 → 돌파 안 막음 (원작 규칙, Muse 결정). RSI None → 50 으로 봐서 돌파 안 막음, pullback_drop_pct 를 주면 모드값 대신 그 눌림 % 를 씀 (판 30)"""
    return QC.evaluate_l2_only_hybrid_reentry_signal(
        live_price=price, anchor_price=anchor, l2_book_price=lowest_layer_price, min_upper_tier_price=lowest_layer_price,
        is_late_new_cycle_cutoff=bool(late_cutoff), is_late_cutoff=bool(late_cutoff), rsi_14=rsi, hm=hm, portion_mode=mode, pullback_drop_pct=pullback_drop_pct)


def sell_targets(layers, price, rise_l1_pct=1.50, rise_upper_pct=1.00):
    """원작 evaluate_multi_grid_sell_targets (1층 +1.5% · 상단 +1.0% · 3~7층 통합이평 졸업) 를 층 목록에 적용 → 원작 결과 dict 그대로"""
    return QE.evaluate_multi_grid_sell_targets(layers_to_buckets(layers), price, rise_l1_pct=rise_l1_pct, rise_upper_pct=rise_upper_pct)
