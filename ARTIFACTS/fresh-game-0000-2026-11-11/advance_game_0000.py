"""Advance only the first real Bot A/B game, saving every bounded segment."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.machinery
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = str(ROOT / 'SOURCE')
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
CAMPAIGN = 'ULFORCE_MIRROR_FACT_FINDING_2026_11_11_V1'
HISTORICAL = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-04-02/game-0000-segment.json.gz'


class DirectSource(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


# The code that acts must be the source whose hashes enter the game record.
sys.path_importer_cache[SOURCE] = importlib.machinery.FileFinder(
    SOURCE, (DirectSource, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0, SOURCE)

from fresh_learning_campaign import (make_schedule, replay_game, run_game,
                                     _policy_seeds, _sources)
from imported_attempts import _load_context_selection
from interaction_learning import LearningState, learning_player_manifest
from interaction_scoring import criteria_manifest
from match_context import canonical, digest


def save_json(name, value):
    with (OUT / name).open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def save_record(name, value):
    with (OUT / name).open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(canonical(value) + b'\n')


def read_record(name):
    with gzip.open(OUT / name, 'rt') as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=int, default=12,
                        help='New commands in this saved segment (1..32).')
    args = parser.parse_args()
    if not 1 <= args.budget <= 32:
        parser.error('budget must be 1..32')
    historical_sha = hashlib.sha256(HISTORICAL.read_bytes()).hexdigest()
    context, context_file, context_sha = _load_context_selection(ROOT, CONTEXT)
    schedule = make_schedule(context.matchup_id, CAMPAIGN)
    sources, criteria = _sources(ROOT), criteria_manifest()
    model = LearningState()
    model_export = model.export()
    policy_seeds = _policy_seeds(context.matchup_id, CAMPAIGN, 0, model.state_id)
    pilots = {seat: learning_player_manifest(context, seat, model.state_id, policy_seeds[seat])
              for seat in ('A', 'B')}
    assert pilots['A']['style'] == 'AGGRESSIVE' and pilots['B']['style'] == 'DEFENSIVE'
    manifest = {'schema': 'fresh-game-0000-lock-v1', 'date': '2026-11-11',
        'campaign_id': CAMPAIGN, 'context_file': context_file,
        'context_file_sha256': context_sha, 'context_id': context.matchup_id,
        'schedule': schedule, 'game': schedule['games'][0], 'game_index': 0,
        'sources': sources, 'criteria': criteria, 'learning_state_before': model_export,
        'learning_state_id': model.state_id, 'pilots': pilots,
        'source_git_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
            text=True, capture_output=True, check=True).stdout.strip(),
        'historical_mixed_game_raw_sha256': historical_sha,
        'authorized_games': [0], 'cohort_running': False,
        'final_evaluation_running': False,
        'production_learning_updates_before_game': 0}
    lock_file = OUT / 'game-0000-lock.json'
    if lock_file.exists():
        saved = json.loads(lock_file.read_text())
        for key in ('schema', 'campaign_id', 'context_file', 'context_file_sha256',
                    'context_id', 'schedule', 'game', 'game_index', 'sources',
                    'criteria', 'learning_state_before', 'learning_state_id',
                    'pilots', 'historical_mixed_game_raw_sha256', 'authorized_games'):
            if canonical(saved[key]) != canonical(manifest[key]):
                raise RuntimeError('GAME_0000_LOCK_CHANGED: ' + key)
    else:
        save_json('game-0000-lock.json', manifest)
    existing = sorted(OUT.glob('game-0000-segment-*.json.gz'))
    for index, path in enumerate(existing):
        if not re.fullmatch(r'game-0000-segment-\d{4}.json.gz', path.name) or path.name != f'game-0000-segment-{index:04d}.json.gz':
            raise RuntimeError('GAME_0000_SEGMENT_SEQUENCE_CHANGED')
    prior = read_record(existing[-1].name) if existing else None
    if prior is not None and prior['status'] != 'PAUSED':
        raise RuntimeError('GAME_0000_STOPPED: inspect and repair the saved action first')
    record = run_game(0, ROOT, context_file=CONTEXT, campaign_id=CAMPAIGN,
        learning_state=model, max_commands=args.budget, previous_record=prior)
    if record['pilots'] != pilots or record['seed'] != manifest['game']['seed'] or record['first'] != manifest['game']['first']:
        raise RuntimeError('GAME_0000_IDENTITY_CHANGED')
    if record['learning_state_before'] != model_export or record['learning_state_after'] != model_export or model.export() != model_export:
        raise RuntimeError('GAME_0000_MODEL_CHANGED')
    if prior is not None and record['commands'][:len(prior['commands'])] != prior['commands']:
        raise RuntimeError('GAME_0000_PREFIX_CHANGED')
    if hashlib.sha256(HISTORICAL.read_bytes()).hexdigest() != historical_sha:
        raise RuntimeError('HISTORICAL_RECORD_CHANGED')
    segment = len(existing)
    name = f'game-0000-segment-{segment:04d}.json.gz'
    save_record(name, record)  # Persist selections and state before optional replay work.
    try:
        replay = replay_game(record, ROOT)
    except Exception as exc:
        save_json(f'game-0000-replay-{segment:04d}.json',
                  {'exact_match': False, 'error': str(exc), 'exception': type(exc).__name__})
        raise
    save_json(f'game-0000-replay-{segment:04d}.json', replay)
    added = record['commands'][len(prior['commands']) if prior else 0:]
    color_counts = Counter(c.get('rating', {}).get('label') for c in added)
    summary = {'schema': 'game-0000-segment-summary-v1', 'segment': segment,
        'record_file': name, 'record_sha256': record['record_sha256'],
        'exact_replay': replay['exact_match'], 'status': record['status'],
        'seed': record['seed'], 'first': record['first'],
        'total_commands': len(record['commands']), 'new_commands': len(added),
        'new_actions': [{'index': len(record['commands']) - len(added) + n,
                         'command': c['command'], 'seat': c['seat'], 'status': c['status'],
                         'label': c.get('rating', {}).get('label'),
                         'learning_eligible': c.get('rating', {}).get('learning_eligible', False)}
                        for n, c in enumerate(added)],
        'new_accepted_judge_receipts': sum(c.get('judge', {}).get('accepted') is True for c in added),
        'new_colors': {k: color_counts[k] for k in ('GREEN', 'YELLOW', 'RED')},
        'active': record['final']['state']['active'], 'phase': record['final']['state']['phase'],
        'turn': record['final']['state']['turn'], 'memory': record['final']['state']['memory'],
        'winner': record['winner'], 'terminal_reason': record['terminal_reason'],
        'halt_reason': record['halt_reason'], 'learning_state_unchanged': True,
        'accepted_fact_finding_credit': record['accepted_fact_finding_credit'],
        'final_evaluation_credit': record['final_evaluation_credit']}
    save_json(f'game-0000-summary-{segment:04d}.json', summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
