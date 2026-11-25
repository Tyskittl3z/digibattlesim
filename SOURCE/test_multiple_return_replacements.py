"""Two printed inherited leave replacements on one stack resolve in chosen order."""
import copy
import unittest

from context_runtime import ContextRuntime
from effect_scheduler import pending_options, queue_effects, resolve_pending
from matchup_readiness import load_context_file
from return_effects import REPLACEMENT_EFFECT, BT22_REPLACEMENT_EFFECT
from selected_mechanics import build_selected_registry, _set_orientation
from test_selected_mechanics import ROOT, stage


class MultipleReturnReplacementsTests(unittest.TestCase):
    def runtime(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 500, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        source = stage(runtime, 'B', ['BT11-032'])
        stage(runtime, 'B', ['BT11-112'])
        stage(runtime, 'B', ['BT22-085'])
        target = stage(runtime, 'A', ['EX13-017', 'BT22-022', 'BT22-023'])
        runtime.state.battle['A'][target].instance_id = 'entity-target'
        queue_effects(runtime, [{'seat': 'B', 'source': source,
            'effect_id': 'BT11-032.unsuspend_return', 'field': 'main_text',
            'trigger': {'kind': 'ORIENTATION_CHANGED', 'entity': source,
                        'suspended_before': True, 'suspended_after': False}}])
        return runtime, target

    def test_both_inherited_replacements_are_offered_and_each_can_prevent_return(self):
        runtime, target = self.runtime()
        pending = pending_options(runtime, 'B')[0]
        result = resolve_pending(runtime, 'B', pending['id'], target)
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        offered = pending_options(runtime, 'A')
        self.assertEqual({p['effect_id'] for p in offered},
                         {REPLACEMENT_EFFECT, BT22_REPLACEMENT_EFFECT})
        self.assertEqual(len(offered), 2)
        for selected in offered:
            with self.subTest(effect=selected['effect_id']):
                branch = copy.deepcopy(runtime)
                chosen = next(p for p in pending_options(branch, 'A') if p['effect_id'] == selected['effect_id'])
                saved = resolve_pending(branch, 'A', chosen['id'], True)
                self.assertTrue(saved['prevented_return'])
                self.assertIn(target, branch.state.battle['A'])
                self.assertTrue(branch.state.battle['A'][target].suspended)
                self.assertEqual(branch.state.pending, [])
                branch.verify()

    def test_declining_first_offers_second_and_declining_both_returns(self):
        runtime, target = self.runtime()
        returning = pending_options(runtime, 'B')[0]
        resolve_pending(runtime, 'B', returning['id'], target)
        first = next(p for p in pending_options(runtime, 'A') if p['effect_id'] == REPLACEMENT_EFFECT)
        declined = resolve_pending(runtime, 'A', first['id'], False)
        self.assertFalse(declined['prevented_return'])
        self.assertTrue(declined['replacement_pending'])
        second = pending_options(runtime, 'A')
        self.assertEqual([p['effect_id'] for p in second], [BT22_REPLACEMENT_EFFECT])
        final = resolve_pending(runtime, 'A', second[0]['id'], False)
        self.assertFalse(final['prevented_return'])
        self.assertNotIn(target, runtime.state.battle['A'])
        self.assertIn(target, [card.key for card in runtime.state.zones['A']['hand']])
        runtime.verify()

    def test_bt12_return_queues_both_printed_replacements(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 12029, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        source = stage(runtime, 'B', ['BT12-029'], suspended=True)
        stage(runtime, 'B', ['BT11-112'])
        target = stage(runtime, 'A', ['EX13-017', 'BT22-022', 'BT22-023'])
        runtime.state.battle['A'][target].instance_id = 'entity-target'
        _set_orientation(runtime, 'B', runtime.state.battle['B'][source], False)
        returning = next(p for p in pending_options(runtime, 'B')
                         if p['effect_id'] == 'BT12-029.unsuspend_return_lowest')
        result = resolve_pending(runtime, 'B', returning['id'], target)
        self.assertEqual(result['processing'], 'RETURN_REPLACEMENT_PENDING')
        self.assertEqual({p['effect_id'] for p in pending_options(runtime, 'A')},
                         {REPLACEMENT_EFFECT, BT22_REPLACEMENT_EFFECT})
        runtime.verify()
