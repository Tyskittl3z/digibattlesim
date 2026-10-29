# Frozen 10,000-match evaluation design

## Intent

Make the final Jupitermon versus Amaterasumon/Toho evaluation executable as soon
as the existing rules, coverage, strategy and roadmap gate becomes eligible.
The runner must never turn a blocked preparation into results, replace a halted
seed, mix versions, or label a software replay as rules certification.

## Goals

- Create an atomic freeze from an eligible gate, the exact 10,000-entry balanced
  schedule and all seven frozen component hashes.
- Play every scheduled match turn by turn with the frozen pilot and learning
  disabled, writing one compressed, hash-bound record per scheduled position.
- Checkpoint after each credited match and resume only with the exact frozen
  inputs, schedule position and original seed.
- Stop on the first gameplay/rules HALT and preserve its record and seed.
- Produce numerical W/L, starting-player and turn summaries only after all
  10,000 scheduled records have passed identity, integrity and terminal checks.
- Preserve the two pilots as Bot A (Jupitermon) and Bot B
  (Amaterasumon/Toho). Label the three distinct audit layers Justitia (runtime
  integrity), Dike (independent rules) and Týr (final evidence audit).

## Non-goals

- This work does not resolve or certify card interactions.
- It does not manufacture rules, strategy or roadmap attestations.
- It does not run the current blocked final schedule or expose provisional win
  rates in the browser app.
- It does not add general deck or card-engine support.

## Constraints

- Exact loaded decks only. Deck files remain unchanged.
- Python standard library only.
- The current `assessment_eligibility` result is the sole freeze gate.
- A change to engine, rules/format, decks, pilots, criteria, roadmaps or schedule
  requires a new freeze and a restart at schedule position zero.
- Infrastructure recovery replays the original match and verifies the exact
  record before credit. A rules HALT cannot be resumed under the same freeze.
- Every file written by the runner uses a temporary sibling, flush, fsync and
  atomic replace. Existing unrelated artifacts are never overwritten.

## Approaches

Three storage approaches were considered. A single gzip JSONL stream is compact
but hard to repair atomically after interruption. Chunked streams reduce file
count but make mid-chunk recovery and per-match proof more complicated. One gzip
file per match gives direct seed/hash identity, simple replay and an exact atomic
checkpoint at the cost of 10,000 small files. The per-match approach is selected
because evidence integrity matters more than directory compactness for this
fixed-size evaluation.

The runner remains a Python CLI beside the existing gate. The browser app stays
offline and imports only a completed, validated summary later; it will not call
an unverified simulator or a hidden service.

## Components

- `SOURCE/frozen_evaluation.py`: freeze creation, frozen-input validation,
  atomic writes, exact-schedule runner, resume and final summary.
- `SOURCE/test_frozen_evaluation.py`: gate rejection, balanced schedule binding,
  match record identity, atomic checkpoint, halt preservation, interruption
  replay, changed-freeze rejection and complete numerical summary tests.
- `EVALUATION/README.md`: exact operator contract and status distinction.
- The browser simulation panel and saved after-report carry the same bot and
  judge labels; the names are presentation, while their responsibilities and
  evidence boundaries remain unchanged.

## Remaining external path

The runner can be software-complete while the current evaluation remains
blocked. Starting the real 10,000 requires retrieved official source snapshots,
the selected format/region/language, resolved loaded-card interactions, a fresh
balanced cohort, independent rules review, complete branch coverage, approved
roadmaps and a separate strategy review.
