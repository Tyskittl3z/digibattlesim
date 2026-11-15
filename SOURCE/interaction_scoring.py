"""Declared immediate public-board measurements, not learned strategic ratings."""
import copy
import hashlib
import json
import math
from pathlib import Path

from context_runtime import RuntimeHalt
from field_tracker import FieldTracker
from match_context import canonical, digest


_ROOT = Path(__file__).resolve().parents[1]
_FILE = 'RULES/learning-2026-11-10/INTERACTION_CRITERIA.json'
_CRITERIA_FILE_BYTES = (_ROOT / _FILE).read_bytes()
_CRITERIA_FILE_SHA256 = hashlib.sha256(_CRITERIA_FILE_BYTES).hexdigest()
_SCORER_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_CRITERIA_BYTES = canonical(json.loads(_CRITERIA_FILE_BYTES))
CRITERIA = json.loads(_CRITERIA_BYTES)
CRITERIA_SHA256 = digest(CRITERIA)
_STACK_FIELDS = frozenset(('cards', 'suspended', 'statuses', 'instance_id', 'played_turn', 'ready_since_turn'))
_VIEW_FIELDS = frozenset(('active', 'memory', 'turn', 'phase', 'attack', 'terminal', 'winner', 'players', 'resolving_option'))
_PLAYER_FIELDS = frozenset(('hand', 'deck', 'eggdeck', 'security', 'trash', 'battle', 'breeding'))
_SPEND_COMMANDS = frozenset(('PLAY_CARD', 'USE_OPTION', 'BATTLE_EVOLUTION', 'BREEDING_EVOLUTION'))


def criteria_manifest():
    return {'criteria': json.loads(_CRITERIA_BYTES), 'criterion_sha256': CRITERIA_SHA256,
            'file': _FILE, 'file_sha256': _CRITERIA_FILE_SHA256,
            'scorer_source_sha256': _SCORER_SOURCE_SHA256,
            'binding': 'LOADED_ARTIFACTS_AT_MODULE_IMPORT',
            'strategic_approval': 'NONE', 'probability_claim': False}


def _view(view, seat, context):
    """Validate the public projection without reconstructing private contents."""
    if (not isinstance(view, dict) or set(view) != _VIEW_FIELDS
            or view['active'] not in ('A', 'B') or type(view['memory']) is not int
            or not -10 <= view['memory'] <= 10 or type(view['turn']) is not int or view['turn'] < 0
            or not isinstance(view['phase'], str) or type(view['terminal']) is not bool
            or view['winner'] not in (None, 'A', 'B')
            or not isinstance(view['players'], dict) or set(view['players']) != {'A', 'B'}):
        raise RuntimeHalt('SCORING_PUBLIC_VIEW_REQUIRED')
    validator = FieldTracker(context)
    visible, hidden_counts, entities = {'A': [], 'B': []}, {'A': 0, 'B': 0}, set()

    def remember_stack(owner, stack):
        visible[owner].extend(stack['cards'])
        identity = stack['instance_id']
        if identity:
            if identity in entities:
                raise RuntimeHalt('SCORING_PUBLIC_DUPLICATE_ENTITY')
            entities.add(identity)

    for owner, player in view['players'].items():
        if not isinstance(player, dict) or set(player) != _PLAYER_FIELDS:
            raise RuntimeHalt('SCORING_PUBLIC_PLAYER_SCHEMA')
        for zone in ('deck', 'eggdeck', 'security') + (() if owner == seat else ('hand',)):
            value = player[zone]
            if (not isinstance(value, dict) or set(value) != {'count'}
                    or type(value['count']) is not int or value['count'] < 0):
                raise RuntimeHalt('SCORING_PUBLIC_HIDDEN_ZONE: ' + zone)
            hidden_counts[owner] += value['count']
        for zone in ('trash', 'breeding') + (('hand',) if owner == seat else ()):
            if not isinstance(player[zone], list):
                raise RuntimeHalt('SCORING_PUBLIC_ZONE_SCHEMA')
            for key in player[zone]:
                validator._card(owner, key)
                visible[owner].append(key)
        if not isinstance(player['battle'], dict):
            raise RuntimeHalt('SCORING_PUBLIC_BATTLE_SCHEMA')
        for anchor, stack in player['battle'].items():
            _stack(stack, owner, validator, view['turn'], anchor)
            remember_stack(owner, stack)
    # Attack/resolving fields are already public, but reject undeclared private
    # payloads rather than copying or using them as arbitrary model features.
    attack = view['attack']
    attack_fields = {'attacker', 'attacker_instance', 'target', 'target_instance',
                     'controller', 'defender', 'window', 'counter_used', 'block_used', 'checked'}
    if attack is not None:
        if not isinstance(attack, dict) or set(attack) - attack_fields:
            raise RuntimeHalt('SCORING_PUBLIC_ATTACK_SCHEMA')
        for name, value in attack.items():
            valid = (type(value) is bool if name in ('counter_used', 'block_used') else
                     value is None or isinstance(value, str) if name == 'checked' else isinstance(value, str))
            if not valid:
                raise RuntimeHalt('SCORING_PUBLIC_ATTACK_FIELD')
    resolving = view['resolving_option']
    if resolving is not None:
        if not isinstance(resolving, dict) or set(resolving) != {'seat', 'stack'} or resolving['seat'] not in ('A', 'B'):
            raise RuntimeHalt('SCORING_PUBLIC_RESOLVING_SCHEMA')
        _stack(resolving['stack'], resolving['seat'], validator, view['turn'])
        if len(resolving['stack']['cards']) != 1:
            raise RuntimeHalt('SCORING_PUBLIC_RESOLVING_STACK')
        remember_stack(resolving['seat'], resolving['stack'])
    for owner in ('A', 'B'):
        if len(visible[owner]) != len(set(visible[owner])):
            raise RuntimeHalt('SCORING_PUBLIC_DUPLICATE_CARD')
        if len(visible[owner]) + hidden_counts[owner] != len(validator._inventory[owner]):
            raise RuntimeHalt('SCORING_PUBLIC_CARD_COUNT_MISMATCH')


def _stack(stack, owner, validator, turn, anchor=None):
    if (not isinstance(stack, dict) or set(stack) != _STACK_FIELDS
            or not isinstance(stack['cards'], list) or not stack['cards']
            or type(stack['suspended']) is not bool or not isinstance(stack['instance_id'], str)
            or not isinstance(stack['statuses'], dict)
            or any(value is not None and type(value) is not int for value in
                   (stack['played_turn'], stack['ready_since_turn']))
            or anchor is not None and stack['cards'][-1] != anchor):
        raise RuntimeHalt('SCORING_PUBLIC_STACK_SCHEMA')
    for key in stack['cards']:
        validator._card(owner, key)
    validator._public_statuses(owner, stack['statuses'], turn)


def _card(context, owner, key):
    return context.card(owner, key.split(':', 1)[1].split('#', 1)[0]).to_dict()


def _active_grants(stack, turn):
    return [r for r in stack['statuses'].get('effect_grants', [])
            if r['target_instance'] == stack['instance_id'] and r['expires']['turn'] >= turn]


def _amounts(view, context, owner):
    player = view['players'][owner]
    amount = dict.fromkeys(('security_remaining', 'battle_units', 'sources', 'levels',
        'known_dp_thousands', 'ready_cards', 'ready_blockers', 'disabled_threat', 'hand_cards', 'breeding_cards'), 0.0)
    amount['security_remaining'] = player['security']['count']
    amount['battle_units'] = len(player['battle'])
    amount['hand_cards'] = len(player['hand']) if isinstance(player['hand'], list) else player['hand']['count']
    amount['breeding_cards'] = len(player['breeding'])
    for stack in player['battle'].values():
        card = _card(context, owner, stack['cards'][-1])
        grants = _active_grants(stack, view['turn'])
        restrictions = {x for r in grants for x in r['effect'].get('restrictions', [])}
        cannot_suspend = stack['statuses'].get('cannot_suspend', False) or 'cannot_suspend' in restrictions
        disabled = cannot_suspend or (stack['suspended'] and stack['statuses'].get('cannot_unsuspend', False))
        sources = len(stack['cards']) - 1
        level = card.get('level') or 0
        dp = (card.get('dp') or 0) + sum(r['effect'].get('dp_bonus', 0) for r in grants)
        amount['sources'] += sources
        amount['levels'] += level
        amount['known_dp_thousands'] += dp / 1000
        ready = card['type'] in ('Digimon', 'Tamer') and not stack['suspended'] and not cannot_suspend
        amount['ready_cards'] += int(ready)
        blocker = any(line.strip().startswith(('＜Blocker＞', '<Blocker>')) for line in card['main_text'].splitlines())
        blocker = blocker or any('Blocker' in r['effect'].get('keywords', []) for r in grants)
        amount['ready_blockers'] += int(ready and card['type'] == 'Digimon' and blocker)
        if disabled:
            amount['disabled_threat'] += 1 + 0.5 * sources + 0.25 * level + 0.1 * dp / 1000
    return amount


def _metrics(view, context, supplied):
    board = {}
    for owner in ('A', 'B'):
        stacks = view['players'][owner]['battle']
        kinds = [_card(context, owner, s['cards'][-1])['type'] for s in stacks.values()]
        sizes = [len(s['cards']) for s in stacks.values()]
        board[owner] = {'battle_card_count': len(stacks), 'digimon_count': kinds.count('Digimon'),
            'tamer_count': kinds.count('Tamer'), 'option_count': kinds.count('Option'),
            'total_stack_cards': sum(sizes), 'digivolution_card_count': sum(n - 1 for n in sizes),
            'largest_stack_size': max(sizes, default=0)}
    checks = dict.fromkeys(('A', 'B'), None)
    if supplied is not None:
        if (not isinstance(supplied, dict) or set(supplied) != {'board', 'successful_security_checks'}
                or supplied['board'] != board or not isinstance(supplied['successful_security_checks'], dict)
                or set(supplied['successful_security_checks']) != {'A', 'B'}
                or any(type(n) is not int or n < 0 for n in supplied['successful_security_checks'].values())):
            raise RuntimeHalt('SCORING_PUBLIC_METRICS_MISMATCH')
        checks = dict(supplied['successful_security_checks'])
    return {'board': board, 'successful_security_checks': checks}


def _tempo(view, metrics):
    board, checks = metrics['board'], metrics['successful_security_checks']
    fields = {'cards_in_play': 'battle_card_count', 'total_sources': 'digivolution_card_count',
              'largest_stack': 'largest_stack_size'}
    axes = {name: {s: board[s][field] for s in ('A', 'B')} for name, field in fields.items()}
    axes['completed_security_checks'] = dict(checks)
    for values in axes.values():
        a, b = values['A'], values['B']
        values['leader'] = 'UNKNOWN' if a is None or b is None else 'TIED' if a == b else 'A' if a > b else 'B'
    leaders = {values['leader'] for values in axes.values()} - {'TIED', 'UNKNOWN'}
    leader = ('CONTESTED' if len(leaders) > 1 else 'UNKNOWN' if any(v['leader'] == 'UNKNOWN' for v in axes.values())
              else next(iter(leaders)) if leaders else 'TIED')
    return {'players': {s: {**board[s], 'successful_security_checks': checks[s],
                             'remaining_security': view['players'][s]['security']['count']} for s in ('A', 'B')},
            'axes': axes, 'leader': leader, 'method': 'UNWEIGHTED_COMPONENT_DOMINANCE'}


def _cost(result, command, before, after, actor):
    def number(value):
        return type(value) in (int, float) and math.isfinite(value) and value >= 0

    def payments(node, path='result'):
        if not isinstance(node, dict):
            return []
        operation = node.get('operation', '')
        if isinstance(operation, str) and operation.startswith('PAY_') and 'cost' in node:
            if not number(node['cost']):
                raise RuntimeHalt('SCORING_INVALID_PAID_COST')
            return [{'path': path, 'operation': operation, 'cost': node['cost'], 'evidence': 'PAY_STEP'}]
        steps = node.get('steps')
        if isinstance(steps, list):
            values = [item for i, step in enumerate(steps) for item in payments(step, path + '.steps[' + str(i) + ']')]
        elif isinstance(node.get('result'), dict):
            values = payments(node['result'], path + '.result')
        else:
            # Without steps/result, these are named canonical subresults.
            values = [item for name in ('evolution', 'play') if isinstance(node.get(name), dict)
                      for item in payments(node[name], path + '.' + name)]
        if values:
            return values
        if 'cost' in node:
            if not number(node['cost']):
                raise RuntimeHalt('SCORING_INVALID_PAID_COST')
            return [{'path': path, 'operation': 'DIRECT_COST', 'cost': node['cost'], 'evidence': 'DIRECT_COST'}]
        return []

    found = payments(result)
    if found:
        source = 'EXPLICIT_PAY_STEPS' if any(p['evidence'] == 'PAY_STEP' for p in found) else 'EXPLICIT_RESULT_COST'
        return {'paid': float(sum(p['cost'] for p in found)), 'source': source,
                'payments': found, 'verified_payment': True, 'controller': actor}
    if command.get('command', command.get('kind')) in _SPEND_COMMANDS and before['active'] == after['active']:
        sign = 1 if before['active'] == actor else -1
        paid = max(0, sign * (before['memory'] - after['memory']))
        return {'paid': float(paid), 'source': 'ACTOR_RELATIVE_GAUGE_FALLBACK',
                'payments': [], 'verified_payment': False, 'controller': actor}
    return {'paid': 0.0, 'source': 'NO_PAYMENT_EVIDENCE', 'payments': [],
            'verified_payment': False, 'controller': actor}


def score_transition(before_view, after_view, seat, *, command=None, result=None,
                     context=None, public_metrics_before=None, public_metrics_after=None):
    """Return an inspectable immediate-impact label from public observations."""
    if seat not in ('A', 'B') or context is None:
        raise RuntimeHalt('SCORING_CONTEXT_AND_SEAT_REQUIRED')
    try:
        _view(before_view, seat, context); _view(after_view, seat, context)
    except (RuntimeHalt, KeyError, TypeError, ValueError) as exc:
        raise RuntimeHalt('SCORING_PUBLIC_INPUT_INVALID: ' + str(exc)) from exc
    command, result = copy.deepcopy(command or {}), copy.deepcopy(result or {})
    if not isinstance(command, dict) or not isinstance(result, dict):
        raise RuntimeHalt('SCORING_COMMAND_RESULT_SCHEMA')
    actor = command.get('seat', seat)
    if actor not in ('A', 'B'):
        raise RuntimeHalt('SCORING_ACTOR_REQUIRED')
    if (public_metrics_before is None) != (public_metrics_after is None):
        raise RuntimeHalt('SCORING_BOTH_METRIC_BOUNDARIES_REQUIRED')
    mb = _metrics(before_view, context, public_metrics_before)
    ma = _metrics(after_view, context, public_metrics_after)
    kind = command.get('command', command.get('kind'))
    configuration = json.loads(_CRITERIA_BYTES)
    procedural = kind in configuration['procedural_commands']
    outcome = {'terminal': after_view['terminal'], 'winner': after_view['winner'],
               'included_in_board_reward': False}
    common = {'criterion_sha256': CRITERIA_SHA256, 'scorer_source_sha256': _SCORER_SOURCE_SHA256,
              'procedural': procedural, 'learning_eligible': not procedural,
              'decision_type': 'PROCEDURAL' if procedural else 'RESOLVED_ACTION',
              'tempo_before': _tempo(before_view, mb), 'tempo_after': _tempo(after_view, ma),
              'check_history_status': 'PROVIDED_BY_TRACKER' if public_metrics_before is not None else 'NOT_PROVIDED',
              'outcome': outcome, 'strategic_approval': 'NONE', 'probability_claim': False}
    if command.get('status') not in (None, 'EXPERIMENTAL_RESOLVED'):
        return {**common, 'label': 'UNRATED', 'meaning': 'unrated', 'reward': None, 'raw_reward': None,
                'learning_eligible': False,
                'status': 'UNRATED', 'components': {}, 'memory_cost': {'paid': 0, 'source': 'UNRATED', 'payments': []},
                'efficiency': {'status': 'UNRATED', 'benefit': None, 'benefit_per_memory': None}}
    if public_metrics_before is not None:
        deltas = {s: ma['successful_security_checks'][s] - mb['successful_security_checks'][s] for s in ('A', 'B')}
        if any(n < 0 for n in deltas.values()) or any(deltas.values()) and (
                kind != 'CONFIRM_ATTACK' or result.get('success') is not True or not result.get('checked_card')
                or deltas[actor] != 1 or deltas['B' if actor == 'A' else 'A'] != 0):
            raise RuntimeHalt('SCORING_SECURITY_COUNTER_TRANSITION_INVALID')
    opposite = 'B' if seat == 'A' else 'A'
    own_before, other_before = _amounts(before_view, context, seat), _amounts(before_view, context, opposite)
    own_after, other_after = _amounts(after_view, context, seat), _amounts(after_view, context, opposite)
    amounts_before = {k: own_before[k] - other_before[k] for k in own_before}
    amounts_after = {k: own_after[k] - other_after[k] for k in own_after}
    amounts_before['security_checks'] = ((mb['successful_security_checks'][seat] - mb['successful_security_checks'][opposite])
                                         if public_metrics_before is not None else 0)
    amounts_after['security_checks'] = ((ma['successful_security_checks'][seat] - ma['successful_security_checks'][opposite])
                                        if public_metrics_after is not None else 0)
    components = {}
    for name in amounts_before:
        delta = amounts_after[name] - amounts_before[name]
        weight = configuration['weights'][name]
        components[name] = {'before': amounts_before[name], 'after': amounts_after[name],
                            'delta': delta, 'weight': weight, 'contribution': delta * weight}
    board_reward = sum(c['contribution'] for c in components.values())
    cost = _cost(result, command, before_view, after_view, actor)
    perspective = 1 if actor == seat else -1
    residual = 0.0
    if before_view['active'] == after_view['active']:
        actor_sign = 1 if before_view['active'] == actor else -1
        residual = actor_sign * (after_view['memory'] - before_view['memory']) + cost['paid']
    for name, amount in (('memory_paid', perspective * cost['paid']),
                         ('memory_resource_residual', perspective * residual)):
        weight = configuration['weights'][name]
        components[name] = {'before': 0, 'after': amount, 'delta': amount, 'weight': weight, 'contribution': amount * weight}
    raw_reward = sum(c['contribution'] for c in components.values())
    reward = round(raw_reward, 10)
    threshold = configuration['neutral_absolute_threshold']
    label, meaning = ('GREEN', 'positive') if reward > threshold else ('RED', 'negative') if reward < -threshold else ('YELLOW', 'neutral')
    benefit = max(0.0, board_reward)
    evidence = cost['verified_payment'] or cost['source'] == 'ACTOR_RELATIVE_GAUGE_FALLBACK'
    efficiency_status = ('NO_BENEFIT' if benefit <= 0 else 'UNVERIFIED' if not evidence else
                         'FREE' if cost['paid'] == 0 and cost['verified_payment'] else 'PAID' if cost['paid'] > 0 else 'UNVERIFIED')
    efficiency = {'status': efficiency_status, 'benefit': benefit,
                  'benefit_per_memory': benefit / cost['paid'] if evidence and cost['paid'] > 0 else None,
                  'payment_estimated': not cost['verified_payment'], 'minimum_claim': 'NONE'}
    return {**common, 'label': label, 'meaning': meaning, 'reward': reward,
            'raw_reward': round(raw_reward, 10), 'status': 'HEURISTIC_OBSERVED_BOARD_IMPACT',
            'components': components, 'memory_cost': cost, 'efficiency': efficiency}
