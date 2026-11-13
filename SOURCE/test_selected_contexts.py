"""Exact source-pinned contexts share basic actions, never arbitrary effects."""
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from breeding_evolution import choose_breeding_evolution
from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
from main_actions import choose_play
from match_context import CardDefinition, DeckDefinition, MatchContext
from matchup_readiness import load_context_file
from search_effects import search_choices
from selected_mechanics import build_selected_registry

ROOT = Path(__file__).resolve().parents[1]
MIRROR = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'


def from_raw(raw):
    return MatchContext.create(DeckDefinition.from_dict(raw['decks']['A']),
                               DeckDefinition.from_dict(raw['decks']['B']),
                               {n: CardDefinition.from_dict(d) for n, d in raw['cards'].items()},
                               raw['rules'])


class SelectedContextTests(unittest.TestCase):
    def supported(self, operation, *args):
        try:
            return operation(*args)
        except RuntimeHalt as exc:
            self.fail('Expected selected mirror basic action to resolve: ' + str(exc))

    def runtime(self, seat='A', context=None):
        context = context or load_context_file(ROOT / MIRROR)
        runtime = ContextRuntime(context, 187, seat, build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.active = seat
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 1
        runtime.state.memory = 10
        return runtime

    def hand(self, runtime, seat, number):
        zones = runtime.state.zones[seat]
        card = next(c for c in zones['deck'] if c.card_number == number)
        zones['deck'].remove(card)
        zones['hand'].append(card)
        return card.key

    def test_mirror_plain_hard_play_uses_own_exact_card_and_cost_in_both_seats(self):
        for seat in ('A', 'B'):
            with self.subTest(seat=seat):
                runtime = self.runtime(seat)
                key = self.hand(runtime, seat, 'EX1-013')
                result = self.supported(choose_play, runtime, seat, key, ROOT)
                self.assertEqual([c.key for c in runtime.state.battle[seat][key].cards], [key])
                self.assertEqual(runtime.state.memory, 10 - result['cost'])
                self.assertEqual(result['scope_context_id'], runtime.context.matchup_id)
                self.assertEqual(result['triggered_effects'], [])
                runtime.verify()

    def test_mirror_search_resolves_using_that_seats_physical_revealed_cards(self):
        for seat in ('A', 'B'):
            with self.subTest(seat=seat):
                runtime = self.runtime(seat)
                key = self.hand(runtime, seat, 'BT11-023')
                self.supported(choose_play, runtime, seat, key, ROOT)
                pending = pending_options(runtime, seat)
                self.assertEqual(len(pending), 1)
                choices = search_choices(runtime, seat, key)
                selection = choices['selections'][0]
                bottom = [k for k in choices['revealed'] if k not in selection]
                result = resolve_pending(runtime, seat, pending[0]['id'],
                                         {'selected': selection, 'bottom_order': bottom})
                self.assertEqual(result['selected'], selection)
                self.assertEqual([c.key for c in runtime.state.zones[seat]['deck'][:len(bottom)]], bottom)
                self.assertTrue(all(k.startswith(seat + ':') for k in choices['revealed']))
                runtime.verify()

    def test_mirror_breeding_evolution_pays_printed_cost_and_draws(self):
        runtime = self.runtime('B')
        egg = next(c for c in runtime.state.zones['B']['eggdeck'] if c.card_number == 'EX13-002')
        runtime.state.zones['B']['eggdeck'].remove(egg)
        runtime.state.breeding['B'] = [egg]
        key = self.hand(runtime, 'B', 'EX13-017')
        draw = runtime.state.zones['B']['deck'][-1].key
        before = len(runtime.state.zones['B']['hand'])
        result = self.supported(choose_breeding_evolution, runtime, 'B', key, 0, ROOT)
        self.assertEqual(runtime.state.breeding['B'][-1].key, key)
        self.assertEqual(runtime.state.memory, 10 - result['cost'])
        self.assertEqual(len(runtime.state.zones['B']['hand']), before)
        self.assertIn(draw, [c.key for c in runtime.state.zones['B']['hand']])
        self.assertFalse(runtime.state.pending, 'Breeding does not activate the ordinary On Play search')
        runtime.verify()

    def test_mirror_basic_attack_keeps_explicit_windows_and_physical_identity(self):
        from attack_flow import declare_attack, choose_counter, choose_blocker, confirm_attack, end_attack
        runtime = self.runtime()
        key = self.hand(runtime, 'A', 'EX1-013')
        self.supported(choose_play, runtime, 'A', key, ROOT)
        checked_key = self.hand(runtime, 'B', 'EX1-013')
        checked = runtime.state.zones['B']['hand'].pop()
        runtime.state.zones['B']['security'].append(checked)
        runtime.state.turn = 2
        self.supported(declare_attack, runtime, 'A', key, 'PLAYER', ROOT)
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        self.assertEqual(runtime.state.attack['attacker'], key)
        self.supported(choose_counter, runtime, 'B', None, ROOT)
        self.assertEqual(runtime.state.attack['window'], 'BLOCK')
        self.supported(choose_blocker, runtime, 'B', None, ROOT)
        self.supported(confirm_attack, runtime, 'A', ROOT)
        self.assertFalse(runtime.state.terminal, 'The last security check is not a direct attack')
        self.assertIn(checked_key, [c.key for c in runtime.state.zones['B']['trash']])
        self.assertEqual(runtime.state.attack['window'], 'END')
        self.supported(end_attack, runtime, 'A', ROOT)
        self.assertIsNone(runtime.state.attack)
        self.assertEqual(runtime.matches_played, 0)
        runtime.verify()

    def test_readiness_binds_the_capability_resolver_source_bytes(self):
        from matchup_readiness import inspect_readiness
        runtime = self.runtime()
        report = inspect_readiness(runtime.context, runtime.registry, ROOT)
        actual = hashlib.sha256((ROOT / 'SOURCE/selected_contexts.py').read_bytes()).hexdigest()
        self.assertEqual(report['engine_source_sha256'].get('selected_contexts.py'), actual)

    def assert_rejected_without_movement(self, context, root=ROOT):
        runtime = self.runtime(context=context)
        key = self.hand(runtime, 'A', 'EX1-013')
        before = copy.deepcopy(runtime.snapshot())
        with self.assertRaises(RuntimeHalt):
            choose_play(runtime, 'A', key, root)
        self.assertEqual(runtime.snapshot()['state'], before['state'])
        self.assertEqual(runtime.snapshot()['rng_state'], before['rng_state'])
        self.assertTrue(runtime.halted)

    def test_same_composition_with_changed_source_id_is_not_authorized(self):
        original = load_context_file(ROOT / MIRROR)
        raw = original.to_dict()
        raw['decks']['B']['source_id'] = 'unselected-copy'
        changed = from_raw(raw)
        self.assertEqual(changed.matchup_id, original.matchup_id,
                         'Composition identity deliberately excludes source ID')
        self.assert_rejected_without_movement(changed)

    def test_changed_deck_counts_do_not_gain_capability(self):
        raw = load_context_file(ROOT / MIRROR).to_dict()
        main = raw['decks']['B']['main']
        next(c for c in main if c['card_number'] == 'EX1-013')['quantity'] += 1
        next(c for c in main if c['card_number'] == 'P-138')['quantity'] -= 1
        self.assert_rejected_without_movement(from_raw(raw))

    def test_changed_rules_do_not_gain_capability(self):
        raw = load_context_file(ROOT / MIRROR).to_dict()
        raw['rules']['region'] = 'Different region'
        self.assert_rejected_without_movement(from_raw(raw))

    def test_changed_card_wording_does_not_gain_capability(self):
        raw = load_context_file(ROOT / MIRROR).to_dict()
        raw['cards']['P-104']['main_text'] += '\n[Main] Draw 99.'
        self.assert_rejected_without_movement(from_raw(raw))

    def test_editing_on_disk_lock_does_not_authorize_its_changed_source_id(self):
        self.assertIsNotNone(importlib.util.find_spec('selected_contexts'),
                             'Shared exact-context capability is required')
        from selected_contexts import require_selected_context
        raw = load_context_file(ROOT / MIRROR).to_dict()
        raw['decks']['B']['source_id'] = 'forged-source'
        # Source IDs are excluded from matchup_id, so the loader accepts this
        # structure; capability binding must reject the altered lock separately.
        changed = from_raw(raw)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / MIRROR
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'matchup_id': changed.matchup_id, 'context': raw}))
            with self.assertRaisesRegex(RuntimeHalt, 'BASIC_BOARD_SELECTED_CONTEXT_REQUIRED'):
                require_selected_context(load_context_file(ROOT / MIRROR), root)


if __name__ == '__main__':
    unittest.main()
