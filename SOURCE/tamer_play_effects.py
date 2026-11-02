"""EX13-022's encountered shared Tamer play and Tamer-play restriction."""
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding, RuntimeHalt
from effect_scheduler import pending_options, source_stack
from match_context import require


PLAY_EFFECT = 'EX13-022.play_tamer'
OBSERVER_EFFECT = 'EX13-022.tamer_play_restriction'
PLAY_LINE = ('[On Play] [When Digivolving] [When Attacking] [Once Per Turn] You may play 1 '
             'Tamer card with [Veedramon] in its text from your hand without paying the cost.')
OBSERVER_LINE = ("[All Turns] [Once Per Turn] When any of your Tamers are played, 1 of your "
                 "opponent's Digimon or Tamers can't suspend until their turn ends.")
PLAY_SPECS = {'EX13-022': (PLAY_EFFECT, PLAY_LINE)}


def known_play_observer(source_number, field, line):
    return source_number == 'EX13-022' and field == 'main_text' and line == OBSERVER_LINE


def _printed_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _printed_strings(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _printed_strings(item)


def _eligible_tamer(definition):
    if definition.kind != 'Tamer':
        return False
    data = definition.to_dict()
    # CR4-23-1/Q7264 reference printed information, never gained effects,
    # source URLs, verification notes or another card's text in runtime state.
    return any('Veedramon' in text for field in ('name', 'traits', 'main_text',
        'inherited_text', 'security_text', 'normal_digivolution', 'special_conditions')
        for text in _printed_strings(data[field]))


def _source_window(runtime, seat, source_key, effect_id):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'EX13-022' or effect_id not in (PLAY_EFFECT, OBSERVER_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_SOURCE_OR_EFFECT_INVALID')
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('TAMER_PLAY_WINDOW_REQUIRED')
    if runtime.state.phase != 'SCENARIO':
        expected = (effect_id, seat, source_key, 'main_text')
        activated = getattr(runtime, '_activated_effect', None)
        in_handler = activated is not None and activated[:4] == expected and activated[4] is not None
        if not in_handler and not any(
                (record['effect_id'], record['seat'], record['source'], record['field']) == expected
                for record in pending_options(runtime, seat)):
            raise RuntimeHalt('TAMER_PLAY_WINDOW_REQUIRED')


def tamer_play_choices(runtime, seat, source_key, effect_id):
    _source_window(runtime, seat, source_key, effect_id)
    if effect_id == PLAY_EFFECT:
        return [None] + sorted(card.key for card in runtime.state.zones[seat]['hand']
            if _eligible_tamer(runtime.context.card(seat, card.card_number)))
    opponent = 'B' if seat == 'A' else 'A'
    targets = sorted(key for key, stack in runtime.state.battle[opponent].items()
        if runtime.context.card(opponent, stack.cards[-1].card_number).kind in ('Digimon', 'Tamer'))
    return targets if targets else [None]


def tamer_play_usage(runtime, seat, source_key, effect_id):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'EX13-022' or effect_id not in (PLAY_EFFECT, OBSERVER_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_SOURCE_OR_EFFECT_INVALID')
    stack = source_stack(runtime, seat, source_key, 'main_text')
    if not stack.instance_id:
        runtime.state.entity_sequence += 1
        stack.instance_id = 'entity-' + str(runtime.state.entity_sequence)
    return (runtime.state.turn, seat, source_key, stack.instance_id, effect_id)


def collect_tamer_play_reactions(runtime, played_seat, physical):
    """Return one simultaneous raw group after actual Tamer placement.

    The caller combines these records with the played card's own On Play before
    queueing. Other actual live observers remain precise unsupported events.
    """
    runtime._source(played_seat, physical.key, 'main_text')
    if runtime.context.card(played_seat, physical.card_number).kind != 'Tamer':
        return []
    from basic_event_dependencies import require_inert_for_event
    records = []
    event = {'seat': played_seat, 'card_number': physical.card_number}
    for owner in ('A', 'B'):
        for stack in runtime.state.battle[owner].values():
            for index, source in enumerate(stack.cards):
                field = 'main_text' if index == len(stack.cards) - 1 else 'inherited_text'
                require_inert_for_event(runtime, owner, source, field, 'play_plain', event)
                definition = runtime.context.card(owner, source.card_number)
                if owner != played_seat:
                    continue
                if not any(known_play_observer(source.card_number, field, line)
                           for line in definition.effect_text(field).splitlines()):
                    continue
                runtime.registry.lookup(source.card_number, OBSERVER_EFFECT, field)
                usage = tamer_play_usage(runtime, owner, source.key, OBSERVER_EFFECT)
                if usage in runtime.state.once_used:
                    continue
                records.append({'seat': owner, 'source': source.key, 'effect_id': OBSERVER_EFFECT,
                    'field': field, 'usage': list(usage), 'trigger': {'kind': 'Tamer Played',
                        'played_card': physical.key, 'played_seat': played_seat}})
    return records


def _consume(runtime, seat, source_key, effect_id):
    usage = tamer_play_usage(runtime, seat, source_key, effect_id)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED: ' + source_key)
    runtime.state.once_used.add(usage)


def resolve_tamer_play(runtime, seat, source_key, choice):
    if choice not in tamer_play_choices(runtime, seat, source_key, PLAY_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_TARGET_INVALID')
    _consume(runtime, seat, source_key, PLAY_EFFECT)
    if choice is None:
        return {'played_card': None, 'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
                'once_per_turn_consumed': True, 'full_match_credit': 0}
    from main_actions import play_tamer_from_effect
    play = play_tamer_from_effect(runtime, seat, choice, Path(__file__).resolve().parents[1])
    return {'played_card': choice, 'play': play, 'processing': 'TAMER_PLAYED_WITHOUT_PAYING_COST',
            'once_per_turn_consumed': True, 'full_match_credit': 0}


def resolve_tamer_restriction(runtime, seat, source_key, choice):
    if choice not in tamer_play_choices(runtime, seat, source_key, OBSERVER_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_TARGET_INVALID')
    _consume(runtime, seat, source_key, OBSERVER_EFFECT)
    if choice is None:
        return {'target': None, 'processing': 'NO_ELIGIBLE_TARGET',
                'once_per_turn_consumed': True, 'full_match_credit': 0}
    from effect_grants import grant_effect
    opponent = 'B' if seat == 'A' else 'A'
    grant = grant_effect(runtime, seat, choice, {'restrictions': ['cannot_suspend']}, source_key,
                         'end_of_opponent_turn', target_owner=opponent)
    return {'target': choice, 'grant': grant, 'processing': 'RESTRICTION_APPLIED',
            'once_per_turn_consumed': True, 'full_match_credit': 0}


def tamer_play_bindings(context, root, rules):
    from selected_mechanics import _source_evidence
    bindings = []
    for card in context.cards:
        if card.number != 'EX13-022':
            continue
        text = card.effect_text('main_text')
        require(PLAY_LINE in text.splitlines() and OBSERVER_LINE in text.splitlines(),
                'EX13-022 Tamer-play wording changed')
        evidence = _source_evidence(root, card.to_dict()['official_source'],
            '#EX13-022 shared On Play/When Digivolving/When Attacking; All Turns Tamer play; '
            'Q7264; CR3-4-3,4-23-1,7-1-3,15-4-3-5-1,15-10-2-1,15-14-1,15-16-2,15-16-3')
        for effect, handler in ((PLAY_EFFECT, resolve_tamer_play), (OBSERVER_EFFECT, resolve_tamer_restriction)):
            bindings.append(MechanicBinding(card.number, effect, 'main_text', card.definition_sha256,
                hashlib.sha256(text.encode()).hexdigest(), (evidence, rules), handler))
    return tuple(bindings)
