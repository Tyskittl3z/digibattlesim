# Current verified development progress — 2026-10-29

**BLOCKED before judge-valid fact-finding, strategic lane approval, and freeze.**
No official interaction fix, judge certificate, or final match result is claimed.

| Measurement | Tool-verified value |
|---|---:|
| Unit tests | 111 passed, 0 failed |
| Current diagnostic match attempts | 60 |
| Starting player A / B | 30 / 30 |
| SOFTWARE_COMPLETED / HALT | 29 / 31 |
| Full evidence replays matched | 60 / 60 |
| Final physical-card/stack checks | 60 / 60 passed |
| Judge-certified valid fact-finding matches | 0 / 60 |
| Unmodeled optional attack declines | 20 |
| Approved GREEN / YELLOW / RED lanes | 0 / 0 / 0 |
| UNKNOWN situation groups, A / B | 609 / 427 |
| Final evaluation actually played | 0 / 10,000 |
| Reserved final starts, A / B, unplayed | 5,000 / 5,000 |

Certified W/L, rates, combos, and lane outcomes are **unavailable**, not zero.
Diagnostic turn distributions, paid-play frequencies, and decision counts are
in the accompanying JSON and must not be interpreted as validated matchup results.

## Verified software changes

- Imported all 103 original files byte-for-byte and verified every supplied
  checksum. Preserved the baseline as local commit `8579e0c`; no remote push.
- Reproduced the original 55 software completions / five halts and all five
  exact Susanoomon halt states. Saved full zones, stacks, active text, memory,
  once-per-turn state, pending queues, RNG state, seed, and trace tails.
- Found that the old total-count invariant permitted orphan stack registrations.
  A baseline reaudit failed 13 final states, including 11 of the 55 apparent
  software completions. Historical completions cannot establish valid matches.
- Added the strict current `EvidenceMatch` wrapper, preserving historical source
  and tests. It validates exact physical copies, stack anchors, memory bounds,
  and terminal-event boundaries. It clears singleton stack registrations after
  deletion and rejects unsafe opening-helper calls before zone mutation.
- Streamed 60 compressed current records, each bound to source/deck/card-data
  provenance, initial/final full state, transcript, and deterministic replay.
  Decision records include public board context and the acting player's hand.
- Added a fail-closed evaluation gate, UNKNOWN-only situational roadmap indexes,
  and a disjoint balanced unplayed final seed schedule.

## Current halts and unresolved rules

| Current first-halt category | Count |
|---|---:|
| PREFIX_HANDLER_STACK_UNSUPPORTED | 26 |
| PREFIX_HANDLER_REPLACEMENT_UNVERIFIED | 2 |
| PREFIX_HANDLER_STATUS_UNSUPPORTED | 1 |
| SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED | 2 |

The prefix halts enforce a helper's single-card opening-board scope. They are
conservative software barriers, **not ILLEGAL rulings**. More early halts prevent
some seeds from reaching the original Susanoomon windows. All five original
Susanoomon cases remain unresolved and preserved independently.

Current unmodeled optional attacking declines: BT26-016 **4**, EX12-065 **12**,
EX12-036 **4**. Legal activate/decline alternatives and nested responses have
not been fully adjudicated or evaluated. No forced decline is learned strategy.

Official rules/card-Q&A access returned **proxy CONNECT 403**. The bundled
manifest has official catalog URLs but marks its contents `UNVERIFIED`.
No guessed Decode/protection/timing rule was substituted to clear the halts.
Exact cases and required evidence are in `RULES/REVIEW_REQUIRED.md`.

## Roadmaps and final preparation

The two roadmap files contain 1,036 UNKNOWN indexing conditions with 2,463 trace
references. There are no approved legal strategic lanes or ILLEGAL rulings.
Conditions group decision kind/source, security counts, memory and active player;
they are not sufficient strategy rules or completed alternative-branch studies.

The actual CLI gate exited **2 / BLOCKED**, with 31 match-halt blockers plus
unmodeled optional attacks, missing independent judge review, and unapproved
roadmaps. It found no stale-source, schema, physical-state, or hash errors in
the current recorded evidence.

`EVALUATION/preparation-2026-10-29-01/` contains **BLOCKED_NOT_FROZEN** preparation
and 10,000 unique reserved seeds, 5,000 starts per seat, disjoint from training.
There is no freeze hash and no final results file. The actual frozen runner,
learning/exploration lock, compressed final streaming and checkpoint/resume
implementation remain behind the eligibility gate.

## Verification and provenance

From `SOURCE/`:

```bash
python -m unittest discover -p 'test_*.py' -q
python -m match_evidence --out ../ARTIFACTS/current-2026-10-29-01 --count 60
python -m evaluation_gate --cohort ../ARTIFACTS/current-2026-10-29-01 --candidate-roadmaps --prepare ../EVALUATION/preparation-2026-10-29-01
```

The recorded output directories now exist; use new versioned directories for
future runs. Preserve/version both roadmap files before regeneration.

- Source/input bundle SHA-256: `4f28b284ca81a0a0d5241fe5c194feae85da16758b9278ad2f40ddbdd31dc835`
- Provenance SHA-256: `bb5e638a3ccadb2f0ae623c116e305e3a10b55680adf269014c37734575b4ae0`
- Cohort manifest SHA-256: `fe84cefd32e6a85d228640002496feb21a51adff4f898a4a303201fda0a67204`

A fresh code reviewer identified status-overwrite, incomplete evidence schema,
empty/unbound official-citation, and actual-training-seed overlap defects. Each
received a failing regression and fix; malformed review objects also now return
structured blockers. The final suite passed 111 tests. This software review is
not a Digimon rules certification. Review attestation authenticity/qualifications
cannot be established by parsing a JSON file.

## Required next action and remaining development

The environment draft now contains the additive `world.digimoncard.com` domain
and reusable `start_skill`. **Review/save these changes in environment settings,
then publish the environment** to activate them. Saving the draft did not change
the running policy or publish a snapshot. No install script is needed: Python
3.11+ and the standard library suffice.

After official access works: retrieve/hash the exact rules and card rulings;
fix the five original interactions and additional encountered loaded-deck
branches with targeted tests; fully evaluate optional alternatives; rerun all
60 matches after engine changes; independently judge-review every complete
transcript; approve evidence-backed conditional roadmaps; then implement and
verify the frozen 10,000-match evaluation and safe resume behavior.
