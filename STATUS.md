# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-25 13:14 (KST) · 계기: 업데이트 적용 (staging: 메리츠 v2.15.0 (판 41): 암살자 실전 루프 + GUARD30 수혈 + 틱 종료 분리 + 마감 일일결산 + 바벨 삭제)

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-25 10:56 KST부터) | v1.0.6 | 2026-11-20 13:53 | audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-25 11:59 KST부터) | v1.2.8 | 2026-11-18 19:45 | toss: 공유 토큰 복원 (a) + 동기화 뒤 훅 자동 재적용 Q5 (방 room2-toss-sniper) |
| 3번 토스 적립 | `toss_dca` | ⚪ 꺼짐 | - | - | - |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-20 12:16 KST부터) | v4.4.1 | 2026-11-20 12:17 | audit-fix-v2 r3: 7번 탑쌓기 전용 (사다리 삭제) + 전 봇 구멍 고침, 7번 v2.2.10, |
| 5번 사무실 비서 | `bot-office` | ⚪ 꺼짐 | v2.0.2 | 2026-11-24 09:12 | bot_updater: captures/ 데이터 브랜치를 업데이트 대기에서 제외 |
| 메리츠 SOXL 하이브리드모드 | `meritz_laoer` | 🟢 실행 중 (11-25 13:13 KST부터) | v1.4.9 | 2026-11-25 13:14 | 메리츠 v2.15.0 (판 41): 암살자 실전 루프 + GUARD30 수혈 + 틱 종료 분리 + 마감 일일 |
| 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-25 11:52 KST부터) | v1.3.4 | 2026-11-20 13:53 | audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6 |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-20 12:17 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-24 09:01 KST부터)
- 사무실 터널 `bot-office-tunnel`: ⚪ 꺼짐
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-24 09:12 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 43% (남은 11.7GB)

## 최근 적용 10건

- 2026-11-25 13:14 · 메리츠 SOXL 하이브리드모드 v1.4.9 · assassin_live.py, barbell_adapter.py, config.py, free_cash.p · 메리츠 v2.15.0 (판 41): 암살자 실전 루프 + GUARD30 수혈 + 틱 종료 분리 + 마감 일일
- 2026-11-25 11:44 · 메리츠 SOXL 하이브리드모드 v1.4.9 · main.py, assassin_live.py(신규), free_cash.py(신규), barbell_ada · 메리츠 v2.15.0 (판 41): ① 암살자 실전 루프 연결(원작 틱을 메리츠 API로 호출·1분 폴링 4
- 2026-11-25 11:00 · 메리츠 SOXL 하이브리드모드 v1.4.8 · main.py, meritz_api.py, sniper_mode.py · 메리츠 v2.14.0 (판 42): 미체결 매수 60초 안전 취소 + 야간 코드 001 SELL_STATUS
- 2026-11-25 09:53 · 메리츠 SOXL 하이브리드모드 v1.4.8 · main.py, meritz_api.py, sniper_mode.py, 시험 파일(test_hybrid_v3 · 메리츠 v2.14.0 (판 42): P1 미체결 매수 60초 안전 취소 (원작 BUY_ORDER_MAX_WA
- 2026-11-24 12:41 · 메리츠 SOXL 하이브리드모드 v1.4.7 · barbell_adapter.py, config.py, main.py, sniper_adapter.py, s · 메리츠 v2.13.0 (판 40): 1.5초 루프 + 암살자 실전(부분) + 매도 창 전체 + GUARD30
- 2026-11-24 11:15 · 메리츠 SOXL 하이브리드모드 v1.4.6 · config.py, main.py, meritz_api.py, sniper_adapter.py, sniper · 메리츠 v2.12.0 (판 39): 첫 매수 원작화 + 메뉴 원작화
- 2026-11-24 10:13 · 메리츠 SOXL 하이브리드모드 v1.4.6 · README.md, config.py, main.py, meritz_api.py, sniper_adapter · 메리츠 v2.12.0 (판 39): 첫 매수 원작 분기 A(가격 조건 없이 현재가·검문 포함) + 레이더 전
- 2026-11-24 09:41 · 메리츠 SOXL 하이브리드모드 v1.4.5 · main.py, ORIGIN.json, barbell_plugin.py, sniper_exit_plugin. · 메리츠 v2.11.0 (판 38): Audit-113 동기화 + 시간 확대
- 2026-11-24 09:39 · 메리츠 SOXL 하이브리드모드 v1.4.5 · README.md, main.py, orig_sniper/ORIGIN.json, orig_sniper/bar · 메리츠 v2.11.0 (판 38): Audit-113 동기화 (원작 23a16d5 복사본 2개 + ORIGI
- 2026-11-24 09:12 · 5번 사무실 비서 v2.0.2 · bot_updater.py · bot_updater: captures/ 데이터 브랜치를 업데이트 대기에서 제외

## 대기 중인 업로드 (아직 승인 안 됨)

- `captures/p-verify`: p-verify/14_k_pattern_analysis.md, p-verify/15_output_v16.txt, p-verify/15_verify_k_pattern.py, p-verify/16_test_k_pattern.py, p-verify/README.md, p-verify/VERIFY_k10.md 외

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
