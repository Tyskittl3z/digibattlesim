# Frozen 10,000-match Evaluation Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the fail-closed runner that can execute the exact balanced 10,000-match schedule after the existing eligibility gate passes.

**Architecture:** A Python standard-library module creates a hash-bound freeze, writes one atomic gzip evidence record per scheduled match, advances an atomic checkpoint only after validation, and emits a numerical final summary only after exactly 10,000 credited matches. The current blocked gate remains authoritative, so this implementation cannot start real final play yet.

**Tech Stack:** Python 3.11+, unittest, JSON, gzip, SHA-256, `os.replace`/`fsync`.

**Spec:** `docs/superpowers/specs/2026-10-29-frozen-evaluation-design.md`

## Global Constraints

- Exact loaded Jupitermon versus Amaterasumon/Toho decks only; no deck edits or advice.
- No real final match may run unless `assess_eligibility` is eligible and every frozen input hash is current.
- Preserve the exact schedule position, index, seed and starting player; no replacement seeds.
- Rules HALT stops the run. Infrastructure recovery replays the same original match and verifies it before credit.
- Changed frozen inputs invalidate all prior final results and require a new freeze and full restart.
- No learning, exploration, rules certification or provisional win rate is introduced by this runner.

## Review Focus

- A forged eligible flag without the complete gate identity must not create a freeze.
- A schedule with 10,000 rows but one changed seed, duplicate or 5,001/4,999 starts must fail.
- A compressed record whose body identity differs from its schedule row must not advance the checkpoint.
- An interruption between record write and checkpoint write must replay the same seed and converge without duplicate credit.
- A run with 9,999 valid records or one HALT must never emit a completed final summary.

---

### Task 1: Freeze and immutable schedule

**Files:**
- Create: `SOURCE/frozen_evaluation.py`
- Create: `SOURCE/test_frozen_evaluation.py`

**Interfaces:**
- Consumes: `assess_eligibility`, `provenance`, `validate_record`, `workflow_policy.FROZEN_COMPONENTS`, and `SEEDS.json.gz`.
- Produces: `create_freeze(root, cohort_dir, preparation_dir, output, review_path, strategy_review_path) -> dict` and `load_freeze(run_dir) -> tuple[dict, list[dict]]`.

- [x] **Step 1: Write failing freeze tests** for a blocked gate, forged/imbalanced schedule, schedule-file hash mismatch, and a valid synthetic eligible freeze containing all seven component hashes.
- [x] **Step 2: Run the focused tests and confirm they fail because the module/API is missing.**
- [x] **Step 3: Implement atomic canonical writes, schedule validation and freeze creation.** Refuse an existing output directory and bind engine, rules/format, decks, pilots, criteria, roadmaps and schedule to current bytes.
- [x] **Step 4: Run focused and full suites; confirm all pass.**
- [x] **Step 5: Commit Task 1.**

### Task 2: Exact-seed execution and checkpoint recovery

**Files:**
- Modify: `SOURCE/frozen_evaluation.py`
- Modify: `SOURCE/test_frozen_evaluation.py`

**Interfaces:**
- Consumes: Task 1 freeze and `record_match(index, provenance_sha256)`.
- Produces: `run_frozen(run_dir, match_runner=record_match, stop_after=None, interruption_hook=None) -> dict` and `resume_frozen(run_dir, match_runner=record_match) -> dict`.

- [x] **Step 1: Write failing tests** for record/schedule identity, one credited match, preserved rules HALT, no checkpoint advance on invalid record, an orphan record after simulated interruption, exact-seed replay, and changed-input full-restart rejection.
- [x] **Step 2: Run focused tests and confirm each new behavior fails for the expected missing implementation.**
- [x] **Step 3: Implement minimal execution/checkpoint logic.** Write gzip with deterministic mtime, validate before atomic checkpoint advance, replay an orphan at the same position, and stop on HALT without substituting a seed.
- [x] **Step 4: Run focused and full suites; confirm all pass.**
- [x] **Step 5: Commit Task 2.**

### Task 3: Complete-run numerical report and CLI

**Files:**
- Modify: `SOURCE/frozen_evaluation.py`
- Modify: `SOURCE/test_frozen_evaluation.py`
- Modify: `EVALUATION/README.md`
- Modify: `STATUS.md`

**Interfaces:**
- Consumes: 10,000 validated record manifests from Task 2.
- Produces: `summarize_completed_run(run_dir) -> dict`, `FINAL_RESULTS.json`, and CLI subcommands `freeze`, `run`, `resume`, `status`.

- [ ] **Step 1: Write failing tests** proving that 9,999/HALT runs cannot finalize and a synthetic complete balanced run reports exact W/L, starts, first-player wins and turn distribution without recommendations.
- [ ] **Step 2: Run focused tests and confirm expected failures.**
- [ ] **Step 3: Implement streaming validation/aggregation and CLI.** Finalize only when all schedule positions are uniquely credited and hash-valid; never infer missing results.
- [ ] **Step 4: Document the operational command and current blocked status.** Do not run the real schedule.
- [ ] **Step 5: Run focused/full tests and a blocked real freeze CLI check; confirm the CLI refuses current evidence before playing a match.**
- [ ] **Step 6: Commit Task 3.**

### Task 4: Review and handoff

**Files:**
- Modify: `REPORTS/` with a versioned runner-verification report.
- Modify: `CURRENT_SHA256SUMS.txt`.

**Interfaces:**
- Consumes: all prior tasks and the current blocked evidence.
- Produces: reviewable software verification and an exact remaining-blocker list.

- [ ] **Step 1: Build a final review package and obtain a fresh code review.**
- [ ] **Step 2: Re-grade findings; fix Critical/Important findings with RED-to-GREEN regressions and rerun the whole suite once.**
- [ ] **Step 3: Run final verification, refresh checksums, record actual test/CLI results and commit.**
- [ ] **Step 4: Report the concrete next external actions: publish official-site access, select format/region/language, and supply independent rules/strategy review.**
