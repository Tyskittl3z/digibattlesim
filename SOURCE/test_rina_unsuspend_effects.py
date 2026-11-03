"""Source-bound Rina reactions from Game0's actual end-turn unsuspend."""
import copy,gzip,importlib.util,json,unittest
from context_runtime import ContextRuntime,RuntimeHalt
from effect_scheduler import pending_options,queue_effects,resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT,stage

_ACTUAL=None
class RinaUnsuspendTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('rina_unsuspend_effects'),'Encountered Rina unsuspend handlers missing')
 def runtime(self):
  c=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
  r=ContextRuntime(c,651,'B',build_selected_registry(c,ROOT),allow_experimental=True)
  r.state.turn=6;r.state.phase='END_OF_TURN';r.state.memory=-3;return r
 def actual(self):
  global _ACTUAL
  if _ACTUAL is None:
   d=json.loads(gzip.decompress((ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-05/game-0000-segment.json.gz').read_bytes()))
   c=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
   r=ContextRuntime(c,d['seed'],d['first'],build_selected_registry(c,ROOT),allow_experimental=True)
   for command in d['commands'][:-1]:_apply(r,command['command'],command['seat'],command['args'],ROOT)
   self.assertEqual(r.snapshot()['state'],d['halts'][-1]['before']['state'])
   self.assertEqual(r.snapshot()['rng_state'],d['halts'][-1]['before']['rng_state'])
   _ACTUAL=r
  r=copy.deepcopy(_ACTUAL)
  resolve_pending(r,'B','effect-21','B:EX13-022#3');return r
 def selected(self,r,effect,source=None):
  return next(p for p in pending_options(r,'B') if p['effect_id']==effect and (source is None or p['source']==source))
 def isolated(self):
  from rina_unsuspend_effects import collect_rina_unsuspend_reactions
  r=self.runtime();tamer=stage(r,'B',['EX13-069']);base=stage(r,'B',['EX1-013'])
  deck=r.state.zones['B']['deck'];target=next(c for c in deck if c.card_number=='EX13-019')
  deck.remove(target);r.state.zones['B']['hand'].append(target)
  queue_effects(r,collect_rina_unsuspend_reactions(r,'B',r.state.battle['B'][base],True))
  return r,tamer,base,target.key
 def test_actual_unsuspend_queues_three_own_tamers_and_mandatory_memory_opt(self):
  from rina_unsuspend_effects import BT11_MEMORY_EFFECT,EX13_DRAW_EFFECT,rina_unsuspend_choices
  r=self.actual();self.assertFalse(r.state.battle['B']['B:EX13-022#3'].suspended)
  self.assertEqual((r.state.memory,r.state.phase),(-3,'END_OF_TURN'))
  group=pending_options(r,'B')
  self.assertEqual(sorted((p['effect_id'],p['source']) for p in group),sorted([
   (BT11_MEMORY_EFFECT,'B:BT11-112#3'),(EX13_DRAW_EFFECT,'B:EX13-069#3'),(EX13_DRAW_EFFECT,'B:EX13-069#4')]))
  self.assertEqual({p['depth'] for p in group},{1});self.assertEqual(pending_options(r,'A'),[])
  p=self.selected(r,BT11_MEMORY_EFFECT)
  self.assertEqual(rina_unsuspend_choices(r,'B',p['source'],p['effect_id']),[None])
  resolve_pending(r,'B',p['id'],None);self.assertEqual(r.state.memory,-2)
  self.assertIn(tuple(p['usage']),r.state.once_used);r.verify()
 def test_predraw_choice_has_no_deck_peek_and_decline_has_no_after(self):
  from rina_unsuspend_effects import EX13_DRAW_EFFECT,EX13_EVOLVE_EFFECT,rina_unsuspend_choices
  r=self.actual();p=self.selected(r,EX13_DRAW_EFFECT,'B:EX13-069#3');before=r.snapshot()
  self.assertEqual(rina_unsuspend_choices(r,'B',p['source'],p['effect_id']),[False,True])
  self.assertEqual(r.snapshot(),before)
  result=resolve_pending(r,'B',p['id'],False)
  self.assertFalse(result['suspension_paid']);self.assertEqual(r.state.zones['B']['deck'][-1].key,'B:EX13-023#1')
  self.assertFalse(r.state.battle['B'][p['source']].suspended)
  self.assertFalse(any(x['effect_id']==EX13_EVOLVE_EFFECT for x in r.state.pending))
 def paid(self):
  from rina_unsuspend_effects import EX13_DRAW_EFFECT,EX13_EVOLVE_EFFECT
  r=self.actual();p=self.selected(r,EX13_DRAW_EFFECT,'B:EX13-069#3')
  result=resolve_pending(r,'B',p['id'],True)
  self.assertTrue(result['suspension_paid']);self.assertEqual(result['drawn_card'],'B:EX13-023#1')
  self.assertTrue(r.state.battle['B'][p['source']].suspended)
  continuation=pending_options(r,'B')
  self.assertEqual(len(continuation),1);self.assertEqual(continuation[0]['effect_id'],EX13_EVOLVE_EFFECT)
  self.assertEqual(continuation[0]['depth'],2);return r,continuation[0]
 def test_paid_draw_continuation_precedes_siblings_and_uses_postdraw_hand(self):
  from rina_unsuspend_effects import rina_unsuspend_choices
  r,p=self.paid();choices=rina_unsuspend_choices(r,'B',p['source'],p['effect_id'])
  self.assertIsNone(choices[0]);self.assertTrue(any(x and x['hand_key']=='B:EX13-023#1' for x in choices))
  self.assertTrue(any(x and x['hand_key']=='B:BT11-032#1' for x in choices))
  result=resolve_pending(r,'B',p['id'],None);self.assertIsNone(result['evolution'])
  self.assertEqual(len(pending_options(r,'B')),2);r.verify()
 def test_unknown_real_digivolving_effect_halts_only_when_postdraw_route_selected(self):
  from rina_unsuspend_effects import rina_unsuspend_choices
  r,p=self.paid();choices=rina_unsuspend_choices(r,'B',p['source'],p['effect_id'])
  selected=next(x for x in choices if x and x['source_key']=='B:EX13-022#1' and x['hand_key']=='B:EX13-023#1')
  before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'BATTLE_DIGIVOLVING_EFFECT_UNSUPPORTED: EX13-023'):
   resolve_pending(r,'B',p['id'],selected)
  self.assertEqual(r.snapshot(),before)
 def test_bound_evolution_at_negative_end_memory_uses_only_fixed_reduction_two(self):
  from rina_unsuspend_effects import EX13_DRAW_EFFECT
  r,tamer,base,target=self.isolated();stack=copy.deepcopy(r.state.battle['B'][base])
  resolve_pending(r,'B',self.selected(r,EX13_DRAW_EFFECT)['id'],True)
  p=pending_options(r,'B')[0]
  result=resolve_pending(r,'B',p['id'],{'source_key':base,'hand_key':target,'route_index':0})
  self.assertEqual((result['evolution']['cost'],result['evolution']['cost_reduction']),(0,2))
  self.assertEqual((r.state.memory,r.state.phase),(-3,'END_OF_TURN'))
  evolved=r.state.battle['B'][target]
  self.assertEqual(evolved.instance_id,stack.instance_id);self.assertEqual([c.key for c in evolved.cards],[base,target])
  self.assertTrue(r.state.battle['B'][tamer].suspended);r.verify()
 def test_unpayable_self_suspension_cannot_draw_or_enable_after(self):
  from rina_unsuspend_effects import EX13_DRAW_EFFECT,EX13_EVOLVE_EFFECT,rina_unsuspend_choices
  r,tamer,_,_=self.isolated();r.state.battle['B'][tamer].suspended=True
  p=self.selected(r,EX13_DRAW_EFFECT);before=r.snapshot()
  self.assertEqual(rina_unsuspend_choices(r,'B',tamer,EX13_DRAW_EFFECT),[False])
  result=resolve_pending(r,'B',p['id'],False)
  self.assertFalse(result['suspension_paid']);self.assertEqual(r.snapshot()['state']['zones'],before['state']['zones'])
  self.assertFalse(any(x['effect_id']==EX13_EVOLVE_EFFECT for x in r.state.pending))
 def test_forged_continuation_without_paid_parent_is_rejected_atomically(self):
  from rina_unsuspend_effects import EX13_EVOLVE_EFFECT
  r=self.runtime();tamer=stage(r,'B',['EX13-069']);r.state.battle['B'][tamer].suspended=True
  queue_effects(r,[{'seat':'B','source':tamer,'effect_id':EX13_EVOLVE_EFFECT,'field':'main_text',
   'trigger':{'kind':'RINA_AFTER_DRAW','parent_pending':'fake','suspension_paid':True}}])
  before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'RINA_CONTINUATION_PROOF_REQUIRED'):
   resolve_pending(r,'B',pending_options(r,'B')[0]['id'],None)
  self.assertEqual(r.snapshot(),before)

if __name__=='__main__':unittest.main()
