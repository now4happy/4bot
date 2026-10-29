# GPT SMA menu simplification work record

- Status: completed as offline draft, not deployed
- Started: 2026-10-29 (UTC / KST); finished: 2026-10-29 08:19:44 UTC / 2026-10-29 17:19:44 KST
- Baseline: user-supplied SMA rework v4.2.0 draft based on main 67cff522 (v4.1.0); not reverified against live main
- Scope: UI-only simplification approved after user reviewed a visual mockup
- Files changed:
  - bithumb_laoeo_bot/main.py — simplified callback navigation: coin -> method choice, amount input, ratio input, approval; clear numeric input examples; return to coin screen after valid input
  - bithumb_laoeo_bot/b_ui.py — compact per-coin settings and method-choice views; rename control buttons to BTC/ETH settings
- Files NOT changed: b_core.py, original order API, scheduler, SMA signal, existing smart accumulation rules, seed, amounts, trading configuration
- Display: BTC SMA100, ETH SMA200; SMA period fixed, no free-text 'Sma 200' command needed. Users select SMA method using a button.
- Input: choose coin -> choose SMA method -> tap SMA buy amount and send numeric KRW value -> tap SMA sell ratio and send numeric percentage -> tap SMA approval. Buy amount is distinct from seed. Approval remains locked until both saved and method selected.
- Important: switching to SMA before approval pauses the coin's existing method-1 regular buys and staged profit-taking. No live trading until Muse reviews and user approves operational conditions.
- Validation: Python py_compile on all 3 source files PASS; AST parse PASS; static checks for existing SMA order and approval code PASS. No live Telegram interaction, end-to-end mock trading, live exchange API, order, staging, GitHub upload, server deployment or restart.
- Existing replay scenario: no real event log supplied; replay against server logs NOT VERIFIED. Muse must verify callback -> input -> save -> approval in Telegram test environment before deployment.
- Unconfirmed: user-entered BTC and ETH SMA buy amounts; BTC/ETH sell percentages; confirmation of method-2 replacement behavior before live activation.
- Next AI: read STATUS.md (version/pending), START.md principles, start.md section 0 and relevant replay scenario, one handoff docs/handoff/04_bithumb.md; compare against newest main and any staged edits. Review only the two changed files, preserve the existing b_core.py.
