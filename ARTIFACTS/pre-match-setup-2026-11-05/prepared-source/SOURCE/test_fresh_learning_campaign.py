"""Fresh named learning games; private fixtures never count as a cohort."""
import copy
import importlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from context_runtime import RuntimeHalt
import imported_attempts as diagnostic


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
CAMPAIGN = 'private-fresh-runner-test-v1'


class FreshLearningCampaignTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('fresh_learning_campaign'))
        self.runner = importlib.import_module('fresh_learning_campaign')
        self.State = importlib.import_module('interaction_learning').LearningState

    def run_game(self, **kwargs):
        return self.runner.run_game(0, ROOT, context_file=CONTEXT,
            campaign_id=CAMPAIGN, learning_state=kwargs.pop('learning_state', self.State()),
            max_commands=kwargs.pop('max_commands', 3), **kwargs)

    def test_schedule_is_reproducible_balanced_and_bound_to_context_and_campaign(self):
        context, _, _ = diagnostic._load_context_selection(ROOT, CONTEXT)
        schedule = self.runner.make_schedule(context.matchup_id, CAMPAIGN)
        self.assertEqual(schedule, self.runner.make_schedule(context.matchup_id, CAMPAIGN))
        self.assertEqual(len(schedule['games']), 60)
        self.assertEqual(sum(row['first'] == 'A' for row in schedule['games']), 30)
        self.assertEqual(len({row['seed'] for row in schedule['games']}), 60)
        self.assertNotEqual(schedule['schedule_sha256'],
                            self.runner.make_schedule(context.matchup_id, CAMPAIGN + '-new')['schedule_sha256'])
        self.assertNotEqual(schedule['games'][0]['seed'], diagnostic.seed_for(0, context.matchup_id))
        for count in (1, 0, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.runner.make_schedule(context.matchup_id, CAMPAIGN, count=count)

    def test_fresh_opening_uses_only_named_bots_and_tracker_views(self):
        state = self.State()
        initial_learning = copy.deepcopy(state.export())
        with patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('reference policy used')):
            record = self.run_game(learning_state=state)
        self.assertEqual(record['status'], 'PAUSED')
        self.assertEqual([c['command'] for c in record['commands']],
                         ['BEGIN_PREPARATION', 'REDRAW_CHOICE', 'REDRAW_CHOICE'])
        self.assertEqual([c['seat'] for c in record['commands'][1:]], ['A', 'B'])
        self.assertEqual(record['final']['state']['phase'], 'START_OF_TURN')
        self.assertEqual(len(record['tracker_observations']), 3)
        self.assertEqual(record['learning_state_before'], initial_learning)
        self.assertEqual(record['learning_state_after'], initial_learning)
        self.assertEqual(state.export(), initial_learning)
        for command in record['commands'][1:]:
            owner = command['seat']; other = 'B' if owner == 'A' else 'A'
            self.assertIsInstance(command['public_view']['players'][owner]['hand'], list)
            self.assertEqual(set(command['public_view']['players'][other]['hand']), {'count'})
            self.assertIn('policy_rng_before_choice', command)
            self.assertIn('policy_rng_after_choice', command)
            self.assertTrue(command['decisions'])
            self.assertEqual(command['judge']['status'], 'RUNTIME_VALIDATED')
            self.assertIn(command['rating']['label'], ('GREEN', 'YELLOW', 'RED'))
        self.assertEqual(record['accepted_fact_finding_credit'], 0)

    def test_complete_record_replay_and_pause_resume_preserve_choices(self):
        previous = self.run_game()
        self.assertTrue(self.runner.replay_game(previous, ROOT)['exact_match'])
        resumed = self.run_game(previous_record=previous, max_commands=2)
        self.assertEqual(resumed['commands'][:3], previous['commands'])
        for key in ('seed', 'first', 'context_id', 'campaign_id', 'learning_state_before'):
            self.assertEqual(resumed[key], previous[key])
        self.assertEqual(resumed['commands'][3]['policy_rng_before_choice'], previous['policy_rng_final'])
        self.assertTrue(self.runner.replay_game(resumed, ROOT)['exact_match'])

    def test_selected_failed_action_is_unrated_and_retried_without_choosing(self):
        real_apply = self.runner._apply
        def missing(runtime, kind, seat, args, root):
            if kind == 'REDRAW_CHOICE':
                raise RuntimeHalt('ACTUAL_PRIVATE_TEST_GAP')
            return real_apply(runtime, kind, seat, args, root)
        with patch.object(self.runner, '_apply', side_effect=missing):
            stopped = self.run_game()
        self.assertEqual(stopped['status'], 'HALT')
        failed = stopped['commands'][-1]
        self.assertEqual(failed['command'], 'REDRAW_CHOICE')
        self.assertEqual(failed['rating']['status'], 'UNRATED')
        self.assertEqual(stopped['learning_state_before'], stopped['learning_state_after'])
        with patch.object(self.runner.LearningPlayerBot, 'choose', side_effect=AssertionError('choice rerolled')):
            resumed = self.run_game(previous_record=stopped, max_commands=1)
        retry = resumed['commands'][-1]
        for key in ('command', 'seat', 'args', 'decisions', 'policy_rng_after_choice'):
            # A resolved retry gains rewards/status on its saved decision records.
            if key != 'decisions':
                self.assertEqual(retry[key], failed[key])
        self.assertEqual(retry['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(resumed['policy_rng_final'], stopped['policy_rng_final'])

    def test_unselected_generator_failure_can_resume_its_same_window(self):
        opening = self.run_game()
        with patch.object(self.runner, 'breeding_candidates', side_effect=RuntimeHalt('CANDIDATES_NOT_YET_IMPLEMENTED')):
            stopped = self.run_game(previous_record=opening, max_commands=4)
        self.assertEqual(stopped['commands'][-1]['command'], 'GENERATE_BREEDING_CHOICES')
        self.assertNotIn('args', stopped['commands'][-1])
        self.assertEqual(stopped['commands'][-1]['policy_rng_before_choice'], stopped['policy_rng_final'])
        resumed = self.run_game(previous_record=stopped, max_commands=1)
        self.assertEqual(resumed['commands'][-1]['command'], 'BREEDING_CHOICE')
        self.assertEqual(resumed['commands'][-1]['status'], 'EXPERIMENTAL_RESOLVED')

    def test_prefix_results_state_rng_and_training_input_tampering_fail_before_policy(self):
        previous = self.run_game()
        for change in ('result', 'state', 'rng', 'training'):
            altered = copy.deepcopy(previous)
            state = self.State()
            if change == 'result': altered['commands'][0]['result']['tamper'] = True
            elif change == 'state': altered['final']['state']['memory'] += 1
            elif change == 'rng': altered['final']['rng_state'][1][0] ^= 1
            else: altered['learning_state_before']['tamper'] = True
            with self.subTest(change=change), patch.object(self.runner, 'LearningPlayerBot',
                    side_effect=AssertionError('policy constructed before proof')):
                with self.assertRaisesRegex(RuntimeHalt, 'FRESH_.*MISMATCH'):
                    self.run_game(previous_record=altered, learning_state=state, max_commands=1)

    def test_post_apply_audit_failure_preserves_changed_state_without_false_rollback(self):
        with patch.object(self.runner, 'judge_action', return_value={
                'status': 'AUDIT_FAILED', 'accepted': False, 'reason': 'PRIVATE_AUDIT_TEST'}):
            record = self.run_game()
        self.assertEqual(record['status'], 'JUDGE_AUDIT_FAILURE')
        self.assertEqual(record['commands'][-1]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(record['final']['state']['phase'], 'INITIAL_HANDS')
        self.assertNotEqual(record['final']['state'], record['initial']['state'])
        self.assertEqual(record['learning_state_after'], record['learning_state_before'])


if __name__ == '__main__':
    unittest.main()
