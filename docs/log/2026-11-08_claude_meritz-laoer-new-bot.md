# 2026-11-08 Claude — 메리츠 SOXL 무매 새 봇 (meritz_laoer v1.0.0) 초안

- 지시: 메리츠 이관계획 v1.2 · 2번 지시문 v1.2 (토스 218주 기준). Muse 검토만, push·서버 적용·재시작·실주문 없음.
- 기준: main c53f8d4, 대기 업로드 없음. 메리츠 openapi.json 2026-10-28.
- 바꾼 파일: 새 폴더 meritz_laoer/ 8개 (strategy_v14.py·global_throttle.py 는 hantu_laoer 바이트 동일 복사). 기존 파일 수정 0개.
- 이유: hantu_laoer 는 그대로 두고, V14 무한매수 핵심만 메리츠 API(즉시주문 LOC/MOC/지정가)로 새 봇에서 운영.
- 검증: 테스트 54/54 통과 (가짜 API). 상세는 제출 ZIP 의 VERIFY.md.
- 남은 일: 업데이트 비서 대상 등록·서비스 생성·서버 설정 파일, 익절% 서버값 확인, 메리츠 즉시주문 접수 시각·체결내역 기준일 확인, 분할수·시드 확정, 입고 후 inject-start → 모의 → 승인.
- 다음 AI가 읽을 파일: meritz_laoer/README.md, meritz_laoer/main.py (안전장치), 이 기록.
- 다음 작업: 3번 토스 스나이퍼 리셋 → 4번 토스적립 메리츠 4번 이관 검토 (2번 Muse 검토 뒤).
