"""Game 25's BT20-102 return meets two inherited leave replacements."""
import copy
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from return_effects import BT22_REPLACEMENT_EFFECT, REPLACEMENT_EFFECT
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class MultipleReturnReplacementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'ARTIFACTS/ulforce-prospective-60-2026-11-17/game-0025/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            cls.record = json.load(handle)
        context = load_context_file(ROOT / cls.record['context_file'])
        cls.runtime = ContextRuntime(context, cls.record['seed'], cls.record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in cls.record['commands'][:-1]:
            _apply(cls.runtime, command['command'], command['seat'], command['args'], ROOT)
        assert cls.runtime.snapshot()['state'] == cls.record['commands'][-1]['before']['state']

    def start_return(self):
        runtime = copy.deepcopy(self.runtime)
        failed = self.record['commands'][-1]
        result = resolve_pending(runtime, failed['seat'], failed['args']['pending_id'],
                                 failed['args']['choice'])
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        offered = pending_options(runtime, 'A')
        self.assertEqual({effect['effect_id'] for effect in offered},
                         {REPLACEMENT_EFFECT, BT22_REPLACEMENT_EFFECT})
        return runtime, {effect['effect_id']: effect for effect in offered}

    def test_paying_either_replacement_prevents_return_and_cancels_the_other(self):
        for effect_id in (REPLACEMENT_EFFECT, BT22_REPLACEMENT_EFFECT):
            with self.subTest(effect_id=effect_id):
                runtime, offered = self.start_return()
                result = resolve_pending(runtime, 'A', offered[effect_id]['id'], True)
                self.assertTrue(result['prevented_return'])
                self.assertTrue(runtime.state.battle['A']['A:BT12-029#2'].suspended)
                self.assertEqual(pending_options(runtime, 'A'), [])
                runtime.verify()

    def test_declining_first_offers_second_and_second_decline_returns(self):
        runtime, offered = self.start_return()
        first = resolve_pending(runtime, 'A', offered[REPLACEMENT_EFFECT]['id'], False)
        self.assertFalse(first['prevented_return'])
        self.assertIn('A:BT12-029#2', runtime.state.battle['A'])
        remaining = pending_options(runtime, 'A')
        self.assertEqual([effect['effect_id'] for effect in remaining],
                         [BT22_REPLACEMENT_EFFECT])
        last = resolve_pending(runtime, 'A', remaining[0]['id'], False)
        self.assertFalse(last['prevented_return'])
        self.assertNotIn('A:BT12-029#2', runtime.state.battle['A'])
        self.assertEqual(runtime.state.zones['A']['deck'][0].key, 'A:BT12-029#2')
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
