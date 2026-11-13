import unittest
from context_evolution import printed_evolution_options, UnsupportedEvolutionCondition
from match_context import CardDefinition, MatchContext
from test_selected_mechanics import selected_context


class EvolutionTests(unittest.TestCase):
    def test_uses_official_printed_cost_instead_of_third_party_cost(self):
        c = selected_context()
        routes = printed_evolution_options(c, 'B', 'EX2-001', 'BT19-007')
        self.assertEqual([(r.cost, r.basis) for r in routes], [(0, 'PRINTED_NORMAL')])

    def test_compact_multicolor_printing_accepts_either_printed_color(self):
        c = selected_context()
        routes = printed_evolution_options(c, 'B', 'BT19-007', 'EX8-012')
        self.assertEqual([(r.cost, r.basis) for r in routes], [(3, 'PRINTED_NORMAL')])
        self.assertEqual(printed_evolution_options(c, 'A', 'BT11-023', 'EX13-023'), ())

    def test_exact_name_route_is_not_name_contains(self):
        c = selected_context()
        routes = printed_evolution_options(c, 'B', 'BT19-009', 'EX8-012')
        self.assertEqual([(r.cost, r.basis) for r in routes], [(0, 'PRINTED_SPECIAL')])
        self.assertEqual(printed_evolution_options(c, 'B', 'BT9-011', 'EX8-012'), ())

    def test_name_alternatives_and_old_printed_special_syntax(self):
        c = selected_context()
        self.assertIn((0, 'PRINTED_SPECIAL'), [(r.cost,r.basis) for r in printed_evolution_options(c,'B','EX2-001','EX8-009')])
        self.assertEqual([(r.cost,r.basis) for r in printed_evolution_options(c,'B','BT19-009','BT9-011')], [(0,'PRINTED_SPECIAL')])
        self.assertEqual([(r.cost,r.basis) for r in printed_evolution_options(c,'A','BT11-032','BT12-029')], [(1,'PRINTED_SPECIAL')])

    def test_trait_and_name_contains_conditions_respect_printed_level(self):
        c = selected_context()
        routes = printed_evolution_options(c,'A','EX13-017','EX13-019')
        self.assertEqual([(r.cost,r.basis) for r in routes], [(2,'PRINTED_NORMAL'),(2,'PRINTED_SPECIAL')])
        routes = printed_evolution_options(c,'B','BT19-011','P-186')
        self.assertEqual([(r.cost,r.basis) for r in routes], [(3,'PRINTED_SPECIAL'),(4,'PRINTED_NORMAL')])

    def test_unknown_special_condition_cannot_silently_fall_back_to_normal(self):
        c = selected_context(); cards={x.number:x for x in c.cards}
        raw=cards['EX13-019'].to_dict()
        raw['special_conditions']['[Special Digivolution Condition]']='[Digivolve] a condition not implemented: Cost 0'
        cards['EX13-019']=CardDefinition.from_dict(raw)
        changed=MatchContext.create(c.deck_a,c.deck_b,cards,c.to_dict()['rules'])
        with self.assertRaises(UnsupportedEvolutionCondition):
            printed_evolution_options(changed,'A','EX13-017','EX13-019')

    def test_wrong_seat_and_tamer_cannot_supply_evolution_base(self):
        c=selected_context()
        with self.assertRaisesRegex(ValueError,'not in seated deck'):
            printed_evolution_options(c,'A','EX2-001','BT19-007')
        self.assertEqual(printed_evolution_options(c,'A','BT11-112','EX13-019'),())


if __name__=='__main__':unittest.main()
