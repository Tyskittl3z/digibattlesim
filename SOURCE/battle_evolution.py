"""Ordinary printed digivolutions encountered in the locked Ulforce gameplay.

The physical Digimon keeps its incarnation, orientation, play history and
individual grants. Only the new top's actual When Digivolving trigger fires;
this action neither plays a card nor suspends/unsuspends a Digimon.
"""
from dataclasses import asdict
import re

from context_evolution import printed_evolution_options, UnsupportedEvolutionCondition
from context_runtime import RuntimeHalt
from effect_scheduler import queue_effects
from match_preparation import _rules
from printed_triggers import effect_body, effect_headers, trigger_lines
from selected_contexts import require_selected_context


RULE_LOCATOR = ('Comprehensive rules v4.3: 1-3-11-1; 3-4-5; 4-2-2; 6-5-1-2; '
                '8-1-1 through 8-1-3-3; 15-3-1; 15-4; 15-11-1; 15-13; 15-16-3-1')


def _digivolving_effect(runtime, target):
    """Require a handler for every actual new-top trigger before payment."""
    definition = runtime.context.card(target.owner, target.card_number)
    lines = trigger_lines(definition.effect_text('main_text'), 'When Digivolving')
    if not lines:
        return None
    from search_effects import SEARCH_SPECS
    from aero_effects import DIGIVOLVE_EFFECT, RETURN_LINE
    from tamer_play_effects import PLAY_SPECS
    if target.card_number == 'P-138' and lines == (SEARCH_SPECS['P-138'][1],):
        effect = SEARCH_SPECS['P-138'][0]
    elif target.card_number == 'BT22-023' and lines == (RETURN_LINE,):
        effect = DIGIVOLVE_EFFECT
    elif target.card_number in PLAY_SPECS:
        effect,line=PLAY_SPECS[target.card_number]
        if lines!=(line,):
            raise RuntimeHalt('BATTLE_DIGIVOLVING_EFFECT_UNSUPPORTED: '+target.card_number)
    else:
        raise RuntimeHalt('BATTLE_DIGIVOLVING_EFFECT_UNSUPPORTED: '
                          + target.card_number + ' timing=When Digivolving source=' + target.key)
    runtime.registry.lookup(target.card_number, effect, 'main_text')
    return effect


def _observer_dependencies(runtime, seat, source_key, target):
    """Check active event clauses, excluding quoted/self-trigger timing labels.

    None of the locked bootstrap's22 definitions observes another Digimon's
    ordinary evolution or evolution draw. Rina's text that activates a When
    Digivolving effect is triggered by suspension, and isn't such an observer.
    A genuinely new live observer remains an explicit dependency, not a skip.
    """
    target_definition = runtime.context.card(seat, target.card_number)
    for owner in ('A', 'B'):
        for key, stack in runtime.state.battle[owner].items():
            cards = stack.cards + [target] if owner == seat and key == source_key else stack.cards
            for index, physical in enumerate(cards):
                field = 'main_text' if index == len(cards) - 1 else 'inherited_text'
                text = runtime.context.card(owner, physical.card_number).effect_text(field)
                for line in text.splitlines():
                    headers = effect_headers(line)
                    if ('Your Turn' in headers and owner != runtime.state.active
                            or "Opponent's Turn" in headers and owner == runtime.state.active):
                        continue
                    clause = effect_body(line).split(',', 1)[0]
                    if not clause.startswith('When '):
                        continue
                    if not re.search(r'\bdigivolv(?:e|es|ed|ing)\b|\bdraw(?:s|n)?\b', clause, re.I):
                        continue
                    if 'your Digimon' in clause and owner != seat:
                        continue
                    if 'this Digimon' in clause and not (owner == seat and key == source_key):
                        continue
                    # The original selected-pair lock also includes this exact
                    # Takato observer. Its printed name condition is false for
                    # the Ulforce target cards; do not invent an activation.
                    if physical.card_number == 'BT19-080' and not any(
                            name in target_definition.name for name in ('Growlmon', 'Gallantmon')):
                        continue
                    raise RuntimeHalt('BATTLE_EVOLUTION_OBSERVER_UNSUPPORTED: '
                                      + physical.card_number + ' ' + field + ' source=' + physical.key)


def _choose(runtime, seat, choice, root, *, within_effect=False):
    state = runtime.state
    locked = require_selected_context(runtime.context, root)
    if not runtime.allow_experimental:
        raise RuntimeHalt('EXPERIMENTAL_OPT_IN_REQUIRED')
    if seat != state.active:
        raise RuntimeHalt('ACTIVE_PLAYER_REQUIRED')
    if not within_effect and state.phase != 'MAIN':
        raise RuntimeHalt('MAIN_PHASE_REQUIRED')
    if not within_effect and state.memory < 0:
        raise RuntimeHalt('TURN_END_WINDOW_UNIMPLEMENTED')
    # Reduction is only legal inside the resolution of its own bound effect.
    # Ordinary main actions cannot request a free-standing discount.
    if type(choice['cost_reduction']) is not int or choice['cost_reduction'] < 0 or (not within_effect and choice['cost_reduction'] != 0):
        raise RuntimeHalt('UNBOUND_EVOLUTION_COST_REDUCTION')
    source_key, target_key, index = choice['source_key'], choice['hand_key'], choice['route_index']
    stack = state.battle[seat].get(source_key)
    if stack is None:
        raise RuntimeHalt('BATTLE_EVOLUTION_SOURCE_REQUIRED: ' + str(source_key))
    source = stack.cards[-1]
    if runtime.context.card(seat, source.card_number).kind != 'Digimon':
        raise RuntimeHalt('BATTLE_EVOLUTION_SOURCE_TYPE_INVALID: ' + source_key)
    target = next((c for c in state.zones[seat]['hand'] if c.key == target_key), None)
    if target is None:
        raise RuntimeHalt('HAND_COPY_REQUIRED: ' + str(target_key))
    definition = runtime.context.card(seat, target.card_number)
    if definition.kind != 'Digimon':
        raise RuntimeHalt('BATTLE_EVOLUTION_TARGET_TYPE_INVALID: ' + str(target_key))
    try:
        routes = printed_evolution_options(runtime.context, seat, source.card_number, target.card_number)
    except UnsupportedEvolutionCondition as exc:
        raise RuntimeHalt('PRINTED_BATTLE_EVOLUTION_ROUTE_UNSUPPORTED: ' + str(exc)) from exc
    if type(index) is not int or not 0 <= index < len(routes):
        raise RuntimeHalt('ROUTE_INDEX_INVALID: ' + str(index))
    route = routes[index]
    cost=max(0,route.cost-choice['cost_reduction'])
    if type(route.cost) is not int or route.cost < 0 or cost > state.memory + 10:
        raise RuntimeHalt('INSUFFICIENT_AVAILABLE_MEMORY: cost=' + str(route.cost))
    effect = _digivolving_effect(runtime, target)
    from battlefield_scope import assert_basic_board_scope
    assert_basic_board_scope(runtime, 'battle_evolve', root, within_effect=within_effect)
    _observer_dependencies(runtime, seat, source_key, target)
    from selected_mechanics import _source_evidence
    sources = [_source_evidence(root, runtime.context.card(seat, physical.card_number).to_dict()['official_source'],
        '#' + physical.card_number + ' printed identity, evolution conditions and active effect text').manifest()
        for physical in (source, target)]
    memory_before = state.memory
    state.memory -= cost
    state.zones[seat]['hand'].remove(target)
    del state.battle[seat][source_key]
    stack.cards.append(target)
    state.battle[seat][target.key] = stack
    deck = state.zones[seat]['deck']
    drawn = deck.pop() if deck else None
    if drawn is not None:
        state.zones[seat]['hand'].append(drawn)
    if effect is not None:
        usage=[]
        if target.card_number=='EX13-022':
            from tamer_play_effects import tamer_play_usage
            usage=list(tamer_play_usage(runtime,seat,target.key,effect))
        queue_effects(runtime, [{'seat': seat, 'source': target.key, 'effect_id': effect,
            'field': 'main_text', 'usage':usage,'trigger': {'kind': 'When Digivolving', 'card': target.key,
                                            'previous_top': source_key}}])
    return {'source_key': source_key, 'hand_key': target_key, 'route_index': index,
            'route': asdict(route), 'cost': cost, 'cost_reduction':choice['cost_reduction'], 'memory_after': state.memory,
            'drew': drawn is not None, 'drawn_card': drawn.key if drawn else None,
            'rules_source': choice['rules'], 'card_sources': sources,
            'scope_context_id': locked.matchup_id,
            'triggered_effects': [effect] if effect is not None else [],
            'steps': [{'operation': 'DECLARE_DIGIVOLUTION', 'source': source_key,
                       'target': target_key, 'route_index': index, 'route': asdict(route)},
                      {'operation': 'PAY_DIGIVOLUTION_COST', 'cost': cost,
                       'memory_before': memory_before, 'memory_after': state.memory},
                      {'operation': 'STACK_DIGIMON', 'previous_top': source_key,
                       'new_top': target_key, 'instance': stack.instance_id},
                      {'operation': 'EVOLUTION_DRAW', 'card': drawn.key if drawn else None},
                      {'operation': 'TRIGGER_WHEN_DIGIVOLVING',
                       'effects': [effect] if effect is not None else []}],
            'full_match_credit': 0}


def trusted_evolve_from_effect(runtime,seat,source_key,hand_key,route_index,root):
    """Use only the fixed reduction of the active bound, paid card effect."""
    from option_actions import OPTION_EVOLUTION_EFFECTS,validate_option_activation,option_evolution_choices
    activated=getattr(runtime,'_activated_effect',None)
    effect=activated[0] if isinstance(activated,tuple) and activated else None
    from rina_unsuspend_effects import EX13_EVOLVE_EFFECT,validate_rina_continuation,rina_evolution_choices
    choice={'source_key':source_key,'hand_key':hand_key,'route_index':route_index}
    if effect==EX13_EVOLVE_EFFECT:
        validate_rina_continuation(runtime,seat)
        if choice not in rina_evolution_choices(runtime,seat):
            raise RuntimeHalt('RINA_EVOLUTION_CHOICE_INVALID')
        return _choose(runtime,seat,{**choice,'cost_reduction':2,
            'rules':{**_rules(root),'locator':RULE_LOCATOR}},root,within_effect=True)
    spec=OPTION_EVOLUTION_EFFECTS.get(effect)
    if spec is None:raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    source=validate_option_activation(runtime,seat,(effect,),source_zone=spec['source_zone'])
    if source.card_number!=spec['number']:raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    if choice not in option_evolution_choices(runtime,seat,effect):
        raise RuntimeHalt('OPTION_EVOLUTION_CHOICE_INVALID')
    return _choose(runtime,seat,{**choice,'cost_reduction':spec['reduction'],
        'rules':{**_rules(root),'locator':RULE_LOCATOR}},root,within_effect=True)


def choose_battle_evolution(runtime, seat, source_key, hand_key, route_index, root, *, cost_reduction=0):
    """Choose an ordinary evolution; effect-bound reductions are separate work."""
    rules = {**_rules(root), 'locator': RULE_LOCATOR}
    return runtime._control_command('BATTLE_EVOLUTION', seat,
        {'source_key': source_key, 'hand_key': hand_key, 'route_index': route_index,
         'cost_reduction': cost_reduction, 'rules': rules},
        lambda trial, controller, choice: _choose(trial, controller, choice, root))
