"""Game 24's queued Piercing check survives the accepted attack-end action."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT


class PiercingAfterAttackEndTests(unittest.TestCase):
    def test_saved_piercing_check_uses_queued_battle_record(self):
        path = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0024/segment-0000.json.gz'
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        self.assertIsNone(runtime.state.attack)
        chosen = failed['selected_pending']
        self.assertEqual(chosen['effect_id'], 'BT20-102.piercing_check')
        self.assertEqual(selected_pending_choices(runtime, 'B', chosen), [None])
        security_before = len(runtime.state.zones['A']['security'])
        result = resolve_pending(runtime, 'B', chosen['id'], None)
        self.assertEqual(result['processing'], 'MANDATORY_PIERCING_SECURITY_CHECK')
        self.assertEqual(len(runtime.state.zones['A']['security']), security_before - 1)
        self.assertIsNone(runtime.state.attack)
        self.assertIn('BT22-023.end_turn_unsuspend',
                      [p['effect_id'] for p in pending_options(runtime, 'B')])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
