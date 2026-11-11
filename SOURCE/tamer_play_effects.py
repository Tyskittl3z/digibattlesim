"""Encountered conditional Tamer plays and simultaneous Tamer-play reactions."""
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding, RuntimeHalt
from effect_scheduler import pending_options, source_stack
from match_context import require


PLAY_EFFECT = 'EX13-022.play_tamer'
OBSERVER_EFFECT = 'EX13-022.tamer_play_restriction'
VEEDRAMON_PLAY_EFFECT = 'BT22-022.play_tamer'
VEEDRAMON_PLAY_LINE = ('[When Digivolving] If you have 1 or fewer Tamers, you may play 1 '
                      'Tamer card with [Veedramon] in its text from your hand without paying the cost.')
EGG_EFFECT = 'EX13-002.tamer_play_unsuspend'
VEEMON_MEMORY_EFFECT = 'BT11-023.blue_tamer_memory'
VEEMON_MEMORY_LINE = '[Your Turn][Once Per Turn] When you play a blue Tamer, gain 1 memory.'
ULFORCE_PLAY_EFFECT = 'BT11-032.play_blue_tamer'
ULFORCE_PLAY_LINE = '[When Digivolving] You may play 1 blue Tamer card from your hand without paying the cost.'
ULFORCE_TAMER_EFFECT = 'BT11-032.blue_tamer_unsuspend'
ULFORCE_TAMER_LINE = '[Your Turn] When you play a blue Tamer, unsuspend this Digimon.'
ATTACK_TAMER_EFFECT = 'EX13-019.attack_play_tamer'
ATTACK_TAMER_LINE = ('[When Attacking] [Once Per Turn] You may play 1 Tamer card with '
                     '[Veedramon] in its text from your hand with the cost reduced by 2.')
EGG_LINE = ('[Your Turn] [Once Per Turn] When any of your blue Tamers are played, this '
            'Digimon with [Veedramon] in its name may unsuspend.')
PLAY_LINE = ('[On Play] [When Digivolving] [When Attacking] [Once Per Turn] You may play 1 '
             'Tamer card with [Veedramon] in its text from your hand without paying the cost.')
OBSERVER_LINE = ("[All Turns] [Once Per Turn] When any of your Tamers are played, 1 of your "
                 "opponent's Digimon or Tamers can't suspend until their turn ends.")
PLAY_SPECS = {'EX13-022': (PLAY_EFFECT, PLAY_LINE),
              'BT22-022': (VEEDRAMON_PLAY_EFFECT, VEEDRAMON_PLAY_LINE),
              'BT11-032': (ULFORCE_PLAY_EFFECT,ULFORCE_PLAY_LINE)}
PLAY_FILTERS = {PLAY_EFFECT:{'text':'Veedramon'},VEEDRAMON_PLAY_EFFECT:{'text':'Veedramon'},
               ULFORCE_PLAY_EFFECT:{'colors':('Blue',)},ATTACK_TAMER_EFFECT:{'text':'Veedramon'}}
TAMER_CHOICE_EFFECTS = frozenset([spec[0] for spec in PLAY_SPECS.values()]+[OBSERVER_EFFECT,EGG_EFFECT,ULFORCE_TAMER_EFFECT,VEEMON_MEMORY_EFFECT,ATTACK_TAMER_EFFECT])


def play_observer_effect(source_number, field, line):
    if source_number == 'EX13-022' and field == 'main_text' and line == OBSERVER_LINE:
        return OBSERVER_EFFECT
    if source_number == 'EX13-002' and field == 'inherited_text' and line == EGG_LINE:
        return EGG_EFFECT
    if source_number == 'BT11-032' and field == 'main_text' and line == ULFORCE_TAMER_LINE:
        return ULFORCE_TAMER_EFFECT
    if source_number == 'BT11-023' and field == 'inherited_text' and line == VEEMON_MEMORY_LINE:
        return VEEMON_MEMORY_EFFECT
    return None


def known_play_observer(source_number, field, line):
    return play_observer_effect(source_number, field, line) is not None


def _printed_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _printed_strings(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _printed_strings(item)


def _eligible_tamer(definition,effect_id=PLAY_EFFECT):
    if definition.kind != 'Tamer':
        return False
    data = definition.to_dict()
    filters=PLAY_FILTERS[effect_id]
    if filters.get('colors') and not set(filters['colors']).intersection(data['colors']):
        return False
    if 'text' not in filters:return True
    # CR4-23-1/Q7264 reference printed information, never gained effects,
    # source URLs, verification notes or another card's text in runtime state.
    return any(filters['text'] in text for field in ('name', 'traits', 'main_text',
        'inherited_text', 'security_text', 'normal_digivolution', 'special_conditions')
        for text in _printed_strings(data[field]))


def _source_window(runtime, seat, source_key, effect_id):
    field = 'inherited_text' if effect_id in (EGG_EFFECT, VEEMON_MEMORY_EFFECT) else 'main_text'
    source = runtime._source(seat, source_key, field)
    expected_number = 'EX13-002' if effect_id == EGG_EFFECT else 'BT11-023' if effect_id == VEEMON_MEMORY_EFFECT else (
        'BT22-022' if effect_id == VEEDRAMON_PLAY_EFFECT else 'BT11-032'
        if effect_id in (ULFORCE_PLAY_EFFECT,ULFORCE_TAMER_EFFECT) else 'EX13-019'
        if effect_id == ATTACK_TAMER_EFFECT else 'EX13-022')
    if source.card_number != expected_number or effect_id not in TAMER_CHOICE_EFFECTS:
        raise RuntimeHalt('TAMER_PLAY_SOURCE_OR_EFFECT_INVALID')
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('TAMER_PLAY_WINDOW_REQUIRED')
    if runtime.state.phase != 'SCENARIO':
        expected = (effect_id, seat, source_key, field)
        activated = getattr(runtime, '_activated_effect', None)
        in_handler = activated is not None and activated[:4] == expected and activated[4] is not None
        if not in_handler and not any(
                (record['effect_id'], record['seat'], record['source'], record['field']) == expected
                for record in pending_options(runtime, seat)):
            raise RuntimeHalt('TAMER_PLAY_WINDOW_REQUIRED')


def tamer_play_choices(runtime, seat, source_key, effect_id):
    _source_window(runtime, seat, source_key, effect_id)
    if effect_id == EGG_EFFECT:
        return [False,True]
    if effect_id in (ULFORCE_TAMER_EFFECT, VEEMON_MEMORY_EFFECT):
        return [None]
    if effect_id in PLAY_FILTERS:
        if effect_id == ATTACK_TAMER_EFFECT and (runtime.state.attack is None
                or runtime.state.attack['controller'] != seat):
            return [None]
        if effect_id == VEEDRAMON_PLAY_EFFECT and sum(
                runtime.context.card(seat,s.cards[-1].card_number).kind == 'Tamer'
                for s in runtime.state.battle[seat].values()) > 1:
            return [None]
        return [None] + sorted(card.key for card in runtime.state.zones[seat]['hand']
            if _eligible_tamer(runtime.context.card(seat, card.card_number),effect_id))
    opponent = 'B' if seat == 'A' else 'A'
    targets = sorted(key for key, stack in runtime.state.battle[opponent].items()
        if runtime.context.card(opponent, stack.cards[-1].card_number).kind in ('Digimon', 'Tamer'))
    return targets if targets else [None]


def tamer_play_usage(runtime, seat, source_key, effect_id):
    field = 'inherited_text' if effect_id in (EGG_EFFECT, VEEMON_MEMORY_EFFECT) else 'main_text'
    source = runtime._source(seat, source_key, field)
    if not ((source.card_number == 'EX13-022' and effect_id in (PLAY_EFFECT,OBSERVER_EFFECT))
            or (source.card_number == 'EX13-002' and effect_id == EGG_EFFECT)
            or (source.card_number == 'EX13-019' and effect_id == ATTACK_TAMER_EFFECT)
            or (source.card_number == 'BT11-023' and effect_id == VEEMON_MEMORY_EFFECT)):
        raise RuntimeHalt('TAMER_PLAY_SOURCE_OR_EFFECT_INVALID')
    stack = source_stack(runtime, seat, source_key, field)
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
                effects = [play_observer_effect(source.card_number,field,line)
                           for line in definition.effect_text(field).splitlines()]
                effects = [effect for effect in effects if effect is not None]
                if not effects:
                    continue
                effect = effects[0]
                if effect == EGG_EFFECT and (owner != runtime.state.active
                        or 'Blue' not in runtime.context.card(played_seat,physical.card_number).to_dict()['colors']
                        or 'Veedramon' not in runtime.context.card(owner,stack.cards[-1].card_number).name):
                    continue
                if effect in (ULFORCE_TAMER_EFFECT, VEEMON_MEMORY_EFFECT) and (owner != runtime.state.active
                        or 'Blue' not in runtime.context.card(played_seat,physical.card_number).to_dict()['colors']):
                    continue
                runtime.registry.lookup(source.card_number, effect, field)
                usage = () if effect == ULFORCE_TAMER_EFFECT else tamer_play_usage(runtime, owner, source.key, effect)
                if usage in runtime.state.once_used:
                    continue
                records.append({'seat': owner, 'source': source.key, 'effect_id': effect,
                    'field': field, 'usage': list(usage), 'trigger': {'kind': 'Tamer Played',
                        'played_card': physical.key, 'played_seat': played_seat}})
    return records


def _consume(runtime, seat, source_key, effect_id):
    usage = tamer_play_usage(runtime, seat, source_key, effect_id)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED: ' + source_key)
    runtime.state.once_used.add(usage)


def resolve_tamer_play(runtime, seat, source_key, choice):
    activated=getattr(runtime,'_activated_effect',None)
    effect=activated[0] if activated is not None else PLAY_EFFECT
    if choice not in tamer_play_choices(runtime, seat, source_key, effect):
        raise RuntimeHalt('TAMER_PLAY_TARGET_INVALID')
    if effect == VEEDRAMON_PLAY_EFFECT and sum(
            runtime.context.card(seat,s.cards[-1].card_number).kind=='Tamer'
            for s in runtime.state.battle[seat].values())>1:
        return {'played_card':None,'processing':'CONDITION_NOT_MET','full_match_credit':0}
    opt = effect in (PLAY_EFFECT, ATTACK_TAMER_EFFECT)
    if opt:_consume(runtime, seat, source_key, effect)
    if choice is None:
        return {'played_card': None, 'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
                'once_per_turn_consumed': opt, 'full_match_credit': 0}
    from main_actions import play_tamer_from_effect
    play = play_tamer_from_effect(runtime, seat, choice, Path(__file__).resolve().parents[1])
    processing = ('TAMER_PLAYED_WITH_COST_REDUCED_BY_2' if effect == ATTACK_TAMER_EFFECT
                  else 'TAMER_PLAYED_WITHOUT_PAYING_COST')
    return {'played_card': choice, 'play': play, 'processing': processing,
            'once_per_turn_consumed': opt, 'full_match_credit': 0}


def resolve_egg_unsuspend(runtime,seat,source_key,choice):
    if type(choice) is not bool or choice not in tamer_play_choices(runtime,seat,source_key,EGG_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_TARGET_INVALID')
    _consume(runtime,seat,source_key,EGG_EFFECT)
    if not choice:
        return {'changed':False,'processing':'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
                'once_per_turn_consumed':True,'full_match_credit':0}
    from selected_mechanics import _set_orientation
    result=_set_orientation(runtime,seat,source_stack(runtime,seat,source_key,'inherited_text'),False)
    return {**result,'processing':'UNSUSPEND_SELECTED','once_per_turn_consumed':True,'full_match_credit':0}


def resolve_ulforce_tamer_unsuspend(runtime,seat,source_key,choice):
    if choice is not None or choice not in tamer_play_choices(runtime,seat,source_key,ULFORCE_TAMER_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_TARGET_INVALID')
    from selected_mechanics import _set_orientation
    result=_set_orientation(runtime,seat,source_stack(runtime,seat,source_key,'main_text'),False)
    return {**result,'processing':'MANDATORY_SELF_UNSUSPEND','full_match_credit':0}


def resolve_veemon_tamer_memory(runtime, seat, source_key, choice):
    if choice is not None or choice not in tamer_play_choices(runtime, seat, source_key, VEEMON_MEMORY_EFFECT):
        raise RuntimeHalt('TAMER_PLAY_TARGET_INVALID')
    _consume(runtime, seat, source_key, VEEMON_MEMORY_EFFECT)
    before = runtime.state.memory
    runtime.state.memory = min(10, before + 1)
    return {'memory_before': before, 'memory_after': runtime.state.memory,
            'gained': runtime.state.memory - before, 'once_per_turn_consumed': True,
            'processing': 'INHERITED_BLUE_TAMER_PLAY_MEMORY', 'full_match_credit': 0}


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
        if card.number not in ('EX13-022','BT22-022','EX13-002','BT11-032','BT11-023','EX13-019'):
            continue
        field='inherited_text' if card.number in ('EX13-002','BT11-023') else 'main_text'
        text = card.effect_text(field)
        specs = ([(PLAY_EFFECT,PLAY_LINE,resolve_tamer_play),(OBSERVER_EFFECT,OBSERVER_LINE,resolve_tamer_restriction)]
            if card.number=='EX13-022' else [(VEEDRAMON_PLAY_EFFECT,VEEDRAMON_PLAY_LINE,resolve_tamer_play)]
            if card.number=='BT22-022' else [(ULFORCE_PLAY_EFFECT,ULFORCE_PLAY_LINE,resolve_tamer_play),
                (ULFORCE_TAMER_EFFECT,ULFORCE_TAMER_LINE,resolve_ulforce_tamer_unsuspend)]
            if card.number=='BT11-032' else [(VEEMON_MEMORY_EFFECT,VEEMON_MEMORY_LINE,resolve_veemon_tamer_memory)]
            if card.number=='BT11-023' else [(ATTACK_TAMER_EFFECT,ATTACK_TAMER_LINE,resolve_tamer_play)]
            if card.number=='EX13-019' else [(EGG_EFFECT,EGG_LINE,resolve_egg_unsuspend)])
        require(all(line in text.splitlines() for _,line,_ in specs),card.number+' Tamer-play wording changed')
        evidence = _source_evidence(root, card.to_dict()['official_source'],
            '#'+card.number+' actual Tamer-play text; EX13-022 Q7264 where applicable; '
            'CR1-3-3,3-4-3,4-23-1,7-1-3,15-4-3-5-1,15-8-3-9,15-10-2-1,15-14-1,15-16-2,15-16-3')
        for effect, line, handler in specs:
            bindings.append(MechanicBinding(card.number, effect, field, card.definition_sha256,
                hashlib.sha256(text.encode()).hexdigest(), (evidence, rules), handler))
    return tuple(bindings)
