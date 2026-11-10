# Learning Runner Integration Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Integrate Bot C with scoring, named-player learning and a fresh-game runner while actual matches remain paused.

**Architecture:** Independent public-board scorer, frozen per-game learner, transaction/source/physical judge receipts, and deterministic fresh runner. Existing card mechanics and historical runners remain unchanged.

**Tech Stack:** Python3.12 standard library.

**Spec:** docs/superpowers/specs/2026-11-04-fresh-learning-campaign-design.md plus ARTIFACTS/pre-match-setup-2026-11-05/learning-design-wip.md and verified Bot C API.

## Constraints and Review Focus

- No actual fresh match/cohort or historical forward choices; short private fixtures only.
- Public views/metrics only to players; private audit contents never become features.
- Colors reflect observed board/tempo/memory effects, not win probabilities or roadmap approval.
- Procedural changes retain their measured color but are not learning decisions; singleton choices are recorded without strategic credit.
- Model is frozen within each game; completed eligible games update once by stable logical campaign/context/index/seed identity.
- Save and restore engine RNG, policy RNG, selected actions and pending selections; validate all replay hashes and prefix results before resuming.
- Judge receipts name automated checks honestly and never imply independent full-game certification.

## Tasks

- [ ] Finish interaction_scoring.py/tests and pin explicit provisional criteria JSON; regress cost aliases, private fields, successful checks and procedural semantics.
- [ ] Implement interaction_learning.py/tests: strict persistent state, atomic deduplicated updates, public normalized keys, explicit named exploration/RNG and frozen model snapshots.
- [ ] Implement judge_ledger.py/tests: match real transaction event, verify official-source pins/bindings and independently count physical cards; rejected software gaps stay separate from illegality.
- [ ] Implement fresh_learning_campaign.py/tests: fresh opening, Bot C views, named learners, judged transitions/ratings, immutable seed schedule and exact pause/failure/generator resume.
- [ ] Independently review modules and run focused integration checks using private fixtures only.
- [ ] Publish source/criteria/test evidence and run-disabled setup control; update status/handoff/draft PR. Do not claim fresh-game completions.
