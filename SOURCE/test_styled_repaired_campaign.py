"""The repaired cohort starts at zero with a distinct fixed source lock."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_selected_mechanics import ROOT


class RepairedStyledCampaignTests(unittest.TestCase):
    def test_new_campaign_uses_new_seed_and_repaired_engine_without_old_handoff(self):
        driver = ROOT / 'ARTIFACTS/styled-prospective-60-2026-11-22-v2/campaign.py'
        spec = importlib.util.spec_from_file_location('repaired_styled_campaign', driver)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as temporary:
            out = Path(temporary)
            result = module.advance_once(out, 0, budget=3)
            lock = json.loads((out / 'campaign-lock.json').read_text())
            self.assertEqual(result['status'], 'PAUSED')
            self.assertTrue(result['exact_replay'])
            self.assertEqual(result['model_games_before'], 0)
            self.assertEqual(lock['campaign_id'], 'ULFORCE_STYLED_FRESH_60_2026_11_22_V2')
            self.assertEqual(lock['engine_sources']['selected_mechanics.py'],
                             hashlib.sha256((ROOT / 'SOURCE/selected_mechanics.py').read_bytes()).hexdigest())
            self.assertNotEqual(lock['schedule']['games'][0]['seed'], 13222111115381104236)
            self.assertFalse((out / 'game-0000/model-after.json').exists())
            self.assertEqual(json.loads((out / 'campaign-status.json').read_text())['completed_software_games'], 0)
