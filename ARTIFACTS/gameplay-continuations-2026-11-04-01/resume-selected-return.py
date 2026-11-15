"""Save only Game0000's already-selected return, then verify exact replay.

Run this script in a new copy without its generated checkpoint files. It never
overwrites evidence or constructs a player policy. No match/strategy credit.
"""
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'SOURCE'))

import imported_attempts as diagnostic
from match_context import canonical, digest
from recorded_action_checkpoint import continue_selected_action, replay_selected_action


def write_json(name, value):
    with (OUT / name).open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


previous_path = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-03-11/game-0000-segment.json.gz'
destination = OUT / 'game-0000-segment.json.gz'
if destination.exists():
    raise SystemExit('Refusing to overwrite the saved checkpoint')
original_bytes = previous_path.read_bytes()
previous = json.loads(gzip.decompress(original_bytes))
assert digest(previous) == '8d596ab2b7b665453a4e87b9fd2775cb7ce27080603be2349a4f7602b53fec9a'
assert previous['commands'][-1]['command'] == 'RESOLVE_PENDING'
assert previous['commands'][-1]['seat'] == 'B'
assert previous['commands'][-1]['args'] == {'pending_id': 'effect-57', 'choice': 'A:BT22-022#1'}
source_paths = sorted((ROOT / 'SOURCE').glob('*.py'))
source_bytes = {str(path.relative_to(ROOT)): path.read_bytes() for path in source_paths}
source_hashes = {name: hashlib.sha256(body).hexdigest() for name, body in source_bytes.items()}

with patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('No policy may be constructed')), \
        patch.object(diagnostic, 'main_candidates', side_effect=AssertionError('No new action selection')), \
        patch.object(diagnostic, 'pending_choice', side_effect=AssertionError('No new pending selection')):
    record = continue_selected_action(previous, ROOT)
    # Preserve the actual attempted continuation before verification can fail.
    with destination.open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(canonical(record) + b'\n')

    checkpoint = {
        'schema': 'game0000-selected-return-checkpoint-v1',
        'date': '2026-11-04', 'seed': record['seed'], 'first': record['first'],
        'status': record['status'], 'turn': record['final']['state']['turn'],
        'active': record['final']['state']['active'], 'memory': record['final']['state']['memory'],
        'phase': record['final']['state']['phase'], 'commands': len(record['commands']),
        'successful_commands': sum(c['status'] == 'EXPERIMENTAL_RESOLVED' for c in record['commands']),
        'newly_resolved_commands': 1, 'new_policy_decisions': 0, 'policy_invocations': 0,
        'historical_policies': {seat: {'policy': record['pilots'][seat]['policy'],
                                     'pilot_id': record['pilot_id'][seat]} for seat in ('A', 'B')},
        'historical_policies_are_user_bots': False,
        'user_bot_evidence_credit': 0, 'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
        'ratings_assigned': False, 'scoring_criteria': 'NOT_DEFINED_OR_BOUND_FOR_THIS_GAME',
        'winner': record['winner'], 'record_sha256': digest(record),
        'previous_record': str(previous_path.relative_to(ROOT)),
        'previous_record_sha256': digest(previous),
        'execution_id': record['replay_provenance']['execution_id'],
        'stop_reason': 'USER_REQUESTED_PAUSE_AFTER_SAVED_ACTION_BEFORE_NEW_PLAYER_DECISION',
    }
    write_json('checkpoint.json', checkpoint)
    print(json.dumps(checkpoint), flush=True)

    replay = replay_selected_action(record, ROOT)
    write_json('replay.json', replay)
    assert replay['exact_match'], 'Saved checkpoint retained; exact replay failed'

expected = copy.deepcopy(previous['final']['state'])
target = expected['battle']['A'].pop('A:BT22-022#1')
assert target['cards'] == ['A:EX13-002#2', 'A:EX1-013#2', 'A:BT22-022#1']
expected['zones']['A']['deck'].insert(0, target['cards'][-1])
expected['zones']['A']['trash'].extend(target['cards'][:-1])
expected['pending'] = []
expected['phase'] = 'END_OF_TURN'
assert record['final']['state'] == expected
assert record['final']['rng_state'] == previous['final']['rng_state']
assert record['seed'] == 12017913134550805276
assert record['commands'][:-1] == previous['commands'][:-1]
assert record['policy_execution']['new_policy_decisions'] == 0
assert previous_path.read_bytes() == original_bytes
assert source_hashes == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted((ROOT / 'SOURCE').glob('*.py'))}
write_json('state-delta-proof.json', {
    'status': 'PASS', 'exact_entire_state_delta': True, 'exact_replay': True,
    'saved_prefix_unchanged': True, 'saved_successful_commands_revalidated': 151,
    'only_saved_return_resolved': True, 'original_seed_preserved': True,
    'RNG_unchanged_by_return': True, 'previous_record_bytes_unchanged': True,
    'source_bytes_stable': True, 'top_to_owner_deck_bottom': 'A:BT22-022#1',
    'lower_to_owner_trash': ['A:EX13-002#2', 'A:EX1-013#2'],
    'after': {'active': 'B', 'turn': 10, 'memory': -1, 'phase': 'END_OF_TURN', 'pending': []},
    'new_policy_decisions': 0, 'policy_invocations': 0, 'ratings_assigned': False,
    'user_bot_evidence_credit': 0, 'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
})

manifest = {'schema': 'source-checkpoint-v1', 'execution_id': checkpoint['execution_id'],
            'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'files': source_hashes}
write_json('source-manifest.json', manifest)
with (OUT / 'source-checkpoint.tar.gz').open('xb') as handle:
    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w|') as archive:
            for name, body in source_bytes.items():
                info = tarfile.TarInfo(name)
                info.size = len(body)
                info.mtime = 0
                archive.addfile(info, io.BytesIO(body))

lines = ['# Game0000: saved return resolved', '',
         'Original seed: 12017913134550805276. Historical random-reference choices are preserved.',
         'Only the saved return was newly resolved; no player policy was invoked. All match/bot credits: 0.',
         'Paused at B turn10, memory -1, END_OF_TURN. No ratings assigned.', '',
         '| Step | Turn | Player | Command / saved choice | Memory before | Observed result |',
         '|---:|---:|---|---|---:|---|']
for index, command in enumerate(record['commands']):
    view = command.get('public_view', {})
    result = command.get('result', {})
    action = command['command'] + ' ' + json.dumps(command.get('args', {}), sort_keys=True)
    observed = result.get('processing') or result.get('phase') or command['status']
    if index == len(record['commands']) - 1:
        observed += '; BT22-022 to A deck bottom; EX13-002 and EX1-013 to A trash; opens END_OF_TURN'
    lines.append('|' + '|'.join(str(value).replace('|', '/') for value in
                              (index, view.get('turn', ''), command.get('seat', ''),
                               action, view.get('memory', ''), observed)) + '|')
with (OUT / 'game-0000-turns.md').open('x') as handle:
    handle.write('\n'.join(lines) + '\n')
print(json.dumps(replay), flush=True)
