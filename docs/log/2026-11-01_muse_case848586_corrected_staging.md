# 2026-11-01 Muse — Case 84·85·86 보완본 staging (1번 상황판 8번 적용 뒤)

- 기준: main e56edcac44792b56337172eca6bfdbe39f286f73 (상황판 8번 적용 완료 상태).
  보완본 5개 파일은 이 main과 대조했고, Case 변경 외에 main 내용이 사라지는 줄이 없다.
  (quant_engine.py의 기존 수수료 계산 3줄만 보완된 계산으로 교체됐다.)
- 원본 staging 73e12f3이 아니라, 이 방에서 만든 보완본이다.
  Case 84: 15:30~15:59 EST, 0주 새 사이클 + BREAKOUT_RELOAD만 차단, DIP·PULLBACK 허용.
  Case 85: f-string 오기 치유, 따옴표·속성 케이스 포함, 원본 백업 유지.
  Case 86: commissions 응답 파서(result·시장별 키, 단위 정규화), 24시간 재동기화,
  매도 실측 + 매수 편도 추정 정산, tax 없어도 실측 사용.
- 문법 검사 통과, 비밀 스캔 깨끗함.
- 아직 미완료 (서버 적용 승인 전에 확인 필요):
  1) 실제 GET /api/v1/commissions 응답 모양·단위 1건 확인
  2) execution.commission이 매도 편도인지 왕복 전체인지 확인
  보완본은 execution.commission을 매도 편도로 가정하고 매수 편도를 더한다.
  왕복 전체로 확인되면 매수 편도 추정을 빼야 한다.
- 서버 적용은 아직 안 함. 텔레그램 6. Update 알림 승인 대기 중.
