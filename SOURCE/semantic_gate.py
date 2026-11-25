"""Fail-closed rule checks on proposed actions, independent of engine handlers.

The installed generic checkers cover opening preparation only. Future mechanic
packs can register checkers for actual encountered actions. This code supplies
an algorithmic cross-check, not an independent human rules certification.
"""
import copy
import json
from pathlib import Path
import random
import re

from context_runtime import RuntimeHalt
from match_context import canonical, digest
from rules_evidence import comprehensive_rules, rules_version


_OPENING_LOCATOR = 'Comprehensive rules v4.3: 5-2-1-1 through 5-2-1-8'
_PHASE_LOCATOR = 'Comprehensive rules v4.3: 1-2-3-2; 6-1 through 6-4; 15-4'
_BREEDING_LOCATOR = 'Comprehensive rules v4.3: 4-17; 4-18; 6-4; 6-5; 15-4'
_BREEDING_EVOLUTION_LOCATOR = ('Comprehensive rules v4.3: 1-3-11-1; 3-4-7-3 through 3-4-7-8; '
                               '6-5; 8-1-2-8; 8-1-3-1 through 8-1-3-3')
_TURN_LOCATOR = ('Comprehensive rules v4.3: 6-1-3; 6-1-4; 6-5-1-7-1; 6-6; '
                 '15-8-3-6; 15-11-1; 15-13; 15-14-1-5-1; 15-16-12')
_PLAY_LOCATOR = 'Comprehensive rules v4.3: 1-3-11-1; 4-2; 6-5-1-1; 7-1-1 through 7-1-3-3'
_EX13_017_SEARCH = ('[When Moving] [On Play] Reveal the top 3 cards of your deck. '
    'Add 1 card with [Veedramon] in its text or the [Royal Knight] trait among them '
    'to the hand. Return the rest to the bottom of the deck.')
_EX13_019_ATTACK = ('[When Attacking] [Once Per Turn] You may play 1 Tamer card with '
                    '[Veedramon] in its text from your hand with the cost reduced by 2.')
_BT11_112_ON_PLAY = ('[On Play] Until the end of your opponent\'s turn, 1 of your '
    'Digimon with [Veemon] or [Veedramon] in its name gains ＜Blocker＞ and ＜Evade＞.')
_EX13_002_EGG = ('[Your Turn] [Once Per Turn] When any of your blue Tamers are played, '
    'this Digimon with [Veedramon] in its name may unsuspend.')


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


def _source_at(source, locator):
    version = re.search(r'Comprehensive rules v(\d+\.\d+):', source['locator'])
    return {**source, 'locator': locator.replace('Comprehensive rules v4.3:',
        'Comprehensive rules v' + version.group(1) + ':') if version else locator}


def _physical_number(key):
    if not isinstance(key, str) or not re.fullmatch(r'[AB]:[A-Z0-9-]+#[1-9][0-9]*', key):
        raise RuntimeHalt('RULE_PHYSICAL_KEY_INVALID')
    return key.split(':', 1)[1].split('#', 1)[0]


def _special_cost(condition, base):
    legacy = re.fullmatch(r'\[Digivolve\] (\d+) from (\[[^\]]+\](?:/\[[^\]]+\])*)', condition)
    if legacy:
        cost, requirement = int(legacy.group(1)), legacy.group(2)
    else:
        current = re.fullmatch(r'\[Digivolve\] (.+): Cost (\d+)', condition)
        if current is None:
            raise RuntimeHalt('RULE_SPECIAL_ROUTE_UNREVIEWED: ' + condition)
        requirement, cost = current.group(1), int(current.group(2))
    if re.fullmatch(r'\[[^\]]+\](?:/\[[^\]]+\])*', requirement):
        return cost if base['name'] in re.findall(r'\[([^\]]+)\]', requirement) else None
    qualified = re.fullmatch(r'Lv\.(\d+) w/\[([^\]]+)\] (trait|in name)', requirement)
    if qualified is None:
        raise RuntimeHalt('RULE_SPECIAL_PREDICATE_UNREVIEWED: ' + requirement)
    level, value, kind = qualified.groups()
    if base.get('level') != int(level):
        return None
    matched = value in base.get('traits', []) if kind == 'trait' else value in base['name']
    return cost if matched else None


def _ordinary_window(before, command, *, allow_negative=False):
    state = before['state']
    if (state['terminal'] or command['seat'] != state['active']
            or (state['memory'] < 0 and not allow_negative)
            or state['attack'] is not None or state['resolving_option'] is not None):
        raise RuntimeHalt('RULE_ORDINARY_WINDOW_INVALID')
    if state['pending']:
        raise RuntimeHalt('RULE_PHASE_PENDING_UNREVIEWED')
    return state


def _quiet_timing(context, state, seat, timing):
    """Defer a live printed timing until its effect checker is installed."""
    for stack in state['battle'][seat].values():
        cards = stack['cards']
        for index, physical in enumerate(cards):
            field = 'main_text' if index == len(cards) - 1 else 'inherited_text'
            text = context.card(seat, _physical_number(physical)).effect_text(field)
            if '[' + timing + ']' in text:
                raise RuntimeHalt('RULE_PHASE_EFFECT_UNREVIEWED: ' + timing + ' card=' + physical)


def _advance_phase(context, before, command, source):
    state = _ordinary_window(before, command)
    seat = command['seat']
    phase = state['phase']
    expected = copy.deepcopy(before)
    new = expected['state']
    rules = _source_at(source, _PHASE_LOCATOR)
    if phase == 'START_OF_TURN':
        _quiet_timing(context, state, seat, 'Start of Your Turn')
        new['phase'] = 'TURN_START_EFFECTS'
    elif phase == 'TURN_START_EFFECTS':
        for stack in state['battle'][seat].values():
            if stack['suspended'] or stack['statuses']:
                raise RuntimeHalt('RULE_UNSUSPEND_INTERACTION_UNREVIEWED: ' + stack['cards'][-1])
        new['phase'] = 'DRAW'
    elif phase == 'UNSUSPEND':
        new['phase'] = 'DRAW'
    elif phase == 'DRAW':
        if not (state['turn'] == 1 and seat == before['first']):
            deck = new['zones'][seat]['deck']
            if not deck:
                new['terminal'] = True
                new['winner'] = 'B' if seat == 'A' else 'A'
                new['terminal_reason'] = 'DRAW_PHASE_DECKOUT'
                return expected, {'phase': 'DRAW', 'winner': new['winner'],
                    'status': 'EXPERIMENTAL_TERMINAL', 'full_match_credit': 0,
                    'rules_source': rules}
            new['zones'][seat]['hand'].append(deck.pop())
        new['phase'] = 'BREEDING'
    elif phase == 'BREEDING_MOVING_EFFECTS':
        _quiet_timing(context, state, seat, 'Start of Your Main Phase')
        new['phase'] = 'MAIN'
    else:
        raise RuntimeHalt('RULE_PHASE_ADVANCE_UNREVIEWED: ' + str(phase))
    return expected, {'phase': new['phase'], 'full_match_credit': 0, 'rules_source': rules}


def _breeding_choice(context, before, command, source):
    state = _ordinary_window(before, command)
    seat = command['seat']
    action = command['args'].get('action')
    if state['phase'] != 'BREEDING' or action not in ('skip', 'hatch', 'promote'):
        raise RuntimeHalt('RULE_BREEDING_CHOICE_UNREVIEWED: ' + str(action))
    expected = copy.deepcopy(before)
    new = expected['state']
    if action == 'hatch':
        if state['breeding'][seat] or not state['zones'][seat]['eggdeck']:
            raise RuntimeHalt('RULE_HATCH_NOT_AVAILABLE')
        new['breeding'][seat] = [new['zones'][seat]['eggdeck'].pop()]
    elif action == 'promote':
        cards = state['breeding'][seat]
        if not cards:
            raise RuntimeHalt('RULE_PROMOTION_SOURCE_MISSING')
        top = cards[-1]
        top_def = context.card(seat, _physical_number(top)).to_dict()
        if top_def['type'] != 'Digimon' or not isinstance(top_def['level'], int) or top_def['level'] < 3:
            raise RuntimeHalt('RULE_PROMOTION_LEVEL_INVALID')
        if any(stack['statuses'] for owner in ('A', 'B') for stack in state['battle'][owner].values()):
            raise RuntimeHalt('RULE_PROMOTION_STATUS_UNREVIEWED')
        for index, card in enumerate(cards):
            field = 'main_text' if index == len(cards) - 1 else 'inherited_text'
            if '[When Moving]' in context.card(seat, _physical_number(card)).effect_text(field):
                raise RuntimeHalt('RULE_PROMOTION_EFFECT_UNREVIEWED: ' + card)
        new['entity_sequence'] += 1
        new['battle'][seat][top] = {'cards': list(cards), 'suspended': False,
            'statuses': {}, 'instance_id': 'entity-' + str(new['entity_sequence']),
            'played_turn': None, 'ready_since_turn': new['turn']}
        new['breeding'][seat] = []
    _quiet_timing(context, new, seat, 'Start of Your Main Phase')
    for stack in state['battle']['B' if seat == 'A' else 'A'].values():
        for index, card in enumerate(stack['cards']):
            field = 'main_text' if index == len(stack['cards']) - 1 else 'inherited_text'
            if "[Start of Opponent's Main Phase]" in context.card('B' if seat == 'A' else 'A',
                    _physical_number(card)).effect_text(field):
                raise RuntimeHalt('RULE_OPPONENT_MAIN_EFFECT_UNREVIEWED: ' + card)
    new['phase'] = 'MAIN'
    return expected, {'action': action, 'phase': 'MAIN', 'full_match_credit': 0,
                      'rules_source': _source_at(source, _BREEDING_LOCATOR)}


def _breeding_evolution(context, before, command, source):
    state = _ordinary_window(before, command)
    seat, args = command['seat'], command['args']
    if state['phase'] != 'MAIN' or any(state['battle'][s] for s in ('A', 'B')):
        raise RuntimeHalt('RULE_BREEDING_EVOLUTION_BOARD_UNREVIEWED')
    stack = state['breeding'][seat]
    if not stack:
        raise RuntimeHalt('RULE_BREEDING_SOURCE_MISSING')
    base = stack[-1]
    if args.get('source_key', base) != base:
        raise RuntimeHalt('RULE_BREEDING_SOURCE_MISMATCH')
    hand = state['zones'][seat]['hand']
    target = next((card for card in hand if card == args.get('hand_key')), None)
    if target is None:
        raise RuntimeHalt('RULE_EVOLUTION_HAND_COPY_MISSING')
    base_def = context.card(seat, _physical_number(base)).to_dict()
    definition = context.card(seat, _physical_number(target))
    card_def = definition.to_dict()
    if base_def['type'] not in ('Digi-Egg', 'Digimon') or card_def['type'] != 'Digimon':
        raise RuntimeHalt('RULE_EVOLUTION_ROUTE_UNREVIEWED: ' + _physical_number(target))
    for physical in [target] + [card for owner in ('A', 'B') for card in state['breeding'][owner]]:
        definition_at = context.card(physical[0], _physical_number(physical))
        if any('breeding' in definition_at.effect_text(field).lower()
               for field in ('main_text', 'inherited_text')):
            raise RuntimeHalt('RULE_BREEDING_EFFECT_UNREVIEWED: ' + physical)
    routes = []
    for condition in card_def.get('normal_digivolution', {}).values():
        match = re.fullmatch(r'((?:(?:Red|Blue|Yellow|Green|Black|Purple|White)\s*)+)\s+(\d+) from Lv\.(\d+)', condition)
        if match is None:
            raise RuntimeHalt('RULE_PRINTED_ROUTE_UNREVIEWED: ' + str(condition))
        colors, cost, level = match.groups()
        accepted = set(re.findall(r'Red|Blue|Yellow|Green|Black|Purple|White', colors))
        if base_def.get('level') == int(level) and accepted.intersection(base_def['colors']):
            routes.append({'cost': int(cost), 'basis': 'PRINTED_NORMAL',
                'printed_condition': condition, 'definition_sha256': definition.definition_sha256,
                'status': 'PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY'})
    for condition in card_def.get('special_conditions', {}).get('[Special Digivolution Condition]', '').splitlines():
        cost = _special_cost(condition, base_def)
        if cost is not None:
            routes.append({'cost': cost, 'basis': 'PRINTED_SPECIAL',
                'printed_condition': condition, 'definition_sha256': definition.definition_sha256,
                'status': 'PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY'})
    routes.sort(key=lambda route: (route['cost'], route['basis'], route['printed_condition']))
    index = args.get('route_index')
    if type(index) is not int or not 0 <= index < len(routes):
        raise RuntimeHalt('RULE_PRINTED_ROUTE_MISSING')
    route = routes[index]
    for key in ('cost', 'basis', 'printed_condition', 'definition_sha256', 'status'):
        if key in args and args[key] != route[key]:
            raise RuntimeHalt('RULE_PRINTED_ROUTE_MISMATCH: ' + key)
    if route['cost'] > state['memory'] + 10:
        raise RuntimeHalt('RULE_EVOLUTION_COST_UNPAYABLE')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['memory'] -= route['cost']
    new_hand = new['zones'][seat]['hand']
    new_hand.remove(target)
    new['breeding'][seat].append(target)
    deck = new['zones'][seat]['deck']
    drew = bool(deck)
    if drew:
        new_hand.append(deck.pop())
    if new['memory'] < 0:
        new['phase'] = 'END_OF_TURN'
    return expected, {'hand_key': target, 'source_key': base,
        'route_index': index, 'route': route, 'cost': route['cost'], 'drew': drew,
        'memory': new['memory'], 'phase': new['phase'],
        'rules_source': _source_at(source, _BREEDING_EVOLUTION_LOCATOR),
        'full_match_credit': 0}


def _quiet_end(context, state, seat):
    for owner in ('A', 'B'):
        timing = 'End of Your Turn' if owner == seat else "End of Opponent's Turn"
        for stack in state['battle'][owner].values():
            if stack['statuses']:
                raise RuntimeHalt('RULE_TURN_END_STATUS_UNREVIEWED: ' + stack['cards'][-1])
            cards = stack['cards']
            for index, physical in enumerate(cards):
                field = 'main_text' if index == len(cards) - 1 else 'inherited_text'
                text = context.card(owner, _physical_number(physical)).effect_text(field)
                if '[' + timing + ']' in text or '[End of All Turns]' in text:
                    raise RuntimeHalt('RULE_TURN_END_EFFECT_UNREVIEWED: ' + physical)


def _pass_turn(context, before, command, source):
    state = _ordinary_window(before, command)
    if state['phase'] != 'MAIN':
        raise RuntimeHalt('RULE_PASS_WINDOW_INVALID')
    seat = command['seat']
    _quiet_end(context, state, seat)
    expected = copy.deepcopy(before)
    expected['state']['memory'] = -3
    expected['state']['phase'] = 'END_OF_TURN'
    return expected, {'phase': 'END_OF_TURN', 'memory_before': state['memory'],
        'memory_after': -3, 'turn_postponed': False, 'pending_end_effects': 0,
        'rules_source': _source_at(source, _TURN_LOCATOR), 'full_match_credit': 0}


def _finish_turn(context, before, command, source):
    state = _ordinary_window(before, command, allow_negative=True)
    if state['phase'] != 'END_OF_TURN':
        raise RuntimeHalt('RULE_TURN_END_WINDOW_INVALID')
    seat = command['seat']
    _quiet_end(context, state, seat)
    expected = copy.deepcopy(before)
    new = expected['state']
    rules = _source_at(source, _TURN_LOCATOR)
    if state['memory'] >= 0:
        new['phase'] = 'MAIN'
        return expected, {'phase': 'MAIN', 'memory_before': state['memory'],
            'memory_after': state['memory'], 'turn_postponed': True,
            'rules_source': rules, 'full_match_credit': 0}
    new['active'] = 'B' if seat == 'A' else 'A'
    new['memory'] = -state['memory']
    new['turn'] += 1
    new['once_used'] = []
    new['phase'] = 'START_OF_TURN'
    return expected, {'phase': 'START_OF_TURN', 'memory_before': state['memory'],
        'memory_after': new['memory'], 'next_controller': new['active'],
        'turn': new['turn'], 'turn_postponed': False,
        'rules_source': rules, 'full_match_credit': 0}


def _play_card(context, before, command, source):
    state = _ordinary_window(before, command)
    seat = command['seat']
    if state['phase'] != 'MAIN' or any(state['battle'][owner] for owner in ('A', 'B')):
        raise RuntimeHalt('RULE_PLAY_BOARD_UNREVIEWED')
    key = command['args'].get('hand_key')
    if key not in state['zones'][seat]['hand']:
        raise RuntimeHalt('RULE_PLAY_HAND_COPY_MISSING')
    definition = context.card(seat, _physical_number(key)).to_dict()
    if definition['type'] not in ('Digimon', 'Tamer'):
        raise RuntimeHalt('RULE_PLAY_TYPE_UNREVIEWED: ' + definition['type'])
    cost = definition['play_cost']
    if type(cost) is not int or cost < 0 or cost > state['memory'] + 10:
        raise RuntimeHalt('RULE_PLAY_COST_UNPAYABLE')
    if 'printed_cost' in command['args'] and command['args']['printed_cost'] != cost:
        raise RuntimeHalt('RULE_PLAY_PRINTED_COST_MISMATCH')
    text = definition['main_text']
    if definition['card_number'] == 'EX13-017' and text == _EX13_017_SEARCH:
        effect_id = 'EX13-017.on_play_search'
    elif text == '':
        effect_id = None
    else:
        raise RuntimeHalt('RULE_PLAY_CARD_TEXT_UNREVIEWED: ' + definition['card_number'])
    expected = copy.deepcopy(before)
    new = expected['state']
    new['zones'][seat]['hand'].remove(key)
    new['memory'] -= cost
    new['entity_sequence'] += 1
    instance = 'entity-' + str(new['entity_sequence'])
    new['battle'][seat][key] = {'cards': [key], 'suspended': False, 'statuses': {},
        'instance_id': instance, 'played_turn': new['turn'],
        'ready_since_turn': new['turn'] + 1}
    effects = []
    if effect_id is not None:
        new['effect_sequence'] += 1
        new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
            'seat': seat, 'source': key, 'effect_id': effect_id, 'field': 'main_text',
            'instance': instance, 'depth': 0,
            'trigger': {'kind': 'On Play', 'card': key}, 'usage': []})
        effects.append(effect_id)
    elif new['memory'] < 0:
        new['phase'] = 'END_OF_TURN'
    card_source = definition['official_source']
    return expected, {'played_card': key, 'cost': cost, 'memory_after': new['memory'],
        'full_match_credit': 0, 'rules_source': _source_at(source, _PLAY_LOCATOR),
        'card_source': {'url': card_source['url'], 'sha256': card_source['sha256'],
            'locator': '#' + definition['card_number'] + ' printed type, play cost and main effects'},
        'scope_context_id': context.matchup_id, 'printed_trigger': 'On Play',
        'triggered_effects': effects, 'play_method': 'MAIN_ACTION', 'assembly_materials': []}


def _printed_strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for key, item in value.items()
                for text in _printed_strings(key) + _printed_strings(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _printed_strings(item)]
    return []


def _search_has_veedramon(context, seat, key):
    card = context.card(seat, _physical_number(key)).to_dict()
    return any('Veedramon' in text for field in ('name', 'traits', 'main_text',
        'inherited_text', 'security_text', 'special_conditions', 'normal_digivolution')
        for text in _printed_strings(card.get(field)))


def _resolve_pending(context, before, command, source):
    state = before['state']
    seat = command['seat']
    if state['terminal'] or not state['pending']:
        raise RuntimeHalt('RULE_PENDING_WINDOW_UNREVIEWED')
    pending = next((effect for effect in state['pending']
                    if effect['id'] == command['args'].get('pending_id')), None)
    if pending is None:
        raise RuntimeHalt('RULE_PENDING_ID_INVALID')
    if pending['effect_id'] == 'EX13-019.attack_play_tamer':
        if len(state['pending']) != 1:
            raise RuntimeHalt('RULE_ATTACK_TAMER_PENDING_GROUP_UNREVIEWED')
        return _resolve_attack_tamer(context, before, command, source, pending)
    if pending['effect_id'] != 'EX13-017.on_play_search':
        raise RuntimeHalt('RULE_EFFECT_CHECK_NOT_INSTALLED: ' + pending['effect_id'])
    if (len(state['pending']) != 1 or state['attack'] is not None or state['resolving_option'] is not None
            or seat != state['active']):
        raise RuntimeHalt('RULE_PENDING_WINDOW_UNREVIEWED')
    if (pending['id'] != command['args'].get('pending_id') or pending['seat'] != seat
            or pending['field'] != 'main_text' or pending['source'] not in state['battle'][seat]
            or state['battle'][seat][pending['source']]['instance_id'] != pending['instance']
            or context.card(seat, _physical_number(pending['source'])).effect_text('main_text')
               != _EX13_017_SEARCH):
        raise RuntimeHalt('RULE_SEARCH_PENDING_MISMATCH')
    choice = command['args'].get('choice')
    if not isinstance(choice, dict) or set(choice) != {'selected', 'bottom_order'}:
        raise RuntimeHalt('RULE_SEARCH_CHOICE_INVALID')
    selected, bottom = choice['selected'], choice['bottom_order']
    deck = state['zones'][seat]['deck']
    revealed = list(reversed(deck[-3:]))
    eligible = [key for key in revealed if _search_has_veedramon(context, seat, key)
                or 'Royal Knight' in context.card(seat, _physical_number(key)).to_dict()['traits']]
    if (not isinstance(selected, list) or not isinstance(bottom, list)
            or any(not isinstance(key, str) for key in selected + bottom)
            or len(selected) != (1 if eligible else 0)
            or (selected and selected[0] not in eligible)
            or len(bottom) != len(revealed) - len(selected)
            or set(bottom) != set(revealed) - set(selected)
            or len(set(bottom)) != len(bottom)):
        raise RuntimeHalt('RULE_SEARCH_SELECTION_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = []
    new_deck = new['zones'][seat]['deck']
    if revealed:
        del new_deck[-len(revealed):]
    new['zones'][seat]['hand'].extend(selected)
    new_deck[:0] = bottom
    if new['phase'] == 'MAIN' and new['memory'] < 0:
        new['phase'] = 'END_OF_TURN'
    return expected, {'revealed': revealed, 'selected': selected, 'bottom_order': bottom,
        'bottom_order_convention': 'first element is bottommost', 'status': 'EXPERIMENTAL'}


def _resolve_attack_tamer(context, before, command, source, pending):
    state = before['state']
    seat, args = command['seat'], command['args']
    attack = state['attack']
    source_key = pending['source']
    stack = state['battle'][seat].get(source_key)
    usage = [state['turn'], seat, source_key, pending['instance'], pending['effect_id']]
    if (seat != pending['seat'] or seat != state['active']
            or pending['id'] != args.get('pending_id') or pending['field'] != 'main_text'
            or pending['usage'] != usage or usage in state['once_used']
            or stack is None or stack['instance_id'] != pending['instance']
            or attack is None or attack['controller'] != seat or attack['window'] != 'COUNTER'
            or _EX13_019_ATTACK not in context.card(seat, _physical_number(source_key))
                .effect_text('main_text').splitlines()):
        raise RuntimeHalt('RULE_ATTACK_TAMER_PENDING_MISMATCH')
    choice = args.get('choice')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = []
    new['once_used'] = sorted(state['once_used'] + [usage])
    if choice is None:
        return expected, {'played_card': None,
            'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
            'once_per_turn_consumed': True, 'full_match_credit': 0}
    if not isinstance(choice, str) or choice not in state['zones'][seat]['hand']:
        raise RuntimeHalt('RULE_TAMER_CHOICE_INVALID')
    definition = context.card(seat, _physical_number(choice)).to_dict()
    if definition['type'] != 'Tamer' or not _search_has_veedramon(context, seat, choice):
        raise RuntimeHalt('RULE_TAMER_CHOICE_INVALID')
    if (definition['card_number'] != 'BT11-112'
            or _BT11_112_ON_PLAY not in definition['main_text'].splitlines()):
        raise RuntimeHalt('RULE_TAMER_PLAY_TEXT_UNREVIEWED: ' + definition['card_number'])
    cost = max(0, definition['play_cost'] - 2)
    if cost > state['memory'] + 10:
        raise RuntimeHalt('RULE_TAMER_COST_UNPAYABLE')
    new['memory'] -= cost
    new['zones'][seat]['hand'].remove(choice)
    new['entity_sequence'] += 1
    instance = 'entity-' + str(new['entity_sequence'])
    new['battle'][seat][choice] = {'cards': [choice], 'suspended': False,
        'statuses': {}, 'instance_id': instance, 'played_turn': new['turn'],
        'ready_since_turn': new['turn'] + 1}
    new['effect_sequence'] += 1
    new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
        'seat': seat, 'source': choice, 'effect_id': 'BT11-112.on_play_grant',
        'field': 'main_text', 'instance': instance, 'depth': pending['depth'] + 1,
        'trigger': {'kind': 'On Play', 'card': choice}, 'usage': []})
    effects = ['BT11-112.on_play_grant']
    for physical in stack['cards'][:-1]:
        text = context.card(seat, _physical_number(physical)).effect_text('inherited_text')
        if 'Tamer' not in text:
            continue
        if (physical != stack['cards'][0] or _physical_number(physical) != 'EX13-002'
                or _EX13_002_EGG not in text.splitlines()
                or 'Blue' not in definition['colors']
                or 'Veedramon' not in context.card(seat, _physical_number(source_key)).name):
            raise RuntimeHalt('RULE_TAMER_PLAY_REACTION_UNREVIEWED: ' + physical)
        egg_effect = 'EX13-002.tamer_play_unsuspend'
        egg_usage = [state['turn'], seat, physical, stack['instance_id'], egg_effect]
        if egg_usage not in state['once_used']:
            new['effect_sequence'] += 1
            new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
                'seat': seat, 'source': physical, 'effect_id': egg_effect,
                'field': 'inherited_text', 'instance': stack['instance_id'],
                'depth': pending['depth'] + 1,
                'trigger': {'kind': 'Tamer Played', 'played_card': choice,
                            'played_seat': seat}, 'usage': egg_usage})
            effects.append(egg_effect)
    card_source = definition['official_source']
    play = {'played_card': choice, 'cost': cost, 'memory_after': new['memory'],
        'full_match_credit': 0, 'rules_source': _source_at(source,
            'Comprehensive rules v4.3: 3-4-3; 7-1-3; 15-4; 15-9-2-2; EX13-022 Q7264'),
        'card_source': {'url': card_source['url'], 'sha256': card_source['sha256'],
            'locator': '#' + definition['card_number'] + ' printed type, play cost and main effects'},
        'scope_context_id': context.matchup_id, 'printed_trigger': 'On Play',
        'triggered_effects': effects, 'play_method': 'EFFECT_WITHOUT_PAYING_COST',
        'assembly_materials': []}
    return expected, {'played_card': choice, 'play': play,
        'processing': 'TAMER_PLAYED_WITH_COST_REDUCED_BY_2',
        'once_per_turn_consumed': True, 'full_match_credit': 0}


def _declare_attack(context, before, command, source):
    state = _ordinary_window(before, command)
    seat, args = command['seat'], command['args']
    if state['phase'] != 'MAIN' or args.get('target') != 'PLAYER':
        raise RuntimeHalt('RULE_ATTACK_TARGET_UNREVIEWED')
    key = args.get('attacker')
    stack = state['battle'][seat].get(key)
    if stack is None or stack['suspended'] or stack['statuses']:
        raise RuntimeHalt('RULE_ATTACKER_NOT_READY')
    top = stack['cards'][-1]
    if (context.card(seat, _physical_number(top)).kind != 'Digimon'
            or stack['played_turn'] == state['turn']
            or stack['ready_since_turn'] is None
            or stack['ready_since_turn'] > state['turn']):
        raise RuntimeHalt('RULE_ATTACK_HISTORY_UNREVIEWED')
    for owner in ('A', 'B'):
        for other_key, other_stack in state['battle'][owner].items():
            if other_stack['statuses']:
                raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + other_key)
            for index, physical in enumerate(other_stack['cards']):
                field = 'main_text' if index == len(other_stack['cards']) - 1 else 'inherited_text'
                text = context.card(owner, _physical_number(physical)).effect_text(field)
                if 'suspend' in text.lower().replace('unsuspend', ''):
                    raise RuntimeHalt('RULE_ATTACK_ORIENTATION_EFFECT_UNREVIEWED: ' + physical)
                if other_key != key and ('[When Attacking]' in text or 'when any of your digimon attacks' in text.lower()):
                    raise RuntimeHalt('RULE_ATTACK_OBSERVER_UNREVIEWED: ' + physical)
                if other_key == key and physical != top and '[When Attacking]' in text:
                    raise RuntimeHalt('RULE_ATTACK_INHERITED_EFFECT_UNREVIEWED: ' + physical)
    top_text = context.card(seat, _physical_number(top)).effect_text('main_text')
    if _EX13_019_ATTACK in top_text.splitlines() and _physical_number(top) == 'EX13-019':
        effect_id = 'EX13-019.attack_play_tamer'
    elif '[When Attacking]' in top_text:
        raise RuntimeHalt('RULE_ATTACK_EFFECT_UNREVIEWED: ' + top)
    else:
        effect_id = None
    expected = copy.deepcopy(before)
    new = expected['state']
    new['battle'][seat][key]['suspended'] = True
    other = 'B' if seat == 'A' else 'A'
    new['attack'] = {'attacker': key, 'attacker_instance': stack['instance_id'],
        'target': 'PLAYER', 'target_instance': '', 'controller': seat,
        'defender': other, 'window': 'COUNTER', 'counter_used': False,
        'block_used': False, 'checked': None}
    result = {'attacker': key, 'target': 'PLAYER', 'window': 'COUNTER', 'full_match_credit': 0}
    if effect_id is not None:
        usage = [state['turn'], seat, top, stack['instance_id'], effect_id]
        if usage not in state['once_used']:
            new['effect_sequence'] += 1
            new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
                'seat': seat, 'source': top, 'effect_id': effect_id,
                'field': 'main_text', 'instance': stack['instance_id'], 'depth': 0,
                'trigger': {'kind': 'When Attacking', 'attacker': top, 'target': 'PLAYER'},
                'usage': usage})
            result['triggered_effects'] = [effect_id]
    return expected, result


class SemanticGate:
    """Reusable action checker registry; absent mechanics have no verdict."""
    def __init__(self, context, root, checkers=()):
        self.context = context
        self.root = Path(root).resolve()
        self.checkers = {'BEGIN_PREPARATION': _opening, 'REDRAW_CHOICE': _redraw,
                         'ADVANCE_PHASE': _advance_phase, 'BREEDING_CHOICE': _breeding_choice,
                         'BREEDING_EVOLUTION': _breeding_evolution, 'PASS_TURN': _pass_turn,
                         'FINISH_TURN': _finish_turn, 'PLAY_CARD': _play_card,
                         'RESOLVE_PENDING': _resolve_pending,
                         'DECLARE_ATTACK': _declare_attack}
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
        if rules_version(self.context) is None:
            raise RuntimeHalt('RULES_MANUAL_VERSION_UNREVIEWED')
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
