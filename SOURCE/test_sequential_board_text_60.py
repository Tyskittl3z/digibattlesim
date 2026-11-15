"""A paused new campaign game cannot train or start the next game."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_selected_mechanics import ROOT


DRIVER = ROOT / 'ARTIFACTS/board-text-60-2026-11-11/campaign.py'


class SequentialBoardText60Tests(unittest.TestCase):
    def test_first_game_loads_latest_history_and_pause_does_not_advance(self):
        self.assertTrue(DRIVER.is_file(), 'sequential campaign driver is missing')
        spec = importlib.util.spec_from_file_location('board_text_60_campaign', DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as temporary:
            out = Path(temporary)
            result = module.advance_once(out, 0, budget=3)
            self.assertEqual(result['status'], 'PAUSED')
            self.assertEqual(result['game_index'], 0)
            self.assertEqual(result['commands'], 3)
            self.assertTrue(result['exact_replay'])
            self.assertEqual(result['model_games_before'], 2)
            game = out / 'game-0000'
            self.assertTrue((game / 'segment-0000.json.gz').is_file())
            self.assertFalse((game / 'model-after.json').exists())
            self.assertFalse((out / 'game-0001').exists())
            status = json.loads((out / 'campaign-status.json').read_text())
            self.assertEqual(status['completed_software_games'], 0)
            self.assertEqual(status['accepted_fact_finding_credit'], 0)


if __name__ == '__main__':
    unittest.main()
