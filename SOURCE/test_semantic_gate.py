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
from phase_flow import advance_phase, choose_breeding_action
from breeding_evolution import choose_breeding_evolution
from turn_flow import pass_turn, finish_turn
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry


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

    def ready_first_turn(self):
        opening = {'command': 'BEGIN_PREPARATION', 'seat': 'A', 'args': {}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, opening,
            lambda candidate: begin_preparation(candidate, ROOT))
        for seat in ('A', 'B'):
            redraw = {'command': 'REDRAW_CHOICE', 'seat': seat, 'args': {'redraw': False}}
            self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, redraw,
                lambda candidate, seat=seat: choose_redraw(candidate, seat, False, ROOT))

    def advance(self):
        command = {'command': 'ADVANCE_PHASE', 'seat': 'A', 'args': {}}
        self.runtime, result, receipt = self.checked_trial(self.runtime, self.gate, command,
            lambda candidate: advance_phase(candidate, 'A', ROOT))
        return result, receipt

    def test_ordinary_first_turn_phases_and_hatch_are_checked(self):
        self.ready_first_turn()
        self.assertEqual(self.runtime.state.phase, 'START_OF_TURN')
        for phase in ('TURN_START_EFFECTS', 'DRAW', 'BREEDING'):
            result, receipt = self.advance()
            self.assertEqual(result['phase'], phase)
            self.assertEqual(receipt['status'], 'ALGORITHM_CHECK_PASSED')
        hand_before = len(self.runtime.state.zones['A']['hand'])
        self.assertEqual(len(self.runtime.state.zones['A']['hand']), hand_before)
        egg_count = len(self.runtime.state.zones['A']['eggdeck'])
        command = {'command': 'BREEDING_CHOICE', 'seat': 'A', 'args': {'action': 'hatch'}}
        self.runtime, result, receipt = self.checked_trial(self.runtime, self.gate, command,
            lambda candidate: choose_breeding_action(candidate, 'A', 'hatch', ROOT))
        self.assertEqual(result['phase'], 'MAIN')
        self.assertEqual(len(self.runtime.state.zones['A']['eggdeck']), egg_count - 1)
        self.assertEqual(len(self.runtime.state.breeding['A']), 1)
        self.assertEqual(receipt['checker'], 'BREEDING_CHOICE')

    def test_phase_checker_rejects_unknown_pending_before_trial(self):
        self.ready_first_turn()
        self.runtime.state.pending.append({'id': 'unknown-effect'})
        before = self.runtime.snapshot()
        command = {'command': 'ADVANCE_PHASE', 'seat': 'A', 'args': {}}
        with self.assertRaisesRegex(RuntimeHalt, 'RULE_PHASE_PENDING_UNREVIEWED'):
            self.checked_trial(self.runtime, self.gate, command,
                lambda candidate: self.fail('Engine ran before rule check'))
        self.assertEqual(self.runtime.snapshot(), before)

    def test_printed_breeding_digivolution_checks_cost_stack_and_draw(self):
        self.ready_first_turn()
        for _ in range(3):
            self.advance()
        hatch = {'command': 'BREEDING_CHOICE', 'seat': 'A', 'args': {'action': 'hatch'}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, hatch,
            lambda candidate: choose_breeding_action(candidate, 'A', 'hatch', ROOT))
        hand_key = next(card.key for card in self.runtime.state.zones['A']['hand']
                        if card.card_number == 'BT11-023')
        before = self.runtime.snapshot()
        command = {'command': 'BREEDING_EVOLUTION', 'seat': 'A',
                   'args': {'hand_key': hand_key, 'route_index': 0}}
        self.runtime, result, receipt = self.checked_trial(self.runtime, self.gate, command,
            lambda candidate: choose_breeding_evolution(candidate, 'A', hand_key, 0, ROOT))
        self.assertEqual(result['cost'], 0)
        self.assertEqual(len(self.runtime.state.breeding['A']), 2)
        self.assertEqual(len(self.runtime.state.zones['A']['deck']),
                         len(before['state']['zones']['A']['deck']) - 1)
        self.assertEqual(receipt['checker'], 'BREEDING_EVOLUTION')

    def test_breeding_digivolution_rejects_wrong_candidate_cost(self):
        self.ready_first_turn()
        for _ in range(3):
            self.advance()
        hatch = {'command': 'BREEDING_CHOICE', 'seat': 'A', 'args': {'action': 'hatch'}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, hatch,
            lambda candidate: choose_breeding_action(candidate, 'A', 'hatch', ROOT))
        hand_key = next(card.key for card in self.runtime.state.zones['A']['hand']
                        if card.card_number == 'BT11-023')
        before = self.runtime.snapshot()
        command = {'command': 'BREEDING_EVOLUTION', 'seat': 'A',
                   'args': {'hand_key': hand_key, 'route_index': 0, 'cost': 7}}
        with self.assertRaisesRegex(RuntimeHalt, 'RULE_PRINTED_ROUTE_MISMATCH'):
            self.checked_trial(self.runtime, self.gate, command,
                lambda candidate: self.fail('Engine ran before rule check'))
        self.assertEqual(self.runtime.snapshot(), before)

    def test_normal_route_remains_available_when_special_predicate_does_not_match(self):
        self.ready_first_turn()
        for _ in range(3):
            self.advance()
        hatch = {'command': 'BREEDING_CHOICE', 'seat': 'A', 'args': {'action': 'hatch'}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, hatch,
            lambda candidate: choose_breeding_action(candidate, 'A', 'hatch', ROOT))
        rookie = next(card.key for card in self.runtime.state.zones['A']['hand']
                      if card.card_number == 'BT11-023')
        evolve = {'command': 'BREEDING_EVOLUTION', 'seat': 'A',
                  'args': {'hand_key': rookie, 'route_index': 0}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, evolve,
            lambda candidate: choose_breeding_evolution(candidate, 'A', rookie, 0, ROOT))
        champion = next(card.key for card in self.runtime.state.zones['A']['hand']
                        if card.card_number == 'EX13-019')
        evolve['args'] = {'hand_key': champion, 'route_index': 0}
        self.runtime, result, _ = self.checked_trial(self.runtime, self.gate, evolve,
            lambda candidate: choose_breeding_evolution(candidate, 'A', champion, 0, ROOT))
        self.assertEqual(result['route']['basis'], 'PRINTED_NORMAL')
        self.assertEqual(result['cost'], 2)

    def test_plain_pass_and_finish_turn_switch_player_and_memory(self):
        self.ready_first_turn()
        for _ in range(3):
            self.advance()
        skip = {'command': 'BREEDING_CHOICE', 'seat': 'A', 'args': {'action': 'skip'}}
        self.runtime, _, _ = self.checked_trial(self.runtime, self.gate, skip,
            lambda candidate: choose_breeding_action(candidate, 'A', 'skip', ROOT))
        passing = {'command': 'PASS_TURN', 'seat': 'A', 'args': {}}
        self.runtime, result, receipt = self.checked_trial(self.runtime, self.gate, passing,
            lambda candidate: pass_turn(candidate, 'A', ROOT))
        self.assertEqual(result['memory_after'], -3)
        self.assertEqual(receipt['checker'], 'PASS_TURN')
        finishing = {'command': 'FINISH_TURN', 'seat': 'A', 'args': {}}
        self.runtime, result, receipt = self.checked_trial(self.runtime, self.gate, finishing,
            lambda candidate: finish_turn(candidate, 'A', ROOT))
        self.assertEqual(result['next_controller'], 'B')
        self.assertEqual(self.runtime.state.memory, 3)
        self.assertEqual(self.runtime.state.turn, 2)
        self.assertEqual(receipt['checker'], 'FINISH_TURN')

    def test_encountered_ex13_017_play_queues_its_search_without_resolving_it(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-route.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        gate = importlib.import_module('semantic_gate').SemanticGate(context, ROOT)
        command = {k: record['commands'][-1][k] for k in ('command', 'seat', 'args')}
        before = runtime.snapshot()
        trial, result, receipt = self.checked_trial(runtime, gate, command,
            lambda candidate: _apply(candidate, command['command'], command['seat'],
                                     command['args'], ROOT))
        self.assertEqual(runtime.snapshot(), before)
        self.assertEqual(result['played_card'], 'B:EX13-017#2')
        self.assertEqual(result['triggered_effects'], ['EX13-017.on_play_search'])
        self.assertEqual(trial.state.pending[0]['effect_id'], 'EX13-017.on_play_search')
        self.assertEqual(receipt['checker'], 'PLAY_CARD')

    def test_encountered_search_resolution_checks_selection_and_deck_order(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-route.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        play = record['commands'][-1]
        _apply(runtime, play['command'], play['seat'], play['args'], ROOT)
        pending = runtime.state.pending[0]
        gate = importlib.import_module('semantic_gate').SemanticGate(context, ROOT)
        revealed = list(reversed(runtime.snapshot()['state']['zones']['B']['deck'][-3:]))
        selected = [key for key in revealed if key.startswith('B:BT22-023')]
        choice = {'selected': selected, 'bottom_order': [key for key in revealed if key not in selected]}
        command = {'command': 'RESOLVE_PENDING', 'seat': 'B',
                   'args': {'pending_id': pending['id'], 'choice': choice}}
        before = runtime.snapshot()
        trial, result, receipt = self.checked_trial(runtime, gate, command,
            lambda candidate: _apply(candidate, 'RESOLVE_PENDING', 'B', command['args'], ROOT))
        self.assertEqual(runtime.snapshot(), before)
        self.assertEqual(result['selected'], selected)
        self.assertEqual(trial.state.phase, 'END_OF_TURN')
        self.assertEqual(trial.state.pending, [])
        self.assertEqual(receipt['checker'], 'RESOLVE_PENDING')

        wrong = copy.deepcopy(command)
        wrong['args']['choice']['selected'] = [revealed[0]]
        wrong['args']['choice']['bottom_order'] = revealed[1:]
        with self.assertRaisesRegex(RuntimeHalt, 'RULE_SEARCH_SELECTION_INVALID'):
            self.checked_trial(runtime, gate, wrong,
                lambda candidate: self.fail('Engine ran before rule check'))
        self.assertEqual(runtime.snapshot(), before)

    def test_encountered_breeding_promotion_moves_the_whole_stack(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-search.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        gate = importlib.import_module('semantic_gate').SemanticGate(context, ROOT)
        command = {k: record['commands'][-1][k] for k in ('command', 'seat', 'args')}
        stack_before = list(runtime.state.breeding['A'])
        trial, result, receipt = self.checked_trial(runtime, gate, command,
            lambda candidate: _apply(candidate, 'BREEDING_CHOICE', 'A', command['args'], ROOT))
        self.assertEqual(result['phase'], 'MAIN')
        self.assertEqual(runtime.state.breeding['A'], stack_before)
        self.assertEqual(trial.state.breeding['A'], [])
        self.assertEqual([c.key for c in trial.state.battle['A'][stack_before[-1].key].cards],
                         [c.key for c in stack_before])
        self.assertEqual(receipt['checker'], 'BREEDING_CHOICE')

    def test_encountered_attack_declaration_suspends_and_queues_printed_trigger(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-promotion.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        gate = importlib.import_module('semantic_gate').SemanticGate(context, ROOT)
        command = {k: record['commands'][-1][k] for k in ('command', 'seat', 'args')}
        before = runtime.snapshot()
        trial, result, receipt = self.checked_trial(runtime, gate, command,
            lambda candidate: _apply(candidate, 'DECLARE_ATTACK', 'A', command['args'], ROOT))
        self.assertEqual(runtime.snapshot(), before)
        self.assertEqual(result['window'], 'COUNTER')
        self.assertEqual(result['triggered_effects'], ['EX13-019.attack_play_tamer'])
        self.assertTrue(trial.state.battle['A'][command['args']['attacker']].suspended)
        self.assertEqual(trial.state.attack['target'], 'PLAYER')
        self.assertEqual(receipt['checker'], 'DECLARE_ATTACK')

    def test_nested_tamer_play_uses_current_manual_locator(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-attack-gap.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        last = record['commands'][-1]
        result = _apply(runtime, last['command'], last['seat'], last['args'], ROOT)
        self.assertTrue(result['play']['rules_source']['locator'].startswith('Comprehensive rules v4.4:'))

    def test_encountered_attack_tamer_play_checks_cost_and_child_triggers(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-attack-gap.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        gate = importlib.import_module('semantic_gate').SemanticGate(context, ROOT)
        command = {k: record['commands'][-1][k] for k in ('command', 'seat', 'args')}
        before = runtime.snapshot()
        trial, result, receipt = self.checked_trial(runtime, gate, command,
            lambda candidate: _apply(candidate, 'RESOLVE_PENDING', 'A', command['args'], ROOT))
        self.assertEqual(runtime.snapshot(), before)
        self.assertEqual(result['play']['cost'], 1)
        self.assertEqual(result['play']['rules_source']['locator'].split(':', 1)[0],
                         'Comprehensive rules v4.4')
        self.assertEqual(result['play']['triggered_effects'],
                         ['BT11-112.on_play_grant', 'EX13-002.tamer_play_unsuspend'])
        self.assertEqual(trial.state.memory, 2)
        self.assertEqual([item['effect_id'] for item in trial.state.pending],
                         ['BT11-112.on_play_grant', 'EX13-002.tamer_play_unsuspend'])
        self.assertEqual(receipt['checker'], 'RESOLVE_PENDING')

        wrong = copy.deepcopy(command)
        wrong['args']['choice'] = 'A:EX13-017#2'
        with self.assertRaisesRegex(RuntimeHalt, 'RULE_TAMER_CHOICE_INVALID'):
            self.checked_trial(runtime, gate, wrong,
                lambda candidate: self.fail('Engine ran before rule check'))
        self.assertEqual(runtime.snapshot(), before)

    def test_parallel_child_effect_halt_names_selected_effect(self):
        path = ROOT / 'ARTIFACTS/strict-probe-2026-11-24'
        record = json.loads((path / 'game-0000-after-tamer-play.json').read_bytes())
        context = load_context_file(path / 'context.json')
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for saved in record['commands'][:-1]:
            _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        gate = importlib.import_module('semantic_gate').SemanticGate(context, ROOT)
        command = {k: record['commands'][-1][k] for k in ('command', 'seat', 'args')}
        before = runtime.snapshot()
        with self.assertRaisesRegex(RuntimeHalt,
                'RULE_EFFECT_CHECK_NOT_INSTALLED: BT11-112.on_play_grant'):
            self.checked_trial(runtime, gate, command,
                lambda candidate: self.fail('Engine ran before rule check'))
        self.assertEqual(runtime.snapshot(), before)

    def test_unknown_action_halts_before_live_state_changes(self):
        before = self.runtime.snapshot()
        command = {'command': 'USE_OPTION', 'seat': 'A', 'args': {'hand_key': 'A:LM-034#1'}}
        with self.assertRaisesRegex(RuntimeHalt, 'RULE_CHECK_NOT_INSTALLED: USE_OPTION'):
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
                learning_state=LearningState(), max_commands=30,
                player_policy='BOARD_TEXT_HISTORY_STYLED', rules_mode='STRICT')
            self.assertEqual(record['status'], 'HALT')
            self.assertTrue(record['halt_reason'].startswith('RULE_'))
            self.assertEqual(record['commands'][-1]['before'], record['commands'][-1]['after'])
            self.assertEqual(record['commands'][-1]['judge']['status'], 'SOFTWARE_GAP')
            self.assertEqual(record['rules_mode'], 'STRICT')
            self.assertTrue(replay_game(copy.deepcopy(record), ROOT)['exact_match'])


if __name__ == '__main__':
    unittest.main()
