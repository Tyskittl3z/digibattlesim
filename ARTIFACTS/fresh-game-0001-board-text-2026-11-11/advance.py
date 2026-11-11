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
sys.path_importer_cache[SOURCE] = importlib.machinery.FileFinder(
    SOURCE, (importlib.machinery.SourceFileLoader, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0, SOURCE)

from fresh_learning_campaign import replay_game, run_game
from interaction_learning import LearningState
from match_context import canonical

CAMPAIGN = 'ULFORCE_MIRROR_BOARD_TEXT_HISTORY_2026_11_11_V1'
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
HISTORY = 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-report.md'
MODEL = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-learning-model-after.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=int, default=16)
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
        if previous['status'] != 'PAUSED':
            raise RuntimeError('STOPPED_GAME_REQUIRES_REVIEW')
    state = LearningState.from_dict(json.loads(MODEL.read_text()))
    record = run_game(1, ROOT, context_file=CONTEXT, campaign_id=CAMPAIGN,
        learning_state=state, max_commands=args.budget, previous_record=previous,
        player_policy='BOARD_TEXT_HISTORY', history_report=HISTORY)
    assert state.export() == record['learning_state_before'] == record['learning_state_after']
    assert record['pilots']['A']['style'] == record['pilots']['B']['style'] == 'BOARD_AND_CARD_TEXT'
    if previous is not None:
        assert record['commands'][:len(previous['commands'])] == previous['commands']
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
