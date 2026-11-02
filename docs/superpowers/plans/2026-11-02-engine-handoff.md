# Engine Handoff Implementation Plan

> **For agentic workers:** use superpowers:executing-plans inline; user requested changes and GitHub update.

**Goal:** Prepare a trustworthy browser-to-engine handoff and enforce release checks.
**Architecture:** Read-only Python readiness builder; JS request exporter and Python validator; existing static app and offline builds consume the same snapshot.
**Tech Stack:** Python standard library, JavaScript, Node, Playwright/Chromium, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-02-engine-handoff-design.md

## Global Constraints
No gameplay/deck changes, automatic certification, fabricated matches/results, or reuse across pairings. Requests are PREPARE_MATCHUP only and never execute gameplay. Fail closed on malformed/stale dependencies.

## Review Focus
Raw/entry mismatch; locale-dependent hashes; unknown/swapped decks borrowing evidence; stale source files; client-supplied eligibility bypass; readiness unavailable in portable/offline builds.

### Task 1: Readiness and protocol
Files: TOOLS/engine/{readiness,request}.py, tests; APP/core/engine.js.
- [x] Write failing tests for real snapshot blockers/drift and JS-to-Python interchange, tampering, seat swap, unsupported decks and stale dependencies.
- [x] Implement deterministic readiness, stable identity ordering, strict raw reparse/hash and source binding validation, non-executing preflight CLI.
- [x] Run protocol/Node tests and verify expected blocked status with actual source evidence.

### Task 2: Browser integration
Files: APP/shell/app.js, index.html, build_pwa.py; APP/engine/readiness.json; browser tests.
- [x] Write failing real-browser tests for request download/Python validation, exact-pair readiness, unsupported-pair isolation and portable/offline snapshot.
- [x] Include readiness in release metadata/assets and report; render actual blockers and source drift; add Export simulation request.
- [x] Run full app regression checks and release verifiers.

### Task 3: Release automation and handoff
Files: TOOLS/verify_project.py, .github/workflows/verify.yml, docs, backup.
- [x] Add one-command checks and CI, with configurable Chromium executable.
- [x] Rebuild deterministically, run all software suites, independently review, fix material issues and document remaining mechanics blockers.
- [x] Commit code, create and verify updated portable/source/history backup, commit backup and push general-browser-simulator.

Verification: REPORTS/ENGINE_HANDOFF_2026-11-02.md. Preserve branch separation; user authorized pushing this branch.
