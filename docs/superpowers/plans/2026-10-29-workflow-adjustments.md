# Verification Workflow Adjustments Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. The user approved all five proposed adjustments with “make the changes”; continue without a new approval pause.

**Goal:** Enforce the agreed rules-version, coverage, review separation, lane-evidence and evaluation-restart requirements without changing decks or inventing rulings.

**Architecture:** Extend the current evidence gate with a small workflow-policy module. Snapshot rules/format and preregistered lane criteria in provenance, require separately bound rules/coverage/strategy evidence, and expose a pure resume-policy decision for the future frozen runner. Preserve old reports and generate a new current diagnostic version.

**Tech Stack:** Python 3.11+, standard library, unittest, existing JSON/gzip evidence.

**Spec:** User-approved five adjustments in conversation; `AGENTS.md` and `CODEX_TASK.md` as updated by Task 1.

## Global Constraints

- Exact loaded Jupitermon vs Amaterasumon/Toho decks remain unchanged.
- No guessed official rules, fake reviews, invented lane approvals or final results.
- Minimum 60 full judge-reviewed matches, balanced starts; targeted scenarios count as zero full matches.
- Rules legality and strategic effectiveness require separate evidence/review.
- Changed frozen gameplay invalidates all prior final results; retain halted seeds/traces and restart the whole evaluation under a new freeze.
- Use existing isolated checkout; no additional worktree.

## Review Focus

- A 62-match balanced cohort must not be rejected simply for exceeding 60; an unbalanced cohort still fails.
- Rules review cannot approve strategic lanes or substitute for legal alternative coverage.
- Missing/changed official snapshot documents and criteria must invalidate current provenance/eligibility.
- One winning outcome or two unevaluated alternative labels must never approve a lane.
- A HALT cannot be replaced with a new seed or resumed across a changed freeze.

### Task 1: Update the binding workflow and pin templates

**Files:** `AGENTS.md`, `CODEX_TASK.md`, `WORKFLOW.md`, `RULES/RULES_LOCK.json`, `RULES/INTERACTION_COVERAGE.json`, `ROADMAPS/APPROVAL_CRITERIA.json`.

- [x] Record the five accepted requirements and the exact approval/coverage/resume contracts.
- [x] Add an explicitly UNVERIFIED rules/format template and an empty unapproved coverage registry. Do not fill missing format, edition or official evidence from guesses.
- [x] Preregister structural lane criteria (at least two independent seeds, legal alternative comparisons, defined metric/objective and uncertainty); document that these are a minimum evidence floor, not statistical proof.

### Task 2: Enforce pinning, coverage and separate reviews

**Files:** `SOURCE/workflow_policy.py`, `SOURCE/evaluation_gate.py`, `SOURCE/match_evidence.py`, `SOURCE/test_workflow_policy.py`, `SOURCE/test_evaluation_gate.py`.

**Interfaces:** policy validators raise ValueError on missing/invalid evidence; `assess_eligibility(..., review_path=None, strategy_review_path=None)` returns structured blockers.

- [x] Write/run failing tests for minimum cohort/balance, unpinned rules, missing branch coverage, rules-only lane approval and absent alternative/uncertainty evidence.
- [x] Include rules lock, source documents and lane criteria in pre-cohort provenance; enforce source bytes/hash/edition/effective date/format pins.
- [x] Require every encountered decision/judge-path event to be linked to an explicit reviewed branch inventory. Legal branches need match/scenario evidence; scenarios never increase match counts.
- [x] Require a separate strategy-review file bound to current criteria, cohort, pilots and both roadmaps. Validate evaluated alternatives, trace references, metric definitions and uncertainty.
- [x] Run the complete suite after implementation.

### Task 3: Enforce final HALT/restart policy and preserve current evidence

**Files:** `SOURCE/workflow_policy.py`, workflow tests, `EVALUATION/README.md`, `ROADMAPS/README.md`, `STATUS.md`, new versioned reports/artifacts and progress ZIP.

**Interface:** `assess_resume(checkpoint, current_frozen_inputs, requested_seed=None) -> dict` returns BLOCKED_HALT, REPLAY_ORIGINAL_MATCH or RESTART_FULL_EVALUATION; it does not execute/resume matches.

- [x] Write/run failing tests for same-seed replay, changed-freeze invalidation and seed substitution rejection.
- [x] Implement the pure fail-closed policy; embed the policy contract in preparation output. Keep the actual frozen runner behind existing prerequisites.
- [x] Run code review, address material findings with regressions, then run full tests and a new 60-attempt diagnostic cohort. Preserve old evidence as historical.
- [x] Record verified counts and current blockers; package an updated downloadable project at completion. Do not claim any new rule certification or final matches.

## Execution ledger

- Baseline: local commit `5f5a6bd`, clean checkout before this work. User approval covers all five adjustments; no new worktree, deck edits or guessed rulings.
- Task 1 complete: revised binding requirements and `WORKFLOW.md`; rules/format and coverage remain explicitly UNVERIFIED; lane criteria preregistered before current cohort.
- Task 2 complete: initial new-policy/minimum62/separate-review regressions failed against the prior gate, then passed. Pin/source and criteria snapshots enter provenance; coverage/reviews bind it afterward to avoid circular hashes. Larger balanced cohorts require one review per actual record.
- Task 3 complete: missing sealed schedule first failed, then original10000 schedule hash/position validation passed; original seed, same-freeze rules halt and changed-freeze full restart tested. This is policy enforcement, not a live frozen runner.
- Code review: two Important coverage-binding defects reproduced with failing tests. Fixed foreign card/decision evidence, evidence outside its own encounters, and missing/ILLEGAL observed branches. Added equivalent same-context protection for strategy alternatives. Full suite 128/128 passed after the fix pass; no rules certification or second review claimed.
- New current cohort02: attempts60, starts30/30, software29/HALT31, full evidence replay60, final physical-state PASS60. Gate2/BLOCKED has only expected gameplay/pin/review/coverage/roadmap blockers. Prepared10000 distinct unplayed seeds, starts5000/5000; no freeze/final results.
- Prior maps preserved byte-for-byte in history01. Prior reports/cohorts remain historical; new workflow/source hashes require current evidence. Original simulation goals remain blocked on official rulings/format, legal interactions, full judge review and strategic evidence.
