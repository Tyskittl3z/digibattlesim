# Repaired styled V2: 60-game software cohort

The fixed-build V2 campaign completed its scheduled Games 0000–0059. All 60
games reached an experimental software terminal without a judge halt. Bot A
won 32 and Bot B won 28. The games contain 10,732 judge-accepted actions and
10,732 Bot C observations. All 64 saved segments have exact replay receipts;
four games needed a continuation after the 256-action segment limit.

The policies were `BOARD_TEXT_HISTORY_STYLED`: aggressive Bot A and defensive
Bot B selected from each live public state, their own hands, printed card
text, and supported prior-game history. Each game's report and model were
handed to the next game. The campaign started with an empty model and used a
new campaign ID and seeds under the repaired source lock. The schedule,
source hashes, policy, scoring criteria, and rules-source status are pinned
in `campaign-lock.json`.

The immediate board-impact labels were 4,093 green, 5,203 yellow, and 1,436
red. They describe the observed effect of each accepted action. They do not
rank strategic alternatives or certify legality under an independent rules
review. The model records outcomes across games, but its state keys group
positions coarsely; sharing a key does not prove identical board states or
counterfactual outcomes.

The official source audit matches all 22 selected card pages and finds no
file-hash mismatch. It still reports `EFFECTIVE_DATE_MISSING` and
`SEPARATE_REVIEW_MISSING`. Automated judge acceptance and replay establish
internal consistency only. Accordingly, the campaign status correctly
records **0/60 rules-certified fact-finding games** and **0/10,000 final
evaluation games**. The final evaluation is neither frozen nor running.

Roadmap colors require the preregistered criteria in the V1
`ROADMAP_CRITERIA.json`: reviewed legal alternatives under a stated public
condition, at least two independent seeds per alternative, observed board
effect and memory cost, exact match references, and separate rules and
strategy review. No V2 choice is promoted to a best, medium, or worst
roadmap solely from these immediate labels.
