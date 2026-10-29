# Bithumb balance board normal font — work record

Status: 완료 (오프라인 초안, 미배포)
Start: 2026-10-29 KST / UTC
Finish: 2026-10-29 17:57:20 KST / 2026-10-29 08:57:20 UTC
Baseline: user-supplied main v4.2.1 package, previously generated v4.3.0 code (not verified against newer server main).

Changed final code:
- bithumb_laoeo_bot/b_ui.py — remove fixed-width code block, display normal Telegram font; preserve BTC/ETH order and all values.
- bithumb_laoeo_bot/b_core.py — BOT_VERSION v4.3.0 -> v4.3.1 only.

Checks: py_compile PASS (2 files); isolated mock board render PASS; no code block, both coins and cash visible; zip CRC PASS. No live Telegram UI test, server deploy, GitHub upload, or live order.

Note: Telegram message font size is client-controlled. Without code block, standard chat font is used. Exact column alignment with proportional fonts cannot be guaranteed. Existing orders and strategy untouched.

Next AI/Muse: read STATUS.md for latest version/pending, START.md principles, start.md section 0/relevant scope, one handoff docs/handoff/04_bithumb.md; compare latest main before upload; test Android Telegram rendering.
