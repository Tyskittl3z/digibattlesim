import unittest

from printed_triggers import effect_headers,trigger_lines
from test_selected_mechanics import selected_context


class PrintedTriggerTests(unittest.TestCase):
    def test_only_leading_labels_trigger_an_effect(self):
        line='[All Turns] When this Digimon suspends, activate 1 [When Digivolving] effect.'
        self.assertEqual(effect_headers(line),('All Turns',))
        self.assertEqual(trigger_lines(line,'When Digivolving'),())
        self.assertEqual(effect_headers('[On Play] [When Digivolving] ＜Draw 1＞.'),('On Play','When Digivolving'))

    def test_ordinary_play_does_not_trigger_printed_digivolving_or_attacking_effect(self):
        c=selected_context()
        for seat,number in [('A','EX13-019'),('B','BT12-016'),('B','EX8-012')]:
            text=c.card(seat,number).effect_text('main_text')
            self.assertEqual(trigger_lines(text,'On Play'),())
        self.assertEqual(len(trigger_lines(c.card('A','EX13-017').effect_text('main_text'),'On Play')),1)


if __name__=='__main__':unittest.main()
