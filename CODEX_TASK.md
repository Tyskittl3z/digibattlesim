# First Codex task (execute, don't just plan)

> **Game 0000 active — 2026-11-11.** The user authorized the first fully
> logged Bot A (aggressive) versus Bot B (defensive) game. Latest exact-replay
> checkpoint: `ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0019.json.gz`,
> 156 accepted commands, A turn 9, saved HALT at Blocker battle confirmation.
> The EX13-019 inherited Jamming fix has a passing focused test; migrate/retry
> that exact saved confirmation, then continue only this game
> with its seed, choices, policy identities, frozen empty model and Bot C ledger.
> The formal repair lineage and earlier HALTs are retained; use the next actual
> action, verify replay, and save a new segment. Do not launch the 60/10,000
> cohorts or credit an unfinished game. The old pre-first-match pause below is
> superseded only for Game 0000. Publish progress on the draft branch.

> **Engine repair migration verified — 2026-11-10; matches still paused.**
> 173 focused tests pass (73.877s), independent review is clean after the cached
> code fix, and a durable cross-build private proof passes exact migration and
> saved-action retry. Read latest STATUS/handoff and
> `ARTIFACTS/repair-migration-2026-11-10/pause-control.json`.
> Use `fresh_repair_migration.migrate_repaired_game` explicitly with original
> sources and exact reviewed differences; never replace source hashes manually.
> Earlier results, full state/RNG, named players, rules and model must agree.
> Migration does not retry a failure or train. Ordinary migrated replay/resume
> loads source directly. Zero production games/updates/ratings/match credit;
> do not launch gameplay/cohorts on a usage reset. The older same-build-only
> restriction is superseded by this narrow verified repair path.

> **Integration checkpoint verified — 2026-11-10; actual matches paused.**
> Named A aggressive/B defensive, Bot C, board scoring, judge receipts and
> persistent learning are connected. 155 focused tests passed (35.346s), plus
> exact replay/resume of a five-command private fixture. Read latest STATUS,
> PYTHON_DEVELOPER_HANDOFF.md and
> `ARTIFACTS/learning-integration-2026-11-10/pause-control.json`.
> Zero production games, learning updates, live ratings or match credit.
> No production schedule is locked. Preserve the old mixed-policy game without
> training from it. Resume is same-build only; verified repair migration is
> still unsupported. Do not start actual games/cohorts on a usage reset, weaken
> source pins, substitute reference players or imply independent certification.
> All older pending-module instructions below are historical and superseded.

> **Integration in progress — 2026-11-10.** Scorer/criteria and judge ledger
> pass 59 focused checks with Bot C. See the scoring-judge milestone artifact.
> Learner and fresh runner are still in progress; actual matches remain paused.
> No fresh-game, production-training or live-rating credit exists. Continue
> preparation/verification only, preserving old archives and saved choices.
> Older Bot-C-only instructions below are superseded by current integration work.

> **Bot C verified — 2026-11-10; actual games still paused.** FieldTracker is
> implemented with 30 regression tests, 74 focused checks, independent review and
> exact observer replay of the 164 stored commands. See
> `ARTIFACTS/bot-c-2026-11-10/verification.json` and pause-control.json.
> No fresh game/deal, player decision, learning update or rating ran. Bot C is
> standalone; learner/scorer, judge ledger and fresh runner/integration remain
> pending. Do not start an actual match/cohort until user continues. Old records
> remain immutable and excluded from fresh training.

> **PAUSED BEFORE FIRST FRESH MATCH — 2026-11-05.** User explicitly requested
> pausing before the match. Usage reset does not resume it. No opening deal,
> fresh game or learning update has started. Read
> `ARTIFACTS/pre-match-setup-2026-11-05/pause-control.json` and latest STATUS.
> Save setup only; do not call a gameplay/cohort runner until user continues.
>23 draft tests/API notes are parked outside live SOURCE; implementation is
> pending. Historical164-command game remains archived, excluded from fresh
> training. The new60-game plan is authorized in principle but currently paused.
> Older instructions below are historical and subordinate to this pause.

> **2026-11-04 named bots now connected:** A AGGRESSIVE/B DEFENSIVE, fresh
> untrained profiles with explicit identities. Latest sameGame0000 checkpoint:
> `ARTIFACTS/gameplay-continuations-2026-11-04-02/game-0000-segment.json.gz`.
> Originalseed/first152 choices preserved;12newcommands allsuccess,164total,
> Aturn11 MAINmemory2.82focusedtests and exactreplay pass. Nextpendingeffect64
> is A BT11Ulforce play_blue_tamer from secondpaidRina, thenolderinherited60;
> Counter waits until pending clears. Use named_bot_continuation, notrandom
> continue_attempt. Keep zero wholemixedgame/factfinding/finalcredits. No
> cohorts, preloadedroutes or outcomeratings. See STATUS/roster/decisionlogs.
> Older paused-bot-identity instructions below are historical and superseded.

> **2026-11-04 latest user boundary:** Game0000's selected effect57 return is
> resolved; preserve the new PAUSED_AFTER_SAVED_ACTION checkpoint at
> `ARTIFACTS/gameplay-continuations-2026-11-04-01/game-0000-segment.json.gz`.
> Bactive, turn10, memory−1, END_OF_TURN;152 successful commands, original seed
> and choices. Both historical policies are untrained random references,
> not verified as the user's bots. Zero policies were invoked for this retry;
> zero user-bot/fact-finding/final credit. Establish the actual imported-context
> bot identities/adapters before a new decision. Do not call the old random
> continuation, preload routes, run60/10,000 cohorts, or assign ratings without
> defined scoring criteria.62 focused tests pass; latest full suite495 at
> aed966b. See STATUS and the new saved checkpoint's replay/proof files.
> Older next-action instructions below are historical and superseded.

> **Latest live continuation:**495 tests pass. Game0000turn10 /152commands,
> original seed/choices, exact archived-source replay. Continue effect57
> BT22-023.when_digivolving_return: sourceB:BT22-023#2,targetA:BT22-022#1,
> memory−1/MAIN from
> `ARTIFACTS/gameplay-continuations-2026-11-03-11/game-0000-segment.json.gz`.
> Targetegg→EX1→BT22 mustreturntopdeckbottom/lower2trash. Share actual-field
> return preflight; no whitelist or false unrelated self protection. After
> pending clears, END_OF_TURN opens at−1 without switching B/turn10.
> Return worker prepared work outside SOURCE; official review insegment12.
> Zero valid full games. Publish current progress before usage ends.

> **2026-11-02 current priority:** User delegated choosing the best starting
> matchup. Use the distinct-list Ulforce mirror 123129 vs122110, not the original
> pair's default CLI argument. Read `PYTHON_DEVELOPER_HANDOFF.md`, latest STATUS,
> and `REPORTS/ULFORCE_BOOTSTRAP_PROGRESS_2026-11-02.md`. Latest source passes335
> tests. New diagnostic version02 records60 original context-bound seeds with
>30 starts each and60 exact replays; all60 HALT, zero valid full-match credit.
> Finish the encountered real effects and inspect overbroad scope guards;
> retain all evidence and the original randomized queue.

> **2026-11-01 live continuation:** Read the latest STATUS section and
> `REPORTS/EX13_LIVE_ENGINE_PROGRESS_2026-11-01.md`. The selected engine now has
> 307 passing tests and actual balanced diagnostic attempts; both60-attempt
> versions halted and provide zero accepted-match credit. Continue from their
> preserved seeds and exact blockers; do not restart the project or reinterpret
> the diagnostic cohort as the completed fact-finding requirement.

> **2026-10-30 continuation:** The user expanded this engine track to selected,
> randomized exact pairs from `DigiLab_EX13_Top_Decklists_Deduplicated.xlsx` and
> chose English-version worldwide rules. The old two-deck-only restriction below
> is historical and superseded for this authorized track; all integrity,
> no-advice, source-evidence, fresh-matchup and freeze requirements remain.
> Read `REPORTS/EX13_ENGINE_PROGRESS_2026-10-30.md` before continuing. The current
> explicit-context foundation has 193 passing tests but no full-game simulator
> support or valid matches for the first imported pairing. Continue implementing
> its remaining scoped mechanics and full gameplay, then the 60/roadmap/10,000
> gates. The other chat owns catalog/import/comparison/storage/browser work.

## Goal
Bring the **Jupitermon (A) vs Amaterasumon/Toho (B)** two-deck simulator to at least 60 **fully completed, judge-verified** fact-finding games with balanced starts, then evidence-backed GREEN/YELLOW/RED roadmap readiness. Sixty is the minimum, not proof that all encountered branches were covered. Keep the 10,000-match final evaluation as a later gate. Apply the accepted verification adjustments in `WORKFLOW.md`.

## Immediate steps
1. Reproduce the baseline: run `python -m unittest discover -p 'test_*.py' -q` from `SOURCE/`; identify source hashes and preserve previous reports as versioned artifacts.
2. Reproduce the five EX12-076 Susanoomon HALT cases from `MATCH_LOGS/` or the 60-seed runner. Extract their exact states. Determine official interaction/timing for Decode and leave-the-battle-area protection/replacement from the **loaded** cards only.
3. Implement the required controller choice(s) and exact resolution, with judge citations and targeted tests. Do not conflate a Digimon being moved, a replacement effect, and Decode; resolve in official order.
4. Audit other unmodeled *encountered* optional attacking effects; evaluate legal activate/decline branches rather than forced declines. No unsupported effect may be silently treated as resolved.
5. Pin the rules/format snapshot, then rerun a minimum of 60 complete games (at least 30 starts per deck, equal counts) and verify replay, zones, timing, and ending. Close encountered branch gaps with targeted scenarios; scenarios count as zero full games. If a new halt occurs, solve its loaded-deck rule and rerun. Preserve raw records with engine/rules/criteria hashes.
6. Construct situational three-lane roadmaps under preregistered approval criteria. Separate rules-legality review from strategy-effectiveness review. Require evaluated legal alternatives, metric/objective, multiple independent-seed traces and uncertainty; report unknowns without inventing positive lanes.
7. Only after verified gameplay and frozen pilots may you implement/run the 10,000 real turn-by-turn evaluation; keep learning disabled during the final run.

## Completion gates
- At least 60 **full** legally resolved, judge-reviewed training matches, at least 30 starts per deck with equal counts, plus reviewed coverage of encountered interaction alternatives and zero unresolved mandatory effects.
- No hidden substitutions, skipped active effects, invented rules, or unverified end states.
- Persistent green/yellow/red classifications conditioned on objective board state and traceable evidence; UNKNOWN allowed.
- Comprehensive numerical report and raw compressed match logs.
- Final 10,000 results only if freeze/eligibility gates actually pass; otherwise report exact blockers.
- Preserve every final HALT's seed and trace. No replacement seeds; identical-freeze infrastructure retries replay the original match. Any frozen gameplay/input change requires a new freeze and full final restart, never a mixture of versions.

## Hard restriction
NO deck advice. NO previous deck matchups. NO universal card engine. NO claimed certification based solely on a test-count or a replay-count.
