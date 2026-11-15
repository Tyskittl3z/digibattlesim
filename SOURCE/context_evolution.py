"""Printed routes for the selected imported cards, independent of seat globals.

These are printed candidate routes, not full action legality: live name/color
changes, prohibitions, memory payment, reductions and triggered effects still
require context-bound gameplay handlers and official review.
"""
from dataclasses import dataclass
import re


class UnsupportedEvolutionCondition(ValueError):
    pass


@dataclass(frozen=True)
class EvolutionRoute:
    cost: int
    basis: str
    printed_condition: str
    definition_sha256: str
    status: str = 'PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY'


COLORS = ('Red', 'Blue', 'Yellow', 'Green', 'Black', 'Purple', 'White')


def _normal(raw, base):
    match = re.fullmatch(r'((?:(?:Red|Blue|Yellow|Green|Black|Purple|White)\s*)+)\s+(\d+) from Lv\.(\d+)', raw)
    if not match:
        raise UnsupportedEvolutionCondition('Unsupported printed normal route: ' + raw)
    colors, cost, level = match.groups()
    accepted = set(re.findall('|'.join(COLORS), colors))
    return int(cost) if base.get('level') == int(level) and accepted.intersection(base['colors']) else None


def _special(raw, base):
    # Both legacy "1 from [Name]" and current "[Name]: Cost 1" occur in
    # these exact imported decks. Unknown syntax fails before any fallback.
    legacy = re.fullmatch(r'\[Digivolve\] (\d+) from (\[[^\]]+\](?:/\[[^\]]+\])*)', raw)
    if legacy:
        cost, predicate = legacy.groups()
    else:
        modern = re.fullmatch(r'\[Digivolve\] (.+): Cost (\d+)', raw)
        if not modern:
            raise UnsupportedEvolutionCondition('Unsupported printed special route: ' + raw)
        predicate, cost = modern.groups()
    names = re.fullmatch(r'\[[^\]]+\](?:/\[[^\]]+\])*', predicate)
    if names:
        matched = base['name'] in re.findall(r'\[([^\]]+)\]', predicate)
    else:
        qualified = re.fullmatch(r'Lv\.(\d+) w/\[([^\]]+)\] (trait|in name)', predicate)
        if not qualified:
            raise UnsupportedEvolutionCondition('Unsupported printed predicate: ' + predicate)
        level, value, kind = qualified.groups()
        matched = base.get('level') == int(level) and (
            value in base.get('traits', []) if kind == 'trait' else value in base['name'])
    return int(cost) if matched else None


def printed_evolution_options(context, seat, base_number, target_number):
    base = context.card(seat, base_number).to_dict()
    target_card = context.card(seat, target_number)
    target = target_card.to_dict()
    if base['type'] not in ('Digimon', 'Digi-Egg') or target['type'] != 'Digimon':
        return ()
    routes = []
    if 'normal_digivolution' not in target or 'special_conditions' not in target:
        raise UnsupportedEvolutionCondition('Explicit printed route metadata required')
    for raw in target['normal_digivolution'].values():
        cost = _normal(raw, base)
        if cost is not None:
            routes.append(EvolutionRoute(cost, 'PRINTED_NORMAL', raw, target_card.definition_sha256))
    raw_special = target['special_conditions'].get('[Special Digivolution Condition]', '')
    for raw in raw_special.splitlines():
        cost = _special(raw, base)
        if cost is not None:
            routes.append(EvolutionRoute(cost, 'PRINTED_SPECIAL', raw, target_card.definition_sha256))
    return tuple(sorted(routes, key=lambda r: (r.cost, r.basis, r.printed_condition)))
