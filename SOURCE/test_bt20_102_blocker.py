"""The printed BT20-102 Blocker is a legal current defensive choice."""
import gzip
import json
import unittest

from attack_flow import choose_blocker, confirm_attack
from context_runtime import ContextRuntime
from imported_attempts import _apply
from matchup_readiness import load_context_file
from named_bot_continuation import _plain_block_options
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class OmnimonBlockerTests(unittest.TestCase):
    def test_saved_block_window_offers_and_accepts_printed_blocker(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0004/segment-0002.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        choices = _plain_block_options(runtime, 'B')
        blocker = 'B:BT20-102#1'
        self.assertIn({'card': blocker, 'status': 'READY_BLOCKER'}, choices)
        result = choose_blocker(runtime, 'B', blocker, ROOT)
        self.assertEqual(result['blocker'], blocker)
        self.assertEqual(runtime.state.attack['target'], blocker)
        self.assertTrue(runtime.state.battle['B'][blocker].suspended)
        battle = confirm_attack(runtime, 'A', ROOT)
        self.assertEqual(battle['battle_losers'], ['ATTACKER'])
        self.assertNotIn('A:BT11-023#4', runtime.state.battle['A'])
        self.assertIn(blocker, runtime.state.battle['B'])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
