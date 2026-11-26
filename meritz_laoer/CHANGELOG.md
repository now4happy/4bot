# 메리츠 SOXL 하이브리드모드 변경 기록

## v1.5.3 · 2026-11-26 13:51 (KST)
- 파일: main.py
- 내용: 판 46 (v2.19.0): 마감 일일결산에 당일 실현수익·매수/익절·누적실현 + 줄별 이모티콘
- 브랜치: staging

## v1.5.2 · 2026-11-26 11:44 (KST)
- 파일: main.py
- 내용: 판 45 (v2.18.0): run_sync 평소 체결 반영 메시지 발송 삭제 + 비정상 때만 짧은 알림
- 브랜치: staging

## v1.5.2 · 2026-11-26 11:37 (KST)
- 파일: main.py
- 내용: 판 45 (v2.18.0): run_sync 평소 체결 반영 메시지 발송 삭제 — 마감 일일결산만 남김. 동기화·장부 반영·잔고 대조·halt 로직은 그대로. 비정상 때만 짧게 알림 (주문 응답 유실·보유 0주 사이클 종료·잔고 불일치 정지). 시험 파일은 검토 폴더에만 둠
- 브랜치: staging

## v1.5.1 · 2026-11-26 10:10 (KST)
- 파일: main.py, notifier.py
- 내용: 판 44 (v2.17.0): 아침 자동환전 동기화 게이트 삭제 + 파일 이름 표시 수정
- 브랜치: staging

## v1.5.1 · 2026-11-26 09:26 (KST)
- 파일: main.py, notifier.py, README.md
- 내용: 판 44 (v2.17.0): 아침 자동환전 동기화 게이트 삭제 — 미동기화 주문 기록이 있어도 환전 진행. 환전 필요액은 설정값만으로 계산하고 달러·원화 예수금·환율은 실시간 조회라 장부가 금액을 틀리게 만들 수 없음. 환전 창(09:00 KST)이 동기화 시각(20:00 ET)보다 1시간 먼저 열려 매일 아침 '자동환전 안 함 — 체결 반영 전인 주문 기록' 알림이 반복되던 근본 원인 (11-24·11-25 이틀 연속 확인). notifier.py: 파일 이름이 '설정값-11-25.json' 으로 바뀌던 표시 문제 수정 (to_korean 이 파일 이름을 그대로 둠). 시험 파일은 검토 폴더에만 둠
- 브랜치: staging

## v1.5.0 · 2026-11-25 13:51 (KST)
- 파일: main.py, tower_strategy.py
- 내용: 판 43 (v2.16.0): 탑 매도 후 미완성 F 2개 방지 — 빈 F 삭제 + Q1 합치기 + Q5 초과분 분리
- 브랜치: staging

## v1.4.10 · 2026-11-25 13:40 (KST)
- 파일: main.py, tower_strategy.py
- 내용: 메리츠 v2.16.0 (판 43): 탑 매도 후 미완성 F 2개 방지 — 빈 F 삭제(완성 F가 다시 미완성이 되면 빈 F 전부 삭제) + Q1 합치기(방금 판 F를 원래 미완성 F에 합침, 전량 체결 때·부분 체결로 끝나면 동기화 때, 원래 F 번호 유지) + Q5 초과분 분리(합산 15,000달러 초과분은 같은 평단의 새 공사중 F로, 스나이퍼가 계속 채움) + 합친 F·새 공사중 F 당일 매도 차단. 시험 파일(test_hybrid_v430)은 검토 폴더에만 둠
- 브랜치: staging

## v1.4.9 · 2026-11-25 13:14 (KST)
- 파일: assassin_live.py, barbell_adapter.py, config.py, free_cash.py, main.py, meritz_api.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.15.0 (판 41): 암살자 실전 루프 + GUARD30 수혈 + 틱 종료 분리 + 마감 일일결산 + 바벨 삭제
- 브랜치: staging

## v1.4.9 · 2026-11-25 11:44 (KST)
- 파일: main.py, assassin_live.py(신규), free_cash.py(신규), barbell_adapter.py, meritz_api.py, tower_strategy.py, tg_menu.py, config.py, sniper_adapter.py, sniper_mode.py, 시험 파일(test_hybrid_v260·v340·v350·v351_render·v360·v390·v400 수정, test_v2_15_0 신규)
- 내용: 메리츠 v2.15.0 (판 41): ① 암살자 실전 루프 연결(원작 틱을 메리츠 API로 호출·1분 폴링 400봉 누적·정정(modify) API·승격 잠금 해제, LIVE면 하이브리드 정지) ② GUARD30 수혈 장부(free_cash·INJECT·매도 시 수혈금 먼저 상환) 이식 ③ 틱 종료 분리(20:00 ET 마감 뒤에도 매도 창 동안 틱) ④ 마감 일일결산 텔레그램 1개 ⑤ 바벨(금고·SGOV 30%·60/30/10·버튼) 삭제. 승격 1탭·SCHD 삭제는 파기라 안 함. 수정 1차: modify 본문에 oder_cond_cls_code "0" 추가(공식 스펙 필수 6필드), 옛 시험 48건 정리(삭제 15건·수정 33건)
- 브랜치: staging

## v1.4.8 · 2026-11-25 11:00 (KST)
- 파일: main.py, meritz_api.py, sniper_mode.py
- 내용: 메리츠 v2.14.0 (판 42): 미체결 매수 60초 안전 취소 + 야간 코드 001 SELL_STATUS 확장
- 브랜치: staging

## v1.4.8 · 2026-11-25 09:53 (KST)
- 파일: main.py, meritz_api.py, sniper_mode.py, 시험 파일(test_hybrid_v380 수정, test_hybrid_v410 신규)
- 내용: 메리츠 v2.14.0 (판 42): P1 미체결 매수 60초 안전 취소 (원작 BUY_ORDER_MAX_WAIT_SEC=60.0 이식, 취소 API 연결) + Q1 야간 코드 "001" SELL_STATUS 확장 (판 41 항목 3)
- 브랜치: staging

## v1.4.7 · 2026-11-24 12:41 (KST)
- 파일: barbell_adapter.py, config.py, main.py, sniper_adapter.py, sniper_mode.py, tg_menu.py
- 내용: 메리츠 v2.13.0 (판 40): 1.5초 루프 + 암살자 실전(부분) + 매도 창 전체 + GUARD30 검문 + 금고 + B-0
- 브랜치: staging

## v1.4.7 · 2026-11-24 (KST) — 봇 v2.13.0 (판 40)
- 파일: barbell_adapter.py, config.py, main.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, 시험 파일(test_hybrid_v340·v351_render·v380·v390 수정, test_hybrid_v400 신규)
- 내용: ① 1.5초 틱 루프 + 분 경계 쉴드 (되돌리기: sniper_tick_sec=30) ② 암살자 승격 버튼·확인·execution_mode 저장 (실전 매매 루프는 미연결, assassin_live_unlock 기본 False) ③ 틱을 매도 실효 창 전체(주말·야간)로 확장, 일일 기록 마감(sync_time_et)과 분리 ④ GUARD30 (바벨 꺼짐일 때 단리·복리 온디맨드 검문, 금고 제외) ⑤ 바벨 수익금 금고 되살림, SCHD 제거 ⑥ B-0 부분체결 잔량 보충 (본 그리드; 서브 S-B0 는 SUB_GRID_ON=False 라 꺼짐)
- 원작 orig_sniper/ 바이트 동일, BOT_VERSION v2.7.0 유지
- 브랜치: staging

## v1.4.6 · 2026-11-24 11:15 (KST)
- 파일: config.py, main.py, meritz_api.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.12.0 (판 39): 첫 매수 원작화 + 메뉴 원작화
- 브랜치: staging

## v1.4.6 · 2026-11-24 10:13 (KST)
- 파일: README.md, config.py, main.py, meritz_api.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py, 시험 파일(test_hybrid_v250·v260·v270·v320·v330·v340·v350·v351_render·v360·v370·v300·v390)
- 내용: 메리츠 v2.12.0 (판 39): 첫 매수 원작 분기 A(가격 조건 없이 현재가·검문 포함) + 레이더 전술 제어반(복리 모드·바벨 관제보드) + 시드 설정 잔고 동기화로 이동 + 동기화 20:00 ET + 1분봉 함수 + 옛 시험 정리
- 브랜치: staging

## v1.4.5 · 2026-11-24 09:41 (KST)
- 파일: main.py, ORIGIN.json, barbell_plugin.py, sniper_exit_plugin.py, sniper_adapter.py, sniper_mode.py, sub_grid.py
- 내용: 메리츠 v2.11.0 (판 38): Audit-113 동기화 + 시간 확대
- 브랜치: staging

## v1.4.5 · 2026-11-24 09:39 (KST)
- 파일: README.md, main.py, orig_sniper/ORIGIN.json, orig_sniper/barbell_plugin.py, orig_sniper/sniper_exit_plugin.py, sniper_adapter.py, sniper_mode.py, sub_grid.py
- 내용: 메리츠 v2.11.0 (판 38): Audit-113 동기화 (원작 23a16d5 복사본 2개 + ORIGIN.json, Audit-113-02 1499→1459) + 시간 확대 (매수 04:07~16:00, 매도 04:00~04:06 제외 전 세션 — 16:10 이후 미적용, 조건부 통과)
- 브랜치: staging

## v1.4.4 · 2026-11-23 21:32 (KST)
- 파일: grid_tiers.py, main.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 판 37 후속: Case 113 100% 이식 (암살자 제외) — 7층 상한·합병·고정 태그·계단 복원·2층 공석 OFF
- 브랜치: staging

## v1.4.3 · 2026-11-23 11:43 (KST)
- 파일: config.py, main.py, ORIGIN.json, quant_engine.py, quant_engine_core.py, quant_indicators_plugin.py, sniper_exit_plugin.py, toss_api_core.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.10.0 (판 36): 브리핑 타이머를 스테이징에서 제외 — 메리츠 파일만 적용 대상으로
- 브랜치: staging

## v1.4.3 · 2026-11-23 11:25 (KST)
- 파일: README.md, config.py, main.py, orig_sniper/ORIGIN.json, orig_sniper/quant_engine.py, orig_sniper/quant_engine_core.py, orig_sniper/quant_indicators_plugin.py, orig_sniper/sniper_exit_plugin.py, orig_sniper/toss_api_core.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.10.0 (판 36): Case 113 이식 (단일 통합 T4 엔진 — 황금비율 눌림 10%·바벨 코어 15%, 서브·스토커·마중물·돌파 폐기, 1층 익절 1.0%, T4 래칫, 컷오프 15:00, 개장 7분 쉴드)
- 브랜치: staging

## v1.4.2 · 2026-11-22 22:11 (KST)
- 파일: tg_menu.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 14차): 레이더에 스나이퍼 설정 바로 표시
- 브랜치: staging

## v1.4.3 · 2026-11-22 21:07 (KST)
- 파일: tg_menu.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 14차): 레이더에 스나이퍼 설정 바로 표시 (스나이퍼 설정 버튼 빼고 설정 6개를 2개씩 묶어 레이더에 바로 표시, 레이더에서 바꾼 설정은 레이더에 머무름, snset 화면은 그대로)
- 브랜치: staging

## v1.4.2 · 2026-11-22 22:04 (KST)
- 파일: tg_menu.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 13차): 봇 상태 안내 문구 고침 (12차에 뺀 봇 켜기/끄기·도구 버튼을 가리키던 말 수정 — 봇 상태 화면·동기화 안내·환전 힌트. 채팅에 직접 보내면 돼요: '봇 끄기'·'매매 정지'·'장부 시작'·'주식 넣기')
- 브랜치: staging

## v1.4.1 · 2026-11-22 21:59 (KST)
- 파일: tg_menu.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 12차): 레이더·동기화 메뉴 단순화·탑쌓기 메뉴 정리
- 브랜치: staging

## v1.4.1 · 2026-11-22 20:52 (KST)
- 파일: tg_menu.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 12차): 레이더·동기화·탑쌓기 메뉴 단순화 (레이더는 스나이퍼 설정 버튼만, 동기화 결과는 글만, 탑쌓기 화면은 시작·바벨 먼저 + 설정 2개씩 묶음, 봇 전원·도구 뺌)
- 브랜치: staging

## v1.4.0 · 2026-11-22 21:19 (KST)
- 파일: config.py, main.py, notifier.py, seed_adjust.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 11차): 용어 정리 문법 오류 고침
- 브랜치: staging

## v1.3.11 · 2026-11-22 20:16 (KST)
- 파일: tower_strategy.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 11차): 용어 정리 문법 오류 고침 (f-string 안에 같은 따옴표 중첩 — Python 3.12 전용 문법이 10차에 들어가 서버 3.10에서 문법 오류로 롤백됨)
- 브랜치: staging

## v1.3.10 · 2026-11-22 21:09 (KST)
- 파일: config.py, main.py, notifier.py, README.md, seed_adjust.py, sniper_adapter.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 10차): 남은 용어 정리 ("층" → F 표기, F 완성 기준 금액, 새 시드, 맨 위 F 시작가)
- 브랜치: staging

## v1.3.9 · 2026-11-22 20:35 (KST)
- 파일: tg_menu.py
- 내용: 메리츠 v2.9.0 (판 35 수정, 9차): 레이더 인라인 버튼 KeyError 고침
- 브랜치: staging

# 메리츠 SOXL 무매 변경 기록

## v1.3.8 · 2026-11-22 18:45 (KST)
- 파일: config.py, main.py, notifier.py, seed_adjust.py, sniper_adapter.py, sniper_mode.py, sub_grid.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.9.0 (판 35, 8차): 용어·텔레그램 개편
- 브랜치: staging

## v1.3.7 · 2026-11-22 17:52 (KST)
- 파일: barbell_adapter.py, config.py, main.py, tg_menu.py, tower_strategy.py
- 내용: 메리츠 v2.9.0 (판 34, 7차): 바벨·SGOV·SCHD·암살자 연결
- 브랜치: staging

# 7번 메리츠 SOXL 탑쌓기 변경 기록

## v2.4.0 · 2026-11-22 (KST) — 판 35 수정 (meritz_laoer v2.9.0 9차, 레이더 인라인 버튼 KeyError 고침)
- 파일: tg_menu.py, CHANGELOG.md, test_hybrid_v351_render.py(신설). 원작 orig_sniper/* 안 고침.
- 고침: RADAR_INLINE의 "⚙️ 스나이퍼 설정" 문자열을 ("⚙️ 스나이퍼 설정", "스나이퍼 설정") 튜플로 고침. ikb()가 LABEL_IDX에서 이모티콘 붙은 글자를 못 찾아 KeyError가 나 스나이퍼 레이더·잔고 동기화·레이더 안 조회가 전부 죽던 문제. 보이는 글자는 그대로, 버튼 이름은 이모티콘 없는 "스나이퍼 설정".
- 시험: 모든 인라인 키보드에 ikb()를 실제로 돌리는 렌더링 시험 신설(test_hybrid_v351_render.py 6개). v350이 bot.send를 mock으로 갈아끼워 ikb()를 안 타서 이 버그를 놓쳤던 걸 막음. v350 기대값도 튜플 형태로 고침(시험만, staging 안 올림).
- 미실행: 서버·실거래·텔레그램 실발송.

## v2.4.0 · 2026-11-22 (KST) — 판 35 (meritz_laoer v2.9.0 8차, 용어 정리 + 텔레그램 개편)
- 파일: main.py, seed_adjust.py, tower_strategy.py, tg_menu.py, sniper_mode.py, sniper_adapter.py, sub_grid.py, config.py, notifier.py, barbell_adapter.py, README.md, CHANGELOG.md, 옛 시험 8개(문구·해시 고정만), test_hybrid_v350.py(신설). 원작 orig_sniper/* 안 고침.
- 용어(동작 변경 없음): "F 시드"→"F 완성 기준 금액", "층 $720"→"버킷 $720", "박스"→"버킷"(주석·문서·표시 문구, 11개 파일). 기준: 버킷 = 매수 1건(원작 StratumBucket) · 층 = 그리드 단계(원작 tier) · F = 탑쌓기 위치(하이브리드 전용). sniper_adapter.py 헤더 옛 문구·sniper_mode.py RSI 주석(판 30 Q2: RSI 모르면 돌파 안 막음) 고침. 설정 키 이름(tower_box_seed_usd 등)은 안 바꿈.
- 텔레그램: 전술 제어반(⚙️) 삭제. 첫 화면 [🔫 스나이퍼 레이더][🏛️ 탑쌓기 매매] / [🔄 잔고 동기화][💱 환전]. 스나이퍼 레이더 안 [⚙️ 스나이퍼 설정](버킷 시드·눌림%·돌파%·첫 기준가·1층 익절·상단층 익절). 탑쌓기 매매 화면 안: 매수 간격·F 완성 기준 금액·탑쌓기 매도%·매도 비중·하루 매수/매도 F 수·남은 시드 + 매매 모드·바벨·봇 켜기/끄기·도구 버튼(옮길 곳이 없어 같은 화면에 둠).
- 화면 문구: 졸업 매도 표시("· 졸업 매도", kind=grad), 돌파 RSI 문구("RSI 50 이하일 때만 · RSI 모르면 그냥 통과").
- 미실행: 서버·실거래·텔레그램 실발송.

## v2.3.0 · 2026-11-22 (KST) — 판 34 3차 (meritz_laoer v2.9.0 7차, Q6~Q9 반영)
- 파일: main.py, barbell_adapter.py, test_hybrid_v340.py, CHANGELOG.md. 원작 orig_sniper/* 안 고침. 안 바뀜: tower_strategy.py, config.py, tg_menu.py 등 (2차와 같음).
- Q6 free_cash: 바벨 켠 뒤 처음 한 번 $9,000 − 미완성 F 원가로 시작 → SOXL 매수 체결 −, 매도 체결 +, 수혈은 원작 guard 가 shim 원장에 +. 
- Q7: 실현수익은 금고에 안 넣고 SCHD 매수 대기금에 누적 → 1주 값 이상 모이면 정수 주 지정가 매수(못 사면 계속 모음, 주문 실패면 대기금 그대로). 원작 record_barbell_realized_profit 은 안 부름(금고 비어 있음).
- Q8: 수혈 워터폴 = 매수 직전(send_order) 원작 evaluate_and_execute_barbell_guard30_or_injection 호출, 못 통과하면 그 매수 보류. SGOV 실주문 = 실거래(dry_run=false)일 때 메리츠 api.order(LIMIT) 경유 (SOXL 과 같은 방식), 체결 확인 = 체결 내역, 거래소 = 보유 조회 값 → sgov_exch_id → exch_id. 모의면 주문 안 나감.
- Q9: 바벨 틱마다(30초) SOXL·QQQ 시세를 1분 종가 봉으로 저장(시·고·저=종가, 거래량 0, VWAP 안 만듦) → 원작 1분 지표 함수로 암살자 모의 지표 기록. 암살자 모의(SIMULATED) 고정, LIVE 이면 새 매매 막음(원작 규칙).
- 미실행: 서버·실거래·SGOV/SCHD 실주문·메리츠 실시세·텔레그램 실발송.

## v2.2.0 · 2026-11-22 (KST) — 판 34 2차·부분 (meritz_laoer v2.9.0 7차, 바벨 연결)
- 파일: main.py, tower_strategy.py, config.py, tg_menu.py, barbell_adapter.py, test_hybrid_v340.py, test_hybrid_v300.py(해시 고정 항목만), CHANGELOG.md. 원작 orig_sniper/* 안 고침.
- 설정 barbell_enabled(기본 꺼짐, true/false 만). 텔레그램 [바벨 모드 켜기/끄기] → 확인 메시지 → [네, 바벨 바꿀게요] 를 눌러야만 바뀜. 켜면 F 완성 기준 금액 $15,000→$9,000, 버킷 시드 ×0.60 → 버킷 $720 (16:10 동기화에서 F 완성 기준 금액 조정이 다시 나눔). 꺼짐이면 판 33 과 똑같음.
- 연결됨: ① SOXL 매도 체결(apply_tower_fills) → 수익금 금고 기록(원작 record_barbell_realized_profit) ② SGOV 틱(run_sniper_tick 맨 앞, 원작 execute_barbell_sgov_tick_plugin) — 모의 전용(실주문 안 나감, 실거래 SGOV 주문은 막아 둠).
- 미연결: 4단계 수혈 워터폴(guard30/injection) 매수 직전 연결, SGOV 실주문, 암살자 1분봉 모의 실행(암살자는 모의 고정·실전 전환 코드 없음).
- 미실행: 서버 적용·실거래·SGOV 실주문/시세·텔레그램 실발송·푸시.

## v2.1.0 · 2026-11-22 (KST) — 판 34 1차·부분 (meritz_laoer v2.9.0 7차, 바벨 어댑터 + 암살자 모의 고정)
- 파일: barbell_adapter.py(신설), test_hybrid_v340.py(신설), CHANGELOG.md. 안 바뀜: main.py, sniper_mode.py, tower_strategy.py, config.py, tg_menu.py, notifier.py, seed_adjust.py, sniper_adapter.py, orig_sniper/*
- barbell_adapter.py: 원작 barbell_plugin.py·assassin_plugin.py 복사본을 안 고치고 부르는 얇은 층 — 60/30/10 배분, SGOV 정규장 시간창(09:31~15:55 EST), 현금 10% 상당 SGOV 정수 주 내림 수량, 바벨 전용 원장(state_dir/data/barbell), 암살자 실전 여부(원작 함수). 암살자는 모의(SIMULATED) 고정, 실전으로 바꾸는 코드 없음.
- 거래 코드에는 아직 연결 안 함(하이브리드 동작은 판 33 과 같음). 4단계 수혈 워터폴·수익금 금고 기록·SGOV 주문은 SOXL 원장 모양·SGOV API 결정이 필요해 질문란으로 넘김.

## v2.0.0 · 2026-11-22 (KST) — 판 33 (meritz_laoer v2.9.0 6차, 탑쌓기 매매 모드 + 잔고 동기화 F 완성 기준 금액 조정)
- 파일: main.py, sniper_mode.py, tower_strategy.py, config.py, tg_menu.py, notifier.py, seed_adjust.py(신설), CHANGELOG.md, test_hybrid_v330.py(신설), test_hybrid_v300.py(해시 고정 항목만 판 33 값도 허용). 안 바뀜: sniper_adapter.py, sub_grid.py, sync_orig.py, orig_sniper/*
- 탑쌓기 매매 모드: 설정 trade_mode(sniper 기본 | tower), 텔레그램 [탑쌓기 매매 시작] → 확인 메시지 → [네, 바꿀게요] 를 눌러야만 바뀜 (스나이퍼로 돌아갈 때도 같음). tower 일 때 스나이퍼 신호 매수 대신 하루 한 번 탑쌓기 매수: 시초가 가까운 칸부터 $1씩 아래로 tower_buy_gap_usd 칸(기본 5, 1~10), F 완성 기준 금액(기본 $15,000)를 칸마다 균등. 매도는 기존 그대로.
- F 완성 기준 금액 조정(잔고 동기화 둘째 일, 16:10 run_sync): 시드(F 완성 기준 금액·버킷 시드)가 바뀌면 보유 주식을 높은 F 부터 새 시드로 다시 채움/나눔 (합계 그대로, 평단 다시 계산, 텔레그램에 F 개수·평단·늘어난 층). 처음엔 기록만.
- 미실행: 서버 적용·실거래·푸시.

## v1.9.2 · 2026-11-22 (KST) — 판 32 3차 (meritz_laoer v2.9.0 5차, 래칫·하드캡·RSI 수확 거래 흐름 연결)
- 파일: sniper_adapter.py, sniper_mode.py, main.py, CHANGELOG.md, test_hybrid_v320.py(저장소 밖). 안 바뀜: tg_menu.py, tower_strategy.py, orig_sniper/* 등
- 내용: 질문 4·5 반영. 거래 루프가 시세를 읽을 때마다 SN.trail_tick(dry·live 2곳) → 1층(가장 낮은 버킷) 고정 +1.5% 매도가 원작 트레일링으로 바뀜(점화 +1.5%·샤프 래칫·하드캡 +6.0%·RSI 65 수확). 원작 흐름 그대로: 실호가가 점화가 밑이면 슬롯 해제, 보존선 이탈 신호인데 실호가가 정지가 이상이면 취소, 매도 하한가 = 보존선 이상(하드캡이면 캡 가격), 2층 동반 졸업. 졸업(전 층 전량)은 그대로 우선. 보존선·최고점은 메모리에만 두고 sniper_state.json 에 저장 안 함(재시작하면 다시 계산). 어댑터 sell_targets·sell_plan 에 exclude_l1 추가(원작 exclude_daytime_l1). 스토커 보류·VWAP 방어·HA 음봉 청산 안 함
- 검증: v320 36개 · v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250 16개 통과 · pyflakes 새 경고 0 · 실거래·서버 적용·push 없음

## v1.9.1 · 2026-11-22 (KST) — 판 32 2차·부분 (meritz_laoer v2.9.0 4차, 래칫·하드캡·RSI 수확 어댑터까지)
- 파일: sniper_adapter.py, sync_orig.py, orig_sniper/ORIGIN.json, orig_sniper/{sniper_exit_plugin.py, assassin_plugin.py, barbell_plugin.py, quant_indicators_plugin.py}(새, 원작 d9170fa 바이트 동일 — 해시로만 검증), CHANGELOG.md, test_hybrid_v320.py(저장소 밖). 안 바뀜: sniper_mode.py, main.py, tg_menu.py, tower_strategy.py 등
- 내용: 원작 sniper_exit_plugin.py 복사(질문 1 (a)) — import 에 필요한 3개도 같이 복사, ORIGIN.json files 로 등록(watch 에서 뺌)·sync_orig --check 가 import 까지 확인. 어댑터에 l1_trail_slot·l1_trail_sync·l1_trail_step·minute_key 추가 = 원작 SniperL1TrailSlot·_step_l1_trail_slot_candidate 호출 (단리 S-112: 샤프 래칫·하드캡 +6.0%·RSI 65 수확). 입력은 봇이 모은 1분 종가로 만든 값, 스토커·VWAP 방어·HA 음봉 청산은 안 함. ⚠ 새 의존성: quant_indicators_plugin 이 numpy·pandas 를 import. 거래 코드에는 아직 연결 안 함
- 검증: v320 24개 · v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250 16개 통과 · pyflakes 새 경고 0 · sync_orig --check 통과 · 실거래·서버 적용·push 없음

## v1.9.0 · 2026-11-22 (KST) — 판 32 1차·부분 (meritz_laoer v2.9.0 4차, 스토커·래칫·하드캡 이식 중)
- 파일: sniper_adapter.py, CHANGELOG.md, test_hybrid_v320.py(새, 저장소 밖), test_hybrid_v300.py(저장소 밖, 분봉 입력 금지 검사에서 어댑터 제외 1곳 수정). 안 바뀜: sniper_mode.py, main.py, tg_menu.py, tower_strategy.py 등, orig_sniper/*
- 내용: 어댑터에 단리 Case 112 정책(rebound_policy = S-112: 스토커 +0.25%·VWAP -3.0%·샤프 래칫·하드캡 6.0%·RSI 65)과 스토커 판정 래퍼(stalker_fire = 원작 evaluate_stalker_reversal_fire) 추가. 거래 코드에는 아직 연결 안 함 — 래칫·하드캡 실행부(SniperL1TrailSlot)가 원작 sniper_exit_plugin.py 안이라 복사본에 없고, 분봉·VWAP 입력이 메리츠 API 에 없어 Muse 결정 대기(질문란)
- 검증: v320 9개 · v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250 16개 통과 · pyflakes 새 경고 0 · 실거래·서버 적용·push 없음

## v1.8.1 · 2026-11-22 (KST) — 판 31 질문 3 (meritz_laoer v2.9.0 3차, 원작식 부분 주문)
- 파일: sniper_mode.py, main.py, CHANGELOG.md, test_hybrid_v310.py(저장소 밖). 안 바뀜: sniper_adapter.py, tg_menu.py, tower_strategy.py, sub_grid.py, config.py, notifier.py, orig_sniper/*
- 내용: 원작 execute_bulletproof_sell_sweep 방식 — 매도 주문 전 매도가능 수량을 2초(0.25초 간격) 기다림(SN.wait_sellable) · 목표(닿은 버킷 합, 졸업이면 전 버킷)에 매도가능이 모자라면 평단 낮은 버킷부터 가능한 만큼만 주문(마지막 버킷은 일부 수량) · 장외 매도가능 0이면 주문 없이 조용히 대기 · 정규장 0이면 원작처럼 목표 수량 시도. 부분 체결 정산은 기존 _apply_sell 이 체결 수량만큼만 버킷을 줄임(남은 버킷·남은 수량은 장부에 그대로 — 시험으로 확인). '전부 아니면 무'는 안 함 (Muse 결정)
- 검증: v310 21개 · v300 25개 · v270 7개 · v260 31개 · v250(수정) 16개 통과 · pyflakes 새 경고 0 (main.py 기존 5건·sniper_mode.py 기존 1건 그대로) · 실거래·서버 적용·push 없음

## v1.8.0 · 2026-11-22 (KST) — 판 31 (meritz_laoer v2.9.0 2차)
- 파일: sniper_mode.py, sniper_adapter.py, CHANGELOG.md, test_hybrid_v310.py(새, 저장소 밖), test_hybrid_v250.py(저장소 밖, test_04 기대값 1줄 수정). 안 바뀜: main.py, tg_menu.py, tower_strategy.py, sub_grid.py, config.py, notifier.py, orig_sniper/*
- 내용: 스나이퍼 매도 판정(box_rows)을 원작 evaluate_multi_grid_sell_targets 로 연결 (방식 B = 전체 층 그대로, Muse 결정; 비교 결과 A·B 동일). 미완성 층 버킷 전체를 한 묶음으로: 1층 +1.5% · 2층 +1.0%(닿으면 1층도 같이) · 3층 이상 개별 매도 없음 · 졸업(3층~끝 가중평단 +1.0%)에 닿으면 전 버킷 전량. 동작 변경(Muse 수락): 3층 이상 개별 +1.0% 매도 사라짐, '층마다 L1' → 전체 한 묶음 L1. 탑 매도·매수·서브 안 바뀜
- 검증: v310 14개 · v300 25개 · v270 7개 · v260 31개 · v250(수정) 16개 통과 · pyflakes 새 경고 0 (기존 copy 미사용 1건) · 실거래·서버 적용·push 없음

## v1.7.0 · 2026-11-22 (KST) — 판 30 (meritz_laoer v2.9.0 1차)
- 파일: sniper_mode.py, main.py, tg_menu.py, sniper_adapter.py, README.md, CHANGELOG.md, test_hybrid_v300.py(새, 저장소 밖). 안 바뀜: tower_strategy.py, sub_grid.py, config.py, notifier.py, orig_sniper/*
- 내용: 매수 신호 판정을 원작 복사본(어댑터 경유)으로 연결. B1 눌림 깊이 = 버킷 수 · B2 상한 = 가장 낮은 층 평단 · B3 눌림·돌파 % 비교 · B3b RSI 모르면 돌파 안 막음 · B4 서브 가동일 기록(seed_main_day). 매도·탑쌓기·서브 매수 규칙은 안 건드림
- 검증: test_hybrid_v300.py 25개 통과 · v270 7개·v260 31개 통과 · v250 16개 중 2개 실패(B1 이 바꾼 가정 — 되돌리면 통과) · 실거래·서버 적용·push 없음

## v1.6.0 · 2026-11-22 (KST) — 판 29 1차 (구조만, meritz_laoer v2.9.0 은 미완)
- 파일(새): orig_sniper/{quant_engine_core.py, quant_engine.py, toss_api_core.py (원작 d9170fa 바이트 동일), toss_api.py (shim), ORIGIN.json}, sniper_adapter.py, sync_orig.py, test_hybrid_v290.py(저장소 밖). 바뀜: README.md, CHANGELOG.md. 매매 코드(main.py·sniper_mode.py 등)는 안 바뀜
- 내용: 원작 순수 판정 함수 복사본 + 얇은 어댑터 + 원작 업뎃 적용 도구 + README 대응표(3단계 문서). 아직 매매에 연결 안 함 — 동작은 v2.7.0 과 같다. 미구현: 원작 이식 연결·스토커·래칫·바벨·탑쌓기 매매 모드·텔레그램 개편·잔고 동기화 시드 조정·용어(층·F) 변경 (VERIFY.md 미구현 절)
- 검증: test_hybrid_v290.py 13개 통과 · 기존 시험 v270·v260·v250 은 이 세션에 파일이 없어 미실행 · pyflakes 새 경고 0 · 실거래·서버 적용·push 없음
## v1.5.0 · 2026-11-21 (KST) — 판 27 (meritz_laoer v2.7.0)
- 파일: main.py, sniper_mode.py, tower_strategy.py, tg_menu.py, config.py, notifier.py, README.md, CHANGELOG.md, test_hybrid_v270.py(새). sub_grid.py 는 안 바뀜
- 내용: 층 간격 사용자 설정(tower_gap_usd) 제거 — 텔레그램 '층 간격 변경' 버튼·설정 검사·설정 표시·계획 '새 층 가격' 줄 삭제. 간격은 내부 고정값 GAP_USD=5로 칸 만들기에만 씀 (tower_strategy.params가 항상 5를 돌려줌). 설정 파일에 tower_gap_usd가 남아 있어도 무시·통과. 매매 로직은 안 건드림.
- 검증: test_hybrid_v270.py 통과 · 기존 시험(v260·v250) 통과 · pyflakes 새 경고 0. 자세한 건 VERIFY.md
## v1.4.0 · 2026-11-21 (KST) — 판 26 (meritz_laoer v2.6.0)
- 파일: main.py, sniper_mode.py, tower_strategy.py, tg_menu.py, config.py, notifier.py, README.md, CHANGELOG.md, test_hybrid_v260.py(새). sub_grid.py 는 안 바뀜
- 내용: ① 버킷별 매도 — 미완성 층의 매수 1건 = 버킷 1개(floor['boxes']), 버킷마다 자기 평단 기준 매도(그 층 안 최저 평단 버킷 +1.5% · 나머지 +1.0%, 그 버킷 전량), 층 원가·수량은 판 버킷 몫만 줄고 층 평단은 남은 버킷 가중평균, 층 완성 → 탑 매도. 예전 상태(버킷 없음)·탑 매도 잔여 = 버킷 1개 ② 눌림 매수% 설정 sniper_portion_pct(기본 8, 0 초과 100 이하) + 텔레그램 '눌림 매수% 변경'. 돌파 16%·서브 4% 그대로
- 검증: test_hybrid_v260.py 통과 · 기존 시험(v250·v240)·Golden 은 파일이 없어 미실행 · 실거래·서버 적용·push 없음. 자세한 건 VERIFY.md
## v1.3.0 · 2026-11-21 (KST) — 판 25 (meritz_laoer v2.5.0)
- 파일: main.py, sniper_mode.py, sub_grid.py(새), tower_strategy.py, tg_menu.py, config.py, notifier.py, test_hybrid_v250.py(새)
- 내용: 하이브리드 버킷·층 (토스 스나이퍼 이식): 매수 1번 = 버킷 시드(기본 $15,000)의 8% · 서브 그리드 4% · 버킷 안 자동 매도(+1.5%/+1.0%) 복귀 · 층 간격 규칙 삭제 · 첫 기준가 설정 · 평단 정수 달러 층 이름 · 지하층→공사중 · 퍼센트 작업 계산(percent_plan). 판 24 선택 질문 코드는 남기고 안 부름.
- 수정1(돌파 매수액): 설정 sniper_breakout_portion_pct(기본 16%, 눌림 8% 그대로) + 텔레그램 '돌파 매수% 변경' 메뉴.
- 검증: test_hybrid_v250.py 16개 통과 · pyflakes 새 경고 0 · import 확인. test_hybrid_v240.py·Golden 비교는 파일이 없어 미실행. 실거래·서버 적용 없음.

## v1.2.9 · 2026-11-21 11:08 (KST)
- 파일: main.py, notifier.py, sniper_mode.py, tg_menu.py, tower_strategy.py
- 내용: 판 24 meritz_laoer v2.4.0 (층 나눔·잠금·스나이퍼 선택: 장부 바로잡기 684주·지하층·선택 버튼·업데이트 알림 판 번호). 검증: 새 시험 18개 통과, 기존 시험 40개 통과·3개 실패(의도한 변경), 해시 전부 일치, 비밀 0건.
- 브랜치: staging

## v1.2.8 · 2026-11-21 09:05 (KST)
- 파일: main.py, sniper_mode.py, tg_menu.py
- 내용: meritz_laoer v2.3.0 (판 23 수정1: 장중 환전 고침 제외·하루 매수 층 수 제한·B3 미체결 조회·B7 모의 스나이퍼·S3 눌림 잠금·S1 16:10 뒤 체결 다음 날 반영·라벨 고침·죽은 코드 제거). 검증: 새 시험 43개 통과, 기존 시험 17개 통과·27개 실패(의도한 변경), 해시 전부 일치, 비밀 0건.
- 브랜치: staging

## v2.4.0 · 2026-11-21 (KST) — 판 24 (office 번호는 적용 때 확정, 미확인)
- 파일: tower_strategy.py, sniper_mode.py, main.py, tg_menu.py, notifier.py, bot_office/bot_updater.py, README.md, CHANGELOG.md, VERIFY.md (+ 새 시험 test_hybrid_v240.py)
- 내용: meritz_laoer v2.4.0 (판 24) — ① 일회성 장부 바로잡기(실제 잔고 684주일 때만, 층 373주 $40.29 · 311주 $48.14 잠금 + 지하층) ② 잠금=탑 매도 ③ 지하층부터 스나이퍼 매수 ④ 스나이퍼 목표 도달 시 자동 매도 대신 텔레그램 선택(스나이퍼/탑쌓기) ⑤ 업데이트 알림 맨 앞 판 번호 · 수동 확인이 대기 목록 표시
- 브랜치: staging 에 올리기 전 (검토 대기)

## v1.2.8 수정1 · 2026-11-21 (KST) — 버전 v2.3.0 그대로 (판 23 수정1, 풀이님 정정 반영)
- 파일: main.py, sniper_mode.py, tg_menu.py, README.md, CHANGELOG.md, test_hybrid_v230.py
- 내용: ① (풀이님 결정으로 뺌) 장중 환전 고침 — auto_fx 마커·하루 한 번 환전은 v2.3.0 그대로, test_intraday_fx_exchanges_only_shortfall 도 그대로 ② 하루 매수 층 수 제한: 그날 매수 주문이 나간 층 수가 tower_max_buy_layers_per_day(기존 설정, 새 설정 없음)에 닿으면 새 층 매수는 안 하고 알림만(하루 한 번), 거절·취소 주문은 안 셈, 이미 산 층의 남은 시드 채우기는 계속 ③ B3 미체결 판단을 미체결 조회(open_orders_today)로 (앱에서 취소한 주문은 매수·매도 잠금에서 빠짐) ④ B7 모의에서도 스나이퍼 틱이 돌되 주문 없이 시뮬레이션 기록(dry_orders_<날짜>.json) ⑤ S3 눌림 깊이 = max(현재 층 수, 사이클 최고 층수) — sniper_state.json peak_layers, 0주면 초기화 ⑥ S1 16:10 동기화 뒤 체결은 다음 날 첫 확인 때 장부·층에 반영(최근 4일 기록, late_done 표시) ⑦ 정리: pyflakes 새 경고 5개, '목표 도달' 라벨, 죽은 코드 defer_sell·limit_morning_sells 제거
- 브랜치: staging 에 올리기 전 (검토 대기)

## v1.2.8 · 2026-11-21 (KST)
- 파일: tower_strategy.py, sniper_mode.py, config.py, main.py, tg_menu.py, notifier.py, README.md, CHANGELOG.md (+ 새 시험 test_hybrid_v230.py)
- 내용: meritz_laoer v2.3.0 (판 23 하이브리드 — 매수는 스나이퍼, 완성 층은 탑 매도): 모드 선택(trading_mode)·모드 버튼 삭제 · 사기=스나이퍼(눌림·돌파)만 · 층 시드에 닿은 층은 완성 → 탑 매도(평단 +10% → 50%), 미완성(재매수 대기 포함) 층은 스나이퍼 매도(1층 +1.5%·상단 +1.0%·전량), 한 층에 매도 둘이 같은 날 겹치지 않음 · 총 시드·층 수 한도 없음(total_krw 선택·tower_floors 무시) · 새 층 = 가장 낮은 층 평단 − tower_gap_usd(기본 5) 이하일 때 · 탑 매도 체결도 스나이퍼 기준가 갱신 · 환전(아침 = 층 시드 × 하루 매수 층 수 · 장중 자동환전 · 달러부족 알림 · 휴장 전날 rounds · --check 부족 달러 표시 고침) · 텔레그램 메뉴를 스나이퍼 봇 형식(첫 화면 4개 · 레이더 · 잔고 동기화 · 전술 제어반 · 환전, 인라인 버튼)으로 새로 만듦, 시스템 업데이트 버튼 삭제 · 표시 고침(B8). 16:10 동기화·장부=잔고 정지·체결 중복 방지·주문 시간·스나이퍼 신호 숫자·매도 %는 그대로. 수정1 고침 중 B3·B7·S3·S1 은 수정1 원문이 이 판 자료에 없어 미반영(질문란)
- 브랜치: staging 에 올리기 전 (검토 대기)

## v1.2.7 · 2026-11-21 (KST)
- 파일: sniper_mode.py(새 파일), tower_strategy.py, config.py, main.py, tg_menu.py, notifier.py, README.md
- 내용: meritz_laoer v2.2.20 (판 22 듀얼 모드 — 스나이퍼 + 탑쌓기): 설정 trading_mode(tower 기본 | sniper) · 텔레그램 첫 메뉴 모드 버튼 · 스나이퍼 매매(눌림·돌파 재장전 / 층 전량 익절, 익절 % 는 설정 sniper_tp_l1_pct 1.5 · sniper_tp_upper_pct 1.0) · 층·장부 공유 · 스나이퍼 봇 형식 실시간 상황판. 탑쌓기 로직·주문 시간·16:10 동기화·장부=잔고 정지 규칙은 그대로
- 브랜치: staging

## v1.2.6 · 2026-11-20 19:09 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz_laoer v2.2.18 (판 21 거래 내역·봇 상태 버튼 오류 고침): _local 이 4개(pos·halt·avg·tgt)를 돌려주는데 ledger_text·power_text 가 5개로 풀어서 ValueError 가 나던 것을 4개로 고침. 매매 로직·문구 변경 없음. 회귀 시험 3개 통과(서버 실제 상태로 재현·확인), 기존 시험 38개 통과, test_v226 기존 실패 6개와 동일.
- 브랜치: staging

## v1.2.5 · 2026-11-20 19:00 (KST)
- 파일: config.py, main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.17 (판 20 하루 매수·매도 층 수 설정 + 수정1 아침 매도 N_sell): 설정 키 2개(tower_max_buy_layers_per_day·tower_max_sell_layers_per_day, 1~3, 없으면 1) + 텔레그램 버튼 2개, 매수 계획·장중 매도·아침 계획 매도가 그 층 수만큼 사고팔게 함. N=1은 기준 v2.2.15와 5,118 항목 동일.
- 브랜치: staging

## v1.2.4 · 2026-11-20 18:02 (KST)
- 파일: main.py, tower_strategy.py
- 내용: meritz_laoer v2.2.15 (판 19 오늘 계획 미리보기에 탑 진행률): plan_head 한 곳에 탑 줄과 채우는 층 진행률 추가, 표시만 바꿈 (매매·주문·장부 그대로). make_plan이 floors 각 층에 target 키를 실음 (표시 전용)
- 브랜치: staging

## v1.2.3 · 2026-11-20 16:46 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.14 (판 17 시초가 상한): 오늘 채우는 층의 안 산 칸이 시초가를 넘지 않게 상한, 시초가는 09:30 ET 이후 첫 확인가로 그날 한 번만 정해 저장
- 브랜치: staging

## v1.2.2 · 2026-11-20 13:53 (KST)
- 파일: main.py, tg_menu.py
- 내용: audit-fix-v2 r4 + r4-fix: 7번 v2.2.13, 6번 v1.3.4, 1번 v1.0.6
- 브랜치: staging

## v1.2.1 · 2026-11-20 12:26 (KST)
- 파일: main.py, notifier.py, tg_menu.py
- 내용: 7번 이름 변경: 속쓸 적립봇 → SOXL 탑쌓기, 7번 v2.2.11, 사무실 v1.9.6, 브리핑 1.1.1
- 브랜치: staging

## v1.2.0 · 2026-11-20 12:17 (KST)
- 파일: accum_strategy.py, config.py, main.py, notifier.py, tg_menu.py, tower_strategy.py
- 내용: audit-fix-v2 r3: 7번 탑쌓기 전용 (사다리 삭제) + 전 봇 구멍 고침, 7번 v2.2.10, 사무실 v1.9.5 (bot_updater 병합)
- 브랜치: staging

## v1.1.9 · 2026-11-20 06:39 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.8 (하루에 한 층 매수): 안 산 칸 전부 주문
- 브랜치: staging

## v1.1.8 · 2026-11-20 06:18 (KST)
- 파일: config.py, main.py, meritz_api.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.6 (판 16 본격): 층별 매도·반칸 표시·체결 알림
- 브랜치: staging

## v1.1.7 · 2026-11-20 05:31 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.5: 1층 채우기 매수 (판 16 일부)
- 브랜치: staging

## v1.1.6 · 2026-11-19 21:53 (KST)
- 파일: config.py, main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.4: 1층 시작가 설정 메뉴
- 브랜치: staging

## v1.1.5 · 2026-11-19 21:37 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.3: 층 칸 색상 + 다음 회차 가격별 배정
- 브랜치: staging

## v1.1.4 · 2026-11-19 21:23 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.2: tower layer visualization (pan 14) - tower_lines in status board, view_lines in tower_strategy, filled layers only
- 브랜치: staging

## v1.1.3 · 2026-11-19 20:54 (KST)
- 파일: accum_strategy.py, config.py, main.py
- 내용: fix(audit): 1번 보유 조회 실패 구분·타임아웃 중복 방지, 6번 v1.3.2, 7번 v2.2.1
- 브랜치: staging

## v1.1.2 · 2026-11-19 20:42 (KST)
- 파일: main.py, tg_menu.py, tower_strategy.py
- 내용: meritz_laoer v2.2.0: tower stacking (pan 13) - new tower_strategy.py module, strategy switch (default ladder), migration from holdings, slippage handling
- 브랜치: staging

## v1.1.1 · 2026-11-19 17:08 (KST)
- 파일: main.py
- 내용: meritz_laoer v2.1.0: merge pan 12 intraday sell gate fix onto menu 3rd v3
- 브랜치: staging

## v1.1.0 · 2026-11-19 16:49 (KST)
- 파일: main.py, notifier.py, tg_menu.py
- 내용: 텔레그램 매매봇 메뉴 정리 3차 v3: 7번 v2.0.9 기준 재적용 + 6번 문구 정리
- 브랜치: staging

## v1.0.9 · 2026-11-19 14:44 (KST)
- 파일: main.py, meritz_api.py, tg_menu.py
- 내용: meritz_laoer v2.0.9: usd_cash reads estm_frcr_amt (pan 11, Q27 fix)
- 브랜치: staging

## v1.0.8 · 2026-11-19 14:24 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz_laoer v2.0.8: auto FX in realtime window, shortage alert, holiday pre-FX, --diag-cash (pan 10)
- 브랜치: staging

## v1.0.7 · 2026-11-19 13:43 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz_laoer v2.0.7: auto FX at 09:00 KST, one round per day (pan 9)
- 브랜치: staging

## v1.0.6 · 2026-11-18 18:01 (KST)
- 파일: config.py, main.py, tg_menu.py
- 내용: meritz_laoer v2.0.1: 텔레그램 메뉴 정리 (메인 4개 카테고리, 전술 설정, 상황판 설정값 표시)
- 브랜치: staging

## v1.0.5 · 2026-11-18 16:53 (KST)
- 파일: accum_strategy.py, config.py, main.py, meritz_api.py, notifier.py, tg_menu.py
- 내용: meritz: SOXL 적립봇 v2.0.0 — 사다리·부분매도·재매수·자동환전 (방 meritz-soxl-dca-bot)
- 브랜치: staging

## v1.0.4 · 2026-11-14 13:57 (KST)
- 파일: main.py, notifier.py, tg_menu.py
- 내용: bot-names-renumber: 새 1~9번 목록으로 봇 이름·번호 정리 (vNEXT)
- 브랜치: staging

## v1.0.3 · 2026-11-14 10:25 (KST)
- 파일: main.py, tg_menu.py
- 내용: meritz split: 4번 주식만·SGOV 비서봇·무매봇 메뉴 (dca v1.2.6, laoer v1.0.3, office vNEXT)
- 브랜치: staging

## v1.0.2 · 2026-11-08 10:11 (KST)
- 파일: config.py, main.py
- 내용: 메리츠 무매 평단 조절 추가 meritz_laoer v1.0.2
- 브랜치: staging

# meritz_laoer.service 변경 기록

## v1.0.1 · 2026-11-08 03:52 (KST)
- 파일: config.py, global_throttle.py, main.py, meritz_api.py, notifier.py, strategy_v14.py
- 내용: meritz settings.example.json 제거 (구버전 업데이터가 .json을 거부해 묶음 적용이 막힘 — 서버 설정은 이미 /etc/meritz-laoer/settings.json으로 설치됨)
- 브랜치: staging

