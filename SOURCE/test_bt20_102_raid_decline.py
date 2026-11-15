"""An explicit player attack may decline optional Raid (rule 16-23-3)."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class RaidDeclineTests(unittest.TestCase):
    def test_saved_player_target_stays_player_with_unsuspended_enemy(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0004/segment-0000.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        self.assertTrue(any(not stack.suspended for stack in runtime.state.battle['A'].values()))
        choice = failed['args']['choice']
        self.assertEqual(choice['target'], 'PLAYER')
        result = resolve_pending(runtime, 'B', failed['args']['pending_id'], choice)
        self.assertEqual(result['target'], 'PLAYER')
        self.assertEqual(runtime.state.attack['target'], 'PLAYER')
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
