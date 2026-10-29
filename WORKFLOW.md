# Accepted verification workflow

These five adjustments were approved by the user on 2026-10-29. The exact two
decklists and numerical-results-only purpose remain unchanged.

## 1. Pin official rules and the selected format

`RULES/RULES_LOCK.json` records the format name/region, language, as-of date and
official comprehensive-rules, errata, restriction-list, card-text and card-Q&A
documents. Each document needs an ID, kind, edition, effective date, official URL,
local file, SHA-256 and meaningful citation. Effective dates cannot exceed the
selected as-of date. All documents live under `RULES/` and require a separate
verified snapshot review. Missing selections or evidence stay UNVERIFIED.

The lock, its source bytes and the lane criteria enter provenance before any
cohort runs. A changed lock/document/criterion invalidates the old cohort for
current eligibility. No official evidence or missing format selection is guessed.

## 2. Minimum cohort plus encountered branch coverage

The minimum is 60 full judge-reviewed matches, with equal starts and at least
30 starts per deck. Larger balanced cohorts are allowed. Keep every attempted
seed and HALT; do not cherry-pick a successful subset.

`RULES/INTERACTION_COVERAGE.json` is bound to current provenance. Its entries
identify loaded-card interactions, link all encountered BOT_DECISION/JUDGE_PATH
events, and enumerate reviewed alternatives. A judge must attest that each
branch inventory is complete. Legal branches need evidence from a bound match
trace or a reproducible targeted scenario; ILLEGAL alternatives need official
citations and remain separate. Unknown or uncovered legal branches block freeze.
Other events and timing still require full-transcript rules review.

Coverage-entry contract:

```text
interaction_id, card, encounters: [match trace references],
inventory_review: {reviewer, verdict: VERIFIED, citations},
branches: [{id, legality: LEGAL|ILLEGAL, citations, evidence}]
```

Match references identify `index`, `seed`, `record_sha256`, `event_index`, and
`kind: MATCH`. An inventory groups only one card/decision/effect context. Every
observed choice/path must be present as a LEGAL branch; unchosen prohibited
alternatives may be ILLEGAL with citations. A branch's match evidence must be
one of that inventory's declared encounters and actually select that branch.
Equal ACTIVATE/DECLINE labels on another card or effect cannot supply coverage.
Use `card: null` only for generic pilot decisions with no card source; their
decision type and acting seat still define the context.

Scenario evidence identifies `kind: SCENARIO`, a file under
`RULES/scenarios/` and its SHA-256. A scenario records current provenance,
initial/final snapshots, nonempty actions and its own rules review/citations.
**A targeted scenario contributes zero full matches.**

## 3. Keep three verification questions separate

- Software integrity: did the engine preserve physical cards, bounds, timing
  records, determinism and terminal-state invariants?
- Rules legality: did a judge verify the encountered choices/resolution against
  the pinned official evidence? Supply `--review` for this attestation.
- Strategic effectiveness: were legal alternatives evaluated under objective
  conditions with supporting traces, metrics and uncertainty? Supply a separate
  `--strategy-review` attestation for this.

Neither review substitutes for the other. Software completion/replay does not
answer either review question. Parsing attestations validates their bindings;
it cannot authenticate reviewer qualifications or source truth.

## 4. Preregister lane approval criteria

`ROADMAPS/APPROVAL_CRITERIA.json` is hashed before fact-finding. It defines the
evidence floor and each color. Each approved entry requires objective board
conditions, legal status, a stated objective/metric/direction, at least two
evaluated legal alternatives with numeric observations and bound evidence,
multiple independent seeds, a comparison basis and uncertainty. The evidence
floor is not a claim of adequate statistical power.

A strategy review has kind `STRATEGY_EVALUATION_REVIEW` and binds reviewer,
cohort hash, provenance hash, criteria hash, both pilot hashes, both roadmap
hashes and explicit per-seat approval verdicts. Approved lanes contain
`criteria_sha256`, `objective`, `metric`, `direction` (MAXIMIZE/MINIMIZE),
`uncertainty`, `compared_alternatives` (distinct IDs, metrics and match evidence),
and the existing condition/evidence/approval_basis fields. A rules-review file
cannot supply this approval.

Each alternative's ID must match an actually selected choice in its referenced
BOT_DECISION event. Alternatives and lane evidence share the same interaction
context; a reference from another card/decision cannot stand in for an untested
choice. Narrative and numeric observations still need independent review.

GREEN/YELLOW/RED apply only to legal choices. ILLEGAL is a separate official
ruling. UNKNOWN persists until evidence is sufficient. Preregistered criteria
cannot be edited after seeing outcomes while retaining the same cohort.

## 5. Halt, retry and new-freeze protocol

The final runner must retain the exact halted seed, attempt and trace. Never
substitute another seed to fill a quota or silently discard a failure.

- Same frozen inputs plus an infrastructure interruption: replay the original
  match from its original seed; verify before crediting a completed result.
- Unresolved gameplay/rules HALT: stop final play and preserve all evidence.
- Any changed frozen engine, rules/format, decks, pilots, criteria or roadmaps:
  invalidate all prior final results, create a new freeze and restart the entire
  10,000-match schedule from position zero. Preserve the old run diagnostically.

`workflow_policy.assess_resume` enforces these decisions for a checkpoint whose
`frozen_inputs` has SHA-256 values for `engine`, `rules_format`, `decks`, `pilots`,
`criteria`, `roadmaps`, and `schedule`; `next_match` records index/seed/first and
`schedule_position` identifies its entry. The caller must supply the original
10,000-match `frozen_schedule`: its canonical JSON hash (the preparation's
`schedule_sha256`), uniqueness, balance and exact checkpoint position are checked.
`halt_kind` is RULES or INFRASTRUCTURE. It makes a decision only. The actual
frozen runner, checkpoint storage and transcript streaming remain gated work.
