# 메리츠 SOXL 무한매수 봇 (meritz_laoer) — v1.0.2

메리츠 3번 계좌(Super365)에서 SOXL 라오어 무한매수(V14)를 돌리는 **새 봇**. hantu_laoer 는 수정하지 않는다.

- 전략 파일 `strategy_v14.py`·`global_throttle.py` 는 hantu_laoer 와 **바이트까지 같은 복사본**.
- 키·토큰·설정·장부는 GitHub 에 올리지 않는다: `/etc/meritz-laoer/` (설정·키·토큰), `/var/lib/meritz-laoer/data/` (장부).
- 기본 `enabled=false`, `dry_run=true`. 실주문은 아래가 모두 맞을 때만 나간다:
  enabled=true · dry_run=false · transfer_confirmed=true · toss_sniper_stopped_confirmed=true ·
  키 지문 = expected_key_fp · P/VR6 키·다른 봇 토큰과 다름 · 장부 시작(--inject-start) · 장부 수량 = 메리츠 잔고 · 정지 표시 없음.

## 켜는 순서 (Muse·사용자)
1. 설정 파일·새 키·새 텔레그램 토큰을 서버 `/etc/meritz-laoer/` 에 둔다 (권한 600).
2. `python3 main.py --fingerprint` → 나온 값을 `expected_key_fp` 에 넣는다.
3. `python3 main.py --check` — 주문 없이 점검·계획 미리보기.
4. 입고 확인 → `transfer_confirmed=true`, 토스 스나이퍼 정지·미체결 0건 → `toss_sniper_stopped_confirmed=true`.
5. `python3 main.py --inject-start` (메리츠 잔고 = start.qty 일 때만 장부 시작).
6. `enabled=true` (dry_run=true 로 며칠 모의) → 승인 뒤 `dry_run=false`.

## 직접 산 주식 반영 (v1.0.2)
`python3 main.py --add-shares --qty N --avg X` — 메리츠 잔고 = 장부 + N 일 때만 수량 +N, 원금 +N×X, 평단 = 원금÷수량. enabled=true·미국장 주문 시간(미 동부 order_time_et~order_deadline_et)엔 거부. 주문 안 냄. 전후를 텔레그램·`data/add_shares_log.json` 에 남김.
