"""Game 37's EX13-023 return meets two inherited leave replacements."""
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


class UlforceDoubleReplacementTests(unittest.TestCase):
    def test_saved_single_target_return_offers_both_printed_replacements(self):
        path = ROOT / 'ARTIFACTS/ulforce-prospective-60-2026-11-17/game-0037/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])

        result = resolve_pending(runtime, failed['seat'], failed['args']['pending_id'],
                                 failed['args']['choice'])
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        offered = pending_options(runtime, 'A')
        self.assertEqual({effect['effect_id'] for effect in offered},
                         {REPLACEMENT_EFFECT, BT22_REPLACEMENT_EFFECT})
        chosen = next(effect for effect in offered
                      if effect['effect_id'] == BT22_REPLACEMENT_EFFECT)
        protected = resolve_pending(runtime, 'A', chosen['id'], True)
        self.assertTrue(protected['prevented_return'])
        self.assertTrue(runtime.state.battle['A']['A:EX13-023#1'].suspended)
        self.assertEqual(pending_options(runtime, 'A'), [])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
