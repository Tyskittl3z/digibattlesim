import importlib.util
from pathlib import Path
import unittest
P = Path(__file__).resolve().parents[1] / 'parse_official.py'

class CatalogTests(unittest.TestCase):
    def parser(self):
        self.assertTrue(P.exists(), 'official parser must exist')
        spec = importlib.util.spec_from_file_location('official', P)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_base_art_preserves_fields_and_ignores_alternate_text(self):
        m = self.parser()
        raw = '''<select name="category"><option value="1">Starter</option></select>
        <div class="popupCol" id="BT1-010"><li class="cardNo">BT1-010</li><li class="cardType">Digimon</li><li class="cardLv">Lv.3</li><div class="cardTitle">Agumon &amp; friend</div><dl><dt>Color</dt><dd><span>Red</span></dd></dl><dl><dt>Play Cost</dt><dd>3</dd></dl><dl><dt>[Effect]</dt><dd>[On Play] Draw 1.<br>Then stop.</dd></dl></div>
        <div class="popupCol" id="BT1-010_P1"><li class="cardNo">BT1-010</li><div class="cardTitle">Bad alternate</div></div>'''
        cards = m.parse_cards(raw)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]['name'], 'Agumon & friend')
        self.assertEqual(cards[0]['level'], 3)
        self.assertEqual(cards[0]['play_cost'], 3)
        self.assertIn('Draw 1.', cards[0]['effect'])
        self.assertEqual(m.categories(raw), {'1': 'Starter'})

    def test_current_site_cost_label_and_special_conditions(self):
        m=self.parser()
        card=m.parse_cards('<div class="popupCol" id="BT1-010"><li class="cardNo">BT1-010</li><li class="cardType">Digimon</li><div class="cardTitle">Agumon</div><dl><dt>Cost</dt><dd>3</dd></dl><dl><dt>[Special Digivolution Condition]</dt><dd>[Digivolve] Cost 0</dd></dl></div>')[0]
        self.assertEqual(card['play_cost'],3)
        self.assertEqual(card['special_conditions']['[Special Digivolution Condition]'],'[Digivolve] Cost 0')

    def test_errata_preserves_official_after_text_for_each_affected_card(self):
        m=self.parser()
        self.assertTrue(hasattr(m,'parse_errata'))
        records=m.parse_errata('<section><h4>May 15, 2026<br>BT25-057 Monarchlizamon</h4><div class="beforeCol"><b>Before</b> old</div><div class="afterCol"><b>After</b> for the turn</div></section>')
        self.assertEqual(records['BT25-057'][0]['after'],'for the turn')

    def test_hybrid_cards_and_legacy_egg_spelling_are_playable(self):
        m=self.parser()
        for typ in ['Digimon/Option','Digimon/Tamer','Digi-egg']:
            card=m.parse_cards(f'<div class="popupCol" id="BT1-010"><li class="cardNo">BT1-010</li><li class="cardType">{typ}</li><div class="cardTitle">Card</div><dl><dt>Cost</dt><dd>D</dd></dl></div>')[0]
            self.assertTrue(card['deck_card'])
            self.assertEqual(card['printed_cost'],'D')
            self.assertEqual(card['type'],'Digi-Egg' if typ=='Digi-egg' else typ)

    def test_missing_cost_and_token_stay_explicit(self):
        m = self.parser()
        cards = m.parse_cards('<div class="popupCol" id="TOKEN-001"><li class="cardNo">TOKEN-001</li><li class="cardType">Token</li><div class="cardTitle">Token</div></div>')
        self.assertIsNone(cards[0]['play_cost'])
        self.assertFalse(cards[0]['deck_card'])

    def test_alternate_only_category_can_be_pinned_without_executable_cards(self):
        m=self.parser(); self.assertTrue(m.has_card_markup('<div class="popupCol" id="BT1-010_P1"></div>'))
        self.assertFalse(m.has_card_markup('<html>Unavailable</html>'))

if __name__ == '__main__': unittest.main()

class RestrictionTests(unittest.TestCase):
    def test_current_affected_section_excludes_historical_restrictions(self):
        spec=importlib.util.spec_from_file_location('official',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertTrue(hasattr(m,'parse_restrictions'))
        raw='<h5>Restricted Cards (1)</h5><span class="num">BT1-001</span><h4>List of Currently Affected Cards</h4><h5>Banned cards</h5><span class="num">BT5-109</span><h5>Restricted Cards (1)</h5><span class="num">EX1-066</span><h5>Banned Pair</h5><div class="noticeFrame">Component A EX2-007 Component B EX7-064</div>'
        r=m.parse_restrictions(raw)
        self.assertEqual(r['limits'],{'BT5-109':0,'EX1-066':1})
        self.assertEqual(r['pairs'],[['EX2-007','EX7-064']])
