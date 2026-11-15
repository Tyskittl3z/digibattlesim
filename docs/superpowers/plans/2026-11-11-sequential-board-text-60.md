# Sequential Board-Text 60 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run 60 additional sequential Bot A/B games for the selected Ulforce pairing, carrying verified match history forward after each completed game.

**Architecture:** A small artifact driver wraps the existing source-pinned `run_game`, `replay_game`, and `commit_completed_game` APIs. It saves every bounded segment before replay, advances the cumulative model only after a terminal replay, and binds each game's prior report hash. A saved halt stops the batch at that game and seed for a focused card-text repair and exact-prefix migration.

**Tech Stack:** Python standard library; existing Digimon engine and test suite.

**Spec:** User request in this conversation: “okay now do that 60 times in a row”; current policy and evidence constraints in `AGENTS.md` and `STATUS.md`.

## Global Constraints

- Run 60 **additional** games, indices 0–59, starting from the two already completed history records.
- Use `BOARD_TEXT_HISTORY` for both seats; no named or random reference policy, route preload, hidden opponent cards, or randomized exploration.
- Use one selected pairing and a fresh campaign ID, deterministic unique seeds, and alternating first player 30/30.
- Load the immediate previous completed report and cumulative model before every new deal. Do not update either after a pause or halt.
- Preserve full before/after state, choices, judge and Bot C observations, ratings, RNG and source hashes. Replay each saved checkpoint exactly.
- A software completion has zero independently certified fact-finding credit. Do not run the 10,000-match evaluation or assert that the 60-game evidence gate is certified.
- Publish checkpoints frequently on the authorized draft branch.

## Review Focus

- Crash between record write, replay receipt and model update must not double-count a game or start the next.
- A halt must keep the same game index, seed, model and report hash.
- The first new game reads Game 0001 history, and the next reads that new game's report/model.
- Source changes during an unfinished game require exact-prefix migration; completed prior games stay immutable.
- Summary counts separate software terminal games from judge-certified fact-finding credit.

## Task 1: Durable sequential handoff

- [ ] Add a focused test that starts the new schedule from Game 0001 history, saves a bounded pause, and proves no model update or next game start.
- [ ] Run the test and observe the expected missing-driver failure.
- [ ] Add the artifact campaign driver with atomic segment, replay, report, model and status writes and strict handoff checks.
- [ ] Run focused tests and the appropriate full suite; fix failures.
- [ ] Commit and push the runner and first durable checkpoint.

## Task 2: Play through 60 games

- [ ] Run games sequentially and publish regular checkpoints. Each completed game must have a terminal record, exact replay, accepted judge receipts, Bot C observations, report, and a single model update.
- [ ] On each actual halt, preserve its record, investigate printed text/rules/Q&A, write a failing focused test, repair the minimal encountered mechanic, verify, migrate the same saved game, and continue.
- [ ] Stop only on a genuine unresolved block; report completed software games and remaining count precisely if that happens.

## Task 3: Cohort audit

- [ ] Verify indices 0–59, seed uniqueness, 30/30 first players, report/model chain, terminal records, all judge receipts, Bot C observations, exact replays and no random policy draws.
- [ ] Publish aggregate numerical outcomes and caveat that independent certification remains separate.
- [ ] Update `STATUS.md` and draft PR with the final actual counts. Leave the 10,000-match evaluation off.
