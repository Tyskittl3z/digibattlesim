"""Q7265 permits returning a Digimon while protecting its stacked cards."""
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class DirectReturnQ7265Tests(unittest.TestCase):
    def test_recorded_bt12_return_moves_unsuspended_ulforce_to_hand(self):
        with gzip.open(ROOT / 'ARTIFACTS/fresh-game-0001-board-text-2026-11-11/segment-0010.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        target = 'A:EX13-023#2'
        selected = next(p for p in pending_options(runtime, 'B') if p['id'] ==
                        record['commands'][-1]['args']['pending_id'])
        result = resolve_pending(runtime, 'B', selected['id'], target)
        self.assertEqual(result['returned'], target)
        self.assertNotIn(target, runtime.state.battle['A'])
        self.assertIn(target, [card.key for card in runtime.state.zones['A']['hand']])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
