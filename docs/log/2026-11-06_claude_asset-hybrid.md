# 2026-11-06 · Claude · 자산 현황 하이브리드 (자산 도넛 + 투자 막대 + 수익률)

- 기준: staging 2f1cff4 (bot-office-v1.4.1)
- 바꾼 파일 (사무실 vNEXT): bot_office/board.html, bot_office/asset_board.py, bot_office/office_board.py, bot_office/test_asset_board.py
- office_board.py: 지시서에는 '건드리지 않음'이었으나, assets()가 정해진 칸만 /api/board로 보내 returns가 빠지므로 사용자 승인(2026-11-06 16:2x)을 받아 returns 전달만 추가
- 대체: c207521(두 도넛 지름 맞추기, v1.4.1)의 minHalf 로직 삭제 · assets_band_bars ZIP(띠+막대 전체 교체)은 쓰지 않음(막대 코드만 가져옴)
- board.html: 자산 구성 = v1.3.7 도넛 그대로(최대 240px · 사용자 결정) · 투자 종목 = 가로 막대(prep·barsHTML) · 카드 맨 아래 '수익률 월 -7.7% · 수익률 년 +0.5% (2026-11)' (returns 없으면 숨김) · 320px 폭 넘침 막는 그리드 한 줄
- asset_board.py: '입력정리'!A67:H78 추가 읽기 → B(총자산)가 있는 마지막 행의 D(월 수익률)·H(1년 수익률)를 %로 → returns {month, monthly, yearly} · 금액 저장 안 함 · 시트 실패 때 이전 returns 유지 · 시트를 읽었는데 표가 비면 returns 뺌 · dry-run 수익률 1줄 · --probe 그대로 · update() version "v1.3.8" → "vNEXT"(승인 때 채움)
- 검증: test_asset_board.py 28개 통과(18 → 28) · verify_hybrid.py(headless 크롬 320·360·390·1280px, 라이트·다크) 통과 · 실제 서버·폰 확인 안 함
- 남은 일: Muse 검토 → staging 업로드 → 텔레그램 승인 → 서버 적용 뒤 폰 확인 · 1월(2027)이 되면 월별 표 범위 A67:H78·RETURNS_YEAR=2026 확인 필요
- 다음 AI가 읽을 파일: 이 기록, 2026-11-06_claude_asset-donut.md, bot_office/asset_board.py·office_board.py 머리말
