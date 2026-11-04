"""BT22-023 probes from recorded stops; scenarios earn no full-match credit."""
import copy
import gzip
import json
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending, queue_effects
from imported_attempts import _apply
from main_actions import choose_play
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage
import turn_flow

import aero_effects as aero


class AeroEffectTests(unittest.TestCase):
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
        return runtime, record['commands'][-1]

    def test_actual_0010_on_play_without_opponent_target_resolves_mandatory_noop(self):
        runtime, command = self.actual(10)
        source = command['args']['hand_key']
        try:
            choose_play(runtime, command['seat'], source, ROOT)
        except RuntimeHalt as exc:
            self.fail('Actual no-target hard play must reach its On Play: ' + str(exc))
        pending = pending_options(runtime, 'A')
        self.assertEqual([effect['effect_id'] for effect in pending], [aero.PLAY_EFFECT])
        self.assertEqual(aero.aero_choices(runtime, 'A', source, aero.PLAY_EFFECT), [None])
        result = resolve_pending(runtime, 'A', pending[0]['id'], None)
        self.assertEqual(result['processing'], 'NO_ELIGIBLE_TARGET')
        self.assertEqual((runtime.state.active, runtime.state.memory, runtime.state.phase),
                         ('A', -7, 'END_OF_TURN'))
        self.assertIn(source, runtime.state.battle['A'])
        self.assertEqual(runtime.matches_played, 0)
        runtime.verify()

    def test_actual_0017_unique_return_is_mandatory_and_uses_opponents_deck_bottom(self):
        runtime, command = self.actual(17)
        source = command['args']['hand_key']
        target = next(iter(runtime.state.battle['A']))
        original_deck = [card.key for card in runtime.state.zones['A']['deck']]
        choose_play(runtime, 'B', source, ROOT)
        self.assertEqual(aero.aero_choices(runtime, 'B', source, aero.PLAY_EFFECT), [target])
        pending = pending_options(runtime, 'B')[0]
        declined = copy.deepcopy(runtime)
        before = declined.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'AERO_TARGET_INVALID'):
            resolve_pending(declined, 'B', pending['id'], None)
        self.assertEqual(declined.snapshot(), before)
        result = resolve_pending(runtime, 'B', pending['id'], target)
        self.assertEqual(result['processing'], 'RETURNED_TO_DECK_BOTTOM')
        self.assertNotIn(target, runtime.state.battle['A'])
        self.assertEqual([card.key for card in runtime.state.zones['A']['deck']], [target] + original_deck)
        self.assertEqual(result['trashed_sources'], [])
        self.assertFalse(any(event.get('type') in ('DELETION', 'BATTLE') for event in runtime.events))
        runtime.verify()

    def test_actual_0045_preserves_both_explicit_return_choices(self):
        runtime, command = self.actual(45)
        source = command['args']['hand_key']
        targets = sorted(runtime.state.battle['A'])
        self.assertEqual(len(targets), 2)
        choose_play(runtime, 'B', source, ROOT)
        self.assertEqual(aero.aero_choices(runtime, 'B', source, aero.PLAY_EFFECT), targets)
        pending = pending_options(runtime, 'B')[0]
        for target in targets:
            branch = copy.deepcopy(runtime)
            result = resolve_pending(branch, 'B', pending['id'], target)
            self.assertEqual(result['target'], target)
            self.assertEqual(set(branch.state.battle['A']), set(targets) - {target})
            self.assertEqual(branch.state.zones['A']['deck'][0].key, target)
            branch.verify()

    def scenario(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        return ContextRuntime(context, 223, 'A', build_selected_registry(context, ROOT),
                              allow_experimental=True)

    def test_when_digivolving_return_trashes_sources_without_deletion(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        target = stage(runtime, 'B', ['EX1-013', 'P-138'])
        lower = runtime.state.battle['B'][target].cards[0].key
        result = runtime.dispatch(aero.DIGIVOLVE_EFFECT, 'A', source, target)
        self.assertEqual(result['trashed_sources'], [lower])
        self.assertEqual(runtime.state.zones['B']['trash'][-1].key, lower)
        self.assertEqual(runtime.state.zones['B']['deck'][0].key, target)
        self.assertEqual(runtime.state.pending, [])
        runtime.verify()

    def test_turn10_when_digivolving_return_uses_actual_fields_and_no_extra_events(self):
        runtime = self.scenario()
        source = stage(runtime, 'B', ['EX13-019', 'BT22-023'])
        target = stage(runtime, 'A', ['EX1-013', 'BT22-022'])
        egg = next(card for card in runtime.state.zones['A']['eggdeck']
                   if card.card_number == 'EX13-002')
        runtime.state.zones['A']['eggdeck'].remove(egg)
        runtime.state.battle['A'][target].cards.insert(0, egg)
        for number in ('BT11-112', 'BT11-112', 'EX13-069'):
            stage(runtime, 'A', [number])
        other = stage(runtime, 'B', ['BT22-022', 'EX13-023'])
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 10
        runtime.state.active = 'B'
        runtime.state.memory = -1
        queue_effects(runtime, [{'seat': 'B', 'source': source,
            'effect_id': aero.DIGIVOLVE_EFFECT, 'field': 'main_text',
            'trigger': {'kind': 'When Digivolving', 'previous_top': 'B:EX13-019#1'}}])
        lower = [card.key for card in runtime.state.battle['A'][target].cards[:-1]]
        before_other = copy.deepcopy(runtime.state.battle['B'][other])
        before_rng = runtime.snapshot()['rng_state']
        pending = pending_options(runtime, 'B')[0]
        self.assertEqual(pending['effect_id'], aero.DIGIVOLVE_EFFECT)
        result = resolve_pending(runtime, 'B', pending['id'], target)
        self.assertEqual(result['trashed_sources'], lower)
        self.assertEqual(runtime.state.zones['A']['deck'][0].key, target)
        self.assertEqual([card.key for card in runtime.state.zones['A']['trash'][-2:]], lower)
        self.assertNotIn(target, runtime.state.battle['A'])
        self.assertEqual(runtime.state.battle['B'][other], before_other)
        self.assertEqual(runtime.state.pending, [])
        self.assertEqual((runtime.state.active, runtime.state.turn, runtime.state.memory), ('B', 10, -1))
        self.assertEqual(runtime.state.phase, 'END_OF_TURN')
        self.assertEqual(runtime.snapshot()['rng_state'], before_rng)
        self.assertFalse(any(event.get('type') in ('DELETION', 'BATTLE') for event in runtime.events))
        runtime.verify()

    def test_active_leave_protection_halts_without_partial_return(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        target = stage(runtime, 'B', ['EX13-017', 'P-138'])
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'AERO_RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED.*EX13-017'):
            runtime.dispatch(aero.PLAY_EFFECT, 'A', source, target)
        self.assertEqual(runtime.snapshot(), before)

    def test_actual_0010_end_timing_has_explicit_decline_or_unchanged_self_choice(self):
        runtime, command = self.actual(10)
        source = command['args']['hand_key']
        choose_play(runtime, 'A', source, ROOT)
        resolve_pending(runtime, 'A', pending_options(runtime, 'A')[0]['id'], None)
        result = turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertTrue(result['end_processing_pending'])
        self.assertEqual((runtime.state.active, runtime.state.turn, runtime.state.memory), ('A', 1, -7))
        pending = pending_options(runtime, 'A')
        self.assertEqual([effect['effect_id'] for effect in pending], [aero.END_EFFECT])
        self.assertEqual(aero.aero_choices(runtime, 'A', source, aero.END_EFFECT), [None, source])
        for choice in (None, source):
            with self.subTest(choice=choice):
                branch = copy.deepcopy(runtime)
                result = resolve_pending(branch, 'A', pending[0]['id'], choice)
                self.assertFalse(result['changed'])
                self.assertEqual(branch.state.pending, [])
                self.assertEqual(branch.state.memory, -7)
                self.assertEqual(len(branch.state.once_used), 1)
                turn_flow.finish_turn(branch, 'A', ROOT)
                self.assertEqual((branch.state.active, branch.state.memory), ('B', 7))
                self.assertEqual(branch.state.pending, [])
                branch.verify()

    def test_pass_queues_end_effect_and_finish_cannot_duplicate_unresolved_choice(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        runtime.state.phase = 'MAIN'
        turn_flow.pass_turn(runtime, 'A', ROOT)
        pending = pending_options(runtime, 'A')
        self.assertEqual([effect['effect_id'] for effect in pending], [aero.END_EFFECT])
        self.assertEqual(pending[0]['instance'], runtime.state.battle['A'][source].instance_id)
        self.assertIn(pending[0]['instance'], pending[0]['usage'])
        blocked = copy.deepcopy(runtime)
        before = blocked.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            turn_flow.finish_turn(blocked, 'A', ROOT)
        self.assertEqual(blocked.snapshot(), before)
        resolve_pending(runtime, 'A', pending[0]['id'], None)
        turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertEqual(runtime.state.active, 'B')
        self.assertEqual(runtime.state.pending, [])

    def test_real_unsuspend_derives_memory_pending_before_turn_can_be_postponed(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        target = stage(runtime, 'A', ['P-138', 'EX13-023'], suspended=True)
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.memory = -1
        turn_flow.finish_turn(runtime, 'A', ROOT)
        resolve_pending(runtime, 'A', pending_options(runtime, 'A')[0]['id'], target)
        self.assertFalse(runtime.state.battle['A'][target].suspended)
        pending = pending_options(runtime, 'A')
        self.assertEqual([effect['effect_id'] for effect in pending], ['P-138.unsuspend_memory'])
        blocked = copy.deepcopy(runtime)
        with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            turn_flow.finish_turn(blocked, 'A', ROOT)
        resolve_pending(runtime, 'A', pending[0]['id'], None)
        result = turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertTrue(result['turn_postponed'])
        self.assertEqual((runtime.state.phase, runtime.state.active, runtime.state.memory), ('MAIN', 'A', 0))
        runtime.state.memory = -1
        runtime._finish_main_processing()
        turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertEqual((runtime.state.active, runtime.state.memory), ('B', 1))
        self.assertEqual(runtime.state.pending, [])

    def test_changed_unsuspend_queues_rina_optional_processing_before_end_can_finish(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        target = stage(runtime, 'A', ['EX1-013'], suspended=True)
        stage(runtime, 'A', ['EX13-069'])
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.memory = -1
        turn_flow.finish_turn(runtime, 'A', ROOT)
        resolve_pending(runtime, 'A', pending_options(runtime, 'A')[0]['id'], target)
        self.assertFalse(runtime.state.battle['A'][target].suspended)
        pending=pending_options(runtime,'A')
        self.assertEqual([effect['effect_id'] for effect in pending],['EX13-069.unsuspend_draw'])
        self.assertEqual(runtime.state.memory,-1)
        resolve_pending(runtime,'A',pending[0]['id'],False)
        self.assertEqual(runtime.state.pending,[])
        self.assertEqual(runtime.state.phase,'END_OF_TURN')

    def test_end_choices_include_own_blue_tamer_but_exclude_opponent(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        tamer = stage(runtime, 'A', ['BT22-085'])
        enemy = stage(runtime, 'B', ['EX1-013'])
        self.assertEqual(aero.aero_choices(runtime, 'A', source, aero.END_EFFECT),
                         [None] + sorted((source, tamer)))
        self.assertNotIn(enemy, aero.aero_choices(runtime, 'A', source, aero.END_EFFECT))
        result = runtime.dispatch(aero.END_EFFECT, 'A', source, tamer)
        self.assertFalse(result['changed'])
        self.assertEqual(runtime.state.pending, [])

    def test_return_choices_exclude_own_units_and_opponent_level_six(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        stage(runtime, 'A', ['P-138'])
        stage(runtime, 'B', ['BT12-029'])
        self.assertEqual(aero.aero_choices(runtime, 'A', source, aero.PLAY_EFFECT), [None])

    def test_return_does_not_trigger_other_units_self_leave_protection(self):
        runtime = self.scenario()
        source = stage(runtime, 'A', ['BT22-023'])
        target = stage(runtime, 'B', ['P-138'])
        other = stage(runtime, 'B', ['EX13-017', 'P-138'])
        result = runtime.dispatch(aero.PLAY_EFFECT, 'A', source, target)
        self.assertEqual(result['target'], target)
        self.assertIn(other, runtime.state.battle['B'])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
