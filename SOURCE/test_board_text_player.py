"""Fresh decisions use current public state, own hand text, and prior evidence."""
import json
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime
from interaction_learning import LearningState, verify_decision_input
from matchup_readiness import load_context_file
from test_selected_mechanics import ROOT, stage


class BoardTextPlayerTests(unittest.TestCase):
    def test_printed_security_effect_is_an_offered_pending_choice(self):
        from interaction_learning import _decision
        pending = {'id': 'effect-1', 'seat': 'A', 'source': 'A:LM-056#1',
                   'effect_id': 'LM-056.main_search', 'field': 'security_text',
                   'instance': 'entity-1', 'depth': 0}
        self.assertEqual(_decision({'kind': 'PENDING_EFFECT_ORDER',
                                    'selected_pending': pending})['selected_pending'], pending)

    def test_no_history_starts_at_game_one_and_never_constructs_named_prior(self):
        from fresh_learning_campaign import run_game, replay_game
        with patch('interaction_learning.NamedPlayerBot', side_effect=AssertionError('named prior used')):
            record = run_game(0, ROOT,
                context_file='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',
                campaign_id='private-no-history-policy-test', learning_state=LearningState(),
                max_commands=3, player_policy='BOARD_TEXT_HISTORY')
        self.assertEqual(record['index'], 0)
        self.assertIsNone(record['history_report'])
        self.assertIsNone(record['pilots']['A']['history_report_sha256'])
        self.assertTrue(replay_game(record, ROOT)['exact_match'])

    def test_fresh_runner_binds_report_and_uses_board_text_bots_for_both_seats(self):
        from fresh_learning_campaign import run_game, replay_game
        model = LearningState.from_dict(json.loads((ROOT /
            'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-learning-model-after.json').read_text()))
        record = run_game(1, ROOT,
            context_file='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',
            campaign_id='private-board-text-policy-test', learning_state=model,
            max_commands=3, player_policy='BOARD_TEXT_HISTORY',
            history_report='ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-report.md')
        self.assertEqual(record['status'], 'PAUSED')
        self.assertEqual(record['player_policy'], 'BOARD_TEXT_HISTORY')
        self.assertEqual(record['pilots']['A']['style'], 'BOARD_AND_CARD_TEXT')
        self.assertEqual(record['pilots']['B']['style'], 'BOARD_AND_CARD_TEXT')
        self.assertEqual(record['pilots']['A']['history_report_sha256'],
                         record['pilots']['B']['history_report_sha256'])
        self.assertEqual([c['command'] for c in record['commands']],
                         ['BEGIN_PREPARATION', 'REDRAW_CHOICE', 'REDRAW_CHOICE'])
        self.assertTrue(all(d['learning']['mode'] == 'PUBLIC_STATE_TEXT'
                            for c in record['commands'] for d in c['decisions']))
        self.assertTrue(replay_game(record, ROOT)['exact_match'])

    def test_both_seats_use_same_live_rule_without_random_exploration(self):
        from board_text_player import BoardTextPlayerBot
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        for seat in ('A', 'B'):
            with self.subTest(seat=seat):
                runtime = ContextRuntime(context, 1337, seat, allow_experimental=True)
                attacker = stage(runtime, seat, ['EX1-013'])
                runtime.state.battle[seat][attacker].played_turn = 1
                runtime.state.battle[seat][attacker].ready_since_turn = 2
                runtime.state.phase = 'MAIN'
                runtime.state.turn = 3
                runtime.state.memory = 3
                bot = BoardTextPlayerBot(context, seat, LearningState(), 451, 'a' * 64)
                before_rng = bot.export_rng()
                selected = bot.choose(runtime.public_view(seat), [
                    {'kind': 'PASS_TURN'},
                    {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': 'PLAYER'}],
                    decision={'kind': 'MAIN_ACTION'})
                self.assertEqual(selected['kind'], 'DECLARE_ATTACK')
                self.assertEqual(bot.export_rng(), before_rng)
                self.assertEqual(bot.decision_log[-1]['learning']['mode'], 'PUBLIC_STATE_TEXT')
                self.assertEqual(bot.decision_log[-1]['learning']['epsilon'], 0.0)
                self.assertEqual(bot.manifest()['style'], 'BOARD_AND_CARD_TEXT')
                self.assertTrue(verify_decision_input(
                    bot.decision_log[-1], runtime.public_view(seat), context, bot.manifest()))


if __name__ == '__main__':
    unittest.main()
