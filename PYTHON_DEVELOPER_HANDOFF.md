# Digimon simulator: Python developer handoff

Checkpoint: November 2, 2026. This document describes the engine track. Read
`AGENTS.md`, the newest section of `STATUS.md`, and `WORKFLOW.md` before editing.

Latest publication is a **work-in-progress checkpoint** per the user's instruction
to publish before usage runs out. Last full-suite result: **459 tests at713a513**.
Current BT11 Ulforce increment passes13 focused Tamer tests and independent actual
case checks; its full suite has not been run. Same original Game0000 reaches
**turn8 /104 commands**, exact replay, zero complete-match credit. Latest record:
`ARTIFACTS/gameplay-continuations-2026-11-03-07/game-0000-segment.json.gz`.
Next selected Rina AfterDraw evolution is B:BT22-023#1→B:EX13-023#1, cost1
(printed3−2), Bmemory2 in UNSUSPEND. Wire both actual WhenDigivolving effects
as a simultaneous group: orientation and return-all fewest sources. Current
sole minimum is A:BT12-029#2; do not invent an order for future multi-target
returns. Preserve the selected action, all earlier choices and source evidence.
No full games or strategic/final credits exist. See newest STATUS for limits.

## Goal and ownership

Build a turn-by-turn Digimon simulator for exact imported decklists. For each
selected pairing: complete at least 60 valid fact-finding matches with balanced
starts, evaluate best/medium/worst situational roadmaps, freeze the inputs and
bots, then actually play 10,000 evaluation matches (5,000 starts per deck).
The user wants randomized deck matchups across their EX13 workbook and has
chosen English-version worldwide rules. They have no coding experience.

Another chat owns the full card catalog, generic deck import, legality checks,
comparison/storage and Digimon-themed browser UI. This chat owns shared engine
procedures, selected-card mechanics, match evidence, bots, roadmaps and final
evaluation. Coordinate through the repository; do not replace the other chat's
catalog or UI work as part of an engine fix.

This is a simulation/results project. Do not alter decks, recommend cards or
slots, manufacture outcomes, or transfer another matchup's strategy/results.

## Current state: what works and what does not

- **459 Python unittest tests passed**, last full run444.077 seconds.
- Immutable exact card/deck contexts, physical accounting, transactional commands,
  deterministic seeds and source-bound failure/replay records work.
- Openings, phases/breeding, selected searches/plays/evolutions, Option Main/Delay,
  Rina/Aero grants, relevant attack triggers, ordinary Security battles and the
  encountered checked-Tamer play have experimental implementations.
- Active mirror registry has36 experimental bindings. This does not establish
  complete interaction coverage or judge certification.
- The preserved historical60-attempt mirror diagnostic has30 starts per deck,
  60 replays and60 HALTs. Gameplay-first work now continues those original traces;
  Game0000 is still unfinished at turn7 /94 commands.
- **Zero valid complete current-pair fact-finding matches, zero approved roadmap
  lanes and zero final matches. No usable win rate exists.**

Passing tests and deterministic replays are software evidence. Complete games,
independent rules review and strategic evidence remain separate requirements.
Historical legacy-engine completion counts do not apply to this context.

## Current exact decks and why this pairing

The user authorized choosing the starting matchup that best helps development.
The active development pairing is two different UlforceVeedramon lists:

| Seat | Workbook source ID | Listed player | Main / eggs |
|---|---|---|---|
| A |123129|Federico Nine|50 /4|
| B |122110|Bern|50 /4|

They use 22 distinct pinned cards versus 45 in the original Ulforce/Gallant pair.
Their composition hashes differ. This reduces the required card families; it
does not predict deck strength or guarantee a quick engine completion.

Active context: `ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json`.

Context ID:
`9dd326339d64f263c7570a33b03e4ab9d57c1cd466ec0fddffcec4d7ea5bcd8d`.

Deck A composition:
`f9c8261b83e908e13c6bf5770faf5809649543b5d3494081c8ec5eae8d7965c7`.

Deck B composition:
`50e14d9172891a00025b7708edabbc740cffac55d2e1ba3beb0f8f75c42998e7`.

Exact quantities and canonical definitions are in that directory's `deck-A.json`,
`deck-B.json`, and `context.json`. The workbook indexes 54 exact-list entries,
11 archetypes. The preserved random queue contains 1,431 distinct unordered
exact-list pairs; this mirror is entry 145. Selecting it first is a development
priority change; the original queue was not rewritten or called an evaluation.
It does not mean all 1,431 pairings are implemented or already scheduled to run.

The old development context is still supported for its prior basic capabilities:
123129 vs124303, ID
`53f4e043b49fca0bf6e691754098e73774995cfee182e7c8245cf446e2d70733`,
at `ARTIFACTS/ex13-engine-2026-10-30/context.json`. Its reports/seeds are preserved.
**The diagnostic CLI still defaults to that original context for compatibility.
Pass `--context-file` explicitly for the current mirror.**

## Start locally

Core engine/tests use Python's standard library. Python 3.12 is verified; no pip
packages are needed for these commands. Scratch video-analysis packages are not
engine dependencies and should not be installed to run the simulator.

```bash
git clone --branch engine-ulforce-bootstrap https://github.com/Tyskittl3z/digibattlesim.git
cd digibattlesim/SOURCE
python3 -m unittest discover -p 'test_*.py' -q
```

Inspect the active readiness inventory:

```bash
python3 matchup_readiness.py --context ../ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json
```

Expected: `BLOCKED`, process exit2. This currently reports unfinished gameplay
and evidence gates; it is not a claim the input decks are illegal.

Run a NEW diagnostic cohort, using an unused output directory:

```bash
python3 imported_attempts.py --context-file ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json --out ../ARTIFACTS/helper-diagnostic-01 --count 60 --max-commands 300
```

Here `--context-file` is relative to repository root; `--out` is relative to
your shell directory. Counts must be even and at least2. Output directories are
never overwritten. Command-budget exhaustion is a diagnostic stop, not a draw
or a valid completed game. The bots are fresh untrained uniform-random reference
policies; there is no trained AI or approved roadmap yet.

Read one saved attempt without launching another simulation:

```python
import gzip, json
from pathlib import Path
p = Path('../ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0000.json.gz')
record = json.loads(gzip.decompress(p.read_bytes()))
print(record['seed'], record['first'], record['halt_reason'])
print(record['commands'][-1])
```

From `SOURCE`, replay a record under its recorded context:

```python
from imported_attempts import replay_attempt
result = replay_attempt(record)
assert result['exact_match']
```

Exact replay requires the recorded engine, runner, sources and context bytes.
Runner bytes affect pilot identity and randomness; editing the runner changes
the pilots. The original records must be preserved when code changes.

## Code map and contracts

| File | Responsibility |
|---|---|
|`SOURCE/match_context.py`|Immutable CardDefinition/DeckDefinition/MatchContext, canonical hashes, exact inventory|
|`SOURCE/selected_contexts.py`|Pins the two permitted contexts, ordered source IDs and saved locks; a path alone grants no support|
|`SOURCE/context_runtime.py`|PhysicalCard, Stack, PhysicalState, transaction/rollback, snapshots, public views, source-bound dispatch and verification|
|`SOURCE/effect_scheduler.py`|Pending effects, source incarnation, controller choice, derived-trigger priority and cancellations|
|`SOURCE/printed_triggers.py`|Leading printed timing labels; a timing quoted in an effect body is not a trigger|
|`SOURCE/context_evolution.py`|Printed evolution-route parsing; unsupported conditions explicit|
|`SOURCE/match_preparation.py`|Initial hands and redraw choices|
|`SOURCE/phase_flow.py`|Turn phases, moving-trigger windows, experimental draw-deckout|
|`SOURCE/breeding_evolution.py`|Choose/pay/stack/draw for supported breeding evolution; ordinary battle effects suppressed there|
|`SOURCE/main_actions.py`|Ordinary hard play, exact cost, actual On Play scheduling|
|`SOURCE/search_effects.py`|Explicit reveal selection and bottom ordering for exact supported searches|
|`SOURCE/selected_mechanics.py`|Experimental orientation, inherited reactions, phase-memory bindings and official-byte checks|
|`SOURCE/battlefield_scope.py`|Conservative action-dependent board capability guards; many remaining stops originate here|
|`SOURCE/attack_flow.py`|Attack declaration, Counter, Block, confirmation, ending and narrow plain security handling|
|`SOURCE/turn_flow.py`|Explicit passing and turn change; unsupported durations/end effects still stop|
|`SOURCE/imported_attempts.py`|Fresh reference pilots, candidate generation, diagnostic loop, original records, replay and cohort writing|
|`SOURCE/matchup_readiness.py`|Context-byte parsing, readiness inventory and blocked-gate reporting|
|`SOURCE/frozen_evaluation.py`|Older pair's gated final-runner machinery; not integrated or eligible for this new context|

Physical identity is `owner:card_number#copy_index`. Stacks and deck arrays are
bottom-to-top; deck.pop() draws the top. For search bottom ordering, the first
specified key becomes bottommost. Stack `instance_id` protects against stale
effects after a card becomes a new entity. Every physical card must exist in
exactly one zone/stack; owner and memory bounds are checked.

Mutation goes through `_control_command` or `dispatch`, using trial state and
rollback on failure. Preserve seed, prior state, chosen input, error and trace.
Bots receive only public information, their own hand and explicitly revealed
choices; full snapshots/RNG/opponent hidden zones are audit data.

`run_attempt(..., context_file=...)` and `write_attempts(..., context_file=...)`
accept explicit inputs. Replay carries expected hash/identity into loading
before runtime construction. The input is parsed from the same immutable bytes
that are hashed; do not reintroduce a separate path read for parsing.

## Latest evidence and remaining first stops

Current cohort:
`ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/summary.json` and 60 original
`attempt-*.json.gz` files. Both version 01 and02 remain preserved. Version 02 has:

| First stop | Attempts |
|---|---:|
|Actual On Play processing|42|
|Option actions|8|
|Battle-area evolution|7|
|Stacked board capability|2|
|Security card capability|1|

On Play stops: BT11-112: 16, EX13-022: 12, BT22-023: 5, BT22-085: 5, EX13-023: 4.
These are counts of first stops, not counts of all defects or a strategy signal.
Options observed first include LM-028, LM-034, LM-056, LM-057 and P-104.
Other cards such as LM-058 remain in scope even when no seed reaches them first.

The security stop is EX13-023. `attack_flow._confirm` currently requires a small
blank-main whitelist before allowing a plain security Digimon battle. This is
a likely overbroad guard to inspect: unrelated main effects do not automatically
activate as security effects. Pin exact security wording/procedures and test the
case, while keeping actual unsupported Security effects explicit.

## Rules and sources: do not turn missing code into invented ambiguity

Execute card wording at its printed trigger. Clear wording needs implementation;
the comprehensive rules supply procedures/timing. A When Digivolving ability
does not by itself forbid normal hard play. An effect mentioned inside a body
does not acquire that trigger. Keep explicit player choices and per-effect
once-per-turn limits. Never silently skip a real active effect, hide an optional
choice through automatic decline, or replace a stopped seed with an easier seed.

Official rules/errata/Q&A and card wording are authoritative. Tests, narration
and deterministic replays are not rules certification. Sources currently live
largely under `RULES/matchups/123129-vs-124303/`: shared rules and overlapping
card definitions are deliberately reused with their original hashes. This does
not transfer the original pair's match results.

Key source files: `SOURCE_INDEX.json`, `CARD_QA.json`, official HTML/PNG sources
and comprehensive-rule PDF in that directory. Pinned comprehensive rules are
v4.3 dated 2026-09-18; PDF SHA256
`a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271`.
Region/language were selected, but complete final rules-lock/errata/restriction
review remains unfinished. Read metadata-review notes: LM-027/028/034 HTML type
conflicts are preserved with official OPTION images; X Antibody field extraction
is unreliable in the original pair; extracted Q&A can lose keyword angle tags.
Use raw official sources/images when extraction conflicts.

Eight user-provided transcripts, two reference decklists and 105 exact frame
samples are indexed under `ARTIFACTS/video-reference-2026-11-02/`. The 17-minute
240p SeitenGokuumon/Gammamon video was sampled, not reconstructed continuously.
The original six 720p uploads exceeded a 32MiB transfer limit and were not viewed.
Other game transcripts are references only, with recognition errors and different
deck compositions. They supply timestamped synthetic test ideas, not pilot data,
authoritative rulings or simulator match credit.

## Recommended contribution order

1. Pick a saved current-context HALT, reproduce its exact state/command, and
   identify the actual printed clause and shared procedure involved.
2. Check whether it is missing behavior or an overbroad guard. Add a meaningful
   regression that fails first; implement the smallest correct reusable
   procedure plus the selected card binding. Preserve genuine unsupported cases.
3. Prioritize encountered On Play effects, explicit Option resolution, battle
   evolution and supported stacks/status durations. These depend on shared
   choice/event infrastructure; do not hardcode a successful game script.
4. Verify own/opponent triggers, source incarnation, mandatory versus optional
   choices, per-effect limits, Counter windows, security, leave prevention and
   zero-DP rule checks. Run focused tests and the full suite.
5. Rerun the same current-context diagnostic seed indices under the changed
   engine into a new directory. Preserve old records and report actual stops.
6. Only complete reviewed matches count toward the 60+ gate. Close encountered
   branches, evaluate legal alternatives and build situation-specific roadmaps.
7. Integrate a new context-bound freeze/evaluation after readiness passes. Keep
   learning disabled during 10,000 actual matches and preserve every final HALT.

Roadmap GREEN/best, YELLOW/medium and RED/worst are strategic comparisons under
objective situations; RED is not the same as illegal. UNKNOWN is allowed.
Independent rules review and strategy evaluation are separate responsibilities.
No current lanes are approved. Another deck or changed list gets fresh pilots,
roadmaps and evidence; only generic verified mechanics are reusable.

## Recent checkpoints

- `881b9fc`: explicit-context/physical-runtime foundation, 193 tests.
- `24fee77`: scheduling/opening/search/breeding work, 247 tests.
- `ab099ed`: scoped live turns/attacks and diagnostics, 307 tests.
- `f0bb02f`: printed-trigger correction, 312 tests; 24 historical wrongly blocked
  ordinary plays replay successfully without unrelated effects firing.
- `5bae536`: source-indexed gameplay reference cases.
- `386dbfc`: distinct-list mirror snapshots and implementation design/plan.
- `43eace1`: dual-context integration, 333 tests and mirror diagnostic01.
- Current branch also contains the tested replay byte-binding fix, 335 tests and
  mirror diagnostic02. Use the branch HEAD for the complete handoff checkpoint.

Development branch: `engine-ulforce-bootstrap`. Publication is a draft PR for
review; this document does not claim a merge or a finished playable simulator.
Keep scratch `work/`, virtual environments, downloaded videos, credentials and
temporary packages out of commits. Core engine changes require no credentials.

Published review: https://github.com/Tyskittl3z/digibattlesim/pull/1 (draft, unmerged).
