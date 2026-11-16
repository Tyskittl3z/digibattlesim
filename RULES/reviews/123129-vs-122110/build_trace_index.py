"""Index the archived 60-game command decisions for a separate rules review.

This extracts evidence references only. It does not approve legality, certify
matches, or convert command decisions into the older loaded-pair event schema.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CAMPAIGN = ROOT / 'ARTIFACTS/board-text-60-piercing-corrected-v2-2026-11-15'
SOURCES = ROOT / 'RULES/matchups/123129-vs-124303/sources'


def read(path):
    return json.loads(path.read_text())


def serial(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def main():
    cache = {hashlib.sha256(path.read_bytes()).hexdigest(): str(path.relative_to(ROOT))
             for path in SOURCES.iterdir() if path.is_file()}
    source_refs = defaultdict(lambda: {'count': 0, 'roles': Counter(), 'urls': set(), 'locators': set()})
    missing_sources = Counter()
    commands, event_types, effect_counts, decision_counts = Counter(), Counter(), Counter(), Counter()
    effects, decisions, cancellations, records = [], [], [], []
    for index in range(60):
        game_dir = CAMPAIGN / f'game-{index:04d}'
        paths = sorted(game_dir.glob('segment-*.json.gz'))
        if not paths:
            raise ValueError(f'Missing game {index}')
        with gzip.open(paths[-1], 'rt') as handle:
            record = json.load(handle)
        if (record['status'] != 'EXPERIMENTAL_SOFTWARE_TERMINAL'
                or record['player_policy'] != 'BOARD_TEXT_HISTORY'
                or len(record['commands']) != len(record['tracker_observations'])):
            raise ValueError(f'Unexpected game identity or status: {index}')
        records.append({'index': index, 'seed': record['seed'],
                        'record_sha256': record['record_sha256'],
                        'commands': len(record['commands'])})
        event_types.update(event['type'] for event in record['events'])
        resolved_actions = 0
        for event in record['events']:
            if event['type'] == 'PENDING_CANCELLED':
                if resolved_actions >= len(record['commands']):
                    raise ValueError(f'Cancellation after final action: {index}')
                command = record['commands'][resolved_actions]
                effect = event['effect']
                cancellations.append({'index': index, 'seed': record['seed'],
                                      'record_sha256': record['record_sha256'],
                                      'action_index': resolved_actions,
                                      'judge_receipt_sha256': command['judge']['receipt_sha256'],
                                      'effect_id': effect['effect_id'],
                                      'source_key': effect['source'],
                                      'pending_id': effect['id'],
                                      'reason': event['reason'], 'turn': event['turn']})
            if event['type'] in ('CONTROL_RESOLVED', 'MECHANIC_RESOLVED'):
                resolved_actions += 1
        if resolved_actions != len(record['commands']):
            raise ValueError(f'Action/event count mismatch: {index}')
        for action_index, command in enumerate(record['commands']):
            if command['judge'].get('accepted') is not True:
                raise ValueError(f'Unaccepted action: {index}:{action_index}')
            commands[command['command']] += 1
            ref = {'index': index, 'seed': record['seed'],
                   'record_sha256': record['record_sha256'], 'action_index': action_index,
                   'judge_receipt_sha256': command['judge']['receipt_sha256']}
            for source in command['judge'].get('sources', []):
                sha = source.get('sha256')
                url = urlparse(source.get('url', ''))
                if (sha not in cache or url.scheme != 'https'
                        or not (url.hostname == 'digimoncard.com'
                                or (url.hostname or '').endswith('.digimoncard.com'))):
                    missing_sources[(sha, source.get('url'))] += 1
                    continue
                item = source_refs[sha]
                item['count'] += 1
                item['roles'][source.get('role', 'UNSPECIFIED')] += 1
                item['urls'].add(source['url'])
                item['locators'].add(source.get('locator', ''))
            binding = command['judge'].get('binding')
            if binding:
                for source in binding.get('evidence', []):
                    url = urlparse(source.get('url', ''))
                    if (source.get('sha256') not in cache or url.scheme != 'https'
                            or not (url.hostname == 'digimoncard.com'
                                    or (url.hostname or '').endswith('.digimoncard.com'))):
                        missing_sources[(source.get('sha256'), source.get('url'))] += 1
            pending = command.get('selected_pending')
            if pending:
                effect_counts[pending['effect_id']] += 1
                effects.append({**ref, 'effect_id': pending['effect_id'],
                                'source_card': pending['source'].split(':', 1)[1].split('#', 1)[0],
                                'source_key': pending['source'], 'field': pending['field'],
                                'trigger': pending['trigger'], 'choice': command['args']['choice'],
                                'binding_status': (binding or {}).get('status'),
                                'result_processing': command['result'].get('processing')})
            for decision_index, decision in enumerate(command['decisions']):
                decision_type = decision.get('decision', {}).get('kind', 'UNSPECIFIED')
                decision_counts[decision_type] += 1
                decisions.append({**ref, 'decision_index': decision_index,
                                  'decision_type': decision_type,
                                  'effect_id': (pending or {}).get('effect_id'),
                                  'seat': decision['learning']['seat'],
                                  'candidate_count': len(decision['candidates']),
                                  'candidates': decision['candidates'],
                                  'chosen': decision['chosen'],
                                  'learning_eligible': decision.get('learning_eligible')})
    audit = {'schema': 'ulforce-rules-trace-index-v1', 'status': 'UNREVIEWED',
             'campaign': str(CAMPAIGN.relative_to(ROOT)), 'records': records,
             'command_counts': dict(sorted(commands.items())),
             'event_types': dict(sorted(event_types.items())),
             'effect_counts': dict(sorted(effect_counts.items())),
             'decision_counts': dict(sorted(decision_counts.items())),
             'source_audit': {'matched_official_hashes': len(source_refs),
                              'unmatched_citations': [
                                  {'sha256': sha, 'url': url, 'count': count}
                                  for (sha, url), count in sorted(missing_sources.items())],
                              'sources': [
                                  {'sha256': sha, 'file': cache[sha], 'count': item['count'],
                                   'roles': dict(sorted(item['roles'].items())),
                                   'urls': sorted(item['urls']),
                                   'locators': sorted(item['locators'])}
                                  for sha, item in sorted(source_refs.items())]},
             'counts': {'games': len(records), 'commands': sum(commands.values()),
                        'effects': len(effects), 'decisions': len(decisions),
                        'cancellations': len(cancellations)},
             'coverage_note': 'Command decisions are not BOT_DECISION/JUDGE_PATH events in the older loaded-pair coverage schema. No legal-branch or match-certification verdict is asserted.'}
    if missing_sources:
        raise ValueError('Official source bytes missing or URL not official')
    choice_summary = defaultdict(lambda: {'total': 0, 'multiple_candidates': 0,
                                          'single_candidate': 0, 'empty_candidates': 0,
                                          'learning_eligible': 0})
    for decision in decisions:
        item = choice_summary[decision['decision_type']]
        item['total'] += 1
        count = decision['candidate_count']
        item['multiple_candidates' if count > 1 else
             'single_candidate' if count == 1 else 'empty_candidates'] += 1
        item['learning_eligible'] += decision['learning_eligible'] is True
    audit['choice_summary'] = dict(sorted(choice_summary.items()))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'trace-index.json').write_bytes(json.dumps(audit, sort_keys=True, indent=2).encode() + b'\n')
    (OUT / 'choice-references.json.gz').write_bytes(gzip.compress(
        serial({'effects': effects, 'decisions': decisions,
                'cancellations': cancellations}) + b'\n', mtime=0))
    print(json.dumps({'counts': audit['counts'],
                      'effect_ids': len(effect_counts),
                      'source_hashes': len(source_refs),
                      'unmatched_citations': len(missing_sources)}, sort_keys=True))


if __name__ == '__main__':
    main()
