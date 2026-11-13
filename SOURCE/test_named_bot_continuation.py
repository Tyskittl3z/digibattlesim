"""Bounded named-bot segments preserve saved history; no full-match credit."""
import copy
import importlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime, RuntimeHalt
import imported_attempts as diagnostic
from match_context import digest
from recorded_action_checkpoint import continue_selected_action
import test_recorded_action_checkpoint as saved_scenarios


ROOT = Path(__file__).resolve().parents[1]


class NamedBotContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Stage a short private recorded opening, never advance a saved file.
        saved_scenarios.RecordedActionCheckpointTests.setUpClass()
        paused = continue_selected_action(saved_scenarios.RecordedActionCheckpointTests.fixture, ROOT)
        context, _, _ = diagnostic._load_context_selection(
            ROOT, paused['replay_provenance']['context_file'])
        runtime = ContextRuntime(context, paused['seed'], paused['first'],
                                 diagnostic.build_selected_registry(context, ROOT), allow_experimental=True)
        for command in paused['commands']:
            diagnostic._apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        while runtime.state.phase != 'BREEDING':
            assert not runtime.state.pending
            kind = 'FINISH_TURN' if runtime.state.phase == 'END_OF_TURN' else 'ADVANCE_PHASE'
            seat = runtime.state.active
            command = {'command': kind, 'seat': seat, 'args': {},
                       'public_view': runtime.public_view(seat)}
            command['result'] = diagnostic._apply(runtime, kind, seat, {}, ROOT)
            command['status'] = 'EXPERIMENTAL_RESOLVED'
            paused['commands'].append(command)
        paused['final'] = runtime.snapshot()
        paused.pop('continuation_provenance')  # This is an explicit synthetic fixture.
        cls.fixture = paused

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('named_bot_continuation'))
        self.runner = importlib.import_module('named_bot_continuation')

    def saved(self):
        return copy.deepcopy(self.fixture)

    def test_named_segment_preserves_prefix_and_never_constructs_reference_policy(self):
        previous = self.saved()
        before = copy.deepcopy(previous)
        with patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('random policy used')):
            record = self.runner.continue_with_named_bots(previous, ROOT, max_new_commands=1)
        self.assertEqual(previous, before)
        self.assertEqual(record['status'], 'PAUSED_AFTER_NAMED_BOT_SEGMENT')
        self.assertEqual(record['commands'][:-1], previous['commands'])
        self.assertEqual(record['pilots'], previous['pilots'])
        self.assertEqual(record['pilot_id'], previous['pilot_id'])
        for field in ('index', 'context_id', 'seed', 'first'):
            self.assertEqual(record[field], previous[field])
        command = record['commands'][-1]
        self.assertEqual(command['command'], 'BREEDING_CHOICE')
        self.assertEqual(command['bot_id'], record['active_pilots']['B']['bot_id'])
        self.assertTrue(command['decisions'])
        self.assertEqual(command['decisions'][0]['chosen'], command['args'])
        self.assertEqual(record['continuation_provenance']['successful_commands_revalidated'], len(previous['commands']))
        proof = record['continuation_provenance']['physical_state_proof']
        self.assertEqual(proof['original_before_sha256'], proof['revalidated_before_sha256'])
        self.assertEqual(proof['original_rng_sha256'], proof['revalidated_rng_sha256'])
        for field in ('user_bot_evidence_credit', 'accepted_fact_finding_credit', 'final_evaluation_credit'):
            self.assertEqual(record[field], 0)
        self.assertFalse(record['ratings_assigned'])

    def test_full_record_exact_replay_and_paused_segment_resume(self):
        record = self.runner.continue_with_named_bots(self.saved(), ROOT, max_new_commands=1)
        replay = self.runner.replay_named_bot_continuation(record, ROOT)
        self.assertTrue(replay['exact_match'])
        self.assertEqual(replay['saved_record_sha256'], replay['replayed_record_sha256'])
        resumed = self.runner.continue_with_named_bots(record, ROOT, max_new_commands=1)
        self.assertEqual(resumed['commands'][:-1], record['commands'])

    def test_prefix_views_results_full_state_and_rng_must_match_before_bot_construction(self):
        for field in ('result', 'view', 'state', 'rng'):
            previous = self.saved()
            if field == 'result': previous['commands'][0]['result']['tampered'] = True
            elif field == 'view': previous['commands'][0]['public_view']['memory'] += 1
            elif field == 'state': previous['final']['state']['memory'] += 1
            else: previous['final']['rng_state'][1][0] ^= 1
            with self.subTest(field=field), patch.object(
                    self.runner, 'NamedPlayerBot', side_effect=AssertionError('bot constructed before proof')):
                with self.assertRaisesRegex(RuntimeHalt, 'NAMED_BOT_.*MISMATCH'):
                    self.runner.continue_with_named_bots(previous, ROOT, max_new_commands=1)

    def test_selected_failed_action_retries_without_reselecting(self):
        real_apply = self.runner._apply
        def missing(runtime, kind, seat, args, root):
            if kind == 'BREEDING_CHOICE' and seat == 'B': raise RuntimeHalt('ACTUAL_TEST_GAP')
            return real_apply(runtime, kind, seat, args, root)
        with patch.object(self.runner, '_apply', side_effect=missing):
            stopped = self.runner.continue_with_named_bots(self.saved(), ROOT, max_new_commands=1)
        self.assertEqual(stopped['status'], 'HALT')
        selected = copy.deepcopy(stopped['commands'][-1])
        with patch.object(self.runner.NamedPlayerBot, 'choose', side_effect=AssertionError('selection rerolled')):
            fixed = self.runner.continue_with_named_bots(stopped, ROOT, max_new_commands=1)
        retry = fixed['commands'][-1]
        for field in ('command', 'seat', 'args', 'bot_id', 'candidates', 'decisions'):
            self.assertEqual(retry[field], selected[field])
        self.assertEqual(retry['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(fixed['new_decisions'], [])

    def test_unselected_generator_failure_is_preserved_without_fallback(self):
        previous = self.saved()
        # Generator failure is explicitly retained; it is not an applied command.
        with patch.object(self.runner, 'breeding_candidates', side_effect=RuntimeHalt('UNKNOWN_TEST_CHOICE_SCHEMA')):
            stopped = self.runner.continue_with_named_bots(previous, ROOT, max_new_commands=1)
        self.assertEqual(stopped['status'], 'HALT')
        self.assertEqual(stopped['commands'][-1]['command'], 'GENERATE_BREEDING_CHOICES')
        self.assertEqual(stopped['final']['state'], previous['final']['state'])
        with self.assertRaisesRegex(RuntimeHalt, 'NAMED_BOT_UNSELECTED_GENERATOR_CHECKPOINT'):
            self.runner.continue_with_named_bots(stopped, ROOT, max_new_commands=1)

    def test_unknown_pending_choice_keeps_selected_effect_without_reselecting_on_retry(self):
        previous = copy.deepcopy(saved_scenarios.RecordedActionCheckpointTests.fixture)
        previous['commands'] = previous['commands'][:-1]
        previous['status'] = 'PAUSED_AFTER_SAVED_ACTION'
        previous['schema'] = 'recorded-selected-action-checkpoint-v1'
        previous['halts'] = []
        with patch.object(self.runner, 'pending_choice', side_effect=RuntimeHalt('UNKNOWN_TEST_PENDING_SCHEMA')):
            stopped = self.runner.continue_with_named_bots(previous, ROOT, max_new_commands=1)
        failed = stopped['commands'][-1]
        self.assertEqual(failed['command'], 'GENERATE_PENDING_CHOICES')
        self.assertEqual(failed['selected_pending']['effect_id'], 'BT11-112.on_play_grant')
        self.assertEqual(failed['decisions'][0]['chosen'], failed['selected_pending'])
        real_choose = self.runner.NamedPlayerBot.choose
        seen = []
        def forbid_reselect(bot, view, candidates, *, decision=None):
            seen.append(decision)
            if decision and decision.get('kind') == 'PENDING_EFFECT_ORDER':
                raise AssertionError('pending effect selection rerolled')
            return real_choose(bot, view, candidates, decision=decision)
        with patch.object(self.runner.NamedPlayerBot, 'choose', forbid_reselect):
            fixed = self.runner.continue_with_named_bots(stopped, ROOT, max_new_commands=1)
        resolved = fixed['commands'][-1]
        self.assertEqual(resolved['command'], 'RESOLVE_PENDING')
        self.assertEqual(resolved['args']['pending_id'], failed['selected_pending']['id'])
        self.assertEqual(resolved['result']['processing'], 'NO_ELIGIBLE_TARGET')
        self.assertEqual(resolved['selected_pending'], failed['selected_pending'])
        self.assertTrue(seen)

    def test_lineage_tamper_and_invalid_budget_are_rejected(self):
        record = self.runner.continue_with_named_bots(self.saved(), ROOT, max_new_commands=1)
        record['continuation_provenance']['previous_record']['seed'] += 1
        with self.assertRaisesRegex(RuntimeHalt, 'CONTINUATION_PREVIOUS_RECORD_HASH_MISMATCH'):
            self.runner.replay_named_bot_continuation(record, ROOT)
        for budget in (0, -1, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.runner.continue_with_named_bots(self.saved(), ROOT, max_new_commands=budget)


if __name__ == '__main__':
    unittest.main()
