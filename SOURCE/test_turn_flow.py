"""Selected-pair turn-boundary probes; each has zero full-match credit."""
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
from selected_mechanics import ORIENTATION_EFFECT, build_selected_registry
from test_selected_mechanics import ROOT, selected_context, stage
import turn_flow


class TurnFlowTests(unittest.TestCase):
    def runtime(self, seat='A', *, phase='MAIN', memory=0):
        context = selected_context()
        runtime = ContextRuntime(context, 1901, seat,
                                 build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = phase
        runtime.state.turn = 4
        runtime.state.memory = memory
        return runtime

    def test_explicit_pass_sets_opponent_three_and_opens_end_window(self):
        for seat in ('A', 'B'):
            for memory in (0, 1, 10):
                with self.subTest(seat=seat, memory=memory):
                    r = self.runtime(seat, memory=memory)
                    r.state.once_used.add((4, seat, 'usage', 'effect'))
                    result = turn_flow.pass_turn(r, seat, ROOT)
                    self.assertEqual((r.state.active, r.state.memory, r.state.turn,
                                      r.state.phase), (seat, -3, 4, 'END_OF_TURN'))
                    self.assertEqual(r.state.once_used, {(4, seat, 'usage', 'effect')})
                    self.assertEqual(result['full_match_credit'], 0)
                    self.assertEqual(r.matches_played, 0)

    def test_negative_memory_finishes_with_exact_sign_turn_and_opt_reset(self):
        for seat in ('A', 'B'):
            for memory in (-1, -3, -10):
                with self.subTest(seat=seat, memory=memory):
                    r = self.runtime(seat, phase='END_OF_TURN', memory=memory)
                    r.state.once_used = {(4, 'A', 'one', 'effect'),
                                         (4, 'B', 'two', 'effect')}
                    original_preparation = dict(r.state.preparation)
                    result = turn_flow.finish_turn(r, seat, ROOT)
                    other = 'B' if seat == 'A' else 'A'
                    self.assertEqual((r.state.active, r.state.memory, r.state.turn,
                                      r.state.phase), (other, -memory, 5, 'START_OF_TURN'))
                    self.assertEqual(r.state.once_used, set())
                    self.assertEqual(r.state.preparation, original_preparation)
                    self.assertFalse(r.state.terminal)
                    self.assertEqual(result['full_match_credit'], 0)
                    self.assertEqual(r.matches_played, 0)

    def test_real_pending_memory_gain_rescues_turn_without_resetting_usage(self):
        r = self.runtime(phase='END_OF_TURN', memory=-1)
        source = stage(r, 'A', ['P-138', 'EX13-023'], suspended=True)
        r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
        pending = pending_options(r, 'A')
        self.assertEqual(len(pending), 1)
        resolve_pending(r, 'A', pending[0]['id'], None)
        self.assertEqual((r.state.memory, r.state.phase), (0, 'END_OF_TURN'))
        used = set(r.state.once_used)
        result = turn_flow.finish_turn(r, 'A', ROOT)
        self.assertEqual((r.state.active, r.state.memory, r.state.turn,
                          r.state.phase), ('A', 0, 4, 'MAIN'))
        self.assertEqual(r.state.once_used, used)
        self.assertTrue(result['turn_postponed'])
        # Meeting the condition again is a new end timing in the same turn;
        # uses consumed before postponement remain consumed until it changes.
        r.state.memory = -2
        r._finish_main_processing()
        turn_flow.finish_turn(r, 'A', ROOT)
        self.assertEqual((r.state.active, r.state.memory, r.state.turn), ('B', 2, 5))
        self.assertEqual(r.state.once_used, set())

    def test_pending_processing_blocks_both_turn_commands_without_mutation(self):
        for command in (turn_flow.pass_turn, turn_flow.finish_turn):
            with self.subTest(command=command.__name__):
                r = self.runtime()
                source = stage(r, 'A', ['EX13-022', 'EX13-023'])
                r.dispatch(ORIENTATION_EFFECT, 'A', source, source)
                r.state.phase = 'MAIN' if command == turn_flow.pass_turn else 'END_OF_TURN'
                before = r.snapshot()
                with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
                    command(r, 'A', ROOT)
                self.assertEqual(r.snapshot(), before)
                self.assertEqual(r.events[-1]['before'], before)

    def test_wrong_controller_rolls_back_and_retains_rules_and_seed(self):
        for command in (turn_flow.pass_turn, turn_flow.finish_turn):
            with self.subTest(command=command.__name__):
                phase = 'MAIN' if command == turn_flow.pass_turn else 'END_OF_TURN'
                r = self.runtime(phase=phase, memory=0 if phase == 'MAIN' else -3)
                before = r.snapshot()
                with self.assertRaisesRegex(RuntimeHalt, 'ACTIVE_PLAYER_REQUIRED'):
                    command(r, 'B', ROOT)
                self.assertEqual(r.snapshot(), before)
                event = r.events[-1]
                self.assertEqual(event['seed'], 1901)
                self.assertEqual(event['before'], before)
                self.assertEqual(event['choice']['rules']['sha256'],
                                 'a9f5d9589726e8750caf765c1fb44e3d5b723a5324a10b877f226059faf81271')
                self.assertIn('6-6', event['choice']['rules']['locator'])

    def test_exact_optional_end_effects_halt_before_pass_or_finish_mutates(self):
        for seat, number in (('B', 'BT20-102'),):
            for command in (turn_flow.pass_turn, turn_flow.finish_turn):
                with self.subTest(card=number, command=command.__name__):
                    phase = 'MAIN' if command == turn_flow.pass_turn else 'END_OF_TURN'
                    r = self.runtime(seat, phase=phase, memory=2 if phase == 'MAIN' else -3)
                    source = stage(r, seat, [number])
                    before = r.snapshot()
                    with self.assertRaisesRegex(RuntimeHalt, 'TURN_END_TRIGGER_UNSUPPORTED.*' + number):
                        command(r, seat, ROOT)
                    self.assertEqual(r.snapshot(), before)
                    self.assertEqual(r.state.once_used, set())
                    self.assertEqual(r.events[-1]['before'], before)
                    self.assertIn(source, r.events[-1]['reason'])

    def test_opponent_your_turn_and_hidden_main_effect_do_not_trigger(self):
        r = self.runtime()
        stage(r, 'B', ['BT20-102'])
        stage(r, 'A', ['BT22-023', 'EX13-023'])
        turn_flow.pass_turn(r, 'A', ROOT)
        turn_flow.finish_turn(r, 'A', ROOT)
        self.assertEqual((r.state.active, r.state.memory), ('B', 3))

    def test_unmodeled_status_duration_halts_instead_of_expiring_or_retaining_guess(self):
        for seat in ('A', 'B'):
            for status in ('cannot_suspend', 'cannot_unsuspend', 'dp_delta'):
                for command in (turn_flow.pass_turn, turn_flow.finish_turn):
                    with self.subTest(seat=seat, status=status, command=command.__name__):
                        phase = 'MAIN' if command == turn_flow.pass_turn else 'END_OF_TURN'
                        r = self.runtime(phase=phase, memory=0 if phase == 'MAIN' else -1)
                        source = stage(r, seat, ['BT11-023' if seat == 'A' else 'EX13-015'])
                        r.state.battle[seat][source].statuses[status] = True
                        before = r.snapshot()
                        with self.assertRaisesRegex(RuntimeHalt, 'TURN_END_STATUS_UNSUPPORTED'):
                            command(r, 'A', ROOT)
                        self.assertEqual(r.snapshot(), before)

    def test_pass_and_finish_reject_wrong_windows_without_implicit_actions(self):
        cases = [(turn_flow.pass_turn, 'BREEDING', 0, 'PASS_WINDOW_NOT_OPEN'),
                 (turn_flow.pass_turn, 'MAIN', -1, 'PASS_WINDOW_NOT_OPEN'),
                 (turn_flow.finish_turn, 'MAIN', 0, 'TURN_END_WINDOW_NOT_OPEN'),
                 (turn_flow.finish_turn, 'START_OF_TURN', 3, 'TURN_END_WINDOW_NOT_OPEN')]
        for command, phase, memory, reason in cases:
            with self.subTest(command=command.__name__, phase=phase, memory=memory):
                r = self.runtime(phase=phase, memory=memory)
                before = r.snapshot()
                with self.assertRaisesRegex(RuntimeHalt, reason):
                    command(r, 'A', ROOT)
                self.assertEqual(r.snapshot(), before)

    def test_success_retains_official_rule_evidence_and_zero_match_credit(self):
        r = self.runtime()
        for command in (turn_flow.pass_turn, turn_flow.finish_turn):
            result = command(r, 'A', ROOT)
            evidence = result['rules_source']
            self.assertEqual(evidence, r.events[-1]['choice']['rules'])
            self.assertIn('https://world.digimoncard.com/rule/pdf/general_rule.pdf', evidence['url'])
            self.assertIn('15-14-1', evidence['locator'])
            self.assertEqual(result['full_match_credit'], 0)
            self.assertEqual(r.events[-1]['status'], 'EXPERIMENTAL')
        self.assertEqual(r.matches_played, 0)


if __name__ == '__main__':
    unittest.main()
