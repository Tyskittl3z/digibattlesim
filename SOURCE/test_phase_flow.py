import unittest

from context_runtime import ContextRuntime,RuntimeHalt
from effect_scheduler import pending_options,resolve_pending
from match_preparation import begin_preparation,choose_redraw
from phase_flow import advance_phase,choose_breeding_action
from selected_mechanics import build_selected_registry
from test_selected_mechanics import selected_context,stage,ROOT


class PhaseTests(unittest.TestCase):
    def runtime(self):
        c=selected_context();r=ContextRuntime(c,901,'A',build_selected_registry(c,ROOT),allow_experimental=True)
        begin_preparation(r,ROOT);choose_redraw(r,'A',False,ROOT);choose_redraw(r,'B',False,ROOT)
        return r

    def test_empty_board_first_turn_skips_draw_and_explicit_hatch_enters_main(self):
        r=self.runtime()
        advance_phase(r,'A',ROOT);self.assertEqual(r.state.phase,'TURN_START_EFFECTS')
        advance_phase(r,'A',ROOT);self.assertEqual(r.state.phase,'DRAW')
        advance_phase(r,'A',ROOT);self.assertEqual(r.state.phase,'BREEDING')
        self.assertEqual(len(r.state.zones['A']['hand']),5)
        choose_breeding_action(r,'A','hatch',ROOT)
        self.assertEqual(r.state.phase,'MAIN');self.assertEqual(len(r.state.breeding['A']),1)
        self.assertEqual(r.state.zones['A']['eggdeck'].__len__(),3)
        self.assertEqual(r.matches_played,0)

    def test_draw_on_later_turn_and_no_breeding_choice_is_automatic(self):
        r=self.runtime();r.state.turn=2;r.state.active='B'
        for _ in range(3):advance_phase(r,'B',ROOT)
        self.assertEqual(len(r.state.zones['B']['hand']),6)
        self.assertEqual(r.state.breeding['B'],[])
        choose_breeding_action(r,'B','skip',ROOT)
        self.assertEqual(r.state.breeding['B'],[]);self.assertEqual(r.state.phase,'MAIN')

    def test_start_turn_memory_effect_precedes_unsuspending(self):
        r=self.runtime();source=stage(r,'A',['BT22-085'],suspended=True)
        advance_phase(r,'A',ROOT)
        self.assertTrue(r.state.battle['A'][source].suspended)
        with self.assertRaisesRegex(RuntimeHalt,'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            advance_phase(r,'A',ROOT)
        r=self.runtime();source=stage(r,'A',['BT22-085'],suspended=True)
        advance_phase(r,'A',ROOT)
        resolve_pending(r,'A',pending_options(r,'A')[0]['id'],None)
        self.assertEqual(r.state.memory,3)
        advance_phase(r,'A',ROOT)
        self.assertFalse(r.state.battle['A'][source].suspended)

    def test_unsuspend_phase_emits_inherited_memory_but_not_main_phase_only_memory(self):
        r=self.runtime();r.state.turn=2
        source=stage(r,'A',['P-138','EX1-013','EX13-023'],suspended=True)
        advance_phase(r,'A',ROOT);advance_phase(r,'A',ROOT)
        self.assertFalse(r.state.battle['A'][source].suspended)
        opts=pending_options(r,'A');self.assertEqual(len(opts),1)
        self.assertEqual(opts[0]['effect_id'],'P-138.unsuspend_memory')
        self.assertEqual(r.state.phase,'UNSUSPEND')
        self.assertEqual(r.public_view('A')['phase'],'UNSUSPEND')
        resolve_pending(r,'A',opts[0]['id'],None)
        self.assertEqual(r.state.phase,'UNSUSPEND')
        advance_phase(r,'A',ROOT)
        self.assertEqual(r.state.phase,'DRAW')

    def test_start_main_conditional_memory_uses_current_board(self):
        r=self.runtime();stage(r,'A',['EX13-069']);stage(r,'A',['BT11-023'])
        for _ in range(3):advance_phase(r,'A',ROOT)
        choose_breeding_action(r,'A','skip',ROOT)
        opts=pending_options(r,'A');self.assertEqual(len(opts),1)
        resolve_pending(r,'A',opts[0]['id'],None)
        self.assertEqual(r.state.memory,1)

    def test_wrong_actor_or_main_phase_advance_is_not_an_implicit_pass(self):
        r=self.runtime();before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'ACTIVE_PLAYER_REQUIRED'):
            advance_phase(r,'B',ROOT)
        self.assertEqual(before,r.snapshot()['state'])
        r=self.runtime();r.state.phase='MAIN'
        with self.assertRaisesRegex(RuntimeHalt,'MAIN_ACTION_REQUIRED'):
            advance_phase(r,'A',ROOT)

    def test_unknown_start_turn_option_effect_halts_before_phase_changes(self):
        r=self.runtime();stage(r,'A',['LM-028'])
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PHASE_TRIGGER_UNSUPPORTED.*LM-028'):
            advance_phase(r,'A',ROOT)
        self.assertEqual(before,r.snapshot()['state'])

    def test_egg_cannot_promote_and_when_moving_search_is_not_skipped(self):
        r=self.runtime();r.state.phase='BREEDING'
        egg=r.state.zones['A']['eggdeck'].pop();r.state.breeding['A']=[egg]
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PROMOTION_REQUIRES_LEVEL_3'):
            choose_breeding_action(r,'A','promote',ROOT)
        self.assertEqual(before,r.snapshot()['state'])
        r=self.runtime();r.state.phase='BREEDING'
        c=next(c for c in r.state.zones['A']['deck'] if c.card_number=='EX13-017')
        r.state.zones['A']['deck'].remove(c);r.state.breeding['A']=[c]
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'WHEN_MOVING_UNSUPPORTED.*EX13-017'):
            choose_breeding_action(r,'A','promote',ROOT)
        self.assertEqual(before,r.snapshot()['state'])


if __name__=='__main__':unittest.main()
