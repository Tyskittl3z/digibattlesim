"""Encountered BT22-023 return effects and their explicit current choices."""
import hashlib
import re

from context_runtime import MechanicBinding, RuntimeHalt
from effect_scheduler import pending_options, source_stack
from match_context import require
from printed_triggers import effect_body


PLAY_EFFECT = 'BT22-023.on_play_return'
DIGIVOLVE_EFFECT = 'BT22-023.when_digivolving_return'
END_EFFECT = 'BT22-023.end_turn_unsuspend'
RETURN_LINE = ("[On Play] [When Digivolving] Return 1 of your opponent's level 4 "
               'or lower Digimon to the bottom of the deck.')
END_LINE = '[End of Your Turn] [Once Per Turn] 1 of your blue Digimon or Tamers may unsuspend.'
PLAY_SPECS = {'BT22-023': (PLAY_EFFECT, RETURN_LINE)}

# These active fields occur on the reviewed actual return targets. Lower
# EX1-013/P-138 are also safe during removal: returning is not unsuspending.
_RETURN_TOPS = frozenset(('P-138', 'EX1-013', 'EX13-019', 'EX13-017'))
_RETURN_INHERITED = frozenset(('EX1-013', 'P-138', 'EX13-019'))
_LEAVE_OBSERVER = re.compile(
    r'\b(?:when|would)\b[^\n]*\b(?:leave|leaves|left|removed|returned|trashed)\b', re.I)


def _source_window(runtime, seat, source_key, effect_id):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'BT22-023' or effect_id not in (PLAY_EFFECT, DIGIVOLVE_EFFECT, END_EFFECT):
        raise RuntimeHalt('AERO_SOURCE_OR_EFFECT_INVALID')
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('AERO_EFFECT_WINDOW_REQUIRED')
    if runtime.state.phase != 'SCENARIO':
        expected = (effect_id, seat, source_key, 'main_text')
        activated = getattr(runtime, '_activated_effect', None)
        in_handler = activated is not None and activated[:4] == expected and activated[4] is not None
        if not in_handler and not any(
                (record['effect_id'], record['seat'], record['source'], record['field']) == expected
                for record in pending_options(runtime, seat)):
            raise RuntimeHalt('AERO_EFFECT_WINDOW_REQUIRED')
    return source


def aero_choices(runtime, seat, source_key, effect_id):
    """Legal current choices, without replacing an unresolved effect by decline."""
    _source_window(runtime, seat, source_key, effect_id)
    if effect_id == END_EFFECT:
        targets = [key for key, stack in runtime.state.battle[seat].items()
                   if runtime.context.card(seat, stack.cards[-1].card_number).kind in ('Digimon', 'Tamer')
                   and 'Blue' in runtime.context.card(seat, stack.cards[-1].card_number).to_dict()['colors']]
        return [None] + sorted(targets)
    opponent = 'B' if seat == 'A' else 'A'
    targets = []
    for key, stack in runtime.state.battle[opponent].items():
        definition = runtime.context.card(opponent, stack.cards[-1].card_number)
        level = definition.to_dict()['level']
        if definition.kind == 'Digimon' and type(level) is int and level <= 4:
            targets.append(key)
    return sorted(targets) if targets else [None]


def _return_dependencies(runtime, owner, target_key):
    from effect_grants import validate_grants
    stack = runtime.state.battle[owner][target_key]
    if stack.statuses:
        validate_grants(runtime, owner, target_key)
    for index, card in enumerate(stack.cards):
        field = 'main_text' if index == len(stack.cards) - 1 else 'inherited_text'
        text = runtime.context.card(owner, card.card_number).effect_text(field)
        supported = _RETURN_TOPS if field == 'main_text' else _RETURN_INHERITED
        if text and card.card_number not in supported:
            raise RuntimeHalt('AERO_RETURN_DEPENDENCY_UNSUPPORTED: ' + card.card_number + ' ' + field)
    # Check actual active observers before moving any card. Returning the top
    # and trashing its sources must not bypass a leave-area replacement/trigger.
    for seat in ('A', 'B'):
        for observer in runtime.state.battle[seat].values():
            for index, card in enumerate(observer.cards):
                field = 'main_text' if index == len(observer.cards) - 1 else 'inherited_text'
                if observer is not stack and card.card_number == 'EX13-017' and field == 'inherited_text':
                    # Its printed replacement only protects "this Digimon";
                    # returning a different stack does not request that choice.
                    continue
                text = runtime.context.card(seat, card.card_number).effect_text(field)
                if any(_LEAVE_OBSERVER.search(effect_body(line)) for line in text.splitlines()):
                    raise RuntimeHalt('AERO_RETURN_DEPENDENCY_UNSUPPORTED: ' + card.card_number + ' ' + field)


def resolve_aero_return(runtime, seat, source_key, choice):
    activated = getattr(runtime, '_activated_effect', None)
    effect_id = activated[0] if activated else PLAY_EFFECT
    if choice not in aero_choices(runtime, seat, source_key, effect_id):
        raise RuntimeHalt('AERO_TARGET_INVALID')
    if choice is None:
        return {'target': None, 'processing': 'NO_ELIGIBLE_TARGET', 'full_match_credit': 0}
    opponent = 'B' if seat == 'A' else 'A'
    _return_dependencies(runtime, opponent, choice)
    stack = runtime.state.battle[opponent].pop(choice)
    top, lower = stack.cards[-1], stack.cards[:-1]
    runtime.state.zones[opponent]['deck'].insert(0, top)
    runtime.state.zones[opponent]['trash'].extend(lower)
    return {'target': choice, 'returned': top.key, 'trashed_sources': [card.key for card in lower],
            'processing': 'RETURNED_TO_DECK_BOTTOM', 'full_match_credit': 0}


def end_turn_usage(runtime, seat, source_key):
    """A once-per-turn use belongs to this physical source incarnation."""
    stack = source_stack(runtime, seat, source_key, 'main_text')
    if not stack.instance_id:
        runtime.state.entity_sequence += 1
        stack.instance_id = 'entity-' + str(runtime.state.entity_sequence)
    return (runtime.state.turn, seat, source_key, stack.instance_id, END_EFFECT)


def resolve_aero_end(runtime, seat, source_key, choice):
    if choice not in aero_choices(runtime, seat, source_key, END_EFFECT):
        raise RuntimeHalt('AERO_TARGET_INVALID')
    usage = end_turn_usage(runtime, seat, source_key)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED: ' + source_key)
    runtime.state.once_used.add(usage)
    if choice is None:
        return {'target': None, 'changed': False,
                'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
                'once_per_turn_consumed': True, 'full_match_credit': 0}
    from selected_mechanics import _set_orientation
    result = _set_orientation(runtime, seat, runtime.state.battle[seat][choice], False)
    return {'target': choice, **result, 'processing': 'UNSUSPEND_SELECTED',
            'once_per_turn_consumed': True, 'full_match_credit': 0}


def aero_bindings(context, root, rules):
    from selected_mechanics import _source_evidence
    bindings = []
    for card in context.cards:
        if card.number != 'BT22-023':
            continue
        text = card.effect_text('main_text')
        require(RETURN_LINE in text.splitlines(), 'BT22-023 return wording changed')
        require(END_LINE in text.splitlines(), 'BT22-023 end wording changed')
        evidence = _source_evidence(root, card.to_dict()['official_source'],
            '#BT22-023 On Play/When Digivolving/End of Your Turn; '
            'CR1-3-2,1-3-3,3-1-3,4-7-8,6-6,15-8-3-6,15-10-2-1,15-14-1-4,15-16-2,15-16-3,15-16-12')
        for effect, handler in ((PLAY_EFFECT, resolve_aero_return),
                                (DIGIVOLVE_EFFECT, resolve_aero_return),
                                (END_EFFECT, resolve_aero_end)):
            bindings.append(MechanicBinding(card.number, effect, 'main_text', card.definition_sha256,
                hashlib.sha256(text.encode()).hexdigest(), (evidence, rules), handler))
    return tuple(bindings)
