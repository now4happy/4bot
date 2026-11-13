# 메리츠 적립 변경 기록

## v1.1.1 · 2026-11-13 14:26 (KST)
- 파일: main.py, t_core.py
- 내용: 토스 브리핑 키 읽기 폴백 (TOSS_DIR → SNIPER_DIR, office_briefing vNEXT)
- 브랜치: staging

## v1.1.0 · 2026-11-13 12:38 (KST)
- 파일: main.py, sgov.py, t_core.py, t_ui.py
- 내용: SGOV 테스트 파일 staging에서 제외 (업데이터 허용 파일 아님)
- 브랜치: staging

## v1.1.0 · 2026-11-13 (KST)
- 파일: main.py, t_core.py, t_ui.py, sgov.py(새 파일), README.md
- 내용: SGOV(미국 초단기 국채 ETF) 회차 적립 — 같은 봇·같은 4번 계좌, NKE/QLD 동작은 그대로
  - 상태 파일 최상위 `sgov` 블록 (stocks 에 넣지 않음) · 모으기만 (익절·N7·분할매도·½ 매수 없음)
  - 환율 관문: (a) 적용환율 < 36개월 평균 (공개 USD/KRW 일별 종가, 하루 1번) · (b) 7일 상승 ≥ X%(기본 1.5) → 건너뜀
  - 건너뛴 회차는 맨 뒤로 · 연속 건너뜀 메뉴 설정(review 기본 / proceed3)
  - 현금 분리: SGOV 예약분·대기 달러를 적립 매수 달러 검사에서 뺌 · 아침 환전에 SGOV 몫 더함
  - 관제탑 🪙 SGOV 메뉴 (X·모드 변경, 재점검 완료, 분배금 기록, SGOV 장부 따로 표시) · --check 미리보기
- 브랜치: staging

## v1.0.2 · 2026-11-13 12:25 (KST)
- 파일: main.py, meritz_api.py, t_core.py
- 내용: 메리츠 4번 낮 자동환전 참고가 fallback (meritz_dca v1.0.2)
- 브랜치: staging

## v1.0.1 · 2026-11-12 13:20 (KST)
- 파일: main.py, meritz_api.py, t_core.py
- 내용: 메리츠 4번 need 브리핑 + 자동환전 (office_briefing vNEXT, meritz_dca v1.0.1)
- 브랜치: staging

# meritz_dca.service 변경 기록

## v1.0.0 · 2026-11-08 05:25 (KST)
- 파일: dca_engine.py, main.py, meritz_api.py, replay_log.py, t_core.py, t_ui.py
- 내용: 업데이터: NAMES에 meritz_dca.service 추가 (메리츠 적립, 사무실 vNEXT)
- 브랜치: staging

