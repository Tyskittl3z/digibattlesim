"""The encountered Omnimon (X Antibody) condition has no eligible source."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class OmnimonConditionalDigivolveTests(unittest.TestCase):
    def test_saved_digivolution_skips_unmet_if_clause(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0001/segment-0000.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        source = runtime.state.battle['B']['B:EX13-023#2']
        self.assertFalse(any('Omnimon' in context.card('B', p.card_number).name
            or 'X Antibody' in context.card('B', p.card_number).name for p in source.cards))
        result = _apply(runtime, failed['command'], failed['seat'], failed['args'], ROOT)
        self.assertEqual(result['triggered_effects'], [])
        self.assertIn('B:BT20-102#1', runtime.state.battle['B'])
        self.assertEqual(runtime.state.battle['A'], {})
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
