"""Fail-closed rule checks on proposed actions, independent of engine handlers.

Generic turn checks and encountered effect checks compare expected transitions
with the engine on a copy. They do not supply independent rules certification.
"""
import copy
import hashlib
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
_BATTLE_EVOLUTION_LOCATOR = ('Comprehensive rules v4.3: 1-3-11-1; 3-4-5; 4-2-2; 6-5-1-2; '
    '8-1-1 through 8-1-3-3; 15-3-1; 15-4; 15-11-1; 15-13; 15-16-3-1')
_TURN_LOCATOR = ('Comprehensive rules v4.3: 6-1-3; 6-1-4; 6-5-1-7-1; 6-6; '
                 '15-8-3-6; 15-11-1; 15-13; 15-14-1-5-1; 15-16-12')
_PLAY_LOCATOR = 'Comprehensive rules v4.3: 1-3-11-1; 4-2; 6-5-1-1; 7-1-1 through 7-1-3-3'
_EX13_017_SEARCH = ('[When Moving] [On Play] Reveal the top 3 cards of your deck. '
    'Add 1 card with [Veedramon] in its text or the [Royal Knight] trait among them '
    'to the hand. Return the rest to the bottom of the deck.')
_EX13_019_ATTACK = ('[When Attacking] [Once Per Turn] You may play 1 Tamer card with '
                    '[Veedramon] in its text from your hand with the cost reduced by 2.')
_EX13_022_PLAY = ('[On Play] [When Digivolving] [When Attacking] [Once Per Turn] You may '
    'play 1 Tamer card with [Veedramon] in its text from your hand without paying the cost.')
_EX13_022_OBSERVER = ("[All Turns] [Once Per Turn] When any of your Tamers are played, 1 "
    "of your opponent's Digimon or Tamers can't suspend until their turn ends.")
_BT11_112_ON_PLAY = ('[On Play] Until the end of your opponent\'s turn, 1 of your '
    'Digimon with [Veemon] or [Veedramon] in its name gains ＜Blocker＞ and ＜Evade＞.')
_EX13_002_EGG = ('[Your Turn] [Once Per Turn] When any of your blue Tamers are played, '
    'this Digimon with [Veedramon] in its name may unsuspend.')
_EX1_013_UNSUSPEND = ('[Your Turn][Once Per Turn] When this Digimon becomes '
    'unsuspended during your main phase, gain 1 memory.')
_BT11_112_UNSUSPEND = ('[Your Turn][Once Per Turn] When one of your blue Digimon '
    'becomes unsuspended, gain 1 memory.')
_BT11_112_SUSPEND = ('[All Turns] When one of your Digimon with [Veedramon] in its name '
    'becomes suspended, by suspending this Tamer, activate 1 of that Digimon\'s '
    '[When Digivolving] effects.')
_EX13_069_UNSUSPEND = ('[Your Turn] When any of your Digimon unsuspend, by suspending this '
    'Tamer, ＜Draw 1＞. After, 1 of your Digimon may digivolve into a Digimon card with '
    '[Veedramon] in its name in the hand with the cost reduced by 2.')
_LM_057_SECURITY = ('[Security] Reveal the top 2 cards of your deck. Add 1 red or blue card '
    'among them to the hand. Return the rest to the bottom of the deck. Then, place this '
    'card in the battle area.')
_SECURITY_TAMER_LOCATOR = ('Comprehensive rules v4.3: 3-4-3; 7-1-3; 13-1-6; 13-1-8-1; '
    '13-1-8-2; 13-1-8-4; 15-4; 15-16-2-1; 15-16-10-1 through 15-16-10-2')
_SECURITY_TAMER_TEXT = '[Security] Play this card without paying the cost.'


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
        for key, stack in state['battle'][seat].items():
            _reviewed_attack_statuses(context, state, seat, key, stack)
            if stack['suspended']:
                raise RuntimeHalt('RULE_UNSUSPEND_INTERACTION_UNREVIEWED: ' + key)
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
        for key, stack in state['battle'][owner].items():
            _reviewed_attack_statuses(context, state, owner, key, stack)
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
    if state['phase'] != 'MAIN':
        raise RuntimeHalt('RULE_PLAY_BOARD_UNREVIEWED')
    key = command['args'].get('hand_key')
    if key not in state['zones'][seat]['hand']:
        raise RuntimeHalt('RULE_PLAY_HAND_COPY_MISSING')
    definition = context.card(seat, _physical_number(key)).to_dict()
    if definition['type'] not in ('Digimon', 'Tamer'):
        raise RuntimeHalt('RULE_PLAY_TYPE_UNREVIEWED: ' + definition['type'])
    for owner in ('A', 'B'):
        for observer_key, observer in state['battle'][owner].items():
            _reviewed_attack_statuses(context, state, owner, observer_key, observer)
            for index, physical in enumerate(observer['cards']):
                field = 'main_text' if index == len(observer['cards']) - 1 else 'inherited_text'
                text = context.card(owner, _physical_number(physical)).effect_text(field)
                for line in text.splitlines():
                    body = re.sub(r'^(?:\[[^\]]+\]\s*)+', '', line)
                    if re.search(r'\b(?:cannot|can\'t) play\b', body, re.I):
                        raise RuntimeHalt('RULE_PLAY_RESTRICTION_UNREVIEWED: ' + physical)
                    if re.search(r'\bwhen\b[^.]*\bplayed\b', body, re.I):
                        if (definition['type'] == 'Digimon'
                                and _physical_number(physical) == 'EX13-002'
                                and field == 'inherited_text'
                                and line == _EX13_002_EGG):
                            continue
                        raise RuntimeHalt('RULE_PLAY_OBSERVER_UNREVIEWED: ' + physical)
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
    if pending['effect_id'] == 'BT11-112.on_play_grant':
        return _resolve_blocker_evade_grant(context, before, command, source, pending)
    if pending['effect_id'] == 'EX13-002.tamer_play_unsuspend':
        return _resolve_egg_unsuspend(context, before, command, source, pending)
    if pending['effect_id'] in ('EX1-013.unsuspend_memory', 'BT11-112.unsuspend_memory'):
        return _resolve_memory_reaction(context, before, command, source, pending)
    if pending['effect_id'] == 'BT11-112.suspend_reactivation':
        return _resolve_rina_suspension(context, before, command, source, pending)
    if pending['effect_id'] == 'LM-057.main_search' and pending['field'] == 'security_text':
        return _resolve_training_security(context, before, command, source, pending)
    if pending['effect_id'] == 'EX13-022.play_tamer':
        return _resolve_ulforce_tamer(context, before, command, source, pending)
    if pending['effect_id'] == 'EX13-022.tamer_play_restriction':
        return _resolve_ulforce_restriction(context, before, command, source, pending)
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


def _resolve_blocker_evade_grant(context, before, command, source, pending):
    state = before['state']
    seat = command['seat']
    source_key = pending['source']
    source_stack = state['battle'][seat].get(source_key)
    source_card = context.card(seat, _physical_number(source_key))
    if (seat != state['active'] or seat != pending['seat']
            or pending['id'] != command['args'].get('pending_id')
            or pending['field'] != 'main_text' or source_stack is None
            or source_stack['instance_id'] != pending['instance']
            or source_card.number != 'BT11-112'
            or _BT11_112_ON_PLAY not in source_card.effect_text('main_text').splitlines()):
        raise RuntimeHalt('RULE_GRANT_PENDING_MISMATCH')
    eligible = sorted(key for key, stack in state['battle'][seat].items()
        if context.card(seat, _physical_number(stack['cards'][-1])).kind == 'Digimon'
        and any(name in context.card(seat, _physical_number(stack['cards'][-1])).name
                for name in ('Veemon', 'Veedramon')))
    choice = command['args'].get('choice')
    if choice not in (eligible if eligible else [None]):
        raise RuntimeHalt('RULE_GRANT_TARGET_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = [effect for effect in state['pending'] if effect['id'] != pending['id']]
    if choice is None:
        return expected, {'target': None, 'processing': 'NO_ELIGIBLE_TARGET',
                          'full_match_credit': 0}
    target_stack = state['battle'][seat][choice]
    grant = {'controller': seat, 'source': source_key,
        'source_instance': source_stack['instance_id'], 'source_field': 'main_text',
        'source_kind': 'Tamer', 'source_definition_sha256': source_card.definition_sha256,
        'source_text_sha256': hashlib.sha256(source_card.effect_text('main_text').encode()).hexdigest(),
        'target': choice, 'target_owner': seat, 'target_instance': target_stack['instance_id'],
        'effect': {'keywords': ['Blocker', 'Evade']}, 'created_turn': state['turn'],
        'expires': {'turn': state['turn'] + 1,
                    'controller': 'B' if seat == 'A' else 'A', 'boundary': 'turn_end'}}
    new['battle'][seat][choice]['statuses'].setdefault('effect_grants', []).append(grant)
    return expected, {'target': choice, 'processing': 'GRANT_APPLIED',
                      'grant': grant, 'full_match_credit': 0}


def _resolve_egg_unsuspend(context, before, command, source, pending):
    state = before['state']
    seat, source_key = command['seat'], pending['source']
    usage = [state['turn'], seat, source_key, pending['instance'], pending['effect_id']]
    stack = next((item for item in state['battle'][seat].values()
                  if source_key in item['cards'][:-1]), None)
    if (seat != state['active'] or seat != pending['seat']
            or pending['id'] != command['args'].get('pending_id')
            or pending['field'] != 'inherited_text' or len(state['pending']) != 1
            or pending['usage'] != usage or usage in state['once_used']
            or stack is None or stack['instance_id'] != pending['instance']
            or context.card(seat, _physical_number(source_key)).effect_text('inherited_text')
               != _EX13_002_EGG or state['phase'] != 'MAIN'):
        raise RuntimeHalt('RULE_EGG_UNSUSPEND_PENDING_MISMATCH')
    choice = command['args'].get('choice')
    if type(choice) is not bool:
        raise RuntimeHalt('RULE_EGG_UNSUSPEND_CHOICE_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = []
    new['once_used'] = sorted(state['once_used'] + [usage])
    if not choice:
        return expected, {'changed': False,
            'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
            'once_per_turn_consumed': True, 'full_match_credit': 0}
    target = stack['cards'][-1]
    top = context.card(seat, _physical_number(target))
    if 'Veedramon' not in top.name or 'Blue' not in top.to_dict()['colors']:
        raise RuntimeHalt('RULE_EGG_UNSUSPEND_TARGET_INVALID')
    if not stack['suspended']:
        raise RuntimeHalt('RULE_EGG_UNSUSPEND_ALREADY_READY')
    statuses = stack['statuses']
    if set(statuses) - {'effect_grants'} or any(
            'cannot_unsuspend' in grant['effect'].get('restrictions', [])
            for grant in statuses.get('effect_grants', [])):
        raise RuntimeHalt('RULE_EGG_UNSUSPEND_STATUS_UNREVIEWED')
    new_stack = next(item for item in new['battle'][seat].values()
                     if source_key in item['cards'][:-1])
    new_stack['suspended'] = False
    for physical in stack['cards'][:-1]:
        text = context.card(seat, _physical_number(physical)).effect_text('inherited_text')
        if 'becomes unsuspended' not in text:
            continue
        if _physical_number(physical) != 'EX1-013' or text != _EX1_013_UNSUSPEND:
            raise RuntimeHalt('RULE_UNSUSPEND_REACTION_UNREVIEWED: ' + physical)
        effect_id = 'EX1-013.unsuspend_memory'
        child_usage = [state['turn'], seat, physical, effect_id]
        if child_usage in state['once_used']:
            continue
        new['effect_sequence'] += 1
        new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
            'seat': seat, 'source': physical, 'effect_id': effect_id,
            'field': 'inherited_text', 'instance': stack['instance_id'],
            'depth': pending['depth'] + 1,
            'trigger': {'kind': 'ORIENTATION_CHANGED', 'entity': target,
                'name_at_trigger': top.name, 'phase': state['phase'],
                'suspended_before': True, 'suspended_after': False},
            'usage': child_usage})
    for key, observer in state['battle'][seat].items():
        if key == target:
            continue
        physical = observer['cards'][-1]
        text = context.card(seat, _physical_number(physical)).effect_text('main_text')
        if 'becomes unsuspended' not in text:
            continue
        if (_physical_number(physical) != 'BT11-112'
                or _BT11_112_UNSUSPEND not in text.splitlines()):
            raise RuntimeHalt('RULE_UNSUSPEND_OBSERVER_UNREVIEWED: ' + physical)
        effect_id = 'BT11-112.unsuspend_memory'
        child_usage = [state['turn'], seat, physical, observer['instance_id'], effect_id]
        if child_usage in state['once_used']:
            continue
        new['effect_sequence'] += 1
        new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
            'seat': seat, 'source': physical, 'effect_id': effect_id,
            'field': 'main_text', 'instance': observer['instance_id'],
            'depth': pending['depth'] + 1,
            'trigger': {'kind': 'DIGIMON_UNSUSPENDED', 'entity': target,
                'name_at_trigger': top.name, 'suspended_before': True,
                'suspended_after': False}, 'usage': child_usage})
    return expected, {'suspended_before': True, 'suspended_after': False,
        'changed': True, 'prohibition': None, 'processing': 'UNSUSPEND_SELECTED',
        'once_per_turn_consumed': True, 'full_match_credit': 0}


def _resolve_memory_reaction(context, before, command, source, pending):
    state = before['state']
    seat, key, effect_id = command['seat'], pending['source'], pending['effect_id']
    tamer = effect_id == 'BT11-112.unsuspend_memory'
    field = 'main_text' if tamer else 'inherited_text'
    stack = next((item for item in state['battle'][seat].values()
                  if key in (item['cards'][-1:] if tamer else item['cards'][:-1])), None)
    definition = context.card(seat, _physical_number(key))
    expected_text = _BT11_112_UNSUSPEND if tamer else _EX1_013_UNSUSPEND
    expected_usage = ([state['turn'], seat, key, pending['instance'], effect_id]
                      if tamer else [state['turn'], seat, key, effect_id])
    if (seat != state['active'] or seat != pending['seat']
            or pending['id'] != command['args'].get('pending_id')
            or command['args'].get('choice') is not None
            or pending['field'] != field or stack is None
            or stack['instance_id'] != pending['instance']
            or expected_text not in definition.effect_text(field).splitlines()
            or pending['usage'] != expected_usage or expected_usage in state['once_used']
            or state['phase'] != 'MAIN'):
        raise RuntimeHalt('RULE_UNSUSPEND_MEMORY_PENDING_MISMATCH: ' + effect_id)
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = [item for item in state['pending'] if item['id'] != pending['id']]
    new['once_used'] = sorted(state['once_used'] + [expected_usage])
    new['memory'] = min(10, state['memory'] + 1)
    result = {'memory_before': state['memory'], 'memory_after': new['memory'],
              'gained': new['memory'] - state['memory']}
    if tamer:
        result.update({'once_per_turn_consumed': True, 'full_match_credit': 0})
    return expected, result


def _resolve_ulforce_tamer(context, before, command, source, pending):
    state = before['state']
    seat, args = command['seat'], command['args']
    key = pending['source']
    stack = state['battle'][seat].get(key)
    usage = [state['turn'], seat, key, pending['instance'], pending['effect_id']]
    text = context.card(seat, _physical_number(key)).effect_text('main_text')
    if (seat != state['active'] or seat != pending['seat']
            or pending['id'] != args.get('pending_id') or len(state['pending']) != 1
            or pending['field'] != 'main_text' or stack is None
            or stack['instance_id'] != pending['instance'] or stack['cards'][-1] != key
            or _physical_number(key) != 'EX13-022'
            or _EX13_022_PLAY not in text.splitlines()
            or _EX13_022_OBSERVER not in text.splitlines()
            or pending['trigger'].get('kind') != 'When Digivolving'
            or pending['trigger'].get('card') != key
            or pending['usage'] != usage or usage in state['once_used']):
        raise RuntimeHalt('RULE_ULFORCE_TAMER_PENDING_MISMATCH')
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
    if definition['card_number'] != 'BT11-112' or _BT11_112_ON_PLAY not in definition['main_text'].splitlines():
        raise RuntimeHalt('RULE_TAMER_PLAY_TEXT_UNREVIEWED: ' + definition['card_number'])
    if context.card(seat, _physical_number(key)).name.find('Veedramon') < 0:
        raise RuntimeHalt('RULE_ULFORCE_TAMER_SOURCE_MISMATCH')
    for physical in stack['cards'][:-1]:
        inherited = context.card(seat, _physical_number(physical)).effect_text('inherited_text')
        if 'Tamers are played' not in inherited:
            continue
        if _physical_number(physical) == 'EX13-002' and inherited == _EX13_002_EGG:
            prior = [state['turn'], seat, physical, stack['instance_id'],
                     'EX13-002.tamer_play_unsuspend']
            if prior in state['once_used']:
                continue
        raise RuntimeHalt('RULE_TAMER_PLAY_REACTION_UNREVIEWED: ' + physical)
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
    observer_usage = [state['turn'], seat, key, stack['instance_id'],
                      'EX13-022.tamer_play_restriction']
    if observer_usage in state['once_used']:
        raise RuntimeHalt('RULE_ULFORCE_OBSERVER_ALREADY_USED_UNREVIEWED')
    new['effect_sequence'] += 1
    new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
        'seat': seat, 'source': key, 'effect_id': 'EX13-022.tamer_play_restriction',
        'field': 'main_text', 'instance': stack['instance_id'],
        'depth': pending['depth'] + 1,
        'trigger': {'kind': 'Tamer Played', 'played_card': choice, 'played_seat': seat},
        'usage': observer_usage})
    official = definition['official_source']
    play = {'played_card': choice, 'cost': 0, 'memory_after': state['memory'],
        'full_match_credit': 0, 'rules_source': _source_at(source,
            'Comprehensive rules v4.3: 3-4-3; 7-1-3; 15-4; 15-9-2-2; EX13-022 Q7264'),
        'card_source': {'url': official['url'], 'sha256': official['sha256'],
            'locator': '#BT11-112 printed type, play cost and main effects'},
        'scope_context_id': context.matchup_id, 'printed_trigger': 'On Play',
        'triggered_effects': ['BT11-112.on_play_grant', 'EX13-022.tamer_play_restriction'],
        'play_method': 'EFFECT_WITHOUT_PAYING_COST', 'assembly_materials': []}
    return expected, {'played_card': choice, 'play': play,
        'processing': 'TAMER_PLAYED_WITHOUT_PAYING_COST',
        'once_per_turn_consumed': True, 'full_match_credit': 0}


def _resolve_ulforce_restriction(context, before, command, source, pending):
    state = before['state']
    seat, key = command['seat'], pending['source']
    opponent = 'B' if seat == 'A' else 'A'
    source_stack = state['battle'][seat].get(key)
    trigger = pending['trigger']
    played = trigger.get('played_card')
    usage = [state['turn'], seat, key, pending['instance'], pending['effect_id']]
    if (seat != state['active'] or seat != pending['seat']
            or pending['id'] != command['args'].get('pending_id')
            or len(state['pending']) != 1 or pending['field'] != 'main_text'
            or source_stack is None or source_stack['instance_id'] != pending['instance']
            or source_stack['cards'][-1] != key or _physical_number(key) != 'EX13-022'
            or _EX13_022_OBSERVER not in context.card(seat, _physical_number(key))
                .effect_text('main_text').splitlines()
            or trigger != {'kind': 'Tamer Played', 'played_card': played,
                           'played_seat': seat}
            or played not in state['battle'][seat]
            or context.card(seat, _physical_number(played)).kind != 'Tamer'
            or pending['usage'] != usage or usage in state['once_used']):
        raise RuntimeHalt('RULE_RESTRICTION_PENDING_MISMATCH')
    eligible = sorted(target for target, stack in state['battle'][opponent].items()
        if context.card(opponent, _physical_number(stack['cards'][-1])).kind
           in ('Digimon', 'Tamer'))
    choice = command['args'].get('choice')
    if choice not in (eligible if eligible else [None]):
        raise RuntimeHalt('RULE_RESTRICTION_TARGET_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = []
    new['once_used'] = sorted(state['once_used'] + [usage])
    if new['memory'] < 0:
        new['phase'] = 'END_OF_TURN'
    if choice is None:
        return expected, {'target': None, 'processing': 'NO_ELIGIBLE_TARGET',
            'once_per_turn_consumed': True, 'full_match_credit': 0}
    target_stack = state['battle'][opponent][choice]
    card = context.card(seat, _physical_number(key))
    grant = {'controller': seat, 'source': key,
        'source_instance': source_stack['instance_id'], 'source_field': 'main_text',
        'source_kind': 'Digimon', 'source_definition_sha256': card.definition_sha256,
        'source_text_sha256': hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
        'target': choice, 'target_owner': opponent,
        'target_instance': target_stack['instance_id'],
        'effect': {'restrictions': ['cannot_suspend']}, 'created_turn': state['turn'],
        'expires': {'turn': state['turn'] + 1, 'controller': opponent,
                    'boundary': 'turn_end'}}
    new['battle'][opponent][choice]['statuses'].setdefault('effect_grants', []).append(grant)
    return expected, {'target': choice, 'grant': grant,
        'processing': 'RESTRICTION_APPLIED', 'once_per_turn_consumed': True,
        'full_match_credit': 0}


def _resolve_rina_suspension(context, before, command, source, pending):
    state = before['state']
    seat, key = command['seat'], pending['source']
    tamer = state['battle'][seat].get(key)
    trigger = pending['trigger']
    observed = state['battle'][seat].get(trigger.get('observed_source'))
    attack = state['attack']
    if (seat != state['active'] or seat != pending['seat']
            or pending['id'] != command['args'].get('pending_id')
            or len(state['pending']) != 1 or pending['field'] != 'main_text'
            or pending['usage'] != [] or tamer is None
            or tamer['instance_id'] != pending['instance']
            or context.card(seat, _physical_number(key)).number != 'BT11-112'
            or _BT11_112_SUSPEND not in context.card(seat, _physical_number(key))
                .effect_text('main_text').splitlines()
            or observed is None or observed['instance_id'] != trigger.get('observed_instance')
            or not observed['suspended']
            or trigger != {'kind': 'DIGIMON_SUSPENDED',
                'observed_instance': observed['instance_id'],
                'observed_source': observed['cards'][-1],
                'name_at_trigger': context.card(seat, _physical_number(observed['cards'][-1])).name,
                'suspended_before': False, 'suspended_after': True}
            or attack is None or attack['window'] != 'COUNTER'
            or attack['attacker_instance'] != observed['instance_id']):
        raise RuntimeHalt('RULE_RINA_SUSPENSION_PENDING_MISMATCH')
    if command['args'].get('choice') is not None:
        raise RuntimeHalt('RULE_RINA_PAID_CHOICE_UNREVIEWED')
    expected = copy.deepcopy(before)
    expected['state']['pending'] = []
    return expected, {'suspension_paid': False, 'activated_effect': None,
        'processing': 'RINA_REACTIVATION_DECLINED', 'full_match_credit': 0}


def _resolve_training_security(context, before, command, source, pending):
    state = before['state']
    seat, key = command['seat'], pending['source']
    attack = state['attack']
    current = state['resolving_option']
    card = context.card(seat, _physical_number(key))
    if (seat != pending['seat'] or pending['id'] != command['args'].get('pending_id')
            or len(state['pending']) != 1 or pending['usage'] != []
            or card.number != 'LM-057' or card.kind != 'Option'
            or card.effect_text('security_text') != _LM_057_SECURITY
            or attack is None or attack['window'] != 'END' or attack['defender'] != seat
            or attack['checked'] != key or current is None or current['seat'] != seat
            or current['stack']['cards'] != [key]
            or current['stack']['instance_id'] != pending['instance']
            or pending['trigger'] != {'kind': 'Security Check', 'card': key}):
        raise RuntimeHalt('RULE_SECURITY_SEARCH_PENDING_MISMATCH')
    choice = command['args'].get('choice')
    if not isinstance(choice, dict) or set(choice) != {'selected', 'bottom_order'}:
        raise RuntimeHalt('RULE_SECURITY_SEARCH_SELECTION_INVALID')
    selected, bottom = choice['selected'], choice['bottom_order']
    if (not isinstance(selected, list) or not isinstance(bottom, list)
            or any(not isinstance(item, str) for item in selected + bottom)):
        raise RuntimeHalt('RULE_SECURITY_SEARCH_SELECTION_INVALID')
    deck = state['zones'][seat]['deck']
    revealed = list(reversed(deck[-2:]))
    eligible = [item for item in revealed if
        {'Red', 'Blue'}.intersection(context.card(seat, _physical_number(item)).to_dict()['colors'])]
    if (len(selected) != (1 if eligible else 0)
            or (selected and selected[0] not in eligible)
            or len(bottom) != len(revealed) - len(selected)
            or set(bottom) != set(revealed) - set(selected)
            or len(set(bottom)) != len(bottom)):
        raise RuntimeHalt('RULE_SECURITY_SEARCH_SELECTION_INVALID')
    expected = copy.deepcopy(before)
    new = expected['state']
    new['pending'] = []
    new_deck = new['zones'][seat]['deck']
    if revealed:
        del new_deck[-len(revealed):]
    new['zones'][seat]['hand'].extend(selected)
    new_deck[:0] = bottom
    placed = new['resolving_option']['stack']
    placed['played_turn'] = state['turn']
    new['battle'][seat][key] = placed
    new['resolving_option'] = None
    return expected, {'revealed': revealed, 'selected': selected,
        'bottom_order': bottom, 'placed_option': key,
        'bottom_order_convention': 'first element is bottommost',
        'status': 'EXPERIMENTAL', 'full_match_credit': 0}


def _battle_evolution(context, before, command, source):
    state = _ordinary_window(before, command)
    seat, args = command['seat'], command['args']
    if state['phase'] != 'MAIN' or args.get('cost_reduction', 0) != 0:
        raise RuntimeHalt('RULE_BATTLE_EVOLUTION_WINDOW_UNREVIEWED')
    source_key, target = args.get('source_key'), args.get('hand_key')
    stack = state['battle'][seat].get(source_key)
    if stack is None or target not in state['zones'][seat]['hand']:
        raise RuntimeHalt('RULE_BATTLE_EVOLUTION_SOURCE_MISSING')
    _reviewed_attack_statuses(context, state, seat, source_key, stack)
    base = stack['cards'][-1]
    base_def = context.card(seat, _physical_number(base)).to_dict()
    definition = context.card(seat, _physical_number(target))
    card_def = definition.to_dict()
    if base_def['type'] != 'Digimon' or card_def['type'] != 'Digimon':
        raise RuntimeHalt('RULE_BATTLE_EVOLUTION_TYPE_INVALID')
    routes = []
    for condition in card_def['normal_digivolution'].values():
        match = re.fullmatch(r'((?:(?:Red|Blue|Yellow|Green|Black|Purple|White)\s*)+)\s+(\d+) from Lv\.(\d+)', condition)
        if match is None:
            raise RuntimeHalt('RULE_PRINTED_ROUTE_UNREVIEWED: ' + condition)
        colors, cost, level = match.groups()
        accepted = set(re.findall(r'Red|Blue|Yellow|Green|Black|Purple|White', colors))
        if base_def['level'] == int(level) and accepted.intersection(base_def['colors']):
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
    for field in ('cost', 'basis', 'printed_condition', 'definition_sha256', 'status'):
        if field in args and args[field] != route[field]:
            raise RuntimeHalt('RULE_PRINTED_ROUTE_MISMATCH: ' + field)
    if route['cost'] > state['memory'] + 10:
        raise RuntimeHalt('RULE_EVOLUTION_COST_UNPAYABLE')
    for owner in ('A', 'B'):
        for observer_key, observer in state['battle'][owner].items():
            _reviewed_attack_statuses(context, state, owner, observer_key, observer)
            for physical in observer['cards']:
                text = context.card(owner, _physical_number(physical)).effect_text('main_text')
                for line in text.splitlines():
                    body = re.sub(r'^(?:\[[^\]]+\]\s*)+', '', line).split(',', 1)[0]
                    if body.startswith('When ') and re.search(r'\bdigivolv(?:e|es|ed|ing)\b|\bdraw(?:s|n)?\b', body, re.I):
                        raise RuntimeHalt('RULE_BATTLE_EVOLUTION_OBSERVER_UNREVIEWED: ' + physical)
    text = card_def['main_text']
    lines = [line for line in text.splitlines() if '[When Digivolving]' in line]
    if definition.number == 'EX13-022' and lines == [_EX13_022_PLAY]:
        effects = ['EX13-022.play_tamer']
    elif lines:
        raise RuntimeHalt('RULE_BATTLE_EVOLUTION_EFFECT_UNREVIEWED: ' + target)
    else:
        effects = []
    expected = copy.deepcopy(before)
    new = expected['state']
    new['memory'] -= route['cost']
    new['zones'][seat]['hand'].remove(target)
    evolved = new['battle'][seat].pop(source_key)
    evolved['cards'].append(target)
    new['battle'][seat][target] = evolved
    deck = new['zones'][seat]['deck']
    drawn = deck.pop() if deck else None
    if drawn is not None:
        new['zones'][seat]['hand'].append(drawn)
    for effect in effects:
        new['effect_sequence'] += 1
        new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
            'seat': seat, 'source': target, 'effect_id': effect, 'field': 'main_text',
            'instance': evolved['instance_id'], 'depth': 0,
            'trigger': {'kind': 'When Digivolving', 'card': target, 'previous_top': source_key},
            'usage': [state['turn'], seat, target, evolved['instance_id'], effect]})
    official = []
    for physical in (base, target):
        card_source = context.card(seat, _physical_number(physical)).to_dict()['official_source']
        official.append({'url': card_source['url'], 'sha256': card_source['sha256'],
            'locator': '#' + _physical_number(physical)
                + ' printed identity, evolution conditions and active effect text'})
    return expected, {'source_key': source_key, 'hand_key': target, 'route_index': index,
        'route': route, 'cost': route['cost'], 'cost_reduction': 0,
        'memory_after': new['memory'], 'drew': drawn is not None, 'drawn_card': drawn,
        'rules_source': _source_at(source, _BATTLE_EVOLUTION_LOCATOR),
        'card_sources': official, 'scope_context_id': context.matchup_id,
        'triggered_effects': effects, 'steps': [
            {'operation': 'DECLARE_DIGIVOLUTION', 'source': source_key,
             'target': target, 'route_index': index, 'route': route},
            {'operation': 'PAY_DIGIVOLUTION_COST', 'cost': route['cost'],
             'memory_before': state['memory'], 'memory_after': new['memory']},
            {'operation': 'STACK_DIGIMON', 'previous_top': source_key,
             'new_top': target, 'instance': evolved['instance_id']},
            {'operation': 'EVOLUTION_DRAW', 'card': drawn},
            {'operation': 'TRIGGER_WHEN_DIGIVOLVING', 'effects': effects}],
        'full_match_credit': 0}


def _reviewed_attack_statuses(context, state, owner, key, stack):
    statuses = stack['statuses']
    if not statuses:
        return
    grants = statuses.get('effect_grants')
    if set(statuses) != {'effect_grants'} or not isinstance(grants, list) or not grants:
        raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + key)
    for grant in grants:
        source_key = grant.get('source') if isinstance(grant, dict) else None
        target_key = grant.get('target') if isinstance(grant, dict) else None
        controller = grant.get('controller') if isinstance(grant, dict) else None
        if controller not in ('A', 'B') or target_key not in stack['cards']:
            raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + key)
        source_stack = next((item for item in state['battle'][controller].values()
            if source_key in item['cards']), None)
        if source_stack is None:
            raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + key)
        card = context.card(controller, _physical_number(source_key))
        created = grant.get('created_turn')
        if card.number == 'BT11-112' and owner == controller:
            expected_effect = {'keywords': ['Blocker', 'Evade']}
            source_kind = 'Tamer'
            text_ok = _BT11_112_ON_PLAY in card.effect_text('main_text').splitlines()
        elif card.number == 'EX13-022' and owner != controller:
            expected_effect = {'restrictions': ['cannot_suspend']}
            source_kind = 'Digimon'
            text_ok = _EX13_022_OBSERVER in card.effect_text('main_text').splitlines()
        else:
            raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + key)
        if (not isinstance(created, int)
                or created > state['turn'] or state['turn'] > created + 1
                or not text_ok
                or grant != {'controller': controller, 'source': source_key,
                    'source_instance': source_stack['instance_id'], 'source_field': 'main_text',
                    'source_kind': source_kind, 'source_definition_sha256': card.definition_sha256,
                    'source_text_sha256': hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
                    'target': target_key, 'target_owner': owner, 'target_instance': stack['instance_id'],
                    'effect': expected_effect, 'created_turn': created,
                    'expires': {'turn': created + 1,
                        'controller': 'B' if controller == 'A' else 'A', 'boundary': 'turn_end'}}):
            raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + key)


def _declare_attack(context, before, command, source):
    state = _ordinary_window(before, command)
    seat, args = command['seat'], command['args']
    if state['phase'] != 'MAIN' or args.get('target') != 'PLAYER':
        raise RuntimeHalt('RULE_ATTACK_TARGET_UNREVIEWED')
    key = args.get('attacker')
    stack = state['battle'][seat].get(key)
    if stack is None or stack['suspended']:
        raise RuntimeHalt('RULE_ATTACKER_NOT_READY')
    top = stack['cards'][-1]
    if (context.card(seat, _physical_number(top)).kind != 'Digimon'
            or stack['played_turn'] == state['turn']
            or stack['ready_since_turn'] is None
            or stack['ready_since_turn'] > state['turn']):
        raise RuntimeHalt('RULE_ATTACK_HISTORY_UNREVIEWED')
    _reviewed_attack_statuses(context, state, seat, key, stack)
    if stack['statuses'].get('cannot_suspend'):
        raise RuntimeHalt('RULE_ATTACK_STATUS_UNREVIEWED: ' + key)
    suspension_observers = []
    for owner in ('A', 'B'):
        for other_key, other_stack in state['battle'][owner].items():
            _reviewed_attack_statuses(context, state, owner, other_key, other_stack)
            for index, physical in enumerate(other_stack['cards']):
                field = 'main_text' if index == len(other_stack['cards']) - 1 else 'inherited_text'
                text = context.card(owner, _physical_number(physical)).effect_text(field)
                known_suspension = (_physical_number(physical) == 'BT11-112'
                    and field == 'main_text' and _BT11_112_SUSPEND in text.splitlines())
                known_unsuspend_cost = (_physical_number(physical) == 'EX13-069'
                    and field == 'main_text' and _EX13_069_UNSUSPEND in text.splitlines())
                if ('suspend' in text.lower().replace('unsuspend', '')
                        and not (known_suspension or known_unsuspend_cost)):
                    raise RuntimeHalt('RULE_ATTACK_ORIENTATION_EFFECT_UNREVIEWED: ' + physical)
                if known_suspension and owner == seat and 'Veedramon' in context.card(seat, _physical_number(top)).name:
                    suspension_observers.append((physical, other_stack['instance_id']))
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
    triggered = []
    for observer, instance in suspension_observers:
        new['effect_sequence'] += 1
        effect = 'BT11-112.suspend_reactivation'
        new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
            'seat': seat, 'source': observer, 'effect_id': effect, 'field': 'main_text',
            'instance': instance, 'depth': 0,
            'trigger': {'kind': 'DIGIMON_SUSPENDED', 'observed_instance': stack['instance_id'],
                'observed_source': top,
                'name_at_trigger': context.card(seat, _physical_number(top)).name,
                'suspended_before': False, 'suspended_after': True}, 'usage': []})
        triggered.append(effect)
    if effect_id is not None:
        usage = [state['turn'], seat, top, stack['instance_id'], effect_id]
        if usage not in state['once_used']:
            new['effect_sequence'] += 1
            new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
                'seat': seat, 'source': top, 'effect_id': effect_id,
                'field': 'main_text', 'instance': stack['instance_id'], 'depth': 0,
                'trigger': {'kind': 'When Attacking', 'attacker': top, 'target': 'PLAYER'},
                'usage': usage})
            triggered.append(effect_id)
    if triggered:
        result['triggered_effects'] = triggered
    return expected, result


def _attack_decline(context, before, command, source):
    state = before['state']
    attack = state['attack']
    kind = command['command']
    required = 'COUNTER' if kind == 'COUNTER_CHOICE' else 'BLOCK'
    if (state['terminal'] or state['phase'] != 'MAIN' or state['pending']
            or attack is None or attack['window'] != required
            or command['seat'] != attack['defender'] or state['active'] != attack['controller']):
        raise RuntimeHalt('RULE_ATTACK_CHOICE_WINDOW_INVALID: ' + kind)
    if command['args'].get('card') is not None:
        raise RuntimeHalt('RULE_ATTACK_CHOICE_CARD_UNREVIEWED: ' + kind)
    expected = copy.deepcopy(before)
    if kind == 'COUNTER_CHOICE':
        expected['state']['attack']['window'] = 'BLOCK'
        return expected, {'choice': 'EXPLICIT_COUNTER_DECLINE',
                          'window': 'BLOCK', 'strategy_status': 'UNTRAINED'}
    expected['state']['attack']['window'] = 'CONFIRM'
    return expected, {'choice': 'EXPLICIT_NO_BLOCK', 'window': 'CONFIRM'}


def _confirm_attack(context, before, command, source):
    state = before['state']
    attack = state['attack']
    seat = command['seat']
    if (state['terminal'] or state['phase'] != 'MAIN' or state['pending']
            or attack is None or attack['window'] != 'CONFIRM'
            or attack['controller'] != seat or state['active'] != seat
            or attack['target'] != 'PLAYER' or attack['checked'] is not None):
        raise RuntimeHalt('RULE_ATTACK_CONFIRM_WINDOW_INVALID')
    attacker = state['battle'][seat].get(attack['attacker'])
    if attacker is None or attacker['instance_id'] != attack['attacker_instance']:
        raise RuntimeHalt('RULE_ATTACKER_CHANGED_UNREVIEWED')
    defender = attack['defender']
    security = state['zones'][defender]['security']
    if not security:
        raise RuntimeHalt('RULE_DIRECT_WIN_CHECK_UNREVIEWED')
    checked = security[-1]
    card = context.card(defender, _physical_number(checked))
    definition = card.to_dict()
    if card.number == 'LM-057' and card.kind == 'Option':
        return _confirm_training_security(context, before, command, source, checked, card)
    if (card.number != 'EX13-069' or card.kind != 'Tamer'
            or card.effect_text('security_text') != _SECURITY_TAMER_TEXT
            or '[On Play]' in card.effect_text('main_text')):
        raise RuntimeHalt('RULE_SECURITY_CARD_UNREVIEWED: ' + checked)
    for stack in state['battle'][defender].values():
        for index, physical in enumerate(stack['cards']):
            field = 'main_text' if index == len(stack['cards']) - 1 else 'inherited_text'
            text = context.card(defender, _physical_number(physical)).effect_text(field)
            if 'Tamer' in text and ('played' in text or 'play' in text):
                raise RuntimeHalt('RULE_SECURITY_TAMER_REACTION_UNREVIEWED: ' + physical)
    expected = copy.deepcopy(before)
    new = expected['state']
    new['zones'][defender]['security'].pop()
    new['entity_sequence'] += 1
    new['battle'][defender][checked] = {'cards': [checked], 'suspended': False,
        'statuses': {}, 'instance_id': 'entity-' + str(new['entity_sequence']),
        'played_turn': new['turn'], 'ready_since_turn': new['turn'] + 1}
    new['attack']['checked'] = checked
    new['attack']['window'] = 'END'
    card_source = definition['official_source']
    locator = _source_at(source, _SECURITY_TAMER_LOCATOR)['locator']
    play = {'played_card': checked, 'cost': 0, 'memory_after': state['memory'],
        'full_match_credit': 0, 'rules_source': _source_at(source, _SECURITY_TAMER_LOCATOR),
        'card_source': {'url': card_source['url'], 'sha256': card_source['sha256'],
            'locator': '#' + card.number + ' printed type, play cost and main effects'},
        'scope_context_id': context.matchup_id, 'printed_trigger': 'On Play',
        'triggered_effects': [], 'play_method': 'EFFECT_WITHOUT_PAYING_COST',
        'assembly_materials': []}
    return expected, {'success': True, 'checked_card': checked,
        'security_effect': 'EX13-069.security_play', 'attacker_deleted': False,
        'security_card_deleted': False,
        'source': {'url': card_source['url'], 'sha256': card_source['sha256'],
            'locator': '#' + card.number + ' exact mandatory Security play; ' + locator},
        'play': play, 'steps': [
            {'operation': 'REVEAL_SECURITY_CARD', 'card': checked},
            {'operation': 'ACTIVATE_SECURITY_EFFECT_IMMEDIATELY',
             'effect_id': 'EX13-069.security_play', 'field': 'security_text',
             'source_area': None},
            {'operation': 'PLAY_CHECKED_TAMER', 'card': checked, 'cost': 0}],
        'full_match_credit': 0}


def _confirm_training_security(context, before, command, source, checked, card):
    state = before['state']
    defender = state['attack']['defender']
    if (card.effect_text('security_text') != _LM_057_SECURITY
            or state['resolving_option'] is not None or state['pending']
            or checked != state['zones'][defender]['security'][-1]):
        raise RuntimeHalt('RULE_SECURITY_OPTION_TEXT_UNREVIEWED: ' + checked)
    expected = copy.deepcopy(before)
    new = expected['state']
    new['zones'][defender]['security'].pop()
    new['entity_sequence'] += 1
    instance = 'entity-' + str(new['entity_sequence'])
    new['resolving_option'] = {'seat': defender, 'stack': {
        'cards': [checked], 'suspended': False, 'statuses': {},
        'instance_id': instance, 'played_turn': None, 'ready_since_turn': None}}
    new['attack']['checked'] = checked
    new['attack']['window'] = 'END'
    new['effect_sequence'] += 1
    effect = 'LM-057.main_search'
    new['pending'].append({'id': 'effect-' + str(new['effect_sequence']),
        'seat': defender, 'source': checked, 'effect_id': effect,
        'field': 'security_text', 'instance': instance, 'depth': 0,
        'trigger': {'kind': 'Security Check', 'card': checked}, 'usage': []})
    official = card.to_dict()['official_source']
    return expected, {'success': True, 'checked_card': checked,
        'security_effect': effect, 'attacker_deleted': False,
        'security_card_deleted': False, 'source': {
            'url': official['url'], 'sha256': official['sha256'],
            'locator': '#LM-057 exact printed Security search and placement'},
        'full_match_credit': 0}


def _end_attack(context, before, command, source):
    state = before['state']
    attack = state['attack']
    seat = command['seat']
    if (state['terminal'] or state['pending'] or attack is None
            or attack['window'] != 'END' or attack['controller'] != seat
            or state['active'] != seat or state['phase'] != 'MAIN'):
        raise RuntimeHalt('RULE_ATTACK_END_WINDOW_INVALID')
    for owner in ('A', 'B'):
        for stack in state['battle'][owner].values():
            for index, physical in enumerate(stack['cards']):
                field = 'main_text' if index == len(stack['cards']) - 1 else 'inherited_text'
                if '[End of Attack]' in context.card(owner,
                        _physical_number(physical)).effect_text(field):
                    raise RuntimeHalt('RULE_END_ATTACK_EFFECT_UNREVIEWED: ' + physical)
    expected = copy.deepcopy(before)
    expected['state']['attack'] = None
    if expected['state']['memory'] < 0:
        expected['state']['phase'] = 'END_OF_TURN'
    return expected, {'attack_ended': True, 'full_match_credit': 0}


class SemanticGate:
    """Reusable action checker registry; absent mechanics have no verdict."""
    def __init__(self, context, root, checkers=()):
        self.context = context
        self.root = Path(root).resolve()
        self.checkers = {'BEGIN_PREPARATION': _opening, 'REDRAW_CHOICE': _redraw,
                         'ADVANCE_PHASE': _advance_phase, 'BREEDING_CHOICE': _breeding_choice,
                         'BREEDING_EVOLUTION': _breeding_evolution, 'PASS_TURN': _pass_turn,
                         'FINISH_TURN': _finish_turn, 'PLAY_CARD': _play_card,
                         'BATTLE_EVOLUTION': _battle_evolution,
                         'RESOLVE_PENDING': _resolve_pending,
                         'DECLARE_ATTACK': _declare_attack,
                         'COUNTER_CHOICE': _attack_decline, 'BLOCK_CHOICE': _attack_decline,
                         'CONFIRM_ATTACK': _confirm_attack, 'END_ATTACK': _end_attack}
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
