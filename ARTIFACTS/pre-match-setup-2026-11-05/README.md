# Paused before the first fresh match

**No fresh match or opening deal has started.** The user asked to pause before
the match. A later usage reset leaves that pause in effect. No learning update,
interaction rating or 60-game run has occurred. The10,000-match evaluation is off.

The intended fresh setup is:

- Bot A: aggressive player.
- Bot B: defensive player.
- Bot C: field tracker for battle stacks, breeding, security, deck counts and
  trash, with private audit data kept separate from each player's inputs.
- Judges: action/rule checks recorded separately from strategic labels.
- Colors: observed board changes, removal/incapacitation, successful Security
  checks and actual memory efficiency.
- Tempo: cards in play, stack sizes and completed successful Security checks.

Numeric scoring weights and aggregation are still drafts. No provisional
weights have been used to rate a live interaction. No global-cheapest or winning
probability claims are made.

## Saved preparation

- `pause-control.json`: explicit run-disabled state and zero fresh-game counts.
- `prepared-source/SOURCE/test_field_tracker.py`:16 drafted tests.
- `prepared-source/SOURCE/test_fresh_learning_campaign.py`:7 drafted tests.
- `learning-design-wip.md`: proposed APIs, scoring components and learning rules.
- Repository design/plan:
  `docs/superpowers/specs/2026-11-04-fresh-learning-campaign-design.md` and
  `docs/superpowers/plans/2026-11-04-fresh-learning-campaign.md`.

Tracker, learner/scorer, fresh runner and judge-ledger implementations remain
pending. Two initial TDD checks failed as expected because their modules do not
exist; the remaining drafts are unrun. The drafts are parked outside live SOURCE
so they do not change its current executable/test state. Do not run them in place;
their paths assume restoration into SOURCE when implementation resumes.

Live source remains unchanged from220afab, whose82 focused tests passed. The
last full-suite baseline remains495 tests at aed966b. This save operation ran no
games or tests.

The prior164-command mixed-history Game0000 is preserved at
`ARTIFACTS/gameplay-continuations-2026-11-04-02/` and contributes no data to the
fresh learning run. No fresh schedule/seeds have been locked.

**Remain paused until the user says to continue.** On resumption, implement and
verify the tracker, criteria, learner and fresh runner before the opening deal;
preserve any actual selected gap and seed instead of skipping it. Save progress
without starting a match while this pause is active.
