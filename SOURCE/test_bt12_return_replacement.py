"""BT12-029's return offers the defender's EX13-017 replacement."""
import copy
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from matchup_readiness import load_context_file
from return_effects import REPLACEMENT_EFFECT, return_replacement_choices
from selected_mechanics import build_selected_registry, _set_orientation
from test_selected_mechanics import ROOT, stage


class Bt12ReturnReplacementTests(unittest.TestCase):
    def test_return_offers_suspend_or_return_choice(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 12029, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        source = stage(runtime, 'A', ['BT12-029'], suspended=True)
        stage(runtime, 'A', ['BT11-112'])
        target = stage(runtime, 'B', ['EX13-017', 'P-138'])
        runtime.state.battle['B'][target].instance_id = 'target-instance'
        _set_orientation(runtime, 'A', runtime.state.battle['A'][source], False)
        returning = next(p for p in pending_options(runtime, 'A')
                         if p['effect_id'] == 'BT12-029.unsuspend_return_lowest')
        result = resolve_pending(runtime, 'A', returning['id'], target)
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        self.assertIn(target, runtime.state.battle['B'])
        replacement = [p for p in pending_options(runtime, 'B') if p['effect_id'] == REPLACEMENT_EFFECT]
        self.assertEqual(len(replacement), 1)
        self.assertEqual(return_replacement_choices(runtime, 'B', replacement[0]['source']), [False, True])
        returned = copy.deepcopy(runtime)
        decline = resolve_pending(returned, 'B', replacement[0]['id'], False)
        self.assertFalse(decline['prevented_return'])
        self.assertIn(target, [c.key for c in returned.state.zones['B']['hand']])
        self.assertNotIn(target, returned.state.battle['B'])
        protected = resolve_pending(runtime, 'B', replacement[0]['id'], True)
        self.assertTrue(protected['prevented_return'])
        self.assertTrue(runtime.state.battle['B'][target].suspended)
        runtime.verify()
