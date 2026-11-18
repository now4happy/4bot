# 메리츠 속쓸 적립봇 (meritz_laoer · 서비스 meritz_laoer.service) — v2.0.0 초안

메리츠 3번 계좌(Super365)에서 **SOXL 분할매수·부분매도**를 하는 봇. 기존 무한매수(V14) 봇 `meritz_laoer`를 고쳐 만들었다
(계좌 키 지문·텔레그램·장부·정지 장치·텔레그램 메뉴 재사용). 버전 번호·표시 이름은 Muse 가 정한다. `strategy_v14.py` 는 이제 안 불리지만 지우지 않았다.

## 규칙 (노션 작업 페이지 2026-11-18)
- 매수 사다리: **$50 부터 $5 내려갈 때마다 1회차**, 매수가 $50·45·…·5 (10회). 회차 금액 = 총 투자금(원) ÷ 10 ÷ 메리츠 적용환율(매수), 정수 주 내림.
- 매도: 평단 대비 **+10%** 에 보유 **50%** (정수 주 내림, 0주면 안 팖). 부분 매도라 평단은 그대로.
- 매도 뒤 = **재매수 모드**: 매도 시점 평단 − $5 × n 에서 1/10 씩 다시 매수 (기존 $50~$5 사다리는 안 씀).
- 한도: 보유 원가(달러) ≤ 총 투자금 ÷ 적용환율. 기존 보유분도 포함. 계좌 USD 예수금이 모자라면 그 회차 생략. 이 봇엔 환전 기능이 없다.
- **1회차 차감**: 기존 보유(토스에서 옮겨 온 SOXL 등)의 원가를 **첫 사다리 매수 한 번만** 회차 금액에서 뺀다 (`start.first_round_credit_usd` 또는 `--add-shares … --credit`). 체결되면 소멸.
- **필요 달러**: 오늘 매수 주문이 다 체결될 때 드는 달러(= 주문 수량×가격 합계). 예수금과 비교한 **부족 달러**와 함께 계획·`--check`·텔레그램 💰 자금에 표시.
- **자동환전** (`auto_fx_enabled`, 기본 꺼짐): 켜면 부족 달러 + `auto_fx_buffer_pct`% (올림, 정수 달러)를 `auto_fx_max_usd_per_day` 안에서 원→달러 환전 신청한 뒤, **환전 후 실제 예수금**으로 계획을 다시 짜서 주문한다(모자라면 매수가 줄거나 빠짐).
  실주문 모드에서만·하루 한 번(신청 전 `data/fx_<날짜>.json` 기록, 실패·불확실해도 그날 재신청 안 함)·원화 예수금이 모자라면 안 함. 모의(dry_run)·`--check`·메뉴는 계산만, 환전 신청 없음. 환전 API 호출 형식은 meritz_dca_bot 과 같고 서버 수용 여부는 **실환전 전까지 미확인**(실환전으로 시험하지 않음).
- 매일 미 동부 `order_time_et`~`order_deadline_et` 사이 한 번: 다음 사다리 레벨 매수 주문(최대 `max_rounds_per_day`개) + 평단 +10% 매도 주문을 같은 방식(LOC 또는 LIMIT)으로 낸다. 체결은 `sync_time_et` 뒤 주문번호로 읽어 장부(`data/position.json`)와 적립 상태(`data/accum_state.json`)에 반영.

## 노션에서 아직 안 정해진 값 = 설정 필수 (비어 있으면 실주문 차단, `--check` 가 이유를 출력)
| 설정 | 값 | 노션 질문 |
|---|---|---|
| `first_buy_mode` | `now` / `wait_top` | Q1 |
| `unit_base` | `total` / `cash` | Q2 |
| `start.mode`, `start.filled_levels`, `start.qty`, `start.principal_usd` | 기존 보유를 사다리에 어떻게 칠지 | Q3 |
| `max_rounds_per_day` | 1 이상 정수 | Q4 |
| `order_type` | `LOC` / `LIMIT` | Q5 |
| `allow_consecutive_sell` | `true` / `false` | Q6 |
| `total_krw`, `split_count` | 금액·10 | 기본값 없음 |
| `auto_fx_enabled`(기본 false) · 켜면 `auto_fx_buffer_pct`·`auto_fx_max_usd_per_day` 필수 | 자동환전 | Q11 |

설정 예시 (**가상 값 — 실제 값은 Muse 가 채우고 GitHub 에 올리지 않음**, `.json` 파일로 저장소에 두지 않음):
```
"total_krw": <총 투자금 원>, "split_count": 10,
"first_buy_mode": "<now|wait_top>", "unit_base": "<total|cash>", "max_rounds_per_day": <정수>,
"order_type": "<LOC|LIMIT>", "allow_consecutive_sell": <true|false>,
"start": {"qty": <정수>, "principal_usd": <원금>, "mode": "ladder", "filled_levels": [], "first_round_credit_usd": <1회차 차감액 또는 null>}
```
그대로인 안전 조건: enabled·dry_run·transfer_confirmed·toss_sniper_stopped_confirmed·키 지문·P/VR6 키·다른 봇 토큰 금지·장부=잔고·정지 표시·하루 1회 표시 파일.

## 명령
`--fingerprint` · `--check`(주문 없이 점검·오늘 계획) · `--inject-start`(장부+적립 상태 시작) · `--clear-halt` ·
`--add-shares --qty N --avg X [--credit]`(직접 산·입고된 N주를 평단 X 로 장부에 더함. `--credit` = 원가 N×X 를 1회차 때 차감. enabled=false·주문 시간 밖·잔고 = 장부+N 일 때만) · 인자 없음 = 상시 실행.
텔레그램 ➕ 직접 산 주식 반영: `63 61.50 차감` 처럼 끝에 '차감'.

## 켜는 순서 (Muse·사용자)
1. 서버 `/etc/meritz-laoer/settings.json` 에 위 값을 채운다 (권한 600). 7번 무매(V14)의 미체결·진행 사이클이 없는지 먼저 확인 (노션 Q8).
2. `python3 main.py --check` → 3. 입고 확인 뒤 `transfer_confirmed=true` → `--inject-start` → 4. `enabled=true`(dry_run=true) 모의 → 승인 뒤 `dry_run=false`.
