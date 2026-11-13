"""The actual checked EX13-069 Security play and its derived effects."""
import copy,gzip,json,unittest
from attack_flow import declare_attack,choose_counter,choose_blocker,confirm_attack,end_attack
from context_runtime import ContextRuntime,RuntimeHalt
from effect_scheduler import pending_options,resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT,stage

class SecurityTamerTests(unittest.TestCase):
 def runtime(self,seed=640,first='B'):
  c=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
  return ContextRuntime(c,seed,first,build_selected_registry(c,ROOT),allow_experimental=True)
 def actual(self):
  d=json.loads(gzip.decompress((ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-04/game-0000-segment.json.gz').read_bytes()))
  r=self.runtime(d['seed'],d['first'])
  for c in d['commands'][:-1]:_apply(r,c['command'],c['seat'],c['args'],ROOT)
  self.assertEqual(r.snapshot()['state'],d['halts'][-1]['before']['state'])
  self.assertEqual(r.snapshot()['rng_state'],d['halts'][-1]['before']['rng_state']);return r
 def fixture(self,number='EX13-069'):
  r=self.runtime();r.state.phase='MAIN';r.state.turn=4;r.state.memory=3
  attacker=stage(r,'B',['EX1-013']);r.state.battle['B'][attacker].played_turn=2
  r.state.battle['B'][attacker].ready_since_turn=3;stage(r,'A',['EX13-022'])
  card=next(c for c in r.state.zones['A']['deck'] if c.card_number==number)
  r.state.zones['A']['deck'].remove(card);r.state.zones['A']['security'].append(card)
  declare_attack(r,'B',attacker,'PLAYER',ROOT);choose_counter(r,'A',None,ROOT);choose_blocker(r,'A',None,ROOT)
  return r,card.key
 def test_actual_security_play_preserves_card_and_waits_for_defender_observer(self):
  from tamer_play_effects import OBSERVER_EFFECT,tamer_play_choices
  r=self.actual();before=r.snapshot();card='A:EX13-069#1';result=confirm_attack(r,'B',ROOT)
  self.assertEqual((result['checked_card'],result['security_effect'],result['attacker_deleted']),(card,'EX13-069.security_play',False))
  self.assertEqual((r.state.attack['checked'],r.state.attack['window']),(card,'END'))
  self.assertEqual([c.key for c in r.state.zones['A']['security']],['A:EX13-069#2','A:P-138#1'])
  self.assertEqual([c.key for c in r.state.zones['A']['trash']],['A:P-138#4','A:EX13-022#4'])
  self.assertEqual([c.key for c in r.state.zones['A']['hand']],before['state']['zones']['A']['hand'])
  stack=r.state.battle['A'][card];self.assertEqual([c.key for c in stack.cards],[card]);self.assertFalse(stack.suspended)
  self.assertEqual((stack.played_turn,stack.ready_since_turn),(6,7));self.assertEqual((r.state.memory,r.state.active),(3,'B'))
  self.assertEqual(r.snapshot()['rng_state'],before['rng_state'])
  p=pending_options(r,'A');self.assertEqual([(x['effect_id'],x['source']) for x in p],[(OBSERVER_EFFECT,'A:EX13-022#1')])
  self.assertEqual(pending_options(r,'B'),[])
  self.assertEqual(tamer_play_choices(r,'A','A:EX13-022#1',OBSERVER_EFFECT),
   ['B:BT11-112#3','B:BT22-023#1','B:EX13-022#1','B:EX13-022#3','B:EX13-069#3','B:EX13-069#4'])
  blocked=copy.deepcopy(r);snapshot=blocked.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'PENDING_EFFECTS_REQUIRE_RESOLUTION'):end_attack(blocked,'B',ROOT)
  self.assertEqual(blocked.snapshot(),snapshot)
  resolve_pending(r,'A',p[0]['id'],'B:EX13-022#3')
  grant=next(g for g in r.state.battle['B']['B:EX13-022#3'].statuses['effect_grants'] if g['effect']=={'restrictions':['cannot_suspend']})
  self.assertEqual(grant['expires'],{'turn':6,'controller':'B','boundary':'turn_end'})
  end_attack(r,'B',ROOT);self.assertIsNone(r.state.attack);r.verify()
 def test_unbound_security_play_is_rejected_without_moving_card(self):
  import main_actions
  self.assertTrue(hasattr(main_actions,'play_tamer_from_security'),'Bound Security play primitive missing')
  r,k=self.fixture();before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'SECURITY_TAMER_WINDOW_REQUIRED'):main_actions.play_tamer_from_security(r,'A',k,ROOT)
  self.assertEqual(r.snapshot(),before)
 def test_bt11_112_memory_cost_wording_plays_from_security(self):
  r,k=self.fixture('BT11-112');before=r.snapshot();result=confirm_attack(r,'B',ROOT)
  self.assertEqual(result['security_effect'],'BT11-112.security_play')
  self.assertEqual(result['checked_card'],k)
  self.assertIn(k,r.state.battle['A'])
  self.assertEqual(r.state.memory,before['state']['memory'])
  self.assertEqual(r.state.attack['window'],'END')
  self.assertEqual(len(r.state.zones['A']['security']),len(before['state']['zones']['A']['security'])-1)
  r.verify()
 def test_recorded_bt11_112_security_play(self):
  with gzip.open(ROOT/'ARTIFACTS/board-text-60-2026-11-11/game-0003/segment-0000.json.gz','rt') as handle:
   record=json.load(handle)
  context=load_context_file(ROOT/record['context_file'])
  r=ContextRuntime(context,record['seed'],record['first'],build_selected_registry(context,ROOT),allow_experimental=True)
  for command in record['commands'][:-1]:_apply(r,command['command'],command['seat'],command['args'],ROOT)
  self.assertEqual(r.snapshot()['state'],record['commands'][-1]['before']['state'])
  result=confirm_attack(r,'B',ROOT)
  self.assertEqual(result['checked_card'],'A:BT11-112#3')
  self.assertIn('A:BT11-112#3',r.state.battle['A'])
  self.assertEqual(r.state.attack['window'],'END')
  r.verify()
 def test_same_printed_security_template_plays_bt22_rina_and_queues_on_play_with_observer(self):
  from on_play_effects import ON_PLAY_SPECS
  from tamer_play_effects import OBSERVER_EFFECT
  r,k=self.fixture('BT22-085');result=confirm_attack(r,'B',ROOT)
  self.assertEqual(result['security_effect'],'BT22-085.security_play')
  self.assertIn(k,r.state.battle['A']);self.assertNotIn(k,[c.key for c in r.state.zones['A']['trash']])
  self.assertEqual({p['effect_id'] for p in pending_options(r,'A')},
                   {ON_PLAY_SPECS['BT22-085'][0],OBSERVER_EFFECT})
  self.assertEqual({p['depth'] for p in pending_options(r,'A')},{1})
  self.assertEqual(pending_options(r,'B'),[]);r.verify()
 def test_binding_required_before_checked_card_moves(self):
  from context_runtime import MechanicRegistry
  from match_context import canonical
  r,k=self.fixture();r.registry=MechanicRegistry(tuple(b for b in r.registry.bindings if b.field!='security_text'))
  r._pack_manifest=canonical(r.registry.manifest());before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'UNSUPPORTED_MECHANIC.*EX13-069.security_play'):confirm_attack(r,'B',ROOT)
  self.assertEqual(r.snapshot(),before);self.assertEqual(r.state.zones['A']['security'][-1].key,k)
 def test_security_removal_preflight_can_halt_before_any_card_moves(self):
  from unittest.mock import patch
  r,k=self.fixture();before=r.snapshot()
  with patch('battlefield_scope.assert_combat_consequences_scope',
             side_effect=RuntimeHalt('SECURITY_OBSERVER_UNIMPLEMENTED: TEST_ONLY_BOUNDARY')):
   with self.assertRaisesRegex(RuntimeHalt,'SECURITY_OBSERVER_UNIMPLEMENTED'):
    confirm_attack(r,'B',ROOT)
  self.assertEqual(r.snapshot(),before);self.assertEqual(r.state.zones['A']['security'][-1].key,k)

if __name__=='__main__':unittest.main()
