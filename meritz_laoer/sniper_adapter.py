# ==========================================================
# FILE: meritz_laoer/sniper_adapter.py   (MERITZ_LAOER v2.12.0 — 판 39)
# v2.12.0 수정 1차 (2026-11-24, 판 39 수정 1차): 1분봉 실제 필드(korea_date·korea_hour·oprc·hprc·lprc·prpr) 대응 — candle_min_key(tz='KST') 한국시간→미국 동부 변환 · 오래된 완결봉 가드 FIRST_BUY_MAX_BAR_AGE_MIN
# v2.12.0 (2026-11-24, 판 39): first_buy_ha 추가 — 메리츠 1분봉(meritz_api.minute_candles)을 원작 _compute_vectorized_heikin_ashi_and_rsi 에 그대로 넣어 '직전 완결봉이 무머리 HA음봉인가'를 돌려줌 (첫 매수 분기 A 용). MODE_DEFAULT 는 단리 그대로(눌림 신호·매도 판정용) — 모드별 매수 비율은 tower_strategy.portion_mode
# v2.11.0 (2026-11-24, 판 38): buy_window_open·sell_window_open 추가 (원작 quant_indicators_plugin.is_active_buy_window·is_active_sell_window 를 그대로 부름). orig_sniper/ 의 sniper_exit_plugin·barbell_plugin 은 원작 23a16d5 로 교체 (Audit-113)
# v2.10.0 (2026-11-23, 판 36 Case 113 이식, D1·D3·D8): ① stalker_fire·rebound_policy 삭제 (스토커 영구 폐기, 호출처 없었음) ② reentry_signal 에 hm(ET 시각 HHMM) 전달 — 원작 신호 함수의 개장 7분 쉴드용 ③ sell_targets·sell_plan 기본 1층 익절 rise_l1_pct 1.50 → 1.00 (원작 Case 113 1층 기준 +1.00%)
# 판 31: 매도 연결, 방식 B
# 판 32 질문 1·2 (2026-11-22, 2차·부분): 래칫·하드캡·RSI 수확 — 원작 sniper_exit_plugin.py(SniperL1TrailSlot · _step_l1_trail_slot_candidate)를 orig_sniper/ 에 그대로 복사해 어댑터가 그 클래스·함수를 부름 (l1_trail_slot · l1_trail_step · minute_key). 거래 코드에는 아직 연결 안 함
# 판 32 (2026-11-22, 1차·부분): 단리 모드 Case 112 정책(S-112)·리바운드 스토커 판정 래퍼 추가 — 거래 코드에는 아직 연결 안 함 (래칫·하드캡 실행부는 원작 sniper_exit_plugin.py 안이라 복사본에 없음 → 질문란 참조)
# 판 31 (2026-11-22): sell_plan 추가 — 원작 evaluate_multi_grid_sell_targets 에 전체 층을 자르지 않고 그대로 넘김(방식 B, Muse 결정). 원작 코드는 안 고침.
# 원작 스나이퍼 순수 판정 함수(orig_sniper/ 안 원작 복사본, 한 줄도 안 고침)를 하이브리드 상태(F)에 맞춰 부르는 얇은 어댑터.
# 규칙: ① 원작 로직은 orig_sniper/ 에만 있다 (여기서 다시 쓰지 않음) ② 이 파일은 데이터 모양 바꾸기(F → StratumBucket)와 호출뿐
#       ③ 원작 코드가 메리츠 코드를 부르지 않는다 (test_hybrid_v290.py 가 검사) ④ 브로커 호출·텔레그램 문구·계좌 경로는 여기에도 안 둠
# 지금 상태: sniper_mode.py·main.py 에 연결됨 (신호 판정 판 30 · 매도 연결 판 31 · 래칫·스토커 판 32). 하이브리드 매매 동작은 이 어댑터를 거쳐 원작 판정을 부름.
# 용어(판 35): 버킷 = 매수 1건 (원작 StratumBucket, 시드의 8%) · 층 = 그리드 단계 (원작 tier) · F = 탑쌓기 위치 (하이브리드 전용, F 완성 기준 금액 $15,000). 버킷과 층은 다른 개념 — 한 층에 버킷이 여러 개 있을 수 있음.
# ==========================================================
import json
import os
import sys

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig_sniper")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import grid_tiers as GT             # noqa: E402  판 37 후속: 층 태그·7층 상한·합병 (원작 이식, orig 대조 시험 있음)
import quant_engine as QE            # noqa: E402  원작 복사본 (orig_sniper/)
import quant_engine_core as QC       # noqa: E402
import quant_indicators_plugin as QI  # noqa: E402  판 38: 원작 매수·매도 시간창 (is_active_buy_window · is_active_sell_window)
import toss_api_core as TC           # noqa: E402

MODE_DEFAULT = TC.PORTION_MODE_SIMPLE        # 하이브리드는 단리 고정 (모드 전환 UI 는 다음 판)


def _as_et(now_et):
    """시간대가 없는 시각은 미국 동부 시각으로 읽음 (있으면 동부로 바꿈)"""
    return now_et.replace(tzinfo=QI.EST_TZ) if now_et.tzinfo is None else now_et.astimezone(QI.EST_TZ)


def buy_window_open(now_et):
    """판 38 시간 확대: 원작 매수 창 그대로 — 평일 04:07~16:00 ET (is_active_buy_window, 주말·금 20:00 뒤는 닫힘). now_et 는 시간대가 붙은 미국 동부 시각.
    이 함수는 시각만 본다 — 메리츠 장운영 코드(프리장 매수 접수 여부는 미확인)는 main.py 가 따로 확인"""
    dt = _as_et(now_et)
    return bool(QI.is_active_buy_window(dt.hour * 100 + dt.minute, now_est=dt))


def sell_window_open(now_et):
    """판 38 시간 확대: 원작 매도 창 그대로 — 평일 04:00~04:06 ET 7분만 닫고 나머지는 전 구간 열림 (is_active_sell_window, 주말·금 20:00 뒤 닫힘).
    시각만 본다 — 메리츠가 실제로 받는 구간(장운영 코드)은 main.py 가 따로 확인"""
    dt = _as_et(now_et)
    return bool(QI.is_active_sell_window(dt.hour * 100 + dt.minute, now_est=dt))


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
    """F 목록 [{"qty", "cost"}, ...] → 원작 StratumBucket 목록 (평단 오름차순 = 원작 순서, [0] = 가장 싼 층 = 1층). 수량 0 이하는 뺌"""
    out = []
    for r in sorted((x for x in layers or [] if int(TC.safe_float(x.get("qty"))) > 0), key=lambda x: TC.safe_float(x.get("cost")) / max(1, int(TC.safe_float(x.get("qty"))))):
        q, c = int(TC.safe_float(r.get("qty"))), round(TC.safe_float(r.get("cost")), 4)
        out.append(QC.StratumBucket(qty=q, book_price=round(c / q, 4), book_invested_usd=c, actual_cost_usd=c, lot_count=1, lot_type="QUOTA_L1"))
    return out


def tiered(layers):
    """판 37 후속: 층 목록 → (order, buckets, groups). 큐 순서 = 원작 순서 ([0] 이 GRID_L1 이면 1층, 그 뒤 상단층 번호 순, 7층 칸은 합병분이 한 칸).
    모든 층에 태그(lot_type = GRID_L1..GRID_L7)가 있으면 태그대로 (같은 태그 = 합병된 한 버킷 — 수량·원가 합), 하나라도 없으면 예전처럼 평단 오름차순 ([0] = 가장 싼 층 = 1층, 층마다 버킷 1개).
    order = 큐 순서의 입력 번호 목록 · buckets = 원작 StratumBucket 목록 · groups[k] = 버킷 k 에 든 입력 번호들"""
    idx = [i for i, x in enumerate(layers or []) if int(TC.safe_float(x.get("qty"))) > 0]
    gq = GT.group_by_tag([{"key": i, "qty": int(TC.safe_float(layers[i].get("qty"))), "cost": TC.safe_float(layers[i].get("cost")), "lot_type": layers[i].get("lot_type")} for i in idx])
    if gq is not None:
        bk = [QC.StratumBucket(qty=b["qty"], book_price=b["price"], book_invested_usd=b["cost"], actual_cost_usd=b["cost"], lot_count=max(1, len(b["members"])), lot_type=b["tag"]) for b in gq]
        groups = [list(b["members"]) for b in gq]
        return [i for g in groups for i in g], bk, groups
    order = sorted(idx, key=lambda i: TC.safe_float(layers[i].get("cost")) / max(1, int(TC.safe_float(layers[i].get("qty")))))
    return order, layers_to_buckets([layers[i] for i in order]), [[i] for i in order]


def has_l1(layers):
    """큐 맨 앞이 1층(GRID_L1 또는 예전 방식이면 가장 싼 층)이면 True — 1층이 팔려 상단층만 남았으면 False (원작 has_active_l1_bucket)"""
    bk = tiered(layers)[1]
    return bool(bk) and QC.has_active_l1_bucket(bk)


def queue_order(layers):
    """큐 순서의 입력 번호 목록 (tiered 의 order)"""
    return tiered(layers)[0]


def tags_on_buy(existing_layers, new_key, qty, cost):
    """판 37 후속: 새 매수 한 건의 태그 갱신 — existing_layers = [{"key","qty","cost","lot_type"}] → {키: 태그} (원작 vrev_add_quota_lot_and_merge_2tier, 7층 상한·L2_L7 합병)"""
    return GT.tags_on_buy(existing_layers, new_key, qty, cost, GT.MAX_GRID_TIERS_7)


def layers_of(st):
    """하이브리드 상태(tower_strategy 장부)에서 스나이퍼 층 목록 — 완성·잠긴 F 는 탑쌓기 몫이라 뺌, 미완성 F 의 버킷(boxes_view)만. [{"qty","cost","floor_id","layer_id","lot_type"}]"""
    import tower_strategy as TW
    rows = []
    for f in TW.top_down(st if isinstance(st, dict) else {}):
        if int(TW._f(f.get("qty"))) <= 0 or TW.is_tower(f):
            continue
        for b in TW.boxes_view(f):
            rows.append({"qty": b["qty"], "cost": b["cost"], "floor_id": int(TW._f(f.get("id"))), "layer_id": int(b["id"]), "lot_type": b.get("lot_type") or ""})
    return rows


def reentry_signal(price, anchor, lowest_layer_price, rsi=None, late_cutoff=False, mode=MODE_DEFAULT, hm=None, pullback_drop_pct=None):
    """원작 evaluate_l2_only_hybrid_reentry_signal 호출 (Case 113: 눌림만 — 돌파 폐기, 기준가 = min(직전 매도가, 가장 낮은 F 평단), 상한 가드 = 가장 낮은 F 평단, hm 을 주면 09:30~09:36 7분 쉴드. late_cutoff 는 원작이 무시함).
    분봉 HA·세션 VWAP·기억 저가 입력은 메리츠 API 에 분봉이 없어 None (원작도 None 이면 그 필터를 건너뜀). RSI None = 모름 → 50 으로 봐서 돌파 안 막음 (원작 규칙, Muse 결정). pullback_drop_pct 를 주면 모드값 대신 그 눌림 % 를 씀 (판 30: 와이드 활주로 눌림)"""
    return QC.evaluate_l2_only_hybrid_reentry_signal(
        live_price=price, anchor_price=anchor, l2_book_price=lowest_layer_price, min_upper_tier_price=lowest_layer_price,
        is_late_new_cycle_cutoff=bool(late_cutoff), is_late_cutoff=bool(late_cutoff), rsi_14=rsi, hm=hm, portion_mode=mode, pullback_drop_pct=pullback_drop_pct)


def l2_vacant_break_signal(layers, price, cycle_min_buy_price=0.0, ratchet_layers=0, closed_ha_shaved_bear=None):
    """판 37 후속 항목 3: 원작 evaluate_l2_vacant_low_break_signal (LOW_BREAK_L2_VAC_RELOAD) 연결 — 원작 결과 dict 그대로. 원작 Case 113 에서 영구 폐기돼 꺼져 있음(is_eligible_l2_vac=False → eligible=False · should_buy 항상 False) — 풀이님 Q1 결정: 연결은 하되 OFF 그대로, 절대 안 삼"""
    return QC.evaluate_l2_vacant_low_break_signal(
        live_price=price, buckets=tiered(layers)[1], cycle_min_buy_price=cycle_min_buy_price, cycle_ratchet_max_lots=max(0, int(ratchet_layers)), closed_ha_shaved_bear=closed_ha_shaved_bear)


def sell_targets(layers, price, rise_l1_pct=1.00, rise_upper_pct=1.00, exclude_l1=False):
    """원작 evaluate_multi_grid_sell_targets (1층 +1.0% · 상단 +1.0% · 3~7층 통합이평 졸업) 를 층 목록에 적용 → 원작 결과 dict 그대로.
    exclude_l1=True (판 32 질문 4): 원작 exclude_daytime_l1 — 1층 고정 +1.5% 매도와 2층 개별 매도를 끄고(트레일링이 대신함) 졸업만 남김"""
    return QE.evaluate_multi_grid_sell_targets(tiered(layers)[1], price, rise_l1_pct=rise_l1_pct, rise_upper_pct=rise_upper_pct, exclude_daytime_l1=bool(exclude_l1))


def sell_plan(layers, price, rise_l1_pct=1.00, rise_upper_pct=1.00, exclude_l1=False):
    """판 31 방식 B: 전체 층을 자르지 않고 원작 매도 판정에 넘김 → 층마다 {idx(큐 순서 번호), src(입력 목록 번호), role(L1|L2|grad|None), target, reached}.
    판 37 후속: 큐 순서·층 구분은 tiered 가 정함 — 태그가 있으면 태그대로 (1층이 팔려도 다음 층은 상단층으로 남음, 새 1층이 안 생김 · 7층 칸은 합병분 = 한 버킷), 없으면 예전처럼 평단 오름차순 ([0] = 1층).
    reached = 원작 결과 sold_indices (판정은 원작 그대로, 합병 버킷이 닿으면 그 안의 모든 층). target = 표시·주문 가격: L1 = 1층 평단 +rise_l1 · L2 = max(2층 평단 +rise_upper, L1 목표) (L2 가 닿으면 L1 도 같이 팔림 — 원작) · 졸업(grad) = 3~7층 가중평단 +rise_upper (닿으면 전 층 전량).
    반환 (rows, result) — result 는 원작 결과 dict 그대로. 졸업 가능한 층 수(3층 이상 층 있음)일 때만 grad 목표가 있음"""
    order, bk, groups = tiered(layers)
    res = QE.evaluate_multi_grid_sell_targets(bk, price, rise_l1_pct=rise_l1_pct, rise_upper_pct=rise_upper_pct, exclude_daytime_l1=bool(exclude_l1))
    w = QE.compute_upper_2_to_12_moving_avg(bk, rise_upper_pct=rise_upper_pct)
    sold = set(res.get("sold_indices") or [])

    def up(v, pct):
        return round(-(-(v * (1.0 + pct / 100.0) - 1e-9) * 100.0 // 1) / 100.0, 2)

    l1_t = up(bk[0].book_price, rise_l1_pct) if (bk and w.get("has_active_l1")) else 0.0
    l2_idx = (1 if w.get("has_active_l1") else 0) if w.get("has_active_l2") else -1
    l2_t = max(up(bk[l2_idx].book_price, rise_upper_pct), l1_t) if l2_idx >= 0 else 0.0
    grad_t = float(w.get("inv_3_7_wma_target_price") or 0.0) if int(w.get("inv_3_7_tier_count") or 0) > 0 else 0.0
    rows = []
    for k, g in enumerate(groups):
        role = "L1" if (k == 0 and w.get("has_active_l1")) else ("L2" if k == l2_idx else None)
        reached = k in sold
        if grad_t > 0 and res.get("reason_tag") == "SELL_ALL_GRAD":
            tgt = grad_t
        elif role == "L1":
            tgt = l1_t
        elif role == "L2":
            tgt = l2_t
        else:
            tgt = grad_t
        for i in g:
            rows.append({"idx": len(rows), "src": i, "role": role or ("grad" if grad_t > 0 else None), "target": tgt, "reached": reached})
    return rows, res


def minute_key(ts):
    """에포크초 → 원작 분봉 키 글자 'YYYY-MM-DD HH:MM' (UTC 기준 — 키는 서로 크기만 비교하므로 시간대는 상관없음)"""
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(ts), tz=_dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def l1_trail_slot(kind="MAIN"):
    """판 32: 원작 SniperL1TrailSlot 새 슬롯 (1층 트레일링 상태: 점화·스텝 잠금·하드캡·최고점). 원작 클래스 그대로"""
    import sniper_exit_plugin as XP
    return XP.SniperL1TrailSlot(kind)


def l1_trail_sync(slot, qty, book_price, mode=MODE_DEFAULT):
    """판 32: 1층(가장 낮은 층) 수량·평단이 바뀌면 슬롯을 처음부터 다시 맞춤 (원작 sync_fingerprint — 점화 +1.00% · 스텝 (1.35,1.15)~(5.00,4.50) · 하드캡 +6.00% — Case 113 T4 래칫, 전 모드 같음)"""
    slot.sync_fingerprint(int(qty), float(book_price), mode)
    return slot


def l1_trail_step(slot, live_price, now_ts, closed_minute_ts=None, closed_rsi=None):
    """판 32: 원작 _step_l1_trail_slot_candidate 한 번 호출 → (신호 코드, 방금 점화 여부). 코드: TRAIL_CAP_500(하드캡 +6.0%) · TRAIL_CB_STOP(래칫 보존선 이탈) · TRAIL_CLIMAX_EXHAUST(최고 +3.00% 이상 & 완결봉 RSI >= 65 & 고점 -0.50% 이탈) · '' (없음).
    입력은 메리츠에 분봉이 없어 봇이 모은 1분 종가로 만든 값: closed_minute_ts = 직전 완결 분의 시각(없으면 None → 완결봉 없음), closed_rsi = 그 완결 분까지의 RSI(14) (모르면 None → 원작 기본 50 = 수확 안 함).
    완결봉 HA 음봉 청산(TRAIL_CLOSED_HA_RED)은 이 판 범위 밖이라 '양봉 확정'으로 넘겨 꺼 둠 (지시: 래칫·하드캡·RSI 65 수확만). 세션 VWAP·QQQ 속도는 없음(0)"""
    import sniper_exit_plugin as XP
    cmk = minute_key(closed_minute_ts) if closed_minute_ts else ""
    return XP._step_l1_trail_slot_candidate(
        slot, float(live_price), 0.0, minute_key(now_ts), cmk, bool(cmk), True, 0.0,
        closed_ha_shaved_bull=True, cur_bar_min_key="", session_vwap=0.0,
        closed_rsi_14=(50.0 if closed_rsi is None else float(closed_rsi)))


# ---- v2.12.0 판 39 할 일 1·6: 첫 매수(분기 A) 무머리 HA음봉 판정 — 원작 계산기를 그대로 부름
_TIME_FMTS_DASH = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")      # 메리츠 1분봉 시각 형식은 미확인 → 흔한 형식만 시도, 못 읽으면 '준비 안 됨'(매수 보류)
_TIME_FMTS_DIGITS = {14: "%Y%m%d%H%M%S", 12: "%Y%m%d%H%M", 6: "%H%M%S", 4: "%H%M"}      # 숫자만 있는 글자는 자릿수로 형식을 정함 ("1030" 이 10:03:0 으로 읽히는 모호함 방지)


FIRST_BUY_MAX_BAR_AGE_MIN = 5      # 판 39 수정 1차: 직전 완결봉이 지금 분보다 이 분 넘게 오래됐으면 낡은 데이터로 보고 첫 매수 보류 (코드로 정한 값 — 근거 측정값 없음, VERIFY.md 참고)


def candle_min_key(t, now_et, tz=None):
    """1분봉 시각 글자 → 미국 동부 'YYYY-MM-DD HH:MM' (원작 min_key 형식). 못 읽으면 ''.
    tz='KST' (메리츠 1분봉 실제 응답: korea_date+korea_hour 는 한국시간) 이면 한국시간으로 읽어 미국 동부로 바꿈 — 서머타임(EST 14시간·EDT 13시간 차)은 시간대 데이터가 처리.
      14자리 YYYYMMDDHHMMSS 또는 6자리 HHMMSS (날짜 없으면 now_et 를 한국시간으로 바꾼 날짜).
    tz 가 None 이면 예전처럼 '이미 동부 시각'으로 읽음 (날짜 없는 시각은 now_et 의 날짜)"""
    import datetime as _dt
    s = str(t or "").strip()
    if tz == "KST":
        from zoneinfo import ZoneInfo as _Z
        kst = _Z("Asia/Seoul")
        try:
            if s.isdigit() and len(s) == 14:
                d = _dt.datetime.strptime(s, "%Y%m%d%H%M%S")
            elif s.isdigit() and len(s) == 6:
                base = _as_et(now_et).astimezone(kst)
                d = _dt.datetime.strptime(s, "%H%M%S").replace(year=base.year, month=base.month, day=base.day)
            else:
                return ""
        except ValueError:
            return ""
        return d.replace(tzinfo=kst).astimezone(QI.EST_TZ).strftime("%Y-%m-%d %H:%M")
    fmts = (_TIME_FMTS_DIGITS.get(len(s)),) if s.isdigit() else _TIME_FMTS_DASH
    for f in fmts:
        if not f:
            continue
        try:
            d = _dt.datetime.strptime(s, f)
        except ValueError:
            continue
        if "%Y" not in f:
            d = d.replace(year=now_et.year, month=now_et.month, day=now_et.day)
        return d.strftime("%Y-%m-%d %H:%M")
    return ""


def first_buy_ha(candles, now_et):
    """분기 A 4번 검문 재료: 직전 완결 1분봉의 HA 상태 → {"ready": bool, "shaved_bear": bool, "closed_mk": str}.
    candles = meritz_api.minute_candles() 결과 (오래된 것 → 최신). 계산은 원작 _compute_vectorized_heikin_ashi_and_rsi 를 그대로 부름 (closed_ha_ready = 완결봉 순번 14 이상).
    체결 없는 분은 봉이 빠져 있으므로 빈 분을 채우지 않음 (간격 2분 이상 가능). 못 읽거나 비어 있으면 ready False → 호출한 쪽이 매수 보류 (원작 `(not ready) or shaved_bear` 와 같음)"""
    import numpy as _np
    import datetime as _dt
    dt = _as_et(now_et)
    bad = {"ready": False, "shaved_bear": False, "closed_mk": ""}
    rows = [c for c in (candles or []) if isinstance(c, dict)]
    keys = [candle_min_key(c.get("t"), dt, c.get("tz")) for c in rows]
    if not rows or not all(keys):
        return bad
    order = sorted(range(len(rows)), key=lambda i: keys[i])
    uniq, seen = [], set()
    for i in order:
        if keys[i] in seen:
            continue
        seen.add(keys[i])
        uniq.append(i)
    arr = lambda k: _np.array([float(rows[i][k]) for i in uniq], dtype=float)
    m = QI._compute_vectorized_heikin_ashi_and_rsi(arr("o"), arr("h"), arr("l"), arr("c"), [keys[i] for i in uniq], dt.strftime("%Y-%m-%d %H:%M"))
    closed_mk = str(m.get("closed_bar_minute_key") or "")
    ready = bool(m.get("closed_ha_ready"))
    # 판 39 수정 1차: 오래된 1분봉 가드 — API 가 낡은 데이터를 돌려주면 낡은 HA 로 사지 않게 보류 (나이가 음수 = 시계·시간대 어긋남이라 이것도 보류)
    try:
        age = (_dt.datetime.strptime(dt.strftime("%Y-%m-%d %H:%M"), "%Y-%m-%d %H:%M") - _dt.datetime.strptime(closed_mk, "%Y-%m-%d %H:%M")).total_seconds() / 60.0
    except ValueError:
        age = None
    if ready and (age is None or age < 0 or age > FIRST_BUY_MAX_BAR_AGE_MIN):
        return {"ready": False, "shaved_bear": False, "closed_mk": "", "stale": True, "age_min": age}
    return {"ready": ready, "shaved_bear": bool(m.get("closed_ha_shaved_bear")), "closed_mk": closed_mk, "age_min": age}


def zero_share_cutoff(now_et):
    """분기 A 1번 검문: 원작 is_late_regular_new_cycle_cutoff_window 를 그대로 부름 (15:00~16:00 hm 포함, 주말 제외)"""
    dt = _as_et(now_et)
    return bool(QI.is_late_regular_new_cycle_cutoff_window(dt.hour * 100 + dt.minute, now_est=dt))


def zero_share_open_shield(now_et):
    """분기 A 3번 검문: 정규장 개장 7분 쉴드 09:30~09:36 (원작 REG_OPEN_VWAP_SHIELD_START_HM·END_HM 를 그대로 읽음)"""
    dt = _as_et(now_et)
    return bool(QC.REG_OPEN_VWAP_SHIELD_START_HM <= dt.hour * 100 + dt.minute <= QC.REG_OPEN_VWAP_SHIELD_END_HM)
