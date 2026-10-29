"""Integrity failures that a total-card count cannot detect."""
import unittest

from match_evidence import EvidenceMatch as FullMatch
from loaded_effects import Copy, JudgeHalt


class PhysicalIntegrityTests(unittest.TestCase):
    def test_same_count_duplicate_and_missing_card_is_rejected(self):
        m = FullMatch(0)
        p = m.ps['A']
        p.z.hand[0] = p.z.deck[0]
        with self.assertRaisesRegex(JudgeHalt, 'PHYSICAL_CARD_MISMATCH'):
            m.verify()

    def test_copy_not_in_loaded_deck_is_rejected(self):
        m = FullMatch(0)
        m.ps['A'].z.hand[0] = Copy('EX12-076', 1)
        with self.assertRaisesRegex(JudgeHalt, 'PHYSICAL_CARD_MISMATCH'):
            m.verify()

    def test_invalid_physical_copy_number_is_rejected(self):
        m = FullMatch(0)
        p = m.ps['A']
        p.z.hand[0] = Copy(p.z.hand[0].card, 999)
        with self.assertRaisesRegex(JudgeHalt, 'PHYSICAL_CARD_MISMATCH'):
            m.verify()

    def test_stack_must_end_with_its_battle_card(self):
        m = FullMatch(0)
        p = m.ps['A']
        top, bottom = p.z.hand.pop(), p.z.hand.pop()
        p.z.battle.append(top)
        p.stacks[top.key()] = [top, bottom]
        with self.assertRaisesRegex(JudgeHalt, 'STACK_ANCHOR_MISMATCH'):
            m.verify()

    def test_stack_cannot_exist_without_battle_card(self):
        m = FullMatch(0)
        p = m.ps['A']
        a, b = p.z.hand.pop(), p.z.hand.pop()
        p.z.battle.append(a)
        p.stacks[b.key()] = [b, a]
        with self.assertRaisesRegex(JudgeHalt, 'STACK_ANCHOR_MISMATCH'):
            m.verify()

    def test_memory_gauge_outside_bounds_is_rejected(self):
        for memory in (-11, 11, 1.5, True):
            with self.subTest(memory=memory):
                m = FullMatch(0)
                m.mem = memory
                with self.assertRaisesRegex(JudgeHalt, 'MEMORY_GAUGE_INVALID'):
                    m.verify()

    def test_no_event_can_follow_game_end(self):
        m = FullMatch(0)
        m.event('GAME_END', winner='A')
        before = list(m.events)
        with self.assertRaisesRegex(JudgeHalt, 'EVENT_AFTER_GAME_END'):
            m.event('TURN_END', memory=-3)
        self.assertEqual(m.events, before)

    def test_initial_physical_cards_and_legal_memory_pass(self):
        for memory in (-10, 0, 10):
            m = FullMatch(0)
            m.mem = memory
            m.verify()


if __name__ == '__main__':
    unittest.main()
