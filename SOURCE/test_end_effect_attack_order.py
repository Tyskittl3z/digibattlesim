"""Game 20's chosen end-turn attack finishes before the other end effect."""
import gzip
import json
import unittest

from attack_flow import choose_counter, choose_blocker, confirm_attack, end_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from field_tracker import FieldTracker
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class EndEffectAttackOrderTests(unittest.TestCase):
    def test_saved_end_attack_defers_other_same_depth_effect(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0020/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        result = resolve_pending(runtime, 'B', failed['args']['pending_id'], failed['args']['choice'])
        self.assertEqual(result['processing'], 'RUSH_AND_ATTACK_WITHOUT_SUSPENDING')
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        self.assertNotIn('deferred_depth', runtime.public_view('B')['attack'])
        tracker = FieldTracker(context)
        tracker.start(runtime.snapshot())
        self.assertNotIn('deferred_depth', tracker.player_view('B')['attack'])
        self.assertEqual([p['effect_id'] for p in runtime.state.pending],
                         ['BT22-023.end_turn_unsuspend'])
        self.assertEqual(pending_options(runtime, 'B'), [])
        choose_counter(runtime, 'A', None, ROOT)
        choose_blocker(runtime, 'A', None, ROOT)
        confirm_attack(runtime, 'B', ROOT)
        end_attack(runtime, 'B', ROOT)
        self.assertEqual([p['effect_id'] for p in pending_options(runtime, 'B')],
                         ['BT22-023.end_turn_unsuspend'])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
