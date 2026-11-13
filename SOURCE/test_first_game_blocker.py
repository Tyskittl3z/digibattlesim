"""Bot B's first encountered Blocker window in fresh Game 0000."""
import gzip
import json
import unittest

from attack_flow import choose_blocker
from context_runtime import ContextRuntime
from imported_attempts import _apply
from matchup_readiness import load_context_file
from named_bot_continuation import _plain_block_options
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class FirstGameBlockerTests(unittest.TestCase):
    def test_saved_window_offers_explicit_decline_and_real_blocker(self):
        path = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0017.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        self.assertEqual(runtime.state.attack['window'], 'BLOCK')
        options = _plain_block_options(runtime, 'B')
        self.assertIn({'card':None,'status':'EXPLICIT_DECLINE'}, options)
        self.assertIn({'card':'B:EX13-023#2','status':'READY_BLOCKER'}, options)
        result = choose_blocker(runtime, 'B', 'B:EX13-023#2', ROOT)
        self.assertEqual(result['blocker'], 'B:EX13-023#2')
        self.assertEqual(runtime.state.attack['target'], 'B:EX13-023#2')
        self.assertTrue(runtime.state.attack['block_used'])
        self.assertTrue(runtime.state.battle['B']['B:EX13-023#2'].suspended)
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
