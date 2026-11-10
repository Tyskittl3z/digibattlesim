"""Judge receipts describe actual engine checks, not independent certification."""
import copy
import importlib
import importlib.util
import inspect
from pathlib import Path
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import queue_effects, resolve_pending
from field_tracker import FieldTracker
from match_preparation import begin_preparation
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import stage


ROOT = Path(__file__).resolve().parents[1]


class JudgeLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('judge_ledger'))
        self.raw_judge = importlib.import_module('judge_ledger').judge_action
        self.judge = lambda *args, **kwargs: self.raw_judge(*args, tracker=self.tracker, **kwargs)

    def runtime(self):
        runtime = ContextRuntime(self.context, 13, 'A', build_selected_registry(self.context, ROOT),
                                 allow_experimental=True)
        self.tracker = FieldTracker(self.context)
        self.tracker.start(runtime.snapshot())
        return runtime

    def opening(self):
        runtime = self.runtime()
        before = runtime.snapshot()
        result = begin_preparation(runtime, ROOT)
        command = {'command': 'BEGIN_PREPARATION', 'seat': 'A', 'args': {},
                   'status': 'EXPERIMENTAL_RESOLVED'}
        return runtime, command, before, runtime.snapshot(), result

    def test_receipt_binds_real_transaction_sources_and_conservation_without_certification(self):
        runtime, command, before, after, result = self.opening()
        receipt = self.judge(runtime, command, before, after, result, root=ROOT)
        self.assertTrue(receipt['accepted'])
        self.assertEqual(receipt['status'], 'RUNTIME_VALIDATED')
        self.assertEqual(set(receipt['layers']), {'Justitia', 'Dike', 'Tyr'})
        self.assertEqual(receipt['physical_card_count'], 108)
        self.assertTrue(receipt['sources'])
        self.assertEqual(receipt['certification'], 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED')
        self.assertFalse(receipt['independent_semantic_certification'])
        receipt['sources'].clear()
        self.assertTrue(self.judge(runtime, command, before, after, result, root=ROOT)['sources'])

    def test_pending_effect_receipt_binds_actual_before_pending_and_registered_wording(self):
        runtime = self.runtime()
        source = stage(runtime, 'A', ['BT11-112'])
        queue_effects(runtime, [{'seat': 'A', 'source': source, 'field': 'main_text',
            'effect_id': 'BT11-112.on_play_grant', 'trigger': {'kind': 'On Play'}}])
        pending_id = runtime.state.pending[0]['id']
        before = runtime.snapshot()
        self.tracker = FieldTracker(self.context); self.tracker.start(before)
        result = resolve_pending(runtime, 'A', pending_id, None)
        command = {'command': 'RESOLVE_PENDING', 'seat': 'A',
                   'args': {'pending_id': pending_id, 'choice': None}, 'status': 'EXPERIMENTAL_RESOLVED'}
        receipt = self.judge(runtime, command, before, runtime.snapshot(), result, root=ROOT)
        self.assertTrue(receipt['accepted'])
        self.assertEqual(receipt['binding']['effect_id'], 'BT11-112.on_play_grant')
        self.assertEqual(receipt['binding']['status'], 'EXPERIMENTAL_UNREVIEWED')
        wrong = copy.deepcopy(command); wrong['args']['pending_id'] = 'invented'
        self.assertFalse(self.judge(runtime, wrong, before, runtime.snapshot(), result, root=ROOT)['accepted'])

    def test_mismatched_command_or_result_cannot_claim_a_validated_transaction(self):
        runtime, command, before, after, result = self.opening()
        wrong = copy.deepcopy(command); wrong['command'] = 'FINISH_TURN'
        self.assertEqual(self.judge(runtime, wrong, before, after, result, root=ROOT)['status'], 'AUDIT_FAILED')
        changed = copy.deepcopy(result); changed['initial_hands']['A'] = 99
        self.assertFalse(self.judge(runtime, command, before, after, changed, root=ROOT)['accepted'])

    def test_software_gap_is_unrated_rejection_with_unchanged_state_not_illegality(self):
        runtime = self.runtime(); before = runtime.snapshot()
        command = {'command': 'UNKNOWN_OPTION_ACTION', 'seat': 'A', 'args': {}, 'status': 'HALT'}
        receipt = self.judge(runtime, command, before, before, None,
                             RuntimeHalt('OPTION_UNIMPLEMENTED'), root=ROOT)
        self.assertFalse(receipt['accepted'])
        self.assertEqual(receipt['status'], 'SOFTWARE_GAP')
        self.assertNotEqual(receipt.get('verdict'), 'ILLEGAL')
        self.assertTrue(receipt['rollback_unchanged'])

    def test_failed_transaction_cannot_claim_rollback_after_state_changed(self):
        runtime, command, before, after, result = self.opening()
        receipt = self.judge(runtime, command, before, after, result, 'CONTROL_COMMAND_ERROR', root=ROOT)
        self.assertEqual(receipt['status'], 'AUDIT_FAILED')
        self.assertFalse(receipt['accepted'])
        self.assertFalse(receipt['rollback_unchanged'])

    def test_snapshot_tampering_is_rejected_and_does_not_change_runtime(self):
        runtime, command, before, after, result = self.opening()
        live = runtime.snapshot()
        for field in ('memory', 'physical', 'identity'):
            forged = copy.deepcopy(after)
            if field == 'memory': forged['state']['memory'] += 1
            elif field == 'physical': forged['state']['zones']['A']['deck'].pop()
            else: forged['seed'] += 1
            with self.subTest(field=field):
                self.assertFalse(self.judge(runtime, command, before, forged, result, root=ROOT)['accepted'])
                self.assertEqual(runtime.snapshot(), live)

    def test_unknown_and_missing_semantic_arguments_are_rejected(self):
        runtime, command, before, after, result = self.opening()
        command['args']['tamper'] = 1
        self.assertFalse(self.judge(runtime, command, before, after, result, root=ROOT)['accepted'])
        from match_preparation import choose_redraw
        before = runtime.snapshot()
        self.tracker = FieldTracker(self.context); self.tracker.start(before)
        result = choose_redraw(runtime, 'A', False, ROOT)
        self.assertFalse(self.judge(runtime, {'command': 'REDRAW_CHOICE', 'seat': 'A', 'args': {}},
                                    before, runtime.snapshot(), result, root=ROOT)['accepted'])

    def test_before_state_must_match_the_independent_tracker_anchor(self):
        runtime, command, before, after, result = self.opening()
        self.assertIn('tracker', inspect.signature(self.raw_judge).parameters)
        before['state']['memory'] += 1
        receipt = self.judge(runtime, command, before, after, result, root=ROOT)
        self.assertFalse(receipt['accepted'])


if __name__ == '__main__':
    unittest.main()
