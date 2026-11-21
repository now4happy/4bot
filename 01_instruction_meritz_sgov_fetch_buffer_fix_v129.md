# 지시문: 메리츠 적립 v1.2.9 — SGOV 환율 재시도 창 캐시 폴백 + 시장가 주문 10% 여유 + 오래된 FRED 자료로 캐시 덮지 않기

**방: 3. 미국주식 적립 (room3-meritz-accum)**
**버전: v1.2.8 → v1.2.9**

---

## §1. 읽기 전 확인 게이트 (코드 건드리기 전에 반드시 먼저 한다)

- 지시문을 요약·의역·번역하지 말고, 아래 §이식 항목을 원문 그대로 나열할 것. 나열한 내용이 지시문과 다르면 멈추고, 제출물의 'Muse에게 묻는 질문' 항목에 적을 것. 유저에게 채팅으로 직접 묻지 않는다.
- MANIFEST의 파일 목록·개수·sha256을 먼저 대조하고, 맞는 것을 보여줄 것. 개수가 안 맞으면 멈추고, 제출물의 'Muse에게 묻는 질문' 항목에 적을 것.
- **기준 확인 방법:** 기준 파일 5개의 sha256은 Muse가 2026-11-17 KST에 서버(실행 중인 meritz_dca_bot)에서 직접 가져와 확인했다. 서버의 `BOT_VERSION`은 `"v1.2.8"`이다. 다른 AI는 원격 저장소·서버에 접속하지 않으므로, 원격 대조를 다시 하지 않는다. 대신 ZIP 안의 5개 기준 파일이 MANIFEST에 적힌 sha256과 일치하는지 (ZIP 내부 일치성)를 확인하면 게이트를 통과한다. ZIP 내부 해시가 MANIFEST와 다르면 멈추고, 제출물의 'Muse에게 묻는 질문' 항목에 적을 것.
- 이식 대상이 import하는 파일이 ZIP에 없으면, 수정 대상이 아니어도 참조용으로 ZIP에 포함할 것. 없으면 멈추고, 제출물의 'Muse에게 묻는 질문' 항목에 적을 것. 이 ZIP에는 의존성 닫힘(closure)이 전부 들어 있다: `sgov.py`→`t_core.py`·`bridge.py`, `t_core.py`→`replay_log.py`·`dca_engine.py`, `bridge.py`·`replay_log.py`·`dca_engine.py`는 표준 라이브러리만 쓴다. `main.py`·`meritz_api.py`·`t_ui.py`는 이 고침의 대상이 아니고 `sgov.py`가 import하지 않으므로 ZIP에 없다. 고침이 그 파일들을 건드려야 한다고 판단되면, 코드를 고치지 말고 제출물의 'Muse에게 묻는 질문' 항목에 적을 것.
- 위 두 가지가 끝나야 이식을 시작한다.

## §2. 중간에 멈추지 않기

- 파일 확인이 끝나면 바로 이식을 시작할 것. "파일 확인됨·이식 미완료"로 끝내지 말 것.
- 검증 항목을 전부 직접 실행한 뒤에야 제출할 것. 검증하지 않고 제출하지 말 것.
- 숫자를 지어내지 말고, 근거 파일에 없으면 공개 출처에서 찾아 인용하거나 미확인으로 표시하고 근거 파일의 사실만으로 제안하라.
- 막히면 멈추고, 제출물의 'Muse에게 묻는 질문' 항목에 구체적인 사유를 적을 것. 추측해서 진행하지 말 것. 유저에게 채팅으로 직접 묻지 않는다.

## §3. 제출 형식

- 바뀐 파일만 번호 매겨(1, 2, 3…) ZIP 1개로. ZIP 안에 VERIFY.md(맨 위에 "방: 3. 미국주식 적립", 해시·검증 결과·주의점) + 검증 스크립트 포함.
- 채팅 메시지는 3줄만: 첫 줄 맨 앞에 "방: 3. 미국주식 적립"을 붙이고 최종 목록 한 줄, 바뀐 것 한 줄, 검증 통과/실패 한 줄.
- 제출 ZIP 파일명: `meritz_sgov_fetch_buffer_fix_v129_room3-meritz-accum.zip` 형식 (작업_버전_방슬러그).
- GitHub push·main 직접 push·서버 적용·재시작·실주문 금지.

---

## 근거 (사실만 — 2026-11-16 미국장, 서버 실측)

2026-11-16 미국장에서 SGOV 1회차가 두 번 막혔다. 첫 번째는 환율 자료, 두 번째는 주문가능금액이다. 아래는 서버 로그·감사(audit) 기록·직접 조회로 확인한 사실이다.

### 근거 1: SGOV 1회차 건너뜀 — FRED 타임아웃 + 재시도 창이 캐시를 버림

- 로그 2026-11-17 00:05:23 KST (2026-11-16 10:05 EST): `sgov_tranche` skipped, reason `gate_a:fetch_failed_recently`, streak 2, audit_ref `a9dc88988`.
- 그날 서버에서 `sgov_fx_history`가 하루 종일 실패했다. `ReadTimeout: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=15)`가 2026-11-16 08:21 UTC부터 약 30분 간격으로 반복됐고, 판단 직전 마지막 실패는 15:04:58 UTC, 판단은 15:05:23 UTC (25초 뒤)였다.
- `sgov.py` `get_history()` 169–170행이 원인이다. 실패 뒤 30분(HIST_RETRY_SEC) 안에는 새로 받지 않고 `None, "fetch_failed_recently"`를 돌려준다. 이 분기에는 캐시 폴백이 없다. v1.2.5에서 넣은 캐시 폴백(`cache_stale`)은 직접 받기가 실패한 `except` 블록에만 있다. 그래서 판단 직전 25초 전에 실패한 기록이 있으면, 캐시에 쓸 만한 자료가 있어도 판단은 자료 없음을 받는다.
- 캐시(`/var/lib/meritz-dca/fx_usdkrw_history.json`)에는 자료가 있었다: fetched_kst 2026-11-13, closes 780행, 마지막 행 2026-11-13 종가 1334.08, source Yahoo (FRED DEXKOUS unreachable 2026-11-13, Yahoo substitute).
- 캐시 기준으로 관문은 둘 다 통과한다. 판단 감사 기록(audit_ref `a346ad743`, 수동 재실행 때 기록): 적용환율 1336.95 < 36개월 평균 1402.2292 (n=776) → (a) 통과, 7일 변동 -1.6412% (history, 2026-11-06→2026-11-13) → (b) 통과. 즉 건너뜀은 시장 신호가 아니라 자료 받기 경로의 문제였다.

### 근거 2: 45주 주문 거절 — 메리츠 시장가 주문은 약 10% 여유를 따진다

- 수동 재실행 뒤 봇이 45주 시장가 매수를 시도했으나 거절됐다. 감사 기록(audit_ref `a14a72b66`, chain `ord-r852a679d`, client_order_id `sg_2026-11-16_1`): `API 5988 주문가능금액이 부족합니다.`
- 44주 시도도 같은 5988로 거절됐다. 42주는 접수됐다 (broker order no. `537562`, audit_ref `a9fd36328`). 체결은 42주 @ $100.5764, 원금 $4,224.21 (ledger_fill audit_ref `a9129bd6a`). 메리츠 잔고 확인: SGOV 42주, 매도가능 42주, 평단 $100.5764.
- 당시 숫자 (서버 직접 조회, 2026-11-16 14:31–14:38 EST): USD 예수금 $4,660.68 (frcr_amt, 추정예수금 estm_frcr_amt와 동일), SGOV 현재가 $100.5750. 봇의 계획: 45주 = $4,525.76, 1% 여유 포함 필요액 $4,571.02 (현금보다 적어 봇 자체 검사는 통과했다). 44주 = $4,425.30, 42주 = $4,224.15.
- 거절·접수 경계로 메리츠가 따지는 여유를 좁힐 수 있다. 44주 실패 → 주당 필요액 > $4,660.68 / 44 = $105.92 (가격 대비 5.32% 초과). 42주 성공 → 주당 필요액 ≤ $4,660.68 / 42 = $110.97 (가격 대비 10.34% 이하). 즉 메리츠 시장가 주문의 여유는 5.3% 초과·10.3% 이하 범위에 있다. **10%로 두면 두 관측과 일치한다** (44주: 44 × 100.575 × 1.10 = $4,867.73 > 현금이라 거절, 42주: 42 × 100.575 × 1.10 = $4,646.47 ≤ 현금이라 접수). 10%는 확정값이 아니라 관측 범위 안의 안전 쪽 값이다. 이 지시문은 10%를 쓴다. 10%가 틀렸다고 판단되면 코드를 고치지 말고 'Muse에게 묻는 질문'에 근거와 함께 적을 것.
- 봇의 달러 검사(`get_buying_power` → `usd_cash_or_zero` → frcr_amt, 예수금 기준)와 주문 필요액(1% 여유)은 메리츠의 시장가 주문 검사와 맞지 않는다. 그래서 봇 검사는 통과하고 메리츠에서 거절되는 일이 생긴다.

### 근거 3: 새로 받은 FRED 자료가 기존 캐시보다 오래됐다

- 서버에서 2026-11-17 04:xx KST에 FRED를 curl로 직접 받으면 HTTP 200, 217KB, 2.0초로 된다. 그런데 CSV 마지막 종가는 2026-11-06 1361.89이다. 캐시 마지막 종가(2026-11-13)보다 7일 오래됐다. 미국 셧다운으로 Fed 자료가 늦어진 것으로 추정되나, 이 지시문에서는 미확인으로 둔다.
- Yahoo 대체원은 같은 시각 429 Too Many Requests를 돌려준다.
- 지금 `get_history()`의 성공 경로는 새로 받은 자료를 무조건 캐시에 덮어쓴다. FRED가 11-06 자료를 돌려주는 상태에서 덮어쓰면 캐시가 11-13에서 11-06으로 뒷걸음질한다. 그러면 `weekly_jump`의 history 폴백이 `no_reference`가 되고 (마지막 종가가 오늘보다 10일 넘게 오래됨), `avg_months`도 14일이 지나면 `history_stale`이 된다. 다음 회차(2026-11-30) 판단이 또 막힐 수 있다.

### 참고: Muse가 이미 손으로 조치한 것 (이 고침이 코드로 옮길 대상 — 서버 상태 파일을 다시 건드리지 말 것)

- FX 캐시 `fetched_kst`를 2026-11-17로 찍었다 (closes 780행 그대로 유지). FRED를 새로 받지 않고 당일 캐시를 쓰게 한 것이다.
- SGOV 회차 날짜를 되돌렸다 (`last_exec_date` 2026-11-16 → 2026-11-15, `next_due_date` 2026-11-30 → 2026-11-16). 봇이 다음 스케줄러 틱에서 다시 판단하게 한 것이다.
- 45주 거절 뒤 42주 시장가 매수를 봇의 `_order` 경로로 직접 냈고, 체결이 봇 장부에 자동 반영됐다 (42주, 원금 $4,224.21). 회차 진행도 봇의 `apply_buy`와 같은 값으로 맞췄다: tranches_done 1, wait_usd $375.79 (= 회차금 $4,600.00 − 체결금 $4,224.21), skip_streak 0, next_due_date 2026-11-30, last_decision buy (rate 1336.95 / avg 1402.2292 / jump -1.6412 / basis history).
- 이 지시문의 고침 3개는 위 손조치를 코드로 옮겨 다음 회차부터는 손 안 대고 돌아가게 하는 것이다. 서버의 설정·장부·캐시 파일을 이 작업에서 직접 바꾸지 않는다.

---

## §이식 항목 1: 재시도 창에서도 캐시가 있으면 그걸로 판단 (sgov.py)

파일: `meritz_dca_bot/sgov.py`, `get_history(today_kst)` (현재 163–187행).

바꾸기 전 (30분 창 안에는 캐시가 있어도 None):

```python
    if _HIST["fail_day"] == today_kst and time.time() - _HIST["fail_ts"] < HIST_RETRY_SEC:
        return None, "fetch_failed_recently"
```

바꾼 뒤 (30분 안 다시 받지 않는 것은 유지하되, 캐시가 있으면 그걸로 판단한다):

```python
    if _HIST["fail_day"] == today_kst and time.time() - _HIST["fail_ts"] < HIST_RETRY_SEC:
        # v1.2.9: 30분 안 다시 받지 않는 것은 유지하되, 캐시가 있으면 그걸로 판단한다.
        # 2026-11-16에 이 분기가 None을 돌려줘 관문 (a)(b)가 둘 다 실패해 건너뛴 것이 원인이다.
        # v1.2.5의 except 블록과 같은 cache_stale 이유를 쓴다.
        if c.get("closes"):
            return [tuple(x) for x in c["closes"]], "cache_stale"
        return None, "fetch_failed_recently"
```

- 바꾸는 곳은 이 분기뿐이다. `HIST_RETRY_SEC`(1800초) 값, `except` 블록의 기존 `cache_stale` 폴백, 게이트 판정 로직은 건드리지 않는다.
- 캐시가 없을 때만 그대로 `(None, "fetch_failed_recently")`를 돌려준다.

## §이식 항목 2: 시장가 주문 수량에 메리츠 여유 10%를 반영 (sgov.py)

파일: `meritz_dca_bot/sgov.py`, `buy_plan()` (현재 305–311행) 및 `sgov_step()`의 수량 0 처리 (현재 419–424행).

바꾸기 전:

```python
def buy_plan(sg: dict, price: float, buffer_pct: float) -> dict:
    """정수 주 수량 + 1% 여유 포함 필요 달러 (적립 매수와 같은 계산). 남은 돈은 SGOV 대기 달러로 넘김"""
    budget = round(tranche_amount(sg) + max(0.0, _f(sg.get("wait_usd"))), 4)
    q = int(budget // price) if price > 0 else 0
    need = round(q * price * (1 + float(buffer_pct) / 100.0), 2)
    return {"budget": budget, "qty": q, "need": need, "left": round(budget - q * price, 4)}
```

바꾼 뒤 (수량과 필요액을 메리츠 시장가 주문 검사 기준에 맞춘다):

```python
ORDER_BUFFER_PCT = 10.0   # 시장가 주문 때 메리츠가 따지는 여유 (근거 2: 관측 범위 5.3% 초과·10.3% 이하 — 10%로 잡으면 안전 쪽)
```

```python
def buy_plan(sg: dict, price: float, buffer_pct: float) -> dict:
    """정수 주 수량 + 시장가 주문 여유 포함 필요 달러. 남은 돈은 SGOV 대기 달러로 넘김.
    메리츠 시장가 매수는 주문가능금액을 수량×가격×(1+약 10%)로 따져서, 1% 여유만으로는 주문이 거절된다 (2026-11-16 실측: 45주·44주 거절, 42주 접수)."""
    budget = round(tranche_amount(sg) + max(0.0, _f(sg.get("wait_usd"))), 4)
    q = int(budget // (price * (1 + ORDER_BUFFER_PCT / 100.0))) if price > 0 else 0
    need = round(q * price * (1 + ORDER_BUFFER_PCT / 100.0), 2)
    return {"budget": budget, "qty": q, "need": need, "left": round(budget - q * price, 4)}
```

- `buffer_pct` 매개변수는 서명 호환을 위해 그대로 둔다 (`sgov_preview_lines`가 `SETTINGS`의 `buy_cash_buffer_pct`를 넘긴다). `need` 계산은 이제 `ORDER_BUFFER_PCT`(10%)를 쓴다. 1% 수수료 여유는 10% 안에 들어간다.
- `left` 계산은 그대로 둔다 (회차금 − 실제 매수금 = 다음 회차로 넘어가는 대기 달러). `apply_buy()`·`tranche_amount()`·`sgov_fx_need()`는 건드리지 않는다. 아침 환전 필요액(`sgov_fx_need`가 돌려주는 회차금 + 대기 달러)은 바꾸지 않는다. 환전은 회차금을 맞추는 것이고, 수량은 그날 현금에 맞게 이 고침이 정한다.
- **수량 0 처리도 같이 고친다.** 현재 `sgov_step()`은 `plan["qty"] <= 0`이면 무조건 회차를 완료 처리하고 주문 없이 넘긴다 (`carry_no_order`). 이 분기는 회차금 자체가 1주 값보다 적을 때만 맞다. 여유를 반영한 뒤에는 회차금은 1주 값보다 많은데 주문가능금액(10% 여유 포함)이 모자라서 수량이 0이 될 수 있다. 그때 회차를 완료 처리하면 안 된다. 조건을 나눈다:
  - `plan["qty"] <= 0`이고 `plan["budget"] < price`이면 기존대로 주문 없이 넘김 (`carry_no_order`, 회차 완료).
  - `plan["qty"] <= 0`인데 `plan["budget"] >= price`이면 달러 부족 미룸으로 처리한다. 기존 `usd_before < plan["need"]` 분기와 같은 동작이다: 건너뜀이 아니고 예정일 그대로, 다음 거래일 다시 확인, 알림은 `usd_deferred` 문구 그대로 쓴다. 회차 완료 처리·`tranches_done` 증가·`next_due_date` 변경을 하지 않는다.
  - `need`가 0인 채로 달러 부족 분기에 들어가지 않게, 이 수량 0 검사는 달러 부족 검사보다 먼저, 위 조건대로 나눠서 처리한다. 정확한 분기 순서는 구현할 때 코드 흐름에 맞게 정하되, 위 두 경우의 동작이 바뀌지 않게 한다.

## §이식 항목 3: 새로 받은 자료가 기존 캐시보다 오래되면 덮지 않는다 (sgov.py)

파일: `meritz_dca_bot/sgov.py`, `get_history(today_kst)`의 성공 경로 (현재 186–187행).

바꾸기 전 (새로 받은 자료를 무조건 캐시에 덮어쓴다):

```python
    _write_json(p, {"fetched_kst": today_kst, "source": url.split("?")[0], "closes": closes})
    RL.ev("external_call", "sgov_fx_history", "ok", None, actor="scheduler", rows=len(closes), last=closes[-1][0])
    return closes, "fetched"
```

바꾼 뒤 (새로 받은 마지막 종가가 기존 캐시 마지막 종가보다 오래되면 캐시를 유지하고 캐시를 돌려준다):

```python
    # v1.2.9: 새로 받은 자료가 기존 캐시보다 오래됐으면(FRED 지연 등) 캐시를 덮지 않는다.
    # 2026-11-17 실측: FRED 마지막 종가 2026-11-06, 캐시 마지막 2026-11-13(Yahoo).
    # 덮어쓰면 weekly_jump이 no_reference가 되고 avg_months도 14일이 지나면 history_stale이 된다.
    # closes는 오름차순 정렬돼 있고, 날짜는 ISO 문자열이라 문자열 비교가 날짜 비교와 같다.
    if c.get("closes") and closes and closes[-1][0] < c["closes"][-1][0]:
        RL.ev("external_call", "sgov_fx_history", "ok", "cache_newer", actor="scheduler", rows=len(c["closes"]), last=c["closes"][-1][0])
        return [tuple(x) for x in c["closes"]], "cache_newer"
    _write_json(p, {"fetched_kst": today_kst, "source": url.split("?")[0], "closes": closes})
    RL.ev("external_call", "sgov_fx_history", "ok", None, actor="scheduler", rows=len(closes), last=closes[-1][0])
    return closes, "fetched"
```

- 캐시를 유지할 때는 `fetched_kst`를 오늘로 찍지 않는다. 다음 날 다시 받기를 시도해서 FRED가 따라오면 그때 갱신된다.
- 캐시가 없을 때는 기존대로 새로 받은 자료를 쓴다.
- `avg_months()`의 14일 규칙(`history_stale`)은 바꾸지 않는다. FRED가 2026-11-30까지 따라오지 않으면 그 회차 판단이 `history_stale`로 막힐 수 있는데, 그건 이 고침의 범위가 아니다. 검증에서 11-30 시나리오를 돌려보고 결과를 VERIFY.md 주의점에 적는다. 규칙을 바꾸는 것은 Muse에게 묻는 질문에 적는다.

## 버전

- `meritz_dca_bot/t_core.py`의 `BOT_VERSION`을 `"v1.2.8"`에서 `"v1.2.9"`로 올린다.
- `t_core.py`·`sgov.py` 머리말 주석에 v1.2.9 한 줄씩 추가한다 (무엇을 바꿨는지 한 줄로).
- 그 외 파일의 버전 표기는 건드리지 않는다.

---

## 검증 (반드시 직접 실행하고 결과를 VERIFY.md에 적을 것)

검증 스크립트 `verify_sgov_fetch_buffer_v129.py`를 새로 만들어 ZIP에 넣고, 아래 항목을 전부 직접 실행할 것. 실제 메리츠 API 키·서버 접속 없이, 가짜(mock) 응답과 가짜 캐시 파일로 검증한다. 실제 API를 부르지 않는다. `sgov.py`를 import할 때는 ZIP 안의 `t_core.py`·`bridge.py`·`replay_log.py`·`dca_engine.py`를 같은 디렉터리에 두고 import한다.

1. 항목 1 재시도 창 폴백: 가짜 캐시 파일(fetched_kst를 어제 날짜로, closes에 780행짜리 가짜 종가 목록 — 날짜·가격은 아무 값이나, 단 100행 이상)을 만들고, `HIST_FETCH`가 예외를 내게 한 뒤 `get_history(오늘 KST 날짜)`를 두 번 부른다. 첫 번째 호출이 캐시 종가 목록과 이유 `"cache_stale"`을 돌려주는지, 두 번째 호출(30분 창 안)도 캐시 종가 목록과 `"cache_stale"`을 돌려주는지 확인한다. (바꾸기 전에는 두 번째 호출이 `(None, "fetch_failed_recently")`였다.)
2. 항목 1 캐시 없음: 캐시 파일이 없을 때(빈 dict) `HIST_FETCH`가 예외를 내면 `(None, "fetch_failed")`를 돌려주는지, 30분 창 안 두 번째 호출은 `(None, "fetch_failed_recently")`를 돌려주는지 확인한다.
3. 항목 3 오래된 자료 덮지 않기: 캐시 마지막 종가를 2026-11-13으로, `HIST_FETCH`가 돌려주는 CSV의 마지막 종가를 2026-11-06으로 만든다. `get_history(오늘 KST 날짜)`가 캐시 종가 목록과 이유 `"cache_newer"`를 돌려주고, 캐시 파일의 `fetched_kst`와 마지막 행이 바뀌지 않았는지 확인한다. 반대로 받은 자료 마지막 종가가 2026-11-14이면 캐시가 새 자료로 덮어써지고 `"fetched"`를 돌려주는지 확인한다.
4. 항목 2 11-16 재현: `buy_plan`에 회차금 $4,600.00(대기 달러 $0.00), 가격 $100.5750을 넣는다. 수량이 42주, 필요액이 $4,660.68 이하인지 확인한다. (바꾸기 전에는 수량 45주, 필요액 $4,571.02였다.) 같은 가격에 현금 $4,660.68이면 주문 시도가 메리츠 검사를 통과하는 쪽(수량×가격×1.10 ≤ 현금)인지 숫자만으로 확인한다.
5. 항목 2 수량 0 구분: 회차금 $4,600.00, 가격 $100.5750인데 현금이 $100.00뿐이면, 가짜 클라이언트(현재가·예수금·잔고)와 가짜 주문 함수로 `sgov_step`을 돌린다. 주문 함수가 불리지 않고, `tranches_done`이 그대로이며, `next_due_date`가 그대로인지 확인한다. (바꾸기 전에는 회차 완료 처리가 됐다.) 반대로 회차금이 $50.00(1주 값보다 적음)이면 주문 없이 회차가 완료되는지(`carry_no_order`) 확인한다.
6. 항목 2 정상 매수 경로: 회차금 $4,600.00, 가격 $100.5750, 현금 $4,660.68, 잔고 0주로 가짜 클라이언트·가짜 주문 함수로 `sgov_step`을 돌린다. 주문 함수가 42주로 한 번 불리는지, `tranches_done`이 1 오르고, `wait_usd`가 회차금 − 42주×가격과 같은지(오차 $0.01 이내), `next_due_date`가 2026-11-30인지 확인한다.
7. 11-30 시나리오 (주의점 확인용): 캐시 마지막 종가를 2026-11-13으로 두고 `avg_months`(36개월)를 2026-11-30 기준으로 돌린다. `history_stale`이 나오는지 확인하고, 결과를 VERIFY.md 주의점에 적는다. (이 항목은 실패가 아니라 관찰 결과이다. 규칙을 바꾸지 않는다.)
8. 바뀐 파일 2개(`sgov.py`·`t_core.py`)가 `py_compile`을 통과하는지 확인한다.
9. `BOT_VERSION`이 `"v1.2.9"`인지 확인한다.
10. `bridge.py`·`replay_log.py`·`dca_engine.py`는 바꾸지 않았는지 (해시가 MANIFEST와 같은지) 확인한다.

검증 결과를 VERIFY.md에 항목별로 통과/실패로 적는다. 실패가 있으면 제출하지 않고 'Muse에게 묻는 질문'에 적는다.

---

## 제출

- 바뀐 파일만 번호 매겨 ZIP 1개로: 1. sgov.py, 2. t_core.py (파일은 `meritz_dca_bot/` 상대 경로 그대로 넣는다). 고침은 `sgov.py`에만 있고 `t_core.py`는 버전만 올린다. 그 외 파일이 바뀌면 안 된다.
- ZIP 안에 VERIFY.md(맨 위에 "방: 3. 미국주식 적립", 각 파일의 변경 전후 sha256, 검증 항목별 결과, 주의점) + 검증 스크립트 `verify_sgov_fetch_buffer_v129.py`를 넣는다.
- 채팅 메시지는 3줄만: 첫 줄 맨 앞에 "방: 3. 미국주식 적립"을 붙이고 최종 목록 한 줄, 바뀐 것 한 줄, 검증 통과/실패 한 줄.
- 제출 ZIP 파일명: `meritz_sgov_fetch_buffer_fix_v129_room3-meritz-accum.zip`.
- 막히면 제출물의 'Muse에게 묻는 질문' 항목에 적는다. 유저에게 채팅으로 직접 묻지 않는다.
