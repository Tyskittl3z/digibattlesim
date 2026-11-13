"""Encountered On Play effects, with choices derived from the current board."""
import hashlib

from context_runtime import MechanicBinding, RuntimeHalt
from match_context import require


ON_PLAY_SPECS = {
    'BT11-112': ('BT11-112.on_play_grant',
        "[On Play] Until the end of your opponent's turn, 1 of your Digimon with [Veemon] or [Veedramon] in its name gains ＜Blocker＞ and ＜Evade＞.",
        {'names': ('Veemon', 'Veedramon'), 'grant': {'keywords': ['Blocker', 'Evade']}}),
    'BT22-085': ('BT22-085.on_play_grant',
        "[On Play] 1 of your Digimon with [Veedramon] in its name gets +3000 DP until your opponent's turn ends.",
        {'names': ('Veedramon',), 'grant': {'dp_bonus': 3000}}),
}


def on_play_choices(runtime, seat, source_key):
    source = runtime._source(seat, source_key, 'main_text')
    spec = ON_PLAY_SPECS.get(source.card_number)
    if spec is None:
        raise RuntimeHalt('ON_PLAY_SOURCE_UNSUPPORTED')
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('ON_PLAY_WINDOW_REQUIRED')
    if runtime.state.phase != 'SCENARIO':
        activated = getattr(runtime, '_activated_effect', None)
        expected = (spec[0], seat, source_key, 'main_text')
        in_handler = activated is not None and activated[:4] == expected and activated[4] is not None
        if not in_handler:
            from effect_scheduler import pending_options
            if not any((p['effect_id'], p['seat'], p['source'], p['field']) == expected
                       for p in pending_options(runtime, seat)):
                raise RuntimeHalt('ON_PLAY_WINDOW_REQUIRED')
    targets = []
    for key, stack in runtime.state.battle[seat].items():
        card = runtime.context.card(seat, stack.cards[-1].card_number)
        if card.kind == 'Digimon' and any(name in card.name for name in spec[2]['names']):
            targets.append(key)
    # CR1-3-2: impossible processing is omitted. A mandatory available target
    # cannot be declined; only an actually empty target set produces None.
    return sorted(targets) if targets else [None]


def resolve_on_play(runtime, seat, source_key, choice):
    if choice not in on_play_choices(runtime, seat, source_key):
        raise RuntimeHalt('ON_PLAY_TARGET_INVALID')
    source = runtime._source(seat, source_key, 'main_text')
    spec = ON_PLAY_SPECS[source.card_number]
    if choice is None:
        return {'target': None, 'processing': 'NO_ELIGIBLE_TARGET', 'full_match_credit': 0}
    from effect_grants import grant_effect
    grant = grant_effect(runtime, seat, choice, spec[2]['grant'], source_key,
                         'end_of_opponent_turn')
    return {'target': choice, 'processing': 'GRANT_APPLIED', 'grant': grant, 'full_match_credit': 0}


def on_play_bindings(context, root, rules_evidence):
    from selected_mechanics import _source_evidence
    bindings = []
    for card in context.cards:
        if card.number not in ON_PLAY_SPECS:
            continue
        effect, line, _ = ON_PLAY_SPECS[card.number]
        require(line in card.effect_text('main_text').splitlines(), 'On Play wording changed: ' + card.number)
        evidence = _source_evidence(root, card.to_dict()['official_source'],
            '#' + card.number + ' On Play; CR1-3-2,7-1-3,15-10-2-1,15-11-1-3-1,15-16-2-1')
        bindings.append(MechanicBinding(card.number, effect, 'main_text', card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence, rules_evidence), resolve_on_play))
    return tuple(bindings)
