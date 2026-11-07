# 2026-11-08 Claude — 메리츠 적립 새 봇 (meritz_dca_bot v1.0.0) 초안

- 지시: 메리츠 적립 새 봇 지시문 v1.1 · 이관 상태 파일 v1.0. Muse 검토만, push·서버 적용·재시작·실주문 없음.
- 기준: main 69488925, 대기 업로드 없음. 메리츠 openapi.json 2026-10-28.
- 바꾼 파일: 새 폴더 meritz_dca_bot/ 7개 (replay_log.py 는 3번과 바이트 동일). 기존 파일 수정 0개.
- 이유: 3번 toss_dca 는 그대로 두고, 3번 적립 엔진을 메리츠 4번 계좌(미국주식 NKE·QLD)로 옮김.
- 검증: 가짜 API 테스트 65/65 통과. 상세는 제출 ZIP 의 VERIFY.md.
- 결정 필요: 정수 주문 이월(carry) 방식 승인, 시장가 05 첫 실주문 확인.
- 발견: 3번 상세 화면의 일차 자동 추정이 분할매도·정지 시작 직후에도 일차를 덮어씀 (3번은 수정 안 함, 별도 지시 필요).
- 남은 일: 업데이트 비서 targets·NAMES 등록, 서비스·상태 폴더·settings.json, 입고 뒤 --inject-start → 모의 → 승인.
- 다음 AI가 읽을 파일: meritz_dca_bot/README.md, meritz_dca_bot/main.py (안전장치·execute_us_step), 이 기록.
