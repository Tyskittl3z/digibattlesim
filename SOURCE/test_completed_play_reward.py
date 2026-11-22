"""A completed attack's observed exchange, not its opening suspension, trains it."""
import copy
import unittest


class CompletedPlayRewardTests(unittest.TestCase):
    def test_successful_check_replaces_red_declaration_reward_for_learning_only(self):
        from completed_play_reward import attack_learning_rewards, learning_decisions
        commands = [
            {'command': 'DECLARE_ATTACK', 'seat': 'A', 'rating': {'reward': -0.5,
                'label': 'RED'}, 'decisions': [{'reward': -0.5, 'chosen': {'kind': 'DECLARE_ATTACK'}}]},
            {'command': 'COUNTER_CHOICE', 'seat': 'B', 'rating': {'reward': 1.0}, 'decisions': []},
            {'command': 'CONFIRM_ATTACK', 'seat': 'A', 'rating': {'reward': 4.0}, 'decisions': []},
            {'command': 'END_ATTACK', 'seat': 'A', 'rating': {'reward': 0.0}, 'decisions': []},
        ]
        original = copy.deepcopy(commands)
        self.assertEqual(attack_learning_rewards(commands), {0: 2.5})
        self.assertEqual(learning_decisions(commands, 'BOARD_TEXT_HISTORY_STYLED')[0]['reward'], 2.5)
        self.assertEqual(learning_decisions(commands, 'BOARD_TEXT_HISTORY')[0]['reward'], -0.5)
        self.assertEqual(commands, original)

    def test_terminal_direct_attack_includes_last_command_without_end_attack(self):
        from completed_play_reward import attack_learning_rewards
        commands = [
            {'command': 'DECLARE_ATTACK', 'seat': 'B', 'rating': {'reward': -1.0}, 'decisions': []},
            {'command': 'RESOLVE_PENDING', 'seat': 'B', 'rating': {'reward': 1.5}, 'decisions': []},
            {'command': 'CONFIRM_ATTACK', 'seat': 'B', 'rating': {'reward': 2.0}, 'decisions': []},
        ]
        self.assertEqual(attack_learning_rewards(commands), {0: 2.5})

    def test_separate_attack_windows_do_not_share_reward(self):
        from completed_play_reward import attack_learning_rewards
        commands = [
            {'command': 'DECLARE_ATTACK', 'seat': 'A', 'rating': {'reward': -0.5}, 'decisions': []},
            {'command': 'END_ATTACK', 'seat': 'A', 'rating': {'reward': 1.0}, 'decisions': []},
            {'command': 'DECLARE_ATTACK', 'seat': 'A', 'rating': {'reward': -0.5}, 'decisions': []},
            {'command': 'CONFIRM_ATTACK', 'seat': 'A', 'rating': {'reward': 4.0}, 'decisions': []},
        ]
        self.assertEqual(attack_learning_rewards(commands), {0: 0.5, 2: 3.5})


if __name__ == '__main__':
    unittest.main()
