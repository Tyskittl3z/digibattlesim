"""The encountered Omnimon end-turn effect is chosen and attacks explicitly."""
import gzip
import json
import unittest

from attack_flow import choose_blocker, choose_counter, confirm_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT
from turn_flow import finish_turn


class OmnimonEndAttackTests(unittest.TestCase):
    def test_saved_end_turn_trigger_offers_choice_and_can_win(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0001/segment-0002.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        result = finish_turn(runtime, 'B', ROOT)
        self.assertTrue(result['end_processing_pending'])
        pending = pending_options(runtime, 'B')
        self.assertEqual(len(pending), 1)
        choices = selected_pending_choices(runtime, 'B', pending[0])
        attack = {'kind': 'DECLARE_ATTACK', 'attacker': 'B:BT20-102#1', 'target': 'PLAYER'}
        self.assertIn(None, choices)
        self.assertIn(attack, choices)
        self.assertTrue(runtime.state.battle['B'][attack['attacker']].suspended)
        resolved = resolve_pending(runtime, 'B', pending[0]['id'], attack)
        self.assertEqual(resolved['attacker'], attack['attacker'])
        self.assertTrue(runtime.state.battle['B'][attack['attacker']].suspended)
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        choose_counter(runtime, 'A', None, ROOT)
        choose_blocker(runtime, 'A', None, ROOT)
        won = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(won['winner'], 'B')
        self.assertTrue(runtime.state.terminal)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
