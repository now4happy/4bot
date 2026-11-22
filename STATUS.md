# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-11-22 14:15 (KST) · 계기: 업데이트 적용 (staging: 메리츠 v2.9.0 (판 31, 2차·3차): 매도 연결 + 질문 3 부분 주문)

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (11-20 13:53 KST부터) | v1.0.6 | 2026-11-20 13:53 | audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (11-19 12:46 KST부터) | v1.2.8 | 2026-11-18 19:45 | toss: 공유 토큰 복원 (a) + 동기화 뒤 훅 자동 재적용 Q5 (방 room2-toss-sniper) |
| 3번 토스 적립 | `toss_dca` | ⚪ 꺼짐 | - | - | - |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (11-20 12:16 KST부터) | v4.4.1 | 2026-11-20 12:17 | audit-fix-v2 r3: 7번 탑쌓기 전용 (사다리 삭제) + 전 봇 구멍 고침, 7번 v2.2.10, |
| 5번 사무실 비서 | `bot-office` | ⚪ 꺼짐 | v1.9.8 | 2026-11-22 14:07 | 사무실 vNEXT: meritz_laoer/ 하위 폴더(orig_sniper/) 배포 분류 |
| 메리츠 SOXL 무매 | `meritz_laoer` | 🟢 실행 중 (11-22 14:14 KST부터) | v1.3.4 | 2026-11-22 14:15 | 메리츠 v2.9.0 (판 31, 2차·3차): 매도 연결 + 질문 3 부분 주문 |
| 메리츠 적립 | `meritz_dca` | 🟢 실행 중 (11-20 13:53 KST부터) | v1.3.4 | 2026-11-20 13:53 | audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6 |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (11-20 12:17 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (11-19 15:40 KST부터)
- 사무실 터널 `bot-office-tunnel`: ⚪ 꺼짐
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (11-22 14:07 KST부터)
- 실패 상태로 남은 서비스·타이머: 없음
- 디스크 사용: 72% (남은 5.7GB)

## 최근 적용 10건

- 2026-11-22 14:15 · 메리츠 SOXL 무매 v1.3.4 · main.py, sniper_adapter.py, sniper_mode.py · 메리츠 v2.9.0 (판 31, 2차·3차): 매도 연결 + 질문 3 부분 주문
- 2026-11-22 14:07 · 5번 사무실 비서 v1.9.8 · bot_updater.py · 사무실 vNEXT: meritz_laoer/ 하위 폴더(orig_sniper/) 배포 분류
- 2026-11-21 11:08 · 메리츠 SOXL 무매 v1.2.9 · main.py, notifier.py, sniper_mode.py, tg_menu.py, tower_stra · 판 24 meritz_laoer v2.4.0 (층 나눔·잠금·스나이퍼 선택: 장부 바로잡기 684주·지하층·
- 2026-11-21 11:08 · 5번 사무실 비서 v1.9.7 · bot_updater.py · 판 24 meritz_laoer v2.4.0 (층 나눔·잠금·스나이퍼 선택: 장부 바로잡기 684주·지하층·
- 2026-11-21 09:05 · 메리츠 SOXL 무매 v1.2.8 · main.py, sniper_mode.py, tg_menu.py · meritz_laoer v2.3.0 (판 23 수정1: 장중 환전 고침 제외·하루 매수 층 수 제한·B3 미
- 2026-11-20 19:09 · 메리츠 SOXL 무매 v1.2.6 · main.py, tg_menu.py · meritz_laoer v2.2.18 (판 21 거래 내역·봇 상태 버튼 오류 고침): _local 이 4개
- 2026-11-20 19:00 · 메리츠 SOXL 무매 v1.2.5 · config.py, main.py, tg_menu.py, tower_strategy.py · meritz_laoer v2.2.17 (판 20 하루 매수·매도 층 수 설정 + 수정1 아침 매도 N_sel
- 2026-11-20 18:02 · 메리츠 SOXL 무매 v1.2.4 · main.py, tower_strategy.py · meritz_laoer v2.2.15 (판 19 오늘 계획 미리보기에 탑 진행률): plan_head 한 곳
- 2026-11-20 16:46 · 메리츠 SOXL 무매 v1.2.3 · main.py, tg_menu.py, tower_strategy.py · meritz_laoer v2.2.14 (판 17 시초가 상한): 오늘 채우는 층의 안 산 칸이 시초가를 넘지
- 2026-11-20 13:53 · 메리츠 적립 v1.3.4 · main.py, t_core.py · audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6

## 대기 중인 업로드 (아직 승인 안 됨)

- `pan25-toss-sniper-ref`: pan25-toss-ref/sniper_plugin.py

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
