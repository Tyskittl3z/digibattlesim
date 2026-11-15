"""Encountered Rina reactivation scenarios; none counts as a full game."""
import copy
import gzip
import importlib.util
import json
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime,MechanicRegistry,RuntimeHalt,Stack
from effect_scheduler import pending_options,queue_effects,resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry,ORIENTATION_EFFECT
from test_selected_mechanics import ROOT,stage

_ACTUAL=None
class RinaReactivationTests(unittest.TestCase):
 def runtime(self):
  from rina_reactivation import REACTIVATION_EFFECT,rina_reactivation_bindings
  c=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
  registry=build_selected_registry(c,ROOT)
  bindings=tuple(b for b in registry.bindings if b.effect_id!=REACTIVATION_EFFECT)
  bindings+=rina_reactivation_bindings(c,ROOT,registry.bindings[0].evidence[-1])
  r=ContextRuntime(c,909,'B',MechanicRegistry(bindings),allow_experimental=True)
  r.state.turn=8;r.state.phase='UNSUSPEND';r.state.memory=1
  return r
 def fixture(self,number='EX13-023',used=True):
  from rina_reactivation import collect_rina_suspension_reactions
  r=self.runtime();tamer=stage(r,'B',['BT11-112']);digimon=stage(r,'B',[number],suspended=True)
  if used:r.state.once_used.add((8,'B',digimon,ORIENTATION_EFFECT))
  queue_effects(r,collect_rina_suspension_reactions(r,'B',r.state.battle['B'][digimon],False))
  return r,tamer,digimon
 def actual(self):
  global _ACTUAL
  if _ACTUAL is None:
   d=json.loads(gzip.decompress((ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-08/game-0000-segment.json.gz').read_bytes()))
   c=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
   r=ContextRuntime(c,d['seed'],d['first'],build_selected_registry(c,ROOT),allow_experimental=True)
   for command in d['commands'][:-1]:_apply(r,command['command'],command['seat'],command['args'],ROOT)
   self.assertEqual(r.snapshot()['state'],d['halts'][-1]['before']['state'])
   self.assertEqual(r.snapshot()['rng_state'],d['halts'][-1]['before']['rng_state']);_ACTUAL=r
  r=copy.deepcopy(_ACTUAL);resolve_pending(r,'B','effect-34','B:EX13-023#1');return r
 def reaction(self,r):
  from rina_reactivation import REACTIVATION_EFFECT
  return next(p for p in pending_options(r,'B') if p['effect_id']==REACTIVATION_EFFECT)
 def test_actual_reaction_pays_only_rina_then_queues_only_available_return_deeper(self):
  self.assertIsNotNone(importlib.util.find_spec('rina_reactivation'),'Encountered Rina reactivation missing')
  from rina_reactivation import rina_reactivation_choices
  from ex13_ulforce_effects import RETURN_EFFECT
  r=self.actual();p=self.reaction(r)
  self.assertEqual({x['effect_id'] for x in pending_options(r,'B')},{'BT22-023.inherited_unsuspend',p['effect_id']})
  self.assertEqual(p['depth'],3)
  self.assertEqual(rina_reactivation_choices(r,'B',p['source']),[None,RETURN_EFFECT])
  before=copy.deepcopy(r.state);rng=r.snapshot()['rng_state'];result=resolve_pending(r,'B',p['id'],RETURN_EFFECT)
  self.assertTrue(result['suspension_paid']);self.assertEqual(result['activated_effect'],RETURN_EFFECT)
  self.assertTrue(r.state.battle['B']['B:BT11-112#3'].suspended)
  self.assertTrue(r.state.battle['B']['B:EX13-023#1'].suspended)
  group=pending_options(r,'B');self.assertEqual(len(group),1)
  self.assertEqual((group[0]['effect_id'],group[0]['source'],group[0]['depth']),(RETURN_EFFECT,'B:EX13-023#1',4))
  self.assertTrue(any(x['id']=='effect-35' and x['depth']==2 for x in r.state.pending))
  self.assertEqual(r.state.zones,before.zones);self.assertEqual(r.state.memory,before.memory)
  self.assertEqual(r.state.once_used,before.once_used);self.assertEqual(r.snapshot()['rng_state'],rng)
  resolve_pending(r,'B',group[0]['id'],False)
  self.assertEqual([x['effect_id'] for x in pending_options(r,'B')],['BT22-023.inherited_unsuspend']);r.verify()
 def test_decline_is_explicit_and_no_cost_or_derived_effect(self):
  from rina_reactivation import rina_reactivation_choices
  r,tamer,_=self.fixture();before=copy.deepcopy(r.state)
  self.assertEqual(len(rina_reactivation_choices(r,'B',tamer)),2)
  result=resolve_pending(r,'B',self.reaction(r)['id'],None)
  self.assertFalse(result['suspension_paid']);before.pending=[];self.assertEqual(r.state,before)
 def test_multiple_current_effects_are_explicit_and_used_opt_is_filtered(self):
  from rina_reactivation import rina_reactivation_choices
  from ex13_ulforce_effects import RETURN_EFFECT
  r,tamer,digimon=self.fixture(used=False)
  self.assertEqual(rina_reactivation_choices(r,'B',tamer),[None,ORIENTATION_EFFECT,RETURN_EFFECT])
  r.state.once_used.add((8,'B',digimon,ORIENTATION_EFFECT))
  self.assertEqual(rina_reactivation_choices(r,'B',tamer),[None,RETURN_EFFECT]);before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'RINA_REACTIVATION_CHOICE_INVALID'):
   resolve_pending(r,'B',self.reaction(r)['id'],ORIENTATION_EFFECT)
  self.assertEqual(r.snapshot(),before)
 def test_no_available_effect_can_still_pay_without_activating_one(self):
  from rina_reactivation import PAY_NO_EFFECT,rina_reactivation_choices
  r,tamer,_=self.fixture('EX13-019');self.assertEqual(rina_reactivation_choices(r,'B',tamer),[None,PAY_NO_EFFECT])
  before=copy.deepcopy(r.state.zones);result=resolve_pending(r,'B',self.reaction(r)['id'],PAY_NO_EFFECT)
  self.assertTrue(result['suspension_paid']);self.assertIsNone(result['activated_effect'])
  self.assertTrue(r.state.battle['B'][tamer].suspended);self.assertEqual(r.state.pending,[])
  self.assertEqual(r.state.zones,before);r.verify()
 def test_no_effect_payment_is_not_an_alternative_to_selecting_available_effect(self):
  from rina_reactivation import PAY_NO_EFFECT
  r,_,_=self.fixture();before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'RINA_REACTIVATION_CHOICE_INVALID'):
   resolve_pending(r,'B',self.reaction(r)['id'],PAY_NO_EFFECT)
  self.assertEqual(r.snapshot(),before)
 def test_unpayable_cost_declines_without_parsing_current_unknown_effects(self):
  from rina_reactivation import rina_reactivation_choices
  for prohibition in ('suspended','cannot_suspend'):
   r,tamer,_=self.fixture()
   if prohibition=='suspended':r.state.battle['B'][tamer].suspended=True
   else:r.state.battle['B'][tamer].statuses['cannot_suspend']=True
   with patch('battle_evolution.current_digivolving_effects',side_effect=AssertionError('must not inspect')):
    self.assertEqual(rina_reactivation_choices(r,'B',tamer),[None])
    result=resolve_pending(r,'B',self.reaction(r)['id'],None)
   self.assertFalse(result['suspension_paid'])
 def test_observed_instance_uses_current_top_after_intervening_evolution(self):
  from rina_reactivation import rina_reactivation_choices
  from ex13_ulforce_effects import RETURN_EFFECT
  r,tamer,old=self.fixture('EX13-022',used=False);stack=r.state.battle['B'].pop(old)
  new=next(c for c in r.state.zones['B']['deck'] if c.card_number=='EX13-023')
  r.state.zones['B']['deck'].remove(new);stack.cards.append(new);r.state.battle['B'][new.key]=stack
  self.assertEqual(rina_reactivation_choices(r,'B',tamer),[None,ORIENTATION_EFFECT,RETURN_EFFECT])
  resolve_pending(r,'B',self.reaction(r)['id'],RETURN_EFFECT)
  self.assertEqual(pending_options(r,'B')[0]['source'],new.key);r.verify()
 def test_new_incarnation_of_same_copy_is_not_observed_digimon(self):
  from rina_reactivation import PAY_NO_EFFECT,rina_reactivation_choices
  r,tamer,digimon=self.fixture();old=r.state.battle['B'][digimon];r.state.entity_sequence+=1
  r.state.battle['B'][digimon]=Stack(old.cards,suspended=True,instance_id='entity-'+str(r.state.entity_sequence))
  self.assertEqual(rina_reactivation_choices(r,'B',tamer),[None,PAY_NO_EFFECT])
 def test_invalid_trigger_and_unbound_direct_dispatch_roll_back(self):
  from rina_reactivation import REACTIVATION_EFFECT
  for forged in (False,True):
   r,tamer,_=self.fixture()
   if forged:r.state.pending[0]['trigger']['suspended_before']=True
   else:r.state.pending=[]
   before=r.snapshot()
   with self.assertRaisesRegex(RuntimeHalt,'RINA_REACTIVATION_WINDOW_REQUIRED|RINA_REACTIVATION_TRIGGER_INVALID'):
    if forged:resolve_pending(r,'B',r.state.pending[0]['id'],None)
    else:r.dispatch(REACTIVATION_EFFECT,'B',tamer,None)
   self.assertEqual(r.snapshot(),before)
 def test_collector_only_own_veedramon_digimon_actual_suspension(self):
  from rina_reactivation import collect_rina_suspension_reactions
  r=self.runtime();stage(r,'B',['BT11-112']);stage(r,'A',['BT11-112'])
  digimon=stage(r,'B',['EX13-023'],suspended=True)
  self.assertEqual(len(collect_rina_suspension_reactions(r,'B',r.state.battle['B'][digimon],False)),1)
  self.assertEqual(collect_rina_suspension_reactions(r,'B',r.state.battle['B'][digimon],True),[])
  tamer=next(s for s in r.state.battle['B'].values() if s.cards[-1].card_number=='BT11-112');tamer.suspended=True
  self.assertEqual(collect_rina_suspension_reactions(r,'B',tamer,False),[])
  veemon=stage(r,'B',['EX1-013'],suspended=True)
  self.assertEqual(collect_rina_suspension_reactions(r,'B',r.state.battle['B'][veemon],False),[])

if __name__=='__main__':unittest.main()
