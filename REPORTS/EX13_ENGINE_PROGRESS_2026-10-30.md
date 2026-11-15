# EX13 engine foundation checkpoint — October 30, 2026

## User-authorized inputs

The uploaded workbook indexes 54 deck entries across 11 archetypes. It is not a
card-by-card composition workbook. All entries were retained in a random queue
of 1,431 distinct unordered pairs. Each entry appears 53 times in that queue.
The queue has its own saved random seed; it is not a final gameplay schedule.
The user selected **English-version worldwide rules** and confirmed that the
60-match/10,000-match requirements apply separately to each selected pairing.

First pairing: UlforceVeedramon/Federico Nine, DigiLab **123129**, versus
Gallantmon/RTA, DigiLab **124303**. Both exact source pages were retrieved and
provided 50 main cards and 4 Digi-Eggs. The original Gallantmon retrieval was
403; a subsequent request succeeded. No entry was substituted in the queue.

## Implemented software

- `SOURCE/match_context.py`: immutable card/deck definitions and exact per-seat
  composition identities. Card text, eggs, quantities, seats and rules selections
  participate in identity. No old matchup knowledge is imported.
- `SOURCE/context_runtime.py`: separate physical copies, deterministic undealt
  shuffling, stack/zone/card conservation, hidden-information views, terminal
  guards and transactional mechanic dispatch. It has no full-game phase loop,
  pilot, match credit or rules-certification path.
- `SOURCE/context_evolution.py`: printed normal/multicolor and selected
  special-name/trait evolution candidates. These are not complete action
  legality: payment, live information changes, prohibitions and effects remain
  separate. Unknown condition syntax cannot silently fall back to a normal route.
- `SOURCE/selected_mechanics.py`: exact-source EX13-023 orientation processing
  for closed scenarios, including optional processing and per-copy/per-turn
  usage. Unsupported inherited/Tamer reactions and DP/status rule-check
  dependencies halt before mutation. Pack status is EXPERIMENTAL_UNREVIEWED.
- `SOURCE/matchup_readiness.py`: executable input/source/printed-text inspection
  with explicit gameplay and review blockers. It cannot approve a freeze.

APP/catalog/import/storage code and the historical loaded-pair engine/gate were
not modified. No decklist was edited, no card recommendations were made, and
no older matchup pilot, roadmap or result was used for the new pair.

## Preserved evidence

`RULES/matchups/123129-vs-124303/` contains 45 official card pages, 99 extracted
Q&A entries, comprehensive rules v4.3, restrictions, errata, two exact deck source
pages and three official card images, all indexed with source hashes. Source
retrieval is not an independent rules review. Edition/effective-date pins still
need review before a verified rules lock can be claimed.

The official HTML labels LM-027, LM-028 and LM-034 as Digimon, but their inspected
official PNGs visibly say OPTION. The context uses the image value and preserves
both assertions, the image hashes and the field decision for independent review.

`ARTIFACTS/ex13-engine-2026-10-30/` contains the exact deck/context definitions,
the workbook index, random queue, readiness inventories and six compressed
orientation scenarios. The earlier region-unselected context and readiness
record are preserved historically; current context identity is:

`53f4e043b49fca0bf6e691754098e73774995cfee182e7c8245cf446e2d70733`

## Executed verification

Baseline: `python -m unittest discover -p 'test_*.py' -q` from SOURCE:
**148 passed**. After implementation and review fixes, the same full command:
**193 passed**, zero failures. Forty-five new tests cover identity/input
isolation, conservation, auditability, rollback, printed routes and scoped
orientation mechanics. New behavior tests were executed before their handlers
existed; review regressions reproduced the defects before fixes.

An independent code-review agent inspected all five new production modules and
their tests. It identified unexpected-player zones bypassing conservation and
unauditable choices being committed, plus minimal-HALT/result-alias issues.
The findings were reproduced in regression tests and fixed. A further regression
ensures a security effect cannot be dispatched from a battle source without a
security-check window. The final 193-test run passed after these fixes. No
second review or judge certification is claimed.

`python -m matchup_readiness --out ../ARTIFACTS/ex13-engine-2026-10-30/readiness-02.json`
was actually executed from SOURCE and exited **2 / BLOCKED**, as required.

Six saved scenarios executed with seeds 9001–9006: **3 experimental resolutions,
3 expected scope HALTs**, exact pre/post snapshots and action traces retained.
They contribute **0 full matches**. Scenario archive SHA-256:
`face493809553f5fb419f92fd5b3537dc764bd258953aa77299503a7254f1e98`.

## Current counts and remaining work

| Measure | Executed/current value |
|---|---:|
| Exact selected decks | 2, each 50 main + 4 eggs |
| Distinct official card definitions | 45 |
| Printed-text inventory units | 150 |
| Scoped experimental processing handlers | 1 |
| Remaining printed-text units without full handlers | 149 |
| Judge-certified mechanic packs | 0 |
| Full current-pair fact-finding attempts | 0 |
| Judge-valid fact-finding matches | 0/60 minimum |
| Approved best/medium/worst roadmap lanes | 0 |
| Frozen final evaluation matches | 0/10,000 |

Printed-text inventory units are not complete interaction branches or a claim
that only 149 engineering tasks remain. A keyword line can contain several
mechanics, and combinations require additional encountered-interaction review.

The overall user objective is **not complete**. Remaining implementation starts
with full context-bound phase/trigger/choice scheduling, attack/security timing,
the selected decks' search/draw/play/digivolution effects, X Antibody, orientation
reaction chains, replacements/preventions and Assembly as actually encountered.
No forced optional declines may be counted as learned strategy. Official source
comparisons and independent rules/branch review must accompany each handler.

Then produce a fresh balanced 60+ cohort; evaluate legal alternatives under
preregistered criteria; establish independently approved matchup-specific
best/medium/worst lanes; generalize the existing freeze/receipt runner to the
new context without weakening its gate; and actually play 10,000 matches with
5,000 starts per deck. A changed engine/context requires new evidence and a new
freeze. Preserve every halt and original seed.

## Implementation decisions

- Kept the historical simulator intact and added explicit context modules rather
  than monkey-patching its global manifests. This isolates old evidence at the
  cost of additional integration work before new full-game play.
- Used official images for the three conflicting type fields, recording the
  disagreement for review. An incorrect choice would invalidate the context;
  no certified result currently relies on it.
- Added printed candidate-route support during the foundation work because
  exact normal/special alternatives are a prerequisite for imported gameplay;
  these outputs deliberately make no full-action legality claim.
- Regraded the review's minimal-HALT and alias findings as integrity issues and
  fixed them alongside the important defects, with failing-then-passing tests.

No deferred code-review findings remain. The review was a software review,
not an official Digimon rules certificate.
