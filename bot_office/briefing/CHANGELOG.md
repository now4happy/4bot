# 9번 브리핑 변경 기록

## vNEXT · 2026-11-25 (타이베이)
- 파일: config.json, run.py (시험 tests/test_briefing.py는 검토용으로만 두고 staging에는 안 올림)
- 내용: 필요 달러 브리핑 발송 중단. send.need=false면 need 단계를 보내지 않고 latest에 status disabled로 기록. 포트폴리오 브리핑은 그대로 (send.portfolio=true). need.json 계산(office_briefing.py)은 건드리지 않음. 타이머·서비스는 그대로 두고 발송만 끔. 발송 중단 범위는 풀이님 확정 (2026-11-25).
- 브랜치: staging

## v1.0.1 · 2026-11-20 12:26 (KST)
- 파일: __init__.py, meritz.py
- 내용: 7번 이름 변경: 속쓸 적립봇 → SOXL 탑쌓기, 7번 v2.2.11, 사무실 v1.9.6, 브리핑 1.1.1
- 브랜치: staging

