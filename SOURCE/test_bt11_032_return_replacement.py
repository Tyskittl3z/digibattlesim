"""Game 12's live BT11-032 return offers the EX13-017 leave replacement."""
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


class Bt11ReturnReplacementTests(unittest.TestCase):
    def test_saved_return_offers_both_replacement_outcomes(self):
        path = (ROOT / 'ARTIFACTS/ulforce-prospective-60-2026-11-17/'
                'game-0012/segment-0000.json.gz')
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        target = failed['args']['choice']
        result = resolve_pending(runtime, 'A', failed['args']['pending_id'], target)
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        self.assertIn(target, runtime.state.battle['B'])
        replacement = [p for p in pending_options(runtime, 'B')
                       if p['effect_id'] == REPLACEMENT_EFFECT]
        self.assertEqual(len(replacement), 1)
        self.assertEqual(return_replacement_choices(runtime, 'B', replacement[0]['source']),
                         [False, True])
        declined = copy.deepcopy(runtime)
        moved = resolve_pending(declined, 'B', replacement[0]['id'], False)
        self.assertFalse(moved['prevented_return'])
        self.assertNotIn(target, declined.state.battle['B'])
        self.assertIn(target, [card.key for card in declined.state.zones['B']['hand']])
        protected = resolve_pending(runtime, 'B', replacement[0]['id'], True)
        self.assertTrue(protected['prevented_return'])
        self.assertTrue(runtime.state.battle['B'][target].suspended)
        declined.verify();runtime.verify()


if __name__ == '__main__':
    unittest.main()
