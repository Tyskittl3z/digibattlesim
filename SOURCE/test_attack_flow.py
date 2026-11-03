import unittest
import copy
import gzip
import json

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

    def test_tamers_cannot_declare_or_be_chosen_as_normal_attack_targets(self):
        r=self.runtime();tamer=self.plain(r,'A','BT11-112')
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'ATTACKER_NOT_DIGIMON'):
            declare_attack(r,'A',tamer,'PLAYER',ROOT)
        self.assertEqual(r.snapshot()['state'],before)
        r=self.runtime('B');attacker=self.plain(r,'B','ST7-05')
        tamer=self.plain(r,'A','BT11-112',suspended=True)
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'ATTACK_TARGET_NOT_DIGIMON'):
            declare_attack(r,'B',attacker,tamer,ROOT)
        self.assertEqual(r.snapshot()['state'],before)

    def test_actual_battle_deletion_does_not_skip_an_unrelated_live_inherited_observer(self):
        r=self.runtime('B');attacker=self.plain(r,'B','ST7-05')
        defender=self.plain(r,'A','EX1-013',suspended=True)
        stage(r,'B',['EX8-009','ST7-05'])
        self.windows(r,'B',attacker,defender);before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'BATTLE_LEAVE_OBSERVER_UNIMPLEMENTED.*EX8-009'):
            confirm_attack(r,'B',ROOT)
        self.assertEqual(r.snapshot()['state'],before)


class EncounteredAeroAttackTests(unittest.TestCase):
    def actual(self):
        from imported_attempts import _apply
        from matchup_readiness import load_context_file
        path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-03/game-0000-segment.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context=load_context_file(ROOT/record['replay_provenance']['context_file'])
        r=ContextRuntime(context,record['seed'],record['first'],
                         build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(r,command['command'],command['seat'],command['args'],ROOT)
        self.assertEqual(r.snapshot()['state'],record['halts'][-1]['before']['state'])
        self.assertEqual(r.snapshot()['rng_state'],record['halts'][-1]['before']['rng_state'])
        return r,record['commands'][-1]['args']['attacker']

    def test_saved_aero_attack_queues_actual_when_attacking_then_completes_security_check(self):
        from effect_scheduler import pending_options,resolve_pending
        r,attacker=self.actual()
        self.assertEqual((r.state.turn,r.state.memory,r.state.active),(6,3,'B'))
        before_rng=r.snapshot()['rng_state']
        result=declare_attack(r,'B',attacker,'PLAYER',ROOT)
        self.assertTrue(r.state.battle['B'][attacker].suspended)
        self.assertEqual(r.state.attack['window'],'COUNTER')
        options=pending_options(r,'B')
        self.assertEqual([(p['source'],p['effect_id']) for p in options],
                         [(attacker,'EX13-022.play_tamer')])
        self.assertEqual(result['triggered_effects'],['EX13-022.play_tamer'])
        trial=copy.deepcopy(r);before=trial.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            choose_counter(trial,'A',None,ROOT)
        self.assertEqual(trial.snapshot()['state'],before)
        resolve_pending(r,'B',options[0]['id'],None)
        self.assertTrue(any(usage[-1]=='EX13-022.play_tamer' for usage in r.state.once_used))
        choose_counter(r,'A',None,ROOT);choose_blocker(r,'A',None,ROOT)
        result=confirm_attack(r,'B',ROOT)
        self.assertEqual(result['checked_card'],'A:P-138#4')
        self.assertFalse(result['attacker_deleted'])
        self.assertIn(attacker,r.state.battle['B'])
        self.assertEqual(len(r.state.zones['A']['security']),4)
        self.assertIn('A:P-138#4',[c.key for c in r.state.zones['A']['trash']])
        end_attack(r,'B',ROOT)
        self.assertIsNone(r.state.attack)
        self.assertEqual(r.state.memory,3)
        self.assertEqual(r.snapshot()['rng_state'],before_rng);r.verify()

    def test_same_owner_rina_actual_suspension_observer_is_not_silently_skipped(self):
        r,attacker=self.actual()
        physical=next(c for c in r.state.zones['B']['hand'] if c.card_number=='BT11-112')
        r.state.zones['B']['hand'].remove(physical)
        from context_runtime import Stack
        r.state.battle['B'][physical.key]=Stack([physical],played_turn=4)
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'ATTACK_ORIENTATION_TRIGGER_UNIMPLEMENTED.*BT11-112'):
            declare_attack(r,'B',attacker,'PLAYER',ROOT)
        self.assertEqual(r.snapshot()['state'],before)

    def test_defender_with_available_granted_blocker_cannot_be_silently_omitted(self):
        from effect_grants import grant_effect
        from effect_scheduler import pending_options,resolve_pending
        r,attacker=self.actual()
        grant_effect(r,'A','A:EX13-022#1',{'keywords':['Blocker']},'A:BT11-112#2')
        declare_attack(r,'B',attacker,'PLAYER',ROOT)
        pending=pending_options(r,'B')[0]
        resolve_pending(r,'B',pending['id'],None)
        choose_counter(r,'A',None,ROOT);before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'BLOCKER_CHOICE_UNIMPLEMENTED.*A:EX13-022#1'):
            choose_blocker(r,'A',None,ROOT)
        self.assertEqual(r.snapshot()['state'],before)

    def test_free_rina_play_after_declaration_does_not_retrotrigger_suspension(self):
        from effect_scheduler import pending_options,resolve_pending
        r,attacker=self.actual();declare_attack(r,'B',attacker,'PLAYER',ROOT)
        resolve_pending(r,'B',pending_options(r,'B')[0]['id'],'B:BT11-112#3')
        effects=pending_options(r,'B')
        self.assertEqual({p['effect_id'] for p in effects},
                         {'BT11-112.on_play_grant','EX13-022.tamer_play_restriction',
                          'EX13-002.tamer_play_unsuspend'})
        self.assertTrue(r.state.battle['B'][attacker].suspended)
        while r.state.pending:
            effect=pending_options(r,'B')[0]
            choice=(attacker if effect['effect_id']=='BT11-112.on_play_grant'
                    else False if effect['effect_id']=='EX13-002.tamer_play_unsuspend'
                    else 'A:BT12-029#2')
            resolve_pending(r,'B',effect['id'],choice)
        choose_counter(r,'A',None,ROOT);choose_blocker(r,'A',None,ROOT)
        confirm_attack(r,'B',ROOT);end_attack(r,'B',ROOT)
        self.assertTrue(r.state.battle['B'][attacker].suspended);r.verify()

    def test_shared_aero_once_per_turn_use_prevents_another_attack_activation(self):
        from tamer_play_effects import PLAY_EFFECT,tamer_play_usage
        r,attacker=self.actual()
        r.state.once_used.add(tamer_play_usage(r,'B',attacker,PLAY_EFFECT))
        declare_attack(r,'B',attacker,'PLAYER',ROOT)
        self.assertEqual(r.state.pending,[])
        self.assertTrue(r.state.battle['B'][attacker].suspended);r.verify()

    def evade_fixture(self,*,unsuspend=False):
        from matchup_readiness import load_context_file
        from effect_grants import grant_effect
        from effect_scheduler import pending_options,resolve_pending
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        r=ContextRuntime(context,441,'B',build_selected_registry(context,ROOT),allow_experimental=True)
        r.state.phase='MAIN';r.state.turn=3
        attacker=stage(r,'B',['EX13-022']);r.state.battle['B'][attacker].played_turn=1
        source=stage(r,'B',['BT11-112'])
        grant_effect(r,'B',attacker,{'keywords':['Evade']},source)
        # Applied grants persist after their source leaves (CR15-13). This
        # narrow fixture avoids introducing a second orientation observer.
        r.state.zones['B']['trash'].extend(r.state.battle['B'].pop(source).cards)
        checked=next(c for c in r.state.zones['A']['deck'] if c.card_number=='BT12-029')
        r.state.zones['A']['deck'].remove(checked);r.state.zones['A']['security'].append(checked)
        declare_attack(r,'B',attacker,'PLAYER',ROOT)
        resolve_pending(r,'B',pending_options(r,'B')[0]['id'],None)
        if unsuspend:
            # A post-effect snapshot: an orientation effect may unsuspend this
            # singleton during its attack. No live unsuspend observers remain.
            r.state.battle['B'][attacker].suspended=False
        choose_counter(r,'A',None,ROOT);choose_blocker(r,'A',None,ROOT)
        return r,attacker,checked.key

    def test_payable_evade_halts_actual_deletion_before_security_or_battle_cards_move(self):
        r,attacker,checked=self.evade_fixture(unsuspend=True)
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'BATTLE_EVADE_CHOICE_UNIMPLEMENTED.*'+attacker):
            confirm_attack(r,'B',ROOT)
        self.assertEqual(r.snapshot()['state'],before)
        self.assertEqual(r.state.zones['A']['security'][-1].key,checked)

    def test_suspended_evade_cannot_pay_and_does_not_prevent_battle_deletion(self):
        r,attacker,checked=self.evade_fixture()
        result=confirm_attack(r,'B',ROOT)
        self.assertTrue(result['attacker_deleted'])
        self.assertNotIn(attacker,r.state.battle['B'])
        self.assertIn(checked,[c.key for c in r.state.zones['A']['trash']]);r.verify()


if __name__=='__main__':unittest.main()
