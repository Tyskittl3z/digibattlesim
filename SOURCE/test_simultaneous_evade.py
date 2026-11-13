"""Game 28 tie battle offers turn player and opponent separate Evade choices."""
import copy
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


class SimultaneousEvadeTests(unittest.TestCase):
    def test_turn_player_then_defender_each_choose(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0028/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        attacker, defender = 'B:EX13-023#4', 'A:EX13-023#3'
        offered = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(offered['processing'], 'EVADE_CHOICE_PENDING')
        first = pending_options(runtime, 'B')
        self.assertEqual([p['effect_id'] for p in first], ['EX13-023.evade'])
        self.assertEqual(first[0]['source'], attacker)
        protected_first = copy.deepcopy(runtime)
        yes_first = resolve_pending(protected_first, 'B', first[0]['id'], True)
        self.assertTrue(yes_first['prevented_deletion'])
        self.assertTrue(protected_first.state.battle['B'][attacker].suspended)
        self.assertIn(defender, protected_first.state.battle['A'])
        self.assertTrue(any(p['effect_id'] == 'EX13-023.evade' and p['seat'] == 'A'
                            for p in protected_first.state.pending))
        no = resolve_pending(runtime, 'B', first[0]['id'], False)
        self.assertFalse(no['prevented_deletion'])
        self.assertIn(attacker, runtime.state.battle['B'])
        self.assertIn(defender, runtime.state.battle['A'])
        second = pending_options(runtime, 'A')
        self.assertEqual([p['effect_id'] for p in second], ['EX13-023.evade'])
        self.assertEqual(second[0]['source'], defender)
        both_decline = copy.deepcopy(runtime)
        resolve_pending(both_decline, 'A', second[0]['id'], False)
        self.assertNotIn(attacker, both_decline.state.battle['B'])
        self.assertNotIn(defender, both_decline.state.battle['A'])
        yes = resolve_pending(runtime, 'A', second[0]['id'], True)
        self.assertTrue(yes['prevented_deletion'])
        self.assertNotIn(attacker, runtime.state.battle['B'])
        self.assertIn(defender, runtime.state.battle['A'])
        self.assertTrue(runtime.state.battle['A'][defender].suspended)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
