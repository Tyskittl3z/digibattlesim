"""An encountered UlforceVeedramon unsuspend queues its printed return."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT


class UlforceUnsuspendReturnTests(unittest.TestCase):
    def test_saved_tamer_unsuspend_queues_return_with_scaled_level(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0005/segment-0000.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        source = 'A:BT11-032#1'
        self.assertTrue(runtime.state.battle['A'][source].suspended)
        resolve_pending(runtime, 'A', failed['args']['pending_id'], None)
        self.assertFalse(runtime.state.battle['A'][source].suspended)
        pending = [p for p in pending_options(runtime, 'A')
            if p['effect_id'] == 'BT11-032.unsuspend_return']
        self.assertEqual(len(pending), 1)
        choices = selected_pending_choices(runtime, 'A', pending[0])
        self.assertIn('B:EX13-022#1', choices)
        self.assertNotIn('B:BT11-112#4', choices)
        moved = resolve_pending(runtime, 'A', pending[0]['id'], 'B:EX13-022#1')
        self.assertEqual(moved['returned'], 'B:EX13-022#1')
        self.assertNotIn('B:EX13-022#1', runtime.state.battle['B'])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
