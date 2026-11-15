# Named Bot Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task.

**Goal:** Connect Bot A aggressive and Bot B defensive and continue the saved game without altering its history.

**Architecture:** Separate public-view policies from a bounded audited runner. Existing rules and candidate helpers remain authoritative; no reference-policy construction.

**Tech Stack:** Python 3.12 standard library.

**Spec:** docs/superpowers/specs/2026-11-04-named-bot-profiles-design.md

## Global Constraints

No cohorts, pretrained/old-matchup strategy transfer, route preloading or outcome ratings. Preserve seed/first/context/prior selections. Whole mixed-history game credits remain zero. Freeze all source during actual continuation and replay.

## Review Focus

- Hidden hand/deck/security content must never reach or influence a bot.
- Same public choices produce deterministic style differences without game RNG.
- Prefix/result/state/RNG tampering fails before a new policy decision.
- A selected unsupported action is preserved, never silently replaced.
- Policies/source/configuration hashes and historical identities remain distinct.

### Task 1: Explicit fresh named profiles

Files: SOURCE/named_player_bots.py and SOURCE/test_named_player_bots.py.

Interface: NamedPlayerBot(context, seat), manifest(), choose(view, candidates, *, decision=None), bottom_order(remainder); deterministic decision_log list. Stable profile A AGGRESSIVE / B DEFENSIVE, source/config/context identity, public-only inputs.

- [x] Add failing tests for styles, hidden information rejection, determinism and identity isolation.
- [x] Implement printed-data/current-choice preferences and transparent rationale.
- [x] Pass focused tests; freeze files for independent review.

### Task 2: Bounded named-bot continuation

Files: SOURCE/named_bot_continuation.py and SOURCE/test_named_bot_continuation.py.

Interface: continue_with_named_bots(previous_record, root=ROOT, max_new_commands=12), replay_named_bot_continuation(record, root=ROOT). A bound adapter adds public pending effect context to choose calls. Active policy manifests are separate from historical manifests.

- [x] Add failing tests for exact prefix preservation, forbidden ReferencePilot construction, full-state/RNG tamper detection and bounded exact replay.
- [x] Revalidate all saved successes, then execute current windows with named bots, retaining any selected failed command.
- [x] Stop after the bounded segment, terminal or actual gap; pass focused tests and freeze files.

### Task 3: Actual saved segment and publication

Files: next ARTIFACTS/gameplay-continuations-2026-11-04-02 directory, AGENTS.md, STATUS.md, CODEX_TASK.md, PYTHON_DEVELOPER_HANDOFF.md and progress report.

- [x] Independently review both modules and run focused dependency tests without cohort tests.
- [x] Save same Game0000's bounded continuation before exact replay; archive stable source and policy manifests.
- [x] Record actual actions/outcomes and verification limits, preserve zero whole-game credit, publish branch and update draft PR.
