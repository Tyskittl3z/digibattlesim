import unittest
from loaded_effects import (Copy,MatchZones,resolve_search,resolve_discard_draw,
                            options_for_search,discard_candidates,IllegalSelection,JudgeHalt,
                            source_hash,TWO_CATEGORY_SEARCH,SINGLE_CATEGORY_SEARCH,DISCARD_DRAW)


def zones(seat,ids, hand=None, security=None):
    counted={}
    def physical(items):
        out=[]
        for card in items:
            counted[card]=counted.get(card,0)+1
            out.append(Copy(card,counted[card]))
        return out
    return MatchZones(seat,physical(ids),physical(hand or []),[],physical(security or []),[],[])

class SearchJudgeTests(unittest.TestCase):
    def test_official_card_text_pins(self):
        for c in [*TWO_CATEGORY_SEARCH,*SINGLE_CATEGORY_SEARCH,*DISCARD_DRAW]:
            seat='A' if c.startswith('BT24') or c.startswith('BT25') else 'B'
            if c=='BT26-104':seat='B'
            self.assertEqual(len(source_hash(seat,c)),64)

    def test_jupiter_two_category_search_must_take_two(self):
        z=zones('A',['BT26-033','BT24-084','BT24-034'])
        elig=options_for_search(z,'BT24-031')
        self.assertEqual(len(elig['revealed']),3)
        with self.assertRaises(IllegalSelection):resolve_search(z,'BT24-031')
        ev=resolve_search(z,'BT24-031',elig['category_1'][0],elig['category_2'][1])
        self.assertEqual(len(ev['to_hand']),2)
        self.assertEqual(z.count(),3)
        self.assertEqual(z.deck[0].key(),ev['to_bottom'][0])

    def test_toho_two_category_search_distinct_copies(self):
        z=zones('B',['EX12-009','EX12-026','EX12-061'])
        elig=options_for_search(z,'EX12-009')
        with self.assertRaises(IllegalSelection):
            resolve_search(z,'EX12-009',elig['category_1'][0],elig['category_2'][0])
        ev=resolve_search(z,'EX12-009',elig['category_1'][0],elig['category_2'][1])
        self.assertEqual(len(ev['to_hand']),2)
        self.assertEqual(len(z.hand),2)

    def test_only_one_eligible_dual_trait_must_take_one(self):
        z=zones('B',['EX12-009','EX1-066','EX1-066'])
        e=options_for_search(z,'EX12-009')
        self.assertEqual(len(e['category_1']),1)
        self.assertEqual(len(e['category_2']),1)
        with self.assertRaises(IllegalSelection):resolve_search(z,'EX12-009')
        result=resolve_search(z,'EX12-009',choose1=e['category_1'][0])
        self.assertEqual(len(result['to_hand']),1)

    def test_single_match_choose_one(self):
        z=zones('A',['BT26-103','BT24-085','BT25-028'])
        opt=options_for_search(z,'BT24-083')
        with self.assertRaises(IllegalSelection):resolve_search(z,'BT24-083')
        e=resolve_search(z,'BT24-083',choose1=opt['category_1'][0])
        self.assertEqual(len(e['to_hand']),1)

    def test_zero_matches_returns_all_to_bottom(self):
        z=zones('B',['EX1-066','EX1-066','EX1-066'])
        ev=resolve_search(z,'EX12-009')
        self.assertEqual(ev['to_hand'],[])
        self.assertEqual(len(z.deck),3)

    def test_bottom_order_and_replay_hash(self):
        def run():
            z=zones('B',['EX12-009','EX12-026','EX12-061'])
            e=options_for_search(z,'EX12-009')
            chosen=[e['category_1'][0],e['category_2'][1]]
            leftover=[k for k in e['revealed'] if k not in chosen]
            return resolve_search(z,'EX12-009',*chosen,bottom_order=list(reversed(leftover)))
        self.assertEqual(run(),run())

    def test_wrong_deck_rejected(self):
        z=zones('A',['BT24-031'])
        with self.assertRaises(IllegalSelection):resolve_search(z,'EX12-009')

    def test_selection_error_does_not_mutate(self):
        z=zones('A',['BT24-031','BT24-034','BT24-084'])
        before=z.fingerprint()
        with self.assertRaises(IllegalSelection):resolve_search(z,'BT24-031',choose1='INVALID')
        self.assertEqual(z.fingerprint(),before)

    def test_hanimon_discard_draw_optional(self):
        z=zones('B',['EX12-009','EX12-026','EX12-031'],['EX12-062','EX1-066'])
        before=z.count()
        self.assertEqual(resolve_discard_draw(z,'EX12-061')['discarded'],None)
        eligible=discard_candidates(z,'EX12-061')
        self.assertEqual(len(eligible),1)
        e=resolve_discard_draw(z,'EX12-061',eligible[0])
        self.assertEqual(len(e['drawn']),2)
        self.assertEqual(len(z.trash),1)
        self.assertEqual(z.count(),before)

    def test_discard_noneligible_rejected(self):
        z=zones('B',['EX12-009','EX12-026'],['EX1-066'])
        with self.assertRaises(IllegalSelection):resolve_discard_draw(z,'EX12-061',z.hand[0].key())

    def test_asuna_qualifies_from_ts_trait(self):
        z=zones('A',['BT25-030'],['BT24-031','BT25-028'])
        choices=discard_candidates(z,'BT24-088')
        self.assertIn(z.hand[0].key(),choices)

    def test_empty_deck_effect_draw_not_defeat(self):
        z=zones('B',[],['EX12-062'])
        a=discard_candidates(z,'EX12-061')[0]
        e=resolve_discard_draw(z,'EX12-061',a)
        self.assertEqual(e['drawn'],[])
        self.assertEqual(len(z.trash),1)

if __name__=='__main__':unittest.main()

class AdditionalEncounterTests(unittest.TestCase):
    def test_analog_youth_add_and_trash(self):
        from loaded_effects import resolve_analog_youth
        z=zones('B',['EX12-009','EX1-066','EX12-061'])
        with self.assertRaises(IllegalSelection):resolve_analog_youth(z)
        ev=resolve_analog_youth(z,'EX12-061#1')
        self.assertEqual(ev['added'],'EX12-061#1')
        self.assertEqual(len(ev['trashed']),2)
        self.assertEqual(len(z.deck),0)
        self.assertEqual(z.count(),3)

    def test_analog_youth_ignores_non_digimon(self):
        from loaded_effects import resolve_analog_youth
        z=zones('B',['EX1-066','EX12-075','BT26-104'])
        ev=resolve_analog_youth(z)
        self.assertIsNone(ev['added'])
        self.assertEqual(len(ev['trashed']),3)

    def test_aegiomon_cost_plays_ts_tamer(self):
        from loaded_effects import resolve_aegiomon_tamer,eligible_free_tamers
        z=zones('A',[],['BT24-084','BT24-085'],['BT26-103','BT24-031'])
        target=eligible_free_tamers(z)[0]
        ev=resolve_aegiomon_tamer(z,target)
        self.assertEqual(ev['selected'],target)
        self.assertEqual(len(z.security),1)
        self.assertEqual(len(z.battle),1)
        self.assertEqual(z.count(),4)

    def test_aegiomon_cannot_duplicate_tamer_name(self):
        from loaded_effects import resolve_aegiomon_tamer
        z=zones('A',[],['BT24-084','BT24-085'],['BT24-031'])
        z.battle.append(z.hand.pop(0))
        with self.assertRaises(IllegalSelection):resolve_aegiomon_tamer(z,'BT24-084#1')
        self.assertEqual(resolve_aegiomon_tamer(z,'BT24-085#1')['selected'],'BT24-085#1')

    def test_aegiomon_cannot_pay_when_no_security(self):
        from loaded_effects import resolve_aegiomon_tamer
        z=zones('A',[],['BT24-084'])
        with self.assertRaises(IllegalSelection):resolve_aegiomon_tamer(z,'BT24-084#1')
        self.assertIsNone(resolve_aegiomon_tamer(z)['selected'])

class NoTargetBranchTests(unittest.TestCase):
    def test_no_target_branch_only_in_empty_board(self):
        from loaded_effects import resolve_no_target_branch,EMPTY_OPPONENT_ONLY
        for c in EMPTY_OPPONENT_ONLY:
            z=zones('A' if c=='BT26-013' else 'B', [])
            # BT26-013 Musyamon also belongs to Toho seat B.
            z.seat='B'
            e=resolve_no_target_branch(z,c)
            self.assertEqual(e['type'],'VERIFIED_EMPTY_OPPONENT_BRANCH')
            with self.assertRaises(JudgeHalt):
                resolve_no_target_branch(z,c,opponent_has_digimon=True)
            with self.assertRaises(JudgeHalt):
                resolve_no_target_branch(z,c,opponent_has_tamer=True)

class OfficialAegiomonQATests(unittest.TestCase):
    def test_q5613_pay_security_decline_tamer(self):
        from loaded_effects import resolve_aegiomon_tamer
        z=zones('A',[],['BT24-084'],['BT24-031'])
        e=resolve_aegiomon_tamer(z,pay_security_only=True)
        self.assertIsNone(e['selected'])
        self.assertEqual(e['security_to_hand'],'BT24-031#1')
        self.assertEqual(len(z.battle),0)
        self.assertEqual(len(z.hand),2)

    def test_q5613_no_cost_no_play(self):
        from loaded_effects import resolve_aegiomon_tamer
        z=zones('A',[],['BT24-084'],['BT24-031'])
        e=resolve_aegiomon_tamer(z)
        self.assertIsNone(e['selected'])
        self.assertIsNone(e['security_to_hand'])
        self.assertEqual(len(z.hand),1)
        self.assertEqual(len(z.security),1)

class OpponentTargetsTests(unittest.TestCase):
    def test_shellmon_locks_plain_battle_card(self):
        from loaded_effects import resolve_encountered_target
        a=zones('B',[]);b=zones('A',[]);b.battle.append(Copy('BT24-031',1))
        ev=resolve_encountered_target(a,b,'EX12-026')
        self.assertEqual(ev['trashed_sources'],[])
        self.assertTrue(b.statuses['BT24-031#1']['cant_attack'])
        self.assertEqual(len(b.battle),1)

    def test_musyamon_cost_and_delete(self):
        from loaded_effects import resolve_encountered_target
        a=zones('B',[],hand=['EX12-061']);b=zones('A',[])
        b.battle.append(Copy('BT24-031',1))
        e=resolve_encountered_target(a,b,'BT26-013')
        self.assertEqual(e['type'],'MUSYAMON_DISCARD_DELETE')
        self.assertEqual(len(a.trash),1)
        self.assertEqual(len(b.trash),1)
        self.assertEqual(len(b.battle),0)

    def test_kokeshimon_cost_deletes_itself_and_opponent(self):
        from loaded_effects import resolve_encountered_target
        a=zones('B',[]);a.battle.append(Copy('EX12-062',1))
        b=zones('A',[]);b.battle.append(Copy('BT24-034',1))
        e=resolve_encountered_target(a,b,'EX12-062')
        self.assertEqual(e['type'],'KOKESHIMON_COST_DELETE')
        self.assertEqual(len(a.trash),1)
        self.assertEqual(len(b.trash),1)

    def test_target_effect_not_other_decks(self):
        from loaded_effects import resolve_encountered_target
        z=zones('A',[]);opp=zones('B',[])
        with self.assertRaises(JudgeHalt):resolve_encountered_target(z,opp,'EX12-062')

class SecurityCardTamerSelectionTests(unittest.TestCase):
    def test_security_tamer_can_be_played_after_cost(self):
        from loaded_effects import eligible_free_tamers,resolve_aegiomon_tamer
        z=zones('A',[],['BT24-031'],['BT24-084'])
        self.assertIn('BT24-084#1',eligible_free_tamers(z,include_top_security=True))
        ev=resolve_aegiomon_tamer(z,selected='BT24-084#1')
        self.assertEqual(ev['security_to_hand'],'BT24-084#1')
        self.assertEqual(len(z.battle),1)
        self.assertEqual(len(z.security),0)

    def test_security_tamer_duplicate_name_rejected(self):
        from loaded_effects import resolve_aegiomon_tamer
        z=zones('A',[],['BT24-084'],['BT24-084'])
        t=z.hand.pop();z.battle.append(t)
        with self.assertRaises(IllegalSelection):
            resolve_aegiomon_tamer(z,selected='BT24-084#2')
