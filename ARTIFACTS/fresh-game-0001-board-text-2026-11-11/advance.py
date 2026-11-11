"""Advance one bounded board/text Bot A versus Bot B game segment."""
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

from fresh_learning_campaign import _source_bytes, replay_game, run_game
import fresh_repair_migration as migration
from interaction_learning import LearningState
from match_context import canonical

CAMPAIGN = 'ULFORCE_MIRROR_BOARD_TEXT_HISTORY_2026_11_11_V1'
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
HISTORY = 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-report.md'
MODEL = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-learning-model-after.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=int, default=16)
    parser.add_argument('--old-root', type=Path)
    args = parser.parse_args()
    if not 1 <= args.budget <= 32:
        parser.error('budget must be 1..32')
    paths = sorted(OUT.glob('segment-*.json.gz'))
    if [p.name for p in paths] != [f'segment-{i:04d}.json.gz' for i in range(len(paths))]:
        raise RuntimeError('SEGMENT_SEQUENCE_CHANGED')
    previous = None
    if paths:
        with gzip.open(paths[-1], 'rt') as handle:
            previous = json.load(handle)
        if previous['status'] not in ('PAUSED', 'HALT'):
            raise RuntimeError('STOPPED_GAME_REQUIRES_REVIEW')
    if previous is not None and previous['sources'] != _source_bytes(ROOT):
        if args.old_root is None:
            parser.error('--old-root required for source migration')
        old_root = args.old_root.resolve()
        old, new = _source_bytes(old_root), _source_bytes(ROOT)
        if old != previous['sources']:
            raise RuntimeError('ORIGINAL_SOURCE_MAP_MISMATCH')
        changes = {key: {'before': old.get(key), 'after': new.get(key)}
                   for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key)}
        if 'ULFORCE_RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED: EX13-017' in (previous['halt_reason'] or ''):
            repair = 'EX13-017 inherited return replacement'
            note = ('The saved EX13-023 return encountered EX13-017 inherited protection. '
                'The defender now receives an explicit printed once-per-turn suspend choice. '
                'No earlier seed, selection, engine state, or Bot C observation changes.')
        else:
            repair = 'LM-056 Security search'
            note = ('The saved turn-five LM-056 Security check halted. The printed Security search '
                'now reveals two, offers the defender an eligible card choice, bottoms the rest, '
                'and places the Option. Earlier game choices and state are replayed exactly.')
        migration._SOURCE_ONLY_WORKER = True
        migrated = migration.migrate_repaired_game(previous, root=ROOT,
            original_source_root=old_root, approved_changes=changes,
            repair_note=note)
        number = len(paths)
        path = OUT / f'segment-{number:04d}.json.gz'
        with path.open('xb') as handle:
            with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
                zipped.write(canonical(migrated) + b'\n')
        replay = replay_game(migrated, ROOT)
        summary = {'segment': number, 'record_file': path.name,
            'record_sha256': migrated['record_sha256'], 'status': migrated['status'],
            'commands': len(migrated['commands']), 'repair': repair,
            'changed_source_files': sorted(changes), 'exact_replay': replay['exact_match'],
            'accepted_fact_finding_credit': 0}
        (OUT / f'summary-{number:04d}.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
        print(json.dumps(summary, sort_keys=True))
        return
    if previous is not None and previous['status'] == 'HALT' and 'repair_lineage' not in previous:
        raise RuntimeError('HALTED_GAME_REQUIRES_REVIEWED_REPAIR')
    state = LearningState.from_dict(json.loads(MODEL.read_text()))
    record = run_game(1, ROOT, context_file=CONTEXT, campaign_id=CAMPAIGN,
        learning_state=state, max_commands=args.budget, previous_record=previous,
        player_policy='BOARD_TEXT_HISTORY', history_report=HISTORY)
    assert state.export() == record['learning_state_before'] == record['learning_state_after']
    assert record['pilots']['A']['style'] == record['pilots']['B']['style'] == 'BOARD_AND_CARD_TEXT'
    if previous is not None:
        accepted = len(previous['commands']) - int(previous['status'] == 'HALT')
        assert record['commands'][:accepted] == previous['commands'][:accepted]
    number = len(paths)
    path = OUT / f'segment-{number:04d}.json.gz'
    with path.open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(canonical(record) + b'\n')
    replay = replay_game(record, ROOT)
    assert replay['exact_match']
    summary = {'segment': number, 'record_file': path.name,
        'record_sha256': record['record_sha256'], 'status': record['status'],
        'seed': record['seed'], 'first': record['first'],
        'commands': len(record['commands']), 'winner': record['winner'],
        'turn': record['final']['state']['turn'], 'halt_reason': record['halt_reason'],
        'replay': replay, 'history_report': record['history_report'],
        'player_policy': record['player_policy'], 'accepted_fact_finding_credit': 0}
    (OUT / f'summary-{number:04d}.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
