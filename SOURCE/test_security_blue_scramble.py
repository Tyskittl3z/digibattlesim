"""LM-028 Security gives the defender a trash-play choice, then returns to hand."""
import copy
import gzip
import json
import unittest

from attack_flow import confirm_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT


class BlueScrambleSecurityTests(unittest.TestCase):
    def test_recorded_check_offers_blue_small_trash_card_and_adds_option_to_hand(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0006/segment-0000.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        before = runtime.snapshot()['state']
        checked = confirm_attack(runtime, 'A', ROOT)
        self.assertEqual(checked['checked_card'], 'B:LM-028#1')
        self.assertEqual(runtime.state.attack['window'], 'END')
        pending = [p for p in pending_options(runtime, 'B')
            if p['effect_id'] == 'LM-028.security_play_trash']
        self.assertEqual(len(pending), 1)
        choices = selected_pending_choices(runtime, 'B', pending[0])
        self.assertIn(None, choices)
        self.assertIn('B:EX1-013#3', choices)
        self.assertNotIn('B:EX13-023#2', choices)
        self.assertNotIn('B:EX13-002#2', choices)
        declined = copy.deepcopy(runtime)
        decline = resolve_pending(declined, 'B', pending[0]['id'], None)
        self.assertIsNone(decline['played_card'])
        self.assertIn('B:LM-028#1', [c.key for c in declined.state.zones['B']['hand']])
        self.assertFalse(declined.state.battle['B'])
        with_trigger = copy.deepcopy(runtime)
        other = resolve_pending(with_trigger, 'B', pending[0]['id'], 'B:EX13-017#1')
        self.assertEqual(other['played_card'], 'B:EX13-017#1')
        self.assertIn('B:LM-028#1', [c.key for c in with_trigger.state.zones['B']['hand']])
        self.assertTrue(any(p['effect_id'] == 'EX13-017.on_play_search'
            for p in pending_options(with_trigger, 'B')))
        result = resolve_pending(runtime, 'B', pending[0]['id'], 'B:EX1-013#3')
        self.assertEqual(result['played_card'], 'B:EX1-013#3')
        self.assertIn('B:EX1-013#3', runtime.state.battle['B'])
        self.assertIn('B:LM-028#1', [c.key for c in runtime.state.zones['B']['hand']])
        self.assertEqual(runtime.state.memory, before['memory'])
        self.assertEqual(len(runtime.state.zones['B']['security']), len(before['zones']['B']['security']) - 1)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
