# Jupitermon vs Amaterasumon / Toho — Source-Scoped Attack Audit

**Experimental only; no judge-certified matchup results.**

| Measurement | Value |
|---|---:|
| Full match attempts | 60 |
| A starts / B starts | 30 / 30 |
| Completed software games | 55 |
| Halted games | 5 |
| Completed-game software winners (A/B) | 27 / 28 |
| Independently judge-certified games | 0 |
| Full deterministic replays | 60 |
| Source tests | 78/78 |
| Approved lanes | 0 |
| 10,000-game frozen evaluation | 0 |

## Unresolved judge halts
- 1 × `JudgeHalt: SUSANOOMON_TARGET_LEAVE_REPLACEMENT_UNVERIFIED`
- 1 × `JudgeHalt: SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: BT26-029`
- 2 × `JudgeHalt: SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: P-213`
- 1 × `JudgeHalt: SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: BT24-101`

## Attack source audit

- Buried main `[When Attacking]` effects no longer activate merely because the card is in the evolution stack. Only inherited text can activate underneath.
- BT24-031 / BT25-030 inherited Elecmon effects now have explicit activate/decline decisions and correct zero-security recovery options (Bandai Q5611/Q6297).
- BT26-012 Manekimon and BT25-028 Dianamon inherited attacking effects now resolve in their source positions.
- EX12-076 Susanoomon places unprotected opponent Digimon into security; replacement and Decode cases halt explicitly. Q7194 is pinned.
- Unaffordable hard-play actions are filtered rather than clamped past the memory-gauge endpoint.
- Existing top-level optional attacking effects remain explicitly logged as unmodeled declines, not as learned or approved play lanes.

## Source references

- BT24-031: https://world.digimoncard.com/cards/?category=522033&search=true (Q5611)
- BT25-030: https://world.digimoncard.com/cards/?category=522036&search=true (Q6297)
- BT26-012: https://world.digimoncard.com/cards/?category=522038&search=true
- EX12-076: https://world.digimoncard.com/cards/?card_no=EX12-076&search=true (Q7194)
- P-213 Decode: https://world.digimoncard.com/cards/index.php?free=P-213&search=true
