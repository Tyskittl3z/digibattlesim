"""The encountered EX13-017 inherited replacement on an opposing return."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class ReturnReplacementTests(unittest.TestCase):
    def recorded(self):
        with gzip.open(ROOT / 'ARTIFACTS/fresh-game-0001-board-text-2026-11-11/segment-0007.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        return runtime

    def test_recorded_return_offers_defender_suspend_choice(self):
        runtime = self.recorded()
        target = 'B:EX13-023#4'
        self.assertFalse(runtime.state.battle['B'][target].suspended)
        pending = pending_options(runtime, 'A')
        result = resolve_pending(runtime, 'A', pending[0]['id'], True)
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        self.assertIn(target, runtime.state.battle['B'])
        defender = pending_options(runtime, 'B')
        self.assertEqual(len(defender), 1)
        self.assertEqual(defender[0]['source'], 'B:EX13-017#3')
        protected = resolve_pending(runtime, 'B', defender[0]['id'], True)
        self.assertTrue(protected['prevented_return'])
        self.assertIn(target, runtime.state.battle['B'])
        self.assertTrue(runtime.state.battle['B'][target].suspended)
        runtime.verify()

    def test_declined_replacement_allows_direct_return_under_q7265(self):
        runtime = self.recorded()
        target = 'B:EX13-023#4'
        pending = pending_options(runtime, 'A')
        resolve_pending(runtime, 'A', pending[0]['id'], True)
        defender = pending_options(runtime, 'B')
        result = resolve_pending(runtime, 'B', defender[0]['id'], False)
        self.assertFalse(result['prevented_return'])
        self.assertNotIn(target, runtime.state.battle['B'])
        self.assertEqual(runtime.state.zones['B']['deck'][0].key, target)
        runtime.verify()
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
