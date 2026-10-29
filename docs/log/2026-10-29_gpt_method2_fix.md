# Method 2 v4.2.0 fix work record

- Status: COMPLETE AS DRAFT; NOT APPROVED FOR LIVE DEPLOYMENT.
- Start: 2026-10-29 UTC / KST (review began after user package upload).
- Finish UTC: 2026-10-29 07:43:46; KST: 2026-10-29 16:43:46.
- Baseline: package states main 67cff522f667c68eab19d9ad3b8901ee60cf4d7b, v4.1.0; edited draft_v420, not main originals. STATUS package: bot 4 v4.1.0, no pending uploads. Recheck main before Muse upload.
- Scope: read STATUS version/pending, START principles, start.md section 0 + sections 2/4/5 relevant replay, docs_handoff/04_bithumb.md, 00_GPT_FIX_BRIEF.md, draft and main reference. No other handoff.

## Changed files and purpose
- bithumb_laoeo_bot/b_core.py: restore exact existing main CHAT_ID environment fallback line; no other change from draft.
- bithumb_laoeo_bot/main.py: per-coin Telegram approval button; approval only for selected method 2 and valid saved per-coin ratio; explicit error if ratio absent; switching away and back continues resetting approval.
- bithumb_laoeo_bot/b_ui.py: show per-coin approved/pending state on control panel and held-coin balance rows.

## Three brief decisions
1. CONFIRMED: daily-close crossover, previous completed daily close versus its SMA to latest completed close versus its SMA; after 09:00 KST. No intraday switch.
2. RESTORED: Telegram chat ID fallback exactly as main; not reproduced in this record to avoid publishing identifiers.
3. IMPLEMENTED: explicit separate approval button per coin; selecting method or saving ratio alone does not approve. Missing ratio blocks approval. Approval flag is persisted only on explicit approval; switching to method 2 resets it. Restart/config load do not auto-approve. Until approved, method-2 coin trades nothing, including no method-1 regular trades.

## Still UNCONFIRMED: must get user confirmation BEFORE server application
- Up-cross buy amount equals existing per-coin seed.
- 20% down-cross sell-ratio default is only a placeholder, not user-approved. Explicitly entered per-coin ratio is user's own setting.
- Method 2 replaces method-1 daily buys and staged take-profit for that coin (not combined).
- Approving method 2 enables actual automatic orders under these still-unconfirmed assumptions; do NOT deploy or approve until decisions resolved.

## Validation
- python -m py_compile b_core.py main.py b_ui.py: PASS.
- Offline isolated mock: missing ratio -> approval remains false and error panel; before approval -> no order; valid saved ratio + explicit button -> approved; post-approval mock order after baseline -> one mock order; switching away/back -> approval false; ETH independent; status display; exact fallback matches main: PASS.
- AST comparison: all non-callback functions in main.py identical to draft; method-1 scheduler function unchanged: PASS.
- No actual order, API trading, staging, GitHub push, deployment, restart, or live trade performed.
- Replay scenario: scheduler bypass approval_required observed via isolated mock path; production JSONL replay not available in offline package. Real environment integration not tested.

## Next AI
Read STATUS (version/pending), START (principles), start.md section 0 and relevant replay sections, docs/handoff/04_bithumb.md, then this work record and the three files. Verify latest main and conflicts; obtain user confirmation on three unresolved financial assumptions before deployment. Muse reviews and uploads; ChatGPT does not.
