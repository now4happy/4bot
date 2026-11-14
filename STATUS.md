# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-14 14:21 (KST) · 계기: 업데이트 적용 (staging: web-office-remove: 웹 사무실 완전 제거 + 8번 비서 SGOV 전용 (vNEXT))

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-12 15:28 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-13 15:23 KST부터) | v1.2.7 | 2026-11-13 15:23 | sniper: plugin_updater commits synced files after direct ups |
| 6번 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-14 13:56 KST부터) | v1.2.8 | 2026-11-14 13:57 | bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT) |
| 3번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-14 14:12 KST부터) | v4.3.5 | 2026-11-14 14:12 | bithumb-menu: 처음 화면을 BTC·ETH 설정 중심으로 (v4.3.5) |
| 사무실 비서(번호 없음) | `bot-office` | ⚪ 꺼짐 | v1.8.7 | 2026-11-14 14:21 | web-office-remove: 웹 사무실 완전 제거 + 8번 비서 SGOV 전용 (vNEXT) |
| 7번 메리츠 무매 | `meritz_laoer` | 🟢 실행 중 (11-14 13:56 KST부터) | v1.0.4 | 2026-11-14 13:57 | bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT) |

## 사무실 상시 서비스

- 8번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-14 14:21 KST부터)
- 4번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-14 13:57 KST부터)
- 사무실 터널 `bot-office-tunnel`: ⚪ 꺼짐
- 9번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-14 13:57 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 40% (남은 12.4GB)

## 최근 적용 10건

- 2026-11-14 14:21 · 사무실 비서(번호 없음) v1.8.7 · board.html, bot_updater.py, login.html, office_board.py, off · web-office-remove: 웹 사무실 완전 제거 + 8번 비서 SGOV 전용 (vNEXT)
- 2026-11-14 14:12 · 3번 빗썸 적립 v4.3.5 · b_core.py, b_ui.py, main.py · bithumb-menu: 처음 화면을 BTC·ETH 설정 중심으로 (v4.3.5)
- 2026-11-14 13:57 · 사무실 비서(번호 없음) v1.8.6 · bot_updater.py, fanding_trade.py, office_briefing.py, office · bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT)
- 2026-11-14 13:57 · 7번 메리츠 무매 v1.0.4 · main.py, notifier.py, tg_menu.py · bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT)
- 2026-11-14 13:57 · 6번 메리츠 적립 v1.2.8 · t_core.py · bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT)
- 2026-11-14 13:57 · 3번 빗썸 적립 v4.3.4 · b_core.py, main.py · bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT)
- 2026-11-14 13:30 · 사무실 비서(번호 없음) v1.8.5 · bot_updater.py, fanding_direct_upload.py, office_url.py · web-server-off-prep: office health check off, intentional-st
- 2026-11-14 10:54 · 사무실 비서(번호 없음) v1.8.4 · office_sgov.py · meritz_dca_bot v1.2.7 + office vNEXT: SGOV 회차 알림을 4번 방 대신 br
- 2026-11-14 10:54 · 6번 메리츠 적립 v1.2.7 · bridge.py, sgov.py, t_core.py · meritz_dca_bot v1.2.7 + office vNEXT: SGOV 회차 알림을 4번 방 대신 br
- 2026-11-14 10:25 · 사무실 비서(번호 없음) v1.8.3 · office_secretary.py, office_sgov.py · meritz split: 4번 주식만·SGOV 비서봇·무매봇 메뉴 (dca v1.2.6, laoer v1.0

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 9. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
