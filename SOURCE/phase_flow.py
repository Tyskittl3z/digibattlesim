"""Selected-pair opening phases, with explicit trigger and breeding choices.

Main actions/attacks are separate modules; this module also records experimental
draw-phase deckout. Unsupported timing/status interactions halt before commit.
"""
from context_runtime import RuntimeHalt,Stack
from effect_scheduler import queue_effects
from match_preparation import _rules
from selected_mechanics import PHASE_EFFECTS,_orientation_dependencies,_orientation_reactions
from search_effects import SEARCH_SPECS


def _actor(runtime,seat):
    if seat!=runtime.state.active:
        raise RuntimeHalt('ACTIVE_PLAYER_REQUIRED')
    if runtime.state.memory<0:
        raise RuntimeHalt('TURN_END_WINDOW_UNIMPLEMENTED')
    for owner in ('A','B'):
        for stack in runtime.state.battle[owner].values():
            if set(stack.statuses)-{'cannot_suspend','cannot_unsuspend'}:
                raise RuntimeHalt('PHASE_STATUS_UNSUPPORTED: '+stack.cards[-1].key)


def _phase_triggers(runtime,seat,timing):
    effects=[]
    for stack in runtime.state.battle[seat].values():
        for index,card in enumerate(stack.cards):
            field='main_text' if index==len(stack.cards)-1 else 'inherited_text'
            text=runtime.context.card(seat,card.card_number).effect_text(field)
            if '['+timing+']' not in text:continue
            spec=PHASE_EFFECTS.get(card.card_number)
            if field!='main_text' or not spec or spec[1]!=timing or spec[2] not in text.splitlines():
                raise RuntimeHalt('PHASE_TRIGGER_UNSUPPORTED: '+card.card_number+' '+timing)
            effects.append({'seat':seat,'source':card.key,'effect_id':spec[0],'field':field,
                            'trigger':{'kind':timing,'phase':runtime.state.phase}})
    queue_effects(runtime,effects)


def _advance(runtime,seat,choice):
    _actor(runtime,seat)
    state=runtime.state
    if state.phase=='START_OF_TURN':
        state.phase='TURN_START_EFFECTS'
        _phase_triggers(runtime,seat,'Start of Your Turn')
    elif state.phase=='TURN_START_EFFECTS':
        state.phase='UNSUSPEND'
        changed=[s for s in state.battle[seat].values() if s.suspended and not s.statuses.get('cannot_unsuspend',False)]
        if changed:_orientation_dependencies(runtime)
        # Rule 6-2-1: all cards unsuspend simultaneously. Collect reactions only
        # after every affected card has changed orientation.
        for stack in changed:stack.suspended=False
        for stack in changed:_orientation_reactions(runtime,seat,stack,True)
        if not state.pending:state.phase='DRAW'
    elif state.phase=='UNSUSPEND':
        # Pending guards ensure all unsuspend processing has finished before
        # rule 6-1-3 permits the draw phase to begin.
        state.phase='DRAW'
    elif state.phase=='DRAW':
        if not (state.turn==1 and seat==runtime.first):
            if not state.zones[seat]['deck']:
                state.terminal=True;state.winner='B' if seat=='A' else 'A'
                state.terminal_reason='DRAW_PHASE_DECKOUT'
                return {'phase':state.phase,'winner':state.winner,'status':'EXPERIMENTAL_TERMINAL',
                        'full_match_credit':0,'rules_source':choice['rules']}
            state.zones[seat]['hand'].append(state.zones[seat]['deck'].pop())
        state.phase='BREEDING'
    elif state.phase=='MAIN':
        raise RuntimeHalt('MAIN_ACTION_REQUIRED_NOT_IMPLICIT_PASS')
    elif state.phase=='BREEDING_MOVING_EFFECTS':
        state.phase='MAIN'
        _phase_triggers(runtime,seat,'Start of Your Main Phase')
    else:
        raise RuntimeHalt('PHASE_ADVANCE_NOT_AVAILABLE: '+state.phase)
    return {'phase':state.phase,'full_match_credit':0,'rules_source':choice['rules']}


def advance_phase(runtime,seat,root):
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 1-2-3-2; 6-1 through 6-4; 15-4'}
    return runtime._control_command('ADVANCE_PHASE',seat,{'rules':rules},_advance)


def _breeding(runtime,seat,choice):
    _actor(runtime,seat)
    state=runtime.state;action=choice['action']
    if state.phase!='BREEDING':raise RuntimeHalt('BREEDING_WINDOW_NOT_OPEN')
    if action=='hatch':
        if state.breeding[seat] or not state.zones[seat]['eggdeck']:
            raise RuntimeHalt('HATCH_NOT_AVAILABLE')
        state.breeding[seat]=[state.zones[seat]['eggdeck'].pop()]
    elif action=='promote':
        cards=state.breeding[seat]
        if not cards:raise RuntimeHalt('PROMOTION_NOT_AVAILABLE')
        top=cards[-1];definition=runtime.context.card(seat,top.card_number).to_dict()
        if definition['type']!='Digimon' or not isinstance(definition['level'],int) or definition['level']<3:
            raise RuntimeHalt('PROMOTION_REQUIRES_LEVEL_3_OR_HIGHER')
        moving=None
        if '[When Moving]' in definition['main_text']:
            moving=SEARCH_SPECS.get(top.card_number)
            if moving is None or '[When Moving]' not in moving[1] or moving[1] not in definition['main_text'].splitlines():
                raise RuntimeHalt('WHEN_MOVING_UNSUPPORTED: '+top.card_number)
        state.entity_sequence+=1
        state.battle[seat][top.key]=Stack(list(cards),instance_id='entity-'+str(state.entity_sequence),
                                        ready_since_turn=state.turn)
        state.breeding[seat]=[]
        if moving is not None:
            queue_effects(runtime,[{'seat':seat,'source':top.key,'effect_id':moving[0],'field':'main_text',
                                   'trigger':{'kind':'When Moving','card':top.key}}])
            state.phase='BREEDING_MOVING_EFFECTS'
            return {'action':action,'phase':state.phase,'full_match_credit':0,'rules_source':choice['rules']}
    elif action!='skip':raise RuntimeHalt('BREEDING_CHOICE_INVALID')
    state.phase='MAIN'
    _phase_triggers(runtime,seat,'Start of Your Main Phase')
    return {'action':action,'phase':state.phase,'full_match_credit':0,'rules_source':choice['rules']}


def choose_breeding_action(runtime,seat,action,root):
    rules={**_rules(root),'locator':'Comprehensive rules v4.3: 4-17; 4-18; 6-4; 6-5; 15-4'}
    return runtime._control_command('BREEDING_CHOICE',seat,{'action':action,'rules':rules},_breeding)
