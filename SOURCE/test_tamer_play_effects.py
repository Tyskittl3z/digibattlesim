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
