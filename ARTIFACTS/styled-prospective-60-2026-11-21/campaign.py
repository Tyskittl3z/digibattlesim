"""Sequential styled Bot A/B software games with immutable per-segment replay.

An unsupported action halts its scheduled seed. The rules lock is still
unverified, so no game receives independent fact-finding certification.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'SOURCE'))

from fresh_learning_campaign import _sources, commit_completed_game, make_schedule, replay_game, run_game
from imported_attempts import _load_context_selection
from interaction_learning import LearningState
from interaction_scoring import criteria_manifest
from match_context import canonical, digest
from matchup_rules_lock import inspect_lock

CAMPAIGN = 'ULFORCE_STYLED_FRESH_60_2026_11_21_V1'
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
RULES = 'RULES/matchups/123129-vs-122110/RULES_LOCK.json'
ROADMAP_CRITERIA = 'ARTIFACTS/styled-prospective-60-2026-11-21/ROADMAP_CRITERIA.json'
POLICY = 'BOARD_TEXT_HISTORY_STYLED'
TARGET = 60


def _bytes(value):
    return json.dumps(value, indent=2, sort_keys=True).encode() + b'\n'


def _save(path, data, *, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        if path.read_bytes() != data:
            raise RuntimeError('IMMUTABLE_CAMPAIGN_FILE_CHANGED: ' + str(path))
        return
    temp = path.with_name(path.name + '.tmp')
    with temp.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def _record(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def _segments(folder):
    paths = sorted(folder.glob('segment-*.json.gz'))
    if [p.name for p in paths] != [f'segment-{i:04d}.json.gz' for i in range(len(paths))]:
        raise RuntimeError('NONCONTIGUOUS_SEGMENTS')
    return paths


def _lock(out):
    context, context_file, context_sha = _load_context_selection(ROOT, CONTEXT)
    rules = json.loads((ROOT / RULES).read_bytes())
    audit = inspect_lock(rules, ROOT)
    if audit['bad_hashes'] or set(audit['blockers']) - {'EFFECTIVE_DATE_MISSING', 'SEPARATE_REVIEW_MISSING'}:
        raise RuntimeError('RULES_SOURCE_IDENTITY_INVALID: ' + repr(audit))
    body = {'schema': 'styled-sequential-60-lock-v1', 'campaign_id': CAMPAIGN,
        'context_id': context.matchup_id, 'context_file': context_file,
        'context_file_sha256': context_sha, 'rules_lock_file': RULES,
        'rules_lock_file_sha256': hashlib.sha256((ROOT / RULES).read_bytes()).hexdigest(),
        'rules_status': audit['status'], 'rules_blockers': audit['blockers'],
        'schedule': make_schedule(context.matchup_id, CAMPAIGN),
        'engine_sources': _sources(ROOT), 'criteria': criteria_manifest(),
        'roadmap_criteria_file': ROADMAP_CRITERIA,
        'roadmap_criteria_file_sha256': hashlib.sha256((ROOT / ROADMAP_CRITERIA).read_bytes()).hexdigest(),
        'player_policy': POLICY, 'initial_model_state_id': LearningState().state_id,
        'target_games': TARGET, 'accepted_fact_finding_credit': 0,
        'final_evaluation_credit': 0}
    _save(out / 'campaign-lock.json', _bytes({**body, 'lock_sha256': digest(body)}))
    return body


def _handoff(out, index, lock):
    if index == 0:
        return LearningState(), None
    prior = out / f'game-{index-1:04d}'
    for name in ('report.md', 'model-after.json', 'commit.json'):
        if not (prior / name).is_file():
            raise RuntimeError('PRIOR_GAME_NOT_COMMITTED: ' + name)
    paths = _segments(prior)
    if not paths:
        raise RuntimeError('PRIOR_TERMINAL_RECORD_MISSING')
    record = _record(paths[-1])
    receipt = json.loads((prior / 'commit.json').read_text())
    scheduled = lock['schedule']['games'][index - 1]
    if (record['status'] != 'EXPERIMENTAL_SOFTWARE_TERMINAL'
            or (record['seed'], record['first']) != (scheduled['seed'], scheduled['first'])
            or receipt['record_sha256'] != digest(record) or receipt['updated'] is not True):
        raise RuntimeError('PRIOR_GAME_IDENTITY_MISMATCH')
    model = LearningState.from_dict(json.loads((prior / 'model-after.json').read_text()))
    if len(model.export()['games']) != index or model.state_id != receipt['learning_state_id']:
        raise RuntimeError('PRIOR_MODEL_MISMATCH')
    return model, str((prior / 'report.md').relative_to(ROOT))


def _actions_csv(record):
    stream = io.StringIO(newline='')
    fields = ('action', 'turn', 'seat', 'command', 'choice_json', 'judge_accepted',
        'board_color', 'learning_eligible', 'reward', 'memory_before', 'memory_after',
        'zone_movements_json')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for index, command in enumerate(record['commands'], 1):
        writer.writerow({'action': index, 'turn': command['before']['state']['turn'],
            'seat': command['seat'], 'command': command['command'],
            'choice_json': json.dumps(command['args'], sort_keys=True),
            'judge_accepted': command['judge']['accepted'],
            'board_color': command['rating']['label'],
            'learning_eligible': command['rating']['learning_eligible'],
            'reward': command['rating']['reward'],
            'memory_before': command['before']['state']['memory'],
            'memory_after': command['after']['state']['memory'],
            'zone_movements_json': json.dumps(command['observation']['zone_movements'], sort_keys=True)})
    return stream.getvalue().encode()


def _report(record):
    labels = Counter(command['rating']['label'] for command in record['commands'])
    checks = record['commands'][-1]['observation']['public_metrics_after']['successful_security_checks']
    return (f"# Game {record['index']:04d}: styled Bot A versus Bot B\n\n"
        f"Winner: Bot {record['winner']} on turn {record['final']['state']['turn']}. "
        f"Seed: {record['seed']}; first: Bot {record['first']}.\n\n"
        f"Policies: A {record['pilots']['A']['style']}; B {record['pilots']['B']['style']}. "
        f"Prior report: {record['history_report']}.\n\n"
        f"Accepted actions and Bot C observations: {len(record['commands'])} each. "
        f"Immediate board labels: green {labels['GREEN']}, yellow {labels['YELLOW']}, "
        f"red {labels['RED']}. Completed security checks: A {checks['A']}, B {checks['B']}.\n\n"
        'Attack-learning reward is calculated at between-game commit; the action colors remain immediate. '
        'This is experimental software evidence with zero independent rules-certification credit.\n')


def _status(out, index, state):
    completed = sum((out / f'game-{i:04d}' / 'model-after.json').is_file() for i in range(TARGET))
    _save(out / 'campaign-status.json', _bytes({'schema': 'styled-sequential-60-status-v1',
        'campaign_id': CAMPAIGN, 'target_games': TARGET, 'completed_software_games': completed,
        'next_game_index': completed, 'current_game_index': index, 'current_status': state,
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0}), replace=True)


def _finalize_terminal(folder, record, model):
    """Complete a terminal checkpoint after an interrupted write, idempotently."""
    receipt = commit_completed_game(record, model, ROOT)
    _save(folder / 'report.md', _report(record).encode())
    _save(folder / 'actions.csv', _actions_csv(record))
    _save(folder / 'commit.json', _bytes(receipt))
    _save(folder / 'model-after.json', _bytes(model.export()))


def advance_once(out=OUT, index=0, *, budget=256):
    if type(index) is not int or not 0 <= index < TARGET or type(budget) is not int or budget < 1:
        raise ValueError('Game index 0..59 and positive budget required')
    out = Path(out).resolve()
    lock = _lock(out)
    model, report = _handoff(out, index, lock)
    folder = out / f'game-{index:04d}'
    paths = _segments(folder)
    previous = _record(paths[-1]) if paths else None
    if previous is not None:
        replay_file = folder / f'replay-{len(paths)-1:04d}.json'
        if not replay_file.is_file() or json.loads(replay_file.read_text()).get('exact_match') is not True:
            raise RuntimeError('PREVIOUS_REPLAY_REQUIRED')
        if previous['status'] != 'PAUSED':
            if previous['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL':
                _finalize_terminal(folder, previous, model)
            _status(out, index, previous['status'])
            return {'game_index': index, 'status': previous['status'],
                'commands': len(previous['commands']), 'exact_replay': True,
                'model_games_before': index, 'player_policy': POLICY}
    record = run_game(index, ROOT, context_file=CONTEXT, campaign_id=CAMPAIGN,
        learning_state=model, max_commands=budget, previous_record=previous,
        player_policy=POLICY, history_report=report)
    if (record['sources'] != lock['engine_sources'] or record['criteria'] != lock['criteria']
            or record['seed'] != lock['schedule']['games'][index]['seed']
            or record['first'] != lock['schedule']['games'][index]['first']
            or record['player_policy'] != POLICY
            or record['pilots']['A']['style'] != 'AGGRESSIVE_BOARD_TEXT'
            or record['pilots']['B']['style'] != 'DEFENSIVE_BOARD_TEXT'):
        raise RuntimeError('CAMPAIGN_IDENTITY_CHANGED')
    if previous and record['commands'][:len(previous['commands'])] != previous['commands']:
        raise RuntimeError('CAMPAIGN_PREFIX_CHANGED')
    number = len(paths)
    _save(folder / f'segment-{number:04d}.json.gz', gzip.compress(canonical(record) + b'\n', mtime=0))
    proof = replay_game(record, ROOT)
    if proof.get('exact_match') is not True:
        raise RuntimeError('EXACT_REPLAY_FAILED')
    _save(folder / f'replay-{number:04d}.json', _bytes(proof))
    if record['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL':
        _finalize_terminal(folder, record, model)
    _status(out, index, record['status'])
    return {'game_index': index, 'status': record['status'],
        'commands': len(record['commands']), 'exact_replay': True,
        'model_games_before': index, 'player_policy': POLICY,
        'seed': record['seed'], 'winner': record['winner'], 'halt_reason': record['halt_reason']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=int, default=256)
    parser.add_argument('--max-new-games', type=int, default=TARGET)
    args = parser.parse_args()
    if not 1 <= args.max_new_games <= TARGET:
        parser.error('max-new-games must be 1..60')
    for _ in range(args.max_new_games):
        status_file = OUT / 'campaign-status.json'
        index = json.loads(status_file.read_text())['next_game_index'] if status_file.is_file() else 0
        if index >= TARGET:
            return
        result = advance_once(OUT, index, budget=args.budget)
        print(json.dumps(result, sort_keys=True), flush=True)
        if result['status'] != 'EXPERIMENTAL_SOFTWARE_TERMINAL':
            return


if __name__ == '__main__':
    main()
