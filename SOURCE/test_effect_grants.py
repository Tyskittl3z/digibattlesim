"""Encountered Rina duration probes; every fixture has zero full-match credit."""
import copy
import unittest

from context_runtime import ContextRuntime, RuntimeHalt, Stack
from effect_scheduler import pending_options, resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import ORIENTATION_EFFECT, build_selected_registry
from test_selected_mechanics import ROOT, stage
import turn_flow

import effect_grants as grants


class EffectGrantTests(unittest.TestCase):
    def runtime(self, active='A'):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 602, active,
                                 build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 4
        return runtime

    def grant(self, runtime, controller='A', *, effect=None, source_number='BT11-112'):
        source = stage(runtime, controller, [source_number])
        target = stage(runtime, controller, ['BT11-023'])
        record = grants.grant_effect(runtime, controller, target,
                                     effect or {'keywords': ['Blocker', 'Evade']},
                                     source, 'end_of_opponent_turn')
        return source, target, record

    def test_keywords_are_semantic_and_bind_physical_source_and_target(self):
        runtime = self.runtime()
        source, target, record = self.grant(runtime)
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Blocker'))
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Evade'))
        self.assertFalse(grants.active_keyword(runtime, 'A', target, 'Jamming'))
        self.assertEqual(grants.active_dp_bonus(runtime, 'A', target), 0)
        self.assertEqual(record['source'], source)
        self.assertEqual(record['source_field'], 'main_text')
        self.assertEqual(record['source_kind'], 'Tamer')
        self.assertEqual(record['source_instance'], runtime.state.battle['A'][source].instance_id)
        self.assertEqual(record['target'], target)
        self.assertEqual(record['target_instance'], runtime.state.battle['A'][target].instance_id)
        self.assertNotEqual(record['source_instance'], record['target_instance'])
        self.assertEqual(record['expires'], {'turn': 5, 'controller': 'B', 'boundary': 'turn_end'})
        self.assertEqual(set(runtime.state.battle['A'][target].statuses), {'effect_grants'})
        runtime.verify()
        record['effect']['keywords'].clear()
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Evade'))

    def test_dp_grants_add_without_changing_printed_dp_or_orientation(self):
        runtime = self.runtime()
        source, target, _ = self.grant(runtime, source_number='BT22-085', effect={'dp_bonus': 3000})
        grants.grant_effect(runtime, 'A', target, {'dp_bonus': 3000}, source)
        self.assertEqual(grants.active_dp_bonus(runtime, 'A', target), 6000)
        self.assertEqual(runtime.context.card('A', 'BT11-023').to_dict()['dp'], 1000)
        self.assertFalse(runtime.state.battle['A'][target].suspended)
        self.assertFalse(grants.active_keyword(runtime, 'A', target, 'Blocker'))

    def test_expiry_uses_effect_controllers_opponent_in_both_seats(self):
        for controller, active, expiry_turn in [('A', 'A', 5), ('A', 'B', 4),
                                                ('B', 'B', 5), ('B', 'A', 4)]:
            with self.subTest(controller=controller, active=active):
                runtime = self.runtime(active)
                _, _, record = self.grant(runtime, controller)
                self.assertEqual(record['expires'], {
                    'turn': expiry_turn, 'controller': 'B' if controller == 'A' else 'A',
                    'boundary': 'turn_end'})

    def test_lingering_grant_survives_source_tamer_leaving(self):
        runtime = self.runtime()
        source, target, _ = self.grant(runtime)
        runtime.state.zones['A']['hand'].extend(runtime.state.battle['A'].pop(source).cards)
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Blocker'))
        runtime.verify()

    def test_grant_follows_same_instance_when_digivolution_changes_anchor(self):
        runtime = self.runtime()
        _, target, _ = self.grant(runtime)
        stack = runtime.state.battle['A'].pop(target)
        deck = runtime.state.zones['A']['deck']
        evolved = next(card for card in deck if card.card_number == 'BT22-022')
        deck.remove(evolved)
        stack.cards.append(evolved)
        runtime.state.battle['A'][evolved.key] = stack
        self.assertTrue(grants.active_keyword(runtime, 'A', evolved.key, 'Evade'))
        runtime.verify()

    def test_same_physical_card_as_new_instance_does_not_keep_grant(self):
        runtime = self.runtime()
        _, target, _ = self.grant(runtime)
        old_stack = runtime.state.battle['A'][target]
        runtime.state.battle['A'][target] = Stack(old_stack.cards,
            instance_id='replacement-entity', statuses=copy.deepcopy(old_stack.statuses))
        self.assertFalse(grants.active_keyword(runtime, 'A', target, 'Blocker'))
        self.assertEqual(grants.active_dp_bonus(runtime, 'A', target), 0)

    def test_source_field_must_be_active_before_grant_mutates_state(self):
        for field in ('main_text', 'inherited_text'):
            with self.subTest(field=field):
                runtime = self.runtime()
                target = stage(runtime, 'A', ['BT11-023'])
                anchor = stage(runtime, 'A', ['EX13-022', 'EX13-023'])
                cards = runtime.state.battle['A'][anchor].cards
                source = cards[0].key if field == 'main_text' else cards[-1].key
                before = runtime.snapshot()
                with self.assertRaisesRegex(RuntimeHalt, 'SOURCE_NOT_ACTIVE'):
                    grants.grant_effect(runtime, 'A', target, {'dp_bonus': 3000},
                                        source, source_field=field)
                self.assertEqual(runtime.snapshot(), before)

    def test_inherited_source_records_digimon_effect_semantics(self):
        runtime = self.runtime()
        target = stage(runtime, 'A', ['BT11-023'])
        anchor = stage(runtime, 'A', ['EX13-022', 'EX13-023'])
        source = runtime.state.battle['A'][anchor].cards[0].key
        record = grants.grant_effect(runtime, 'A', target, {'dp_bonus': 3000}, source,
                                     source_field='inherited_text')
        self.assertEqual((record['source_field'], record['source_kind']), ('inherited_text', 'Digimon'))

    def test_unknown_status_and_malformed_grant_fail_closed(self):
        for malformed in ({'cannot_suspend': False}, {'effect_grants': True},
                          {'effect_grants': [{'effect': {'dp_bonus': 3000}}]}):
            with self.subTest(statuses=malformed):
                runtime = self.runtime()
                target = stage(runtime, 'A', ['BT11-023'])
                runtime.state.battle['A'][target].statuses = malformed
                with self.assertRaisesRegex(RuntimeHalt, 'GRANT_STATUS_UNSUPPORTED|GRANT_SCHEMA_INVALID'):
                    grants.validate_grants(runtime, 'A', target)

    def test_invalid_semantic_effect_or_duration_does_not_assign_instances(self):
        for effect, duration in [({'dp_bonus': True}, 'end_of_opponent_turn'),
                                 ({'dp_bonus': -3000}, 'end_of_opponent_turn'),
                                 ({'keywords': ['Evade'], 'cannot_suspend': False}, 'end_of_opponent_turn'),
                                 ({'keywords': ['Evade']}, 'guess_next_turn')]:
            with self.subTest(effect=effect, duration=duration):
                runtime = self.runtime()
                source = stage(runtime, 'A', ['BT11-112'])
                target = stage(runtime, 'A', ['BT11-023'])
                before = runtime.snapshot()
                with self.assertRaisesRegex(RuntimeHalt, 'GRANT_EFFECT_UNSUPPORTED|GRANT_DURATION_UNSUPPORTED'):
                    grants.grant_effect(runtime, 'A', target, effect, source, duration)
                self.assertEqual(runtime.snapshot(), before)

    def test_future_creation_and_source_semantic_tampering_fail_closed(self):
        for change in ('future_creation', 'source_kind', 'source_field'):
            with self.subTest(change=change):
                runtime = self.runtime()
                _, target, _ = self.grant(runtime)
                record = runtime.state.battle['A'][target].statuses['effect_grants'][0]
                if change == 'future_creation':
                    record['created_turn'] = 8
                    record['expires']['turn'] = 9
                elif change == 'source_kind':
                    record['source_kind'] = 'Digimon'
                else:
                    record['source_field'] = 'inherited_text'
                with self.assertRaisesRegex(RuntimeHalt, 'GRANT_SCHEMA_INVALID|GRANT_SOURCE_BINDING_INVALID'):
                    grants.validate_grants(runtime, 'A', target)

    def test_malformed_empty_status_halts_before_pass_commits(self):
        runtime = self.runtime()
        target = stage(runtime, 'A', ['BT11-023'])
        runtime.state.battle['A'][target].statuses = []
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'TURN_END_STATUS_UNSUPPORTED'):
            turn_flow.pass_turn(runtime, 'A', ROOT)
        self.assertEqual(runtime.snapshot(), before)

    def test_opponent_restriction_keeps_source_and_target_ownership_distinct(self):
        runtime = self.runtime('B')
        source = stage(runtime, 'B', ['EX13-022'])
        target = stage(runtime, 'A', ['BT11-032'])
        record = grants.grant_effect(runtime, 'B', target,
            {'restrictions': ['cannot_suspend']}, source, target_owner='A')
        self.assertEqual((record['controller'], record['target_owner'], record['source_kind']),
                         ('B', 'A', 'Digimon'))
        self.assertEqual(record['expires'], {'turn': 5, 'controller': 'A', 'boundary': 'turn_end'})
        self.assertTrue(grants.active_restriction(runtime, 'A', target, 'cannot_suspend'))
        self.assertFalse(runtime.state.battle['A'][target].suspended)
        self.assertFalse(grants.active_keyword(runtime, 'A', target, 'Blocker'))
        turn_flow.pass_turn(runtime, 'B', ROOT)
        turn_flow.finish_turn(runtime, 'B', ROOT)
        self.assertTrue(grants.active_restriction(runtime, 'A', target, 'cannot_suspend'))
        runtime.state.phase = 'MAIN'
        turn_flow.pass_turn(runtime, 'A', ROOT)
        self.assertTrue(grants.active_restriction(runtime, 'A', target, 'cannot_suspend'))
        turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertFalse(grants.active_restriction(runtime, 'A', target, 'cannot_suspend'))
        runtime.verify()

    def test_restriction_applied_during_target_owners_turn_expires_at_that_turn_end(self):
        runtime = self.runtime('A')
        source = stage(runtime, 'B', ['EX13-022'])
        target = stage(runtime, 'A', ['BT11-032'])
        record = grants.grant_effect(runtime, 'B', target,
            {'restrictions': ['cannot_suspend']}, source, target_owner='A')
        self.assertEqual(record['expires'], {'turn': 4, 'controller': 'A', 'boundary': 'turn_end'})
        runtime.state.zones['B']['hand'].extend(runtime.state.battle['B'].pop(source).cards)
        self.assertTrue(grants.active_restriction(runtime, 'A', target, 'cannot_suspend'))
        turn_flow.pass_turn(runtime, 'A', ROOT)
        turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertFalse(grants.active_restriction(runtime, 'A', target, 'cannot_suspend'))

    def test_grant_survives_own_turn_and_expires_only_after_opponent_turn_finishes(self):
        runtime = self.runtime()
        _, target, _ = self.grant(runtime)
        turn_flow.pass_turn(runtime, 'A', ROOT)
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Evade'))
        turn_flow.finish_turn(runtime, 'A', ROOT)
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Evade'))
        runtime.state.phase = 'MAIN'
        turn_flow.pass_turn(runtime, 'B', ROOT)
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Evade'))
        turn_flow.finish_turn(runtime, 'B', ROOT)
        self.assertFalse(grants.active_keyword(runtime, 'A', target, 'Evade'))
        self.assertEqual(runtime.state.battle['A'][target].statuses, {})

    def test_pending_and_memory_postponement_preserve_grants_until_real_boundary(self):
        runtime = self.runtime('B')
        source = stage(runtime, 'B', ['P-138', 'EX13-023'], suspended=True)
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.memory = -1
        runtime.dispatch(ORIENTATION_EFFECT, 'B', source, source)
        _, target, _ = self.grant(runtime)
        before = runtime.snapshot()
        blocked = copy.deepcopy(runtime)
        with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            turn_flow.finish_turn(blocked, 'B', ROOT)
        self.assertEqual(blocked.snapshot(), before)
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Blocker'))
        resolve_pending(runtime, 'B', pending_options(runtime, 'B')[0]['id'], None)
        self.assertEqual(runtime.state.memory, 0)
        result = turn_flow.finish_turn(runtime, 'B', ROOT)
        self.assertTrue(result['turn_postponed'])
        self.assertTrue(grants.active_keyword(runtime, 'A', target, 'Blocker'))
        runtime.state.memory = -1
        runtime._finish_main_processing()
        turn_flow.finish_turn(runtime, 'B', ROOT)
        self.assertFalse(grants.active_keyword(runtime, 'A', target, 'Blocker'))


if __name__ == '__main__':
    unittest.main()
