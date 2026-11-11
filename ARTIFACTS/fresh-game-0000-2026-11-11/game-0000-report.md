# Game 0000: Bot A versus Bot B

**Result:** Bot A won by successful direct attack.

**Record:** 182 accepted actions across 13 turns. Bot C recorded 182 field observations; the automated judge accepted 182 actions.

**Replay:** exact against the final saved source map. Record SHA-256: `b3e0dab95a55c0100cf7f2e851e97c0165ec3d98d93d5703a933d300d46c2439`.

**Locked setup:** seed 4851742998504393566; Bot A aggressive and first, Bot B defensive; Federico Nine 123129 versus Bern 122110.

**Board-impact labels:** green 71, yellow 87, red 24. These are measured board changes under provisional criteria, not verdicts on long-term strategy.

**Successful Security checks:** Bot A 5, Bot B 0. Final Security: A 5, B 0.

The complete action-by-action log is in `game-0000-actions.csv`. The gzipped final record contains each full before/after state, bot decision, RNG state, judge receipt, Bot C observation, and exact replay lineage.

## Turn record

| Turn | Active bot | Actions | Security checks by A / B after turn | Last action |
|---:|:---:|---:|:---:|:---|
| 0 | A | 3 | 0 / 0 | REDRAW_CHOICE |
| 1 | A | 9 | 0 / 0 | FINISH_TURN |
| 2 | B | 11 | 0 / 0 | FINISH_TURN |
| 3 | A | 13 | 1 / 0 | FINISH_TURN |
| 4 | B | 17 | 1 / 0 | FINISH_TURN |
| 5 | A | 20 | 2 / 0 | FINISH_TURN |
| 6 | B | 10 | 2 / 0 | FINISH_TURN |
| 7 | A | 31 | 5 / 0 | FINISH_TURN |
| 8 | B | 11 | 5 / 0 | FINISH_TURN |
| 9 | A | 11 | 5 / 0 | FINISH_TURN |
| 10 | B | 7 | 5 / 0 | FINISH_TURN |
| 11 | A | 17 | 5 / 0 | FINISH_TURN |
| 12 | B | 11 | 5 / 0 | FINISH_TURN |
| 13 | A | 11 | 5 / 0 | CONFIRM_ATTACK |

## Interpretation limits

This is a completed experimental software game with an automated judge. Its result has no independent card-rules certification, accepted 60-match fact-finding credit, roadmap, or 10,000-match evaluation credit. Earlier development HALTs remain embedded in the verified repair lineage; the final 182-action game ledger contains only accepted actions.

Bot A labels: green 42, yellow 45, red 12. Bot B labels: green 29, yellow 42, red 12.
