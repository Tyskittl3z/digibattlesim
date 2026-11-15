"""Game 0000's encountered printed Blocker/Evade attack declaration."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_grants import active_keyword
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, ORIENTATION_EFFECT
from test_selected_mechanics import ROOT


class PrintedKeywordAttackTests(unittest.TestCase):
    def test_saved_ex13_023_player_attack_has_legal_keyword_scope(self):
        path = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0012.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        saved = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], saved['before']['state'])
        attacker = saved['args']['attacker']
        self.assertTrue(active_keyword(runtime, 'A', attacker, 'Blocker'))
        self.assertTrue(active_keyword(runtime, 'A', attacker, 'Evade'))
        result = _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(result['target'], 'PLAYER')
        self.assertEqual(runtime.state.attack['attacker'], attacker)
        self.assertTrue(runtime.state.battle['A'][attacker].suspended)
        self.assertIn(ORIENTATION_EFFECT, [p['effect_id'] for p in runtime.state.pending])


if __name__ == '__main__':
    unittest.main()
