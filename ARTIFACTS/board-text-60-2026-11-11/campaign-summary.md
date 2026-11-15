# Sequential Bot A versus Bot B software campaign

The 60 additional games are complete. Each game used the `BOARD_TEXT_HISTORY`
player policy for both seats, the saved report and model from the preceding
game, and its locked seed. Bot C recorded 10,047 accepted judge actions.
Every terminal game has an exact replay receipt, an action log, a report, and
a committed next-game learning model. The schedule started each seat 30 times.

| Result | Count |
| --- | ---: |
| Bot A wins | 29 |
| Bot B wins | 31 |
| Green board-impact labels | 3,746 |
| Yellow board-impact labels | 5,004 |
| Red board-impact labels | 1,297 |

The final model contains 62 game histories: the two initial games and these
60 additional games. The colors describe the recorded board-impact criteria;
they are not an independent ruling on strategic quality.

## Known measurement gap

Eight successful BT20-102 Piercing Security checks moved a Security card but
did not increment Bot C's `successful_security_checks` counter. They occurred
in additional games 11, 21, 24, 25, 33, 41, 55, and 56, all for Bot B. This
can affect tempo and color ratings, and the resulting learning model. Preserve
this campaign as inspectable software evidence; correct the tracker and scorer
before using the ratings to choose best, medium, or worst plays or to freeze an
evaluation.

The campaign has zero independently certified fact-finding matches and zero
final-evaluation matches. The 10,000-match evaluation has not been run.
