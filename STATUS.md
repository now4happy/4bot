# STATUS — 서버가 자동으로 쓰는 현재 상태

> 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-19 21:37 (KST) · 계기: 업데이트 적용 (staging: meritz_laoer v2.2.3: 층 칸 색상 + 다음 회차 가격별 배정)

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 실행 중 (11-19 20:53 KST부터) | v1.0.4 | 2026-11-19 20:54 | fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1 |
| 2번 토스 스나이퍼 | `toss_sniper` | 실행 중 (11-19 12:46 KST부터) | v1.2.8 | 2026-11-18 19:45 | toss: 공유 토큰 복원 (a) + 동기화 뒤 훅 자동 재적용 Q5 (방 room2-toss-sniper) |
| 6번 메리츠 적립 | `meritz_dca` | 실행 중 (11-19 20:53 KST부터) | v1.3.2 | 2026-11-19 20:54 | fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1 |
| 3번 빗썸 적립 | `bithumb_bot` | 실행 중 (11-19 15:39 KST부터) | v4.4.0 | 2026-11-19 15:40 | 텔레그램 매매봇 메뉴 정리 3차 v2 (7번 제외): 첫 화면 4칸·금액 메뉴 설명·범위 표시·이모티콘 제거 |
| 7번 메리츠 속쓸 적립봇 | `meritz_laoer` | 실행 중 (11-19 21:37 KST부터) | v1.1.5 | 2026-11-19 21:37 | meritz_laoer v2.2.3: 층 칸 색상 + 다음 회차 가격별 배정 |
| 사무실 파일(bot_office) | `bot-office` (서비스 없음) | 파일 묶음 | v1.9.3 | 2026-11-19 17:40 | updater redesign pan2 v2: sniper sync via plugin_updater CLI |

## 사무실 상시 서비스

- 8번 비서(SGOV) `bot-office-secretary`: 실행 중 (11-19 15:40 KST부터)
- 4번 팬딩 가격표 `bot-office-fanding`: 실행 중 (11-19 15:40 KST부터)
- 9번 업데이트 비서 `bot-updater`: 실행 중 (11-19 17:40 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 94% (남은 1.2GB)

## 최근 적용 10건

- 2026-11-19 21:37 · 7번 메리츠 속쓸 적립봇 v1.1.5 · main.py, tg_menu.py, tower_strategy.py · meritz_laoer v2.2.3: 층 칸 색상 + 다음 회차 가격별 배정
- 2026-11-19 21:23 · 7번 메리츠 속쓸 적립봇 v1.1.4 · main.py, tg_menu.py, tower_strategy.py · meritz_laoer v2.2.2: tower layer visualization (pan 14) - to
- 2026-11-19 20:54 · 7번 메리츠 속쓸 적립봇 v1.1.3 · accum_strategy.py, config.py, main.py · fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1
- 2026-11-19 20:54 · 6번 메리츠 적립 v1.3.2 · dca_engine.py, main.py, meritz_api.py, sgov.py, t_core.py, t · fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1
- 2026-11-19 20:54 · 1번 한투 라오어 v1.0.4 · kis_order_engine.py, order_executor.py, scheduler_regular.py · fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1
- 2026-11-19 20:42 · 7번 메리츠 속쓸 적립봇 v1.1.2 · main.py, tg_menu.py, tower_strategy.py · meritz_laoer v2.2.0: tower stacking (pan 13) - new tower_str
- 2026-11-19 17:40 · 사무실 파일(bot_office) v1.9.3 · bot_updater.py, sniper_upstream.py · updater redesign pan2 v2: sniper sync via plugin_updater CLI
- 2026-11-19 17:08 · 7번 메리츠 속쓸 적립봇 v1.1.1 · main.py · meritz_laoer v2.1.0: merge pan 12 intraday sell gate fix ont
- 2026-11-19 16:49 · 7번 메리츠 속쓸 적립봇 v1.1.0 · main.py, notifier.py, tg_menu.py · 텔레그램 매매봇 메뉴 정리 3차 v3: 7번 v2.0.9 기준 재적용 + 6번 문구 정리
- 2026-11-19 16:49 · 6번 메리츠 적립 v1.3.1 · main.py · 텔레그램 매매봇 메뉴 정리 3차 v3: 7번 v2.0.9 기준 재적용 + 6번 문구 정리

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## 보류 중인 봇 업데이트 (매매 중·일시중지 대기는 풀리면 자동 재시도 · 앞섬은 사람 승인 필요)

- 없음

## 2번 스나이퍼 (관찰 전용 — 업데이트 비서가 적용하지 않음)

- 서버 스나이퍼 최신 커밋: 6a110b9c sniper: upstream 01ac6da direct sync
- 원작 기준 커밋: 45d0e4c
- 자동 업뎃: 기록 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 9. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
