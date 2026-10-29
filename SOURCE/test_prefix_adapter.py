"""A full match must respect the opening helper's single-card-only scope."""
import unittest

from loaded_effects import JudgeHalt
from match_evidence import EvidenceMatch


def take(player, card):
    for zone in (player.z.deck, player.z.hand, player.z.security):
        for copy in list(zone):
            if copy.card == card:
                zone.remove(copy)
                return copy
    raise AssertionError(card)


class PrefixAdapterTests(unittest.TestCase):
    def prepare(self, *target_ids):
        m = EvidenceMatch(0)
        p, other = m.ps['B'], m.ps['A']
        copies = [take(other, card) for card in target_ids]
        other.z.battle.append(copies[-1])
        other.stacks[copies[-1].key()] = copies
        source = take(p, 'EX12-062')
        p.z.hand.append(source)
        m.selected_main_card = source
        m.mem = 5
        return m, p, other, source, copies

    def test_single_card_deletion_clears_both_stack_registrations(self):
        m, p, other, source, targets = self.prepare('BT24-034')
        self.assertTrue(m.hard_play(p))
        self.assertIn(source, p.z.trash)
        self.assertIn(targets[-1], other.z.trash)
        self.assertNotIn(source.key(), p.stacks)
        self.assertNotIn(targets[-1].key(), other.stacks)
        m.verify()

    def test_stacked_target_halts_before_play_or_deletion(self):
        m, p, other, source, targets = self.prepare('BT24-031', 'BT24-034')
        before_hand = list(p.z.hand)
        before_security = list(other.z.security)
        with self.assertRaisesRegex(JudgeHalt, 'PREFIX_HANDLER_STACK_UNSUPPORTED'):
            m.hard_play(p)
        self.assertEqual(p.z.hand, before_hand)
        self.assertIn(targets[-1], other.z.battle)
        self.assertEqual(other.stacks[targets[-1].key()], targets)
        self.assertEqual(other.z.security, before_security)
        m.verify()

    def test_protected_single_card_target_halts_before_mutation(self):
        m, p, other, source, targets = self.prepare('BT24-034')
        protector = take(other, 'BT24-101')
        other.z.battle.append(protector)
        other.stacks[protector.key()] = [protector]
        with self.assertRaisesRegex(JudgeHalt, 'PREFIX_HANDLER_REPLACEMENT_UNVERIFIED'):
            m.hard_play(p)
        self.assertIn(source, p.z.hand)
        self.assertIn(targets[-1], other.z.battle)
        m.verify()

    def test_prefix_handler_cannot_overwrite_existing_statuses(self):
        m, p, other, old_source, targets = self.prepare('BT24-034')
        for card in ('EX12-026', 'BT26-013'):
            with self.subTest(card=card):
                source = take(p, card)
                p.z.hand.append(source)
                m.selected_main_card = source
                status = {'dp_delta': 3000, 'cant_suspend': True,
                          'expires': 'end_of_affected_player_next_turn'}
                other.z.statuses[targets[-1].key()] = dict(status)
                with self.assertRaisesRegex(JudgeHalt, 'PREFIX_HANDLER_STATUS_UNSUPPORTED'):
                    m.hard_play(p)
                self.assertEqual(other.z.statuses[targets[-1].key()], status)
                self.assertIn(source, p.z.hand)
                self.assertIn(targets[-1], other.z.battle)
                m.verify()


if __name__ == '__main__':
    unittest.main()
