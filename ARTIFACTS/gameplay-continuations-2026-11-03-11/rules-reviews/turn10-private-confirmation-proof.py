"""Verify one actual confirmation on a private copy; never extend saved gameplay."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'SOURCE'))
from attack_flow import confirm_attack
from context_runtime import ContextRuntime, RuntimeHalt
from imported_attempts import _apply
from match_context import digest
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry

started=time.monotonic()
source_names=['SOURCE/attack_flow.py','SOURCE/battlefield_scope.py',
              'SOURCE/test_attack_flow.py','SOURCE/test_battlefield_scope.py']
source_sha={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names}
p=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-10/game-0000-segment.json.gz'
record_bytes=p.read_bytes()
record=json.loads(gzip.decompress(record_bytes))
assert len(record['commands'])==147
assert record['commands'][-1]['command']=='CONFIRM_ATTACK'
context=load_context_file(ROOT/record['replay_provenance']['context_file'])
runtime=ContextRuntime(context,record['seed'],record['first'],
                      build_selected_registry(context,ROOT),allow_experimental=True)
for command in record['commands'][:-1]:
    assert runtime.public_view(command['seat'])==command['public_view']
    assert _apply(runtime,command['command'],command['seat'],command['args'],ROOT)==command['result']
    runtime.verify()
assert runtime.snapshot()['state']==record['final']['state']
assert runtime.snapshot()['rng_state']==record['final']['rng_state']
assert runtime.state.pending==[]
assert runtime.state.attack['window']=='CONFIRM'
assert len(runtime.state.zones['A']['security'])==2
before=runtime.snapshot()
expected=copy.deepcopy(before['state'])
attacker=runtime.state.battle['B']['B:BT11-032#1']
assert attacker.suspended and attacker.instance_id=='entity-5'
assert context.card('B','BT11-032').to_dict()['dp']==12000
assert context.card('A','P-138').to_dict()['dp']==5000
assert context.card('A','P-138').effect_text('security_text')==''
protected_before=copy.deepcopy(runtime.state.battle['B']['B:EX13-023#1'])
assert not protected_before.suspended
assert protected_before.instance_id=='entity-10'
assert expected['zones']['A']['security']==['A:EX13-069#2','A:P-138#1']
checked=expected['zones']['A']['security'].pop()
expected['zones']['A']['trash'].append(checked)
expected['attack']['checked']=checked
expected['attack']['window']='END'
events_before=len(runtime.events)
result=confirm_attack(runtime,'B',ROOT)
assert runtime.snapshot()['state']==expected
assert runtime.snapshot()['rng_state']==before['rng_state']
assert runtime.state.battle['B']['B:EX13-023#1']==protected_before
assert result['checked_card']=='A:P-138#1'
assert result['attacker_deleted'] is False
assert result['security_card_deleted'] is False
assert not runtime.state.terminal and runtime.state.winner is None
assert runtime.state.pending==[]
assert runtime.state.memory==5
assert not any(e['type']=='EFFECT_PENDING' for e in runtime.events[events_before:])
runtime.verify()
physical=[]
for seat in ('A','B'):
    physical.extend(c.key for zone in runtime.state.zones[seat].values() for c in zone)
    physical.extend(c.key for c in runtime.state.breeding[seat])
    physical.extend(c.key for stack in runtime.state.battle[seat].values() for c in stack.cards)
assert len(physical)==len(set(physical))==108
# The resolved confirmation cannot be replayed to check another card.
second_before=runtime.snapshot()
try:
    confirm_attack(runtime,'B',ROOT)
    raise AssertionError('confirmation accepted twice')
except RuntimeHalt as exc:
    second_reason=str(exc)
    assert second_reason=='ATTACK_WINDOW_NOT_OPEN: CONFIRM'
assert runtime.snapshot()==second_before
assert p.read_bytes()==record_bytes
assert source_sha=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names}
output={'schema':'private-actual-confirmation-proof-v1','status':'PASS',
        'record_sha256':digest(record),'seed':record['seed'],'execution_id':runtime.execution_id,
        'source_sha256':source_sha,'saved_successful_commands_revalidated':146,
        'preconfirmation_state_rng_exact':True,'private_confirmation_result':result,
        'private_after_state_sha256':digest(expected),'private_state_change_exact':True,
        'checked_card':'A:P-138#1','A_security_before':2,'A_security_after':1,
        'checked_security_digimon_deleted':False,'attacker_deleted':False,
        'unrelated_protected_stack_unchanged':True,'RNG_unchanged':True,
        'memory_unchanged':5,'new_pending_effects':0,'attack_window':'END','terminal':False,
        'unique_physical_cards':len(set(physical)),'second_confirmation_guard':second_reason,
        'second_confirmation_rolled_back':True,'source_bytes_stable':True,
        'original_record_bytes_unchanged':True,'private_branch_only':True,
        'new_actual_gameplay_commands':0,'accepted_fact_finding_credit':0,
        'judge_certification_credit':0,'strategy_credit':0,'final_evaluation_credit':0,
        'seconds':round(time.monotonic()-started,3)}
Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in output.items() if k not in ['source_sha256','private_confirmation_result']},indent=2))
