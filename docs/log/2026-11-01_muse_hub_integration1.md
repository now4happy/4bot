# 2026-11-01 Muse — alert-hub 연동 1차 (분류안 승인 뒤)

- 범위: 사용자 승인 (2026-11-01, 간단 설명 뒤 "이대로 진행해")
  - 전 봇 하트비트: 1번(60초 job), 2번(메인 루프), 3번(50초 스케줄러), 4번(모니터 루프),
    8번(웹서버 백그라운드 스레드 60초), 5번(팬딩 메인 루프), 6번(업데이터 루프), 7번(비서 루프)
  - 자율 알림 hub 복사: 7번 PC 감시(오프라인 critical / 복구 info / 매직스플릿 warning),
    5번 팬딩(가격표 도착 info / 판독 1차 실패 warning / 5번 실패 critical)
  - 제외: 7번 비서 브리핑 자체 (중복 방지), 버튼/명령 답장, 매매 로직·전략·종목·금액·enabled 무변경
  - 기존 텔레그램 전송은 그대로 (1~2주 병행), hub 호출은 전부 try/except로 감싸고
    hub import 실패 시에도 봇은 계속 동작 (helper가 None이면 no-op)
- 변경 파일 9개: bot_office/pc_monitor.py, office_secretary.py, server.py, fanding_trade.py, bot_updater.py,
  hantu_laoer/scheduler_sniper.py, toss_sniper/main.py, toss_dca_bot/main.py, bithumb_laoeo_bot/main.py
- 검증: 전 파일 py_compile 통과, 비밀 값 추가 없음 (경로는 서버 공용 /home/gieokkim/alert-hub만 사용)
- 주의: 이 staging 적용 시 사무실 버전은 굴림으로 v1.1.0이 된다 (최대 태그 v1.0.82 → 중간 +1).
  매매 봇 notify 사이트(주문 실패·잔고 부족 등)는 다음 staging에서, 이 1차 적용 뒤 hub 상태 확인 후에 진행한다.
- 서버 적용: 아직 안 함 — 텔레그램 6. Update 가장 마지막 알림 승인 대기
