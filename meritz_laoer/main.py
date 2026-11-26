#!/usr/bin/env python3
# ==========================================================
# FILE: meritz_laoer/main.py   (MERITZ_LAOER v2.7.0 · 판 46 v2.19.0)
# v2.19.0 (2026-11-26, 판 46 — BOT_VERSION 은 v2.7.0 그대로): ① 마감 일일결산에 당일 실현수익(봇 장부 기준·수수료·세금 미반영)·당일 매수/익절 횟수·누적실현 추가 — 체결을 장부에 반영할 때마다 data/realized_daily.json 에 주문별로 쌓음(장중 반영분 포함, exec_id 로 중복 방지) ② 결산 줄마다 이모티콘. 발송 시점·횟수·매매 로직 변경 없음
# v2.12.0 수정 1차 (2026-11-24, 판 39 수정 1차): ① 모의 매도 컷오프 16:10 → 20:00 (run_sniper_dry) ② ANCHOR_KO 의 죽은 라벨 "first" 삭제 (1분봉 필드명 수정은 meritz_api.py·어댑터 파일)
# v2.12.0 (2026-11-24, 판 39 — BOT_VERSION 은 v2.7.0 그대로): ① first_buy_ha 추가 — 보유 층 0개일 때만 메리츠 1분봉(api.minute_candles)을 읽어 plan_buy(ha=) 로 전달 (실거래·모의 둘 다) ② 동기화 시각 기본 16:10 → 20:00 ET (_hm 대체값 3곳) ③ run_late_fills 안내 글자 '동기화 시각 이후'
# v2.11.0 (2026-11-24, 판 38 시간 확대 — BOT_VERSION 은 이번에도 그대로): 스나이퍼 시간을 원작 시간으로 — 매수 04:07~16:00 ET(프리장·정규장, SN.buy_ok) · 매도는 평일 04:00~04:06 ET 7분만 빼고 전 구간(SN.sell_ok) 인데 장운영 코드 003·004·005 일 때만 주문 (그 밖 코드 = 야간 등은 메리츠 접수 여부 미확인이라 안 냄). 틱이 00:00 ET 부터 돌고(바벨 틱은 예전 09:30 ET~ 그대로), 16:10 ET 체결 반영 뒤에는 그날 기록이 닫혀 예전처럼 주문 안 함 (16:10~20:00 장후·야간 매도는 미적용 — 노션 질문).
# v2.10.0 (2026-11-23, 판 36 Case 113): 매수 신호 한 줄에서 돌파 표시 삭제 (BOT_VERSION 은 이번 판 범위 밖이라 그대로)
# v2.9.0 6차 (2026-11-22, 판 33): ① tower_buy_tick 신설 — 매매 모드가 tower 일 때 run_sniper_tick(실거래)·run_sniper_dry(모의)가 스나이퍼 신호 대신 하루 한 번 탑쌓기 매수(시초가 가까운 칸부터 아래로, 칸마다 같은 금액) ② run_sync 가 잔고 대조(TW.reconcile) 뒤 F 완성 기준 금액 조정(seed_adjust.adjust)을 부름. 모드 기본은 sniper(하이브리드 그대로). 매도·래칫·스토커·16:10 동기화 시각은 안 바꿈
# v2.9.0 판 32 질문 4·5 (2026-11-22): 시세를 읽을 때마다 SN.trail_tick (실거래·모의 둘 다) — 1층 트레일링 슬롯은 메모리에만
# v2.9.0 판 31 질문 3 (2026-11-22): 스나이퍼 매도 주문 전에 매도가능 수량을 2초(0.25초 간격) 기다리고(SN.wait_sellable), plan_sells 에 장외 여부(ext) 전달 — 원작 execute_bulletproof_sell_sweep 방식 부분 주문
# v2.7.0 (2026-11-21, 판 27 층 간격 설정·버튼 제거): 계획 미리보기 '새 층 가격' 줄(간격 기준) 삭제 · 탑쌓기 계획 머리 '간격' 표시 삭제. 간격은 내부 고정값 GAP_USD=5로만 씀.
# v2.6.0 (2026-11-21, 판 26 버킷별 매도·매수 비율 설정): 버킷별 매도 주문의 중복 방지를 버킷 단위로(sold_box_keys_today·busy_boxes·거절 기록 키 '층:버킷') · 매도 체결 알림 글자(버킷만 줄임) · 계획 미리보기에 버킷별 목표 줄. 층 단위 주문(탑 매도)은 예전 그대로.
# v2.5.0 (2026-11-21, 판 25 하이브리드 버킷·층 — 토스 스나이퍼 이식): ① 매수 = 신호 1번에 버킷 시드의 8%(sniper_mode.plan_buy) · 서브 그리드 4%(sub_grid.py) ② 버킷 안 매도(+1.5%/+1.0%, 버킷 전체) 자동으로 복귀 — 판 24 선택 질문(pick_scan) 호출 삭제(코드는 남김)
#   ③ 하루 매수 층 수 제한(buy_layer_limit_hit)은 스나이퍼 매수에 안 씀 ④ 서브 상태 동기화(sync_sub)·10분 게이트(mark_sub_gate) ⑤ 지하층 → 공사중. 계좌·API·16:10 동기화·장부=잔고 정지·주문 시간은 안 바꿈
# v2.4.0 (2026-11-21, 판 24): ① 장부 바로잡기(run_ledger_migration, 일회성: 메리츠 실제 잔고 684주일 때만 → 장부 684주 · 두 층 373주 $40.29 / 311주 $48.14 · 잠금 · 공사중(빈 층), 주문·실제 잔고 안 건드림, 마커 파일로 한 번만, 이전 날 늦은 체결은 건너뜀)
#   ② 스나이퍼 목표가에 닿으면 자동 매도 대신 텔레그램 버튼(스나이퍼/탑쌓기) 선택 (run_sniper_tick·apply_pick) ③ 잠긴 층은 탑 매도만 ④ 지하층부터 스나이퍼 매수. 업데이트 알림 판 번호는 bot_office/bot_updater.py
# v2.3.0 수정1 (2026-11-21, 판 23 수정1 — 버전 그대로): 하루 매수 층 수 제한(buy_layer_limit_hit, 기존 설정 tower_max_buy_layers_per_day) · B3 미체결 조회 · B7 모의 스나이퍼(run_sniper_dry) · S3 사이클 최고 층수 잠금 · S1 16:10 뒤 체결 다음 날 반영(run_late_fills) · '목표 도달' 라벨 · 죽은 코드 defer_sell·limit_morning_sells 제거
# v2.3.0 (2026-11-21, 판 23 하이브리드 — 스나이퍼 매수 + 탑 매도): 모드 선택(trading_mode) 삭제, 항상 하이브리드. 사기=스나이퍼(눌림·돌파)만, F 완성 기준 금액(기본 $15,000)에 닿은 층은 '완성'이라 탑 매도(층 평단 +10% → 50%), 미완성 층(재매수 대기 포함)은 스나이퍼 매도(1층 +1.5%·상단 +1.0%·층 전량).
#   총 시드·층 수 한도 없음(total_krw 선택). 새 버킷·층은 스나이퍼 신호가 뜰 때 만듦 (v2.7.0 판 27: 층 간격 규칙 삭제 — 간격은 내부 고정값 GAP_USD=5로 칸 만들기에만 씀). 탑 매도 체결도 스나이퍼 기준가(직전 익절) 갱신. 같은 날 한 층에 매도 주문이 이미 있었으면(탑 매도 일부 체결 뒤 남은 몫 포함) 그 층은 그날 다시 안 팖.
#   환전: 아침 = F 완성 기준 금액 × tower_max_buy_layers_per_day (휴장 전날은 × 회차), 장중 매수 신호 때 달러 부족하면 자동환전(실시간 환전 시간만), 마감 60분 전 달러부족 알림 유지. --check 환전 표시 고침(부족 달러 shortfall_usd). 계좌·종목·API·스나이퍼 신호 숫자·매도 %·16:10 동기화·장부=잔고 정지·중복 체결 방지·주문 시간은 안 바꿈.
# v2.2.20 (2026-11-21, 판 22 메리츠 3번 계좌 SOXL 듀얼 모드 — 스나이퍼 + 탑쌓기): 설정 trading_mode(tower 기본 | sniper). 탑쌓기는 v2.2.18 그대로 (run_order_day·run_intraday_sell·run_sync·16:10 동기화·장부=잔고 정지 규칙 안 바꿈).
#   스나이퍼(새 파일 sniper_mode.py): loop 가 run_sniper_tick(30초 간격, 정규장 09:30~16:00 ET 매수 · 정규장+장후 16:10 까지 매도) 를 부름. 하루 기록 파일(orders_<날짜>.json)을 탑쌓기와 같이 씀 — 스나이퍼 매도·스나이퍼 매수 체결은 확인 즉시 장부·층에 반영, 탑쌓기 매수는 그대로 run_sync 가 반영.
#   build_plan·plan_head·next_trade_lines·strategy_ko·cmd_check 는 모드를 따라감. 모드를 바꾸면 다음 판단부터 적용(이미 낸 주문은 안 건드림). 같은 날 스나이퍼 → 탑쌓기로 바꾸면 run_order_day 가 스나이퍼 기록에 이어 탑쌓기 주문을 냄(sniper_day·tower_ordered 표시).
#   스나이퍼 모드에서는 자동환전·달러부족 알림을 안 함(탑쌓기 회차 기준 계산이라). 층 상태·장부·계좌·종목·API 는 그대로
# v2.2.18 (2026-11-20, 판 21 거래 내역·봇 상태 버튼 오류 고침): BOT_VERSION 만 올림 (고침은 tg_menu.py — _local 4개 반환에 ledger_text·power_text 가 5개로 풀던 것을 4개로 고침). 매매 로직 변경 없음
# v2.2.17 (2026-11-20, 판 20 하루 매수·매도 층 수 설정): ① 설정 tower_max_buy_layers_per_day · tower_max_sell_layers_per_day (1~3, 없으면 1 = 예전 동작). 매수 계획은 tower_strategy.make_plan 이 하루 최대 N_buy 층 (층마다 floor_id) — 여기서는 표시(plan_head·next_trade_lines)가 오늘 사는 층을 전부 보여줌
#   ② run_intraday_sell: 같은 확인에서 여러 층이 목표에 닿으면 번호가 큰 층부터 '오늘 남은 매도 횟수'(N_sell − 오늘 이미 판 층 수)까지 팔고 나머지는 알림만(pick_sells). v2.2.12 '첫 매도 뒤 2차는 알림만' 은 이 횟수 규칙으로 바뀜 (N_sell=1 이면 예전과 같음).
#   예전 하루 1건 표시 m["sell_attempt"] 는 층 번호가 있으면 그 층, 없으면 층을 모르는 1건으로 셈. ③ 자동환전 아침 계산(_next_rounds_inputs)은 build_plan 이 돌려준 오늘 매수 주문 전부(최대 N_buy 층)로 필요 달러를 계산 — rounds(휴장 전날 extra)는 계획에 안 들어가 층 수와 곱해지지 않음(코드 확인, 변경 없음). 1주 층 제외·재매수 보류·매도 비중·목표 이익률·장운영 규칙은 그대로
#   ④ (판 20 수정1) 아침 계획 매도에도 N_sell 적용: build_plan 이 defer_sell 뒤에 limit_morning_sells 를 불러, 닿은 매도 주문을 번호 큰 층부터 최대 N_sell 개만 남기고 나머지는 주문에서 빼 plan["info"]["held_back"] 로 남김(pick_sells 재사용). run_order_day 아침 알림에 '알림만 · 주문은 안 냈어요' 로 적음. defer_sell 규칙(매수 주문이 있는 날은 아침 매도 전부 장중으로)은 그대로
# v2.2.15 (2026-11-20, 판 19 오늘 계획 미리보기에 탑 진행률): 표시만 바뀜 (매매 로직·주문·장부 변경 없음). plan_head 한 곳만 고침 → 텔레그램 미리보기(tg_menu)·CLI 미리보기(--check)·주문 알림에 같이 반영
#   ① 맨 앞에 '탑: ...' 줄 — 상황판과 같은 표현 (tower_strategy.view_lines 첫 줄 재사용: 층 마커 + 채움 비율 합계/최대층) ② '지금 채우는 층 N층' 뒤에 '· 미완성 (74%)' (tower_strategy.floor_status·fill_ratio 재사용, 비율을 새로 계산하지 않음). 새 층이면 '(새 층)' 그대로
#   ③ 표시 계산이 실패해도 주문·알림이 막히지 않게 탑 줄만 건너뜀 (try/except)
# v2.2.14 (2026-11-20, 판 17 시초가 상한): ① 시초가 = 정규장(장운영 004) 09:30 ET 이후 처음 확인한 SOXL 현재가 (시세 API 의 시초가 필드는 근거 파일에 없어 미확인 → 첫 확인가 방식). 그날 한 번만 정해 data/open_price_<ET날짜>.json 에 저장(모의는 dry_ 접두), 재시작해도 저장값을 씀. 새 함수 load_open_price·ensure_open_price·run_open_capture, loop 가 주문 시각 전에도 09:30 부터 확인
#   ② build_plan(open_px=) → tower_strategy.make_plan 이 오늘 채우는 층의 안 산 칸에 상한 적용. 주문 시간(run_order_day)은 저장값(없으면 그때 확인한 현재가)을 씀 ③ plan_head 에 시초가·첫 칸 한 줄. 상황판·--check 은 저장값만 읽음(없으면 계획 그대로 — 시초가를 만들지 않음) ④ 자동환전 아침 계산(_next_rounds_inputs)·체결 알림 '다음 매수'는 시초가 모름 → 계획 그대로. 새 층 생성·매도·간격·금액·층 수 규칙은 그대로
# v2.2.13 (2026-11-20, audit-fix-v2 r4-fix): ① 하루에 한 층만 매도 (풀이님 결정) — 같은 확인에서 여러 층이 목표에 닿으면 번호가 가장 큰 층(맨 위 층)만 팔고 나머지는 알림만 (층마다 하루 한 번, run_intraday_sell). 첫 매도 뒤 새로 닿은 층 알림(2차)은 그대로 ② v2.0.5 주석 문구를 004·005 매도 동작에 맞게 고침 (주석만, 동작 변경 없음)
# v2.2.12 (2026-11-20, audit-fix-v2 r4): ① 표시 문구 '당일 시드' → '한층 금액' (tg_menu.py·README) ② 2차 매도 조건 알림 — 오늘 첫 매도를 낸 뒤 다른 층이 +목표% 에 새로 닿으면 주문 없이 알림만 (층마다 하루 한 번, run_intraday_sell). 같은 확인에서 함께 닿은 층 처리는 v2.2.13 에서 '맨 위 층만 판다' 로 바뀜 ③ 장후 매도(판 15) — 장운영 코드 005 에서도 매도를 냄 (마감 시각 뒤에도 005 면 새 매도 허용). 메리츠가 장후 주문을 받는지는 미확인 — 거절·응답 없음은 메시지로 알리고 그 층은 오늘 다시 안 냄, 장부·층은 체결 반영 때만 바뀜. run_order_day(하루 주문)의 004 검사는 그대로
# v2.2.11 (2026-11-20, 7번 이름 변경): 표시 이름 '속쓸 적립봇' → '7번 메리츠 SOXL 탑쌓기' (HEAD·상황판·알림·CLI·argparse·README·CHANGELOG·업데이터 NAMES·브리핑 라벨). 동작 변경 없음
# v2.2.10 (2026-11-20, staging — 풀이님 결정 11:03): BOT_VERSION 만 (audit-fix-v2 r3 내용 그대로, 버전만 올림 — 사다리 삭제가 들어간 큰 변경이라 헷갈리지 않게 올림). 동작 변경 없음
# v2.2.9 (2026-11-20, audit-fix 7-4·7-5, 3차): ① 7번은 탑쌓기만 씀 — 사다리 삭제 (accum_strategy.py 삭제, strategy 전환·사다리 상태 data/accum_state.json·재매수·1회차 차감(--credit)·사다리 설정 키·메뉴 버튼 제거). strategy 값이 "ladder" 로 남아 있으면 설정 검사가 막음 ② 탑쌓기 1주 층은 자동 매도에서 뺌 + 하루 한 번 '1주 남음' 메시지(run_one_share_notice) — 풀이님 결정 10:03 ③ 새 층을 못 만들면(총 한도·가격 칸 없음) 만들지 않고 하루 한 번 풀이님께 물어봄(run_new_floor_notice) — 자동으로 늘리거나 멈추지 않음(09:59) ④ 휴장일 목록 범위 밖(2030~)·마지막 해 12월에 하루 한 번 알림(run_holiday_range_notice) — 자동환전·알림 꺼짐 안전장치는 그대로 ⑤ 휴장일 목록 2028·2029 추가(HOLIDAY_YEARS). 7-3 은 풀이님 결정(달러 한도·원화 매매법 없음)으로 코드 변경 없음. 층 간격 기본값 $5 그대로(메뉴로 바꿈).
# v2.2.8 (2026-11-20, 하루에 한 층 매수): 탑쌓기는 하루에 안 산 칸 전부 주문 (max_rounds_per_day는 사다리 회차만) — tower_strategy.py make_plan·main.py 다음 매수 표시만 바뀜
# v2.2.7 (2026-11-20, 층 표시 고침): ① 층 수는 채움 비율 합계 (1층 48%면 0.48/10층) ② 미완성 층은 한 칸에 사선 ◧ (2칸 중 1칸이 아니라 한 칸) — tower_strategy.py view_lines·layer_marker만 바뀜
# v2.2.6 (2026-11-20, 판 16 본격): ① 층별 매도(계획은 tower_strategy.make_plan) + 장중 확인이 층마다 1건씩 냄(층당 하루 1건·게이트는 가장 낮은 층 평단) ② 체결 반영: 시간순(체결 시각 필드 미확인이면 매도 먼저)·주문번호별 증분 반영(두 번 반영 방지)·장부와 층을 같은 묶음으로 저장
#   ③ 장중 매도 체결을 확인하는 즉시 장부와 층에 반영 (16:10 동기화 전에도 층 상태가 맞음) ④ 체결 텔레그램 알림: 장중 확인에서도 알림(부분 체결은 이전 알림 이후 늘어난 수량, 주문별 notified_qty 를 주문 기록 파일에 저장, 전송 성공 뒤에만 저장) + 다음 매매 안내
#   ⑤ 토스 입고분(--add-shares)은 탑쌓기면 1층 빈곳에 넣음 ⑥ 장중 확인 기본 간격 30초(config.py). 판 15(장후 매도) 코드는 이 ZIP 에 없음 — 주문 기록 형식(floor_id·floor_avg·notified_qty·sell_attempts)만 맞춰 둠
# v2.2.5 (2026-11-20, 판 16 1층 채우기 매수): BOT_VERSION 만 (1층 채우기 매수 로직은 tower_strategy.py apply_fill — 새 층 계획 매수 체결이 1층 빈칸 가격이면 1층에 넣음). 동작 변경은 tower_strategy.py에만 있음
# v2.2.4 (2026-11-19, 1층 시작가 메뉴): 1층 시작가 설정(tower_floor1_start_usd) 추가 — 정하면 1층 칸이 시작가 기준, 안 정하면 평단 기준(지금 그대로). 동작 변경 없음
# v2.2.3 (2026-11-19, 판 14 색상 고침 + 다음 회차 가격별 배정): 층 칸 색상(tower_strategy.py) + plan_head 에 다음 회차 칸별 배정 표시. 동작 변경 없음
# v2.2.2 (2026-11-19, 판 14): BOT_VERSION 만 (현상태 탑쌓기 층 시각화는 tg_menu.py·tower_strategy.py). 동작 변경 없음
# v2.2.1 (2026-11-19, audit-fix 7-1·7-2): cmd_check 가 적용환율을 읽은 뒤 1회차 크레딧 상한(credit_problems)도 검사. 부분 매수 이월·크레딧 상한은 accum_strategy.py·config.py (tower_strategy 는 건드리지 않음).
# v2.2.0 (2026-11-19, 판 13): 탑쌓기(동적 층 시스템) 전환 지점 추가 — 계산은 새 파일 tower_strategy.py. settings["strategy"] 가 "tower" 일 때만 탑쌓기, 그 외(없음 포함)는 예전 사다리 그대로 (기본 "ladder").
#   바뀐 곳: strategy_of · tower_state_for · build_plan(전략 선택) · plan_head(탑쌓기 문구) · run_intraday_sell(탑쌓기 상태로 매도 판단) · run_order_day(탑쌓기면 사다리 armed 건너뜀, 매일 층 상태를 장부에 맞춤·첫날 1층 만들기) ·
#   run_sync(탑쌓기면 실제 체결 수량·금액으로 층 상태 갱신 → 장부에 맞춤) · cmd_check(전략 표시). 사다리 경로(strategy=ladder)는 동작 변경 없음. 탑쌓기 상태 파일: data/tower_state.json (사다리 상태 data/accum_state.json 은 안 건드림)
# v2.1.0 (2026-11-19, 판 12 + 방 telegram-bot-menu-review 3차 v3 합침): ① 판 12 당일 매도 가격 게이트 고침 (run_intraday_sell) — 게이트가 매수 주문의 '지정가'로 최소 목표가를 계산해서, 지정가보다 낮게 체결된 날 진짜 목표(체결 평단 +목표%)에 닿아도 '목표 아래'로 넘기던 문제 (2026-11-18 사례). 이제 체결 조회(fills)를 시세 게이트보다 먼저 하고, 게이트는 '기존 평단 · 오늘 실제 체결된 매수의 체결 단가' 중 가장 낮은 값으로 계산함 (체결 안 된 매수의 지정가는 안 씀). 게이트 목적(시세가 명백히 낮을 때 불필요한 조회 생략)은 유지. 체결 조회 실패는 알림 없이 로그만 남기고 다음 확인 때 다시 시도 ('체결 조회 실패'). 시험: test_intraday_sell_gate.py 추가. ② 3차 v3 텔레그램 메뉴 문구 정리를 v2.0.9(판 11) 기준 위에 다시 적용 — 이모티콘 제거(예전 이모티콘 키보드 글자도 같은 버튼으로 읽음)·값 설명(넣을 수 있는 값·뜻·바꾸면)·주식 넣기 확인 단계. 판 11 변경(헤더 v2.0.9 문구·cmd_diag_cash 의 estm_frcr_amt 문구)은 그대로 둠, 매매 동작 변경 없음
# v2.0.9 (2026-11-19, 판 11): Q27 원인 고침 — usd_cash()가 estm_frcr_amt를 읽게 함 (meritz_api.py). frcr_amt는 주식 가치를 포함해 앱 값과 달라서 바꿈 (서버 진단 2026-11-19 확인). --diag-cash 문구도 estm_frcr_amt로 고침. 그 외 변경 없음.
# v2.0.8 (2026-11-19, 판 10): ① 자동환전 창 — 판 9 의 '09:00~09:30 고정 30분'을 없애고, 메리츠 실시간 환전 시간 안에서
#   '한국시간 09:00 ~ 주문 시간(order_time_et 를 한국시간으로 바꾼 시각)' 까지로 바꿈. 수수료 무료(스프레드 0%)는 실시간 환전 때만이라 시간외(02:00~08:50)·
#   환전 불가(08:50~09:00, 23:50~00:20)·주말·국내 공휴일엔 환전 안 함 (fx_window_info). 주문 시간 대비용 auto_fx 도 같은 시간 조건을 통과해야 신청.
#   ② 마감 60분 전 부족 알림(run_fx_shortage_alert): 주문 시간 60분 전에 필요 달러 > 달러 예수금이면 '달러부족' 알림 하루 한 번 (자동환전 꺼짐이어도).
#   ③ 휴장 전날 알림·조기 환전(run_closure_alert · closure_ahead): 다음 영업일이 미국증시 또는 한국증시 휴장이면 오늘 알리고, 자동환전이 켜져 있으면
#      오늘 몫 + 휴장 때문에 자기 환전 창이 없는 주문일(최소 1회차)만큼 미리 환전. 휴장일은 코드 안 목록(2026~2027, 근거는 VERIFY.md).
#   ④ 읽기 전용 점검 --diag-cash (달러 예수금 필드 확인용, 주문·환전 없음). Q24(부족분 0이면 기록 안 씀)·Q25(한 회차 = 정수 주 × 사다리 가격)는 판 9 그대로.
# v2.0.7 (2026-11-19, 판 9): 자동환전 시간을 한국시간 오전 9시로 옮김 (수수료 때문). run_fx_morning 추가 — 평일 한국시간 09:00~09:30 사이 하루 한 번,
#   '다음 한 회차분'(사다리·재매수 기존 로직, 가격 기준 전일 종가·그 시점 적용환율) 필요 달러 − 달러 예수금 = 부족분만 환전. 부족 없거나 매수 계획 없으면 안 함.
#   안전장치는 auto_fx 그대로(적용환율 실패·원화 부족이면 안 함·신청 전 fx_<한국시간 날짜>.json 먼저 기록). 환전 뒤 90초 대기 없음.
#   주문 시간(run_order_day)의 기존 auto_fx 호출은 그대로 — 오전 9시 기록(fx_<날짜>.json)이 있으면 건너뜀(= 다시 환전 안 함), 기록이 없을 때만 예전처럼 환전(대비용)
# v2.0.6 (2026-11-19, 판 8): 버전 표기만 올림 — staging 에 빠진 v2.0.4 파일(notifier·tg_menu·accum_strategy)을 v2.0.5 main·meritz_api 와 한 묶음으로 맞춤 (ImportError 해소). 코드 로직 변경 없음
# v2.0.5 (2026-11-19): 정규장 외(장전 003·장후 005) 장중 매도 — 당시엔 '004 아니면 건너뜀'이었음(공식 openapi.json 에 연장 시간 주문·체결 근거가 없어 미확인). 현재는 v2.2.12 판 15 로 004·005 에 매도, 003·그 밖은 장 닫힘으로 건너뜀(005 접수 여부는 여전히 미확인). BOT_VERSION v2.0.5. 체결 내역 심볼 필드 수정은 meritz_api.py
# v2.0.4 (2026-11-19, 판 5 점검 보완 + 판 6): ① 현금 부분 매수(accum_strategy.make_plan) — 계획·--check·텔레그램에 부분 매수 수량 표시
#   ② 주문 응답 유실 자동처리: 주문 전에 '시도' 기록(attempts)을 먼저 저장 → 응답을 못 받으면(시간 초과·연결 끊김·주문번호 없음) 멈추지 않고
#      그 주문을 다시 내지 않은 채 체결 내역(fills_rows)에서 같은 방향·수량·가격 조건의 주문번호를 찾아 이어 붙임(주문 직후 3번, 마감 뒤 체결 반영 때 한 번 더).
#      못 찾으면 '체결 안 된 것'으로 두고 마지막 잔고=장부 확인이 안전망(어긋나면 예전처럼 정지). 서버가 오류 코드로 분명히 거절한 주문은 '안 들어감'으로 처리
#   ③ 텔레그램 chat_id 필수: 비어 있거나 숫자가 아니면 점검(--check·--add-shares·주문 전 확인)에서 막음 — 하루 기록은 안 써서 고치면 같은 날 다시 시도
#   ④ 판 5 보완 포함: 거래소 번호·적용환율 일시 오류는 하루 기록 없이 5분 뒤 재시도, 자동환전 뒤 달러 반영 최대 90초 대기, 장중 매도는 장이 열려 있을 때만
# 7번 메리츠 SOXL 탑쌓기 (SOXL 분할매수·부분매도) — 실행·안전장치
# v2.0.3 (2026-11-18): ① 당일 매도 — 오늘 산 주식이 평단(오늘 체결 반영) +목표% 에 닿으면 그날 바로 매도 비중만큼 매도.
#     장중 intraday_sell_check_sec(기본 120초)마다 run_intraday_sell 이 확인 (실거래·LIMIT 주문일 때만). 매수는 하루 1회차 그대로(장중 재매수 없음),
#     하루 매도 주문은 1건 (이미 오늘 매도 주문이 있으면 안 냄), 연속 매도 금지(sell_block)는 make_plan 규칙 그대로 (오늘 체결된 매수가 있으면 풀림).
#     오늘 매수 주문이 있는 날은 아침 계획에서 매도 주문을 빼고 장중 확인으로 넘김(defer_sell) — 오늘 체결로 평단이 바뀌는데 메리츠 API 에 주문 취소가 없어 낡은 평단의 매도 주문이 남기 때문. (매수 취소는 판 42에서 연결됨, 매도 취소는 아직 안 함)
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
#   python3 main.py --diag-cash        읽기 전용: 외화잔고 USD 행 필드 출력 (달러 예수금이 앱과 다를 때 — v2.0.8)
#   python3 main.py --inject-start     입고 확인 뒤 장부 시작 (settings.start 로 원금·수량 덮어쓰기)
#   python3 main.py --clear-halt       정지 표시 해제 (원인 확인 후)
#   python3 main.py --add-shares --qty N --avg X   직접 산 N주를 평단 $X 로 장부에 더함 (주문 없음)
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
import tower_strategy as TW               # noqa: E402  탑쌓기 (v2.2.9 부터 7번은 탑쌓기만 씀)
import sniper_mode as SN                  # noqa: E402  v2.2.20 스나이퍼 모드 계산부
import seed_adjust as SA                  # noqa: E402  v2.9.0 6차 판 33 F 완성 기준 금액 조정
import barbell_adapter as BB              # noqa: E402  암살자 어댑터 (원작 orig_sniper 호출 — 파일 이름은 옛 바벨 어댑터 그대로. 바벨 기능은 v2.15.0 판 41 에서 삭제)
import free_cash as FC                    # noqa: E402  v2.15.0 판 41 할 일 2: GUARD30 수혈 장부
from tower_strategy import ceil2          # noqa: E402
from config import ConfigManager, load_settings, validate_settings   # noqa: E402
from meritz_api import MeritzApi, MeritzError, WarnNeeded, key_fingerprint, ORDER_TYPES   # noqa: E402  판 42: 미체결 매수 취소 시 주문 유형→oder_cls_code 변환용
from notifier import Notifier, _read_chat, _read_token, token_fp, to_korean   # noqa: E402
import tg_menu                                # noqa: E402  v1.0.3 텔레그램 메뉴 (폴링은 idle() 안에서만)

BOT_VERSION = "v2.7.0"
EST = ZoneInfo("America/New_York")
KST = ZoneInfo("Asia/Seoul")          # v2.0.7: 한국시간은 서머타임이 없음 → 미국 서머타임(EST 19시/EDT 20시)은 시계가 알아서 처리 (고정 시차를 코드에 박지 않음)
OPEN_TIME_ET = datetime.time(9, 30)  # v2.2.14 시초가 = 이 시각 이후 처음 확인한 현재가 (정규장 개장 09:30 ET)
FX_KST_TIME = datetime.time(9, 0)     # 자동환전 시작 시각 (한국시간) = 메리츠 실시간 환전 시작
SHORT_ALERT_MIN = 60                  # v2.0.8 마감(주문 시간) 이 분 전에 '달러부족' 알림
# v2.0.8 메리츠 환전 시간표 (사용자가 보낸 앱 '환전신청 유의사항' 2026-11-19 기준): 실시간 환전 평일 09:00 ~ 다음 날 02:00, 환전 불가 08:50~09:00·23:50~00:20, 시간외(02:00~08:50)는 안 씀
FX_REALTIME = ((datetime.time(9, 0), datetime.time(23, 50)), (datetime.time(0, 20), datetime.time(2, 0)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def now_et():
    return datetime.datetime.now(EST)


def now_kst():
    return datetime.datetime.now(KST)


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


TOWER_FILE = "data/tower_state.json"      # v2.2.0 탑쌓기 층 상태 (state_dir 기준)
REALIZED_FILE = "data/realized_daily.json"  # v2.19.0 판 46 봇 장부 기준 실현수익 기록 (state_dir 기준). 판 46 적용 뒤 체결부터 쌓음 — 그 전 실현은 없음(지어내지 않음)
REALIZED_KEEP_DAYS = 45                    # 이보다 오래된 주문별 기록은 날짜 합계(past)로 접어 파일이 커지지 않게 함


def _realized_blank(d):
    return {"since": str(d), "orders": {}, "past": {"pnl": 0.0, "sells": 0, "wins": 0, "buys": 0, "through": ""}}


def realized_load(cfg, d=None):
    """실현수익 기록 읽기. 파일이 없거나 깨졌으면 d 날짜부터 새로 시작하는 빈 기록 (저장은 안 함)"""
    r = cfg._load_json(REALIZED_FILE, None)
    if isinstance(r, dict) and isinstance(r.get("orders"), dict) and isinstance(r.get("past"), dict):
        return r
    return _realized_blank(d or now_et().strftime("%Y-%m-%d"))


def realized_init(cfg, d):
    """파일이 없으면 d 날짜를 기준일(since)로 만들어 둠 — 체결 없는 날에도 '누적 시작일'이 남게"""
    if not os.path.exists(REALIZED_FILE):
        cfg._save_json(REALIZED_FILE, _realized_blank(d))


def record_realized(cfg, d, o, side, dq, da, cost, exec_id):
    """v2.19.0 판 46: 체결 증분 1건을 주문별로 쌓음 (장부 반영 직후 apply_tower_fills 가 부름 — 장중 반영도 같은 길).
    · 키 = 날짜_주문번호 (주문번호 없으면 exec_id). 같은 exec_id 는 한 번만 (장부와 같은 규칙 — 다시 불러도 안 늘어남)
    · 매도의 cost = F별 뺀 원가(cost_removed) — 장부 원금을 줄인 값과 같은 값 (없으면 호출한 쪽이 평단 × 수량으로 채워 줌)
    · 실패해도 체결 반영은 안 막음 (호출한 쪽이 try/except)"""
    r = realized_load(cfg, d)
    no = str(o.get("no") or "").strip() or str(exec_id)
    key = f"{d}_{no}"
    e = r["orders"].get(key) or {"date": str(d), "side": side, "qty": 0, "amt": 0.0, "cost": 0.0, "ids": []}
    if exec_id in e["ids"]:
        return
    e["qty"] = int(e["qty"]) + int(dq)
    e["amt"] = round(float(e["amt"]) + float(da), 4)
    if side == "SELL":
        e["cost"] = round(float(e["cost"]) + float(cost or 0.0), 4)
    e["ids"] = (e["ids"] + [exec_id])[-20:]
    r["orders"][key] = e
    try:                                              # 오래된 주문별 기록은 합계로 접음 (익절 판정은 주문 단위라 접기 전에 계산)
        cut = (datetime.date.fromisoformat(str(d)) - datetime.timedelta(days=REALIZED_KEEP_DAYS)).isoformat()
        old = [k for k, v in r["orders"].items() if str(v.get("date")) < cut]
        for k in old:
            v = r["orders"].pop(k)
            pa = r["past"]
            if v.get("side") == "SELL":
                pa["pnl"] = round(float(pa["pnl"]) + float(v["amt"]) - float(v["cost"]), 4)
                pa["sells"] = int(pa["sells"]) + 1
                pa["wins"] = int(pa["wins"]) + (1 if float(v["amt"]) > float(v["cost"]) else 0)
            else:
                pa["buys"] = int(pa["buys"]) + 1
            pa["through"] = max(str(pa.get("through") or ""), str(v.get("date")))
    except (ValueError, TypeError):
        pass
    cfg._save_json(REALIZED_FILE, r)


def realized_summary(cfg, d):
    """마감 결산용 숫자. 기준(코드 주석으로 고정):
    · 당일 실현수익 = 그날 매도 주문들의 (체결 금액 − 원가) 합계 · 수수료·세금 안 뺌
    · 당일 매수 횟수 = 체결이 있는 매수 주문 수 · 익절 횟수 = 체결이 있는 매도 주문 중 (체결 금액 > 원가) 인 주문 수 (손실·본전 매도는 익절 아님)
    · 누적실현 = since(기록 시작일)부터 모든 날 매도 주문 (체결 금액 − 원가) 합계 (접힌 past 포함)"""
    r = realized_load(cfg, d)
    day = [v for v in r["orders"].values() if str(v.get("date")) == str(d)]
    sells = [v for v in day if v.get("side") == "SELL"]
    pnl = sum(float(v["amt"]) - float(v["cost"]) for v in sells)
    total = float(r["past"].get("pnl") or 0.0) + sum(float(v["amt"]) - float(v["cost"]) for v in r["orders"].values() if v.get("side") == "SELL")
    return {"pnl": round(pnl, 2), "buys": sum(1 for v in day if v.get("side") == "BUY"), "sells": len(sells),
            "wins": sum(1 for v in sells if float(v["amt"]) > float(v["cost"])), "total": round(total, 2), "since": r.get("since")}


def _usd_signed(v):
    return ("+" if v > 0 else "-" if v < 0 else "") + f"${abs(v):,.2f}"


def strategy_ko(s=None):
    """v2.3.0: 7번은 하이브리드 (스나이퍼 매수 + 탑 매도) 하나만 씀"""
    return "하이브리드"


def tower_state_for(cfg, qty, principal, s=None):
    """탑쌓기 층 상태 → (상태, 파일에 있었는지). 파일이 없으면 지금 보유분(장부의 주식수·원금, 실행 시 읽은 값)을 1F로 만든 상태를 돌려줌 (저장은 안 함)"""
    d = cfg._load_json(TOWER_FILE, None)
    if isinstance(d, dict) and isinstance(d.get("floors"), list):
        return TW.ensure_state(d), True          # v2.2.6: 예전 상태(sell_block)를 층별 rebuy_pending 으로 옮김·주문번호 맵 준비
    return TW.migrate_from_holdings(qty, principal, s), False


def build_plan(s, cfg, price, fx, cash, qty, principal, sellable, ignore_auto_fx=False, open_px=0.0, tst=None):
    """오늘 계획 (장부·상태를 바꾸지 않음) → {"orders", "notes", "info"}. info 에 필요달러(need_usd)·부족달러(shortfall_usd)
    open_px: 오늘 시초가 (v2.2.14 — 0 이면 확정 전: 계획 배정 그대로)"""
    if tst is None:                                       # v2.3.0 B8: 호출한 쪽이 '오늘 체결을 메모리에서 더한 층 상태'를 주면 그걸로 계산 (텔레그램 오늘 계획·자금 현황)
        tst, _ = tower_state_for(cfg, qty, principal, s)
    ss = SN.load_state(cfg)                               # v2.3.0: 항상 하이브리드 계획 미리보기 (스나이퍼 매수·매도 + 탑 매도, 상태·장부 안 바꿈)
    return SN.make_plan(s, tst, price, ss, SN.rsi_from_state(ss, time.time())[0], cash, sellable, now_et(), is_trading_day=us_trading_day)


def hybrid_fx_plan(s, cash, rounds=1):
    """v2.3.0 환전 계산용 계획 모양 {"orders","notes","info"}: 필요 달러 = F 완성 기준 금액 × 하루 매수 F 수(tower_max_buy_layers_per_day, 기본 1) × rounds (휴장 전날은 1 + extra 회차).
    부족 달러 = max(0, 필요 − 달러 예수금) (info["shortfall_usd"] — auto_fx·알림이 읽는 키). 계산만 함 (시세·F 상태 안 읽음)"""
    fu, _n, _g = TW.params(s)
    layers = TW.buy_layers(s)
    rounds = max(1, int(rounds))
    need = round(fu * layers * rounds, 2)
    cash = float(cash or 0)
    basis = f"F 완성 기준 금액 ${fu:,.0f} × 하루 매수 F 수 {layers}" + (f" × {rounds}회차" if rounds > 1 else "") + f" = ${need:,.0f}"
    return {"orders": [{"side": "BUY", "type": "LIMIT", "qty": 0, "price": 0.0, "desc": basis}], "notes": [], "fx_basis": basis,
            "info": {"mode": SN.MODE_SNIPER, "need_usd": need, "usd_cash": round(cash, 2), "shortfall_usd": round(max(0.0, need - cash), 2), "auto_fx": True,
                     "floor_usd": fu, "layers": layers, "rounds": rounds}}


# ---------------------------------------------------------------- v2.2.14 판 17 시초가 (그날 한 번만 정함)
def open_price_path(s, d, live):
    return os.path.join(s["state_dir"], "data", f"{'' if live else 'dry_'}open_price_{d}.json")


def load_open_price(s, d, live):
    """오늘(ET 날짜 d) 이미 정한 시초가 → 가격, 없거나 이상하면 0.0 (읽기만 — 정하지 않음)"""
    try:
        with open(open_price_path(s, d, live), "r", encoding="utf-8") as f:
            r = json.load(f)
        v = float(r.get("open") or 0)
        return v if isinstance(r, dict) and r.get("date") == d and math.isfinite(v) and v > 0 else 0.0
    except (OSError, ValueError, TypeError, AttributeError):
        return 0.0


def ensure_open_price(s, cfg, d, live, now, price, status):
    """시초가: 이미 저장돼 있으면 그 값(그날 내내 같은 값 · 재시작해도 안 바뀜). 없으면 정규장(status "004") 이고 09:30 ET 이후일 때 지금 현재가를 처음으로 확인한 값으로 저장.
    시초가를 예측하거나 전일종가로 대신하지 않음 — 아직 못 정하면 0.0. 시세 API 에 시초가 필드가 있는지는 근거 파일에 없어 미확인 → 첫 확인가 방식"""
    saved = load_open_price(s, d, live)
    if saved > 0:
        return saved
    try:
        px = float(price)
    except (TypeError, ValueError):
        return 0.0
    if not (math.isfinite(px) and px > 0) or str(status) != "004" or now.time() < OPEN_TIME_ET:
        return 0.0
    cfg._save_json(open_price_path(s, d, live), {"date": d, "open": round(px, 4), "source": "first_price_seen_after_0930_ET",
                                                  "seen_at_et": now.strftime("%Y-%m-%d %H:%M:%S")})
    logging.info(f"시초가 확정 ${px:.2f} (09:30 ET 이후 처음 확인한 현재가, {d})")
    return px


def run_open_capture(s, api, live, now):
    """loop 가 매번 부름 (평일 09:30 ET 이후). 오늘 시초가가 아직 없으면 시세를 한 번 읽어 정함. 저장돼 있으면 시세 조회 없이 바로 끝 → 가격 또는 0.0"""
    d = now.strftime("%Y-%m-%d")
    saved = load_open_price(s, d, live)
    if saved > 0 or now.time() < OPEN_TIME_ET or now.time() >= datetime.time(16, 0):
        return saved
    try:
        status = api.us_market_status()
        if str(status) != "004":
            return 0.0
        px = float(api.price(s["symbol"], s["price_market"])["price"])
    except MeritzError as e:
        logging.warning(f"시초가 확인 실패(다시 시도): {e}")
        return 0.0
    return ensure_open_price(s, ConfigManager(s), d, live, now, px, status)


def auto_fx(s, api, cfg, plan, live, d, fx_now=None):
    """부족 달러만큼 원→달러 환전. 부족 없거나 꺼져 있으면 None. live=False 면 신청 없이 계산만.
    v2.0.8: fx_now(한국시간으로 바꿀 수 있는 시각)를 주면 실거래 신청 전에 '실시간 환전 시간(평일·국내 휴일 아님·09:00~23:50/00:20~02:00)'인지 확인 — 시간외·환전 불가 시간엔 신청 안 함(기록 안 씀)
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
    if fx_now is not None:                                 # v2.0.8 수수료 무료는 실시간 환전 때만 — 시간외·환전 불가 시간·휴일엔 신청 안 함 (기록 안 씀)
        w = fx_window_info(fx_now, s, check_deadline=False)
        if not w["open"]:
            r.update(status=f"환전 안 함 — 지금은 실시간 환전 시간이 아니에요 ({w['why']})")
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
    t = (f"환전: 부족 ${math.ceil(r['short']):,} → 신청 ${r['want']:,}" + (" (하루 상한 적용)" if r["capped"] else "")
         + (f" · 약 ₩{r['krw_est']:,} (환율 {r['rate']:,.0f})" if r.get("rate") else "") + f" · {r['status']}")
    return t + (f"\n{r['error']}" if r.get("error") else "") + "\n"


SIDE_KO = {"BUY": "매수", "SELL": "매도"}
TYPE_KO = {"LIMIT": "지정가", "LOC": "종가 조건", "MOC": "종가 시장가"}


def fmt_orders(orders):
    return "\n".join(f"- {SIDE_KO.get(o['side'], o['side'])} {o['qty']}주 @ {'시장가' if o['type'] == 'MOC' else '$%.2f' % float(o['price'])} "
                     f"({TYPE_KO.get(o['type'], o['type'])}) {o.get('desc', '')}".rstrip()
                     for o in orders) or "- (주문 없음)"


def _tower_progress(tw, s, fid=None):
    """v2.2.15 판 19: (탑 줄, 지금 채우는 F 진행 글자) — 상황판과 같은 tower_strategy 함수를 그대로 부름 (비율 새로 계산 안 함). v2.2.17: fid 를 주면 그 F의 진행 글자 (없으면 tw["active"] = 첫 F).
    plan['info']['tower']['floors'] 를 view_lines 가 읽는 모양(id·qty·cost·target·done)으로 맞춰 넘김. 실패하면 ('', '') — 표시만 빠지고 주문·알림은 그대로"""
    try:
        view = [{"id": f["id"], "qty": f["qty"], "cost": f["cost"], "target": f.get("target") or tw.get("floor_usd"), "done": bool(f.get("complete"))}
                for f in (tw.get("floors") or [])]
        top = TW.view_lines({"floors": view}, s)[0]
        act = ""
        want = tw.get("active") if fid is None else fid
        if want and not (tw.get("new_floor") and want == tw.get("active")):
            for f in view:
                if f["id"] == want:
                    act = f" · {TW.floor_status(f)}" + ("" if TW.is_complete(f) else f" ({int(round(TW.fill_ratio(f) * 100))}%)")
        return top + "\n", act
    except Exception:
        return "", ""


ANCHOR_KO = {"exit": "직전 매도가", "buy": "직전 매수가", "avg": "낮은 F 평단"}      # v2.3.0 B8: 영어 종류 이름을 화면에 그대로 안 보임


def sniper_plan_head(plan, s):
    """v2.2.20 스나이퍼 계획 미리보기 글자"""
    i, sg = plan["info"], plan["info"]["signal"]
    pl = f" ({i['profit_pct']:+.2f}%)" if i.get("profit_pct") is not None else ""
    tp = i.get("tower_pct") or [0.0, 0.0]
    head = (f"하이브리드 · 현재가 ${i['price']:.2f} · 평단 ${i['avg']:.2f}{pl} · F {i['n_layers']}개 · 스나이퍼 익절(미완성 F) 1층 +{i['tp_l1']:g}% · 상단층 +{i['tp_upper']:g}% · 탑 매도(완성 F) +{tp[0]:g}% → {tp[1]:g}%\n"
            + ("매도 목표 " + " · ".join(f"{r['no']}F{'(완성·탑)' if r.get('complete') else ''} ${(SN.ceil2(r['avg'] * (1 + tp[0] / 100.0)) if r.get('complete') else r['target']):.2f}" + (" (공격 층)" if r["role"] == "L1" and not r.get("complete") else "") for r in sorted(i["sells"], key=lambda r: r["no"])) if i.get("sells") else "매도 목표 없음 (보유 F 없음)"))
    if i.get("boxes"):                                                       # v2.6.0 버킷별 매도 목표 (미완성 F의 버킷마다 자기 평단 기준)
        head += "\n버킷별 매도 목표 " + " · ".join(f"{b['label']} ${b['avg']:.2f}→${b['target']:.2f} ({b['qty']}주{'·공격' if b['role'] == 'L1' else ''}{'·졸업 매도' if b.get('kind') == 'grad' else ''})" for b in i["boxes"][:6]) + (f" · 그 위 {len(i['boxes']) - 6}개" if len(i["boxes"]) > 6 else "")
    head += f"\n매수 신호: {SN.SIGNAL_KO.get(sg['signal_type'], sg['signal_type'])}"
    if sg.get("anchor"):
        head += f" · 기준 ${sg['anchor']:.2f}({ANCHOR_KO.get(sg['anchor_kind'], sg['anchor_kind'])}) · 눌림 ${sg['pullback_price']:.2f}({sg['drop_pct']:+.1f}%)"
        if sg.get("cap_price"):
            head += f" · 상한 ${sg['cap_price']:.2f}"
    head += " · RSI " + (f"{i['rsi']:.1f}" if i.get("rsi") is not None else "모으는 중")
    fl = i.get("fill")
    if fl:
        head += f"\n채우는 F {fl['no']}F{' (재매수 대기)' if fl['rebuy'] else ''}: 채움 {fl['ratio'] * 100:.0f}% (원가 ${fl['cost']:,.0f} / F 완성 기준 금액 ${fl['target']:,.0f})"
    head += f"\n필요 달러 ${i['need_usd']:,.0f} · 예수금 ${i['usd_cash']:,.0f}" + (f" · 부족 ${math.ceil(i['need_usd'] - i['usd_cash']):,}" if i['need_usd'] > i['usd_cash'] + 1e-9 else "")
    return head


def plan_head(plan, s):
    if plan["info"].get("mode") == SN.MODE_SNIPER:
        return sniper_plan_head(plan, s)
    i = plan["info"]
    pl = f" ({i['profit_pct']:+.2f}%)" if i.get("profit_pct") is not None else ""
    tw = i.get("tower") or {}
    fl = tw.get("floors") or []
    _rank = {int(f.get("id")): n + 1 for n, f in enumerate(sorted([f for f in fl if int(f.get("qty") or 0) > 0], key=lambda f: (float(f.get("avg") or 0), -int(f.get("id") or 0))))}

    def _flab(fid, new=False):
        if new:
            return "새 F"
        f = next((x for x in fl if int(x.get("id")) == int(fid)), None)
        if f is None:
            return f"{fid}F"
        no = _rank.get(int(fid))
        base = int(math.floor(float(f.get("avg") or 0) + 1e-9))
        return f"{base}F{no}" if no else f"{base}F"

    top_line, act_prog = _tower_progress(tw, s)      # v2.2.15 판 19: 탑 진행률 (맨 앞 줄 + 지금 채우는 F 뒤)
    layers = tw.get("layers") or ([{"id": tw["active"], "new_floor": tw.get("new_floor"), "cells": tw.get("cells")}] if tw.get("active") else [])   # v2.2.17: 오늘 사는 F 전부 (예전 모양 info 도 읽음)
    act_txt = " + ".join(f"{_flab(ly['id'], ly.get('new_floor'))}{act_prog if ly['id'] == tw.get('active') else _tower_progress(tw, s, ly['id'])[1]}"
                         for ly in layers) or "없음"
    head = (top_line + f"탑쌓기 · 현재가 ${i['price']:.2f} · 평단 ${i['avg']:.2f}{pl} · F {len(fl)}개 (완성 {sum(1 for f in fl if f['complete'])}) · 지금 채우는 F "
            + act_txt + "\n"
            + ("매도 목표 " + " · ".join(f"{_flab(r['id'])} ${r['target']:.2f}" for r in i["sells"]) if i.get("sells") else f"매도 목표 ${i['sell_target']:.2f}")
            + (f" · 칸당 " + " / ".join(f"{_flab(ly['id'], ly.get('new_floor'))} ${ly.get('unit_usd', 0):,.0f}" for ly in tw["layers"]) if len(tw.get("layers") or []) > 1 else f" · 칸당 ${i.get('unit_usd', 0):,.0f}")   # v2.2.17: 여러 F이면 F마다
            + (f" · 환율 {i['fx']:,.0f}" if i.get("fx") else ""))
    for ly in layers:   # v2.2.3: 다음 회차 가격별 배정 (v2.2.17: 오늘 사는 F마다 floor_id 를 적어 1F·2F가 같이 나가는 게 보이게)
        cells = ly.get("cells") or []
        if cells:
            head += "\n다음 회차" + (f" {_flab(ly['id'], ly.get('new_floor'))}" if ly.get("id") else "") + " 가격별 배정:"
            for c in cells:
                head += f"\n${c['price']:.2f} → ${c['amount']:,.0f} ({c['qty']}주)"
    oc = i.get("open_cap") or {}
    if oc.get("open") and oc.get("first"):      # v2.2.14: 시초가가 정해진 뒤에만 (정해지기 전엔 계획 배정 그대로, 시초가를 지어내 보이지 않음)
        if len(tw.get("layers") or []) <= 1:
            head += f"\n시초가 ${oc['open']:.2f} · 첫 칸 ${oc['first']:.2f}" + (" (상한 적용)" if oc.get("applied") else " (상한 안 걸림 · 계획 그대로)")
        else:                                   # v2.2.17: 여러 F이면 F마다 첫 칸
            head += f"\n시초가 ${oc['open']:.2f}" + "".join(
                f" · {_flab(ly['id'], ly.get('new_floor'))} 첫 칸 ${ly['open_cap']['first']:.2f}" + (" (상한 적용)" if ly["open_cap"].get("applied") else " (상한 안 걸림 · 계획 그대로)")
                for ly in tw["layers"] if (ly.get("open_cap") or {}).get("first"))
    if tw.get("new_floor_blocked"):
        head += "\n새 F 못 만듦: " + tw["new_floor_blocked"]["text"] + " — 풀이님 확인 필요"
    head += (f"\n필요 달러 ${i['need_usd']:,.0f} · 예수금 ${i['usd_cash']:,.0f}" + (f" · 부족 ${math.ceil(i['shortfall_usd']):,}" if i.get("shortfall_usd") else "")
             if i.get("need_usd") is not None else "")
    return head


# ---------------------------------------------------------------- v2.0.3 당일 매도
_INTRA = {"last": 0.0, "err_day": ""}
MKT_PRE = SN.STATUS_PRE                  # 판 38: 프리마켓 코드 003 (v2.0.5 주석뿐 — 공식 문서 확인 안 됨, 프리장 주문·시세 접수는 미확인)
MKT_REGULAR, MKT_AFTER = "004", "005"    # 장운영 코드: 정규장 · 장후 (v2.2.12 판 15: 장후에도 매도를 냄. 005 가 장후인 근거는 v2.0.5 주석뿐 — 공식 문서 확인 안 됨)


def intraday_on(s):
    """당일 매도 확인을 쓰는지: 확인 간격 > 0 이고 주문 방식이 지정가(LIMIT)일 때만. (LOC 는 종가에만 체결돼서 장중 확인이 의미 없음 → 예전 동작)"""
    try:
        sec = float(s.get("intraday_sell_check_sec") or 0)
    except (TypeError, ValueError):
        return False
    return sec > 0 and s.get("order_type") == "LIMIT"


def _warn_once(cfg, mark, m, key, note, text):
    """같은 이유의 알림은 하루 한 번만 (주문 기록 파일에 남김)"""
    w = m.setdefault("intraday_warn", [])
    if key in w:
        return
    w.append(key)
    cfg._save_json(mark, m)
    note.send(text)


# ---------------------------------------------------------------- v2.2.6 체결 반영 · 알림 도우미
def fill_rows_for(api, s, d):
    """그날 주문의 체결 내역 {주문번호: {"no","side","qty","amt","t"}}. t = 체결 시각 글자 (설정 fill_time_field 로 읽음 — 필드 이름 미확인, 없으면 None).
    api 에 fills_rows 가 있으면 그것, 없으면 fills()"""
    dt = datetime.date.fromisoformat(d)
    a, b = (dt - datetime.timedelta(days=1)).strftime("%Y%m%d"), (dt + datetime.timedelta(days=2)).strftime("%Y%m%d")
    fr = getattr(api, "fills_rows", None)
    if fr is not None:
        tk = str(s.get("fill_time_field") or "").strip()
        try:
            rows = fr(a, b, tk) if tk else fr(a, b)
        except TypeError:
            rows = fr(a, b)
        return {str(r["no"]): dict(r, t=r.get("t")) for r in rows}
    return {str(no): {"no": str(no), "side": v[0], "qty": int(v[1]), "amt": float(v[2]), "t": None} for no, v in api.fills(a, b).items()}


def fill_items(m, rows):
    """오늘 주문 기록(m["orders"]) 중 체결이 있는 것 → [{"o": 주문, "side", "q": 누적 체결 수량, "amt": 누적 금액, "t"}]"""
    out = []
    for o in m.get("orders") or []:
        r = rows.get(str(o.get("no")))
        if r and int(r["qty"]) >= 1:
            out.append({"o": o, "side": r["side"], "q": int(r["qty"]), "amt": float(r["amt"]), "t": r.get("t")})
    return out


def free_cash_ctx(s):
    """v2.15.0 판 41 할 일 2: free_cash 장부(free_cash.py)를 처음 한 번 시작 — 시작값 = 버킷 시드 − 미완성 F 원가 (이미 시작했으면 그대로). 장부 파일 위치(state_dir)를 돌려줌"""
    sd = s["state_dir"]
    tst = ConfigManager(s)._load_json(TOWER_FILE, {}) or {}
    inc = sum(float(f.get("cost") or 0.0) for f in (tst.get("floors") or []) if not TW.is_complete(f))
    FC.ensure_init(sd, TW.box_seed(s), inc)
    return sd


def free_cash_fill(s, side, amount, cost_removed=None):
    """SOXL 체결 → free_cash 장부 (매수 −, 매도 + 수혈금 먼저 상환 — 판 41 Q5·Q7). 실패해도 체결 반영은 안 막음 (로그만)"""
    if amount <= 0:
        return None
    try:
        return FC.on_fill(free_cash_ctx(s), side, amount, cost_removed)
    except Exception as e:
        logging.warning(f"free_cash 기록 실패 {type(e).__name__}")
        return None


def guard_gate(s, order, cash_usd):
    """v2.15.0 판 41 할 일 2: 스나이퍼 매수 직전 GUARD30 + 수혈(INJECT) — 원작 evaluate_guard30_and_reserve_injection 그대로 (FC.guard). 장부 free_cash 와 메리츠 실제 달러(cash_usd)를 견줌:
    PROCEED_NORMAL 통과 · INJECT_AND_PROCEED 는 장부에 수혈을 반영하고 통과 · BLOCK_AND_ALERT_DEPOSIT 는 보류. 판정이 고장나면 안전하게 보류 → (통과, 판정 dict)"""
    if not order or order.get("side") != "BUY":
        return True, {}
    try:
        sd = free_cash_ctx(s)
        info = FC.guard(sd, cash_usd, order.get("price"), order.get("plan_usd") or 0.0)
        injected = FC.apply_inject(sd, info)
        return bool(info.get("should_proceed")), dict(info, injected=injected)
    except Exception as e:
        return False, {"action": "GUARD_ERROR", "error": type(e).__name__, "min_req_cash": 0.0, "recommended_deposit_usd": 0.0}


def assassin_promote(s, api, want_live, apply=False):
    """v2.13.0 판 40 할 일 2: 암살자 승격·복귀 (원작 toggle_assassin_live_promotion 규칙, BB.assassin_promote_plan). apply=False 면 계획만 (텔레그램 확인 전 미리보기) → (계획 dict, 현재 모드).
    apply=True 면 계획대로 execution_mode 저장. 보유·미체결은 메리츠에서 읽음 (못 읽으면 verified=False → 승격 거절). 주문은 안 냄"""
    sd = s["state_dir"]
    cur = BB.assassin_mode(sd)
    held, verified, open_orders = 0, False, []
    try:
        held = int(api.holding(s["symbol"])[0])
        open_orders = list(api.open_orders_today(s["symbol"]))
        verified = True
    except Exception as e:
        logging.warning(f"암살자 승격: 보유 확인 실패 {type(e).__name__}")
    plan = BB.assassin_promote_plan(cur, want_live, held, open_orders, verified, s.get("assassin_live_unlock") is True)
    if apply and plan["to"] is not None:
        BB.assassin_set_mode(sd, plan["to"], demote_to_sim_after_exit=bool(plan["demote_after_exit"]), mode_changed_at=now_et().isoformat())
    return plan, cur


def assassin_poll(s, api, note):
    """1분 봉 모으기 + 암살자 모의 지표 (실패해도 SOXL 매매 안 막음). v2.15.0 판 41: 바벨 틱에서 분리 — 바벨이 없어졌으니 바벨 켜짐과 무관하게 돈다 (SGOV 틱은 삭제)"""
    out = {}
    try:
        sd = s["state_dir"]
        sx = float(api.price(s["symbol"], s["price_market"])["price"])
        qx = float(api.price("QQQ", s["price_market"])["price"])
        sb, qb = BB.bars_add(sd, s["symbol"], sx), BB.bars_add(sd, "QQQ", qx)
        out["assassin"] = BB.assassin_sim_metrics(sd, sb, qb, sx, qx)
    except Exception as e:
        logging.warning(f"암살자 모의 지표 실패 {type(e).__name__}")
    return out


ASSASSIN_TICK_SEC = 5.0               # 판 41 할 일 1: 암살자 틱 간격 (모의·예약 때). 실전(LIVE)이면 매 틱 (정정·스윕이 빨라야 해서)


def assassin_live_step(s, api, note):
    """판 41 할 일 1: 원작 암살자 틱(모의⇄0주예약⇄실전 통합 상태 머신)을 메리츠 API 로 한 번 부름 → 원작 결과 글자 (실패·건너뜀이면 None).
    알림(원작이 만든 title·body)은 텔레그램으로 보냄. 주문·정정·취소는 assassin_live.py 를 거침 (dry_run 이면 주문 없이 가짜 번호)"""
    try:
        n = now_et()
        if not BB.assassin_blocks(s["state_dir"]) and time.time() - _SNIPER.get("assassin_last", 0.0) < ASSASSIN_TICK_SEC:
            return None
        _SNIPER["assassin_last"] = time.time()
        import assassin_live as AL
        d = n.strftime("%Y-%m-%d")
        seed = TW.box_seed(s)
        ctx = AL.get_context(api, s, lambda: fill_rows_for(api, s, d), lambda: n.strftime("%Y%m%d"),
                             lambda: {"initial_seed_usd": seed, "buckets": [], "sub_buckets": [], "buy_order_id": "", "sell_order_id": ""},
                             dry=bool(s.get("dry_run", True)))
        ctx.alerts.clear()
        r = AL.tick(ctx, n)
        for title, body in list(ctx.alerts):
            note.send(f"{title}\n{body}" if body else title)
        return r
    except Exception as e:
        logging.warning(f"암살자 틱 실패 {type(e).__name__}: {str(e)[:120]}")
        return None


def apply_tower_fills(s, cfg, d, items, tst, only_sells=False, persist=True, sniper_only=False):
    """체결을 F 상태(tst)와 장부에 반영 → [{"o","side","dq","da","cq","closed"}] (실제로 새로 반영한 것만).
    - 순서: TW.sort_fills (시간순, 시각 필드가 없으면 매도 먼저, 새 F 계획 매수는 매도 뒤) — 장부도 같은 순서로 반영 (버그 1)
    - 두 번 반영 방지: 주문번호별 누적 체결 중 늘어난 몫만 (TW.apply_fill_delta). 장부는 exec_id(날짜_주문번호[_누적수량])로도 막음 (버그 2)
    - 한 묶음 저장: 항목마다 장부(원금·수량 → 거래 기록)에 쓰고, 끝에 층 상태를 저장. 중간에 멈춰도 다시 부르면 장부는 exec_id 로, 층은 주문번호 맵으로 각각 빠진 몫만 채워 맞춰짐
    - 매도는 F별로 줄이고, 장부 원금은 그 F 원가만큼만 줄임 (cost_removed)
    persist=False 면 F 상태(메모리)만 바꾸고 장부·파일은 안 건드림 (장중 평단 판단용)
    v2.2.20: sniper_only=True 면 매도와 스나이퍼 매수(kind buy_sniper)만 반영 (탑쌓기 매수는 run_sync 몫). 장부에 쓴 체결이 있으면 스나이퍼 기준가(직전 익절·매수가)도 갱신"""
    gap, start = TW.params(s)[2], float(s.get("tower_floor1_start_usd") or 0)
    done = []
    for it in TW.sort_fills(tst, items):
        if only_sells and it["side"] != "SELL":
            continue
        if sniper_only and it["side"] == "BUY" and it["o"].get("kind") != "buy_sniper":
            continue
        o, side = it["o"], it["side"]
        pq = TW.applied_qty(tst, o)
        dq, da = TW.apply_fill_delta(tst, o, it["q"], it["amt"], gap, start)
        removed = tst.pop("_cost_removed", None)
        if dq <= 0:
            continue
        closed = None
        cost = removed if side == "SELL" else None             # v2.19.0 판 46: 매도 원가 — 장부 원금을 줄인 값과 같은 값 (done 에도 실어 줌)
        if persist:
            exec_id = f"{d}_{o['no']}" if pq == 0 else f"{d}_{o['no']}_{it['q']}"
            if side == "SELL" and cost is None:                # 원가를 못 받았으면 장부(config.apply_fill)와 같은 규칙: 평단 × 수량
                cost = dq * cfg.avg_price(cfg.get_position())
            _, closed = cfg.apply_fill(side, dq, da / dq, d, False, exec_id, cost_removed=(removed if side == "SELL" else None))
            try:                                               # 실현수익 기록 (실패해도 체결 반영은 계속)
                record_realized(cfg, d, o, side, dq, da, cost, exec_id)
            except Exception as e:
                logging.warning(f"실현수익 기록 실패 {type(e).__name__}: {str(e)[:100]}")
        done.append({"o": o, "side": side, "dq": dq, "da": da, "cq": it["q"], "closed": closed, "cost": cost})
        if persist:
            free_cash_fill(s, side, da, removed if side == "SELL" else None)      # v2.15.0 판 41 할 일 2: free_cash 장부 (매수 −, 매도 + 수혈금 먼저 상환)
    tst.pop("_cost_removed", None)
    if persist and done:
        cfg._save_json(TOWER_FILE, tst)
        try:
            ss = SN.load_state(cfg)
            if SN.note_fills(ss, done, now_et().isoformat()):
                SN.save_state(cfg, ss)
        except Exception as e:
            logging.warning(f"스나이퍼 기준가 갱신 실패 {type(e).__name__}")
    return done


def next_trade_lines(s, st):
    """체결 알림에 붙는 '다음 매매': F별 다음 매도(목표가·수량)와 다음에 살 칸. 상태(st)는 바꾸지 않음. 글자 주의: notifier.to_korean 이 '= $'·'필요 $' 같은 앞말 뒤 금액의 소수점을 지우므로
    가격 앞에는 '평단'·'목표가'·'→' 만 씀 (금액은 어차피 정수)"""
    try:                                                      # v2.3.0: 하이브리드 다음 매매 (F별 목표가 — 완성 F는 탑 매도 + 눌림·돌파 타점)
        return SN.trigger_lines(s, st, SN.load_state(ConfigManager(s)))
    except Exception:
        return ["다음 매매: 계산 못 함"]
    pct = float(s.get("sell_profit_pct") or 0)
    frac = float(s.get("sell_fraction_pct") or 0)
    lines = []
    tq, tc = TW.totals(st)
    live = [f for f in TW.top_down(st) if int(f.get("qty") or 0) > 0]
    nos = SN.sniper_numbers(st)      # 표시용 F 번호 {층 id: 스나이퍼 번호}
    for f in live[:4]:
        fa = TW.floor_avg(f)
        wait = " (이 F 재매수가 체결된 뒤부터)" if f.get("rebuy_pending") and not s.get("allow_consecutive_sell") else ""
        sq = TW.floor_sell_qty(int(f['qty']), frac)
        if sq < 1:
            lines.append(f"다음 매도: {nos.get(int(f['id']), int(f['id']))}F 평단 ${fa:.2f} · 보유 {int(f['qty'])}주 — 자동 매도 제외 (직접 매도)")
        else:
            lines.append(f"다음 매도: {nos.get(int(f['id']), int(f['id']))}F 평단 ${fa:.2f} → 목표가 ${ceil2(fa * (1 + pct / 100.0)):.2f} 에 {sq}주 ({pct:g}%){wait}")
    if len(live) > 4:
        lines.append(f"다음 매도: 그 위·아래 {len(live) - 4}개 F는 같은 규칙")
    try:
        pl = TW.make_plan(dict(s, auto_fx_enabled=True), st, tq, tc, 0.0, 1.0, 1e12, tq)
        tw = (pl.get("info") or {}).get("tower") or {}
        lys = tw.get("layers") or ([{"id": tw["active"], "new_floor": tw.get("new_floor"), "cells": tw.get("cells")}] if tw.get("active") else [])
        shown = [ly for ly in lys if ly.get("cells")]   # v2.2.8: F의 안 산 칸 전부 표시 (v2.2.17: 하루 최대 N_buy F — F마다 한 줄)
        for ly in shown:
            lab = "새 F" if ly.get("new_floor") else f"{nos.get(int(ly['id']), ly['id'])}F"
            lines.append(f"다음 매수: {lab} " + " · ".join(f"${c['price']:.2f} → ${c['amount']:,.0f} ({c['qty']}주)" for c in ly["cells"]))
        if not shown:
            lines.append("다음 매수: 없음 (F를 다 채웠거나 한도에 닿음)")
    except Exception:
        lines.append("다음 매수: 계산 못 함")
    return lines


def fill_alert_text(s, d, new, open_rows, sim):
    """체결 알림 글자. new = [(item, 이전 알림 수량)]. 한 줄 = 이번에 늘어난 수량·평균가, 주문 대비 누적·미체결, 조건(주문 설명·지정가)"""
    own_open = {str(r.get("oder_no") or "").strip(): int(float(str(r.get("ncnt_qty") or 0).replace(",", "") or 0)) for r in open_rows if isinstance(r, dict)}
    lines = [f"{d} 체결 알림"]
    for it, nq in new:
        o = it["o"]
        dq, da = it["q"] - nq, it["amt"] - float(o.get("notified_amt") or 0)
        px = da / dq if dq else 0.0
        left = own_open.get(str(o.get("no")), max(0, int(o.get("qty") or 0) - it["q"]))
        lines.append(f"{SIDE_KO.get(it['side'], it['side'])} 체결 {dq}주 @ ${px:.2f}" + (f" (이전 알림 {nq}주 이후 늘어난 수량)" if nq else ""))
        lines.append(f"  주문 {o.get('qty')}주 중 누적 {it['q']}주 체결 · " + ("전량 체결" if left <= 0 else f"미체결 {left}주"))
        lines.append(f"  조건: {o.get('desc', '')}" + (f" · {TYPE_KO.get(o.get('type'), o.get('type'))} ${float(o['price']):.2f}" if o.get("type") != "MOC" and o.get("price") else ""))
    if sim is not None:
        lines += next_trade_lines(s, sim)
    else:
        lines.append("다음 매매는 내일 아침 계획에서 정해져요")
    return "\n".join(lines)


def send_fill_alerts(s, api, note, cfg, m, mark, items, d, sim):
    """주문마다 '알림 보낸 누적 수량'(주문 기록의 notified_qty)보다 늘어난 체결이 있으면 한 메시지로 알림 → 보낸 주문 수.
    '보냄' 표시는 전송 성공 뒤에만 저장 (v2.2.6: 전송이 실패하면 표시 안 함 → 다음 확인 때 다시. 저장 직전에 멈추면 중복은 가능하지만 누락은 없음)"""
    if not getattr(note, "ok", True):
        return 0
    new = [(it, int(it["o"].get("notified_qty") or 0)) for it in items if it["q"] > int(it["o"].get("notified_qty") or 0)]
    if not new:
        return 0
    try:
        open_rows = api.open_orders_today(s["symbol"])         # 미체결 수량(ncnt_qty)으로 '남은 주문' 구분
    except Exception as e:
        logging.warning(f"체결 알림: 미체결 조회 실패 {type(e).__name__} — 주문 수량 − 누적 체결로 계산")
        open_rows = []
    if note.send(fill_alert_text(s, d, new, open_rows, sim)) is False:
        return 0
    for it, _ in new:
        it["o"]["notified_qty"] = it["q"]
        it["o"]["notified_amt"] = round(it["amt"], 4)
    cfg._save_json(mark, m)
    return len(new)


def foreign_open_sells(open_rows, m, rows):
    """우리 주문이 아닌 SOXL 매도 미체결 (수동 주문 등). 미체결 행에 주문번호(oder_no)가 있으면 번호로, 없으면 우리 미체결 매도 주문 수만큼 빼고 셈 (필드 이름 미확인)"""
    opens = [r for r in open_rows if isinstance(r, dict) and str(r.get("seln_byov_clcd")) == "1"]
    own = {str(o.get("no")) for o in (m.get("orders") or []) if o.get("no")}
    ids = [str(r.get("oder_no") or "").strip() for r in opens]
    if opens and all(ids):
        return [r for r, i in zip(opens, ids) if i not in own]
    unfilled = sum(1 for o in (m.get("orders") or []) if o.get("no") and o.get("side") == "SELL" and int((rows.get(str(o["no"])) or {}).get("qty", 0)) < int(o.get("qty") or 0))
    return opens[unfilled:]


def pick_sells(reached, left_n):
    """v2.2.17: 같은 확인에서 목표에 닿은 층(reached = 매도 주문 목록)을 번호가 큰 층(맨 위 층)부터 정렬해, 오늘 남은 매도 횟수(left_n)만큼은 팔 주문으로, 나머지는 알림만(들어온 순서 그대로) → (팔 주문, 알림만 주문). 순수 계산"""
    n = max(0, int(left_n))
    sells = sorted(reached, key=lambda o: -int(o["floor_id"]))[:n]
    return sells, [o for o in reached if not any(o is x for x in sells)]        # 알림만 층은 들어온 순서 그대로 (N_sell=1 일 때 예전 알림 순서와 같음)


def run_intraday_sell(s, api, note, allow_new_sells=True):
    """당일 확인 (실거래만, loop 가 주문 시간대~체결 반영 시각 전에 부름). 오늘 주문 기록이 있고 체결 반영 전인 동안 intraday_sell_check_sec(기본 30초)마다:
    ① (v2.2.6, 탑쌓기) 오늘 매도 체결을 장부와 F에 즉시 반영 ② 체결 알림 (이전 알림 이후 늘어난 수량) ③ 오늘 체결된 매수까지 반영한 F 평단의 +목표% 에 현재가가 닿은 F마다 그 F의 매도 비중을 지정가로 매도.
    매수는 안 함 · F당 하루 매도 1건 · 하루 매도 F 수는 최대 N_sell (v2.2.17, 설정 tower_max_sell_layers_per_day 기본 1) · 매수 체결의 장부 반영은 run_sync (매도 반영 뒤에 새 F 매수를 배정해야 해서). allow_new_sells=False 면 새 매도 주문은 안 내고 ①②만 → 상태 글자"""
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
    bad = gate_problems(s, cfg, live=True)
    if bad:
        logging.warning("당일 매도 확인 건너뜀: " + "; ".join(bad)[:200])
        return "차단"
    pos = cfg.get_position()
    buys = [o for o in m["orders"] if o.get("side") == "BUY"]
    pct = float(s["sell_profit_pct"])
    # v2.1.0: 체결 조회를 시세 게이트보다 먼저 (지정가 매수는 지정가보다 낮게 체결될 수 있음 — 2026-11-18 사례). v2.2.6: 탑쌓기는 매도·알림 때문에 주문이 하나라도 있으면 조회
    rows = {}
    if buys or any(o.get("no") for o in m["orders"]):
        try:
            rows = fill_rows_for(api, s, d)
        except MeritzError as e:
            logging.warning(f"당일 매도 확인: 체결 조회 실패 {e}")
            return "체결 조회 실패"
    items = fill_items(m, rows)
    st, applied_now = None, []
    st, had = tower_state_for(cfg, int(pos["qty"]) if pos else 0, float(pos["principal"]) if pos else 0.0, s)
    if had and pos:
        applied_now = apply_tower_fills(s, cfg, d, items, st, only_sells=True)         # 매도 체결 즉시 반영 (장부·F 같이 저장) — 동기화 전에도 F 상태가 맞음
        pos = cfg.get_position()
    if (pos is None) or (int(pos["qty"]) <= 0 and not buys):
        return "해당 없음"                            # 기존 보유도 오늘 낼 매수도 없음 → 조회할 것 없음
    q0, pr0 = int(pos["qty"]), float(pos["principal"])
    q, pr = q0, pr0
    sim = copy.deepcopy(st)
    cands = [cfg.avg_price(pos)] if q0 > 0 else []     # 시세 게이트용: 평균은 구성 값(기존 평단·오늘 실제 체결 단가) 중 가장 낮은 값보다 낮아질 수 없음 → 안 맞게 막는 일 없음
    # 오늘 체결된 매수를 '메모리 안에서만' 반영 (장부 파일은 그대로) — 새 F 계획 매수는 매도 반영 뒤 1층 빈칸으로 (B1)
    gap, start = TW.params(s)[2], float(s.get("tower_floor1_start_usd") or 0)
    for it in TW.sort_fills(sim, [i for i in items if i["side"] == "BUY"]):
        dq, da = TW.apply_fill_delta(sim, it["o"], it["q"], it["amt"], gap, start)
        sim.pop("_cost_removed", None)
        q, pr = q + dq, pr + da
    cands = [TW.floor_avg(f) for f in TW.top_down(sim) if int(f.get("qty") or 0) > 0 and TW.floor_avg(f) > 0]     # 게이트 = 가장 낮은 층 평단 (v2.2.6)
    try:
        send_fill_alerts(s, api, note, cfg, m, mark, items, d, sim)        # v2.2.6 체결 알림 (장중에도). 실패해도 매도 확인은 계속
    except Exception as e:
        logging.warning(f"체결 알림 중 오류 {type(e).__name__}")
    if not cands:
        return "해당 없음"                            # 보유 없고 오늘 체결된 매수도 아직 없음 (체결 조회가 늦은 것일 수 있음 → 다음 확인 때 다시)
    status = None
    if not allow_new_sells:
        # 주문 마감 시각 뒤: 장후(005) 면 새 매도를 냄 (판 15). 정규장(004) 막판·그 밖은 예전처럼 체결 반영·알림만
        try:
            status = str(api.us_market_status())
        except MeritzError as e:
            logging.warning(f"당일 매도 확인: 장운영 코드 조회 실패 {e}")
            return "알림만"
        if status != MKT_AFTER:
            return "알림만"
    try:
        px = float(api.price(s["symbol"], s["price_market"])["price"])
    except MeritzError as e:
        logging.warning(f"당일 매도 확인: 시세 조회 실패 {e}")
        return "시세 실패"
    if px < ceil2(min(cands) * (1 + pct / 100.0)):
        return "목표 아래"
    hold, sellable, exch_vid = api.holding(s["symbol"])
    if hold != q:
        _warn_once(cfg, mark, m, "hold", note, f"오늘 체결 반영 뒤 예상 {q}주 ≠ 메리츠 잔고 {hold}주 — 당일 매도 확인을 보류하고 계속 확인해요 (체결 조회가 늦은 것일 수 있음)")
        return "잔고 불일치"
    plan = TW.make_plan(s, sim, q, round(pr, 4), px, 0.0, 0.0, sellable)       # 환율 0 → 매수 계산 없이 매도 규칙만
    info = plan["info"]
    if not info.get("profit_reached"):
        return "목표 아래"                                                   # 오늘 체결로 평단이 올라 목표가 더 높아진 경우
    # 층당 하루 1건: 오늘 이미 매도 주문(접수·시도)이 있는 층은 건너뜀.
    used = {int(x["floor_id"]) for x in (list(m["orders"]) + list(m.get("attempts") or []) + list(m.get("sell_attempts") or []))
            if isinstance(x, dict) and x.get("kind", "sell") == "sell" and x.get("floor_id") is not None and (x.get("side") in (None, "SELL"))}
    # v2.2.17: 예전 하루 1건 표시 m["sell_attempt"] (이 ZIP 코드에는 쓰는 곳이 없음, 읽기만: 여기·tg_menu.py 표시). 층 번호(floor_id)가 있으면 그 층을 오늘 판 층으로, 없으면 층을 모르는 1건으로 셈
    # (예전엔 이 표시가 있으면 오늘 새 매도를 전부 막았음 = N_sell 1 과 같음). 표시 안의 필드 이름은 근거 파일에 없어 floor_id 가 있는지는 미확인 → 없으면 1건으로 셈
    anon_sold = 0
    if m.get("sell_attempt"):
        try:
            used.add(int(m["sell_attempt"]["floor_id"]))
        except (TypeError, ValueError, KeyError, IndexError):
            anon_sold = 1
    # v2.2.17 (풀이님 요청): 하루에 최대 N_sell 층까지 판다 (설정 tower_max_sell_layers_per_day, 기본 1). 같은 확인에서 여러 층이 목표에 닿으면 번호가 큰 층(맨 위 층)부터 오늘 남은 횟수(N_sell − 오늘 이미 판 층 수)까지 팔고 나머지는 알림만 (층마다 하루 한 번).
    # 오늘 이미 N_sell F를 팔았으면 그 뒤에 새로 닿은 F는 팔지 않고 알림만 (v2.2.12 '첫 매도 뒤 2차는 알림만' → 횟수 규칙). N_sell 보다 적게 팔았으면 나중에 새로 닿은 F는 남은 횟수 안에서 판다. 연속 매도 금지는 plan 이 F별로 그대로 걸러 줌.
    n_sell = TW.sell_layers(s)
    sold_n = len(used) + anon_sold
    left_n = max(0, n_sell - sold_n)
    merged_today = TW.merged_floor_ids(sim, [x.get("no") for x in m["orders"] if isinstance(x, dict) and x.get("side") in (None, "SELL")])      # v2.16.0 판 43 Q1: 오늘 판 F의 잔여분을 받은 F도 오늘은 안 팜
    reached_now = [o for o in plan["orders"] if o.get("kind") == "sell" and o.get("reached") and int(o["floor_id"]) not in used | merged_today]
    sells, held_back = pick_sells(reached_now, left_n)
    nos = SN.sniper_numbers(sim)      # 표시용 F 번호 {층 id: 스나이퍼 번호} (sim = 오늘 체결 반영 뒤 상태)
    if left_n <= 0 and held_back:
        rows = {int(r["id"]): r for r in info.get("sells") or []}
        for o in held_back:
            fid = int(o["floor_id"])
            r = rows.get(fid, {})
            _warn_once(cfg, mark, m, f"second_sell_{fid}", note,
                       (f"2차 매도 조건이 생겼어요 (알림만 · 주문은 안 냈어요 — 오늘 첫 매도 뒤라 연속 매도는 안 해요)\n" if n_sell == 1 else
                        f"2차 매도 조건이 생겼어요 (알림만 · 주문은 안 냈어요 — 오늘 이미 {sold_n}F 매도해서 하루 최대 {n_sell}F에 닿았어요)\n")
                       + f"· {nos.get(fid, fid)}F 평단 ${float(o.get('floor_avg') or 0):.2f} +{pct:g}% → 매도 목표 ${float(o['price']):.2f} · 현재가 ${px:.2f}에서 닿음\n"
                       f"· 매도하게 될 수량 {int(o['qty'])}주 (보유 {int(r.get('qty') or 0)}주)\n"
                       f"· 오늘 이미 매도한 F: {', '.join(str(nos.get(i, i)) + 'F' for i in sorted(used)) or '확인 못 함'}\n"
                       f"오늘은 이 F 주문을 내지 않았어요. 내일 아침 계획에서 다시 판단해요.")
        return "2차 매도 조건 알림"
    if not sells and any(o.get("kind") == "sell" and o.get("reached") for o in plan["orders"]):
        return "오늘 매도 주문 있음"
    if not sells:
        why = "; ".join(n for n in plan["notes"] if "매도" in n) or "매도 조건 미충족"
        _warn_once(cfg, mark, m, "block", note, f"평가 이익 +{pct:g}% 에 닿았지만 매도 안 함: {why}")
        return "매도 보류"
    exch = str(s.get("exch_id") or exch_vid or "")
    if not exch:
        _warn_once(cfg, mark, m, "exch", note, "거래소 번호를 알 수 없어 당일 매도를 못 냄 — 설정에 거래소 번호를 넣어 주세요")
        return "거래소"
    # v2.0.5 → v2.2.12 판 15: 정규장("004")과 장후("005")에 매도를 내고, 프리마켓("003")·휴장 등 그 밖의 상태는 장 닫힘으로 건너뜀. 005 에 메리츠가 지정가 매도를 접수·체결하는지는 공식 openapi.json 에 없음(주문 API 에 연장 시간 구분 필드 없음) → 미확인(거절되면 아래에서 메시지로 알림)
    # v2.2.12 판 15: 장후("005")에도 매도를 냄. 메리츠가 장후 주문을 받아줄지는 확인 안 됨 — 거절되면 아래에서 메시지로 알리고 그 층은 오늘 다시 안 냄 (장부·층은 체결 반영 때만 바뀜)
    if status is None:
        status = str(api.us_market_status())
    if status not in (MKT_REGULAR, MKT_AFTER):     # 프리마켓(003)·휴장 등은 안 냄
        return "장 닫힘"
    after_hours = status == MKT_AFTER
    if foreign_open_sells(api.open_orders_today(s["symbol"]), m, rows):
        _warn_once(cfg, mark, m, "open_sell", note, "이 계좌에 SOXL 매도 미체결 주문이 이미 있어 당일 매도를 안 냄 (수동 확인)")
        return "매도 미체결 있음"
    results, errs_all, placed = [], [], []
    rows_by_id = {int(r["id"]): r for r in info.get("sells") or []}
    for sel in sells:                                                          # v2.2.17: 하루 최대 N_sell F (기본 1 — v2.2.13 하루 한 F): sells 는 남은 횟수 이하
        o = dict(sel, desc="당일 매도 · " + sel.get("desc", ""))
        o.pop("reached", None)
        att = {{"at": now_et().isoformat(), "qty": o["qty"], "price": o["price"], "kind": "sell", "floor_id": o.get("floor_id"),
               "status": "접수 시도 (이 기록이 있으면 오늘 이 F는 다시 매도 주문을 내지 않음)"}}
        if after_hours:
            att["market_status"] = status                 # 장후 주문 표시 (거절돼도 오늘 이 층은 다시 안 냄)
        m.setdefault("sell_attempts", []).append(att)
        cfg._save_json(mark, m)                          # 주문 전에 먼저 기록 → 응답이 불확실해도 중복 주문 없음
        errs = []
        res = send_order(s, api, cfg, mark, m, o, exch, errs, intraday=True)     # v2.0.4: 응답을 못 받으면 attempts 에 남겨 마감 뒤 자동으로 찾음
        err = (errs[0] if errs else None)
        if res == "ok":
            att.update(status="접수 완료", no=m["orders"][-1]["no"])
        else:
            att["status"] = ("증권사가 거절 — 오늘 이 F는 다시 안 냄: " if res == "rejected" else "응답 못 받음 — 오늘 이 F는 다시 안 냄, 체결 내역에서 자동으로 찾음: ") + (err or "")[:100]
        cfg._save_json(mark, m)
        results.append(res)
        placed.append(o)
        if err:
            errs_all.append(err)
    placed_ids = [int(o["floor_id"]) for o in placed]
    for o in held_back:                                  # v2.2.13: 같이 닿았지만 팔지 않은 F는 알림만 (F마다 하루 한 번). v2.2.17: 하루 최대 N_sell F
        fid = int(o["floor_id"])
        _warn_once(cfg, mark, m, f"second_sell_{fid}", note,
                   (f"같은 확인에서 여러 F가 목표에 닿았어요 (알림만 · 주문은 안 냈어요 — 하루에 한 F만 팔고, 맨 위 F {nos.get(placed_ids[0], placed_ids[0])}F만 매도해요)\n" if n_sell == 1 else
                    f"같은 확인에서 여러 F가 목표에 닿았어요 (알림만 · 주문은 안 냈어요 — 하루에 최대 {n_sell}F까지 팔고, 번호가 큰 F부터 {', '.join(str(nos.get(i, i)) + 'F' for i in placed_ids)}만 매도해요)\n")
                   + f"· {nos.get(fid, fid)}F 평단 ${float(o.get('floor_avg') or 0):.2f} +{pct:g}% → 매도 목표 ${float(o['price']):.2f} · 현재가 ${px:.2f}에서 닿음\n"
                   f"· 매도하게 될 수량 {int(o['qty'])}주 (보유 {int(rows_by_id.get(fid, {}).get('qty') or 0)}주)\n"
                   f"· 오늘 이미 매도한 F: {', '.join(str(nos.get(i, i)) + 'F' for i in sorted(set(placed_ids) | used))}\n"
                   f"오늘은 이 F 주문을 내지 않았어요. 내일 아침 계획에서 다시 판단해요.")
    ok_n = sum(1 for r in results if r == "ok")
    head = (f"{'장후(' + status + ') ' if after_hours else ''}당일 매도 {'접수' if ok_n == len(results) else ('실패' if ok_n == 0 and all(r == 'rejected' for r in results) else '일부 접수 · 실패·응답 없음 있음')}\n"
            f"오늘 체결 반영 F별 평단 기준 · 현재가 ${px:.2f}\n")
    note.send(head + fmt_orders(placed) + ("\n" + "\n".join(errs_all) + ("\n장후 주문을 메리츠가 받아주는지는 확인된 적이 없어요(미확인). 거절·응답 없음이면 이 메시지로 알려요 — 장부·F 상태는 체결이 확인될 때만 바뀌어서 그대로예요." if after_hours else "") + "\n오늘은 이 F 매도를 다시 시도하지 않아요. 내일 아침 계획에서 다시 판단해요." if errs_all else ""))
    if ok_n:
        return "매도 접수"
    return "매도 실패" if all(r == "rejected" for r in results) else "매도 응답 유실"


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
            m.setdefault("orders", []).append(dict(o, no=str(r["no"]).strip(), placed_ts=round(time.time(), 1), **({"intraday": True} if intraday else {})))
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


def reached_line(plan, price):
    """판 23 수정1: 목표 도달 안내 — F마다 '완성 F = 탑 매도 +% / 미완성 F = 스나이퍼 +%' 와 그 F 목표가를 각각 적음 (예전엔 스나이퍼 목표가를 '+10% 목표'로 적었음)"""
    rs = [r for r in plan["info"].get("sells") or [] if r.get("reached")]
    return "".join(f"{r['no']}F({'완성·탑 매도' if r.get('complete') else '스나이퍼'}) 평단 +{r['pct']:g}% 도달 (현재가 ${price:.2f} ≥ 목표 ${r['target']:.2f})\n"
                   for r in sorted(rs, key=lambda r: r["no"]))


def held_back_lines(plan, s, price):
    """v2.2.17 판 20 수정1: 아침 계획에서 N_sell 때문에 주문에서 뺀 F의 알림 글자 (없으면 빈 글자). 장중 held_back 알림과 같은 내용 — F마다 평단·목표가·현재가·매도하게 될 수량"""
    hb = plan["info"].get("held_back") or []
    if not hb:
        return ""
    n = int(plan["info"].get("held_back_n_sell") or 1)
    placed = plan["info"].get("held_back_placed") or []
    nos = {int(r["id"]): r["no"] for r in plan["info"].get("sells") or [] if "no" in r}
    if not nos:      # 탑쌓기 계획(make_plan sells 에는 no 없음) — tower floors 평단으로 순위 계산
        _fl = [f for f in (plan["info"].get("tower") or {}).get("floors") or [] if int(f.get("qty") or 0) > 0]
        nos = {int(f["id"]): n + 1 for n, f in enumerate(sorted(_fl, key=lambda f: (float(f.get("avg") or 0), -int(f.get("id") or 0))))}
    pct = float(s.get("sell_profit_pct") or 0)
    out = f"\n같은 확인에서 여러 F가 목표에 닿았어요 (알림만 · 주문은 안 냈어요 — 하루 최대 {n}F까지만 팔아요" + (f", 번호가 큰 F부터 {', '.join(str(nos.get(int(i), i)) + 'F' for i in placed)}만 매도해요)" if placed else ")")
    for h in hb:
        out += (f"\n· {nos.get(int(h['floor_id']), h['floor_id'])}F 평단 ${h['floor_avg']:.2f} +{pct:g}% → 매도 목표 ${h['target']:.2f} · 현재가 ${float(price):.2f}에서 닿음"
                f"\n  매도하게 될 수량 {h['qty']}주 (보유 {h['hold_qty']}주)")
    return out + "\n오늘은 이 F 주문을 내지 않았어요. 내일 아침 계획에서 다시 판단해요."


def run_order_day(s, api, note, live):
    state = s["state_dir"]
    d = now_et().strftime("%Y-%m-%d")
    mark = os.path.join(state, "data", f"{'orders' if live else 'dry_orders'}_{d}.json")
    cfg = ConfigManager(s)
    prev = None          # v2.2.20: 같은 날 스나이퍼 → 탑쌓기로 바꾼 경우 — 스나이퍼가 만든 기록(sniper_day)에 탑쌓기 주문을 이어 냄 (그 밖의 기록이 있으면 예전처럼 '이미 함')
    if os.path.exists(mark):
        pv = cfg._load_json(mark, None)
        if live and isinstance(pv, dict) and pv.get("sniper_day") and not pv.get("tower_ordered") and not pv.get("skipped") and not pv.get("synced", True) and not sniper_on(s):
            prev = pv
        else:
            return "이미 함"
    if live and _retry_wait(d):
        return "대기"

    def skip_mark(payload):
        if prev is None:
            cfg._save_json(mark, payload)
        else:
            prev["tower_ordered"] = True
            prev["tower_skipped"] = payload.get("skipped")
            cfg._save_json(mark, prev)
    if live:
        bad = gate_problems(s, cfg, live=True)
        if bad and all(b.startswith(CHAT_BAD) for b in bad):      # chat_id 만 문제면 하루 기록을 안 써서, 고치면 같은 날 5분 안에 다시 시도 (알림은 chat_id 가 없어 로그로만 남음)
            _retry_later(note, d, "chat", "오늘 주문 안 함\n" + "\n".join("- " + b for b in bad) + "\n(고치면 오늘도 5분 안에 다시 시도해요)")
            return "chat_id"
        if bad:
            note.send("오늘 주문 안 함\n" + "\n".join("- " + b for b in bad))
            skip_mark({"skipped": bad})
            return "차단"
    status = api.us_market_status()
    if status != "004":
        skip_mark({"skipped": f"장운영 코드 {status} (휴장 또는 정규장 아님)"})
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
            note.send("정지: " + warn[-1] + "\n확인한 뒤 텔레그램 기타 → 정지 해제")
            skip_mark({"skipped": warn})
            return "정지"
    if live and api.open_orders_today(s["symbol"]):
        note.send("이 계좌에 SOXL 미체결 주문이 이미 있음 — 오늘 주문 안 함 (수동 확인)" + (" (스나이퍼 주문 포함)" if prev is not None else ""))
        skip_mark({"skipped": "기존 미체결 있음"})
        return "미체결"
    if live and not exch:      # 보유 0주면 잔고에서 거래소 번호를 못 얻음 — 표시 파일을 안 써서, 설정을 고치면 같은 날 다시 시도
        _retry_later(note, d, "exch", "거래소 번호를 알 수 없음 — 설정에 거래소 번호를 넣어 주세요 (고치면 오늘도 5분 안에 다시 시도해요)")
        return "거래소"
    price, prev_close, fx = market_inputs(s, api)
    open_px = ensure_open_price(s, cfg, d, live, now_et(), price, status)      # v2.2.14 판 17: 저장된 시초가(없으면 지금 확인한 현재가로 정함 — 정규장 09:30 ET 이후)
    if live and not (fx and fx > 0):      # 적용환율 일시 오류로 오늘 매수가 통째로 빠지지 않게 (market_inputs 는 실패를 0.0 으로 삼킴)
        _retry_later(note, d, "fx", "적용환율을 못 읽어 오늘 매수 계획을 못 세웠어요 — 5분 뒤 다시 시도해요")
        return "환율 실패"
    cash = api.usd_cash()
    tower_notes = []
    if live:      # v2.2.0 매일 동기화: 층 상태를 장부(실제 보유분)에 맞춤. 상태 파일이 없으면 지금 보유분을 1F로 만들어 저장
        tst, had = tower_state_for(cfg, qty, float(pos["principal"]), s)
        if prev is not None:      # v2.2.20: 스나이퍼 주문이 이미 층 번호(floor_id)를 달고 있어서 같은 날 층을 다시 정리(번호 바뀜)하지 않음 — 오늘 스나이퍼 시작 때 이미 맞춤
            tower_notes = []
        else:
            tst, tower_notes = TW.reconcile(tst, qty, float(pos["principal"]), TW.params(s)[2], s) if had else (tst, [f"탑쌓기 시작: 현재 보유분 {qty}주 · 평단 ${avg:.2f} 를 1F로 만듦"])
            cfg._save_json(TOWER_FILE, tst)
    sell_q = sellable if live else qty
    plan = build_plan(s, cfg, price, fx, cash, qty, float(pos["principal"]), sell_q, open_px=open_px)
    fxres = auto_fx(s, api, cfg, plan, live, d, fx_now=now_et())      # 주문 시간 대비용 환전도 실시간 환전 시간일 때만 (v2.0.8)
    if live and s.get("auto_fx_enabled"):
        if fxres and fxres.get("done"):      # 환전 신청 직후엔 예수금 반영이 늦을 수 있어 잠깐 기다림 (환전은 다시 신청하지 않음)
            need = float(plan["info"].get("need_usd") or 0)
            for _ in range(FX_WAIT_TRIES):
                if api.usd_cash() >= need:
                    break
                time.sleep(FX_WAIT_SEC)
        cash = api.usd_cash()          # 환전 뒤(또는 안 한 뒤) 실제 예수금으로 다시 계획 — 모자라면 그만큼 매수가 줄어듦
        plan = build_plan(s, cfg, price, fx, cash, qty, float(pos["principal"]), sell_q, ignore_auto_fx=True, open_px=open_px)
    try:
        run_one_share_notice(s, note, plan, d, live)       # v2.2.9 audit-fix 7-4: 1주 남음 메시지 (실패해도 주문 흐름 계속)
    except Exception as e:
        logging.warning(f"1주 남음 알림 실패: {type(e).__name__}")
    try:
        run_new_floor_notice(s, note, plan, d, live)       # v2.2.9 새 F 규칙: 새 F를 못 만들면 풀이님께 물어봄 (실패해도 주문 흐름 계속)
    except Exception as e:
        logging.warning(f"새 F 못 만듦 알림 실패: {type(e).__name__}")
    orders, notes = plan["orders"], plan["notes"] + tower_notes
    errors, recovered = [], 0
    m = {"date": d, "prev_close": prev_close, "price": price, "open_price": open_px, "fx": fx, "auto_fx": fxres,
         "qty": qty, "avg": avg, "cash": round(cash, 2), "orders": [] if live else orders, "attempts": [],
         "errors": errors, "synced": False if live else True, "sell_deferred": bool(plan["info"].get("sell_deferred"))}
    held_back = plan["info"].get("held_back") or []
    if held_back:       # 아침에 알린 층은 장중 확인이 같은 알림을 또 보내지 않게 (장중 알림 키와 같은 이름)
        m["intraday_warn"] = [f"second_sell_{h['floor_id']}" for h in held_back]
    if prev is not None:                             # v2.2.20: 스나이퍼 기록에 이어 씀 — 이미 낸 주문·시도·알림 표시를 그대로 가져오고 탑쌓기 주문을 더함
        for k in ("orders", "attempts", "sell_attempts", "sniper_rejected"):
            if k in prev:
                m[k] = prev[k]
        m["intraday_warn"] = list(prev.get("intraday_warn") or []) + [x for x in m.get("intraday_warn", []) if x not in (prev.get("intraday_warn") or [])]
        m["sniper_day"], m["tower_ordered"] = True, True
        errors = m["errors"]
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
              + (reached_line(plan, price) if reached else "")
              + fx_lines(fxres)
              + fmt_orders(placed)
              + held_back_lines(plan, s, price)
              + ("\n" + "\n".join("· " + n for n in notes + warn) if notes or warn else "")
              + ("\n실패\n" + "\n".join("- " + e for e in errors) if errors else ""))
    return "완료"


# ---------------------------------------------------------------- v2.2.20 판 22 스나이퍼 모드 (장중 틱)
_SNIPER = {"last": 0.0, "last_buy": 0.0, "err_day": ""}


class SniperApi:
    """v2.13.0 판 40 할 일 1: 1.5초 틱용 조회 캐시. 시세(price)·1분봉은 매번 새로 읽고, 천천히 바뀌는 조회(체결·잔고·미체결·예수금)는 book_sec(기본 10초)동안 다시 씀 · 장운영 코드는 30초.
    주문(order)·환전을 낸 직후엔 캐시를 모두 버려 바로 다시 조회 (낸 주문이 체결 조회에 안 보이는 사이 중복 주문이 나가지 않게 — 주문 기록(orders_<날짜>.json)이 먼저 막고, 이건 두 번째 방어).
    raw = 원래 api (캐시 없이 지금 값이 꼭 필요한 곳 — 매도가능수량 대기 — 에서 씀)"""
    SLOW = ("holding", "open_orders_today", "fills_rows", "usd_cash")
    STATUS_SEC = 30.0
    DROP = ("order", "fx_exchange")

    def __init__(self, raw, book_sec=10.0, clock=time.monotonic):
        self.raw = raw
        self.book_sec = max(1.0, float(book_sec or 10.0))
        self._clock = clock
        self._c = {}
        self.calls = 0                     # 진짜로 나간 조회 수 (VERIFY.md 호출 수 측정용)

    def __getattr__(self, name):
        fn = getattr(self.raw, name)
        if not callable(fn):
            return fn
        if name in self.SLOW or name == "us_market_status":
            ttl = self.STATUS_SEC if name == "us_market_status" else self.book_sec

            def cached(*a, **k):
                key = (name, repr(a), repr(sorted(k.items())))
                now = self._clock()
                hit = self._c.get(key)
                if hit is not None and now - hit[0] < ttl:
                    return hit[1]
                self.calls += 1
                v = fn(*a, **k)
                self._c[key] = (self._clock(), v)
                return v
            return cached
        if name in self.DROP:
            def dropping(*a, **k):
                try:
                    return fn(*a, **k)
                finally:
                    self._c.clear()
            return dropping

        def passthru(*a, **k):
            self.calls += 1
            return fn(*a, **k)
        return passthru


GUARD_RECHECK_SEC = 60            # 판 40: GUARD30 에 막힌 뒤 다시 보는 간격 (원작 60초 입금 감지)
ASSASSIN_POLL_SEC = 30.0      # 판 40: 1분 봉 모으기·모의 지표 간격 (스나이퍼 틱이 1.5초여도 30초 — 예전 동작. 판 41: 옛 이름 BARBELL_TICK_SEC)
QUIET_TICK = ("꺼짐", "해당 없음", "차단", "장 닫힘", "매도 창 밖", "휴장", "장 전", "정지", "미체결", "거래소", "chat_id")      # 이 결과면 이번 30초 동안은 더 안 돌림 (할 일이 없는 상태)


def sniper_tick_window(s, n):
    """v2.13.0 판 40 할 일 3: 스나이퍼 틱을 돌릴 때인가 — 원작 매도 창 (평일, 04:00~04:06 ET 7분만 닫힘, 주말 닫힘) 이 열려 있고, 하루 기록 마감(sync_time_et) 전이거나 오늘 기록이 이미 있을 때.
    예전엔 평일·마감 시각(20:00) 전만 돌려서 마감 시각이 곧 틱 끝이었음 → 이제 틱 끝은 창이 정하고 마감 시각은 '하루 기록을 닫는 시각'일 뿐 (마감 시각을 늦추면 그만큼 틱이 이어짐). 기록이 없는 마감 뒤에는 안 돌림 (장 닫힘 알림이 매일 밤 나가지 않게)"""
    if not SN.AD.sell_window_open(n):
        return False
    if n.time() < _hm(s.get("sync_time_et"), datetime.time(20, 0)):
        return True
    return os.path.isfile(os.path.join(s["state_dir"], "data", f"orders_{n.strftime('%Y-%m-%d')}.json"))


def night_tick_ok(s, m, n):
    """v2.15.0 판 41 할 일 3: 하루 기록이 마감(synced, 기본 20:00 ET)된 뒤에도 틱을 계속 돌려도 되는가 — 원작 매도 창이 열려 있고(일요일 18:00 ~ 금요일 20:00 ET, 04:00~04:06 제외),
    오늘 기록이 마감 시각 뒤에 '마감됨'이 된 스나이퍼 기록일 때. 마감은 '하루 기록을 닫는 일'일 뿐 틱 끝이 아님 (틱 끝은 매도 창이 정함).
    반영 안 된 밤 체결은 다음 날 첫 확인(run_late_fills)이 주문번호별 증분만 장부·층에 넣음. 매수는 원래 SN.buy_ok(04:07~16:00 ET)가 막아서 밤에 매수는 안 나감 (판 41 범위 밖)"""
    return bool(isinstance(m, dict) and m.get("sniper_day") and m.get("synced") is True and isinstance(m.get("orders"), list)
                and n.time() >= _hm(s.get("sync_time_et"), datetime.time(20, 0)) and SN.AD.sell_window_open(n))


def menu_poll():
    """1.5초 틱 사이 텔레그램 메뉴를 기다림 없이 한 번 확인 (같은 스레드). 메뉴가 안 되면 조용히 건너뜀"""
    try:
        if _MENU["bot"] is None:
            _MENU["bot"] = tg_menu.MenuBot(sys.modules[__name__])
        _MENU["bot"].idle(load_settings(), time.time(), once=True)
    except Exception as e:
        logging.warning(f"텔레그램 메뉴 처리 오류: {type(e).__name__} {getattr(e, 'code', '')}".strip())


def sniper_fast_wait(total, s, api, note, sleep=time.sleep, mono=time.monotonic):
    """loop() 의 idle(30) 자리 (스나이퍼 켜짐일 때): total 초 동안 틱 간격(SN.tick_gap)마다 run_sniper_tick 을 돌림. 틱 사이엔 sleep + 3초에 한 번 텔레그램 메뉴 확인.
    틱 결과가 QUIET_TICK(할 일 없음)이거나 창이 닫히면 남은 시간은 예전처럼 idle 로 기다림. 간격이 total 이상이면(30초로 되돌린 설정) 곧바로 idle(total)"""
    gap = SN.tick_gap(s)
    t_end = mono() + float(total)
    if gap >= total:
        idle(total)
        return 0
    capi = SniperApi(api, s.get("sniper_book_sec") or 10)
    ticks, last_menu = 0, 0.0
    while mono() < t_end:
        sleep(min(gap, max(0.0, t_end - mono())))
        if mono() - last_menu >= 3.0:
            last_menu = mono()
            menu_poll()
        n = now_et()
        if not sniper_tick_window(s, n):
            break
        try:
            r = run_sniper_tick(s, capi, note)
        except Exception as e:
            logging.exception(f"스나이퍼 확인 중 오류: {type(e).__name__}")
            if _SNIPER["err_day"] != n.strftime("%Y-%m-%d"):
                _SNIPER["err_day"] = n.strftime("%Y-%m-%d")
                note.send(f"스나이퍼 확인 중 오류가 났어요 ({type(e).__name__}) — 이미 낸 주문은 그대로예요. 서버 로그를 확인해 주세요.")
            break
        ticks += 1
        if r in QUIET_TICK:
            break
    left = t_end - mono()
    if left > 0:
        idle(left)
    return ticks
SNIPER_STALE_BUY_SEC = 600           # 낸 매수가 이 시간(초)이 지나도 다 체결 안 되면 알림 (60초 취소가 실패했을 때만 남는 경우 — 판 42에서 취소 API 연결됨)
SNIPER_BUY_CANCEL_SEC = 60            # 판 42: 미체결 매수 주문은 이 시간(초)이 지나면 취소함 (원작 BUY_ORDER_MAX_WAIT_SEC=60.0과 같게)


def sniper_on(s):
    """v2.3.0: 모드 선택이 없어 항상 하이브리드 루프 (옛 이름 유지 — 장중 틱이 항상 돈다)"""
    return True


def buy_layer_limit_hit(s, m, rows, open_rows, order):
    """판 23 수정1 (풀이님 결정): 그날 매수 주문이 나간 F 수가 tower_max_buy_layers_per_day(설정 그대로, 기본 1) 에 닿았는데 오늘 아직 안 산 새 F에 사려 하면 → 알림 글자, 아니면 None.
    센 대상 = 오늘 기록의 매수 주문 중 살아 있는 것 (미체결 조회에 있거나 체결 있음·방금 낸 주문·응답 못 받은 시도) — 거절·앱에서 취소한 주문은 안 셈. 같은 F에 더 사는 건(남은 시드 채우기) F 수를 안 늘리므로 계속 가능"""
    if not order or order.get("floor_id") is None:
        return None
    n_max = TW.buy_layers(s)
    bought = {int(o["floor_id"]) for o in our_live_orders(m, rows, open_rows, "BUY") if o.get("floor_id") is not None}
    if len(bought) >= n_max and int(order["floor_id"]) not in bought:
        return (f"스나이퍼 매수 신호가 났지만 오늘 매수한 층이 하루 매수 층 수 {n_max}개에 닿아 더 안 샀어요 "
                f"(오늘 매수 층: {', '.join(str(x) + '층' for x in sorted(bought))} · 안 산 {int(order['floor_id'])}층 {order['qty']}주 @ ${float(order['price']):.2f})")
    return None


def open_rows_or_none(api, s):
    """미체결 조회(open_orders_today) 결과 — 조회 실패면 None (그때는 주문 기록만으로 판단하는 예전 방식으로 안전하게 되돌림)"""
    try:
        return [r for r in api.open_orders_today(s["symbol"]) if isinstance(r, dict)]
    except Exception as e:
        logging.warning(f"미체결 조회 실패 {type(e).__name__} — 주문 기록으로 판단")
        return None


OPEN_LIST_GRACE_SEC = 180          # 방금 낸 주문은 미체결 조회에 늦게 보일 수 있어 이 시간 동안은 살아 있다고 봄 (취소로 오해해 같은 매도를 또 내는 일 방지)


def _just_placed(o):
    try:
        return time.time() - float(o.get("placed_ts") or 0) < OPEN_LIST_GRACE_SEC
    except (TypeError, ValueError):
        return False


def _open_nos(open_rows, side):
    """미체결 행 중 side(BUY/SELL) 주문번호 집합과 번호 없는 행 수 → (번호 집합, 번호 없는 행 수)"""
    code = "1" if side == "SELL" else "2"
    rs = [r for r in open_rows if str(r.get("seln_byov_clcd")) == code]
    nos = {str(r.get("oder_no") or "").strip() for r in rs} - {""}
    return nos, sum(1 for r in rs if not str(r.get("oder_no") or "").strip())


def our_live_orders(m, rows, open_rows, side):
    """판 23 수정1 (B3): 우리가 낸 side 주문 중 '살아 있는' 것 = 미체결 조회에 남아 있거나 체결이 있는 주문 (앱에서 취소한 주문은 미체결도 체결도 아니라 빠짐).
    미체결 행에 주문번호가 있으면 번호로 맞추고, 번호가 없으면 미체결 행 수만큼만 (주문 기록에서 아직 다 안 체결된 것 중) 살아 있다고 봄. open_rows=None(조회 실패)이면 예전처럼 기록만으로 판단.
    응답 못 받은 시도(attempts)는 번호가 없어 체결 내역에서 찾기 전까지 살아 있다고 봄 (중복 주문 방지가 우선)"""
    orders = [o for o in m.get("orders") or [] if isinstance(o, dict) and o.get("side") == side and o.get("no")]
    filled = lambda o: int((rows.get(str(o["no"])) or {}).get("qty", 0))
    if open_rows is None:
        live = list(orders)
    else:
        nos, anon = _open_nos(open_rows, side)
        live = []
        for o in orders:
            if filled(o) >= 1 or str(o["no"]) in nos or _just_placed(o):
                live.append(o)
            elif anon > 0 and filled(o) < int(o.get("qty") or 0):
                live.append(o)
                anon -= 1
    return live + [a for a in m.get("attempts") or [] if isinstance(a, dict) and a.get("side") == side]


def sold_floor_ids_today(m, rows=None, open_rows=None):
    """오늘 이 층에 매도가 '살아 있는'(미체결이거나 체결 있음 · 응답 못 받음) 층 id 집합 — 한 층에 두 매도가 같은 날 겹치지 않게 (v2.3.0). 판 23 수정1 B3: 앱에서 취소해 미체결도 체결도 없는 주문은 '이미 팔았다'로 안 셈.
    rows·open_rows 를 안 주면 (예전 호출) 주문 기록만 봄"""
    src = our_live_orders(m, rows or {}, open_rows, "SELL") if rows is not None else list(m.get("orders") or []) + list(m.get("attempts") or [])
    out = set()
    for o in src:
        if isinstance(o, dict) and o.get("side") == "SELL" and o.get("floor_id") is not None and o.get("box_id") is None:      # v2.6.0: 버킷 주문은 sold_box_keys_today 가 봄
            try:
                out.add(int(o["floor_id"]))
            except (TypeError, ValueError):
                pass
    return out


def sold_box_keys_today(m, rows=None, open_rows=None):
    """v2.6.0 오늘 매도 주문이 '살아 있는' 버킷 키 {(층 id, 버킷 id)} — 같은 버킷에 매도 둘이 겹치지 않게 (다른 버킷은 같은 날에도 팔 수 있음). 취소된 주문은 sold_floor_ids_today 와 같은 규칙으로 뺌"""
    src = our_live_orders(m, rows or {}, open_rows, "SELL") if rows is not None else list(m.get("orders") or []) + list(m.get("attempts") or [])
    out = set()
    for o in src:
        if isinstance(o, dict) and o.get("side") == "SELL" and o.get("floor_id") is not None and o.get("box_id") is not None:
            try:
                out.add((int(o["floor_id"]), int(o["box_id"])))
            except (TypeError, ValueError):
                pass
    return out


def tower_sold_count_today(m, rows=None, open_rows=None):
    src = our_live_orders(m, rows or {}, open_rows, "SELL") if rows is not None else list(m.get("orders") or []) + list(m.get("attempts") or [])
    return len({int(o["floor_id"]) for o in src if isinstance(o, dict) and o.get("side") == "SELL" and o.get("mode") == "tower" and o.get("floor_id") is not None})


def sniper_open_orders(m, rows, side, open_rows=None):
    """우리가 낸 side 주문 중 아직 다 체결 안 된 것 + 응답 못 받은 시도(attempts). 판 42부터 미체결 매수는 60초 뒤 취소됨 (원작과 같게). 취소 실패 시에만 장 끝까지 남음.
    판 23 수정1 B3: open_rows(미체결 조회)를 주면 거기 없는 주문(앱에서 취소)은 빠짐 — 취소한 주문 때문에 그날 매수·매도가 잠기지 않음"""
    if open_rows is None:
        out = [o for o in m.get("orders") or [] if isinstance(o, dict) and o.get("side") == side and o.get("no")
               and int((rows.get(str(o["no"])) or {}).get("qty", 0)) < int(o.get("qty") or 0)]
        return out + [a for a in m.get("attempts") or [] if isinstance(a, dict) and a.get("side") == side]
    nos, anon = _open_nos(open_rows, side)
    out = []
    for o in m.get("orders") or []:
        if not (isinstance(o, dict) and o.get("side") == side and o.get("no")):
            continue
        if int((rows.get(str(o["no"])) or {}).get("qty", 0)) >= int(o.get("qty") or 0):
            continue                                            # 다 체결됨
        if str(o["no"]) in nos or _just_placed(o):
            out.append(o)
        elif anon > 0:                                          # 미체결 행에 번호가 없으면 행 수만큼만 우리 주문으로 봄
            out.append(o)
            anon -= 1
    return out + [a for a in m.get("attempts") or [] if isinstance(a, dict) and a.get("side") == side]


def sniper_preflight(s, api, note, cfg, d, mark, n):
    """오늘 첫 틱: 주문 전 확인을 하고 하루 기록(orders_<날짜>.json)을 만듦 (탑쌓기 run_order_day 와 같은 확인: 게이트·장운영·잔고=장부·기존 미체결·층 상태 맞춤) → (기록 또는 None, 상태 글자).
    못 만드는 이유가 일시적이면 기록을 안 쓰고 다음 틱에 다시, 그날 못 하는 이유면 skipped 기록"""
    if _retry_wait(d):
        return None, "대기"
    bad = gate_problems(s, cfg, live=True)
    if bad and all(b.startswith(CHAT_BAD) for b in bad):
        _retry_later(note, d, "chat", "오늘 스나이퍼 주문 안 함\n" + "\n".join("- " + b for b in bad) + "\n(고치면 오늘도 5분 안에 다시 시도해요)")
        return None, "chat_id"
    if bad:
        note.send("오늘 주문 안 함\n" + "\n".join("- " + b for b in bad))
        cfg._save_json(mark, {"skipped": bad, "sniper_day": True})
        return None, "차단"
    status = str(api.us_market_status())
    if status not in SN.SELL_STATUS:                       # 판 38: 프리마켓(003)에도 하루 기록을 만듦 (예전엔 정규장·장후만)
        if n.weekday() >= 5:                               # 판 40: 일요일 저녁 틱(원작 매도 창 18:00~) — 장운영 코드가 열림이 아니면 기록·알림 없이 다음 틱에 다시 (주말마다 '정규장 아님' 알림이 나가지 않게)
            return None, "장 전"
        if n.time() >= _hm(s["order_time_et"], datetime.time(10, 5)):
            cfg._save_json(mark, {"skipped": f"장운영 코드 {status} (휴장 또는 정규장 아님)", "sniper_day": True})
            note.send(f"오늘은 정규장 아님 (코드 {status}) — 스나이퍼 주문 없음")
            return None, "휴장"
        return None, "장 전"
    hold, _sellable, exch_vid = api.holding(s["symbol"])
    pos = cfg.get_position()
    qty, principal = int(pos["qty"]), float(pos["principal"])
    if hold != qty:
        why = f"잔고 {hold}주 ≠ 장부 {qty}주"
        cfg.halt(why)
        note.send("정지: " + why + "\n확인한 뒤 텔레그램 기타 → 정지 해제")
        cfg._save_json(mark, {"skipped": [why], "sniper_day": True})
        return None, "정지"
    if api.open_orders_today(s["symbol"]):
        note.send("이 계좌에 SOXL 미체결 주문이 이미 있음 — 오늘 스나이퍼 주문 안 함 (수동 확인)")
        cfg._save_json(mark, {"skipped": "기존 미체결 있음", "sniper_day": True})
        return None, "미체결"
    if not str(s.get("exch_id") or exch_vid or ""):
        _retry_later(note, d, "exch", "거래소 번호를 알 수 없음 — 설정에 거래소 번호를 넣어 주세요 (고치면 오늘도 5분 안에 다시 시도해요)")
        return None, "거래소"
    try:
        price = float(api.price(s["symbol"], s["price_market"])["price"])
    except MeritzError as e:
        if status == MKT_PRE:                              # 판 38: 프리마켓 시세 조회가 되는지는 미확인 — 안 되면 기록 없이 다음 틱에 다시 (정규장이 되면 예전과 같음)
            logging.warning(f"스나이퍼: 프리마켓 시세 조회 실패 {e}")
            return None, "장전 시세 없음"
        raise
    cash = api.usd_cash()
    tst, had = tower_state_for(cfg, qty, principal, s)
    tst, tnotes = TW.reconcile(tst, qty, principal, TW.params(s)[2], s) if had else (tst, [f"탑쌓기 시작: 현재 보유분 {qty}주를 1F로 만듦"])
    cfg._save_json(TOWER_FILE, tst)
    m = {"date": d, "prev_close": 0.0, "price": price, "open_price": 0.0, "fx": 0.0, "auto_fx": None, "qty": qty, "avg": cfg.avg_price(pos), "cash": round(cash, 2),
         "orders": [], "attempts": [], "errors": [], "synced": False, "sell_deferred": False, "sniper_day": True, "tower_ordered": False}
    cfg._save_json(mark, m)
    note.send(f"{d} 스나이퍼 모드 시작 · 보유 {qty}주 평단 ${cfg.avg_price(pos):.2f} · 현재가 ${price:.2f}" + ("\n" + "\n".join("· " + x for x in tnotes) if tnotes else ""))
    return m, "시작"


def live_fx_ok(s):
    return bool(s.get("auto_fx_enabled")) and not s.get("dry_run", True)


def intraday_fx(s, api, cfg, note, mark, m, d, n, need, cash):
    """v2.3.0 장중 자동환전 → (환전 뒤 달러 예수금, auto_fx 결과 또는 None). 필요 달러 need − 예수금 만큼(+여유%, 하루 상한 안)만 환전. 환전 신청 직후엔 예수금 반영을 잠깐 기다림. 못 한 이유는 같은 이유로 하루 한 번만 알림"""
    plan = {"info": {"shortfall_usd": round(need - cash, 2)}}
    fxres = auto_fx(s, api, cfg, plan, True, d, fx_now=n)
    if fxres is None:
        return cash, None
    if fxres.get("done"):
        for _ in range(FX_WAIT_TRIES):
            c2 = api.usd_cash()
            if c2 >= need:
                break
            time.sleep(FX_WAIT_SEC)
        cash = api.usd_cash()
        note.send(f"장중 자동환전 · 스나이퍼 매수 필요 ${need:,.0f} · 예수금 ${cash:,.0f}\n" + fx_lines(fxres).strip())
    else:
        _warn_once(cfg, mark, m, "intraday_fx_" + str(fxres.get("status"))[:20], note,
                   f"장중 자동환전 안 함 · 스나이퍼 매수에 필요 ${need:,.0f} > 예수금 ${cash:,.0f}\n" + fx_lines(fxres).strip())
    return cash, fxres


DRY_SNIPER_FILE = "data/dry_sniper_state.json"


def run_sniper_dry(s, api, note):
    """판 23 수정1 B7 모의 스나이퍼: 실거래 틱과 같은 신호·계획을 쓰되 주문(api.order)은 절대 안 냄. 시세·예수금 조회만 하고, 층 상태·장부·실거래 스나이퍼 상태 파일은 안 건드림.
    시뮬레이션 주문은 data/dry_orders_<날짜>.json 에 'sim' 으로 기록하고 [모의] 알림만 보냄 (체결은 가정하지 않아 층·장부는 그대로 → 같은 층 매도·같은 층 매수는 하루 한 번만 기록).
    눌림 깊이·RSI 용 시세 기록은 모의 전용 파일(dry_sniper_state.json)에만 저장. 시간대는 실거래와 같음 (매수 정규장·16:00 전, 매도 16:10 전)"""
    now_t = time.time()
    if now_t - _SNIPER["last"] < SN.tick_gap(s):                       # 판 40: 틱 간격 = 설정 sniper_tick_sec (기본 1.5초). 되돌리기: 30 으로
        return "대기"
    _SNIPER["last"] = now_t
    n = now_et()
    d = n.strftime("%Y-%m-%d")
    cfg = ConfigManager(s)
    mark = os.path.join(s["state_dir"], "data", f"dry_orders_{d}.json")
    m = cfg._load_json(mark, None)
    if not isinstance(m, dict) or not isinstance(m.get("orders"), list):
        m = {"date": d, "dry": True, "orders": []}
    status = str(api.us_market_status())
    if not SN.sell_ok(status, n):                                       # 판 38: 실거래와 같은 매도 창·장운영 코드
        return "장 닫힘"
    pos = cfg.get_position()
    if not pos:
        return "해당 없음"
    q, principal = int(pos["qty"]), float(pos["principal"])
    tst, _had = tower_state_for(cfg, q, principal, s)                   # 읽기만 (저장 안 함)
    sim = copy.deepcopy(tst)
    try:
        px = float(api.price(s["symbol"], s["price_market"])["price"])
    except MeritzError as e:
        if status == MKT_PRE:                                           # 판 38: 프리마켓 시세 조회가 되는지는 미확인 — 안 되면 이번 틱만 건너뜀
            logging.warning(f"모의 스나이퍼: 프리마켓 시세 조회 실패 {e}")
            return "장전 시세 없음"
        raise
    ss = cfg._load_json(DRY_SNIPER_FILE, None)
    if not isinstance(ss, dict):
        ss = copy.deepcopy(SN.load_state(cfg))                          # 처음엔 실거래 기준가를 복사해 시작 (이후 모의 파일만 씀)
    SN.series_add(ss, px, now_t)
    SN.trail_tick(sim, s, px, now_t, ss)                                  # 판 32: 1층 트레일링 (메모리 슬롯 — 저장 안 함)
    SN.update_peak(ss, SN.layer_count(SN.active_floors(sim)), q)
    cfg._save_json(DRY_SNIPER_FILE, ss)
    done_sell = {int(o["floor_id"]) for o in m["orders"] if o.get("side") == "SELL" and o.get("floor_id") is not None and o.get("box_id") is None}
    done_sell |= TW.merged_floor_ids(sim, [o.get("no") for o in m["orders"] if o.get("side") == "SELL"])      # v2.16.0 판 43 Q1
    done_boxes = {(int(o["floor_id"]), int(o["box_id"])) for o in m["orders"] if o.get("side") == "SELL" and o.get("floor_id") is not None and o.get("box_id") is not None}      # v2.6.0 버킷별 매도: 버킷 단위로 건너뜀
    out = []
    if n.time() < datetime.time(20, 0):                                      # 판 39 수정 1차: 16:10 → 20:00 (실거래 틱·동기화 시각과 같게 — 모의만 16:10 에 매도를 멈추면 16:10~20:00 이 실거래와 달라짐)
        sells, _sn = SN.plan_sells(s, sim, px, max(0, q), skip_ids=done_sell, skip_boxes=done_boxes)                  # v2.6.0: 버킷별 매도 자동 (모의는 기록만)
        tw_all, _tn, _tr = SN.tower_sells(s, sim, px, max(0, q - sum(o["qty"] for o in sells)), skip_ids=done_sell | {a for a, _b in done_boxes})
        tw_pick, _held = pick_sells(tw_all, TW.sell_layers(s) - len({int(o["floor_id"]) for o in m["orders"] if o.get("mode") == "tower" and o.get("side") == "SELL"}))
        for o in sells + tw_pick:
            if o.get("floor_id") in done_sell or (o.get("box_id") is not None and (int(o["floor_id"]), int(o["box_id"])) in done_boxes):
                continue
            rec = dict(o, sim=True, at=n.isoformat())
            rec.pop("reached", None)
            m["orders"].append(rec)
            out.append(rec)
    if SN.buy_ok(status, n) and TW.trade_mode(s) == "tower":      # 판 33: 탑쌓기 매매 모의 — 하루 한 번 탑쌓기 매수를 기록만 (주문 안 냄)
        if not m.get("tower_buy_sent"):
            open_px = ensure_open_price(s, cfg, d, False, n, px, status)
            try:
                fx = float(api.fx_applied_rate())
            except MeritzError:
                fx = 0.0
            if open_px > 0 and fx > 0:
                pl = SN.plan_tower_buy(s, sim, q, principal, px, fx, api.usd_cash(), open_px)
                m["tower_buy_sent"] = True
                for o in pl["orders"]:
                    rec = dict(o, sim=True, at=n.isoformat())
                    m["orders"].append(rec)
                    out.append(rec)
    elif SN.buy_ok(status, n):           # v2.5.0: 하루 매수 F 수 제한 없음
        rsi = SN.rsi_from_state(ss, now_t)[0]
        ha = first_buy_ha(s, api, sim, n, ss=_SNIPER)
        pb = SN.plan_buy(s, sim, px, ss, rsi, api.usd_cash(), n, "LIMIT", is_trading_day=us_trading_day, ha=ha)
        if pb["order"] and not any(o.get("side") == "BUY" and o.get("floor_id") == pb["order"]["floor_id"] and o.get("signal") == pb["order"].get("signal") for o in m["orders"]):
            rec = dict(pb["order"], sim=True, at=n.isoformat())
            m["orders"].append(rec)
            out.append(rec)
    if out:
        cfg._save_json(mark, m)
        note.send(f"모의 스나이퍼 — 주문은 안 냈어요 (시뮬레이션 기록만)\n현재가 ${px:.2f}\n" + fmt_orders(out))
        return "모의 기록"
    return "모의 신호 없음"


PICK_TEXT = ("스나이퍼 목표가에 닿은 F가 있어요 — 자동으로 팔지 않아요. 선택해 주세요.\n"
             "{no}F 평단 ${avg:.2f} ({qty}주) · 목표가 ${target:.2f} (평단 +{pct:g}%) · 현재가 ${price:.2f}\n"
             "• 스나이퍼: 이 F는 그대로(안 팔고 안 바꿈) 두고, 목표가 ${target:.2f} 를 기준가로 하는 새 F를 만들어 스나이퍼 매매\n"
             "• 탑쌓기: 이 F를 잠가 탑 매도(평단 +10% → 50%)로 넘김\n"
             "답이 없으면 탑쌓기로 두고 기다려요 (그동안 스나이퍼 매수 신호가 오면 바로 새 F를 사요 — 다시 안 물어요).")


def send_pick_prompts(s, note, asks):
    """v2.4.0: 목표가에 닿은 F마다 텔레그램 버튼 2개(스나이퍼/탑쌓기)로 물음. 버튼 글자는 callback 'pk:<F 평단>:s|t'"""
    for a in asks:
        text = PICK_TEXT.format(**a)
        btn = [[("스나이퍼", f"pk:{a['key']}:s"), ("탑쌓기", f"pk:{a['key']}:t")]]
        fn = getattr(note, "send_buttons", None)
        if fn is not None:
            fn(text, btn)
        else:
            note.send(text)


def apply_pick(s, key, choice):
    """v2.4.0 텔레그램 버튼(스나이퍼/탑쌓기) 반영 → 안내 글자. 스나이퍼 상태·F 상태 파일을 같이 저장. 이미 처리됐거나 없어진 F면 아무것도 안 바꿈. 실제 주문·장부는 안 건드림"""
    cfg = ConfigManager(s)
    if choice not in ("s", "t"):
        return "알 수 없는 선택이에요"
    pos = cfg.get_position()
    if not pos:
        return "장부가 없어 처리하지 않았어요"
    tst, had = tower_state_for(cfg, int(pos["qty"]), float(pos["principal"]), s)
    if not had:
        return "F 상태 파일이 없어 처리하지 않았어요"
    ss = SN.load_state(cfg)
    msg = SN.pick_resolve(ss, tst, key, choice, TW.params(s)[0])
    if msg is None:
        return "이미 처리됐거나 없어진 F예요 (아무것도 안 바꿨어요)"
    cfg._save_json(TOWER_FILE, tst)
    SN.save_state(cfg, ss)
    return msg


LEDGER_FIX_FILE = "data/ledger_fix_v240.json"        # 판 24 일회성 장부 바로잡기 완료 표시 (있으면 다시 안 함)
LEDGER_FIX_SKIP_FILE = "data/ledger_fix_v240_skip.json"      # 잔고 불일치로 안 돌렸을 때 하루 한 번 알림용
LEDGER_FIX_SHARES = 684                              # 실제 잔고가 이 값일 때만 실행
LEDGER_FIX_FLOORS = ((373, 15028.0), (311, 14972.0))         # 판 24 지시문: (수량, 원가) → 평단 $40.29(약) · $48.14(약)


def run_ledger_migration(s, api, note, today):
    """판 24 장부 바로잡기 (일회성). 16:10 이후 장부에만 +69주가 늘어난 것(실제 체결 없음)을 바로잡음: 메리츠 실제 잔고가 684주일 때만 → 장부 684주·원금 $30,000 · 층 2개(373주 $15,028 · 311주 $14,972, 잠금) + 지하층(빈 층).
    실제 잔고·주문은 안 건드림 (장부·층 상태 파일만). 반영한 주문번호(applied)는 그대로 → 늦은 체결이 가짜 69주를 되살리지 않음 + run_late_fills 는 이 날짜까지의 기록을 건너뜀. 정지 표시는 풀지 않음. 한 번 하면 마커 파일로 다시 안 함. → 상태 글자"""
    cfg = ConfigManager(s)
    if cfg._load_json(LEDGER_FIX_FILE, None):
        return "이미 실행"
    try:
        hold = int(api.holding(s["symbol"])[0])
    except Exception as e:
        logging.warning(f"장부 바로잡기: 잔고 조회 실패 {type(e).__name__}")
        return "잔고 조회 실패"
    if hold != LEDGER_FIX_SHARES:
        sk = cfg._load_json(LEDGER_FIX_SKIP_FILE, None)
        if not (isinstance(sk, dict) and sk.get("day") == today and sk.get("hold") == hold):
            cfg._save_json(LEDGER_FIX_SKIP_FILE, {"day": today, "hold": hold})
            note.send(f"장부 바로잡기를 안 했어요 — 메리츠 실제 잔고 {hold}주 ≠ 기준 {LEDGER_FIX_SHARES}주. 장부·층은 그대로예요. Muse 확인 필요 (Notion [AI] 질문란에 적어 주세요).")
        return "잔고 불일치"
    pos = cfg.get_position()
    if not pos:
        return "장부 없음"
    old_q, old_p = int(pos["qty"]), float(pos["principal"])
    tst, had = tower_state_for(cfg, old_q, old_p, s)
    new_p = round(sum(c for _q, c in LEDGER_FIX_FLOORS), 4)
    TW.ledger_fix_state(tst, LEDGER_FIX_FLOORS, TW.params(s)[0])
    pos["qty"], pos["principal"] = LEDGER_FIX_SHARES, new_p
    if "cycle_buy_total" in pos:
        pos["cycle_buy_total"] = round(max(0.0, float(pos.get("cycle_buy_total") or 0) - (old_p - new_p)), 4)
    cfg._save_json(cfg.FILES["POSITION"], pos)
    cfg._save_json(TOWER_FILE, tst)
    cfg._save_json(LEDGER_FIX_FILE, {"done_at": now_et().isoformat(), "through": today, "before": {"qty": old_q, "principal": round(old_p, 4), "had_tower_file": bool(had)},
                                     "after": {"qty": LEDGER_FIX_SHARES, "principal": new_p, "floors": [list(x) for x in LEDGER_FIX_FLOORS]}})
    fl = sorted(tst["floors"], key=TW.floor_avg)
    note.send(f"장부 바로잡기 완료 (일회성)\n이유: 16:10 이후 장부에만 +{old_q - LEDGER_FIX_SHARES}주가 늘어났고 실제 체결은 없었어요 (장부 {old_q}주 → 실제 잔고 {LEDGER_FIX_SHARES}주).\n"
              + "\n".join(f"- {i}층 {int(f['qty'])}주 · 원가 ${f['cost']:,.0f} · 평단 ${TW.floor_avg(f):.2f} (잠금 · 탑 매도)" for i, f in enumerate(fl, 1))
              + "\n- 공사중: 0주 · $0 (다음 스나이퍼 매수부터 채움)\n실제 잔고·주문은 안 건드렸어요. 정지 표시가 남아 있으면 확인한 뒤 직접 풀어 주세요.")
    return "완료"


def tower_buy_tick(s, api, cfg, note, mark, m, d, n, px, sim, q, pr, exch, status, out):
    """판 33 탑쌓기 매매 모드의 하루 한 번 매수: 시초가와 가장 가까운 칸부터 아래로 칸마다 같은 금액 지정가 (TW.make_plan 매수 계획 그대로).
    이미 오늘 냈으면(tower_buy_sent) 다시 안 냄. 체결은 기존대로 run_sync 가 반영(탑쌓기 매수). 시초가·환율을 못 읽으면 내지 않고 다음 틱에 다시 시도"""
    if m.get("tower_buy_sent"):
        return out[0] if out else "탑쌓기 매수 오늘 완료"
    open_px = ensure_open_price(s, cfg, d, True, n, px, status)
    if not open_px > 0:
        return out[0] if out else "시초가 대기"
    try:
        fx = float(api.fx_applied_rate())
    except MeritzError as e:
        logging.warning(f"탑쌓기 매수: 적용환율 조회 실패 {e}")
        fx = 0.0
    if not fx > 0:
        return out[0] if out else "환율 실패"
    if not exch:
        _warn_once(cfg, mark, m, "exch", note, "거래소 번호를 알 수 없어 탑쌓기 매수를 못 냄 — 설정에 거래소 번호를 넣어 주세요")
        return "거래소"
    cash = api.usd_cash()
    pl = SN.plan_tower_buy(s, sim, q, pr, px, fx, cash, open_px)
    if not pl["orders"]:
        m["tower_buy_sent"] = True
        cfg._save_json(mark, m)
        note.send("탑쌓기 매수: 오늘 낼 주문 없음\n" + "\n".join("· " + x for x in pl["notes"]))
        return out[0] if out else "탑쌓기 매수 없음"
    m["tower_buy_sent"] = True          # 주문 전에 표시 → 도중에 멈춰도 같은 날 다시 안 냄
    cfg._save_json(mark, m)
    placed, errs = [], []
    for o in pl["orders"]:
        o = dict(o, ts=round(time.time(), 1))
        if send_order(s, api, cfg, mark, m, o, exch, errs, intraday=True) in ("ok", "unsure"):
            placed.append(o)
        time.sleep(0.3)
    note.send(f"탑쌓기 매수 접수 {len(placed)}건 (시초가 ${open_px:.2f} 기준)\n" + fmt_orders(placed) + ("\n" + "\n".join("· " + x for x in pl["notes"]) if pl["notes"] else "") + ("\n" + "\n".join(errs) if errs else ""))
    return "탑쌓기 매수 접수" if placed else "탑쌓기 매수 실패"


def first_buy_ha(s, api, sim, n, ss=None):
    """v2.12.0 판 39 할 일 1·6: 보유 층 0개(첫 매수 분기 A)일 때만 메리츠 1분봉(api.minute_candles)을 읽어 직전 완결봉 HA 상태를 만듦 → plan_buy(ha=). 층이 있으면 호출 안 함(None).
    못 읽으면(형식·통신 오류) None → 매수 보류 (HOLD_ZERO_SHARES_SHAVED_HA_BEAR). 읽기 전용 호출.
    v2.13.0 판 40: ss(보통 _SNIPER)를 주면 분 경계 쉴드 적용 — 같은 분 안에서 HA음봉 보류 뒤엔 1분봉을 다시 안 읽고, 새 분 직후 직전 완결봉이 아직 안 보이면 기다림 (SN.ha_shield). ss 없으면 예전 그대로"""
    if SN.layer_count(SN.active_floors(sim)) > 0:
        return None
    if ss is not None:
        blocked, why, rem = SN.ha_shield(ss, n, None)
        if blocked:
            return {"ready": False, "shaved_bear": False, "closed_mk": "", "shield": why, "wait_sec": rem}
    try:
        ha = SN.AD.first_buy_ha(api.minute_candles(s["symbol"], s["price_market"]), n)
    except (MeritzError, ValueError, KeyError, TypeError):
        return None
    if ss is not None:
        blocked, why, rem = SN.ha_shield(ss, n, ha)
        if blocked:
            return dict(ha, ready=False, shield=why, wait_sec=rem)
        if (not ha.get("ready")) or ha.get("shaved_bear"):
            SN.ha_wait_mark(ss, n, ha)
    return ha


def topup_try(s, api, cfg, note, mark, m, rows, sim, ss, status, n, now_t, px, exch, d):
    """v2.13.0 판 40 할 일 6 — 원작 분기 B-0 (본 그리드 1층) · S-B0 (서브): 부분체결로 남은 잔량이 있고 현재가가 그 단가에 다시 닿으면 잔량을 지정가로 재발주 (TOPUP_1FL).
    조건: 매수 창·장운영 코드 열림 · 주문 뒤 60초 쉼(원작 60초 타임쉴드) · 5분 쉼(거절 뒤) · 열린 매수 주문 없음(호출 앞에서 확인됨) · 거래소 번호 있음. 보충 주문을 내면 이전 주문에 topup_done 표시 (같은 잔량 중복 방지).
    메리츠 API 에 취소가 없으므로 '열린 채 남은 주문'은 보충하지 않음 (그 주문이 체결되거나 닫힐 때까지 기다림). 결과 글자 또는 None (할 일 없음 → 호출한 쪽이 보통 매수 판단을 이어 감)"""
    if not SN.buy_ok(status, n) or not exch:
        return None
    if now_t - float(ss.get("last_order_ts") or 0) < SN.ORDER_SHIELD_SEC or now_t < float(ss.get("buy_block_until") or 0):
        return None
    tp = SN.topup_find(m.get("orders") or [], rows, [])
    if not tp:
        return None
    if px > float(tp["book_price"]) + 1e-6:
        return None                                              # 도래 전 — 조회 없이 기다림 (달러 조회도 안 함)
    try:
        cash = api.usd_cash()
    except MeritzError:
        return None
    o, why = SN.topup_order(s, sim, tp, px, cash, n)
    if o is None:
        if why and "도래" not in why:
            _warn_once(cfg, mark, m, "topup_" + str(tp["no"]), note, "스나이퍼 1층 잔량 보충 안 함: " + why)
        return None
    prev = next((x for x in m.get("orders") or [] if str(x.get("no")) == str(tp["no"])), None)
    if prev is not None:
        prev["topup_done"] = True                                 # 주문 전에 표시 (send_order 가 기록 파일을 저장함 — 응답을 못 받아도 같은 잔량을 다시 안 냄)
    o = dict(o, ts=round(now_t, 1))
    errs = []
    res = send_order(s, api, cfg, mark, m, o, exch, errs, intraday=True)
    ss["last_order_ts"] = now_t
    if res == "rejected":
        ss["buy_block_until"] = now_t + 300
    SN.save_state(cfg, ss)
    note.send(f"스나이퍼 1층 잔량 보충(TOPUP_1FL) {'접수' if res == 'ok' else ('실패' if res == 'rejected' else '응답 못 받음')}\n현재가 ${px:.2f}\n" + fmt_orders([o]) + ("\n" + "\n".join(errs) if errs else ""))
    return "보충 접수" if res == "ok" else "보충 실패"


def _order_placed_ts(o):
    """주문 낸 시각 (send_order 가 저장한 placed_ts 우선, 옛 ts 대체). 둘 다 없으면 None — 시각을 알 수 없는 주문은 취소하지 않음."""
    for k in ("placed_ts", "ts"):
        try:
            v = float(o.get(k) or 0)
        except (TypeError, ValueError):
            continue
        if v > 0:
            return v
    return None


def _cancel_stale_buys(s, api, cfg, note, mark, m, rows, open_buys, d, now_t):
    """판 42: 60초(SNIPER_BUY_CANCEL_SEC) 넘게 미체결인 매수 주문을 취소함 (원작 BUY_ORDER_MAX_WAIT_SEC=60.0과 같게).
    잔량 = 주문 수량 − 누적 체결 수량. 잔량 0이면 이미 다 체결된 거라 취소 안 함. 번호·시각이 없는 주문(attempts 등)은 취소 못 해서 건너뜀.
    → 취소한 주문이 1건이라도 있으면 True (호출처는 주문 뒤 60초 쉼을 걸고 이번 틱은 새 매수 없이 돌아감). 취소 실패는 로그만 남기고 False 쪽으로 (새 매수는 계속 막힘)."""
    cancelled_any = False
    for o in open_buys:
        if not isinstance(o, dict) or not str(o.get("no") or "").strip():
            continue                                                # 번호 없으면 취소할 주문을 특정 못 함
        placed = _order_placed_ts(o)
        if placed is None or now_t - placed <= SNIPER_BUY_CANCEL_SEC:
            continue                                                # 60초 안 지났거나 시각 모름 → 취소 안 함
        filled = int((rows.get(str(o["no"])) or {}).get("qty", 0))
        remain = int(o.get("qty") or 0) - filled
        if remain <= 0:
            continue                                                # 다 체결됨 — 다음 틱에서 open_buys 에서 빠짐
        otype = str(o.get("type") or "LIMIT").upper().strip()
        cls = ORDER_TYPES.get(otype, ("01", "0"))[0] if otype in ORDER_TYPES else "01"
        try:
            api.cancel_order(oder_date=d.replace("-", ""), orgl_oder_no=str(o["no"]), oder_cls_code=cls, odqt=remain)
        except Exception as e:
            logging.warning(f"스나이퍼 미체결 매수 60초 취소 실패 (주문 {o.get('no')}): {type(e).__name__} {e}")
            continue
        cancelled_any = True
        note.send(f"미체결 매수 60초 지나 취소했어요: {remain}주 @ ${float(o.get('price') or 0):.2f} (주문 {o.get('no')}) — 체결된 {filled}주는 장부에 반영돼요")
    return cancelled_any


def run_sniper_tick(s, api, note):
    """v2.2.20 스나이퍼 한 번치 (실거래만, loop 가 09:30 ET ~ 체결 반영 시각 전에 부름. 간격 = intraday_sell_check_sec, 최소 30초). 순서:
    ① 오늘 기록이 없으면 만듦 ② 체결 확인 → 매도·스나이퍼 매수 체결은 즉시 장부·F에 반영 (탑쌓기 매수는 run_sync) ③ 체결 알림 ④ 잔고 = 예상 확인 (다르면 보류)
    ⑤ 시세를 분 단위로 모음(RSI 용) ⑥ F별 목표에 닿으면 그 F 전량 지정가 매도 (정규장·장후, 16:10 전까지) ⑦ 60초마다 눌림·돌파 신호 → F 완성 기준 금액의 남은 몫만큼 지정가 매수 (정규장·16:00 전까지, 15:30 뒤 돌파 차단)"""
    if now_et().time() >= OPEN_TIME_ET and time.time() - _SNIPER.get("last_poll", 0.0) >= ASSASSIN_POLL_SEC:      # 판 38: 틱이 04:00 부터 돌아도 1분 봉 모으기는 예전 시각(09:30 ET~) 그대로. 판 40: 틱이 1.5초가 돼도 30초 간격
        _SNIPER["last_poll"] = time.time()
        assassin_poll(s, api, note)                                # 판 41: 1분 봉 모으기 + 암살자 모의 지표 (바벨 켜짐과 무관)
    ar = assassin_live_step(s, api, note)                          # 판 41 할 일 1: 원작 암살자 틱 (모의·예약·실전 모두)
    if BB.assassin_blocks(s["state_dir"]):                         # 실전(LIVE)이면 하이브리드는 서 있음 — 암살자가 SOXL 을 단독 운용 (원작 is_live_assassin_standalone_active). 보유·잔고 대조도 안 함
        return "해당 없음" if ar in ("WEEKEND_CLOSED", "WAIT_0407_OPEN", "ASSASSIN_DISABLED", "NO_TRADE_OFFWORK_0815", "NO_LIVE_PRICE") else "암살자 실전"
    if s.get("dry_run", True):
        return run_sniper_dry(s, api, note)                    # 판 23 수정1 B7: 모의에서도 스나이퍼가 돌되 주문은 안 나가고 시뮬레이션 기록만
    if not sniper_on(s):
        return "꺼짐"
    now_t = time.time()
    if now_t - _SNIPER["last"] < SN.tick_gap(s):                       # 판 40: 틱 간격 = 설정 sniper_tick_sec (기본 1.5초). 되돌리기: 30 으로
        return "대기"
    _SNIPER["last"] = now_t
    n = now_et()
    d = n.strftime("%Y-%m-%d")
    mark = os.path.join(s["state_dir"], "data", f"orders_{d}.json")
    cfg = ConfigManager(s)
    m = cfg._load_json(mark, None)
    if not isinstance(m, dict):
        m, why = sniper_preflight(s, api, note, cfg, d, mark, n)
        if m is None:
            return why
    if m.get("skipped") or not isinstance(m.get("orders"), list):
        return "해당 없음"
    if m.get("synced", True) and not night_tick_ok(s, m, n):         # 판 41 할 일 3: 마감(20:00 ET) 뒤에도 매도 창이 열려 있으면 틱을 이어 감 (야간 매도 실질화)
        return "해당 없음"
    bad = gate_problems(s, cfg, live=True)
    if bad:
        logging.warning("스나이퍼 확인 건너뜀: " + "; ".join(bad)[:200])
        return "차단"
    try:
        rows = fill_rows_for(api, s, d)
    except MeritzError as e:
        logging.warning(f"스나이퍼: 체결 조회 실패 {e}")
        return "체결 조회 실패"
    items = fill_items(m, rows)
    pos = cfg.get_position()
    tst, had = tower_state_for(cfg, int(pos["qty"]) if pos else 0, float(pos["principal"]) if pos else 0.0, s)
    if had and pos:
        apply_tower_fills(s, cfg, d, items, tst, sniper_only=True)           # 매도·스나이퍼 매수 체결 즉시 반영 (장부·층 같이 저장)
        pos = cfg.get_position()
    if not pos:
        _ss0 = SN.load_state(cfg)
        if SN.update_peak(_ss0, 0, 0):                           # 판 23 수정1 S3: 보유 0주 = 사이클 끝 → 최고 층수 초기화
            SN.save_state(cfg, _ss0)
        return "해당 없음"
    q, pr = int(pos["qty"]), float(pos["principal"])
    sim = copy.deepcopy(tst)
    gap, start = TW.params(s)[2], float(s.get("tower_floor1_start_usd") or 0)
    for it in TW.sort_fills(sim, [i for i in items if i["side"] == "BUY" and i["o"].get("kind") != "buy_sniper"]):      # 탑쌓기 매수는 메모리 안에서만 (장부는 run_sync)
        dq, da = TW.apply_fill_delta(sim, it["o"], it["q"], it["amt"], gap, start)
        sim.pop("_cost_removed", None)
        q, pr = q + dq, pr + da
    try:
        send_fill_alerts(s, api, note, cfg, m, mark, items, d, sim)
    except Exception as e:
        logging.warning(f"체결 알림 중 오류 {type(e).__name__}")
    status = str(api.us_market_status())
    if status not in SN.SELL_STATUS:                       # 판 38: 프리마켓(003) 포함. 그 밖 코드(야간 등)는 메리츠 접수 여부 미확인이라 안 냄
        return "장 닫힘"
    if not SN.sell_ok(status, n):                          # 판 38: 원작 매도 창 — 평일 04:00~04:06 ET 7분만 닫힘 (이 7분은 매수 창도 아님)
        return "매도 창 밖"
    try:
        px = float(api.price(s["symbol"], s["price_market"])["price"])
    except MeritzError as e:
        if status == MKT_PRE:                              # 판 38: 프리마켓 시세 조회가 되는지는 미확인 — 안 되면 이번 틱만 건너뜀
            logging.warning(f"스나이퍼: 프리마켓 시세 조회 실패 {e}")
            return "장전 시세 없음"
        raise
    ss = SN.load_state(cfg)
    SN.series_add(ss, px, now_t)
    SN.trail_tick(sim, s, px, now_t, ss)                                    # 판 32: 1층 트레일링 (원작 슬롯, 메모리에만 — 상태 파일에 저장 안 함, 재시작하면 다시 계산)
    SN.update_peak(ss, SN.layer_count(SN.active_floors(sim)), q)            # 판 23 수정1 S3: 이번 사이클 최고 층수 (눌림 깊이 잠금) — 상태 파일에 저장
    SN.save_state(cfg, ss)
    hold, sellable, exch_vid = api.holding(s["symbol"])
    if hold != q:
        _warn_once(cfg, mark, m, "hold", note, f"오늘 체결 반영 뒤 예상 {q}주 ≠ 메리츠 잔고 {hold}주 — 스나이퍼 매매를 보류하고 계속 확인해요 (체결 조회가 늦은 것일 수 있음)")
        return "잔고 불일치"
    exch = str(s.get("exch_id") or exch_vid or "")
    ch_sub = SN.sync_sub(ss, hold)                              # v2.5.0 서브 버킷 수량을 실제 보유에 맞춤
    ch_day = SN.seed_main_day(ss, sim, n.strftime("%Y-%m-%d"))  # 판 30 B4: 층이 있는데 본 매매일이 비어 있으면 오늘로 (서브 5영업일 시계 시작)
    if ch_sub or ch_day:
        SN.save_state(cfg, ss)
    out = []
    # ---- 매도: 층 평단 + 익절% 에 닿은 층 전량. 이 층 매도가 이미 나가 있거나(미체결·응답 못 받음) 같은 목표가로 거절됐던 층은 건너뜀
    open_rows = open_rows_or_none(api, s)                # 판 23 수정1 B3: 미체결 판단은 미체결 조회로 (앱에서 취소한 주문은 잠금에서 빠짐)
    open_sells = sniper_open_orders(m, rows, "SELL", open_rows)
    busy = {int(x["floor_id"]) for x in open_sells if x.get("floor_id") is not None and x.get("box_id") is None}                      # 층 단위 주문(탑 매도 등)이 나가 있는 층
    busy_boxes = {(int(x["floor_id"]), int(x["box_id"])) for x in open_sells if x.get("floor_id") is not None and x.get("box_id") is not None}      # v2.6.0 버킷별 매도: 주문이 나가 있는 버킷
    rej_raw = m.get("sniper_rejected") or {}
    rej = {int(k): float(v) for k, v in rej_raw.items() if ":" not in str(k)}
    rej_box = {tuple(int(x) for x in str(k).split(":")): float(v) for k, v in rej_raw.items() if ":" in str(k)}                         # 버킷 거절 기록 키 "층:버킷"
    for r in SN.sell_rows(sim, s, px):
        if r["id"] in rej and abs(rej[r["id"]] - r["target"]) < 1e-9:
            busy.add(r["id"])
    for br in SN.box_rows(sim, s, px):
        k = (br["floor_id"], br["box_id"])
        if k in rej_box and abs(rej_box[k] - br["target"]) < 1e-9:
            busy_boxes.add(k)
    busy |= sold_floor_ids_today(m, rows, open_rows)                    # v2.3.0: 오늘 이미 매도 주문이 나간 F는 다시 안 냄 (F 단위 주문만 — 버킷 주문은 버킷 단위로 아래에서 봄)
    busy_boxes |= sold_box_keys_today(m, rows, open_rows)
    busy |= TW.merged_floor_ids(sim, [x.get("no") for x in m["orders"] if isinstance(x, dict) and x.get("side") == "SELL"])      # v2.16.0 판 43 Q1: 방금 판 잔여분이 합쳐진 F는 오늘 매도 안 함
    need_q = sum(o["qty"] for o in SN.plan_sells(s, sim, px, 10 ** 9, skip_ids=busy, skip_boxes=busy_boxes)[0])       # 판 31 질문 3: 원작식 — 목표 수량을 먼저 구하고 매도가능이 그만큼 될 때까지 2초(0.25초 간격) 기다림
    if need_q > 0:
        sellable = SN.wait_sellable(lambda: getattr(api, "raw", api).holding(s["symbol"])[1], need_q)      # 판 40: 캐시 말고 지금 값
    sells, _sn = SN.plan_sells(s, sim, px, max(0, int(sellable)), skip_ids=busy, skip_boxes=busy_boxes, ext=(status == MKT_AFTER))      # v2.6.0: 버킷별 매도 자동 (미완성 F: 버킷마다 자기 평단 기준 — 공격 버킷 +1.5% · 나머지 +1.0%, 그 버킷만 전량). 판 24 선택 질문은 안 부름
    tw_all, _tn, _tr = SN.tower_sells(s, sim, px, max(0, int(sellable) - sum(o["qty"] for o in sells)), skip_ids=busy | {a for a, _b in busy_boxes})      # 완성 F만 (탑 매도 +10% → 50%)
    tw_pick, tw_held = pick_sells([o for o in tw_all if not (int(o["floor_id"]) in rej and abs(rej[int(o["floor_id"])] - float(o["price"])) < 1e-9)],
                                  TW.sell_layers(s) - tower_sold_count_today(m, rows, open_rows))      # 하루 매도 F 수(N_sell) 적용 — 넘는 F는 알림만 (알림은 하루 한 번)
    if tw_held:
        _nos = SN.sniper_numbers(sim)
        _warn_once(cfg, mark, m, "tower_sell_held", note, "탑 매도 목표에 닿았지만 하루 매도 F 수(" + str(TW.sell_layers(s)) + ")를 넘어 주문은 안 냄: " + ", ".join(f"{_nos.get(int(o['floor_id']), o['floor_id'])}F" for o in tw_held))
    sells = sells + [dict(o, type="LIMIT") for o in tw_pick]
    if sells:
        if foreign_open_sells(open_rows if open_rows is not None else api.open_orders_today(s["symbol"]), m, rows):
            _warn_once(cfg, mark, m, "open_sell", note, "이 계좌에 SOXL 매도 미체결 주문이 이미 있어 스나이퍼 매도를 안 냄 (수동 확인)")
            sells = []
        elif not exch:
            _warn_once(cfg, mark, m, "exch", note, "거래소 번호를 알 수 없어 스나이퍼 매도를 못 냄 — 설정에 거래소 번호를 넣어 주세요")
            sells = []
    if sells:
        results, errs_all, placed = [], [], []
        for sel in sells:
            o = dict(sel, desc=("" if sel.get("mode") == "tower" else "스나이퍼 매도 · ") + sel.get("desc", ""))
            o.pop("reached", None)
            att = {"at": n.isoformat(), "qty": o["qty"], "price": o["price"], "kind": "sell", "floor_id": o.get("floor_id"), "box_id": o.get("box_id"), "status": "접수 시도 (이 기록이 있으면 같은 목표가로는 다시 안 냄)"}
            if status != MKT_REGULAR:
                att["market_status"] = status
            m.setdefault("sell_attempts", []).append(att)
            cfg._save_json(mark, m)
            errs = []
            res = send_order(s, api, cfg, mark, m, o, exch, errs, intraday=True)
            if res == "ok":
                att.update(status="접수 완료", no=m["orders"][-1]["no"])
            else:
                att["status"] = ("증권사가 거절: " if res == "rejected" else "응답 못 받음 — 체결 내역에서 자동으로 찾음: ") + (errs[0] if errs else "")[:100]
                if res == "rejected":
                    m.setdefault("sniper_rejected", {})[(f"{int(o['floor_id'])}:{int(o['box_id'])}" if o.get("box_id") is not None else str(int(o["floor_id"])))] = float(o["price"])      # v2.6.0: 버킷 주문은 "층:버킷" 키
            cfg._save_json(mark, m)
            results.append(res)
            placed.append(o)
            errs_all += errs
        ss["last_order_ts"] = now_t
        SN.save_state(cfg, ss)
        ok_n = sum(1 for r in results if r == "ok")
        note.send(f"{ {MKT_PRE: '장전(003) ', MKT_AFTER: '장후(005) '}.get(status, '') }매도 {'접수' if ok_n == len(results) else ('실패' if ok_n == 0 and all(r == 'rejected' for r in results) else '일부 접수 · 실패·응답 없음 있음')}\n"
                  f"현재가 ${px:.2f}\n" + fmt_orders(placed) + ("\n" + "\n".join(errs_all) if errs_all else ""))
        out.append("매도 접수" if ok_n else "매도 실패")
    # ---- 매수: 04:07~16:00 ET(프리장·정규장, 판 38)·60초마다·주문 뒤 60초 쉼 · 낸 매수가 안 끝났으면 새로 안 냄 (판 42: 60초 지나면 취소 — 원작과 같게)
    open_buys = sniper_open_orders(m, rows, "BUY", open_rows)
    if open_buys:
        if _cancel_stale_buys(s, api, cfg, note, mark, m, rows, open_buys, d, now_t):
            ss["last_order_ts"] = now_t                             # 취소한 틱에는 새 매수 안 냄 (원작 60초 쉴드와 같은 효과 — 다음 틱부터 다시 판단)
            SN.save_state(cfg, ss)
            return out[0] if out else "매수 주문 취소함"
        old = [o for o in open_buys if (_order_placed_ts(o) or 0) and now_t - _order_placed_ts(o) > SNIPER_STALE_BUY_SEC]
        if old:
            _warn_once(cfg, mark, m, "stale_buy", note, f"스나이퍼 매수 {int(old[0].get('qty') or 0)}주 @ ${float(old[0].get('price') or 0):.2f} 가 {SNIPER_STALE_BUY_SEC // 60}분 넘게 다 체결 안 됐어요 — 60초 취소가 안 돼서 그대로 두고 있어요 (이 주문이 끝나기 전엔 새 매수를 안 내요)")
        return out[0] if out else "매수 주문 진행 중"
    tp_res = topup_try(s, api, cfg, note, mark, m, rows, sim, ss, status, n, now_t, px, exch, d)        # 판 40 할 일 6: B-0 부분체결 잔량 보충 (틱마다 확인 — 원작 1.5초 모니터)
    if tp_res:
        return tp_res
    if (not SN.buy_ok(status, n) or now_t - _SNIPER["last_buy"] < SN.buy_check_gap(SN.layer_count(SN.active_floors(sim)), s)
            or now_t - float(ss.get("last_order_ts") or 0) < SN.ORDER_SHIELD_SEC or now_t < float(ss.get("buy_block_until") or 0)):
        return out[0] if out else "대기"
    _SNIPER["last_buy"] = now_t
    if TW.trade_mode(s) == "tower":      # 판 33: 탑쌓기 매매 모드 — 스나이퍼 신호 대신 하루 한 번 탑쌓기 매수 (사용자가 확인 버튼으로 모드를 바꿨을 때만)
        return tower_buy_tick(s, api, cfg, note, mark, m, d, n, px, sim, q, pr, exch, status, out)
    rsi = SN.rsi_from_state(ss, now_t)[0]
    cash_now = api.usd_cash()
    ha = first_buy_ha(s, api, sim, n, ss=_SNIPER)
    pb = SN.plan_buy(s, sim, px, ss, rsi, cash_now, n, "LIMIT", is_trading_day=us_trading_day, ha=ha)
    buy_sig = bool(pb["signal"].get("should_buy")) or bool(pb.get("sub") and pb["sub"].get("buy"))
    if live_fx_ok(s) and buy_sig:          # v2.3.0 장중 자동환전: 매수 신호가 났는데 달러가 모자라면 부족분만 환전 (실시간 환전 시간·하루 한 번·상한은 auto_fx 가 지킴)
        full = SN.plan_buy(s, sim, px, ss, rsi, 1e12, n, "LIMIT", is_trading_day=us_trading_day, ha=ha)["order"]
        need = round(full["qty"] * full["price"], 2) if full else 0.0
        if need > cash_now + 1e-9:
            cash_now, fxres = intraday_fx(s, api, cfg, note, mark, m, d, n, need, cash_now)
            if fxres and fxres.get("done"):
                pb = SN.plan_buy(s, sim, px, ss, rsi, cash_now, n, "LIMIT", is_trading_day=us_trading_day, ha=ha)
    if not pb["order"]:
        if pb["notes"] and pb["signal"].get("should_buy"):
            _warn_once(cfg, mark, m, "buy_" + pb["signal"]["signal_type"], note, "스나이퍼 매수 신호가 났지만 안 샀어요\n" + "\n".join("· " + x for x in pb["notes"]))
        return out[0] if out else "매수 신호 없음"
    if not exch:
        _warn_once(cfg, mark, m, "exch", note, "거래소 번호를 알 수 없어 스나이퍼 매수를 못 냄 — 설정에 거래소 번호를 넣어 주세요")
        return "거래소"
    o = dict(pb["order"], ts=round(now_t, 1))
    g_ok, g_info = guard_gate(s, o, cash_now)                    # 판 41 할 일 2: GUARD30 + 수혈(INJECT) — free_cash 장부 vs 메리츠 실제 달러
    if not g_ok:
        ss["buy_block_until"] = now_t + GUARD_RECHECK_SEC          # 원작: 60초마다 입금 감지
        SN.save_state(cfg, ss)
        if _SNIPER.get("guard_alert_day") != d:                    # 원작: 입금 요청 알림은 한 번만 (스팸 방지 래치)
            _SNIPER["guard_alert_day"] = d
            note.send(f"스나이퍼 매수 보류 (GUARD30 · 자투리 매수 차단)\n쓸 수 있는 달러 ${cash_now:,.2f} < 최소 ${float(g_info.get('min_req_cash') or 0.0):,.2f} (1주 값 또는 1회분의 30%)\n"
                      f"달러를 넣어 주세요 (권장 ${float(g_info.get('recommended_deposit_usd') or 0.0):,.2f}). 입금되면 {GUARD_RECHECK_SEC}초 안에 다시 확인해요 (알림은 하루 한 번)")
        return "수혈 검문 보류"
    _SNIPER["guard_alert_day"] = ""                                 # 통과하면 래치 풀림
    if g_info.get("injected"):
        note.send(f"수혈(INJECT) — 장부에 ${float(g_info.get('inject_usd') or 0.0):,.2f} 넣었어요 ({int(g_info.get('inject_portions') or 0)}회분, 누적 {int(g_info.get('used_portions_after') or 0)}회분)\n"
                  f"메리츠 실제 달러에는 변화 없어요 (장부 안 이동). 매도가 나면 이 금액부터 먼저 갚아요")
    errs = []
    res = send_order(s, api, cfg, mark, m, o, exch, errs, intraday=True)
    ss["last_order_ts"] = now_t
    if o.get("sub") and res != "rejected":
        SN.mark_sub_gate(ss, pb.get("sub"))                    # v2.5.0 서브 10분 게이트 기록
    elif res != "rejected":
        SN.mark_buy_gate(ss, pb)                               # v1.4.4 판 37 항목 7: 본 매수 10분 게이트 기록
    if res == "rejected":
        ss["buy_block_until"] = now_t + 300                    # 거절되면 5분 쉼 (같은 거절을 매분 반복하지 않게)
    SN.save_state(cfg, ss)
    note.send(f"스나이퍼 매수 {'접수' if res == 'ok' else ('실패' if res == 'rejected' else '응답 못 받음')}\n현재가 ${px:.2f}" + (f" · RSI {rsi:.1f}" if rsi is not None else "") + "\n" + fmt_orders([o])
              + ("\n" + "\n".join(pb["notes"]) if pb["notes"] else "") + ("\n" + "\n".join(errs) if errs else ""))
    return "매수 접수" if res == "ok" else "매수 실패"


# ---------------------------------------------------------------- v2.0.8 휴장일 목록 (코드 안, 2026~2027) · 환전 창
# 근거(2026-11-19 확인, VERIFY.md 에 출처): 미국 = NYSE 공시(2026 10일·2027 10일), 한국 2026 = KRX 휴장 17일(노동절·제헌절·지방선거일 포함),
# 한국 2027 = 우주항공청 월력요항 기준 평일 공휴일 15일 + 연말 휴장 12/31(관례 — KRX 2027 공식 공시는 미확인). 주말은 목록에 안 넣음(코드가 따로 판단).
# 목록 밖 연도(2028~)는 휴장 여부를 모르므로 자동환전·휴장 전날 알림을 하지 않음 (fx_window_info → '휴장일 목록 범위 밖') → 연말에 목록을 갱신해야 함
def _ds(*xs):
    return frozenset(datetime.date.fromisoformat(x) for x in xs)


HOLIDAY_YEARS = (2026, 2027, 2028, 2029)   # audit-fix 7-5: 2028·2029 추가 (뮤즈 자료 2026-11-20; 2029 는 NYSE·월력요항 미발표분 포함 — 바뀌면 다시 확인)
US_HOLIDAYS = _ds("2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
                  "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
                  "2028-01-17", "2028-02-21", "2028-04-14", "2028-05-29", "2028-06-19", "2028-07-04", "2028-09-04", "2028-11-23", "2028-12-25",
                  "2029-01-01", "2029-01-15", "2029-02-19", "2029-03-30", "2029-05-28", "2029-06-19", "2029-07-04", "2029-09-03", "2029-11-22", "2029-12-25")
KR_HOLIDAYS = _ds("2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-02", "2026-05-01", "2026-05-05", "2026-05-25", "2026-06-03", "2026-07-17",
                  "2026-08-17", "2026-09-24", "2026-09-25", "2026-10-05", "2026-10-09", "2026-12-25", "2026-12-31",
                  "2027-01-01", "2027-02-08", "2027-02-09", "2027-03-01", "2027-05-03", "2027-05-05", "2027-05-13", "2027-07-19", "2027-08-16",
                  "2027-09-14", "2027-09-15", "2027-09-16", "2027-10-04", "2027-10-11", "2027-12-27", "2027-12-31",
                  "2028-01-26", "2028-01-27", "2028-01-28", "2028-03-01", "2028-04-12", "2028-05-01", "2028-05-02", "2028-05-05", "2028-06-06", "2028-08-15",
                  "2028-10-02", "2028-10-03", "2028-10-04", "2028-10-05", "2028-10-09", "2028-12-25",
                  "2029-01-01", "2029-02-12", "2029-02-13", "2029-02-14", "2029-03-01", "2029-05-01", "2029-05-07", "2029-05-21", "2029-06-06", "2029-08-15",
                  "2029-09-21", "2029-09-24", "2029-10-03", "2029-10-09", "2029-12-25", "2029-12-31")


def holidays_known(d):
    return d.year in HOLIDAY_YEARS


def us_trading_day(d):
    """미국증시가 열리는 평일(휴장일 목록 제외) — 이 날짜(미국 동부 날짜)에 주문이 나감"""
    return d.weekday() < 5 and d not in US_HOLIDAYS


def kr_fx_day(d):
    """한국 영업일(평일·국내 공휴일 아님) — 메리츠 환전 가능한 날 (국내 휴일은 당일 환전 불가)"""
    return d.weekday() < 5 and d not in KR_HOLIDAYS


def order_time_kst(d, s=None):
    """미국 동부 날짜 d 의 주문 시작 시각(order_time_et)을 한국시간으로 — 겨울 00:05(다음 날)·여름 23:05. 시계(zoneinfo)가 서머타임을 처리"""
    t = _hm((s or {}).get("order_time_et"), datetime.time(10, 5))
    return datetime.datetime.combine(d, t, tzinfo=EST).astimezone(KST)


def fx_time_ok(t):
    """한국시간 시각 t 가 메리츠 실시간 환전 시간(09:00~23:50, 00:20~02:00)인가. 시간외(02:00~08:50)·불가(08:50~09:00, 23:50~00:20)는 False"""
    return any(a <= t < b for a, b in FX_REALTIME)


def _fx_time_why(t):
    if datetime.time(8, 50) <= t < datetime.time(9, 0):
        return "환전 불가 시간 (08:50~09:00)"
    if t >= datetime.time(23, 50) or t < datetime.time(0, 20):
        return "환전 불가 시간 (23:50~00:20 점검)"
    return "시간외 (02:00~08:50 — 수수료 무료가 아니라 안 해요)"


def fx_window_info(n, s=None, check_deadline=True):
    """n(시각) 이 자동환전 가능한 때인가 → {"open", "why", "day"(그날 주문하는 미국 동부 날짜 = 환전 기록 날짜), "deadline"(주문 시간, 한국시간)}.
    열림 조건: ① 주문일(day)이 평일 ② 지금 한국 날짜가 평일·국내 공휴일 아님 ③ 한국시간이 실시간 환전 시간 ④ (check_deadline 이면) 주문 시간 전. 날짜는 휴장일 목록 범위 안일 때만"""
    n = n.astimezone(KST)
    day = n.date() if n.time() >= FX_KST_TIME else n.date() - datetime.timedelta(days=1)      # 자정~08:59 는 전날 창의 연장
    info = {"open": False, "why": "", "day": day, "deadline": order_time_kst(day, s)}
    if not (holidays_known(day) and holidays_known(n.date())):
        info["why"] = "휴장일 목록 범위(2026~2027) 밖 — 목록을 갱신해야 함"
    elif day.weekday() >= 5:
        info["why"] = "주말 (주문 없는 날)"
    elif not kr_fx_day(n.date()):
        info["why"] = "주말·국내 공휴일 (당일 환전 불가)"
    elif not fx_time_ok(n.time()):
        info["why"] = _fx_time_why(n.time())
    elif check_deadline and n >= info["deadline"]:
        info["why"] = "주문 시간 이후"
    else:
        info["open"] = True
    return info


def fx_morning_due(n, s=None):
    """(옛 이름 유지) n 이 자동환전 창 안인가 — v2.0.8 부터 '한국시간 09:00 ~ 주문 시간, 실시간 환전 시간 안에서만'"""
    return fx_window_info(n, s)["open"]


def next_business_day(d):
    x = d + datetime.timedelta(days=1)
    while x.weekday() >= 5:
        x += datetime.timedelta(days=1)
    return x


def closure_ahead(today, s=None):
    """today(오늘의 주문일) 의 '다음 영업일'(평일)이 미국증시 또는 한국증시 휴장 예정이면 → {"day", "kr", "us", "extra", "orders"}, 아니면 None.
    extra = 오늘 몫 말고 미리 환전할 회차 수 = 오늘부터 다음 환전 가능일 사이에 '미국장은 열리는데 한국 휴일이라 그날 환전 창이 없는' 주문일 수 (최소 1 — 사용자 지시: 다음 거래일 한 회차분).
    예) 추석 연휴 목·금(한국 휴장·미국 열림) 전날 수요일 → 2 (수요일 몫 + 2회차)"""
    nb = next_business_day(today)
    if not holidays_known(nb):
        return None
    kr, us = nb in KR_HOLIDAYS, nb in US_HOLIDAYS
    if not (kr or us):
        return None
    e = today + datetime.timedelta(days=1)
    for _ in range(20):
        if kr_fx_day(e) or not holidays_known(e):
            break
        e += datetime.timedelta(days=1)
    orders, x = [], today + datetime.timedelta(days=1)
    while x < e:
        if us_trading_day(x):
            orders.append(x)
        x += datetime.timedelta(days=1)
    return {"day": nb, "kr": kr, "us": us, "extra": max(1, len(orders)), "orders": orders}


WD_KO = "월화수목금토일"


def _hm_text(dt, base_day):
    return ("다음 날 " if dt.date() > base_day else "") + dt.strftime("%H:%M")


# ---------------------------------------------------------------- 오전 9시~주문 시간 자동환전 (v2.0.7 시작 · v2.0.8 창 변경)
_FXM = {"day": "", "done": False, "next": 0.0, "warned": [], "short_next": 0.0}    # 오늘 이미 판단했는지·다시 시도할 시각·알린 이유 (메모리 — 재시작하면 다시 확인하지만 환전 중복은 fx_<날짜>.json 이 막음)


def _fxm_later(note, d, key, text, sec=300):
    """자동환전을 못 한 이유 알림(같은 이유는 하루 한 번)을 보내고 sec 초 뒤 다시 시도. (주문용 _RETRY 와 따로 — 주문 시간 대기에 영향 없음)"""
    if key not in _FXM["warned"]:
        _FXM["warned"].append(key)
        note.send(text)
    _FXM["next"] = time.time() + sec


def _next_rounds_inputs(s, api, cfg, rounds):
    """v2.3.0: '다음 rounds 회차분' 환전 계산용 입력 → (계획, 0.0, 적용환율, 달러 예수금). 계획 = hybrid_fx_plan: 필요 달러 = F 완성 기준 금액 × 하루 매수 F 수 × rounds (시세·F 상태는 안 읽음 — 아침 환전은 그날 채울 F 분을 미리).
    조회 실패는 MeritzError (옛 반환 모양 유지: 두 번째 값은 예전의 전일 종가 자리 — 쓰지 않아 0.0)"""
    rate, _tm = api.fx_applied()
    cash = api.usd_cash()
    return hybrid_fx_plan(s, cash, rounds), 0.0, rate, cash


def run_fx_morning(s, api, note, live):
    """자동환전 → 상태 글자. loop 가 창 안에서만 부름. 주문은 안 냄. (함수 이름은 판 9 그대로)
    '다음 한 회차분'(탑쌓기 계획, max_rounds_per_day 를 1로 둔 계획) 필요 달러 − 달러 예수금 = 부족분만 환전 (여유%·하루 상한은 auto_fx 그대로).
    v2.0.8: 휴장 전날(closure_ahead)이면 오늘 몫 + 휴장 중 주문일(최소 1회차)만큼 — '다음 1+extra 회차분' 으로 계산해 한 번에 환전. 하루 한 번(fx_<날짜>.json).
    가격 기준은 전일 종가(prev_close), 환율은 그 시점 적용환율. 매수 계획이 없거나 부족이 없으면 안 함(기록 안 씀 — Q24). 환전 뒤 달러 반영을 기다리지 않음 (주문까지 시간이 많음)"""
    if not s.get("auto_fx_enabled"):
        return "꺼짐"
    n = now_kst()
    w = fx_window_info(n, s)
    if not w["open"]:
        return "시간 아님"
    d = w["day"].strftime("%Y-%m-%d")                          # 환전 기록 날짜 = 그날 주문하는 미국 동부 날짜 (한국 날짜와 같아 주문 시간 auto_fx 가 같은 파일을 봄. 자정 뒤 연장 구간에도 같은 날짜)
    if _FXM["day"] != d:
        _FXM.update(day=d, done=False, next=0.0, warned=[], short_next=0.0)
    state = s["state_dir"]
    marker = os.path.join(state, "data", f"{'fx' if live else 'dry_fx'}_{d}.json")
    if os.path.exists(marker):
        return "이미 함"
    if _FXM["done"]:
        return "확인 끝"
    if time.time() < _FXM["next"]:
        return "대기"
    cfg = ConfigManager(s)
    if live:
        bad = gate_problems(s, cfg, live=True)
        if bad:
            _fxm_later(note, d, "gate", "자동환전 안 함\n" + "\n".join("- " + b for b in bad) + "\n(고치면 주문 시간 전까지 5분마다 다시 확인해요. 못 하면 마감 60분 전에 달러부족 알림을 보내요)")
            return "차단"
        # 판 44 (2026-11-26): 미동기화 주문 기록이 있어도 아침 자동환전은 막지 않음 — 옛 동기화 게이트 삭제.
        #   이유: 아침 환전 필요액(hybrid_fx_plan)은 설정값(F 완성 기준 금액 × 하루 매수 F 수 × 회차)만으로 계산하고
        #   달러 예수금·적용환율·원화 예수금은 실시간 API 조회라 장부·주문 기록을 전혀 안 읽음. 미동기화 장부가 환전 금액을
        #   틀리게 만들 수 없음 (장중 자동환전 intraday_fx 도 같은 auto_fx 를 동기화 검사 없이 씀).
        #   옛 게이트는 환전 창(09:00 KST = 19:00 ET 전날)이 동기화 시각(20:00 ET = 10:00 KST)보다 1시간 먼저 열려
        #   매일 09:00~10:00 KST에 '자동환전 안 함 — 체결 반영 전인 주문 기록' 알림을 보내고 환전을 막았음 (11-24·11-25 이틀 연속 확인).
        #   동기화 자체는 그대로 20:00 ET run_sync 가 하고, 늦은 체결은 run_late_fills 가 다음 날 반영함. 진단용으로만 로그에 남김.
        _unsynced = []
        for mp in pending_syncs(state):
            _m = cfg._load_json(mp, {})
            if isinstance(_m, dict) and (_m.get("orders") or _m.get("attempts")) and not _m.get("synced", True):
                _unsynced.append(os.path.basename(mp))
        if _unsynced:
            logging.info("아침 자동환전: 미동기화 주문 기록이 있으나 환전 계산은 설정·실시간 잔고만 써서 그대로 진행: %s", ", ".join(_unsynced))
    ca = closure_ahead(w["day"], s)
    rounds = 1 + (ca["extra"] if ca else 0)
    try:
        plan, prev_close, rate, cash = _next_rounds_inputs(s, api, cfg, rounds)
    except MeritzError as e:
        _fxm_later(note, d, "read", f"자동환전 안 함 — 시세·적용환율·달러 예수금 조회 실패: {str(e)[:100]} (5분 뒤 다시 시도해요)")
        return "조회 실패"
    except ValueError:
        _fxm_later(note, d, "close", "자동환전 안 함 — 전일 종가를 못 읽었어요 (5분 뒤 다시 시도해요)")
        return "전일종가 없음"
    buys = [o for o in plan["orders"] if o.get("side") == "BUY"]
    if not buys:                                               # 다음 회차 없음(F 전부 채움·시작 대기 등)·한도 부족 → 환전 안 함
        _FXM["done"] = True
        logging.info("자동환전: 다음 회차 매수 계획 없음 — 환전 안 함")
        return "매수 계획 없음"
    fxres = auto_fx(s, api, cfg, plan, live, d, fx_now=n)
    if fxres is None:                                          # 부족 달러 없음 (기록 안 씀 — Q24)
        _FXM["done"] = True
        logging.info("자동환전: 부족 달러 없음 — 환전 안 함")
        return "필요 없음"
    i = plan["info"]
    head = f"{d} 아침 자동환전 (한국시간 {n.strftime('%H:%M')}) · 다음 {rounds}회차분" + (f" (휴장 전날: 오늘 몫 + 휴장 중 주문일 {ca['extra']}회차)" if ca else "")
    cap_usd = int(float(s.get("auto_fx_max_usd_per_day") or 0))
    over = (f"\n⚠️ 필요 ${i['need_usd']:,.0f} (+여유 {float(s.get('auto_fx_buffer_pct') or 0):g}%)가 하루 환전 상한 ${cap_usd:,} 를 넘어요 — 상한만큼만 환전하고 나머지는 장중 자동환전이나 직접 환전이 필요해요"
            if fxres.get("capped") else "")
    text = head + f"\n{plan.get('fx_basis') or fmt_orders(buys)}\n필요 달러 ${i['need_usd']:,.0f} · 예수금 ${i['usd_cash']:,.0f}\n" + fx_lines(fxres) + over
    if live and not fxres.get("done") and not os.path.exists(marker):      # 환율·원화 예수금·시간 문제로 신청 전에 멈춤 (기록 안 씀) → 같은 창 안에서 다시 시도
        _fxm_later(note, d, "fx", text + "(5분 뒤 다시 시도해요)")
        return "환전 안 함"
    if not live:
        cfg._save_json(marker, {"date": d, "usd": fxres["want"], "result": "모의 — 신청 안 함 (계산만)"})
    _FXM["done"] = True
    note.send(text)
    return "완료" if fxres.get("done") else "환전 안 함(기록 있음)"


def _alert_marker(s, kind, d, live):
    return os.path.join(s["state_dir"], "data", f"{'' if live else 'dry_'}{kind}_{d}.json")


def run_closure_alert(s, note, live):
    """v2.0.8 휴장 전날 알림 — 오늘이 환전 창 안이고 다음 영업일이 미국증시 또는 한국증시 휴장이면 하루 한 번 알림 (자동환전 꺼짐이어도).
    표시 파일 closure_alert_<날짜>.json (모의는 dry_ 접두) — 재시작해도 다시 안 보냄. 환전은 안 함(환전은 run_fx_morning)"""
    n = now_kst()
    w = fx_window_info(n, s)
    if not w["open"]:
        return "시간 아님"
    ca = closure_ahead(w["day"], s)
    if not ca:
        return "휴장 없음"
    d = w["day"].strftime("%Y-%m-%d")
    mk = _alert_marker(s, "closure_alert", d, live)
    if os.path.exists(mk):
        return "이미 알림"
    nb = ca["day"]
    why = " · ".join(x for x, f in (("한국증시 휴장(환전 불가)", ca["kr"]), ("미국증시 휴장", ca["us"])) if f)
    text = (f"휴장 전날 알림 — 다음 영업일 {nb.month}/{nb.day}({WD_KO[nb.weekday()]})은 {why} 예정이에요.\n"
            f"환전은 오늘 한국시간 09:00 ~ 주문 시간({_hm_text(w['deadline'], w['day'])}) 안에 미리 해야 해요 (23:50~00:20 점검 시간은 환전 불가).\n"
            + (f"자동환전이 켜져 있어요 — 오늘 몫 + 휴장 중 주문일 {ca['extra']}회차분을 함께 환전해요 (하루 상한 안에서)."
               if s.get("auto_fx_enabled") else "자동환전이 꺼져 있어요 — 직접 환전해 주세요 (필요 달러는 자금 현황에서 확인)."))
    if note.send(text) is not False:                           # 보내기 실패(False)면 기록 안 써서 다음 확인 때 다시 시도
        ConfigManager(s)._save_json(mk, {"date": d, "next_business_day": nb.isoformat(), "kr": ca["kr"], "us": ca["us"], "extra": ca["extra"]})
    return "알림"


def shortage_alert_due(n, s=None):
    """n 이 마감(주문 시간) 60분 전 ~ 마감 사이인가 (그날이 한국 영업일·미국 주문일일 때). 환전 가능 시간과는 무관 — 알림만"""
    n = n.astimezone(KST)
    day = n.date() if n.time() >= FX_KST_TIME else n.date() - datetime.timedelta(days=1)
    if not holidays_known(day) or not kr_fx_day(day) or not us_trading_day(day):
        return False
    dl = order_time_kst(day, s)
    return dl - datetime.timedelta(minutes=SHORT_ALERT_MIN) <= n < dl


def run_fx_shortage_alert(s, api, note, live):
    """v2.0.8 마감 60분 전 '달러부족' 알림 — 마감 = 주문 시간. 다음 한 회차(휴장 전날이면 1+extra 회차)에 필요한 달러 > 달러 예수금이면 하루 한 번.
    부족분이 0원이면 아무 기록도 안 씀(Q24) — 5분마다 다시 확인. 알림 뒤에도 창 안이면 자동환전은 계속 시도(별도 함수). 자동환전 꺼짐이어도 알림.
    Q25: 필요 달러 = F 완성 기준 금액 × 하루 매수 F 수 × rounds (hybrid_fx_plan 그대로)"""
    n = now_kst()
    if not shortage_alert_due(n, s):
        return "시간 아님"
    day = n.date() if n.time() >= FX_KST_TIME else n.date() - datetime.timedelta(days=1)
    d = day.strftime("%Y-%m-%d")
    mk = _alert_marker(s, "shortage_alert", d, live)
    if os.path.exists(mk):
        return "이미 알림"
    if _FXM["day"] != d:
        _FXM.update(day=d, done=False, next=0.0, warned=[], short_next=0.0)
    if time.time() < _FXM["short_next"]:
        return "대기"
    _FXM["short_next"] = time.time() + 300
    cfg = ConfigManager(s)
    ca = closure_ahead(day, s)
    rounds = 1 + (ca["extra"] if ca else 0)
    try:
        plan, prev_close, rate, cash = _next_rounds_inputs(s, api, cfg, rounds)
    except (MeritzError, ValueError) as e:
        logging.warning(f"달러부족 확인 실패(5분 뒤 다시): {str(e)[:100]}")
        return "조회 실패"
    i = plan["info"]
    if not [o for o in plan["orders"] if o.get("side") == "BUY"]:
        return "매수 계획 없음"
    short = float(i.get("shortfall_usd") or 0)
    if short <= 0:
        return "부족 없음"                                     # 기록 안 씀 (Q24)
    dl = order_time_kst(day, s)
    left = max(0, int((dl - n).total_seconds() // 60))
    text = (f"달러부족 — 마감(주문 시간 {_hm_text(dl, day)}) 약 {left}분 전이에요.\n"
            f"다음 {rounds}회차 매수분({plan.get('fx_basis', '')})에 필요 달러 ${i['need_usd']:,.0f} · 예수금 ${i['usd_cash']:,.0f} · 부족 ${math.ceil(short):,}\n"
            + ("자동환전이 켜져 있어요 — 환전 시간 안이면 계속 시도해요. 그래도 안 되면(원화 부족·환율 조회 실패 등) 직접 환전해 주세요."
               if s.get("auto_fx_enabled") else "자동환전이 꺼져 있어요 — 직접 환전해 주세요."))
    if note.send(text) is not False:
        cfg._save_json(mk, {"date": d, "need": i["need_usd"], "cash": i["usd_cash"], "short": round(short, 2), "rounds": rounds})
    return "알림"


def holiday_range_text(d):
    """v2.2.9 (audit-fix 7-5): 휴장일 목록(HOLIDAY_YEARS) 범위 밖이거나 마지막 해 12월이면 알릴 글자, 아니면 None. 범위 밖 안전장치(자동환전·휴장 전날·달러부족 알림 꺼짐)는 그대로"""
    last = max(HOLIDAY_YEARS)
    if d.year not in HOLIDAY_YEARS and d.year > last:
        return (f"휴장일 목록이 {last}년까지라 오늘({d.isoformat()})은 범위 밖이에요 — 자동환전·휴장 전날 알림·달러부족 알림이 꺼진 상태예요. "
                "달러는 직접 챙겨 주세요. 코드 안 휴장일 목록(US_HOLIDAYS·KR_HOLIDAYS)을 갱신해야 켜져요.")
    if d.year == last and d.month == 12:
        return (f"휴장일 목록이 {last}년 12월 31일까지예요 — 새해부터 자동환전·휴장 전날 알림·달러부족 알림이 꺼져요. 그 전에 목록(US_HOLIDAYS·KR_HOLIDAYS)을 갱신해 주세요.")
    return None


def run_holiday_range_notice(s, note, live):
    """하루 한 번 휴장일 목록 범위 알림 (표시 파일 holiday_range_<날짜>.json — 보내기 성공 뒤에만 기록, 모의는 dry_ 접두)"""
    d = now_kst().date()
    text = holiday_range_text(d)
    if not text:
        return "범위 안"
    mk = _alert_marker(s, "holiday_range", d.isoformat(), live)
    if os.path.exists(mk):
        return "이미 알림"
    if note.send(text) is not False:
        ConfigManager(s)._save_json(mk, {"date": d.isoformat(), "known_years": list(HOLIDAY_YEARS)})
    return "알림"


def one_share_text(plan):
    """audit-fix 7-4 (풀이님 결정 2026-11-20 10:03): 탑쌓기에서 1주만 남은 F가 자동 매도에서 빠지면 보낼 '1주 남음' 글자, 아니면 None"""
    ex = (plan.get("info") or {}).get("sell_excluded") or {}
    if ex.get("why") != "one_share":
        return None
    tw = (plan.get("info") or {}).get("tower") or {}
    tfl = tw.get("floors") or []
    _rank = {int(f.get("id")): n + 1 for n, f in enumerate(sorted([f for f in tfl if int(f.get("qty") or 0) > 0], key=lambda f: (float(f.get("avg") or 0), -int(f.get("id") or 0))))}

    def _flab(fid):
        f = next((x for x in tfl if int(x.get("id")) == int(fid)), None)
        if f is None:
            return f"{fid}F"
        no = _rank.get(int(fid))
        base = int(math.floor(float(f.get("avg") or 0) + 1e-9))
        return f"{base}F{no}" if no else f"{base}F"

    fl = " · ".join(_flab(i) for i in ex.get("floors") or [])
    return f"1주 남음 — {fl} 보유 1주는 자동 매도에서 뺐어요. 그대로 두고, 팔려면 직접 매도해 주세요."


def run_one_share_notice(s, note, plan, d, live):
    """하루 한 번 '1주 남음' 메시지 (표시 파일 one_share_<날짜>.json — 보내기 성공 뒤에만 기록, 모의는 dry_ 접두)"""
    text = one_share_text(plan)
    if not text:
        return "해당 없음"
    mk = _alert_marker(s, "one_share", str(d), live)
    if os.path.exists(mk):
        return "이미 알림"
    if note.send(text) is not False:
        ConfigManager(s)._save_json(mk, {"date": str(d)})
    return "알림"


def new_floor_text(plan):
    """새 F 규칙 (풀이님 결정 2026-11-20 09:59): 새 F를 못 만들면 풀이님께 물어볼 글자, 아니면 None"""
    nb = (((plan.get("info") or {}).get("tower")) or {}).get("new_floor_blocked")
    if not nb:
        return None
    return (f"새 F를 만들 수 없어요 — {nb['text']}.\n"
            "자동으로 F·간격을 늘리거나 봇을 멈추지 않았어요. 새 F 매수만 쉬고 있고, 있는 F의 매도는 그대로예요.\n"
            "어떻게 할지 알려 주세요 (예: 총 한도 늘리기, F 수·F 완성 기준 금액 바꾸기, 이대로 두기).")


def run_new_floor_notice(s, note, plan, d, live):
    """새 F를 못 만드는 날마다 한 번 물어봄 (표시 파일 new_floor_<날짜>.json — 보내기 성공 뒤에만 기록, 모의는 dry_ 접두)"""
    text = new_floor_text(plan)
    if not text:
        return "해당 없음"
    mk = _alert_marker(s, "new_floor", str(d), live)
    if os.path.exists(mk):
        return "이미 알림"
    if note.send(text) is not False:
        ConfigManager(s)._save_json(mk, {"date": str(d)})
    return "알림"


def run_fx_tasks(s, note, live):
    """loop 의 한 번치 자동환전·알림 → 만든 MeritzApi(없으면 None). 환전 창 안이면 휴장 전날 알림(자동환전 꺼짐이어도) + 자동환전(켜져 있을 때),
    마감 60분 전~마감이면 달러부족 알림. 어떤 오류도 밖으로 안 던짐(주문·체결 반영 흐름 보호) — 하루 한 번 알림"""
    kst = now_kst()
    try:
        run_holiday_range_notice(s, note, live)         # v2.2.9 audit-fix 7-5: 범위 밖이면 꺼진 이유를 하루 한 번 알림 (실패해도 아래 흐름 계속)
    except Exception:
        logging.exception("휴장일 범위 알림 오류")
    fxw = fx_window_info(kst, s)["open"]
    short_due = shortage_alert_due(kst, s)
    if not (fxw or short_due):
        return None
    api = None
    try:
        api = MeritzApi(s["key_file"], os.path.join(s["state_dir"], "data", "meritz_token.json"))
        if fxw:
            run_closure_alert(s, note, live)
            if s.get("auto_fx_enabled"):
                run_fx_morning(s, api, note, live)
        if short_due:
            run_fx_shortage_alert(s, api, note, live)
    except Exception as e:
        logging.exception(f"자동환전·알림 중 오류: {type(e).__name__}")
        ek = "err_" + kst.strftime("%Y-%m-%d")
        if ek not in _FXM["warned"]:
            _FXM["warned"].append(ek)
            note.send(f"자동환전·알림 중 오류가 났어요 ({type(e).__name__}) — 환전은 안 했거나 기록을 확인해 주세요. 마감 60분 전에 달러부족 알림을 보내요.")
    return api


# ---------------------------------------------------------------- 체결 반영
def daily_close_text(s, d, items, tst, cfg=None):
    """v2.15.0 판 41 할 일 4 + v2.19.0 판 46: 마감 일일결산 메시지 글자 (텔레그램 1개). items = 그날 기록의 체결 있는 주문(fill_items), tst = 체결 반영·잔고 맞춤을 마친 F 상태.
    · 매매 횟수 = 체결이 1주라도 있는 주문 수 (매수+매도) · 매수/매도 주식수 = 그 주문들의 누적 체결 수량 · 변경 = 매수 − 매도 (순증감)
    · 보유 F = 수량이 있는 F 개수 · 진행중 F = 그중 미완성 F, 진행률 = F 원가 ÷ 그 F 목표(F 완성 기준 금액, 기본 $15,000)
    · 판 46: 당일 실현수익·매수/익절·누적실현은 realized_summary (봇 장부 기준 · 수수료·세금 미반영 · 기준은 그 함수 설명). cfg 가 없으면 이 세 줄은 '확인 불가'
    · 이모티콘: 📊 제목 · 💰 당일 실현수익 · 🛒 매수/익절 · 📈 누적실현 · 📦 보유 F · 🔨 진행중 F (매매·매수/매도 줄은 그대로)"""
    bq = sum(int(i["q"]) for i in items if i["side"] == "BUY")
    sq = sum(int(i["q"]) for i in items if i["side"] == "SELL")
    act = SN.active_floors(tst if isinstance(tst, dict) else {})
    base = TW.params(s)[0]
    lines = [f"📊 {d} 마감 일일결산"]
    try:
        if cfg is None:
            raise ValueError("cfg 없음")
        rs = realized_summary(cfg, d)
        lines.append(f"💰 당일 실현수익 {_usd_signed(rs['pnl'])} (봇 장부 기준 · 수수료·세금 미반영)")
        lines.append(f"🛒 당일 매수 {rs['buys']}회 · 익절 {rs['wins']}회 (이익 매도 주문 수)")
        lines.append(f"📈 누적실현 {_usd_signed(rs['total'])} ({str(rs['since'])[5:]}부터 기록)")
    except Exception as e:
        logging.warning(f"결산 실현수익 계산 실패 {type(e).__name__}: {str(e)[:100]}")
        lines.append("💰 당일 실현수익 확인 불가 (기록을 못 읽음)")
    lines += [f"· 매매 {len(items)}회 (체결 있는 주문 수)", f"· 매수 {bq}주 · 매도 {sq}주 · 변경 {bq - sq:+d}주 (매수−매도)", f"📦 보유 F {len(act)}층"]
    inc = [f for f in act if not TW.is_complete(f)]
    if inc:
        lbl = TW.floor_labels(tst)
        for f in inc:
            tgt = float(f.get("target") or base) or base
            lines.append(f"🔨 진행중 {lbl.get(int(f['id']), 'F')}: ${float(f.get('cost') or 0):,.0f} / ${tgt:,.0f} ({float(f.get('cost') or 0) / tgt * 100:.1f}%)")
    else:
        lines.append("🔨 진행중 F 없음 (보유 F 모두 완성)")
    lines.append("봇 장부 기준이라 메리츠 앱 실현손익과 다를 수 있어")
    return "\n".join(lines)


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
    rows = fill_rows_for(api, s, d)                   # v2.2.6: 체결 시각(t)까지 읽음 — 필드 이름 미확인이면 t 는 None → 매도 먼저
    items = fill_items(m, rows)
    done = None
    # v2.2.0 탑쌓기: F 상태 (파일이 없으면 이 체결들을 넣기 전 장부로 1F)
    _p0 = cfg.get_position() or {"qty": 0, "principal": 0.0}
    tst = tower_state_for(cfg, int(_p0["qty"]), float(_p0["principal"]), s)[0]
    # v2.2.6: 시간순(없으면 매도 먼저)·새 F 계획 매수는 매도 뒤·주문번호별 증분만 (장중에 이미 반영한 매도는 다시 안 넣음)·장부와 F를 같은 묶음으로 저장
    applied = apply_tower_fills(s, cfg, d, items, tst)
    # v2.18.0 판 45: 건별 체결 줄은 메시지에 안 써서 안 쌓음 (마감 일일결산이 요약해 보냄). done만 applied에서 계산.
    for a in applied:
        done = a["closed"] or done
    hold, _, _ = api.holding(s["symbol"])
    pos = cfg.get_position()
    if tst is not None:                   # 매일 동기화: 층 상태를 장부(실제 보유분)에 맞추고, 꼬인 층은 합침
        tst, _tnotes = TW.reconcile(tst, int(pos["qty"]), float(pos["principal"]), TW.params(s)[2], s)
        tst, _snotes = SA.adjust(tst, s)               # 판 33: 잔고 동기화의 둘째 일 — F 완성 기준 금액 조정 (시드가 안 바뀌었으면 아무것도 안 함)
        cfg._save_json(TOWER_FILE, tst)
    try:                                            # v2.2.6 체결 알림: 장중에 못 보낸(또는 아직 안 보낸) 몫만 — 주문별 notified_qty 기준
        send_fill_alerts(s, api, note, cfg, m, mark_path, items, d, tst)
    except Exception as e:
        logging.warning(f"체결 알림 중 오류 {type(e).__name__}")
    m["synced"] = True
    cfg._save_json(mark_path, m)
    # v2.18.0 판 45: 평소 체결 반영 메시지는 안 보냄 — 마감 일일결산이 같은 날 매매를 요약해서 보내. 비정상 때만 짧게 알림.
    alert = []
    if lost:
        alert.append(f"주문 응답을 못 받은 주문 {lost}건은 체결 내역에서 못 찾았어요 (체결 안 된 것으로 봄 — 잔고 확인이 맞는지 검사)")
    if done:
        alert.append("보유 0주가 되어 사이클 종료 처리됨 — 이 봇의 매도 규칙으로는 생기지 않는 상황, 확인 필요")
    if hold != pos["qty"]:
        cfg.halt(f"체결 반영 뒤 잔고 {hold}주 ≠ 장부 {pos['qty']}주")
        alert.append(f"정지: 잔고 {hold}주 ≠ 장부 {pos['qty']}주 (확인한 뒤 정지 해제)")
    if alert:
        note.send(f"{d} 체결 반영 확인 필요\n" + "\n".join(alert))
    try:                                            # v2.15.0 판 41 할 일 4: 마감 일일결산 (체결 반영 알림 바로 뒤, 별도 메시지 1개) — 실패해도 동기화는 이미 끝남
        realized_init(cfg, d)                      # 판 46: 기록 파일이 없으면 오늘을 누적 시작일로 만들어 둠
        note.send(daily_close_text(s, d, items, tst, cfg))
    except Exception as e:
        logging.warning(f"마감 일일결산 메시지 실패 {type(e).__name__}")
    return "완료"


LATE_FILL_DAYS = 4          # 늦은 체결은 최근 며칠(달력 기준) 기록만 다시 확인 — 오래된 기록을 처음 배포한 날 한꺼번에 조회하지 않음


def run_late_fills(s, api, note, mp, today):
    """판 23 수정1 S1: 동기화(기본 20:00 ET, 판 39)로 '반영 끝'이 된 날 기록(orders_<날짜>.json)에 대해, 그 뒤(장후)에 체결된 몫을 다음 날 첫 확인 때 장부·층에 반영.
    주문번호별 '이미 반영한 수량'을 층 상태가 갖고 있어 늘어난 몫만 들어감 (중복 반영 없음). 반영한 뒤 층 상태를 장부에 맞추고 알림. 확인을 한 번 마치면 late_done 표시 (같은 날 기록은 다시 안 봄).
    메리츠가 동기화 시각 이후 접수·체결을 하는지는 미확인 — 체결이 있을 때만 반영하고, 없으면 아무것도 안 바꿈. 조회가 실패하면 표시 안 하고 다음 반복에 다시"""
    cfg = ConfigManager(s)
    m = cfg._load_json(mp, {})
    if not isinstance(m, dict) or not m.get("synced") or m.get("late_done") or not m.get("orders") or str(m.get("date") or "") >= today:
        return "해당 없음"
    d = m["date"]
    fix = cfg._load_json(LEDGER_FIX_FILE, None)
    if isinstance(fix, dict) and str(d) <= str(fix.get("through") or ""):          # 판 24: 장부 바로잡기 날짜까지의 기록은 이미 실제 잔고에 들어 있음 → 다시 넣지 않음 (가짜 +69주 방지)
        m["late_done"] = True
        cfg._save_json(mp, m)
        return "장부 바로잡기 이전 기록 — 건너뜀"
    try:
        rows = fill_rows_for(api, s, d)
    except MeritzError as e:
        logging.warning(f"늦은 체결 확인 실패(다음에 다시): {str(e)[:100]}")
        return "조회 실패"
    items = fill_items(m, rows)
    _p0 = cfg.get_position() or {"qty": 0, "principal": 0.0}
    tst, had = tower_state_for(cfg, int(_p0["qty"]), float(_p0["principal"]), s)
    applied = apply_tower_fills(s, cfg, d, items, tst) if had else []
    lines = [f"- {SIDE_KO.get(a['side'], a['side'])} {a['dq']}주 @ ${a['da'] / a['dq']:.2f} ({a['o'].get('desc', '')})" for a in applied]
    if applied:
        pos = cfg.get_position()
        tst2, tnotes = TW.reconcile(tst, int(pos["qty"]), float(pos["principal"]), TW.params(s)[2], s)
        cfg._save_json(TOWER_FILE, tst2)
        lines += [f"  {x}" for x in tnotes]
        note.send(f"{d} 동기화 시각(20:00 ET) 이후에 체결된 주문을 오늘 아침 장부에 반영\n" + "\n".join(lines) + f"\n장부 {pos['qty']}주 평단 ${cfg.avg_price(pos):.2f}")
    m["late_done"] = True
    cfg._save_json(mp, m)
    return "반영" if applied else "없음"


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
        fast = None                          # 판 40: 스나이퍼 틱을 돌린 반복이면 (s, api, note) — 아래에서 30초 대기 대신 1.5초 틱
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
            api = run_fx_tasks(s, note, live)       # v2.0.8 자동환전 창·휴장 전날 알림·마감 60분 전 달러부족 알림 (실패해도 주문·체결 반영 흐름은 계속) → 만든 api 는 아래에서 재사용
            ot, dl = _hm(s["order_time_et"], datetime.time(10, 5)), _hm(s["order_deadline_et"], datetime.time(15, 40))
            if n.weekday() < 5 and OPEN_TIME_ET <= n.time() < datetime.time(16, 0) and load_open_price(s, n.strftime("%Y-%m-%d"), live) <= 0:
                try:      # v2.2.14 판 17: 주문 시각(기본 10:05)보다 일찍, 09:30 ET 이후 처음 확인한 현재가를 시초가로 저장 (실패해도 주문 흐름 계속 — 주문 시간에 다시 정함)
                    api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                    run_open_capture(s, api, live, n)
                except Exception as e:
                    logging.warning(f"시초가 확인 중 오류: {type(e).__name__}")
            if live:                     # 판 24: 일회성 장부 바로잡기 (실제 잔고 684주일 때만) — 늦은 체결 반영·스나이퍼 틱보다 먼저
                try:
                    api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                    run_ledger_migration(s, api, note, n.strftime("%Y-%m-%d"))
                except Exception as e:
                    logging.warning(f"장부 바로잡기 중 오류: {type(e).__name__}")
            if live:                     # 판 23 수정1 S1: 어제 이전 기록 중 16:10 뒤에 체결된 몫을 다음 날 첫 확인에 장부·층에 반영 — 오늘 스나이퍼 틱(잔고=장부 확인)보다 먼저
                for mp in pending_syncs(state):
                    try:
                        md = datetime.date.fromisoformat(os.path.basename(mp)[7:17])
                        if 0 < (n.date() - md).days <= LATE_FILL_DAYS:
                            api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                            run_late_fills(s, api, note, mp, n.strftime("%Y-%m-%d"))
                    except Exception as e:
                        logging.warning(f"늦은 체결 반영 중 오류: {type(e).__name__}")
            if sniper_on(s):          # v2.2.20 스나이퍼 모드 · 판 38: 00:00 ET ~ 체결 반영 시각 전 (실제 주문은 SN.buy_ok 04:07~16:00 · SN.sell_ok 04:00~04:06 빼고 전 구간 + 장운영 코드 확인). 옛 설명: 09:30 ET ~ 체결 반영 시각 전 (정규장 매수·정규장+장후 매도). 탑쌓기 주문 시간·당일 매도 확인은 안 돌림
                if sniper_tick_window(s, n):      # 판 23 수정1 B7: 모의도 돌림 (run_sniper_tick 이 모의면 주문 없이 시뮬레이션). 판 40: 평일·마감 시각 전 → 매도 창 (주말·야간까지) — 하루 기록 마감은 따로
                    try:
                        api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                        run_sniper_tick(s, api, note)
                        fast = (s, api, note)
                    except Exception as e:
                        logging.exception(f"스나이퍼 확인 중 오류: {type(e).__name__}")
                        if _SNIPER["err_day"] != n.strftime("%Y-%m-%d"):
                            _SNIPER["err_day"] = n.strftime("%Y-%m-%d")
                            note.send(f"스나이퍼 확인 중 오류가 났어요 ({type(e).__name__}) — 이미 낸 주문은 그대로예요. 서버 로그를 확인해 주세요.")
            elif n.weekday() < 5 and ot <= n.time() <= dl:
                api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                run_order_day(s, api, note, live)
            # v2.0.3 당일 매도 확인 + v2.2.6 체결 반영·알림 (실패해도 주문·체결 반영 흐름은 계속). 주문 마감(order_deadline_et) 뒤~체결 반영 시각 전에는 새 매도 주문 없이 체결 반영·알림만
            if live and not BB.assassin_blocks(state) and not sniper_on(s) and n.weekday() < 5 and ot <= n.time() < _hm(s["sync_time_et"], datetime.time(20, 0)):
                try:
                    api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                    run_intraday_sell(s, api, note, allow_new_sells=(n.time() <= dl))
                except Exception as e:
                    logging.exception(f"당일 매도 확인 중 오류: {type(e).__name__}")
                    if _INTRA["err_day"] != n.strftime("%Y-%m-%d"):
                        _INTRA["err_day"] = n.strftime("%Y-%m-%d")
                        note.send(f"당일 매도 확인 중 오류가 났어요 ({type(e).__name__}) — 이미 낸 주문은 그대로예요. 서버 로그를 확인해 주세요.")
            if live and not BB.assassin_blocks(state):                 # 판 41: 암살자 실전이면 하이브리드 마감 동기화(잔고=장부 대조)도 멈춤 — 암살자 보유분이 장부와 달라서
                today = n.strftime("%Y-%m-%d")
                for mp in pending_syncs(state):
                    md = os.path.basename(mp)[7:17]
                    if md < today or n.time() >= _hm(s["sync_time_et"], datetime.time(20, 0)):
                        m = ConfigManager(s)._load_json(mp, {})
                        if (m.get("orders") or m.get("attempts")) and not m.get("synced", True):
                            api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                            run_sync(s, api, note, mp)
        except Exception as e:
            logging.exception(f"반복 중 오류: {type(e).__name__}")
            try:
                Notifier(load_settings()["telegram_file"]).send(f"봇에 오류가 났어요 ({type(e).__name__}): {str(e)[:200]}")
            except Exception:
                pass
            idle(120)
            fast = None
        if fast:
            sniper_fast_wait(30, *fast)      # 판 40 할 일 1: 30초 동안 틱 간격(기본 1.5초)마다 스나이퍼 틱 (되돌리기: sniper_tick_sec=30 이면 예전처럼 idle(30))
        else:
            idle(30)


def cmd_check(s):
    print(f"7번 메리츠 SOXL 하이브리드 {BOT_VERSION} 점검 (주문 없음)")
    bad = validate_settings(s)
    idb, fp = check_identity(s)
    print(f"- 봇 {'켜짐' if s.get('enabled') else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'} · "
          f"입고 확인 {'됨' if s.get('transfer_confirmed') else '전'} · 토스 스나이퍼 정지 확인 {'됨' if s.get('toss_sniper_stopped_confirmed') else '전'}")
    print(f"- 키 지문: {fp or '-'} (기대값 {'있음' if s.get('expected_key_fp') else '없음'})")
    print(f"- 전략: {strategy_ko(s)}")
    for b in bad + idb:
        print("  -", to_korean(b))
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
    open_px = load_open_price(s, now_et().strftime("%Y-%m-%d"), not s.get("dry_run", True))      # v2.2.14: 저장된 시초가만 읽음 (점검은 시초가를 정하지 않음)
    with in_dir(state):
        plan = build_plan(s, ConfigManager(s), price, fx, cash, q, principal, sellable, open_px=open_px)
    orders, notes = plan["orders"], plan["notes"]
    print("- 오늘 계획 (미리보기·주문 안 냄):\n  " + to_korean(plan_head(plan, s)).replace("\n", "\n  "))
    print("  " + to_korean(fmt_orders(orders)).replace("\n", "\n  "))
    for n in notes:
        print("  ·", to_korean(n))
    fxp = hybrid_fx_plan(s, cash, 1)      # v2.3.0: 환전 필요량 = F 완성 기준 금액 × 하루 매수 F 수 (부족 달러는 shortfall_usd — 예전엔 이 키가 없어 늘 '필요 없음'으로 나왔음)
    print(f"  환전 기준: {fxp['fx_basis']} · 예수금 ${cash:,.0f} · 부족 ${math.ceil(fxp['info']['shortfall_usd']):,}")
    with in_dir(state):
        r = auto_fx(s, api, ConfigManager(s), fxp, False, now_et().strftime("%Y-%m-%d"))
    print("  " + (fx_lines(r).strip().replace("\n", "\n  ") if r else ("환전: 자동환전 꺼짐" if not s.get("auto_fx_enabled") else "환전: 부족 달러 없음 (필요 없음)")))
    if hold != q:
        print(f"  잔고 {hold}주 ≠ 장부/시작 {q}주 → 입고 전이거나 다른 계좌")
    return 0


# ---------------------------------------------------------------- 추가 투입 (주문 없음)
def sell_target(s, cfg, pos):
    """표시용: 매도 목표가 = 평단 × (1+매도%) 올림 (전체 평단 기준 — 탑쌓기는 층별 목표가 따로 있음)"""
    avg = cfg.avg_price(pos)
    return ceil2(avg * (1 + float(s["sell_profit_pct"]) / 100.0)) if avg > 0 else 0.0


def cmd_add_shares(s, qty, avg, api=None):
    """메리츠 잔고 == 장부 + qty 일 때만 장부 갱신 → 0(성공)/1(거부)"""
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
            bad.append("장부 시작 전 (먼저 기타 → 장부 시작)")
        if bad:
            print("추가 투입 반영 안 함:\n" + "\n".join("- " + to_korean(b) for b in bad))
            return 1
        api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
        hold, _, _ = api.holding(s["symbol"])
        want = int(pos["qty"]) + qty
        note = Notifier(s["telegram_file"], dry_run=s.get("dry_run", True))
        if hold != want:
            msg = f"추가 투입 반영 안 함: 메리츠 잔고 {hold}주 ≠ 장부 {pos['qty']}주 + {qty}주 = {want}주 (주문 없음)"
            print(msg)
            logging.warning(msg)
            note.send(msg)
            return 1
        g0 = sell_target(s, cfg, pos)
        # v2.2.6 (사용자 결정): 토스 입고분은 1층 빈곳에 넣고, 1층 평단 기준 탑쌓기로 나머지 빈칸을 채움. 층 상태는 장부에 넣기 '전' 값에서 시작 (파일이 없으면 넣기 전 장부로 1F)
        tst0, _had = tower_state_for(cfg, int(pos["qty"]), float(pos["principal"]), s)
        before, after = cfg.add_shares(qty, avg, n.strftime("%Y-%m-%d"))
        _fid, tw_notes = TW.add_holdings(tst0, qty, avg, s)
        cfg._save_json(TOWER_FILE, tst0)
        tw_txt = "\n탑쌓기: " + " / ".join(tw_notes)
        g1 = sell_target(s, cfg, after)
        a0, a1 = cfg.avg_price(before), cfg.avg_price(after)
        msg = (f"추가 투입 반영 {qty}주 @ ${avg:.2f} (주문 없음)\n"
               f"전: {before['qty']}주 · 원금 ${before['principal']:,.0f} · 평단 ${a0:.2f} · 매도 목표 ${g0:.2f}\n"
               f"후: {after['qty']}주 · 원금 ${after['principal']:,.0f} · 평단 ${a1:.2f} · 매도 목표 ${g1:.2f}" + tw_txt)
        hist = cfg._load_json("data/add_shares_log.json", [])
        hist.append({"at": n.isoformat(), "qty": qty, "avg": avg, "hold": hold,
                     "before": {"qty": before["qty"], "principal": before["principal"], "avg": a0},
                     "after": {"qty": after["qty"], "principal": after["principal"], "avg": a1}})
        cfg._save_json("data/add_shares_log.json", hist)
        logging.info(msg.replace("\n", " | "))
        print(msg)
        if cfg.get_halt():
            print(f"정지 표시는 그대로 있음: {cfg.get_halt().get('reason')} (확인한 뒤 정지 해제)")
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
        print("장부 시작 안 함:\n" + "\n".join("- " + to_korean(b) for b in bad))
        return 1
    api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
    hold, _, _ = api.holding(s["symbol"])
    want = int(float(s["start"]["qty"]))
    if hold != want:
        print(f"메리츠 잔고 {hold}주 ≠ 시작 수량 {want}주 — 입고 미완료 또는 다른 계좌")
        return 1
    with in_dir(state):
        cfg = ConfigManager(s)
        pos, wrote = cfg.inject_start(overwrite=overwrite)
        print(("장부 시작: " if wrote else "이미 장부 있음 (덮어쓰려면 덮어쓰기 확인): ")
              + f"{pos['qty']}주 · 원금 ${pos['principal']:,.0f} · 평단 ${cfg.avg_price(pos):.2f}")
    return 0


# ---------------------------------------------------------------- v2.0.8 읽기 전용 점검: 달러 예수금이 앱과 다를 때
_DIAG_SKIP = re.compile(r"acnt|acct|account|cano|pwd|pass", re.I)


def cmd_diag_cash(s, api=None):
    """읽기 전용 (주문·환전·장부 변경 없음). 메리츠 외화잔고 응답의 USD 행을 필드별로 그대로 보여 줌 → 메리츠 앱 '외화예수금' 숫자와 같은 필드가 무엇인지 찾는 용도.
    봇은 USD 행의 estm_frcr_amt 를 달러 예수금으로 씀 (meritz_api.usd_cash, v2.0.9 — frcr_amt는 주식 가치를 포함해 앱 값과 달라서 바꿈. 서버 진단 2026-11-19 확인). 보유 주식 가치(보유 수량 × 전일 종가)도 같이 보여 줘서 차이가 그것과 비슷한지 대조"""
    api = api or MeritzApi(s["key_file"], os.path.join(s["state_dir"], "data", "meritz_token.json"))
    d = api._call("GET", "/accounts/v1/me/overseas/currencies")
    rows = d.get("data")
    print(f"7번 메리츠 SOXL 탑쌓기 {BOT_VERSION} --diag-cash (읽기 전용 · 주문/환전 없음)")
    print(f"- 응답 이어보기 표시(tr_cont): {d.get('tr_cont')!r} · 행 수: {len(rows) if isinstance(rows, list) else '목록 아님'}")
    usd = [r for r in rows if isinstance(r, dict) and str(r.get("crcd", "")).strip().upper() == "USD"] if isinstance(rows, list) else []
    print(f"- USD 행 {len(usd)}개 (1개여야 정상)")
    for r in usd:
        for k, v in r.items():
            print(f"    {k} = {'(가림)' if _DIAG_SKIP.search(str(k)) else v}")
    try:
        bot_cash = api.usd_cash()
        print(f"- 봇이 쓰는 값 (estm_frcr_amt) = ${bot_cash:,.2f}")
    except MeritzError as e:
        bot_cash = None
        print(f"- 봇이 쓰는 값 읽기 실패: {e}")
    hold, _sellable, _ex = api.holding(s["symbol"])
    p = api.price(s["symbol"], s["price_market"])
    val = hold * float(p.get("prev_close") or 0)
    print(f"- 보유 {s['symbol']} {hold}주 × 전일 종가 ${float(p.get('prev_close') or 0):.2f} = ${val:,.2f} (주식 가치 대략)")
    print("- 읽는 법: 메리츠 앱의 외화예수금(달러) 숫자와 같은 값인 필드를 위에서 찾으세요. v2.0.9부터 봇은 estm_frcr_amt를 씁니다.")
    print("  봇 값 − 앱 값 ≈ 주식 가치이면 frcr_amt 에 주식 가치가 섞여 있는 것입니다 (v2.0.9에서 estm_frcr_amt로 바꿈).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="7번 메리츠 SOXL 탑쌓기")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fingerprint", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--inject-start", action="store_true")
    g.add_argument("--clear-halt", action="store_true")
    g.add_argument("--diag-cash", action="store_true", help="읽기 전용: 외화잔고 USD 행을 필드별로 출력 (달러 예수금이 앱과 다를 때)")
    g.add_argument("--add-shares", action="store_true", help="직접 산 주식을 지정 평단으로 장부 반영 (--qty N --avg X)")
    ap.add_argument("--overwrite", action="store_true", help="--inject-start 때 기존 장부 덮어쓰기")
    ap.add_argument("--qty", type=int, help="--add-shares: 추가한 주식 수 (1 이상)")
    ap.add_argument("--avg", type=float, help="--add-shares: 추가한 주식의 평단 (달러)")
    a = ap.parse_args(argv)
    s = load_settings()
    if a.fingerprint:
        print(key_fingerprint(s["key_file"]))
        return 0
    if a.check:
        return cmd_check(s)
    if a.diag_cash:
        return cmd_diag_cash(s)
    if a.add_shares:
        return cmd_add_shares(s, a.qty, a.avg)
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
