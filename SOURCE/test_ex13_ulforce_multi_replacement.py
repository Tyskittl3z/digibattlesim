"""Game 15's simultaneous return keeps EX13-017's replacement choice."""
import copy
import gzip
import json
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from return_effects import REPLACEMENT_EFFECT, return_replacement_choices
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class MultiTargetReturnReplacementTests(unittest.TestCase):
    def test_saved_order_and_defender_replacement_are_both_resolved(self):
        path = (ROOT / 'ARTIFACTS/ulforce-prospective-60-2026-11-17/'
                'game-0015/segment-0000.json.gz')
        with gzip.open(path, 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        order = failed['args']['choice']['bottom_order']
        self.assertEqual(order, ['A:EX13-023#2', 'A:EX13-023#4'])
        result = resolve_pending(runtime, 'B', failed['args']['pending_id'],
                                 failed['args']['choice'])
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        self.assertEqual(result['returned'], [])
        replacement = [p for p in pending_options(runtime, 'A')
                       if p['effect_id'] == REPLACEMENT_EFFECT]
        self.assertEqual(len(replacement), 1)
        self.assertEqual(return_replacement_choices(runtime, 'A', replacement[0]['source']),
                         [False, True])

        declined = copy.deepcopy(runtime)
        moved = resolve_pending(declined, 'A', replacement[0]['id'], False)
        self.assertFalse(moved['prevented_return'])
        self.assertEqual(moved['returned'], order)
        self.assertEqual([c.key for c in declined.state.zones['A']['deck'][:2]], order)
        self.assertNotIn(order[0], declined.state.battle['A'])
        self.assertNotIn(order[1], declined.state.battle['A'])

        protected = resolve_pending(runtime, 'A', replacement[0]['id'], True)
        self.assertTrue(protected['prevented_return'])
        self.assertEqual(protected['returned'], [order[0]])
        self.assertEqual(runtime.state.zones['A']['deck'][0].key, order[0])
        self.assertNotIn(order[0], runtime.state.battle['A'])
        self.assertTrue(runtime.state.battle['A'][order[1]].suspended)
        declined.verify();runtime.verify()


if __name__ == '__main__':
    unittest.main()
