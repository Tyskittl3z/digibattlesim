"""The new cohort starts fresh and commits only terminal exact-replayed games."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_selected_mechanics import ROOT


DRIVER = ROOT / 'ARTIFACTS/styled-prospective-60-2026-11-21/campaign.py'


class StyledSequentialCampaignTests(unittest.TestCase):
    def test_first_game_uses_new_profiles_and_pause_cannot_train_next_game(self):
        self.assertTrue(DRIVER.is_file(), 'styled campaign driver is missing')
        spec = importlib.util.spec_from_file_location('styled_campaign', DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as temporary:
            out = Path(temporary)
            result = module.advance_once(out, 0, budget=3)
            self.assertEqual(result['status'], 'PAUSED')
            self.assertEqual(result['commands'], 3)
            self.assertTrue(result['exact_replay'])
            self.assertEqual(result['model_games_before'], 0)
            self.assertEqual(result['player_policy'], 'BOARD_TEXT_HISTORY_STYLED')
            replay = json.loads((out / 'game-0000/replay-0000.json').read_text())
            self.assertEqual(replay['certification'], 'NONE_SOFTWARE_REPLAY_ONLY')
            self.assertFalse((out / 'game-0000/model-after.json').exists())
            self.assertFalse((out / 'game-0001').exists())
            status = json.loads((out / 'campaign-status.json').read_text())
            self.assertEqual(status['completed_software_games'], 0)
            self.assertEqual(status['accepted_fact_finding_credit'], 0)
            self.assertEqual(status['final_evaluation_credit'], 0)


if __name__ == '__main__':
    unittest.main()
