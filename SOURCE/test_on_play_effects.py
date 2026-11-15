"""Regressions from actually encountered plays, not a route inventory."""
import copy
import gzip
import json
from pathlib import Path
import unittest

from context_runtime import ContextRuntime, RuntimeHalt, Stack
from effect_scheduler import pending_options, resolve_pending
from main_actions import choose_play
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'


class EncounteredOnPlayTests(unittest.TestCase):
    def runtime(self):
        context = load_context_file(ROOT / CONTEXT)
        runtime = ContextRuntime(context, 25, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'; runtime.state.turn = 1; runtime.state.memory = 10
        return runtime

    def take(self, runtime, seat, number, battle=False):
        zone = runtime.state.zones[seat]['deck']
        card = next(c for c in zone if c.card_number == number)
        zone.remove(card)
        if battle:
            runtime.state.entity_sequence += 1
            runtime.state.battle[seat][card.key] = Stack(
                [card], instance_id='entity-' + str(runtime.state.entity_sequence),
                played_turn=0, ready_since_turn=1)
        else:
            runtime.state.zones[seat]['hand'].append(card)
        return card.key

    def play(self, runtime, key):
        try:
            return choose_play(runtime, 'A', key, ROOT)
        except RuntimeHalt as exc:
            self.fail('Encountered legal ordinary play should resolve: ' + str(exc))

    def test_recorded_first_rina_play_with_no_targets_resolves_then_passes_turn(self):
        from imported_attempts import _apply
        from turn_flow import finish_turn
        record = json.loads(gzip.decompress((ROOT / 'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0000.json.gz').read_bytes()))
        context = load_context_file(ROOT / CONTEXT)
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        expected=copy.deepcopy(record['halts'][-1]['before']['state'])
        expected.setdefault('resolving_option',None)
        self.assertEqual(runtime.snapshot()['state'], expected)
        key = record['commands'][-1]['args']['hand_key']
        self.play(runtime, key)
        self.assertEqual(runtime.state.memory, -3)
        self.assertEqual(runtime.state.phase, 'MAIN', 'Pending On Play finishes before turn change')
        pending = pending_options(runtime, 'A')
        self.assertEqual(len(pending), 1)
        result = resolve_pending(runtime, 'A', pending[0]['id'], None)
        self.assertEqual(result['processing'], 'NO_ELIGIBLE_TARGET')
        self.assertEqual(runtime.state.battle['A'][key].statuses, {})
        self.assertEqual(runtime.state.phase, 'END_OF_TURN')
        finish_turn(runtime, 'A', ROOT)
        self.assertEqual((runtime.state.active, runtime.state.memory), ('B', 3))
        runtime.verify()

    def test_rina_has_explicit_target_when_a_qualifying_digimon_exists(self):
        from on_play_effects import on_play_choices
        from effect_grants import active_keyword
        runtime = self.runtime()
        target = self.take(runtime, 'A', 'EX1-013', battle=True)
        self.take(runtime, 'B', 'EX1-013', battle=True)
        source = self.take(runtime, 'A', 'BT11-112')
        self.play(runtime, source)
        self.assertEqual(on_play_choices(runtime, 'A', source), [target])
        pending = pending_options(runtime, 'A')[0]
        resolve_pending(runtime, 'A', pending['id'], target)
        self.assertTrue(active_keyword(runtime, 'A', target, 'Blocker'))
        self.assertTrue(active_keyword(runtime, 'A', target, 'Evade'))
        runtime.verify()

    def test_mandatory_available_target_cannot_be_silently_declined(self):
        runtime = self.runtime()
        self.take(runtime, 'A', 'EX1-013', battle=True)
        source = self.take(runtime, 'A', 'BT11-112')
        self.play(runtime, source)
        pending = pending_options(runtime, 'A')[0]
        before = copy.deepcopy(runtime.snapshot()['state'])
        with self.assertRaisesRegex(RuntimeHalt, 'ON_PLAY_TARGET_INVALID'):
            resolve_pending(runtime, 'A', pending['id'], None)
        self.assertEqual(runtime.snapshot()['state'], before)

    def test_granted_rina_remains_compatible_with_later_unrelated_play(self):
        runtime = self.runtime()
        target = self.take(runtime, 'A', 'EX1-013', battle=True)
        source = self.take(runtime, 'A', 'BT11-112')
        self.play(runtime, source)
        resolve_pending(runtime, 'A', pending_options(runtime, 'A')[0]['id'], target)
        next_card = self.take(runtime, 'A', 'BT11-023')
        self.play(runtime, next_card)
        self.assertEqual(pending_options(runtime, 'A')[0]['effect_id'], 'BT11-023.on_play_search')
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
