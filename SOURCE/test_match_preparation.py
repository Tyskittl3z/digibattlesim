import unittest

from context_runtime import ContextRuntime,RuntimeHalt
from match_preparation import begin_preparation,choose_redraw
from test_selected_mechanics import selected_context,ROOT


class PreparationTests(unittest.TestCase):
    def runtime(self,first='A'):
        return ContextRuntime(selected_context(),841,first,allow_experimental=True)

    def test_both_initial_hands_dealt_before_first_redraw_decision(self):
        r=self.runtime();begin_preparation(r,ROOT)
        self.assertEqual(r.state.phase,'INITIAL_HANDS')
        for seat in ('A','B'):
            self.assertEqual(len(r.state.zones[seat]['hand']),5)
            self.assertEqual(len(r.state.zones[seat]['deck']),45)
            self.assertEqual(r.state.zones[seat]['security'],[])
        self.assertEqual(r.state.preparation['choices'],[])
        self.assertEqual(r.matches_played,0)

    def test_first_player_decides_before_second_and_each_decides_once(self):
        r=self.runtime('B');begin_preparation(r,ROOT);before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'REDRAW_CONTROLLER_ORDER'):
            choose_redraw(r,'A',False,ROOT)
        self.assertEqual(before,r.snapshot()['state'])
        r=self.runtime('B');begin_preparation(r,ROOT)
        choose_redraw(r,'B',False,ROOT)
        with self.assertRaisesRegex(RuntimeHalt,'REDRAW_CONTROLLER_ORDER'):
            choose_redraw(r,'B',True,ROOT)

    def test_redraw_returns_entire_hand_shuffles_and_deals_five(self):
        a,b=self.runtime(),self.runtime()
        for r in (a,b):
            begin_preparation(r,ROOT);choose_redraw(r,'A',True,ROOT)
            self.assertEqual(len(r.state.zones['A']['hand']),5)
            self.assertEqual(len(r.state.zones['A']['deck']),45)
            self.assertEqual(r.state.preparation['choices'],[{'seat':'A','redraw':True}])
            r.verify()
        self.assertEqual(a.snapshot(),b.snapshot())
        self.assertEqual(a.events,b.events)

    def test_security_top_deck_becomes_bottom_security_after_both_choices(self):
        r=self.runtime();begin_preparation(r,ROOT);choose_redraw(r,'A',False,ROOT)
        tops={s:[c.key for c in reversed(r.state.zones[s]['deck'][-5:])] for s in ('A','B')}
        choose_redraw(r,'B',False,ROOT)
        for seat in ('A','B'):
            self.assertEqual([c.key for c in r.state.zones[seat]['security']],tops[seat])
            self.assertEqual(len(r.state.zones[seat]['deck']),40)
        self.assertEqual(r.state.phase,'START_OF_TURN')
        self.assertEqual(r.state.turn,1);self.assertEqual(r.state.memory,0)
        self.assertEqual(r.matches_played,0)
        self.assertEqual(r.public_view('A')['players']['B']['security'],{'count':5})

    def test_invalid_choice_and_repeated_preparation_cannot_mutate(self):
        r=self.runtime();begin_preparation(r,ROOT);before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'BOOLEAN_REDRAW_CHOICE'):
            choose_redraw(r,'A','no',ROOT)
        self.assertEqual(before,r.snapshot()['state'])
        r=self.runtime();begin_preparation(r,ROOT);before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PREPARATION_ALREADY_STARTED'):
            begin_preparation(r,ROOT)
        self.assertEqual(before,r.snapshot()['state'])


if __name__=='__main__':unittest.main()
