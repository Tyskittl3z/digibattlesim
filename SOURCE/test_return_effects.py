"""Shared deck-return dependencies; scenarios count as zero full matches."""
import copy
from dataclasses import replace
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from match_context import CardDefinition
from matchup_readiness import load_context_file
from return_effects import preflight_deck_bottom_return, return_to_deck_bottom
from test_selected_mechanics import ROOT, stage


class ReturnDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def fixture(self, numbers=('EX1-013', 'BT22-022')):
        runtime = ContextRuntime(self.context, 57, 'B', allow_experimental=True)
        runtime.state.turn = 10
        runtime.state.memory = -1
        return runtime, stage(runtime, 'A', numbers)

    def text(self, runtime, number, field, text):
        # Synthetic wording probes only the fail-closed procedure; it does not
        # register invented card effects or grant gameplay support to them.
        cards = []
        for definition in runtime.context.cards:
            if definition.number == number:
                raw = definition.to_dict()
                raw[field] = text
                definition = CardDefinition.from_dict(raw)
            cards.append(definition)
        runtime.context = replace(runtime.context, cards=tuple(cards))

    def blocked(self, runtime, target, pattern):
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, pattern):
            return_to_deck_bottom(runtime, 'B', 'A', [target], [target])
        self.assertEqual(runtime.snapshot(), before)

    def test_target_top_inherited_prevention_is_inactive(self):
        runtime, target = self.fixture()
        preflight_deck_bottom_return(runtime, 'B', 'A', target)

    def test_target_lower_inherited_prevention_remains_an_actual_dependency(self):
        runtime, target = self.fixture(('BT22-022', 'BT22-023'))
        self.blocked(runtime, target, 'RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED.*BT22-022 inherited_text')

    def test_lower_card_overflow_is_not_hidden_by_inherited_field_selection(self):
        runtime, target = self.fixture()
        self.text(runtime, 'EX1-013', 'main_text', '＜Overflow -3＞')
        self.blocked(runtime, target, 'RETURN_LEAVE_KEYWORD_UNIMPLEMENTED.*EX1-013 Overflow')

    def test_unrelated_card_overflow_does_not_observe_this_return(self):
        runtime, target = self.fixture()
        stage(runtime, 'B', ['EX13-019'])
        self.text(runtime, 'EX13-019', 'main_text', '＜Overflow -3＞')
        preflight_deck_bottom_return(runtime, 'B', 'A', target)

    def test_bare_actual_leave_keywords_fail_closed(self):
        for keyword in ('Decode', 'Partition'):
            with self.subTest(keyword=keyword):
                runtime, target = self.fixture()
                self.text(runtime, 'BT22-022', 'main_text', '＜' + keyword + '＞')
                self.blocked(runtime, target, 'RETURN_LEAVE_KEYWORD_UNIMPLEMENTED.*BT22-022 main_text')

    def test_inactive_lower_main_decode_is_not_an_active_leave_effect(self):
        runtime, target = self.fixture()
        self.text(runtime, 'EX1-013', 'main_text', '＜Decode＞')
        preflight_deck_bottom_return(runtime, 'B', 'A', target)

    def test_unknown_leaving_card_special_rule_fails_closed(self):
        runtime, target = self.fixture()
        self.text(runtime, 'EX1-013', 'special_conditions',
                  {'[Rule]': 'When this card is removed from the battle area, gain 1 memory.'})
        self.blocked(runtime, target, 'RETURN_LEAVE_SPECIAL_CONDITION_UNIMPLEMENTED.*EX1-013')

    def test_unknown_unrelated_special_rule_does_not_observe_this_return(self):
        runtime, target = self.fixture()
        stage(runtime, 'B', ['EX13-019'])
        self.text(runtime, 'EX13-019', 'special_conditions', {'[Rule]': '＜Partition＞'})
        preflight_deck_bottom_return(runtime, 'B', 'A', target)

    def test_mixed_global_ward_is_not_discarded_for_an_unrelated_self_reference(self):
        runtime, target = self.fixture()
        stage(runtime, 'A', ['EX13-019'])
        self.text(runtime, 'EX13-019', 'main_text',
                  "[All Turns] All your Digimon can't be returned while this Digimon is unsuspended.")
        self.blocked(runtime, target, 'RETURN_PROTECTION_UNIMPLEMENTED.*EX13-019 main_text')

    def test_protection_does_not_require_the_word_effects(self):
        runtime, target = self.fixture()
        self.text(runtime, 'BT22-022', 'main_text', "[All Turns] This Digimon can't be returned.")
        self.blocked(runtime, target, 'RETURN_PROTECTION_UNIMPLEMENTED.*BT22-022 main_text')

    def test_unknown_affect_and_does_not_leave_wording_stays_fail_closed(self):
        for text in ("Your opponent's effects cannot affect this Digimon.",
                     'This Digimon does not leave the battle area.'):
            with self.subTest(text=text):
                runtime, target = self.fixture()
                self.text(runtime, 'BT22-022', 'main_text', '[All Turns] ' + text)
                self.blocked(runtime, target, 'RETURN_PROTECTION_UNIMPLEMENTED')

    def test_unrelated_self_ward_does_not_protect_the_target(self):
        runtime, target = self.fixture()
        stage(runtime, 'A', ['EX13-019'])
        self.text(runtime, 'EX13-019', 'main_text', "[All Turns] This Digimon can't be returned.")
        preflight_deck_bottom_return(runtime, 'B', 'A', target)

    def test_trait_brackets_are_not_misread_as_a_name_filter(self):
        runtime, target = self.fixture()
        stage(runtime, 'A', ['EX13-019'])
        self.text(runtime, 'EX13-019', 'main_text',
                  '[All Turns] When one of your Digimon with the [CS] trait leaves the battle area, gain 1 memory.')
        self.blocked(runtime, target, 'RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED.*EX13-019 main_text')

    def test_removed_event_is_not_silently_skipped(self):
        runtime, target = self.fixture()
        self.text(runtime, 'BT22-022', 'main_text',
                  '[All Turns] When this Digimon is removed from the battle area, gain 1 memory.')
        self.blocked(runtime, target, 'RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED.*BT22-022 main_text')

    def test_off_turn_observer_is_inactive_but_opponents_turn_observer_is_live(self):
        for timing, active in (('Your Turn', False), ("Opponent's Turn", True)):
            with self.subTest(timing=timing):
                runtime, target = self.fixture()
                self.text(runtime, 'BT22-022', 'main_text',
                          '[' + timing + '] When this Digimon leaves the battle area, gain 1 memory.')
                if active:
                    self.blocked(runtime, target, 'RETURN_LEAVE_DEPENDENCY_UNIMPLEMENTED')
                else:
                    preflight_deck_bottom_return(runtime, 'B', 'A', target)

    def test_all_targets_are_checked_before_the_first_card_moves(self):
        runtime, target = self.fixture()
        second = stage(runtime, 'A', ['EX13-017', 'BT22-023'])
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'RETURN_REPLACEMENT_CHOICE_REQUIRED'):
            return_to_deck_bottom(runtime, 'B', 'A', [target, second], [target, second])
        self.assertEqual(runtime.snapshot(), before)

    def test_unknown_target_status_is_not_silently_discarded(self):
        runtime, target = self.fixture()
        runtime.state.battle['A'][target].statuses['unknown_ward'] = True
        self.blocked(runtime, target, 'GRANT_STATUS_UNSUPPORTED')

    def test_return_preserves_memory_rng_and_other_stacks_with_evade_granted(self):
        from effect_grants import grant_effect
        runtime, target = self.fixture()
        tamer = stage(runtime, 'A', ['BT11-112'])
        grant_effect(runtime, 'A', target, {'keywords': ['Blocker', 'Evade']}, tamer)
        other = copy.deepcopy(runtime.state.battle['A'][tamer])
        before_rng = runtime.snapshot()['rng_state']
        lower = runtime.state.battle['A'][target].cards[0].key
        result = return_to_deck_bottom(runtime, 'B', 'A', [target], [target])
        self.assertEqual(result['returned'], [target])
        self.assertEqual(result['trashed_sources'], [lower])
        self.assertEqual(runtime.state.battle['A'][tamer], other)
        self.assertEqual(runtime.state.memory, -1)
        self.assertEqual(runtime.snapshot()['rng_state'], before_rng)
        self.assertEqual(runtime.state.pending, [])
        self.assertEqual(runtime.events, [])
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
