# 7번 메리츠 SOXL 탑쌓기 변경 기록

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

