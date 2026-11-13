"""One saved selection can resolve without selecting any subsequent action."""
import copy
import gzip
import importlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime, RuntimeHalt
from match_context import digest
import imported_attempts as diagnostic


ROOT = Path(__file__).resolve().parents[1]


class RecordedActionCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('recorded_action_checkpoint'),
                             'A bounded saved-action checkpoint must not call random pilots')
        self.runner = importlib.import_module('recorded_action_checkpoint')

    @classmethod
    def setUpClass(cls):
        # Private short regression scenario: use an archived opening's choices
        # to stage Rina's no-target grant. This never writes/advances Game0000.
        path = ROOT / 'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0000.json.gz'
        saved = json.loads(gzip.decompress(path.read_bytes()))
        context, _, _ = diagnostic._load_context_selection(
            ROOT, saved['replay_provenance']['context_file'])
        runtime = ContextRuntime(context, saved['seed'], saved['first'],
                                 diagnostic.build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        initial = runtime.snapshot()
        commands = []
        for old in saved['commands']:
            command = {key: copy.deepcopy(old[key]) for key in
                       ('command', 'seat', 'args', 'candidates', 'pilot_id') if key in old}
            command['public_view'] = runtime.public_view(command['seat'])
            command['result'] = diagnostic._apply(runtime, command['command'], command['seat'],
                                                  command['args'], ROOT)
            command['status'] = 'EXPERIMENTAL_RESOLVED'
            commands.append(command)
        pending = diagnostic.pending_options(runtime, 'A')[0]
        assert pending['effect_id'] == 'BT11-112.on_play_grant'
        commands.append({'command': 'RESOLVE_PENDING', 'seat': 'A',
                         'args': {'pending_id': pending['id'], 'choice': None},
                         'public_view': runtime.public_view('A'), 'candidates': [pending],
                         'pilot_id': saved['pilot_id']['A'], 'status': 'HALT',
                         'reason': 'SYNTHETIC_MISSING_HANDLER', 'exception': 'RuntimeHalt'})
        before = runtime.snapshot()
        cls.fixture = {key: copy.deepcopy(saved[key]) for key in
                       ('index', 'seed', 'first', 'context_id', 'pilot_id', 'pilots', 'replay_provenance')}
        cls.fixture.update({'schema': 'synthetic-saved-selection-test-v1', 'status': 'HALT',
                            'commands': commands, 'initial': initial, 'final': before,
                            'halts': [{'type': 'HALT', 'before': before}],
                            'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0})

    def saved(self):
        return copy.deepcopy(self.fixture)

    def test_saved_selection_only_preserves_history_and_never_constructs_a_policy(self):
        previous = self.saved()
        original = copy.deepcopy(previous)
        real_apply = self.runner._apply
        with patch.object(diagnostic.ReferencePilot, 'choose', side_effect=AssertionError('policy chosen')), \
                patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('policy constructed')), \
                patch.object(diagnostic, 'main_candidates', side_effect=AssertionError('new candidates')), \
                patch.object(diagnostic, 'pending_choice', side_effect=AssertionError('new decision')), \
                patch.object(self.runner, '_apply', wraps=real_apply) as apply:
            record = self.runner.continue_selected_action(previous, ROOT)
        self.assertEqual(previous, original)
        self.assertEqual(record['status'], 'PAUSED_AFTER_SAVED_ACTION')
        self.assertEqual(len(record['commands']), len(previous['commands']))
        self.assertEqual(record['commands'][:-1], previous['commands'][:-1])
        for field in ('index', 'seed', 'first', 'context_id', 'pilots', 'pilot_id'):
            self.assertEqual(record[field], previous[field])
        retry = record['commands'][-1]
        for field in ('command', 'seat', 'args', 'pilot_id', 'candidates', 'public_view'):
            self.assertEqual(retry[field], previous['commands'][-1][field])
        self.assertEqual(retry['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(retry['result']['processing'], 'NO_ELIGIBLE_TARGET')
        self.assertEqual(apply.call_count, len(previous['commands']))
        self.assertEqual(apply.call_args.args[1:4], ('RESOLVE_PENDING', 'A', retry['args']))
        self.assertEqual(record['final']['rng_state'], previous['final']['rng_state'])
        self.assertFalse(record['final']['state']['terminal'])
        proof = record['continuation_provenance']['physical_state_proof']
        self.assertEqual(proof['original_before_sha256'], proof['revalidated_before_sha256'])
        self.assertEqual(proof['original_rng_sha256'], proof['revalidated_rng_sha256'])
        self.assertEqual(record['continuation_provenance']['previous_record'], previous)
        self.assertEqual(record['continuation_provenance']['previous_record_sha256'], digest(previous))
        self.assertEqual(record['policy_execution']['new_policy_decisions'], 0)
        self.assertEqual(record['policy_execution']['policy_invocations'], 0)
        for field in ('accepted_fact_finding_credit', 'final_evaluation_credit', 'user_bot_evidence_credit'):
            self.assertEqual(record[field], 0)
        self.assertNotIn('rating', retry)

    def test_exact_full_record_replay_and_hash_tamper_rejection(self):
        record = self.runner.continue_selected_action(self.saved(), ROOT)
        replay = self.runner.replay_selected_action(record, ROOT)
        self.assertTrue(replay['exact_match'])
        self.assertEqual(replay['saved_record_sha256'], replay['replayed_record_sha256'])
        record['continuation_provenance']['previous_record']['seed'] += 1
        with self.assertRaisesRegex(RuntimeHalt, 'CONTINUATION_PREVIOUS_RECORD_HASH_MISMATCH'):
            self.runner.replay_selected_action(record, ROOT)

    def test_prefix_result_and_public_view_changes_are_rejected(self):
        previous = self.saved()
        previous['commands'][0]['result']['tampered'] = True
        with self.assertRaisesRegex(RuntimeHalt, 'SAVED_ACTION_PREFIX_RESULT_MISMATCH'):
            self.runner.continue_selected_action(previous, ROOT)
        previous = self.saved()
        previous['commands'][0]['public_view']['memory'] = 1
        with self.assertRaisesRegex(RuntimeHalt, 'SAVED_ACTION_PREFIX_PUBLIC_VIEW_MISMATCH'):
            self.runner.continue_selected_action(previous, ROOT)

    def test_full_pre_halt_state_and_rng_must_match_before_retry(self):
        for field in ('state', 'rng_state'):
            previous = self.saved()
            if field == 'state':
                previous['final']['state']['memory'] += 1
            else:
                previous['final']['rng_state'][1][0] ^= 1
            previous['halts'][-1]['before'] = copy.deepcopy(previous['final'])
            with self.subTest(field=field), self.assertRaisesRegex(
                    RuntimeHalt, 'SAVED_ACTION_BEFORE_HALT_PHYSICAL_MISMATCH'):
                self.runner.continue_selected_action(previous, ROOT)

    def test_generator_or_missing_saved_selection_is_rejected_before_gameplay(self):
        for change in ({'command': 'GENERATE_PENDING_CHOICES'}, {'args': {'pending_id': 'effect-1'}}):
            previous = self.saved()
            previous['commands'][-1].update(change)
            with self.subTest(change=change), patch.object(
                    self.runner, 'ContextRuntime', side_effect=AssertionError('gameplay started')):
                with self.assertRaisesRegex(RuntimeHalt, 'SAVED_ACTION_RESOLVE_SELECTION_REQUIRED'):
                    self.runner.continue_selected_action(previous, ROOT)

    def test_retried_action_failure_propagates_without_a_new_selection(self):
        real_apply = self.runner._apply
        def fail_selected(runtime, command, seat, args, root):
            if command == 'RESOLVE_PENDING':
                raise RuntimeHalt('ACTUAL_DEPENDENCY_STILL_MISSING')
            return real_apply(runtime, command, seat, args, root)
        with patch.object(self.runner, '_apply', side_effect=fail_selected) as apply:
            with self.assertRaisesRegex(RuntimeHalt, 'ACTUAL_DEPENDENCY_STILL_MISSING'):
                self.runner.continue_selected_action(self.saved(), ROOT)
        self.assertEqual(apply.call_count, len(self.fixture['commands']))


if __name__ == '__main__':
    unittest.main()
