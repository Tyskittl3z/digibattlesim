"""Private copies of the saved encounter; no new actual game record or credit."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'SOURCE'))
from attack_flow import declare_attack, choose_counter, choose_blocker, confirm_attack
from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
import effect_scheduler
from imported_attempts import _apply
from match_context import digest
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from rina_reactivation import rina_reactivation_choices

started = time.monotonic()
source_names = ['SOURCE/attack_flow.py', 'SOURCE/battlefield_scope.py',
                'SOURCE/test_attack_flow.py', 'SOURCE/test_battlefield_scope.py']
source_hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
record_path = ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-09/game-0000-segment.json.gz'
record_bytes = record_path.read_bytes()
record = json.loads(gzip.decompress(record_bytes))
context = load_context_file(ROOT / record['replay_provenance']['context_file'])
runtime = ContextRuntime(context, record['seed'], record['first'],
                         build_selected_registry(context, ROOT), allow_experimental=True)
for saved in record['commands'][:-1]:
    assert runtime.public_view(saved['seat']) == saved['public_view']
    actual = _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
    assert actual == saved['result']
    runtime.verify()
assert runtime.snapshot()['state'] == record['final']['state']
assert runtime.snapshot()['rng_state'] == record['final']['rng_state']
args = record['commands'][-1]['args']
before = runtime.snapshot()
old_attacker = copy.deepcopy(runtime.state.battle['B'][args['attacker']])
base_events = len(runtime.events)
with patch('effect_scheduler.queue_effects', wraps=effect_scheduler.queue_effects) as queue:
    result = declare_attack(runtime, 'B', args['attacker'], args['target'], ROOT)
assert queue.call_count == 1
old_attacker.suspended = True
assert runtime.state.battle['B'][args['attacker']] == old_attacker
assert runtime.state.memory == 5 and runtime.state.phase == 'MAIN'
assert runtime.state.attack['attacker_instance'] == 'entity-5'
assert runtime.state.attack['target'] == 'PLAYER'
assert runtime.state.attack['window'] == 'COUNTER'
assert runtime.snapshot()['state']['zones'] == before['state']['zones']
assert runtime.snapshot()['rng_state'] == before['rng_state']
assert runtime.snapshot()['state']['once_used'] == before['state']['once_used']
pending = pending_options(runtime, 'B')
expected = {('B:EX13-022#1', 'EX13-022.inherited_unsuspend', 'inherited_text', 0),
            ('B:BT11-112#2', 'BT11-112.suspend_reactivation', 'main_text', 0),
            ('B:BT11-112#3', 'BT11-112.suspend_reactivation', 'main_text', 0)}
assert {(p['source'], p['effect_id'], p['field'], p['depth']) for p in pending} == expected
assert pending_options(runtime, 'A') == []
assert result['triggered_effects'] == [p['effect_id'] for p in pending]
assert len([e for e in runtime.events[base_events:] if e['type'] == 'EFFECT_PENDING']) == 3
runtime.verify()

# Every later attack window is unavailable while declaration reactions remain.
window_guards = {}
for name, function, seat, extra in [
        ('COUNTER', choose_counter, 'A', (None,)),
        ('BLOCK', choose_blocker, 'A', (None,)),
        ('CONFIRM', confirm_attack, 'B', ())]:
    branch = copy.deepcopy(runtime)
    snapshot = branch.snapshot()
    try:
        function(branch, seat, *extra, ROOT)
        raise AssertionError('premature attack window accepted')
    except RuntimeHalt as exc:
        assert str(exc) == 'PENDING_EFFECTS_REQUIRE_RESOLUTION'
        window_guards[name] = str(exc)
    assert branch.snapshot() == snapshot

# Explicit decline branches on private copies preserve the normal window order.
# No confirmation/security check is performed in this proof.
declines = copy.deepcopy(runtime)
chosen_order = ['B:BT11-112#3', 'B:EX13-022#1', 'B:BT11-112#2']
for source in chosen_order:
    effect = next(p for p in pending_options(declines, 'B') if p['source'] == source)
    if source.startswith('B:BT11-112'):
        assert rina_reactivation_choices(declines, 'B', source) == [None, 'BT11-032.play_blue_tamer']
        choice = None
    else:
        choice = False
    resolve_pending(declines, 'B', effect['id'], choice)
    declines.verify()
assert declines.state.pending == []
assert declines.state.battle['B'][args['attacker']].suspended
assert not declines.state.battle['B']['B:BT11-112#2'].suspended
assert not declines.state.battle['B']['B:BT11-112#3'].suspended
assert declines.state.attack['window'] == 'COUNTER'
choose_counter(declines, 'A', None, ROOT)
assert declines.state.attack['window'] == 'BLOCK'
choose_blocker(declines, 'A', None, ROOT)
assert declines.state.attack['window'] == 'CONFIRM'
assert len(declines.state.zones['A']['security']) == 2
assert declines.snapshot()['rng_state'] == before['rng_state']
assert declines.snapshot()['state']['zones'] == before['state']['zones']
declines.verify()

# The selected-event implementation must not silently skip the later true
# BT11 unsuspend reaction. The failure is a private negative test, not gameplay.
unsupported = copy.deepcopy(runtime)
aero = next(p for p in pending_options(unsupported, 'B')
            if p['effect_id'] == 'EX13-022.inherited_unsuspend')
unsupported_before = unsupported.snapshot()
try:
    resolve_pending(unsupported, 'B', aero['id'], True)
    raise AssertionError('unsupported BT11 unsuspend was silently accepted')
except RuntimeHalt as exc:
    unsupported_reason = str(exc)
    assert unsupported_reason.startswith('ORIENTATION_DEPENDENT_TRIGGER_UNIMPLEMENTED: BT11-032')
assert unsupported.snapshot() == unsupported_before
assert record_path.read_bytes() == record_bytes
assert source_hashes == {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
output = {
    'schema': 'private-actual-declaration-proof-v1', 'status': 'PASS',
    'record_sha256': digest(record), 'seed': record['seed'],
    'execution_id': runtime.execution_id,
    'source_sha256': source_hashes,
    'saved_successful_commands_revalidated': 139,
    'state_and_rng_match_original_before_halt': True,
    'declaration_queue_calls': queue.call_count,
    'declaration_pending': pending,
    'declaration_preserves_zones_rng_memory_entity': True,
    'opponent_pending_count': 0,
    'pending_window_guards': window_guards,
    'explicit_decline_order': chosen_order,
    'after_declines_window_sequence': ['COUNTER', 'BLOCK', 'CONFIRM'],
    'security_checks_executed': 0,
    'unsupported_true_unsuspend_reason': unsupported_reason,
    'unsupported_true_unsuspend_rolled_back': True,
    'source_bytes_stable_during_execution': True,
    'original_record_bytes_unchanged': True,
    'new_actual_gameplay_commands': 0,
    'private_branch_testing_only': True,
    'accepted_fact_finding_credit': 0, 'judge_certification_credit': 0,
    'strategy_credit': 0, 'final_evaluation_credit': 0,
    'seconds': round(time.monotonic()-started, 3),
}
Path(__file__).with_suffix('.json').write_text(json.dumps(output, indent=2, sort_keys=True)+'\n')
print(json.dumps({k: v for k,v in output.items() if k not in ['declaration_pending', 'source_sha256']}, indent=2))
