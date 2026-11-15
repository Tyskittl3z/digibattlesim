"""The saved Game 12 Security battle offers the printed Evade choice."""
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


class EncounteredEvadeTests(unittest.TestCase):
    def test_saved_security_battle_offers_both_evade_outcomes(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0012/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        attacker = runtime.state.attack['attacker']
        security_before = len(runtime.state.zones['B']['security'])
        offered = confirm_attack(runtime, 'A', ROOT)
        self.assertEqual(offered['processing'], 'EVADE_CHOICE_PENDING')
        self.assertEqual(len(runtime.state.zones['B']['security']), security_before)
        pending = [p for p in pending_options(runtime, 'A')
                   if p['effect_id'] == 'EX13-023.evade']
        self.assertEqual(len(pending), 1)
        declined = copy.deepcopy(runtime)
        result = resolve_pending(declined, 'A', pending[0]['id'], False)
        self.assertFalse(result['prevented_deletion'])
        self.assertNotIn(attacker, declined.state.battle['A'])
        self.assertEqual(len(declined.state.zones['B']['security']), security_before - 1)
        kept = resolve_pending(runtime, 'A', pending[0]['id'], True)
        self.assertTrue(kept['prevented_deletion'])
        self.assertIn(attacker, runtime.state.battle['A'])
        self.assertTrue(runtime.state.battle['A'][attacker].suspended)
        self.assertEqual(len(runtime.state.zones['B']['security']), security_before - 1)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
