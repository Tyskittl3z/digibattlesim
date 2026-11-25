"""BT20-102's printed Blocker can enter the current block window."""
import unittest

from attack_flow import declare_attack, choose_counter, choose_blocker, confirm_attack
from context_runtime import ContextRuntime
from matchup_readiness import load_context_file
from named_bot_continuation import _plain_block_options
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class OmnimonBlockerTests(unittest.TestCase):
    def test_block_window_offers_and_accepts_printed_blocker(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 41, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        attacker = stage(runtime, 'A', ['BT11-023'])
        runtime.state.battle['A'][attacker].played_turn = 1
        blocker = stage(runtime, 'B', ['BT20-102'])
        declare_attack(runtime, 'A', attacker, 'PLAYER', ROOT)
        choose_counter(runtime, 'B', None, ROOT)
        self.assertIn({'card': blocker, 'status': 'READY_BLOCKER'}, _plain_block_options(runtime, 'B'))
        result = choose_blocker(runtime, 'B', blocker, ROOT)
        self.assertEqual(result['blocker'], blocker)
        self.assertEqual(runtime.state.attack['target'], blocker)
        self.assertTrue(runtime.state.battle['B'][blocker].suspended)
        battle = confirm_attack(runtime, 'A', ROOT)
        self.assertEqual(battle['battle_losers'], ['ATTACKER'])
        self.assertNotIn(attacker, runtime.state.battle['A'])
        self.assertIn(blocker, runtime.state.battle['B'])
        runtime.verify()
