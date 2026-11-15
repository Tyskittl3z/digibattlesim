# Game 0001: Bot A versus Bot B

**Result:** Bot B won by successful direct attack on turn 7.

**Locked game:** seed 17795081213137388177; Bot B moved first. Both seats used the same public-board, own-hand, printed-text policy and loaded the Game 0000 history model. Their report hash was `9e62a62789bf75fcbd943bd8fe0091bace271c36549489909cb1fb9de27a6c82`.

**Audit:** 132 accepted commands, 132 Bot C observations, and exact replay under record `ac1d7e1d763196a06790110195218e1eaa97b4e67d146e9abd4266fff9b99fbb`. No random player-policy choices were drawn.

**Board-impact labels:** green 45, yellow 69, red 18. These labels measure immediate field changes under the recorded provisional criteria; they do not prove a choice was strategically optimal.

**Security checks:** A 2; B 5. Final Security counts: A 0; B 3.

Every action, choice, judge receipt, board label, memory change, and zone movement is in `game-0001-actions.csv`. The gzipped final segment includes complete before/after states, Bot C observations, policy inputs, and repair lineage.

## Turn record

| Turn | Active bot | Logged actions | Last action |
|---:|:---:|---:|:---|
| 0 | B | 3 | REDRAW_CHOICE |
| 1 | B | 7 | FINISH_TURN |
| 2 | A | 8 | FINISH_TURN |
| 3 | B | 21 | FINISH_TURN |
| 4 | A | 18 | FINISH_TURN |
| 5 | B | 42 | FINISH_TURN |
| 6 | A | 10 | FINISH_TURN |
| 7 | B | 23 | CONFIRM_ATTACK |

## Observed card interactions

- Bot A checked LM-056 in Security, chose LM-034 from two revealed cards, returned P-104 to the deck bottom, and placed LM-056 in the battle area.
- Bot A attempted EX13-023’s return. Bot B chose EX13-017’s inherited suspend replacement and kept its Veedramon stack in play.
- BT12-029 later returned A’s EX13-023 to hand. Official EX13-023 ruling Q7265 allows returning the Digimon itself while protecting its stacked cards.

## Evidence limits

This is a completed experimental software match with an automated judge and exact replay. It has no independent rules certification or accepted 60-match or 10,000-match evaluation credit. The development halts are preserved in the repair lineage; all commands in the final match ledger were accepted.
