"""Read-only synthetic proof of Rina's activated private-record validation."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'SOURCE'))
from context_runtime import RuntimeHalt
from rina_reactivation import REACTIVATION_EFFECT,_source_window
from test_rina_reactivation import RinaReactivationTests
r,tamer,_=RinaReactivationTests().fixture()
p=copy.deepcopy(r.state.pending[0]);r.state.pending=[]
r._activated_effect=(REACTIVATION_EFFECT,'B',tamer,'main_text',p['id'])
r._activated_pending=copy.deepcopy(p)
before=r.snapshot();assert _source_window(r,'B',tamer,resolving=True)==p
assert r.snapshot()==before
rows=[{'probe':'valid_private_selected_record','result':'ACCEPTED_NO_STATE_MUTATION'}]
for label,change in [
 ('missing_private_record',lambda rt:setattr(rt,'_activated_pending',None)),
 ('private_id_mismatch',lambda rt:rt._activated_pending.update(id='wrong-id')),
 ('private_effect_mismatch',lambda rt:rt._activated_pending.update(effect_id='wrong-effect')),
 ('private_source_mismatch',lambda rt:rt._activated_pending.update(source='B:wrong#1')),
 ('private_tamer_incarnation_mismatch',lambda rt:rt._activated_pending.update(instance='different-entity')),
 ('empty_observed_incarnation',lambda rt:rt._activated_pending['trigger'].update(observed_instance='')),
 ('foreign_observed_source',lambda rt:rt._activated_pending['trigger'].update(observed_source='A:EX13-023#1')),
 ('nonmatching_trigger_name',lambda rt:rt._activated_pending['trigger'].update(name_at_trigger='Veemon')),
 ('nonactual_suspension',lambda rt:rt._activated_pending['trigger'].update(suspended_before=True)),
 ('unbound_direct_call',lambda rt:setattr(rt,'_activated_effect',None))]:
 rt=copy.deepcopy(r);change(rt);snapshot=rt.snapshot()
 try:_source_window(rt,'B',tamer,resolving=True)
 except RuntimeHalt as exc:
  assert str(exc) in ('RINA_REACTIVATION_WINDOW_REQUIRED','RINA_REACTIVATION_TRIGGER_INVALID')
  assert rt.snapshot()==snapshot
  rows.append({'probe':label,'result':'REJECTED_NO_STATE_MUTATION','reason':str(exc)})
 else:raise AssertionError(label+' unexpectedly accepted')
proof={'schema':'rina-private-selected-pending-window-proof-v1','date':'2026-11-03','probes':rows,
 'new_actual_gameplay_executed':False,'source_files_edited':[],'full_match_credit':0,
 'limits':'Synthetic direct private-window validation only; source-level guards complement dispatcher tests and actual saved-state tests.'}
out=Path(__file__).with_name('rina-private-pending-proof.json')
out.write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'status':'PASS','accepted_valid':1,'rejected_invalid':10,'source_files_edited':[]}))
