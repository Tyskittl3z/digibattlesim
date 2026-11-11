# Digimon simulator: Python developer handoff

## Live Game 0000 checkpoint — 2026-11-11

The first fresh game is active with locked seed 4851742998504393566, A first,
aggressive Bot A, defensive Bot B, and Bot C. `ARTIFACTS/fresh-game-0000-2026-11-11/`
contains the lock, cumulative gzipped action/state/RNG/decision/judge/tracker
segments, exact replay receipts and the bounded continuation scripts. Latest
segment 0019 has 156 accepted commands and a HALT at A's attack confirmation
against B's Blocker; the inherited Jamming fix has a focused passing test and
still needs migration/retry. Earlier engine gaps were repaired via exact-prefix source
migrations; inspect each embedded `repair_lineage` before changing an action.
The separate `game-0000-audit-failure-0006.json.gz` records a rejected Bot C
status audit and has no training/rating credit. The historical 164-command
mixed-policy record remains excluded. No completed fresh game or cohort credit
exists yet. Continue this one game only; 60 and 10,000 matches remain off.

The repair surface now includes Bot C's narrowly reviewed Jamming/own-turn
grant schema. A one-time hash-gated migration-tool extension rebounded Bot C's
source identity while proving all prior observations, choices, state and
outcomes unchanged. Exact replay verifies the current checkpoint, but these
checks remain experimental software evidence, not independent rules approval.

## Engine repair migration checkpoint — 2026-11-10

The earlier same-build-only limitation now has an explicit verified engine-repair
path for fresh-runner records. This is setup work: actual games/cohorts remain
paused. The old mixed-policy 164-command record is unchanged and is not an input
to fresh training or this fresh-schema migration.

### API and provenance

`SOURCE/fresh_repair_migration.py` exposes:

```python
migrate_repaired_game(record, *, root, original_source_root,
                     approved_changes, repair_note)
verify_repair_lineage(record, root)
```

`approved_changes` maps exact source basenames to `{before: hash_or_none,
after: hash_or_none}`. It must be supplied from a reviewed patch, not inferred
and automatically approved from whatever changed. Preserve a full original
SOURCE tree and matching rules/context/non-Python source assets. The Python
archives plus manifests supply exact source bytes; retain the associated input
files too. The API verifies original sources and their original replay in a
separate source-only interpreter, then replays successes under current verified
source. No failed command is applied by migration, no LearningPlayerBot actor
is constructed, and no choice or model update occurs.

The returned record retains its failed selection, arguments, decisions and
post-choice policy RNG. It embeds the complete parent in `repair_lineage` with
source/dependency maps, original replay receipt, exact differences, checkpoint/
RNG/selection hashes, execution identities and experimental zero-credit limits.
Only documented execution/binding source stamps and dependent receipt/observer
hashes are rebound. Full state, outcomes, views, choices, ratings and policy
identities must agree. Ordinary replay verifies lineage; later continuation
retains it, including a second engine-only repair.

Both sides load `.py` bytes directly, bypassing cached bytecode and already
imported modules. The source-only finder remains active for dynamic handler
imports. `run_game`/`replay_game` delegate migrated records to the same verified
worker; ordinary nonmigrated behavior and strict source pins remain unchanged.
Worker guards forbid actor/choice calls during migration/replay. A one-command
retry of a fully selected failed direct action forbids new choices inside the
worker. Partially generated pending choices retain their saved order/values;
only unresolved values may require a later decision. Caller and worker each
verify that the learning model stays frozen. Parent-process mocks do not control
these workers and must not be represented as doing so.

Migration permits only the declared existing engine files. Policies, scorer,
judge, tracker, context and learning infrastructure are protected. A pinned
bootstrap recognizes the published pre-lineage runner; later framework changes
need separately versioned support. Rules/context/source-asset bytes must agree.
Terminal and post-commit audit-failure records, changed earlier results, and
unlisted differences fail. UNKNOWN aliases are never silently remapped. These
are content-addressed software checks, not independent signatures or semantic
rules certification.

### Verification and delivery

Final command from `SOURCE/`:

```sh
python -m unittest test_fresh_repair_migration test_fresh_learning_campaign test_field_tracker test_interaction_scoring test_interaction_learning test_judge_ledger test_named_player_bots test_context_runtime test_match_context test_match_preparation -q
```

**173 tests passed in 73.877 seconds:** 18 migration plus the existing 155 focused
integration checks. Real distinct on-disk builds cover direct and pending saved
retries, mechanic binding/receipt/observer-chain rebinding, repeated repairs,
changed outcomes/dependencies/protected files, and deeply rehashed lineage
tampering. Independent review found a repaired-cache defect; three RED tests
reproduced it before the source-worker fix, and scoped review confirmed the
original reproduction now rejects both cached and uncached changed prefixes.
Dynamic handler cache and already imported module cases are covered too.

`ARTIFACTS/repair-migration-2026-11-10/` contains a separate 4.920-second private
proof, separately pinned exact three-file repair map, original gap source and
current 114-file archives, stopped/migrated/retried logs, exact replay receipts,
review summary, verification and current disabled-run control. The fixture's
deliberate engine gap exists only in its archived old source. Its exact selected
redraw was retried once with no reselection. Model, original parent, source bytes
and historical production record remained unchanged. This earns zero production
training or match credit. Full discovery remains excluded during the pause
because it includes legacy gameplay/cohort tests; full historical baseline is
still 495 at aed966b.

Keep the first actual fresh game paused until user continuation of gameplay.
Once authorized, use the explicit active Ulforce context and named A/B profiles,
record each encountered action and halt, and repair only that encounter. Do not
preload routes, silently skip effects or start the 60/10,000 cohorts as part of
this setup checkpoint. Publish via `engine-ulforce-bootstrap`, draft PR #1.

## Current integration checkpoint — 2026-11-10

The fresh runner now connects named Bot A aggressive/B defensive, Bot C's
redacted views, board/tempo scoring, automated judge receipts and persistent
learning. **Actual matches remain paused.** No production campaign, deal,
training update or live rating has run. Test fixtures and historical prefixes
count as zero completed fact-finding/final matches. Older sections below are
historical where they describe these modules as pending.

### Source and APIs

- `SOURCE/field_tracker.py`: `FieldTracker.start/observe/player_view/public_metrics`.
  Private audit data is for verification, never a player/learner feature.
- `SOURCE/interaction_scoring.py`: `score_transition(...)` and
  `criteria_manifest()`. Provisional board-impact weights are pinned in
  `RULES/learning-2026-11-10/INTERACTION_CRITERIA.json`; canonical criterion SHA
  is `84de51952609311beadcbec58f9c8252e1aea2c9eae96689eaf5aad4711fcdaf`.
  Actual procedural changes retain measured colors but are ineligible for
  learning; failed/unresolved commands are UNRATED. Tempo reports separate
  cards/stack/check axes, including CONTESTED or UNKNOWN when appropriate.
- `SOURCE/judge_ledger.py`: `judge_action(..., tracker=tracker)` requires
  Bot C's anchored predecessor state, live engine events, action/effect binding,
  physical conservation and pinned official sources. Accepted receipts mean
  RUNTIME_VALIDATED, with EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED status;
  independent semantic certification is false. Software gaps are not automatic
  illegal/RED judgments.
- `SOURCE/interaction_learning.py`: `LearningState.export/from_dict/state_id`,
  `update_completed(...)`, `LearningPlayerBot(...)`, and pure saved-decision
  input/RNG verification. Model snapshots freeze within a game. Completed-game
  updates are atomic and deduplicated by logical game identity; action evidence
  counts once per game. Three independent games are required for learned
  preferences; explicit exploration is 0.10. Win association is separate from
  the primary observed-board reward. No historical training is loaded.
- `SOURCE/fresh_learning_campaign.py`: `make_schedule(context_id,campaign_id)`,
  `run_game(index, root, *, context_file, campaign_id, learning_state,
  max_commands=2000, previous_record=None)`, `replay_game(record, root)` and
  `commit_completed_game(record, learning_state, root)`. The last function is
  the explicit between-game update path; it rejects incomplete games. There is
  no automatic cohort launcher in this increment. Do not invoke production
  gameplay while the pause remains active.

The runner pins source/context/criteria/model/player identities, saves engine
and policy RNG plus selected commands/pending choices, and replays stored
commands without invoking player choice again. Audit failure preserves changed
state with an explicit failure status. **Resume supports identical builds only.**
Any on-disk engine repair changes source pins and currently rejects the old
record. Implement an explicit, verified repair-migration lineage before claiming
same-seed resumption across repairs; preserve the original record and selected
action. Tests mocking runtime availability do not prove cross-build migration.

### Verification and evidence

From `SOURCE/`, the final combined command was:

```sh
python -m unittest test_interaction_scoring test_interaction_learning test_judge_ledger test_fresh_learning_campaign test_field_tracker test_named_player_bots test_context_runtime test_match_context test_match_preparation -q
```

Result: **155 tests passed in 35.346 seconds** (21 scorer, 32 learner, 8 judge,
20 runner, 30 tracker, 13 named-player, 18 runtime, 8 context, 5 preparation).
Independent component review also passed. This is a focused run, not the full
suite: discovery includes legacy gameplay/cohort tests and was not run during
the pause. Latest complete historical baseline remains 495 tests at aed966b.

`ARTIFACTS/learning-integration-2026-11-10/` contains the exact 112-file source
archive/manifest, criterion manifest, private opening and resumed fixture,
replay reports, verification and current pause control. The extra private proof
used five commands only: opening, named redraw choices and automatic phase
transitions. It proves saved choices/RNG and exact replay, unchanged model,
rejection of a paused-game training commit, and unchanged historical game bytes.
It uses no random reference player and earns zero production evidence credit.

Next development gap is verified repair migration, followed by gameplay-first
repairs of only encountered selected-card behavior once the user resumes.
Keep production games and the 60/10,000 cohorts off until the pause is lifted;
do not preload routes or claim complete rules/interaction coverage. Continue
publishing honest checkpoints on `engine-ulforce-bootstrap` and draft PR #1.

## Bot C verified; matches remain paused — 2026-11-10

User authorized Bot C only. **SOURCE/field_tracker.py is implemented**, with 30
tracker regression tests and 74 focused tracker/runtime/context/preparation/player
checks passing (3.935 seconds). Independent privacy/integrity review passed 30 tests
(3.496 seconds), with no blocking findings. Existing engine and player-policy files are
unchanged; only the tracker and its tests were added to live SOURCE.

Bot C validates physical conservation, tracks zones, breeding, battle entities,
stack sources, orientation/statuses, memory/phase/pending state and completed
successful Security checks. It supplies exact redacted player views and public
body/stack/check totals; private audit data stays separate. Known public status
schemas are enforced, invalid counter claims rejected, and observations are
source-bound and hash-chained. It observes net changes at command boundaries;
it does not reconstruct unrecorded intermediate movements, resolve cards, rate
strategy or detect every indistinguishable no-op without an external index.

Read-only verification of all 164 stored commands passed in 38.204 seconds: exact saved
results/events/state/RNG, both player views and deterministic observer ledger,
all 108 cards conserved. It reconstructed A 0/B 4 completed checks from that old
log. No player policy was called, no new command was chosen, and old record
bytes remained unchanged. This proof earns zero new match/training credit.

Evidence/source archive:
`ARTIFACTS/bot-c-2026-11-10/`. All 104 Python sources match the archive; all 102
previous source files match 220afab. No new full suite was run because it includes
legacy match/cohort tests; latest complete baseline remains 495 at aed966b.

**PAUSED_BEFORE_FIRST_MATCH remains active:** zero fresh games/deals, learning
updates or strategic ratings. Bot C is a verified standalone component; fresh
runner integration, learning/scoring and judge-ledger implementation remain
pending. Read the new pause-control.json before future work. Do not start an
actual match/cohort until the user says to continue. The old 164-command game
remains archived and excluded from fresh learning.


## Fresh learning setup paused before first match — 2026-11-05

The user requested starting over with aggressive Bot A, defensive Bot B, Bot C
as field tracker, judge checks, board-impact GREEN/YELLOW/RED labels and learning
across60 fresh games. The user then said **pause before starting the match**.
The later usage reset does not lift that pause. **No fresh match/opening deal
has started; no learning update or rating has been produced.** No schedule is
locked or executing.10,000 final evaluation remains off.

Colors are to reflect removed/incapacitated cards, successful Security checks,
battle-area development and actual memory efficiency. Tempo must track cards
in play, stack sizes and cumulative completed successful Security checks.
Declarations do not count as completed checks. Weights remain draft/unlocked;
no probabilities, globally-cheapest claims or approved roadmaps are implied.

Prepared only: design/plan,16 tracker test drafts,7 fresh-runner test drafts,
and learning/API handoff notes. The two initial TDD checks failed as expected
because the implementation modules are absent; no passing claim is made for
this setup. Draft tests are parked under
`ARTIFACTS/pre-match-setup-2026-11-05/prepared-source/SOURCE/` so the live source
remains unchanged from220afab. Last verified focused set:82 tests at220afab;
latest complete full suite:495 at aed966b. No new game/test run was launched
to save this pause checkpoint.

Read `ARTIFACTS/pre-match-setup-2026-11-05/pause-control.json` and README before
resuming preparation. Tracker, learning/scoring, fresh runner and judge ledger
implementations/integration remain pending. Keep old164-command game archived
and exclude it from fresh training. **Do not start or advance any actual match
until the user says to continue.** Save/publish progress without lifting pause.


Checkpoint: November 4, 2026. Read AGENTS.md and the newest STATUS section.

## Named Bot A/B connected — 2026-11-04

The user confirmed project Bot A/B, one aggressive and one defensive. The
implemented assignment is **A aggressive / B defensive**, as stated in
commentary. Legacy code used shared decision logic, so fresh, explicit,
untrained profiles now use current public views, own hand, explicit reveals
and printed definitions. No old-matchup weights, routes, roadmaps or outcomes
were imported. Bot identities bind the context, style, configuration and source.

| Seat | Style | Bot ID prefix |
|---|---|---|
| A | AGGRESSIVE |3051db093e356d30|
| B | DEFENSIVE |6fe75b159762009e|

The bounded named-bot runner continued the **same Game0000** from the saved152
successful commands. **12 new commands resolved**, producing **164 successes**,
Aturn11, MAIN, memory2. The original seed12017913134550805276, firstA, earlier
commands/choices/results and complete prior state/RNG were revalidated. The
original random-policy manifests remain unchanged; active named policies are
separate.11 new policy calls are recorded (A9/B2, including effect ordering).
B restored BT11Rina#2; A hatched and declared BT11Ulforce's attack on PLAYER.
No Security damage has resolved in this new attack.

**82 focused tests pass** (57.599s). Independent profile13 tests (0.123s) and
runner7 tests (30.341s) pass. Exact whole-record replay passes. Source archive
matches102 Python files; the rules engine itself is unchanged. Latest full-suite
baseline remains495 at aed966b; legacy cohort tests were not run this increment.
The named policies are declared heuristic preferences, not learned strategy or
outcome ratings. Whole mixed-history game/bot, fact-finding and final credits0;
no cohorts, route preloading or outcome ratings.

Latest record and readable trace:
`ARTIFACTS/gameplay-continuations-2026-11-04-02/`. See bot-roster.json,
bot-decisions.json, replay.json and the frozen source archive. Status is
PAUSED_AFTER_NAMED_BOT_SEGMENT, not a software/rules halt or a completed game.

Next actual pending effect is **effect64 BT11-032.play_blue_tamer**, A, source
A:BT11-032#1, depth1, queued by A's second paid Rina reactivation. Older effect60
EX13Aero inherited unsuspend remains depth0. Resolve pending effects before the
attack's Counter window can be used. Continue from this checkpoint with
`named_bot_continuation.continue_with_named_bots`, never the random runner.
Preserve any actually selected unsupported action and repair that encounter.

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

- **82 current focused tests passed** (57.599s). Latest full suite:495 tests
  at aed966b (556.480s); no new full run or legacy cohort tests this increment.
- Immutable exact card/deck contexts, physical accounting, transactional commands,
  deterministic seeds and source-bound failure/replay records work.
- Openings, phases/breeding, selected searches/plays/evolutions, Option Main/Delay,
  Rina/Aero grants, relevant attack triggers, ordinary Security battles and the
  encountered checked-Tamer play have experimental implementations.
- Active mirror registry has40 experimental bindings. This does not establish
  complete interaction coverage or judge certification.
- The preserved historical60-attempt mirror diagnostic has30 starts per deck,
  60 replays and60 HALTs. Gameplay-first work now continues those original traces;
  Game0000 is paused after a named-bot segment at turn11 /164 successful
  commands, A MAINmemory2, with attack-trigger effects still pending.
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
python3 -m unittest test_named_player_bots test_named_bot_continuation test_recorded_action_checkpoint test_context_runtime test_return_effects test_aero_effects test_ex13_ulforce_effects -q
```

This is the current bounded validation set. Full discovery also includes legacy
60-game cohort tests; leave those out under the current user instruction.

Inspect the active readiness inventory:

```bash
python3 matchup_readiness.py --context ../ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json
```

Expected: `BLOCKED`, process exit2. This currently reports unfinished gameplay
and evidence gates; it is not a claim the input decks are illegal.

**Historical diagnostic command — do not run under the current no-cohort
user instruction.** It uses random references, not the user's verified bots:

```bash
python3 imported_attempts.py --context-file ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json --out ../ARTIFACTS/helper-diagnostic-01 --count 60 --max-commands 300
```

Here `--context-file` is relative to repository root; `--out` is relative to
your shell directory. Counts must be even and at least2. Output directories are
never overwritten. Command-budget exhaustion is a diagnostic stop, not a draw
or a valid completed game. The bots are fresh untrained uniform-random reference
policies. The new explicit named profiles are untrained and use a separate
bounded runner; do not use this historical command to control the user's bots.

Read one saved attempt without launching another simulation:

```python
import gzip, json
from pathlib import Path
p = Path('../ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0000.json.gz')
record = json.loads(gzip.decompress(p.read_bytes()))
print(record['seed'], record['first'], record['halt_reason'])
print(record['commands'][-1])
```

For historical diagnostic records, from `SOURCE`, replay under the recorded context
(the new paused checkpoint uses `recorded_action_checkpoint.replay_selected_action`):

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
|`SOURCE/named_player_bots.py`|Fresh public-view aggressive/defensive profiles, source/context-bound identities and decision rationale|
|`SOURCE/named_bot_continuation.py`|Bounded named-policy segments with exact saved-history/state/RNG proofs and replay|
|`SOURCE/recorded_action_checkpoint.py`|Replay saved decisions and resolve only the stored pending selection, then pause without invoking policies|
|`SOURCE/return_effects.py`|Shared actual-event return preflight and top/deck-bottom plus lower/trash movement|
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
