"""Loaded Jupitermon versus Toho 60 full software matches: invariants only."""
import unittest,collections,hashlib,json
from matchup_v8 import MatchV8
from loaded_digivolution import BY_SEAT

class MatchV8Acceptance(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.games=[]
  for i in range(60):
   m=MatchV8(i);r=m.run();m.verify();cls.games.append((m,r))
 def test_sixty_real_match_endings_fifty_fifty_first_player_schedule(self):
  self.assertEqual(collections.Counter(r['first'] for _,r in self.games),{'A':30,'B':30})
  self.assertEqual(len({r['seed'] for _,r in self.games}),60)
  self.assertTrue(all(r['status']=='VALID_COMPLETE_GAME' for _,r in self.games))
 def test_every_game_one_and_only_one_terminal_event_last(self):
  for _,r in self.games:
   ending=[j for j,x in enumerate(r['events']) if x['type'] in ('GAME_END','WIN_DRAW_PHASE_DECKOUT')]
   self.assertEqual(ending,[len(r['events'])-1],r['index'])
   self.assertIsNotNone(r['winner'])
 def test_replay_all_60(self):
  for _,r in self.games:
   replay=MatchV8(r['index']).run()
   self.assertEqual(hashlib.sha256(json.dumps(r,sort_keys=True).encode()).digest(),
      hashlib.sha256(json.dumps(replay,sort_keys=True).encode()).digest())
 def test_card_conservation(self):
  for m,_ in self.games:
   for p in m.ps.values():p.ensure()
 def test_source_bound_all_effect_events(self):
  for _,r in self.games:
   for e in r['judge_paths']:
    self.assertEqual(e['card_text_sha256'],BY_SEAT[e['seat']][e['card']]['card_text_sha256'])
 def test_memory_never_overflows_10(self):
  for m,r in self.games:
   self.assertLessEqual(abs(m.mem),10)
   for e in r['events']:
    for k in ('memory','memory_after'):
     if isinstance(e.get(k),int):self.assertLessEqual(abs(e[k]),10,(r['index'],e))
 def test_ryugumon_and_gasamon_explicitly_encountered(self):
  kinds=collections.Counter(e['kind'] for _,r in self.games for e in r['judge_paths'])
  self.assertGreater(kinds['RYUGUMON_MANDATORY_SUPPRESSION'],0)
  self.assertGreater(kinds['GASAMON_TB_DIGIVOLVE_COST_MINUS_ONE'],0)
  self.assertGreater(kinds['KAGUYAMON_FORTITUDE_REPLAY'],0)
 def test_only_current_41_loaded_cards(self):
  self.assertEqual(len(set(BY_SEAT['A'])|set(BY_SEAT['B'])),41)
  for _,r in self.games:
   for e in r['judge_paths']:self.assertIn(e['card'],BY_SEAT[e['seat']])
if __name__=='__main__':unittest.main()
