# 2026-11-04 Claude — 팬딩 자동주문 시간 선택 + 토글 버튼 동작 표시 (⚡ 켜기 / 💤 끄기)

## 기준 main
- now4happy/4bot main fd4f04c2eccbf978c03f8619ddb0a17420688303 (사무실 버전 기록 v1.2.3), STATUS 2026-11-04 16:25 KST · 대기 업로드 없음
- bot_office/fanding_trade.py 1.13.0 SHA-256 앞 16자 74e6f9f6bd29db20 → **1.14.0 5bc1ddcabbdb6ed3**
- bot_office/fanding_vr6.py 2.5.0 SHA-256 앞 16자 07402966bfd7748b → **2.6.0 b7bf703db0b68861**
- 사무실 버전은 머리말에 vNEXT (업데이터가 승인 시 채움). 바꾼 파일은 이 2개뿐 (office_briefing.py·PC 수집기·1·2번 봇 안 건드림).

## 바뀐 것
### 메뉴 토글 버튼 3종 = 동작 표시 (P·VR6 같은 글자)
| 기능 | 꺼져 있을 때 | 켜져 있을 때 |
|---|---|---|
| 자동주문 | ⚡ 자동 켜기 | 💤 자동 끄기 |
| 자동환전 | ⚡ 자동환전 켜기 | 💤 자동환전 끄기 |
| 역자동환전 | ⚡ 역자동환전 켜기 | 💤 역자동환전 끄기 |
- 이모티콘은 사용자 선택(⚡/💤, 2026-11-04 채팅). 지시서 원안 🟡/⚫ 대신.
- route_shared: 새 글자 → 켜기/끄기 명령(/자동켜기·/자동끄기·/자동환전켜기… / VR6 는 /vr6…). 메뉴 모드를 모르면 아무것도 안 바꿈.
- 옛 글자(🤖 자동 켜짐/꺼짐, 💱 자동환전·역자동환전 켜짐/꺼짐, 🤖 VR6 자동 켜짐/꺼짐)는 메뉴에 안 보이고 별칭으로만 동작. 자동주문 옛 글자는 새 흐름(켜져 있으면 끄기, 꺼져 있으면 시간 선택).
- 상단 상태 줄·확인 메시지의 켜짐/꺼짐 표현 그대로. 안내 문구의 버튼 이름만 새 이름으로.

### 자동주문 켜기 = 시간 선택 (P·VR6 각각)
- ⚡ 자동 켜기 · /자동켜기 · /vr6자동켜기 · /자동 화면의 켜기 버튼 → 바로 켜지 않고 "P 자동주문 켜기 — 시간을 골라줘" / "VR6 자동주문 켜기 — 시간을 골라줘".
- 버튼: [판독후 1시간뒤 (HH:MM)] [마감 1시간전 (HH:MM)] [❌ 취소] (인라인 fm:am:A/B/x · vm:am:A/B/x). 취소 → 켜지 않고 메뉴로.
- 고르면 켜짐 + 모드 저장 (P: fanding.json auto_mode·auto_mode_at, VR6: vr6.json). 확인: "P 자동주문 켜짐 — 판독후 1시간뒤 (10:00)에 자동주문해요 (점검 통과 시)." / VR6 마감 모드는 "(21:30, 첫 발주일 마감 기준)".
- 💤 자동 끄기 · /자동끄기 · /vr6자동끄기 → 바로 꺼짐 + 모드 지움 ("주문하지 않아요.").

### 자동 실행 시각
- 모드 A 판독후 1시간뒤 = 표 알림일 09:00 KST + 1시간 (P: sheet_notice_time, VR6: 받은 날 notice_kst).
- 모드 B 마감 1시간전 = 예약 마감 − 1시간 (P: deadlines() cutoff, VR6: 첫 발주일 cutoff_kst).
- 소급 금지: 모드 시각이 지난 뒤에 켰거나 표 알림이 그 시각 뒤에 나갔으면 자동주문 안 함 → auto_late 표시 + 수동 결정 안내 1번(주문 버튼 포함). VR6 는 판단용으로 notice_sent_at 을 새로 기록.
- 모드 없는 기존 ON(legacy): 마감 10분 전 그대로, 강제 전환 안 함.
- 가격표/주문표 글의 자동 시간 줄과 마감 30분 전 알림의 시각은 모드 시각으로. 꺼짐·legacy 문구는 그대로.
- 점검·승인·접수, 배수·종목·금액, 자동환전·역자동환전 조건·금액·우대 시간은 그대로 (AST 비교로 확인).

## 검증 (모의, 실주문·실환전 없음)
- py_compile 두 파일 통과. 두 diff 를 main fd4f04c 새 클론에 git apply --check/apply → 재구성 파일 SHA-256 이 위 해시와 일치.
- 새 검사 62/62 통과: 메뉴 라벨 6종 × P·VR6, 상태 줄 그대로, 새 글자 라우팅(P/VR6/모름), 옛 글자 별칭, 시간 선택·취소·A·B·끄기, /자동 화면 켜기 버튼, P 시각 10:00/21:30/legacy 22:20/서머타임 20:30, 소급 금지(늦은 알림·늦게 켬, A·B), tick 통합(P·VR6 자동 승인·대기·legacy·마감 지남), 가격표·주문표 글 시각 표시, 자동환전·역자동환전 버튼 바로 켜짐↔꺼짐·P/VR6 분리.
- 이전 환전 검사 139/139 통과 (메뉴 글자 기대값 4개만 새 라벨로 바꿈).
- 비밀값·계좌번호 없음(grep). 바뀐 함수: (P) sheet_text·tick·toggle_auto·menu_keyboard·auto_fx_label·auto_rfx_label·bot_message·bot_callback·TOGGLE_LABELS / (VR6) plan_text·tick·send_plan_notice·keyboard·handle_text·callback. run_checks·submit·deadlines·DEFAULTS·환전 함수 변경 없음.

## 남은 일 · 다음 AI
- Muse 검토 → staging 업로드 → 6. Update 승인 뒤 서버 적용. 적용 후 기존에 켜져 있던 자동주문은 legacy(마감 10분 전)로 동작하므로, 새 시각을 쓰려면 사용자가 한 번 껐다 켜야 함.
- 읽을 파일: bot_office/fanding_trade.py (auto_mode·auto_mode_time·auto_due·p_auto_picker·set_p_auto), bot_office/fanding_vr6.py (같은 이름 + vr6_auto_picker·set_vr6_auto).
