# 사무실 상황판 · 접속 감시 · 파일 권한 자동 정리 (묶음 A+B)
- 상태: **완료(파일 작성·가짜 환경 검사까지)** — 시작 2026-10-28 11:58 KST (02:58 UTC) · 완료 12:20 KST (03:20 UTC)
- 업로드·승인·서버 적용·실제 확인: 아직 (사용자 진행)
- AI / 기기: Claude / 사용자 폰·태블릿
- 기준: main be75e87 (작업 직전 다시 받음, 변경 없음). 이어지는 기록: 2026-10-28_claude_office-connection.md (원인·서버 직접 조치)
- 범위: bot_office/ 의 사무실 웹·주소 관리·업데이트 비서, docs/handoff/05_office.md. 1~4번 봇·팬딩 매매 로직·전략·금액·enabled 는 건드리지 않음.
- 다른 AI 진행중 작업: docs/log 에 '진행중' 상태 기록 없음. 대기 중인 업로드 없음.

## 바꾼 파일 (머리말 vNEXT → 승인 때 실제 번호로 자동 기입, 예상 사무실 v1.0.55)
- `bot_office/bot_updater.py` — 사무실 파일 읽기 권한 자동 정리(주인 유지·그룹 쓰기 없음) + 상황판용 STATUS 복사본(/var/lib/bot-office/status.md)
- `bot_office/office_url.py` — 터널 주소를 cloudflared /quicktunnel 에 먼저 물음 · 5분마다 내부/바깥 접속 감시, 2번 연속 실패 알림·복구 알림 · /주소 에 접속 상태
- `bot_office/server.py` — `/` 를 상황판으로, `/api/board` 추가 (픽셀 `/pixel-office`, 운영 `/operations` 그대로)
- `bot_office/office_board.py` (새 파일) — 상황판 데이터, 보기 전용, 금액·주소·비밀값 없음
- `bot_office/board.html` (새 파일) — 폰 기준 상황판 화면 (방 6개, 1분마다 갱신, 밝은/어두운 화면)
- `docs/handoff/05_office.md` — 12절 추가

## 검증 (가짜 환경)
- 문법 검사 4개 통과.
- office_url: 가짜 /quicktunnel 로 주소 찾기 → 주소 바뀜 알림 · 바깥 실패 1회 무알림 → 2회째 알림 1번 → 3회째 무알림 → 복구 알림 1번 · 내부 실패는 '사무실 서버' 원인으로 구분. 상태 파일 0644, 한 줄 JSON 은 상태 변화 때만.
- server: 로그인 전 `/` 303, 로그인 후 `/` 200(상황판), `/pixel-office` 200, `/api/board` 200.
- 화면: 390px 폭 밝은/어두운 캡처 확인, 신호등 표시 오류 1건 발견·수정.
- 권한 정리: 600/700 파일 → server.py 그룹·읽기로 고침, 주인 유지, 두 번째 실행 0건.
- 재생 시나리오 4(대시보드 실패): 접속 실패 시 원인 코드·사용자에게 보인 알림이 한 줄 JSON 으로 남는지 확인. 요청 ID 는 아직 없음.
- 실제 서버·텔레그램·실계좌는 실행하지 않음.

## 적용 뒤 확인할 것
- 6. Update 완료 알림에 '사무실 파일 읽기 권한 고침' 줄이 있으면 무엇이 고쳐졌는지 기록.
- 사무실 주소 로그인 → 상황판 첫 화면. 기록실의 '최근 적용'은 이번 적용 뒤부터 보임.
- 약 10분 뒤 7번 비서 `/주소` → '마지막 접속 확인: 정상'.

## 남은 일
- 대시보드 요청 ID·사용자에게 보인 오류 문구 로그 (start.md 시나리오 4 완성)
- 상황판 '마지막으로 실제 일한 시각' (봇별 재생 로그 위치가 정해지면)
- 기록실에 재생 로그 검색 (correlation_id)
- 고정 도메인 이동 (보류, 접속 감시로 당분간 임시 주소 유지)

## 다음 AI가 읽을 파일
START.md → STATUS.md → docs/handoff/05_office.md(12절) → 이 기록 → bot_office/office_board.py, office_url.py, bot_updater.py(_office_perm, office_perm_repair)
