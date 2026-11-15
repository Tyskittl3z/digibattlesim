"""An attacking EX13-019 may play an eligible Tamer for 2 less memory."""
import unittest

from attack_flow import declare_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _load_context_selection
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class EX13019AttackTamerTests(unittest.TestCase):
    def test_attack_offers_optional_reduced_cost_tamer_play(self):
        context, _, _ = _load_context_selection(
            ROOT, 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 13019, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        attacker = stage(runtime, 'A', ['EX13-019'])
        runtime.state.battle['A'][attacker].played_turn = 1
        runtime.state.battle['A'][attacker].ready_since_turn = 2
        card = next(card for card in runtime.state.zones['A']['deck']
                    if card.card_number == 'BT11-112')
        runtime.state.zones['A']['deck'].remove(card)
        runtime.state.zones['A']['hand'].append(card)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        runtime.state.memory = 5

        declare_attack(runtime, 'A', attacker, 'PLAYER', ROOT)
        effect = next(item for item in pending_options(runtime, 'A')
                      if item['effect_id'] == 'EX13-019.attack_play_tamer')
        self.assertEqual(effect['trigger']['attacker'], attacker)
        result = resolve_pending(runtime, 'A', effect['id'], card.key)
        self.assertEqual((result['play']['cost'], runtime.state.memory), (1, 4))
        self.assertIn(card.key, runtime.state.battle['A'])
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        self.assertTrue(any(item['effect_id'] == 'BT11-112.on_play_grant'
                            for item in pending_options(runtime, 'A')))
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
