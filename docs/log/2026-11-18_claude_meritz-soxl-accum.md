# 2026-11-18 Claude — 메리츠 속쓸 적립봇 (meritz_laoer v2.0.0 초안)

- 지시: 노션 작업 페이지 '메리츠 속쓸 적립봇' (방 슬러그 meritz-soxl-dca-bot). Muse 검토만, push·서버 적용·재시작·실주문 없음.
- 기준: main cee85d2 (STATUS 2026-11-18 10:44 KST, 7번 meritz_laoer v1.0.4, 대기 업로드 없음).
- 결정: 새 봇 대신 기존 meritz_laoer 를 고쳤다 (키 지문·텔레그램·장부·정지 장치·메뉴 재사용, 한 계좌에 봇 둘이 겹치는 위험 없음). 7번 무매(V14)는 이 봇으로 대체됨 — 노션 Q8.
- 바꾼 파일: meritz_laoer/ accum_strategy.py(새), config.py, main.py, meritz_api.py(적용환율 조회 추가), notifier.py, tg_menu.py, README.md. strategy_v14.py·global_throttle.py 그대로(strategy_v14 는 이제 안 불림).
- 사용자 추가 요청: 입고될 SOXL 을 평단에 반영 + 1회차 매수 때 그 원가 차감 → `--add-shares --credit` / `start.first_round_credit_usd`.
- 사용자 추가 요청(14:14): 필요달러 계산 + 자동환전 → `auto_fx_*` 설정(기본 꺼짐)·`MeritzApi.krw_cash/fx_exchange`(meritz_dca_bot 형식)·main.auto_fx. 실환전·실호출 없음.
- 검증: 가짜 API 테스트 29/29 통과 (test_accum.py, 제출 첨부). 실계좌·실주문·서버 미실행. 미확인 목록은 VERIFY.md.
- 남은 일: 노션 Q1~Q6·Q10 답 → 설정값 채움 → --check → 입고 → inject-start → 모의 → 승인.
