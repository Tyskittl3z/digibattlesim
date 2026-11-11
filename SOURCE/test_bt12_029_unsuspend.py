"""Game 0000's encountered BT12-029 evolution choice."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class BT12UnsuspendTests(unittest.TestCase):
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
