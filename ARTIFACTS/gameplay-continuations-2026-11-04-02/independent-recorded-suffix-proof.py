"""Replay stored commands only; inspect the actual named-bot suffix's rules.

No policy choices, future actions, cohorts, strategy ratings or match credit.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'SOURCE'))
from context_runtime import ContextRuntime
import imported_attempts as diagnostic
from match_context import canonical, digest
from matchup_readiness import load_context_file
import named_player_bots
from selected_mechanics import build_selected_registry

started = time.monotonic()
record_path = OUT / 'game-0000-segment.json.gz'
previous_path = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-04-01/game-0000-segment.json.gz'
original_bytes, previous_bytes = record_path.read_bytes(), previous_path.read_bytes()
record = json.loads(gzip.decompress(original_bytes))
previous = json.loads(gzip.decompress(previous_bytes))
assert len(record['commands']) == 164 and len(previous['commands']) == 152
assert record['commands'][:152] == previous['commands']
assert record['seed'] == previous['seed'] == 12017913134550805276
assert record['first'] == previous['first'] == 'A'
assert record['status'] == 'PAUSED_AFTER_NAMED_BOT_SEGMENT'
assert record['continuation_provenance']['previous_record_sha256'] == digest(previous)
assert record['continuation_provenance']['previous_record'] == previous
source_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted((ROOT / 'SOURCE').glob('*.py'))}
assert source_hashes == json.loads((OUT / 'source-manifest.json').read_text())['files']
context = load_context_file(ROOT / record['replay_provenance']['context_file'])
runtime = ContextRuntime(context, record['seed'], record['first'],
                         build_selected_registry(context, ROOT), allow_experimental=True)
assert runtime.snapshot() == record['initial']
boundary = None
suffix_snapshots = {}
with patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('No reference policy in proof')), \
        patch.object(named_player_bots, 'NamedPlayerBot', side_effect=AssertionError('No named policy in proof')):
    for index, command in enumerate(record['commands']):
        assert command['status'] == 'EXPERIMENTAL_RESOLVED'
        assert canonical(runtime.public_view(command['seat'])) == canonical(command['public_view']), index
        before = runtime.snapshot()
        result = diagnostic._apply(runtime, command['command'], command['seat'],
                                   copy.deepcopy(command['args']), ROOT)
        assert canonical(result) == canonical(command['result']), index
        runtime.verify()
        if index == 151:
            boundary = runtime.snapshot()
            assert boundary == previous['final']
        if index >= 152:
            suffix_snapshots[index] = (before, runtime.snapshot())

assert runtime.snapshot() == record['final']
assert runtime.events == record['events']
assert runtime.snapshot()['rng_state'] == previous['final']['rng_state']
final = runtime.snapshot()['state']
assert (final['active'], final['turn'], final['memory'], final['phase']) == ('A', 11, 2, 'MAIN')
assert not final['terminal'] and final['winner'] is None

# The selected end effect only unsuspends a blue Tamer, not a Digimon.
before, after = suffix_snapshots[153]
assert before['state']['battle']['B']['B:BT11-112#2']['suspended'] is True
assert after['state']['battle']['B']['B:BT11-112#2']['suspended'] is False
assert before['state']['battle']['B']['B:BT11-032#1'] == after['state']['battle']['B']['B:BT11-032#1']
assert after['state']['pending'] == []
assert (after['state']['active'], after['state']['turn'], after['state']['memory']) == ('B', 10, -1)
assert suffix_snapshots[154][1]['state']['active'] == 'A'
assert suffix_snapshots[154][1]['state']['turn'] == 11
assert suffix_snapshots[154][1]['state']['memory'] == 1
assert len(suffix_snapshots[157][1]['state']['zones']['A']['hand']) == len(
    suffix_snapshots[157][0]['state']['zones']['A']['hand']) + 1
assert suffix_snapshots[158][1]['state']['breeding']['A'] == ['A:EX13-002#3']
assert record['commands'][159]['result'] == {'condition_met': True, 'memory_before': 1, 'memory_after': 2}

# Both Rina payments concern A's attacking Ulforce and do not digivolve it.
for index, source, pending_id in ((161, 'A:BT11-112#2', 'effect-63'),
                                  (163, 'A:BT11-112#3', 'effect-64')):
    before, after = suffix_snapshots[index]
    assert before['state']['battle']['A'][source]['suspended'] is False
    assert after['state']['battle']['A'][source]['suspended'] is True
    assert before['state']['battle']['A']['A:BT11-032#1'] == after['state']['battle']['A']['A:BT11-032#1']
    assert before['state']['zones'] == after['state']['zones']
    assert before['state']['memory'] == after['state']['memory'] == 2
    queued = next(p for p in after['state']['pending'] if p['id'] == pending_id)
    assert queued['depth'] == 1 and queued['effect_id'] == 'BT11-032.play_blue_tamer'
    assert queued['source'] == 'A:BT11-032#1'
assert record['commands'][162]['args'] == {'pending_id': 'effect-63', 'choice': None}
assert record['commands'][162]['decisions'][-1]['candidates'] == [None]
assert all(context.card('A', key.split(':')[1].split('#')[0]).kind != 'Tamer'
           for key in suffix_snapshots[162][0]['state']['zones']['A']['hand'])
assert {p['id'] for p in final['pending']} == {'effect-60', 'effect-64'}
assert final['attack']['attacker'] == 'A:BT11-032#1'
assert final['attack']['target'] == 'PLAYER'
assert final['attack']['window'] == 'COUNTER'
assert not final['attack']['counter_used'] and not final['attack']['block_used']
assert final['attack']['checked'] is None
assert len(final['zones']['A']['security']) == 1 and len(final['zones']['B']['security']) == 5

physical = []
for seat in ('A', 'B'):
    physical.extend(c.key for zone in runtime.state.zones[seat].values() for c in zone)
    physical.extend(c.key for c in runtime.state.breeding[seat])
    physical.extend(c.key for stack in runtime.state.battle[seat].values() for c in stack.cards)
assert len(physical) == len(set(physical)) == 108
assert record_path.read_bytes() == original_bytes and previous_path.read_bytes() == previous_bytes
assert source_hashes == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted((ROOT / 'SOURCE').glob('*.py'))}

sources = []
for number in ('BT22-023', 'BT11-112', 'BT11-032', 'EX13-069', 'EX13-022', 'EX13-002'):
    definition = next(card for card in context.cards if card.number == number)
    source = definition.to_dict()['official_source']
    assert hashlib.sha256((ROOT / source['file']).read_bytes()).hexdigest() == source['sha256']
    sources.append({'card': number, **source})
rule_file = 'RULES/matchups/123129-vs-124303/sources/general_rule.pdf'
rule_sha = hashlib.sha256((ROOT / rule_file).read_bytes()).hexdigest()
assert rule_sha == 'a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271'
sources.append({'file': rule_file, 'sha256': rule_sha,
                'url': 'https://world.digimoncard.com/rule/pdf/general_rule.pdf?20260918',
                'locator': 'CR4.3: 6-1-3; 6-2; 6-3-1; 6-4-1; 6-6-2/3; 11-1-4; 11-2-1/2; 15-7-5; 15-8-3; 15-15-7-1'})
qa = json.loads((ROOT / 'RULES/matchups/123129-vs-124303/CARD_QA.json').read_text())
rules_checks = [
    {'commands': [152, 153, 154], 'result': 'SUPPORTED',
     'finding': 'Aero EndYourTurn may ready B blue Rina Tamer; Digimon-only unsuspend reactions do not trigger. Finish remaining end processing before turn A begins at memory1.',
     'authority': ['BT22-023 printed End of Your Turn', 'BT11-112 printed type/color', 'CR6-6-2/3']},
    {'commands': [155, 156, 157, 158, 159], 'result': 'SUPPORTED',
     'finding': 'No A cards require start-turn unsuspending; ordinary draw adds one card, hatch empty breeding area, and EX13Rina gains1 at Main start because A has UlforceVeedramon.',
     'authority': ['CR6-2', 'CR6-3-1', 'CR6-4-1', 'EX13-069 printed Start of Your Main Phase']},
    {'commands': [160, 161, 162, 163], 'result': 'SUPPORTED',
     'finding': 'A attacks Player with existing ready Ulforce. Its suspension triggers inherited Aero and both A BT11Rinas together. Each may suspend to activate one current WhenDigivolving effect; first free-Tamer processing finishes before the next Rina. None is the sole free-Tamer choice because hand has no Tamer.',
     'authority': ['CR11-1-4', 'CR11-2-1/2', 'CR15-7-5', 'CR15-8-3', 'CR15-15-7-1', 'BT11-112 Q2142/Q2143/Q7199/Q7200', 'BT11-032 printed When Digivolving']},
    {'commands': [163], 'result': 'PAUSED_WITH_PENDING_PROCESSING',
     'finding': 'effect64 must resolve before older inherited effect60. Stored COUNTER marker does not authorize defender action while pending reactions remain. Attack is unconfirmed and security is unchanged.',
     'authority': ['CR6-1-3', 'CR11-1-4', 'CR15-8-3', 'CR15-15-7-1']},
]
output = {
    'schema': 'independent-recorded-named-suffix-proof-v1', 'status': 'PASS',
    'record_sha256': digest(record), 'previous_record_sha256': digest(previous),
    'seed': record['seed'], 'execution_id': runtime.execution_id,
    'recorded_commands_replayed_without_policies': 164, 'new_suffix_commands': 12,
    'original152_prefix_unchanged': True, 'full_boundary_state_and_RNG_exact': True,
    'all_public_views_and_results_exact': True, 'full_final_state_and_RNG_exact': True,
    'all_runtime_events_exact': True, 'suffix_RNG_unchanged': True,
    'source_bytes_stable': True, 'source_file_count': len(source_hashes),
    'original_record_files_unchanged': True, 'unique_physical_cards': 108,
    'final_state_sha256': digest(final),
    'final_boundary': {'active': 'A', 'turn': 11, 'phase': 'MAIN', 'memory': 2,
                       'pending': ['effect-60', 'effect-64'], 'attack_confirmed': False},
    'policy_invocations_in_this_proof': 0, 'new_actual_gameplay_commands_in_this_proof': 0,
    'rules_review_status': 'NO_ILLEGALITY_FOUND_IN_RECORDED_SUFFIX',
    'rules_checks': rules_checks, 'official_sources': sources,
    'BT11_112_official_QA': [item for item in qa['BT11-112']
                            if item['id'] in ('Q2142', 'Q2143', 'Q7199', 'Q7200')],
    'strategy_ratings': 'NONE', 'whole_game_user_bot_credit': 0,
    'accepted_fact_finding_credit': 0, 'judge_certification_credit': 0,
    'final_evaluation_credit': 0, 'certification': 'NONE_RECORDED_SUFFIX_REVIEW_ONLY',
    'seconds': round(time.monotonic() - started, 3),
}
with Path(__file__).with_suffix('.json').open('x') as handle:
    handle.write(json.dumps(output, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: value for key, value in output.items()
                  if key not in ('official_sources', 'BT11_112_official_QA', 'rules_checks')}, indent=2))
