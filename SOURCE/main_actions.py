"""Main-phase play actions scoped to verified inert singleton battlefields.

Unknown On Play, Option, live replacement/trigger and Assembly interactions
halt before card/cost mutation. This is not a complete main-action generator.
"""
from context_runtime import RuntimeHalt,Stack
from effect_scheduler import queue_effects
from match_preparation import _rules
from search_effects import SEARCH_SPECS
from pathlib import Path

PLAIN_MAIN_TEXT = {'EX1-013':'','ST7-05':'','BT9-011':''}


def _play(runtime,seat,choice,root):
    state=runtime.state
    from matchup_readiness import load_context_file
    locked=load_context_file(Path(root)/'ARTIFACTS/ex13-engine-2026-10-30/context.json')
    if ((runtime.context.deck_a.source_id,runtime.context.deck_b.source_id)!=('123129','124303')
            or runtime.context.matchup_id!=locked.matchup_id):
        raise RuntimeHalt('SELECTED_PLAY_CAPABILITY_REQUIRED')
    if not runtime.allow_experimental:raise RuntimeHalt('UNREVIEWED_MAIN_ACTION')
    if seat!=state.active or state.phase!='MAIN' or state.memory<0:
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
    spec=SEARCH_SPECS.get(card.number)
    if spec is None and (card.number not in PLAIN_MAIN_TEXT or card.effect_text('main_text')!=PLAIN_MAIN_TEXT[card.number]):
        raise RuntimeHalt('PLAY_EFFECT_UNSUPPORTED: '+card.number)
    from battlefield_scope import assert_basic_board_scope
    assert_basic_board_scope(runtime,'play_search' if spec is not None else 'play_plain',root)
    if spec is not None:
        runtime.registry.lookup(card.number,spec[0],'main_text')
    cost=card.to_dict()['play_cost']
    if type(cost) is not int or cost<0 or cost>state.memory+10:
        raise RuntimeHalt('PLAY_COST_NOT_PAYABLE')
    state.memory-=cost;hand.remove(physical)
    state.entity_sequence+=1
    state.battle[seat][physical.key]=Stack([physical],instance_id='entity-'+str(state.entity_sequence),
                                         played_turn=state.turn,ready_since_turn=state.turn+1)
    if spec is not None:
        queue_effects(runtime,[{'seat':seat,'source':physical.key,'effect_id':spec[0],'field':'main_text',
                                'trigger':{'kind':'On Play','card':physical.key}}])
    return {'played_card':physical.key,'cost':cost,'memory_after':state.memory,'full_match_credit':0,
            'rules_source':choice['rules'],'card_source':card_evidence,'scope_context_id':locked.matchup_id}


def choose_play(runtime,seat,hand_key,root):
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 1-3-11-1; 4-2; 6-5-1-1; 7-1-1 through 7-1-3-3'}
    def play(trial,controller,choice):return _play(trial,controller,choice,root)
    return runtime._control_command('PLAY_CARD',seat,{'hand_key':hand_key,'rules':rules},play)
