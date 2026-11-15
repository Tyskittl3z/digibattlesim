"""Physical-state/pack boundary tests, not Digimon rules certification."""
import hashlib
import json
from dataclasses import replace
import unittest
from pathlib import Path
from unittest.mock import patch

from match_context import MatchContext
from test_match_context import fixture
from context_runtime import (
    ContextRuntime, MechanicBinding, MechanicRegistry, OfficialEvidence,
    RuntimeHalt, Stack,
)


def context_with_effect(text='[On Play] Test effect.'):
    decks, cards, rules = fixture()
    raw = cards['AT1-000'].to_dict(); raw['main_text'] = text
    from match_context import CardDefinition
    cards['AT1-000'] = CardDefinition.from_dict(raw)
    return MatchContext.create(*decks, cards, rules)


def gain_memory(runtime, seat, source, choice):
    runtime.state.memory += 1
    return {'gain': 1}


def corrupt_then_fail(runtime, seat, source, choice):
    runtime.state.zones[seat]['deck'].pop()
    runtime.state.memory = 900
    runtime.rng.random()
    raise RuntimeHalt('UNRESOLVED_DEPENDENT_EFFECT')


def silent_corruption(runtime, seat, source, choice):
    runtime.state.zones[seat]['deck'].pop()
    return {}


def aliased_result(runtime, seat, source, choice):
    runtime.state.battle[seat][source].statuses['observations'] = [1]
    return runtime.state.battle[seat][source].statuses


def registry(context, handler=gain_memory, text_sha=None):
    card = context.card('A', 'AT1-000')
    body = b'official source fixture for software boundary tests only'
    evidence = OfficialEvidence.from_bytes(
        'https://world.digimoncard.com/cardlist/?card_no=AT1-000', body,
        hashlib.sha256(body).hexdigest(), 'fixture locator')
    binding = MechanicBinding(
        card_number=card.number, effect_id='test-effect', field='main_text',
        definition_sha256=card.definition_sha256,
        text_sha256=text_sha or hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
        evidence=(evidence,), handler=handler)
    return MechanicRegistry((binding,))


def put_source(runtime, seat='A'):
    deck = runtime.state.zones[seat]['deck']
    card = next(c for c in deck if c.card_number == 'AT1-000')
    deck.remove(card)
    runtime.state.battle[seat][card.key] = Stack([card])
    return card.key


class RuntimeTests(unittest.TestCase):
    def test_execution_identity_binds_shared_return_dependency(self):
        runtime = ContextRuntime(context_with_effect(), 321, 'A')
        original = runtime.execution_id
        read_bytes = Path.read_bytes

        def changed_return_source(path):
            body = read_bytes(path)
            return body + b'\n# changed return dependency\n' if path.name == 'return_effects.py' else body

        with patch.object(Path, 'read_bytes', changed_return_source):
            self.assertNotEqual(runtime.execution_id, original)

    def test_setup_is_deterministic_and_does_not_play_a_match(self):
        c = context_with_effect()
        a, b = ContextRuntime(c, 321, 'A'), ContextRuntime(c, 321, 'A')
        self.assertEqual(a.snapshot(), b.snapshot())
        self.assertEqual(len(a.state.zones['A']['deck']), 50)
        self.assertEqual(len(a.state.zones['A']['eggdeck']), 4)
        self.assertEqual(a.matches_played, 0)
        self.assertEqual(a.certification, 'EXPERIMENTAL')
        self.assertNotEqual(a.snapshot(), ContextRuntime(c, 322, 'A').snapshot())

    def test_exact_conservation_catches_duplicate_missing_and_wrong_owner(self):
        for mutation in ('duplicate', 'missing', 'wrong-owner'):
            runtime = ContextRuntime(context_with_effect(), 1, 'A')
            zones = runtime.state.zones
            if mutation == 'duplicate': zones['A']['hand'].append(zones['A']['deck'][0])
            if mutation == 'missing': zones['A']['deck'].pop()
            if mutation == 'wrong-owner': zones['B']['hand'].append(zones['A']['deck'].pop())
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeHalt, 'PHYSICAL'):
                runtime.verify()

    def test_stack_sources_count_once_and_anchor_must_match(self):
        runtime = ContextRuntime(context_with_effect(), 1, 'A')
        cards = [runtime.state.zones['A']['deck'].pop() for _ in range(2)]
        runtime.state.battle['A'][cards[-1].key] = Stack(cards)
        runtime.verify()
        runtime.state.battle['A']['bad-anchor'] = runtime.state.battle['A'].pop(cards[-1].key)
        with self.assertRaisesRegex(RuntimeHalt, 'STACK_ANCHOR'):
            runtime.verify()

    def test_public_view_never_exposes_opponent_hand_deck_security_or_rng(self):
        runtime = ContextRuntime(context_with_effect(), 1, 'A')
        b = runtime.state.zones['B']; b['hand'].append(b['deck'].pop()); b['security'].append(b['deck'].pop())
        a = runtime.state.zones['A']; a['hand'].append(a['deck'].pop())
        view = runtime.public_view('A')
        self.assertEqual(view['players']['B']['hand'], {'count': 1})
        self.assertEqual(view['players']['B']['deck'], {'count': 48})
        self.assertEqual(view['players']['B']['security'], {'count': 1})
        self.assertEqual(len(view['players']['A']['hand']), 1)
        self.assertEqual(view['players']['A']['deck'], {'count': 49})
        self.assertNotIn('rng_state', view)
        view['players']['A']['hand'].clear()
        self.assertEqual(len(runtime.state.zones['A']['hand']), 1)

    def test_dispatch_requires_exact_text_and_explicit_experimental_opt_in(self):
        c = context_with_effect()
        for explicit, text_sha, error in [(False, None, 'UNREVIEWED'), (True, '0'*64, 'TEXT_BINDING')]:
            runtime = ContextRuntime(c, 1, 'A', registry(c, text_sha=text_sha), allow_experimental=explicit)
            source = put_source(runtime); before = runtime.snapshot()['state']
            with self.subTest(error=error), self.assertRaisesRegex(RuntimeHalt, error):
                runtime.dispatch('test-effect', 'A', source, None)
            self.assertEqual(before, runtime.snapshot()['state'])

    def test_dispatch_success_logs_exact_source_and_choice_without_certification(self):
        c = context_with_effect(); runtime = ContextRuntime(c, 1, 'A', registry(c), allow_experimental=True)
        source = put_source(runtime)
        runtime.dispatch('test-effect', 'A', source, 'activate')
        self.assertEqual(runtime.state.memory, 1)
        self.assertEqual(runtime.events[-1]['source'], source)
        self.assertEqual(runtime.events[-1]['choice'], 'activate')
        self.assertEqual(runtime.events[-1]['context_id'], c.matchup_id)
        self.assertEqual(runtime.matches_played, 0)
        self.assertEqual(runtime.certification, 'EXPERIMENTAL')

    def test_unknown_mechanic_halts_before_mutation(self):
        runtime = ContextRuntime(context_with_effect(), 8, 'A', allow_experimental=True)
        source = put_source(runtime); before = runtime.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'UNSUPPORTED_MECHANIC'):
            runtime.dispatch('not-implemented', 'A', source, None)
        self.assertEqual(runtime.snapshot()['state'], before)
        self.assertEqual(runtime.events[-1]['type'], 'HALT')
        self.assertEqual(runtime.events[-1]['seed'], 8)

    def test_failed_handler_rolls_back_state_rng_and_retains_original_trace(self):
        c = context_with_effect()
        runtime = ContextRuntime(c, 45, 'A', registry(c, corrupt_then_fail), allow_experimental=True)
        source = put_source(runtime); before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt, 'UNRESOLVED_DEPENDENT_EFFECT'):
            runtime.dispatch('test-effect', 'A', source, 'activate')
        after = runtime.snapshot()
        self.assertEqual(before['state'], after['state'])
        self.assertEqual(before['rng_state'], after['rng_state'])
        self.assertEqual(runtime.events[-1]['before'], before)
        with self.assertRaisesRegex(RuntimeHalt, 'ALREADY_HALTED'):
            runtime.dispatch('test-effect', 'A', source, None)

    def test_silent_handler_corruption_is_not_committed(self):
        c = context_with_effect()
        runtime = ContextRuntime(c, 1, 'A', registry(c, silent_corruption), allow_experimental=True)
        source = put_source(runtime); before = runtime.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'PHYSICAL'):
            runtime.dispatch('test-effect', 'A', source, None)
        self.assertEqual(runtime.snapshot()['state'], before)

    def test_terminal_and_wrong_controller_dispatch_cannot_mutate(self):
        c = context_with_effect()
        runtime = ContextRuntime(c, 1, 'A', registry(c), allow_experimental=True)
        source = put_source(runtime); before = runtime.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'SOURCE_NOT_ACTIVE'):
            runtime.dispatch('test-effect', 'B', source, None)
        self.assertEqual(runtime.snapshot()['state'], before)
        runtime = ContextRuntime(c, 1, 'A', registry(c), allow_experimental=True)
        source = put_source(runtime); runtime.state.terminal = True
        before = runtime.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'AFTER_TERMINAL'):
            runtime.dispatch('test-effect', 'A', source, None)
        self.assertEqual(runtime.snapshot()['state'], before)

    def test_official_evidence_rejects_wrong_hash_or_unofficial_host(self):
        for url, sha in [('https://evil.example/card', hashlib.sha256(b'x').hexdigest()),
                         ('https://world.digimoncard.com/cardlist/', '0'*64)]:
            with self.subTest(url=url, sha=sha), self.assertRaises(ValueError):
                OfficialEvidence.from_bytes(url, b'x', sha, 'locator')

    def test_registry_rejects_ambiguous_duplicate_binding(self):
        c = context_with_effect(); binding = registry(c).bindings[0]
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            MechanicRegistry((binding, binding))

    def test_unknown_top_level_seats_cannot_hide_duplicate_physical_cards(self):
        for field in ('zones', 'battle', 'breeding'):
            runtime = ContextRuntime(context_with_effect(), 1, 'A')
            container = getattr(runtime.state, field)
            container['C'] = {'deck': [runtime.state.zones['A']['deck'][0]]}
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeHalt, 'PLAYER_SCHEMA'):
                runtime.verify()

    def test_unrecordable_choice_never_commits_and_keeps_serializable_halt(self):
        c = context_with_effect()
        runtime = ContextRuntime(c, 1, 'A', registry(c), allow_experimental=True)
        source = put_source(runtime); before = runtime.snapshot()['state']
        with self.assertRaises(RuntimeHalt):
            runtime.dispatch('test-effect', 'A', source, object())
        self.assertEqual(runtime.snapshot()['state'], before)
        self.assertTrue(runtime.halted)
        self.assertEqual(runtime.events[-1]['type'], 'HALT')
        json.dumps(runtime.events, allow_nan=False)

    def test_unrecordable_initial_state_retains_minimal_halt(self):
        c = context_with_effect()
        runtime = ContextRuntime(c, 19, 'A', registry(c), allow_experimental=True)
        source = put_source(runtime)
        runtime.state.battle['A'][source].statuses['bad'] = object()
        with self.assertRaises(RuntimeHalt):
            runtime.dispatch('test-effect', 'A', source, None)
        self.assertTrue(runtime.halted)
        self.assertEqual(runtime.events[-1]['seed'], 19)
        self.assertEqual(runtime.events[-1]['type'], 'HALT')
        self.assertEqual(runtime.state.memory, 0)
        json.dumps(runtime.events, allow_nan=False)

    def test_result_and_audit_event_cannot_alias_committed_state(self):
        c = context_with_effect()
        runtime = ContextRuntime(c, 1, 'A', registry(c, aliased_result), allow_experimental=True)
        source = put_source(runtime)
        result = runtime.dispatch('test-effect', 'A', source, None)
        result['observations'].append(2)
        self.assertEqual(runtime.state.battle['A'][source].statuses['observations'], [1])
        self.assertEqual(runtime.events[-1]['result']['observations'], [1])

    def test_security_effect_cannot_be_activated_from_battle_without_check_window(self):
        c = context_with_effect(); binding = registry(c).bindings[0]
        binding = replace(binding, field='security_text', text_sha256=hashlib.sha256(b'').hexdigest())
        runtime = ContextRuntime(c, 1, 'A', MechanicRegistry((binding,)), allow_experimental=True)
        source = put_source(runtime); before = runtime.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'SECURITY_WINDOW_UNIMPLEMENTED'):
            runtime.dispatch('test-effect', 'A', source, None, field_='security_text')
        self.assertEqual(runtime.snapshot()['state'], before)


if __name__ == '__main__':
    unittest.main()
