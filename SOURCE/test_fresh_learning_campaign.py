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


    def test_policy_rng_criteria_schedule_and_source_tampering_rejected(self):
        original = self.run_game()
        for field in ('policy_rng', 'criteria', 'schedule', 'source', 'pilot'):
            changed = copy.deepcopy(original)
            if field == 'policy_rng':
                changed['commands'][1]['policy_rng_after_choice']['A']['state'][1][0] ^= 1
            elif field == 'criteria': changed['criteria']['criterion_sha256'] = '0' * 64
            elif field == 'schedule': changed['schedule']['games'][0]['seed'] += 1
            elif field == 'pilot': changed['pilots']['A']['source_sha256'] = '0' * 64
            else: changed['sources']['fresh_learning_campaign.py'] = '0' * 64
            with self.subTest(field=field), patch.object(self.runner, 'LearningPlayerBot',
                    side_effect=AssertionError('policy constructed before proof')):
                with self.assertRaisesRegex(RuntimeHalt, 'FRESH_.*MISMATCH'):
                    self.run_game(previous_record=changed, max_commands=1)

    def test_budget_is_pause_with_no_terminal_or_training_credit(self):
        record = self.run_game(max_commands=1)
        self.assertEqual(record['status'], 'PAUSED')
        self.assertEqual(len(record['commands']), 1)
        self.assertFalse(record['final']['state']['terminal'])
        self.assertIsNone(record['winner'])
        self.assertEqual(record['commands'][0]['decisions'], [])
        self.assertFalse(record['commands'][0]['rating']['learning_eligible'])
        self.assertEqual(record['learning_state_after'], record['learning_state_before'])

    def test_redraw_is_observed_but_never_a_strategic_training_choice(self):
        record = self.run_game()
        for command in record['commands'][1:]:
            self.assertFalse(command['rating']['learning_eligible'])
            self.assertTrue(all(not d['learning_eligible'] for d in command['decisions']))

    def test_wrong_context_campaign_index_or_model_rejected_before_policy(self):
        record = self.run_game()
        for field in ('index', 'context_id', 'campaign_id', 'learning_state_id'):
            changed = copy.deepcopy(record)
            changed[field] = 1 if field == 'index' else 'tampered'
            with self.subTest(field=field), patch.object(self.runner, 'LearningPlayerBot',
                    side_effect=AssertionError('policy constructed before proof')):
                with self.assertRaisesRegex(RuntimeHalt, 'FRESH_.*MISMATCH'):
                    self.run_game(previous_record=changed, max_commands=1)

    def test_failed_post_apply_tracker_guard_keeps_real_committed_snapshot(self):
        with patch.object(self.runner.FieldTracker, 'observe', side_effect=RuntimeHalt('PRIVATE_TRACKER_GUARD')):
            record = self.run_game()
        self.assertEqual(record['status'], 'JUDGE_AUDIT_FAILURE')
        command = record['commands'][-1]
        self.assertEqual(command['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(command['before'], record['initial'])
        self.assertEqual(command['after'], record['final'])
        self.assertNotEqual(command['before']['state'], command['after']['state'])
        self.assertEqual(command['rating']['status'], 'UNRATED')


    def test_selected_pending_generator_keeps_order_and_only_chooses_unresolved_value(self):
        real_apply = self.runner._apply
        def fixture_apply(runtime, kind, seat, args, root):
            if kind == 'RESOLVE_PENDING':
                raise RuntimeHalt('PRIVATE_EFFECT_STILL_PENDING')
            result = real_apply(runtime, kind, seat, args, root)
            if kind == 'REDRAW_CHOICE' and runtime.state.phase == 'START_OF_TURN':
                runtime.state.effect_sequence = 2
                runtime.state.pending = [{'id': 'effect-' + str(i), 'seat': 'A',
                    'source': runtime.state.zones['A']['hand'][0].key, 'effect_id': 'BT22-023.inherited_unsuspend',
                    'field': 'inherited_text', 'instance': 'fixture-entity', 'depth': 0,
                    'trigger': {'drawn_card': 'B:BT22-023#1'}, 'usage': ['PRIVATE_FIXTURE']}
                    for i in (1, 2)]
            return result
        def fixture_options(runtime, seat):
            return copy.deepcopy(runtime.state.pending) if seat == 'A' else []
        def unresolved_value(runtime, seat, selected, adapter):
            return adapter.choose(runtime.public_view(seat), [None, selected['source']])
        with patch.object(self.runner, '_apply', side_effect=fixture_apply), \
                patch.object(self.runner, 'pending_options', side_effect=fixture_options):
            opening = self.run_game()
            with patch.object(self.runner, 'pending_choice', side_effect=RuntimeHalt('PRIVATE_VALUE_GAP')):
                stopped = self.run_game(previous_record=opening, max_commands=1)
            failed = stopped['commands'][-1]
            self.assertEqual(failed['command'], 'GENERATE_PENDING_CHOICES')
            self.assertIn('selected_pending', failed)
            self.assertNotEqual(failed['policy_rng_before_choice'], failed['policy_rng_after_choice'])
            selected = copy.deepcopy(failed['selected_pending'])
            original_choose = self.runner.LearningPlayerBot.choose
            def only_value(bot, view, candidates, *, decision=None):
                self.assertEqual(decision['kind'], 'PENDING_CHOICE')
                self.assertNotIn('trigger', decision['selected_pending'])
                self.assertNotIn('usage', decision['selected_pending'])
                return original_choose(bot, view, candidates, decision=decision)
            with patch.object(self.runner, 'pending_choice', side_effect=unresolved_value), \
                    patch.object(self.runner.LearningPlayerBot, 'choose', new=only_value):
                resumed = self.run_game(previous_record=stopped, max_commands=1)
            retried = resumed['commands'][-1]
            self.assertEqual(retried['command'], 'RESOLVE_PENDING')
            self.assertEqual(retried['args']['pending_id'], selected['id'])
            self.assertEqual(retried['decisions'][0], failed['decisions'][0])
            self.assertEqual(len(retried['decisions']), 2)
            for option in failed['decisions'][0]['candidates']:
                self.assertNotIn('trigger', option)
                self.assertNotIn('usage', option)

    def test_rehashed_policy_transition_and_false_certification_still_fail_replay(self):
        from match_context import digest
        previous = self.run_game()
        for change in ('rng', 'credit', 'certification', 'terminal_reason', 'state_key', 'action_key', 'view_hash', 'bot_id', 'choice'):
            altered = copy.deepcopy(previous)
            if change == 'rng':
                command = altered['commands'][1]
                command['policy_rng_after_choice'] = copy.deepcopy(command['policy_rng_before_choice'])
            elif change in ('state_key', 'action_key'):
                altered['commands'][1]['decisions'][0]['learning'][change] = '0' * 64
            elif change == 'view_hash': altered['commands'][1]['decisions'][0]['public_view_sha256'] = '0' * 64
            elif change == 'bot_id': altered['commands'][1]['decisions'][0]['bot_id'] = '0' * 64
            elif change == 'choice':
                from interaction_learning import _action
                decision = altered['commands'][1]['decisions'][0]
                decision['chosen']['redraw'] = not decision['chosen']['redraw']
                decision['learning']['action_key'] = digest(_action(decision['chosen'], 'A'))
            elif change == 'credit': altered['accepted_fact_finding_credit'] = 60
            elif change == 'certification': altered['certification'] = 'JUDGE_CERTIFIED'
            else: altered['terminal_reason'] = 'fabricated'
            altered['record_sha256'] = digest({k: v for k, v in altered.items() if k != 'record_sha256'})
            with self.subTest(change=change), self.assertRaisesRegex(RuntimeHalt, 'FRESH_.*MISMATCH'):
                self.runner.replay_game(altered, ROOT)


    def test_explicit_commit_rejects_pause_halt_and_unaccepted_commands(self):
        state = self.State()
        paused = self.run_game(learning_state=state)
        before = state.export()
        for status in ('PAUSED', 'HALT', 'JUDGE_AUDIT_FAILURE'):
            altered = copy.deepcopy(paused); altered['status'] = status
            with self.subTest(status=status), self.assertRaises(RuntimeHalt):
                self.runner.commit_completed_game(altered, state, ROOT)
        terminal = self._synthetic_terminal_envelope(paused)
        terminal['commands'][-1]['judge']['accepted'] = False
        with self.assertRaisesRegex(RuntimeHalt, 'ACCEPTED'):
            self.runner.commit_completed_game(terminal, state, ROOT)
        self.assertEqual(state.export(), before)

    def _synthetic_terminal_envelope(self, paused):
        # Tests the commit adapter only. This deliberately cannot pass physical
        # replay and is never presented as a played/completed game.
        from match_context import digest
        terminal = copy.deepcopy(paused)
        terminal.update(status='EXPERIMENTAL_SOFTWARE_TERMINAL', winner='A',
                        terminal_reason='PRIVATE_COMMIT_ADAPTER_FIXTURE')
        terminal['final']['state'].update(terminal=True, winner='A',
                        terminal_reason='PRIVATE_COMMIT_ADAPTER_FIXTURE')
        terminal['record_sha256'] = digest({k: v for k, v in terminal.items() if k != 'record_sha256'})
        return terminal

    def test_commit_adapter_updates_once_with_stable_id_and_separate_log_hash(self):
        from match_context import digest
        state = self.State()
        terminal = self._synthetic_terminal_envelope(self.run_game(learning_state=state))
        # A controlled replay stub isolates between-game integration. It does
        # not certify this synthetic envelope as engine gameplay evidence.
        with patch.object(self.runner, 'replay_game', return_value={'exact_match': True}):
            first = self.runner.commit_completed_game(terminal, state, ROOT)
            after_first = state.export()
            repaired = copy.deepcopy(terminal); repaired['max_commands'] += 1
            repaired['record_sha256'] = digest({k: v for k, v in repaired.items() if k != 'record_sha256'})
            second = self.runner.commit_completed_game(repaired, state, ROOT)
        self.assertTrue(first['updated'])
        self.assertFalse(second['updated'])
        self.assertEqual(state.export(), after_first)
        self.assertEqual(first['game_id'], second['game_id'])
        self.assertNotEqual(first['record_sha256'], second['record_sha256'])
        self.assertEqual(first['game_id'], digest({k: terminal[k] for k in
                         ('campaign_id', 'context_id', 'index', 'seed')}))

    def test_synthetic_terminal_and_tampered_input_cannot_pass_real_commit_replay(self):
        state = self.State()
        terminal = self._synthetic_terminal_envelope(self.run_game(learning_state=state))
        before = state.export()
        with self.assertRaisesRegex(RuntimeHalt, 'FRESH_.*MISMATCH'):
            self.runner.commit_completed_game(terminal, state, ROOT)
        self.assertEqual(state.export(), before)


    def test_cached_pending_value_restores_view_context_for_remaining_bottom_order(self):
        from match_context import digest
        context, _, _ = diagnostic._load_context_selection(ROOT, CONTEXT)
        opening = self.run_game()
        view = opening['commands'][1]['public_view']
        metrics = opening['commands'][1]['decisions'][0]['decision']['public_metrics']
        hand = view['players']['A']['hand']
        selected = {'id': 'private-effect', 'seat': 'A', 'source': hand[0],
                    'effect_id': hand[0].split(':')[1].split('#')[0] + '.search',
                    'field': 'main_text', 'instance': 'private-entity', 'depth': 0}
        decision = {'kind': 'PENDING_CHOICE', 'selected_pending': selected,
                    'effect_id': selected['effect_id'], 'source': selected['source'],
                    'public_metrics': metrics}
        original = self.runner.LearningPlayerBot(context, 'A', self.State(), 1)
        candidates = [[hand[0]], []]
        original.choose(view, candidates, decision=decision)
        saved = copy.deepcopy(original.decision_log[-1])
        checkpoint = original.export_rng()
        original.bottom_order(hand[1:3], public_view=view)
        restored = self.runner.LearningPlayerBot(context, 'A', self.State(), 1)
        restored.restore_rng(checkpoint)
        class PublicTrackerFixture:
            def player_view(_self, seat):
                self.assertEqual(seat, 'A')
                return copy.deepcopy(view)
            def public_metrics(_self): return copy.deepcopy(metrics)
        def no_choice(*args): raise AssertionError('saved value was rerolled')
        adapter = self.runner._Adapter(no_choice, restored, PublicTrackerFixture(), selected, [saved])
        self.assertEqual(adapter.choose(view, candidates), saved['chosen'])
        adapter.bottom_order(hand[1:3])
        self.assertEqual(restored.decision_log[-1], original.decision_log[-1])
        self.assertEqual(restored.decision_log[-1]['public_view_sha256'], digest(view))
        self.assertEqual(restored.export_rng(), checkpoint)


    def test_loaded_source_drift_blocks_before_runtime_or_policy(self):
        changed = copy.deepcopy(self.runner._LOADED_SOURCES)
        changed['interaction_learning.py'] = '0' * 64
        with patch.object(self.runner, '_source_bytes', return_value=changed), \
                patch.object(self.runner, 'ContextRuntime', side_effect=AssertionError('runtime started')), \
                patch.object(self.runner, 'LearningPlayerBot', side_effect=AssertionError('policy started')):
            with self.assertRaisesRegex(RuntimeHalt, 'FRESH_LOADED_SOURCES_MISMATCH'):
                self.run_game()

    def test_transactional_engine_halt_event_replays_and_retry_keeps_selection(self):
        real_apply = self.runner._apply
        def private_gap(runtime, kind, seat, args, root):
            if kind == 'REDRAW_CHOICE':
                def unavailable(trial, owner, choice):
                    raise RuntimeHalt('PRIVATE_ENGINE_UNIMPLEMENTED')
                return runtime._control_command(kind, seat, args, unavailable)
            return real_apply(runtime, kind, seat, args, root)
        with patch.object(self.runner, '_apply', side_effect=private_gap):
            stopped = self.run_game()
        self.assertEqual(stopped['events'][-1]['type'], 'HALT')
        self.assertTrue(self.runner.replay_game(stopped, ROOT)['exact_match'])
        with patch.object(self.runner.LearningPlayerBot, 'choose', side_effect=AssertionError('rerolled')):
            resumed = self.run_game(previous_record=stopped, max_commands=1)
        self.assertEqual(resumed['commands'][-1]['args'], stopped['commands'][-1]['args'])
        self.assertEqual(resumed['policy_rng_final'], stopped['policy_rng_final'])
        self.assertTrue(self.runner.replay_game(resumed, ROOT)['exact_match'])


if __name__ == '__main__':
    unittest.main()
