"""A fresh campaign binds sources before its first game."""
import importlib.util
import json
import tempfile
import unittest

from match_context import digest
from test_selected_mechanics import ROOT


class ProspectiveCampaignLockTests(unittest.TestCase):
    def test_empty_campaign_lock_binds_current_rules_engine_criteria_and_policy(self):
        path=ROOT/'ARTIFACTS/ulforce-prospective-60-2026-11-17/campaign.py'
        spec=importlib.util.spec_from_file_location('ulforce_prospective_campaign',path)
        campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)
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


if __name__=='__main__':unittest.main()
