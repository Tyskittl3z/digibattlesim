"""Migrate one saved judge halt after a reviewed, source-only engine repair."""
import argparse
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from campaign import (DEFAULT_OUT, ROOT, _json_bytes, _load, _lock, _record,
                      _save, _segments)
from fresh_learning_campaign import _source_bytes, replay_game
from fresh_repair_migration import migrate_repaired_game
from match_context import canonical, digest
import fresh_repair_migration as migration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-index', type=int, required=True)
    parser.add_argument('--old-root', type=Path, required=True)
    parser.add_argument('--expected-halt', required=True)
    parser.add_argument('--changed-source', action='append', required=True)
    parser.add_argument('--repair-note', required=True)
    args = parser.parse_args()
    if not 0 <= args.game_index < 60:
        parser.error('game index must be 0..59')
    out = DEFAULT_OUT
    game_dir = out / f'game-{args.game_index:04d}'
    paths = _segments(game_dir)
    if not paths:
        raise RuntimeError('NO_SAVED_HALT')
    previous = _record(paths[-1])
    if previous['status'] != 'HALT' or previous['halt_reason'] != args.expected_halt:
        raise RuntimeError('SAVED_HALT_IDENTITY_CHANGED')
    original_lock = _load(out / 'campaign-lock.json')
    old, new = _source_bytes(args.old_root.resolve()), _source_bytes(ROOT)
    if previous['sources'] != old or original_lock['engine_sources'] != old:
        raise RuntimeError('ORIGINAL_SOURCE_MAP_CHANGED')
    changed = {key: {'before': old.get(key), 'after': new.get(key)}
               for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key)}
    if set(changed) != set(args.changed_source) or len(args.changed_source) != len(changed):
        raise RuntimeError('REPAIR_SOURCE_SCOPE_CHANGED: ' + str(sorted(changed)))
    migration._SOURCE_ONLY_WORKER = True
    migrated = migrate_repaired_game(previous, root=ROOT,
        original_source_root=args.old_root.resolve(), approved_changes=changed,
        repair_note=args.repair_note)
    if (migrated['seed'] != previous['seed'] or
            migrated['policy_rng_final'] != previous['policy_rng_final'] or
            migrated['sources'] != new):
        raise RuntimeError('MIGRATED_GAME_IDENTITY_CHANGED')
    with TemporaryDirectory() as temporary:
        new_lock = _lock(Path(temporary))
    prior_body = {key: value for key, value in original_lock.items()
                  if key != 'lock_sha256'}
    if (original_lock['lock_sha256'] != digest(prior_body) or
            {k: v for k, v in prior_body.items() if k != 'engine_sources'} !=
            {k: v for k, v in new_lock.items() if k != 'engine_sources'}):
        raise RuntimeError('CAMPAIGN_LOCK_NONENGINE_CHANGE')
    number = len(paths)
    segment = game_dir / f'segment-{number:04d}.json.gz'
    _save(segment, gzip.compress(canonical(migrated) + b'\n', mtime=0))
    replay = replay_game(migrated, ROOT)
    if replay.get('exact_match') is not True:
        raise RuntimeError('MIGRATED_REPLAY_FAILED')
    _save(game_dir / f'replay-{number:04d}.json', _json_bytes(replay))
    repair_number = len(list(out.glob('campaign-lock-before-repair-*.json'))) + 1
    archived = out / f'campaign-lock-before-repair-{repair_number:04d}.json'
    _save(archived, _json_bytes(original_lock))
    _save(out / f'source-repair-{repair_number:04d}.json', _json_bytes({
        'schema': 'prospective-source-repair-v1', 'game_index': args.game_index,
        'seed': previous['seed'], 'halt_reason': previous['halt_reason'],
        'parent_record_sha256': previous['record_sha256'],
        'migrated_record_sha256': migrated['record_sha256'],
        'lineage_sha256': migrated['repair_lineage']['lineage_sha256'],
        'old_lock_sha256': original_lock['lock_sha256'],
        'new_lock_sha256': digest(new_lock), 'approved_changes': changed,
        'repair_note': args.repair_note}))
    _save(out / 'campaign-lock.json',
          _json_bytes({**new_lock, 'lock_sha256': digest(new_lock)}), replace=True)
    _save(game_dir / 'checkpoint.json', _json_bytes({
        'game_index': args.game_index, 'segment': number,
        'status': migrated['status'], 'commands': len(migrated['commands']),
        'seed': migrated['seed'], 'first': migrated['first'],
        'winner': migrated['winner'], 'halt_reason': migrated['halt_reason'],
        'record_sha256': migrated['record_sha256'],
        'history_report': migrated['history_report'],
        'model_games_before': 2 + args.game_index,
        'exact_replay': True, 'accepted_fact_finding_credit': 0,
        'repair': args.repair_note}), replace=True)
    print(json.dumps({'game_index': args.game_index, 'segment': number,
        'status': migrated['status'], 'record_sha256': migrated['record_sha256'],
        'exact_replay': True, 'approved_changes': changed}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
