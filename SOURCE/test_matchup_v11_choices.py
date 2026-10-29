"""Loaded matchup v11: choice availability, execution, conservation, replay."""
import collections
import unittest
from matchup_v11_endturn_choices import MatchV11,run_cohort

class ActiveChoiceTests(unittest.TestCase):
    def take(self,p,card):
        for zone in (p.z.deck,p.z.hand,p.z.security,p.z.trash):
            for c in list(zone):
                if c.card==card:
                    zone.remove(c);return c
        raise AssertionError('Cannot find physical card '+card)

    def field(self,p,card):
        c=self.take(p,card);p.z.battle.append(c)
        if p.t(c).startswith('Digimon'):p.stacks[c.key()]=[c]
        return c

    def test_block_redirects_and_avoids_security_loss(self):
        m=MatchV11(1);a=m.ps['A'];b=m.ps['B']
        attacker=self.field(a,'BT24-031');blocker=self.field(b,'EX12-026')
        # An attack against an empty security stack would otherwise win.
        while b.z.security:b.z.hand.append(b.z.security.pop())
        m.turn=3;m.active='A'
        before=len(b.z.security)
        self.assertTrue(m.try_attack(a))
        self.assertIsNone(m.winner)
        self.assertEqual(len(b.z.security),before)
        self.assertTrue(any(e['type']=='BLOCK_DECLARED' and e['blocker']==blocker.key() for e in m.events))
        self.assertTrue(any(e['type']=='BOT_DECISION' and e['decision_type']=='BLOCK_TIMING' for e in m.events))
        m.verify()

    def test_suspended_blocker_cannot_block(self):
        m=MatchV11(1);a=m.ps['A'];b=m.ps['B']
        attacker=self.field(a,'BT24-031');blocker=self.field(b,'EX12-026')
        b.suspended.add(blocker.key())
        while b.z.security:b.z.hand.append(b.z.security.pop())
        m.turn=3;m.active='A'
        self.assertTrue(m.try_attack(a))
        self.assertEqual(m.winner,'A')
        self.assertFalse(any(e['type']=='BLOCK_DECLARED' for e in m.events))
        m.verify()

    def test_inori_security_removal_triggers_optional_free_evolution(self):
        m=MatchV11(2);a=m.ps['A']
        tam=self.field(a,'BT24-084');base=self.field(a,'BT24-034')
        target=self.take(a,'BT25-025');a.z.hand.append(target)
        from full_match_attempt import src
        for c in list(a.z.hand):
            if c!=target and 'Aegiochusmon' in src('A',c.card)['name']:
                a.z.hand.remove(c);a.z.deck.append(c)
        m.active='B';m.turn=4
        removed=a.z.security.pop();a.z.trash.append(removed)
        m._after_security_removed(a)
        self.assertIn(target,a.z.battle)
        self.assertNotIn(base,a.z.battle)
        self.assertIn(tam.key(),a.suspended)
        self.assertTrue(any(e['type']=='BOT_DECISION' and e['decision_type']=='INORI_SECURITY_EVOLVE' and e['chosen']==target.key() for e in m.events))
        m.verify()

    def test_inori_no_valid_evolution_declines(self):
        m=MatchV11(2);a=m.ps['A']
        tam=self.field(a,'BT24-084');base=self.field(a,'BT24-034')
        # Keep all eligible Aegiochusmon out of the hand.
        from full_match_attempt import src
        for c in list(a.z.hand):
            if 'Aegiochusmon' in src('A',c.card)['name']:
                a.z.hand.remove(c);a.z.deck.append(c)
        m.turn=3;m._after_security_removed(a)
        self.assertNotIn(tam.key(),a.suspended)
        self.assertIn(base,a.z.battle)
        self.assertTrue(any(e['type']=='BOT_DECISION' and e['decision_type']=='INORI_SECURITY_EVOLVE' and e['chosen']=='DECLINE' for e in m.events))
        m.verify()

    def test_dan_and_kanan_uses_option_and_suspends(self):
        m=MatchV11(2);p=m.ps['A'];m.turn=3;m.mem=-3
        tamer=self.field(p,'BT24-085')
        opt=self.take(p,'BT24-100');p.z.hand.append(opt)
        m.end_turn_check(p)
        self.assertIn(opt,p.z.battle)
        self.assertIn(tamer.key(),p.suspended)
        self.assertTrue(any(e['type']=='END_TURN_OPTION_USED' and e['option']==opt.key() for e in m.events))
        m.verify()

    def test_dan_kanan_followup_attack_can_win_legally(self):
        m=MatchV11(2);p=m.ps['A'];enemy=m.ps['B']
        m.turn=3;m.mem=-3;m.active='A'
        tamer=self.field(p,'BT24-085')
        attacker=self.field(p,'BT24-031')
        opt=self.take(p,'BT24-100');p.z.hand.append(opt)
        while enemy.z.security:enemy.z.hand.append(enemy.z.security.pop())
        m.end_turn_check(p)
        self.assertEqual(m.winner,'A')
        self.assertEqual(m.events[-1]['type'],'GAME_END')
        self.assertTrue(any(e['type']=='BOT_DECISION' and e['decision_type']=='DAN_KANAN_FOLLOWUP_ATTACK'
                            and e['chosen']==attacker.key() for e in m.events))
        m.verify()

    def test_homeros_can_reactivate_jupiter(self):
        m=MatchV11(2);p=m.ps['A'];m.turn=3;m.mem=-3
        tamer=self.field(p,'BT24-102')
        jup=self.field(p,'BT24-101')
        before=len(p.z.security)
        m.end_turn_check(p)
        self.assertIn(tamer.key(),p.suspended)
        self.assertEqual(len(p.z.security),before-1)
        self.assertTrue(any(e['type']=='JUDGE_PATH' and e['kind']=='HOMEROS_OLYMPOS_EFFECT_USED' for e in m.events))
        m.verify()

    def test_kunlun_uses_shambala_search_if_tentei(self):
        m=MatchV11(2);p=m.ps['B'];m.turn=3;m.mem=-3
        tamer=self.field(p,'BT26-104');tentei=self.field(p,'EX12-036')
        opt=self.take(p,'EX12-075');p.z.hand.append(opt)
        m.end_turn_check(p)
        self.assertIn(tamer.key(),p.suspended)
        self.assertIn(opt,p.z.battle)
        self.assertTrue(any(e['type']=='END_TURN_OPTION_USED' and e['option']==opt.key() for e in m.events))
        m.verify()

    def test_sixty_experimental_games_balanced_complete_and_replayed(self):
        report=run_cohort(60)
        self.assertEqual(report['software_completed'],60)
        self.assertEqual(report['judge_certified'],0)
        self.assertEqual(report['halts'],{})
        self.assertEqual(report['starts'],{'A':30,'B':30})
        self.assertEqual(report['decisions']['END_OF_TURN'],247)
        for i,r in enumerate(report['rows']):
            self.assertEqual(r,MatchV11(i).run())
            terminal=[e for e in r['events'] if e['type'] in ('GAME_END','WIN_DRAW_PHASE_DECKOUT')]
            self.assertEqual(len(terminal),1)
            self.assertIn(r['events'][-1]['type'],('GAME_END','WIN_DRAW_PHASE_DECKOUT'))

if __name__=='__main__':unittest.main()
