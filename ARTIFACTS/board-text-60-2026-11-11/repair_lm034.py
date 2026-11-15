"""Migrate the saved LM-034 halt through an exact-prefix, source-only repair."""
import argparse
import gzip
import json
from pathlib import Path

from campaign import DEFAULT_OUT, ROOT, _json_bytes, _record, _save, _segments
from fresh_learning_campaign import _source_bytes, replay_game
from fresh_repair_migration import migrate_repaired_game
from match_context import canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-root', type=Path, required=True)
    args = parser.parse_args()
    game_dir = DEFAULT_OUT / 'game-0000'
    paths = _segments(game_dir)
    previous = _record(paths[-1])
    if (previous['status'] != 'HALT' or previous['halt_reason'] !=
            'SECURITY_CARD_UNSUPPORTED: LM-034 source=A:LM-034#1'):
        raise RuntimeError('LM034_HALT_IDENTITY_CHANGED')
    old = _source_bytes(args.old_root.resolve())
    new = _source_bytes(ROOT)
    if previous['sources'] != old:
        raise RuntimeError('ORIGINAL_SOURCE_MAP_CHANGED')
    changed = {key: {'before': old[key], 'after': new[key]}
        for key in old if old[key] != new[key]}
    if set(changed) != {'option_actions.py'}:
        raise RuntimeError('REPAIR_SOURCE_SCOPE_CHANGED: ' + str(sorted(changed)))
    migrated = migrate_repaired_game(previous, root=ROOT,
        original_source_root=args.old_root.resolve(), approved_changes=changed,
        repair_note=('The saved LM-034 Security check halted before moving any card. '
            'Its printed Security text places this Option in the battle area. '
            'The repair adds that exact action without Main search, memory cost, '
            'or altered prior choices.'))
    if migrated['seed'] != previous['seed'] or migrated['policy_rng_final'] != previous['policy_rng_final']:
        raise RuntimeError('MIGRATED_GAME_IDENTITY_CHANGED')
    number = len(paths)
    _save(game_dir / f'segment-{number:04d}.json.gz',
          gzip.compress(canonical(migrated) + b'\n', mtime=0))
    replay = replay_game(migrated, ROOT)
    if replay.get('exact_match') is not True:
        raise RuntimeError('MIGRATED_REPLAY_FAILED')
    _save(game_dir / f'replay-{number:04d}.json', _json_bytes(replay))
    _save(game_dir / 'checkpoint.json', _json_bytes({'game_index': 0,
        'segment': number, 'status': migrated['status'],
        'commands': len(migrated['commands']), 'seed': migrated['seed'],
        'first': migrated['first'], 'winner': migrated['winner'],
        'halt_reason': migrated['halt_reason'], 'record_sha256': migrated['record_sha256'],
        'history_report': migrated['history_report'], 'model_games_before': 2,
        'exact_replay': True, 'accepted_fact_finding_credit': 0,
        'repair': 'LM-034 printed Security placement'}), replace=True)
    print(json.dumps({'segment': number, 'status': migrated['status'],
        'record_sha256': migrated['record_sha256'], 'exact_replay': True,
        'approved_changes': changed}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
