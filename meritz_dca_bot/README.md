# 메리츠 적립 봇 (meritz_dca_bot · 서비스 meritz_dca) — v1.0.0

3번 토스 적립(toss_dca_bot v4.3.8)의 적립 엔진을 그대로 옮기고, 토스 API 부분만 메리츠 4번 계좌 API로 바꾼 **새 봇**이다. toss_dca_bot 은 수정하지 않는다.

- 미국주식만 (한국주식 제외). 종목 수 제한 없음. 종목 추가는 텔레그램 관제탑 **➕ 종목 추가** (⏸ 중지 상태로 등록).
- 하루 1번, 미국 동부 10:05~15:40, 메리츠 **시장가 즉시주문**(oder_cls_code 05). 메리츠는 **정수 주**로만 주문한다.
  - 매수: 그날 금액(기준금액 × N7 배수 × ½ 규칙)으로 살 수 있는 만큼 사고, 남은 돈은 다음 날로 이월(`us_int_buy_mode: "carry"`, 100일 평균 = 기준금액). `"min1"` 이면 3번 한국주식처럼 최소 1주.
  - 익절·분할매도: 3번 한국주식 정수 규칙 (보유 × 비율 반올림, 최소 1주).
- 평단·수량은 **봇 장부**(시작값 주입 + 체결 내역)가 기준. 입고 평단은 쓰지 않는다. 장부 ≠ 메리츠 잔고면 그 종목은 주문하지 않는다.
- 텔레그램: 3번 기존 토큰을 읽기만 함(`telegram_env_file`). **toss_dca 서비스가 살아 있으면 폴링하지 않는다** (같은 토큰 충돌 방지).
- 상태·로그·토큰은 GitHub 폴더 밖: `state_dir`(기본 `/var/lib/meritz-dca`). 설정: `/etc/meritz-accum/settings.json`.

## 실주문 조건 (모두 맞아야 주문이 나감)
enabled=true · dry_run=false · transfer_confirmed=true · 키 지문 = expected_key_fp · P/VR6/3번 키 지문·파일과 다름 · `--inject-start` 완료 · 전체 전원 ON · 종목 ▶️ · 장운영 코드 004 · 장부 = 잔고 · 체결 대기 없음.
기본은 enabled=false, dry_run=true. 모의(dry_run)는 주문 API 를 부르지 않고 `dca_config.dry.json` 에만 기록한다.

## 설정 예시 (값은 상태 파일 2번 기준으로 Muse 가 채움 — 저장소에 올리지 않음)
```
{
  "enabled": false, "dry_run": true, "transfer_confirmed": false,
  "key_file": "/etc/meritz-accum/meritz_keys.json",
  "expected_key_fp": "<--fingerprint 값>",
  "forbid_key_fps": ["<P 지문>", "<VR6 지문>", "<3번 SOXL 지문>"],
  "telegram_env_file": "/home/gieokkim/toss_dca_bot/.env",
  "poll_block_service": "toss_dca",
  "state_dir": "/var/lib/meritz-dca",
  "us_int_buy_mode": "carry",
  "start": {
    "master_active": false, "tp1_pct": 10, "sr_pct": 20, "n7_enabled": true,
    "n7_state": {"SP500": {"mult": 1.0, "last_candle": "<YYYY-MM-DD>", "d": <거리>, "cand": null, "cand_days": 0}},
    "stocks": {
      "NKE": {"qty": <정수>, "avg_usd": <평단>, "principal_usd": <원금>, "s_day": <일차>, "sold_stage": <0/1/2>, "base_amount": 40},
      "QLD": {"qty": <정수>, "avg_usd": <평단>, "principal_usd": <원금>, "s_day": <일차>, "sold_stage": <0/1/2>, "base_amount": 40}
    }
  }
}
```
현금(시드)은 설정에 넣지 않는다: 매수 때 메리츠 USD 예수금을 그대로 본다 (USD 행이 없는 빈 계좌 = $0, 매수만 보류·익절은 진행).

## 켜는 순서 (Muse·사용자)
1. 설정 파일을 `/etc/meritz-accum/settings.json` 에 둔다 (서비스 사용자만 읽기). `python3 main.py --fingerprint` 값 확인.
2. `python3 main.py --check` — 주문 없이 키·텔레그램·장운영·종목별 오늘 계획 미리보기.
3. 입고 확인 → `transfer_confirmed=true` → `python3 main.py --inject-start` (메리츠 잔고 = start.qty 일 때만).
4. toss_dca 완전 정지 → meritz_dca 시작 (절체). `enabled=true`(dry_run=true)로 며칠 모의 → 승인 뒤 `dry_run=false`.
5. 관제탑에서 🟢 전체 전원 켜기 (주입 때 master_active=false 면 OFF 로 시작).
