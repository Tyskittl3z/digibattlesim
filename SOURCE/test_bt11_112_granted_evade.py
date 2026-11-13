"""The saved Game 12 battle uses Evade granted by BT11-112's printed text."""
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


class GrantedEvadeTests(unittest.TestCase):
    def test_saved_granted_evade_offers_and_resolves_both_choices(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0012/segment-0002.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        target = 'B:EX13-019#4'
        offered = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(offered['processing'], 'EVADE_CHOICE_PENDING')
        pending = [p for p in pending_options(runtime, 'B')
                   if p['effect_id'] == 'BT11-112.granted_evade']
        self.assertEqual(len(pending), 1)
        declined = copy.deepcopy(runtime)
        no = resolve_pending(declined, 'B', pending[0]['id'], False)
        self.assertFalse(no['prevented_deletion'])
        self.assertNotIn(target, declined.state.battle['B'])
        yes = resolve_pending(runtime, 'B', pending[0]['id'], True)
        self.assertTrue(yes['prevented_deletion'])
        self.assertIn(target, runtime.state.battle['B'])
        self.assertTrue(runtime.state.battle['B'][target].suspended)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
