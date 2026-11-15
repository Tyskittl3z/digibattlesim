"""Migrate Game 0000 across a reviewed engine repair, then advance it in place."""
import argparse
import gzip
import importlib.machinery
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = str(ROOT / 'SOURCE')


class DirectSource(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


sys.path_importer_cache[SOURCE] = importlib.machinery.FileFinder(
    SOURCE, (DirectSource, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0, SOURCE)

from fresh_learning_campaign import run_game, replay_game, _source_bytes
import fresh_repair_migration as migration
from interaction_learning import LearningState
from match_context import canonical

# This script itself starts in an isolated interpreter and installs a loader
# that compiles current .py bytes directly. Keep all migration/replay checks,
# but avoid the API's extra 120-second outer subprocess for a long game.
migration._SOURCE_ONLY_WORKER = True


def migrate_without_player_calls(record, *, old_root, changes):
    from fresh_learning_campaign import LearningPlayerBot
    def forbidden(*args, **kwargs):
        raise RuntimeError('MIGRATION_PLAYER_CALL_FORBIDDEN')
    methods = {name:getattr(LearningPlayerBot,name)
               for name in ('__init__','choose','bottom_order')}
    try:
        for name in methods:
            setattr(LearningPlayerBot,name,forbidden)
        return migration.migrate_repaired_game(record, root=ROOT,
            original_source_root=old_root, approved_changes=changes,
            repair_note='Game 0000 encountered a printed interaction. Exact official '
                'card text and rules were added only after the saved HALT; prior '
                'actions, seed, choices, RNG, and Bot C ledger remain fixed.')
    finally:
        for name, method in methods.items():
            setattr(LearningPlayerBot,name,method)


def read(path):
    with gzip.open(path, 'rt') as handle:
        return json.load(handle)


def save(path, data):
    with path.open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(canonical(data) + b'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-root', type=Path)
    parser.add_argument('--budget', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.budget <= 32:
        parser.error('budget must be 1..32')
    paths = sorted(OUT.glob('game-0000-segment-*.json.gz'))
    prior = read(paths[-1])
    if prior['index'] != 0 or prior['status'] not in ('HALT', 'PAUSED'):
        raise RuntimeError('GAME_0000_REPAIR_BOUNDARY_REQUIRED')
    migrated_this_call = prior['sources'] != _source_bytes(ROOT)
    if migrated_this_call:
        if args.old_root is None:
            parser.error('--old-root required for first migration')
        old = _source_bytes(args.old_root)
        new = _source_bytes(ROOT)
        if old != prior['sources']:
            raise RuntimeError('OLD_SOURCE_MAP_MISMATCH')
        changes = {name: {'before': old.get(name), 'after': new.get(name)}
                   for name in sorted(old.keys() | new.keys()) if old.get(name) != new.get(name)}
        migrated = migrate_without_player_calls(prior,old_root=args.old_root,changes=changes)
        index = len(paths)
        save(OUT / f'game-0000-segment-{index:04d}.json.gz', migrated)
        proof = replay_game(migrated, ROOT)
        (OUT / f'game-0000-replay-{index:04d}.json').write_text(
            json.dumps(proof, indent=2, sort_keys=True) + '\n')
        prior = migrated
        print(json.dumps({'segment':index,'status':prior['status'],
            'commands':len(prior['commands']),'exact_replay':proof['exact_match'],
            'approved_changes':sorted(changes)},sort_keys=True),flush=True)
    elif prior['status'] != 'PAUSED':
        raise RuntimeError('GAME_0000_HALTED_WITHOUT_NEW_REPAIR')
    if prior['sources'] != _source_bytes(ROOT):
        raise RuntimeError('SOURCE_MAP_CHANGED_AFTER_MIGRATION')
    model = LearningState.from_dict(prior['learning_state_before'])
    result = run_game(0, ROOT, context_file=prior['context_file'],
        campaign_id=prior['campaign_id'], learning_state=model,
        max_commands=args.budget, previous_record=prior)
    if result['seed'] != prior['seed'] or result['first'] != prior['first']:
        raise RuntimeError('GAME_0000_IDENTITY_CHANGED')
    if result['learning_state_before'] != prior['learning_state_before']:
        raise RuntimeError('GAME_0000_MODEL_CHANGED')
    index = len(paths) + int(migrated_this_call)
    save(OUT / f'game-0000-segment-{index:04d}.json.gz', result)
    proof = replay_game(result, ROOT)
    (OUT / f'game-0000-replay-{index:04d}.json').write_text(
        json.dumps(proof, indent=2, sort_keys=True) + '\n')
    added = result['commands'][len(prior['commands']) - int(prior['status']=='HALT'):]
    print(json.dumps({'segment':index,'status':result['status'],
        'commands':len(result['commands']),'added':len(added),
        'latest':result['commands'][-1]['command'],'halt_reason':result['halt_reason'],
        'winner':result['winner'],'exact_replay':proof['exact_match']},sort_keys=True),flush=True)


if __name__ == '__main__':
    main()
