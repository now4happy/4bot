# 2026-11-01 Muse — alert-hub 폴더 보관용 staging (업데이터 무시 적용 뒤)

- 기준: main = staging = b76e994 (사무실 v1.0.80, 업데이터 alert-hub 무시 처리 적용 완료)
- 내용: alert-hub/ 원본 20개 파일 + BOT_NAMES.md (이름 8번 사무실 비서로 업데이트)
- 범위: 보관만. 업데이터는 이 폴더를 적용 대상으로 보지 않으므로, 이 staging이 서버에 적용돼도
  어떤 봇 서비스도 재시작하지 않고, hub 설치·venv·cron도 하지 않음. 실제 hub 실행은 서버 직접 설치 단계에서 따로 함.
- 비밀: .env 파일 없음. .env.example의 토큰·채팅ID·API키 칸은 모두 비어 있음.
- 검증: py_compile 통과 (alert_hub/*.py)
- 서버 적용: 아직 안 함 — 텔레그램 6. Update 가장 마지막 알림 승인 대기
