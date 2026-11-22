"""A checked LM-034 places its Option without performing its main effect."""
import unittest

from attack_flow import declare_attack, choose_counter, choose_blocker, confirm_attack
from context_runtime import ContextRuntime
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, selected_context, stage


class SecurityOptionTests(unittest.TestCase):
    def test_lm034_check_places_option_without_main_search(self):
        context = selected_context()
        runtime = ContextRuntime(context, 104, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        attacker = stage(runtime, 'B', ['ST7-05'])
        runtime.state.battle['B'][attacker].played_turn = 1
        card = next(c for c in runtime.state.zones['A']['deck'] if c.card_number == 'LM-034')
        runtime.state.zones['A']['deck'].remove(card)
        runtime.state.zones['A']['security'].append(card)
        declare_attack(runtime, 'B', attacker, 'PLAYER', ROOT)
        choose_counter(runtime, 'A', None, ROOT)
        choose_blocker(runtime, 'A', None, ROOT)
        before = runtime.snapshot()['state']
        result = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(result['checked_card'], card.key)
        self.assertEqual(result['security_effect'], 'LM-034.security_place')
        self.assertIn(card.key, runtime.state.battle['A'])
        self.assertEqual(len(runtime.state.zones['A']['security']), len(before['zones']['A']['security']) - 1)
        self.assertEqual([c.key for c in runtime.state.zones['A']['deck']], before['zones']['A']['deck'])
        self.assertEqual(runtime.state.memory, before['memory'])
        self.assertFalse(runtime.state.pending)
        runtime.verify()
