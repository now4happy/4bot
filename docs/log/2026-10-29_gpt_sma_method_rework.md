# BTC/ETH SMA method rework — GPT work record

## Status
- Started: 2026-10-29 (UTC and KST, package review).
- Completed draft: 2026-10-29 07:58:18 UTC / 2026-10-29 16:58:18 KST.
- Baseline: main 67cff522 (v4.1.0), staged v4.2.0 fix (commit 4e269677) from supplied package. v4.2.0 fix is superseded; **do not deploy the old fix**.
- Current state in packaged STATUS.md: 4th bot running v4.1.0, no pending uploads as of packaged snapshot. Muse must recheck latest main and simultaneous edits before upload.
- Read: STATUS.md version/pending, START.md required principles, start.md section 0 + relevant replay/security sections, docs_handoff/04_bithumb.md, 00_GPT_SMA_BRIEF.md and staged code.

## Changed final code files (repository paths)
- `bithumb_laoeo_bot/b_core.py`: unified daily-close crossover with BTC SMA100/ETH SMA200 period map retained; separate validated `sma_buy_amount()` config accessor; `method2_ready()` requires selected SMA method, explicit approval, saved valid sell ratio and saved valid buy amount; no default sell ratio used.
- `bithumb_laoeo_bot/main.py`: Telegram SMA법 label, per-coin buy amount input, approval validation for both financial inputs, explicit approval revocation on method switch and amount/ratio edits; SMA buy orders use **only** `sma_buy_amounts[coin]`, never method-1 seed or its 1/2 multiplier. The SMA branch can operate independently of a zero method-1 seed. Method switch clears crossover baseline to prevent historical replays. SMA-selected coin bypasses method-1 daily buys and staged take-profits.
- `bithumb_laoeo_bot/b_ui.py`: displays SMA법, BTC/ETH period, approval state, saved SMA buy amount and saved sell ratio per selected coin. Existing method-1 seed display remains separate.

## Design and unresolved user choices
- Internal method identifier remains integer `2` for backward config compatibility; only user-visible name is **SMA법**.
- BTC uses SMA100; ETH uses SMA200. Single crossover function compares each **completed daily close** with its own SMA, checked after the 09:00 KST candle boundary. This is not SMA100 vs SMA200 crossing.
- SMA법 buy amount numeric values: **UNCONFIRMED**, user enters each coin's KRW amount; no default. The old seed amount is never a fallback.
- SMA법 down-cross sell ratio numeric values: **UNCONFIRMED**. Previous 20% was only a placeholder; no default in this draft. User enters ratio explicitly for each coin.
- SMA법 selection alone does not approve. Saving either input revokes prior approval; separate per-coin SMA법 approval is mandatory. No trade when missing buy amount, missing ratio, or approval False.
- When SMA법 is selected, method-1 daily buys and staged take-profits do not execute for that coin, including while approval is pending. User must be informed of this pause before selecting it.
- SMA법 has **no proven optimized return** from this change; no historical walk-forward backtest was run.

## Offline verification
- `python -m py_compile` on three final files: PASS.
- Isolated mocked tests: BTC/ETH period map; up/down/none/unknown crossover; independent buy amount vs seed; no defaults; no order when ratio/buy/approval missing; buy with explicit separate amount; sell with user-set fraction; approval revoked on method switch and amount/ratio edits (source inspection); user-facing SMA법 labels; order function AST unchanged: PASS.
- Existing method-1 buy/take-profit branch left unchanged except gate for zero seed on SMA-selected coin. Existing `place_order` AST identical to staged fix.
- Scheduler bypass replay: `buy_amount_required`, `ratio_required`, `approval_required`, `unknown_signal`, `baseline_initialized` reason paths inspected/mocked; production event-log replay unavailable offline.
- No live orders, staging, push, deploy, server restart, automatic FX or forced sell performed. No secrets or account values included in this record.

## Next AI / Muse
1. Recheck STATUS.md and main head, concurrent work, and original bot files. If any newer main change touches these files, reconcile; do not overwrite blindly.
2. Review all three final files and this new record; confirm unresolved buy amounts and sell ratios with user before any server application.
3. Confirm approval and method-switch behavior, read-only candle response, replay logs and actual Telegram control panel before enabling SMA법 on live bot.
4. Upload and deploy only through the user/Muse established staging approval workflow; GPT did not connect GitHub.
