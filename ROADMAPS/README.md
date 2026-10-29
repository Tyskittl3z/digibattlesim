# Matchup-specific roadmap candidates

Only JUPITERMON (A) versus AMATERASUMON_TOHO (B) is in scope.

`A.json` and `B.json`, when generated, index observed decision situations and
reference exact match/seed/event hashes. They are **EXPERIMENTAL_UNAPPROVED**.
All initial situations are **UNKNOWN**; approved GREEN/YELLOW/RED entries and
judge-confirmed ILLEGAL entries are empty.

Heuristic scores and observed winners do not approve a lane. Approval requires
rules evidence plus evaluated alternatives and an explicit strategic basis
supported by multiple independent-seed traces. RED is a strategic judgment
among legal choices; ILLEGAL is a separate rules ruling.

`APPROVAL_CRITERIA.json` is preregistered before a cohort and hashed in its
provenance. Approved entries must state their objective, metric/direction,
comparison basis, evaluated legal alternatives with exact selected-decision
traces, multiple independent seeds, and uncertainty. The two-seed/two-alternative
floor is a minimum structural requirement, not a statistical confidence claim.
Changing criteria after outcomes requires new provenance/evidence.

Rules legality comes from `--review`. A separate `--strategy-review` of kind
`STRATEGY_EVALUATION_REVIEW` supplies effectiveness approval and binds the criteria,
both pilots, both roadmap files and the current cohort. Neither review can
substitute for the other. No existing UNKNOWN entry is promoted by these changes.

The generator groups by decision kind, source, security counts, memory, and
active player. These are indexing conditions, not sufficient strategy rules.
Complete public decision positions and the acting player's hand are in the
referenced records for review. Private audit snapshots must never feed pilots.

Deck, rules, engine, pilot, or matchup changes invalidate these candidates and
their provenance; preserve the old artifacts and regenerate with fresh evidence.
