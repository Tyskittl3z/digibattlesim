"""First selected EX13 mechanics; experimental scenarios, never full matches.

Encountered orientation processing, inherited reactions and Rina reactions are implemented.
Persistent-status rule checks, Assembly, return-to-deck and other abilities
remain unsupported; all bindings are experimental and unreviewed.
An encountered dependency halts before the transaction commits.
"""
import hashlib
import json
from pathlib import Path
import re

from context_runtime import MechanicBinding, MechanicRegistry, OfficialEvidence, RuntimeHalt
from match_context import require
from effect_scheduler import queue_effects, source_stack
from printed_triggers import effect_body,effect_headers

ORIENTATION_EFFECT = 'EX13-023.orientation'
OMNIMON_END_EFFECT = 'BT20-102.end_turn_rush_attack'
OMNIMON_END_LINE = ('[End of Your Turn] [Once Per Turn] 1 of your Digimon may gain '
    '＜Rush＞ for the turn and attack without suspending.')
ORIENTATION_LINE = ('[On Play] [When Digivolving] [When Attacking] [Once Per Turn] '
                    '1 of your Digimon may change orientation.')
INHERITED_REACTIONS = {
    'EX13-022': ('EX13-022.inherited_unsuspend', '[All Turns] [Once Per Turn] When this Digimon with [Veedramon] in its name suspends, it may unsuspend.'),
    'BT22-023': ('BT22-023.inherited_unsuspend', '[All Turns] [Once Per Turn] When this Digimon with [Veedramon] in its name suspends, if you have a blue Tamer, this Digimon may unsuspend.'),
    'P-138': ('P-138.unsuspend_memory', '[Your Turn] [Once Per Turn] When this Digimon becomes unsuspended, gain 1 memory.'),
    'EX1-013': ('EX1-013.unsuspend_memory', '[Your Turn][Once Per Turn] When this Digimon becomes unsuspended during your main phase, gain 1 memory.'),
}
PHASE_EFFECTS = {
    'BT22-085': ('BT22-085.start_turn_memory','Start of Your Turn',
                 '[Start of Your Turn] If you have 2 or less memory, set it to 3.'),
    'BT19-080': ('BT19-080.start_turn_memory','Start of Your Turn',
                 '[Start of Your Turn] If you have 2 or less memory, set it to 3.'),
    'BT19-007': ('BT19-007.start_main_memory','Start of Your Main Phase',
                 '[Start of Your Main Phase] If you have [Takato Matsuki] or [Calumon], gain 1 memory.'),
    'EX13-069': ('EX13-069.start_main_memory','Start of Your Main Phase',
                 '[Start of Your Main Phase] If you have a Digimon with [Veemon] or [Veedramon] in its name, gain 1 memory.'),
}
RINA_JAMMING_EFFECT = 'BT22-085.attack_jamming'
RINA_JAMMING_LINE = ('[Your Turn] When one of your Digimon with [Veedramon] in its name attacks, '
                     'by returning this Tamer to the hand, that Digimon gains ＜Jamming＞ for the turn.')
BT12_UNSUSPEND_EFFECT = 'BT12-029.when_digivolving_unsuspend'
BT12_UNSUSPEND_LINE = '[When Digivolving] Unsuspend this Digimon or 1 of your blue Tamers.'
BT12_RETURN_EFFECT = 'BT12-029.unsuspend_return_lowest'
BT12_RETURN_LINE = ('[All Turns][Once Per Turn] When this Digimon becomes unsuspended, '
                    'if you have a blue Tamer in play or this Digimon has [UlforceVeedramon] '
                    'in its digivolution cards, return 1 of your opponent’s Digimon with the '
                    'lowest level to its owner’s hand.')


def bt12_unsuspend_choices(runtime, seat, source_key):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'BT12-029':
        raise RuntimeHalt('BT12_UNSUSPEND_SOURCE_INVALID')
    expected = (BT12_UNSUSPEND_EFFECT, seat, source_key, 'main_text')
    activated = getattr(runtime, '_activated_effect', None)
    if activated is not None and activated[:4] == expected and activated[4] is not None:
        record = getattr(runtime, '_activated_pending', None)
    else:
        from effect_scheduler import pending_options
        record = next((p for p in pending_options(runtime, seat)
                       if tuple(p[k] for k in ('effect_id','seat','source','field')) == expected), None)
    stack = source_stack(runtime, seat, source_key, 'main_text')
    trigger = record['trigger'] if record is not None else {}
    reactivated = (trigger.get('kind') == 'RINA_REACTIVATED_WHEN_DIGIVOLVING'
        and trigger.get('parent_effect') == 'BT11-112.suspend_reactivation'
        and trigger.get('suspension_paid') is True
        and trigger.get('current_source') == source_key
        and trigger.get('observed_instance') == stack.instance_id)
    if (record is None or record['instance'] != stack.instance_id
            or not (trigger.get('kind') == 'When Digivolving' or reactivated)):
        raise RuntimeHalt('BT12_UNSUSPEND_WINDOW_REQUIRED')
    tamers = sorted(key for key, item in runtime.state.battle[seat].items()
                    if runtime.context.card(seat, item.cards[-1].card_number).kind == 'Tamer'
                    and 'Blue' in runtime.context.card(seat,item.cards[-1].card_number).to_dict()['colors'])
    return [source_key, *tamers]


def resolve_bt12_unsuspend(runtime, seat, source_key, choice):
    options = bt12_unsuspend_choices(runtime, seat, source_key)
    if choice not in options:
        raise RuntimeHalt('BT12_UNSUSPEND_TARGET_INVALID')
    target = runtime.state.battle[seat][choice]
    result = _set_orientation(runtime, seat, target, False)
    return {'target':choice, **result, 'processing':'UNSUSPEND_PRINTED_CHOICE'}


def bt12_return_choices(runtime, seat, source_key):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'BT12-029':
        raise RuntimeHalt('BT12_RETURN_SOURCE_INVALID')
    expected = (BT12_RETURN_EFFECT, seat, source_key, 'main_text')
    activated = getattr(runtime, '_activated_effect', None)
    if activated is not None and activated[:4] == expected and activated[4] is not None:
        record = getattr(runtime, '_activated_pending', None)
    else:
        from effect_scheduler import pending_options
        record = next((p for p in pending_options(runtime, seat)
                       if tuple(p[k] for k in ('effect_id','seat','source','field')) == expected), None)
    stack = source_stack(runtime, seat, source_key, 'main_text')
    trigger = record['trigger'] if record is not None else {}
    if (record is None or record['instance'] != stack.instance_id
            or trigger.get('kind') != 'ORIENTATION_CHANGED'
            or trigger.get('entity') != source_key
            or trigger.get('suspended_before') is not True
            or trigger.get('suspended_after') is not False):
        raise RuntimeHalt('BT12_RETURN_WINDOW_REQUIRED')
    blue_tamer = any(runtime.context.card(seat, item.cards[-1].card_number).kind == 'Tamer'
        and 'Blue' in runtime.context.card(seat, item.cards[-1].card_number).to_dict()['colors']
        for item in runtime.state.battle[seat].values())
    ulforce_source = any('UlforceVeedramon' in runtime.context.card(seat, card.card_number).name
                         for card in stack.cards[:-1])
    if not (blue_tamer or ulforce_source):
        return [None]
    other = 'B' if seat == 'A' else 'A'
    targets = [(key, runtime.context.card(other, item.cards[-1].card_number).to_dict()['level'])
               for key, item in runtime.state.battle[other].items()
               if runtime.context.card(other, item.cards[-1].card_number).kind == 'Digimon']
    if not targets:
        return [None]
    if any(type(level) is not int for _, level in targets):
        raise RuntimeHalt('BT12_RETURN_LEVEL_UNVERIFIED')
    minimum = min(level for _, level in targets)
    return sorted(key for key, level in targets if level == minimum)


def resolve_bt12_return(runtime, seat, source_key, choice):
    if choice not in bt12_return_choices(runtime, seat, source_key):
        raise RuntimeHalt('BT12_RETURN_TARGET_INVALID')
    usage = _usage(runtime, seat, source_key, BT12_RETURN_EFFECT)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED: ' + source_key)
    runtime.state.once_used.add(usage)
    if choice is None:
        return {'processing': 'CONDITION_OR_TARGET_UNAVAILABLE', 'returned': None,
                'trashed_sources': [], 'once_per_turn_consumed': True, 'full_match_credit': 0}
    from return_effects import return_to_hand
    other = 'B' if seat == 'A' else 'A'
    moved = return_to_hand(runtime, seat, other, choice, halt_prefix='BT12_RETURN')
    return {'processing': 'RETURN_LOWEST_LEVEL_DIGIMON_TO_HAND', **moved,
            'once_per_turn_consumed': True, 'full_match_credit': 0}


def selected_pending_choices(runtime, seat, selected):
    """Choice grammar for encountered registered mechanics outside older packs."""
    from return_effects import REPLACEMENT_EFFECT, return_replacement_choices
    if selected['effect_id'] == REPLACEMENT_EFFECT:
        return return_replacement_choices(runtime, seat, selected['source'])
    if selected['effect_id'] == BT12_UNSUSPEND_EFFECT:
        return bt12_unsuspend_choices(runtime, seat, selected['source'])
    if selected['effect_id'] == BT12_RETURN_EFFECT:
        return bt12_return_choices(runtime, seat, selected['source'])
    if selected['effect_id'] == OMNIMON_END_EFFECT:
        return omnimon_end_choices(runtime, seat, selected['source'])
    return None


def omnimon_end_choices(runtime, seat, source_key):
    source = runtime._source(seat, source_key, 'main_text')
    if (source.card_number != 'BT20-102' or seat != runtime.state.active
            or runtime.state.phase != 'END_OF_TURN'):
        raise RuntimeHalt('OMNIMON_END_WINDOW_REQUIRED')
    from effect_scheduler import pending_options
    expected = (OMNIMON_END_EFFECT, seat, source_key, 'main_text')
    activated = getattr(runtime, '_activated_effect', None)
    if activated is None or activated[:4] != expected or activated[4] is None:
        if not any(tuple(p[k] for k in ('effect_id', 'seat', 'source', 'field')) == expected
                   for p in pending_options(runtime, seat)):
            raise RuntimeHalt('OMNIMON_END_PENDING_REQUIRED')
    opponent = 'B' if seat == 'A' else 'A'
    targets = ['PLAYER'] + [key for key, stack in runtime.state.battle[opponent].items()
        if stack.suspended and runtime.context.card(opponent, stack.cards[-1].card_number).kind == 'Digimon']
    return [None] + [
        {'kind': 'DECLARE_ATTACK', 'attacker': key, 'target': target}
        for key, stack in sorted(runtime.state.battle[seat].items())
        if runtime.context.card(seat, stack.cards[-1].card_number).kind == 'Digimon'
        for target in targets]


def resolve_omnimon_end(runtime, seat, source_key, choice, root):
    if choice not in omnimon_end_choices(runtime, seat, source_key):
        raise RuntimeHalt('OMNIMON_END_ATTACK_CHOICE_INVALID')
    usage = _usage(runtime, seat, source_key, OMNIMON_END_EFFECT)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('OMNIMON_END_ALREADY_USED')
    runtime.state.once_used.add(usage)
    if choice is None:
        return {'processing': 'OPTIONAL_ATTACK_DECLINED', 'attacker': None,
                'once_per_turn_consumed': True, 'full_match_credit': 0}
    from effect_grants import grant_effect
    grant = grant_effect(runtime, seat, choice['attacker'], {'keywords': ['Rush']},
        source_key, duration='end_of_controller_turn')
    from attack_flow import trusted_end_attack
    attack = trusted_end_attack(runtime, seat, choice['attacker'], choice['target'], root)
    return {'processing': 'RUSH_AND_ATTACK_WITHOUT_SUSPENDING',
        'attacker': choice['attacker'], 'target': choice['target'],
        'rush_grant': grant, 'attack': attack, 'once_per_turn_consumed': True,
        'full_match_credit': 0}


def collect_rina_attack_jamming(runtime, seat, attacker_key):
    """Collect each live Rina's printed attack trigger without choosing its cost."""
    stack = runtime.state.battle[seat][attacker_key]
    definition = runtime.context.card(seat, stack.cards[-1].card_number)
    if definition.kind != 'Digimon' or 'Veedramon' not in definition.name:
        return []
    effects = []
    for key, tamer in runtime.state.battle[seat].items():
        source = tamer.cards[-1]
        if source.card_number != 'BT22-085':
            continue
        if runtime.context.card(seat, source.card_number).effect_text('main_text').splitlines()[-1] != RINA_JAMMING_LINE:
            raise RuntimeHalt('RINA_JAMMING_TEXT_CHANGED')
        runtime.registry.lookup(source.card_number, RINA_JAMMING_EFFECT, 'main_text')
        effects.append({'seat':seat, 'source':key, 'effect_id':RINA_JAMMING_EFFECT,
                        'field':'main_text', 'trigger':{'kind':'WHEN_ATTACKING',
                        'attacker':attacker_key, 'attacker_instance':stack.instance_id}})
    return effects


def rina_jamming_choices(runtime, seat, source_key):
    pending = next((p for p in runtime.state.pending if p['seat']==seat
                    and p['source']==source_key and p['effect_id']==RINA_JAMMING_EFFECT), None)
    if pending is None:
        pending = getattr(runtime, '_activated_pending', None)
    if pending is None or pending['effect_id'] != RINA_JAMMING_EFFECT:
        raise RuntimeHalt('RINA_JAMMING_WINDOW_REQUIRED')
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'BT22-085' or runtime.state.active != seat:
        raise RuntimeHalt('RINA_JAMMING_SOURCE_INVALID')
    attack = runtime.state.attack
    if attack is None or attack['controller'] != seat:
        return [None]
    trigger = pending['trigger']
    attacker = runtime.state.battle[seat].get(trigger.get('attacker'))
    if (attacker is None or attacker.instance_id != trigger.get('attacker_instance')
            or attack['attacker_instance'] != attacker.instance_id):
        return [None]
    return [None, source_key]


def resolve_rina_attack_jamming(runtime, seat, source_key, choice):
    options = rina_jamming_choices(runtime, seat, source_key)
    if choice not in options:
        raise RuntimeHalt('RINA_JAMMING_CHOICE_INVALID')
    if choice is None:
        return {'processing':'OPTIONAL_COST_DECLINED', 'returned':None, 'granted':False}
    pending = getattr(runtime, '_activated_pending', None)
    if pending is None or pending['source'] != source_key:
        raise RuntimeHalt('RINA_JAMMING_PENDING_REQUIRED')
    attacker_key = pending['trigger']['attacker']
    tamer = runtime.state.battle[seat][source_key]
    if len(tamer.cards) != 1 or runtime.context.card(seat,tamer.cards[-1].card_number).kind != 'Tamer':
        raise RuntimeHalt('RINA_JAMMING_RETURN_SOURCE_INVALID')
    from effect_grants import grant_effect
    grant = grant_effect(runtime, seat, attacker_key, {'keywords':['Jamming']}, source_key,
                         duration='end_of_controller_turn')
    runtime.state.battle[seat].pop(source_key)
    runtime.state.zones[seat]['hand'].append(tamer.cards[-1])
    return {'processing':'RETURN_THIS_TAMER_FOR_JAMMING', 'returned':source_key,
            'attacker':attacker_key, 'grant':grant, 'granted':True}


def orientation_candidates(runtime, seat, source_key):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'EX13-023':
        raise RuntimeHalt('ORIENTATION_SOURCE_MISMATCH')
    return [None] + sorted(key for key, stack in runtime.state.battle[seat].items()
                          if runtime.context.card(seat, stack.cards[-1].card_number).kind == 'Digimon')


def _orientation_event_matches(runtime,owner,observer,line,changed_seat,changed_stack,
                               suspended_before,suspended_after):
    """Match only the triggering clause of this actual orientation change."""
    if suspended_before==suspended_after:return False
    headers=effect_headers(line)
    if ('Your Turn' in headers and owner!=runtime.state.active
            or "Opponent's Turn" in headers and owner==runtime.state.active):
        return False
    clause=effect_body(line).split(',',1)[0]
    if not clause.startswith('When '):return False
    word=r'\bsuspend(?:s|ed)?\b' if suspended_after else r'\bunsuspend(?:s|ed)?\b'
    if not re.search(word,clause,re.I):return False
    changed=runtime.context.card(changed_seat,changed_stack.cards[-1].card_number)
    if 'Digimon' in clause and changed.kind!='Digimon':return False
    if 'Tamer' in clause and changed.kind!='Tamer':return False
    if ('this Digimon' in clause or 'this Tamer' in clause) and observer is not changed_stack:
        return False
    if 'opponent' in clause.lower():
        if owner==changed_seat:return False
    elif 'your ' in clause.lower() and owner!=changed_seat:
        return False
    if 'blue' in clause.lower() and 'Blue' not in changed.to_dict()['colors']:return False
    if 'main phase' in clause.lower() and runtime.state.phase!='MAIN':return False
    names=re.findall(r'\[([^\]]+)\]',clause)
    if names and not any(name in changed.name for name in names):return False
    return True


def _orientation_dependencies(runtime,changed_seat,changed_stack,suspended_before,suspended_after):
    """Require handlers only for observers of this actual entity and change."""
    for seat in ('A', 'B'):
        for stack in runtime.state.battle[seat].values():
            for index, card in enumerate(stack.cards):
                field_ = 'main_text' if index == len(stack.cards) - 1 else 'inherited_text'
                text = runtime.context.card(seat, card.card_number).effect_text(field_)
                for line in text.splitlines():
                    if not _orientation_event_matches(runtime,seat,stack,line,changed_seat,
                                                      changed_stack,suspended_before,suspended_after):
                        continue
                    known = INHERITED_REACTIONS.get(card.card_number)
                    if field_ == 'inherited_text' and known and text == known[1]:
                        runtime.registry.lookup(card.card_number,known[0],field_)
                        continue
                    from rina_unsuspend_effects import (known_rina_orientation_observer,
                        BT11_MEMORY_EFFECT,EX13_DRAW_EFFECT)
                    if known_rina_orientation_observer(card.card_number,field_,line):
                        effect=BT11_MEMORY_EFFECT if card.card_number=='BT11-112' else EX13_DRAW_EFFECT
                        runtime.registry.lookup(card.card_number,effect,field_)
                        continue
                    from rina_reactivation import known_rina_suspension_observer,REACTIVATION_EFFECT
                    if known_rina_suspension_observer(card.card_number,field_,line):
                        runtime.registry.lookup(card.card_number,REACTIVATION_EFFECT,field_)
                        continue
                    if (card.card_number=='BT12-029' and field_=='main_text'
                            and line==BT12_RETURN_LINE):
                        runtime.registry.lookup(card.card_number,BT12_RETURN_EFFECT,field_)
                        continue
                    raise RuntimeHalt('ORIENTATION_DEPENDENT_TRIGGER_UNIMPLEMENTED: '
                                      + card.card_number + ' ' + field_+' source='+card.key)
            if set(stack.statuses) - {'cannot_suspend', 'cannot_unsuspend','effect_grants'}:
                # Includes DP reduction: EX13-023 Q7269 says a 0-DP rule check
                # precedes triggered effects; an unsuspend cannot rescue it.
                raise RuntimeHalt('ORIENTATION_STATUS_UNSUPPORTED: ' + stack.cards[-1].key)
            if 'effect_grants' in stack.statuses:
                from effect_grants import validate_grants
                validate_grants(runtime,seat,stack.cards[-1].key)
            if any(type(v) is not bool for k,v in stack.statuses.items() if k!='effect_grants'):
                raise RuntimeHalt('ORIENTATION_STATUS_UNSUPPORTED: non-boolean prohibition')


def _usage(runtime,seat,source,effect):
    return (runtime.state.turn,seat,source,effect)


def _collect_orientation_reactions(runtime,seat,stack,suspended_before):
    if suspended_before == stack.suspended:
        return []
    top = stack.cards[-1]
    definition = runtime.context.card(seat,top.card_number).to_dict()
    effects = []
    for card in stack.cards[:-1] if definition['type']=='Digimon' else []:
        known = INHERITED_REACTIONS.get(card.card_number)
        if not known:
            continue
        is_unsuspend = card.card_number in ('P-138','EX1-013')
        if is_unsuspend:
            applies = suspended_before and not stack.suspended and runtime.state.active == seat
            if card.card_number == 'EX1-013':
                applies = applies and runtime.state.phase == 'MAIN'
        else:
            applies = not suspended_before and stack.suspended and 'Veedramon' in definition['name']
        if applies:
            effects.append({'seat':seat,'source':card.key,'effect_id':known[0],'field':'inherited_text',
                            'usage':list(_usage(runtime,seat,card.key,known[0])),
                            'trigger':{'kind':'ORIENTATION_CHANGED','entity':top.key,
                                       'suspended_before':suspended_before,'suspended_after':stack.suspended,
                                       'name_at_trigger':definition['name'],'phase':runtime.state.phase}})
    from rina_unsuspend_effects import collect_rina_unsuspend_reactions
    effects.extend(collect_rina_unsuspend_reactions(runtime,seat,stack,suspended_before))
    from rina_reactivation import collect_rina_suspension_reactions
    effects.extend(collect_rina_suspension_reactions(runtime,seat,stack,suspended_before))
    if (suspended_before is True and stack.suspended is False
            and top.card_number == 'BT12-029'):
        runtime.registry.lookup('BT12-029', BT12_RETURN_EFFECT, 'main_text')
        effects.append({'seat': seat, 'source': top.key, 'effect_id': BT12_RETURN_EFFECT,
            'field': 'main_text', 'usage': list(_usage(runtime, seat, top.key, BT12_RETURN_EFFECT)),
            'trigger': {'kind': 'ORIENTATION_CHANGED', 'entity': top.key,
                'suspended_before': True, 'suspended_after': False}})
    return effects


def _orientation_reactions(runtime,seat,stack,suspended_before):
    queue_effects(runtime,_collect_orientation_reactions(runtime,seat,stack,suspended_before))


def _set_orientation(runtime,seat,stack,suspended):
    before = stack.suspended
    prohibition = 'cannot_suspend' if suspended else 'cannot_unsuspend'
    from effect_grants import active_restriction
    blocked = before != suspended and (stack.statuses.get(prohibition,False)
        or ('effect_grants' in stack.statuses
            and active_restriction(runtime,seat,stack.cards[-1].key,prohibition)))
    if before != suspended and not blocked:
        _orientation_dependencies(runtime,seat,stack,before,suspended)
        stack.suspended = suspended
        _orientation_reactions(runtime,seat,stack,before)
    return {'suspended_before':before,'suspended_after':stack.suspended,
            'changed':before != stack.suspended,'prohibition':prohibition if blocked else None}


def resolve_orientation(runtime, seat, source_key, target):
    """Resolve an already activated effect in a closed, verified-scope scenario.

    target=None declines optional processing AFTER activation, consuming OPT
    under comprehensive rule 15-14-1-4. This is distinct from declining to
    activate a pending effect; no automatic decline or learning occurs here.
    """
    if target not in orientation_candidates(runtime, seat, source_key):
        raise RuntimeHalt('ORIENTATION_TARGET_INVALID')
    usage = (runtime.state.turn, seat, source_key, ORIENTATION_EFFECT)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED: ' + source_key)
    if target is None:
        runtime.state.once_used.add(usage)
        return {'changed': False, 'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
                'once_per_turn_consumed': True}
    stack = runtime.state.battle[seat][target]
    runtime.state.once_used.add(usage)
    result = _set_orientation(runtime,seat,stack,not stack.suspended)
    return {'target':target,**result,'once_per_turn_consumed':True}


def resolve_inherited_unsuspend(runtime,seat,source,choice):
    if type(choice) is not bool:
        raise RuntimeHalt('BOOLEAN_PROCESSING_CHOICE_REQUIRED')
    physical = runtime._source(seat,source,'inherited_text')
    known = INHERITED_REACTIONS.get(physical.card_number)
    if physical.card_number not in ('EX13-022','BT22-023') or known is None:
        raise RuntimeHalt('INHERITED_UNSUSPEND_SOURCE_INVALID')
    usage = _usage(runtime,seat,source,known[0])
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED')
    runtime.state.once_used.add(usage)
    if not choice:
        return {'changed':False,'processing':'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION'}
    if physical.card_number == 'BT22-023':
        blue = any(runtime.context.card(seat,s.cards[-1].card_number).kind=='Tamer'
                   and 'Blue' in runtime.context.card(seat,s.cards[-1].card_number).to_dict()['colors']
                   for s in runtime.state.battle[seat].values())
        if not blue:
            return {'changed':False,'processing':'BLUE_TAMER_CONDITION_FAILED'}
    stack = source_stack(runtime,seat,source,'inherited_text')
    return {**_set_orientation(runtime,seat,stack,False),'processing':'OPTIONAL_UNSUSPEND_SELECTED'}


def resolve_unsuspend_memory(runtime,seat,source,choice):
    physical = runtime._source(seat,source,'inherited_text')
    if physical.card_number not in ('P-138','EX1-013') or choice is not None:
        raise RuntimeHalt('MEMORY_REACTION_SOURCE_OR_CHOICE_INVALID')
    if runtime.state.active != seat or (physical.card_number == 'EX1-013' and runtime.state.phase!='MAIN'):
        raise RuntimeHalt('MEMORY_TRIGGER_NOT_APPLICABLE')
    effect = INHERITED_REACTIONS[physical.card_number][0]
    usage = _usage(runtime,seat,source,effect)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED')
    runtime.state.once_used.add(usage)
    before = runtime.state.memory
    runtime.state.memory = min(10,before+1)
    return {'memory_before':before,'memory_after':runtime.state.memory,'gained':runtime.state.memory-before}


def resolve_phase_memory(runtime,seat,source,choice):
    physical = runtime._source(seat,source,'main_text')
    spec = PHASE_EFFECTS.get(physical.card_number)
    if spec is None or choice is not None or runtime.state.active!=seat:
        raise RuntimeHalt('PHASE_MEMORY_SOURCE_OR_CHOICE_INVALID')
    expected_phase = 'TURN_START_EFFECTS' if spec[1]=='Start of Your Turn' else 'MAIN'
    if runtime.state.phase!=expected_phase:
        raise RuntimeHalt('PHASE_MEMORY_TIMING_INVALID')
    before = runtime.state.memory
    condition = True
    if physical.card_number in ('BT22-085','BT19-080'):
        condition = before<=2
        if condition:runtime.state.memory=3
    elif physical.card_number=='BT19-007':
        condition = any(runtime.context.card(seat,s.cards[-1].card_number).name in ('Takato Matsuki','Calumon')
                        for s in runtime.state.battle[seat].values())
        if condition:runtime.state.memory=min(10,before+1)
    elif physical.card_number=='EX13-069':
        condition = any(runtime.context.card(seat,s.cards[-1].card_number).kind=='Digimon'
                        and any(name in runtime.context.card(seat,s.cards[-1].card_number).name
                                for name in ('Veemon','Veedramon')) for s in runtime.state.battle[seat].values())
        if condition:runtime.state.memory=min(10,before+1)
    return {'memory_before':before,'memory_after':runtime.state.memory,'condition_met':condition}


def _source_evidence(root, source, locator):
    root = Path(root).resolve()
    base = (root / 'RULES').resolve()
    path = (root / source['file']).resolve()
    require(path.is_relative_to(base) and base.is_relative_to(root), 'Official source escapes RULES')
    return OfficialEvidence.from_bytes(source['url'], path.read_bytes(), source['sha256'], locator)


def build_selected_registry(context, root):
    cards = {c.number: c for c in context.cards}
    index = json.loads((Path(root) / 'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json').read_bytes())
    source = next(d for d in index['sources'] if d['id'] == 'rules')
    rules = _source_evidence(root,source,'Comprehensive rules v4.3: 4-13; 15-3; 15-4; 15-14-1; memory cap 1-4-2')
    def bound_omnimon_end(runtime, seat, source_key, choice):
        return resolve_omnimon_end(runtime, seat, source_key, choice, root)
    specs = [('EX13-023',ORIENTATION_EFFECT,'main_text',ORIENTATION_LINE,resolve_orientation),
        ('BT20-102',OMNIMON_END_EFFECT,'main_text',OMNIMON_END_LINE,bound_omnimon_end)] + [
        (number,effect,'inherited_text',line,
         resolve_inherited_unsuspend if number in ('EX13-022','BT22-023') else resolve_unsuspend_memory)
        for number,(effect,line) in INHERITED_REACTIONS.items()] + [
        (number,effect,'main_text',line,resolve_phase_memory)
        for number,(effect,timing,line) in PHASE_EFFECTS.items()] + [
        ('BT22-085',RINA_JAMMING_EFFECT,'main_text',RINA_JAMMING_LINE,resolve_rina_attack_jamming),
        ('BT12-029',BT12_UNSUSPEND_EFFECT,'main_text',BT12_UNSUSPEND_LINE,resolve_bt12_unsuspend),
        ('BT12-029',BT12_RETURN_EFFECT,'main_text',BT12_RETURN_LINE,resolve_bt12_return)]
    bindings = []
    for number,effect,field,line,handler in specs:
        if number not in cards:
            continue
        card = cards[number]
        require(line in card.effect_text(field).splitlines(),'Exact mechanic text changed: '+number)
        evidence = (_source_evidence(root,card.to_dict()['official_source'],
                                    '#'+number+' '+field+'; EX1-013 Q3203 / EX13-023 Q7266-Q7269 where applicable'),rules)
        bindings.append(MechanicBinding(number,effect,field,card.definition_sha256,
                                       hashlib.sha256(card.effect_text(field).encode()).hexdigest(),evidence,handler))
    from search_effects import search_bindings
    bindings.extend(search_bindings(context,root,rules))
    from on_play_effects import on_play_bindings
    bindings.extend(on_play_bindings(context,root,rules))
    from option_actions import option_bindings
    bindings.extend(option_bindings(context,root,rules))
    from aero_effects import aero_bindings
    bindings.extend(aero_bindings(context,root,rules))
    from tamer_play_effects import tamer_play_bindings
    bindings.extend(tamer_play_bindings(context,root,rules))
    from security_tamer import security_tamer_bindings
    bindings.extend(security_tamer_bindings(context,root,rules))
    from rina_unsuspend_effects import rina_unsuspend_bindings
    bindings.extend(rina_unsuspend_bindings(context,root,rules))
    from ex13_ulforce_effects import ulforce_return_bindings
    bindings.extend(ulforce_return_bindings(context,root,rules))
    from return_effects import inherited_return_replacement_bindings
    bindings.extend(inherited_return_replacement_bindings(context,root,rules))
    from rina_reactivation import rina_reactivation_bindings
    bindings.extend(rina_reactivation_bindings(context,root,rules))
    return MechanicRegistry(tuple(bindings))
