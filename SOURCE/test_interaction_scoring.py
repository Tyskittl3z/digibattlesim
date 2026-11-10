"""Observable board-impact heuristics, not gameplay or strategy certification."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime, RuntimeHalt, Stack
from effect_grants import grant_effect
from field_tracker import FieldTracker
from match_context import digest
from matchup_readiness import load_context_file


ROOT = Path(__file__).resolve().parents[1]


class InteractionScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('interaction_scoring'),
                             'Board colors need a defined observable scoring rule')
        self.scoring = importlib.import_module('interaction_scoring')

    def runtime(self):
        runtime = ContextRuntime(self.context, 391, 'A', allow_experimental=True)
        runtime.state.turn = 7
        runtime.state.phase = 'MAIN'
        runtime.state.memory = 3
        return runtime

    def take(self, runtime, owner, number):
        for zone in ('deck', 'eggdeck'):
            cards = runtime.state.zones[owner][zone]
            card = next((c for c in cards if c.card_number == number), None)
            if card:
                cards.remove(card)
                return card
        self.fail('Missing fixture card ' + owner + ':' + number)

    def stage(self, runtime, owner, numbers):
        cards = [self.take(runtime, owner, number) for number in numbers]
        runtime.state.entity_sequence += 1
        key = cards[-1].key
        runtime.state.battle[owner][key] = Stack(cards, instance_id='fixture-' + str(runtime.state.entity_sequence))
        return key

    def boundaries(self, runtime, seat='A'):
        tracker = FieldTracker(self.context)
        tracker.start(runtime.snapshot())
        return runtime.public_view(seat), tracker.public_metrics()

    def score(self, before, after, *, seat='A', command=None, result=None,
              metrics_before=None, metrics_after=None):
        return self.scoring.score_transition(before, after, seat, context=self.context,
            command=command or {'command': 'RESOLVE_PENDING', 'seat': seat,
                                'status': 'EXPERIMENTAL_RESOLVED'},
            result=result or {}, public_metrics_before=metrics_before,
            public_metrics_after=metrics_after)

    def test_removing_opposing_large_stack_has_greater_positive_impact_than_rookie(self):
        rewards = []
        for numbers in (['EX1-013'], ['EX1-013', 'BT22-022', 'BT22-023']):
            runtime = self.runtime(); target = self.stage(runtime, 'B', numbers)
            before, metrics_before = self.boundaries(runtime)
            runtime.state.zones['B']['trash'].extend(runtime.state.battle['B'].pop(target).cards)
            after, metrics_after = self.boundaries(runtime)
            rating = self.score(before, after, metrics_before=metrics_before, metrics_after=metrics_after)
            self.assertEqual((rating['label'], rating['meaning']), ('GREEN', 'positive'))
            rewards.append(rating['reward'])
        self.assertGreater(rewards[1], rewards[0])

    def test_losing_own_stack_is_negative_and_control_perspectives_are_symmetric(self):
        runtime = self.runtime(); key = self.stage(runtime, 'A', ['EX1-013', 'BT22-022'])
        a_before, metrics_before = self.boundaries(runtime)
        b_before = runtime.public_view('B')
        runtime.state.zones['A']['trash'].extend(runtime.state.battle['A'].pop(key).cards)
        a_after, metrics_after = self.boundaries(runtime)
        a = self.score(a_before, a_after, metrics_before=metrics_before, metrics_after=metrics_after)
        b = self.score(b_before, runtime.public_view('B'), seat='B',
                       metrics_before=metrics_before, metrics_after=metrics_after)
        self.assertEqual(a['label'], 'RED')
        self.assertEqual(b['label'], 'GREEN')
        self.assertAlmostEqual(a['reward'], -b['reward'])

    def test_ready_blocker_incapacitation_is_visible_and_expired_grants_do_not_count(self):
        runtime = self.runtime(); key = self.stage(runtime, 'B', ['BT11-032'])
        tamer = self.stage(runtime, 'B', ['BT11-112'])
        grant_effect(runtime, 'B', key, {'keywords': ['Blocker']}, tamer)
        before, metrics = self.boundaries(runtime)
        runtime.state.battle['B'][key].statuses['cannot_suspend'] = True
        after, metrics_after = self.boundaries(runtime)
        rating = self.score(before, after, metrics_before=metrics, metrics_after=metrics_after)
        self.assertEqual(rating['label'], 'GREEN')
        self.assertGreater(rating['components']['ready_blockers']['contribution'], 0)
        expired = copy.deepcopy(before)
        expired['players']['B']['battle'][key]['statuses']['effect_grants'][0]['created_turn'] = 5
        expired['players']['B']['battle'][key]['statuses']['effect_grants'][0]['expires']['turn'] = 6
        expired_after = copy.deepcopy(expired)
        expired_after['players']['B']['battle'][key]['statuses']['cannot_suspend'] = True
        other = self.score(expired, expired_after)
        self.assertEqual(other['components']['ready_blockers']['contribution'], 0)

    def test_evolution_keeps_one_body_and_adds_a_source(self):
        runtime = self.runtime(); key = self.stage(runtime, 'A', ['EX1-013'])
        card = self.take(runtime, 'A', 'BT22-022'); runtime.state.zones['A']['hand'].append(card)
        before, metrics_before = self.boundaries(runtime)
        stack = runtime.state.battle['A'].pop(key); stack.cards.append(card)
        runtime.state.battle['A'][card.key] = stack; runtime.state.zones['A']['hand'].remove(card)
        after, metrics_after = self.boundaries(runtime)
        rating = self.score(before, after, result={'cost': 0},
            metrics_before=metrics_before, metrics_after=metrics_after)
        self.assertEqual(rating['components']['battle_units']['delta'], 0)
        self.assertEqual(rating['components']['sources']['delta'], 1)
        self.assertGreater(rating['reward'], 0)

    def test_security_checks_use_cumulative_tracker_counts_not_declarations(self):
        runtime = self.runtime(); before, metrics_before = self.boundaries(runtime)
        metrics_after = copy.deepcopy(metrics_before)
        metrics_after['successful_security_checks']['A'] = 1
        command = {'command': 'CONFIRM_ATTACK', 'seat': 'A'}
        rating = self.score(before, before, command=command,
            result={'success': True, 'checked_card': 'B:P-138#1'},
            metrics_before=metrics_before, metrics_after=metrics_after)
        self.assertEqual(rating['components']['security_checks']['contribution'], 2)
        self.assertEqual(rating['label'], 'GREEN')
        declaration = self.score(before, before, command={'command': 'DECLARE_ATTACK', 'seat': 'A'},
            result={'success': True}, metrics_before=metrics_before, metrics_after=metrics_before)
        self.assertEqual(declaration['components']['security_checks']['contribution'], 0)
        self.assertEqual(declaration['label'], 'YELLOW')
        with self.assertRaisesRegex(RuntimeHalt, 'SCORING_'):
            self.score(before, before, command={'command': 'DECLARE_ATTACK', 'seat': 'A'},
                       metrics_before=metrics_before, metrics_after=metrics_after)

    def test_missing_check_history_is_unknown_and_never_inferred_from_security_count(self):
        runtime = self.runtime(); card = self.take(runtime, 'B', 'P-138')
        runtime.state.zones['B']['security'].append(card)
        before, _ = self.boundaries(runtime)
        runtime.state.zones['B']['security'].remove(card)
        runtime.state.zones['B']['trash'].append(card)
        after, _ = self.boundaries(runtime)
        rating = self.score(before, after)
        self.assertEqual(rating['check_history_status'], 'NOT_PROVIDED')
        self.assertEqual(rating['components']['security_checks']['contribution'], 0)
        self.assertEqual(rating['components']['security_remaining']['contribution'], 2)
        self.assertEqual(rating['tempo_after']['axes']['completed_security_checks']['leader'], 'UNKNOWN')

    def test_actual_payment_is_not_hidden_by_refund_or_double_counted_by_nested_aliases(self):
        runtime = self.runtime(); view, _ = self.boundaries(runtime)
        evolution = {'cost': 4, 'steps': [{'operation': 'PAY_DIGIVOLUTION_COST', 'cost': 4}]}
        wrapper = {'evolution': copy.deepcopy(evolution),
                   'steps': [{'operation': 'OPTIONAL_EVOLUTION', 'result': copy.deepcopy(evolution)}]}
        rating = self.score(view, view, result=wrapper)
        self.assertEqual(rating['memory_cost']['paid'], 4)
        self.assertEqual(rating['memory_cost']['source'], 'EXPLICIT_PAY_STEPS')
        self.assertEqual(len(rating['memory_cost']['payments']), 1)
        self.assertEqual(rating['components']['memory_paid']['contribution'], -2)
        repeat = {'steps': [{'operation': 'PAY_DIGIVOLUTION_COST', 'cost': 2},
                            {'operation': 'PAY_DIGIVOLUTION_COST', 'cost': 2}]}
        again = self.score(view, view, result=repeat)
        self.assertEqual(again['memory_cost']['paid'], 4)
        self.assertEqual(len(again['memory_cost']['payments']), 2)

    def test_ancestor_cost_is_a_summary_of_nested_canonical_payments(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        after = copy.deepcopy(before); after['memory'] = -1
        nested = {'cost': 4, 'steps': [{'operation': 'OPTIONAL_EVOLUTION', 'result': {
            'cost': 4, 'steps': [{'operation': 'PAY_DIGIVOLUTION_COST', 'cost': 2},
                              {'operation': 'PAY_DIGIVOLUTION_COST', 'cost': 2}]}}]}
        rating = self.score(before, after, result=nested)
        self.assertEqual(rating['memory_cost']['paid'], 4)
        self.assertEqual(len(rating['memory_cost']['payments']), 2)
        self.assertEqual(rating['components']['memory_resource_residual']['contribution'], 0)

    def test_observed_capped_memory_gain_and_partial_refund_remain_separate_from_payment(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        capped_before = copy.deepcopy(before); capped_before['memory'] = 8
        capped_after = copy.deepcopy(before); capped_after['memory'] = 10
        gain = self.score(capped_before, capped_after, result={'requested': 5})
        self.assertEqual(gain['components']['memory_resource_residual']['delta'], 2)
        self.assertEqual(gain['reward'], 1)
        at_cap = self.score(capped_after, capped_after, result={'requested': 5})
        self.assertEqual(at_cap['reward'], 0)
        refunded = copy.deepcopy(before); refunded['memory'] = 1
        refund = self.score(before, refunded, result={'cost': 4,
            'steps': [{'operation': 'PAY_DIGIVOLUTION_COST', 'cost': 4},
                      {'operation': 'GAIN_MEMORY', 'requested': 2}]})
        self.assertEqual(refund['memory_cost']['paid'], 4)
        self.assertEqual(refund['components']['memory_paid']['contribution'], -2)
        self.assertEqual(refund['components']['memory_resource_residual']['contribution'], 1)
        self.assertEqual(refund['reward'], -1)

    def test_memory_fallback_requires_same_actor_and_spending_command(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        after = copy.deepcopy(before); after['memory'] = -2
        rating = self.score(before, after, command={'command': 'PLAY_CARD', 'seat': 'A'})
        self.assertEqual(rating['memory_cost']['paid'], 5)
        self.assertEqual(rating['memory_cost']['source'], 'ACTOR_RELATIVE_GAUGE_FALLBACK')
        flipped = copy.deepcopy(after); flipped.update({'active': 'B', 'memory': 2, 'turn': 8})
        turn = self.score(after, flipped, command={'command': 'FINISH_TURN', 'seat': 'A'})
        self.assertEqual(turn['memory_cost']['paid'], 0)
        self.assertEqual(turn['reward'], 0)
        self.assertTrue(turn['procedural'])
        unknown = self.score(before, after, command={'command': 'RESOLVE_PENDING', 'seat': 'A'})
        self.assertEqual(unknown['memory_cost']['paid'], 0)

    def test_memory_efficiency_distinguishes_cheaper_and_free_development(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        self.stage(runtime, 'A', ['EX1-013']); after, _ = self.boundaries(runtime)
        cheap_after = copy.deepcopy(after); cheap_after['memory'] = 2
        dear_after = copy.deepcopy(after); dear_after['memory'] = -2
        cheap = self.score(before, cheap_after, command={'command': 'PLAY_CARD', 'seat': 'A'}, result={'cost': 1})
        dear = self.score(before, dear_after, command={'command': 'PLAY_CARD', 'seat': 'A'}, result={'cost': 5})
        free = self.score(before, after, result={'cost': 0})
        self.assertGreater(cheap['reward'], dear['reward'])
        self.assertGreater(cheap['efficiency']['benefit_per_memory'], dear['efficiency']['benefit_per_memory'])
        self.assertEqual(free['efficiency']['status'], 'FREE')
        self.assertIsNone(free['efficiency']['benefit_per_memory'])
        self.assertNotIn('globally_cheapest', cheap)

    def test_automatic_draw_preserves_observed_benefit_but_is_ineligible_for_learning(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        drawn = self.take(runtime, 'A', 'EX1-013')
        runtime.state.zones['A']['hand'].append(drawn)
        after, _ = self.boundaries(runtime)
        rating = self.score(before, after, command={'command': 'ADVANCE_PHASE', 'seat': 'A'})
        self.assertEqual((rating['label'], rating['reward'], rating['procedural']), ('GREEN', 0.5, True))
        self.assertFalse(rating['learning_eligible'])
        self.assertEqual(rating['decision_type'], 'PROCEDURAL')
        self.assertEqual(rating['components']['hand_cards']['contribution'], 0.5)

    def test_procedural_boundary_retains_actual_negative_impact_and_zero_is_neutral(self):
        runtime = self.runtime(); target = self.stage(runtime, 'A', ['EX1-013'])
        before, _ = self.boundaries(runtime)
        runtime.state.zones['A']['trash'].extend(runtime.state.battle['A'].pop(target).cards)
        after, _ = self.boundaries(runtime)
        rating = self.score(before, after, command={'command': 'END_ATTACK', 'seat': 'A'})
        self.assertEqual(rating['label'], 'RED')
        self.assertLess(rating['reward'], 0)
        self.assertFalse(rating['learning_eligible'])
        no_op = self.score(before, before, command={'command': 'END_ATTACK', 'seat': 'A'})
        self.assertEqual((no_op['label'], no_op['reward']), ('YELLOW', 0))

    def test_failed_commands_are_unrated_even_if_otherwise_positive(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        self.stage(runtime, 'A', ['EX1-013']); after, _ = self.boundaries(runtime)
        rating = self.score(before, after, command={'command': 'PLAY_CARD', 'seat': 'A', 'status': 'HALT'})
        self.assertEqual((rating['label'], rating['status'], rating['reward']), ('UNRATED', 'UNRATED', None))

    def test_tempo_exposes_each_axis_and_marks_conflicting_leads(self):
        runtime = self.runtime(); self.stage(runtime, 'A', ['EX1-013']); self.stage(runtime, 'A', ['P-138'])
        self.stage(runtime, 'B', ['EX1-013', 'BT22-022', 'BT22-023'])
        view, metrics = self.boundaries(runtime)
        metrics['successful_security_checks']['A'] = 1
        rating = self.score(view, view, metrics_before=metrics, metrics_after=metrics)
        tempo = rating['tempo_after']
        self.assertEqual(tempo['axes']['cards_in_play']['leader'], 'A')
        self.assertEqual(tempo['axes']['largest_stack']['leader'], 'B')
        self.assertEqual(tempo['axes']['completed_security_checks']['leader'], 'A')
        self.assertEqual(tempo['leader'], 'CONTESTED')

    def test_a_terminal_winner_is_not_a_blanket_positive_rating(self):
        runtime = self.runtime(); before, _ = self.boundaries(runtime)
        after = copy.deepcopy(before); after.update({'terminal': True, 'winner': 'A'})
        rating = self.score(before, after, command={'command': 'CONFIRM_ATTACK', 'seat': 'A'},
                            result={'success': True, 'winner': 'A'})
        self.assertEqual(rating['label'], 'YELLOW')
        self.assertEqual(rating['outcome']['winner'], 'A')
        self.assertFalse(rating['outcome']['included_in_board_reward'])

    def test_hidden_or_unknown_private_structure_is_rejected(self):
        runtime = self.runtime(); key = self.stage(runtime, 'B', ['EX1-013'])
        view, _ = self.boundaries(runtime)
        for mutation in ('audit', 'opponent_hand', 'own_deck', 'stack_extra', 'status_extra'):
            bad = copy.deepcopy(view)
            if mutation == 'audit': bad['rng_state'] = []
            elif mutation == 'opponent_hand': bad['players']['B']['hand'] = []
            elif mutation == 'own_deck': bad['players']['A']['deck'] = []
            elif mutation == 'stack_extra': bad['players']['B']['battle'][key]['secret_deck'] = ['A:EX1-013#1']
            else: bad['players']['B']['battle'][key]['statuses']['secret_deck'] = ['A:EX1-013#1']
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeHalt, 'SCORING_'):
                self.score(bad, view)

    def test_public_duplicate_cards_entities_and_impossible_counts_are_rejected(self):
        runtime = self.runtime(); key = self.stage(runtime, 'B', ['EX1-013'])
        other = self.stage(runtime, 'B', ['P-138'])
        view, _ = self.boundaries(runtime)
        for mutation in ('card', 'entity', 'count', 'hidden_count_type'):
            bad = copy.deepcopy(view)
            if mutation == 'card':
                bad['players']['B']['trash'].append(key)
                bad['players']['B']['deck']['count'] -= 1
            elif mutation == 'entity':
                bad['players']['B']['battle'][other]['instance_id'] = bad['players']['B']['battle'][key]['instance_id']
            elif mutation == 'count':
                bad['players']['B']['deck']['count'] += 1
            else:
                bad['players']['B']['security']['count'] = False
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeHalt, 'SCORING_'):
                self.score(bad, view)

    def test_metrics_cannot_disagree_with_observed_board_and_inputs_are_detached(self):
        runtime = self.runtime(); view, metrics = self.boundaries(runtime)
        bad = copy.deepcopy(metrics); bad['board']['A']['battle_card_count'] = 4
        with self.assertRaisesRegex(RuntimeHalt, 'SCORING_'):
            self.score(view, view, metrics_before=bad, metrics_after=bad)
        original = copy.deepcopy((view, metrics))
        rating = self.score(view, view, metrics_before=metrics, metrics_after=metrics)
        rating['components'].clear(); rating['tempo_after']['players'].clear()
        self.assertEqual((view, metrics), original)
        self.assertTrue(self.score(view, view)['components'])

    def test_criteria_file_hash_and_export_are_bound_and_detached(self):
        manifest = self.scoring.criteria_manifest()
        self.assertEqual(manifest['criterion_sha256'], self.scoring.CRITERIA_SHA256)
        path = ROOT / manifest['file']
        raw = json.loads(path.read_text())
        self.assertEqual(digest(raw), self.scoring.CRITERIA_SHA256)
        manifest.clear()
        self.assertEqual(self.scoring.criteria_manifest()['criterion_sha256'], self.scoring.CRITERIA_SHA256)

    def test_loaded_scorer_and_criterion_hashes_do_not_relabel_when_disk_files_change(self):
        runtime = self.runtime(); view, _ = self.boundaries(runtime)
        loaded = self.scoring.criteria_manifest()
        with patch.object(Path, 'read_bytes', return_value=b'different on-disk artifact'):
            changed_disk = self.scoring.criteria_manifest()
            rating = self.score(view, view)
        self.assertEqual(changed_disk['file_sha256'], loaded['file_sha256'])
        self.assertEqual(changed_disk['scorer_source_sha256'], loaded['scorer_source_sha256'])
        self.assertEqual(rating['scorer_source_sha256'], loaded['scorer_source_sha256'])


if __name__ == '__main__':
    unittest.main()
