"""Main-phase play actions scoped to verified inert singleton battlefields.

Unknown On Play, Option, live replacement/trigger and Assembly interactions
halt before card/cost mutation. This is not a complete main-action generator.
"""
from context_runtime import RuntimeHalt,Stack
from effect_scheduler import queue_effects
from match_preparation import _rules
from search_effects import SEARCH_SPECS
from on_play_effects import ON_PLAY_SPECS
from aero_effects import PLAY_SPECS
from tamer_play_effects import PLAY_SPECS as TAMER_PLAY_SPECS
from printed_triggers import trigger_lines
from selected_contexts import require_selected_context

PLAIN_MAIN_TEXT = {'EX1-013':'','ST7-05':'','BT9-011':''}


def _play(runtime,seat,choice,root,*,within_effect=False,source_zone='hand',cost_override=None):
    state=runtime.state
    try:
        locked=require_selected_context(runtime.context,root)
    except RuntimeHalt as exc:
        raise RuntimeHalt('SELECTED_PLAY_CAPABILITY_REQUIRED') from exc
    if not runtime.allow_experimental:raise RuntimeHalt('UNREVIEWED_MAIN_ACTION')
    if not within_effect and (seat!=state.active or state.phase!='MAIN' or state.memory<0):
        raise RuntimeHalt('MAIN_PLAY_WINDOW_NOT_OPEN')
    if source_zone not in ('hand','trash','security_check') or (source_zone!='hand' and not within_effect):
        raise RuntimeHalt('EFFECT_PLAY_SOURCE_INVALID')
    pool=None if source_zone=='security_check' else state.zones[seat][source_zone]
    if source_zone=='security_check':
        from security_tamer import validate_security_activation
        physical=validate_security_activation(runtime,seat,choice['hand_key'])
    else:
        physical=next((c for c in pool if c.key==choice['hand_key']),None)
    if physical is None:
        raise RuntimeHalt('PLAY_CARD_NOT_IN_HAND' if source_zone=='hand' else 'PLAY_CARD_NOT_IN_TRASH')
    card=runtime.context.card(seat,physical.card_number)
    from selected_mechanics import _source_evidence
    card_evidence=_source_evidence(root,card.to_dict()['official_source'],
                                   '#'+card.number+' printed type, play cost and main effects').manifest()
    if card.kind=='Option':raise RuntimeHalt('OPTION_USE_UNIMPLEMENTED: '+card.number)
    if card.kind not in ('Digimon','Tamer'):raise RuntimeHalt('PLAY_CARD_TYPE_INVALID')
    spec=(SEARCH_SPECS.get(card.number) or ON_PLAY_SPECS.get(card.number)
          or PLAY_SPECS.get(card.number) or TAMER_PLAY_SPECS.get(card.number))
    specs=(spec,) if spec is not None else ()
    if card.number=='EX13-023':
        from selected_mechanics import ORIENTATION_EFFECT,ORIENTATION_LINE
        from ex13_ulforce_effects import RETURN_EFFECT,RETURN_LINE
        specs=((ORIENTATION_EFFECT,ORIENTATION_LINE),(RETURN_EFFECT,RETURN_LINE))
    on_play=trigger_lines(card.effect_text('main_text'),'On Play')
    if on_play and on_play!=tuple(item[1] for item in specs):
        raise RuntimeHalt('PLAY_EFFECT_UNSUPPORTED: '+card.number+' timing=On Play')
    if not on_play:specs=()
    from battlefield_scope import assert_basic_board_scope
    assert_basic_board_scope(runtime,'play_search' if specs else 'play_plain',root,
        event={'seat':seat,'card_number':card.number},within_effect=within_effect)
    for spec in specs:
        runtime.registry.lookup(card.number,spec[0],'main_text')
    if cost_override is not None and not within_effect:
        raise RuntimeHalt('PLAY_COST_OVERRIDE_WINDOW_INVALID')
    cost=(cost_override if cost_override is not None else 0 if within_effect
          else card.to_dict()['play_cost'])
    if type(cost) is not int or cost<0 or cost>state.memory+10:
        raise RuntimeHalt('PLAY_COST_NOT_PAYABLE')
    state.memory-=cost
    if pool is not None:pool.remove(physical)
    state.entity_sequence+=1
    state.battle[seat][physical.key]=Stack([physical],instance_id='entity-'+str(state.entity_sequence),
                                         played_turn=state.turn,ready_since_turn=state.turn+1)
    effects=[]
    for spec in specs:
        record={'seat':seat,'source':physical.key,'effect_id':spec[0],'field':'main_text',
                'trigger':{'kind':'On Play','card':physical.key}}
        if card.number in TAMER_PLAY_SPECS:
            from tamer_play_effects import tamer_play_usage
            record['usage']=list(tamer_play_usage(runtime,seat,physical.key,spec[0]))
        elif card.number=='EX13-023':
            from selected_mechanics import ORIENTATION_EFFECT,_usage
            record['usage']=(list(_usage(runtime,seat,physical.key,spec[0]))
                             if spec[0]==ORIENTATION_EFFECT else [])
        effects.append(record)
    from tamer_play_effects import collect_tamer_play_reactions
    effects.extend(collect_tamer_play_reactions(runtime,seat,physical))
    queue_effects(runtime,effects)
    return {'played_card':physical.key,'cost':cost,'memory_after':state.memory,'full_match_credit':0,
            'rules_source':choice['rules'],'card_source':card_evidence,'scope_context_id':locked.matchup_id,
            'printed_trigger':'On Play','triggered_effects':[record['effect_id'] for record in effects],
            'play_method':'EFFECT_WITHOUT_PAYING_COST' if within_effect else 'MAIN_ACTION'}


def play_tamer_from_security(runtime,seat,source_key,root):
    """Play the checked no-area card only during its bound immediate effect."""
    from security_tamer import validate_security_activation,RULE_LOCATOR
    validate_security_activation(runtime,seat,source_key)
    return _play(runtime,seat,{'hand_key':source_key,'rules':{**_rules(root),'locator':RULE_LOCATOR}},
                 root,within_effect=True,source_zone='security_check')


def play_tamer_from_effect(runtime,seat,hand_key,root):
    """Trusted EX13-022 resolution primitive, never a nested public command."""
    from tamer_play_effects import PLAY_SPECS,ATTACK_TAMER_EFFECT,tamer_play_choices
    activated=getattr(runtime,'_activated_effect',None)
    if (runtime.halted or runtime.state.terminal or not isinstance(activated,tuple)
            or len(activated)!=5 or activated[0] not in ({spec[0] for spec in PLAY_SPECS.values()} | {ATTACK_TAMER_EFFECT}) or activated[1]!=seat
            or activated[3]!='main_text'
            or (runtime.state.phase!='SCENARIO' and activated[4] is None)):
        raise RuntimeHalt('EFFECT_PLAY_WINDOW_REQUIRED')
    source=runtime._source(seat,activated[2],'main_text')
    if not ((source.card_number in PLAY_SPECS and PLAY_SPECS[source.card_number][0]==activated[0])
            or (source.card_number=='EX13-019' and activated[0]==ATTACK_TAMER_EFFECT)):
        raise RuntimeHalt('EFFECT_PLAY_WINDOW_REQUIRED')
    if hand_key is None or hand_key not in tamer_play_choices(runtime,seat,source.key,activated[0]):
        raise RuntimeHalt('EFFECT_PLAY_TARGET_INVALID')
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 3-4-3; 7-1-3; 15-4; 15-9-2-2; EX13-022 Q7264'}
    cost_override = (max(0, runtime.context.card(seat, next(card.card_number
                    for card in runtime.state.zones[seat]['hand'] if card.key == hand_key)).to_dict()['play_cost'] - 2)
                     if activated[0] == ATTACK_TAMER_EFFECT else None)
    return _play(runtime,seat,{'hand_key':hand_key,'rules':rules},root,
                 within_effect=True,cost_override=cost_override)


def play_blue_scramble_from_trash(runtime,seat,trash_key,root):
    """Play the selected physical card directly from trash during LM-028 Delay."""
    from option_actions import BLUE_SCRAMBLE_DELAY,validate_option_activation
    validate_option_activation(runtime,seat,{BLUE_SCRAMBLE_DELAY},source_zone='trash')
    state=runtime.state
    if any(runtime.context.card(seat,s.cards[-1].card_number).kind=='Digimon'
           for s in state.battle[seat].values()):
        raise RuntimeHalt('BLUE_SCRAMBLE_PLAY_TARGET_INVALID')
    physical=next((c for c in state.zones[seat]['trash'] if c.key==trash_key),None)
    card=runtime.context.card(seat,physical.card_number) if physical is not None else None
    if (card is None or card.kind!='Digimon' or 'Blue' not in card.to_dict()['colors']
            or type(card.to_dict()['dp']) is not int or card.to_dict()['dp']>2000):
        raise RuntimeHalt('BLUE_SCRAMBLE_PLAY_TARGET_INVALID')
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 7-1-3; 15-8-3; LM-028 Start of Your Turn Delay'}
    return _play(runtime,seat,{'hand_key':trash_key,'rules':rules},root,
                 within_effect=True,source_zone='trash')


def choose_play(runtime,seat,hand_key,root):
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 1-3-11-1; 4-2; 6-5-1-1; 7-1-1 through 7-1-3-3'}
    def play(trial,controller,choice):return _play(trial,controller,choice,root)
    return runtime._control_command('PLAY_CARD',seat,{'hand_key':hand_key,'rules':rules},play)
