"""Verify saved actual BT22 Aero return on a private copy; no gameplay credit."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'SOURCE'))
from context_runtime import ContextRuntime,RuntimeHalt
from effect_scheduler import resolve_pending,pending_options
from imported_attempts import _apply
from match_context import digest
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry

started=time.monotonic()
source_paths=sorted((ROOT/'SOURCE').glob('*.py'))
source_sha={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
record_path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-11/game-0000-segment.json.gz'
record_bytes=record_path.read_bytes();record=json.loads(gzip.decompress(record_bytes))
assert len(record['commands'])==152
assert record['commands'][-1]['command']=='RESOLVE_PENDING'
assert record['commands'][-1]['args']=={'choice':'A:BT22-022#1','pending_id':'effect-57'}
context=load_context_file(ROOT/record['replay_provenance']['context_file'])
runtime=ContextRuntime(context,record['seed'],record['first'],build_selected_registry(context,ROOT),allow_experimental=True)
for command in record['commands'][:-1]:
    assert runtime.public_view(command['seat'])==command['public_view']
    assert _apply(runtime,command['command'],command['seat'],command['args'],ROOT)==command['result']
    runtime.verify()
assert runtime.snapshot()['state']==record['final']['state']
assert runtime.snapshot()['rng_state']==record['final']['rng_state']
assert runtime.state.active=='B' and runtime.state.turn==10 and runtime.state.memory==-1
assert runtime.state.phase=='MAIN' and runtime.state.attack is None
options=pending_options(runtime,'B')
assert len(options)==1 and options[0]['id']=='effect-57'
assert options[0]['effect_id']=='BT22-023.when_digivolving_return'
assert options[0]['source']=='B:BT22-023#2'
assert pending_options(runtime,'A')==[]
before=runtime.snapshot();expected=copy.deepcopy(before['state'])
source_before=copy.deepcopy(runtime.state.battle['B']['B:BT22-023#2'])
assert source_before.instance_id=='entity-14'
assert [c.key for c in source_before.cards]==['B:EX13-019#1','B:BT22-023#2']
target=expected['battle']['A'].pop('A:BT22-022#1')
assert target['instance_id']=='entity-17'
assert target['cards']==['A:EX13-002#2','A:EX1-013#2','A:BT22-022#1']
expected['zones']['A']['deck'].insert(0,target['cards'][-1])
expected['zones']['A']['trash'].extend(target['cards'][:-1])
expected['pending']=[]
expected['phase']='END_OF_TURN'
events_before=len(runtime.events)
result=resolve_pending(runtime,'B','effect-57','A:BT22-022#1')
assert result['returned']=='A:BT22-022#1'
assert result['trashed_sources']==['A:EX13-002#2','A:EX1-013#2']
assert result['processing']=='RETURNED_TO_DECK_BOTTOM'
assert runtime.snapshot()['state']==expected
assert runtime.snapshot()['rng_state']==before['rng_state']
assert runtime.state.battle['B']['B:BT22-023#2']==source_before
assert runtime.state.active=='B' and runtime.state.turn==10 and runtime.state.memory==-1
assert runtime.state.phase=='END_OF_TURN' and runtime.state.attack is None
assert runtime.state.pending==[]
assert not runtime.state.terminal and runtime.state.winner is None
assert not any(e['type']=='EFFECT_PENDING' for e in runtime.events[events_before:])
runtime.verify()
physical=[]
for seat in ('A','B'):
    physical.extend(c.key for zone in runtime.state.zones[seat].values() for c in zone)
    physical.extend(c.key for c in runtime.state.breeding[seat])
    physical.extend(c.key for stack in runtime.state.battle[seat].values() for c in stack.cards)
assert len(physical)==len(set(physical))==108
assert record_path.read_bytes()==record_bytes
assert source_sha=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'SOURCE').glob('*.py'))}
output={'schema':'private-actual-return-proof-v1','status':'PASS','record_sha256':digest(record),
        'seed':record['seed'],'execution_id':runtime.execution_id,'source_sha256':source_sha,
        'saved_successful_commands_revalidated':151,'pre_return_state_rng_exact':True,
        'private_return_result':result,'private_after_state_sha256':digest(expected),
        'private_whole_state_change_exact':True,'top_owner_deck_bottom':'A:BT22-022#1',
        'lower_owner_trash':['A:EX13-002#2','A:EX1-013#2'],
        'source_entity14_unchanged':True,'memory_unchanged':-1,'active_unchanged':'B','turn_unchanged':10,
        'phase_after_current_processing':'END_OF_TURN','future_end_effects_resolved':False,
        'RNG_unchanged':True,'new_draws':0,'new_pending_effects':0,
        'unique_physical_cards':len(set(physical)),'source_bytes_stable':True,
        'original_record_bytes_unchanged':True,'private_branch_only':True,
        'new_actual_gameplay_commands':0,'accepted_fact_finding_credit':0,
        'judge_certification_credit':0,'strategy_credit':0,'final_evaluation_credit':0,
        'seconds':round(time.monotonic()-started,3)}
Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in output.items() if k not in ['source_sha256','private_return_result']},indent=2))
