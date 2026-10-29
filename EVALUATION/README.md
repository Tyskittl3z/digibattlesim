# Final evaluation preparation and runner

This directory does not contain final results or a frozen evaluation. The live
runner is now implemented in `SOURCE/frozen_evaluation.py`, but the current
evidence gate remains blocked and has correctly played **0/10,000** final matches.

From `SOURCE/`, after producing a **new** current cohort:

```bash
python -m match_evidence --out ../ARTIFACTS/current-YYYY-MM-DD-NN --count 60
python -m evaluation_gate --cohort ../ARTIFACTS/current-YYYY-MM-DD-NN
```

The gate exits **2** while prerequisites are missing. It rejects missing reviews,
altered records, stale source/decks, incomplete or unbalanced cohorts, unresolved
halts, unmodeled optional attacking choices, and unapproved roadmaps.

The fact-finding floor is now **at least 60 full matches**, equal starts and at
least 30 per deck. Larger balanced cohorts are allowed. Targeted scenarios never
increase the full-match count. The gate also requires the current rules/format
lock, complete encountered branch coverage, and preregistered lane criteria.
See `../WORKFLOW.md` for the file contracts.

After all 60+ matches are valid and reviewed, their legal routes are classified
as GREEN (best), YELLOW (medium) or RED (worst) using the preregistered numeric
comparison and uncertainty requirements. The frozen 10,000-match run starts only
after those three-lane roadmaps are separately approved.

Rules and strategy reviews are separate inputs:

```bash
python -m evaluation_gate --cohort ../ARTIFACTS/CURRENT --review ../RULES/rules-review.json --strategy-review ../ROADMAPS/strategy-review.json
```

A rules review cannot approve lane colors. The strategy review must independently
bind the current cohort, criteria, both pilots and both roadmap hashes. Each lane
requires evaluated legal alternatives, comparable numeric observations and
uncertainty; heuristic scores and one outcome are insufficient.

Candidate roadmap generation is explicit and refuses to overwrite existing
maps. Version old maps before regenerating:

```bash
python -m evaluation_gate --cohort ../ARTIFACTS/current-YYYY-MM-DD-NN --candidate-roadmaps
python -m evaluation_gate --cohort ../ARTIFACTS/current-YYYY-MM-DD-NN --prepare ../EVALUATION/preparation-YYYY-MM-DD-NN
```

The preparation output reserves 10,000 distinct deterministic seeds outside
fact-finding indexes 0–59, with 5,000 starts per seat. It reports played matches
as zero and `frozen: false`. It is an input to the runner, not a freeze.

After the gate is genuinely eligible, create and execute a new run from `SOURCE/`:

```bash
python -m frozen_evaluation freeze --root .. --cohort ../ARTIFACTS/CURRENT --preparation ../EVALUATION/PREPARATION --review ../RULES/rules-review.json --strategy-review ../ROADMAPS/strategy-review.json --out ../EVALUATION/run-NEW
python -m frozen_evaluation run --run-dir ../EVALUATION/run-NEW
python -m frozen_evaluation status --run-dir ../EVALUATION/run-NEW
```

Freeze creation re-runs eligibility and exits 2 without creating a run when any
prerequisite is missing. The current real CLI check does exactly that. Each
credited match gets its own deterministic gzip record and hash receipt. Receipts
advance a cumulative atomic checkpoint chain. An interruption replays the same
original seed and compares the entire record before credit. Rules and integrity
HALTs are preserved as exact diagnostic envelopes and block continuation. Final
JSON is written only after Týr revalidates exactly 10,000 unique record/receipt
pairs, 5,000 starts per deck, frozen hashes, terminal states and aggregate totals.

The two deterministic pilots remain Bot A (Jupitermon) and Bot B
(Amaterasumon/Toho). Judge labels are Justitia for runtime integrity, Dike for
independent rules review and Týr for final evidence audit.

Every preparation records the halt/restart policy: retain the exact seed and
trace, no replacement seeds, replay the original match after an infrastructure
interruption under identical frozen inputs, block unresolved rules HALTs, and
invalidate all final results/restart the whole schedule under a new freeze after
any frozen gameplay/input change. `workflow_policy.assess_resume` validates this
decision against the original 10,000-match schedule hash and checkpoint position.
Checkpoint storage and exact-seed resume are implemented by the runner; this
policy function remains the pure decision boundary they call.

`schedule_file_sha256` binds compressed bytes; `schedule_sha256` binds canonical
JSON and is the frozen `schedule` component checked by the resume policy.

An independent review file passed with `--review` is an external attestation;
the gate can validate its bindings, but cannot authenticate judge qualifications.
Never generate a favorable review file to bypass a blocked gate. Official
evidence and human/rules review must precede any certification claim.
