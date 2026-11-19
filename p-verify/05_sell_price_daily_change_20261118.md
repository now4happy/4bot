# Sell price day-to-day movement — a clue for the unsolved S1 / S4 X (2026-11-18)

Room: P매매 검증 (p-verify)
Date: 2026-11-19 (observation from 11-18 table)
Base dataset: p_data_v12.json (385 rows, sha256 bcedc40142bac16ad71cb1ccf01e92fc0298d4fe4096f2f421005e04ec32ee24)

## The observation (user spotted)

The three sell lines kept the same quantities for three days (11-16 → 11-17 → 11-18),
but their prices moved differently. One line went UP while the other two went DOWN.

| Date | Close | Sell line qty 8 | Sell line qty 11 | Sell line qty 6 |
|---|---|---|---|---|
| 2026-11-16 | 48.76 | 58.10 | 73.59 | 50.17 |
| 2026-11-17 | 49.07 | 57.95 | 73.51 | 50.59 |
| 2026-11-18 | 49.26 | 57.90 | 73.44 | 50.78 |

Day-to-day changes:
- qty 8: 58.10 → 57.95 (−0.15) → 57.90 (−0.05)
- qty 11: 73.59 → 73.51 (−0.08) → 73.44 (−0.07) — this is the solved S2 carryover rule (×0.999 per step, floored)
- qty 6: 50.17 → 50.59 (+0.42) → 50.78 (+0.19) — INCREASED, opposite direction

The qty 6 line is the interesting one:
- 11-16: price − close = 50.17 − 48.76 = 1.41
- 11-17: price − close = 50.59 − 49.07 = 1.52
- 11-18: price − close = 50.78 − 49.26 = 1.52
- The 11-17 → 11-18 move (+0.19) exactly equals the close move (+0.19), so the
  offset stayed at 1.52. But the offset was 1.41 on 11-16, so it changed once
  (11-16 → 11-17) and then held.

## Recent context (sell lines 11-09 → 11-18)

| Date | Close | Buy (P) | Sell lines |
|---|---|---|---|
| 2026-11-09 | 56.20 | 55.14×11 | 65.43×6, 76.96×11, 57.90×6 |
| 2026-11-10 | 56.06 | 54.21×9 | 65.42×6, 76.89×11, 57.28×6 |
| 2026-11-11 | 66.03 | 64.33×14 | 76.81×11, 67.40×11 |
| 2026-11-12 | 65.53 | 63.29×16 | 73.74×11, 67.05×11 |
| 2026-11-13 | 58.32 | 56.60×1 | 73.74×11, 60.04×13 |
| 2026-11-16 | 48.76 | 46.97×1 | 58.10×8, 73.59×11, 50.17×6 |
| 2026-11-17 | 49.07 | — | 57.95×8, 73.51×11, 50.59×6 |
| 2026-11-18 | 49.26 | — | 57.90×8, 73.44×11, 50.78×6 |

Holding avg price is 93.376 on both 11-17 and 11-18 (no buy, no sell filled).
No buy on 11-17 or 11-18, so P stays at the 11-16 value (46.97) for those days.

## The question

What rule makes the qty 6 sell line move UP (+0.42, +0.19) while the other two
lines move DOWN? In particular:
- Is the qty 6 line an S4 X line whose X moves with the close (close + 1.52)?
- If so, why was the offset 1.41 on 11-16 and 1.52 on 11-17/11-18? What changed it?
- Or is it an S1 line, or a different rule entirely?
- Does the same movement pattern appear in earlier data (e.g. other qty 6 lines,
  or the 57.90×6 line on 11-09)?

## What is already settled (do not redo)

- Sell price formula work (판 1–3) is CLOSED. Solved: 296/661 lines (44.8%, v12).
  S2 carryover, S3 bundle (P×1.0015), S4 floor (close+0.02) are solved.
  S1 all-quantity lines and S4 X are confirmed unsolvable from table data +
  external VWAP alone (판 3). This is a NEW angle: use the day-to-day MOVEMENT
  of the prices as the clue, not the absolute price level.
- Do not invent numbers. If a rule cannot be confirmed from the data, say so.
- The sell lines above are the table values (×1). The bot multiplies by 6 for
  actual orders; do not multiply here.

## What to deliver

- A classification of the qty 8 / qty 11 / qty 6 lines on 11-16, 11-17, 11-18
  (which are S1 / S2 / S3 / S4, and why).
- A hypothesis for the qty 6 line movement, tested against the full dataset
  (does the same rule explain earlier qty 6 lines and other increasing lines?).
- If a rule is found, state its exact form, how many lines it fits, and how many
  it fails. If no rule is found, say what was tested and what would be needed.
