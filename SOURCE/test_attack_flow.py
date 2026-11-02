import unittest

from context_runtime import ContextRuntime,RuntimeHalt
from selected_mechanics import build_selected_registry
from test_selected_mechanics import selected_context,stage,ROOT
from attack_flow import declare_attack,choose_counter,choose_blocker,confirm_attack,end_attack,battle_losers,counter_options


class AttackTests(unittest.TestCase):
    def runtime(self,seat='A'):
        c=selected_context();r=ContextRuntime(c,441,seat,build_selected_registry(c,ROOT),allow_experimental=True)
        r.state.phase='MAIN';r.state.turn=3
        return r

    def plain(self,r,seat,number,*,suspended=False,played=1):
        key=stage(r,seat,[number],suspended=suspended)
        r.state.battle[seat][key].played_turn=played
        return key

    def sec(self,r,seat,number):
        deck=r.state.zones[seat]['deck'];card=next(c for c in deck if c.card_number==number)
        deck.remove(card);r.state.zones[seat]['security'].append(card);return card.key

    def windows(self,r,seat,attacker,target='PLAYER'):
        other='B' if seat=='A' else 'A'
        declare_attack(r,seat,attacker,target,ROOT)
        choose_counter(r,other,None,ROOT);choose_blocker(r,other,None,ROOT)

    def test_declaration_suspends_and_requires_both_defender_windows(self):
        r=self.runtime();a=self.plain(r,'A','EX1-013')
        declare_attack(r,'A',a,'PLAYER',ROOT)
        self.assertTrue(r.state.battle['A'][a].suspended)
        self.assertEqual(r.state.attack['window'],'COUNTER')
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'ATTACK_WINDOW'):
            confirm_attack(r,'A',ROOT)
        self.assertEqual(before,r.snapshot()['state'])

    def test_direct_attack_zero_security_ends_immediately_without_end_attack(self):
        r=self.runtime();a=self.plain(r,'A','EX1-013');self.windows(r,'A',a)
        result=confirm_attack(r,'A',ROOT)
        self.assertEqual(result['winner'],'A');self.assertTrue(r.state.terminal)
        self.assertEqual(r.state.winner,'A');self.assertIsNone(r.state.attack)
        self.assertEqual(r.matches_played,0)
        count=len(r.events)
        with self.assertRaisesRegex(RuntimeHalt,'ACTION_AFTER_TERMINAL'):end_attack(r,'A',ROOT)
        self.assertEqual(len(r.events),count+1)

    def test_last_security_check_is_not_a_win_and_security_battle_deletes_attacker(self):
        r=self.runtime();a=self.plain(r,'A','EX1-013');checked=self.sec(r,'B','ST7-05')
        self.windows(r,'A',a);result=confirm_attack(r,'A',ROOT)
        self.assertFalse(r.state.terminal);self.assertEqual(r.state.attack['window'],'END')
        self.assertNotIn(a,r.state.battle['A'])
        self.assertIn(checked,[c.key for c in r.state.zones['B']['trash']])
        self.assertEqual(r.state.zones['B']['security'],[])
        self.assertTrue(result['attacker_deleted']);end_attack(r,'A',ROOT);r.verify()

    def test_security_digimon_goes_to_trash_without_deletion_when_it_loses(self):
        r=self.runtime('B');a=self.plain(r,'B','ST7-05');checked=self.sec(r,'A','EX1-013')
        self.windows(r,'B',a);confirm_attack(r,'B',ROOT)
        self.assertIn(a,r.state.battle['B']);self.assertFalse(r.state.terminal)
        self.assertIn(checked,[c.key for c in r.state.zones['A']['trash']])
        self.assertTrue(r.state.battle['B'][a].suspended)

    def test_suspended_target_battle_uses_printed_dp_and_does_not_touch_security(self):
        r=self.runtime('B');a=self.plain(r,'B','BT9-011');d=self.plain(r,'A','EX1-013',suspended=True)
        self.windows(r,'B',a,d);confirm_attack(r,'B',ROOT)
        self.assertNotIn(d,r.state.battle['A']);self.assertIn(a,r.state.battle['B'])
        self.assertIn(d,[c.key for c in r.state.zones['A']['trash']]);r.verify()

    def test_tied_battle_rules_distinguish_security_from_field_deletion(self):
        for dp_a,dp_b,security,want in [(2,5,False,['ATTACKER']),(6,2,False,['DEFENDER']),
                (5,5,False,['ATTACKER','DEFENDER']),(5,5,True,['ATTACKER']),
                (6,2,True,[])]:
            self.assertEqual(battle_losers(dp_a,dp_b,security=security),want)

    def test_equal_dp_loaded_search_tops_are_deleted_simultaneously(self):
        r=self.runtime();a=self.plain(r,'A','BT11-023');d=self.plain(r,'B','EX2-008',suspended=True)
        self.windows(r,'A',a,d);result=confirm_attack(r,'A',ROOT)
        self.assertEqual(result['battle_losers'],['ATTACKER','DEFENDER'])
        self.assertNotIn(a,r.state.battle['A']);self.assertNotIn(d,r.state.battle['B'])
        self.assertIn(a,[c.key for c in r.state.zones['A']['trash']])
        self.assertIn(d,[c.key for c in r.state.zones['B']['trash']]);r.verify()

    def test_played_this_turn_unknown_history_wrong_actor_and_unsuspended_target_fail(self):
        for case in ('new','unknown','actor','target'):
            r=self.runtime();a=self.plain(r,'A','EX1-013',played=3 if case=='new' else None if case=='unknown' else 1)
            d=self.plain(r,'B','ST7-05') if case=='target' else 'PLAYER'
            before=r.snapshot()['state']
            with self.assertRaises(RuntimeHalt):declare_attack(r,'B' if case=='actor' else 'A',a,d,ROOT)
            self.assertEqual(before,r.snapshot()['state'])

    def test_counter_alternative_stays_explicit_and_unknown_activation_halts(self):
        r=self.runtime();a=self.plain(r,'A','EX1-013')
        card=next(c for c in r.state.zones['B']['deck'] if c.card_number=='BT19-011')
        r.state.zones['B']['deck'].remove(card);r.state.zones['B']['hand'].append(card)
        declare_attack(r,'A',a,'PLAYER',ROOT)
        opts=counter_options(r,'B');self.assertIn(card.key,[e['card'] for e in opts])
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'COUNTER_EFFECT_UNSUPPORTED'):
            choose_counter(r,'B',card.key,ROOT)
        self.assertEqual(before,r.snapshot()['state'])

    def test_future_or_contradictory_placement_history_never_declares_attack(self):
        for played,ready in [(4,None),(4,3),(1,1),(2,1)]:
            r=self.runtime();a=self.plain(r,'A','EX1-013',played=played)
            r.state.battle['A'][a].ready_since_turn=ready
            before=r.snapshot()['state']
            with self.subTest(played=played,ready=ready),self.assertRaisesRegex(RuntimeHalt,'ATTACK_HISTORY_UNVERIFIED'):
                declare_attack(r,'A',a,'PLAYER',ROOT)
            self.assertEqual(before,r.snapshot()['state'])
            self.assertFalse(r.state.terminal)

    def test_unmodeled_security_card_halts_at_confirmation_without_silent_skip(self):
        r=self.runtime();a=self.plain(r,'A','EX1-013');self.sec(r,'B','BT9-109')
        self.windows(r,'A',a);before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'SECURITY_CARD_UNSUPPORTED.*BT9-109'):confirm_attack(r,'A',ROOT)
        self.assertEqual(before,r.snapshot()['state'])

    def test_attacker_loss_keeps_counter_and_block_windows_but_attack_fails(self):
        r=self.runtime();a=self.plain(r,'A','EX1-013');declare_attack(r,'A',a,'PLAYER',ROOT)
        stack=r.state.battle['A'].pop(a);r.state.zones['A']['trash'].extend(stack.cards)
        choose_counter(r,'B',None,ROOT);choose_blocker(r,'B',None,ROOT)
        result=confirm_attack(r,'A',ROOT)
        self.assertFalse(result['success']);self.assertFalse(r.state.terminal)
        end_attack(r,'A',ROOT);self.assertIsNone(r.state.attack);r.verify()

    def test_other_main_actions_cannot_skip_an_open_attack(self):
        from turn_flow import pass_turn
        r=self.runtime();a=self.plain(r,'A','EX1-013');declare_attack(r,'A',a,'PLAYER',ROOT)
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'ATTACK_PROCESSING_PENDING'):pass_turn(r,'A',ROOT)
        self.assertEqual(before,r.snapshot()['state'])


if __name__=='__main__':unittest.main()
