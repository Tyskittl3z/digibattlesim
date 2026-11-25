"""BT11-032's queued unsuspend trigger returns an eligible Digimon."""
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, queue_effects, resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT, stage


class UlforceUnsuspendReturnTests(unittest.TestCase):
    def test_tamer_scaled_return_uses_live_level(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 32, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        source = stage(runtime, 'A', ['BT11-032'])
        stage(runtime, 'A', ['BT11-112'])
        target = stage(runtime, 'B', ['BT22-022'])
        too_large = stage(runtime, 'B', ['EX13-022'])
        queue_effects(runtime, [{'seat': 'A', 'source': source,
            'effect_id': 'BT11-032.unsuspend_return', 'field': 'main_text',
            'trigger': {'kind': 'ORIENTATION_CHANGED', 'entity': source,
                        'suspended_before': True, 'suspended_after': False}}])
        pending = pending_options(runtime, 'A')
        self.assertEqual(len(pending), 1)
        choices = selected_pending_choices(runtime, 'A', pending[0])
        self.assertIn(target, choices)
        self.assertNotIn(too_large, choices)
        moved = resolve_pending(runtime, 'A', pending[0]['id'], target)
        self.assertEqual(moved['returned'], target)
        self.assertNotIn(target, runtime.state.battle['B'])
        runtime.verify()
