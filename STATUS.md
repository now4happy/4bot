# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-12 06:12 (KST) · 계기: 매일 점검

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-01 17:16 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-10 10:21 KST부터) | v1.2.3 | 2026-11-10 10:22 | 2번 스나이퍼 v2.5.2 원작 1478200 실전 매도 수정 + 암살자 UG 진화형 이식 |
| 3번 토스 적립 | `toss_dca` | 🟢 실행 중 (11-05 09:02 KST부터) | v4.3.8 | 2026-11-05 09:02 | 3번 토스 적립 v4.3.8: R1 단계 단조화 + 정지·결정 중 알림 + 가격 0 가드 + N7 지수 20 |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-01 14:57 KST부터) | v4.3.3 | 2026-11-01 14:58 | feat: alert-hub 연동 2차 — 매매 봇 자율 알림 |
| 5번 사무실 비서 | `bot-office` | 🟢 실행 중 (11-11 13:20 KST부터) | v1.6.5 | 2026-11-11 13:21 | Revert "상태 기록: need.json" |
| 메리츠 SOXL 무매 | `meritz_laoer` | 🟢 실행 중 (11-08 10:11 KST부터) | v1.0.2 | 2026-11-08 10:11 | 메리츠 무매 평단 조절 추가 meritz_laoer v1.0.2 |
| 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-08 05:25 KST부터) | v1.0.0 | 2026-11-08 05:25 | 업데이터: NAMES에 meritz_dca.service 추가 (메리츠 적립, 사무실 vNEXT) |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-11 13:20 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-11 10:42 KST부터)
- 사무실 터널 `bot-office-tunnel`: 🟢 실행 중 (10-20 22:54 KST부터)
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-11 13:21 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 39% (남은 12.6GB)

## 최근 적용 10건

- 2026-11-11 13:21 · 5번 사무실 비서 v1.6.5 · bot_updater.py, office_briefing.py · Revert "상태 기록: need.json"
- 2026-11-11 10:42 · 5번 사무실 비서 v1.6.4 · fanding_trade.py · 배수 맞추기 주단위 5일 + 나머지 하루 더 (fanding_trade v1.5.7)
- 2026-11-11 10:15 · 5번 사무실 비서 v1.6.3 · fanding_trade.py · 자동환전 $10 단위 올림(ceiling) — 부족 남지 않게 (fanding_trade v1.5.6)
- 2026-11-11 05:40 · 5번 사무실 비서 v1.6.2 · live_board.py · live_board 원장 파일(sniper_tiers.json) 5분마다 live-board 브랜치에 발행
- 2026-11-10 13:22 · 5번 사무실 비서 v1.6.1 · live_board.py · 키움 수량 변경 live_board vNEXT (NAVER 21→14, TIGER 코리아휴머노이드 237→3
- 2026-11-10 11:16 · 5번 사무실 비서 v1.6.0 · fanding_vr6.py, meritz_client.py, office_briefing.py · VR6 need: 체결된 매수 줄 제외 — reserved_rows + remaining_need_usd (
- 2026-11-10 11:12 · 5번 사무실 비서 v1.5.9 · live_board.py · 시세 직접받기 한국(KRX) 확장 live_board vNEXT (종목명 정정: TIGER 미국S&P500,
- 2026-11-10 11:05 · 5번 사무실 비서 v1.5.8 · live_board.py · 시세 직접받기 한국(KRX) 확장 live_board vNEXT (토스 한국 시세 → krx 섹션 + E41
- 2026-11-10 10:46 · 5번 사무실 비서 v1.5.7 · meritz_client.py · 메리츠 원화 조회 deposit 교체 meritz_client vNEXT (사무실 vNEXT)
- 2026-11-10 10:29 · 5번 사무실 비서 v1.5.6 · bot_updater.py · 업데이트 비서 2번 스나이퍼 버전은 코드 머리말 버전으로 기록 (태그 카운터 대신)

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
