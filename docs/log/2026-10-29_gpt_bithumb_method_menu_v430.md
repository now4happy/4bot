# GPT 2026-10-29 — Bithumb v4.3.0 method-first menu and aligned board
Status: COMPLETED OFFLINE DRAFT (NOT DEPLOYED)
Start: 2026-10-29 KST / UTC
Finish: 2026-10-29 17:39:56 KST; 2026-10-29 08:39:56 UTC

## Baseline and reading
Muse package main a555a23cb77fac5fd6465be04b133b1e6dcf1d0f, BOT_VERSION v4.2.1, STATUS 2026-10-29 17:25 KST; pending uploads none at snapshot. Read 00_NOTE_FROM_MUSE.md first; STATUS for version/pending; prior supplied START.md and start.md section 0 and relevant scope; prior one 04_bithumb handoff. Latest main must be checked again by Muse before staging.

## Changed full source files
- bithumb_laoeo_bot/b_core.py: bump v4.2.1 -> v4.3.0; remove legacy method2_approved flag from trading readiness. Method=2 + explicit valid SMA amount + explicit valid sell ratio required. Add HTML parse mode only for board <pre> display.
- bithumb_laoeo_bot/main.py: remove separate SMA approval callback and approval resets; method-first coin navigation, smart-settings submenu, preserve whole-bot power behavior; same-method selection no-op.
- bithumb_laoeo_bot/b_ui.py: control panel BTC/ETH only; smart-stop/start, seed, buy-days, take-profit presets and custom rule in method-1 settings; SMA settings only in method-2; fixed-width HTML <pre> board BTC/ETH with identical row order and numeric formatting.

## Critical live behavior
- Selecting SMA method is APPROVAL. If saved valid amount AND ratio already exist, trading becomes enabled on the next qualifying signal without another confirmation. If missing either, orders remain locked. Existing saved amounts and ratios are retained; old approval flags remain in config but ignored.
- Existing SMA crossover logic, order execution, minimum, amounts, ratios, deduplication, 1/2x method-1 logic unchanged.
- Existing power is whole-bot ON/OFF including both coins and both methods; do not mistake the relocated button for per-coin power.
- Take-profit thresholds and sell ratio are also shared BTC/ETH method-1 settings; shown explicitly as common.
- Selecting method-2 stops method-1 regular buys and staged profit taking for that coin.
- Board displays KRW cash, today's method-1 required amount, power, per-coin method/ready state/qty/valuation/return/avg/current, total estimate and trend. It uses Telegram HTML pre formatting. This is display-only.

## Validation
PASS: AST and py_compile of all 3 files, static no-approval-button check, isolated readiness tests (ready when both financial values present; blocked without amount; blocked on method 1), HTML parse mode presence, ZIP CRC test.
NOT TESTED: live Telegram callbacks and rendering, full mocked bot integration, live exchange API, live order, server replay. No GitHub upload, staging, restart, deployment, order or forced liquidation.

## Next AI / Muse
1. Recheck latest STATUS/main and simultaneous edits; never overwrite newer code.
2. Review 3 files, especially Telegram HTML formatting and callback return navigation.
3. Replay in test mode: coin -> method -> settings -> numeric save; verify selecting SMA with saved values immediately enables readiness, missing value blocks; verify global power and shared take-profit settings; verify board displays properly on Android Telegram.
4. Require user approval of immediate-on-selection behavior before deployment (user confirmed in chat); never test with live orders.
