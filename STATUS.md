# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-13 14:26 (KST) · 계기: 업데이트 적용 (staging: 토스 브리핑 키 읽기 폴백 (TOSS_DIR → SNIPER_DIR, office_briefing vNEXT))

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-12 15:28 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-13 10:46 KST부터) | v1.2.6 | 2026-11-13 10:47 | remove .upstream_head from staging (updater allowlist reject |
| 3번 토스 적립 | `toss_dca` | ⚪ 꺼짐 | - | - | - |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-12 15:28 KST부터) | v4.3.3 | 2026-11-01 14:58 | feat: alert-hub 연동 2차 — 매매 봇 자율 알림 |
| 5번 사무실 비서 | `bot-office` | 🟢 실행 중 (11-13 14:25 KST부터) | v1.7.6 | 2026-11-13 14:26 | 토스 브리핑 키 읽기 폴백 (TOSS_DIR → SNIPER_DIR, office_briefing vNEXT |
| 메리츠 SOXL 무매 | `meritz_laoer` | 🟢 실행 중 (11-12 15:28 KST부터) | v1.0.2 | 2026-11-08 10:11 | 메리츠 무매 평단 조절 추가 meritz_laoer v1.0.2 |
| 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-13 14:25 KST부터) | v1.1.1 | 2026-11-13 14:26 | 토스 브리핑 키 읽기 폴백 (TOSS_DIR → SNIPER_DIR, office_briefing vNEXT |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-13 14:25 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-12 15:28 KST부터)
- 사무실 터널 `bot-office-tunnel`: ⚪ 꺼짐
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-13 12:50 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 40% (남은 12.4GB)

## 최근 적용 10건

- 2026-11-13 14:26 · 메리츠 적립 v1.1.1 · main.py, t_core.py · 토스 브리핑 키 읽기 폴백 (TOSS_DIR → SNIPER_DIR, office_briefing vNEXT
- 2026-11-13 14:26 · 5번 사무실 비서 v1.7.6 · office_briefing.py · 토스 브리핑 키 읽기 폴백 (TOSS_DIR → SNIPER_DIR, office_briefing vNEXT
- 2026-11-13 12:50 · 5번 사무실 비서 v1.7.5 · bot_updater.py · 업데이터: 배포에서 빠진 파일은 막지 않고 넘김 (사무실 vNEXT)
- 2026-11-13 12:38 · 메리츠 적립 v1.1.0 · main.py, sgov.py, t_core.py, t_ui.py · SGOV 테스트 파일 staging에서 제외 (업데이터 허용 파일 아님)
- 2026-11-13 12:25 · 메리츠 적립 v1.0.2 · main.py, meritz_api.py, t_core.py · 메리츠 4번 낮 자동환전 참고가 fallback (meritz_dca v1.0.2)
- 2026-11-13 12:03 · 5번 사무실 비서 v1.7.4 · office_briefing.py · 11:00 부족액 브리핑에 바벨 씨드 부족액 줄 추가 (office_briefing.py)
- 2026-11-13 10:47 · 5번 사무실 비서 v1.7.3 · sniper_picture.html, sniper_picture.py · remove .upstream_head from staging (updater allowlist reject
- 2026-11-13 10:47 · 2번 토스 스나이퍼 v1.2.6 · plugin_updater.py · remove .upstream_head from staging (updater allowlist reject
- 2026-11-13 10:33 · 2번 토스 스나이퍼 v1.2.5 · assassin_plugin.py, defense_plugin.py, main.py, quant_engine · sniper: upstream cd9e87b as-is migration (15 files, Case 99 
- 2026-11-13 09:51 · 5번 사무실 비서 v1.7.2 · bot_updater.py, live_board.py · live_board: 키움 수량 변경 v1.6.8 기준으로 재적용 (일본종합상사 416→362, 오픈엣지 9

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
