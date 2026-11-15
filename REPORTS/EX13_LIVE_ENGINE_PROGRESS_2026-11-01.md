# EX13 live-engine continuation — November 1, 2026

## Actual current status

First selected pair remains UlforceVeedramon/Federico Nine (123129) versus
Gallantmon/RTA (124303), English-version worldwide rules. Inputs and decks are
unchanged. The paused batch was reverified at 247 tests and preserved in commit
24fee77 before this continuation.

Current complete test suite: **307 tests passed**, zero failures, executed from
SOURCE with `python -m unittest discover -p 'test_*.py' -q` (41.489 seconds).
There are **14 experimental exact-text mechanic bindings**, plus the new core
turn/attack primitives. These are software capabilities, not judge certificates.

Two balanced diagnostic cohorts were actually executed on **the same 60 seeds**
with the same fresh reference-pilot identities under two engine versions. Every
record retains exact inputs, engine/policy identity, original seed, decisions,
full states, events and HALTs. Both cohorts replayed **60/60 byte-equivalent
canonical records**. There were no replacement seeds.

| Actual measure | Version 01 | Version 02 |
|---|---:|---:|
| Attempted seeds | 60 | 60 |
| A-first / B-first | 30 / 30 | 30 / 30 |
| Complete deterministic replays | 60 | 60 |
| HALTs | 60 | 60 |
| Software terminal games | 0 | 0 |
| Accepted/judge-valid fact-finding matches | 0 | 0 |
| Final evaluation credit | 0 | 0 |
| Recorded command attempts | 764 | 827 |
| Highest reached turn index | 4 | 5 |

These are **120 versioned attempt records for 60 original seeds**, not 120
independent matches and not the required 60 completed fact-finding games.

## Implemented continuation

- `turn_flow.py`: explicit pass sets opponent memory to three, opens the end
  window, waits for pending processing, resumes main phase if memory returns,
  or switches seats/sign/turn and resets OPT only on actual turn change.
  Unimplemented end triggers and duration-bearing statuses halt.
- `battlefield_scope.py`: exact selected-context and official-source capability
  checks for inert singleton boards. Initially three blank-main cards; actual
  diagnostics exposed 21 barriers on five supported search Digimon. Reviewed
  those five full main texts and safely added them between their self triggers.
  Inherited effects are inactive on singleton tops under rule 15-3-1. Every
  other card, exposed inherited stack, status and unknown field remains explicit.
- `attack_flow.py`: declaration, explicit defender Counter and Block decisions,
  success confirmation and end-of-attack windows. Tracks entity identity and
  played/ready history. Handles verified basic field battles, simultaneous ties,
  the three plain security Digimon, last-security nonvictory, successful direct
  attack, attacker/target loss and terminal guards. Unknown Counter activation,
  security cards, keywords and live effects halt; declines remain explicit
  untrained decisions. Security whitelist was not expanded by the board change.
- Core state records attack, winner/reason and ready-since provenance. Other main
  actions cannot bypass an open attack. End-of-turn conditions wait for pending
  effects and complete attack processing. Terminal actions cannot continue.
- Existing main play and breeding evolution now accept the reviewed inert board
  capability. Promotion records attack-readiness provenance. Draw-phase deckout
  records an experimental terminal without advancing to breeding.
- Added exact EX13-017 and EX8-009 searches. EX13-017 moving search resolves in
  `BREEDING_MOVING_EFFECTS` before main phase and Start-of-Main effects begin.
  Text matching uses only official printed information; exact X Antibody naming
  excludes Proto Form from the exact-name slot. EX13-017 ruling is Q7255.
- `imported_attempts.py`: fresh seeded random reference pilots use only public
  views, their own hands and explicit reveals. Unknown payable cards, Options
  and printed battle-evolution routes remain candidates; software support does
  not silently remove them. Choice legality/coverage is not certified. Original
  records are saved before replay, and replay mismatch/interruption retains the
  original trace plus a failure receipt and stops.

## Evidence-driven change and remaining blockers

Version 01 stopped on: 32 unsupported play capabilities, 21 search-top scope
barriers, six unknown Option actions and one stacked board. The five encountered
search tops have main effects only on their own play/digivolution/move, and their
other reactions are inherited-only. Independent software review supported that
limited scope extension. The same-seed version 02 has no search-top scope HALTs.

Version 02 still stops on:

| Blocker group | Attempts |
|---|---:|
| Unsupported play capability | 43 |
| Unimplemented Option legality/effects | 11 |
| Unimplemented battle-area digivolution | 4 |
| Unsupported stacked battlefield | 2 |

These are engine-scope barriers, not rulings that those cards/actions are
illegal. Some rejected plays have no On Play effect; their broader capability
has not yet been implemented. Do not describe all 43 as unresolved On Play
effects. No win rate or strategic lane follows from halted attempts.

The largest individual play barrier in this cohort is EX13-019 (7), followed by
BT22-023 (5) and BT19-011 (4). These numbers prioritize engineering investigation
only; they are not card or deck-building recommendations.

Next implementation: selected play capabilities and their relevant triggers,
full battle evolution with inherited-state preservation and reactions, Option
color/cost/processing including Delay, then stacked/modified attack and security
interactions. Re-run the entire original-seed cohort after engine changes.
An actual balanced 60+ full reviewed cohort, branch coverage, strategy evidence,
approved roadmaps and a fresh eligible freeze remain required before 10,000.

## Verification and independent review

Tests were observed failing before new implementation and before review fixes.
Core review found future/contradictory placement history could permit an attack;
regressions reproduce and reject it before suspension or terminal results.
Runner review found replay ran before original evidence persistence; mismatch
and interruption regressions now prove original records and failure receipts
survive, with later seeds unplayed. Both fix passes were followed by passing
focused tests and a passing full suite.

A separate review of the five search-top capability additions found no
Important/Critical defect and passed all 27 focused scope/attack tests. These
were software/evidence reviews, not independent Digimon judge certification.
Stale scope documentation was corrected before the final cohort.

## Saved artifacts

- `ARTIFACTS/imported-diagnostic-2026-11-01-01/`: original 60 attempts/replays.
- `ARTIFACTS/imported-diagnostic-2026-11-01-02/`: same seeds/pilots, changed engine,
  current 60 attempts/replays and exact per-card blockers.
- `ARTIFACTS/ex13-engine-2026-10-30/readiness-04.json`: actual CLI exit 2/BLOCKED;
  14 bindings, 136 printed-text units without a full handler. A printed-text
  inventory is not complete interaction coverage or a percentage of completion.
- `RULES/matchups/123129-vs-124303/METADATA_REVIEW_NOTES.json`: X Antibody
  field-layout issue and potential angle-bracket keyword loss in extracted Q&A.
  Raw pinned official sources remain authority; unsupported behavior was not
  substituted. Catalog verification belongs to the other chat's track.

No card quantities, pilots from older matchups, historical roadmaps, browser UI,
or catalog/import code were changed or reused. Judge-valid matches remain
**0/60**, approved strategic lanes **0**, final evaluation **0/10,000**.
