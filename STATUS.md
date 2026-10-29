# Verified handoff status

## Frozen 10,000 runner software — 2026-10-29

The exact-pair final runner is now implemented behind the existing eligibility
gate. It binds all seven frozen components and the balanced 10,000-seed schedule,
writes deterministic per-match gzip evidence, advances an atomic checkpoint only
after full record validation, preserves rules HALTs, replays an infrastructure
orphan at the same seed, and forces a new freeze/full restart after any frozen
input changes. Final numerical JSON cannot be emitted before all 10,000 unique
records are revalidated.

The two pilots remain Bot A/Jupitermon and Bot B/Amaterasumon-Toho. The named
judge layers are **Justitia** (runtime integrity), **Dike** (independent rules)
and **Týr** (final evidence audit); the names appear in the app, freeze and saved
after-report. They do not merge software, rules or strategy authority.

Verified software checks currently total **148 Python tests**, **9 app-core
tests**, **1 app-build test** and **6 Chromium checks**. A real freeze CLI attempt
exited 2 before creating output because the current cohort/source is stale after
runner development and still contains 31 gameplay HALTs, optional unmodeled
effects, unpinned rules, missing reviews/coverage and unapproved roadmaps.
Final evaluation remains **0/10,000**; no win rate exists.

The required progression is explicit: first obtain 60 valid, full, independently
reviewed fact-finding matches; then approve evidence-backed GREEN/best,
YELLOW/medium and RED/worst routes; then freeze and run 10,000 matches with a
5,000/5,000 start split. Current attempts do not pass the first gate.

## Browser app — 2026-10-29

Open `APP/DeckCompare.html` directly in a modern browser. Drag/drop or paste two
decklists for immediate numerical comparison, then use **Save after-report** to
retain exact inputs, original file/text/composition hashes, full unfiltered
statistics/differences, data gaps and unavailable simulation fields. Reports are
readable offline HTML with complete JSON evidence embedded. The user explicitly
authorized general decklist intake/statistics; simulator gameplay support remains
limited to verified selected-matchup mechanics.

The interface uses Digimon TCG-inspired blue/orange card frames and a digital
playmat background. It runs locally without installation or external requests.
Bundled metadata covers 41 IDs; unknown cards retain their quantities and show
missing data. No unknown effects, egg classifications or costs are guessed.

**Head-to-head win rates are not operational.** The app reports unverified or
unsupported pairing status, matches played 0, and unavailable wins/losses/rates.
No historical matchup results/pilots are reused. Existing engine defects and
verification/frozen-runner work remain outstanding.

Verified app checks: 9 JavaScript core tests, 1 built-inline-script check,
6 Chromium interaction/download/mobile checks. Existing 128 Python engine tests
also pass. Browser checks used an internal static server because managed Chromium
blocks file URLs; the delivered HTML has no runtime server dependency. See
`APP/README.md` and `REPORTS/APP_VERIFICATION_2026-10-29.md`.

## Current workflow adjustments — 2026-10-29, version 02

The user's five requested adjustments are implemented in the requirements and
gate: official rules/format/edition/effective-date pins; minimum balanced 60
full matches plus encountered legal-branch coverage; separate rules and strategy
reviews; preregistered alternative/uncertainty lane criteria; and preserved HALT
seeds with a new freeze/full restart after any frozen gameplay/input change.
See `WORKFLOW.md` and `REPORTS/WORKFLOW_ADJUSTMENTS_2026-10-29.md`.

Verified: **128 tests passed**. Fresh diagnostic cohort
`ARTIFACTS/current-2026-10-29-02/`: **60 attempts, starts 30/30, 29 software
completions, 31 HALTs, 60 matching full evidence replays, 60 final physical-state
checks passed**. Judge-valid matches remain **0**; approved lanes **0**; final
matches played **0/10,000**. No card rule or decklist was changed by these workflow
adjustments. A balanced 62-record cohort is explicitly covered by gate tests.

`RULES/RULES_LOCK.json` and `RULES/INTERACTION_COVERAGE.json` remain explicitly
UNVERIFIED; missing format/region/language and official documents were not guessed.
`ROADMAPS/APPROVAL_CRITERIA.json` is preregistered and hashed before the new cohort.
Old roadmap files are preserved in `ROADMAPS/history/2026-10-29-01/`; current
roadmaps remain UNKNOWN-only. New preparation is
`EVALUATION/preparation-2026-10-29-02/`, explicitly BLOCKED_NOT_FROZEN.

The pure resume-policy validator checks the original 10,000-match schedule's
hash/balance/uniqueness, exact checkpoint position and original seed. It does not
implement the live final runner or checkpoint storage. Those, official rulings,
full rules review/branch coverage and actual strategy approval remain outstanding.

## Prior continuation — 2026-10-29, version 01 (historical)

Work is **blocked before judge-valid fact-finding and freeze**. The five original
Susanoomon interactions have exact reproducible state records but no verified
rule fix. Official rules access returned proxy CONNECT 403; the required
`world.digimoncard.com` domain addition and reusable startup instructions are
saved in the environment draft, awaiting review/save/publication.

| Current strict-run measurement | Verified value |
|---|---:|
| Unit tests | 111 passed |
| Diagnostic match attempts | 60 |
| A-first / B-first | 30 / 30 |
| Software-completed / HALT | 29 / 31 |
| Full deterministic replays matched | 60 |
| Judge-certified / valid fact-finding matches | 0 / 60 |
| Unmodeled optional attacking declines in current cohort | 20 |
| Approved GREEN / YELLOW / RED lanes | 0 / 0 / 0 |
| UNKNOWN situation groups A / B | 609 / 427 |
| Final evaluation played | 0 / 10,000 |
| Reserved final starts A / B, unplayed | 5,000 / 5,000 |

Current runner: `SOURCE/match_evidence.py`; cohort:
`ARTIFACTS/current-2026-10-29-01/`; report:
`REPORTS/CURRENT_VERIFICATION_2026-10-29.md`. Full source/deck/card-data and pilot
hashes are bound in the cohort's `provenance.json`.

The strict wrapper fixes ghost singleton stack registrations after opening-only
deletion helpers, detects exact physical-copy/stack errors, rejects unsupported
complex/status-bearing calls before mutation, and preserves complete states.
Its conservative helper-scope halts are not ILLEGAL rulings. Historical source,
decklists, tests and reports are retained for reproduction.

Baseline physical reaudit: **13/60** final states failed stronger invariants,
including **11/55** historical software completions. This prevents using the
old 55-completion number as proof of valid gameplay. The new halts reveal
previously unsupported paths; they are not evidence of worse deck performance.

Independent code review found and prompted regressions for status overwrites,
incomplete match schemas, empty/unbound official citations, actual training-seed
overlap, and malformed review inputs. Code review does not certify Digimon rules.

Remaining: apply official-site network access; verify/fix loaded interactions
with official citations and focused tests; resolve optional branches; rerun the
entire 60-match cohort after engine changes; independently review those matches;
evaluate and approve conditional roadmap lanes; then implement the atomic freeze,
learning-disabled final runner, compressed streaming and checkpoint/resume.
Current preparation is explicitly **BLOCKED_NOT_FROZEN**.

## Original handoff, preserved as historical context

**Snapshot:** JUPITERMON_TOHO_ATTACK_AUDIT_2026-10-19.zip, imported without older-matchup artifacts.

| Metric | Reported in supplied snapshot |
|---|---:|
| Seeded match attempts | 60 |
| A-first / B-first | 30 / 30 |
| Software-completed games | 55 |
| HALT games | 5 |
| Independently judge-certified matches | 0 |
| Approved strategic play lanes | 0 |
| Final evaluation | 0 / 10,000 |
| Reported unit tests | 78 / 78 |

**Revalidated for this Codex handoff:** The test command ran 78 tests, all passed. The 60-seed batch runner reproduced 55 software completions, five HALTs, and a 30/30 starting-player split.

**Outstanding HALT reasons from supplied report:**
- 1 × `SUSANOOMON_TARGET_LEAVE_REPLACEMENT_UNVERIFIED`
- 1 × `SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: BT26-029`
- 2 × `SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: P-213`
- 1 × `SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: BT24-101`

Historical `MATCH_LOGS` contain software audit events, not certified final results. Source version must be part of every subsequent report.

Next goal: complete and verify the five unresolved loaded-deck interactions, then rerun all 60 full fact-finding games.
