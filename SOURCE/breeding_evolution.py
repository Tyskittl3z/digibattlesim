"""Experimental printed routes with empty or verified inert battle areas.

Official comprehensive rules v4.3, 3-4-7-3..8: ordinary effects on/involving
breeding cards do not activate or trigger. 8-1-3-1..3 specifies choose, pay,
stack, draw; 8-1-2-8 permits evolution without a draw. Explicit breeding-area
effect exceptions remain unsupported and halt. No full matches are credited.
"""
from dataclasses import asdict

from context_evolution import printed_evolution_options, UnsupportedEvolutionCondition
from context_runtime import RuntimeHalt
from match_preparation import _rules
from pathlib import Path
from selected_contexts import require_selected_context


RULE_LOCATOR = ('Comprehensive rules v4.3: 1-3-11-1; 3-4-7-3 through 3-4-7-8; '
                '6-5; 8-1-2-8; 8-1-3-1 through 8-1-3-3')


def _guard(runtime, seat, root=None):
    runtime.context.deck(seat)
    try:
        require_selected_context(runtime.context,root or Path(__file__).resolve().parents[1])
    except RuntimeHalt as exc:
        raise RuntimeHalt('SELECTED_PAIR_REQUIRED') from exc
    runtime.verify()
    if runtime.halted:raise RuntimeHalt('ALREADY_HALTED')
    if runtime.state.terminal:raise RuntimeHalt('ACTION_AFTER_TERMINAL')
    if not runtime.allow_experimental:raise RuntimeHalt('EXPERIMENTAL_OPT_IN_REQUIRED')
    if seat != runtime.state.active:raise RuntimeHalt('ACTIVE_PLAYER_REQUIRED')
    if runtime.state.phase != 'MAIN':raise RuntimeHalt('MAIN_PHASE_REQUIRED')
    if runtime.state.pending:raise RuntimeHalt('PENDING_EFFECTS_REQUIRE_RESOLUTION')
    if runtime.state.memory < 0:raise RuntimeHalt('TURN_END_WINDOW_UNIMPLEMENTED')
    if any(runtime.state.battle[owner] for owner in ('A','B')):
        from battlefield_scope import assert_basic_board_scope
        assert_basic_board_scope(runtime,'breeding_evolve',root or Path(__file__).resolve().parents[1])
    if not runtime.state.breeding[seat]:raise RuntimeHalt('BREEDING_SOURCE_REQUIRED')
    top=runtime.state.breeding[seat][-1]
    if runtime.context.card(seat,top.card_number).kind not in ('Digi-Egg','Digimon'):
        raise RuntimeHalt('BREEDING_SOURCE_TYPE_UNSUPPORTED: '+top.key)


def _routes(runtime,seat,target):
    base=runtime.state.breeding[seat][-1]
    try:
        return printed_evolution_options(runtime.context,seat,base.card_number,target.card_number)
    except UnsupportedEvolutionCondition as exc:
        raise RuntimeHalt('PRINTED_EVOLUTION_ROUTE_UNSUPPORTED: '+target.card_number+' '+str(exc)) from exc


def _exceptions(runtime,seat,target):
    # The rules explicitly exempt breeding-referencing effects from ordinary
    # suppression. Do not silently suppress those exceptions on either stack.
    cards=[target]+[c for owner in ('A','B') for c in runtime.state.breeding[owner]]
    for card in cards:
        definition=runtime.context.card(card.owner,card.card_number)
        for field in ('main_text','inherited_text'):
            if 'breeding' in definition.effect_text(field).lower():
                raise RuntimeHalt('BREEDING_EXPLICIT_EFFECT_UNSUPPORTED: '+card.key+' '+field)


def breeding_evolution_choices(runtime,seat):
    """Return recomputable printed routes for physical hand copies, no mutation."""
    _guard(runtime,seat)
    choices=[]
    for card in runtime.state.zones[seat]['hand']:
        routes=_routes(runtime,seat,card)
        if routes:_exceptions(runtime,seat,card)
        for index,route in enumerate(routes):
            if route.cost <= runtime.state.memory+10:
                choices.append({'hand_key':card.key,'source_key':runtime.state.breeding[seat][-1].key,
                                'route_index':index,**asdict(route)})
    return choices


def _choose(runtime,seat,choice,root):
    _guard(runtime,seat,root)
    key=choice['hand_key'];index=choice['route_index']
    card=next((c for c in runtime.state.zones[seat]['hand'] if c.key==key),None)
    if card is None:raise RuntimeHalt('HAND_COPY_REQUIRED: '+str(key))
    routes=_routes(runtime,seat,card)
    if type(index) is not int or not 0<=index<len(routes):
        raise RuntimeHalt('ROUTE_INDEX_INVALID: '+str(index))
    route=routes[index]
    if route.cost>runtime.state.memory+10:
        raise RuntimeHalt('INSUFFICIENT_AVAILABLE_MEMORY: cost='+str(route.cost))
    _exceptions(runtime,seat,card)
    base=runtime.state.breeding[seat][-1]
    runtime.state.memory-=route.cost
    runtime.state.zones[seat]['hand'].remove(card)
    runtime.state.breeding[seat].append(card)
    deck=runtime.state.zones[seat]['deck'];drew=bool(deck)
    if drew:runtime.state.zones[seat]['hand'].append(deck.pop())
    if runtime.state.memory<0:runtime.state.phase='END_OF_TURN'
    return {'hand_key':key,'source_key':base.key,'route_index':index,'route':asdict(route),
            'cost':route.cost,'drew':drew,'memory':runtime.state.memory,'phase':runtime.state.phase,
            'rules_source':choice['rules'],'full_match_credit':0}


def choose_breeding_evolution(runtime,seat,hand_key,route_index,root):
    evidence=_rules(root)
    evidence={**evidence,'locator':RULE_LOCATOR}
    return runtime._control_command('BREEDING_EVOLUTION',seat,
            {'hand_key':hand_key,'route_index':route_index,'rules':evidence},
            lambda r,s,c:_choose(r,s,c,root))
