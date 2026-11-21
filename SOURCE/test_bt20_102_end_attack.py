"""The Omnimon end-turn effect is chosen and attacks explicitly."""
import unittest

from attack_flow import choose_blocker, choose_counter, confirm_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT,stage
from turn_flow import finish_turn


class OmnimonEndAttackTests(unittest.TestCase):
    def test_end_turn_trigger_offers_choice_and_can_win_after_raid_decline(self):
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 18, 'B',
            build_selected_registry(context, ROOT), allow_experimental=True)
        runtime.state.phase='END_OF_TURN';runtime.state.turn=3;runtime.state.memory=-1
        attacker=stage(runtime,'B',['BT20-102'],suspended=True)
        runtime.state.battle['B'][attacker].played_turn=1
        runtime.state.battle['B'][attacker].ready_since_turn=2
        result = finish_turn(runtime, 'B', ROOT)
        self.assertTrue(result['end_processing_pending'])
        pending = pending_options(runtime, 'B')
        self.assertEqual(len(pending), 1)
        choices = selected_pending_choices(runtime, 'B', pending[0])
        attack = {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': 'PLAYER'}
        self.assertIn(None, choices)
        self.assertIn(attack, choices)
        self.assertTrue(runtime.state.battle['B'][attack['attacker']].suspended)
        resolved = resolve_pending(runtime, 'B', pending[0]['id'], attack)
        self.assertEqual(resolved['attacker'], attack['attacker'])
        self.assertTrue(runtime.state.battle['B'][attack['attacker']].suspended)
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        raid=pending_options(runtime,'B')
        self.assertEqual([item['effect_id'] for item in raid],['BT20-102.raid_target'])
        resolve_pending(runtime,'B',raid[0]['id'],None)
        choose_counter(runtime, 'A', None, ROOT)
        choose_blocker(runtime, 'A', None, ROOT)
        won = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(won['winner'], 'B')
        self.assertTrue(runtime.state.terminal)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
