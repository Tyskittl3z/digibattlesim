import copy
import json
from pathlib import Path
import tempfile
import unittest

from matchup_readiness import load_context_file, inspect_readiness
from selected_mechanics import build_selected_registry
from match_context import MatchContext

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT/'ARTIFACTS/ex13-engine-2026-10-30/context.json'


class ReadinessTests(unittest.TestCase):
    def test_real_pair_never_reuses_legacy_matches_or_claims_readiness(self):
        c = load_context_file(CONTEXT)
        r = inspect_readiness(c, build_selected_registry(c, ROOT), ROOT)
        self.assertEqual(r['status'], 'BLOCKED')
        self.assertEqual(r['counts']['distinct_cards'], 45)
        self.assertEqual(r['counts']['main_cards'], {'A': 50, 'B': 50})
        self.assertEqual(r['counts']['digi_eggs'], {'A': 4, 'B': 4})
        self.assertEqual(r['counts']['judge_valid_fact_finding_matches'], 0)
        self.assertEqual(r['counts']['final_matches'], 0)
        self.assertEqual(r['counts']['software_only_mechanic_bindings'], 14)
        inherited = [e for e in r['printed_text_inventory'] if e['field']=='inherited_text' and e['software_handler']]
        self.assertEqual({e['card_number'] for e in inherited},{'EX13-022','BT22-023','P-138','EX1-013'})
        phase_handlers={e['software_handler'] for e in r['printed_text_inventory'] if e['software_handler'] and 'start_' in e['software_handler']}
        self.assertEqual(phase_handlers,{'BT22-085.start_turn_memory','BT19-080.start_turn_memory','BT19-007.start_main_memory','EX13-069.start_main_memory'})
        search_handlers={e['software_handler'] for e in r['printed_text_inventory'] if e['software_handler'] and 'on_play_search' in e['software_handler']}
        self.assertEqual(search_handlers,{'BT11-023.on_play_search','P-138.on_play_search','EX2-008.on_play_search',
                                          'EX13-017.on_play_search','EX8-009.on_play_search'})
        self.assertTrue(any(b['code'] == 'FULL_MATCH_ENGINE_UNIMPLEMENTED' for b in r['blockers']))
        self.assertFalse(any(b['code'] == 'REGION_UNSELECTED' for b in r['blockers']))
        self.assertEqual(c.to_dict()['rules']['region'], 'English-version worldwide rules')
        self.assertTrue(any(e['card_number'] == 'EX13-023' and e['software_handler']
                            for e in r['printed_text_inventory']))
        self.assertGreater(r['counts']['unsupported_printed_text_units'], 100)

    def test_context_tampering_or_missing_definition_is_rejected(self):
        raw = json.loads(CONTEXT.read_bytes())
        for mutation in ('quantity', 'text', 'id', 'missing'):
            bad = copy.deepcopy(raw)
            if mutation == 'quantity': bad['context']['decks']['A']['eggs'][0]['quantity'] = 3
            if mutation == 'text': bad['context']['cards']['EX13-023']['main_text'] += ' fake'
            if mutation == 'id': bad['matchup_id'] = '0'*64
            if mutation == 'missing': del bad['context']['cards']['EX13-023']
            with tempfile.TemporaryDirectory() as d:
                p = Path(d)/'context.json'; p.write_text(json.dumps(bad))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    load_context_file(p)

    def test_missing_official_source_stays_a_blocker_not_a_success(self):
        c = load_context_file(CONTEXT)
        # Registry built from real sources; checking another empty root must
        # not bless those references without inspecting the local source bytes.
        with tempfile.TemporaryDirectory() as d:
            report = inspect_readiness(c, build_selected_registry(c, ROOT), Path(d))
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertTrue(any(b['code'] == 'OFFICIAL_SOURCE_UNAVAILABLE' for b in report['blockers']))

    def test_missing_region_blocks_even_with_exact_decks(self):
        c = load_context_file(CONTEXT)
        rules = c.to_dict()['rules']; rules['region'] = None
        provisional = MatchContext.create(c.deck_a,c.deck_b,{x.number:x for x in c.cards},rules)
        report = inspect_readiness(provisional,build_selected_registry(provisional,ROOT),ROOT)
        self.assertNotEqual(provisional.matchup_id,c.matchup_id)
        self.assertTrue(any(b['code']=='REGION_UNSELECTED' for b in report['blockers']))


if __name__ == '__main__':
    unittest.main()
