# Engine Repair Migration Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Preserve a stopped fresh game's exact history across an explicitly reviewed engine repair, without starting actual gameplay.

**Architecture:** Separate original-build verification and current-build prefix revalidation, with immutable embedded parent lineage. Ordinary runner replay stays strict and verifies any lineage before resuming.

**Tech Stack:** Existing Python standard library; isolated subprocess for original imports.

**Spec:** docs/superpowers/specs/2026-11-10-engine-repair-migration-design.md

## Global Constraints

- Actual matches/60/10,000 cohorts remain paused; private fixtures earn zero credit.
- Preserve exact decks, named A aggressive/B defensive, model, choices and RNG.
- No policy calls during migration/replay; no failure retry during migration.
- No bypass of normal source pins; reject changed earlier game outcomes.
- No new card effects, routes, strategies or hidden player information.
- Root publishes checkpoints under the user's standing instruction; leave draft PR unmerged.

## Review Focus

- Failed or partially selected commands retain selected choices without being executed by migration.
- Source/evidence stamps change only at documented locations; state and semantic hashes never disappear.
- Rules, model, context and player changes fail even with recomputed outer hashes.
- Old replay imports verified old sources rather than cached current modules.
- Lineage remains validated after continuation and a second engine-only repair.

### Task 1: Explicit migration and runner lineage integration

**Files:** Create SOURCE/fresh_repair_migration.py and SOURCE/test_fresh_repair_migration.py; minimally modify SOURCE/fresh_learning_campaign.py.

**Interfaces:** Implement the exact public APIs and reviewed source-diff map in the spec. Reuse existing strict replay, judge and tracker APIs. Tests use separate temporary roots/source builds, never production campaigns.

- [x] Write failing behavior tests for a stopped private fixture from a genuinely different source build, exact migration, preserved selection and protected-change rejection; observe expected missing-feature failures.
- [x] Implement original subprocess verification, precise semantic comparison/rebinding, source/dependency protection and hashed immutable-parent lineage.
- [x] Wire lineage verification/preservation into ordinary replay/resume without relaxing existing source checks.
- [x] Add state/result/RNG/policy/rules/criteria/lineage tampering and repeated-repair tests; prove failure at the saved boundary is not retried by migration.
- [x] Run migration plus existing focused runner/tracker/scoring/learning/judge tests; fix observed failures.
- [x] Independent task and integration review; resolve material findings.

### Task 2: Private evidence and publication

**Files:** ARTIFACTS/repair-migration-2026-11-10/, latest STATUS/CODEX_TASK/PYTHON_DEVELOPER_HANDOFF/AGENTS, progress report.

- [x] Record a small actual cross-build private proof, exact source/dependency manifests and parent/child replay. Preserve historical production records.
- [x] Update run-disabled control and precise scope/limits; archive current Python source bytes.
- [x] Run final focused checks once on frozen final sources, check archive agreement and diff hygiene.
- [x] Commit/push concrete checkpoint and update draft PR #1; report actual counts with zero production match/training credit.

## Final evidence

173 focused tests passed in 73.877 seconds on frozen final sources. Initial
review found a repaired-cache defect; one correction round added source-only
current workers and regression coverage. Scoped rereview independently confirmed
the original reproduction now fails correctly, with no residual blocker. The
separate durable private proof passed in 4.920 seconds. Final artifact audit
verified 114 current sources, 112 private original sources, exact three-file
approved changes and 68 unchanged dependencies. Evidence and current disabled
control: `ARTIFACTS/repair-migration-2026-11-10/`. Actual games/updates/credit are 0.
