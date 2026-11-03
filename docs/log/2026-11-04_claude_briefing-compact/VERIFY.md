# VERIFY — 비서 브리핑 간결화 (office_briefing.py vNEXT) · 2026-11-04 · Claude

## 상태
파일 작성·가짜 환경 검증 완료 / staging 업로드·승인·서버 적용·실제 텔레그램 확인 **미실행** (Muse·사용자 담당)

## 바뀐 파일 (저장소 상대경로)
| 파일 | 기준 | sha256 |
|---|---|---|
| `bot_office/office_briefing.py` | main `3efb8ca` (사무실 v1.1.7 · 파일 v1.1.5 내용 1,500줄, sha256 `a6a8bf9e…eb478d`) | `65d37d10a3157e9bcb1b1baf390ca9d7a37deff06c81b958d655f02ab0a7a63e` (1,681줄) |

올릴 위치 제안: 위 파일은 staging `bot_office/`, 이 문서와 `verify_briefing.py`는 `docs/log/2026-11-04_claude_briefing-compact/`.
고치지 않음: toss_sniper/ 전부, US_CLOSED 표, fanding_trade.py, 현황판 파일(sniper_picture·board 등).

## 바뀐 부분만
- 머리말 변경 기록에 `사무실 vNEXT` 항목 추가.
- `build()`: 통합 잔액 블록 삭제 → `💰 필요 금액` 표(`section_need`) + 봇 한 줄·이상 봇(그대로) + `📝 전달 노트`.
- `section_need()`·`need_table()` 새로 추가: 고정폭 `<pre>` 표. 머리말 `계좌 보유 필요` 맨 위 1번, 계좌 이름 1번 + 그 아래 묶음 줄(토스 USD·KRW / 메리츠 P·VR6 / 한투 KRW / 빗썸 KRW), 숫자+아이콘만, 범례 `🚨 충전 필요 · 😌 충분 · KRW 단위 원` 1번.
  - 토스 USD 필요 = `section_dollar_check` 의 `total` 그대로 · 토스 KRW 필요 = 3번 국내 적립 `K["need"]` 그대로.
  - 메리츠 보유 = 추정 달러(estm_frcr_amt)만, '예수금' 단어 없음 · 필요 `-` + 노트 "계산식 없음".
  - 한투 원화 조회 실패 → 보유 `0` (+노트), 필요 `-`. 빗썸 필요 `-`.
- `section_dollar_check(now, info=None)`: 계산·문구는 그대로. 기존 줄을 `_keep()`로 분류(경고·상태·노트)해 `info` 로 넘기기만 함.
- `meritz_lines()` → `meritz_fetch()`(조회) + `meritz_lines()`(표시) 분리. 💰 잔액 메뉴 출력은 main 과 같음.
- `message_chunks()`: `<pre>…</pre>` 를 한 덩어리로 다룸. 3500자 넘는 블록은 줄 단위로 나눠 조각마다 다시 `<pre>`로 감쌈.
- `scheduled_run()`: 평일 휴장일만 `📅 휴장 · 날짜` + `🇰🇷 한국장 휴장`/`🇺🇸 미국장 휴장`. 진행 중·예정·안내 문구 삭제. 별도 알림도 휴장일에만. 양 시장 휴장 시 일반 브리핑 생략은 그대로. 조회 실패(kr/us None)는 휴장이라 하지 않고 전달 노트에 적음.
- 표 아래 경고 줄(수혈·예비수혈·골든포켓·2번 상태)은 기존 문구 그대로, `<`·`>` 만 이스케이프. main 의 수혈 줄에 있던 날것 `<`는 HTML 모드에서 전송 오류가 날 수 있던 부분.
- 표 아래에서 빠진 줄(형식만): 2번 본·서브 상세, '지금 보유 달러로는 N주만', 부족액 문장, 2번 당일 추가 매수 상한. 계산은 남아 있고 필요하면 다시 보이게 할 수 있음.

## 시안과 다르게 한 것 (사용자 승인: 1번 "정렬 우선", 2026-11-04 02:07)
시안 v4 HTML은 대화에 첨부되지 않아 지시문 규칙대로 만들었다.
실제 글꼴로 재 보니 한글 폭이 정확히 2칸이 아니었다(Noto Sans Mono CJK 1.84칸, 폰 ≈1.5칸). 그래서 아래 3가지를 시안과 다르게 했다.
- 계좌 이름을 '가운데'가 아니라 묶음 위 한 줄로 씀.
- 달러/원화 대신 USD/KRW로 쓰고, 원화 칸의 '원'은 빼서 범례로 옮김.
- `–` 대신 `-` 를 씀.
→ 숫자 줄은 왼쪽부터 ASCII 만 있어서 어느 글꼴에서도 열이 맞는다. 머리말 한 줄만 폰에서 최대 2칸 어긋날 수 있다(1.75칸 기준으로 가운데 맞춤).

## 검증 — `python3 -I verify_briefing.py <main 원본> <vNEXT> [출력폴더]` → 89/89 통과
- py_compile 통과(두 파일).
- 계산 불변: 3개 시나리오(부족·충분·조회실패)에서 `section_dollar_check` 출력이 main 과 글자 단위로 동일. 💰 잔액 메뉴(`--balances all|meritz|toss|kis|bithumb`)도 동일.
- 의도 밖 변경 없음(AST 비교): 바뀐 함수는 build·meritz_lines·message_chunks·scheduled_run·section_dollar_check 5개. 새 함수 9개, 없어진 함수 0개. 최상위 변경은 독스트링과 상수 2개(ICON·DASH).
- 고정폭: 한글 1.5/1.67/1.84/2.0칸 네 경우 모두 숫자 줄의 보유·필요 열 끝이 일치. 실제 글꼴(Noto Sans Mono CJK KR, DejaVu Sans Mono) 픽셀 측정에서도 일치. 표 줄은 32칸 이하.
- 분할: 모든 조각 3500(UTF-16) 이하, `<pre>` 짝 맞음, 표는 한 조각 안. 3500 넘는 `<pre>`는 나뉘어도 각각 닫힘.
- 일정: 평일 개장(일정 줄 없음) · 미국 휴장 11-26 · 한국 휴장 · 한국 조회 실패(노트) · 양 시장 휴장 12-25(일반 브리핑 생략).
- 안전: 모든 http() 차단 후 호출 0건, 가짜 비밀값 출력 0건, diff 안 비밀·계좌 원문 0건. 실주문·환전·실제 텔레그램 전송 없음.

## 남은 일
1. 시안 v4 HTML과 눈으로 비교 (필요하면 문구만 조정).
2. staging 업로드 → 6. Update ✅ 승인. 이후 `bot-office-secretary` 재시작 여부는 06_updater 기준으로 확인.
3. 실제 폰 텔레그램에서 `--print` 미리보기 또는 다음 정기 브리핑 1회 화면 확인 — 폰 글꼴 정렬은 여기서 직접 볼 수 없었음.
4. 머리말 버전은 `vNEXT` — 승인 뒤 업데이트 비서가 매긴 사무실 번호로 바꿀 것.

## 다음 AI가 읽을 파일
START.md → STATUS.md → docs/handoff/05_office.md → 이 문서 → bot_office/office_briefing.py 의 `section_need`·`need_table`·`scheduled_run`
