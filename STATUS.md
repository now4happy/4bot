# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-18 18:01 (KST) · 계기: 업데이트 적용 (staging: meritz_laoer v2.0.1: 텔레그램 메뉴 정리 (메인 4개 카테고리, 전술 설정, 상황판 설정값 표시))

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-15 14:21 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | ⚪ 꺼짐 | v1.2.7 | 2026-11-13 15:23 | sniper: plugin_updater commits synced files after direct ups |
| 6번 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-17 09:44 KST부터) | v1.2.9 | 2026-11-17 09:44 | meritz_dca_bot v1.2.9: SGOV 환율 재시도 창 캐시 폴백 + 시장가 주문 여유 10% + |
| 3번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-15 14:21 KST부터) | v4.3.6 | 2026-11-14 14:48 | bithumb-bottomkb: 하단 키보드 [🪙 BTC 설정][🪙 ETH 설정] 1줄·2개 + 코인별 상황 |
| 7번 메리츠 무매 | `meritz_laoer` | 🟢 실행 중 (11-18 18:00 KST부터) | v1.0.6 | 2026-11-18 18:01 | meritz_laoer v2.0.1: 텔레그램 메뉴 정리 (메인 4개 카테고리, 전술 설정, 상황판 설정값  |
| 사무실 파일(bot_office) | `bot-office` (서비스 없음) | 📁 파일 묶음 | v1.9.1 | 2026-11-18 10:44 | fanding_trade v1.5.9: 자동주문 모드 A 판독후 30분 (방 fanding-autoorder |

## 사무실 상시 서비스

- 8번 비서(SGOV) `bot-office-secretary`: 🟢 실행 중 (11-15 14:21 KST부터)
- 4번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-18 10:44 KST부터)
- 9번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-18 14:52 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 65% (남은 7.2GB)

## 최근 적용 10건

- 2026-11-18 18:01 · 7번 메리츠 무매 v1.0.6 · config.py, main.py, tg_menu.py · meritz_laoer v2.0.1: 텔레그램 메뉴 정리 (메인 4개 카테고리, 전술 설정, 상황판 설정값 
- 2026-11-18 16:53 · 7번 메리츠 무매 v1.0.5 · accum_strategy.py, config.py, main.py, meritz_api.py, notifi · meritz: SOXL 적립봇 v2.0.0 — 사다리·부분매도·재매수·자동환전 (방 meritz-soxl-d
- 2026-11-18 10:44 · 사무실 파일(bot_office) v1.9.1 · fanding_trade.py · fanding_trade v1.5.9: 자동주문 모드 A 판독후 30분 (방 fanding-autoorder
- 2026-11-17 16:18 · 사무실 파일(bot_office) v1.9.0 · bot_updater.py, fanding_trade.py, fanding_vault.py · fanding_vault v0.1.1-shadow: 매수 현금 한도 + 8,000 한도 기록 (방: P매매 
- 2026-11-17 09:44 · 6번 메리츠 적립 v1.2.9 · sgov.py, t_core.py · meritz_dca_bot v1.2.9: SGOV 환율 재시도 창 캐시 폴백 + 시장가 주문 여유 10% +
- 2026-11-16 11:14 · 사무실 파일(bot_office) v1.8.9 · office_briefing.py · 사무실 vNEXT: 4번 메리츠 need 시세 조회 거래소 폴백 (OQ→NY→AX)
- 2026-11-15 13:49 · 사무실 파일(bot_office) v1.8.8 · bot_updater.py · 사무실 vNEXT: P1 매일 점검·P2 watchdog 제거·P4 captures 제외 (한 달 무인 운영
- 2026-11-14 14:48 · 3번 빗썸 적립 v4.3.6 · b_core.py, b_ui.py, main.py · bithumb-bottomkb: 하단 키보드 [🪙 BTC 설정][🪙 ETH 설정] 1줄·2개 + 코인별 상황
- 2026-11-14 14:21 · 사무실 파일(bot_office) v1.8.7 · board.html, bot_updater.py, login.html, office_board.py, off · web-office-remove: 웹 사무실 완전 제거 + 8번 비서 SGOV 전용 (vNEXT)
- 2026-11-14 14:12 · 3번 빗썸 적립 v4.3.5 · b_core.py, b_ui.py, main.py · bithumb-menu: 처음 화면을 BTC·ETH 설정 중심으로 (v4.3.5)

## 대기 중인 업로드 (아직 승인 안 됨)

- `staging-toss`: toss_sniper/plugin_updater.py, toss_sniper/toss_api.py, toss_sniper/toss_hook_patch.py

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 9. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
