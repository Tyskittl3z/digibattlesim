# Saved Game0000 return checkpoint

## Saved return resolved; policy audit — 2026-11-04

Game0000 is **PAUSED_AFTER_SAVED_ACTION**: all **152 commands resolved**, B active
on turn10, memory−1, phase END_OF_TURN. Original seed12017913134550805276,
first playerA, all151 earlier successful commands/results/views and the complete
pre-return physical state/RNG were preserved. The saved effect57 selection was
retried exactly once: A:BT22-022#1 went to A deckbottom; A:EX13-002#2 and
A:EX1-013#2 went to A trash. No later end-turn processing or player choice ran.

**Policy correction:** both saved seat policies are
`fresh-untrained-uniform-random-reference-v1`, not verified as the user's two
bots. Their full historical identities remain preserved. The new bounded runner
invoked no policy and made zero new decisions; the reference history earns zero
user-bot evidence. Legacy named BotA/B code belongs to Jupitermon/Toho and has no
current imported-context adapter. Do not silently substitute either policy set.

**Verification:**62 focused tests passed (25.371s), including source-identity,
shared return dependencies, saved-choice preservation, forbidden policy calls,
and bounded replay tests. Independent actual-prefix/state-delta proof passed
(24.273s), with108 unique physical cards and unchanged return RNG. The latest
full-suite baseline remains **495 tests at aed966b**; this increment uses focused
checks. The full suite includes legacy60-game cohort tests, which were not run
under the user's current no-cohort instruction.

Latest checkpoint/evidence:
`ARTIFACTS/gameplay-continuations-2026-11-04-01/`. Full checkpoint exact-replay
verification is recorded in that directory's replay.json. Source bytes are
archived beside the saved record. No full game is complete; user-bot evidence,
accepted fact-finding games, approved lanes and final-match credit all remain0.
No routes were preloaded, cohorts launched, or strategic ratings assigned.

**Next boundary:** leave this checkpoint paused. Actual current-context bot
identities/adapters must be established before another player-policy decision.
Do not use imported_attempts.continue_attempt: it constructs fresh random
reference policies. Do not run the60/10,000 cohorts or attach positive/neutral/
negative or GREEN/YELLOW/RED ratings without defined, applicable scoring criteria.
