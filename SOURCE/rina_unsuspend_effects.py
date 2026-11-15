"""Encountered Your Turn Rina unsuspend reactions and paid After processing.

EX13-069 exposes only an activation choice before drawing. Its same-source
continuation is queued deeper than the remaining simultaneous effects, and
only then exposes routes from the hand after the draw (Q7437/Q7439).
"""
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding,RuntimeHalt
from effect_scheduler import pending_options,queue_effects,source_stack
from match_context import require

BT11_MEMORY_EFFECT = 'BT11-112.unsuspend_memory'
MEMORY_EFFECT = BT11_MEMORY_EFFECT
EX13_DRAW_EFFECT = 'EX13-069.unsuspend_draw'
EX13_EVOLVE_EFFECT = 'EX13-069.unsuspend_evolve'
BT11_MEMORY_LINE = '[Your Turn][Once Per Turn] When one of your blue Digimon becomes unsuspended, gain 1 memory.'
EX13_DRAW_LINE = ('[Your Turn] When any of your Digimon unsuspend, by suspending this Tamer, ＜Draw 1＞. '
    'After, 1 of your Digimon may digivolve into a Digimon card with [Veedramon] in its name in the hand with the cost reduced by 2.')
RINA_CHOICE_EFFECTS = frozenset((BT11_MEMORY_EFFECT,EX13_DRAW_EFFECT,EX13_EVOLVE_EFFECT,
    'BT22-085.attack_jamming'))


def known_rina_orientation_observer(number,field,line):
    return field=='main_text' and ((number=='BT11-112' and line==BT11_MEMORY_LINE)
                                  or (number=='EX13-069' and line==EX13_DRAW_LINE))


def _source_window(runtime,seat,source_key,effect_id):
    if (runtime.halted or runtime.state.terminal or runtime.state.active!=seat
            or effect_id not in RINA_CHOICE_EFFECTS):
        raise RuntimeHalt('RINA_EFFECT_WINDOW_REQUIRED')
    source=runtime._source(seat,source_key,'main_text')
    number='BT11-112' if effect_id==BT11_MEMORY_EFFECT else 'EX13-069'
    if source.card_number!=number:raise RuntimeHalt('RINA_EFFECT_SOURCE_INVALID')
    expected=(effect_id,seat,source_key,'main_text')
    activated=getattr(runtime,'_activated_effect',None)
    if activated is not None and activated[:4]==expected and activated[4] is not None:
        record=getattr(runtime,'_activated_pending',None)
        if (not isinstance(record,dict) or record.get('id')!=activated[4]
                or tuple(record.get(k) for k in ('effect_id','seat','source','field'))!=expected):
            raise RuntimeHalt('RINA_EFFECT_WINDOW_REQUIRED')
    else:
        record=next((p for p in pending_options(runtime,seat)
            if tuple(p[k] for k in ('effect_id','seat','source','field'))==expected),None)
        if record is None:raise RuntimeHalt('RINA_EFFECT_WINDOW_REQUIRED')
    stack=source_stack(runtime,seat,source_key,'main_text')
    if record['instance']!=stack.instance_id:raise RuntimeHalt('RINA_EFFECT_WINDOW_REQUIRED')
    return source,record


def _memory_usage(runtime,seat,source_key):
    stack=source_stack(runtime,seat,source_key,'main_text')
    if not stack.instance_id:
        runtime.state.entity_sequence+=1;stack.instance_id='entity-'+str(runtime.state.entity_sequence)
    return (runtime.state.turn,seat,source_key,stack.instance_id,BT11_MEMORY_EFFECT)


def collect_rina_unsuspend_reactions(runtime,changed_seat,stack,suspended_before):
    if suspended_before is not True or stack.suspended or changed_seat!=runtime.state.active:
        return []
    changed=runtime.context.card(changed_seat,stack.cards[-1].card_number)
    if changed.kind!='Digimon':return []
    records=[]
    for key,tamer_stack in runtime.state.battle[changed_seat].items():
        source=tamer_stack.cards[-1]
        if source.card_number=='BT11-112' and 'Blue' in changed.to_dict()['colors']:
            effect=BT11_MEMORY_EFFECT;usage=list(_memory_usage(runtime,changed_seat,key))
            if tuple(usage) in runtime.state.once_used:continue
        elif source.card_number=='EX13-069':
            effect=EX13_DRAW_EFFECT;usage=[]
        else:continue
        runtime.registry.lookup(source.card_number,effect,'main_text')
        records.append({'seat':changed_seat,'source':key,'effect_id':effect,'field':'main_text','usage':usage,
            'trigger':{'kind':'DIGIMON_UNSUSPENDED','entity':stack.cards[-1].key,
                       'suspended_before':True,'suspended_after':False,'name_at_trigger':changed.name}})
    return records


def _cost_payable(runtime,seat,source_key):
    stack=runtime.state.battle[seat][source_key]
    if stack.suspended or stack.statuses.get('cannot_suspend',False):return False
    if 'effect_grants' in stack.statuses:
        from effect_grants import active_restriction
        if active_restriction(runtime,seat,source_key,'cannot_suspend'):return False
    return True


def validate_rina_continuation(runtime,seat,source_key=None):
    activated=getattr(runtime,'_activated_effect',None)
    if source_key is None:
        if (not isinstance(activated,tuple) or len(activated)!=5
                or activated[0]!=EX13_EVOLVE_EFFECT or activated[1]!=seat or activated[4] is None):
            raise RuntimeHalt('RINA_CONTINUATION_PROOF_REQUIRED')
        source_key=activated[2]
    _,record=_source_window(runtime,seat,source_key,EX13_EVOLVE_EFFECT)
    trigger=record['trigger'];stack=source_stack(runtime,seat,source_key,'main_text')
    if (set(trigger)!={'kind','parent_effect','parent_pending_id','paid_source','paid_instance',
                       'suspension_paid','draw_completed','drawn_card'}
            or trigger['kind']!='RINA_AFTER_DRAW' or trigger['parent_effect']!=EX13_DRAW_EFFECT
            or not isinstance(trigger['parent_pending_id'],str) or not trigger['parent_pending_id'].startswith('effect-')
            or trigger['paid_source']!=source_key or trigger['paid_instance']!=stack.instance_id
            or trigger['suspension_paid'] is not True or trigger['draw_completed'] is not True
            or not stack.suspended or record['depth']<1
            or (trigger['drawn_card'] is not None and not isinstance(trigger['drawn_card'],str))):
        raise RuntimeHalt('RINA_CONTINUATION_PROOF_REQUIRED')
    return source_key


def rina_evolution_choices(runtime,seat,source_key=None):
    validate_rina_continuation(runtime,seat,source_key)
    from context_evolution import printed_evolution_options,UnsupportedEvolutionCondition
    choices=[None]
    for key,stack in sorted(runtime.state.battle[seat].items()):
        base=runtime.context.card(seat,stack.cards[-1].card_number)
        if base.kind!='Digimon':continue
        for physical in runtime.state.zones[seat]['hand']:
            card=runtime.context.card(seat,physical.card_number)
            if card.kind!='Digimon' or 'Veedramon' not in card.name:continue
            try:routes=printed_evolution_options(runtime.context,seat,base.number,card.number)
            except UnsupportedEvolutionCondition as exc:
                raise RuntimeHalt('RINA_EVOLUTION_ROUTE_UNSUPPORTED: '+physical.key+' '+str(exc)) from exc
            for index,route in enumerate(routes):
                if max(0,route.cost-2)<=runtime.state.memory+10:
                    choices.append({'source_key':key,'hand_key':physical.key,'route_index':index})
    return choices


def rina_unsuspend_choices(runtime,seat,source_key,effect_id):
    if effect_id=='BT22-085.attack_jamming':
        from selected_mechanics import rina_jamming_choices
        return rina_jamming_choices(runtime,seat,source_key)
    _source_window(runtime,seat,source_key,effect_id)
    if effect_id==BT11_MEMORY_EFFECT:return [None]
    if effect_id==EX13_DRAW_EFFECT:return [False,True] if _cost_payable(runtime,seat,source_key) else [False]
    return rina_evolution_choices(runtime,seat,source_key)


def resolve_rina_memory(runtime,seat,source_key,choice):
    if choice is not None or choice not in rina_unsuspend_choices(runtime,seat,source_key,BT11_MEMORY_EFFECT):
        raise RuntimeHalt('RINA_MEMORY_CHOICE_INVALID')
    usage=_memory_usage(runtime,seat,source_key)
    if usage in runtime.state.once_used:raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED')
    runtime.state.once_used.add(usage);before=runtime.state.memory
    runtime.state.memory=min(10,before+1)
    return {'memory_before':before,'memory_after':runtime.state.memory,'gained':runtime.state.memory-before,
            'once_per_turn_consumed':True,'full_match_credit':0}


def resolve_rina_draw(runtime,seat,source_key,choice):
    _,record=_source_window(runtime,seat,source_key,EX13_DRAW_EFFECT)
    if type(choice) is not bool or choice not in rina_unsuspend_choices(runtime,seat,source_key,EX13_DRAW_EFFECT):
        raise RuntimeHalt('RINA_DRAW_CHOICE_INVALID')
    if not choice:
        return {'suspension_paid':False,'drawn_card':None,'processing':
            'SUSPENSION_DECLINED' if _cost_payable(runtime,seat,source_key) else 'SUSPENSION_COST_NOT_PAYABLE',
            'full_match_credit':0}
    from selected_mechanics import _set_orientation
    stack=source_stack(runtime,seat,source_key,'main_text')
    suspended=_set_orientation(runtime,seat,stack,True)
    if not suspended['changed']:
        return {'suspension_paid':False,'drawn_card':None,'processing':'SUSPENSION_COST_NOT_PAID','full_match_credit':0}
    deck=runtime.state.zones[seat]['deck'];drawn=deck.pop() if deck else None
    if drawn is not None:runtime.state.zones[seat]['hand'].append(drawn)
    queue_effects(runtime,[{'seat':seat,'source':source_key,'effect_id':EX13_EVOLVE_EFFECT,'field':'main_text',
        'trigger':{'kind':'RINA_AFTER_DRAW','parent_effect':EX13_DRAW_EFFECT,'parent_pending_id':record['id'],
            'paid_source':source_key,'paid_instance':stack.instance_id,'suspension_paid':True,
            'draw_completed':True,'drawn_card':drawn.key if drawn else None}}])
    continuation=runtime.state.pending[-1]['id']
    return {'suspension_paid':True,'drawn_card':drawn.key if drawn else None,'continuation_pending_id':continuation,
            'processing':'DRAW_COMPLETE_EVOLUTION_PENDING','steps':[
                {'operation':'SUSPEND_TAMER_AS_COST','card':source_key,'changed':True},
                {'operation':'DRAW','card':drawn.key if drawn else None},
                {'operation':'CONTINUE_AFTER_DRAW','pending_id':continuation}], 'full_match_credit':0}


def resolve_rina_evolve(runtime,seat,source_key,choice):
    validate_rina_continuation(runtime,seat,source_key)
    if choice not in rina_evolution_choices(runtime,seat,source_key):
        raise RuntimeHalt('RINA_EVOLUTION_CHOICE_INVALID')
    evolution=None
    if choice is not None:
        from battle_evolution import trusted_evolve_from_effect
        evolution=trusted_evolve_from_effect(runtime,seat,choice['source_key'],choice['hand_key'],
                                             choice['route_index'],Path(__file__).resolve().parents[1])
    return {'evolution':evolution,'processing':'AFTER_DRAW_EVOLUTION_COMPLETE','full_match_credit':0}


def rina_unsuspend_bindings(context,root,rules):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number not in ('BT11-112','EX13-069'):continue
        line=BT11_MEMORY_LINE if card.number=='BT11-112' else EX13_DRAW_LINE
        require(line in card.effect_text('main_text').splitlines(),'Exact Rina unsuspend text changed: '+card.number)
        evidence=_source_evidence(root,card.to_dict()['official_source'],
            '#'+card.number+' Your Turn Digimon unsuspend; EX13-069 Q7437/Q7439; '
            'CR1-3-3,4-13,8-1,15-4,15-7,15-8-3,15-14-1')
        handlers=[(BT11_MEMORY_EFFECT,resolve_rina_memory)] if card.number=='BT11-112' else [
            (EX13_DRAW_EFFECT,resolve_rina_draw),(EX13_EVOLVE_EFFECT,resolve_rina_evolve)]
        for effect,handler in handlers:
            bindings.append(MechanicBinding(card.number,effect,'main_text',card.definition_sha256,
                hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),(evidence,rules),handler))
    return tuple(bindings)
