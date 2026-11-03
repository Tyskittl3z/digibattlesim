"""The encountered optional return of the opponent's fewest-source Digimon."""
import copy
import unittest

from context_runtime import ContextRuntime,MechanicRegistry,RuntimeHalt
from effect_scheduler import queue_effects,pending_options,resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT,stage


class UlforceFewestReturnTests(unittest.TestCase):
    def fixture(self,opponent='plain'):
        from ex13_ulforce_effects import RETURN_EFFECT,ulforce_return_bindings
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        registry=build_selected_registry(context,ROOT)
        bindings=tuple(b for b in registry.bindings if b.effect_id!=RETURN_EFFECT)
        bindings+=ulforce_return_bindings(context,ROOT,registry.bindings[0].evidence[-1])
        r=ContextRuntime(context,811,'B',MechanicRegistry(bindings),allow_experimental=True)
        r.state.phase='UNSUSPEND';r.state.turn=8;r.state.memory=1
        source=stage(r,'B',['EX1-013','BT22-022','BT22-023','EX13-023'])
        if opponent=='plain':
            target=stage(r,'A',['BT12-029'])
            untouched=stage(r,'A',['EX13-022','BT11-032'])
            tamer=stage(r,'A',['BT11-112'])
            from effect_grants import grant_effect
            grant_effect(r,'A',target,{'keywords':['Blocker','Evade']},tamer)
        elif opponent=='replacement':
            target=stage(r,'A',['BT22-022','BT22-023']);untouched=None
            stage(r,'A',['BT11-112'])
        else:
            target=stage(r,'A',['EX13-023']);untouched=None
        queue_effects(r,[{'seat':'B','source':source,'effect_id':RETURN_EFFECT,
            'field':'main_text','trigger':{'kind':'When Digivolving'}}])
        return r,source,target,untouched

    def resolve(self,r,choice):
        return resolve_pending(r,'B',pending_options(r,'B')[0]['id'],choice)

    def test_sole_minimum_returns_without_deleting_or_using_evade(self):
        from ex13_ulforce_effects import ulforce_return_choices
        r,source,target,untouched=self.fixture();before=copy.deepcopy(r.state.battle['A'][untouched])
        self.assertEqual(ulforce_return_choices(r,'B',source),[False,True])
        rng=r.snapshot()['rng_state'];result=self.resolve(r,True)
        self.assertEqual(result['returned'],[target]);self.assertEqual(result['trashed_sources'],[])
        self.assertNotIn(target,r.state.battle['A'])
        self.assertEqual(r.state.zones['A']['deck'][0].key,target)
        self.assertEqual(r.state.battle['A'][untouched],before)
        self.assertEqual((r.state.memory,r.state.phase),(1,'UNSUSPEND'))
        self.assertEqual(r.snapshot()['rng_state'],rng);r.verify()

    def test_decline_is_explicit_and_moves_no_card(self):
        r,_,target,_=self.fixture();before=copy.deepcopy(r.state)
        result=self.resolve(r,False)
        self.assertEqual(result['processing'],'OPTIONAL_RETURN_DECLINED')
        before.pending=[]
        self.assertEqual(r.state,before);self.assertIn(target,r.state.battle['A'])

    def test_multiple_minima_need_effect_owner_order_before_any_mutation(self):
        r,_,_,_=self.fixture();stage(r,'A',['EX13-019']);before=r.snapshot()
        with self.assertRaisesRegex(RuntimeHalt,'ULFORCE_RETURN_ORDER_REQUIRED: chooser=B deck_owner=A'):
            self.resolve(r,True)
        self.assertEqual(r.snapshot(),before)

    def test_effect_owner_orders_all_tied_minima_at_deck_bottom(self):
        r,_,target,untouched=self.fixture();second=stage(r,'A',['EX13-019'])
        result=self.resolve(r,{'activate':True,'bottom_order':[second,target]})
        self.assertEqual(result['bottom_order_controller'],'B')
        self.assertEqual(result['bottom_order'],[second,target])
        self.assertEqual([c.key for c in r.state.zones['A']['deck'][:2]],[second,target])
        self.assertIn(untouched,r.state.battle['A'])
        self.assertNotIn(target,r.state.battle['A']);self.assertNotIn(second,r.state.battle['A']);r.verify()

    def test_tied_return_order_cannot_omit_duplicate_or_add_a_card(self):
        for mode in ('omit','duplicate','extra'):
            r,_,target,untouched=self.fixture();second=stage(r,'A',['EX13-019'])
            order={'omit':[target],'duplicate':[target,target],
                   'extra':[target,second,untouched]}[mode]
            before=r.snapshot()
            with self.subTest(mode=mode),self.assertRaisesRegex(RuntimeHalt,'ULFORCE_RETURN_ORDER_INVALID'):
                self.resolve(r,{'activate':True,'bottom_order':order})
            self.assertEqual(r.snapshot(),before)

    def test_actual_self_replacement_is_not_silently_skipped(self):
        r,_,_,_=self.fixture('replacement');before=r.snapshot()
        with self.assertRaisesRegex(RuntimeHalt,'ULFORCE_RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED.*BT22-022'):
            self.resolve(r,True)
        self.assertEqual(r.snapshot(),before)

    def test_unsuspended_target_protection_is_not_silently_skipped(self):
        r,_,_,_=self.fixture('protected');before=r.snapshot()
        with self.assertRaisesRegex(RuntimeHalt,'ULFORCE_RETURN_PROTECTION_UNIMPLEMENTED.*EX13-023'):
            self.resolve(r,True)
        self.assertEqual(r.snapshot(),before)


if __name__=='__main__':unittest.main()
