# Roadmap evidence review after 60 V2 games

The final model has 24 Bot A and 18 Bot B coarse state keys with at least
two recorded action keys, each supported by two independent games. These
counts are a search queue, not 42 proven strategic comparisons. A state key
summarizes public tempo and can group different physical cards, hands,
pending effects, and timing windows.

One apparent comparison is false on inspection. For Bot A state key
`12de909c20fd15...`, Games 0004 and 0015 each contain both action keys:

| Match reference | Observed action | Immediate board label |
| --- | --- | --- |
| Game 0004, action 59; Game 0015, action 88 | Digivolve BT11-023 on EX13-002 in breeding for 0 memory | Green |
| Game 0004, action 60; Game 0015, action 89 | Then digivolve P-138 on that BT11-023 for 2 memory | Red |

The second action follows the first in each game. They are successive steps
of a stack, not alternatives available at the same decision point. The
immediate red label describes memory spent at that step; it does not mean
the digivolution was a worse strategic line. Other repeated keys include
ordered pending-effect resolutions, which also need timing-window review
before comparison.

Consequently, **no best/medium/worst strategy lane is approved yet**. The
preregistered `ROADMAP_CRITERIA.json` requires actual legal alternatives
under a stated public condition, at least two independent seeds per
alternative, observed board effects and memory costs, exact match
references, and separate rules and strategy review. The 4,093 immediate
green, 5,203 yellow, and 1,436 red action labels remain action observations,
not roadmap verdicts. The appropriate roadmap status is `UNKNOWN` until
candidate pairs pass those checks.

The next review should start from a single decision's saved `candidates`
and `chosen` fields, compare only alternatives that were available at that
same decision point in independently seeded games, and inspect the full
public field plus each bot's own hand and card text. Match-specific rules
questions belong in the rules review packet, linked to game, seed, and
action. An illegal action is a rules halt, never a red strategic play.
