"""Encountered Option Main and Delay processing, with explicit live choices.

A used Option is outside all areas until its first Main resolves (CR9-1-4).
Delay pays its own trashing condition only after explicit activation. Deck
arrays run bottom to top; the first bottom_order key is bottommost.
"""
from dataclasses import replace
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding, RuntimeHalt, Stack
from effect_scheduler import queue_effects
from match_context import require
from match_preparation import _rules


OPTION_SPECS = {
    'P-104': ('P-104.main_search', '[Main] Reveal the top 2 cards of your deck. Add 1 blue card among them to the hand. Return the rest to the bottom of the deck in any order. Then, place this card in the battle area.', 2),
    'LM-034': ('LM-034.main_search', '[Main] Reveal the top 3 cards of your deck. Add 1 blue or red Digimon card among them to the hand. Return the rest to the bottom of the deck. Then, place this card in the battle area.', 3),
    'LM-056': ('LM-056.main_search', '[Main] Reveal the top 2 cards of your deck. Add 1 purple or blue card among them to the hand. Return the rest to the bottom of the deck. Then, place this card in the battle area.', 2),
    'LM-057': ('LM-057.main_search', '[Main] Reveal the top 2 cards of your deck. Add 1 red or blue card among them to the hand. Return the rest to the bottom of the deck. Then, place this card in the battle area.', 2),
    'LM-058': ('LM-058.main_search', '[Main] Reveal the top 2 cards of your deck. Add 1 blue or green card among them to the hand. Return the rest to the bottom of the deck. Then, place this card in the battle area.', 2),
    'LM-028': ('LM-028.main_evolve', '[Main] 1 of your blue Digimon may digivolve into a blue Digimon card in the hand with the digivolution cost reduced by 3. Then, place this card in the battle area.', 0),
}
_SEARCH_COLORS = {'P-104': ('Blue',), 'LM-034': ('Blue','Red'),
    'LM-056': ('Purple','Blue'), 'LM-057': ('Red','Blue'), 'LM-058': ('Blue','Green')}
_TRAINING_NAMES = {'LM-056':'Image Training','LM-057':'Wall Training','LM-058':'Parkour Training'}
BLUE_SCRAMBLE_DELAY = 'LM-028.start_turn_delay'
DELAY_SPECS = {
    'P-104': ('P-104.main_delay', '[Main] ＜Delay＞', '・1 of your Digimon may digivolve into a blue Digimon card in your hand for its digivolution cost. When it would digivolve by this effect, reduce the cost by 2.'),
    'LM-034': ('LM-034.main_delay', '[Main] ＜Delay＞', '・Gain 2 memory.'),
    'LM-056': ('LM-056.main_delay', '[Main] ＜Delay＞', '・1 of your Digimon may digivolve into a purple or blue Digimon card in the hand with the digivolution cost reduced by 2.'),
    'LM-057': ('LM-057.main_delay', '[Main] ＜Delay＞', '・1 of your Digimon may digivolve into a red or blue Digimon card in the hand with the cost reduced by 2.'),
    'LM-058': ('LM-058.main_delay', '[Main] ＜Delay＞', '・1 of your Digimon may digivolve into a blue or green Digimon card in the hand with the cost reduced by 2.'),
    'LM-028': (BLUE_SCRAMBLE_DELAY, '[Start of Your Turn] If your opponent has a Digimon, ＜Delay＞.', '・Return 1 blue Digimon card from your trash to the top of the deck. Then, if you don\'t have a Digimon, you may play 1 blue Digimon card with 2000 DP or less from your trash without paying the cost.'),
}
OPTION_EVOLUTION_EFFECTS = {
    'LM-028.main_evolve': {'number':'LM-028','reduction':3,'target_colors':('Blue',),'base_colors':('Blue',),'source_zone':'resolving'},
    **{n+'.main_delay': {'number':n,'reduction':2,'target_colors':colors,'base_colors':(),
                       'source_zone':'trash'} for n,colors in _SEARCH_COLORS.items() if n!='LM-034'},
}
_RULES_LOCATOR = ('Comprehensive rules v4.3: 3-4-6; 4-3-1; 4-22-1 through 4-22-4; '
    '6-5-1-3; 8-1; 9-1-1 through 9-1-9; 15-8-3-9; 15-10-2-1; 15-15-3; 16-17-1 through 16-17-3')


def option_colors_met(runtime, seat, card):
    colors = set()
    for stack in runtime.state.battle[seat].values():
        top = runtime.context.card(seat, stack.cards[-1].card_number)
        if top.kind in ('Digimon','Tamer'):
            colors.update(top.to_dict()['colors'])
    if runtime.state.breeding[seat]:
        top = runtime.context.card(seat, runtime.state.breeding[seat][-1].card_number)
        if top.kind in ('Digi-Egg','Digimon'):
            colors.update(top.to_dict()['colors'])
    if card.number in _TRAINING_NAMES and not any(
            runtime.context.card(seat,s.cards[-1].card_number).name == _TRAINING_NAMES[card.number]
            for s in runtime.state.battle[seat].values()):
        return True
    if card.number == 'LM-034':
        return bool(colors.intersection(('Blue','Red')))
    return set(card.to_dict()['colors']) <= colors


def _use(runtime, seat, choice, root):
    from battlefield_scope import assert_basic_board_scope
    from selected_contexts import require_selected_context
    from selected_mechanics import _source_evidence
    state = runtime.state
    locked = require_selected_context(runtime.context, root)
    if not runtime.allow_experimental:
        raise RuntimeHalt('UNREVIEWED_OPTION_ACTION')
    if seat != state.active or state.phase != 'MAIN' or state.memory < 0:
        raise RuntimeHalt('MAIN_OPTION_WINDOW_NOT_OPEN')
    if state.resolving_option is not None:
        raise RuntimeHalt('OPTION_USE_ALREADY_RESOLVING')
    hand = state.zones[seat]['hand']
    physical = next((c for c in hand if c.key == choice['hand_key']), None)
    if physical is None:
        raise RuntimeHalt('OPTION_NOT_IN_HAND')
    card = runtime.context.card(seat, physical.card_number)
    spec = OPTION_SPECS.get(card.number)
    if card.kind != 'Option' or spec is None:
        raise RuntimeHalt('OPTION_USE_UNIMPLEMENTED: ' + card.number)
    evidence = _source_evidence(root,card.to_dict()['official_source'],
        '#'+card.number+' printed Option type, use cost, color conditions and first Main').manifest()
    if not option_colors_met(runtime, seat, card):
        raise RuntimeHalt('OPTION_COLOR_REQUIREMENTS_NOT_MET: ' + card.number)
    assert_basic_board_scope(runtime,'use_option',root)
    runtime.registry.lookup(card.number,spec[0],'main_text')
    cost = card.to_dict()['play_cost']
    if type(cost) is not int or cost < 0 or cost > state.memory + 10:
        raise RuntimeHalt('OPTION_COST_NOT_PAYABLE')
    before = state.memory
    state.memory -= cost; hand.remove(physical); state.entity_sequence += 1
    state.resolving_option = {'seat':seat,'stack':Stack([physical],instance_id='entity-'+str(state.entity_sequence))}
    queue_effects(runtime,[{'seat':seat,'source':physical.key,'effect_id':spec[0],'field':'main_text',
                           'trigger':{'kind':'Option Use','card':physical.key}}])
    return {'used_card':physical.key,'cost':cost,'memory_after':state.memory,
        'rules_source':choice['rules'],'card_source':evidence,'scope_context_id':locked.matchup_id,
        'triggered_effects':[spec[0]],'steps':[{'operation':'DECLARE_USE','card':physical.key},
            {'operation':'PAY_USE_COST','cost':cost,'memory_before':before,'memory_after':state.memory},
            {'operation':'ACTIVATE_FIRST_MAIN','effect_id':spec[0],'source_area':None}], 'full_match_credit':0}


def choose_use_option(runtime, seat, hand_key, root):
    return runtime._control_command('USE_OPTION',seat,
        {'hand_key':hand_key,'rules':{**_rules(root),'locator':_RULES_LOCATOR}},
        lambda trial,controller,choice:_use(trial,controller,choice,root))


def _window(runtime, seat, source_key, effect_id=None):
    runtime.context.deck(seat)
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('OPTION_ACTIVATION_WINDOW_REQUIRED')
    current = runtime.state.resolving_option
    initial = current is not None and current['seat']==seat and current['stack'].cards[-1].key==source_key
    try:
        source = runtime._source(seat,source_key,'main_text')
    except RuntimeHalt as exc:
        raise RuntimeHalt('OPTION_ACTIVATION_WINDOW_REQUIRED') from exc
    if source.card_number not in OPTION_SPECS:
        raise RuntimeHalt('OPTION_SOURCE_UNSUPPORTED')
    expected_id = OPTION_SPECS[source.card_number][0] if initial else DELAY_SPECS[source.card_number][0]
    if effect_id is not None and effect_id != expected_id:
        raise RuntimeHalt('OPTION_ACTIVATION_WINDOW_REQUIRED')
    expected = (expected_id,seat,source_key,'main_text')
    activated = getattr(runtime,'_activated_effect',None)
    inside = activated is not None and activated[:4]==expected and activated[4] is not None
    if not inside:
        from effect_scheduler import pending_options
        options = pending_options(runtime,seat)
        matching = [p for p in options if tuple(p[k] for k in ('effect_id','seat','source','field'))==expected]
        if not matching or (initial and OPTION_SPECS[source.card_number][2] and len(options)!=1):
            raise RuntimeHalt('OPTION_ACTIVATION_WINDOW_REQUIRED')
    return source,expected_id,initial


def validate_option_activation(runtime, seat, allowed_effect_ids, *, source_zone):
    """Proof for trusted processing after Delay's source has paid into trash."""
    activated = getattr(runtime,'_activated_effect',None)
    if (runtime.halted or runtime.state.terminal or not runtime.allow_experimental
            or not isinstance(activated,tuple) or len(activated)!=5
            or activated[0] not in allowed_effect_ids or activated[1]!=seat
            or activated[3]!='main_text' or activated[4] is None):
        raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    source_key = activated[2]
    if source_zone=='resolving':
        current=runtime.state.resolving_option
        pool=current['stack'].cards if current is not None and current['seat']==seat else []
    elif source_zone=='trash':
        pool=runtime.state.zones[seat]['trash']
    elif source_zone=='battle':
        pool=[s.cards[-1] for s in runtime.state.battle[seat].values()]
    else:
        raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    source=next((c for c in pool if c.key==source_key),None)
    if source is None or source.card_number not in OPTION_SPECS:
        raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    ids=(OPTION_SPECS[source.card_number][0],DELAY_SPECS[source.card_number][0])
    if activated[0] not in ids:
        raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    definition=runtime.context.card(seat,source.card_number)
    binding=runtime.registry.lookup(source.card_number,activated[0],'main_text')
    if (binding.definition_sha256!=definition.definition_sha256 or binding.text_sha256!=
            hashlib.sha256(definition.effect_text('main_text').encode()).hexdigest()):
        raise RuntimeHalt('OPTION_ACTIVE_BINDING_REQUIRED')
    return source


def option_evolution_choices(runtime, seat, effect_id):
    """Current public board/own-hand routes for this already selected effect."""
    from context_evolution import printed_evolution_options,UnsupportedEvolutionCondition
    spec=OPTION_EVOLUTION_EFFECTS.get(effect_id)
    if spec is None:
        raise RuntimeHalt('OPTION_EVOLUTION_EFFECT_UNSUPPORTED')
    choices=[None]
    for source_key,stack in sorted(runtime.state.battle[seat].items()):
        base=runtime.context.card(seat,stack.cards[-1].card_number)
        if (base.kind!='Digimon' or spec['base_colors'] and not
                set(spec['base_colors']).intersection(base.to_dict()['colors'])):
            continue
        for target in runtime.state.zones[seat]['hand']:
            definition=runtime.context.card(seat,target.card_number)
            if definition.kind!='Digimon' or not set(spec['target_colors']).intersection(definition.to_dict()['colors']):
                continue
            try:routes=printed_evolution_options(runtime.context,seat,base.number,target.card_number)
            except UnsupportedEvolutionCondition as exc:
                raise RuntimeHalt('OPTION_EVOLUTION_ROUTE_UNSUPPORTED: '+target.key+' '+str(exc)) from exc
            for index,route in enumerate(routes):
                if max(0,route.cost-spec['reduction'])<=runtime.state.memory+10:
                    choices.append({'source_key':source_key,'hand_key':target.key,'route_index':index})
    return choices


def _battle_digimon(runtime,seat):
    return [s for s in runtime.state.battle[seat].values()
            if runtime.context.card(seat,s.cards[-1].card_number).kind=='Digimon']


def _scramble_delay_choices(runtime,seat):
    opponent='B' if seat=='A' else 'A'
    if not _battle_digimon(runtime,opponent):
        return [None]
    trash=runtime.state.zones[seat]['trash']
    blue=[c for c in trash if runtime.context.card(seat,c.card_number).kind=='Digimon'
          and 'Blue' in runtime.context.card(seat,c.card_number).to_dict()['colors']]
    choices=[{'activate':False}]
    for returned in sorted([c.key for c in blue]) or [None]:
        play=[None]
        if not _battle_digimon(runtime,seat):
            play += sorted(c.key for c in blue if c.key!=returned
                and type(runtime.context.card(seat,c.card_number).to_dict()['dp']) is int
                and runtime.context.card(seat,c.card_number).to_dict()['dp']<=2000)
        choices += [{'activate':True,'return_key':returned,'play_key':key} for key in play]
    return choices


def option_choices(runtime, seat, source_key, effect_id=None):
    source,effect,initial=_window(runtime,seat,source_key,effect_id)
    if not initial:
        _delay_turn(runtime,seat,source_key)
        if effect==BLUE_SCRAMBLE_DELAY:
            return {'kind':'delay','choices':_scramble_delay_choices(runtime,seat)}
        if source.card_number=='LM-034':
            return {'kind':'delay','choices':[{'activate':False},{'activate':True}]}
        return {'kind':'delay','choices':[{'activate':False}]+[
            {'activate':True,'evolution':choice} for choice in option_evolution_choices(runtime,seat,effect)]}
    if source.card_number=='LM-028':
        return {'kind':'evolution','choices':option_evolution_choices(runtime,seat,effect)}
    count=OPTION_SPECS[source.card_number][2]
    revealed=list(reversed(runtime.state.zones[seat]['deck'][-count:]))
    selections=[]
    for physical in revealed:
        card=runtime.context.card(seat,physical.card_number)
        if (set(_SEARCH_COLORS[source.card_number]).intersection(card.to_dict()['colors'])
                and (source.card_number!='LM-034' or card.kind=='Digimon')):
            selections.append([physical.key])
    return {'revealed':[c.key for c in revealed],'selections':sorted(selections) or [[]],
            'bottom_order_convention':'first element is bottommost'}


def _place_option(runtime,seat,source_key):
    current=runtime.state.resolving_option
    if current is None or current['seat']!=seat or current['stack'].cards[-1].key!=source_key:
        raise RuntimeHalt('OPTION_RESOLVING_SOURCE_REQUIRED')
    stack=current['stack'];stack.played_turn=runtime.state.turn
    runtime.state.battle[seat][source_key]=stack;runtime.state.resolving_option=None


def resolve_option(runtime,seat,source_key,choice):
    options=option_choices(runtime,seat,source_key)
    if options.get('kind')=='evolution':
        if choice not in options['choices']:
            raise RuntimeHalt('OPTION_EVOLUTION_CHOICE_INVALID')
        evolution=None
        if choice is not None:
            from battle_evolution import trusted_evolve_from_effect
            evolution=trusted_evolve_from_effect(runtime,seat,choice['source_key'],choice['hand_key'],
                                                 choice['route_index'],Path(__file__).resolve().parents[1])
        _place_option(runtime,seat,source_key)
        return {'evolution':evolution,'placed_option':source_key,'steps':[
            {'operation':'OPTIONAL_EVOLUTION','choice':choice,'result':evolution},
            {'operation':'PLACE_OPTION_IN_BATTLE','card':source_key}], 'full_match_credit':0}
    if not isinstance(choice,dict) or set(choice)!={'selected','bottom_order'}:
        raise RuntimeHalt('OPTION_CHOICE_INVALID')
    selected,bottom=choice['selected'],choice['bottom_order']
    if (not isinstance(selected,list) or not isinstance(bottom,list)
            or any(not isinstance(k,str) for k in selected+bottom)
            or len(set(selected))!=len(selected) or len(set(bottom))!=len(bottom)
            or selected not in options['selections']
            or set(bottom)!=set(options['revealed'])-set(selected)):
        raise RuntimeHalt('OPTION_SELECTION_OR_ORDER_INVALID')
    deck=runtime.state.zones[seat]['deck'];count=len(options['revealed'])
    cards={c.key:c for c in deck[-count:]} if count else {}
    if count:del deck[-count:]
    runtime.state.zones[seat]['hand'].extend(cards[k] for k in selected)
    deck[:0]=[cards[k] for k in bottom];_place_option(runtime,seat,source_key)
    return {'revealed':options['revealed'],'selected':selected,'bottom_order':bottom,
        'bottom_order_convention':options['bottom_order_convention'],'placed_option':source_key,
        'steps':[{'operation':'REVEAL','cards':options['revealed']},
                 {'operation':'ADD_TO_HAND','cards':selected},
                 {'operation':'RETURN_TO_DECK_BOTTOM','cards':bottom,'bottom_order_convention':options['bottom_order_convention']},
                 {'operation':'PLACE_OPTION_IN_BATTLE','card':source_key}], 'status':'EXPERIMENTAL','full_match_credit':0}


def _delay_turn(runtime,seat,source_key):
    stack=runtime.state.battle[seat].get(source_key)
    if (stack is None or type(stack.played_turn) is not int or stack.played_turn>=runtime.state.turn):
        raise RuntimeHalt('DELAY_PLACEMENT_TURN_REQUIRED')
    return stack


def choose_option_delay(runtime,seat,source_key,root):
    def choose(trial,controller,choice):
        from selected_contexts import require_selected_context
        require_selected_context(trial.context,root)
        state=trial.state
        if controller!=state.active or state.phase!='MAIN' or state.memory<0:
            raise RuntimeHalt('MAIN_OPTION_WINDOW_NOT_OPEN')
        source=trial._source(controller,choice['source_key'],'main_text')
        if source.card_number not in DELAY_SPECS or source.card_number=='LM-028':
            raise RuntimeHalt('MAIN_DELAY_SOURCE_UNSUPPORTED')
        _delay_turn(trial,controller,source.key)
        effect=DELAY_SPECS[source.card_number][0]
        queue_effects(trial,[{'seat':controller,'source':source.key,'effect_id':effect,'field':'main_text',
                             'trigger':{'kind':'Main Delay','card':source.key}}])
        return {'source':source.key,'effect_id':effect,'rules_source':choice['rules'],'full_match_credit':0}
    return runtime._control_command('OPTION_DELAY',seat,
        {'source_key':source_key,'rules':{**_rules(root),'locator':_RULES_LOCATOR}},choose)


def collect_option_start_turn(runtime,seat):
    """Start timing triggers even if its processing condition is false now."""
    records=[]
    for key,stack in runtime.state.battle[seat].items():
        if stack.cards[-1].card_number!='LM-028':continue
        runtime.registry.lookup('LM-028',BLUE_SCRAMBLE_DELAY,'main_text')
        records.append({'seat':seat,'source':key,'effect_id':BLUE_SCRAMBLE_DELAY,'field':'main_text',
                        'trigger':{'kind':'Start of Your Turn','card':key}})
    return records


def resolve_option_delay(runtime,seat,source_key,choice):
    source,effect,initial=_window(runtime,seat,source_key)
    if initial:raise RuntimeHalt('DELAY_SOURCE_WINDOW_REQUIRED')
    options=option_choices(runtime,seat,source_key,effect)
    if (choice not in options['choices'] or choice is not None
            and (not isinstance(choice,dict) or type(choice.get('activate')) is not bool)):
        raise RuntimeHalt('OPTION_DELAY_CHOICE_INVALID')
    if choice is None:
        return {'processing':'CONDITION_NOT_MET','activated':False,'full_match_credit':0}
    if not choice['activate']:
        return {'processing':'DELAY_DECLINED','activated':False,'full_match_credit':0}
    stack=_delay_turn(runtime,seat,source_key)
    if len(stack.cards)!=1:raise RuntimeHalt('DELAY_SOURCE_STACK_INVALID')
    del runtime.state.battle[seat][source_key]
    runtime.state.zones[seat]['trash'].append(source)
    steps=[{'operation':'TRASH_DELAY_SOURCE','card':source_key}]
    result={'processing':'DELAY_ACTIVATED','activated':True,'trashed_option':source_key,'steps':steps,'full_match_credit':0}
    if effect==BLUE_SCRAMBLE_DELAY:
        returned=choice['return_key'];play_key=choice['play_key'];trash=runtime.state.zones[seat]['trash']
        if returned is not None:
            card=next(c for c in trash if c.key==returned);trash.remove(card);runtime.state.zones[seat]['deck'].append(card)
        steps.append({'operation':'RETURN_TRASH_DIGIMON_TO_DECK_TOP','card':returned})
        play=None
        if play_key is not None:
            from main_actions import play_blue_scramble_from_trash
            play=play_blue_scramble_from_trash(runtime,seat,play_key,Path(__file__).resolve().parents[1])
        steps.append({'operation':'OPTIONAL_PLAY_FROM_TRASH','card':play_key,'result':play})
        result.update({'returned_to_top':returned,'play':play})
    elif source.card_number=='LM-034':
        before=runtime.state.memory;runtime.state.memory=min(10,before+2)
        steps.append({'operation':'GAIN_MEMORY','requested':2,'memory_before':before,'memory_after':runtime.state.memory})
        result.update({'memory_after':runtime.state.memory})
    else:
        evolution=None
        if choice['evolution'] is not None:
            from battle_evolution import trusted_evolve_from_effect
            c=choice['evolution'];evolution=trusted_evolve_from_effect(runtime,seat,c['source_key'],c['hand_key'],
                c['route_index'],Path(__file__).resolve().parents[1])
        steps.append({'operation':'OPTIONAL_EVOLUTION','choice':choice['evolution'],'result':evolution})
        result['evolution']=evolution
    return result


def option_bindings(context,root,rules_evidence):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number not in OPTION_SPECS:continue
        effect,line,_=OPTION_SPECS[card.number];delay,delay_line,continuation=DELAY_SPECS[card.number]
        lines=card.effect_text('main_text').splitlines()
        require(all(x in lines for x in (line,delay_line,continuation)), 'Exact Option text changed: '+card.number)
        if card.number in _TRAINING_NAMES:
            require("While you don't have ["+_TRAINING_NAMES[card.number]+"] in the battle area, you can ignore this card's color requirements." in lines,
                    'Exact training color exception changed: '+card.number)
        if card.number=='LM-034':require("Red also meets this card's color requirements." in lines,'Wisteria color exception changed')
        evidence=_source_evidence(root,card.to_dict()['official_source'],
            '#'+card.number+' first Main, color exception and separate Delay; CR9-1-4,16-17')
        for effect,handler in ((effect,resolve_option),(delay,resolve_option_delay)):
            bindings.append(MechanicBinding(card.number,effect,'main_text',card.definition_sha256,
                hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
                (evidence,replace(rules_evidence,locator=_RULES_LOCATOR)),handler))
    return tuple(bindings)
