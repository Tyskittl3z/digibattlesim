# Verified handoff status

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


## Saved return resolved; policy audit — 2026-11-04

Game0000 is **PAUSED_AFTER_SAVED_ACTION**: all **152 commands resolved**, B active
on turn10, memory−1, phase END_OF_TURN. Original seed12017913134550805276,
first playerA, all151 earlier successful commands/results/views and the complete
pre-return physical state/RNG were preserved. The saved effect57 selection was
retried exactly once: A:BT22-022#1 went to A deckbottom; A:EX13-002#2 and
A:EX1-013#2 went to A trash. No later end-turn processing or player choice ran.

**Policy correction:** both saved seat policies are
`fresh-untrained-uniform-random-reference-v1`, not verified as the user's two
bots. Their full historical identities remain preserved. The new bounded runner
invoked no policy and made zero new decisions; the reference history earns zero
user-bot evidence. Legacy named BotA/B code belongs to Jupitermon/Toho and has no
current imported-context adapter. Do not silently substitute either policy set.

**Verification:**62 focused tests passed (25.371s), including source-identity,
shared return dependencies, saved-choice preservation, forbidden policy calls,
and bounded replay tests. Independent actual-prefix/state-delta proof passed
(24.273s), with108 unique physical cards and unchanged return RNG. The latest
full-suite baseline remains **495 tests at aed966b**; this increment uses focused
checks. The full suite includes legacy60-game cohort tests, which were not run
under the user's current no-cohort instruction.

Latest checkpoint/evidence:
`ARTIFACTS/gameplay-continuations-2026-11-04-01/`. Full checkpoint exact-replay
verification is recorded in that directory's replay.json. Source bytes are
archived beside the saved record. No full game is complete; user-bot evidence,
accepted fact-finding games, approved lanes and final-match credit all remain0.
No routes were preloaded, cohorts launched, or strategic ratings assigned.

**Next boundary:** leave this checkpoint paused. Actual current-context bot
identities/adapters must be established before another player-policy decision.
Do not use imported_attempts.continue_attempt: it constructs fresh random
reference policies. Do not run the60/10,000 cohorts or attach positive/neutral/
negative or GREEN/YELLOW/RED ratings without defined, applicable scoring criteria.


## Verified turn10 continuation — 2026-11-03

**495 tests passed** (556.480s). Same Game0000 now has **152 recorded commands**,
turn10, original seed/choices preserved and exact replay at its archived source.
Attack declaration uses the shared suspension batch; unrelated self-protection
no longer blocks a different combatant. The actual12000vs5000 Security check
resolved: A security2→1, checked P138 to trash, attacker alive, memory unchanged.
Independent state/RNG/card-conservation proofs and role checks are stored with
segments10/11. No full game is complete yet.

**Next selected action:** effect57 BT22-023.when_digivolving_return, source
B:BT22-023#2, target A:BT22-022#1. The actual preceding evolution cost3 moved
Bmemory2→−1; target stack is EX13egg→EX1Veemon→BT22Veedramon. Replace the old
return whitelist with shared actual-field preflight: top to deckbottom, lower2
to trash; egg's Tamer-play text and inactive top-inherited protection do not
trigger. After resolution opens END_OF_TURN at−1; B stays active/turn10 until
later end processing. Source11 is sealed; segment12 holds the pending review.

Latest saved record:
`ARTIFACTS/gameplay-continuations-2026-11-03-11/game-0000-segment.json.gz`.
Return fix is prepared outside SOURCE while the verified checkpoint publishes.
**Zero valid full current-pair games, zero approved lanes, zero final games.**
Keep publishing current work before usage ends.

## Published WIP: turn10 saved — 2026-11-03

Same original Game0000 reaches **turn10 /140 commands**, exact replay at its
archived source, earlier choices/RNG preserved. BT11 Rina's AllTurns reaction
now supports explicit decline, one available current WhenDigivolving effect,
and legal payment with no effect. Used OPT effects are excluded; the selected
effect completes before older siblings, with no new evolution or bonus draw.

Next selected action: **B:BT11-032#1 attacks PLAYER**, memory5, MAIN. Its stack
is EX13Aero→BT11Ulforce. Connect declaration to the shared suspension preflight
and one reaction batch (two B Rinas plus inherited Aero). Prepared, unapplied
patches are preserved under segment09/pending-attack-integration.

Verification remains WIP:10 handler tests,33 integration checks (one source-hash
interruption retried), the actual pilot test, and independent13 tests/proof
probes pass. The full488-test run found one stale expected-error assertion in
an empty-registry fixture; its expectation is corrected. Last entirely green
full suite remains459at713a513. Current source has not had a fresh all-green
full rerun; do not claim otherwise. Segment09 stores exact traces, source
archive, rules reviews and verification limits.

Zero full valid current-pair games, approved lanes or final games. Keep publishing
current code and prepared work before usage ends. Source review09 also corrects
a historical review's EX13-019 name: the pinned card/engine says Veedramon.

## WIP publication: EX13 evolution — 2026-11-03

Same Game0000 now reaches **turn8 /105 commands**, original seed/earlier choices
preserved, exact replay at its archived source. The selected Rina evolution paid
1, drew its bonus card, and queued EX13 Ulforce's two WhenDigivolving effects in
one group. Next selected action is orientation effect34 targeting itself. Its
suspension needs BT11Rina's AllTurns reactivation and inherited BT22Aero reactions.
Those are the next implementation step; no effect is skipped.

**WIP verification:**29 evolution/play/Rina tests passed (62.614s),9 return/pilot
tests passed (3.596s),4 readiness tests passed; source syntax/diff checks clean.
**Last full suite remains459 at713a513. Current full suite is unrun.** Source
review corrected future simultaneous deck-bottom order to the action-causing
card's owner per CR3-1-3-4; explicit complete order is now validated without
enumerating permutations. The actual singleton trace is unchanged by that fix.

Latest source-bound trace, readable turns, archive and reviews:
`ARTIFACTS/gameplay-continuations-2026-11-03-08/`. No full current-pair games,
approved lanes or final games exist. Keep publishing current WIP before usage
ends, and continue the same selected action.

## Published work-in-progress checkpoint — 2026-11-03

The user explicitly directs publishing current progress before usage runs out.
This checkpoint preserves current code/evidence even while the next interaction
is unfinished. **Last full suite:459 passing tests at713a513** (444.077s). The
current Ulforce increment passes13 focused Tamer tests (67.693s), an independent
3-test actual class (21.666s), and the new orientation-choice regression. Python
syntax and diff checks pass. **Full suite has not been run on this increment.**

Same Game0000 reaches **turn8 /104 recorded commands**, seed12017913134550805276,
all earlier choices preserved and exact full-record replay. BT11-032 evolution
paid4, drew/played BT11 Rina, queued her grant and mandatory Ulforce unsuspend
together, and correctly produced no new orientation event because it was already
unsuspended. Actual Aturn7 ended; B's turn8 Rina draw then led to the next chosen
evolution. Segment07 includes records, readable trace, source archive/manifests
and independent93/103-command prefix reviews.

**Next selected action:** resolve Rina AfterDraw effect33, evolving
B:BT22-023#1→B:EX13-023#1, route0, cost3−2=1 at Bmemory2 in UNSUSPEND.
The new EX13 top has two simultaneous WhenDigivolving effects: existing optional
orientation and optional return-all-opponent-Digimon with the fewest sources.
The actual sole minimum is A:BT12-029#2 (zero sources); A BT11 Ulforce has one.
Implement only this encountered behavior, with actual leave-effect checks and
explicit order/timing. If orientation later fires an unsupported real reaction,
preserve that selected action and fix it; do not suppress it.

**Zero complete valid current-pair games, zero approved lanes, zero final games.**
Latest record:
`ARTIFACTS/gameplay-continuations-2026-11-03-07/game-0000-segment.json.gz`.

## End-turn Rina continuation — 2026-11-03

**459 tests passed** (444.077s). Same Game0000 now reaches **turn7 /94 commands**,
original seed12017913134550805276 and all prior decisions preserved, exact replay.
The selected B Aero unsuspend now triggers exactly three simultaneous B Rina
effects: mandatory BT11 memory gain and two explicit EX13 suspension choices.
In the actual continuation both optional costs were declined; memory went−3→−2
and the real turn transition gave A2. Paid Draw/After branches were separately
tested with post-draw choices and one source-bound−2 reduction per effect.

Actual-event orientation checks ignore unrelated opponent/self text. Simultaneous
phase unsuspends share one group. Pending grants expire at actual turn completion,
not at pending end processing. Segment06 retains the full94-command record, exact
replay, readable turns, source archive/manifests and official-source reviews.

The next selected action is ordinary evolution **A:EX13-022#1→A:BT11-032#1**,
printed cost4 at memory3. Its actual When Digivolving blue-Tamer free play is next.
Normal evolution preserves the current cannot_suspend grant/entity; already-
unsuspended processing creates no new unsuspend event. Latest saved record:
`ARTIFACTS/gameplay-continuations-2026-11-03-06/game-0000-segment.json.gz`.

**Zero complete valid current-pair games, zero approved lanes, zero final games.**
All prefixes and targeted scenarios remain separate from the60 full-game target.

## Recorded attacks and Security continuation — 2026-11-03

**446 tests passed** (390.282s). Same Game0000 now reaches **turn6 /83 recorded
commands**, original seed12017913134550805276 and every earlier successful choice
preserved, with exact full-record replay. Two ordinary Security battles resolved;
the third checked EX13-069 Rina, whose immediate Security effect played her into
A battle for0 cost. Her play correctly queued A's Aero observer, with restriction
expiry at the actual current Bturn6 end. No DP battle, hand detour or extra
trashing was applied to the played checked Tamer.

The attack guard now checks actual participants/events rather than rejecting
unrelated Tamer/stack presence. Unsupported real Blocker/Evade/deletion/security
observers remain explicit dependencies. Ordinary attack candidates exclude
suspended Tamers. Identical selected-context Tamer Security wording shares one
source-bound procedure; other text remains unsupported. Current mirror registry
has33 experimental source-bound bindings; this is not branch coverage.

Segments04 and05 preserve full records, replay proofs, source snapshots, readable
turns and source-backed reviews. Independent archived-source segment04 audit
matched all77 successful commands, all108 cards and exact state/RNG; no concrete
defect found in19 newly resolved commands.

**Next actual selected action:** effect21, BT22-023 EndYourTurn unsuspend targeting
B:EX13-022#3 at Bmemory−3. The broader old orientation guard rejects unrelated
A BT11Rina text. Resolve the actual Bunsuspend and three simultaneous B Tamer
reactions: BT11Rina memory gain and two EX13Rina optional self-suspend/Draw/After
evolution effects. Use post-Draw hand choices and source-bound individual−2
reductions; preserve the same saved action and pending end-turn window.
Latest record: `ARTIFACTS/gameplay-continuations-2026-11-03-05/game-0000-segment.json.gz`.

**Zero complete valid current-pair matches, zero approved lanes, zero final
matches.** The60-game and10,000-game requirements remain outstanding.

## Same-game checkpoint — 2026-11-03 UTC

**430 tests passed** (259.488s). Game0000 retains original seed
12017913134550805276 and all earlier choices, now **turn6 /59 recorded commands**,
with exact full-record replay. The Blue Scramble stop is resolved; encountered
Option searches/Delay/reduced evolution and BT22-022 conditional free-Tamer play
now have explicit choices and source-bound handlers. The exposed EX13-002 egg
reaction is recorded with simultaneous Tamer-play effects; already-unsuspended
processing generates no false orientation or memory event.

Saved segments02 and03 include compressed full records, exact replays, readable
turn traces, official-source reviews and source archives/manifests under
`ARTIFACTS/gameplay-continuations-2026-11-03-02/` and `...-03/`. Independent
archived-source review of segment02 matched all54 successful commands,108-card
conservation, physical state and RNG; none of its33 new resolved commands had a
concrete identified defect. This is partial-game evidence only.

The next selected action is **B:EX13-022#1 attacking PLAYER**, turn6/memory3.
An old whole-board combat guard rejects A's BT11-112 Tamer before declaration.
Source-backed review finds the declaration legal: unrelated Rina text does not
trigger on the opponent's suspension. Add the actual When Attacking free-Tamer
trigger, preserve counter/block/security timing and continue this same action.

**Zero complete current-pair matches, zero approved lanes, zero final matches.**
The60/10,000 targets remain outstanding; diagnostic prefixes are never counted.

## Gameplay-first continuation — 2026-11-02

Following the user's correction, continue actual chosen actions and preserve
the same game, rather than front-loading route inventories or rerolling its
earlier decisions. `continue_attempt` revalidates saved successful commands,
proves the pre-stop physical state and RNG, retries the original selected action,
and records a separately seeded discovery-policy segment for subsequent moves.

**409 tests passed** (134.239s). Source-backed reviews and exact historical
prefix regressions now resolve Rina's actual On Play targets/no-target cases,
BT22-023 return effects and end-turn choices, EX13-022 free-Tamer play plus its
simultaneous restriction reaction, Mental Training use, ordinary encountered
battle evolutions, the checked Ulforce security battle, and two plays wrongly
blocked just because unrelated inherited cards were in stacks.

Game0000 preserves original seed12017913134550805276 and advances beyond its
original turn1 Rina stop to **turn3,22 recorded commands**. Its new selected
action is A:LM-028#1 Blue Scramble, whose implementation is next. The complete
new record replays exactly. Evidence and source reviews:
`ARTIFACTS/gameplay-continuations-2026-11-02-01/`.

This is one unfinished game: **zero valid complete matches, zero approved
strategy lanes and zero final matches**. Code/turn prefixes do not count toward
60. Preserve those original decisions and continue this game after the next
specific effect is implemented. The current source is experimental; old60-HALT
cohorts remain historical diagnostic evidence.

## Current development priority: Ulforce mirror — 2026-11-02

User delegated the best starting matchup. Selected two different exact workbook
lists, Federico Nine123129 (A) and Bern122110 (B), each50 main+4 eggs. Their
union is22 source-pinned cards /79 printed units, compared with45 /150 in the
original pair. This narrows implementation scope without predicting deck
strength or completion time. Original randomized queue and old evidence remain
unchanged; mirror pair is queue entry145.

Added shared exact-context capability resolution and explicit diagnostic context
selection/replay. Both context ID and ordered source IDs are pinned. Changed
cards/counts/rules/IDs or escaping input paths do not gain support. Replay uses
one immutable context-byte snapshot and verifies expected bytes/identity before
runtime construction, including changes between preflight and execution.

**335 tests passed** (57.555s). Fresh mirror diagnostic version02: **60 attempts,
30 starts per deck,60 exact replays,60 HALTs**. First stops:42 actual On Play,
8 Options,7 battle evolutions,2 stacked boards,1 scoped security card. No full
current-context games, approved roadmaps or final evaluation results exist.
Version01 is preserved; runner edits changed pilot identities, so differences
between cohorts are not an isolated mechanic-effect comparison.

Active context: `ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json`.
Evidence: `ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/`.
Read `PYTHON_DEVELOPER_HANDOFF.md` for setup, architecture, sources, exact commands
and concrete next work. Original runner default remains Ulforce/Gallantmon;
use `--context-file` for the current development pairing.

## Gameplay reference intake — 2026-11-02

Indexed eight user-supplied timestamped transcripts (5,029 caption blocks),
two exact reference decklists (each listed 50 main + 4 eggs), and timestamped
frame samples from the accessible 17-minute 240p SeitenGokuumon/Gammamon video.
Saved source hashes, printed-source checks and concrete regression candidates
in `ARTIFACTS/video-reference-2026-11-02/`; see
`REPORTS/GAMEPLAY_REFERENCE_REVIEW_2026-11-02.md`.

Ten Ulforce/Gallantmon transcript candidates map to overlapping current-pair
mechanics; sixteen referenced official-source hashes match the pinned context.
The narrated Gallantmon list differs from selected B, so any adapted fixture
must identify its synthetic inputs. These references do not change the selected
pair, production source, rules review, pilots, roadmaps or simulator match
counts. Last engine verification remains 312 passing tests; zero complete valid
fact-finding matches and zero final matches. No new test execution is claimed.

## Printed trigger correction — 2026-11-02

User correction accepted: card wording is executed at the printed timing; prior
"interaction gaps" included overly broad code guards. All24 original no-On-Play
hard-play failures now resolve in exact command-prefix replays, with pre-action
states equal to the saved originals and no unrelated ability fired. Ordinary
play and candidate enumeration no longer require an unrelated timing's handler.

**312 tests pass**. A new balanced60-attempt diagnostic cohort retains the same
match seeds (policy hash changed with candidate correction), with60 exact replays.
Current halts:31 actual On Play handlers,16 Options,8 battle evolutions,2 stacks,
3 battlefield/attack capabilities. Zero complete or judge-valid matches remain;
roadmaps and final10,000 are still gated. These are software limits, not rulings
that the cards are ambiguous or illegal.

Read `REPORTS/PRINTED_TRIGGER_CORRECTION_2026-11-02.md` before continuing. Implement
clear effect wording directly at its trigger; use shared rules for procedures.

## EX13 live turn/attack continuation — 2026-11-01

Paused work was reverified at 247 passing tests and committed as 24fee77.
Current suite: **307 passed**. Added explicit pass/turn switching, basic attack
Counter/Block/success/end windows, scoped DP/security battles and terminal guards,
inert live-board capability, and EX13-017/EX8-009 searches. Fourteen mechanic
bindings remain EXPERIMENTAL_UNREVIEWED; full selected-pair gameplay is incomplete.

Actually executed two balanced diagnostic cohorts on the **same 60 original
seeds/pilots** under different engines: starts30/30 and exact replays60/60 each.
Both cohorts: 60 HALTs, zero software terminals, zero accepted/full fact-finding
credit. Version02 removed all21 search-top scope halts; current blockers are
43 unsupported play capabilities, 11 Option actions, 4 battle evolutions and
2 stacked boards. No ILLEGAL ruling or deck-strength conclusion is implied.

See `REPORTS/EX13_LIVE_ENGINE_PROGRESS_2026-11-01.md` and
`ARTIFACTS/imported-diagnostic-2026-11-01-02/summary.json` before resuming.
Original seed/trace/policy identities and both versions are preserved.
Rules/branch review, valid60+, approved roadmaps and final freeze remain unmet:
**0 judge-valid matches, 0 approved lanes, 0/10,000 final matches**.

Next: implement the actually encountered play/evolution/Option/stack interactions
and rerun those same seeds. Source metadata-review notes identify unresolved
X Antibody extraction and Q&A keyword issues; do not guess around them.

## EX13 engine track — 2026-10-30

The user authorized randomized pairings from the uploaded 54-entry/11-archetype
EX13 workbook and **English-version worldwide rules**, with 60+ fact-finding and
10,000 final matches **per selected pairing**. First queued pairing is
UlforceVeedramon/Federico Nine (123129) versus Gallantmon/RTA (124303).

Added immutable explicit-context input models, experimental physical-state and
transactional mechanic dispatch, selected printed evolution candidates, a scoped
EX13-023 orientation pack and an executable readiness inventory. Retrieved both
exact lists (50+4 each), 45 official card pages, 99 Q&A entries and official
rules/restrictions/errata. Three HTML type conflicts are preserved alongside
official OPTION images. No APP/catalog changes or old-matchup evidence reuse.

Actual verification: **193 Python tests pass**, including the original 148.
Independent software review findings were reproduced and fixed. Six targeted
scenarios: 3 experimental resolutions and 3 expected scope HALTs; **zero full
match credit**. Readiness CLI exits **2/BLOCKED**: 1 experimental handler among
150 printed-text inventory units, 149 units still without full handlers, full
gameplay loop/independent rules review/pilots/roadmaps/freeze unfinished.
**0 judge-valid fact-finding, 0 approved lanes, 0/10,000 final matches** for this
pairing. See `REPORTS/EX13_ENGINE_PROGRESS_2026-10-30.md` and the new plan/spec.

The old loaded-pair engine and its blocked gate remain preserved below. Their
historical results do not establish support for the new imported pairing.

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
