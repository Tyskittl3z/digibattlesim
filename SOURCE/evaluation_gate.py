"""Fail-closed preparation gate; does not run or certify final matches.

Independent review is an external prerequisite. A review file is an explicit
attestation, not something this program can authenticate or manufacture.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import random

from match_evidence import ROOT, canonical_bytes, digest, provenance
from loaded_digivolution import BY_SEAT
from seeded_opening_probe import seed_for


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def validate_snapshot(state):
    if not isinstance(state, dict) or set(state['players']) != {'A', 'B'}:
        raise ValueError('Complete two-player snapshot required')
    runtime = state['runtime']
    for key in ('i', 'seed', 'first', 'active', 'turn', 'mem', 'actions', 'winner',
                '_security_pending', '_dp_zero_pending'):
        if key not in runtime:
            raise ValueError('Missing runtime field: ' + key)
    if (type(runtime['mem']) is not int or not -10 <= runtime['mem'] <= 10
            or runtime['active'] not in ('A', 'B')
            or not isinstance(runtime['_security_pending'], list)
            or not isinstance(runtime['_dp_zero_pending'], list)):
        raise ValueError('Invalid memory, active player or pending queues')
    rng = state['rng_state']
    if not isinstance(rng, list) or len(rng) != 3 or not isinstance(rng[1], list):
        raise ValueError('Complete RNG state required')
    random.Random().setstate((rng[0], tuple(rng[1]), rng[2]))
    for seat, player in state['players'].items():
        zones = player['zones']
        if player['seat'] != seat or zones['seat'] != seat:
            raise ValueError('Snapshot seat mismatch')
        physical = []
        for key in ('deck', 'hand', 'trash', 'security', 'battle'):
            if not isinstance(zones[key], list) or not all(nonblank(c) for c in zones[key]):
                raise ValueError('Invalid physical zone: ' + key)
            physical.extend(zones[key])
        if not isinstance(zones['effects'], list) or not isinstance(zones['statuses'], dict):
            raise ValueError('Missing effects/statuses')
        for key in ('eggdeck', 'breeding', 'suspended', 'sick', 'once_used'):
            if not isinstance(player[key], list) or not all(nonblank(c) for c in player[key]):
                raise ValueError('Invalid player field: ' + key)
        physical.extend(player['eggdeck'])
        physical.extend(player['breeding'])
        for anchor, stack in player['stacks'].items():
            if (not isinstance(stack, list) or not stack or stack[-1] != anchor
                    or anchor not in zones['battle']):
                raise ValueError('Snapshot stack anchor mismatch')
            physical.extend(stack[:-1])
        expected = Counter(f'{card}#{i}' for card, info in BY_SEAT[seat].items()
                           for i in range(1, info['qty'] + 1))
        if Counter(physical) != expected:
            raise ValueError('Snapshot physical-card mismatch: ' + seat)


def validate_record(record):
    if record['schema'] != 'loaded-pair-match-evidence-v1':
        raise ValueError('Unknown match schema')
    transcript = record['transcript']
    for key in ('index', 'seed', 'first'):
        if transcript[key] != record[key]:
            raise ValueError('Transcript identity mismatch: ' + key)
    expected = {'SOFTWARE_COMPLETED': 'VALID_COMPLETE_GAME', 'HALT': 'JUDGE_HALT'}
    if transcript['status'] != expected[record['status']]:
        raise ValueError('Transcript status mismatch')
    if (not isinstance(transcript['events'], list) or not transcript['events']
            or not all(isinstance(e, dict) and nonblank(e.get('type')) for e in transcript['events'])
            or not any(e['type'] == 'TURN_START' for e in transcript['events'])):
        raise ValueError('Full turn-by-turn transcript required')
    for field in ('initial_state', 'final_state'):
        validate_snapshot(record[field])
        runtime = record[field]['runtime']
        for field_name, runtime_name in (('index', 'i'), ('seed', 'seed'), ('first', 'first')):
            if runtime[runtime_name] != record[field_name]:
                raise ValueError('Snapshot identity mismatch: ' + field_name)
    initial, final = record['initial_state']['runtime'], record['final_state']['runtime']
    if initial['turn'] != 0 or initial['actions'] != 0 or initial['winner'] is not None:
        raise ValueError('Initial state is not game setup')
    if final['turn'] != transcript['turn'] or final['actions'] != transcript['actions']:
        raise ValueError('Final turn/action count mismatch')


def read_records(cohort_dir, summary):
    """Load hash-bound records, refusing traversal, altered data, and duplicates."""
    cohort_dir = Path(cohort_dir).resolve()
    records, issues, seen_indexes, seen_seeds = [], [], set(), set()
    for entry in summary['records']:
        filename = entry['file']
        path = (cohort_dir / filename).resolve()
        if path.parent != cohort_dir or not path.name.startswith('MATCH_') or not path.name.endswith('.json.gz'):
            issues.append({'code': 'INVALID_TRANSCRIPT_PATH', 'detail': filename})
            continue
        try:
            compressed = path.read_bytes()
            raw = gzip.decompress(compressed)
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError('Match record must be an object')
            if (hashlib.sha256(compressed).hexdigest() != entry['file_sha256']
                    or hashlib.sha256(raw).hexdigest() != entry['record_sha256']):
                issues.append({'code': 'TRANSCRIPT_HASH_MISMATCH', 'detail': filename})
            index, seed = record['index'], record['seed']
            if (type(index) is not int or index < 0 or type(seed) is not int
                    or seed != seed_for(index)
                    or record['first'] != ('A' if index % 2 == 0 else 'B')):
                issues.append({'code': 'SEED_MAPPING_INVALID', 'detail': filename})
            if index in seen_indexes or seed in seen_seeds:
                issues.append({'code': 'DUPLICATE_MATCH_ID_OR_SEED', 'detail': str(index)})
            seen_indexes.add(index)
            seen_seeds.add(seed)
            for key in ('index', 'seed', 'first', 'status'):
                if record[key] != entry[key]:
                    issues.append({'code': 'MATCH_INDEX_MISMATCH', 'detail': filename + ':' + key})
            if record['provenance_sha256'] != summary['provenance_sha256']:
                issues.append({'code': 'MATCH_PROVENANCE_MISMATCH', 'detail': filename})
            if entry.get('replay_verified') is not True:
                issues.append({'code': 'REPLAY_MISSING', 'detail': filename})
            try:
                validate_record(record)
            except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
                issues.append({'code': 'MATCH_SCHEMA_INVALID', 'detail': filename + ':' + str(exc)})
                continue
            records.append((entry, record))
        except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
            issues.append({'code': 'TRANSCRIPT_UNREADABLE', 'detail': filename + ':' + str(exc)})
    return records, issues


def assess_eligibility(root, cohort_dir, review_path=None):
    root, cohort_dir = Path(root).resolve(), Path(cohort_dir).resolve()
    blockers = []

    def block(code, detail):
        blockers.append({'code': code, 'detail': detail})

    result = {'schema': 'loaded-pair-evaluation-gate-v1', 'eligible': False,
              'status': 'BLOCKED', 'blockers': blockers}
    try:
        summary = json.loads((cohort_dir / 'cohort.json').read_bytes())
        inputs = json.loads((cohort_dir / 'provenance.json').read_bytes())
        if (not isinstance(summary, dict) or not isinstance(inputs, dict)
                or not isinstance(summary.get('records'), list)
                or not all(isinstance(entry, dict) for entry in summary['records'])):
            raise ValueError('Cohort/provenance must be complete objects')
        if digest(inputs) != summary['provenance_sha256']:
            block('PROVENANCE_HASH_MISMATCH', 'Cohort does not bind this provenance document')
        try:
            current = provenance(root)
            if current != inputs:
                block('SOURCE_OR_DECK_CHANGED', 'Rerun the entire cohort with current source and inputs')
        except (OSError, ValueError, KeyError) as exc:
            block('SOURCE_OR_DECK_CHANGED', str(exc))
        records, issues = read_records(cohort_dir, summary)
        blockers.extend(issues)
        if len(records) != 60 or summary['attempted'] != 60:
            block('FACT_FINDING_COHORT_NOT_60', f'{len(records)} records; exactly 60 required')
        starts = Counter(record['first'] for _, record in records)
        if starts != {'A': 30, 'B': 30}:
            block('START_BALANCE_INVALID', str(dict(starts)))
        completed = 0
        optional = Counter()
        for entry, record in records:
            transcript = record['transcript']
            if record['status'] != 'SOFTWARE_COMPLETED' or transcript['halt_reason']:
                block('UNRESOLVED_MATCH_HALT', str(record['index']) + ': ' + str(transcript['halt_reason']))
            else:
                completed += 1
                terminals = [i for i, event in enumerate(transcript['events'])
                             if event['type'] in ('GAME_END', 'WIN_DRAW_PHASE_DECKOUT')]
                if (terminals != [len(transcript['events']) - 1]
                        or transcript['winner'] not in ('A', 'B')
                        or record['final_state']['runtime']['winner'] != transcript['winner']):
                    block('TERMINAL_STATE_INVALID', str(record['index']))
            if record['physical_integrity']['status'] != 'PASS':
                block('PHYSICAL_INTEGRITY_FAILED', str(record['index']))
            for event in transcript['events']:
                if event.get('kind') == 'TOP_ATTACK_OPTIONAL_UNMODELED_DECLINED':
                    optional[event['card']] += 1
        if optional:
            block('UNMODELED_OPTIONAL_ATTACKS', str(dict(optional)))
        result['software_completed'] = completed
        result['starts'] = dict(starts)
        result['cohort_sha256'] = file_hash(cohort_dir / 'cohort.json')
        result['provenance_sha256'] = summary['provenance_sha256']

        review = None
        if review_path is None:
            block('INDEPENDENT_JUDGE_REVIEW_MISSING', 'No independent rules-review attestation supplied')
        else:
            try:
                review = json.loads(Path(review_path).read_bytes())
                if (not isinstance(review, dict) or review.get('kind') != 'INDEPENDENT_RULES_REVIEW'
                        or not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip()
                        or review.get('cohort_sha256') != result['cohort_sha256']
                        or review.get('provenance_sha256') != result['provenance_sha256']
                        or review.get('deck_restrictions') != 'VERIFIED'):
                    raise ValueError('Review identity, provenance, or deck restrictions are unverified')
                sources = review.get('official_sources', [])
                if not isinstance(sources, list) or not sources:
                    raise ValueError('Official rules source snapshots missing')
                source_ids = set()
                for source in sources:
                    if (not isinstance(source, dict) or not nonblank(source.get('id'))
                            or source['id'] in source_ids):
                        raise ValueError('Distinct official source identifiers required')
                    source_ids.add(source['id'])
                    url = urlparse(source['url'])
                    path = (root / source['file']).resolve()
                    if (url.scheme != 'https' or url.hostname != 'world.digimoncard.com'
                            or not path.is_relative_to(root / 'RULES')
                            or file_hash(path) != source['sha256']
                            or path.stat().st_size == 0
                            or not nonblank(source.get('citation'))):
                        raise ValueError('Official source/citation/hash invalid')
                reviewed = review.get('matches', [])
                if not isinstance(reviewed, list) or not all(isinstance(r, dict) for r in reviewed):
                    raise ValueError('Match reviews must be objects')
                by_index = {row['index']: row for row in reviewed}
                if len(reviewed) != 60 or len(by_index) != 60:
                    raise ValueError('Exactly 60 distinct match reviews required')
                checks = {'physical_cards', 'memory', 'timing', 'counter_windows',
                          'once_per_turn', 'optional_choices', 'terminal_state', 'card_rules'}
                for entry, record in records:
                    row = by_index[record['index']]
                    if (row['record_sha256'] != entry['record_sha256']
                            or row['verdict'] != 'JUDGE_CERTIFIED'
                            or not checks.issubset(row.get('verified_checks', []))
                            or not row.get('citations')):
                        raise ValueError('Incomplete review for match ' + str(record['index']))
                    citations = row['citations']
                    if (not isinstance(citations, list) or not all(
                            isinstance(c, dict) and c.get('source_id') in source_ids
                            and nonblank(c.get('locator')) for c in citations)):
                        raise ValueError('Match citations must bind to official source IDs and locators')
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                block('JUDGE_REVIEW_INVALID', str(exc))
                review = None

        roadmap_errors = []
        for seat in ('A', 'B'):
            path = root / 'ROADMAPS' / (seat + '.json')
            try:
                roadmap = json.loads(path.read_bytes())
                if (not isinstance(roadmap, dict) or roadmap.get('seat') != seat
                        or roadmap.get('provenance_sha256') != summary['provenance_sha256']
                        or roadmap.get('cohort_sha256') != result['cohort_sha256']
                        or not roadmap.get('entries')
                        or roadmap.get('unknown')
                        or review is None
                        or review.get('roadmap_sha256', {}).get(seat) != file_hash(path)
                        or review.get('roadmap_verdicts', {}).get(seat) != 'APPROVED'):
                    raise ValueError('Missing approval, classifications, or current evidence')
                for lane in roadmap['entries']:
                    if (lane['lane'] not in ('GREEN', 'YELLOW', 'RED')
                            or lane['legality'] != 'LEGAL'
                            or not lane.get('condition') or not lane.get('evidence')
                            or not lane.get('approval_basis')
                            or len({ref['seed'] for ref in lane['evidence']}) < 2):
                        raise ValueError('Lane needs legal, conditional, multi-seed evidence')
                    available = {record['index']: (entry, record) for entry, record in records}
                    for ref in lane['evidence']:
                        entry, record = available[ref['index']]
                        if (ref['seed'] != record['seed']
                                or ref['record_sha256'] != entry['record_sha256']
                                or type(ref['event_index']) is not int
                                or not 0 <= ref['event_index'] < len(record['transcript']['events'])):
                            raise ValueError('Lane reference is not bound to a reviewed trace')
                # An ILLEGAL ruling is separate from strategically RED.
                for illegal in roadmap.get('illegal', []):
                    if illegal.get('lane') is not None or not illegal.get('citation'):
                        raise ValueError('ILLEGAL must not be a strategic lane')
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                roadmap_errors.append(seat + ': ' + str(exc))
        if roadmap_errors:
            block('ROADMAPS_NOT_APPROVED', '; '.join(roadmap_errors))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        block('EVIDENCE_UNREADABLE', str(exc))
    result['eligible'] = not blockers
    result['status'] = 'ELIGIBLE_PENDING_FREEZE' if result['eligible'] else 'BLOCKED'
    return result


def write_candidate_roadmaps(root, cohort_dir):
    """Index observed situations, without interpreting heuristic scores as lanes."""
    root, cohort_dir = Path(root), Path(cohort_dir)
    summary = json.loads((cohort_dir / 'cohort.json').read_bytes())
    records, issues = read_records(cohort_dir, summary)
    if issues:
        raise ValueError('Cannot index invalid match records: ' + str(issues))
    grouped = {'A': {}, 'B': {}}
    for entry, record in records:
        for offset, event in enumerate(record['transcript']['events']):
            if event['type'] != 'BOT_DECISION' or 'position' not in event:
                continue
            seat = event['seat']
            other = 'B' if seat == 'A' else 'A'
            position = event['position']
            condition = {
                'decision_type': event['decision_type'],
                'source': event.get('source', event.get('tamer', '')).split('#')[0],
                'own_security': position['players'][seat]['security_count'],
                'opponent_security': position['players'][other]['security_count'],
                'memory_from_active_player': position['memory'],
                'active_player': position['active'],
            }
            key = digest(condition)
            if key not in grouped[seat]:
                grouped[seat][key] = {
                    'id': key, 'condition': condition, 'lane': None,
                    'legality': 'UNVERIFIED', 'status': 'UNKNOWN',
                    'reason': 'Observed heuristic choices; rules review and branch evaluation absent',
                    'evidence': [],
                }
            grouped[seat][key]['evidence'].append({
                'index': record['index'], 'seed': record['seed'], 'turn': event['t'],
                'event_index': offset, 'record_sha256': entry['record_sha256'],
                'observed_choice': event['chosen'],
            })
    folder = root / 'ROADMAPS'
    folder.mkdir(parents=True, exist_ok=True)
    if any((folder / (seat + '.json')).exists() for seat in ('A', 'B')):
        raise FileExistsError('Preserve or version existing roadmaps before regenerating')
    maps = {}
    for seat in ('A', 'B'):
        maps[seat] = {
            'schema': 'loaded-pair-roadmap-candidates-v1', 'seat': seat,
            'provenance_sha256': summary['provenance_sha256'],
            'cohort_sha256': file_hash(cohort_dir / 'cohort.json'),
            'status': 'EXPERIMENTAL_UNAPPROVED',
            'approved_counts': {'GREEN': 0, 'YELLOW': 0, 'RED': 0},
            'entries': [], 'illegal': [], 'unknown': list(grouped[seat].values()),
        }
        (folder / (seat + '.json')).write_bytes(canonical_bytes(maps[seat]))
    return maps


def prepare_evaluation(root, cohort_dir, output, review_path=None):
    """Reserve a balanced disjoint seed schedule; never fake a frozen run."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    gate = assess_eligibility(root, cohort_dir, review_path)
    summary = json.loads((Path(cohort_dir) / 'cohort.json').read_bytes())
    training_seeds = {row['seed'] for row in summary['records']}
    training_seeds.update(seed_for(i) for i in range(60))
    schedule, starts, index = [], Counter(), 60
    while len(schedule) < 10000:
        seed, first = seed_for(index), 'A' if index % 2 == 0 else 'B'
        if seed not in training_seeds and starts[first] < 5000:
            schedule.append({'index': index, 'seed': seed, 'first': first})
            starts[first] += 1
        index += 1
    if len({row['seed'] for row in schedule}) != 10000:
        raise ValueError('FINAL_SEED_COLLISION')
    if training_seeds.intersection(row['seed'] for row in schedule):
        raise ValueError('TRAINING_EVALUATION_SEED_OVERLAP')
    packed = gzip.compress(canonical_bytes(schedule), mtime=0)
    (output / 'SEEDS.json.gz').write_bytes(packed)
    report = {
        'schema': 'loaded-pair-evaluation-preparation-v1',
        'status': 'ELIGIBLE_PENDING_FREEZE' if gate['eligible'] else 'BLOCKED_NOT_FROZEN',
        'frozen': False, 'evaluation_matches_played': 0, 'target_matches': 10000,
        'planned_starts': {'A': 5000, 'B': 5000},
        'schedule_file_sha256': hashlib.sha256(packed).hexdigest(),
        'required_learning_enabled': False, 'gate': gate,
        'remaining_execution_work': [
            'Official evidence, complete independent match reviews, and approved conditional roadmaps',
            'Atomic freeze of decks, verified rules, both pilots, and both roadmaps',
            'Frozen runtime that rejects changes and disables learning/exploration',
            'Actually play 10000 matches; stream compressed full transcripts and state',
            'Atomic per-match checkpoints; resume only after hash/replay validation',
            'Report actual W/L, start splits, turns, card/combo/lane frequencies, halts, and rule status',
        ],
    }
    (output / 'PREPARATION.json').write_bytes(canonical_bytes(report))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--prepare', type=Path)
    parser.add_argument('--candidate-roadmaps', action='store_true')
    args = parser.parse_args()
    if args.candidate_roadmaps:
        write_candidate_roadmaps(ROOT, args.cohort)
    if args.prepare:
        result = prepare_evaluation(ROOT, args.cohort, args.prepare, args.review)
        eligible = result['gate']['eligible']
    else:
        result = assess_eligibility(ROOT, args.cohort, args.review)
        eligible = result['eligible']
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if eligible else 2)
