"""Exact selected On Play searches, EXPERIMENTAL; zero full-match credit.

Deck arrays run bottom to top. The first bottom_order key is bottommost.
No trigger detection, strategic selection, or automatic ordering is performed.
Evidence locators identify each exact base-card popup, not alternate printings.
Q2066/2067, Q4244/4245 and Q3289/3290 require maximal legal selection.
Full context definitions, full main_text and official source bytes stay bound.
"""
import hashlib
from itertools import product
from context_runtime import MechanicBinding, RuntimeHalt
from match_context import require

SEARCH_SPECS = {
 'BT11-023': ('BT11-023.on_play_search', '[On Play] Reveal the top 3 cards of your deck. Add 1 Digimon card with [Veedramon] in its name and 1 blue Tamer card among them to your hand. Place the rest at the bottom of your deck in any order.', 3),
 'P-138': ('P-138.on_play_search', '[On Play] [When Digivolving] Reveal the top 3 cards of your deck. Add 1 Digimon card with [Veedramon] in its name and 1 blue Tamer card among them to the hand. Return the rest to the bottom of the deck.', 3),
 'EX2-008': ('EX2-008.on_play_search', '[On Play] Reveal the top 4 cards of your deck. Add 1 card with [Growlmon] or [Gallantmon] in its name and 1 [Takato Matsuki] among them to your hand. Place the remaining cards at the bottom of your deck in any order.', 4),
}
_QA = {'BT11-023':'Q2066/Q2067','P-138':'Q4244/Q4245','EX2-008':'Q3289/Q3290'}


def _selection_alternatives(keys, slots):
    """Maximum injective matching, expressed as physical-copy subsets."""
    candidates = set()
    for assignment in product(*[[None]+[k for k in keys if k in slot] for slot in slots]):
        chosen = [k for k in assignment if k is not None]
        if len(set(chosen)) == len(chosen):
            candidates.add(tuple(k for k in keys if k in chosen))
    maximum = max(map(len,candidates))
    return [list(c) for c in sorted(candidates) if len(c)==maximum]


def search_choices(runtime, seat, source_key):
    """Expose only revealed physical keys and legal selections; never mutate."""
    source = runtime._source(seat,source_key,'main_text')
    if source.card_number not in SEARCH_SPECS:
        raise RuntimeHalt('SEARCH_SOURCE_UNSUPPORTED')
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('SEARCH_ACTIVATION_WINDOW_REQUIRED')
    if runtime.state.phase!='SCENARIO':
        # A choice query must not turn an old search card into a private deck
        # oracle. Live play currently supports a sole forced mandatory search,
        # or that exact effect already selected by the pending dispatcher.
        expected=(SEARCH_SPECS[source.card_number][0],seat,source_key,'main_text')
        activated=getattr(runtime,'_activated_effect',None)
        in_handler=activated is not None and activated[:4]==expected and activated[4] is not None
        if not in_handler:
            from effect_scheduler import pending_options
            options=pending_options(runtime,seat)
            if len(options)!=1 or (options[0]['effect_id'],options[0]['seat'],options[0]['source'],options[0]['field'])!=expected:
                raise RuntimeHalt('SEARCH_ACTIVATION_WINDOW_REQUIRED')
    count = SEARCH_SPECS[source.card_number][2]
    revealed = list(reversed(runtime.state.zones[seat]['deck'][-count:]))
    slots = (set(),set())
    for physical in revealed:
        card = runtime.context.card(seat,physical.card_number)
        if source.card_number == 'EX2-008':
            first = any(n in card.name for n in ('Growlmon','Gallantmon'))
            second = card.name == 'Takato Matsuki'
        else:
            first = card.kind == 'Digimon' and 'Veedramon' in card.name
            second = card.kind == 'Tamer' and 'Blue' in card.to_dict()['colors']
        if first: slots[0].add(physical.key)
        if second: slots[1].add(physical.key)
    keys = [c.key for c in revealed]
    return {'revealed':keys,'selections':_selection_alternatives(keys,slots),
            'bottom_order_convention':'first element is bottommost'}


def resolve_search(runtime,seat,source_key,choice):
    options = search_choices(runtime,seat,source_key)
    if not isinstance(choice,dict) or set(choice)!={'selected','bottom_order'}:
        raise RuntimeHalt('SEARCH_CHOICE_INVALID')
    selected,bottom = choice['selected'],choice['bottom_order']
    if (not isinstance(selected,list) or not isinstance(bottom,list)
            or any(not isinstance(k,str) for k in selected+bottom)
            or len(set(selected))!=len(selected)
            or len(set(bottom))!=len(bottom)
            or sorted(selected) not in [sorted(x) for x in options['selections']]
            or set(bottom)!=set(options['revealed'])-set(selected)):
        raise RuntimeHalt('SEARCH_SELECTION_OR_ORDER_INVALID')
    deck = runtime.state.zones[seat]['deck']
    count = len(options['revealed'])
    cards = {c.key:c for c in deck[-count:]} if count else {}
    if count: del deck[-count:]
    runtime.state.zones[seat]['hand'].extend(cards[k] for k in selected)
    deck[:0] = [cards[k] for k in bottom]
    return {'revealed':options['revealed'],'selected':selected,'bottom_order':bottom,
            'bottom_order_convention':options['bottom_order_convention'],'status':'EXPERIMENTAL'}


def search_bindings(context,root,rules_evidence):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number not in SEARCH_SPECS: continue
        effect,line,_ = SEARCH_SPECS[card.number]
        require(line in card.effect_text('main_text').splitlines(),'Exact search text changed: '+card.number)
        evidence = _source_evidence(root,card.to_dict()['official_source'],
                    '#'+card.number+' On Play search; '+_QA[card.number])
        bindings.append(MechanicBinding(card.number,effect,'main_text',card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence,rules_evidence),resolve_search))
    return tuple(bindings)
