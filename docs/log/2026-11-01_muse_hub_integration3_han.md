# 2026-11-01 Muse — alert-hub 연동 3차 (1번 한투)

- 상태: 2차 적용(979c745) 확인 뒤 staging에 올림. 2차가 대기 중일 때는 push를 보류했었음.
- 범위: 원작 코드라 매매 로직·API 호출·주문 흐름 무변경, 기존 텔레그램 전송 뒤에 hub 복사만 추가, 전부 try/except
  - scheduler_regular.py: 스케줄러 오류 스킵 critical 2곳, 통신 복구 warning 2곳,
    API 지연 warning 2곳(5회마다 1번인 기존 전송 지점), 긴급 최종 실패 critical 2곳
  - main.py: 달력 API 타임아웃/에러 warning 2곳 (평일 강제 개장)
  - 제외: 종목별 장전/이관 메시지 info (이미 사용자에게 직접 가고, hub 브리핑에 또 모으면 중복·소음),
    수동 취소 (사용자 동작, 자율 아님), 내부 재시도 dict 전송 지점
- 변경 파일 2개: hantu_laoer/scheduler_regular.py, hantu_laoer/main.py
  (하트비트는 이미 1차에서 scheduler_sniper 60초 job에 들어감)
- 검증: 전 파일 py_compile 통과, 비밀 값 추가 없음
- 서버 적용: 아직 안 함 — 텔레그램 6. Update 가장 마지막 알림 승인 대기
