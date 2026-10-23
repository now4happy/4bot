# 2번 토스 스나이퍼 변경 기록

## v1.0.5 · 2026-10-23 16:44 (KST)
- 파일: averaging_merge.py, averaging_plugin.py, candle_recorder.py, defense_plugin.py, main.py, plugin_updater.py, quant_engine.py, sniper_plugin.py, tg_router.py, tg_ui_plugin.py, toss_api.py, whipsaw_plugin.py
- 내용: 2번 스나이퍼 v1.0.5 + 원작 자동 합치기
- 브랜치: staging

## v1.0.4 · 2026-10-22 08:10 (KST)
- 파일: sniper_plugin.py, main.py, tg_ui_plugin.py, tg_router.py, quant_engine.py
- 내용: (이전 버전에 이어서) 하루 2번 자동매매(데이장 19:00~03:29 EST 매수 → 03:30 강제 청산 / 프리장 04:00~09:29 매수 → 15:50 강제 청산), 데이장 매매 텔레그램 켜기·끄기, 추가 매수 혼합형 간격(RSI 35 재장전 + 직전 매수가 -N%, 제어반 0.3~1.0% 설정·기본 0.7), 손절 호가 간격 대응(15초 중간가), 손절 체결 결과 알림

## v1.0.3 · 2026-10-22 04:20 (KST)
- 파일: sniper_plugin.py, main.py, tg_ui_plugin.py
- 내용: 데이장(19:00~03:59 EST) 실거래 매수(프리장과 같은 규칙·한 사이클), 강제 청산 15:50 EST 시작, 추가 매수 혼합형 간격(RSI 35 재장전 + 직전 매수가 -0.7%), 손절 호가 간격 대응(15초 중간가), 손절 체결 결과 알림

## v1.0.2 · 2026-10-21 21:07 (KST)
- 파일: main.py, sniper_plugin.py, tg_router.py, tg_ui_plugin.py
- 내용: 09:30 이후에도 손절 작동
- 요약: 손절 라인이 최대 차수까지 샀을 때뿐 아니라 09:30 매수 마감 뒤(더 살 수 없을 때)에도 작동합니다. 익절 목표는 원래대로(+0.64% 또는 +1.00%) 유지합니다.
- 결재 번호: 2182eb46

## v1.0.1 · 2026-10-21 20:53 (KST)
- 파일: main.py, quant_engine.py, sniper_plugin.py, tg_router.py, tg_ui_plugin.py
- 내용: 최대 차수 매수 후 손절 라인
- 요약: 최대 차수까지 모두 산 뒤 현재가가 전체 평단가 대비 설정한 %(1.0~5.0) 아래로 떨어지면 익절 덫을 취소하고 전량 매도합니다. 손절 뒤에는 그날 신규 진입을 멈춥니다. 제어반(/settlement)에 손절 라인 설정 버튼이 생기며 처음에는 꺼져 있습니다.
- 결재 번호: d0727672

