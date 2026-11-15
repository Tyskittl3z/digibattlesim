# Ulforce Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track the steps below.

**Goal:** Start from two narrower, exact Ulforce workbook lists without granting unsupported card behavior or reusing matchup evidence.

**Architecture:** One source-pinned capability resolver recognizes only two exact context IDs plus their ordered source IDs. The diagnostic runner accepts an explicit context file and records it for replay; source-independent engine behavior remains unchanged.

**Tech Stack:** Existing Python standard library and unittest; no dependencies.

**Spec:** `docs/superpowers/specs/2026-11-02-ulforce-bootstrap-design.md`.

## Global Constraints

- Both mirror decks contain exactly 50 main cards and 4 listed eggs; no edits to lists.
- English-version worldwide rules; existing official source hashes stay pinned.
- Original queue, diagnostics, pilots and roadmaps remain preserved.
- No arbitrary context support, silent effect skipping, fabricated completions or certification.
- Other chat's catalog/import/UI files remain outside this increment.

## Review Focus

- A path argument is not authorization for changed cards, decks or rules.
- Source IDs are checked separately because matchup_id excludes them.
- Candidate enumeration must not preflight an unrelated unsupported action.
- Replay uses the recorded exact context and detects changed context bytes.
- A fresh context gets fresh pilots/seeds and never another pairing's roadmap/results.

### Task 1: Pin mirror inputs and centralize exact-context capabilities

**Files:** Create `SOURCE/selected_contexts.py`, `SOURCE/test_selected_contexts.py`; modify `SOURCE/battlefield_scope.py`, `SOURCE/main_actions.py`, `SOURCE/breeding_evolution.py`, `SOURCE/context_runtime.py`; add mirror artifact snapshots.

**Interfaces:** Produce `require_selected_context(context, root) -> MatchContext`, returning the matching locked context or raising RuntimeHalt with the existing selected-context error. Recognize original context/source IDs and the mirror ID/source IDs in the spec only. Include selected_contexts.py in execution_id hashing. The pure context input also lets runner preflight happen before runtime construction.

- [x] Write tests that execute mirror hard play/search and breeding evolution; reject changed source IDs, composition, rules or definitions without card/memory mutation.
- [x] Run `python -m unittest test_selected_contexts -q` from SOURCE and observe missing mirror support fail.
- [x] Implement the shared resolver; replace only the duplicated pair checks. Preserve card/effect/source validation and existing board scope.
- [x] Re-run the focused tests and existing action/board/breeding tests.

### Task 2: Bind diagnostics and replay to the selected context

**Files:** Modify `SOURCE/imported_attempts.py`; create `SOURCE/test_imported_context_selection.py`.

**Interfaces:** Extend `run_attempt(index, root=ROOT, max_commands=300, *, context_file=CONTEXT_FILE)` and `write_attempts(out, root=ROOT, count=60, max_commands=300, *, context_file=CONTEXT_FILE)`. Add CLI `--context-file`. Task 2 consumes the exact snapshot produced by Task 1; original defaults remain unchanged.

- [x] Write tests for explicit mirror context, recorded provenance, fresh pilot/seed identities, exact replay, changed-context rejection and original default behavior.
- [x] Observe failure before implementation with `python -m unittest test_imported_context_selection -q`.
- [x] Pass the selected path through loading, provenance, replay, cohort and CLI. Reject path escape outside root; verify saved context hash before replay. Preserve originals before replay and retain zero-credit fields.
- [x] Run new and existing runner tests; then run the full suite from SOURCE.

### Task 3: Review and demonstrate the new priority

- [x] Independently review the capability boundary and replay path for both contexts; fix any material findings with failing regressions first.
- [x] Run `python -m unittest discover -p 'test_*.py' -q` from SOURCE. Expected: all tests pass.
- [x] Inspect mirror readiness, then run 60 new diagnostic attempts with 30 starts each and exact replays. Preserve every halt and report actual totals.
- [x] Update AGENTS.md/STATUS.md with user delegation, development choice, checks and actual remaining blockers. Keep the original queue unchanged.
- [x] Commit the changes and publish the review branch with a draft PR, following the user's later GitHub publish request.

## Execution notes

Pre-flight: Task 2 consumes Task 1's snapshot path/context identity. Snapshot is
written before concurrent implementation; production files do not overlap.
Root implements Task 1 and a separate worker implements Task 2. The user has
delegated implementation choices and asked to proceed; no further approval is
needed for this reversible scope-preserving increment.

Task1: complete. Original per-action rejection labels retained for compatibility.
Task2: complete. Fresh worker implemented runner with failing regressions first.
Task3: tested335/335; mirror diagnostic02 60 HALTs,60 exact replays; original queue unchanged.
Final review: independent review found a preflight/rerun context-swap race. Two new regressions RED→GREEN; full suite335/335.
Ruling: add load_context_bytes and an internal expected-context argument so parsing/hashing use one immutable input and replay checks its expected identity/hash before any game action. This strengthens the stated replay contract.
Publication preparation: user requested a Python handoff and GitHub publish flow; finish checkpoint and publish a draft PR, preserving the default branch.

Publication complete: draft PR https://github.com/Tyskittl3z/digibattlesim/pull/1 against work. Review branch and isolated worktree retained; no merge performed.
