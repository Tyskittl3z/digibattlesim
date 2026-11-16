# What remains before roadmaps and evaluation

The corrected 60-game sequence is complete as software evidence. Its 10,047
accepted actions and heuristic colors can be inspected in the per-game logs.
No game has independent rules certification, so accepted fact-finding credit
remains zero.

Rules review found a confirmed Piercing timing defect in games 24 and 55:
`END_ATTACK` cleared the attack before the mandatory check resolved. See
`RULES_REVIEW_FINDING.md`. Repair the scheduler under a new source hash and
rerun affected evidence from the locked seeds; this archive stays diagnostic.

The current approval gates still require:

1. A selected-matchup official rules snapshot and independent review.
   `RULES/RULES_LOCK.json` remains `UNVERIFIED` with no pinned documents.
2. An encountered-interaction branch inventory with reviewed legal alternatives.
   `RULES/INTERACTION_COVERAGE.json` remains `UNVERIFIED` with no entries.
3. For each proposed green, yellow, or red strategy lane, the preregistered
   `ROADMAPS/APPROVAL_CRITERIA.json` requires at least two evaluated legal
   alternatives, evidence from multiple independent seeds, uncertainty, and a
   separate strategy review. The action colors alone do not meet that contract.
4. Resolve or explicitly disposition the repository-wide test failures. The
   latest run reported 19 failures and 4 errors out of 712 tests; 55 focused
   tracker, scorer, and Piercing tests passed.

No best/medium/worst roadmap is approved or frozen. The 10,000-match evaluation
has not started. Preserve the corrected 60-game records and their seed schedule
while these gates are reviewed.
