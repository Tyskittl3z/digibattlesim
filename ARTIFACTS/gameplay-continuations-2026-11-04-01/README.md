# Game0000: selected return resolved, paused

Original seed **12017913134550805276**, first player A. The 151 earlier
successful commands, choices, results, public views, complete physical state and
RNG were revalidated. The stored B/effect57 choice `A:BT22-022#1` was then
resolved exactly once. There are now **152 successful commands**.

BT22-022 went to **A's deck bottom**. Its EX13-002 and EX1-013 sources went to
**A's trash**. B remains active on turn10 at memory−1; phase END_OF_TURN is open.
Later end-turn processing has not run. All108 cards are accounted for. The return
changed no RNG state.

Both historical seat policies are
`fresh-untrained-uniform-random-reference-v1`. They are not verified as the
user's two bots. Full identities are preserved in `policy-audit.json` and the
record. The new runner invoked **zero policies**, made **zero new decisions**,
and stopped immediately after the selected return. Other named BotA/B code in
the repository belongs to the legacy Jupitermon/Toho matchup; no current-context
adapter was found. Establish the intended bots before another player decision.

**62 focused tests passed**, and complete-record exact replay passed.
`state-delta-proof.json` checks the entire expected state change. The independent
proof is in
`../gameplay-continuations-2026-11-03-12/rules-reviews/turn10-private-return-proof.json`;
its official sources are in the adjacent `turn10-actual-return-official-review.json`.
Source archive hashes match the source used for the checkpoint and both proofs.
The latest full-suite baseline remains495 tests at aed966b; this increment's
full suite was not run because it includes legacy60-game cohort tests.

User-bot evidence, full-game, fact-finding, roadmap and final credits remain0.
No routes were preloaded, cohorts launched, or strategic ratings assigned.
Scoring criteria have not been defined and bound to this game.

## Files and replay

- `game-0000-segment.json.gz`: complete paused record, with predecessor lineage.
- `checkpoint.json`: concise state and policy/evidence accounting.
- `game-0000-turns.md`: recorded commands and observed outcomes.
- `policy-audit.json`: historical identities and current missing bot adapter.
- `replay.json`, `state-delta-proof.json`, `verification.json`: actual verification.
- `source-checkpoint.tar.gz`, `source-manifest.json`: frozen source bytes/hashes.
- `resume-selected-return.py`: exact bounded generation script; refuses overwrite.

From this repository's `SOURCE` directory, with the archived source restored in
an isolated checkout containing the pinned context/official source files:

```python
import gzip, json
from pathlib import Path
from recorded_action_checkpoint import replay_selected_action

path = Path('../ARTIFACTS/gameplay-continuations-2026-11-04-01/game-0000-segment.json.gz')
record = json.loads(gzip.decompress(path.read_bytes()))
assert replay_selected_action(record)['exact_match']
```

Keep the existing diagnostic `continue_attempt()` runner out of this paused
checkpoint: it constructs random reference policies and continues selecting new
actions. This checkpoint uses `recorded_action_checkpoint.py` and a separate
paused-record schema expressly to preserve the policy boundary.
