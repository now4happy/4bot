방: 메리츠 속쓸 적립봇 (meritz-soxl-dca-bot) — v2.0.5 변경 로그 (2026-11-19, 판 7)

# 한 줄
Q22 체결 내역 심볼 필드 수정(iscd 읽기) + 정규장 외 매도 확인(문서 근거 없음 → "004" 아니면 건너뜀 유지) + 버전 v2.0.5. 기준 v2.0.4(Muse 검증 완료).

# 1. Q22 심볼 필드 (meritz_api.fills_rows)
- 체결 행 심볼을 `ovrs_stck_symb_iscd` 가 있으면 그것, 없으면 `iscd` 로 읽음 (`r.get("ovrs_stck_symb_iscd") or r.get("iscd")`).
- 근거: 실제 체결 내역 응답은 iscd 만 있음 (Muse 서버 확인 — ovrs_stck_symb_iscd present: False, iscd present: True / openapi.json 응답 스키마도 같음).
- 효과: 자동 확인(reconcile_attempts)이 심볼로 후보를 거름 (예전엔 sym 이 항상 "" 라 다른 종목을 못 걸렀음).
- `holding()`·`open_orders_today()` 는 안 건드림 (holding 은 실전 SOXL 299주로 ovrs_stck_symb_iscd 확인됨).

# 2. 정규장 외 매도 — 결론: 확인 불가, 현재 동작 유지
- 확인한 것 (Muse 발췌 13_meritz-openapi-extract.md, 원본 openapi.json 2026-11-19): 장 운영 구분 코드 003 프리마켓 개시 · 004 정규장 개시 · 005 애프터마켓 개시 · 006 애프터마켓 종료 · 001/002 주간거래 · 000 휴장 · 011/012/013. 장 상태를 003·005 로 구분해 알 수는 있음.
- 매도 주문 API(/trading/v1/overseas/orders/sell)에는 장전/장후(연장 시간) 구분 필드가 없음. oder_cond_cls_code "2"(개장 전)는 LOO/MOO 를 장 개시에 체결시키는 조건이지 프리마켓 시간 거래가 아님. 시세 조회에만 주간·애프터 구분이 있음.
- 문서에 "지정가 매도(01·조건 0)를 003·005 에 내면 접수·체결되는가" 가 없음 → "가능"이라고 할 수 없음. 실거래 시험 안 함(사용자 결정 필요), 거절됐을 때 안전하게 실패하는지도 미확인.
- 그래서 `run_intraday_sell` 은 `us_market_status != "004"` 이면 건너뜀(반환 "장 닫힘") 그대로. 동작 변경 없음, 근거 주석 추가.
- 테스트: 003·005·006·001·000·012·013·빈 값에서 매도 주문이 안 나가고 "장 닫힘", 004 에서는 나감.
- 다시 열려면: ① 메리츠에 지정가 연장 시간 주문 가능 여부 확인 또는 ② 사용자 승인 아래 소량 실거래 시험(003/005 에 지정가 매도 접수 여부·오류 코드 확인).

# 3. 버전
BOT_VERSION v2.0.5 · 머리말 · README 제목 · 이 로그.

# 검증 (가짜 API·임시 폴더만, 서버·실계좌·실주문·실 텔레그램·실 메리츠 API 미실행)
- test_accum 29/29 · test_menu 43/43 · test_review 34/34 (v2.0.4 의 27개 + 신규 7개) · py_compile 통과.
- 신규 7개 중 iscd 3개는 v2.0.4 의 meritz_api.py 로 돌리면 실패함을 확인(수정 전 코드에서 실패 → 수정 후 통과).
- 지원 파일 config.py·global_throttle.py·strategy_v14.py 는 첨부 대상이 아니라 GitHub(now4happy/4bot staging)에서 받아 v2.0.3 해시와 일치 확인 후 테스트에 씀.
