"""Loaded-pair evidence/restart contracts; no card rulings or strategy learning."""
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse

from loaded_digivolution import BY_SEAT
from seeded_opening_probe import seed_for

FROZEN_COMPONENTS = ('engine', 'rules_format', 'decks', 'pilots', 'criteria', 'roadmaps', 'schedule')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def load_object(path):
    value = json.loads(Path(path).read_bytes())
    require(isinstance(value, dict), 'Expected JSON object: ' + str(path))
    return value


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_file(root, filename, folder='RULES'):
    require(text(filename), 'Evidence file path missing')
    root = Path(root).resolve()
    base = (root / folder).resolve()
    path = (root / filename).resolve()
    require(base.is_relative_to(root) and path.is_relative_to(base), 'Evidence path escapes ' + folder)
    return path


def iso_date(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'ISO date required')
    return date.fromisoformat(value)


def validate_citations(citations, source_ids):
    require(isinstance(citations, list) and bool(citations), 'Official citations required')
    for citation in citations:
        require(isinstance(citation, dict) and citation.get('source_id') in source_ids
                and text(citation.get('locator')), 'Citation must reference a pinned source and locator')


def validate_rules_pin(root):
    pin = load_object(Path(root) / 'RULES/RULES_LOCK.json')
    require(pin.get('schema') == 'loaded-pair-rules-lock-v1' and pin.get('status') == 'PINNED',
            'Rules/format snapshot is not PINNED')
    format_ = pin.get('format')
    require(isinstance(format_, dict) and text(format_.get('name')) and text(format_.get('region'))
            and text(pin.get('language')), 'Selected format, region and language required')
    as_of = iso_date(pin.get('as_of_date'))
    review = pin.get('review')
    require(isinstance(review, dict) and text(review.get('reviewer'))
            and review.get('verdict') == 'VERIFIED', 'Rules snapshot review missing')
    documents = pin.get('documents')
    require(isinstance(documents, list) and bool(documents), 'Official snapshot documents missing')
    kinds, ids = set(), set()
    for document in documents:
        require(isinstance(document, dict) and text(document.get('id'))
                and document['id'] not in ids, 'Distinct document IDs required')
        ids.add(document['id'])
        kinds.add(document['kind'])
        require(text(document.get('edition')) and text(document.get('citation')), 'Edition/citation missing')
        require(iso_date(document.get('effective_date')) <= as_of, 'Document not effective on selected date')
        url = urlparse(document['url'])
        require(url.scheme == 'https' and (url.hostname == 'digimoncard.com'
                or (url.hostname or '').endswith('.digimoncard.com')), 'Official Digimon URL required')
        path = source_file(root, document['file'])
        require(path.stat().st_size > 0 and sha256(path) == document['sha256'], 'Official document hash mismatch')
    require({'RULES', 'ERRATA', 'RESTRICTIONS', 'CARD_TEXT', 'CARD_QA'} <= kinds,
            'Pin rules, errata, restrictions, card text and card Q&A')
    return pin


def trace_reference(ref, records):
    require(isinstance(ref, dict) and ref.get('kind', 'MATCH') == 'MATCH', 'Match reference required')
    available = {record['index']: (entry, record) for entry, record in records}
    require(type(ref.get('index')) is int and ref['index'] in available, 'Unknown evidence match')
    entry, record = available[ref['index']]
    offset = ref.get('event_index')
    require(ref.get('seed') == record['seed'] and ref.get('record_sha256') == entry['record_sha256']
            and type(offset) is int and 0 <= offset < len(record['transcript']['events']),
            'Evidence reference does not bind to the exact trace')
    return record['transcript']['events'][offset]


def interaction_scope(event):
    """Bind a branch to the actual decision/effect source, not its choice label."""
    if event.get('type') == 'BOT_DECISION':
        require(text(event.get('decision_type')) and event.get('seat') in ('A', 'B'),
                'Decision interaction identity missing')
        source = event.get('source') or event.get('tamer') or event.get('attacker')
        require(source is None or text(source), 'Decision source identity invalid')
        return {'type': 'BOT_DECISION', 'decision_type': event['decision_type'],
                'seat': event['seat'], 'card': source.split('#')[0] if source else None}
    require(event.get('type') == 'JUDGE_PATH' and text(event.get('card'))
            and event.get('owner') in ('A', 'B'), 'Judge-path interaction identity missing')
    return {key: event.get(key) for key in ('type', 'card', 'owner', 'trigger', 'source', 'cause')}


def observed_branch(event):
    value = event.get('chosen') if event.get('type') == 'BOT_DECISION' else event.get('kind')
    require(text(value), 'Observed branch identity missing')
    return value


def validate_coverage(root, provenance_sha256, records, source_ids, snapshot_validator=None):
    coverage = load_object(Path(root) / 'RULES/INTERACTION_COVERAGE.json')
    require(coverage.get('schema') == 'loaded-pair-interaction-coverage-v1'
            and coverage.get('status') == 'VERIFIED'
            and coverage.get('provenance_sha256') == provenance_sha256, 'Current verified coverage required')
    entries = coverage.get('entries')
    require(isinstance(entries, list) and bool(entries), 'Interaction branch inventories missing')
    required = {(record['index'], offset) for _, record in records
                for offset, event in enumerate(record['transcript']['events'])
                if event['type'] in ('BOT_DECISION', 'JUDGE_PATH')}
    covered, ids, scenarios = set(), set(), set()
    for entry in entries:
        require(isinstance(entry, dict) and text(entry.get('interaction_id'))
                and entry['interaction_id'] not in ids, 'Distinct interaction IDs required')
        ids.add(entry['interaction_id'])
        require(entry.get('card') is None or entry['card'] in set(BY_SEAT['A']) | set(BY_SEAT['B']),
                'Interaction outside loaded decks')
        review = entry.get('inventory_review')
        require(isinstance(review, dict) and text(review.get('reviewer'))
                and review.get('verdict') == 'VERIFIED' and review.get('complete') is True,
                'Complete legal branch inventory must be judge-reviewed')
        validate_citations(review.get('citations'), source_ids)
        encounters = entry.get('encounters')
        require(isinstance(encounters, list) and bool(encounters), 'Encounter references missing')
        scope, encounter_ids, observations = None, set(), set()
        for ref in encounters:
            event = trace_reference(ref, records)
            actual_scope = interaction_scope(event)
            if scope is None:
                scope = actual_scope
            require(actual_scope == scope and actual_scope['card'] == entry.get('card'),
                    'Encounter belongs to another card/decision/effect interaction')
            encounter_ids.add((ref['index'], ref['event_index']))
            observations.add(observed_branch(event))
            covered.add((ref['index'], ref['event_index']))
        branches = entry.get('branches')
        require(isinstance(branches, list) and bool(branches), 'Alternatives missing')
        branch_ids, legality = set(), {}
        for branch in branches:
            require(isinstance(branch, dict) and text(branch.get('id'))
                    and branch['id'] not in branch_ids, 'Distinct branch IDs required')
            branch_ids.add(branch['id'])
            require(branch.get('legality') in ('LEGAL', 'ILLEGAL'), 'Unverified branch blocks eligibility')
            legality[branch['id']] = branch['legality']
            validate_citations(branch.get('citations'), source_ids)
            if branch['legality'] == 'ILLEGAL':
                continue
            evidence = branch.get('evidence')
            require(isinstance(evidence, list) and bool(evidence), 'Legal branch has no evaluated evidence')
            for ref in evidence:
                if ref.get('kind', 'MATCH') == 'MATCH':
                    event = trace_reference(ref, records)
                    require((ref['index'], ref['event_index']) in encounter_ids
                            and interaction_scope(event) == scope
                            and observed_branch(event) == branch['id'],
                            'Trace does not exercise this legal branch in its own interaction')
                else:
                    require(ref.get('kind') == 'SCENARIO', 'Unknown evidence kind')
                    path = source_file(root, ref['file'], 'RULES/scenarios')
                    require(sha256(path) == ref['sha256'], 'Scenario hash mismatch')
                    scenario = load_object(path)
                    require(scenario.get('schema') == 'loaded-pair-targeted-scenario-v1'
                            and scenario.get('provenance_sha256') == provenance_sha256
                            and scenario.get('interaction_id') == entry['interaction_id']
                            and scenario.get('branch_id') == branch['id']
                            and scenario.get('counts_as_match') is False
                            and isinstance(scenario.get('actions'), list) and bool(scenario['actions']),
                            'Scenario must be reproducible, current and excluded from match counts')
                    require(snapshot_validator is not None, 'Scenario snapshot validator required')
                    snapshot_validator(scenario['initial_state'])
                    snapshot_validator(scenario['final_state'])
                    reviewed = scenario.get('rule_review')
                    require(isinstance(reviewed, dict) and text(reviewed.get('reviewer'))
                            and reviewed.get('verdict') == 'VERIFIED', 'Scenario rules review missing')
                    validate_citations(reviewed.get('citations'), source_ids)
                    scenarios.add(str(path))
        require(all(legality.get(branch) == 'LEGAL' for branch in observations),
                'Observed branch is missing from inventory or classified ILLEGAL')
    require(required <= covered, 'Encountered decision/interaction events have uncovered alternatives')
    return {'interactions': len(entries), 'covered_events': len(required), 'targeted_scenarios': len(scenarios),
            'scenario_match_credit': 0}


def validate_criteria(criteria):
    require(isinstance(criteria, dict) and criteria.get('schema') == 'loaded-pair-lane-criteria-v1'
            and criteria.get('status') == 'PREREGISTERED', 'Preregistered lane criteria required')
    for key in ('minimum_independent_seeds', 'minimum_evaluated_legal_alternatives'):
        require(type(criteria.get(key)) is int and criteria[key] >= 2, 'Evidence floor must include multiple seeds/alternatives')
    return criteria


def validate_strategy_lane(lane, criteria, criteria_sha256, records):
    criteria = validate_criteria(criteria)
    require(isinstance(lane, dict) and lane.get('lane') in ('GREEN', 'YELLOW', 'RED')
            and lane.get('legality') == 'LEGAL' and lane.get('criteria_sha256') == criteria_sha256,
            'Lane must be legal and use the preregistered criteria')
    require(lane.get('condition') and all(text(lane.get(field)) for field in
            ('objective', 'metric', 'uncertainty', 'approval_basis'))
            and lane.get('direction') in ('MAXIMIZE', 'MINIMIZE'), 'Objective, comparison and uncertainty required')
    refs = lane.get('evidence')
    require(isinstance(refs, list), 'Lane trace evidence required')
    scope, lane_refs = None, set()
    for ref in refs:
        event = trace_reference(ref, records)
        actual_scope = interaction_scope(event)
        if scope is None:
            scope = actual_scope
        require(actual_scope == scope and event['type'] == 'BOT_DECISION',
                'Lane evidence mixes unrelated decision/effect contexts')
        lane_refs.add((ref['index'], ref['event_index']))
    require(len({ref['seed'] for ref in refs}) >= criteria['minimum_independent_seeds'],
            'Multiple independent seeds required')
    alternatives = lane.get('compared_alternatives')
    require(isinstance(alternatives, list)
            and len(alternatives) >= criteria['minimum_evaluated_legal_alternatives'],
            'Evaluated legal alternatives required')
    ids = set()
    for alternative in alternatives:
        require(isinstance(alternative, dict) and text(alternative.get('id'))
                and alternative['id'] not in ids, 'Distinct evaluated alternatives required')
        ids.add(alternative['id'])
        metrics = alternative.get('metrics')
        require(isinstance(metrics, dict) and lane['metric'] in metrics and all(
                type(value) in (int, float) and math.isfinite(value) for value in metrics.values()),
                'Numeric comparable observations required for each alternative')
        evidence = alternative.get('evidence')
        require(isinstance(evidence, list) and bool(evidence), 'Alternative has no evaluated trace')
        for ref in evidence:
            event = trace_reference(ref, records)
            require((ref['index'], ref['event_index']) in lane_refs and interaction_scope(event) == scope
                    and event.get('type') == 'BOT_DECISION' and event.get('chosen') == alternative['id'],
                    'Alternative must have been selected in its referenced decision trace')


def validate_strategy_review(review, gate, pilots, criteria_sha256, roadmap_hashes):
    require(isinstance(review, dict) and review.get('kind') == 'STRATEGY_EVALUATION_REVIEW'
            and text(review.get('reviewer')), 'Separate strategy-effectiveness review required')
    require(review.get('cohort_sha256') == gate['cohort_sha256']
            and review.get('provenance_sha256') == gate['provenance_sha256']
            and review.get('criteria_sha256') == criteria_sha256
            and review.get('pilot_sha256') == {s: pilots[s]['sha256'] for s in ('A', 'B')}
            and review.get('roadmap_sha256') == roadmap_hashes
            and review.get('roadmap_verdicts') == {'A': 'APPROVED', 'B': 'APPROVED'},
            'Strategy review must bind current cohort, criteria, both pilots and roadmaps')


def assess_resume(checkpoint, current_frozen_inputs, requested_seed=None, *, frozen_schedule=None):
    require(isinstance(checkpoint, dict), 'Checkpoint object required')
    original = checkpoint.get('frozen_inputs')
    for frozen in (original, current_frozen_inputs):
        require(isinstance(frozen, dict) and set(frozen) == set(FROZEN_COMPONENTS)
                and all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for v in frozen.values()),
                'Complete frozen component hashes required')
    require(isinstance(frozen_schedule, list) and len(frozen_schedule) == 10000,
            'Original hash-bound 10000-match schedule required')
    for row in frozen_schedule:
        require(isinstance(row, dict) and set(row) == {'index', 'seed', 'first'}
                and type(row['index']) is int and row['index'] >= 60
                and type(row['seed']) is int and row['seed'] == seed_for(row['index'])
                and row['first'] == ('A' if row['index'] % 2 == 0 else 'B'),
                'Invalid original schedule entry')
    packed = (json.dumps(frozen_schedule, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    require(hashlib.sha256(packed).hexdigest() == original['schedule']
            and len({r['index'] for r in frozen_schedule}) == 10000
            and len({r['seed'] for r in frozen_schedule}) == 10000
            and sum(r['first'] == 'A' for r in frozen_schedule) == 5000,
            'Original schedule hash, uniqueness or balance mismatch')
    match = checkpoint.get('next_match')
    require(isinstance(match, dict) and type(match.get('index')) is int and match['index'] >= 60
            and match.get('seed') == seed_for(match['index'])
            and match.get('first') == ('A' if match['index'] % 2 == 0 else 'B'), 'Original scheduled match required')
    position = checkpoint.get('schedule_position')
    require(type(position) is int and 0 <= position < len(frozen_schedule)
            and match == frozen_schedule[position], 'Checkpoint match must equal its frozen schedule position')
    require(requested_seed is None or requested_seed == match['seed'], 'Replacing a halted seed is forbidden')
    if original != current_frozen_inputs:
        return {'status': 'RESTART_FULL_EVALUATION', 'invalidate_all_prior_results': True,
                'restart_schedule_from_position': 0, 'retained_halted_match': dict(match),
                'new_freeze_required': True}
    require(checkpoint.get('halt_kind') in ('RULES', 'INFRASTRUCTURE'), 'Explicit halt/interruption kind required')
    if checkpoint['halt_kind'] == 'RULES':
        return {'status': 'BLOCKED_HALT', 'retained_halted_match': dict(match), 'invalidate_all_prior_results': False}
    return {'status': 'REPLAY_ORIGINAL_MATCH', 'match': dict(match),
            'verify_replay_before_credit': True, 'invalidate_all_prior_results': False}
