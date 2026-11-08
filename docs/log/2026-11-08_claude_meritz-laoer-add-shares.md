# 2026-11-08 Claude — 메리츠 무매 추가 투입 평단 조절 (meritz_laoer v1.0.2)

- 지시: 메리츠 무매 추가 투입 평단 조절 기능 v1.1. Muse 검토만, push·서버 적용·재시작·실주문 없음.
- 기준: main 79557f6 (11-07 21:11 UTC), STATUS meritz_laoer v1.0.1, 대기 업로드 없음, 태그 meritz_laoer-v1.0.1 = main 과 같음.
- 바꾼 파일: meritz_laoer/main.py, meritz_laoer/config.py, meritz_laoer/README.md (3개). strategy_v14.py·meritz_api.py·notifier.py·global_throttle.py·CHANGELOG.md 그대로.
- 이유: 사용자가 직접 산 주식을 지정 평단으로 장부에 반영 (입고 평단 안 씀).
- 검증: 문법 통과, 테스트 38/38 통과 (가짜 잔고·가짜 텔레그램). 상세는 VERIFY.md.
- 남은 일: Muse 검토 → staging 업로드 → 승인. 리버스 모드 중 추가 투입 시 rem_cash 는 안 바꿈 (지시 범위 밖, 아래 VERIFY 참고).
- 다음 AI가 읽을 파일: meritz_laoer/main.py (cmd_add_shares), meritz_laoer/config.py (add_shares), 이 기록.
