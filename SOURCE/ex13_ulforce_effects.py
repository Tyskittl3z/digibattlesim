"""The encountered optional return-all effect, using actual affected stacks."""
from dataclasses import replace
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding,RuntimeHalt
from effect_scheduler import pending_options, queue_effects
from match_context import require
from return_effects import (inherited_return_replacement, replacement_effect_id,
                            return_to_deck_bottom)


RETURN_EFFECT='EX13-023.return_fewest'
RETURN_LINE=("[On Play] [When Digivolving] You may return all of your opponent's Digimon "
             'with the fewest digivolution cards to the bottom of the deck.')
RULE_LOCATOR=('Comprehensive rules v4.3: 3-1-3-4; 3-4; 4-7-8; 15-4; 15-8-3; '
              '15-10-2; 15-16-2; 15-16-3; EX13-023 printed separate On Play/When Digivolving effects')


def _source_window(runtime,seat,source_key):
    from selected_contexts import require_selected_context
    require_selected_context(runtime.context,Path(__file__).resolve().parents[1])
    source=runtime._source(seat,source_key,'main_text')
    if source.card_number!='EX13-023' or runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('ULFORCE_RETURN_WINDOW_REQUIRED')
    expected=(RETURN_EFFECT,seat,source_key,'main_text')
    activated=getattr(runtime,'_activated_effect',None)
    inside=isinstance(activated,tuple) and len(activated)==5 and activated[:4]==expected and activated[4] is not None
    if not inside and not any(tuple(p[k] for k in ('effect_id','seat','source','field'))==expected
                             for p in pending_options(runtime,seat)):
        raise RuntimeHalt('ULFORCE_RETURN_WINDOW_REQUIRED')
    return source


def ulforce_return_choices(runtime,seat,source_key):
    _source_window(runtime,seat,source_key)
    return [False,True]


def ulforce_return_targets(runtime,seat,source_key):
    """Public current targets; the action-causing card's owner chooses order."""
    _source_window(runtime,seat,source_key)
    return [key for key,_ in _minimum_targets(runtime,'B' if seat=='A' else 'A')]


def _minimum_targets(runtime,owner):
    digimon=[(key,stack) for key,stack in runtime.state.battle[owner].items()
             if runtime.context.card(owner,stack.cards[-1].card_number).kind=='Digimon']
    if not digimon:return []
    minimum=min(len(stack.cards)-1 for _,stack in digimon)
    return [(key,stack) for key,stack in digimon if len(stack.cards)-1==minimum]


def resolve_ulforce_return(runtime,seat,source_key,choice):
    ulforce_return_choices(runtime,seat,source_key)
    ordered=isinstance(choice,dict) and set(choice)=={'activate','bottom_order'} and choice['activate'] is True
    if type(choice) is not bool and not ordered:
        raise RuntimeHalt('ULFORCE_RETURN_CHOICE_INVALID')
    if not choice:
        return {'processing':'OPTIONAL_RETURN_DECLINED','returned':[],'trashed_sources':[],
                'full_match_credit':0}
    owner='B' if seat=='A' else 'A'
    targets=_minimum_targets(runtime,owner)
    if len(targets)>1 and not ordered:
        # CR3-1-3-4: the owner of the action-causing card chooses the order.
        # Do not replace that missing choice with key sorting or random order.
        raise RuntimeHalt('ULFORCE_RETURN_ORDER_REQUIRED: chooser='+seat+' deck_owner='+owner
                          +' cards='+','.join(k for k,_ in targets))
    order=choice['bottom_order'] if ordered else [key for key,_ in targets]
    if (not isinstance(order,list) or any(not isinstance(key,str) for key in order)
            or len(order)!=len(targets) or len(set(order))!=len(order)
            or set(order)!={key for key,_ in targets}):
        raise RuntimeHalt('ULFORCE_RETURN_ORDER_INVALID')
    if len(targets) == 1:
        target_key, stack = targets[0]
        replacement = inherited_return_replacement(runtime, seat, owner, target_key)
        if replacement is not None:
            source, usage = replacement
            queue_effects(runtime, [{'seat': owner, 'source': source,
                'effect_id': replacement_effect_id(runtime, owner, source), 'field': 'inherited_text',
                'trigger': {'kind': 'OPPONENT_EFFECT_RETURN', 'actor': seat,
                    'target': target_key, 'target_instance': stack.instance_id,
                    'source_effect': RETURN_EFFECT}}])
            return {'processing': 'RETURN_REPLACEMENT_PENDING', 'target': target_key,
                'replacement_source': source, 'returned': [], 'trashed_sources': [],
                'full_match_credit': 0}
    result=return_to_deck_bottom(runtime,seat,owner,[key for key,_ in targets],order,
                                 halt_prefix='ULFORCE_RETURN')
    return {'processing':'RETURNED_FEWEST_SOURCE_DIGIMON' if targets else 'NO_ELIGIBLE_TARGET',
            **result,'full_match_credit':0,
            'bottom_order':order,'bottom_order_controller':seat,
            'bottom_order_convention':'first element is bottommost'}


def ulforce_return_bindings(context,root,rules):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number!='EX13-023':continue
        require(RETURN_LINE in card.effect_text('main_text').splitlines(),'EX13-023 return wording changed')
        evidence=_source_evidence(root,card.to_dict()['official_source'],
                                  '#EX13-023 separate optional return-all fewest-source Digimon')
        bindings.append(MechanicBinding(card.number,RETURN_EFFECT,'main_text',card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence,replace(rules,locator=RULE_LOCATOR)),resolve_ulforce_return))
    return tuple(bindings)
