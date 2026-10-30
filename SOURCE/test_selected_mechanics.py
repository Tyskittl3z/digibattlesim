"""Focused official-text scenarios. Every scenario counts as zero full matches."""
import json
from pathlib import Path
import unittest

from match_context import CardDefinition, DeckDefinition, MatchContext
from context_runtime import ContextRuntime, RuntimeHalt, Stack
from selected_mechanics import build_selected_registry, orientation_candidates, ORIENTATION_EFFECT

ROOT = Path(__file__).resolve().parents[1]


def selected_context():
    raw = json.loads((ROOT/'ARTIFACTS/ex13-engine-2026-10-30/context.json').read_bytes())['context']
    return MatchContext.create(DeckDefinition.from_dict(raw['decks']['A']),
                               DeckDefinition.from_dict(raw['decks']['B']),
                               {k: CardDefinition.from_dict(v) for k, v in raw['cards'].items()},
                               raw['rules'])


def stage(runtime, seat, numbers, *, suspended=False):
    cards = []
    for number in numbers:
        deck = runtime.state.zones[seat]['deck']
        card = next(c for c in deck if c.card_number == number)
        deck.remove(card); cards.append(card)
    key = cards[-1].key
    runtime.state.battle[seat][key] = Stack(cards, suspended=suspended)
    runtime.verify()
    return key


class OrientationTests(unittest.TestCase):
    def runtime(self):
        context = selected_context()
        return ContextRuntime(context, 101, 'A', build_selected_registry(context, ROOT),
                              allow_experimental=True)

    def test_only_own_battle_digimon_are_offered_plus_optional_decline(self):
        r = self.runtime(); source = stage(r, 'A', ['EX13-023'])
        target = stage(r, 'A', ['BT11-023'])
        tamer = stage(r, 'A', ['BT22-085'])
        enemy = stage(r, 'B', ['EX13-015'])
        choices = orientation_candidates(r, 'A', source)
        self.assertEqual(set(choices), {None, source, target})
        self.assertNotIn(tamer, choices); self.assertNotIn(enemy, choices)

    def test_suspends_unsuspended_or_unsuspends_suspended_target(self):
        for suspended in (True, False):
            r = self.runtime(); source = stage(r, 'A', ['EX13-023'], suspended=suspended)
            result = r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
            self.assertEqual(r.state.battle['A'][source].suspended, not suspended)
            self.assertEqual(result['changed'], True)
            self.assertEqual(result['suspended_after'], not suspended)
            self.assertEqual(r.matches_played, 0)

    def test_declining_resolution_still_consumes_activated_once_per_turn(self):
        r = self.runtime(); source = stage(r, 'A', ['EX13-023'])
        result = r.dispatch(ORIENTATION_EFFECT, 'A', source, None)
        self.assertFalse(result['changed'])
        self.assertFalse(r.state.battle['A'][source].suspended)
        before = r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'ONCE_PER_TURN'):
            r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
        self.assertEqual(r.snapshot()['state'], before)

    def test_usage_is_independent_per_physical_copy_and_resets_on_new_turn(self):
        r = self.runtime(); first = stage(r, 'A', ['EX13-023']); second = stage(r, 'A', ['EX13-023'])
        r.dispatch(ORIENTATION_EFFECT, 'A', first, first)
        r.dispatch(ORIENTATION_EFFECT, 'A', second, second)
        self.assertTrue(r.state.battle['A'][first].suspended)
        self.assertTrue(r.state.battle['A'][second].suspended)
        r.state.turn += 1
        r.dispatch(ORIENTATION_EFFECT, 'A', first, first)
        self.assertFalse(r.state.battle['A'][first].suspended)

    def test_prohibited_orientation_does_not_change_but_consumes_activation(self):
        r = self.runtime(); source = stage(r, 'A', ['EX13-023'])
        r.state.battle['A'][source].statuses['cannot_suspend'] = True
        result = r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
        self.assertFalse(result['changed'])
        self.assertFalse(r.state.battle['A'][source].suspended)
        with self.assertRaisesRegex(RuntimeHalt, 'ONCE_PER_TURN'):
            r.dispatch(ORIENTATION_EFFECT, 'A', source, None)

    def test_opponent_or_tamer_target_is_rejected_without_mutation(self):
        for number, seat in [('EX13-015', 'B'), ('BT22-085', 'A')]:
            r = self.runtime(); source = stage(r, 'A', ['EX13-023']); target = stage(r, seat, [number])
            before = r.snapshot()['state']
            with self.assertRaisesRegex(RuntimeHalt, 'ORIENTATION_TARGET'):
                r.dispatch(ORIENTATION_EFFECT, 'A', source, target)
            self.assertEqual(r.snapshot()['state'], before)

    def test_inherited_suspension_trigger_is_not_silently_skipped(self):
        r = self.runtime(); source = stage(r, 'A', ['EX13-022', 'EX13-023'])
        before = r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'ORIENTATION_DEPENDENT_TRIGGER.*EX13-022'):
            r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
        self.assertEqual(r.snapshot()['state'], before)

    def test_tamer_unsuspend_trigger_is_not_silently_skipped(self):
        r = self.runtime(); source = stage(r, 'A', ['EX13-023'], suspended=True)
        stage(r, 'A', ['EX13-069'])
        before = r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'ORIENTATION_DEPENDENT_TRIGGER.*EX13-069'):
            r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
        self.assertEqual(r.snapshot()['state'], before)

    def test_dp_status_requires_rule_check_before_orientation(self):
        r = self.runtime(); source = stage(r, 'A', ['EX13-023'])
        r.state.battle['A'][source].statuses['dp_delta'] = -12000
        before = r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt, 'ORIENTATION_STATUS_UNSUPPORTED'):
            r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
        self.assertEqual(r.snapshot()['state'], before)


if __name__ == '__main__':
    unittest.main()
