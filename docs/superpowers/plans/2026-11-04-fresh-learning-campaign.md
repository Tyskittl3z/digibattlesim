# Fresh Learning Campaign Implementation Plan

> **PAUSED BEFORE FIRST MATCH (2026-11-05):** User requested a pre-match pause.
> No fresh game, deal or learning update has started. Usage reset does not lift
> the pause. Preparation drafts are saved under
> ARTIFACTS/pre-match-setup-2026-11-05/; implementation and verification remain
> pending. Do not execute this plan's gameplay steps until the user continues.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Start fresh named-bot games with Bot C tracking, judge records, defined interaction colors and learning across60 completed games.

**Architecture:** Separate tracker, learner/ratings and fresh runner. Use existing engine transactions/candidates; preserve selected failures and all old archives. Advance scheduled game/learning state only after actual terminal and required validation.

**Tech Stack:** Python3.12 standard library.

**Spec:** docs/superpowers/specs/2026-11-04-fresh-learning-campaign-design.md

## Global Constraints

60fresh scheduled seeds, starts30/30; no reference policies or past-matchup training. Players get own hand/public state only. No fabricated game outcomes/probabilities/certificates. Keep failed choices/seeds.10,000evaluation stays off. Publish checkpoints frequently.

## Review Focus

- Tracker conservation includes stacked cards and resolving Options; hidden contents stay private.
- Learners do not train on failed/paused games or repeatedly count the same game.
- Resume restores selected action and independent policy RNG, never rerolls.
- Color measurements, empirical win association and legality verdicts stay distinct.
- Source/model/criteria/schedule hashes bind every result and replay.

### Task1 Bot C tracker

Create SOURCE/field_tracker.py and tests. FieldTracker(context).start(snapshot), observe(command,before,after,result,judge_verdict), player_view(seat), audit_snapshot(), manifest(). Tests pin exact public_view equivalence, conservation, chain/stale guards, rollback and detached outputs. Implement minimally and freeze.

### Task2 ratings and learning

Create SOURCE/interaction_learning.py and tests. Define criteria/score_transition(before_view,after_view,seat) with components, labels and confidence; no probability claim. LearningState canonical export/hash/update_completed(game_id,winner,decisions,eligibility). LearningPlayerBot(context,seat,learning_state,policy_seed) compatible manifest/choose/bottom_order/decision_log plus RNG export/restore. Tests coldstart, supported updates, deduplication, no hidden info, no halted training, replayable exploration and no game RNG use. Freeze.

### Task3 fresh runner and checkpointed campaign

Create SOURCE/fresh_learning_campaign.py and tests. Fresh seed schedule/context initialization, opening/redraw phases, existing current-state windows, tracker views and transition logs, source/legality records, ratings, explicit saved-choice/model/RNG resume and exact replay. Save one game before replay. Cohort manifest tracks60planned, completed/paused/halts separately; stop first unresolved gap. Never substitute reference policies.

### Task4 actual encounters and publication

Run fresh game0 with the pinned schedule. Save every actual gap, independently judge exact wording/timing, regress and repair only that encountered behavior, resume original selection. Complete actual games sequentially where supported, train only from completed validated results, verify tracker/replay. Archive source/model/criteria/state and update status/handoff/draft PR with exact counts and limits; never claim60 complete until actually complete.
