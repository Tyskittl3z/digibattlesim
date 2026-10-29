"""Fail-closed behavior test for the fresh loaded-deck full-match attempt."""
import unittest
from full_match_attempt import FullMatch, run_batch

class FullAttemptTests(unittest.TestCase):
    def test_balanced_exact_matchup_and_no_invalid_winners(self):
        batch=run_batch(60)
        self.assertEqual(batch['first_counts'],{'A':30,'B':30})
        self.assertEqual(len({r['seed'] for r in batch['rows']}),60)
        self.assertEqual(batch['valid_complete_matches'],0)
        for row in batch['rows']:
            self.assertEqual(row['status'],'JUDGE_HALT')
            self.assertIsNone(row['winner'])
            self.assertTrue(row['halt_reason'])
            self.assertTrue(any(e['type']=='JUDGE_HALT' for e in row['events']))
    def test_deterministic_replay_of_each_seat(self):
        for i in (0,1,2,3,42,59):
            a=FullMatch(i).run();b=FullMatch(i).run()
            self.assertEqual(a,b)
    def test_conservation_in_all_halted_states(self):
        for i in range(60):
            match=FullMatch(i);match.run();match.verify()

if __name__=='__main__':unittest.main()
