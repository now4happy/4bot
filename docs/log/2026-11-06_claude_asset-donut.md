# 2026-11-06 · Claude · 상황판 자산 현황 (도넛 2개)

- 기준: main f16b9f7 (bot-office-v1.3.6) · board.html 8d2aa48 · office_board.py 8dcb7eb
- 바꾼 파일: bot_office/board.html, bot_office/office_board.py (사무실 vNEXT)
- 새 파일: bot_office/asset_board.py (시트 읽기 → 비율 저장), bot_office/test_asset_board.py
- 내용: 상황판 탭 봇 신호등 삭제 → 자산 현황(자산 구성 보라 · 투자 종목 주황 도넛, 기준일 작게, 큰 조각 라벨 안 · 작은 조각 지시선, 범례 없음)
- 데이터 흐름: 구글 시트 '입력정리' A14:Z14 · A83:B87 · A91:B99 → asset_board.py --write (root 타이머 15분) → /var/lib/bot-office/assets/assets.json(이름·%·기준일만, 0644) → office_board.assets() → /api/board 의 assets → board.html
- 비밀값: 새로 없음. 키움 가져오기의 서비스 계정을 spreadsheets.readonly 범위로 같이 씀
- 남은 일: (1) 서버 타이머 1회 설치 (VERIFY.md 의 명령) (2) --probe 로 A열 이름 칸이 실제 이름인지 확인 — 자산 구성 기본 이름(현금/주식·ETF·코인/보험·연금/오피스텔)은 추측
- 다음 AI가 읽을 파일: 이 기록, bot_office/asset_board.py 머리말, docs/handoff/05_office.md (상황판 금액 규칙 예외 반영 필요 시)

## 2차 (Muse 검토 3가지 수정 · 같은 날)
- asset_board.py: A열 이름 앞 퍼센트("42.7% 현금")를 떼고 씀 (보드 라벨 이중 표시 버그) · 기본 이름을 실제 A열 이름에 맞춤
- asset_board.py: kiwoom_holdings.py import 삭제, HTTP·openssl 서명 부품 내장 (키움 파일 파기해도 동작)
- 서비스 계정: 1차 기록의 "새 비밀값 없음"은 틀림 — 키움 서비스 계정은 만들어진 적 없음. 새 서비스 계정 + 시트 '보기' 공유 + /etc/bot-office/google_sa.json 설치가 필요 (사용자 승인·작업). kiwoom.json 대체 읽기 삭제
- test_asset_board.py: 14개 (실제 A열 형식·키움 없음·키 파일 없음·내장 서명 추가)
- 남은 일: 서비스 계정 설치 → 타이머 설치 (VERIFY.md 5번 A·B). 타이머만으로는 도넛이 안 뜸
