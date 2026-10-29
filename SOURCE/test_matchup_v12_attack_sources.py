"""Source scoping and loaded-pair inherited attack tests."""
import unittest
from matchup_v12_attack_sources import MatchV12
from full_match_attempt import src

class AttackSourceTests(unittest.TestCase):
    def take(self,p,card):
        for zone in (p.z.hand,p.z.security,p.z.deck,p.z.trash):
            for c in list(zone):
                if c.card==card:
                    zone.remove(c)
                    return c
        raise AssertionError('MISSING '+card)

    def stack(self,p,*cards):
        copies=[self.take(p,c) for c in cards]
        p.z.battle.append(copies[-1]);p.stacks[copies[-1].key()]=copies
        return copies

    def test_top_elecm_only_does_not_expose_inherited(self):
        m=MatchV12(1);p=m.ps['A'];top=self.stack(p,'BT24-031')[-1]
        m._when_attacking(p,top)
        self.assertFalse(any(x.get('decision_type')=='ELECMON_INHERITED_ATTACK' for x in m.events))
        m.verify()

    def test_inherited_elecmon_zero_security_recovers_without_card_to_hand(self):
        m=MatchV12(1);p=m.ps['A'];stack=self.stack(p,'BT25-030','BT24-034');attacker=stack[-1]
        while p.z.security:p.z.hand.append(p.z.security.pop())
        deck_before=len(p.z.deck);hand_before=len(p.z.hand)
        m._when_attacking(p,attacker)
        self.assertEqual(len(p.z.security),1)
        self.assertEqual(len(p.z.deck),deck_before-1)
        self.assertEqual(len(p.z.hand),hand_before)
        self.assertTrue(any(e.get('kind')=='ELECMON_INHERITED_ATTACK_USED' for e in m.events))
        m.verify()

    def test_inherited_elecmon_one_security_adds_and_recovers(self):
        m=MatchV12(1);p=m.ps['A'];attacker=self.stack(p,'BT24-031','BT24-034')[-1]
        while len(p.z.security)>1:p.z.hand.append(p.z.security.pop())
        old=p.z.security[-1];prior_deck=len(p.z.deck)
        m._when_attacking(p,attacker)
        self.assertIn(old,p.z.hand)
        self.assertEqual(len(p.z.security),1)
        self.assertEqual(len(p.z.deck),prior_deck-1)
        m.verify()

    def test_inherited_manekimon_minus_2000(self):
        m=MatchV12(1);p=m.ps['B'];opp=m.ps['A'];top=self.stack(p,'BT26-012','EX12-065')[-1]
        opponent=self.stack(opp,'BT24-031')[-1]
        m._when_attacking(p,top)
        self.assertEqual(m._dp(opp,opponent),src('A',opponent.card)['dp']-2000) if opponent in opp.z.battle else self.assertIn(opponent,opp.z.trash)
        self.assertTrue(any(e.get('kind')=='MANEKIMON_INHERITED_ATTACK_DP' for e in m.events))
        m.verify()

    def test_susanoomon_sends_unprotected_digimon_to_security(self):
        m=MatchV12(1);p=m.ps['B'];opp=m.ps['A']
        attacker=self.stack(p,'EX12-076')[-1]
        target=self.stack(opp,'BT25-030')[-1]
        before=len(opp.z.security)
        m._when_attacking(p,attacker)
        self.assertNotIn(target,opp.z.battle)
        self.assertEqual(opp.z.security[-1],target)
        self.assertEqual(len(opp.z.security),before+1)
        self.assertTrue(any(e.get('kind')=='SUSANOOMON_ATTACK_DIGIMON_TO_SECURITY' for e in m.events))
        m.verify()

    def test_susanoomon_decode_halts_before_zone_changes(self):
        m=MatchV12(1);p=m.ps['B'];opp=m.ps['A']
        attacker=self.stack(p,'EX12-076')[-1]
        target=self.stack(opp,'BT24-034','P-213')[-1]
        oldsec=list(opp.z.security)
        with self.assertRaisesRegex(Exception,'DECODE_DECISION_UNVERIFIED'):
            m._when_attacking(p,attacker)
        self.assertIn(target,opp.z.battle)
        self.assertEqual(opp.z.security,oldsec)
        m.verify()

    def test_illegal_high_cost_dianamon_is_not_offered(self):
        m=MatchV12(1);p=m.ps['A'];m.mem=0
        for c in list(p.z.hand):
            p.z.deck.append(c);p.z.hand.remove(c)
        card=self.take(p,'BT25-028');p.z.hand.append(card)
        m.choose_turn_action(p,[])
        decision=[x for x in m.events if x.get('decision_type')=='MAIN_ACTION'][-1]
        self.assertFalse(any(x.get('label')==card.key() for x in decision['candidates']))
        m.verify()

    def test_buried_ryugumon_main_effect_not_inherited(self):
        m=MatchV12(1);p=m.ps['B'];top=self.stack(p,'EX12-036','EX12-076')[-1]
        # The buried EX12-036 When Attacking belongs to its main effect;
        # only Susanoomon's top-card ability can activate here.
        m._when_attacking(p,top)
        self.assertTrue(any(e.get('kind')=='SUSANOOMON_ATTACK_DIGIMON_TO_SECURITY' for e in m.events))
        self.assertFalse(any(e.get('card')=='EX12-036' and 'ATTACK' in (e.get('kind') or '') for e in m.events))
        m.verify()

if __name__=='__main__':unittest.main()
