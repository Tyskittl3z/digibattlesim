"""Ordinary digivolutions selected in the preserved cohort02 gameplay traces."""
import copy
import gzip
import importlib.util
import json
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime, RuntimeHalt
from context_evolution import EvolutionRoute
from effect_scheduler import pending_options, queue_effects, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage

_SEGMENT07 = None


class BattleEvolutionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('battle_evolution'),
                             'Encountered ordinary battle evolution is missing')

    def runtime(self, base='EX1-013', target='EX13-019'):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 181, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'; runtime.state.turn = 4; runtime.state.memory = 3
        source = stage(runtime, 'A', [base])
        stack = runtime.state.battle['A'][source]
        stack.instance_id = 'entity-fixture'; stack.played_turn = 1; stack.ready_since_turn = 2
        deck = runtime.state.zones['A']['deck']
        physical = next(c for c in deck if c.card_number == target)
        deck.remove(physical); runtime.state.zones['A']['hand'].append(physical)
        return runtime, source, physical.key

    def choose(self, runtime, source, target, index=0, **kwargs):
        from battle_evolution import choose_battle_evolution
        return choose_battle_evolution(runtime, runtime.state.active, source, target, index, ROOT, **kwargs)

    def actual(self, index):
        path = ROOT / f'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-{index:04d}.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        expected = copy.deepcopy(record['halts'][-1]['before']['state'])
        expected.setdefault('resolving_option', None)
        self.assertEqual(runtime.snapshot()['state'], expected)
        return runtime, record['commands'][-1]['args']

    def test_five_recorded_veedramon_evolutions_pay_stack_and_draw(self):
        for index, memory, phase in ((27, -2, 'END_OF_TURN'), (28, 0, 'MAIN'),
                (29, 1, 'MAIN'), (34, -2, 'END_OF_TURN'), (42, 0, 'MAIN')):
            with self.subTest(index=index):
                runtime, args = self.actual(index)
                source, target = args['source_key'], args['hand_key']
                old = copy.deepcopy(runtime.state.battle[runtime.state.active][source])
                drawn = runtime.state.zones[runtime.state.active]['deck'][-1].key
                result = self.choose(runtime, source, target, args['route_index'])
                stack = runtime.state.battle[runtime.state.active][target]
                self.assertNotIn(source, runtime.state.battle[runtime.state.active])
                self.assertEqual([c.key for c in stack.cards], [source, target])
                self.assertEqual((stack.instance_id, stack.suspended, stack.played_turn, stack.ready_since_turn),
                                 (old.instance_id, old.suspended, old.played_turn, old.ready_since_turn))
                self.assertEqual((runtime.state.memory, runtime.state.phase), (memory, phase))
                self.assertEqual(result['drawn_card'], drawn)
                self.assertIn(drawn, [c.key for c in runtime.state.zones[runtime.state.active]['hand']])
                self.assertNotIn(target, [c.key for c in runtime.state.zones[runtime.state.active]['hand']])
                self.assertEqual(runtime.state.pending, []); runtime.verify()

    def test_actual_0046_queues_digivolving_return_after_draw_with_both_choices(self):
        from aero_effects import DIGIVOLVE_EFFECT, aero_choices
        runtime, args = self.actual(46)
        source, target = args['source_key'], args['hand_key']
        old = copy.deepcopy(runtime.state.battle['B'][source])
        drawn = runtime.state.zones['B']['deck'][-1].key
        result = self.choose(runtime, source, target, args['route_index'])
        self.assertEqual((result['cost'], runtime.state.memory, runtime.state.phase), (3, 0, 'MAIN'))
        stack = runtime.state.battle['B'][target]
        self.assertEqual([c.key for c in stack.cards], ['B:EX13-019#4', 'B:BT22-023#2'])
        self.assertEqual((stack.instance_id, stack.suspended, stack.played_turn),
                         (old.instance_id, False, 2))
        self.assertEqual(result['drawn_card'], drawn)
        pending = pending_options(runtime, 'B')
        self.assertEqual([(p['effect_id'], p['source']) for p in pending], [(DIGIVOLVE_EFFECT, target)])
        self.assertEqual(aero_choices(runtime, 'B', target, DIGIVOLVE_EFFECT),
                         ['A:EX13-017#3', 'A:EX13-019#4'])
        for selected in ['A:EX13-017#3', 'A:EX13-019#4']:
            branch = copy.deepcopy(runtime)
            resolve_pending(branch, 'B', pending[0]['id'], selected)
            self.assertEqual(branch.state.zones['A']['deck'][0].key, selected)
            self.assertEqual((branch.state.memory, branch.state.phase), (0, 'MAIN')); branch.verify()
        self.assertEqual(runtime.matches_played, 0); runtime.verify()

    def test_actual_0059_queues_its_encountered_optional_tamer_play(self):
        from tamer_play_effects import PLAY_EFFECT,tamer_play_choices
        runtime,args=self.actual(59)
        self.choose(runtime,args['source_key'],args['hand_key'],args['route_index'])
        pending=pending_options(runtime,'B')
        self.assertEqual([p['effect_id'] for p in pending],[PLAY_EFFECT])
        self.assertEqual(tamer_play_choices(runtime,'B',args['hand_key'],PLAY_EFFECT),
                         [None,'B:BT11-112#2'])
        self.assertEqual(runtime.state.memory,3)

    def test_digivolving_search_occurs_and_keeps_turn_until_resolved(self):
        from search_effects import search_choices
        runtime, source, target = self.runtime(target='P-138'); runtime.state.memory = 0
        self.choose(runtime, source, target)
        self.assertEqual((runtime.state.memory, runtime.state.phase), (-2, 'MAIN'))
        pending = pending_options(runtime, 'A')
        self.assertEqual([(p['effect_id'], p['source']) for p in pending], [('P-138.on_play_search', target)])
        options = search_choices(runtime, 'A', target); selected = options['selections'][0]
        resolve_pending(runtime, 'A', pending[0]['id'],
            {'selected': selected, 'bottom_order': [k for k in options['revealed'] if k not in selected]})
        self.assertEqual(runtime.state.phase, 'END_OF_TURN'); runtime.verify()

    def test_orientation_history_and_applied_grants_survive_new_top(self):
        from effect_grants import grant_effect, active_keyword, active_dp_bonus
        runtime, source, target = self.runtime()
        rina = stage(runtime, 'A', ['BT11-112'])
        grant_effect(runtime, 'A', source, {'keywords': ['Blocker', 'Evade']}, rina)
        grant_effect(runtime, 'A', source, {'dp_bonus': 3000}, rina)
        runtime.state.battle['A'][source].suspended = True
        before = copy.deepcopy(runtime.state.battle['A'][source])
        self.choose(runtime, source, target)
        stack = runtime.state.battle['A'][target]
        self.assertEqual((stack.instance_id, stack.suspended, stack.played_turn, stack.ready_since_turn),
                         (before.instance_id, True, 1, 2))
        self.assertEqual(stack.statuses, before.statuses)
        self.assertTrue(active_keyword(runtime, 'A', target, 'Blocker'))
        self.assertTrue(active_keyword(runtime, 'A', target, 'Evade'))
        self.assertEqual(active_dp_bonus(runtime, 'A', target), 3000); runtime.verify()

    def test_invalid_stale_sources_targets_and_routes_are_atomic(self):
        from battle_evolution import choose_battle_evolution
        for name, reason in [('source','BATTLE_EVOLUTION_SOURCE_REQUIRED'),
                ('hand','HAND_COPY_REQUIRED'), ('route','ROUTE_INDEX_INVALID'),
                ('negative','ROUTE_INDEX_INVALID'), ('bool','ROUTE_INDEX_INVALID'),
                ('ineligible','ROUTE_INDEX_INVALID')]:
            runtime, source, target = self.runtime(target='EX13-023' if name == 'ineligible' else 'EX13-019')
            index = 0
            if name == 'source': source = 'A:EX1-013#999'
            elif name == 'hand': target = 'A:EX13-019#999'
            elif name == 'route': index = 99
            elif name == 'negative': index = -1
            elif name == 'bool': index = True
            before = runtime.snapshot()
            with self.assertRaisesRegex(RuntimeHalt, reason):
                choose_battle_evolution(runtime, 'A', source, target, index, ROOT)
            self.assertEqual(runtime.snapshot(), before)

    def test_insufficient_memory_does_not_clamp_or_mutate(self):
        runtime, source, target = self.runtime(); runtime.state.memory = 0
        impossible = EvolutionRoute(11, 'PRINTED_NORMAL', 'TEST_ONLY_BOUND',
                                   runtime.context.card('A', 'EX13-019').definition_sha256)
        before = runtime.snapshot()
        with patch('battle_evolution.printed_evolution_options', return_value=(impossible,)):
            with self.assertRaisesRegex(RuntimeHalt, 'INSUFFICIENT_AVAILABLE_MEMORY'):
                self.choose(runtime, source, target)
        self.assertEqual(runtime.snapshot(), before)

    def test_turn_pending_attack_terminal_and_unbound_reduction_guards(self):
        from attack_flow import declare_attack
        from battle_evolution import choose_battle_evolution
        for scenario, reason in [('seat','ACTIVE_PLAYER_REQUIRED'), ('phase','MAIN_PHASE_REQUIRED'),
                ('memory','TURN_END_WINDOW_UNIMPLEMENTED'), ('pending','PENDING_EFFECTS_REQUIRE_RESOLUTION'),
                ('attack','ATTACK_PROCESSING_PENDING'), ('terminal','ACTION_AFTER_TERMINAL'),
                ('reduction','UNBOUND_EVOLUTION_COST_REDUCTION')]:
            runtime, source, target = self.runtime(); seat='A'; kwargs={}
            if scenario == 'seat': seat='B'
            elif scenario == 'phase': runtime.state.phase='BREEDING'
            elif scenario == 'memory': runtime.state.memory=-1
            elif scenario == 'pending':
                rina = stage(runtime, 'A', ['BT22-085'])
                queue_effects(runtime, [{'seat':'A','source':rina,'effect_id':'BT22-085.start_turn_memory',
                                        'field':'main_text','trigger':{'kind':'Start of Your Turn'}}])
            elif scenario == 'attack': declare_attack(runtime, 'A', source, 'PLAYER', ROOT)
            elif scenario == 'terminal': runtime.state.terminal=True
            else: kwargs={'cost_reduction':2}
            before=runtime.snapshot()
            with self.assertRaisesRegex(RuntimeHalt, reason):
                choose_battle_evolution(runtime, seat, source, target, 0, ROOT, **kwargs)
            self.assertEqual(runtime.snapshot(), before)

    def test_empty_evolution_draw_is_omitted_without_deckout(self):
        runtime, source, target = self.runtime(); deck=runtime.state.zones['A']['deck']
        runtime.state.zones['A']['trash'].extend(deck); deck.clear()
        result=self.choose(runtime, source, target)
        self.assertFalse(result['drew']); self.assertIsNone(result['drawn_card'])
        self.assertFalse(runtime.state.terminal); self.assertIn(target,runtime.state.battle['A'])
        runtime.verify()

    def segment07(self):
        global _SEGMENT07
        if _SEGMENT07 is None:
            path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-07/game-0000-segment.json.gz'
            record=json.loads(gzip.decompress(path.read_bytes()))
            context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
            runtime=ContextRuntime(context,record['seed'],record['first'],
                build_selected_registry(context,ROOT),allow_experimental=True)
            for command in record['commands'][:-1]:
                _apply(runtime,command['command'],command['seat'],command['args'],ROOT)
            self.assertEqual(runtime.snapshot()['state'],record['halts'][-1]['before']['state'])
            self.assertEqual(runtime.snapshot()['rng_state'],record['halts'][-1]['before']['rng_state'])
            _SEGMENT07=runtime,record['commands'][-1]
        return copy.deepcopy(_SEGMENT07)

    def test_actual_segment07_rina_evolution_draw_precedes_both_simultaneous_triggers(self):
        from selected_mechanics import ORIENTATION_EFFECT,_usage
        runtime,command=self.segment07()
        source='B:BT22-023#1';target='B:EX13-023#1'
        old=copy.deepcopy(runtime.state.battle['B'][source])
        drawn=runtime.state.zones['B']['deck'][-1].key
        rng=runtime.snapshot()['rng_state']
        result=_apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        evolved=runtime.state.battle['B'][target]
        self.assertEqual((result['evolution']['cost'],result['evolution']['cost_reduction']), (1,2))
        self.assertEqual((runtime.state.memory,runtime.state.phase),(1,'UNSUSPEND'))
        self.assertEqual([c.key for c in evolved.cards],[c.key for c in old.cards]+[target])
        self.assertEqual((evolved.instance_id,evolved.suspended,evolved.played_turn,evolved.ready_since_turn),
                         (old.instance_id,old.suspended,old.played_turn,old.ready_since_turn))
        self.assertTrue(runtime.state.battle['B']['B:EX13-069#4'].suspended)
        self.assertEqual(result['evolution']['drawn_card'],drawn)
        self.assertIn(drawn,[c.key for c in runtime.state.zones['B']['hand']])
        group=pending_options(runtime,'B')
        self.assertEqual([(p['effect_id'],p['source'],p['depth'],p['instance']) for p in group],
            [(ORIENTATION_EFFECT,target,2,old.instance_id),('EX13-023.return_fewest',target,2,old.instance_id)])
        self.assertEqual(group[0]['usage'],list(_usage(runtime,'B',target,ORIENTATION_EFFECT)))
        self.assertEqual(group[1]['usage'],[])
        self.assertEqual(result['evolution']['triggered_effects'],[p['effect_id'] for p in group])
        self.assertEqual(sum(b.effect_id==ORIENTATION_EFFECT for b in runtime.registry.bindings),1)
        self.assertEqual(runtime.snapshot()['rng_state'],rng);runtime.verify()

    def test_actual_segment07_two_effects_offer_either_order_without_forcing_orientation(self):
        from selected_mechanics import ORIENTATION_EFFECT
        for first in (ORIENTATION_EFFECT,'EX13-023.return_fewest'):
            with self.subTest(first=first):
                runtime,command=self.segment07()
                _apply(runtime,command['command'],command['seat'],command['args'],ROOT)
                untouched=copy.deepcopy(runtime.state.battle['A']['A:BT11-032#1'])
                for effect in (first, 'EX13-023.return_fewest' if first==ORIENTATION_EFFECT else ORIENTATION_EFFECT):
                    pending=next(p for p in pending_options(runtime,'B') if p['effect_id']==effect)
                    resolve_pending(runtime,'B',pending['id'],None if effect==ORIENTATION_EFFECT else True)
                self.assertNotIn('A:BT12-029#2',runtime.state.battle['A'])
                self.assertEqual(runtime.state.zones['A']['deck'][0].key,'A:BT12-029#2')
                self.assertEqual(runtime.state.battle['A']['A:BT11-032#1'],untouched)
                self.assertFalse(runtime.state.battle['B']['B:EX13-023#1'].suspended)
                self.assertEqual((runtime.state.memory,runtime.state.phase),(1,'UNSUSPEND'));runtime.verify()

    def test_actual_segment07_future_unknown_suspension_observer_halts_only_on_that_choice(self):
        from selected_mechanics import ORIENTATION_EFFECT
        runtime,command=self.segment07()
        _apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        pending=next(p for p in pending_options(runtime,'B') if p['effect_id']==ORIENTATION_EFFECT)
        before=runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt,'ORIENTATION_DEPENDENT_TRIGGER_UNIMPLEMENTED: BT11-112'):
            resolve_pending(runtime,'B',pending['id'],'B:EX13-023#1')
        self.assertEqual(runtime.snapshot(),before)


if __name__ == '__main__':
    unittest.main()
