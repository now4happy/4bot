# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-19 15:40 (KST) · 계기: 업데이트 적용 (staging: 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거)

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-15 14:21 KST부터) | v1.0.3 | 2026-11-01 17:16 | feat: alert-hub 연동 3차 — 1번 한투 자율 알림 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-19 12:46 KST부터) | v1.2.8 | 2026-11-18 19:45 | toss: 공유 토큰 복원 (a) + 동기화 뒤 훅 자동 재적용 Q5 (방 room2-toss-sniper) |
| 6번 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-19 15:40 KST부터) | v1.3.0 | 2026-11-19 15:40 | 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거 |
| 3번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-19 15:39 KST부터) | v4.4.0 | 2026-11-19 15:40 | 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거 |
| 7번 메리츠 무매 | `meritz_laoer` | 🟢 실행 중 (11-19 14:44 KST부터) | v1.0.9 | 2026-11-19 14:44 | meritz_laoer v2.0.9: usd_cash reads estm_frcr_amt (pan 11, Q |
| 사무실 파일(bot_office) | `bot-office` (서비스 없음) | 📁 파일 묶음 | v1.9.2 | 2026-11-19 15:40 | 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거 |

## 사무실 상시 서비스

- 8번 비서(SGOV) `bot-office-secretary`: 🟢 실행 중 (11-19 15:40 KST부터)
- 4번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-19 15:40 KST부터)
- 9번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-18 14:52 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 94% (남은 1.2GB)

## 최근 적용 10건

- 2026-11-19 15:40 · 사무실 파일(bot_office) v1.9.2 · bot_updater.py, fanding_trade.py, fanding_vr6.py, office_sec · 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거
- 2026-11-19 15:40 · 6번 메리츠 적립 v1.3.0 · main.py, sgov.py, t_core.py, t_ui.py · 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거
- 2026-11-19 15:40 · 3번 빗썸 적립 v4.4.0 · b_core.py, b_ui.py, main.py · 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거
- 2026-11-19 14:44 · 7번 메리츠 무매 v1.0.9 · main.py, meritz_api.py, tg_menu.py · meritz_laoer v2.0.9: usd_cash reads estm_frcr_amt (pan 11, Q
- 2026-11-19 14:24 · 7번 메리츠 무매 v1.0.8 · main.py, tg_menu.py · meritz_laoer v2.0.8: auto FX in realtime window, shortage al
- 2026-11-19 13:43 · 7번 메리츠 무매 v1.0.7 · main.py, tg_menu.py · meritz_laoer v2.0.7: auto FX at 09:00 KST, one round per day
- 2026-11-18 19:45 · 2번 토스 스나이퍼 v1.2.8 · plugin_updater.py, toss_api.py, toss_hook_patch.py · toss: 공유 토큰 복원 (a) + 동기화 뒤 훅 자동 재적용 Q5 (방 room2-toss-sniper)
- 2026-11-18 18:01 · 7번 메리츠 무매 v1.0.6 · config.py, main.py, tg_menu.py · meritz_laoer v2.0.1: 텔레그램 메뉴 정리 (메인 4개 카테고리, 전술 설정, 상황판 설정값 
- 2026-11-18 16:53 · 7번 메리츠 무매 v1.0.5 · accum_strategy.py, config.py, main.py, meritz_api.py, notifi · meritz: SOXL 적립봇 v2.0.0 — 사다리·부분매도·재매수·자동환전 (방 meritz-soxl-d
- 2026-11-18 10:44 · 사무실 파일(bot_office) v1.9.1 · fanding_trade.py · fanding_trade v1.5.9: 자동주문 모드 A 판독후 30분 (방 fanding-autoorder

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 9. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
