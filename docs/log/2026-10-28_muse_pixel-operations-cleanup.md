# 픽셀 사무실·운영 화면 삭제 · 수집기 유지
- 상태: **파일 작성·diff·문법 검사 완료, staging 업로드·SSH·승인·서버 적용 미완료**
- 기준: main 36ed101 (사무실 v1.0.57, 2026-10-28 13:10 KST 적용). 이전 기록: 2026-10-28_claude_secretary-cleanup.md
- 범위: bot_office/server.py, docs/handoff/05_office.md(15절), 이 기록. 삭제 파일 6개, 매매 봇·팬딩·브리핑·수집기는 건드리지 않음.
- 결정: 시장분석 점수 입력 화면을 쓰지 않음, 상황판으로 충분함, 픽셀 자료는 다 지워도 됨, 수집기는 남김, 점수·결재 기록은 필요없어 지움. 현 묶음(비서 정리 v1.0.57) 적용 확인 뒤 다음 묶음으로 진행하기로 사용자 결정.
- 검증: main server.py 대비 삭제 주소만 빠짐을 diff로 확인, server.py 문법 통과, board.html은 /api/board·/api/server-care만 참조, 남은 파일의 지운 모듈 import 없음 확인. 실제 서버 주소 응답(404 등)은 승인·적용 뒤 확인 필요.
- 남은 일: staging 업로드 → SSH 자료 폴더 백업 이동 → 연결로 6개 파일 삭제 → 6. Update 마지막 알림 승인 → /pixel-office·/operations 404, 상황판·/api/status 정상, inventory 갱신 확인.

## 다음 AI가 읽을 파일
START.md → STATUS.md → `docs/handoff/05_office.md`(12~15절) → 이 기록 → bot_office/server.py
