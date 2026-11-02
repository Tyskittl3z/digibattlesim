"""The encountered Mental Training use with physical cards and explicit choices."""
import importlib.util
from pathlib import Path
import unittest
from context_runtime import ContextRuntime, MechanicRegistry, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending, source_stack
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
ROOT=Path(__file__).resolve().parents[1]

class EncounteredOptionTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('option_actions'),'Encountered Mental Training use is missing')
 def runtime(self,egg=True):
  from option_actions import option_bindings
  ctx=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
  registry=build_selected_registry(ctx,ROOT);rules=registry.bindings[0].evidence[-1]
  bindings=tuple(b for b in registry.bindings if b.card_number!='P-104')
  r=ContextRuntime(ctx,0,'A',MechanicRegistry(bindings+option_bindings(ctx,ROOT,rules)),allow_experimental=True)
  r.state.phase='MAIN';r.state.turn=1;r.state.memory=0
  deck=r.state.zones['A']['deck'];physical=next(c for c in deck if c.card_number=='P-104')
  deck.remove(physical);r.state.zones['A']['hand'].append(physical)
  if egg:r.state.breeding['A'].append(r.state.zones['A']['eggdeck'].pop())
  return r,physical.key
 def top(self,r,numbers):
  deck=r.state.zones['A']['deck'];cards=[]
  for n in numbers:
   c=next(c for c in deck if c.card_number==n);deck.remove(c);cards.append(c)
  deck.extend(reversed(cards));return [c.key for c in cards]
 def use(self,r,k):
  from option_actions import choose_use_option
  return choose_use_option(r,'A',k,ROOT)
 def resolve(self,r,selected,bottom):
  return resolve_pending(r,'A',pending_options(r,'A')[0]['id'],{'selected':selected,'bottom_order':bottom})
 def test_blue_hatched_egg_alone_pays_then_resolves_before_turn_end(self):
  from option_actions import option_choices
  from turn_flow import finish_turn
  r,k=self.runtime();keys=self.top(r,['BT11-112','LM-028'])
  self.assertEqual(r.state.breeding['A'][-1].card_number,'EX13-002')
  result=self.use(r,k)
  self.assertEqual((result['used_card'],result['cost'],result['memory_after']),(k,2,-2))
  self.assertEqual(r.state.phase,'MAIN');self.assertNotIn(k,r.state.battle['A'])
  self.assertNotIn(k,[c.key for c in r.state.zones['A']['hand']])
  self.assertEqual(r.state.resolving_option['seat'],'A')
  self.assertEqual(r._source('A',k,'main_text').key,k)
  self.assertIs(source_stack(r,'A',k,'main_text'),r.state.resolving_option['stack'])
  self.assertEqual(r.public_view('B')['resolving_option']['stack']['cards'],[k]);r.verify()
  options=option_choices(r,'A',k)
  self.assertEqual(options['revealed'],keys);self.assertEqual(options['selections'],sorted([[keys[0]],[keys[1]]]))
  pending=pending_options(r,'A');self.assertEqual(len(pending),1)
  self.assertEqual(pending[0]['effect_id'],'P-104.main_search')
  result=self.resolve(r,keys[:1],keys[1:])
  self.assertEqual((result['revealed'],result['selected'],result['bottom_order']),(keys,keys[:1],keys[1:]))
  self.assertEqual(r.state.zones['A']['deck'][0].key,keys[1])
  self.assertIn(keys[0],[c.key for c in r.state.zones['A']['hand']])
  self.assertIn(k,r.state.battle['A']);self.assertEqual(r.state.battle['A'][k].played_turn,1)
  self.assertIsNone(r.state.resolving_option);self.assertEqual(r.state.phase,'END_OF_TURN')
  finish_turn(r,'A',ROOT);self.assertEqual((r.state.active,r.state.memory),('B',2))
  self.assertEqual([e['type'] for e in r.events],['EFFECT_PENDING','CONTROL_RESOLVED','MECHANIC_RESOLVED','CONTROL_RESOLVED']);r.verify()
 def test_no_own_color_source_rejects_before_memory_or_card_movement(self):
  for opponent_egg in (False,True):
   r,k=self.runtime(egg=False)
   if opponent_egg:r.state.breeding['B'].append(r.state.zones['B']['eggdeck'].pop())
   before=r.snapshot()
   with self.assertRaisesRegex(RuntimeHalt,'OPTION_COLOR_REQUIREMENTS_NOT_MET'):self.use(r,k)
   self.assertEqual(r.snapshot()['state'],before['state']);self.assertEqual(r.snapshot()['rng_state'],before['rng_state'])
   self.assertEqual(r.events[-1]['reason'],'OPTION_COLOR_REQUIREMENTS_NOT_MET: P-104')
 def test_available_blue_card_cannot_be_declined_or_both_taken(self):
  for selected in ([],[0,1]):
   r,k=self.runtime();keys=self.top(r,['EX1-013','BT11-112']);self.use(r,k);before=r.snapshot()['state']
   chosen=[keys[i] for i in selected]
   with self.assertRaisesRegex(RuntimeHalt,'OPTION_SELECTION_OR_ORDER_INVALID'):
    self.resolve(r,chosen,[x for x in keys if x not in chosen])
   self.assertEqual(r.snapshot()['state'],before);self.assertNotIn(k,r.state.battle['A'])
 def test_bottom_remainder_must_be_exact_and_unrepeated(self):
  for bottom in ([],[0],[1,1]):
   r,k=self.runtime();keys=self.top(r,['EX1-013','BT11-112']);self.use(r,k);before=r.snapshot()['state']
   with self.assertRaisesRegex(RuntimeHalt,'OPTION_SELECTION_OR_ORDER_INVALID'):
    self.resolve(r,keys[:1],[keys[i] for i in bottom])
   self.assertEqual(r.snapshot()['state'],before)
 def test_short_and_empty_deck_resolve_without_losing_source_or_cards(self):
  from option_actions import option_choices
  for remaining in (0,1):
   r,k=self.runtime();deck=r.state.zones['A']['deck'];cut=len(deck)-remaining
   r.state.zones['A']['trash'].extend(deck[:cut]);del deck[:cut]
   expected=[c.key for c in reversed(deck)];self.use(r,k)
   options=option_choices(r,'A',k)
   self.assertEqual(options['revealed'],expected);self.assertEqual(options['selections'],[expected])
   self.resolve(r,expected,[]);self.assertIn(k,r.state.battle['A']);r.verify()
 def test_reveal_requires_current_option_activation_and_never_mutates(self):
  from option_actions import option_choices
  r,k=self.runtime();before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'OPTION_ACTIVATION_WINDOW_REQUIRED'):option_choices(r,'A',k)
  self.assertEqual(r.snapshot(),before);self.use(r,k);before=r.snapshot();options=option_choices(r,'A',k)
  self.assertEqual(r.snapshot(),before)
  chosen=options['selections'][0];self.resolve(r,chosen,[x for x in options['revealed'] if x not in chosen]);before=r.snapshot()
  with self.assertRaisesRegex(RuntimeHalt,'OPTION_ACTIVATION_WINDOW_REQUIRED'):option_choices(r,'A',k)
  self.assertEqual(r.snapshot(),before)
 def test_pending_main_prevents_turn_end_and_another_action(self):
  from turn_flow import finish_turn,pass_turn
  from main_actions import choose_play
  for action in ('finish','pass','play','use'):
   r,k=self.runtime();self.use(r,k);before=r.snapshot()['state']
   with self.assertRaisesRegex(RuntimeHalt,'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
    if action=='finish':finish_turn(r,'A',ROOT)
    elif action=='pass':pass_turn(r,'A',ROOT)
    elif action=='play':choose_play(r,'A',k,ROOT)
    else:self.use(r,k)
   self.assertEqual(r.snapshot()['state'],before)
 def test_wrong_turn_phase_hand_and_terminal_cannot_use(self):
  from option_actions import choose_use_option
  for mutation,reason in (('seat','MAIN_OPTION_WINDOW_NOT_OPEN'),('phase','MAIN_OPTION_WINDOW_NOT_OPEN'),('memory','MAIN_OPTION_WINDOW_NOT_OPEN'),('hand','OPTION_NOT_IN_HAND'),('terminal','ACTION_AFTER_TERMINAL')):
   r,k=self.runtime();seat='A'
   if mutation=='seat':seat='B'
   elif mutation=='phase':r.state.phase='BREEDING'
   elif mutation=='memory':r.state.memory=-1
   elif mutation=='hand':k='A:P-104#999'
   else:r.state.terminal=True
   before=r.snapshot()['state']
   with self.assertRaisesRegex(RuntimeHalt,reason):choose_use_option(r,seat,k,ROOT)
   self.assertEqual(r.snapshot()['state'],before)
 def test_resolving_card_is_conserved_and_cannot_be_duplicated_in_an_area(self):
  r,k=self.runtime();self.use(r,k);r.verify()
  r.state.zones['A']['trash'].append(r.state.resolving_option['stack'].cards[0])
  with self.assertRaisesRegex(RuntimeHalt,'PHYSICAL_CARD_MISMATCH'):r.verify()

if __name__=='__main__':unittest.main()
