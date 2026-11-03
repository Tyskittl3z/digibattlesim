import unittest

from context_runtime import ContextRuntime,RuntimeHalt
from effect_scheduler import pending_options,resolve_pending
from main_actions import choose_play
from selected_mechanics import build_selected_registry
from test_selected_mechanics import selected_context,stage,ROOT


def hand_card(runtime,seat,number):
    zones=runtime.state.zones[seat]
    for card in zones['hand']:
        if card.card_number==number:return card.key
    card=next(c for c in zones['deck'] if c.card_number==number)
    zones['deck'].remove(card);zones['hand'].append(card)
    return card.key


class MainPlayTests(unittest.TestCase):
    def runtime(self):
        c=selected_context();r=ContextRuntime(c,117,'A',build_selected_registry(c,ROOT),allow_experimental=True)
        r.state.phase='MAIN';r.state.turn=1
        return r

    def test_plain_card_first_play_pays_exact_cost_and_registers_physical_stack(self):
        r=self.runtime();key=hand_card(r,'A','EX1-013')
        cost=r.context.card('A','EX1-013').to_dict()['play_cost']
        result=choose_play(r,'A',key,ROOT)
        self.assertEqual(r.state.memory,-cost)
        self.assertEqual(r.state.phase,'END_OF_TURN')
        self.assertEqual([c.key for c in r.state.battle['A'][key].cards],[key])
        self.assertEqual(result['played_card'],key);r.verify()
        self.assertEqual(r.matches_played,0)

    def test_search_play_queues_explicit_effect_before_turn_end(self):
        r=self.runtime();key=hand_card(r,'A','BT11-023')
        choose_play(r,'A',key,ROOT)
        self.assertEqual(r.state.phase,'MAIN')
        opts=pending_options(r,'A');self.assertEqual(len(opts),1)
        self.assertEqual(opts[0]['effect_id'],'BT11-023.on_play_search')
        from search_effects import search_choices
        choices=search_choices(r,'A',key);selection=choices['selections'][0]
        remaining=[c for c in choices['revealed'] if c not in selection]
        resolve_pending(r,'A',opts[0]['id'],{'selected':selection,'bottom_order':remaining})
        self.assertEqual(r.state.pending,[]);self.assertEqual(r.state.phase,'END_OF_TURN')
        self.assertEqual(r.matches_played,0)

    def test_unknown_on_play_or_option_is_not_silently_skipped(self):
        for seat,number in (('B','EX13-015'),('A','P-104')):
            r=self.runtime();r.state.active=seat
            key=hand_card(r,seat,number);before=r.snapshot()['state']
            with self.assertRaisesRegex(RuntimeHalt,'PLAY_EFFECT_UNSUPPORTED|OPTION_USE_UNIMPLEMENTED'):
                choose_play(r,seat,key,ROOT)
            self.assertEqual(before,r.snapshot()['state'])

    def test_ulforce_full_cost_play_queues_both_on_play_effects_and_shared_orientation_opt(self):
        from selected_mechanics import ORIENTATION_EFFECT,_usage
        from effect_scheduler import queue_effects
        r=self.runtime();r.state.memory=2
        key=hand_card(r,'A','EX13-023')
        result=choose_play(r,'A',key,ROOT)
        self.assertEqual((result['cost'],r.state.memory,r.state.phase),(12,-10,'MAIN'))
        self.assertEqual([c.key for c in r.state.battle['A'][key].cards],[key])
        group=pending_options(r,'A')
        self.assertEqual([(p['effect_id'],p['depth']) for p in group],
                         [(ORIENTATION_EFFECT,0),('EX13-023.return_fewest',0)])
        self.assertEqual(group[0]['usage'],list(_usage(r,'A',key,ORIENTATION_EFFECT)))
        self.assertEqual(group[1]['usage'],[])
        for pending in group:
            resolve_pending(r,'A',pending['id'],None if pending['effect_id']==ORIENTATION_EFFECT else False)
        self.assertEqual((r.state.memory,r.state.phase),(-10,'END_OF_TURN'))
        self.assertIn(_usage(r,'A',key,ORIENTATION_EFFECT),r.state.once_used)
        queue_effects(r,[{'seat':'A','source':key,'effect_id':ORIENTATION_EFFECT,'field':'main_text',
            'usage':list(_usage(r,'A',key,ORIENTATION_EFFECT)),'trigger':{'kind':'When Attacking'}}])
        self.assertEqual(r.state.pending,[]);r.verify()

    def test_live_board_scope_wrong_actor_or_not_in_hand_fails_atomically(self):
        for case in ('board','actor','source'):
            r=self.runtime();key=hand_card(r,'A','BT11-112' if case=='board' else 'EX1-013')
            if case=='board':stage(r,'A',['BT11-023','P-138'])
            before=r.snapshot()['state']
            with self.assertRaises(RuntimeHalt):
                choose_play(r,'B' if case=='actor' else 'A','absent' if case=='source' else key,ROOT)
            self.assertEqual(before,r.snapshot()['state'])

    def test_search_view_cannot_peek_at_deck_outside_forced_activation_window(self):
        from search_effects import search_choices
        from effect_scheduler import queue_effects
        r=self.runtime();key=stage(r,'A',['BT11-023'])
        with self.assertRaisesRegex(RuntimeHalt,'SEARCH_ACTIVATION_WINDOW_REQUIRED'):
            search_choices(r,'A',key)
        r=self.runtime();key=hand_card(r,'A','BT11-023');choose_play(r,'A',key,ROOT)
        queue_effects(r,[{'seat':'A','source':key,'effect_id':'BT11-023.on_play_search','field':'main_text',
                         'trigger':{'kind':'On Play'}}])
        with self.assertRaisesRegex(RuntimeHalt,'SEARCH_ACTIVATION_WINDOW_REQUIRED'):
            search_choices(r,'A',key)

    def test_plain_play_cannot_bypass_selected_input_capability(self):
        from match_context import MatchContext,DeckDefinition,CardDefinition
        for mutation in ('source_id','cost'):
            context=selected_context();decks=[context.deck_a,context.deck_b]
            cards={c.number:c for c in context.cards}
            if mutation=='source_id':
                raw=decks[0].to_dict();raw['source_id']='unselected-list'
                decks[0]=DeckDefinition.from_dict(raw)
            else:
                raw=cards['EX1-013'].to_dict();raw['play_cost']=0
                cards['EX1-013']=CardDefinition.from_dict(raw)
            context=MatchContext.create(*decks,cards,context.to_dict()['rules'])
            r=ContextRuntime(context,117,'A',allow_experimental=True)
            r.state.phase='MAIN';r.state.turn=1
            key=hand_card(r,'A','EX1-013');before=r.snapshot()['state']
            with self.subTest(mutation=mutation),self.assertRaisesRegex(RuntimeHalt,'SELECTED_PLAY_CAPABILITY_REQUIRED'):
                choose_play(r,'A',key,ROOT)
            self.assertEqual(before,r.snapshot()['state'])

    def test_inert_singleton_board_allows_second_plain_or_search_play(self):
        for number in ('EX1-013','BT11-023'):
            r=self.runtime();r.state.memory=6
            existing=stage(r,'B',['ST7-05'])
            key=hand_card(r,'A',number)
            choose_play(r,'A',key,ROOT)
            self.assertIn(existing,r.state.battle['B']);self.assertIn(key,r.state.battle['A'])
            self.assertEqual(r.state.memory,3);r.verify()

    def test_hard_play_executes_no_unrelated_timing_or_inherited_effect(self):
        for seat,number in [('A','EX13-019'),('B','BT12-016'),('B','EX8-012'),
                            ('B','BT19-007'),('B','BT19-080'),('A','EX13-069')]:
            r=self.runtime();r.state.active=seat;r.state.memory=10
            key=hand_card(r,seat,number);hand_before=len(r.state.zones[seat]['hand'])
            cost=r.context.card(seat,number).to_dict()['play_cost']
            result=choose_play(r,seat,key,ROOT)
            self.assertIn(key,r.state.battle[seat]);self.assertEqual(r.state.memory,10-cost)
            self.assertEqual(len(r.state.zones[seat]['hand']),hand_before-1)
            self.assertEqual(r.state.pending,[])
            self.assertEqual(result['triggered_effects'],[])
            self.assertEqual(r.state.battle[seat][key].statuses,{})
            r.verify()

    def test_scramble_trash_play_cannot_be_called_without_bound_delay(self):
        from main_actions import play_blue_scramble_from_trash
        r=self.runtime();key=hand_card(r,'A','EX1-013')
        physical=next(c for c in r.state.zones['A']['hand'] if c.key==key)
        r.state.zones['A']['hand'].remove(physical);r.state.zones['A']['trash'].append(physical)
        before=r.snapshot()
        with self.assertRaisesRegex(RuntimeHalt,'OPTION_ACTIVE_BINDING_REQUIRED'):
            play_blue_scramble_from_trash(r,'A',key,ROOT)
        self.assertEqual(r.snapshot(),before)
if __name__=='__main__':unittest.main()
