# 7번 메리츠 SOXL 탑쌓기 변경 기록

## v1.9.2 · 2026-11-22 (KST) — 판 32 3차 (meritz_laoer v2.9.0 5차, 래칫·하드캡·RSI 수확 거래 흐름 연결)
- 파일: sniper_adapter.py, sniper_mode.py, main.py, CHANGELOG.md, test_hybrid_v320.py(저장소 밖). 안 바뀜: tg_menu.py, tower_strategy.py, orig_sniper/* 등
- 내용: 질문 4·5 반영. 거래 루프가 시세를 읽을 때마다 SN.trail_tick(dry·live 2곳) → 1층(가장 낮은 박스) 고정 +1.5% 매도가 원작 트레일링으로 바뀜(점화 +1.5%·샤프 래칫·하드캡 +6.0%·RSI 65 수확). 원작 흐름 그대로: 실호가가 점화가 밑이면 슬롯 해제, 보존선 이탈 신호인데 실호가가 정지가 이상이면 취소, 매도 하한가 = 보존선 이상(하드캡이면 캡 가격), 2층 동반 졸업. 졸업(전 층 전량)은 그대로 우선. 보존선·최고점은 메모리에만 두고 sniper_state.json 에 저장 안 함(재시작하면 다시 계산). 어댑터 sell_targets·sell_plan 에 exclude_l1 추가(원작 exclude_daytime_l1). 스토커 보류·VWAP 방어·HA 음봉 청산 안 함
- 검증: v320 36개 · v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250 16개 통과 · pyflakes 새 경고 0 · 실거래·서버 적용·push 없음

## v1.9.1 · 2026-11-22 (KST) — 판 32 2차·부분 (meritz_laoer v2.9.0 4차, 래칫·하드캡·RSI 수확 어댑터까지)
- 파일: sniper_adapter.py, sync_orig.py, orig_sniper/ORIGIN.json, orig_sniper/{sniper_exit_plugin.py, assassin_plugin.py, barbell_plugin.py, quant_indicators_plugin.py}(새, 원작 d9170fa 바이트 동일 — 해시로만 검증), CHANGELOG.md, test_hybrid_v320.py(저장소 밖). 안 바뀜: sniper_mode.py, main.py, tg_menu.py, tower_strategy.py 등
- 내용: 원작 sniper_exit_plugin.py 복사(질문 1 (a)) — import 에 필요한 3개도 같이 복사, ORIGIN.json files 로 등록(watch 에서 뺌)·sync_orig --check 가 import 까지 확인. 어댑터에 l1_trail_slot·l1_trail_sync·l1_trail_step·minute_key 추가 = 원작 SniperL1TrailSlot·_step_l1_trail_slot_candidate 호출 (단리 S-112: 샤프 래칫·하드캡 +6.0%·RSI 65 수확). 입력은 봇이 모은 1분 종가로 만든 값, 스토커·VWAP 방어·HA 음봉 청산은 안 함. ⚠ 새 의존성: quant_indicators_plugin 이 numpy·pandas 를 import. 거래 코드에는 아직 연결 안 함
- 검증: v320 24개 · v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250 16개 통과 · pyflakes 새 경고 0 · sync_orig --check 통과 · 실거래·서버 적용·push 없음

## v1.9.0 · 2026-11-22 (KST) — 판 32 1차·부분 (meritz_laoer v2.9.0 4차, 스토커·래칫·하드캡 이식 중)
- 파일: sniper_adapter.py, CHANGELOG.md, test_hybrid_v320.py(새, 저장소 밖), test_hybrid_v300.py(저장소 밖, 분봉 입력 금지 검사에서 어댑터 제외 1곳 수정). 안 바뀜: sniper_mode.py, main.py, tg_menu.py, tower_strategy.py 등, orig_sniper/*
- 내용: 어댑터에 단리 Case 112 정책(rebound_policy = S-112: 스토커 +0.25%·VWAP -3.0%·샤프 래칫·하드캡 6.0%·RSI 65)과 스토커 판정 래퍼(stalker_fire = 원작 evaluate_stalker_reversal_fire) 추가. 거래 코드에는 아직 연결 안 함 — 래칫·하드캡 실행부(SniperL1TrailSlot)가 원작 sniper_exit_plugin.py 안이라 복사본에 없고, 분봉·VWAP 입력이 메리츠 API 에 없어 Muse 결정 대기(질문란)
- 검증: v320 9개 · v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250 16개 통과 · pyflakes 새 경고 0 · 실거래·서버 적용·push 없음

## v1.8.1 · 2026-11-22 (KST) — 판 31 질문 3 (meritz_laoer v2.9.0 3차, 원작식 부분 주문)
- 파일: sniper_mode.py, main.py, CHANGELOG.md, test_hybrid_v310.py(저장소 밖). 안 바뀜: sniper_adapter.py, tg_menu.py, tower_strategy.py, sub_grid.py, config.py, notifier.py, orig_sniper/*
- 내용: 원작 execute_bulletproof_sell_sweep 방식 — 매도 주문 전 매도가능 수량을 2초(0.25초 간격) 기다림(SN.wait_sellable) · 목표(닿은 박스 합, 졸업이면 전 박스)에 매도가능이 모자라면 평단 낮은 박스부터 가능한 만큼만 주문(마지막 박스는 일부 수량) · 장외 매도가능 0이면 주문 없이 조용히 대기 · 정규장 0이면 원작처럼 목표 수량 시도. 부분 체결 정산은 기존 _apply_sell 이 체결 수량만큼만 박스를 줄임(남은 박스·남은 수량은 장부에 그대로 — 시험으로 확인). '전부 아니면 무'는 안 함 (Muse 결정)
- 검증: v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250(수정) 16개 통과 · pyflakes 새 경고 0 (main.py 기존 5건·sniper_mode.py 기존 1건 그대로) · 실거래·서버 적용·push 없음

## v1.8.0 · 2026-11-22 (KST) — 판 31 (meritz_laoer v2.9.0 2차)
- 파일: sniper_mode.py, sniper_adapter.py, CHANGELOG.md, test_hybrid_v310.py(새, 저장소 밖), test_hybrid_v250.py(저장소 밖, test_04 기대값 1줄 수정). 안 바뀜: main.py, tg_menu.py, tower_strategy.py, sub_grid.py, config.py, notifier.py, orig_sniper/*
- 내용: 스나이퍼 매도 판정(box_rows)을 원작 evaluate_multi_grid_sell_targets 로 연결 (방식 B = 전체 층 그대로, Muse 결정; 비교 결과 A·B 동일). 미완성 층 박스 전체를 한 묶음으로: 1층 +1.5% · 2층 +1.0%(닿으면 1층도 같이) · 3층 이상 개별 매도 없음 · 졸업(3층~끝 가중평단 +1.0%)에 닿으면 전 박스 전량. 동작 변경(Muse 수락): 3층 이상 개별 +1.0% 매도 사라짐, '층마다 L1' → 전체 한 묶음 L1. 탑 매도·매수·서브 안 바뀜
- 검증: v310 14개 · v300 25개 · v270 7개 · v260 31개 · v250(수정) 16개 통과 · pyflakes 새 경고 0 (기존 copy 미사용 1건) · 실거래·서버 적용·push 없음

## v1.7.0 · 2026-11-22 (KST) — 판 30 (meritz_laoer v2.9.0 1차)
- 파일: sniper_mode.py, main.py, tg_menu.py, sniper_adapter.py, README.md, CHANGELOG.md, test_hybrid_v300.py(새, 저장소 밖). 안 바뀜: tower_strategy.py, sub_grid.py, config.py, notifier.py, orig_sniper/*
- 내용: 매수 신호 판정을 원작 복사본(어댑터 경유)으로 연결. B1 눌림 깊이 = 층(박스) 수 · B2 상한 = 가장 낮은 층 평단 · B3 눌림·돌파 % 비교 · B3b RSI 모르면 돌파 안 막음 · B4 서브 가동일 기록(seed_main_day). 매도·탑쌓기·서브 매수 규칙은 안 건드림
- 검증: test_hybrid_v300.py 25개 통과 · v270 7개·v260 31개 통과 · v250 16개 중 2개 실패(B1 이 바꾼 가정 — 되돌리면 통과) · 실거래·서버 적용·push 없음

## v1.6.0 · 2026-11-22 (KST) — 판 29 1차 (구조만, meritz_laoer v2.9.0 은 미완)
- 파일(새): orig_sniper/{quant_engine_core.py, quant_engine.py, toss_api_core.py (원작 d9170fa 바이트 동일), toss_api.py (shim), ORIGIN.json}, sniper_adapter.py, sync_orig.py, test_hybrid_v290.py(저장소 밖). 바뀜: README.md, CHANGELOG.md. 매매 코드(main.py·sniper_mode.py 등)는 안 바뀜
- 내용: 원작 순수 판정 함수 복사본 + 얇은 어댑터 + 원작 업뎃 적용 도구 + README 대응표(3단계 문서). 아직 매매에 연결 안 함 — 동작은 v2.7.0 과 같다. 미구현: 원작 이식 연결·스토커·래칫·바벨·탑쌓기 매매 모드·텔레그램 개편·잔고 동기화 시드 조정·용어(층·F) 변경 (VERIFY.md 미구현 절)
- 검증: test_hybrid_v290.py 13개 통과 · 기존 시험 v270·v260·v250 은 이 세션에 파일이 없어 미실행 · pyflakes 새 경고 0 · 실거래·서버 적용·push 없음
## v1.5.0 · 2026-11-21 (KST) — 판 27 (meritz_laoer v2.7.0)
- 파일: main.py, sniper_mode.py, tower_strategy.py, tg_menu.py, config.py, notifier.py, README.md, CHANGELOG.md, test_hybrid_v270.py(새). sub_grid.py 는 안 바뀜
- 내용: 층 간격 사용자 설정(tower_gap_usd) 제거 — 텔레그램 '층 간격 변경' 버튼·설정 검사·설정 표시·계획 '새 층 가격' 줄 삭제. 간격은 내부 고정값 GAP_USD=5로 칸 만들기에만 씀 (tower_strategy.params가 항상 5를 돌려줌). 설정 파일에 tower_gap_usd가 남아 있어도 무시·통과. 매매 로직은 안 건드림.
- 검증: test_hybrid_v270.py 통과 · 기존 시험(v260·v250) 통과 · pyflakes 새 경고 0. 자세한 건 VERIFY.md
## v1.4.0 · 2026-11-21 (KST) — 판 26 (meritz_laoer v2.6.0)
- 파일: main.py, sniper_mode.py, tower_strategy.py, tg_menu.py, config.py, notifier.py, README.md, CHANGELOG.md, test_hybrid_v260.py(새). sub_grid.py 는 안 바뀜
- 내용: ① 박스별 매도 — 미완성 층의 매수 1건 = 박스 1개(floor['boxes']), 박스마다 자기 평단 기준 매도(그 층 안 최저 평단 박스 +1.5% · 나머지 +1.0%, 그 박스 전량), 층 원가·수량은 판 박스 몫만 줄고 층 평단은 남은 박스 가중평균, 층 완성 → 탑 매도. 예전 상태(박스 없음)·탑 매도 잔여 = 박스 1개 ② 눌림 매수% 설정 sniper_portion_pct(기본 8, 0 초과 100 이하) + 텔레그램 '눌림 매수% 변경'. 돌파 16%·서브 4% 그대로
- 검증: test_hybrid_v260.py 통과 · 기존 시험(v250·v240)·Golden 은 파일이 없어 미실행 · 실거래·서버 적용·push 없음. 자세한 건 VERIFY.md
## v1.3.0 · 2026-11-21 (KST) — 판 25 (meritz_laoer v2.5.0)
- 파일: main.py, sniper_mode.py, sub_grid.py(새), tower_strategy.py, tg_menu.py, config.py, notifier.py, test_hybrid_v250.py(새)
- 내용: 하이브리드 박스·층 (토스 스나이퍼 이식): 매수 1번 = 박스 시드(기본 $15,000)의 8% · 서브 그리드 4% · 박스 안 자동 매도(+1.5%/+1.0%) 복귀 · 층 간격 규칙 삭제 · 첫 기준가 설정 · 평단 정수 달러 층 이름 · 지하층→공사중 · 퍼센트 작업 계산(percent_plan). 판 24 선택 질문 코드는 남기고 안 부름.
- 수정1(돌파 매수액): 설정 sniper_breakout_portion_pct(기본 16%, 눌림 8% 그대로) + 텔레그램 '돌파 매수% 변경' 메뉴.
- 검증: test_hybrid_v250.py 16개 통과 · pyflakes 새 경고 0 · import 확인. test_hybrid_v240.py·Golden 비교는 파일이 없어 미실행. 실거래·서버 적용 없음.

## v1.2.9 · 2026-11-21 11:08 (KST)
- 파일: main.py, notifier.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 판 24 meritz_laoer v2.4.0 (층 나눔·잠금·스나이퍼 선택: 장부 바로잡기 684주·지하층·선택 버튼·업데이트 알림 판 번호). 검증: 새 시험 18개 통과, 기존 시험 40개 통과·3개 실패(의도한 변경), 해시 전부 일치, 비밀 0건.
- 브랜치: staging

## v1.2.8 · 2026-11-21 09:05 (KST)
- 파일: main.py, sniper_mode.py, tg_menu.py
- 내용: meritz_laoer v2.3.0 (판 23 수정1: 장중 환전 고침 제외·하루 매수 층 수 제한·B3 미체결 조회·B7 모의 스나이퍼·S3 눌림 잠금·S1 16:10 뒤 체결 다음 날 반영·라벨 고침·죽은 코드 제거). 검증: 새 시험 43개 통과, 기존 시험 17개 통과·27개 실패(의도한 변경), 해시 전부 일치, 비밀 0건.
- 브랜치: staging

## v2.4.0 · 2026-11-21 (KST) — 판 24 (office 번호는 적용 때 확정, 미확인)
- 파일: tower_strategy.py, sniper_mode.py, main.py, tg_menu.py, notifier.py, bot_office/bot_updater.py, README.md, CHANGELOG.md, VERIFY.md (+ 새 시험 test_hybrid_v240.py)
- 내용: meritz_laoer v2.4.0 (판 24) — ① 일회성 장부 바로잡기(실제 잔고 684주일 때만, 층 373주 $40.29 · 311주 $48.14 잠금 + 지하층) ② 잠금=탑 매도 ③ 지하층부터 스나이퍼 매수 ④ 스나이퍼 목표 도달 시 자동 매도 대신 텔레그램 선택(스나이퍼/탑쌓기) ⑤ 업데이트 알림 맨 앞 판 번호 · 수동 확인이 대기 목록 표시
- 브랜치: staging 에 올리기 전 (검토 대기)

## v1.2.8 수정1 · 2026-11-21 (KST) — 버전 v2.3.0 그대로 (판 23 수정1, 풀이님 정정 반영)
- 파일: main.py, sniper_mode.py, tg_menu.py, README.md, CHANGELOG.md, test_hybrid_v230.py
- 내용: ① (풀이님 결정으로 뺌) 장중 환전 고침 — auto_fx 마커·하루 한 번 환전은 v2.3.0 그대로, test_intraday_fx_exchanges_only_shortfall 도 그대로 ② 하루 매수 층 수 제한: 그날 매수 주문이 나간 층 수가 tower_max_buy_layers_per_day(기존 설정, 새 설정 없음)에 닿으면 새 층 매수는 안 하고 알림만(하루 한 번), 거절·취소 주문은 안 셈, 이미 산 층의 남은 시드 채우기는 계속 ③ B3 미체결 판단을 미체결 조회(open_orders_today)로 (앱에서 취소한 주문은 매수·매도 잠금에서 빠짐) ④ B7 모의에서도 스나이퍼 틱이 돌되 주문 없이 시뮬레이션 기록(dry_orders_<날짜>.json) ⑤ S3 눌림 깊이 = max(현재 층 수, 사이클 최고 층수) — sniper_state.json peak_layers, 0주면 초기화 ⑥ S1 16:10 동기화 뒤 체결은 다음 날 첫 확인 때 장부·층에 반영(최근 4일 기록, late_done 표시) ⑦ 정리: pyflakes 새 경고 5개, '목표 도달' 라벨, 죽은 코드 defer_sell·limit_morning_sells 제거
- 브랜치: staging 에 올리기 전 (검토 대기)

## v1.2.8 · 2026-11-21 (KST)
- 파일: tower_strategy.py, sniper_mode.py, config.py, main.py, tg_menu.py, notifier.py, README.md, CHANGELOG.md (+ 새 시험 test_hybrid_v230.py)
- 내용: meritz_laoer v2.3.0 (판 23 하이브리드 — 매수는 스나이퍼, 완성 층은 탑 매도): 모드 선택(trading_mode)·모드 버튼 삭제 · 사기=스나이퍼(눌림·돌파)만 · 층 시드에 닿은 층은 완성 → 탑 매도(평단 +10% → 50%), 미완성(재매수 대기 포함) 층은 스나이퍼 매도(1층 +1.5%·상단 +1.0%·전량), 한 층에 매도 둘이 같은 날 겹치지 않음 · 총 시드·층 수 한도 없음(total_krw 선택·tower_floors 무시) · 새 층 = 가장 낮은 층 평단 − tower_gap_usd(기본 5) 이하일 때 · 탑 매도 체결도 스나이퍼 기준가 갱신 · 환전(아침 = 층 시드 × 하루 매수 층 수 · 장중 자동환전 · 달러부족 알림 · 휴장 전날 rounds · --check 부족 달러 표시 고침) · 텔레그램 메뉴를 스나이퍼 봇 형식(첫 화면 4개 · 레이더 · 잔고 동기화 · 전술 제어반 · 환전, 인라인 버튼)으로 새로 만듦, 시스템 업데이트 버튼 삭제 · 표시 고침(B8). 16:10 동기화·장부=잔고 정지·체결 중복 방지·주문 시간·스나이퍼 신호 숫자·매도 %는 그대로. 수정1 고침 중 B3·B7·S3·S1 은 수정1 원문이 이 판 자료에 없어 미반영(질문란)
- 브랜치: staging 에 올리기 전 (검토 대기)

## v1.2.7 · 2026-11-21 (KST)
- 파일: sniper_mode.py(새 파일), tower_strategy.py, config.py, main.py, tg_menu.py, notifier.py, README.md
- 내용: meritz_laoer v2.2.20 (판 22 듀얼 모드 — 스나이퍼 + 탑쌓기): 설정 trading_mode(tower 기본 | sniper) · 텔레그램 첫 메뉴 모드 버튼 · 스나이퍼 매매(눌림·돌파 재장전 / 층 전량 익절, 익절 % 는 설정 sniper_tp_l1_pct 1.5 · sniper_tp_upper_pct 1.0) · 층·장부 공유 · 스나이퍼 봇 형식 실시간 상황판. 탑쌓기 로직·주문 시간·16:10 동기화·장부=잔고 정지 규칙은 그대로
- 브랜치: staging

## v1.2.6 · 2026-11-20 19:09 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz_laoer v2.2.18 (판 21 거래 내역·봇 상태 버튼 오류 고침): _local 이 4개(pos·halt·avg·tgt)를 돌려주는데 ledger_text·power_text 가 5개로 풀어서 ValueError 가 나던 것을 4개로 고침. 매매 로직·문구 변경 없음. 회귀 시험 3개 통과(서버 실제 상태로 재현·확인), 기존 시험 38개 통과, test_v226 기존 실패 6개와 동일.
- 브랜치: staging

## v1.2.5 · 2026-11-20 19:00 (KST)
- 파일: config.py, main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.17 (판 20 하루 매수·매도 층 수 설정 + 수정1 아침 매도 N_sell): 설정 키 2개(tower_max_buy_layers_per_day·tower_max_sell_layers_per_day, 1~3, 없으면 1) + 텔레그램 버튼 2개, 매수 계획·장중 매도·아침 계획 매도가 그 층 수만큼 사고팔게 함. N=1은 기준 v2.2.15와 5,118 항목 동일.
- 브랜치: staging

## v1.2.4 · 2026-11-20 18:02 (KST)
- 파일: main.py, tower_strategy.py
- 내용: meritz_laoer v2.2.15 (판 19 오늘 계획 미리보기에 탑 진행률): plan_head 한 곳에 탑 줄과 채우는 층 진행률 추가, 표시만 바꿈 (매매·주문·장부 그대로). make_plan이 floors 각 층에 target 키를 실음 (표시 전용)
- 브랜치: staging

## v1.2.3 · 2026-11-20 16:46 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.14 (판 17 시초가 상한): 오늘 채우는 층의 안 산 칸이 시초가를 넘지 않게 상한, 시초가는 09:30 ET 이후 첫 확인가로 그날 한 번만 정해 저장
- 브랜치: staging

## v1.2.2 · 2026-11-20 13:53 (KST)
- 파일: main.py, tg_menu.py
- 내용: audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6
- 브랜치: staging

## v1.2.1 · 2026-11-20 12:26 (KST)
- 파일: main.py, notifier.py, tg_menu.py
- 내용: 7번 이름 변경: 속쓸 적립봇 → SOXL 탑쌓기, 7번 v2.2.11, 사무실 v1.9.6, 브리핑 1.1.1
- 브랜치: staging

## v1.2.0 · 2026-11-20 12:17 (KST)
- 파일: accum_strategy.py, config.py, main.py, notifier.py, tg_menu.py, tower_strategy.py
- 내용: audit-fix-v2 r3: 7번 탑쌓기 전용 (사다리 삭제) + 전 봇 구멍 고침, 7번 v2.2.10, 사무실 v1.9.5 (bot_updater 병합)
- 브랜치: staging

## v1.1.9 · 2026-11-20 06:39 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.8 (하루에 한 층 매수): 안 산 칸 전부 주문
- 브랜치: staging

## v1.1.8 · 2026-11-20 06:18 (KST)
- 파일: config.py, main.py, meritz_api.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.6 (판 16 본격): 층별 매도·반칸 표시·체결 알림
- 브랜치: staging

## v1.1.7 · 2026-11-20 05:31 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.5: 1층 채우기 매수 (판 16 일부)
- 브랜치: staging

## v1.1.6 · 2026-11-19 21:53 (KST)
- 파일: config.py, main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.4: 1층 시작가 설정 메뉴
- 브랜치: staging

## v1.1.5 · 2026-11-19 21:37 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.3: 층 칸 색상 + 다음 회차 가격별 배정
- 브랜치: staging

## v1.1.4 · 2026-11-19 21:23 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.2: tower layer visualization (pan 14) - tower_lines in status board, view_lines in tower_strategy, filled layers only
- 브랜치: staging

## v1.1.3 · 2026-11-19 20:54 (KST)
- 파일: accum_strategy.py, config.py, main.py
- 내용: fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1
- 브랜치: staging

## v1.1.2 · 2026-11-19 20:42 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.0: tower stacking (pan 13) - new tower_strategy.py module, strategy switch (default ladder), migration from holdings, slippage handling
- 브랜치: staging

## v1.1.1 · 2026-11-19 17:08 (KST)
- 파일: main.py
- 내용: meritz_laoer v2.1.0: merge pan 12 intraday sell gate fix onto menu 3rd v3
- 브랜치: staging

## v1.1.0 · 2026-11-19 16:49 (KST)
- 파일: main.py, notifier.py, tg_menu.py
- 내용: 텔레그램 매매봇 메뉴 정리 3차 v3: 7번 v2.0.9 기준 재적용 + 6번 문구 정리
- 브랜치: staging

## v1.0.9 · 2026-11-19 14:44 (KST)
- 파일: main.py, meritz_api.py, tg_menu.py
- 내용: meritz_laoer v2.0.9: usd_cash reads estm_frcr_amt (pan 11, Q27 fix)
- 브랜치: staging

## v1.0.8 · 2026-11-19 14:24 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz_laoer v2.0.8: auto FX in realtime window, shortage alert, holiday pre-FX, --diag-cash (pan 10)
- 브랜치: staging

## v1.0.7 · 2026-11-19 13:43 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz_laoer v2.0.7: auto FX at 09:00 KST, one round per day (pan 9)
- 브랜치: staging

## v1.0.6 · 2026-11-18 18:01 (KST)
- 파일: config.py, main.py, tg_menu.py
- 내용: meritz_laoer v2.0.1: 텔레그램 메뉴 정리 (메인 4개 카테고리, 전술 설정, 상황판 설정값 표시)
- 브랜치: staging

## v1.0.5 · 2026-11-18 16:53 (KST)
- 파일: accum_strategy.py, config.py, main.py, meritz_api.py, notifier.py, tg_menu.py
- 내용: meritz: SOXL 적립봇 v2.0.0 — 사다리·부분매도·재매수·자동환전 (방 meritz-soxl-dca-bot)
- 브랜치: staging

## v1.0.4 · 2026-11-14 13:57 (KST)
- 파일: main.py, notifier.py, tg_menu.py
- 내용: bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT)
- 브랜치: staging

## v1.0.3 · 2026-11-14 10:25 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz split: 4번 주식만·SGOV 비서봇·무매봇 메뉴 (dca v1.2.6, laoer v1.0.3, office vNEXT)
- 브랜치: staging

## v1.0.2 · 2026-11-08 10:11 (KST)
- 파일: config.py, main.py
- 내용: 메리츠 무매 평단 조절 추가 meritz_laoer v1.0.2
- 브랜치: staging

# meritz_laoer.service 변경 기록

## v1.0.1 · 2026-11-08 03:52 (KST)
- 파일: config.py, global_throttle.py, main.py, meritz_api.py, notifier.py, strategy_v14.py
- 내용: meritz settings.example.json 제거 (구버전 업데이터가 .json을 거부해 묶음 적용이 막힘 — 서버 설정은 이미 /etc/meritz-laoer/settings.json으로 설치됨)
- 브랜치: staging

