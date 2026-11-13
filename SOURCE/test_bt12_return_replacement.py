"""The saved BT12-029 return offers EX13-017's defender replacement choice."""
import copy
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from return_effects import REPLACEMENT_EFFECT, return_replacement_choices
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class Bt12ReturnReplacementTests(unittest.TestCase):
    def test_saved_return_offers_suspend_or_return_choice(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0011/segment-0002.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        result = resolve_pending(runtime, 'A', failed['args']['pending_id'], failed['args']['choice'])
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        target = 'B:P-138#2'
        self.assertIn(target, runtime.state.battle['B'])
        replacement = [p for p in pending_options(runtime, 'B') if p['effect_id'] == REPLACEMENT_EFFECT]
        self.assertEqual(len(replacement), 1)
        self.assertEqual(return_replacement_choices(runtime, 'B', replacement[0]['source']), [False, True])
        returned = copy.deepcopy(runtime)
        decline = resolve_pending(returned, 'B', replacement[0]['id'], False)
        self.assertFalse(decline['prevented_return'])
        self.assertIn(target, [c.key for c in returned.state.zones['B']['hand']])
        self.assertNotIn(target, returned.state.battle['B'])
        protected = resolve_pending(runtime, 'B', replacement[0]['id'], True)
        self.assertTrue(protected['prevented_return'])
        self.assertTrue(runtime.state.battle['B'][target].suspended)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
