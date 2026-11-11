"""LM-056's encountered printed Security search and placement."""
import gzip
import json
import unittest

from attack_flow import confirm_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class SecurityTrainingOptionTests(unittest.TestCase):
    def test_recorded_lm056_check_reveals_selects_and_places(self):
        with gzip.open(ROOT / 'ARTIFACTS/fresh-game-0001-board-text-2026-11-11/segment-0002.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        self.assertEqual(runtime.snapshot()['rng_state'], record['commands'][-1]['before']['rng_state'])
        before = runtime.snapshot()
        result = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(result['checked_card'], 'A:LM-056#1')
        self.assertEqual(runtime.state.attack['window'], 'END')
        self.assertEqual(len(runtime.state.zones['A']['security']), len(before['state']['zones']['A']['security']) - 1)
        self.assertEqual(runtime.state.resolving_option['stack'].cards[0].key, 'A:LM-056#1')
        pending = pending_options(runtime, 'A')
        self.assertEqual(len(pending), 1)
        from option_actions import security_option_choices
        choices = security_option_choices(runtime, 'A', 'A:LM-056#1')
        self.assertEqual(set(map(tuple, choices['selections'])),
                         {('A:P-104#1',), ('A:LM-034#1',)})
        selected = choices['selections'][0]
        remainder = [key for key in choices['revealed'] if key not in selected]
        resolve_pending(runtime, 'A', pending[0]['id'],
                        {'selected': selected, 'bottom_order': remainder})
        self.assertIn('A:LM-056#1', runtime.state.battle['A'])
        self.assertIsNone(runtime.state.resolving_option)
        self.assertIn(selected[0], [card.key for card in runtime.state.zones['A']['hand']])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
