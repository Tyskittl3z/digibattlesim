# Processing-condition activations found during rules review

**Status: confirmed archive discrepancies; the 60 games remain software evidence.**

The cached official Comprehensive Rules v4.3 (SHA-256
`a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`)
states in sections 15-6-3 and 15-8-3-9 that a triggered effect whose only
processing condition is false cannot activate. It may trigger, then remain
pending until activation is attempted. The relevant official card pages print
the following conditions:

| Effect | Printed condition | Archived invalid activations |
| --- | --- | ---: |
| BT22-023 inherited unsuspend | If you have a blue Tamer | 58 of 112 |
| BT22-022 Tamer play | If you have 1 or fewer Tamers | 8 of 13 |
| BT22-085 start-turn memory | If you have 2 or less memory | 25 of 37 |
| EX13-069 start-main memory | If you have a Digimon with [Veemon] or [Veedramon] in its name | 42 of 167 |
| BT12-029 unsuspend return | If you have a blue Tamer or [UlforceVeedramon] in this Digimon's digivolution cards | 12 of 83 |

These counts come from every final command record in the archived 60-game
sequence. Examples are game 0 action 40 for BT22-023, game 4 action 42 for
BT22-022, and game 2 action 39 for BT22-085 (all zero-based). The first case
also consumed the once-per-turn use without a blue Tamer. The other cases
recorded a resolved effect even though the condition was false. The original
seeds, choices, results, and judge receipts remain unchanged.

The BT12-029 archive has 36 `CONDITION_OR_TARGET_UNAVAILABLE` resolutions:
12 had the printed `if` condition false (8 with an opposing target and 4
without), while 24 met the condition but had no opposing Digimon. General
rules sections 15-10-2-1 and 15-14-1-1 support activating the latter with
zero available targets and consuming the once-per-turn use. No BT12-029-specific
Q&A was found in the cached card page.

The current engine branch adds focused tests and prevents these five effects
from activating when their conditions are false. It cancels an ineligible
pending effect with an explicit reason, and the handler also rejects direct
activation. The phase-memory handler now requires its pending trigger proof.
Those fixes change game behavior, so the archived 60 cannot be
reclassified as rules-certified matches. The rules lock and full interaction
review remain open.
