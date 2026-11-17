"""The selected English worldwide source snapshot fails closed."""
import json
import copy
import unittest

from test_selected_mechanics import ROOT


class MatchupRulesLockTests(unittest.TestCase):
    def test_matchup_lock_lists_all_loaded_cards_and_honestly_reports_missing_dates(self):
        path=ROOT/'RULES/matchups/123129-vs-122110/RULES_LOCK.json'
        self.assertTrue(path.is_file())
        lock=json.loads(path.read_text())
        from matchup_rules_lock import inspect_lock
        report=inspect_lock(lock,ROOT)
        self.assertEqual(report['matched_card_pages'],22)
        self.assertEqual(report['bad_hashes'],[])
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertIn('EFFECTIVE_DATE_MISSING',report['blockers'])

    def test_changed_source_hash_and_future_effective_date_block_verification(self):
        path=ROOT/'RULES/matchups/123129-vs-122110/RULES_LOCK.json'
        original=json.loads(path.read_text())
        lock=copy.deepcopy(original)
        lock['documents'][0]['sha256']='0'*64
        lock['documents'][-1]['effective_date']='2027-01-01'
        from matchup_rules_lock import inspect_lock
        report=inspect_lock(lock,ROOT)
        self.assertEqual(report['bad_hashes'],[lock['documents'][0]['id']])
        self.assertIn('SOURCE_HASH_MISMATCH',report['blockers'])
        self.assertIn('EFFECTIVE_AFTER_AS_OF',report['blockers'])


if __name__=='__main__':unittest.main()
