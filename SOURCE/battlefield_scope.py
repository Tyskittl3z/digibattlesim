"""Conservative battlefield capability for selected experimental basic actions.

The official EX1-013, ST7-05 and BT9-011 definitions have no main effect.
Their inherited effects do not apply while those cards are singleton tops.
BT9-011's printed special digivolution route does not create a battlefield
effect. Five exact search tops are also supported between their self triggers.
Every other existing top, inherited source, status or unrecognized
metadata remains unsupported, even when an effect might be inactive now.

This guard grants no rules certification or full-match credit. Callers own
physical-state validation, legal action windows, and the new action's effects.
It inspects neither hidden zones nor breeding contents and never mutates state,
events, RNG or halt flags, including on failure.
"""
from pathlib import Path

from context_runtime import PhysicalCard, PhysicalState, RuntimeHalt, Stack
from match_context import MatchContext


_SELECTED_CONTEXT_ID = '53f4e043b49fca0bf6e691754098e73774995cfee182e7c8245cf446e2d70733'
_CONTEXT_FILE = 'ARTIFACTS/ex13-engine-2026-10-30/context.json'
_ACTIONS = frozenset(('play_plain', 'play_search', 'breeding_evolve', 'attack_plain'))
_PLAIN_TOPS = frozenset(('EX1-013', 'ST7-05', 'BT9-011'))
_SEARCH_TOPS = frozenset(('BT11-023','P-138','EX13-017','EX2-008','EX8-009'))
# Keep explicit schemas: a newly added effect-bearing dataclass field must not
# silently acquire support merely because the dataclass accepted it.
_STATE_FIELDS = frozenset(('zones', 'battle', 'breeding', 'active', 'memory', 'turn',
                           'terminal', 'once_used', 'pending', 'effect_sequence',
                           'entity_sequence', 'phase', 'preparation','attack','winner','terminal_reason'))
_STACK_FIELDS = frozenset(('cards', 'suspended', 'statuses', 'instance_id', 'played_turn','ready_since_turn'))
_CARD_FIELDS = frozenset(('owner', 'card_number', 'index'))


def _assert_selected_context(runtime, root):
    # Pin the original capability as well as reading the selected lock: changing
    # both a runtime and its on-disk context cannot authorize new card effects.
    from matchup_readiness import load_context_file

    try:
        context = runtime.context
        locked = load_context_file(Path(root) / _CONTEXT_FILE)
        selected = ('123129', '124303')
        valid = (type(context) is MatchContext
                 and (context.deck_a.source_id, context.deck_b.source_id) == selected
                 and (locked.deck_a.source_id, locked.deck_b.source_id) == selected
                 and context.matchup_id == locked.matchup_id == _SELECTED_CONTEXT_ID)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
        raise RuntimeHalt('BASIC_BOARD_SELECTED_CONTEXT_REQUIRED') from exc
    if not valid:
        raise RuntimeHalt('BASIC_BOARD_SELECTED_CONTEXT_REQUIRED')


def assert_basic_board_scope(runtime, action, root):
    """Require only original, bare singleton plain Digimon on both battle areas.

    ``action`` must explicitly name one supported basic action. The five search
    tops require their complete pinned main text to equal a known self-search
    effect; inherited reactions remain outside scope when exposed under stacks.
    ``root`` supplies the locked context and hash-bound official source bytes.
    """
    if type(action) is not str or action not in _ACTIONS:
        raise RuntimeHalt('BASIC_BOARD_ACTION_UNSUPPORTED')
    if runtime.allow_experimental is not True:
        raise RuntimeHalt('BASIC_BOARD_EXPERIMENTAL_OPT_IN_REQUIRED')
    _assert_selected_context(runtime, root)
    state = runtime.state
    if type(state) is not PhysicalState or set(vars(state)) != _STATE_FIELDS:
        raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: state')
    if type(state.battle) is not dict or set(state.battle) != {'A', 'B'}:
        raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: battle')
    if state.pending:
        raise RuntimeHalt('BASIC_BOARD_PENDING_EFFECTS_UNSUPPORTED')

    from selected_mechanics import _source_evidence

    checked = set()
    for owner in ('A', 'B'):
        if type(state.battle[owner]) is not dict:
            raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: ' + owner)
        for anchor, stack in state.battle[owner].items():
            if type(stack) is not Stack or set(vars(stack)) != _STACK_FIELDS:
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: stack ' + owner)
            if type(stack.cards) is not list or len(stack.cards) != 1:
                raise RuntimeHalt('BASIC_BOARD_STACK_UNSUPPORTED: ' + owner)
            if type(stack.statuses) is not dict or stack.statuses:
                raise RuntimeHalt('BASIC_BOARD_STATUS_UNSUPPORTED: ' + owner)
            if (type(stack.suspended) is not bool or type(stack.instance_id) is not str
                    or (stack.played_turn is not None
                        and (type(stack.played_turn) is not int or stack.played_turn < 0))
                    or (stack.ready_since_turn is not None
                        and (type(stack.ready_since_turn) is not int or stack.ready_since_turn < 0))):
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: stack ' + owner)
            physical = stack.cards[0]
            if (type(physical) is not PhysicalCard or set(vars(physical)) != _CARD_FIELDS
                    or physical.owner != owner or type(physical.card_number) is not str
                    or type(physical.index) is not int or physical.index < 1
                    or type(anchor) is not str or anchor != physical.key):
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: card ' + owner)
            if physical.card_number not in _PLAIN_TOPS | _SEARCH_TOPS:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number)
            try:
                definition = runtime.context.card(owner, physical.card_number)
            except (ValueError, StopIteration) as exc:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number) from exc
            expected_main=''
            if physical.card_number in _SEARCH_TOPS:
                from search_effects import SEARCH_SPECS
                expected_main=SEARCH_SPECS[physical.card_number][1]
            if definition.kind != 'Digimon' or definition.effect_text('main_text') != expected_main:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number)
            if physical.card_number not in checked:
                try:
                    _source_evidence(root, definition.to_dict()['official_source'],
                                     '#' + physical.card_number + ' singleton main effects: blank or exact self search '
                                     'only on play/digivolving/moving; none triggers on other basic actions. '
                                     'Inherited effect is not active on a singleton top (15-3-1).').manifest()
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise RuntimeHalt('BASIC_BOARD_OFFICIAL_SOURCE_UNAVAILABLE: '
                                      + physical.card_number) from exc
                checked.add(physical.card_number)
