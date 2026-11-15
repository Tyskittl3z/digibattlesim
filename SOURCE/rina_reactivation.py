"""Rina's encountered paid activation of an observed Digimon's current effect.

This reactivates a printed When Digivolving effect. It does not digivolve,
change memory, or draw. The observed incarnation survives ordinary evolution;
its current top supplies the available effects (BT11-112 Q2143).
"""
from dataclasses import replace
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding,RuntimeHalt
from effect_scheduler import pending_options,queue_effects,source_stack
from match_context import require

REACTIVATION_EFFECT='BT11-112.suspend_reactivation'
REACTIVATION_LINE=("[All Turns] When one of your Digimon with [Veedramon] in its name becomes suspended, "
                   "by suspending this Tamer, activate 1 of that Digimon's [When Digivolving] effects.")
PAY_NO_EFFECT='PAY_NO_EFFECT'
RULE_LOCATOR=('BT11-112 Q2142/Q2143/Q7199/Q7200; Comprehensive rules v4.3: '
              '1-3-3; 15-4; 15-7-4; 15-7-5; 15-14; 15-15-7-1')


def known_rina_suspension_observer(number,field,line):
    return number=='BT11-112' and field=='main_text' and line==REACTIVATION_LINE


def collect_rina_suspension_reactions(runtime,changed_seat,stack,suspended_before):
    if suspended_before is not False or stack.suspended is not True:return []
    changed=runtime.context.card(changed_seat,stack.cards[-1].card_number)
    if changed.kind!='Digimon' or 'Veedramon' not in changed.name:return []
    sources=[]
    for key,tamer in runtime.state.battle[changed_seat].items():
        if tamer.cards[-1].card_number!='BT11-112':continue
        runtime.registry.lookup('BT11-112',REACTIVATION_EFFECT,'main_text')
        sources.append(key)
    if not sources:return []
    if not stack.instance_id:
        runtime.state.entity_sequence+=1
        stack.instance_id='entity-'+str(runtime.state.entity_sequence)
    return [{'seat':changed_seat,'source':key,'effect_id':REACTIVATION_EFFECT,'field':'main_text',
             'trigger':{'kind':'DIGIMON_SUSPENDED','observed_instance':stack.instance_id,
                        'observed_source':stack.cards[-1].key,'name_at_trigger':changed.name,
                        'suspended_before':False,'suspended_after':True}}
            for key in sources]


def _source_window(runtime,seat,source_key,*,resolving=False):
    from selected_contexts import require_selected_context
    require_selected_context(runtime.context,Path(__file__).resolve().parents[1])
    if runtime.halted or runtime.state.terminal:raise RuntimeHalt('RINA_REACTIVATION_WINDOW_REQUIRED')
    source=runtime._source(seat,source_key,'main_text')
    if source.card_number!='BT11-112':raise RuntimeHalt('RINA_REACTIVATION_SOURCE_INVALID')
    expected=(REACTIVATION_EFFECT,seat,source_key,'main_text')
    activated=getattr(runtime,'_activated_effect',None)
    inside=isinstance(activated,tuple) and len(activated)==5 and activated[:4]==expected and activated[4] is not None
    if inside:
        record=getattr(runtime,'_activated_pending',None)
        if (not isinstance(record,dict) or record.get('id')!=activated[4]
                or tuple(record.get(k) for k in ('effect_id','seat','source','field'))!=expected):
            raise RuntimeHalt('RINA_REACTIVATION_WINDOW_REQUIRED')
    elif not resolving:
        record=next((p for p in pending_options(runtime,seat)
            if tuple(p[k] for k in ('effect_id','seat','source','field'))==expected),None)
    else:record=None
    stack=source_stack(runtime,seat,source_key,'main_text')
    if record is None or record['instance']!=stack.instance_id:
        raise RuntimeHalt('RINA_REACTIVATION_WINDOW_REQUIRED')
    trigger=record['trigger']
    if (set(trigger)!={'kind','observed_instance','observed_source','name_at_trigger',
                       'suspended_before','suspended_after'}
            or trigger['kind']!='DIGIMON_SUSPENDED' or trigger['suspended_before'] is not False
            or trigger['suspended_after'] is not True
            or not isinstance(trigger['observed_instance'],str) or not trigger['observed_instance']
            or not isinstance(trigger['observed_source'],str) or not trigger['observed_source'].startswith(seat+':')
            or not isinstance(trigger['name_at_trigger'],str) or 'Veedramon' not in trigger['name_at_trigger']):
        raise RuntimeHalt('RINA_REACTIVATION_TRIGGER_INVALID')
    return record


def _cost_payable(runtime,seat,source_key):
    stack=source_stack(runtime,seat,source_key,'main_text')
    if stack.suspended or stack.statuses.get('cannot_suspend',False):return False
    if 'effect_grants' in stack.statuses:
        from effect_grants import active_restriction
        if active_restriction(runtime,seat,source_key,'cannot_suspend'):return False
    return True


def _observed(runtime,seat,record):
    instance=record['trigger']['observed_instance']
    for key,stack in runtime.state.battle[seat].items():
        if stack.instance_id==instance:
            if runtime.context.card(seat,stack.cards[-1].card_number).kind!='Digimon':return None
            return key,stack
    return None


def _available(runtime,seat,record):
    observed=_observed(runtime,seat,record)
    if observed is None:return (),None
    from battle_evolution import current_digivolving_effects
    return current_digivolving_effects(runtime,seat,observed[0]),observed


def rina_reactivation_choices(runtime,seat,source_key):
    record=_source_window(runtime,seat,source_key)
    # A Tamer that cannot pay never needs to inspect unimplemented result text.
    if not _cost_payable(runtime,seat,source_key):return [None]
    effects,_=_available(runtime,seat,record)
    return [None,*effects] if effects else [None,PAY_NO_EFFECT]


def resolve_rina_reactivation(runtime,seat,source_key,choice):
    record=_source_window(runtime,seat,source_key,resolving=True)
    if choice is None:
        return {'suspension_paid':False,'activated_effect':None,'processing':'RINA_REACTIVATION_DECLINED',
                'full_match_credit':0}
    if not isinstance(choice,str) or not _cost_payable(runtime,seat,source_key):
        raise RuntimeHalt('RINA_REACTIVATION_CHOICE_INVALID')
    effects,observed=_available(runtime,seat,record)
    if choice not in (effects if effects else (PAY_NO_EFFECT,)):
        raise RuntimeHalt('RINA_REACTIVATION_CHOICE_INVALID')
    from selected_mechanics import _set_orientation
    tamer=source_stack(runtime,seat,source_key,'main_text')
    cost=_set_orientation(runtime,seat,tamer,True)
    if not cost['changed']:
        return {'suspension_paid':False,'activated_effect':None,'processing':'RINA_SUSPENSION_COST_NOT_PAID',
                'full_match_credit':0}
    activated_effect=None;pending_id=None;current_source=observed[0] if observed else None
    if choice!=PAY_NO_EFFECT:
        from battle_evolution import digivolving_effect_usage
        usage=digivolving_effect_usage(runtime,seat,current_source,choice)
        queue_effects(runtime,[{'seat':seat,'source':current_source,'effect_id':choice,'field':'main_text',
            'usage':list(usage),'trigger':{'kind':'RINA_REACTIVATED_WHEN_DIGIVOLVING',
                'parent_effect':REACTIVATION_EFFECT,'parent_pending_id':record['id'],
                'paid_source':source_key,'paid_instance':tamer.instance_id,'suspension_paid':True,
                'observed_instance':record['trigger']['observed_instance'],
                'observed_source':record['trigger']['observed_source'],'current_source':current_source}}])
        activated_effect=choice;pending_id=runtime.state.pending[-1]['id']
    return {'suspension_paid':True,'activated_effect':activated_effect,'activated_source':current_source,
            'activated_pending_id':pending_id,'processing':'RINA_WHEN_DIGIVOLVING_REACTIVATED' if activated_effect
                else 'RINA_PAID_WITH_NO_AVAILABLE_EFFECT','steps':[
                    {'operation':'SUSPEND_TAMER_AS_COST','card':source_key,'changed':True},
                    {'operation':'ACTIVATE_WHEN_DIGIVOLVING_EFFECT','source':current_source,
                     'effect':activated_effect,'pending_id':pending_id}], 'full_match_credit':0}


def rina_reactivation_bindings(context,root,rules):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number!='BT11-112':continue
        require(REACTIVATION_LINE in card.effect_text('main_text').splitlines(),'BT11-112 reactivation wording changed')
        evidence=_source_evidence(root,card.to_dict()['official_source'],
            '#BT11-112 All Turns paid reactivation; Q2142/Q2143/Q7199/Q7200')
        bindings.append(MechanicBinding(card.number,REACTIVATION_EFFECT,'main_text',card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence,replace(rules,locator=RULE_LOCATOR)),resolve_rina_reactivation))
    return tuple(bindings)
