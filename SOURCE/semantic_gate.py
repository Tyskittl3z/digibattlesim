"""Fail-closed rule checks on proposed actions, independent of engine handlers.

The installed generic checkers cover opening preparation only. Future mechanic
packs can register checkers for actual encountered actions. This code supplies
an algorithmic cross-check, not an independent human rules certification.
"""
import copy
import json
from pathlib import Path
import random

from context_runtime import RuntimeHalt
from match_context import canonical, digest
from rules_evidence import comprehensive_rules


_OPENING_LOCATOR = 'Comprehensive rules v4.3: 5-2-1-1 through 5-2-1-8'


def _tuples(value):
    if isinstance(value, list):
        return tuple(_tuples(item) for item in value)
    return value


def _opening(context, before, command, source):
    state = before['state']
    if (command['seat'] != before['first'] or state['phase'] != 'SCENARIO'
            or state['turn'] != 0 or state['memory'] != 0
            or state['preparation'] != {'started': False, 'choices': []}):
        raise RuntimeHalt('RULE_OPENING_WINDOW_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    for seat in ('A', 'B'):
        zones = state['zones'][seat]
        if (len(zones['deck']) != 50 or zones['hand'] or zones['security']
                or zones['trash'] or state['battle'][seat] or state['breeding'][seat]):
            raise RuntimeHalt('RULE_OPENING_ZONES_INVALID')
        new['zones'][seat]['hand'] = list(reversed(zones['deck'][-5:]))
        new['zones'][seat]['deck'] = zones['deck'][:-5]
    new['preparation'] = {'started': True, 'choices': [], 'rules_source': source}
    new['phase'] = 'INITIAL_HANDS'
    result = {'initial_hands': {'A': 5, 'B': 5}, 'next_controller': before['first'],
              'rules_source': source, 'full_match_credit': 0}
    return expected, result


def _redraw(context, before, command, source):
    state = before['state']
    args = command['args']
    choices = state['preparation'].get('choices', [])
    order = [before['first'], 'B' if before['first'] == 'A' else 'A']
    if (state['phase'] != 'INITIAL_HANDS' or not state['preparation'].get('started')
            or state['preparation'].get('rules_source') != source
            or len(choices) >= 2 or command['seat'] != order[len(choices)]
            or type(args.get('redraw')) is not bool):
        raise RuntimeHalt('RULE_REDRAW_WINDOW_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    seat = command['seat']
    if args['redraw']:
        rng = random.Random()
        rng.setstate(_tuples(before['rng_state']))
        zones = new['zones'][seat]
        zones['deck'].extend(zones['hand'])
        zones['hand'] = []
        rng.shuffle(zones['deck'])
        for _ in range(5):
            zones['hand'].append(zones['deck'].pop())
        expected['rng_state'] = json.loads(canonical(rng.getstate()))
    new['preparation']['choices'].append({'seat': seat, 'redraw': args['redraw']})
    if len(new['preparation']['choices']) == 2:
        for owner in ('A', 'B'):
            zones = new['zones'][owner]
            for _ in range(5):
                zones['security'].append(zones['deck'].pop())
        new['memory'] = 0
        new['turn'] = 1
        new['active'] = before['first']
        new['phase'] = 'START_OF_TURN'
    result = {'redraw': args['redraw'], 'phase': new['phase'], 'full_match_credit': 0}
    return expected, result


class SemanticGate:
    """Reusable action checker registry; absent mechanics have no verdict."""
    def __init__(self, context, root, checkers=()):
        self.context = context
        self.root = Path(root).resolve()
        self.checkers = {'BEGIN_PREPARATION': _opening, 'REDRAW_CHOICE': _redraw}
        for name, checker in checkers:
            if name in self.checkers or not callable(checker):
                raise ValueError('Duplicate or invalid semantic checker: ' + str(name))
            self.checkers[name] = checker

    def preflight(self, before, command):
        if before.get('context_id') != self.context.matchup_id:
            raise RuntimeHalt('RULE_CONTEXT_MISMATCH')
        if (not isinstance(command, dict) or not isinstance(command.get('command'), str)
                or command.get('seat') not in ('A', 'B') or not isinstance(command.get('args'), dict)):
            raise RuntimeHalt('RULE_COMMAND_SCHEMA_INVALID')
        source = self.context.to_dict()['rules'].get('official_source')
        if source is None:
            raise RuntimeHalt('RULES_SOURCE_NOT_SELECTED_FOR_STRICT_JUDGE')
        evidence = comprehensive_rules(self.context, self.root, _OPENING_LOCATOR).manifest()
        kind = command['command']
        checker = self.checkers.get(kind)
        if checker is None:
            detail = kind
            if kind == 'RESOLVE_PENDING':
                selected = next((p for p in before['state']['pending']
                    if p['id'] == command['args'].get('pending_id')), None)
                if selected is not None:
                    detail += ' effect=' + selected['effect_id'] + ' source=' + selected['source']
            elif 'hand_key' in command['args']:
                detail += ' card=' + str(command['args']['hand_key'])
            raise RuntimeHalt('RULE_CHECK_NOT_INSTALLED: ' + detail)
        expected, expected_result = checker(self.context, before, command, evidence)
        return {'checker': kind, 'source': evidence, 'before_sha256': digest(before),
                'command_sha256': digest(command), 'expected': expected,
                'expected_result': expected_result}

    def postflight(self, plan, before, command, after, result):
        if (plan['before_sha256'] != digest(before) or plan['command_sha256'] != digest(command)):
            raise RuntimeHalt('RULE_PLAN_INPUT_CHANGED')
        if canonical(after) != canonical(plan['expected']) or canonical(result) != canonical(plan['expected_result']):
            raise RuntimeHalt('RULE_TRANSITION_MISMATCH: ' + plan['checker'])
        return {'schema': 'semantic-gate-receipt-v1', 'status': 'ALGORITHM_CHECK_PASSED',
                'checker': plan['checker'], 'rules_source': plan['source'],
                'before_sha256': plan['before_sha256'], 'command_sha256': plan['command_sha256'],
                'after_sha256': digest(after), 'independent_rules_certification': False}


def checked_trial(runtime, gate, command, apply):
    """Inspect a copy; the caller commits it only after every judge accepts."""
    before = runtime.snapshot()
    plan = gate.preflight(before, command)
    trial = copy.deepcopy(runtime)
    result = apply(trial)
    receipt = gate.postflight(plan, before, command, trial.snapshot(), result)
    return trial, result, receipt
