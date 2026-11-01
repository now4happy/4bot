# 2026-11-01 Muse — alert-hub 연동 2차 (매매 봇 notify, 한투 제외)

- 범위: 분류안 승인 뒤, 1차 적용 확인 후 진행
  - 3번 토스 적립 (dca_engine.py): 예수금 부족 critical 2곳, 정상/익절/스킵 보고 info, 주문 실행 오류 critical
  - 4번 빗썸 적립 (main.py): SMA 접수 info / 결과 확인 필요 critical, 잔액 부족 critical,
    익절 응답 없음 critical / 익절 완료 info, 정기매수 완료 info / 응답 없음 critical / 매수 실패 critical / 매수 미진행 원화 부족 critical
  - 2번 토스 스나이퍼 (main.py): 슬림 알림 출구에만 hub 복사 (info, ⚠️ 제목은 warning).
    중앙 send_message는 버튼 답장도 쓰므로 건드리지 않음. 래퍼가 아닌 tg 출구 1곳에만 넣어 중복 방지.
  - 제외: 1번 한투 (원작 코드, 별도 검증 뒤), 버튼/명령 답장, 매매 로직·전략·종목·금액·enabled 무변경
  - 기존 텔레그램 전송은 그대로, hub 호출은 try/except로 감싸고 import 실패 시 no-op
- 변경 파일 3개: toss_sniper/main.py, toss_dca_bot/dca_engine.py, bithumb_laoeo_bot/main.py
- 검증: 전 파일 py_compile 통과
- 서버 적용: 아직 안 함 — 텔레그램 6. Update 가장 마지막 알림 승인 대기
