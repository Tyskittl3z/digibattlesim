# Permanent Codex instructions — Digimon Battle Simulator

## Current first-game completion boundary — 2026-11-11
- The user authorized **only the first fully logged fresh game** after the
  earlier pre-match pause. Game 0000 uses named A aggressive, B defensive,
  Bot C, the Federico Nine/Bern lists and the locked seed in
  `ARTIFACTS/fresh-game-0000-2026-11-11/`. Latest saved exact-replay segment:
  `game-0000-segment-0023.json.gz`, 182 accepted actions, status
  EXPERIMENTAL_SOFTWARE_TERMINAL, A direct-attack winner on turn 13. Read the
  CSV/report and exact replay receipt in the same artifact directory. Never
  substitute random reference policies, reroll its seed,
  or use old mixed-policy history as training data.
- Earlier HALTs and a Bot C audit rejection remain preserved. Their exact
  source-repair lineages are part of the record. Source pins, the model and
  prior choices must remain intact. A rejected audit is not a valid action or
  a red play. One explicitly committed learning update is experimental. The
  game has zero valid 60-match fact-finding/final-evaluation credit; independent
  semantic certification remains absent. Game 0001 and the 60-game and
  10,000-game cohorts remain off under this one-game authorization.
- The 2026-11-10 pre-first-match pause instructions below are historical for
  Game 0000. Keep publishing progress on the draft branch as requested.

## Project purpose — NON-NEGOTIABLE
This repository is a **simulation and numerical-results tool**, not a deck-building assistant.
User owns all deck construction, interpretation, and decisions; offer **no card/slot recommendations** and no speculative conclusions. User-requested numerical deck comparisons are allowed. Do not alter decklists without explicit user instruction.

## Scope and isolation
- **User-delegated development priority (2026-11-02):** The user said the
  starting matchup need not be Ulforce/Gallantmon and delegated whichever route
  works best. Bootstrap the two distinct workbook Ulforce lists: Federico Nine
  123129 (A) versus Bern 122110 (B), 50+4 each, 22 distinct pinned cards. Active
  context: `ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json`. This is an
  engineering priority choice, not a deck recommendation or a change to the
  preserved random queue (this pair is entry145). Preserve original-pair
  evidence; new matchup gets fresh pilots/seeds/roadmaps/results. The original
  diagnostic CLI default remains for compatibility: explicitly pass the new
  context. Read `PYTHON_DEVELOPER_HANDOFF.md` and the latest STATUS first.
- **User-authorized engine-track expansion (2026-10-30):** The user selected
  `DigiLab_EX13_Top_Decklists_Deduplicated.xlsx` (54 indexed exact-list entries,
  11 archetypes), requested randomized matchups, and confirmed a separate
  balanced 60+ fact-finding cohort and 10,000 final matches **per selected
  pairing**. This supersedes the old two-deck-only scope for this track. Build
  reusable match infrastructure and verified mechanics only for selected
  imported pairs, never universal speculative card support. The other chat
  owns catalog, generic intake/legality/comparison/storage and browser UI.
  Preserve the random queue and exact composition identities; unavailable lists
  stay explicit. New matchups receive fresh pilots, roadmaps and evidence.
  First queued pair: UlforceVeedramon/Federico Nine (123129) vs Gallantmon/RTA
  (124303). See `docs/superpowers/specs/2026-10-30-ex13-engine-design.md`.
- User request (2026-10-29): add a drag-and-drop browser app for **both** side-by-side deck contents/statistics and head-to-head simulation. Decklist intake/numerical comparison may accept user-supplied lists. This explicitly authorizes the comparison interface; simulation support remains limited to verified mechanics of the selected matchup. Unknown cards/unsupported pairings must remain explicit; never manufacture win rates or reuse another matchup's results. Save exact inputs, hashes, statistics, data gaps, simulation status and actual results/log references in a downloadable after-report.
- **Historical loaded simulator gameplay scope**: `DECKS/JUPITERMON.txt` (A) vs `DECKS/AMATERASUMON_TOHO.txt` (B). Browser import/statistics for another pairing do not certify its gameplay support. The new explicit-context engine track is separate experimental software until it passes the same evidence contracts.
- NEW DECK = FRESH START. For any new deck or changed matchup, invalidate all deck-specific roadmaps, training data, pilot weights, and matchup results. Reuse only rules, generic match infrastructure, and verified generic mechanics. Do not seed a new match with another deck's data.
- Never expand toward universal Digimon card support or unsolicited feature work. Work on interactions that the **loaded two decks can actually produce**, as found during gameplay.

## Authority and integrity
- **Verified engine repair migration (2026-11-10):** The current setup checkpoint
  adds `fresh_repair_migration.migrate_repaired_game` for fresh-schema paused/HALT
  records. 173 focused tests and a durable real cross-build private proof pass;
  see `ARTIFACTS/repair-migration-2026-11-10/` and current pause-control.json.
  Preserve original source/record, exact approved engine differences, seed/full
  state/RNG/choices and unchanged rules/context/model/policies. Verify original
  and repaired execution from source-only workers; never replace source pins or
  trust cached-code equivalence. Migration does not retry, choose or train.
  Retain failed selections and all parent lineage; explicit later continuation
  retries selected actions. Reject changed earlier outcomes and protected-file
  changes. Older same-build-only status is superseded by this narrow repair path,
  not by arbitrary source/data migration. Actual matches/cohorts remain paused
  during this setup continuation; no production games/updates/ratings or credit
  exist. Keep archived mixed-policy history out of fresh training and all final
  evaluation disabled.
- **Verified integration checkpoint (2026-11-10):** Named A aggressive/B
  defensive, Bot C, board/tempo scorer, automated judge receipts, learner and
  fresh runner are connected and verified in private fixtures only. 155 focused
  tests passed; see `ARTIFACTS/learning-integration-2026-11-10/` and its current
  pause-control.json. No production game/update/rating or cohort has run.
  Earlier Bot-C-only pending-module restrictions describe historical scope and
  are superseded by the authorized integration work. Actual matches remain
  PAUSED_BEFORE_FIRST_MATCH; usage reset alone never lifts it. Resume currently
  requires identical sources; repair migration remains unsupported. Preserve
  failed selections/seed/history and add verified migration rather than
  weakening pins or rerolling. Judge receipts are experimental automated checks,
  not independent semantic certification. Keep old mixed-policy history out of
  fresh training and the 10,000 evaluation off.
- **Current integration preparation (2026-11-10):** After Bot C was verified,
  user said to go from here. Continue preparation of the fresh-game runner,
  board/tempo scoring, persistent learning and accurately labelled judge receipts.
  Use private unit fixtures and stored-log verification; actual fresh matches
  remain paused as stated in commentary. Do not run the 60-game campaign or
  final evaluation in this integration increment. Old records remain immutable
  and excluded from new training. Defined colors measure actual board changes;
  procedural and forced choices must not receive strategic learning credit.
- **Current authorized preparation (2026-11-10):** User asked to work on Bot C.
  Implement and test the field tracker only; the pre-match pause remains active.
  Private unit fixtures and read-only replay of stored commands are verification,
  not new match starts. Do not implement learning/ratings/judge/fresh-runner work
  or start actual games/cohorts under this component request. Preserve all old
  records and publish the tracker with precise verification and privacy limits.
- **Latest user pause (2026-11-04, preserved 2026-11-05):** The user requested
  a fresh60-game learning campaign with Bot A aggressive/B defensive, Bot C
  tracking and board-impact colors, then said "pause before u start the match".
  Keep PAUSED_BEFORE_FIRST_MATCH: no fresh opening deal or actual match/cohort
  may start until the user says to continue. A usage reset alone does not lift
  this pause. Save/publish preparation checkpoints only. User-defined tempo
  includes more cards out, bigger stacks and more completed successful Security
  checks. New design/test drafts are not implemented gameplay or learned evidence.
- **User bot clarification (2026-11-04):** The intended players are project
  Bot A and Bot B, one aggressive and one defensive. Use A aggressive and B
  defensive as stated in commentary. The legacy named roster used shared
  decision code without separate styles; implement fresh explicit profiles
  for this context, reusing public-view/engine infrastructure. Bind identities
  and declared heuristic preferences; do not relabel random policies or import
  old-matchup strategy. Resume only a bounded same-game segment after prefix
  and complete state/RNG revalidation. Keep historical random choices separate;
  the mixed-history game earns no whole-match bot/fact-finding/final credit.
  The no-cohort, no-route-preloading and no-outcome-rating constraints persist.
- **User constraint (2026-11-04):** Confirm player-policy identities before
  advancing the saved game. Game0000's existing choices came from untrained
  random reference policies, not verified as the user's two bots. Preserve that
  history without counting it as their bots' evidence. For this increment,
  revalidate the original seed/state/earlier choices, resolve only the already
  selected BT22-023 return, and pause before a new decision. Do not substitute
  reference policies, preload routes, or launch either the 60-match or
  10,000-match cohort. Record observed actions/results without positive,
  neutral, negative or GREEN/YELLOW/RED ratings unless scoring criteria have
  been defined and bound to the relevant evidence. Existing legacy bot logic
  belongs to another matchup and is not an authorized silent replacement.
- **User clarification (2026-11-02):** Execute the actual card wording at its
  printed trigger. An unimplemented When Digivolving/When Attacking effect must
  not by itself block ordinary hard play. Do not label unfinished code or overly
  broad guards as card-text ambiguity. Clear wording does not require inventing
  a new ruling; comprehensive rules supply shared procedures and timing. Do not
  silently skip an effect when its actual trigger occurs.
- Official Digimon card text, comprehensive rules and official card Q&A/rulings are the hard authority for legality and effect resolution. A judge validates each encountered interaction. Never guess card effects, costs, timings, targets, replacements or player choices.
- Mark unsupported, ambiguous, or unverified mandatory interactions as **HALT** with precise card, effect, state, seed and reproducible trace. Do not silently skip them, manufacture outcomes, or treat an automatic decline of an optional effect as learned skill.
- Keep an explicit distinction between: `SOFTWARE_COMPLETED`, `JUDGE_CERTIFIED`, `HALT`, and `EXPERIMENTAL`. Code tests and deterministic replay alone do not certify rules.
- No actions after game end; validate memory bounds, zone/card conservation, security timing, trigger/Counter windows, and once-per-turn state.
- Pin the selected format/region, language, rules editions, errata, restrictions, effective dates and official source hashes in `RULES/RULES_LOCK.json`. Missing pins remain UNVERIFIED and block final eligibility.
- Separate software integrity, judge-verified legality and strategic effectiveness. A rules judge does not approve strategy colors; strategy review cannot establish legality. See `WORKFLOW.md` for the evidence contracts.

## Fixed workflow
The user's latest instruction is gameplay-first: choose an action from the
actual state, assess legality against the wording/rules, resolve and record it,
then continue that game. Use the 60 completed games to discover interactions and
assess empirical green/yellow/red choices. Do not delay gameplay to inventory
all possible routes or rebuild the whole architecture. Implement only the
actually encountered missing behavior needed to continue, preserve every
original trace, and report complete games separately from diagnostic prefixes.
1. Load and lock the two exact decklists; validate 50 main cards + Digi-Eggs as listed and applicable restrictions.
2. Run **at least 60 complete, turn-by-turn bot-vs-bot fact-finding MATCHES**: at least 30 starts per deck, with equal starting-player counts. Sixty is a minimum evidence cohort, not an automatic readiness certificate. Opening probes, partial turns and targeted scenarios count as zero full matches.
3. During those matches discover only in-scope combinations, decision alternatives, interactions, and opponent responses. Judge verifies rules evidence. Fix in-scope defects and rerun affected matches / entire evidence cohort when the engine changes.
4. Close encountered interaction/choice coverage using explicit branch inventories and targeted scenarios where needed; record evidence in `RULES/INTERACTION_COVERAGE.json`. Then save **matchup-specific** situational GREEN / YELLOW / RED lane roadmaps under the preregistered `ROADMAPS/APPROVAL_CRITERIA.json`: objective conditions, evaluated legal alternatives, trace provenance, metric/objective and uncertainty are required. UNKNOWN / UNVERIFIED remain separate; strategically RED is distinct from judge-confirmed ILLEGAL. A rules review or one winning outcome cannot approve a lane.
5. Freeze decks, rules snapshot, both pilots, and both roadmaps with hashes. No learning or exploration in the final evaluation.
6. Run **10,000 ACTUALLY PLAYED turn-by-turn matches**, 5,000 starts per deck, as fast as possible without simplifying effects, inventing outcomes, or violating legality. Stream compressed per-match transcripts, seeds, actions, decisions, interactions and end states. Checkpoint and resume safely.
   Preserve every HALT's original seed and trace; never replace a halted match with a new seed. Infrastructure interruption can replay the original match under identical frozen inputs. Unresolved rules HALTs block continuation. Any change to frozen engine, rules/format, decks, pilots, criteria or roadmaps invalidates all final results and requires a new freeze and full evaluation restart.
7. Deliver numerical results only: W/L, rate, first-player split, turn distributions, card play frequency, combo frequency, lane evidence, halts and rule-check status. Do not interpret the numbers as a deck-building recommendation.

## Current snapshot (2026-10-19)
- This is the *latest supplied code snapshot*, not a claim of a fully finished simulator.
- Latest 60 attempt cohort: 55 software-completed, 5 judge halts, 0 independently judge-certified; 0 approved strategy lanes, 0/10,000 final matches.
- Five halts arise from **EX12-076 Susanoomon** targeting opponent stacks involving **Decode P-213, BT26-029, BT24-101**, or leave-the-battle-area replacement/prevention effects.
- There are also top-level optional attacking effects recorded as unmodeled declines; no permission to regard them as correct training decisions.
- Historical match logs in `MATCH_LOGS/` are diagnostic evidence from this version, not certified training or final evaluation output.
- Do not import older deck-specific source builds to resolve these halts.

## Development practices

- **User publishing instruction (2026-11-03):** “always publish wherever you are
  at before the usage runs out.” Commit and push frequent concrete checkpoints
  to `engine-ulforce-bootstrap`, including unfinished work clearly marked WIP,
  with current status/handoff, saved game traces and exact verification limits.
  Keep the last fully tested commit identifiable; do not present WIP as passing
  or complete. Update draft PR#1. This is continuing authorization for checkpoint
  publication; do not ask for confirmation each time. Exclude private/scratch
  environments and preserve source/game evidence.
- Before changing rules, identify the exact official card text/ruling and add a focused regression test for that case.
- Keep changes minimal and load-deck-scoped, with deterministic seeds and explicit judge audit entries.
- Run from `SOURCE/`: `python -m unittest discover -p 'test_*.py' -q`.
- Work autonomously, proceed through blockers and tests without repeated permission requests; ask only for genuinely required user decisions.
- Report actual tool-executed pass/fail and match counts, never projected figures.
- Read `CODEX_TASK.md` and `STATUS.md` before editing.
