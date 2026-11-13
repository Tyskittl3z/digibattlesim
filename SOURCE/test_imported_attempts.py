"""Diagnostic attempts remain reproducible, fresh, and worth zero match credit."""
import gzip
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime, RuntimeHalt, Stack
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry


ROOT = Path(__file__).resolve().parents[1]


class ImportedAttemptTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('imported_attempts'),
                             'The imported diagnostic runner must exist')
        self.runner = importlib.import_module('imported_attempts')

    def runtime(self, *, mirror=False):
        context_file = ('ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json' if mirror
                        else 'ARTIFACTS/ex13-engine-2026-10-30/context.json')
        context = load_context_file(ROOT / context_file)
        runtime = ContextRuntime(context, 19, 'A', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        runtime.state.memory = 10
        return runtime

    def take(self, runtime, seat, number, zone='hand'):
        cards = runtime.state.zones[seat]['deck']
        physical = next(c for c in cards if c.card_number == number)
        cards.remove(physical)
        if zone == 'battle':
            runtime.state.battle[seat][physical.key] = Stack(
                [physical], played_turn=1, ready_since_turn=2)
        else:
            runtime.state.zones[seat][zone].append(physical)
        return physical.key

    def test_seed_schedule_is_context_bound_and_fresh_without_prior_training(self):
        runtime = self.runtime()
        context_id = runtime.context.matchup_id
        seeds = [self.runner.seed_for(i, context_id) for i in range(4)]
        self.assertEqual(len(set(seeds)), 4)
        self.assertEqual(seeds[0], self.runner.seed_for(0, context_id))
        self.assertNotEqual(seeds[0], self.runner.seed_for(0, 'different-context'))
        first = self.runner.ReferencePilot(context_id, 0, 'A')
        second = self.runner.ReferencePilot(context_id, 1, 'A')
        self.assertNotEqual(first.manifest()['pilot_id'], second.manifest()['pilot_id'])
        for pilot in (first, second):
            self.assertEqual(pilot.manifest()['training_data'], [])
            self.assertIsNone(pilot.manifest()['roadmap'])
            self.assertEqual(pilot.manifest()['strategy_status'], 'FRESH_UNTRAINED_RANDOM_REFERENCE')

    def test_replay_failure_never_loses_original_seed_or_halt_trace(self):
        for failure in ('mismatch','exception'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/'cohort'
                kwargs={'return_value':{'exact_match':False}} if failure=='mismatch' else {
                    'side_effect':RuntimeError('injected replay interruption')}
                with patch.object(self.runner,'replay_attempt',**kwargs):
                    with self.assertRaises((RuntimeHalt,RuntimeError)):
                        self.runner.write_attempts(out,ROOT,count=2,max_commands=1)
                original=out/'attempt-0000.json.gz'
                self.assertTrue(original.exists(),'original attempted seed/trace must precede replay verification')
                record=json.loads(gzip.decompress(original.read_bytes()))
                self.assertEqual(record['index'],0);self.assertEqual(record['status'],'HALT')
                self.assertTrue(record['events']);self.assertTrue(record['halts'])
                note=json.loads((out/'replay-failure-0000.json').read_bytes())
                self.assertEqual(note['seed'],record['seed'])
                self.assertEqual(note['status'],'REPLAY_FAILED_OR_INTERRUPTED')
                self.assertFalse((out/'attempt-0001.json.gz').exists())

    def test_unknown_payable_hand_cards_are_candidates_without_support_filter(self):
        runtime = self.runtime()
        plain = self.take(runtime, 'A', 'EX1-013')
        unknown = self.take(runtime, 'A', 'EX13-023')
        option = self.take(runtime, 'A', 'LM-028')
        runtime.state.breeding['A'].append(runtime.state.zones['A']['eggdeck'].pop())
        candidates = self.runner.main_candidates(runtime, 'A', ROOT)
        by_key = {c['hand_key']: c for c in candidates if 'hand_key' in c}
        self.assertEqual(set(by_key), {plain, unknown, option})
        self.assertEqual(by_key[unknown]['kind'], 'PLAY_CARD')
        self.assertEqual(by_key[option]['kind'], 'USE_OPTION')
        self.assertEqual(by_key[option]['legality'], 'UNVERIFIED_OPTION_ACTION')
        self.assertTrue(any(c['kind'] == 'PASS_TURN' for c in candidates))

    def test_main_delay_candidates_require_prior_placement_and_exclude_start_turn_scramble(self):
        for number in ('P-104', 'LM-034', 'LM-056', 'LM-057', 'LM-058', 'LM-028'):
            for placed in (None, 3, 2):
                with self.subTest(number=number, played_turn=placed):
                    runtime = self.runtime(mirror=True)
                    source = self.take(runtime, 'A', number, 'battle')
                    runtime.state.battle['A'][source].played_turn = placed
                    before = runtime.snapshot()
                    delays = [c for c in self.runner.main_candidates(runtime, 'A', ROOT)
                              if c['kind'] in ('OPTION_DELAY', 'UNKNOWN_DELAY_ACTION')]
                    self.assertEqual(runtime.snapshot(), before)
                    expected = number != 'LM-028' and placed == 2
                    self.assertEqual([c['source_key'] for c in delays], [source] if expected else [])
                    self.assertTrue(all(c['kind'] == 'OPTION_DELAY' for c in delays))

    def test_runner_applies_main_delay_then_uses_explicit_activation_choice(self):
        from effect_scheduler import pending_options
        runtime = self.runtime(mirror=True)
        source = self.take(runtime, 'A', 'LM-034', 'battle')
        chosen = next(c for c in self.runner.main_candidates(runtime, 'A', ROOT)
                      if c['kind'] == 'OPTION_DELAY')
        self.runner._apply(runtime, chosen['kind'], 'A', chosen, ROOT)
        selected = pending_options(runtime, 'A')[0]
        pilot = self.runner.ReferencePilot(runtime.context.matchup_id, 0, 'A')
        with patch.object(pilot, 'choose', return_value={'activate': True}) as choose:
            choice = self.runner.pending_choice(runtime, 'A', selected, pilot)
        self.assertEqual(choose.call_args.args[1], [{'activate': False}, {'activate': True}])
        runtime.state.memory = 3
        self.runner._apply(runtime, 'RESOLVE_PENDING', 'A',
                           {'pending_id': selected['id'], 'choice': choice}, ROOT)
        self.assertEqual(runtime.state.memory, 5)
        self.assertNotIn(source, runtime.state.battle['A'])
        self.assertIn(source, [c.key for c in runtime.state.zones['A']['trash']])
        runtime.verify()

    def test_runner_handles_option_evolution_and_search_choice_schemas(self):
        from effect_scheduler import pending_options
        from option_actions import option_choices
        for number in ('LM-028', 'LM-056'):
            with self.subTest(number=number):
                runtime = self.runtime(mirror=True)
                source = self.take(runtime, 'A', number)
                runtime.state.breeding['A'].append(runtime.state.zones['A']['eggdeck'].pop())
                self.runner._apply(runtime, 'USE_OPTION', 'A', {'hand_key': source}, ROOT)
                selected = pending_options(runtime, 'A')[0]
                exposed = option_choices(runtime, 'A', source, selected['effect_id'])
                pilot = self.runner.ReferencePilot(runtime.context.matchup_id, 0, 'A')
                choice = self.runner.pending_choice(runtime, 'A', selected, pilot)
                if number == 'LM-028':
                    self.assertIn(choice, exposed['choices'])
                else:
                    self.assertIn(choice['selected'], exposed['selections'])
                    self.assertEqual(set(choice['bottom_order']),
                                     set(exposed['revealed']) - set(choice['selected']))
                self.runner._apply(runtime, 'RESOLVE_PENDING', 'A',
                                   {'pending_id': selected['id'], 'choice': choice}, ROOT)
                self.assertIn(source, runtime.state.battle['A'])
                runtime.verify()

    def test_legacy_selected_main_delay_retries_same_source_without_rerolling_prefix(self):
        # Synthetic compatibility fixture: retain Game0's saved decisions, then
        # choose Wisteria's use and a later Main Delay under the legacy name.
        saved = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-02-01/game-0000-segment-01.json.gz'
        checkpoint = json.loads(gzip.decompress(saved.read_bytes()))
        real_candidates = self.runner.main_candidates

        def legacy_candidates(runtime, seat, root):
            candidates = real_candidates(runtime, seat, root)
            for candidate in candidates:
                if candidate['kind'] == 'OPTION_DELAY':
                    candidate['kind'] = 'UNKNOWN_DELAY_ACTION'
            return candidates

        def choose(pilot, view, candidates):
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get('kind') in (
                        'USE_OPTION', 'UNKNOWN_DELAY_ACTION'):
                    key = candidate.get('hand_key', candidate.get('source_key', ''))
                    if 'LM-034' in key:
                        return candidate
            return next((c for c in candidates if isinstance(c, dict)
                         and c.get('kind') == 'PASS_TURN'), candidates[0])

        with patch.object(self.runner, 'main_candidates', side_effect=legacy_candidates), \
                patch.object(self.runner.ReferencePilot, 'choose', new=choose):
            legacy = self.runner.continue_attempt(checkpoint, ROOT, max_commands=60)
        failed = legacy['commands'][-1]
        self.assertEqual(failed['command'], 'UNKNOWN_DELAY_ACTION')
        self.assertEqual(failed['args']['source_key'], 'A:LM-034#1')
        continued = self.runner.continue_attempt(legacy, ROOT, max_commands=len(legacy['commands']))
        retried = continued['commands'][len(legacy['commands']) - 1]
        self.assertEqual(retried['command'], 'OPTION_DELAY')
        self.assertEqual(retried['args'], failed['args'])
        self.assertEqual(retried['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(continued['seed'], checkpoint['seed'])
        self.assertEqual(continued['continuation_provenance']['retry']['current_command'], 'OPTION_DELAY')
        proof = continued['continuation_provenance']['physical_state_proof']
        self.assertEqual(proof['original_before_sha256'], proof['revalidated_before_sha256'])
        self.assertTrue(self.runner.replay_attempt(continued, ROOT)['exact_match'])

    def test_generator_does_not_validate_an_attack_before_one_is_selected(self):
        runtime = self.runtime()
        self.take(runtime, 'B', 'EX13-015', 'battle')
        choices=self.runner.main_candidates(runtime,'A',ROOT)
        self.assertTrue(any(c['kind']=='PASS_TURN' for c in choices))
        self.assertEqual(runtime.state.memory,10)

    def test_generator_does_not_validate_breeding_evolution_before_selection(self):
        r=self.runtime();self.take(r,'A','BT11-032','battle')
        egg=r.state.zones['A']['eggdeck'].pop();r.state.breeding['A']=[egg]
        rookie=self.take(r,'A','EX13-017')
        choices=self.runner.main_candidates(r,'A',ROOT)
        self.assertTrue(any(c['kind']=='PASS_TURN' for c in choices))
        evolutions=[c for c in choices if c['kind']=='BREEDING_EVOLUTION' and c['hand_key']==rookie]
        self.assertTrue(evolutions)
        before=r.snapshot()['state']['battle']
        self.runner._apply(r,'BREEDING_EVOLUTION','A',evolutions[0],ROOT)
        self.assertEqual(before,r.snapshot()['state']['battle'])
        self.assertEqual(r.state.breeding['A'][-1].key,rookie);r.verify()

    def test_printed_battle_evolution_is_visible_and_selected_action_queues_its_effect(self):
        from context_evolution import printed_evolution_options
        runtime = self.runtime()
        source = self.take(runtime, 'A', 'EX1-013', 'battle')
        target = self.take(runtime, 'A', 'P-138')
        before = runtime.snapshot()
        candidates = self.runner.main_candidates(runtime, 'A', ROOT)
        self.assertEqual(runtime.snapshot(),before)
        evolutions = [c for c in candidates if c['kind'] == 'BATTLE_EVOLUTION']
        routes = printed_evolution_options(runtime.context, 'A', 'EX1-013', 'P-138')
        self.assertEqual([(c['source_key'], c['hand_key'], c['route_index'], c['cost'])
                          for c in evolutions],
                         [(source, target, index, route.cost) for index, route in enumerate(routes)])
        self.assertTrue(all(c['legality'] == 'PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY'
                            for c in evolutions))
        self.runner._apply(runtime,'BATTLE_EVOLUTION','A',evolutions[0],ROOT)
        self.assertEqual([c.key for c in runtime.state.battle['A'][target].cards],[source,target])
        self.assertEqual(runtime.state.memory,10-routes[0].cost)
        self.assertEqual(runtime.state.pending[0]['effect_id'],'P-138.on_play_search')
        runtime.verify()

    def test_pilot_identity_and_evidence_bind_runner_policy_bytes(self):
        context_id = self.runtime().context.matchup_id
        pilot = self.runner.ReferencePilot(context_id, 0, 'A')
        runner_hash = hashlib.sha256(Path(self.runner.__file__).read_bytes()).hexdigest()
        self.assertIn('runner_sha256', pilot.manifest())
        self.assertEqual(pilot.manifest()['runner_sha256'], runner_hash)
        record = self.runner.run_attempt(0, ROOT, max_commands=1)
        self.assertEqual(record['replay_provenance']['runner_sha256'], runner_hash)
        self.assertTrue(all(value['runner_sha256'] == runner_hash for value in record['pilots'].values()))

    def test_cannot_suspend_prevents_an_attack_candidate(self):
        from effect_grants import grant_effect
        runtime=self.runtime();runtime.state.active='B'
        target=self.take(runtime,'B','ST7-05','battle')
        source=self.take(runtime,'A','EX13-022','battle')
        grant_effect(runtime,'A',target,{'restrictions':['cannot_suspend']},source,
                     target_owner='B')
        choices=self.runner.main_candidates(runtime,'B',ROOT)
        self.assertFalse(any(c['kind']=='DECLARE_ATTACK' and c['attacker']==target for c in choices))
        self.assertTrue(any(c['kind']=='PASS_TURN' for c in choices))

    def test_plain_attack_candidates_use_public_orientation_and_readiness(self):
        runtime = self.runtime()
        attacker = self.take(runtime, 'A', 'EX1-013', 'battle')
        target = self.take(runtime, 'B', 'ST7-05', 'battle')
        runtime.state.battle['B'][target].suspended = True
        candidates = self.runner.main_candidates(runtime, 'A', ROOT)
        attacks = [c for c in candidates if c['kind'] == 'DECLARE_ATTACK']
        self.assertEqual({(c['attacker'], c['target']) for c in attacks},
                         {(attacker, 'PLAYER'), (attacker, target)})
        runtime.state.battle['A'][attacker].played_turn = runtime.state.turn
        self.assertFalse(any(c['kind'] == 'DECLARE_ATTACK'
                             for c in self.runner.main_candidates(runtime, 'A', ROOT)))

    def test_suspended_tamer_is_not_a_battle_attack_target(self):
        runtime=self.runtime()
        attacker=self.take(runtime,'A','EX1-013','battle')
        tamer=self.take(runtime,'B','BT19-080','battle')
        runtime.state.battle['B'][tamer].suspended=True
        attacks=[c for c in self.runner.main_candidates(runtime,'A',ROOT)
                 if c['kind']=='DECLARE_ATTACK']
        self.assertEqual(attacks,[{'kind':'DECLARE_ATTACK','attacker':attacker,'target':'PLAYER'}])

    def test_hidden_opponent_order_does_not_change_candidates_or_pilot_choice(self):
        runtime = self.runtime()
        self.take(runtime, 'A', 'EX1-013')
        before = self.runner.main_candidates(runtime, 'A', ROOT)
        view = runtime.public_view('A')
        runtime.state.zones['B']['deck'].reverse()
        self.assertEqual(before, self.runner.main_candidates(runtime, 'A', ROOT))
        self.assertEqual(view, runtime.public_view('A'))
        a = self.runner.ReferencePilot(runtime.context.matchup_id, 0, 'A')
        b = self.runner.ReferencePilot(runtime.context.matchup_id, 0, 'A')
        self.assertEqual(a.choose(view, before), b.choose(runtime.public_view('A'), before))

    def test_breeding_candidates_never_offer_promotion_for_an_egg(self):
        runtime = self.runtime()
        runtime.state.phase = 'BREEDING'
        self.assertEqual({c['action'] for c in self.runner.breeding_candidates(
            runtime.context, runtime.public_view('A'), 'A')}, {'skip', 'hatch'})
        runtime.state.breeding['A'].append(runtime.state.zones['A']['eggdeck'].pop())
        self.assertEqual(self.runner.breeding_candidates(
            runtime.context, runtime.public_view('A'), 'A'),
            [{'kind': 'BREEDING_CHOICE', 'action': 'skip'}])
        key = self.take(runtime, 'A', 'EX1-013')
        card = next(c for c in runtime.state.zones['A']['hand'] if c.key == key)
        runtime.state.zones['A']['hand'].remove(card)
        runtime.state.breeding['A'].append(card)
        self.assertEqual({c['action'] for c in self.runner.breeding_candidates(
            runtime.context, runtime.public_view('A'), 'A')}, {'skip', 'promote'})

    def test_pending_boolean_memory_and_search_choices_are_explicit(self):
        from effect_scheduler import pending_options
        from main_actions import choose_play
        from search_effects import search_choices
        runtime = self.runtime()
        pilot = self.runner.ReferencePilot(runtime.context.matchup_id, 0, 'A')
        selected = {'effect_id': 'EX13-022.inherited_unsuspend'}
        self.assertIs(type(self.runner.pending_choice(runtime, 'A', selected, pilot)), bool)
        selected = {'effect_id': 'P-138.unsuspend_memory'}
        self.assertIsNone(self.runner.pending_choice(runtime, 'A', selected, pilot))
        key = self.take(runtime, 'A', 'BT11-023')
        choose_play(runtime, 'A', key, ROOT)
        pending = pending_options(runtime, 'A')[0]
        legal = search_choices(runtime, 'A', key)
        choice = self.runner.pending_choice(runtime, 'A', pending, pilot)
        self.assertIn(choice['selected'], legal['selections'])
        self.assertEqual(set(choice['bottom_order']), set(legal['revealed']) - set(choice['selected']))
        with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECT_CHOICE_UNSUPPORTED'):
            self.runner.pending_choice(runtime, 'A', {'effect_id': 'unknown.effect'}, pilot)

    def test_pending_orientation_choice_uses_own_current_digimon(self):
        from effect_scheduler import pending_options,queue_effects
        from selected_mechanics import ORIENTATION_EFFECT,orientation_candidates
        runtime=self.runtime()
        source=self.take(runtime,'A','EX13-023','battle')
        queue_effects(runtime,[{'seat':'A','source':source,'effect_id':ORIENTATION_EFFECT,
            'field':'main_text','trigger':{'kind':'When Digivolving'}}])
        selected=pending_options(runtime,'A')[0]
        pilot=self.runner.ReferencePilot(runtime.context.matchup_id,0,'A')
        self.assertIn(self.runner.pending_choice(runtime,'A',selected,pilot),
                      orientation_candidates(runtime,'A',source))

    def test_optional_fewest_source_return_reaches_explicit_pilot_choice(self):
        from effect_scheduler import pending_options
        from test_ex13_ulforce_effects import UlforceFewestReturnTests
        runtime,_,_,_=UlforceFewestReturnTests().fixture()
        selected=pending_options(runtime,'B')[0]
        pilot=self.runner.ReferencePilot(runtime.context.matchup_id,0,'B')
        self.assertIn(self.runner.pending_choice(runtime,'B',selected,pilot),[False,True])

    def test_effect_owner_pilot_supplies_one_order_for_all_tied_return_targets(self):
        from effect_scheduler import pending_options,resolve_pending
        from test_ex13_ulforce_effects import UlforceFewestReturnTests
        from test_selected_mechanics import stage
        runtime,_,target,_=UlforceFewestReturnTests().fixture()
        other=stage(runtime,'A',['EX13-019'])
        class Pilot:
            def choose(self,view,choices):return True
            def bottom_order(self,cards):return list(reversed(cards))
        selected=pending_options(runtime,'B')[0]
        choice=self.runner.pending_choice(runtime,'B',selected,Pilot())
        self.assertEqual(choice,{'activate':True,'bottom_order':[other,target]})
        resolve_pending(runtime,'B',selected['id'],choice)
        self.assertEqual([c.key for c in runtime.state.zones['A']['deck'][:2]],[other,target])

    def test_attempt_replays_exactly_and_never_claims_match_credit(self):
        for index in (0, 1):
            with self.subTest(index=index):
                record = self.runner.run_attempt(index, ROOT, max_commands=20)
                self.assertEqual(record['first'], 'A' if index == 0 else 'B')
                self.assertEqual(record['accepted_fact_finding_credit'], 0)
                self.assertEqual(record['final_evaluation_credit'], 0)
                self.assertNotEqual(record['status'], 'JUDGE_CERTIFIED')
                self.assertTrue(self.runner.replay_attempt(record, ROOT)['exact_match'])
                self.assertEqual(record, self.runner.run_attempt(index, ROOT, max_commands=20))
                self.assertIn('initial', record)
                self.assertIn('final', record)
                self.assertIn('commands', record)
                self.assertIn('events', record)
                self.assertIn('replay_provenance', record)
                self.assertTrue(record['halts'] or record['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL')

    def test_cohort_output_is_balanced_compressed_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'diagnostics'
            summary = self.runner.write_attempts(out, ROOT, count=2, max_commands=12)
            self.assertEqual(summary['attempted_seeds'], 2)
            self.assertEqual(summary['first_counts'], {'A': 1, 'B': 1})
            self.assertEqual(summary['accepted_fact_finding_credit'], 0)
            self.assertEqual(summary['final_evaluation_credit'], 0)
            self.assertEqual(summary['exact_replay_matches'], 2)
            files = sorted(out.glob('attempt-*.json.gz'))
            self.assertEqual(len(files), 2)
            for path in files:
                record = json.loads(gzip.decompress(path.read_bytes()))
                self.assertEqual(record['accepted_fact_finding_credit'], 0)
                self.assertTrue(self.runner.replay_attempt(record, ROOT)['exact_match'])
            saved = (out / 'summary.json').read_bytes()
            with self.assertRaises(FileExistsError):
                self.runner.write_attempts(out, ROOT, count=2, max_commands=12)
            self.assertEqual((out / 'summary.json').read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
