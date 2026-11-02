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


def _play(runtime,seat,choice,root,*,within_effect=False):
    state=runtime.state
    try:
        locked=require_selected_context(runtime.context,root)
    except RuntimeHalt as exc:
        raise RuntimeHalt('SELECTED_PLAY_CAPABILITY_REQUIRED') from exc
    if not runtime.allow_experimental:raise RuntimeHalt('UNREVIEWED_MAIN_ACTION')
    if not within_effect and (seat!=state.active or state.phase!='MAIN' or state.memory<0):
        raise RuntimeHalt('MAIN_PLAY_WINDOW_NOT_OPEN')
    hand=state.zones[seat]['hand']
    physical=next((c for c in hand if c.key==choice['hand_key']),None)
    if physical is None:raise RuntimeHalt('PLAY_CARD_NOT_IN_HAND')
    card=runtime.context.card(seat,physical.card_number)
    from selected_mechanics import _source_evidence
    card_evidence=_source_evidence(root,card.to_dict()['official_source'],
                                   '#'+card.number+' printed type, play cost and main effects').manifest()
    if card.kind=='Option':raise RuntimeHalt('OPTION_USE_UNIMPLEMENTED: '+card.number)
    if card.kind not in ('Digimon','Tamer'):raise RuntimeHalt('PLAY_CARD_TYPE_INVALID')
    spec=(SEARCH_SPECS.get(card.number) or ON_PLAY_SPECS.get(card.number)
          or PLAY_SPECS.get(card.number) or TAMER_PLAY_SPECS.get(card.number))
    on_play=trigger_lines(card.effect_text('main_text'),'On Play')
    if on_play and (spec is None or on_play!=(spec[1],)):
        raise RuntimeHalt('PLAY_EFFECT_UNSUPPORTED: '+card.number+' timing=On Play')
    if not on_play:spec=None
    from battlefield_scope import assert_basic_board_scope
    assert_basic_board_scope(runtime,'play_search' if spec is not None else 'play_plain',root,
        event={'seat':seat,'card_number':card.number},within_effect=within_effect)
    if spec is not None:
        runtime.registry.lookup(card.number,spec[0],'main_text')
    cost=0 if within_effect else card.to_dict()['play_cost']
    if type(cost) is not int or cost<0 or cost>state.memory+10:
        raise RuntimeHalt('PLAY_COST_NOT_PAYABLE')
    state.memory-=cost;hand.remove(physical)
    state.entity_sequence+=1
    state.battle[seat][physical.key]=Stack([physical],instance_id='entity-'+str(state.entity_sequence),
                                         played_turn=state.turn,ready_since_turn=state.turn+1)
    effects=[]
    if spec is not None:
        record={'seat':seat,'source':physical.key,'effect_id':spec[0],'field':'main_text',
                'trigger':{'kind':'On Play','card':physical.key}}
        if card.number in TAMER_PLAY_SPECS:
            from tamer_play_effects import tamer_play_usage
            record['usage']=list(tamer_play_usage(runtime,seat,physical.key,spec[0]))
        effects.append(record)
    from tamer_play_effects import collect_tamer_play_reactions
    effects.extend(collect_tamer_play_reactions(runtime,seat,physical))
    queue_effects(runtime,effects)
    return {'played_card':physical.key,'cost':cost,'memory_after':state.memory,'full_match_credit':0,
            'rules_source':choice['rules'],'card_source':card_evidence,'scope_context_id':locked.matchup_id,
            'printed_trigger':'On Play','triggered_effects':[record['effect_id'] for record in effects],
            'play_method':'EFFECT_WITHOUT_PAYING_COST' if within_effect else 'MAIN_ACTION'}


def play_tamer_from_effect(runtime,seat,hand_key,root):
    """Trusted EX13-022 resolution primitive, never a nested public command."""
    from tamer_play_effects import PLAY_EFFECT,tamer_play_choices
    activated=getattr(runtime,'_activated_effect',None)
    if (runtime.halted or runtime.state.terminal or not isinstance(activated,tuple)
            or len(activated)!=5 or activated[0]!=PLAY_EFFECT or activated[1]!=seat
            or activated[3]!='main_text'
            or (runtime.state.phase!='SCENARIO' and activated[4] is None)):
        raise RuntimeHalt('EFFECT_PLAY_WINDOW_REQUIRED')
    source=runtime._source(seat,activated[2],'main_text')
    if source.card_number!='EX13-022':
        raise RuntimeHalt('EFFECT_PLAY_WINDOW_REQUIRED')
    if hand_key is None or hand_key not in tamer_play_choices(runtime,seat,source.key,PLAY_EFFECT):
        raise RuntimeHalt('EFFECT_PLAY_TARGET_INVALID')
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 3-4-3; 7-1-3; 15-4; 15-9-2-2; EX13-022 Q7264'}
    return _play(runtime,seat,{'hand_key':hand_key,'rules':rules},root,within_effect=True)


def choose_play(runtime,seat,hand_key,root):
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 1-3-11-1; 4-2; 6-5-1-1; 7-1-1 through 7-1-3-3'}
    def play(trial,controller,choice):return _play(trial,controller,choice,root)
    return runtime._control_command('PLAY_CARD',seat,{'hand_key':hand_key,'rules':rules},play)
