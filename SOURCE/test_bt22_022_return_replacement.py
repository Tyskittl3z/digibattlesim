"""Saved Game 22 offers BT22-022's inherited leave replacement to its owner."""
import copy
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from return_effects import BT22_REPLACEMENT_EFFECT, return_replacement_choices
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class Bt22ReplacementTests(unittest.TestCase):
    def test_saved_return_offers_defender_suspend_or_deck_return(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0022/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        target = 'A:BT12-029#2'
        result = resolve_pending(runtime, 'B', failed['args']['pending_id'], True)
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        self.assertIn(target, runtime.state.battle['A'])
        offered = [p for p in pending_options(runtime, 'A')
                   if p['effect_id'] == BT22_REPLACEMENT_EFFECT]
        self.assertEqual(len(offered), 1)
        self.assertEqual(return_replacement_choices(runtime, 'A', offered[0]['source']), [False, True])
        declined = copy.deepcopy(runtime)
        no = resolve_pending(declined, 'A', offered[0]['id'], False)
        self.assertFalse(no['prevented_return'])
        self.assertNotIn(target, declined.state.battle['A'])
        self.assertEqual(declined.state.zones['A']['deck'][0].key, target)
        yes = resolve_pending(runtime, 'A', offered[0]['id'], True)
        self.assertTrue(yes['prevented_return'])
        self.assertTrue(runtime.state.battle['A'][target].suspended)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
