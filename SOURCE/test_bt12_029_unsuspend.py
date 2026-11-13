"""Game 0000's encountered BT12-029 evolution choice."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class BT12UnsuspendTests(unittest.TestCase):
    def test_rina_reactivation_can_resolve_bt12_unsuspend_on_opponents_turn(self):
        from effect_scheduler import queue_effects
        from rina_reactivation import collect_rina_suspension_reactions
        from selected_mechanics import BT12_UNSUSPEND_EFFECT, bt12_unsuspend_choices
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 12129, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        digimon = stage(runtime, 'B', ['BT12-029'], suspended=True)
        tamer = stage(runtime, 'B', ['BT11-112'])
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        queue_effects(runtime, collect_rina_suspension_reactions(
            runtime, 'B', runtime.state.battle['B'][digimon], False))
        rina = pending_options(runtime, 'B')[0]
        resolve_pending(runtime, 'B', rina['id'], BT12_UNSUSPEND_EFFECT)
        selected = pending_options(runtime, 'B')[0]
        self.assertEqual(selected['trigger']['kind'], 'RINA_REACTIVATED_WHEN_DIGIVOLVING')
        self.assertIn(tamer, bt12_unsuspend_choices(runtime, 'B', digimon))
        result = resolve_pending(runtime, 'B', selected['id'], tamer)
        self.assertTrue(result['changed'])
        self.assertFalse(runtime.state.battle['B'][tamer].suspended)
        runtime.verify()

    def test_self_unsuspend_returns_lowest_level_opponent_to_hand(self):
        from effect_scheduler import queue_effects
        from rina_reactivation import collect_rina_suspension_reactions
        from selected_mechanics import BT12_UNSUSPEND_EFFECT
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 12130, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        target = stage(runtime, 'A', ['BT11-023', 'EX13-019'])
        source_card = runtime.state.battle['A'][target].cards[0].key
        source = stage(runtime, 'B', ['BT12-029'], suspended=True)
        stage(runtime, 'B', ['BT11-112'])
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        queue_effects(runtime, collect_rina_suspension_reactions(
            runtime, 'B', runtime.state.battle['B'][source], False))
        selected = pending_options(runtime, 'B')[0]
        resolve_pending(runtime, 'B', selected['id'], BT12_UNSUSPEND_EFFECT)
        selected = pending_options(runtime, 'B')[0]
        resolve_pending(runtime, 'B', selected['id'], source)
        returning = next(item for item in pending_options(runtime, 'B')
                         if item['effect_id'] == 'BT12-029.unsuspend_return_lowest')
        result = resolve_pending(runtime, 'B', returning['id'], target)
        self.assertEqual(result['returned'], target)
        self.assertNotIn(target, runtime.state.battle['A'])
        self.assertIn(target, [card.key for card in runtime.state.zones['A']['hand']])
        self.assertIn(source_card, [card.key for card in runtime.state.zones['A']['trash']])
        runtime.verify()

    def test_saved_evolution_queues_printed_choice_and_preserves_memory_cost(self):
        from selected_mechanics import BT12_UNSUSPEND_EFFECT, bt12_unsuspend_choices
        path = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0021.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        saved = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], saved['before']['state'])
        result = _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(result['hand_key'], 'B:BT12-029#1')
        self.assertEqual(runtime.state.memory, 2)
        selected = next(p for p in pending_options(runtime, 'B')
                        if p['effect_id'] == BT12_UNSUSPEND_EFFECT)
        offered = bt12_unsuspend_choices(runtime, 'B', selected['source'])
        self.assertIn('B:BT12-029#1', offered)
        self.assertIn('B:BT22-085#2', offered)
        self.assertNotIn('B:EX13-069#1', offered)
        outcome = resolve_pending(runtime, 'B', selected['id'], 'B:BT22-085#2')
        self.assertEqual(outcome['target'], 'B:BT22-085#2')
        self.assertFalse(outcome['changed'])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
