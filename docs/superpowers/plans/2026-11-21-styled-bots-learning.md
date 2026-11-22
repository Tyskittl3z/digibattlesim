# Styled Bots and Completed-Play Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a new fixed-build Ulforce cohort with distinct board-text pilots and completed-attack learning while preserving prior records.

**Architecture:** Add an explicit styled policy that reuses the legacy candidate grammar but has separate A/B ranking and supported-history influence. Attribute a completed attack's observed signed board reward at between-game commit; do not rewrite raw command colors. Preserve old replay at a pinned Git tag.

**Tech Stack:** Python standard library, unittest, Git, existing exact replay and judge modules.

**Spec:** `docs/superpowers/specs/2026-11-21-styled-bots-learning-design.md`

## Global Constraints

- Use only current legal candidates, public field, own hand, printed card text, and prior same-matchup history.
- Keep old campaign files immutable; zero certification until independent rules review.
- Preserve halted seeds and all earlier choices. Do not start final evaluation.

## Review Focus

- A/B manifests and observed choices must show different styles on the same public decision.
- History must affect a close choice with sufficient independent support, but never an unsupported choice.
- No opponent hidden card may enter either pilot's decision features.
- A completed attack may end by direct win without `END_ATTACK`; its reward still includes the terminal command.
- Old cohort replay must work at the pinned Git version.

---

### Task 1: Preserve old evidence and add styled policy

**Files:** Create `SOURCE/styled_board_text_player.py`; modify `SOURCE/fresh_learning_campaign.py`; test `SOURCE/test_styled_board_text_player.py`.

**Interfaces:** `StyledBoardTextPlayerBot(context, seat, learning_state, policy_seed, report_sha256)` and `styled_board_text_player_manifest(...)`; runner policy `BOARD_TEXT_HISTORY_STYLED`.

- [ ] Pin and publish Git tag at `88961f6` and document its replay command.
- [ ] Write tests for distinct manifests, current-field A/B ranking, supported-history influence, and strict old-policy compatibility; run and observe failure.
- [ ] Implement styled policy and explicit runner dispatch; run focused tests to green.
- [ ] Commit and push the checkpoint.

### Task 2: Learn from the complete attack

**Files:** Create `SOURCE/completed_play_reward.py`; modify `SOURCE/fresh_learning_campaign.py`; test `SOURCE/test_completed_play_reward.py`.

**Interfaces:** `attack_learning_rewards(commands) -> dict[int, float]`, keyed by declaration index, signed from that command's seat.

- [ ] Write tests for a successful check after a red declaration, opponent Counter response, terminal direct attack and unchanged command ratings; run and observe failure.
- [ ] Implement aggregation and apply it only to copied decision records during new-policy `commit_completed_game`; keep old policy commit unchanged.
- [ ] Run focused tests and exact replay; commit and push.

### Task 3: Verification and rules gate

**Files:** New campaign artifacts under a new path; update matchup review packet, not old evidence.

- [ ] Run full test discovery and classify/fix actual current failures with focused regressions.
- [ ] Verify official source identity, dates and encountered interactions. Leave separate independent certification open until evidence exists.
- [ ] Start a fresh sequential 60-game cohort only with fixed source/pilot/scorer hashes. Stop at first unresolved judge halt and preserve it.
- [ ] Record exact replay and zero certified credit unless independent rules review is complete; publish checkpoints.

### Task 4: Roadmap and final gate

- [ ] Summarize observed conditional alternatives, keeping immediate colors separate from strategy approvals.
- [ ] Request separate strategy and rules review on concrete trace evidence.
- [ ] Freeze and run 10,000 only when all gates pass; otherwise record blocked status and reason.
