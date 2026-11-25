# Exact replay version for the 60 software games

The original campaign's source, policy, scorer, rules and artifacts are pinned at Git tag `ulforce-60-software-v1` (commit `88961f6`). Later pilot/scoring changes are a new software version and do not rewrite these games. To replay the old records, use an isolated checkout of the tag:

```sh
git worktree add --detach /tmp/ulforce-60-replay ulforce-60-software-v1
cd /tmp/ulforce-60-replay/SOURCE
python - <<'PY'
import gzip
import json
from pathlib import Path
from fresh_learning_campaign import replay_game

root = Path.cwd().parent
campaign = root / 'ARTIFACTS/ulforce-prospective-60-2026-11-17'
for index in range(60):
    game = campaign / f'game-{index:04d}'
    record_path = sorted(game.glob('segment-*.json.gz'))[-1]
    with gzip.open(record_path, 'rt') as stream:
        record = json.load(stream)
    assert replay_game(record, root)['exact_match'], record_path
print('60 terminal records replay exactly')
PY
```

The existing `replay-*.json` files also preserve the original segment-by-segment receipts. This tag is software evidence only; its records carry zero independent rules-certification credit.
