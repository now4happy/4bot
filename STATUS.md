# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-13 17:51 (KST) · 계기: 업데이트 적용 (staging: 06_updater.md에 옛 브랜치 지우기 버튼 설명 추가 (방: 포트폴리오))

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-12 15:28 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-13 15:23 KST부터) | v1.2.7 | 2026-11-13 15:23 | sniper: plugin_updater commits synced files after direct ups |
| 3번 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-13 16:34 KST부터) | v1.2.4 | 2026-11-13 16:34 | meritz_dca v1.2.4: 관제탑 지금/완성 시 예상 토글 제거, 진행률은 항상 지금 기준 (방: 3 |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-12 15:28 KST부터) | v4.3.3 | 2026-11-01 14:58 | feat: alert-hub 연동 2차 — 매매 봇 자율 알림 |
| 5번 사무실 비서 | `bot-office` | 🟢 실행 중 (11-13 17:15 KST부터) | v1.8.1 | 2026-11-13 17:43 | 업데이터 옛 브랜치 되풀이 방지 (bot_updater vNEXT) (방: 포트폴리오) |
| 메리츠 SOXL 무매 | `meritz_laoer` | 🟢 실행 중 (11-12 15:28 KST부터) | v1.0.2 | 2026-11-08 10:11 | 메리츠 무매 평단 조절 추가 meritz_laoer v1.0.2 |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-13 17:16 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-12 15:28 KST부터)
- 사무실 터널 `bot-office-tunnel`: ⚪ 꺼짐
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-13 17:43 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 40% (남은 12.4GB)

## 최근 적용 10건

- 2026-11-13 17:43 · 5번 사무실 비서 v1.8.1 · bot_updater.py · 업데이터 옛 브랜치 되풀이 방지 (bot_updater vNEXT) (방: 포트폴리오)
- 2026-11-13 17:16 · 5번 사무실 비서 v1.8.0 · bot_updater.py, collect_inventory.py, deployment_control.py, · 메리츠 적립봇을 3번으로 (toss_dca 삭제, 표시·서비스·브리핑 정리)
- 2026-11-13 16:58 · 5번 사무실 비서 v1.7.9 · asset_board.py, board.html, office_board.py, test_asset_boar · 사무실 자산 구성: 포트폴리오 버킷 6개 (asset_board v1.4.4)
- 2026-11-13 16:34 · 3번 메리츠 적립 v1.2.4 · main.py, t_core.py, t_ui.py · meritz_dca v1.2.4: 관제탑 지금/완성 시 예상 토글 제거, 진행률은 항상 지금 기준 (방: 3
- 2026-11-13 16:23 · 3번 메리츠 적립 v1.2.3 · main.py, t_core.py, t_ui.py · meritz_dca v1.2.3: 하단 키보드 자금→관제탑, 관제탑 버튼을 주식/SGOV 패널로 이동 (방:
- 2026-11-13 16:18 · 5번 사무실 비서 v1.7.8 · office_briefing.py · office_briefing: 메리츠 4번에 SGOV 다음 회차 줄 추가, 매수 3거래일 전부터 표시 (방:
- 2026-11-13 15:57 · 3번 메리츠 적립 v1.2.2 · main.py, t_core.py · meritz_dca v1.2.2: 시드 설정을 2개 메뉴로 나눔 (방: 3. 미국주식 적립)
- 2026-11-13 15:53 · 3번 메리츠 적립 v1.2.1 · t_core.py · meritz_dca v1.2.1: 하단 키보드는 3개 메뉴만 (방: 3. 미국주식 적립)
- 2026-11-13 15:48 · 3번 메리츠 적립 v1.2.0 · main.py, sgov.py, t_core.py, t_ui.py · meritz_dca v1.2.0: 하단 고정 메뉴·자금 패널·시드 설정·진행률 그래프 (방: 3. 미국주식 
- 2026-11-13 15:23 · 2번 토스 스나이퍼 v1.2.7 · plugin_updater.py · sniper: plugin_updater commits synced files after direct ups

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
