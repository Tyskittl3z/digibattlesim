"""Strict judging stops unsupported actions before they change a live game."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from fresh_learning_campaign import replay_game, run_game
from interaction_learning import LearningState
from match_context import CardDefinition, DeckDefinition, MatchContext
from match_preparation import begin_preparation, choose_redraw


ROOT = Path(__file__).resolve().parents[1]
INDEX = json.loads((ROOT / 'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json').read_bytes())
RULES_SOURCE = next(item for item in INDEX['sources'] if item['id'] == 'rules')


def selected_context():
    raw = json.loads((ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json').read_bytes())['context']
    raw['rules']['official_source'] = {key: RULES_SOURCE[key] for key in ('url', 'file', 'sha256')}
    return MatchContext.create(DeckDefinition.from_dict(raw['decks']['A']),
        DeckDefinition.from_dict(raw['decks']['B']),
        {number: CardDefinition.from_dict(card) for number, card in raw['cards'].items()}, raw['rules'])


class SemanticGateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('semantic_gate'))
        module = importlib.import_module('semantic_gate')
        self.checked_trial = module.checked_trial
        self.context = selected_context()
        self.runtime = ContextRuntime(self.context, 7, 'A', allow_experimental=True)
        self.gate = module.SemanticGate(self.context, ROOT)

    def test_unknown_action_halts_before_live_state_changes(self):
        before = self.runtime.snapshot()
        command = {'command': 'PLAY_CARD', 'seat': 'A', 'args': {'hand_key': 'A:BT11-023#1'}}
        with self.assertRaisesRegex(RuntimeHalt, 'RULE_CHECK_NOT_INSTALLED: PLAY_CARD'):
            self.checked_trial(self.runtime, self.gate, command,
                          lambda trial: self.fail('Engine ran before rule check'))
        self.assertEqual(self.runtime.snapshot(), before)

    def test_opening_checker_validates_a_trial_without_committing_it(self):
        before = self.runtime.snapshot()
        command = {'command': 'BEGIN_PREPARATION', 'seat': 'A', 'args': {}}
        trial, result, receipt = self.checked_trial(self.runtime, self.gate, command,
                                                lambda candidate: begin_preparation(candidate, ROOT))
        self.assertEqual(self.runtime.snapshot(), before)
        self.assertEqual(trial.state.phase, 'INITIAL_HANDS')
        self.assertEqual(result['initial_hands'], {'A': 5, 'B': 5})
        self.assertEqual(receipt['status'], 'ALGORITHM_CHECK_PASSED')
        self.assertEqual(receipt['rules_source']['sha256'], RULES_SOURCE['sha256'])
        self.assertFalse(receipt['independent_rules_certification'])

    def test_bad_trial_transition_is_rejected_without_live_mutation(self):
        before = self.runtime.snapshot()
        command = {'command': 'BEGIN_PREPARATION', 'seat': 'A', 'args': {}}

        def wrong(candidate):
            result = begin_preparation(candidate, ROOT)
            candidate.state.memory = 1
            return result

        with self.assertRaisesRegex(RuntimeHalt, 'RULE_TRANSITION_MISMATCH'):
            self.checked_trial(self.runtime, self.gate, command, wrong)
        self.assertEqual(self.runtime.snapshot(), before)

    def test_redraw_shuffles_on_a_trial_and_preserves_the_live_game(self):
        opening = {'command': 'BEGIN_PREPARATION', 'seat': 'A', 'args': {}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, opening,
                                                 lambda candidate: begin_preparation(candidate, ROOT))
        before = self.runtime.snapshot()
        redraw = {'command': 'REDRAW_CHOICE', 'seat': 'A', 'args': {'redraw': True}}
        trial, result, receipt = self.checked_trial(self.runtime, self.gate, redraw,
            lambda candidate: choose_redraw(candidate, 'A', True, ROOT))
        self.assertEqual(self.runtime.snapshot(), before)
        self.assertEqual(trial.state.preparation['choices'], [{'seat': 'A', 'redraw': True}])
        self.assertEqual(result['phase'], 'INITIAL_HANDS')
        self.assertEqual(receipt['status'], 'ALGORITHM_CHECK_PASSED')
        self.assertNotEqual(trial.snapshot()['rng_state'], before['rng_state'])

    def test_strict_runner_preserves_unknown_action_and_replays_exactly(self):
        context = self.context.to_dict()
        bundle = {'context': context, 'matchup_id': self.context.matchup_id}
        with tempfile.NamedTemporaryFile('w', suffix='.json', prefix='strict-context-',
                                         dir=ROOT / 'ARTIFACTS') as stream:
            json.dump(bundle, stream)
            stream.flush()
            relative = str(Path(stream.name).relative_to(ROOT))
            record = run_game(0, ROOT, context_file=relative, campaign_id='STRICT_TEST',
                learning_state=LearningState(), max_commands=8,
                player_policy='BOARD_TEXT_HISTORY_STYLED', rules_mode='STRICT')
            self.assertEqual(record['status'], 'HALT')
            self.assertIn('RULE_CHECK_NOT_INSTALLED', record['halt_reason'])
            self.assertEqual(record['commands'][-1]['before'], record['commands'][-1]['after'])
            self.assertEqual(record['commands'][-1]['judge']['status'], 'SOFTWARE_GAP')
            self.assertEqual(record['rules_mode'], 'STRICT')
            self.assertTrue(replay_game(copy.deepcopy(record), ROOT)['exact_match'])


if __name__ == '__main__':
    unittest.main()
