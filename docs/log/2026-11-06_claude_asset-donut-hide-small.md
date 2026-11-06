# 2026-11-06 · Claude · 자산 도넛 작은 조각 숨기기 (자산 구성만)

- 기준: main 4668151 (bot-office-v1.3.7) · asset_board.py 28e6fe0 · test_asset_board.py b7e05ea
- 바꾼 파일: bot_office/asset_board.py, bot_office/test_asset_board.py (사무실 vNEXT) · board.html·office_board.py 변경 없음
- 내용: 자산 구성(mix) 차트만 반올림 % < 1.0 항목을 items 에서 뺌 (HIDE_BELOW = {"mix": 1.0}). 합계·다른 항목 %·check·zero 그대로. 투자 종목(stock)은 숨기지 않음. mix 기본 이름 '보험·연금·오피스텔' → '간접자산'. update() version → vNEXT
- 결과(현재 비율): 자산 도넛 현금·주식·ETF·간접자산 3개 (코인 0.1% 숨김, 1% 이상 되면 자동 표시) · 투자 도넛 8개 그대로
- 주의: 반올림은 기존 round() 그대로라 0.95% → 0.9% (숨김), 0.96% → 1.0% (보임)
- 검증: test_asset_board.py 18개 통과 · dry-run 자산 3개 항목 · --probe 출력 이전과 같음
- 다음 AI가 읽을 파일: 이 기록, 2026-11-06_claude_asset-donut.md, bot_office/asset_board.py 머리말
