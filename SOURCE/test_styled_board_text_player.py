"""New style policy must stay distinct from the published board-text policy."""
import unittest

from context_runtime import ContextRuntime
from interaction_learning import LearningState
from matchup_readiness import load_context_file
from test_selected_mechanics import ROOT, stage


class StyledBoardTextPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def test_aggressive_attacks_while_defensive_develops_single_exposed_field(self):
        from styled_board_text_player import StyledBoardTextPlayerBot
        for seat, expected in (('A', 'DECLARE_ATTACK'), ('B', 'PLAY_CARD')):
            with self.subTest(seat=seat):
                runtime = ContextRuntime(self.context, 1337, seat, allow_experimental=True)
                attacker = stage(runtime, seat, ['EX1-013'])
                other = 'B' if seat == 'A' else 'A'
                target = stage(runtime, other, ['BT11-023'])
                runtime.state.battle[seat][attacker].played_turn = 1
                runtime.state.battle[seat][attacker].ready_since_turn = 2
                runtime.state.phase, runtime.state.turn, runtime.state.memory = 'MAIN', 3, 3
                bot = StyledBoardTextPlayerBot(self.context, seat, LearningState(), 451, None)
                choices = [
                    {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': target},
                    {'kind': 'PLAY_CARD', 'hand_key': seat + ':BT11-023#1'},
                ]
                self.assertEqual(bot.choose(runtime.public_view(seat), choices,
                    decision={'kind': 'MAIN_ACTION'})['kind'], expected)
                self.assertEqual(bot.manifest()['style'],
                    'AGGRESSIVE_BOARD_TEXT' if seat == 'A' else 'DEFENSIVE_BOARD_TEXT')

    def test_supported_history_can_reverse_close_live_card_choice(self):
        from styled_board_text_player import StyledBoardTextPlayerBot
        from match_context import digest
        runtime = ContextRuntime(self.context, 1337, 'A', allow_experimental=True)
        view = runtime.public_view('A')
        bot = StyledBoardTextPlayerBot(self.context, 'A', LearningState(), 452, None)
        choices = [
            {'kind': 'PLAY_CARD', 'hand_key': 'A:BT11-023#1'},
            {'kind': 'PLAY_CARD', 'hand_key': 'A:P-138#1'},
        ]
        decision = {'kind': 'MAIN_ACTION'}
        self.assertEqual(bot.choose(view, choices, decision=decision), choices[0])
        state_key = bot._features._state_key(view, decision)
        better_key = digest(bot._features._action(view, choices[1]))
        bot._model._tables['A'][state_key] = {better_key: {
            'independent_games': 3, 'mean_reward': 2.0, 'reward_sum': 6.0,
            'wins': 1, 'losses': 2}}
        self.assertEqual(bot.choose(view, choices, decision=decision), choices[1])

    def test_runner_identifies_new_policy_without_relabeling_old_policy(self):
        from fresh_learning_campaign import run_game, replay_game
        old = run_game(0, ROOT, campaign_id='private-styled-old-v1',
            context_file='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',
            learning_state=LearningState(), max_commands=3,
            player_policy='BOARD_TEXT_HISTORY')
        new = run_game(0, ROOT, campaign_id='private-styled-new-v1',
            context_file='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',
            learning_state=LearningState(), max_commands=3,
            player_policy='BOARD_TEXT_HISTORY_STYLED')
        self.assertEqual(old['pilots']['A']['style'], 'BOARD_AND_CARD_TEXT')
        self.assertEqual(old['pilots']['B']['style'], 'BOARD_AND_CARD_TEXT')
        self.assertEqual(new['pilots']['A']['style'], 'AGGRESSIVE_BOARD_TEXT')
        self.assertEqual(new['pilots']['B']['style'], 'DEFENSIVE_BOARD_TEXT')
        self.assertTrue(replay_game(old, ROOT)['exact_match'])
        self.assertTrue(replay_game(new, ROOT)['exact_match'])


if __name__ == '__main__':
    unittest.main()
