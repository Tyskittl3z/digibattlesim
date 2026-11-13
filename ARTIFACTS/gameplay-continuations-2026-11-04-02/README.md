# Bot A aggressive / Bot B defensive: Game0000

The intended project players now have distinct fresh policies:

| Player | Style | Identity prefix |
|---|---|---|
| Bot A | Aggressive: winning attacks, security pressure and attacking bodies |3051db093e356d30|
| Bot B | Defensive: winning attacks, favorable visible battles, ready Blockers and reactive resources |6fe75b159762009e|

These are **untrained heuristic preferences**. They use each player's own public
view/hand, explicit reveals and pinned printed definitions. They use no game RNG,
old-matchup weights/routes/roadmaps or random-reference fallback. Every decision
records its bot identity, candidates, chosen value and rationale. Preference
rules are not outcome ratings or claims of optimal strategy.

The same Game0000 continued from the saved152-command checkpoint. Its original
seed **12017913134550805276**, first playerA, every earlier command/choice/result,
complete physical state and RNG were preserved and revalidated. The historical
random-policy manifests remain unchanged; new active profiles are separate.

**12 new commands resolved**, with11 recorded policy calls (A9/B2, including
effect ordering). B restored its suspended BT11Rina#2. A hatched, gained its
printed Rina start-main memory, and declared BT11Ulforce's attack on PLAYER.
Two A BT11Rinas paid suspension costs to reactivate Ulforce's current printed
WhenDigivolving effect. The first free-Tamer choice had no eligible target;
the second effect is still pending. No new attack damage has resolved.

Saved state: **164 successful commands, A turn11, MAIN, memory2**,
PAUSED_AFTER_NAMED_BOT_SEGMENT. Current effect64 (Ulforce free blue Tamer) has
priority over older inherited effect60. Pending effects must finish before the
attack Counter window is usable. This is an intentional budget pause; there
was no halt in this segment.

**82 focused tests passed** (57.599s), independent profile13 and continuation7
tests passed, and complete-record exact replay passed. Source hashes match
the102-file archive. The rules engine is unchanged. The latest full-suite
baseline is495 tests at aed966b; legacy cohort tests were not run here.

This game's historical random prefix means its whole outcome earns zero
named-bot/full-match/fact-finding/final credit. No cohorts were launched, routes
preloaded or outcome ratings assigned.

## Evidence and replay

- `bot-roster.json`: declared profiles, full identities and configuration.
- `bot-decisions.json`: the11 new policy calls and reasons.
- `game-0000-segment.json.gz`: complete saved record and predecessor lineage.
- `game-0000-turns.md`: all recorded commands and observed outcomes.
- `checkpoint.json`, `replay.json`, `verification.json`: state and verification.
- `independent-recorded-suffix-proof.py/.json` and
  `independent-recorded-suffix-review.md`: exact stored-command/state/RNG replay,
  card conservation and review against the pinned official wording/rules.
- `source-checkpoint.tar.gz`, `source-manifest.json`: the exact source used.
- `continue-named-bots.py`: bounded generation script; refuses overwrite.

From `SOURCE`, using this archived source and the repository's pinned context
and official-source files:

```python
import gzip, json
from pathlib import Path
from named_bot_continuation import replay_named_bot_continuation

path = Path('../ARTIFACTS/gameplay-continuations-2026-11-04-02/game-0000-segment.json.gz')
record = json.loads(gzip.decompress(path.read_bytes()))
assert replay_named_bot_continuation(record)['exact_match']
```

For a later authorized bounded segment, use
`named_bot_continuation.continue_with_named_bots(record, max_new_commands=12)`.
Keep the original record immutable and save its successor in a new directory
before replay. Do not use the historical random-reference continuation runner.
