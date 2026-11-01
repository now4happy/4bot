# 2026-11-01 Muse — hub 자동 설치 unittest 명령 고침

- 기준: main 0cc48acd (사무실 v1.0.81, hub 자동 설치 적용 완료)
- 문제: 13:27 텔레그램 알림 — hub 설치가 unittest 단계에서 실패
  `ImportError: Start directory is not importable: '/home/gieokkim/alert-hub/tests'`
  원인: `unittest discover -s <절대 경로>/tests -t <hub 폴더>` 조합은 tests 폴더를 import할 수 없어 실패함.
  venv·pip·.env 단계는 그 전에 성공했음 (실패 문장이 테스트 단계에서 나옴).
- 변경 파일: bot_office/bot_updater.py 1개
  - unittest를 `sh -c "cd <hub 폴더> && <venv python> -m unittest discover -s tests"` 로 바꿈
  - 머리말 사무실 vNEXT 줄 추가
- 검증: py_compile 통과, 로컬에서 같은 sh -c 형태로 19개 테스트 OK 확인
- 서버 적용: 아직 안 함 — 텔레그램 6. Update 가장 마지막 알림 승인 대기
- 승인 뒤 예상: 업데이터가 다시 시작하면서 hub 설치를 다시 시도함 (cron이 없어 미설치로 판단됨).
  .env는 이미 있으므로 덮어쓰지 않고, unittest 통과 뒤 테스트 메시지·cron 순서로 진행됨.
