"""A new imported context must select its own pinned rules document."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from context_runtime import ContextRuntime
from match_context import CardDefinition, DeckDefinition, MatchContext
from match_preparation import begin_preparation
from match_preparation import choose_redraw
from phase_flow import advance_phase


ROOT = Path(__file__).resolve().parents[1]


def context_with_rules(source):
    raw = json.loads((ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json').read_bytes())['context']
    rules = {**raw['rules'], 'official_source': source}
    return MatchContext.create(DeckDefinition.from_dict(raw['decks']['A']),
        DeckDefinition.from_dict(raw['decks']['B']),
        {number: CardDefinition.from_dict(card) for number, card in raw['cards'].items()}, rules)


class RulesEvidenceTests(unittest.TestCase):
    def test_current_v44_manual_updates_all_phase_receipt_locators(self):
        source = {'url': 'https://world.digimoncard.com/rule/pdf/general_rule.pdf?20261120=',
                  'file': 'RULES/official/general_rule_v4.4_20261120.pdf',
                  'sha256': '4c1c601dd9309772a4c97285f443e0c72065246bd4198931c5c06cd3fb0913c1'}
        context = context_with_rules(source)
        runtime = ContextRuntime(context, 7, 'A', allow_experimental=True)
        opening = begin_preparation(runtime, ROOT)
        self.assertTrue(opening['rules_source']['locator'].startswith('Comprehensive rules v4.4:'))
        choose_redraw(runtime, 'A', False, ROOT)
        choose_redraw(runtime, 'B', False, ROOT)
        phase = advance_phase(runtime, 'A', ROOT)
        self.assertTrue(phase['rules_source']['locator'].startswith('Comprehensive rules v4.4:'))

    def test_opening_uses_rules_file_selected_by_imported_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_file = root / 'RULES' / 'custom' / 'manual.pdf'
            source_file.parent.mkdir(parents=True)
            body = b'controlled alternate official-rules fixture\n'
            source_file.write_bytes(body)
            source = {'url': 'https://world.digimoncard.com/rule/pdf/general_rule.pdf',
                      'file': 'RULES/custom/manual.pdf',
                      'sha256': hashlib.sha256(body).hexdigest(),
                      'locator': 'controlled test locator'}
            context = context_with_rules(source)
            runtime = ContextRuntime(context, 7, 'A', allow_experimental=True)
            result = begin_preparation(runtime, root)
            self.assertEqual(result['rules_source']['sha256'], source['sha256'])
            self.assertEqual(result['rules_source']['url'], source['url'])

            source_file.write_bytes(body + b'changed')
            second = ContextRuntime(context, 7, 'A', allow_experimental=True)
            with self.assertRaisesRegex(ValueError, 'Official source hash mismatch'):
                begin_preparation(second, root)
            self.assertEqual(second.state.phase, 'SCENARIO')


if __name__ == '__main__':
    unittest.main()
