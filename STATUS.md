# STATUS — 서버가 자동으로 쓰는 현재 상태

> ⚠️ 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).
> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.

- 갱신: 2026-10-29 14:30 (KST) · 계기: 업데이트 적용 (staging: 팬딩 VR6 버튼 글자에서 'VR6' 빼기: fanding_trade 1.10.1, fanding_vr6 2.2.1 (작업 기록 포함))

## 봇별 현재 상태

| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |
|---|---|---|---|---|---|
| 1번 한투 라오어 | `han4384tubot` | 🟢 실행 중 (10-25 17:36 KST부터) | v1.0.1 | 2026-10-25 17:36 | 안내 문구 수정 2번봇 |
| 2번 토스 스나이퍼 | `toss_sniper` | 🟢 실행 중 (10-29 10:19 KST부터) | v1.0.10 | 2026-10-29 10:19 | 2번 스나이퍼 매매 정책 일치: 데이마켓 매수 잠금, 애프터마켓 매도 감시, 매도 실시간 (staging) |
| 3번 토스 적립 | `toss_dca` | 🟢 실행 중 (10-28 10:48 KST부터) | v4.3.5 | 2026-10-28 10:49 | docs/log 한글 파일명 삭제 (영문 파일명으로 대체, 내용 동일) |
| 4번 빗썸 적립 | `bithumb_bot` | 🟢 실행 중 (10-28 10:47 KST부터) | v4.0.4 | 2026-10-28 10:49 | docs/log 한글 파일명 삭제 (영문 파일명으로 대체, 내용 동일) |
| 5번 사무실 비서 | `bot-office` | 🟢 실행 중 (10-29 14:29 KST부터) | v1.0.65 | 2026-10-29 14:30 | 팬딩 VR6 버튼 글자에서 'VR6' 빼기: fanding_trade 1.10.1, fanding_vr6 2 |

## 사무실 상시 서비스

- 7번 비서(브리핑·PC감시) `bot-office-secretary`: 🟢 실행 중 (10-29 14:17 KST부터)
- 5번 팬딩 가격표 `bot-office-fanding`: 🟢 실행 중 (10-29 14:30 KST부터)
- 사무실 터널 `bot-office-tunnel`: 🟢 실행 중 (10-20 22:54 KST부터)
- 6번 업데이트 비서 `bot-updater`: 🟢 실행 중 (10-29 14:17 KST부터)
- 실패 상태로 남은 서비스·타이머: `bot-office-inventory.service`
- 디스크 사용: 76% (남은 2.4GB)

## 최근 적용 10건

- 2026-10-29 14:30 · 5번 사무실 비서 v1.0.65 · fanding_trade.py, fanding_vr6.py · 팬딩 VR6 버튼 글자에서 'VR6' 빼기: fanding_trade 1.10.1, fanding_vr6 2
- 2026-10-29 14:17 · 5번 사무실 비서 v1.0.64 · bot_updater.py, fanding_trade.py, fanding_vr6.py · 팬딩 메뉴 정리: fanding_trade 1.10.0, fanding_vr6 2.2.0, bot_updat
- 2026-10-29 13:34 · 5번 사무실 비서 v1.0.63 · fanding_trade.py, fanding_vr6.py · VR6 환전·09:00 알림 + P·VR6 매도 수량 맞춤: fanding_trade 1.9.0, fandi
- 2026-10-29 13:06 · 5번 사무실 비서 v1.0.62 · fanding_vr6_win.py · VR6 수집기 1.1.0: 이미지 20장·글 끝까지 스크롤·run.bat 안내 수정 (작업 기록 개정 포함)
- 2026-10-29 12:48 · 5번 사무실 비서 v1.0.61 · fanding_vr6.py, fanding_vr6_win.py, meritz_client.py · VR6 예약주문 2단계: fanding_vr6 2.0.0, meritz_client V1.5, fanding
- 2026-10-29 11:03 · 5번 사무실 비서 v1.0.60 · fanding_fetch_win.py · 팬딩 PC 수집기 1.5.3: 하루 30개·미전송 우선·완료 후 건너뛰기
- 2026-10-29 10:43 · 5번 사무실 비서 v1.0.59 · board.html, fanding_trade.py, office_board.py · 팬딩 아침 알림 정리 + 상황판 가격표 모음 매일 포함 (사무실 v1.0.59 예정)
- 2026-10-29 10:19 · 2번 토스 스나이퍼 v1.0.10 · main.py, quant_indicators_plugin.py, sniper_exit_plugin.py,  · 2번 스나이퍼 매매 정책 일치: 데이마켓 매수 잠금, 애프터마켓 매도 감시, 매도 실시간 (staging)
- 2026-10-28 13:55 · 5번 사무실 비서 v1.0.58 · index.html, market_manual.py, office_reviews.py, office_task · 픽셀·운영 삭제: office_tasks.py
- 2026-10-28 13:10 · 5번 사무실 비서 v1.0.57 · ai_room.py, apply_deploy.py, deploy_worker.py, draft_change. · 꺼진 기능 파일 삭제: generate_ideas.py

## 대기 중인 업로드 (아직 승인 안 됨)

- 없음

## AI·사람 작업 순서 (요약)

1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).
2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).
3. 고친 파일은 staging 에 올리고 6. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 🚨 경고가 뜬다.
4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).
