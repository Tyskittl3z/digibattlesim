# Bot C Field Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Implement and verify Bot C without starting an actual match.

**Architecture:** A deterministic independent observer validates snapshots, derives private audit deltas and redacted public views, and hashes a sequential ledger. Existing engine and policies remain unchanged.

**Tech Stack:** Python3.12 standard library.

**Spec:** docs/superpowers/specs/2026-11-10-bot-c-field-tracker-design.md

## Global Constraints

Actual matches/cohorts stay paused. No new scoring, learning, judge or runner implementation. Old records remain immutable. Unit fixtures/replay proofs earn zero match credit.

## Review Focus

- Hidden security/deck order/opponent hands never enter player views.
- Inventory includes every source/breeding/resolving Option exactly once.
- Before/after identity changes or stale snapshots fail before ledger commit.
- False Security claims cannot inflate cumulative checks.
- Stable entities, hashchain and detached outputs preserve audit integrity.

### Task1 Tracker and regression tests

Files: SOURCE/field_tracker.py, SOURCE/test_field_tracker.py.

Interface: FieldTracker(context).start(snapshot), observe(command,before,after,result,judge_verdict), player_view(seat), audit_snapshot(), public_metrics(), manifest(), detached observations property.

- [x] Copy archived16test draft into SOURCE; observe expected absent-module failure.
- [x] Implement minimally; add strict successful-check and after-identity regressions.
- [x] Run focused tracker tests and independent privacy/integrity review; freeze source.

### Task2 Verification and publication

Files: ARTIFACTS/bot-c-2026-11-10/, current status/task/handoff.

- [x] Run relevant existing dependency tests without legacy actual-match/cohort tests.
- [x] Replay only saved commands into the observer; compare views, counts, state/RNG and deterministic ledger. Preserve old files and forbid player-policy calls.
- [x] Save tracker manifest, evidence, source hashes and run-disabled control state.
- [x] Publish verified component and updated draft PR with actual checks and remaining preparation work.
