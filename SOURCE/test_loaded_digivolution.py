import unittest
from loaded_digivolution import BY_SEAT, legal_printed_evolutions, UnsupportedPrintedCondition

class LoadedCardEvolutionTests(unittest.TestCase):
    def cost(self,seat,a,b,s=5):
        routes=legal_printed_evolutions(seat,a,b,security_count=s)
        return routes[0].cost if routes else None

    def test_exact_card_pool(self):
        self.assertEqual((len(BY_SEAT['A']),len(BY_SEAT['B'])),(20,21))
        self.assertEqual(len(set(BY_SEAT['A'])|set(BY_SEAT['B'])),41)

    def test_egg_to_rookie_a(self):
        for c in ('BT24-031','BT25-022','BT25-030'):
            with self.subTest(c=c):self.assertEqual(self.cost('A','BT24-003',c),0)

    def test_egg_to_rookie_b(self):
        for c in ('EX12-009','EX12-020','EX12-061'):
            with self.subTest(c=c):self.assertEqual(self.cost('B','EX12-004',c),0)

    def test_jupiter_line(self):
        self.assertEqual(self.cost('A','BT24-031','BT24-034'),2)
        self.assertEqual(self.cost('A','BT24-034','BT26-029'),3)
        self.assertEqual(self.cost('A','BT26-029','BT24-101',s=3),3)
        self.assertEqual(self.cost('A','BT26-029','BT24-101',s=1),1)
        self.assertEqual(self.cost('A','BT26-029','BT24-101',s=0),0)
        self.assertEqual(self.cost('A','BT26-029','BT26-033',s=3),4)
        self.assertEqual(self.cost('A','BT26-033','BT26-103'),5)

    def test_toho_line(self):
        self.assertEqual(self.cost('B','EX12-009','EX12-026'),2)
        self.assertEqual(self.cost('B','EX12-026','EX12-046'),3)
        self.assertEqual(self.cost('B','EX12-046','EX12-047'),3)
        self.assertEqual(self.cost('B','EX12-047','EX12-076'),5)
        self.assertEqual(self.cost('B','EX12-061','EX12-062'),2)
        self.assertEqual(self.cost('B','EX12-062','EX12-063'),3)
        self.assertEqual(self.cost('B','EX12-063','EX12-065'),3)

    def test_negative(self):
        self.assertIsNone(self.cost('A','BT24-003','BT26-103'))
        self.assertIsNone(self.cost('B','EX12-004','EX12-047'))
        self.assertIsNone(self.cost('B','EX12-047','EX12-026'))
        with self.assertRaises(ValueError):
            legal_printed_evolutions('A','EX12-004','BT24-031')

    def test_known_route_scores_keep_printed_option(self):
        r=legal_printed_evolutions('B','EX12-009','BT26-012')
        self.assertEqual([(x.cost,x.source) for x in r],[(2,'printed_special'),(3,'printed_regular')])

    def test_unparsed_future_syntax_fails_closed(self):
        from loaded_digivolution import special_options
        target=dict(BY_SEAT['A']['BT24-031'])
        target['card_text']='[Digivolve] Any player can evolve: Cost ?'
        with self.assertRaises(UnsupportedPrintedCondition):
            special_options(BY_SEAT['A']['BT24-003'],target,5)

if __name__=='__main__': unittest.main()
