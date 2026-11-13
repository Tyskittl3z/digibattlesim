# Bot C field tracker

Bot C is implemented and verified as a standalone field observer. Actual matches
remain **paused before the first fresh deal**. Learning, scoring, judge-ledger
recording and the fresh-game runner still need implementation/integration.

Bot C tracks:

- Battle-area bodies, stack tops and sources, orientation and public statuses.
- Breeding, security count, main/egg deck counts, hand count and trash.
- Memory, active player, phase, pending effects and attack window.
- Cumulative completed security checks, separately for each player.
- Physical card conservation and a chained audit record for each observation.

The player interfaces are `player_view(seat)` and `public_metrics()`. Views match
the existing runtime exactly: own hand plus public field/breeding/trash, with
count-only decks, security and opponent hand. Public metrics contain body counts,
total/largest stack sizes, source counts and successful-check totals. Bot C does
not assign strategic colors or a weighted tempo verdict.

`audit_snapshot()` and `observations` are **private audit data**. Never feed them
or `private-tracker-ledger.json.gz` to the acting players or their learner.
Unexpected private fields in projected structures are rejected, including
nested status/grant metadata. Public statuses currently support the existing
`cannot_suspend`, `cannot_unsuspend` and typed `effect_grants` schemas; a future
new public schema needs an explicit tracker update.

A successful-check counter requires a consistent completed security-card
confirmation and physical movement. Declarations, cancellations, failed
commands and direct wins at zero security add no checked card. A completed
check still counts when the attacker loses its security battle. A recovered
card may legitimately be checked again in a later attack.

The ledger records net movements between command boundaries and retains supplied
command/result steps. It does not invent intermediate movements. Stable entity
IDs preserve stack identity through normal evolution. Failed commands require
unchanged physical state and RNG and receive `FAILED_UNRATED`; invalid snapshots
leave the tracker unchanged. The hash chain establishes sequence/state
continuity; indistinguishable no-op retries need an external index to distinguish.

History counters start at zero in `start(snapshot)`. To reconstruct prior totals
on resume, replay the saved observations/commands from the original start;
remaining security count alone cannot establish past checks.

## Verification

**74 focused tests passed** (3.935 seconds), including 30 tracker regressions.
Independent review passed all 30 tracker tests (3.496 seconds). All 164 stored
commands from the historical game were checked against Bot C: exact states,
RNG, results, events and both player views, with all 108 cards conserved. The
observer ledger also reproduced exactly. Its historical check totals are A 0,
B 4; these are not fresh-run results.

No player policies were invoked and no new play, match, learning update or
strategic rating was generated. The historical record is unchanged. All 102
previous Python sources are unchanged; only the tracker and its test were added.
The latest full-suite baseline remains 495 tests at aed966b. This component used
focused checks because full discovery includes legacy match/cohort tests.

Files:

- `verification.json`, `archived-observer-proof.json`: actual checks and limits.
- `tracker-manifest.json`: source/context-bound tracker identity.
- `public-metrics.json`: the historical record's final public totals.
- `private-tracker-ledger.json.gz`: private archived verification observations.
- `source-manifest.json`, `source-checkpoint.tar.gz`: exact source and hashes.
- `verify-archived-record.py`: reproduces the stored-command observer proof;
  refuses to overwrite output files. Run in an isolated copy without generated
  outputs, using the pinned repository context/official source files.
- `pause-control.json`: fresh-game execution remains disabled.

From `SOURCE`, the focused verification command is:

```bash
python -m unittest test_field_tracker test_context_runtime test_match_context test_match_preparation test_named_player_bots -q
```

The tracker API is `FieldTracker(context)`, `start(snapshot)`,
`observe(command, before, after, result, judge_verdict)`, `player_view(seat)`,
`audit_snapshot()`, `public_metrics()`, `manifest()` and detached `observations`.
It consumes the engine's committed snapshots; card resolution and legality
remain the engine/judges' responsibilities.
