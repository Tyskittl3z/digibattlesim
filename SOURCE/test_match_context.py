"""Context regressions: new decks cannot inherit old identities or mutable data."""
import copy
import unittest

from match_context import CardDefinition, DeckDefinition, MatchContext


def fixture(eggs=4):
    cards = {}
    for prefix in ('A', 'B'):
        for i in range(13):
            key = f'{prefix}T1-{i:03}'
            cards[key] = CardDefinition.from_dict({
                'card_number': key, 'name': key, 'type': 'Digimon', 'level': 3,
                'colors': ['Blue'], 'play_cost': 3, 'dp': 1000,
                'main_text': '', 'inherited_text': '', 'security_text': '',
            })
        key = f'{prefix}T1-099'
        cards[key] = CardDefinition.from_dict({
            'card_number': key, 'name': key, 'type': 'Digi-Egg', 'level': 2,
            'colors': ['Blue'], 'main_text': '', 'inherited_text': '', 'security_text': '',
        })
    decks = [DeckDefinition.from_dict({
        'label': prefix, 'source_id': prefix,
        'main': [{'card_number': f'{prefix}T1-{i:03}', 'quantity': 4 if i < 12 else 2}
                 for i in range(13)],
        'eggs': [{'card_number': f'{prefix}T1-099', 'quantity': eggs}] if eggs else [],
    }) for prefix in ('A', 'B')]
    if not eggs:
        cards = {k: v for k, v in cards.items() if not k.endswith('-099')}
    rules = {'name': 'EX13', 'region': None, 'language': 'English', 'as_of_date': '2026-10-30'}
    return decks, cards, rules


class ContextTests(unittest.TestCase):
    def test_new_context_has_exact_seated_inventory(self):
        decks, cards, rules = fixture()
        context = MatchContext.create(*decks, cards, rules)
        self.assertEqual(len(context.inventory('A')), 54)
        self.assertEqual(len(context.inventory('B')), 54)
        self.assertIn(('AT1-000', 4), context.inventory('A'))
        with self.assertRaisesRegex(ValueError, 'not in seated deck'):
            context.card('A', 'BT1-000')

    def test_egg_composition_is_part_of_identity(self):
        d, c, r = fixture(4)
        four = MatchContext.create(*d, c, r)
        d, c, r = fixture(3)
        three = MatchContext.create(*d, c, r)
        self.assertNotEqual(four.matchup_id, three.matchup_id)
        self.assertEqual(len(three.inventory('A')), 53)
        d, c, r = fixture(0)
        self.assertEqual(len(MatchContext.create(*d, c, r).inventory('A')), 50)

    def test_order_is_normalized_but_seats_and_rules_are_bound(self):
        d, c, r = fixture()
        one = MatchContext.create(*d, c, r)
        two = MatchContext.create(*d, dict(reversed(list(c.items()))), r)
        self.assertEqual(one.matchup_id, two.matchup_id)
        self.assertNotEqual(one.matchup_id, MatchContext.create(d[1], d[0], c, r).matchup_id)
        r['region'] = 'Worldwide'
        self.assertNotEqual(one.matchup_id, MatchContext.create(*d, c, r).matchup_id)

    def test_caller_mutation_cannot_change_frozen_context(self):
        d, c, r = fixture()
        context = MatchContext.create(*d, c, r)
        original = context.matchup_id
        r['language'] = 'Japanese'
        c.clear()
        exported = context.to_dict()
        exported['rules']['language'] = 'Japanese'
        exported['cards'].clear()
        self.assertEqual(context.to_dict()['rules']['language'], 'English')
        self.assertEqual(context.matchup_id, original)
        self.assertEqual(context.card('A', 'AT1-000').name, 'AT1-000')

    def test_text_change_invalidates_context(self):
        d, c, r = fixture()
        one = MatchContext.create(*d, c, r)
        data = c['AT1-000'].to_dict()
        data['main_text'] = '[On Play] Draw 1.'
        c['AT1-000'] = CardDefinition.from_dict(data)
        self.assertNotEqual(one.matchup_id, MatchContext.create(*d, c, r).matchup_id)

    def test_missing_or_wrong_zone_definition_is_rejected(self):
        d, c, r = fixture()
        del c['AT1-000']
        with self.assertRaisesRegex(ValueError, 'Missing card'):
            MatchContext.create(*d, c, r)
        d, c, r = fixture()
        data = c['AT1-099'].to_dict(); data['type'] = 'Digimon'
        c['AT1-099'] = CardDefinition.from_dict(data)
        with self.assertRaisesRegex(ValueError, 'egg zone'):
            MatchContext.create(*d, c, r)

    def test_duplicate_unknown_and_malformed_deck_entries_fail(self):
        d, c, r = fixture()
        raw = d[0].to_dict()
        for qty in [True, 0, -1, 1.5, '4']:
            bad = copy.deepcopy(raw); bad['main'][0]['quantity'] = qty
            with self.subTest(qty=qty), self.assertRaises(ValueError):
                DeckDefinition.from_dict(bad)
        raw['main'].append(raw['main'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            DeckDefinition.from_dict(raw)

    def test_effect_fields_must_be_explicit_not_silently_blank(self):
        d, c, r = fixture()
        raw = c['AT1-000'].to_dict(); del raw['main_text']
        with self.assertRaisesRegex(ValueError, 'main_text'):
            CardDefinition.from_dict(raw)


if __name__ == '__main__':
    unittest.main()
