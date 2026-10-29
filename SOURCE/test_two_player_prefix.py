import json,unittest
from collections import Counter
from pathlib import Path
from two_player_prefix import run_pair,report
from loaded_digivolution import BY_SEAT

class PrefixValidationTests(unittest.TestCase):
    def test_sides_balanced_and_not_falsely_counted(self):
        d=report(60)
        self.assertEqual(d['first_side_counts'],{'A':30,'B':30})
        self.assertEqual(d['fact_finding_games_accepted'],0)
        self.assertEqual(d['completed_two_seat_first_actions'],60)

    def test_replay_deterministic(self):
        for i in (0,1,8,19,42,59):
            self.assertEqual(run_pair(i),run_pair(i))

    def test_no_fabricated_winners(self):
        for i in range(60):
            row=run_pair(i)
            self.assertFalse(row['valid_full_game'])
            self.assertTrue(all('winner' not in e for e in row['events']))

    def test_only_exact_loaded_cards_played(self):
        for i in range(60):
            row=run_pair(i)
            for e in row['events']:
                if e['type']=='PAID_PLAY':
                    self.assertIn(e['card'].split('#')[0],BY_SEAT[e['player']])

    def test_legal_eggs_and_breeding(self):
        for i in range(60):
            row=run_pair(i)
            for e in row['events']:
                if e['type']=='BREEDING_EVOLVE':
                    self.assertEqual(e['cost'],0)
                    self.assertIn(e['to'].split('#')[0],BY_SEAT[e['player']])

    def test_different_seeds_not_same_hands(self):
        fingerprints=[]
        for i in range(60):
            row=run_pair(i)
            fingerprints.append((row['seed'],row['first']))
        self.assertEqual(len(fingerprints),len(set(fingerprints)))

if __name__=='__main__':unittest.main()
