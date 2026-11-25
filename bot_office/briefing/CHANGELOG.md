# briefing 변경 기록

## v1.0.5 · 2026-11-25 15:29 (KST)
- 파일: need_table.py, run.py
- 내용: 3차 rev3: 재발행 때 팬딩 원인을 briefing_latest.json에 기록
- 브랜치: staging

## v1.0.4 · 2026-11-25 15:23 (KST)
- 파일: tg_send.py
- 내용: 3차 rev2: 가드 오판 고침 + VR6 상태 파일 원인 기록
- 브랜치: staging

## v1.0.3 · 2026-11-25 14:22 (KST)
- 파일: need_table.py, render.py, run.py, tg_send.py
- 내용: 3차: 새 봇 방 + 9시 KST + 읽기 편한 형식 + 완충 규칙 (rev1)
- 브랜치: staging

## v1.0.2 · 2026-11-25 13:14 (KST)
- 파일: run.py
- 내용: 메리츠 v2.15.0 (판 41): 암살자 실전 루프 + GUARD30 수혈 + 틱 종료 분리 + 마감 일일결산 + 바벨 삭제
- 브랜치: staging

# 9번 브리핑 변경 기록

## vNEXT · 2026-11-25 (타이베이) — 3차 rev3: 재발행 때 팬딩 원인을 briefing_latest.json 에 기록
- 파일: run.py, need_table.py (시험 tests/test_fanding_cause.py는 검토용으로만 두고 staging에는 안 올림)
- 내용: 재발행(office_briefing.py --print)의 stderr 에서 [FANDING_NEED] 줄만 골라 briefing_latest.json need.fanding_causes 에 남긴다. 원인이 없으면 필드를 만들지 않는다. 메시지 형식·need.json 구조·need 계산식은 그대로.
- 브랜치: staging

## vNEXT · 2026-11-25 (타이베이) — 3차 rev2: 가드 오판 고침 + VR6 상태 파일 원인 기록
- 파일: tg_send.py, ../office_briefing.py (시험 tests/test_guard_vr6.py는 검토용으로만 두고 staging에는 안 올림)
- 내용: 섞임 방지 가드는 토큰이 다르면 같은 개인 채팅 번호(양수)를 막지 않는다. 같은 토큰·같은 그룹 방은 계속 막는다. 팬딩 상태 파일(P·VR6)을 못 읽으면 원인을 [FANDING_NEED] 로그로 남긴다. need 계산식·need.json 구조·메시지 형식은 그대로.
- 브랜치: staging

## vNEXT · 2026-11-25 (타이베이) — 3차: 새 봇 방 + 9시 + 읽기 편한 형식
- 파일: render.py, need_table.py, run.py, tg_send.py, config.json, systemd/briefing.timer, systemd/bot-office-briefing.timer (시험 tests/test_briefing.py는 검토용으로만 두고 staging에는 안 올림)
- 내용: 필요 달러(부족 금액) 브리핑을 새 텔레그램 봇·새 전용 방으로 보낸다 (paths.telegram_need_cfg, 9번 봇·업데이트 방과 섞지 않음, 토큰 해시·방 비교 가드). 형식은 pre 표 대신 일반 글자 + 굵은 글씨, 부족 있는 계좌만 한 줄씩, 합계·바벨 씨드 참고 줄(합계 제외), 전부 충분하고 전부 확인되면 "오늘 계좌 완충" 한 줄만 (확인 불가 줄이 있으면 완충 안 보냄). 시간 기준 KST 09:00 (briefing.timer 00:00 UTC), need.json 아침 발행 08:00 KST로 앞당김. send.need=true 는 새 방 발송 시작, false 는 중단(되돌리기). 포트폴리오 브리핑·need.json 계산(office_briefing.py)은 그대로.
  완충 판정에서 need 를 계산 안 하는 줄(한투 KRW, 토스 KRW need=None)은 제외하고, 필요 달러 메시지의 USD 는 정수(올림)로 보여 준다 (3차 rev1).
- 브랜치: staging

## vNEXT · 2026-11-25 (타이베이)
- 파일: config.json, run.py (시험 tests/test_briefing.py는 검토용으로만 두고 staging에는 안 올림)
- 내용: 필요 달러 브리핑 발송 중단. send.need=false면 need 단계를 보내지 않고 latest에 status disabled로 기록. 포트폴리오 브리핑은 그대로 (send.portfolio=true). need.json 계산(office_briefing.py)은 건드리지 않음. 타이머·서비스는 그대로 두고 발송만 끔. 발송 중단 범위는 풀이님 확정 (2026-11-25).
- 브랜치: staging

## v1.0.1 · 2026-11-20 12:26 (KST)
- 파일: __init__.py, meritz.py
- 내용: 7번 이름 변경: 속쓸 적립봇 → SOXL 탑쌓기, 7번 v2.2.11, 사무실 v1.9.6, 브리핑 1.1.1
- 브랜치: staging

