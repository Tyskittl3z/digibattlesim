"""A checked P-104 places its Option without performing its main effect."""
import unittest

from attack_flow import declare_attack, choose_counter, choose_blocker, confirm_attack
from context_runtime import ContextRuntime
from selected_mechanics import build_selected_registry
from matchup_readiness import load_context_file
from test_selected_mechanics import ROOT, stage


class SecurityOptionTests(unittest.TestCase):
    def test_p104_check_places_option_without_main_search(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 104, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        attacker = stage(runtime, 'A', ['EX1-013'])
        runtime.state.battle['A'][attacker].played_turn = 1
        card = next(c for c in runtime.state.zones['B']['deck'] if c.card_number == 'P-104')
        runtime.state.zones['B']['deck'].remove(card)
        runtime.state.zones['B']['security'].append(card)
        declare_attack(runtime, 'A', attacker, 'PLAYER', ROOT)
        choose_counter(runtime, 'B', None, ROOT)
        choose_blocker(runtime, 'B', None, ROOT)
        before = runtime.snapshot()['state']
        result = confirm_attack(runtime, 'A', ROOT)
        self.assertEqual(result['checked_card'], card.key)
        self.assertEqual(result['security_effect'], 'P-104.security_place')
        self.assertIn(card.key, runtime.state.battle['B'])
        self.assertEqual(len(runtime.state.zones['B']['security']), len(before['zones']['B']['security']) - 1)
        self.assertEqual([c.key for c in runtime.state.zones['B']['deck']], before['zones']['B']['deck'])
        self.assertEqual(runtime.state.memory, before['memory'])
        self.assertFalse(runtime.state.pending)
        runtime.verify()
