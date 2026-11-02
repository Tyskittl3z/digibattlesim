"""Encountered Mental Training initial use; its later Delay is a separate action.

A used Option is outside all areas until its first Main effect resolves
(CR9-1-4). Reveals require that exact live, source-bound activation.
Deck arrays run bottom to top; the first bottom_order key is bottommost.
"""
from dataclasses import replace
import hashlib

from context_runtime import MechanicBinding, RuntimeHalt, Stack
from effect_scheduler import queue_effects
from match_context import require
from match_preparation import _rules


OPTION_SPECS = {
    'P-104': ('P-104.main_search',
        '[Main] Reveal the top 2 cards of your deck. Add 1 blue card among them to the hand. Return the rest to the bottom of the deck in any order. Then, place this card in the battle area.', 2),
}
_RULES_LOCATOR = ('Comprehensive rules v4.3: 3-4-6; 4-3-1; 4-22-1 through 4-22-4; '
                  '6-5-1-3; 9-1-1 through 9-1-9; 15-10-2-1; 15-15-3')


def option_colors_met(runtime, seat, card):
    """Shared use requirement, including a hatched Digi-Egg as a Digimon.

    Only field tops count: hand, trash, sources under a Digimon and existing
    Option cards in battle cannot supply a Digimon/Tamer color.
    """
    colors = set()
    for stack in runtime.state.battle[seat].values():
        top = runtime.context.card(seat, stack.cards[-1].card_number)
        if top.kind in ('Digimon', 'Tamer'):
            colors.update(top.to_dict()['colors'])
    if runtime.state.breeding[seat]:
        top = runtime.context.card(seat, runtime.state.breeding[seat][-1].card_number)
        if top.kind in ('Digi-Egg', 'Digimon'):
            colors.update(top.to_dict()['colors'])
    return set(card.to_dict()['colors']) <= colors


def _use(runtime, seat, choice, root):
    from battlefield_scope import assert_basic_board_scope
    from selected_contexts import require_selected_context
    from selected_mechanics import _source_evidence
    state = runtime.state
    locked = require_selected_context(runtime.context, root)
    if not runtime.allow_experimental:
        raise RuntimeHalt('UNREVIEWED_OPTION_ACTION')
    if seat != state.active or state.phase != 'MAIN' or state.memory < 0:
        raise RuntimeHalt('MAIN_OPTION_WINDOW_NOT_OPEN')
    if state.resolving_option is not None:
        raise RuntimeHalt('OPTION_USE_ALREADY_RESOLVING')
    hand = state.zones[seat]['hand']
    physical = next((c for c in hand if c.key == choice['hand_key']), None)
    if physical is None:
        raise RuntimeHalt('OPTION_NOT_IN_HAND')
    card = runtime.context.card(seat, physical.card_number)
    spec = OPTION_SPECS.get(card.number)
    if card.kind != 'Option' or spec is None:
        raise RuntimeHalt('OPTION_USE_UNIMPLEMENTED: ' + card.number)
    card_evidence = _source_evidence(root, card.to_dict()['official_source'],
        '#' + card.number + ' printed Option type, use cost, color and first Main effect').manifest()
    if not option_colors_met(runtime, seat, card):
        raise RuntimeHalt('OPTION_COLOR_REQUIREMENTS_NOT_MET: ' + card.number)
    assert_basic_board_scope(runtime, 'use_option', root)
    runtime.registry.lookup(card.number, spec[0], 'main_text')
    cost = card.to_dict()['play_cost']
    if type(cost) is not int or cost < 0 or cost > state.memory + 10:
        raise RuntimeHalt('OPTION_COST_NOT_PAYABLE')
    memory_before = state.memory
    state.memory -= cost
    hand.remove(physical)
    state.entity_sequence += 1
    stack = Stack([physical], instance_id='entity-' + str(state.entity_sequence))
    state.resolving_option = {'seat': seat, 'stack': stack}
    queue_effects(runtime, [{'seat': seat, 'source': physical.key, 'effect_id': spec[0],
        'field': 'main_text', 'trigger': {'kind': 'Option Use', 'card': physical.key}}])
    return {'used_card': physical.key, 'cost': cost, 'memory_after': state.memory,
            'rules_source': choice['rules'], 'card_source': card_evidence,
            'scope_context_id': locked.matchup_id, 'triggered_effects': [spec[0]],
            'steps': [{'operation': 'DECLARE_USE', 'card': physical.key},
                      {'operation': 'PAY_USE_COST', 'cost': cost,
                       'memory_before': memory_before, 'memory_after': state.memory},
                      {'operation': 'ACTIVATE_FIRST_MAIN', 'effect_id': spec[0],
                       'source_area': None}], 'full_match_credit': 0}


def choose_use_option(runtime, seat, hand_key, root):
    rules = {**_rules(root), 'locator': _RULES_LOCATOR}
    def use(trial, controller, choice):
        return _use(trial, controller, choice, root)
    return runtime._control_command('USE_OPTION', seat, {'hand_key': hand_key, 'rules': rules}, use)


def option_choices(runtime, seat, source_key):
    """Expose the current first-Main reveal only; do not inspect future uses."""
    runtime.context.deck(seat)
    current = runtime.state.resolving_option
    if (runtime.halted or runtime.state.terminal or current is None
            or current['seat'] != seat or current['stack'].cards[-1].key != source_key):
        raise RuntimeHalt('OPTION_ACTIVATION_WINDOW_REQUIRED')
    source = runtime._source(seat, source_key, 'main_text')
    spec = OPTION_SPECS.get(source.card_number)
    if spec is None:
        raise RuntimeHalt('OPTION_SOURCE_UNSUPPORTED')
    expected = (spec[0], seat, source_key, 'main_text')
    activated = getattr(runtime, '_activated_effect', None)
    in_handler = activated is not None and activated[:4] == expected and activated[4] is not None
    if not in_handler:
        from effect_scheduler import pending_options
        options = pending_options(runtime, seat)
        if len(options) != 1 or tuple(options[0][k] for k in ('effect_id', 'seat', 'source', 'field')) != expected:
            raise RuntimeHalt('OPTION_ACTIVATION_WINDOW_REQUIRED')
    revealed = list(reversed(runtime.state.zones[seat]['deck'][-spec[2]:]))
    selected = [[physical.key] for physical in revealed
                if 'Blue' in runtime.context.card(seat, physical.card_number).to_dict()['colors']]
    return {'revealed': [c.key for c in revealed], 'selections': sorted(selected) or [[]],
            'bottom_order_convention': 'first element is bottommost'}


def resolve_option(runtime, seat, source_key, choice):
    options = option_choices(runtime, seat, source_key)
    if not isinstance(choice, dict) or set(choice) != {'selected', 'bottom_order'}:
        raise RuntimeHalt('OPTION_CHOICE_INVALID')
    selected, bottom = choice['selected'], choice['bottom_order']
    if (not isinstance(selected, list) or not isinstance(bottom, list)
            or any(not isinstance(k, str) for k in selected + bottom)
            or len(set(selected)) != len(selected) or len(set(bottom)) != len(bottom)
            or selected not in options['selections']
            or set(bottom) != set(options['revealed']) - set(selected)):
        raise RuntimeHalt('OPTION_SELECTION_OR_ORDER_INVALID')
    deck = runtime.state.zones[seat]['deck']
    count = len(options['revealed'])
    cards = {c.key: c for c in deck[-count:]} if count else {}
    if count:
        del deck[-count:]
    runtime.state.zones[seat]['hand'].extend(cards[k] for k in selected)
    deck[:0] = [cards[k] for k in bottom]
    stack = runtime.state.resolving_option['stack']
    stack.played_turn = runtime.state.turn
    runtime.state.battle[seat][source_key] = stack
    runtime.state.resolving_option = None
    return {'revealed': options['revealed'], 'selected': selected, 'bottom_order': bottom,
            'bottom_order_convention': options['bottom_order_convention'],
            'placed_option': source_key,
            'steps': [{'operation': 'REVEAL', 'cards': options['revealed']},
                      {'operation': 'ADD_TO_HAND', 'cards': selected},
                      {'operation': 'RETURN_TO_DECK_BOTTOM', 'cards': bottom,
                       'bottom_order_convention': options['bottom_order_convention']},
                      {'operation': 'PLACE_OPTION_IN_BATTLE', 'card': source_key}],
            'status': 'EXPERIMENTAL', 'full_match_credit': 0}


def option_bindings(context, root, rules_evidence):
    from selected_mechanics import _source_evidence
    bindings = []
    for card in context.cards:
        if card.number not in OPTION_SPECS:
            continue
        effect, line, _ = OPTION_SPECS[card.number]
        require(line in card.effect_text('main_text').splitlines(),
                'Exact Option first Main text changed: ' + card.number)
        evidence = _source_evidence(root, card.to_dict()['official_source'],
            '#' + card.number + ' first Main effect; later Delay is a separate activation')
        bindings.append(MechanicBinding(card.number, effect, 'main_text', card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence, replace(rules_evidence, locator=_RULES_LOCATOR)), resolve_option))
    return tuple(bindings)
