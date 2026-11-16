# Corrected sequential Bot A versus Bot B software campaign

All 60 additional games completed in software under the same locked schedule
as the original campaign. Each game loaded the preceding game’s report and
model, used the `BOARD_TEXT_HISTORY` policy for both seats, and has accepted
judge actions, Bot C observations, a full action log, a terminal report, a
committed next-game model, and an exact replay receipt. Two games needed a
second saved segment at the 256-action budget; neither was a judge halt.

| Measure | Count |
| --- | ---: |
| Bot A starts | 30 |
| Bot B starts | 30 |
| Bot A wins | 29 |
| Bot B wins | 31 |
| Accepted actions | 10,047 |
| Green board-impact labels | 3,747 |
| Yellow board-impact labels | 5,004 |
| Red board-impact labels | 1,296 |
| Terminal exact replays | 60 |
| Judge halts | 0 |

The final learning model contains 62 game histories: the two initial games
and these 60 additional games. All 60 terminal records used the same source
manifest and the current tracker and scorer source hashes. Report and model
handoffs, locked seeds, and every segment replay receipt were checked. Eight
successful BT20-102 Piercing checks in games 11, 21, 24, 25, 33, 41, 55,
and 56 each increased Bot C’s successful-check count and the scorer’s check
component by one. Games 24 and 55 used the closed-attack pending shape.

The colors describe the defined immediate board-impact heuristic. They are
not approved best, medium, or worst strategy lanes. The automated judge
receipts and exact replay establish software behavior, not independent rules
certification. Accepted fact-finding credit remains zero. The repository-wide
suite ran 712 tests and reported 19 failures and 4 errors, mostly in migration
fixtures; 55 focused tracker, scorer, and Piercing tests passed. The 10,000-match
evaluation has not started and no evaluation credit is claimed.
