"""Source-bound opening preparation (rules v4.3 section 5), zero match credit."""
import json
from pathlib import Path

from context_runtime import RuntimeHalt
from selected_mechanics import _source_evidence


def _rules(root):
    index=json.loads((Path(root)/'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json').read_bytes())
    raw=next(s for s in index['sources'] if s['id']=='rules')
    return _source_evidence(root,raw,'Comprehensive rules v4.3: 5-2-1-1 through 5-2-1-8').manifest()


def _begin(runtime,seat,choice):
    state=runtime.state
    if (state.preparation['started'] or state.phase!='SCENARIO' or state.turn!=0
            or state.memory!=0 or state.active!=runtime.first):
        raise RuntimeHalt('PREPARATION_ALREADY_STARTED')
    for owner in ('A','B'):
        zones=state.zones[owner]
        if state.battle[owner] or state.breeding[owner] or any(zones[z] for z in ('hand','security','trash')):
            raise RuntimeHalt('PREPARATION_REQUIRES_UNDEALT_DECKS')
        if len(zones['deck'])!=50:
            raise RuntimeHalt('PREPARATION_REQUIRES_50_MAIN_CARDS')
    for owner in ('A','B'):
        for _ in range(5):
            state.zones[owner]['hand'].append(state.zones[owner]['deck'].pop())
    state.preparation={'started':True,'choices':[],'rules_source':choice['rules']}
    state.phase='INITIAL_HANDS'
    return {'initial_hands':{'A':5,'B':5},'next_controller':runtime.first,
            'rules_source':choice['rules'],'full_match_credit':0}


def begin_preparation(runtime,root):
    return runtime._control_command('BEGIN_PREPARATION',runtime.first,
                                    {'rules':_rules(root)},_begin)


def _redraw(runtime,seat,choice):
    state=runtime.state
    if type(choice['redraw']) is not bool:
        raise RuntimeHalt('BOOLEAN_REDRAW_CHOICE_REQUIRED')
    if state.phase!='INITIAL_HANDS' or not state.preparation['started']:
        raise RuntimeHalt('REDRAW_WINDOW_NOT_OPEN')
    order=[runtime.first,'B' if runtime.first=='A' else 'A']
    index=len(state.preparation['choices'])
    if index>=2 or seat!=order[index]:
        raise RuntimeHalt('REDRAW_CONTROLLER_ORDER')
    if choice['rules']!=state.preparation['rules_source']:
        raise RuntimeHalt('PREPARATION_RULES_CHANGED')
    zones=state.zones[seat]
    if choice['redraw']:
        zones['deck'].extend(zones['hand']);zones['hand']=[]
        runtime.rng.shuffle(zones['deck'])
        for _ in range(5):zones['hand'].append(zones['deck'].pop())
    state.preparation['choices'].append({'seat':seat,'redraw':choice['redraw']})
    if len(state.preparation['choices'])==2:
        for owner in ('A','B'):
            zones=state.zones[owner]
            for _ in range(5):zones['security'].append(zones['deck'].pop())
        state.memory=0;state.turn=1;state.active=runtime.first;state.phase='START_OF_TURN'
    return {'redraw':choice['redraw'],'phase':state.phase,'full_match_credit':0}


def choose_redraw(runtime,seat,redraw,root):
    return runtime._control_command('REDRAW_CHOICE',seat,
                                    {'redraw':redraw,'rules':_rules(root)},_redraw)
