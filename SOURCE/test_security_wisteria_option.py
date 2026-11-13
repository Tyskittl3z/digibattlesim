"""The encountered LM-034 Security text places its Option on the field."""
import gzip
import json
import unittest

from attack_flow import confirm_attack
from context_runtime import ContextRuntime
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class WisteriaSecurityTests(unittest.TestCase):
    def test_recorded_security_check_places_lm034_without_main_search(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0000/segment-0000.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        before = runtime.snapshot()['state']
        result = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(result['checked_card'], 'A:LM-034#1')
        self.assertEqual(result['security_effect'], 'LM-034.security_place')
        self.assertIn('A:LM-034#1', runtime.state.battle['A'])
        self.assertEqual(runtime.state.attack['window'], 'END')
        self.assertEqual(len(runtime.state.zones['A']['security']),
                         len(before['zones']['A']['security']) - 1)
        self.assertEqual([c.key for c in runtime.state.zones['A']['deck']],
                         before['zones']['A']['deck'])
        self.assertEqual(runtime.state.memory, before['memory'])
        self.assertFalse(runtime.state.pending)
        self.assertIsNone(runtime.state.resolving_option)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
