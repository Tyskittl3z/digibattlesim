"""Private synthetic public-view fixtures; no game/deal/cohort is started."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import unittest

from context_runtime import RuntimeHalt
from match_context import digest
from matchup_readiness import load_context_file


ROOT = Path(__file__).resolve().parents[1]


class InteractionLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('interaction_learning'),
                             'interaction_learning implementation is missing')
        self.module = importlib.import_module('interaction_learning')
        self.State, self.Bot = self.module.LearningState, self.module.LearningPlayerBot

    def fixture(self, seat='A'):
        def stack(key, identity):
            return {'cards': [key], 'suspended': False, 'statuses': {},
                    'instance_id': identity, 'played_turn': 0, 'ready_since_turn': 0}
        players = {s: {'hand': ['A:EX13-017#1'] if s == seat else {'count': 1},
            'deck': {'count': 46}, 'eggdeck': {'count': 3}, 'security': {'count': 3},
            'trash': [], 'battle': {}, 'breeding': []} for s in ('A', 'B')}
        if seat == 'B':
            players['B']['hand'] = ['B:EX13-017#1']
        own, other = seat + ':BT11-032#1', ('B' if seat == 'A' else 'A') + ':EX1-013#1'
        players[seat]['battle'][own] = stack(own, 'entity-1')
        players['B' if seat == 'A' else 'A']['battle'][other] = stack(other, 'entity-2')
        players['B' if seat == 'A' else 'A']['battle'][other]['suspended'] = True
        view = {'active': seat, 'memory': 3, 'turn': 8, 'phase': 'MAIN', 'attack': None,
                'terminal': False, 'winner': None, 'players': players, 'resolving_option': None}
        choices = [{'kind': 'DECLARE_ATTACK', 'attacker': own, 'target': 'PLAYER'},
                   {'kind': 'PASS_TURN'}]
        return view, choices

    def bot(self, state=None, seat='A', seed=0):
        return self.Bot(self.context, seat, state or self.State(), seed)

    def record(self, state=None, *, chosen_kind=None, reward=4, seat='A'):
        state = state or self.State()
        view, choices = self.fixture(seat)
        for seed in range(300):
            bot = self.bot(state, seat, seed)
            chosen = bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
            if chosen_kind is None or chosen['kind'] == chosen_kind:
                record = copy.deepcopy(bot.decision_log[-1])
                record.update(status='EXPERIMENTAL_RESOLVED', reward=reward)
                return record
        self.fail('exploration did not expose requested public candidate')

    def game_id(self, index):
        return digest({'campaign_id': 'private-unit-fixture', 'context_id': self.context.matchup_id,
                       'index': index, 'seed': index + 100})

    def train(self, state, index, **kwargs):
        record = self.record(state, **kwargs)
        self.assertTrue(state.update_completed(self.game_id(index), 'A', [record]))
        return record

    def test_fresh_export_is_strict_deterministic_and_detached(self):
        a, b = self.State(), self.State()
        self.assertEqual(a.export(), b.export())
        self.assertEqual(a.export()['tables'], {'A': {}, 'B': {}})
        self.assertEqual(a.state_id, b.state_id)
        self.assertEqual(self.State.from_dict(json.loads(json.dumps(a.export()))).export(), a.export())
        exported = a.export()
        exported['tables']['A']['bad'] = {}
        self.assertEqual(a.export()['tables']['A'], {})

    def test_actual_named_styles_are_the_cold_start_prior(self):
        for seat in ('A', 'B'):
            view, choices = self.fixture(seat)
            own = choices[0]['attacker']
            other = next(iter(view['players']['B' if seat == 'A' else 'A']['battle']))
            choices.append({'kind': 'DECLARE_ATTACK', 'attacker': own, 'target': other})
            bot = self.bot(seat=seat)
            selected = bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
            self.assertEqual(selected['target'], 'PLAYER' if seat == 'A' else other)
            self.assertEqual(bot.manifest()['prior']['style'], 'AGGRESSIVE' if seat == 'A' else 'DEFENSIVE')
            self.assertEqual(bot.decision_log[-1]['learning']['mode'], 'NAMED_PRIOR')

    def test_three_independent_games_are_needed_to_override_prior(self):
        state = self.State()
        for index in range(3):
            self.train(state, index, chosen_kind='PASS_TURN', reward=5)
            view, choices = self.fixture()
            bot = self.bot(state)
            selected = bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
            self.assertEqual(selected['kind'], 'PASS_TURN' if index == 2 else 'DECLARE_ATTACK')
        learning = bot.decision_log[-1]['learning']
        self.assertEqual(learning['support'], 3)
        self.assertEqual(learning['mode'], 'LEARNED_BOARD_REWARD')
        self.assertEqual(state.export()['tables']['B'], {})

    def test_repeated_state_action_in_game_counts_once_with_game_mean_reward(self):
        state = self.State()
        a = self.record(state, reward=8)
        b = copy.deepcopy(a); b['reward'] = -2
        self.assertTrue(state.update_completed(self.game_id(0), 'B', [a, b]))
        learning = a['learning']
        row = state.export()['tables']['A'][learning['state_key']][learning['action_key']]
        self.assertEqual(row['independent_games'], 1)
        self.assertEqual(row['mean_reward'], 3)
        self.assertEqual((row['wins'], row['losses']), (0, 1))

    def test_duplicate_game_is_idempotent_and_conflicting_log_is_rejected(self):
        state = self.State(); record = self.train(state, 0)
        before = state.export()
        self.assertFalse(state.update_completed(self.game_id(0), 'A', [record]))
        self.assertEqual(before, state.export())
        changed = copy.deepcopy(record); changed['reason'] += ' changed evidence'
        with self.assertRaisesRegex(RuntimeHalt, 'DUPLICATE'):
            state.update_completed(self.game_id(0), 'A', [changed])
        self.assertEqual(before, state.export())

    def test_all_records_validate_before_any_mutation(self):
        for mutation in ('reward', 'status', 'context', 'seat', 'key', 'input'):
            state = self.State(); good = self.record(state); bad = copy.deepcopy(good)
            if mutation == 'reward': bad['reward'] = float('nan')
            elif mutation == 'status': bad['status'] = 'HALT'
            elif mutation == 'context': bad['learning']['context_id'] = 'f' * 64
            elif mutation == 'seat': bad['learning']['seat'] = 'C'
            elif mutation == 'key': bad['learning']['action_key'] = 'bad'
            elif mutation == 'input': bad['learning']['input_state_id'] = 'f' * 64
            before = state.export()
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt):
                state.update_completed(self.game_id(0), 'A', [good, bad])
            self.assertEqual(before, state.export())

    def test_paused_halted_or_ineligible_games_do_not_train(self):
        state = self.State(); record = self.record(state)
        before = state.export()
        self.assertFalse(state.update_completed(self.game_id(0), None, [record], eligible=False))
        for status in ('PAUSED', 'HALT', 'UNRATED', None):
            bad = copy.deepcopy(record); bad['status'] = status
            with self.subTest(status=status), self.assertRaises(RuntimeHalt):
                state.update_completed(self.game_id(0), 'A', [bad])
        self.assertEqual(before, state.export())

    def test_singleton_and_procedural_have_evidence_without_strategic_credit(self):
        state = self.State(); view, choices = self.fixture(); bot = self.bot(state)
        bot.choose(view, choices[:1], decision={'kind': 'MAIN_ACTION'})
        singleton = copy.deepcopy(bot.decision_log[-1])
        self.assertFalse(singleton['learning']['eligible_choice'])
        singleton.update(status='EXPERIMENTAL_RESOLVED', reward=100)
        procedural = self.record(state); procedural['learning_eligible'] = False
        state.update_completed(self.game_id(0), 'A', [singleton, procedural])
        self.assertEqual(state.export()['tables'], {'A': {}, 'B': {}})
        self.assertEqual(len(state.export()['games']), 1)

    def test_model_is_copied_and_input_hash_remains_frozen_within_game(self):
        state = self.State(); bot = self.bot(state); input_id = state.state_id
        for index in range(3): self.train(state, index, chosen_kind='PASS_TURN')
        view, choices = self.fixture()
        self.assertEqual(bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})['kind'], 'DECLARE_ATTACK')
        self.assertEqual(bot.decision_log[-1]['learning']['input_state_id'], input_id)
        self.assertEqual(bot.manifest()['input_state_id'], input_id)

    def test_export_hash_schema_tables_and_context_are_validated(self):
        state = self.State(); record = self.train(state, 0)
        for mutation in ('extra', 'hash', 'table', 'context', 'config'):
            exported = state.export()
            if mutation == 'extra': exported['unexpected'] = True
            elif mutation == 'hash': exported['state_id'] = 'f' * 64
            elif mutation == 'table':
                learning = record['learning']
                exported['tables']['A'][learning['state_key']][learning['action_key']]['wins'] += 1
                exported['state_id'] = digest({k: v for k, v in exported.items() if k != 'state_id'})
            elif mutation == 'context':
                exported['context_id'] = None
                exported['state_id'] = digest({k: v for k, v in exported.items() if k != 'state_id'})
            else:
                exported['configuration']['epsilon'] = 0
                exported['state_id'] = digest({k: v for k, v in exported.items() if k != 'state_id'})
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt):
                self.State.from_dict(exported)

    def test_state_and_action_keys_ignore_copy_entity_pending_identity(self):
        view, choices = self.fixture(); a = self.bot()
        stack = view['players']['A']['battle'].pop('A:BT11-032#1')
        stack['cards'] = ['A:BT22-023#1']; stack['suspended'] = True
        view['players']['A']['battle']['A:BT22-023#1'] = stack
        decision = {'kind': 'PENDING_CHOICE', 'effect_id': 'BT22-023.end_turn_unsuspend',
                    'source': 'A:BT22-023#1', 'selected_pending': {'id': 'effect-1', 'field': 'main_text'}}
        a.choose(view, ['A:BT22-023#1', None], decision=decision)
        changed = copy.deepcopy(view)
        stack = changed['players']['A']['battle'].pop('A:BT22-023#1')
        stack['cards'] = ['A:BT22-023#3']; stack['instance_id'] = 'entity-99'
        changed['players']['A']['battle']['A:BT22-023#3'] = stack
        decision['source'] = 'A:BT22-023#3'; decision['selected_pending']['id'] = 'effect-999'
        b = self.bot(); b.choose(changed, ['A:BT22-023#3', None], decision=decision)
        for key in ('state_key', 'action_key'):
            self.assertEqual(a.decision_log[-1]['learning'][key], b.decision_log[-1]['learning'][key])

    def test_duplicate_physical_candidates_are_not_strategic_alternatives(self):
        view, _ = self.fixture(); bot = self.bot()
        bot.choose(view, ['A:EX1-013#1', 'A:EX1-013#2'], decision={'kind': 'SEARCH_SELECTION'})
        self.assertFalse(bot.decision_log[-1]['learning']['eligible_choice'])

    def test_private_metadata_and_hidden_views_fail_before_rng_or_log_mutation(self):
        for mutation in ('opponent_hand', 'nested_player', 'decision', 'candidate', 'stack'):
            view, choices = self.fixture(); decision = {'kind': 'MAIN_ACTION'}; bot = self.bot()
            if mutation == 'opponent_hand': view['players']['B']['hand'] = ['B:EX1-013#2']
            elif mutation == 'nested_player': view['players']['A']['private_deck'] = []
            elif mutation == 'decision': decision['private_snapshot'] = {'deck': ['secret']}
            elif mutation == 'candidate': choices[0]['private_deck'] = ['secret']
            else: view['players']['A']['battle'][choices[0]['attacker']]['private'] = True
            before = bot.export_rng()
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt):
                bot.choose(view, choices, decision=decision)
            self.assertEqual(bot.export_rng(), before)
            self.assertEqual(bot.decision_log, [])

    def test_all_candidates_are_validated_before_exploration(self):
        view, _ = self.fixture(); bot = self.bot(seed=31); before = bot.export_rng()
        with self.assertRaises(RuntimeHalt):
            bot.choose(view, [None, {'mystery': True}], decision={'kind': 'MAIN_ACTION'})
        self.assertEqual(bot.export_rng(), before)
        self.assertEqual(bot.decision_log, [])

    def test_rng_roundtrip_restores_exact_choices_and_records_boundaries(self):
        view, choices = self.fixture(); a = self.bot(seed=31)
        a.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
        checkpoint = json.loads(json.dumps(a.export_rng()))
        b = self.bot(seed=31); b.restore_rng(checkpoint)
        self.assertEqual(a.choose(view, choices, decision={'kind': 'MAIN_ACTION'}),
                         b.choose(view, choices, decision={'kind': 'MAIN_ACTION'}))
        self.assertEqual(a.export_rng(), b.export_rng())
        log = b.decision_log[-1]['learning']
        self.assertEqual(log['rng_before'], checkpoint)
        self.assertEqual(log['rng_after'], b.export_rng())
        self.assertTrue(self.module.verify_decision_rng(b.decision_log[-1], checkpoint))

    def test_rng_restore_is_strict_context_bound_and_atomic(self):
        bot = self.bot(seed=31); original = bot.export_rng()
        for mutation in ('hash', 'seat', 'seed', 'version', 'vector', 'gauss'):
            changed = copy.deepcopy(original)
            if mutation == 'hash': changed['rng_sha256'] = 'f' * 64
            elif mutation == 'seat': changed['seat'] = 'B'
            elif mutation == 'seed': changed['policy_seed'] = True
            elif mutation == 'version': changed['state'][0] = 2
            elif mutation == 'vector': changed['state'][1][0] = True
            else: changed['state'][2] = float('inf')
            if mutation not in ('hash', 'gauss'):
                changed['rng_sha256'] = digest({k: v for k, v in changed.items() if k != 'rng_sha256'})
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt): bot.restore_rng(changed)
            self.assertEqual(bot.export_rng(), original)

    def test_bottom_order_is_fixed_logged_and_never_trains(self):
        bot = self.bot(); before = bot.export_rng()
        result = bot.bottom_order(['A:EX1-013#1', 'A:BT11-032#1'])
        self.assertEqual(result, ['A:BT11-032#1', 'A:EX1-013#1'])
        self.assertEqual(bot.export_rng(), before)
        self.assertFalse(bot.decision_log[-1]['learning']['eligible_choice'])
        self.assertEqual(bot.decision_log[-1]['learning']['rng_before'], before)

    def test_empty_search_remainder_is_valid_nonlearning_evidence(self):
        state = self.State(); bot = self.bot(state); before = bot.export_rng()
        self.assertEqual(bot.bottom_order([]), [])
        self.assertEqual(self.module.verify_decision_rng(bot.decision_log[-1], before), before)
        record = copy.deepcopy(bot.decision_log[-1])
        record.update(status='EXPERIMENTAL_RESOLVED', reward=1)
        state.update_completed(self.game_id(0), 'A', [record])
        self.assertEqual(state.export()['tables'], {'A': {}, 'B': {}})

    def test_export_rejects_boolean_or_float_support_even_with_rehashed_payload(self):
        state = self.State(); record = self.train(state, 0)
        learning = record['learning']
        for field, value in (('independent_games', True), ('wins', 1.0), ('losses', False)):
            exported = state.export()
            exported['tables']['A'][learning['state_key']][learning['action_key']][field] = value
            exported['state_id'] = digest({k: v for k, v in exported.items() if k != 'state_id'})
            with self.subTest(field=field), self.assertRaises(RuntimeHalt): self.State.from_dict(exported)

    def test_observed_board_reward_can_be_learned_despite_losing_game_association(self):
        state = self.State()
        for index in range(3):
            record = self.record(state, chosen_kind='PASS_TURN', reward=5)
            state.update_completed(self.game_id(index), 'B', [record])
        view, choices = self.fixture(); bot = self.bot(state)
        self.assertEqual(bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})['kind'], 'PASS_TURN')
        row = state.export()['tables']['A'][record['learning']['state_key']][record['learning']['action_key']]
        self.assertEqual((row['wins'], row['losses'], row['mean_reward']), (0, 3, 5))

    def test_nested_pending_private_metadata_is_rejected_before_log_or_rng(self):
        view, _ = self.fixture(); bot = self.bot(); before = bot.export_rng()
        pending = {'id': 'effect-1', 'source': 'A:BT11-032#1',
                   'effect_id': 'BT11-032.when_attacking', 'trigger': {'deck': ['secret']}}
        for candidates, decision in (([None, pending], {'kind': 'PENDING_EFFECT_ORDER'}),
                ([None], {'kind': 'PENDING_CHOICE', 'selected_pending': pending})):
            with self.assertRaises(RuntimeHalt): bot.choose(view, candidates, decision=decision)
        self.assertEqual(bot.export_rng(), before)
        self.assertEqual(bot.decision_log, [])

    def test_rng_proof_rejects_learning_support_and_decision_schema_tampering(self):
        record = self.record()
        for mutation in ('support', 'eligible', 'decision', 'candidate'):
            changed = copy.deepcopy(record)
            if mutation == 'support': changed['learning']['support'] = True
            elif mutation == 'eligible': changed['learning']['eligible_choice'] = 'yes'
            elif mutation == 'decision': changed['decision']['private'] = ['secret']
            else: changed['candidates'][0]['private'] = ['secret']
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt):
                self.module.verify_decision_rng(changed)

    def test_saved_public_inputs_are_verified_without_constructing_a_policy(self):
        view, choices = self.fixture(); bot = self.bot()
        bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
        record = bot.decision_log[-1]; manifest = bot.manifest()
        verifier = getattr(self.module, 'verify_decision_input', None)
        self.assertTrue(callable(verifier), 'pure saved-public-input proof is missing')
        self.assertTrue(verifier(record, view, self.context, manifest))
        for mutation in ('state_key', 'action_key', 'input_state_id', 'bot_id', 'view_hash'):
            changed = copy.deepcopy(record)
            if mutation == 'view_hash': changed['public_view_sha256'] = 'f' * 64
            elif mutation == 'bot_id': changed['bot_id'] = 'f' * 64
            else: changed['learning'][mutation] = 'f' * 64
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt):
                verifier(changed, view, self.context, manifest)

    def test_nonexistent_copies_and_invisible_opponent_sources_are_rejected(self):
        view, _ = self.fixture()
        for choices, decision in ((['A:EX1-013#999', None], {'kind': 'SEARCH_SELECTION'}),
                ([None], {'kind': 'MAIN_ACTION', 'source': 'B:BT22-023#1'})):
            bot = self.bot(); before = bot.export_rng()
            with self.assertRaises(RuntimeHalt): bot.choose(view, choices, decision=decision)
            self.assertEqual(bot.export_rng(), before)
            self.assertEqual(bot.decision_log, [])

    def test_bottom_order_can_bind_public_view_after_retry(self):
        view, _ = self.fixture(); bot = self.bot(); before = bot.export_rng()
        self.assertEqual(bot.bottom_order([], public_view=view), [])
        record = bot.decision_log[-1]
        self.assertEqual(record['public_view_sha256'], digest(view))
        self.assertTrue(self.module.verify_decision_input(record, view, self.context, bot.manifest()))
        self.assertEqual(bot.export_rng(), before)

    def test_pure_manifest_helper_matches_constructed_policy(self):
        bot = self.bot(seed=31)
        helper = getattr(self.module, 'learning_player_manifest', None)
        self.assertTrue(callable(helper), 'pure manifest helper is missing')
        self.assertEqual(helper(self.context, 'A', self.State().state_id, 31), bot.manifest())

    def test_learning_state_roundtrip_preserves_trained_evidence(self):
        state = self.State()
        for index in range(3): self.train(state, index, chosen_kind='PASS_TURN')
        restored = self.State.from_dict(json.loads(json.dumps(state.export())))
        self.assertEqual(restored.export(), state.export())
        view, choices = self.fixture()
        self.assertEqual(self.bot(restored).choose(view, choices, decision={'kind': 'MAIN_ACTION'})['kind'], 'PASS_TURN')

    def test_opponent_bottom_order_requires_current_public_targets(self):
        view, _ = self.fixture(); bot = self.bot()
        self.assertEqual(bot.bottom_order(['B:EX1-013#1'], public_view=view), ['B:EX1-013#1'])
        before = bot.export_rng(); count = len(bot.decision_log)
        with self.assertRaises(RuntimeHalt): bot.bottom_order(['B:BT22-023#1'], public_view=view)
        self.assertEqual(bot.export_rng(), before)
        self.assertEqual(len(bot.decision_log), count)

    def test_invalid_public_conservation_and_duplicate_entities_fail(self):
        for mutation in ('count', 'duplicate', 'entity'):
            view, choices = self.fixture(); bot = self.bot(); before = bot.export_rng()
            if mutation == 'count': view['players']['A']['deck']['count'] += 1
            elif mutation == 'duplicate':
                view['players']['A']['trash'].append('A:EX13-017#1')
                view['players']['A']['deck']['count'] -= 1
            else:
                view['players']['B']['battle']['B:EX1-013#1']['instance_id'] = 'entity-1'
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt):
                bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
            self.assertEqual(bot.export_rng(), before)

    def test_trained_context_and_input_chain_cannot_be_relabelled(self):
        state = self.State()
        self.train(state, 0); self.train(state, 1)
        for mutation in ('context', 'input'):
            exported = state.export()
            if mutation == 'context': exported['context_id'] = 'f' * 64
            else: exported['games'][self.game_id(1)]['input_state_id'] = 'f' * 64
            exported['state_id'] = digest({k: v for k, v in exported.items() if k != 'state_id'})
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeHalt): self.State.from_dict(exported)

    def test_required_action_fields_and_types_are_checked_before_prior_or_rng(self):
        malformed = [
            {'kind': 'DECLARE_ATTACK'},
            {'kind': 'DECLARE_ATTACK', 'attacker': None, 'target': 'PLAYER'},
            {'kind': 'PLAY_CARD'}, {'kind': 'USE_OPTION', 'hand_key': None},
            {'kind': 'OPTION_DELAY'}, {'kind': 'BREEDING_CHOICE'},
            {'kind': 'BREEDING_CHOICE', 'action': 'invented'},
            {'kind': 'BATTLE_EVOLUTION', 'hand_key': 'A:BT11-032#1'},
            {'id': 'effect-1', 'effect_id': 'BT11-032.when_attacking'},
        ]
        view, _ = self.fixture()
        for candidate in malformed:
            bot = self.bot(); before = bot.export_rng()
            with self.subTest(candidate=candidate), self.assertRaises(RuntimeHalt):
                bot.choose(view, [candidate, None], decision={'kind': 'MAIN_ACTION'})
            self.assertEqual(bot.export_rng(), before)
            self.assertEqual(bot.decision_log, [])

    def test_coherently_rehashed_malformed_saved_action_fails_input_and_update(self):
        state = self.State(); view, choices = self.fixture(); bot = self.bot(state)
        bot.choose(view, choices, decision={'kind': 'MAIN_ACTION'})
        record = copy.deepcopy(bot.decision_log[-1])
        record['candidates'][0] = record['chosen'] = {'kind': 'DECLARE_ATTACK'}
        record['learning']['action_key'] = digest(record['chosen'])
        record.update(status='EXPERIMENTAL_RESOLVED', reward=5)
        with self.assertRaises(RuntimeHalt):
            self.module.verify_decision_input(record, view, self.context, bot.manifest())
        before = state.export()
        with self.assertRaises(RuntimeHalt): state.update_completed(self.game_id(0), 'A', [record])
        self.assertEqual(state.export(), before)


if __name__ == '__main__':
    unittest.main()
