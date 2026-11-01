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
        for number in ('EX13-023','P-104'):
            r=self.runtime();key=hand_card(r,'A',number);before=r.snapshot()['state']
            with self.assertRaisesRegex(RuntimeHalt,'PLAY_EFFECT_UNSUPPORTED|OPTION_USE_UNIMPLEMENTED'):
                choose_play(r,'A',key,ROOT)
            self.assertEqual(before,r.snapshot()['state'])

    def test_live_board_scope_wrong_actor_or_not_in_hand_fails_atomically(self):
        for case in ('board','actor','source'):
            r=self.runtime();key=hand_card(r,'A','EX1-013')
            if case=='board':stage(r,'B',['EX13-015'])
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
if __name__=='__main__':unittest.main()
