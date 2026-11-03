"""EX13-022 case59 choices and source-bound free play; zero full-match credit."""
import copy
import gzip
import json
import unittest

from battle_evolution import choose_battle_evolution
from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, queue_effects, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage

import tamer_play_effects as tamers


class TamerPlayEffectTests(unittest.TestCase):
    def runtime(self, active='A'):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        return ContextRuntime(context, 5900, active, build_selected_registry(context, ROOT),
                              allow_experimental=True)

    def actual59(self):
        record = json.loads(gzip.decompress((ROOT /
            'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0059.json.gz').read_bytes()))
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        expected = copy.deepcopy(record['halts'][-1]['before']['state'])
        expected.setdefault('resolving_option', None)
        self.assertEqual(runtime.snapshot()['state'], expected)
        args = record['commands'][-1]['args']
        choose_battle_evolution(runtime, 'B', args['source_key'], args['hand_key'], args['route_index'], ROOT)
        self.assertEqual((runtime.state.memory, runtime.state.phase), (3, 'MAIN'))
        self.assertEqual([card.key for card in runtime.state.battle['B'][args['hand_key']].cards],
                         ['B:EX13-019#1', 'B:EX13-022#4'])
        self.assertIn('B:BT11-023#1', [card.key for card in runtime.state.zones['B']['hand']])
        return runtime, args['hand_key']

    def test_actual59_decline_consumes_shared_opt_without_playing_or_reacting(self):
        runtime, source = self.actual59()
        pending = pending_options(runtime, 'B')
        self.assertEqual([record['effect_id'] for record in pending], [tamers.PLAY_EFFECT])
        self.assertEqual(tamers.tamer_play_choices(runtime, 'B', source, tamers.PLAY_EFFECT),
                         [None, 'B:BT11-112#2'])
        result = resolve_pending(runtime, 'B', pending[0]['id'], None)
        self.assertEqual(result['processing'], 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION')
        self.assertEqual(set(runtime.state.battle['B']), {source})
        self.assertEqual((runtime.state.active, runtime.state.memory, runtime.state.phase), ('B', 3, 'MAIN'))
        self.assertEqual(runtime.state.pending, [])
        self.assertIn(tamers.tamer_play_usage(runtime, 'B', source, tamers.PLAY_EFFECT), runtime.state.once_used)
        # This is one consolidated effect: a later printed trigger in the same
        # turn cannot create a second allowance after the activation declined.
        queue_effects(runtime, [{'seat': 'B', 'source': source, 'effect_id': tamers.PLAY_EFFECT,
            'field': 'main_text', 'trigger': {'kind': 'When Attacking'},
            'usage': list(tamers.tamer_play_usage(runtime, 'B', source, tamers.PLAY_EFFECT))}])
        self.assertEqual(runtime.state.pending, [])
        runtime.verify()

    def test_actual59_free_rina_queues_simultaneous_choices_and_accepts_both_orders(self):
        from effect_grants import active_keyword, active_restriction
        from on_play_effects import ON_PLAY_SPECS, on_play_choices
        runtime, source = self.actual59()
        pending = pending_options(runtime, 'B')[0]
        result = resolve_pending(runtime, 'B', pending['id'], 'B:BT11-112#2')
        self.assertEqual((result['play']['cost'], runtime.state.memory), (0, 3))
        self.assertIn('B:BT11-112#2', runtime.state.battle['B'])
        group = pending_options(runtime, 'B')
        rina_effect = ON_PLAY_SPECS['BT11-112'][0]
        self.assertEqual({record['effect_id'] for record in group}, {rina_effect, tamers.OBSERVER_EFFECT})
        self.assertEqual({record['depth'] for record in group}, {1})
        for order in ((rina_effect, tamers.OBSERVER_EFFECT), (tamers.OBSERVER_EFFECT, rina_effect)):
            with self.subTest(order=order):
                branch = copy.deepcopy(runtime)
                for effect_id in order:
                    selected = next(record for record in pending_options(branch, 'B')
                                    if record['effect_id'] == effect_id)
                    if effect_id == rina_effect:
                        self.assertEqual(on_play_choices(branch, 'B', 'B:BT11-112#2'), [source])
                        target = source
                    else:
                        self.assertEqual(tamers.tamer_play_choices(branch, 'B', source, effect_id),
                                         ['A:BT11-032#1'])
                        target = 'A:BT11-032#1'
                    resolve_pending(branch, 'B', selected['id'], target)
                self.assertTrue(active_keyword(branch, 'B', source, 'Blocker'))
                self.assertTrue(active_keyword(branch, 'B', source, 'Evade'))
                self.assertTrue(active_restriction(branch, 'A', 'A:BT11-032#1', 'cannot_suspend'))
                restriction = branch.state.battle['A']['A:BT11-032#1'].statuses['effect_grants'][0]
                self.assertEqual((restriction['controller'], restriction['target_owner']), ('B', 'A'))
                self.assertEqual(restriction['expires'], {'turn': 4, 'controller': 'A', 'boundary': 'turn_end'})
                self.assertEqual((branch.state.active, branch.state.memory, branch.state.phase), ('B', 3, 'MAIN'))
                self.assertTrue(all(not stack.suspended for area in branch.state.battle.values()
                                    for stack in area.values()))
                self.assertEqual(branch.state.pending, [])
                resolved = [event['effect_id'] for event in branch.events
                            if event['type'] == 'MECHANIC_RESOLVED']
                self.assertEqual(tuple(resolved[-2:]), order)
                branch.verify()

    def test_actual59_mandatory_observer_target_cannot_be_declined(self):
        runtime, source = self.actual59()
        resolve_pending(runtime, 'B', pending_options(runtime, 'B')[0]['id'], 'B:BT11-112#2')
        selected = next(record for record in pending_options(runtime, 'B')
                        if record['effect_id'] == tamers.OBSERVER_EFFECT)
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'TAMER_PLAY_TARGET_INVALID'):
            resolve_pending(runtime, 'B', selected['id'], None)
        self.assertEqual(runtime.snapshot(), before)

    def hand(self, runtime, seat, number):
        deck = runtime.state.zones[seat]['deck']
        physical = next(card for card in deck if card.card_number == number)
        deck.remove(physical)
        runtime.state.zones[seat]['hand'].append(physical)
        return physical.key

    def test_bound_free_play_allows_opponent_turn_and_negative_memory(self):
        runtime = self.runtime('A')
        source = stage(runtime, 'B', ['EX13-022'])
        hand_key = self.hand(runtime, 'B', 'BT11-112')
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.memory = -2
        queue_effects(runtime, [{'seat': 'B', 'source': source, 'effect_id': tamers.PLAY_EFFECT,
            'field': 'main_text', 'trigger': {'kind': 'When Digivolving'},
            'usage': list(tamers.tamer_play_usage(runtime, 'B', source, tamers.PLAY_EFFECT))}])
        result = resolve_pending(runtime, 'B', pending_options(runtime, 'B')[0]['id'], hand_key)
        self.assertEqual(result['play']['cost'], 0)
        self.assertEqual((runtime.state.active, runtime.state.memory), ('A', -2))
        self.assertIn(hand_key, runtime.state.battle['B'])
        runtime.verify()

    def test_internal_free_play_requires_activated_matching_source(self):
        from main_actions import play_tamer_from_effect
        runtime = self.runtime()
        self.hand(runtime, 'A', 'BT11-112')
        source = stage(runtime, 'A', ['EX13-022'])
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'EFFECT_PLAY_WINDOW_REQUIRED'):
            play_tamer_from_effect(runtime, 'A', runtime.state.zones['A']['hand'][0].key, ROOT)
        self.assertEqual(runtime.snapshot(), before)

    def test_additional_actual_unimplemented_tamer_observer_halts_before_free_placement(self):
        runtime = self.runtime()
        source = stage(runtime, 'A', ['EX13-022'])
        stage(runtime, 'A', ['BT11-032'])
        hand_key = self.hand(runtime, 'A', 'BT11-112')
        runtime.state.phase = 'MAIN'
        queue_effects(runtime, [{'seat': 'A', 'source': source, 'effect_id': tamers.PLAY_EFFECT,
            'field': 'main_text', 'trigger': {'kind': 'When Digivolving'}}])
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'BASIC_EVENT_OBSERVER_UNIMPLEMENTED.*BT11-032'):
            resolve_pending(runtime, 'A', pending_options(runtime, 'A')[0]['id'], hand_key)
        self.assertEqual(runtime.snapshot(), before)


class EncounteredVeedramonTamerTests(unittest.TestCase):
    def actual(self):
        path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-02/game-0000-segment.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,record['seed'],record['first'],
            build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        self.assertEqual(runtime.snapshot()['state'],record['halts'][-1]['before']['state'])
        args=record['commands'][-1]['args']
        choose_battle_evolution(runtime,'B',args['source_key'],args['hand_key'],args['route_index'],ROOT)
        self.assertEqual((runtime.state.memory,runtime.state.phase),(6,'MAIN'))
        self.assertEqual([c.key for c in runtime.state.battle['B'][args['hand_key']].cards],
                         ['B:EX13-002#1','B:EX1-013#3','B:BT22-022#1'])
        return runtime,args['hand_key']

    def test_actual_bt22_choices_include_post_draw_tamer_and_decline_without_opt(self):
        runtime,source=self.actual()
        selected=pending_options(runtime,'B')[0]
        self.assertEqual(selected['effect_id'],'BT22-022.play_tamer')
        self.assertEqual(selected['usage'],[])
        self.assertEqual(tamers.tamer_play_choices(runtime,'B',source,'BT22-022.play_tamer'),
                         [None,'B:BT11-112#3','B:EX13-069#3'])
        before=set(runtime.state.once_used)
        result=resolve_pending(runtime,'B',selected['id'],None)
        self.assertEqual(result['processing'],'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION')
        self.assertEqual(runtime.state.once_used,before)
        self.assertNotIn('B:BT11-112#3',runtime.state.battle['B']);runtime.verify()

    def test_bt22_condition_is_rechecked_at_activation_and_false_is_a_noop(self):
        runtime,source=self.actual()
        # Another simultaneous effect may have placed a second Tamer before
        # this already triggered effect activates.
        stage(runtime,'B',['BT22-085'])
        self.assertEqual(tamers.tamer_play_choices(runtime,'B',source,'BT22-022.play_tamer'),[None])
        before=copy.deepcopy(runtime.state.battle)
        result=resolve_pending(runtime,'B',pending_options(runtime,'B')[0]['id'],None)
        self.assertEqual(result['processing'],'CONDITION_NOT_MET')
        self.assertEqual(runtime.state.battle,before);self.assertEqual(runtime.state.once_used,set())

    def test_actual_free_rina_and_egg_emit_four_simultaneous_effects_without_orientation_event(self):
        from on_play_effects import ON_PLAY_SPECS
        runtime,source=self.actual()
        result=resolve_pending(runtime,'B',pending_options(runtime,'B')[0]['id'],'B:BT11-112#3')
        self.assertEqual((result['play']['cost'],runtime.state.memory),(0,6))
        group=pending_options(runtime,'B')
        self.assertEqual(sorted((p['effect_id'],p['source'],p['field']) for p in group),sorted([
            (ON_PLAY_SPECS['BT11-112'][0],'B:BT11-112#3','main_text'),
            (tamers.OBSERVER_EFFECT,'B:EX13-022#1','main_text'),
            (tamers.OBSERVER_EFFECT,'B:EX13-022#3','main_text'),
            ('EX13-002.tamer_play_unsuspend','B:EX13-002#1','inherited_text')]))
        self.assertEqual({p['depth'] for p in group},{1})
        self.assertEqual(len({p['id'] for p in group}),4)
        egg=next(p for p in group if p['effect_id']=='EX13-002.tamer_play_unsuspend')
        for choice in (False,True):
            branch=copy.deepcopy(runtime);before=set(branch.state.once_used)
            result=resolve_pending(branch,'B',egg['id'],choice)
            self.assertFalse(result['changed']);self.assertFalse(branch.state.battle['B'][source].suspended)
            self.assertEqual(len(branch.state.once_used-before),1)
            self.assertFalse(any(p['effect_id']=='EX1-013.unsuspend_memory' for p in branch.state.pending))
            self.assertEqual((branch.state.memory,branch.state.phase),(6,'MAIN'));branch.verify()

    def test_post_draw_rina_is_playable_and_still_queues_egg_and_two_observers(self):
        runtime,source=self.actual()
        resolve_pending(runtime,'B',pending_options(runtime,'B')[0]['id'],'B:EX13-069#3')
        self.assertIn('B:EX13-069#3',runtime.state.battle['B'])
        group=pending_options(runtime,'B')
        self.assertEqual(len(group),3)
        self.assertEqual(sorted(p['effect_id'] for p in group),
            sorted([tamers.OBSERVER_EFFECT,tamers.OBSERVER_EFFECT,'EX13-002.tamer_play_unsuspend']))
        self.assertFalse(runtime.state.battle['B'][source].suspended);runtime.verify()
