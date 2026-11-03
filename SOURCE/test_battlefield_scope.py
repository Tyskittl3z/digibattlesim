"""Conserved selected-pair scope checks; all cases have zero match credit."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from match_context import CardDefinition, DeckDefinition, MatchContext
from test_selected_mechanics import ROOT, selected_context, stage

try:
    from battlefield_scope import assert_basic_board_scope
except ImportError:
    assert_basic_board_scope = None


ACTIONS = ('play_plain', 'play_search', 'breeding_evolve', 'attack_plain')
PLAIN = {'EX1-013', 'ST7-05', 'BT9-011'}
SEARCH_TOPS = {'BT11-023','P-138','EX13-017','EX2-008','EX8-009'}
OTHER_TIMINGS = {'BT12-016','BT12-029','BT17-013','BT17-016','BT19-007','BT19-009',
                 'BT19-080','BT22-022','EX13-019','EX13-069','EX8-012','EX8-015'}
CONTEXT_FILE = Path('ARTIFACTS/ex13-engine-2026-10-30/context.json')


class BattlefieldScopeTests(unittest.TestCase):
    def runtime(self):
        runtime = ContextRuntime(selected_context(), 721, 'A', allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 1
        return runtime

    def guard(self, runtime, action='play_plain', root=ROOT):
        self.assertTrue(callable(assert_basic_board_scope), 'basic battlefield scope API missing')
        return assert_basic_board_scope(runtime, action, root)

    def snapshot(self, runtime):
        return (runtime.snapshot(), copy.deepcopy(runtime.events), runtime.halted,
                copy.deepcopy(vars(runtime.state)))

    def assert_rejected_unchanged(self, runtime, reason, action='play_plain', root=ROOT):
        before = self.snapshot(runtime)
        with self.assertRaisesRegex(RuntimeHalt, reason):
            self.guard(runtime, action, root)
        self.assertEqual(before, self.snapshot(runtime))

    def copied_root(self, destination):
        destination = Path(destination)
        context = destination / CONTEXT_FILE
        context.parent.mkdir(parents=True)
        shutil.copy2(ROOT / CONTEXT_FILE, context)
        for number in PLAIN:
            source = selected_context().card('A' if number == 'EX1-013' else 'B', number).to_dict()['official_source']
            target = destination / source['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / source['file'], target)
        return destination

    def test_empty_boards_and_both_sides_plain_singletons_are_pure_for_each_action(self):
        for action in ACTIONS:
            for live in (False, True):
                with self.subTest(action=action, live=live):
                    runtime = self.runtime()
                    if live:
                        stage(runtime, 'A', ['EX1-013'])
                        stage(runtime, 'B', ['ST7-05'], suspended=True)
                        stage(runtime, 'B', ['BT9-011'])
                    before = self.snapshot(runtime)
                    self.assertIsNone(self.guard(runtime, action))
                    self.assertEqual(before, self.snapshot(runtime))
                    self.assertEqual(runtime.matches_played, 0)
                    self.assertEqual(runtime.certification, 'EXPERIMENTAL')

    def test_unimplemented_attack_tops_remain_explicitly_outside_combat_scope(self):
        context = selected_context()
        for seat in ('A', 'B'):
            for number, _ in context.deck(seat).main:
                from option_actions import OPTION_SPECS
                if number in PLAIN | SEARCH_TOPS | set(OPTION_SPECS):
                    continue
                for action in ('attack_plain',):
                    with self.subTest(seat=seat, number=number, action=action):
                        runtime = self.runtime()
                        stage(runtime, seat, [number])
                        self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_TOP_UNSUPPORTED', action)

    def test_verified_option_tops_are_inert_for_combat_without_broadening_digimon_support(self):
        from option_actions import OPTION_SPECS
        from matchup_readiness import load_context_file
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        for number in OPTION_SPECS:
            with self.subTest(number=number):
                runtime=ContextRuntime(context,721,'A',allow_experimental=True)
                runtime.state.phase='MAIN';runtime.state.turn=3
                stage(runtime,'A',[number]);stage(runtime,'B',['EX1-013'])
                before=self.snapshot(runtime)
                self.guard(runtime,'attack_plain')
                self.assertEqual(before,self.snapshot(runtime))

    def test_existing_self_timings_do_not_block_a_different_digimon_play(self):
        context=selected_context()
        for seat in ('A','B'):
            for number,_ in context.deck(seat).main:
                if context.card(seat,number).kind not in ('Digimon','Tamer'):continue
                with self.subTest(seat=seat,number=number):
                    runtime=self.runtime();stage(runtime,seat,[number]);before=self.snapshot(runtime)
                    assert_basic_board_scope(runtime,'play_plain',ROOT,
                        event={'seat':'A','card_number':'EX1-013'})
                    self.assertEqual(self.snapshot(runtime),before)

    def test_an_actual_unimplemented_tamer_play_observer_is_not_skipped(self):
        runtime=self.runtime();stage(runtime,'A',['BT11-032'])
        before=self.snapshot(runtime)
        with self.assertRaisesRegex(RuntimeHalt,'BASIC_EVENT_OBSERVER_UNIMPLEMENTED.*BT11-032'):
            assert_basic_board_scope(runtime,'play_plain',ROOT,
                event={'seat':'A','card_number':'BT11-112'})
        self.assertEqual(self.snapshot(runtime),before)

    def test_other_card_timings_do_not_block_ordinary_play_or_breeding(self):
        c=selected_context()
        for seat in ('A','B'):
            for number,_ in c.deck(seat).main:
                if number not in OTHER_TIMINGS:continue
                for action in ('play_plain','play_search','breeding_evolve'):
                    r=self.runtime();stage(r,seat,[number]);before=self.snapshot(r)
                    self.guard(r,action)
                    self.assertEqual(before,self.snapshot(r))

    def test_encountered_search_tops_are_inert_between_their_specific_triggers(self):
        context=selected_context()
        for seat in ('A','B'):
            for number,_ in context.deck(seat).main:
                if number not in SEARCH_TOPS:continue
                for action in ACTIONS:
                    with self.subTest(number=number,action=action):
                        r=self.runtime();stage(r,seat,[number])
                        before=self.snapshot(r)
                        self.guard(r,action)
                        self.assertEqual(before,self.snapshot(r))

    def test_inherited_effects_are_checked_at_the_actual_event(self):
        for seat, numbers in (('A', ['EX1-013', 'EX1-013']),
                              ('B', ['ST7-05', 'BT9-011'])):
            for action in ACTIONS:
                with self.subTest(seat=seat, action=action):
                    runtime = self.runtime()
                    stage(runtime, seat, numbers)
                    if action=='attack_plain':
                        self.assert_rejected_unchanged(runtime,'BASIC_BOARD_STACK_UNSUPPORTED',action)
                    else:
                        before=self.snapshot(runtime);self.guard(runtime,action)
                        self.assertEqual(self.snapshot(runtime),before)

    def test_statuses_including_false_or_zero_values_are_outside_scope(self):
        for statuses in ({'cannot_play': True}, {'cannot_suspend': False},
                         {'dp_delta': 0}, {'gained_effects': []}, {'linked_cards': []}):
            with self.subTest(statuses=statuses):
                runtime = self.runtime()
                anchor = stage(runtime, 'B', ['ST7-05'])
                runtime.state.battle['B'][anchor].statuses = statuses
                self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_STATUS_UNSUPPORTED')

    def test_unknown_stack_and_global_state_metadata_are_never_assumed_inert(self):
        for field, value in (('linked_cards', []), ('gained_effects', []), ('cost_modifier', 0)):
            with self.subTest(field=field):
                runtime = self.runtime()
                anchor = stage(runtime, 'A', ['EX1-013'])
                setattr(runtime.state.battle['A'][anchor], field, value)
                self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_METADATA_UNSUPPORTED')
        runtime = self.runtime()
        runtime.state.continuous_effects = []
        self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_METADATA_UNSUPPORTED')

    def test_malformed_known_stack_metadata_is_rejected(self):
        for field, value in (('statuses', []), ('suspended', 0), ('instance_id', []),
                             ('played_turn', True), ('played_turn', -1)):
            with self.subTest(field=field, value=value):
                runtime = self.runtime()
                anchor = stage(runtime, 'A', ['EX1-013'])
                setattr(runtime.state.battle['A'][anchor], field, value)
                self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_(STATUS|METADATA)_UNSUPPORTED')

    def test_known_played_entity_metadata_is_accepted(self):
        runtime = self.runtime()
        anchor = stage(runtime, 'A', ['EX1-013'])
        stack = runtime.state.battle['A'][anchor]
        stack.instance_id = 'entity-1'
        stack.played_turn = runtime.state.turn
        self.assertIsNone(self.guard(runtime))

    def test_original_source_ids_and_context_definitions_are_required(self):
        for mutation in ('source_id', 'cost', 'main_text', 'name', 'rules', 'metadata'):
            with self.subTest(mutation=mutation):
                runtime = self.runtime()
                context = runtime.context
                decks = [context.deck_a, context.deck_b]
                cards = {card.number: card for card in context.cards}
                rules = context.to_dict()['rules']
                if mutation == 'source_id':
                    raw = decks[0].to_dict()
                    raw['source_id'] = 'unselected-list'
                    decks[0] = DeckDefinition.from_dict(raw)
                elif mutation == 'rules':
                    rules['region'] = 'altered-region'
                else:
                    raw = cards['EX1-013'].to_dict()
                    field, value = {'cost': ('play_cost', 0), 'main_text': ('main_text', '[All Turns] Test only'),
                                    'name': ('name', 'Changed'), 'metadata': ('gained_effects', [])}[mutation]
                    raw[field] = value
                    cards['EX1-013'] = CardDefinition.from_dict(raw)
                runtime.context = MatchContext.create(*decks, cards, rules)
                self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_SELECTED_CONTEXT_REQUIRED')

    def test_replacing_locked_context_and_runtime_together_cannot_expand_capability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copied_root(temporary)
            runtime = self.runtime()
            bundle = json.loads((root / CONTEXT_FILE).read_bytes())
            raw = bundle['context']
            raw['cards']['EX1-013']['main_text'] = '[All Turns] Test only'
            runtime.context = MatchContext.create(
                DeckDefinition.from_dict(raw['decks']['A']), DeckDefinition.from_dict(raw['decks']['B']),
                {number: CardDefinition.from_dict(card) for number, card in raw['cards'].items()}, raw['rules'])
            bundle['matchup_id'] = runtime.context.matchup_id
            (root / CONTEXT_FILE).write_text(json.dumps(bundle))
            self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_SELECTED_CONTEXT_REQUIRED', root=root)

    def test_missing_or_changed_official_existing_top_source_halts_without_mutation(self):
        for change in ('missing', 'altered'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = self.copied_root(temporary)
                runtime = self.runtime()
                stage(runtime, 'B', ['BT9-011'])
                source = root / runtime.context.card('B', 'BT9-011').to_dict()['official_source']['file']
                if change == 'missing':
                    source.unlink()
                else:
                    source.write_bytes(b'altered official bytes')
                self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_OFFICIAL_SOURCE_UNAVAILABLE', root=root)

    def test_missing_or_invalid_locked_context_halts(self):
        for content in (None, b'{}'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                if content is not None:
                    path = root / CONTEXT_FILE
                    path.parent.mkdir(parents=True)
                    path.write_bytes(content)
                self.assert_rejected_unchanged(self.runtime(), 'BASIC_BOARD_SELECTED_CONTEXT_REQUIRED', root=root)

    def test_unknown_action_or_missing_experimental_opt_in_halts(self):
        runtime = self.runtime()
        self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_ACTION_UNSUPPORTED', 'attack')
        runtime.allow_experimental = False
        self.assert_rejected_unchanged(runtime, 'BASIC_BOARD_EXPERIMENTAL_OPT_IN_REQUIRED')

    def test_scope_guard_does_not_inspect_hidden_zones(self):
        class HiddenZones:
            def __getitem__(self, key):
                raise AssertionError('scope guard inspected hidden zones')

            def __iter__(self):
                raise AssertionError('scope guard inspected hidden zones')

        runtime = self.runtime()
        stage(runtime, 'A', ['EX1-013'])
        hidden = runtime.state.zones
        runtime.state.zones = HiddenZones()
        try:
            self.assertIsNone(self.guard(runtime))
        finally:
            runtime.state.zones = hidden
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
