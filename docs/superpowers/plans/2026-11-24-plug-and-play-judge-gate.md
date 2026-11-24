# Plug and play rules gate implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let new imported matchups select pinned rules and fail closed on unreviewed actions before they change a game.

**Architecture:** A context-selected rules source replaces the fixed matchup path for new contexts. A separate semantic gate examines a proposed action and validates its transition on a copy of the runtime in strict mode; the existing transaction judge continues physical and provenance checks. Old experimental records retain their historical mode.

**Tech Stack:** Python standard library, `unittest`, existing `MatchContext`, `ContextRuntime`, `fresh_learning_campaign`.

**Spec:** `docs/superpowers/specs/2026-11-24-plug-and-play-judge-gate.md`

## Global Constraints

- Preserve all completed V2 records and their tag.
- Unknown card semantics halt on the original seed; they are never scored red or called illegal.
- No deck-specific action route list or new cohort run.
- Strict mode must not claim rules certification without separate review.

## Review Focus

- A missing or tampered rules source must halt before gameplay.
- A new matchup must not silently inherit the Ulforce rules path in strict mode.
- An unknown card effect must stop before state mutation.
- A post-apply semantic mismatch must leave the live state unchanged.
- Saved strict attempts must replay the same gate decisions and seed.

---

### Task 1: Context-selected rules evidence

**Files:** `SOURCE/rules_evidence.py`, `SOURCE/match_context.py`, `SOURCE/match_preparation.py`, `SOURCE/selected_mechanics.py`, rule-source call sites, `SOURCE/test_rules_evidence.py`.

- [ ] Write a failing test that a context's pinned alternate official rules file is used by opening preparation and mechanic bindings.
- [ ] Run the test and confirm it fails for the fixed-path lookup.
- [ ] Add `rules_evidence.comprehensive_rules(context, root, locator)` and pass the active context through rule-source call sites; retain the old fallback only for old experimental contexts.
- [ ] Run the focused tests and confirm the new source is selected and a missing or altered file fails.
- [ ] Commit the verified task.

### Task 2: Strict semantic gate and immutable trial

**Files:** `SOURCE/semantic_gate.py`, `SOURCE/fresh_learning_campaign.py`, `SOURCE/test_semantic_gate.py`.

- [ ] Write failing tests for an unsupported action halting before mutation, a supported opening transition being checked independently, and a mismatching trial transition preserving the live state.
- [ ] Run the tests and confirm the intended failures.
- [ ] Add a generic checker registry and strict mode to `run_game`; use a copied runtime for trial execution and bind gate receipts to saved commands and replay.
- [ ] Run focused runner/judge/gate tests, then the full repository suite; report any historical replay limitations by name.
- [ ] Commit and publish the verified change on the draft branch.
