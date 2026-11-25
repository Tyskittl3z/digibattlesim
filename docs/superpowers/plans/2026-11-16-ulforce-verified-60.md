# Ulforce Rules Review and Fresh 60 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Review the selected 123129 vs 122110 mirror against official English worldwide evidence and run 60 newly recorded, balanced, rules-verified Bot A/B matches without altering historical archives.

**Architecture:** Keep the explicit-context engine and the existing board-and-card-text pilots. Pin a matchup-scoped rules snapshot, close reachable mechanic and choice branches with focused scenarios, then run the existing sequential campaign driver in a new output directory. Treat exact replay, automated judge checks, semantic rules review, and strategy review as separate evidence.

**Tech Stack:** Python 3.12, `unittest`, JSON and gzip artifacts, official cached Digimon card pages and Comprehensive Rules.

**Spec:** `docs/superpowers/specs/2026-10-30-ex13-engine-design.md`; `WORKFLOW.md` supplies the accepted verification contract.

## Global Constraints

- Preserve the exact A/B decklists, two initial match histories, Bot A/B board-and-card-text policy, Bot C observations, 60-seed schedule, and prior archives.
- English-version worldwide format; official card wording, rules and Q&A govern each legal action.
- Every HALT keeps its seed and trace. Scenarios count as zero matches; software completion alone gives zero certified fact-finding credit.
- No roadmap approval or 10,000-match evaluation is part of this plan.

## Review Focus

- False `if` conditions that become true before activation must remain pending until eligible or explicitly settled.
- Ordinary and deferred attacks must settle ineligible child effects and resolve Piercing before `END_ATTACK`.
- Direct scenario dispatch must not be mistaken for a legal game action.
- Unchosen paid/decline branches need targeted rule evidence; an unchosen branch cannot be declared covered by a match.
- A changed engine or rules snapshot invalidates the prospective cohort and requires a new archive from game zero.

---

### Task 1: Lock official matchup sources

**Files:** Create `RULES/matchups/123129-vs-122110/RULES_LOCK.json`; add a source-audit note under `RULES/reviews/123129-vs-122110/`; test in `SOURCE/test_matchup_rules_lock.py`.

**Interfaces:** The lock contains official URLs, local files, SHA-256, editions and effective dates for the selected format, rules, restrictions, errata, card text and Q&A. The cohort consumes its canonical hash before game zero.

- [ ] Verify cached and current official source bytes, effective dates, format and applicability to all 22 loaded card numbers.
- [ ] Write a failing lock-validation test for missing/changed source bytes or unsupported effective dates.
- [ ] Add the narrow lock and validation; keep status UNVERIFIED if any required pin is missing.
- [ ] Run the focused test and record the exact lock hash.

### Task 2: Close reachable mechanics and choices

**Files:** Modify only the in-scope `SOURCE/` handlers and focused tests identified by the effect/choice review; update `RULES/reviews/123129-vs-122110/` with citations and branch status.

**Interfaces:** Every encountered effect ID and conditional path has an official-source rule verdict, legal alternatives, and a deterministic scenario where archive matches do not exercise the branch.

- [ ] Complete the per-card audit of the 45 archived effect IDs and their choice paths, including cancellation events.
- [ ] For each confirmed defect, write a failing scenario test, make the smallest source fix, then run the relevant focused suite.
- [ ] Resolve or mark UNKNOWN each unchosen paid/decline branch and the direct-dispatch boundary; do not label UNKNOWN as verified.
- [ ] Record source citations, decision alternatives and exact test/trace references in the review ledger.

### Task 3: Validate prospective match recording

**Files:** Create a new campaign driver under a new `ARTIFACTS/` directory; modify `SOURCE/fresh_learning_campaign.py` and focused tests only if a concrete recording defect is found.

**Interfaces:** The driver pins source/rules/criteria/pilot hashes, uses the existing 60 balanced seeds and initial two-game history, and writes each segment before exact replay or model update.

- [ ] Write a failing test for any missing provenance, hidden policy substitution, replay or checkpoint identity gate found in the runner review.
- [ ] Repair those gates and run a small noncredit smoke scenario with exact replay.
- [ ] Freeze the prospective software/rules snapshot and create an empty, new campaign archive.

### Task 4: Run and review 60 games

**Files:** New `ARTIFACTS/<cohort>/` game segments, replay receipts, reports and a cohort-level rules-review artifact; `RULES/INTERACTION_COVERAGE.json` or a matchup-scoped equivalent if the existing event schema cannot express this runner.

**Interfaces:** Exactly 60 terminal games, 30 starts per seat, accepted actions, Bot C observations, zero unresolved judge HALTs, exact replay and a separate semantic rules verdict per encountered path.

- [ ] Run the new sequential driver from index zero; on a HALT preserve its seed/trace, repair by test first and restart the evidence cohort under a new engine snapshot.
- [ ] Verify all 60 terminal records, seed uniqueness and balance, card conservation, judge receipts, Bot C observations, policy identities and exact replay.
- [ ] Review the complete transcript/path inventory against the locked official sources; bind reviewed alternatives and targeted scenarios. Record independent rules verdicts.
- [ ] Credit only matches that pass the rules review; if any gate remains open, report the exact blocker and keep certified count at zero.

### Task 5: Publish the evidence checkpoint

**Files:** `STATUS.md`, the new cohort summary, this plan's ledger and a draft GitHub PR based on the prior review branch.

- [ ] Run focused and repository verification; report every failure by name and distinguish historical replay fixtures.
- [ ] Commit/push each verified milestone and publish a draft PR with actual match counts, source hashes and unresolved gaps.
