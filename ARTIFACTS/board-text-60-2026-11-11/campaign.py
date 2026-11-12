"""Run 60 additional sequential, history-fed Bot A/B software games.

Each segment is saved before replay. An unresolved action stops the campaign
on its original index and seed. No game trains the next until terminal replay.
"""
from collections import Counter
import argparse
import csv
import gzip
import hashlib
import importlib.machinery
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path(__file__).resolve().parent
SOURCE = str(ROOT / 'SOURCE')


class DirectSource(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


sys.path_importer_cache[SOURCE] = importlib.machinery.FileFinder(
    SOURCE, (DirectSource, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0, SOURCE)

import fresh_repair_migration as migration
from fresh_learning_campaign import (commit_completed_game, make_schedule,
    replay_game, run_game)
from imported_attempts import _load_context_selection
from interaction_learning import LearningState
from match_context import canonical, digest

migration._SOURCE_ONLY_WORKER = True

CAMPAIGN = 'ULFORCE_BOARD_TEXT_ADDITIONAL_60_2026_11_11_V1'
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
INITIAL_REPORT = 'ARTIFACTS/fresh-game-0001-board-text-2026-11-11/game-0001-report.md'
INITIAL_MODEL = 'ARTIFACTS/fresh-game-0001-board-text-2026-11-11/game-0001-learning-model-after.json'
INITIAL_RECEIPT = 'ARTIFACTS/fresh-game-0001-board-text-2026-11-11/game-0001-learning-commit.json'
TARGET = 60


def _json_bytes(value):
    return json.dumps(value, indent=2, sort_keys=True).encode() + b'\n'


def _save(path, data, *, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        if path.read_bytes() != data:
            raise RuntimeError('CHECKPOINT_ALREADY_EXISTS_WITH_DIFFERENT_BYTES: ' + str(path))
        return
    temp = path.with_name(path.name + '.tmp')
    with temp.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _load(path):
    return json.loads(path.read_text())


def _record(path):
    with gzip.open(path, 'rt') as handle:
        return json.load(handle)


def _segments(game_dir):
    paths = sorted(game_dir.glob('segment-*.json.gz'))
    if [p.name for p in paths] != [f'segment-{n:04d}.json.gz' for n in range(len(paths))]:
        raise RuntimeError('NONCONTIGUOUS_GAME_SEGMENTS: ' + str(game_dir))
    return paths


def _lock(out):
    context, context_file, context_sha = _load_context_selection(ROOT, CONTEXT)
    schedule = make_schedule(context.matchup_id, CAMPAIGN)
    model = LearningState.from_dict(_load(ROOT / INITIAL_MODEL))
    receipt = _load(ROOT / INITIAL_RECEIPT)
    if (len(model.export()['games']) != 2 or receipt['updated'] is not True
            or receipt['learning_state_id'] != model.state_id):
        raise RuntimeError('INITIAL_TWO_GAME_HISTORY_INVALID')
    report_sha = hashlib.sha256((ROOT / INITIAL_REPORT).read_bytes()).hexdigest()
    body = {'schema': 'board-text-sequential-60-lock-v1', 'campaign_id': CAMPAIGN,
        'context_id': context.matchup_id, 'context_file': context_file,
        'context_file_sha256': context_sha, 'schedule': schedule,
        'target_additional_games': TARGET, 'player_policy': 'BOARD_TEXT_HISTORY',
        'initial_model_state_id': model.state_id,
        'initial_report': INITIAL_REPORT, 'initial_report_sha256': report_sha,
        'software_evidence_only': True, 'accepted_fact_finding_credit': 0,
        'final_evaluation_credit': 0}
    _save(out / 'campaign-lock.json', _json_bytes({**body, 'lock_sha256': digest(body)}))
    return body


def _handoff(out, index, lock):
    if index == 0:
        model_file, report = ROOT / INITIAL_MODEL, INITIAL_REPORT
    else:
        prior = out / f'game-{index-1:04d}'
        model_file, report_file = prior / 'model-after.json', prior / 'report.md'
        if not model_file.is_file() or not report_file.is_file() or not (prior / 'commit.json').is_file():
            raise RuntimeError('PRIOR_GAME_NOT_COMMITTED: ' + str(prior))
        report = str(report_file.resolve().relative_to(ROOT))
        receipt = _load(prior / 'commit.json')
        if receipt['learning_state_id'] != _load(model_file)['state_id'] or receipt['updated'] is not True:
            raise RuntimeError('PRIOR_MODEL_RECEIPT_MISMATCH')
    model = LearningState.from_dict(_load(model_file))
    if len(model.export()['games']) != 2 + index:
        raise RuntimeError('HISTORY_GAME_COUNT_MISMATCH')
    report_sha = hashlib.sha256((ROOT / report).read_bytes()).hexdigest()
    if index == 0 and report_sha != lock['initial_report_sha256']:
        raise RuntimeError('INITIAL_REPORT_CHANGED')
    return model, report, report_sha


def _report_text(record):
    labels = Counter(c['rating']['label'] for c in record['commands'])
    checks = record['commands'][-1]['observation']['public_metrics_after']['successful_security_checks']
    return ('# Game ' + f"{record['index']:04d}" + ': Bot A versus Bot B\n\n'
        + f"Bot {record['winner']} won by {record['terminal_reason'].replace('_', ' ').lower()} on turn {record['final']['state']['turn']}.\n\n"
        + f"Seed: {record['seed']}. First player: Bot {record['first']}. "
        + f"Policy: {record['player_policy']} for both seats. Prior report: `{record['history_report']['file']}` "
        + f"(SHA-256 `{record['history_report']['sha256']}`).\n\n"
        + f"Accepted judge actions: {len(record['commands'])}. Bot C observations: {len(record['tracker_observations'])}. "
        + f"Board-impact labels: green {labels['GREEN']}, yellow {labels['YELLOW']}, red {labels['RED']}. "
        + f"Successful Security checks: A {checks['A']}, B {checks['B']}.\n\n"
        + 'See `actions.csv` for each action, choice, result, color and field change. '
        + 'See the final gzipped segment for full states, decisions, judge receipts and exact replay evidence.\n\n'
        + 'This is experimental software evidence. It has no independent rules certification or accepted fact-finding/evaluation credit.\n')


def _actions_csv(record):
    stream = io.StringIO(newline='')
    fields = ['action', 'turn', 'phase', 'seat', 'command', 'choice_json',
        'result_json', 'judge_accepted', 'board_color', 'learning_eligible',
        'memory_before', 'memory_after', 'security_a_before', 'security_a_after',
        'security_b_before', 'security_b_after', 'bot_decisions_json', 'zone_movements_json']
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    short = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))
    for n, command in enumerate(record['commands'], 1):
        before, after = command['before']['state'], command['after']['state']
        writer.writerow({'action': n, 'turn': before['turn'], 'phase': before['phase'],
            'seat': command['seat'], 'command': command['command'],
            'choice_json': short(command['args']), 'result_json': short(command['result']),
            'judge_accepted': command['judge']['accepted'],
            'board_color': command['rating']['label'],
            'learning_eligible': command['rating']['learning_eligible'],
            'memory_before': before['memory'], 'memory_after': after['memory'],
            'security_a_before': len(before['zones']['A']['security']),
            'security_a_after': len(after['zones']['A']['security']),
            'security_b_before': len(before['zones']['B']['security']),
            'security_b_after': len(after['zones']['B']['security']),
            'bot_decisions_json': short([{'chosen': d['chosen'], 'reason': d['reason'],
                'mode': d['learning']['mode']} for d in command['decisions']]),
            'zone_movements_json': short(command['observation']['zone_movements'])})
    return stream.getvalue().encode()


def _finalize(game_dir, record, model):
    if (record['status'] != 'EXPERIMENTAL_SOFTWARE_TERMINAL'
            or any(c['status'] != 'EXPERIMENTAL_RESOLVED'
                   or c['judge']['accepted'] is not True for c in record['commands'])
            or len(record['tracker_observations']) != len(record['commands'])):
        raise RuntimeError('NONTERMINAL_OR_UNJUDGED_GAME_CANNOT_TRAIN')
    receipt = commit_completed_game(record, model, ROOT)
    if receipt['updated'] is not True:
        raise RuntimeError('DUPLICATE_OR_MISSING_MODEL_COMMIT')
    _save(game_dir / 'report.md', _report_text(record).encode())
    _save(game_dir / 'actions.csv', _actions_csv(record))
    _save(game_dir / 'commit.json', _json_bytes(receipt))
    _save(game_dir / 'model-after.json', _json_bytes(model.export()))


def _campaign_status(out, current_index, current_status):
    completed = sum((out / f'game-{n:04d}' / 'model-after.json').is_file()
                    for n in range(TARGET))
    body = {'schema': 'board-text-sequential-60-status-v1',
        'campaign_id': CAMPAIGN, 'target_additional_games': TARGET,
        'completed_software_games': completed,
        'current_game_index': current_index, 'current_status': current_status,
        'next_game_index': completed,
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0}
    _save(out / 'campaign-status.json', _json_bytes(body), replace=True)


def advance_once(out=DEFAULT_OUT, index=0, *, budget=256):
    """Advance only one bounded segment of one scheduled game."""
    if type(index) is not int or not 0 <= index < TARGET or type(budget) is not int or budget < 1:
        raise ValueError('game index 0..59 and positive budget required')
    out = Path(out).resolve()
    lock = _lock(out)
    model, report, report_sha = _handoff(out, index, lock)
    game_dir = out / f'game-{index:04d}'
    game_dir.mkdir(parents=True, exist_ok=True)
    paths = _segments(game_dir)
    previous = _record(paths[-1]) if paths else None
    if previous is not None:
        last_replay = game_dir / f'replay-{len(paths)-1:04d}.json'
        if not last_replay.is_file():
            _save(last_replay, _json_bytes(replay_game(previous, ROOT)))
        if _load(last_replay).get('exact_match') is not True:
            raise RuntimeError('EXISTING_CHECKPOINT_REPLAY_FAILED')
        if previous['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL':
            if not (game_dir / 'model-after.json').is_file():
                _finalize(game_dir, previous, model)
            _campaign_status(out, index, previous['status'])
            return {'game_index': index, 'status': previous['status'],
                'commands': len(previous['commands']), 'exact_replay': True,
                'model_games_before': 2 + index, 'winner': previous['winner']}
        if previous['status'] != 'PAUSED' and not (previous['status'] == 'HALT'
                and 'repair_lineage' in previous):
            _campaign_status(out, index, previous['status'])
            return {'game_index': index, 'status': previous['status'],
                'commands': len(previous['commands']), 'exact_replay': True,
                'model_games_before': 2 + index, 'halt_reason': previous['halt_reason']}
    record = run_game(index, ROOT, context_file=CONTEXT, campaign_id=CAMPAIGN,
        learning_state=model, max_commands=budget, previous_record=previous,
        player_policy='BOARD_TEXT_HISTORY', history_report=report)
    if (record['learning_state_before'] != model.export()
            or record['learning_state_after'] != model.export()
            or record['history_report']['sha256'] != report_sha
            or any(p['style'] != 'BOARD_AND_CARD_TEXT' or p['random_exploration']
                   for p in record['pilots'].values())
            or record['seed'] != lock['schedule']['games'][index]['seed']):
        raise RuntimeError('SEQUENTIAL_GAME_IDENTITY_CHANGED')
    accepted_prefix = len(previous['commands']) - int(previous['status'] == 'HALT') if previous else 0
    if previous is not None and record['commands'][:accepted_prefix] != previous['commands'][:accepted_prefix]:
        raise RuntimeError('SEQUENTIAL_GAME_PREFIX_CHANGED')
    number = len(paths)
    _save(game_dir / f'segment-{number:04d}.json.gz',
          gzip.compress(canonical(record) + b'\n', mtime=0))
    replay = replay_game(record, ROOT)
    if replay.get('exact_match') is not True:
        raise RuntimeError('SEQUENTIAL_GAME_REPLAY_FAILED')
    _save(game_dir / f'replay-{number:04d}.json', _json_bytes(replay))
    summary = {'game_index': index, 'segment': number, 'status': record['status'],
        'commands': len(record['commands']), 'seed': record['seed'],
        'first': record['first'], 'winner': record['winner'],
        'halt_reason': record['halt_reason'], 'record_sha256': record['record_sha256'],
        'history_report': record['history_report'], 'model_games_before': 2 + index,
        'exact_replay': True, 'accepted_fact_finding_credit': 0}
    _save(game_dir / 'checkpoint.json', _json_bytes(summary), replace=True)
    if record['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL':
        _finalize(game_dir, record, model)
    _campaign_status(out, index, record['status'])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=int, default=256)
    parser.add_argument('--max-new-games', type=int, default=TARGET)
    args = parser.parse_args()
    if not 1 <= args.max_new_games <= TARGET:
        parser.error('max-new-games must be 1..60')
    out = DEFAULT_OUT
    _lock(out)
    completed_this_call = 0
    while completed_this_call < args.max_new_games:
        status = _load(out / 'campaign-status.json') if (out / 'campaign-status.json').is_file() else None
        index = status['next_game_index'] if status else 0
        if index >= TARGET:
            break
        result = advance_once(out, index, budget=args.budget)
        print(json.dumps(result, sort_keys=True), flush=True)
        if result['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL':
            completed_this_call += 1
        elif result['status'] != 'PAUSED':
            break


if __name__ == '__main__':
    main()
