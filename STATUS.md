# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-08 05:25 (KST) · 계기: 업데이트 적용 (staging: 업데이터: NAMES에 meritz_dca.service 추가 (메리츠 적립, 사무실 vNEXT))

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-01 17:16 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-07 13:24 KST부터) | v1.2.0 | 2026-11-07 13:25 | 하단 메뉴 2개로 줄이기 (2번 v2.4.1·tg_ui v2.3.1·사무실 vNEXT) |
| 3번 토스 적립 | `toss_dca` | 🟢 실행 중 (11-05 09:02 KST부터) | v4.3.8 | 2026-11-05 09:02 | 3번 토스 적립 v4.3.8: R1 단계 단조화 + 정지·결정 중 알림 + 가격 0 가드 + N7 지수 20 |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-01 14:57 KST부터) | v4.3.3 | 2026-11-01 14:58 | feat: alert-hub 연동 2차 — 매매 봇 자율 알림 |
| 5번 사무실 비서 | `bot-office` | 🟢 실행 중 (11-07 13:45 KST부터) | v1.4.7 | 2026-11-08 05:25 | 업데이터: NAMES에 meritz_dca.service 추가 (메리츠 적립, 사무실 vNEXT) |
| 메리츠 SOXL 무매 | `meritz_laoer` | 🟢 실행 중 (11-08 03:52 KST부터) | v1.0.1 | 2026-11-08 03:52 | meritz settings.example.json 제거 (구버전 업데이터가 .json을 거부해 묶음 적용이 |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-07 13:45 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-06 13:28 KST부터)
- 사무실 터널 `bot-office-tunnel`: 🟢 실행 중 (10-20 22:54 KST부터)
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-08 03:52 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 36% (남은 13.1GB)

## 최근 적용 10건

- 2026-11-08 05:25 · 5번 사무실 비서 v1.4.7 · bot_updater.py · 업데이터: NAMES에 meritz_dca.service 추가 (메리츠 적립, 사무실 vNEXT)
- 2026-11-08 03:52 · 메리츠 SOXL 무매 v1.0.1 · config.py, global_throttle.py, main.py, meritz_api.py, notif · meritz settings.example.json 제거 (구버전 업데이터가 .json을 거부해 묶음 적용이
- 2026-11-08 03:52 · 5번 사무실 비서 v1.4.6 · bot_updater.py · meritz settings.example.json 제거 (구버전 업데이터가 .json을 거부해 묶음 적용이
- 2026-11-07 13:46 · 5번 사무실 비서 v1.4.5 · office_briefing.py, office_secretary.py · 브리핑 수동 --manual + 메뉴 사무실 주소 버튼 삭제 (office_briefing.py·office
- 2026-11-07 13:25 · 5번 사무실 비서 v1.4.4 · bot_updater.py, office_secretary.py · 하단 메뉴 2개로 줄이기 (2번 v2.4.1·tg_ui v2.3.1·사무실 vNEXT)
- 2026-11-07 13:25 · 2번 토스 스나이퍼 v1.2.0 · main.py, tg_ui_plugin.py · 하단 메뉴 2개로 줄이기 (2번 v2.4.1·tg_ui v2.3.1·사무실 vNEXT)
- 2026-11-07 12:06 · 5번 사무실 비서 v1.4.3 · asset_board.py, board.html, office_board.py, test_asset_boar · 사무실 vNEXT: 현금 금액 표기 + 투자 종목 증권사별 색
- 2026-11-07 09:43 · 2번 토스 스나이퍼 v1.1.9 · assassin_plugin.py, main.py, plugin_updater.py, quant_engine · 2번 스나이퍼 v2.4.0 Case 93 [모의] 암살자 이식 (하드락 True, 실주문 없음)
- 2026-11-06 17:39 · 5번 사무실 비서 v1.4.2 · asset_board.py, board.html, office_board.py, test_asset_boar · 자산 현황 하이브리드: 도넛+막대+수익률 (사무실 vNEXT)
- 2026-11-06 17:13 · 5번 사무실 비서 v1.4.1 · board.html · 자산 현황 도넛 2개 파이 지름 같게 (사무실 vNEXT)

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
