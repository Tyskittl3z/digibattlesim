"""A repaired engine continues saved decisions without rerolling their game."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from context_runtime import RuntimeHalt
from match_context import digest
import imported_attempts as runner


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / 'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02'


class GameContinuationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(runner, 'continue_attempt', None)),
                        'Saved games need a continuation API, not fresh pilot rerolls')

    def saved(self, index=0):
        return json.loads(gzip.decompress((COHORT / f'attempt-{index:04d}.json.gz').read_bytes()))

    def test_actual_rina_halt_replays_decisions_and_continues_into_opponents_turn(self):
        previous = self.saved()
        before = copy.deepcopy(previous)
        source_bytes = (COHORT / 'attempt-0000.json.gz').read_bytes()
        continued = runner.continue_attempt(previous, ROOT, max_commands=30)
        self.assertEqual(previous, before)
        self.assertEqual((COHORT / 'attempt-0000.json.gz').read_bytes(), source_bytes)
        for field in ('context_id', 'seed', 'first', 'index'):
            self.assertEqual(continued[field], previous[field])
        successful = previous['commands'][:-1]
        for original, revalidated in zip(successful, continued['commands']):
            self.assertEqual((revalidated['command'], revalidated['seat'], revalidated['args']),
                             (original['command'], original['seat'], original['args']))
            self.assertEqual(revalidated['status'], 'EXPERIMENTAL_RESOLVED')
            self.assertEqual(revalidated['decision_origin']['kind'], 'REVALIDATED_SAVED_COMMAND')
        retry = continued['commands'][len(successful)]
        self.assertEqual(retry['command'], 'PLAY_CARD')
        self.assertEqual(retry['args'], previous['commands'][-1]['args'])
        self.assertEqual(retry['status'], 'EXPERIMENTAL_RESOLVED')
        resolution = continued['commands'][len(successful) + 1]
        self.assertEqual(resolution['command'], 'RESOLVE_PENDING')
        self.assertEqual(resolution['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(resolution['result']['processing'], 'NO_ELIGIBLE_TARGET')
        self.assertTrue(any(command.get('public_view', {}).get('active') == 'B'
                            and command.get('public_view', {}).get('turn', 0) >= 2
                            for command in continued['commands']))
        lineage = continued['continuation_provenance']
        self.assertEqual(lineage['previous_record_sha256'], digest(previous))
        self.assertEqual(lineage['previous_execution_id'], previous['replay_provenance']['execution_id'])
        self.assertEqual(lineage['previous_pilots'], previous['pilots'])
        self.assertEqual(lineage['successful_commands_revalidated'], len(successful))
        proof = lineage['physical_state_proof']
        self.assertEqual(proof['original_before_sha256'], proof['revalidated_before_sha256'])
        self.assertEqual(proof['original_rng_sha256'], digest(previous['halts'][-1]['before']['rng_state']))
        for seat, manifest in continued['pilots'].items():
            self.assertEqual(manifest['policy_segment']['previous_record_sha256'], digest(previous))
            self.assertEqual(lineage['policy_segment']['pilots'][seat], manifest)
            self.assertNotEqual(manifest['pilot_id'], previous['pilot_id'][seat])
        self.assertEqual(continued['accepted_fact_finding_credit'], 0)
        self.assertEqual(continued['final_evaluation_credit'], 0)

    def test_continuation_replays_entire_new_record_exactly_and_preserves_caller(self):
        record = runner.continue_attempt(self.saved(), ROOT, max_commands=16)
        before = copy.deepcopy(record)
        replay = runner.replay_attempt(record, ROOT)
        self.assertTrue(replay['exact_match'])
        self.assertEqual(replay['saved_record_sha256'], replay['replayed_record_sha256'])
        self.assertEqual(record, before)
        record['continuation_provenance']['previous_record']['commands'][1]['args']['redraw'] = False
        with self.assertRaisesRegex(RuntimeHalt, 'CONTINUATION_PREVIOUS_RECORD_HASH_MISMATCH'):
            runner.replay_attempt(record, ROOT)

    def test_changed_context_hash_or_identity_is_rejected_before_gameplay(self):
        record = self.saved()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / record['replay_provenance']['context_file']
            path.parent.mkdir(parents=True)
            path.write_bytes((ROOT / record['replay_provenance']['context_file']).read_bytes() + b'\n')
            with patch.object(runner, 'ContextRuntime', side_effect=AssertionError('gameplay started')):
                with self.assertRaisesRegex(RuntimeHalt, 'REPLAY_CONTEXT_FILE_CHANGED'):
                    runner.continue_attempt(record, root)
        record['context_id'] = 'wrong-context'
        with patch.object(runner, 'ContextRuntime', side_effect=AssertionError('gameplay started')):
            with self.assertRaisesRegex(RuntimeHalt, 'REPLAY_CONTEXT_ID_MISMATCH'):
                runner.continue_attempt(record, ROOT)

    def test_prior_wrong_decision_cannot_be_replaced_to_reach_the_old_checkpoint(self):
        record = self.saved()
        record['commands'][1]['args']['redraw'] = False
        with self.assertRaisesRegex(RuntimeHalt, 'CONTINUATION_PREFIX_PUBLIC_VIEW_MISMATCH'):
            runner.continue_attempt(record, ROOT)
        record = self.saved()
        record['commands'][0]['command'] = 'PASS_TURN'
        with self.assertRaisesRegex(RuntimeHalt, 'CONTINUATION_PREFIX_ACTION_FAILED'):
            runner.continue_attempt(record, ROOT)

    def test_original_before_halt_physical_state_and_rng_are_proved(self):
        for field in ('rng_state', 'state'):
            record = self.saved()
            if field == 'rng_state':
                record['halts'][-1]['before'][field][1][0] ^= 1
            else:
                record['halts'][-1]['before'][field]['memory'] += 1
            # Keep the saved final consistent so the actual replayed checkpoint
            # must catch the tampering, rather than a superficial record check.
            record['final'] = copy.deepcopy(record['halts'][-1]['before'])
            with self.subTest(field=field), self.assertRaisesRegex(
                    RuntimeHalt, 'CONTINUATION_BEFORE_HALT_PHYSICAL_MISMATCH'):
                runner.continue_attempt(record, ROOT)

    def test_generator_checkpoint_without_selected_action_resumes_its_window(self):
        record = runner.run_attempt(0, ROOT, max_commands=1,
                                    context_file=self.saved()['replay_provenance']['context_file'])
        self.assertEqual(record['commands'][-1]['command'], 'COMMAND_BUDGET')
        continued = runner.continue_attempt(record, ROOT, max_commands=5)
        self.assertEqual(continued['commands'][1]['command'], 'REDRAW_CHOICE')
        self.assertEqual(continued['commands'][1]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(continued['continuation_provenance']['retry']['kind'], 'RESUME_GENERATOR_WINDOW')
        self.assertTrue(runner.replay_attempt(continued, ROOT)['exact_match'])

    def test_main_generator_failure_with_no_selection_resumes_without_rerolling_prefix(self):
        with patch.object(runner, 'main_candidates', side_effect=RuntimeHalt('GENERATOR_NOT_IMPLEMENTED')):
            record = runner.run_attempt(0, ROOT, max_commands=20,
                context_file=self.saved()['replay_provenance']['context_file'])
        self.assertEqual(record['commands'][-1]['command'], 'GENERATE_MAIN_CANDIDATES')
        self.assertNotIn('args', record['commands'][-1])
        continued = runner.continue_attempt(record, ROOT, max_commands=20)
        next_command = continued['commands'][len(record['commands']) - 1]
        self.assertNotEqual(next_command['command'], 'GENERATE_MAIN_CANDIDATES')
        self.assertEqual(continued['continuation_provenance']['retry']['kind'], 'RESUME_GENERATOR_WINDOW')
        self.assertTrue(runner.replay_attempt(continued, ROOT)['exact_match'])

    def test_selected_pending_effect_survives_a_choice_generator_failure(self):
        with patch.object(runner, 'pending_choice', side_effect=RuntimeHalt('CHOICE_NOT_IMPLEMENTED')):
            previous = runner.continue_attempt(self.saved(), ROOT, max_commands=12)
        failed = previous['commands'][-1]
        self.assertEqual(failed['command'], 'GENERATE_PENDING_CHOICES')
        self.assertEqual(failed['selected_pending']['effect_id'], 'BT11-112.on_play_grant')
        continued = runner.continue_attempt(previous, ROOT, max_commands=12)
        retry_index = len(previous['commands']) - 1
        retry = continued['commands'][retry_index]
        self.assertEqual(retry['command'], 'RESOLVE_PENDING')
        self.assertEqual(retry['args']['pending_id'], failed['selected_pending']['id'])
        self.assertEqual(retry['result']['processing'], 'NO_ELIGIBLE_TARGET')
        self.assertEqual(continued['continuation_provenance']['policy_segment'][
            'first_new_decision_command_index'], retry_index)
        self.assertTrue(runner.replay_attempt(continued, ROOT)['exact_match'])

    def test_repaired_training_option_retries_the_same_selected_physical_card(self):
        record = self.saved(12)
        before = copy.deepcopy(record)
        continued = runner.continue_attempt(record, ROOT, max_commands=30)
        self.assertEqual(record, before)
        retry = continued['commands'][len(record['commands']) - 1]
        self.assertEqual(retry['command'], 'USE_OPTION')
        self.assertEqual(retry['args'], record['commands'][-1]['args'])
        self.assertEqual(retry['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(retry['result']['used_card'], record['commands'][-1]['args']['hand_key'])
        self.assertGreater(len(continued['commands']), len(record['commands']))
        self.assertTrue(runner.replay_attempt(continued, ROOT)['exact_match'])

    def test_legacy_option_and_battle_evolution_keep_inputs_when_mapping_to_current_api(self):
        for index, expected in ((19, 'USE_OPTION'), (27, 'BATTLE_EVOLUTION')):
            record = self.saved(index)
            with self.subTest(index=index):
                continued = runner.continue_attempt(record, ROOT, max_commands=30)
                retry = continued['commands'][len(record['commands']) - 1]
                self.assertEqual(retry['command'], expected)
                self.assertEqual(retry['args'], record['commands'][-1]['args'])
                self.assertEqual(continued['continuation_provenance']['retry']['current_command'], expected)
                self.assertTrue(runner.replay_attempt(continued, ROOT)['exact_match'])

    def test_successful_prefix_uses_recorded_decisions_before_any_new_pilot_choice(self):
        previous = self.saved()
        observed = []
        real_choose = runner.ReferencePilot.choose

        def choose(pilot, view, candidates):
            observed.append(copy.deepcopy(candidates))
            return real_choose(pilot, view, candidates)

        with patch.object(runner.ReferencePilot, 'choose', choose):
            runner.continue_attempt(previous, ROOT, max_commands=10)
        self.assertTrue(observed, 'The repaired On Play must reach a new explicit choice')
        self.assertEqual(observed[0][0]['effect_id'], 'BT11-112.on_play_grant')

    def test_second_continuation_preserves_the_extended_game_and_nested_lineage(self):
        first = runner.continue_attempt(self.saved(), ROOT, max_commands=12)
        before = copy.deepcopy(first)
        second = runner.continue_attempt(first, ROOT, max_commands=18)
        self.assertEqual(first, before)
        self.assertEqual(second['continuation_provenance']['previous_record_sha256'], digest(first))
        self.assertEqual(second['continuation_provenance']['successful_commands_revalidated'],
                         sum(command['status'] == 'EXPERIMENTAL_RESOLVED' for command in first['commands']))
        self.assertTrue(runner.replay_attempt(second, ROOT)['exact_match'])

    def test_tamer_play_and_observer_adapters_choose_from_explicit_public_choices(self):
        from battle_evolution import choose_battle_evolution
        from effect_scheduler import pending_options, resolve_pending
        import tamer_play_effects as tamers

        record = self.saved(59)
        context, _, _ = runner._load_context_selection(ROOT, record['replay_provenance']['context_file'])
        runtime = runner.ContextRuntime(context, record['seed'], record['first'],
            runner.build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            runner._apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        args = record['commands'][-1]['args']
        choose_battle_evolution(runtime, 'B', args['source_key'], args['hand_key'], args['route_index'], ROOT)
        pilot = runner.ReferencePilot(context.matchup_id, record['index'], 'B')
        selected = pending_options(runtime, 'B')[0]
        self.assertEqual(selected['effect_id'], tamers.PLAY_EFFECT)
        self.assertIn(runner.pending_choice(runtime, 'B', selected, pilot),
                      tamers.tamer_play_choices(runtime, 'B', selected['source'], tamers.PLAY_EFFECT))
        resolve_pending(runtime, 'B', selected['id'], 'B:BT11-112#2')
        observer = next(item for item in pending_options(runtime, 'B')
                        if item['effect_id'] == tamers.OBSERVER_EFFECT)
        self.assertIn(runner.pending_choice(runtime, 'B', observer, pilot),
                      tamers.tamer_play_choices(runtime, 'B', observer['source'], tamers.OBSERVER_EFFECT))

    def test_actual_veedramon_tamer_and_egg_choices_reach_the_runner(self):
        from effect_scheduler import pending_options,resolve_pending
        import tamer_play_effects as tamers
        path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-02/game-0000-segment.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context,_,_=runner._load_context_selection(ROOT,record['replay_provenance']['context_file'])
        runtime=runner.ContextRuntime(context,record['seed'],record['first'],
            runner.build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            runner._apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        failed=record['commands'][-1]
        runner._apply(runtime,failed['command'],failed['seat'],failed['args'],ROOT)
        pilot=runner.ReferencePilot(context.matchup_id,record['index'],'B')
        selected=pending_options(runtime,'B')[0]
        self.assertEqual(selected['effect_id'],'BT22-022.play_tamer')
        self.assertIn(runner.pending_choice(runtime,'B',selected,pilot),
                      tamers.tamer_play_choices(runtime,'B',selected['source'],selected['effect_id']))
        resolve_pending(runtime,'B',selected['id'],'B:BT11-112#3')
        egg=next(p for p in pending_options(runtime,'B')
                 if p['effect_id']=='EX13-002.tamer_play_unsuspend')
        self.assertIn(runner.pending_choice(runtime,'B',egg,pilot),[False,True])

    def test_actual_end_unsuspend_rina_choices_route_after_the_draw(self):
        from effect_scheduler import pending_options,resolve_pending
        import rina_unsuspend_effects as rina
        path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-05/game-0000-segment.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context,_,_=runner._load_context_selection(ROOT,record['replay_provenance']['context_file'])
        runtime=runner.ContextRuntime(context,record['seed'],record['first'],
            runner.build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            runner._apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        failed=record['commands'][-1]
        runner._apply(runtime,failed['command'],failed['seat'],failed['args'],ROOT)
        pilot=runner.ReferencePilot(context.matchup_id,record['index'],'B')
        group=pending_options(runtime,'B')
        memory=next(p for p in group if p['effect_id']==rina.BT11_MEMORY_EFFECT)
        self.assertIsNone(runner.pending_choice(runtime,'B',memory,pilot))
        draw=next(p for p in group if p['effect_id']==rina.EX13_DRAW_EFFECT)
        self.assertIn(runner.pending_choice(runtime,'B',draw,pilot),[False,True])
        resolve_pending(runtime,'B',draw['id'],True)
        after=pending_options(runtime,'B')
        self.assertEqual(len(after),1)
        self.assertEqual(after[0]['effect_id'],rina.EX13_EVOLVE_EFFECT)
        self.assertIn('B:EX13-023#1',runtime.public_view('B')['players']['B']['hand'])
        self.assertIn(runner.pending_choice(runtime,'B',after[0],pilot),
                      rina.rina_unsuspend_choices(runtime,'B',after[0]['source'],after[0]['effect_id']))

    def test_actual_suspension_rina_routes_one_immediate_effect_without_bonus_draw(self):
        from effect_scheduler import pending_options,resolve_pending
        from ex13_ulforce_effects import RETURN_EFFECT
        import rina_reactivation as rina
        path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-08/game-0000-segment.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context,_,_=runner._load_context_selection(ROOT,record['replay_provenance']['context_file'])
        runtime=runner.ContextRuntime(context,record['seed'],record['first'],
            runner.build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            runner._apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        failed=record['commands'][-1]
        runner._apply(runtime,failed['command'],failed['seat'],failed['args'],ROOT)
        selected=next(p for p in pending_options(runtime,'B') if p['effect_id']==rina.REACTIVATION_EFFECT)
        pilot=runner.ReferencePilot(context.matchup_id,record['index'],'B')
        self.assertEqual(rina.rina_reactivation_choices(runtime,'B',selected['source']),[None,RETURN_EFFECT])
        self.assertIn(runner.pending_choice(runtime,'B',selected,pilot),[None,RETURN_EFFECT])
        zones=copy.deepcopy(runtime.state.zones);rng=runtime.snapshot()['rng_state']
        resolve_pending(runtime,'B',selected['id'],RETURN_EFFECT)
        self.assertTrue(runtime.state.battle['B'][selected['source']].suspended)
        self.assertEqual(runtime.state.zones,zones);self.assertEqual(runtime.snapshot()['rng_state'],rng)
        immediate=pending_options(runtime,'B')
        self.assertEqual(len(immediate),1)
        self.assertEqual((immediate[0]['effect_id'],immediate[0]['depth']),(RETURN_EFFECT,4))
        self.assertNotEqual(immediate[0]['id'],'effect-35')
        self.assertTrue(any(p['id']=='effect-35' and p['depth']==2 for p in runtime.state.pending))


if __name__ == '__main__':
    unittest.main()
