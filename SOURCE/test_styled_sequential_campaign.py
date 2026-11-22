"""The new cohort starts fresh and commits only terminal exact-replayed games."""
import importlib.util
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from test_selected_mechanics import ROOT


DRIVER = ROOT / 'ARTIFACTS/styled-prospective-60-2026-11-21/campaign.py'


class StyledSequentialCampaignTests(unittest.TestCase):
    def test_missing_replay_receipt_is_rebuilt_from_saved_segment(self):
        spec = importlib.util.spec_from_file_location('styled_campaign', DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as temporary:
            out = Path(temporary)
            first = module.advance_once(out, 0, budget=3)
            self.assertEqual(first['status'], 'PAUSED')
            receipt = out / 'game-0000/replay-0000.json'
            expected = receipt.read_bytes()
            receipt.unlink()
            resumed = module.advance_once(out, 0, budget=1)
            self.assertTrue(resumed['exact_replay'])
            self.assertEqual(receipt.read_bytes(), expected)
            self.assertEqual(resumed['commands'], 4)

    def test_terminal_checkpoint_finalizes_after_interrupted_commit(self):
        spec = importlib.util.spec_from_file_location('styled_campaign', DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            record = {'status': 'EXPERIMENTAL_SOFTWARE_TERMINAL'}
            model = module.LearningState()
            receipt = {'updated': True, 'learning_state_id': model.state_id}
            with patch.object(module, 'commit_completed_game', return_value=receipt), \
                    patch.object(module, '_report', return_value='report'), \
                    patch.object(module, '_actions_csv', return_value=b'actions'):
                module._finalize_terminal(folder, record, model)
            for name in ('report.md', 'actions.csv', 'commit.json', 'model-after.json'):
                self.assertTrue((folder / name).is_file(), name)
            with patch.object(module, 'commit_completed_game', return_value=receipt), \
                    patch.object(module, '_report', return_value='report'), \
                    patch.object(module, '_actions_csv', return_value=b'actions'):
                module._finalize_terminal(folder, record, module.LearningState())

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
            lock = json.loads((out / 'campaign-lock.json').read_text())
            self.assertEqual(lock['roadmap_criteria_file_sha256'], hashlib.sha256(
                (ROOT / 'ARTIFACTS/styled-prospective-60-2026-11-21/ROADMAP_CRITERIA.json').read_bytes()).hexdigest())
            self.assertEqual(status['completed_software_games'], 0)
            self.assertEqual(status['accepted_fact_finding_credit'], 0)
            self.assertEqual(status['final_evaluation_credit'], 0)


if __name__ == '__main__':
    unittest.main()
