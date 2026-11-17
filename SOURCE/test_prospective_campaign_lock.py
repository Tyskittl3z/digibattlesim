"""A fresh campaign binds sources before its first game."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

from match_context import digest
from test_selected_mechanics import ROOT


class ProspectiveCampaignLockTests(unittest.TestCase):
    def campaign(self):
        path=ROOT/'ARTIFACTS/ulforce-prospective-60-2026-11-17/campaign.py'
        spec=importlib.util.spec_from_file_location('ulforce_prospective_campaign',path)
        campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)
        return campaign

    def test_empty_campaign_lock_binds_current_rules_engine_criteria_and_policy(self):
        campaign=self.campaign()
        with tempfile.TemporaryDirectory() as temp:
            lock=campaign._lock(__import__('pathlib').Path(temp))
            saved=json.loads((__import__('pathlib').Path(temp)/'campaign-lock.json').read_text())
        rules=json.loads((ROOT/'RULES/matchups/123129-vs-122110/RULES_LOCK.json').read_text())
        self.assertEqual(lock['rules_lock_sha256'],digest(rules))
        self.assertEqual(lock['rules_lock_status'],'UNVERIFIED')
        self.assertEqual(lock['engine_sources']['main_actions.py'],
                         campaign._sources(ROOT)['main_actions.py'])
        self.assertEqual(lock['pilot_source_sha256'],lock['engine_sources']['board_text_player.py'])
        self.assertEqual(lock['criteria']['criterion_sha256'],campaign.criteria_manifest()['criterion_sha256'])
        self.assertEqual(saved['lock_sha256'],digest(lock))

    def test_unverified_rules_lock_prevents_first_cohort_game(self):
        campaign=self.campaign()
        with tempfile.TemporaryDirectory() as temp:
            from pathlib import Path
            out=Path(temp)
            with patch.object(campaign,'run_game',side_effect=AssertionError('game started')):
                with self.assertRaisesRegex(RuntimeError,'RULES_LOCK_UNVERIFIED'):
                    campaign.advance_once(out,0,budget=1)
            self.assertFalse((out/'game-0000').exists())

    def test_prior_receipt_must_bind_the_terminal_segment_before_handoff(self):
        campaign=self.campaign()
        source=ROOT/'ARTIFACTS/ulforce-smoke-v2-2026-11-17/game-0000'
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            from pathlib import Path
            out=Path(temp);prior=out/'game-0000';prior.mkdir()
            for name in ('segment-0000.json.gz','model-after.json','report.md','commit.json'):
                shutil.copy2(source/name,prior/name)
            lock=campaign._lock(out)
            model,_,_=campaign._handoff(out,1,lock)
            self.assertEqual(len(model.export()['games']),3)
            receipt=json.loads((prior/'commit.json').read_text())
            receipt['record_sha256']='0'*64
            (prior/'commit.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(RuntimeError,'PRIOR_RECORD_RECEIPT_MISMATCH'):
                campaign._handoff(out,1,lock)


if __name__=='__main__':unittest.main()
