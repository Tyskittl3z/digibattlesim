"""Bounded tests for the loaded matchup's decision scorer, not deck strength."""
import unittest
from collections import Counter
from matchup_v9_decision_policy import MatchV9, run_cohort
from full_match_attempt import src

class DecisionV9Tests(unittest.TestCase):
    def test_main_action_lists_alternatives_and_is_deterministic(self):
        a=MatchV9(4)
        p=a.ps[a.active]
        result=a.choose_turn_action(p,a.evolution_candidates(p))
        e=a.events[-1]
        self.assertEqual(e['type'],'BOT_DECISION')
        self.assertEqual(e['decision_type'],'MAIN_ACTION')
        self.assertEqual(e['scorer_id'],a.SCORER_ID)
        self.assertIn(result[0],('PLAY','EVOLVE','PASS','ATTACK'))
        b=MatchV9(4);q=b.ps[b.active]
        self.assertEqual(a.events[-1],b.events[-1] if b.choose_turn_action(q,b.evolution_candidates(q)) else None)

    def test_rush_and_attack_eligibility_agree(self):
        m=MatchV9(2);p=m.ps['A']
        # Find a real Digimon in the loaded deck, create a newly-played stack.
        candidate=next(c for c in p.z.hand+p.z.deck if src('A',c.card)['type']=='Digimon')
        (p.z.hand if candidate in p.z.hand else p.z.deck).remove(candidate)
        p.z.battle.append(candidate);p.stacks[candidate.key()]=[candidate]
        p.sick.add(candidate.key())
        self.assertNotIn(candidate,m._ready(p))
        p.z.statuses.setdefault(candidate.key(),{})['rush']=True
        self.assertIn(candidate,m._ready(p))
        m.verify()

    def _battle_elecm(self,m):
        p=m.ps['A']
        c=next(c for c in p.z.deck+p.z.hand+p.z.security if c.card=='BT25-030')
        (p.z.deck if c in p.z.deck else p.z.hand if c in p.z.hand else p.z.security).remove(c)
        p.z.battle.append(c);p.stacks[c.key()]=[c]
        m.verify()
        return p,c

    def test_elecm_pays_and_moves_one_real_security(self):
        m=MatchV9(1);p,c=self._battle_elecm(m)
        m.turn=3;m.mem=1
        hand_before=len(p.z.hand); security_before=len(p.z.security)
        m._start_main_effects(p)
        self.assertEqual(len(p.z.security),security_before-1)
        self.assertEqual(len(p.z.hand),hand_before+1)
        self.assertEqual(m.mem,2)
        self.assertTrue(any(x['type']=='BOT_DECISION' and x['chosen']=='PAY'
            and x.get('source')==c.key() for x in m.events))
        m.verify()

    def test_elecm_can_decline_to_preserve_last_security(self):
        m=MatchV9(1);p,c=self._battle_elecm(m)
        while len(p.z.security)>1:p.z.hand.append(p.z.security.pop())
        m.turn=3;m.mem=1
        before=len(p.z.security)
        m._start_main_effects(p)
        self.assertEqual(len(p.z.security),before)
        self.assertEqual(m.mem,1)
        self.assertTrue(any(x['type']=='BOT_DECISION' and x['chosen']=='DECLINE'
            and x.get('source')==c.key() for x in m.events))
        m.verify()

    def test_enemy_target_selection_uses_public_board_not_secret_hand(self):
        m=MatchV9(5);p=m.ps['B'];enemy=m.ps['A']
        copies=[c for c in enemy.z.deck+enemy.z.hand if src('A',c.card)['type']=='Digimon']
        copies=sorted(copies,key=lambda c:(src('A',c.card)['level'],c.key()))
        chosen1=m.choose_enemy_target(enemy,[copies[0],copies[-1]],'EX12-046')
        assert len(enemy.z.hand)>=2
        enemy.z.hand[0],enemy.z.hand[-1]=enemy.z.hand[-1],enemy.z.hand[0]
        chosen2=m.choose_enemy_target(enemy,[copies[0],copies[-1]],'EX12-046')
        self.assertEqual(chosen1,chosen2)
        self.assertTrue(any(x['decision_type']=='OPPONENT_TARGET' for x in m.events if x['type']=='BOT_DECISION'))

    def test_aegiomon_optional_security_tamer_play(self):
        m=MatchV9(3);p=m.ps['A'];m.turn=3
        def take_card(card):
            for z in (p.z.hand,p.z.deck,p.z.security):
                for c in list(z):
                    if c.card==card:
                        z.remove(c);return c
            raise AssertionError('loaded card missing '+card)
        source=take_card('BT24-034');tamer=take_card('BT24-102')
        p.z.battle.append(source);p.stacks[source.key()]=[source]
        p.z.hand.append(tamer);m.verify()
        hand_count=len(p.z.hand);security_count=len(p.z.security)
        m.resolve_aegiomon_ability(p,source,'When Digivolving')
        self.assertIn(tamer,p.z.battle)
        self.assertNotIn(tamer,p.z.hand)
        self.assertEqual(len(p.z.security),security_count-1)
        self.assertEqual(len(p.z.hand),hand_count)
        self.assertTrue(any(e['type']=='BOT_DECISION' and e['decision_type']=='AEGIOMON_SECURITY_TAMER'
            and e['chosen']==tamer.key() for e in m.events))
        m.verify()

    def test_aegiomon_declines_at_one_security(self):
        m=MatchV9(3);p=m.ps['A'];m.turn=3
        source=next(c for c in p.z.deck if c.card=='BT24-034')
        p.z.deck.remove(source);p.z.battle.append(source);p.stacks[source.key()]=[source]
        while len(p.z.security)>1:p.z.hand.append(p.z.security.pop())
        before=len(p.z.security)
        m.resolve_aegiomon_ability(p,source,'When Digivolving')
        self.assertEqual(len(p.z.security),before)
        self.assertTrue(any(e['type']=='BOT_DECISION' and e['decision_type']=='AEGIOMON_SECURITY_TAMER'
            and e['chosen']=='DECLINE' for e in m.events))
        m.verify()

    def test_sixty_full_software_games_have_no_halts(self):
        r=run_cohort(60)
        self.assertEqual(r['software_completed'],60)
        self.assertEqual(r['firsts'],{'A':30,'B':30})
        self.assertEqual(r['halts'],{})
        self.assertEqual(r['judge_certified'],0)
        self.assertGreater(r['decisions']['MAIN_ACTION'],100)
        self.assertGreater(r['decisions']['OPPONENT_TARGET'],0)
        self.assertGreater(r['decisions']['ELECMON_START_MAIN'],0)
        for x in r['rows']:
            self.assertEqual(sum(e['type']=='GAME_END' for e in x['events']),1)
            self.assertEqual(x['events'][-1]['type'],'GAME_END')
            self.assertFalse(any(e['type']=='JUDGE_HALT' for e in x['events']))

    def test_full_match_replay_same_turn_actions(self):
        for i in (0,1,10,11):
            self.assertEqual(MatchV9(i).run(),MatchV9(i).run())

if __name__=='__main__':unittest.main()
