# Verified workflow adjustments — 2026-10-29

All five user-approved workflow adjustments are implemented in the project
requirements and executable evidence gate. No decklist or card-resolution rule
was changed, and no rules/strategy certificate or final result was created.

| Accepted adjustment | Implemented behavior |
|---|---|
| Pin rules and format | `RULES/RULES_LOCK.json` records format/region/language, as-of date, official editions/effective dates and source hashes. The gate rejects missing pins, future-effective documents and changed bytes. The actual template remains UNVERIFIED. |
| 60 matches is a minimum | Gate accepts balanced cohorts above 60 and requires at least 30 starts per deck. Every record needs review; targeted scenarios receive zero full-match credit. Encountered branches require a reviewed coverage inventory. |
| Separate legality and effectiveness | `--review` supplies rules review; `--strategy-review` supplies a distinct strategy attestation bound to cohort, criteria, both pilots and roadmaps. Neither substitutes for the other. |
| Preregister lane criteria | `ROADMAPS/APPROVAL_CRITERIA.json` enters pre-cohort provenance. Lanes require legal evaluated alternatives, exact same-interaction decision traces, multiple seeds, metric/objective, comparison basis and uncertainty. UNKNOWN remains unapproved. |
| Preserve HALTs/restart changed freezes | Preparation records no replacement seeds. `workflow_policy.assess_resume` checks the original schedule and checkpoint seed/position; infrastructure retries replay the original match, unresolved rules HALTs block, and any frozen input change requires a new freeze/full restart. |

The two-seed/two-alternative floor is a structural minimum, not statistical
confidence or proof of a good strategy. Parsing attestation bindings cannot
authenticate reviewer qualifications or make an unverified rule true.

## Verification

- **128 unit tests passed**, including larger balanced cohorts, missing/changed
  pins, legal-branch coverage, separate reviews, alternative/uncertainty checks,
  source/path isolation, original-seed preservation and changed-freeze restart.
- Independent code review found two coverage-binding loopholes. Reproduced both
  with failing regressions and fixed them: evidence must belong to its own card/
  decision/effect inventory; observed choices cannot be omitted or labeled ILLEGAL.
  The same interaction-binding protection also applies to lane alternatives.
- New diagnostic cohort: **60 attempts; 30 A-first / 30 B-first; 29 software
  completions / 31 HALTs; 60 matching deterministic evidence replays; 60 final
  physical-state checks passed**. These are software observations, not legal
  fact-finding results.
- Current gate CLI exited **2 / BLOCKED** for the known gameplay halts/unmodeled
  optional attacks and missing rules pins, rules review, coverage, strategy
  review and roadmap approval. It reported no stale-source, schema or hash errors
  for the new cohort.
- Final seed preparation contains **10,000 unique unplayed seeds**, 5,000 starts
  per deck, disjoint from the diagnostic cohort. The canonical schedule hash is
  checked separately from the compressed-file hash. It remains NOT FROZEN.

## Current evidence

- Cohort: `ARTIFACTS/current-2026-10-29-02/`
- Preparation: `EVALUATION/preparation-2026-10-29-02/`
- Current roadmaps: A **609 UNKNOWN** groups; B **427 UNKNOWN** groups; no approved lanes.
- Prior roadmap files preserved at `ROADMAPS/history/2026-10-29-01/`.
- Source/input bundle: `81e53350f3a5b6b51936432f582e02b588f4320ee3bca09f3a7550dcb0d26904`
- Provenance: `c39c533058cac760d7172ccdbe813cd0b30cc822134514582ff23b1f466772a4`
- Cohort manifest: `e140932a82853891416aa1b70f1661ca9a319596315db05fe03410704ea52663`

The rules/format pin and interaction registry remain UNVERIFIED until actual
official evidence and the selected format are established. Judge-valid full
matches remain **0**, approved lanes **0**, final matches played **0/10,000**.
Original Susanoomon and additional encountered card-interaction work remains
outstanding. The pure resume-policy validator does not implement the live frozen
runner, checkpoint storage or transcript streaming; those remain behind the gate.

See `WORKFLOW.md` for the precise contracts. Deck changes invalidate all matchup
evidence; frozen gameplay/input changes invalidate all final evaluation results.
