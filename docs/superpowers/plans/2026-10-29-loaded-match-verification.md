# Loaded Match Verification Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. The user explicitly requested autonomous continuation; do not insert design or plan approval pauses.

**Goal:** Resolve only the loaded matchup's verified interactions, and produce inspectable evidence that cannot be mistaken for certified training or a frozen evaluation.

**Architecture:** Retain the existing Python engine and exact decks. Add physical-card invariants, complete state/provenance records, and a separate fail-closed eligibility gate. Rule changes require official evidence; unavailable rulings remain explicit blockers.

**Tech Stack:** Python 3.11+, standard library, unittest, gzip, SHA-256.

**Spec:** `AGENTS.md`, `CODEX_TASK.md`, `STATUS.md`.

## Global Constraints

- Loaded decks only; no deck edits, advice, prior matchup data, or universal engine work.
- 60 complete judge-reviewed matches, 30 starts per seat, before final evaluation eligibility.
- No rule guesses, hidden substitutions, forced optional declines counted as learning, or fabricated certification.
- Final evaluation: 10,000 actually played matches, 5,000 starts per seat, frozen inputs, no learning.
- Existing isolated cloud checkout; no additional worktree. Preserve imported reports and logs.

## Review Focus

- A duplicate card replacing a missing card must fail even when totals remain 54.
- Halt output must preserve the exact stack, pending effects, memory, and deterministic seed.
- Missing review evidence, empty evidence, or an obsolete engine hash must block evaluation.
- A replay or software completion must never approve a strategic lane or certify a match.
- Missing official rulings must leave affected choices UNKNOWN, not invented or classified ILLEGAL.

### Task 1: Preserve and reproduce the handoff

**Files:** `ARTIFACTS/baseline-2026-10-29/`, imported source and reports (unchanged).

- [x] Verify archive/checksums; run the existing suite (78 tests passed).
- [x] Reproduce 60 attempts; preserve compressed cohort and original source hashes (55 software completions, 5 halts).

### Task 2: Enforce physical identity and capture exact evidence

**Files:** Create `SOURCE/match_evidence.py`, `SOURCE/test_match_evidence.py`, `SOURCE/test_physical_integrity.py`, `SOURCE/test_prefix_adapter.py`. Preserve historical `full_match_attempt.py` (see execution ledger).

**Interfaces:** `snapshot_match(match) -> dict`; `run_evidence_cohort(output: Path, count: int = 60) -> dict`.

- [x] Write and run failing tests: same-size duplicate/missing card, invalid stack top, memory outside [-10,10], and missing structured final state.
- [x] Validate the multiset of exact loaded physical copies and stack anchors; preserve every persistent gameplay field in snapshots, including pending queues and RNG state.
- [x] Stream deterministic gzip per-match records with source/deck/data hashes and exact halt states; rerun all 60 twice and compare replay hashes.
- [x] Run `python -m unittest discover -p 'test_*.py' -q`; preserve outcomes without promoting certification.

### Task 3: Resolve rules only against authoritative evidence

**Files:** `RULES/` evidence index and judge audit, targeted tests/engine paths only if verified.

- [ ] Retrieve official Susanoomon, Decode, replacement/prevention, and encountered optional attacking rules; snapshot URLs, bytes, hashes, and exact citations.
- [x] Extract all five original target stacks and active replacement sources from the preserved baseline, and enumerate encountered unmodeled optional attacks.
- [ ] For each verified interaction, write a failing focused test, implement the exact controller choices and resolution, then run affected regressions and the entire 60-match cohort.
- [x] If official evidence remains inaccessible, preserve a precise unresolved-interaction ledger and continue independent work; do not alter rule resolution from speculation.

### Task 4: Prepare roadmap and frozen-evaluation gates

**Files:** `SOURCE/evaluation_gate.py`, `SOURCE/test_evaluation_gate.py`, `ROADMAPS/`, `EVALUATION/`.

**Interfaces:** `assess_eligibility(root: Path, cohort_dir: Path, review_path: Path | None) -> dict`.

- [x] Write failing tests: software-only cohort rejected; stale hashes, missing reviews, incomplete snapshots, unsupported choices, or unknown roadmap entries rejected.
- [x] Hash both deck files, card/cost snapshots, complete source and both pilot/roadmap identities; require judge reviews bound to exact transcript hashes and official evidence. No favorable reviews exist.
- [x] Save situational lane candidates with objective conditions and trace provenance; retain UNKNOWN until legal/strategic review exists. Keep RED distinct from ILLEGAL.
- [x] Save blocked preparation output and balanced disjoint final seed schedule. Do not create a fake freeze or final results. A live 10,000 runner is deferred until eligibility actually passes.
- [x] Run the complete suite, independent code review, and real CLI checks; update STATUS and a new versioned report with exact verified counts and external blockers.
