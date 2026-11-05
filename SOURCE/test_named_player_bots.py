"""Fresh named policy preferences; no games, training or outcome ratings."""
import copy
from dataclasses import replace
import hashlib
import importlib
import importlib.util
from pathlib import Path
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_grants import grant_effect
from match_context import canonical
from matchup_readiness import load_context_file
from test_selected_mechanics import stage


ROOT = Path(__file__).resolve().parents[1]


class NamedPlayerBotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('named_player_bots'))
        self.Bot = importlib.import_module('named_player_bots').NamedPlayerBot

    def board(self, seat):
        runtime = ContextRuntime(self.context, 17, seat, allow_experimental=True)
        runtime.state.turn = 10
        runtime.state.memory = 3
        runtime.state.phase = 'MAIN'
        own = stage(runtime, seat, ['BT11-032'])
        other = 'B' if seat == 'A' else 'A'
        target = stage(runtime, other, ['EX1-013'])
        runtime.state.battle[other][target].suspended = True
        return runtime, own, target

    def test_styles_choose_security_pressure_versus_visible_favorable_battle(self):
        for seat, expected in (('A', 'PLAYER'), ('B', 'DIGIMON')):
            runtime, attacker, target = self.board(seat)
            # Synthetic candidate set with no zero-security attack shortcut.
            view = runtime.public_view(seat)
            view['players']['B' if seat == 'A' else 'A']['security'] = {'count': 3}
            choices = [{'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': 'PLAYER'},
                       {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': target}]
            bot = self.Bot(self.context, seat)
            selected = bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
            self.assertEqual(selected['target'], 'PLAYER' if expected == 'PLAYER' else target)
            self.assertEqual(bot.manifest()['style'], 'AGGRESSIVE' if seat == 'A' else 'DEFENSIVE')

    def test_both_prefer_attack_at_zero_visible_security(self):
        for seat in ('A', 'B'):
            runtime, attacker, target = self.board(seat)
            view = runtime.public_view(seat)
            view['players']['B' if seat == 'A' else 'A']['security'] = {'count': 0}
            choice = self.Bot(self.context, seat).choose(view, [
                {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': target},
                {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': 'PLAYER'}],
                decision={'kind': 'MAIN_ACTION'})
            self.assertEqual(choice['target'], 'PLAYER')

    def test_current_unsuspend_styles_are_not_engine_support_filters(self):
        for seat in ('A', 'B'):
            runtime, digimon, _ = self.board(seat)
            tamer = stage(runtime, seat, ['BT11-112'])
            runtime.state.battle[seat][digimon].suspended = True
            runtime.state.battle[seat][tamer].suspended = True
            choice = self.Bot(self.context, seat).choose(runtime.public_view(seat),
                [None, digimon, tamer], decision={'kind': 'PENDING_CHOICE',
                    'effect_id': 'BT22-023.end_turn_unsuspend', 'source': digimon})
            self.assertEqual(choice, digimon if seat == 'A' else tamer)

    def test_defensive_prefers_suspended_printed_or_granted_blocker(self):
        runtime, digimon, _ = self.board('B')
        tamer = stage(runtime, 'B', ['BT11-112'])
        blocker = stage(runtime, 'B', ['EX13-023'])
        for key in (digimon, tamer, blocker):
            runtime.state.battle['B'][key].suspended = True
        bot = self.Bot(self.context, 'B')
        decision = {'kind': 'UNSUSPEND'}
        self.assertEqual(bot.choose(runtime.public_view('B'), [digimon, tamer, blocker],
                                    decision=decision), blocker)
        runtime.state.battle['B'][blocker].suspended = False
        grant_effect(runtime, 'B', digimon, {'keywords': ['Blocker']}, tamer)
        self.assertEqual(bot.choose(runtime.public_view('B'), [digimon, tamer, blocker],
                                    decision=decision), digimon)

    def test_expired_and_wrong_incarnation_blocker_grants_do_not_influence_choice(self):
        runtime, digimon, _ = self.board('B')
        tamer = stage(runtime, 'B', ['BT11-112'])
        for key in (digimon, tamer):
            runtime.state.battle['B'][key].suspended = True
        grant_effect(runtime, 'B', digimon, {'keywords': ['Blocker']}, tamer)
        for mutation in ('expired', 'wrong_instance'):
            view = runtime.public_view('B')
            grant = view['players']['B']['battle'][digimon]['statuses']['effect_grants'][0]
            if mutation == 'expired': grant['expires']['turn'] = 9
            else: grant['target_instance'] = 'different-entity'
            self.assertEqual(self.Bot(self.context, 'B').choose(view, [digimon, tamer],
                decision={'kind': 'UNSUSPEND'}), tamer)

    def test_optional_unsuspend_declines_when_every_target_is_already_ready(self):
        runtime, digimon, _ = self.board('B')
        bot = self.Bot(self.context, 'B')
        self.assertIsNone(bot.choose(runtime.public_view('B'), [None, digimon],
                                    decision={'kind': 'UNSUSPEND'}))

    def test_hidden_information_and_audit_snapshots_are_rejected(self):
        runtime, _, _ = self.board('A')
        original = runtime.public_view('A')
        for mutation in ('opponent_hand', 'own_deck', 'opponent_security', 'rng'):
            view = copy.deepcopy(original)
            if mutation == 'opponent_hand': view['players']['B']['hand'] = []
            if mutation == 'own_deck': view['players']['A']['deck'] = []
            if mutation == 'opponent_security': view['players']['B']['security'] = []
            if mutation == 'rng': view['rng_state'] = [1, 2]
            bot = self.Bot(self.context, 'A')
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeHalt, 'BOT_PUBLIC_VIEW'):
                bot.choose(view, [None])
            self.assertEqual(bot.decision_log, [])

    def test_deterministic_identity_logs_and_detached_results(self):
        runtime, attacker, target = self.board('A')
        view = runtime.public_view('A')
        choices = [{'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': target},
                   {'kind': 'PASS_TURN'}]
        a, b = self.Bot(self.context, 'A'), self.Bot(self.context, 'A')
        rng_before = runtime.snapshot()['rng_state']
        chosen_a = a.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
        chosen_b = b.choose(view, list(reversed(choices)), decision={'kind': 'MAIN_ACTION'})
        self.assertEqual(chosen_a, chosen_b)
        self.assertEqual(a.manifest(), b.manifest())
        self.assertNotEqual(a.manifest()['bot_id'], self.Bot(self.context, 'B').manifest()['bot_id'])
        self.assertEqual(runtime.snapshot()['rng_state'], rng_before)
        self.assertEqual(set(a.decision_log[0]),
            {'decision', 'public_view_sha256', 'candidates', 'chosen', 'reason', 'bot_id'})
        self.assertNotIn('rating', a.decision_log[0])
        chosen_a['kind'] = 'CORRUPTED'
        choices.clear()
        self.assertEqual(a.decision_log[0]['chosen'], chosen_b)
        self.assertEqual(a.manifest()['training_data'], [])

    def test_identity_binds_source_config_context_and_manifest_is_detached(self):
        bot = self.Bot(self.context, 'A')
        manifest = bot.manifest()
        self.assertEqual(manifest['source_sha256'], hashlib.sha256(
            (ROOT / 'SOURCE/named_player_bots.py').read_bytes()).hexdigest())
        changed = replace(self.context, _rules=canonical({'fixture': 'other-context'}))
        self.assertNotEqual(manifest['bot_id'], self.Bot(changed, 'A').manifest()['bot_id'])
        manifest['configuration']['priorities'].clear()
        self.assertTrue(bot.manifest()['configuration']['priorities'])

    def test_stable_bottom_order_is_recorded_without_rng(self):
        bot = self.Bot(self.context, 'A')
        keys = ['A:BT11-032#1', 'A:EX1-013#1']
        self.assertEqual(bot.bottom_order(list(reversed(keys))), keys)
        self.assertEqual(bot.decision_log[-1]['decision'], {'kind': 'BOTTOM_ORDER'})

    def test_explicit_reveals_evolution_and_pending_order_shapes_are_supported(self):
        runtime, base, _ = self.board('A')
        view = runtime.public_view('A')
        bot = self.Bot(self.context, 'A')
        reveal = [['A:EX1-013#1'], ['A:BT11-032#2']]
        self.assertIn(bot.choose(view, reveal, decision={'kind': 'SEARCH_SELECTION'}), reveal)
        evolves = [None, {'source_key': base, 'hand_key': 'A:BT11-032#2', 'route_index': 0}]
        self.assertEqual(bot.choose(view, evolves, decision={'kind': 'EVOLUTION'}), evolves[1])
        pending = [{'id': 'effect-2', 'effect_id': 'sample.second', 'source': base},
                   {'id': 'effect-1', 'effect_id': 'sample.first', 'source': base}]
        self.assertEqual(bot.choose(view, pending, decision={'kind': 'PENDING_EFFECT_ORDER'}), pending[1])

    def test_unknown_choice_shape_never_becomes_an_automatic_decline(self):
        runtime, _, _ = self.board('A')
        bot = self.Bot(self.context, 'A')
        for choices in ([None, {'mystery': True}], [None, 'unrecognized choice'], [False, True]):
            with self.subTest(choices=choices), self.assertRaisesRegex(RuntimeHalt, 'BOT_CHOICE'):
                bot.choose(runtime.public_view('A'), choices)
        self.assertEqual(bot.decision_log, [])

    def test_malformed_delay_and_bottom_order_shapes_fail_precisely(self):
        runtime, _, _ = self.board('A')
        bot = self.Bot(self.context, 'A')
        with self.assertRaisesRegex(RuntimeHalt, 'BOT_CHOICE'):
            bot.choose(runtime.public_view('A'), [{'activate': False},
                {'activate': True, 'evolution': 12}], decision={'kind': 'DELAY'})
        with self.assertRaisesRegex(RuntimeHalt, 'BOT_CHOICE'):
            bot.bottom_order([[]])


if __name__ == '__main__':
    unittest.main()
