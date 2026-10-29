"""Fail-closed frozen evaluation runner for the exact loaded matchup.

This module can prepare execution software, but it cannot certify gameplay.
`create_freeze` re-runs the external-evidence gate and refuses blocked inputs.
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

from evaluation_gate import assess_eligibility, file_hash
from match_evidence import ROOT, canonical_bytes, digest, provenance
from seeded_opening_probe import seed_for
from workflow_policy import FROZEN_COMPONENTS


FREEZE_SCHEMA = 'loaded-pair-frozen-evaluation-v1'
HEX_SHA256 = re.compile(r'[0-9a-f]{64}')


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

    output.mkdir(parents=True, exist_ok=False)
    try:
        atomic_write(output / 'SEEDS.json.gz', packed_schedule)
        atomic_write(output / 'FREEZE.json', canonical_bytes(manifest))
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


__all__ = [
    'FROZEN_COMPONENTS', 'ROOT', 'atomic_write', 'create_freeze', 'load_freeze',
    'seed_for', 'validate_schedule',
]
