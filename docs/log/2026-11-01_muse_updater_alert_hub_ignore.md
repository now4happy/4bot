# 2026-11-01 Muse — 업데이터 alert-hub 무시 처리

- 기준: main 8402a6a (staging도 동일, 대기 업로드 없음)
- 변경 파일: bot_office/bot_updater.py 1개
  - classify() 시작 부분에 alert-hub/ 경로 skip 추가: 거부 목록에 넣지 않고, 적용 대상에도 넣지 않음
  - 머리말 변경 기록에 사무실 vNEXT 줄 추가 (적용 때 실제 번호로 자동 기입됨)
- 의도: alert-hub 파일이 같이 묶여도 다른 봇 업데이트가 "허용되지 않은 파일"로 막히지 않게 함
- 범위: 보관만. alert-hub 실제 설치는 여전히 서버 직접 설치로, 업데이터가 hub를 설치·재시작하지 않음
- 검증: py_compile 통과, classify 테스트 5건 통과
  - alert-hub .py/.md만 있으면 units={}, bad=[]
  - 스나이퍼/사무실 파일 + alert-hub 파일이 섞이면 봇 파일만 units, bad=[]
  - 모르는 폴더 파일은 여전히 bad로 거부됨
- 비밀: 추가된 내용에 비밀값 없음 (기존 SECRET_RE 패턴 문구만 원래 파일에 있음)
- 서버 적용: 아직 안 함 — 텔레그램 6. Update 가장 마지막 알림 승인 대기
