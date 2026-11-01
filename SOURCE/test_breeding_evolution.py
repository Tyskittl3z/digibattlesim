"""Conserved selected-pair scenarios; zero full-match credit."""
import unittest
from unittest.mock import patch
from context_evolution import EvolutionRoute
from context_runtime import ContextRuntime, RuntimeHalt
from test_selected_mechanics import selected_context, ROOT, stage

try:
    from breeding_evolution import breeding_evolution_choices, choose_breeding_evolution
except ImportError:
    breeding_evolution_choices = choose_breeding_evolution = None


class BreedingEvolutionTests(unittest.TestCase):
    def runtime(self, base='EX2-001', target='EX8-009', memory=0):
        r = ContextRuntime(selected_context(), 913, 'B', allow_experimental=True)
        r.state.phase='MAIN';r.state.memory=memory
        for number, destination in ((base,r.state.breeding['B']), (target,r.state.zones['B']['hand'])):
            zone = r.state.zones['B']['eggdeck' if number=='EX2-001' else 'deck']
            card=next(c for c in zone if c.card_number==number)
            zone.remove(card);destination.append(card)
        r.verify()
        return r

    def choose(self,r,index=0):
        self.assertTrue(callable(choose_breeding_evolution), 'breeding action API missing')
        return choose_breeding_evolution(r,'B',r.state.zones['B']['hand'][0].key,index,ROOT)

    def test_egg_rookie_draws_and_mandatory_digivolving_search_is_suppressed(self):
        r=self.runtime();deck=len(r.state.zones['B']['deck']);target=r.state.zones['B']['hand'][0]
        self.choose(r)
        self.assertEqual(r.state.breeding['B'][-1],target)
        self.assertEqual(len(r.state.zones['B']['deck']),deck-1)
        self.assertEqual(len(r.state.zones['B']['hand']),1)
        self.assertEqual(r.state.pending,[]);self.assertEqual(r.state.memory,0)
        self.assertEqual(r.state.phase,'MAIN');self.assertEqual(r.matches_played,0);r.verify()

    def test_exact_cost_crosses_zero_and_closes_main(self):
        r=self.runtime('BT19-007','EX8-012',1)
        self.choose(r)
        self.assertEqual(r.state.memory,-2);self.assertEqual(r.state.phase,'END_OF_TURN')
        with self.assertRaisesRegex(RuntimeHalt,'MAIN_PHASE_REQUIRED'):
            self.choose(r)

    def test_paid_cost_stays_main_when_memory_remains_nonnegative(self):
        r=self.runtime('BT19-007','EX8-012',5)
        result=self.choose(r)
        self.assertEqual(result['cost'],3);self.assertEqual(r.state.memory,2)
        self.assertEqual(r.state.phase,'MAIN');self.assertTrue(result['drew'])

    def test_tamer_source_and_non_digimon_hand_target_are_refused(self):
        r=self.runtime('BT19-080','EX8-009');before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'BREEDING_SOURCE_TYPE_UNSUPPORTED'):self.choose(r)
        self.assertEqual(before,r.snapshot()['state'])
        r=self.runtime('EX2-001','BT19-080');before=r.snapshot()['state']
        self.assertEqual(breeding_evolution_choices(r,'B'),[])
        with self.assertRaisesRegex(RuntimeHalt,'ROUTE_INDEX_INVALID'):self.choose(r)
        self.assertEqual(before,r.snapshot()['state'])

    def test_special_same_level_and_normal_routes(self):
        r=self.runtime('BT19-009','BT9-011')
        self.assertTrue(callable(breeding_evolution_choices),'breeding choices API missing')
        choices=breeding_evolution_choices(r,'B')
        self.assertEqual([(c['cost'],c['basis']) for c in choices],[(0,'PRINTED_SPECIAL')])
        self.choose(r);self.assertEqual(r.state.memory,0)
        r=self.runtime('EX2-001','BT19-007')
        self.assertEqual(breeding_evolution_choices(r,'B')[0]['basis'],'PRINTED_NORMAL')
        self.choose(r)

    def test_guards_are_atomic(self):
        scenarios=[('actor','ACTIVE_PLAYER_REQUIRED'),('phase','MAIN_PHASE_REQUIRED'),
                   ('source','BREEDING_SOURCE_REQUIRED'),('card','HAND_COPY_REQUIRED'),
                   ('route','ROUTE_INDEX_INVALID'),('experimental','EXPERIMENTAL_OPT_IN_REQUIRED'),
                   ('negative','TURN_END_WINDOW_UNIMPLEMENTED'),('terminal','ACTION_AFTER_TERMINAL')]
        for name,reason in scenarios:
            with self.subTest(name=name):
                r=self.runtime();seat='B';key=r.state.zones['B']['hand'][0].key;index=0
                if name=='actor':seat='A'
                if name=='phase':r.state.phase='BREEDING'
                if name=='source':r.state.zones['B']['eggdeck'].extend(r.state.breeding['B']);r.state.breeding['B']=[]
                if name=='card':key='B:EX8-009#999'
                if name=='route':index=True
                if name=='experimental':r.allow_experimental=False
                if name=='negative':r.state.memory=-1
                if name=='terminal':r.state.terminal=True
                before=r.snapshot()['state']
                self.assertTrue(callable(choose_breeding_evolution),'breeding action API missing')
                with self.assertRaisesRegex(RuntimeHalt,reason):choose_breeding_evolution(r,seat,key,index,ROOT)
                self.assertEqual(r.snapshot()['state'],before)
                self.assertEqual(r.events[-1]['type'],'HALT')

    def test_invalid_route_including_unpayable_gauge(self):
        # Invalid indices never select a route through Python negative indexing.
        for index in (-1,99):
            r=self.runtime('BT19-007','EX8-012')
            before=r.snapshot()['state']
            with self.assertRaisesRegex(RuntimeHalt,'ROUTE_INDEX_INVALID'):self.choose(r,index)
            self.assertEqual(before,r.snapshot()['state'])

    def test_defensive_unpayable_gauge_refuses_without_clamping(self):
        # No printed selected-pair route exceeds 10. Inject only the route
        # result to test the defensive bound; do not invent official card text.
        r=self.runtime('BT19-007','EX8-012');before=r.snapshot()['state']
        impossible=EvolutionRoute(11,'PRINTED_NORMAL','TEST_ONLY_BOUND','test-only')
        with patch('breeding_evolution.printed_evolution_options',return_value=(impossible,)):
            self.assertEqual(breeding_evolution_choices(r,'B'),[])
            with self.assertRaisesRegex(RuntimeHalt,'INSUFFICIENT_AVAILABLE_MEMORY'):self.choose(r)
        self.assertEqual(before,r.snapshot()['state'])

    def test_unselected_pair_is_explicitly_out_of_scope(self):
        from match_context import DeckDefinition,MatchContext
        r=self.runtime();raw=r.context.deck_a.to_dict();raw['source_id']='other-list'
        r.context=MatchContext.create(DeckDefinition.from_dict(raw),r.context.deck_b,
                                      {c.number:c for c in r.context.cards},r.context.to_dict()['rules'])
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'SELECTED_PAIR_REQUIRED'):self.choose(r)
        self.assertEqual(before,r.snapshot()['state'])

    def test_pending_effect_guard_precedes_even_live_battle_action(self):
        from effect_scheduler import queue_effects
        from selected_mechanics import build_selected_registry
        r=self.runtime();r.registry=build_selected_registry(r.context,ROOT)
        from match_context import canonical
        r._pack_manifest=canonical(r.registry.manifest())
        source=stage(r,'A',['BT22-085'])
        queue_effects(r,[{'seat':'A','source':source,'effect_id':'BT22-085.start_turn_memory',
                         'field':'main_text','trigger':{'kind':'Start of Your Turn'}}])
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PENDING_EFFECTS_REQUIRE_RESOLUTION'):self.choose(r)
        self.assertEqual(before,r.snapshot()['state'])

    def test_live_battle_on_either_side_refused_before_mutation(self):
        for seat,number in [('A','BT11-023'),('B','BT19-007')]:
            r=self.runtime();stage(r,seat,[number]);before=r.snapshot()['state']
            with self.assertRaisesRegex(RuntimeHalt,'LIVE_BATTLE_SCOPE_UNSUPPORTED'):self.choose(r)
            self.assertEqual(before,r.snapshot()['state'])

    def test_empty_evolution_draw_does_not_lose(self):
        r=self.runtime();r.state.zones['B']['trash'].extend(r.state.zones['B']['deck']);r.state.zones['B']['deck']=[]
        result=self.choose(r)
        self.assertFalse(result['drew']);self.assertFalse(r.state.terminal);r.verify()

    def test_replay_conservation_and_read_only_choices(self):
        runs=[self.runtime(),self.runtime()]
        self.assertTrue(callable(breeding_evolution_choices),'breeding choices API missing')
        before=runs[0].snapshot()
        breeding_evolution_choices(runs[0],'B')
        self.assertEqual(before,runs[0].snapshot())
        for r in runs:self.choose(r);r.verify()
        self.assertEqual(runs[0].snapshot(),runs[1].snapshot())
        self.assertEqual(runs[0].events,runs[1].events)
        self.assertEqual(runs[0].events[-1]['choice']['rules']['sha256'],runs[0].events[-1]['result']['rules_source']['sha256'])

if __name__=='__main__':unittest.main()
