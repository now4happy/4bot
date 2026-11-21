# MANIFEST — 메리츠 적립 v1.2.9 SGOV 수정 패키지

**방: 3. 미국주식 적립 (room3-meritz-accum)**
**버전: v1.2.8 → v1.2.9**
**파일 수: 6개 (지시문 1개 + 기준 파일 5개)**

## 기준 확인 (Muse가 확인함)

- 기준 파일 5개는 2026-11-17 KST에 실행 중인 서버의 `meritz_dca_bot`에서 직접 가져왔다 (SSH). 서버의 `BOT_VERSION`은 `"v1.2.8"`이다.
- 로컬 4bot 작업본의 `sgov.py`는 서버 파일과 동일하다 (diff 없음).
- 다른 AI는 원격 대조를 하지 않는다. ZIP 안의 5개 기준 파일이 아래 sha256과 일치하는지만 확인하면 된다.

## 파일 목록

| # | 파일 | 바이트 | sha256 |
|---|---|---|---|
| 1 | 01_instruction_meritz_sgov_fetch_buffer_fix_v129.md | 21697 | baa3a0d333f966db1d8a569cfa59aa301763c66a8bfd5f1da1ef04fc7d4c8054 |
| 2 | meritz_dca_bot/sgov.py | 35724 | b7d5fb585539ab96f510119f2166bbc7a9297add3077db626327c01405afcb29 |
| 3 | meritz_dca_bot/t_core.py | 26497 | da41453c36342ab324af67fc17917b9468c9cdc03920b524e8b77de1f11e8c7c |
| 4 | meritz_dca_bot/bridge.py | 8798 | b19bf91685f3bb3214ae5495caf309f13419c4493b25a69c2b6df6e19612b1c1 |
| 5 | meritz_dca_bot/replay_log.py | 18094 | 0ac39f8f917affba0c6788809506933a552be4a47058efab80ac33c2d7d3610d |
| 6 | meritz_dca_bot/dca_engine.py | 5773 | e8db3bafd3bb039e11220b3df5c424837b2854e5895c27bd33f9023f397985c8 |

## 의존성 닫힘

- `sgov.py` → `t_core.py`·`bridge.py`
- `t_core.py` → `replay_log.py`·`dca_engine.py`
- `bridge.py`·`replay_log.py`·`dca_engine.py`는 표준 라이브러리만 쓴다.
- `main.py`·`meritz_api.py`·`t_ui.py`는 이 고침의 대상이 아니고 `sgov.py`가 import하지 않으므로 포함하지 않는다.

## 고침 요약

1. `sgov.py` `get_history()` 재시도 창(30분)에서도 캐시가 있으면 `cache_stale`로 판단.
2. `sgov.py` `buy_plan()` 수량·필요액에 메리츠 시장가 주문 여유 10%(`ORDER_BUFFER_PCT`) 반영 + 수량 0일 때 회차금 기준 구분 (1주 값보다 적을 때만 주문 없이 넘김, 그 외는 달러 부족 미룸).
3. `sgov.py` `get_history()` 성공 경로에서 새로 받은 자료가 기존 캐시보다 오래되면 덮지 않고 캐시 유지 (`cache_newer`).
4. `t_core.py` `BOT_VERSION` `"v1.2.8"` → `"v1.2.9"`.
