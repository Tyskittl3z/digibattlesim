"""Game 23's BT22-023 return offers EX13-017's owner the choice."""
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


class AeroReturnReplacementTests(unittest.TestCase):
    def test_saved_aero_return_offers_defender_replacement(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0023/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        target = 'A:P-138#1'
        result = resolve_pending(runtime, 'B', failed['args']['pending_id'], failed['args']['choice'])
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        offered = [p for p in pending_options(runtime, 'A')
                   if p['effect_id'] == REPLACEMENT_EFFECT]
        self.assertEqual(len(offered), 1)
        self.assertEqual(return_replacement_choices(runtime, 'A', offered[0]['source']), [False, True])
        decline = copy.deepcopy(runtime)
        no = resolve_pending(decline, 'A', offered[0]['id'], False)
        self.assertFalse(no['prevented_return'])
        self.assertNotIn(target, decline.state.battle['A'])
        self.assertEqual(decline.state.zones['A']['deck'][0].key, target)
        yes = resolve_pending(runtime, 'A', offered[0]['id'], True)
        self.assertTrue(yes['prevented_return'])
        self.assertTrue(runtime.state.battle['A'][target].suspended)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
