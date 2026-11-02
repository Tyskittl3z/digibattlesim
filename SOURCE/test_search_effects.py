"""Official search scenarios, zero full matches."""
import importlib.util
import unittest
from context_runtime import ContextRuntime, MechanicRegistry, RuntimeHalt
from test_selected_mechanics import selected_context, stage, ROOT
class SearchTests(unittest.TestCase):
 def test_module_available(self):
  self.assertIsNotNone(importlib.util.find_spec('search_effects'),'Exact search handlers missing')
 def prepare(self,number='BT11-023',top=None):
  from search_effects import search_bindings
  from selected_mechanics import build_selected_registry
  ctx=selected_context();rules=build_selected_registry(ctx,ROOT).bindings[0].evidence[-1]
  r=ContextRuntime(ctx,101,'A',MechanicRegistry(search_bindings(ctx,ROOT,rules)),allow_experimental=True)
  s='B' if number=='EX2-008' else 'A';k=stage(r,s,[number]);deck=r.state.zones[s]['deck'];cards=[]
  for n in top or ['BT12-029','BT22-085','EX1-013']:
   c=next(c for c in deck if c.card_number==n);deck.remove(c);cards.append(c)
  deck.extend(reversed(cards));return r,s,k,[c.key for c in cards]
 def resolve(self,r,s,k,selected,bottom):
  from search_effects import SEARCH_SPECS
  return r.dispatch(SEARCH_SPECS[r._source(s,k,'main_text').card_number][0],s,k,{'selected':selected,'bottom_order':bottom})
 def test_choices_are_public_and_do_not_mutate(self):
  from search_effects import search_choices
  r,s,k,keys=self.prepare();before=r.snapshot()['state'];c=search_choices(r,s,k)
  self.assertEqual(c['revealed'],keys);self.assertEqual(c['selections'],[keys[:2]]);self.assertEqual(before,r.snapshot()['state'])
 def test_exact_cards_and_explicit_bottom_order(self):
  for n,top in [('BT11-023',None),('P-138',None),('EX2-008',['ST7-05','BT19-080','BT9-011','EX2-008'])]:
   r,s,k,keys=self.prepare(n,top);bottom=list(reversed(keys[2:]));result=self.resolve(r,s,k,keys[:2],bottom)
   self.assertEqual([c.key for c in r.state.zones[s]['hand']],keys[:2]);self.assertEqual([c.key for c in r.state.zones[s]['deck'][:len(bottom)]],bottom)
   self.assertEqual(result['revealed'],keys);r.verify();self.assertEqual(r.matches_played,0)
 def test_absent_categories(self):
  from search_effects import search_choices
  for top in [['BT12-029','BT12-029','EX1-013'],['EX1-013']*3]:
   r,s,k,keys=self.prepare(top=top);options=search_choices(r,s,k)['selections'];self.assertEqual(len(options[0]),int(top[0]=='BT12-029'))
   chosen=options[-1];self.resolve(r,s,k,chosen,[x for x in keys if x not in chosen]);r.verify()
 def test_short_and_empty_deck(self):
  from search_effects import search_choices
  for remaining in (0,1):
   r,s,k,keys=self.prepare();deck=r.state.zones[s]['deck'];cut=len(deck)-remaining;r.state.zones[s]['trash'].extend(deck[:cut]);del deck[:cut]
   c=search_choices(r,s,k);self.assertEqual(len(c['revealed']),remaining);chosen=c['selections'][0];self.resolve(r,s,k,chosen,[x for x in c['revealed'] if x not in chosen])
 def test_invalid_choices_roll_back(self):
  for a,b in [([0],[2]),([0,0],[1,2]),([0,2],[1]),([0,1],[]),([0,1],[2,2])]:
   r,s,k,keys=self.prepare();before=r.snapshot()['state']
   with self.assertRaisesRegex(RuntimeHalt,'SEARCH_'):self.resolve(r,s,k,[keys[i] for i in a],[keys[i] for i in b])
   self.assertEqual(before,r.snapshot()['state'])
 def test_overlapping_slots(self):
  from search_effects import _selection_alternatives
  self.assertEqual(_selection_alternatives(['x'],({'x'},{'x'})),[['x']])
  self.assertEqual(_selection_alternatives(['x','y'],({'x','y'},{'x'})),[['x','y']])

class ExtendedSearchTests(unittest.TestCase):
 resolve = SearchTests.resolve
 def prepare(self,number='EX13-017',top=None):
  # Existing fixture supports a B-owned EX8 source without changing inventory.
  if number!='EX8-009':return SearchTests.prepare(self,number,top)
  from search_effects import search_bindings
  from selected_mechanics import build_selected_registry
  ctx=selected_context();rules=build_selected_registry(ctx,ROOT).bindings[0].evidence[-1]
  r=ContextRuntime(ctx,101,'A',MechanicRegistry(search_bindings(ctx,ROOT,rules)),allow_experimental=True)
  s='B';k=stage(r,s,[number]);deck=r.state.zones[s]['deck'];cards=[]
  for n in top:
   c=next(c for c in deck if c.card_number==n);deck.remove(c);cards.append(c)
  deck.extend(reversed(cards));return r,s,k,[c.key for c in cards]
 def test_ex13_one_slot_includes_tamer_text_and_exact_royal_knight(self):
  from search_effects import search_choices
  r,s,k,keys=self.prepare(top=['BT22-085','BT11-032','EX1-013'])
  self.assertEqual(search_choices(r,s,k)['selections'],sorted([[keys[0]],[keys[1]]]))
  self.resolve(r,s,k,[keys[0]],keys[1:]);r.verify()
 def test_ex13_cannot_take_two_or_decline_available_card(self):
  for selected in ([],[0,1]):
   r,s,k,keys=self.prepare(top=['BT22-085','BT11-032','EX1-013']);before=r.snapshot()['state']
   with self.assertRaisesRegex(RuntimeHalt,'SEARCH_'):self.resolve(r,s,k,[keys[i] for i in selected],[keys[2]])
   self.assertEqual(before,r.snapshot()['state'])
 def test_ex13_missing_target(self):
  from search_effects import search_choices
  r,s,k,keys=self.prepare(top=['EX1-013']*3)
  self.assertEqual(search_choices(r,s,k)['selections'],[[]]);self.resolve(r,s,k,[],keys)
 def test_printed_text_fields_only(self):
  from search_effects import _has_veedramon_text
  from types import SimpleNamespace
  fields=('name','traits','main_text','inherited_text','security_text','special_conditions','normal_digivolution')
  for field in fields:
   for kind in ('Option','Tamer'):
    raw={'type':kind,field:{'Assembly':'Veedramon'} if field in ('special_conditions','normal_digivolution') else 'Veedramon'}
    self.assertTrue(_has_veedramon_text(SimpleNamespace(to_dict=lambda:raw)),(field,kind))
  raw={'name':'Other','official_source':{'url':'https://example/Veedramon'},'verification_status':'Veedramon','unrelated':'Veedramon'}
  self.assertFalse(_has_veedramon_text(SimpleNamespace(to_dict=lambda:raw)))
 def test_ex8_exact_x_antibody_and_missing_slot(self):
  from search_effects import search_choices
  for third,expected in [('BT9-109',2),('EX5-070',1)]:
   r,s,k,keys=self.prepare('EX8-009',['ST7-05',third,'EX2-008'])
   selected=search_choices(r,s,k)['selections'][0];self.assertEqual(len(selected),expected)
   self.assertEqual(set(selected),set(keys[:expected]));self.resolve(r,s,k,selected,[x for x in keys if x not in selected]);r.verify()
 def test_ex8_must_take_both_available_targets(self):
  r,s,k,keys=self.prepare('EX8-009',['ST7-05','BT9-109','EX2-008']);before=r.snapshot()['state']
  with self.assertRaisesRegex(RuntimeHalt,'SEARCH_'):self.resolve(r,s,k,keys[:1],keys[1:])
  self.assertEqual(before,r.snapshot()['state'])
 def test_new_search_cards_do_not_expose_deck_without_activation(self):
  from search_effects import search_choices
  for number,top in [('EX13-017',['BT22-085','BT11-032','EX1-013']),('EX8-009',['ST7-05','BT9-109','EX2-008'])]:
   r,s,k,keys=self.prepare(number,top);r.state.phase='MAIN';before=r.snapshot()['state']
   with self.assertRaisesRegex(RuntimeHalt,'SEARCH_ACTIVATION_WINDOW_REQUIRED'):search_choices(r,s,k)
   self.assertEqual(before,r.snapshot()['state'])
