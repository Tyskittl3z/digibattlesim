"""Fail-closed frozen evaluation runner for the exact loaded matchup.

This module can prepare execution software, but it cannot certify gameplay.
`create_freeze` re-runs the external-evidence gate and refuses blocked inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

from evaluation_gate import assess_eligibility, file_hash, validate_record
from match_evidence import ROOT, canonical_bytes, digest, provenance, record_match
from seeded_opening_probe import seed_for
from workflow_policy import FROZEN_COMPONENTS, assess_resume


FREEZE_SCHEMA = 'loaded-pair-frozen-evaluation-v1'
CHECKPOINT_SCHEMA = 'loaded-pair-frozen-checkpoint-v1'
HEX_SHA256 = re.compile(r'[0-9a-f]{64}')
JUDGE_LAYERS = (
    {'name': 'Justitia', 'role': 'RUNTIME_INTEGRITY'},
    {'name': 'Dike', 'role': 'INDEPENDENT_RULES'},
    {'name': 'Týr', 'role': 'FINAL_EVIDENCE_AUDIT'},
)
BOT_ROSTER = (
    {'name': 'Bot A', 'seat': 'A', 'deck': 'Jupitermon'},
    {'name': 'Bot B', 'seat': 'B', 'deck': 'Amaterasumon/Toho'},
)


def atomic_write(path, data):
    """Write bytes durably without exposing a partial destination file."""
    path = Path(path)
    if not isinstance(data, bytes):
        raise TypeError('atomic_write requires bytes')
    temporary = path.with_name(path.name + '.tmp')
    if temporary.exists():
        raise FileExistsError('Stale atomic-write temporary file: ' + str(temporary))
    with temporary.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def validate_schedule(schedule, expected_sha256):
    """Return a validated copy of the sealed balanced 10,000-match schedule."""
    if not isinstance(schedule, list) or len(schedule) != 10000:
        raise ValueError('Exactly 10000 scheduled matches required')
    if not isinstance(expected_sha256, str) or not HEX_SHA256.fullmatch(expected_sha256):
        raise ValueError('Valid expected schedule SHA-256 required')
    seen_indexes, seen_seeds = set(), set()
    starts = Counter()
    for position, row in enumerate(schedule):
        if not isinstance(row, dict) or set(row) != {'index', 'seed', 'first'}:
            raise ValueError('Invalid schedule row at position ' + str(position))
        index, seed, first = row['index'], row['seed'], row['first']
        if (type(index) is not int or index < 60 or type(seed) is not int
                or seed != seed_for(index) or first != ('A' if index % 2 == 0 else 'B')):
            raise ValueError('Invalid schedule identity at position ' + str(position))
        if index in seen_indexes or seed in seen_seeds:
            raise ValueError('Duplicate schedule index or seed at position ' + str(position))
        seen_indexes.add(index)
        seen_seeds.add(seed)
        starts[first] += 1
    if starts != Counter({'A': 5000, 'B': 5000}):
        raise ValueError('Schedule must contain 5000 starts for each deck')
    if digest(schedule) != expected_sha256:
        raise ValueError('Schedule canonical hash mismatch')
    return [dict(row) for row in schedule]


def _component_hashes(root, schedule, inputs=None):
    root = Path(root).resolve()
    inputs = provenance(root) if inputs is None else inputs
    files = inputs['files']
    engine = {name: value for name, value in files.items()
              if name.startswith('SOURCE/') and name.endswith('.py')}
    rules = {name: value for name, value in files.items() if name.startswith('RULES/')}
    decks = {name: value for name, value in files.items()
             if name.startswith('DECKS/') or name in (
                 'SOURCE/JUPITERMON.txt', 'SOURCE/AMATERASUMON_TOHO.txt')}
    criteria_name = 'ROADMAPS/APPROVAL_CRITERIA.json'
    if not engine or 'RULES/RULES_LOCK.json' not in rules or not decks:
        raise ValueError('Provenance is missing frozen engine, rules, or deck inputs')
    if criteria_name not in files:
        raise ValueError('Preregistered criteria missing from provenance')
    roadmap_hashes = {}
    for seat in ('A', 'B'):
        path = root / 'ROADMAPS' / (seat + '.json')
        roadmap_hashes[seat] = file_hash(path)
    result = {
        'engine': digest(engine),
        'rules_format': digest(rules),
        'decks': digest(decks),
        'pilots': digest(inputs['pilots']),
        'criteria': files[criteria_name],
        'roadmaps': digest(roadmap_hashes),
        'schedule': digest(schedule),
    }
    if set(result) != set(FROZEN_COMPONENTS) or not all(
            isinstance(value, str) and HEX_SHA256.fullmatch(value)
            for value in result.values()):
        raise ValueError('Incomplete frozen component hashes')
    return result


def create_freeze(root, cohort_dir, preparation_dir, output,
                  review_path, strategy_review_path):
    """Create an immutable run directory only after the live gate is eligible."""
    root = Path(root).resolve()
    cohort_dir = Path(cohort_dir).resolve()
    preparation_dir = Path(preparation_dir).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Freeze output already exists: ' + str(output))

    gate = assess_eligibility(root, cohort_dir, review_path, strategy_review_path)
    if (not isinstance(gate, dict) or gate.get('eligible') is not True
            or gate.get('status') != 'ELIGIBLE_PENDING_FREEZE'
            or gate.get('blockers')):
        codes = [item.get('code', 'UNKNOWN') for item in gate.get('blockers', [])]
        raise ValueError('Evaluation is not eligible for freeze: ' + ', '.join(codes))
    if review_path is None or strategy_review_path is None:
        raise ValueError('Both independent review files are required for freeze')

    preparation = json.loads((preparation_dir / 'PREPARATION.json').read_bytes())
    packed_schedule = (preparation_dir / 'SEEDS.json.gz').read_bytes()
    if (preparation.get('schema') != 'loaded-pair-evaluation-preparation-v1'
            or preparation.get('status') != 'ELIGIBLE_PENDING_FREEZE'
            or preparation.get('frozen') is not False
            or preparation.get('evaluation_matches_played') != 0
            or preparation.get('target_matches') != 10000
            or preparation.get('planned_starts') != {'A': 5000, 'B': 5000}):
        raise ValueError('Preparation is not an unplayed eligible 10000-match schedule')
    if hashlib.sha256(packed_schedule).hexdigest() != preparation.get('schedule_file_sha256'):
        raise ValueError('Preparation schedule file hash mismatch')
    try:
        schedule = json.loads(gzip.decompress(packed_schedule))
    except (OSError, EOFError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('Preparation schedule is unreadable') from exc
    schedule = validate_schedule(schedule, preparation.get('schedule_sha256'))

    inputs = provenance(root)
    inputs_sha256 = digest(inputs)
    if gate.get('provenance_sha256') != inputs_sha256:
        raise ValueError('Eligible gate does not bind current provenance')
    if not isinstance(gate.get('cohort_sha256'), str) or not HEX_SHA256.fullmatch(
            gate['cohort_sha256']):
        raise ValueError('Eligible gate lacks a complete cohort identity')
    frozen_inputs = _component_hashes(root, schedule, inputs)
    rules_review = Path(review_path).resolve()
    strategy_review = Path(strategy_review_path).resolve()
    manifest = {
        'schema': FREEZE_SCHEMA,
        'status': 'FROZEN_READY',
        'target_matches': 10000,
        'learning_enabled': False,
        'bots': [dict(bot) for bot in BOT_ROSTER],
        'judge_layers': [dict(judge) for judge in JUDGE_LAYERS],
        'frozen_inputs': frozen_inputs,
        'provenance_sha256': inputs_sha256,
        'cohort_sha256': gate['cohort_sha256'],
        'schedule_file': 'SEEDS.json.gz',
        'schedule_file_sha256': hashlib.sha256(packed_schedule).hexdigest(),
        'rules_review_sha256': file_hash(rules_review),
        'strategy_review_sha256': file_hash(strategy_review),
        'review_separation': gate.get('review_separation'),
        'evaluation_matches_played': 0,
    }

    checkpoint = {
        'schema': CHECKPOINT_SCHEMA,
        'status': 'READY',
        'frozen_inputs': dict(frozen_inputs),
        'schedule_position': 0,
        'credited_matches': 0,
        'next_match': dict(schedule[0]),
        'halt_kind': 'INFRASTRUCTURE',
        'last_record': None,
        'halt_record': None,
    }

    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / 'records').mkdir()
        (output / 'halts').mkdir()
        atomic_write(output / 'SEEDS.json.gz', packed_schedule)
        atomic_write(output / 'FREEZE.json', canonical_bytes(manifest))
        atomic_write(output / 'CHECKPOINT.json', canonical_bytes(checkpoint))
    except BaseException:
        # Never turn a partially written directory into a valid-looking freeze.
        marker = output / 'FREEZE_INCOMPLETE'
        if not marker.exists():
            atomic_write(marker, b'Freeze creation did not complete.\n')
        raise
    return manifest


def load_freeze(run_dir):
    """Load and validate the sealed manifest and exact schedule bytes."""
    run_dir = Path(run_dir).resolve()
    manifest = json.loads((run_dir / 'FREEZE.json').read_bytes())
    if (not isinstance(manifest, dict) or manifest.get('schema') != FREEZE_SCHEMA
            or manifest.get('status') != 'FROZEN_READY'
            or manifest.get('target_matches') != 10000
            or manifest.get('learning_enabled') is not False
            or manifest.get('bots') != [dict(bot) for bot in BOT_ROSTER]
            or manifest.get('judge_layers') != [dict(judge) for judge in JUDGE_LAYERS]
            or set(manifest.get('frozen_inputs', {})) != set(FROZEN_COMPONENTS)
            or not all(isinstance(value, str) and HEX_SHA256.fullmatch(value)
                       for value in manifest['frozen_inputs'].values())):
        raise ValueError('Invalid frozen evaluation manifest')
    packed = (run_dir / manifest.get('schedule_file', '')).read_bytes()
    if hashlib.sha256(packed).hexdigest() != manifest.get('schedule_file_sha256'):
        raise ValueError('Frozen schedule file hash mismatch')
    try:
        schedule = json.loads(gzip.decompress(packed))
    except (OSError, EOFError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('Frozen schedule is unreadable') from exc
    schedule = validate_schedule(schedule, manifest['frozen_inputs']['schedule'])
    return manifest, schedule


def _load_checkpoint(run_dir, manifest, schedule):
    checkpoint = json.loads((Path(run_dir) / 'CHECKPOINT.json').read_bytes())
    position = checkpoint.get('schedule_position')
    if (not isinstance(checkpoint, dict) or checkpoint.get('schema') != CHECKPOINT_SCHEMA
            or checkpoint.get('status') not in ('READY', 'RUNNING', 'BLOCKED_HALT',
                                                 'COMPLETE_PENDING_SUMMARY', 'COMPLETED')
            or checkpoint.get('frozen_inputs') != manifest['frozen_inputs']
            or type(position) is not int or not 0 <= position <= len(schedule)
            or checkpoint.get('credited_matches') != position
            or checkpoint.get('next_match') != (
                schedule[position] if position < len(schedule) else None)
            or checkpoint.get('halt_kind') not in ('INFRASTRUCTURE', 'RULES')):
        raise ValueError('Invalid frozen evaluation checkpoint')
    if checkpoint['halt_kind'] == 'RULES' and checkpoint.get('halt_record') is None:
        raise ValueError('Rules halt checkpoint is missing its preserved record')
    return checkpoint


def _record_path(run_dir, position, row, folder='records'):
    return (Path(run_dir) / folder /
            f"MATCH_{position + 1:05d}_INDEX_{row['index']:05d}.json.gz")


def _validate_scheduled_record(record, row, provenance_sha256):
    if not isinstance(record, dict):
        raise ValueError('Scheduled match runner must return a record object')
    try:
        validate_record(record)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ValueError('Scheduled record schema invalid: ' + str(exc)) from exc
    if (record.get('index') != row['index'] or record.get('seed') != row['seed']
            or record.get('first') != row['first']
            or record.get('provenance_sha256') != provenance_sha256):
        raise ValueError('Scheduled record identity mismatch')
    if record.get('physical_integrity') != {'status': 'PASS'}:
        raise ValueError('Scheduled record physical integrity failed')
    transcript = record['transcript']
    if record['status'] == 'SOFTWARE_COMPLETED':
        terminals = [i for i, event in enumerate(transcript['events'])
                     if event['type'] in ('GAME_END', 'WIN_DRAW_PHASE_DECKOUT')]
        if (transcript.get('halt_reason') is not None
                or transcript.get('winner') not in ('A', 'B')
                or terminals != [len(transcript['events']) - 1]
                or record['final_state']['runtime']['winner'] != transcript['winner']):
            raise ValueError('Completed scheduled record lacks one final terminal result')
    elif record['status'] == 'HALT':
        if (not isinstance(transcript.get('halt_reason'), str)
                or not transcript['halt_reason'].strip()
                or transcript.get('winner') is not None
                or transcript['events'][-1].get('type') != 'JUDGE_HALT'):
            raise ValueError('HALT record lacks its exact terminal judge trace')
    else:
        raise ValueError('Unknown scheduled record status')
    return record


def _write_or_verify_record(path, record):
    raw = canonical_bytes(record)
    packed = gzip.compress(raw, mtime=0)
    path = Path(path)
    if path.exists():
        try:
            prior_raw = gzip.decompress(path.read_bytes())
        except (OSError, EOFError) as exc:
            raise ValueError('Existing scheduled record is unreadable') from exc
        if prior_raw != raw:
            raise ValueError('Infrastructure replay did not reproduce the original record')
    else:
        atomic_write(path, packed)
    return {
        'file': path.relative_to(path.parent.parent).as_posix(),
        'record_sha256': hashlib.sha256(raw).hexdigest(),
        'file_sha256': hashlib.sha256(packed).hexdigest(),
        'index': record['index'],
        'seed': record['seed'],
        'first': record['first'],
        'status': record['status'],
    }


def _read_record(path):
    try:
        return json.loads(gzip.decompress(Path(path).read_bytes()))
    except (OSError, EOFError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('Frozen match record is unreadable: ' + str(path)) from exc


def _verify_credited_records(run_dir, schedule, checkpoint, provenance_sha256):
    position = checkpoint['schedule_position']
    expected = set()
    for offset in range(position):
        row = schedule[offset]
        path = _record_path(run_dir, offset, row)
        expected.add(path.resolve())
        if not path.is_file():
            raise ValueError('Credited match record missing at position ' + str(offset))
        _validate_scheduled_record(_read_record(path), row, provenance_sha256)
    actual = {path.resolve() for path in (Path(run_dir) / 'records').glob('*.json.gz')}
    allowed_orphan = set()
    if position < len(schedule):
        orphan = _record_path(run_dir, position, schedule[position]).resolve()
        if orphan in actual:
            allowed_orphan.add(orphan)
    extras = actual - expected - allowed_orphan
    if extras:
        raise ValueError('Uncredited match records exist beyond the checkpoint')


def _write_checkpoint(run_dir, checkpoint):
    atomic_write(Path(run_dir) / 'CHECKPOINT.json', canonical_bytes(checkpoint))


def run_frozen(run_dir, match_runner=record_match, stop_after=None,
               interruption_hook=None):
    """Run exact scheduled matches, advancing only after durable validation."""
    if stop_after is not None and (type(stop_after) is not int or stop_after <= 0):
        raise ValueError('stop_after must be a positive integer')
    run_dir = Path(run_dir).resolve()
    manifest, schedule = load_freeze(run_dir)
    checkpoint = _load_checkpoint(run_dir, manifest, schedule)
    position = checkpoint['schedule_position']
    if position == len(schedule):
        return summarize_completed_run(run_dir)

    current_inputs = _component_hashes(ROOT, schedule)
    decision = assess_resume(checkpoint, current_inputs, frozen_schedule=schedule)
    if decision['status'] == 'RESTART_FULL_EVALUATION':
        return decision
    if decision['status'] == 'BLOCKED_HALT':
        return {
            **decision,
            'credited_matches': position,
            'halted_match': dict(checkpoint['next_match']),
            'halt_record': checkpoint['halt_record'],
        }
    _verify_credited_records(run_dir, schedule, checkpoint,
                             manifest['provenance_sha256'])

    played = 0
    while position < len(schedule) and (stop_after is None or played < stop_after):
        row = schedule[position]
        record = match_runner(row['index'], manifest['provenance_sha256'])
        _validate_scheduled_record(record, row, manifest['provenance_sha256'])
        if record['status'] == 'HALT':
            metadata = _write_or_verify_record(
                _record_path(run_dir, position, row, 'halts'), record)
            checkpoint = {
                **checkpoint,
                'status': 'BLOCKED_HALT',
                'halt_kind': 'RULES',
                'schedule_position': position,
                'credited_matches': position,
                'next_match': dict(row),
                'halt_record': metadata,
            }
            _write_checkpoint(run_dir, checkpoint)
            return {
                'status': 'BLOCKED_HALT',
                'credited_matches': position,
                'halted_match': dict(row),
                'halt_record': metadata,
            }

        metadata = _write_or_verify_record(
            _record_path(run_dir, position, row), record)
        if interruption_hook is not None:
            interruption_hook(record)
        position += 1
        played += 1
        checkpoint = {
            **checkpoint,
            'status': ('COMPLETE_PENDING_SUMMARY' if position == len(schedule)
                       else 'RUNNING'),
            'halt_kind': 'INFRASTRUCTURE',
            'schedule_position': position,
            'credited_matches': position,
            'next_match': (dict(schedule[position]) if position < len(schedule) else None),
            'last_record': metadata,
            'halt_record': None,
        }
        _write_checkpoint(run_dir, checkpoint)

    if position == len(schedule):
        return summarize_completed_run(run_dir)
    return {'status': 'PAUSED', 'credited_matches': position,
            'target_matches': len(schedule), 'next_match': dict(schedule[position])}


def resume_frozen(run_dir, match_runner=record_match, stop_after=None):
    """Resume by replaying the exact checkpoint seed under the same freeze."""
    return run_frozen(run_dir, match_runner=match_runner, stop_after=stop_after)


def _sorted_counter(counter):
    return {key: counter[key] for key in sorted(counter)}


def aggregate_results(records):
    """Aggregate already validated final records into numerical results only."""
    wins, starts, turns = Counter(), Counter(), Counter()
    win_by_start = {'A': Counter(), 'B': Counter()}
    card_plays, interactions = Counter(), Counter()
    decisions, combos, lanes = Counter(), Counter(), Counter()
    seen_indexes, seen_seeds = set(), set()
    first_player_wins = total_turns = count = 0
    for record in records:
        if (not isinstance(record, dict) or type(record.get('index')) is not int
                or type(record.get('seed')) is not int
                or record.get('first') not in ('A', 'B')
                or record.get('winner') not in ('A', 'B')
                or type(record.get('turn')) is not int or record['turn'] <= 0
                or not isinstance(record.get('events'), list)):
            raise ValueError('Complete numerical match facts required')
        if record['index'] in seen_indexes or record['seed'] in seen_seeds:
            raise ValueError('Duplicate final match identity')
        seen_indexes.add(record['index'])
        seen_seeds.add(record['seed'])
        first, winner, turn = record['first'], record['winner'], record['turn']
        count += 1
        wins[winner] += 1
        starts[first] += 1
        win_by_start[first][winner] += 1
        turns[str(turn)] += 1
        total_turns += turn
        first_player_wins += winner == first
        for event in record['events']:
            if not isinstance(event, dict):
                raise ValueError('Final event facts must be objects')
            if event.get('type') == 'PAID_PLAY' and isinstance(event.get('card'), str):
                card_plays[event['card'].split('#')[0]] += 1
            if (event.get('type') == 'JUDGE_PATH' and isinstance(event.get('card'), str)
                    and isinstance(event.get('kind'), str)):
                interactions[event['card'].split('#')[0] + '|' + event['kind']] += 1
            if event.get('type') == 'BOT_DECISION':
                values = [event.get('decision_type'), event.get('source', ''), event.get('chosen')]
                if all(isinstance(value, str) for value in values):
                    decisions['|'.join(values)] += 1
            if isinstance(event.get('combo_id'), str) and event['combo_id']:
                combos[event['combo_id']] += 1
            if isinstance(event.get('lane_id'), str) and event['lane_id']:
                lanes[event['lane_id']] += 1
    if count == 0:
        raise ValueError('At least one completed match is required')
    return {
        'matches_played': count,
        'wins': {'A': wins['A'], 'B': wins['B']},
        'losses': {'A': wins['B'], 'B': wins['A']},
        'win_rate': {'A': round(wins['A'] / count, 8),
                     'B': round(wins['B'] / count, 8)},
        'starts': {'A': starts['A'], 'B': starts['B']},
        'wins_by_starting_deck': {
            first: {'A': win_by_start[first]['A'], 'B': win_by_start[first]['B']}
            for first in ('A', 'B')},
        'first_player_wins': first_player_wins,
        'first_player_win_rate': round(first_player_wins / count, 8),
        'turn_distribution': {key: turns[key] for key in sorted(turns, key=int)},
        'mean_turns': round(total_turns / count, 8),
        'card_play_frequency': _sorted_counter(card_plays),
        'interaction_frequency': _sorted_counter(interactions),
        'decision_frequency': _sorted_counter(decisions),
        'combo_frequency': _sorted_counter(combos),
        'lane_frequency': _sorted_counter(lanes),
    }


def summarize_completed_run(run_dir):
    """Revalidate all 10,000 records and atomically publish final numbers."""
    run_dir = Path(run_dir).resolve()
    manifest, schedule = load_freeze(run_dir)
    checkpoint = _load_checkpoint(run_dir, manifest, schedule)
    if (checkpoint['schedule_position'] != 10000
            or checkpoint['credited_matches'] != 10000
            or checkpoint['halt_kind'] == 'RULES'):
        raise ValueError('Exactly 10000 credited matches and zero unresolved halts required')
    current_inputs = _component_hashes(ROOT, schedule)
    if current_inputs != manifest['frozen_inputs']:
        raise ValueError('Frozen inputs changed; a new freeze and full restart are required')

    expected_paths = {_record_path(run_dir, position, row).resolve()
                      for position, row in enumerate(schedule)}
    actual_paths = {path.resolve() for path in (run_dir / 'records').glob('*.json.gz')}
    if actual_paths != expected_paths:
        raise ValueError('Final record set does not exactly match all 10000 positions')
    entries = []

    def validated_facts():
        for position, row in enumerate(schedule):
            path = _record_path(run_dir, position, row)
            packed = path.read_bytes()
            record = _read_record(path)
            _validate_scheduled_record(record, row, manifest['provenance_sha256'])
            if record['status'] != 'SOFTWARE_COMPLETED':
                raise ValueError('Final record set contains a HALT')
            raw = canonical_bytes(record)
            if gzip.decompress(packed) != raw:
                raise ValueError('Final record is not canonical JSON evidence')
            transcript = record['transcript']
            entries.append({
                'position': position, 'file': path.relative_to(run_dir).as_posix(),
                'index': row['index'], 'seed': row['seed'], 'first': row['first'],
                'winner': transcript['winner'], 'turn': transcript['turn'],
                'record_sha256': hashlib.sha256(raw).hexdigest(),
                'file_sha256': hashlib.sha256(packed).hexdigest(),
            })
            yield {
                'index': row['index'], 'seed': row['seed'], 'first': row['first'],
                'winner': transcript['winner'], 'turn': transcript['turn'],
                'events': transcript['events'],
            }

    numerical = aggregate_results(validated_facts())
    if numerical['matches_played'] != 10000 or numerical['starts'] != {'A': 5000, 'B': 5000}:
        raise ValueError('Final numerical aggregation lost matches or start balance')
    packed_manifest = gzip.compress(canonical_bytes(entries), mtime=0)
    result = {
        'schema': 'loaded-pair-final-results-v1',
        'status': 'COMPLETED',
        'bots': [dict(bot) for bot in BOT_ROSTER],
        'judge_layers': [dict(judge) for judge in JUDGE_LAYERS],
        'frozen_inputs': dict(manifest['frozen_inputs']),
        'cohort_sha256': manifest['cohort_sha256'],
        'provenance_sha256': manifest['provenance_sha256'],
        'halted_matches': 0,
        'record_manifest_file': 'RECORD_MANIFEST.json.gz',
        'record_manifest_sha256': hashlib.sha256(packed_manifest).hexdigest(),
        'numerical_results': numerical,
    }
    atomic_write(run_dir / 'RECORD_MANIFEST.json.gz', packed_manifest)
    atomic_write(run_dir / 'FINAL_RESULTS.json', canonical_bytes(result))
    checkpoint = {
        **checkpoint,
        'status': 'COMPLETED',
        'final_results_sha256': hashlib.sha256(canonical_bytes(result)).hexdigest(),
    }
    _write_checkpoint(run_dir, checkpoint)
    return result


def status_frozen(run_dir):
    run_dir = Path(run_dir).resolve()
    manifest, schedule = load_freeze(run_dir)
    checkpoint = _load_checkpoint(run_dir, manifest, schedule)
    current_inputs = _component_hashes(ROOT, schedule)
    if current_inputs != manifest['frozen_inputs']:
        return {'status': 'RESTART_FULL_EVALUATION',
                'invalidate_all_prior_results': True,
                'restart_schedule_from_position': 0,
                'credited_matches': checkpoint['credited_matches']}
    return {
        'status': checkpoint['status'],
        'credited_matches': checkpoint['credited_matches'],
        'target_matches': len(schedule),
        'next_match': checkpoint['next_match'],
        'halt_kind': checkpoint['halt_kind'],
        'judge_layers': [dict(judge) for judge in JUDGE_LAYERS],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    freeze = commands.add_parser('freeze')
    freeze.add_argument('--root', type=Path, default=ROOT)
    freeze.add_argument('--cohort', type=Path, required=True)
    freeze.add_argument('--preparation', type=Path, required=True)
    freeze.add_argument('--out', type=Path, required=True)
    freeze.add_argument('--review', type=Path)
    freeze.add_argument('--strategy-review', type=Path)
    for name in ('run', 'resume'):
        command = commands.add_parser(name)
        command.add_argument('--run-dir', type=Path, required=True)
        command.add_argument('--stop-after', type=int)
    status = commands.add_parser('status')
    status.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'freeze':
            result = create_freeze(args.root, args.cohort, args.preparation, args.out,
                                   args.review, args.strategy_review)
        elif args.command == 'run':
            result = run_frozen(args.run_dir, stop_after=args.stop_after)
        elif args.command == 'resume':
            result = resume_frozen(args.run_dir, stop_after=args.stop_after)
        else:
            result = status_frozen(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        print(json.dumps({'status': 'ERROR', 'error': str(exc)}, indent=2,
                         ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


__all__ = [
    'BOT_ROSTER', 'FROZEN_COMPONENTS', 'JUDGE_LAYERS', 'ROOT', 'aggregate_results',
    'atomic_write', 'create_freeze', 'load_freeze', 'main', 'resume_frozen',
    'run_frozen', 'seed_for', 'status_frozen', 'summarize_completed_run',
    'validate_schedule',
]


if __name__ == '__main__':
    raise SystemExit(main())
