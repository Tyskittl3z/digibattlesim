"""The EX13-019 inherited Jamming encountered in Game 0000."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_grants import active_keyword
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class InheritedJammingTests(unittest.TestCase):
    def test_saved_digimon_battle_ignores_defenders_security_only_jamming(self):
        path = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0019.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        saved = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], saved['before']['state'])
        defender = runtime.state.attack['target']
        self.assertTrue(active_keyword(runtime, 'B', defender, 'Jamming'))
        result = _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(result['battle_losers'], ['ATTACKER'])
        self.assertIn(defender, runtime.state.battle['B'])
        self.assertNotIn('A:BT22-023#1', runtime.state.battle['A'])


if __name__ == '__main__':
    unittest.main()
