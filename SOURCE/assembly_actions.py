"""Exact EX13-023 Assembly material selection from the controller's trash."""
from itertools import product

from context_runtime import RuntimeHalt

ASSEMBLY_TEXT = 'Assembly -5: Lv.5 × Lv.4 × Lv.3, all w/[Veemon]/[Veedramon] in name'
ASSEMBLY_COST = 7


def assembly_choices(runtime, seat, hand_key):
    hand = next((card for card in runtime.state.zones[seat]['hand'] if card.key == hand_key), None)
    if hand is None or hand.card_number != 'EX13-023':
        return []
    top = runtime.context.card(seat, hand.card_number)
    if top.to_dict()['special_conditions'].get('[Special Play Condition]') != ASSEMBLY_TEXT:
        raise RuntimeHalt('ASSEMBLY_PRINTED_CONDITION_CHANGED')
    levels = {}
    for level in (3, 4, 5):
        levels[level] = [card.key for card in runtime.state.zones[seat]['trash']
            if (runtime.context.card(seat, card.card_number).kind == 'Digimon'
                and runtime.context.card(seat, card.card_number).to_dict()['level'] == level
                and any(name in runtime.context.card(seat, card.card_number).name
                        for name in ('Veemon', 'Veedramon')))]
    return [list(keys) for keys in product(levels[3], levels[4], levels[5])]
