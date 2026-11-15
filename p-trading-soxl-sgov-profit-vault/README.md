# P-trading backtest data — SOXL profit separation to SGOV (30 / 35 / 40%)

For the Notion work room `p-trading-soxl-sgov-profit-vault` (P매매 SOXL 수익금 분리 백테스트 방).
Base: now4happy/4bot `origin/main` 49a83fb. No secrets, no account numbers.
All trade numbers are the author's published price-table numbers (gross, before fees —
the trading code has no fee / slippage / tax model).

## Files

| File | Original name | Rows | Date range | sha256 |
|---|---|---|---|---|
| p_analysis_v5.csv | P_매매_분석자료_최종_20261110_v5.csv | 378 + header | 2025-04-07 – 2026-11-09 | a7d3c39fbf7bb80ebfcd0076d0510d1c140d7fb8d6391da8b0d234adec4331c2 |
| p_analysis_v5.json | P_매매_분석자료_최종_20261110_v5.json | 378 | 2025-04-07 – 2026-11-09 | 3f293c0dff01b42c10f4eded4f8a3f2493598bc8d5cfe25470a26e088308e3cd |
| p_data_v9.json | 02_data_v9.json (newer dataset) | 382 | 2025-04-07 – 2026-11-13 | a476e6ce9c9db61b0b3ced8815b306666d7a25bb1052559ceae24f36e8238566 |
| p_numbers_178rows.jsonl | 03_숫자파일_178행.jsonl | 178 | 2025-04-07 – 2026-11-04 | 4bda2190ab1786221143b9081a8372de981fcbbb9860e018bc3bc75cbca066c7 |
| p_past_data_batch1_20261110.zip | P_과거자료_1차30개_20261110.zip | 30 days (+ combined) | see inside | 2ff9a62ba911281381dac3f699cb7b8237e49b4afecdd566c99fca311ea4811b |
| p_past_data_batch2_20261110.zip | P_과거자료_2차30개_20261110.zip | 30 days (+ combined) | see inside | 850dcfd44f73df13d41d2a50c49a23381e360063d5ac9ea4609cab7de9be339f |
| p_past_data_batch3_20261110.zip | P_과거자료_3차30개_20261110.zip | 30 days (+ combined) | see inside | a8e1c98731ea111e419fb9495dcd286f4acc185f8dfe2cd2c782ff33cf00af41 |

## Columns (v5 / v9)

종가일 (close date), 종가 (SOXL close), 매수 [{price, qty}] (buy legs),
매도 [{price, qty}] (sell legs), 보유평단 (avg holding price), 잔금 (cash balance),
총수익률 (total return %), 직전매매개수, 현재보유개수 (current holdings),
시즌실현수익 (season realized profit), 시즌 (season), 전부_환산.
CSV stores 매수/매도 as strings like `8.9x80, 9.2x83`; JSON stores arrays of {price, qty}.
`null` = not recorded for that day (early rows).

`p_numbers_178rows.jsonl` has the same trade legs plus the author's Fanding post URL per day.
Each past-data ZIP has `past_sheet_numbers_batchN_*.jsonl` (30 days),
`past_sheet_batchN_detail_*.json` (30 days incl. 평단/보유수량/잔금/시즌실현수익),
and `past_sheet_numbers_combined_*.jsonl` (cumulative; batch3 = 267 lines).

## Not included (fetch from public sources, cite the source)

- Full daily SOXL OHLC / volume series. The datasets above carry the SOXL close (종가)
  only on table days. No daily price file exists in the repo.
- SGOV price and distribution amounts. The SGOV engine only records distributions
  in its server ledger (cumulative); no SGOV price file exists in the repo.
- Trading costs. `fanding_trade.py` has no commission / slippage / tax assumption;
  order-result fee fields are usually empty. State any cost assumption explicitly.

## Authoritative record (server only, not in this repo)

`/var/lib/bot-office/fanding/history.jsonl` — one line per day with every table cell
(잔금, cycle start, realized profit, …) and the order result. Ask Muse for excerpts.
