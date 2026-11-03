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
from context_runtime import PhysicalCard, PhysicalState, RuntimeHalt, Stack
from option_actions import OPTION_SPECS
from selected_contexts import require_selected_context


_ACTIONS = frozenset(('play_plain', 'play_search', 'breeding_evolve', 'battle_evolve','attack_plain', 'use_option'))
_PLAIN_TOPS = frozenset(('EX1-013', 'ST7-05', 'BT9-011'))
_SEARCH_TOPS = frozenset(('BT11-023','P-138','EX13-017','EX2-008','EX8-009'))
_OTHER_TIMINGS_TOPS = frozenset(('BT12-016','BT12-029','BT17-013','BT17-016','BT19-007',
    'BT19-009','BT19-080','BT22-022','EX13-019','EX13-069','EX8-012','EX8-015'))
_RESOLVED_PLAY_TOPS = frozenset(('BT11-112','BT22-085','BT22-023'))
_INERT_OPTION_TOPS = frozenset(OPTION_SPECS)
# Keep explicit schemas: a newly added effect-bearing dataclass field must not
# silently acquire support merely because the dataclass accepted it.
_STATE_FIELDS = frozenset(('zones', 'battle', 'breeding', 'active', 'memory', 'turn',
                           'terminal', 'once_used', 'pending', 'effect_sequence',
                           'entity_sequence', 'phase', 'preparation','attack','winner','terminal_reason',
                           'resolving_option'))
_STACK_FIELDS = frozenset(('cards', 'suspended', 'statuses', 'instance_id', 'played_turn','ready_since_turn'))
_CARD_FIELDS = frozenset(('owner', 'card_number', 'index'))


def _assert_selected_context(runtime, root):
    require_selected_context(runtime.context, root)


def assert_basic_board_scope(runtime, action, root, *, event=None, within_effect=False):
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
    if within_effect and not getattr(runtime,'_activated_effect',None):
        raise RuntimeHalt('BASIC_BOARD_ACTIVE_EFFECT_REQUIRED')
    if state.pending and not within_effect:
        raise RuntimeHalt('BASIC_BOARD_PENDING_EFFECTS_UNSUPPORTED')
    if state.resolving_option is not None and not within_effect:
        raise RuntimeHalt('BASIC_BOARD_OPTION_PROCESSING_PENDING')

    from selected_mechanics import _source_evidence

    checked = set()
    for owner in ('A', 'B'):
        if type(state.battle[owner]) is not dict:
            raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: ' + owner)
        for anchor, stack in state.battle[owner].items():
            if type(stack) is not Stack or set(vars(stack)) != _STACK_FIELDS:
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: stack ' + owner)
            if type(stack.cards) is not list or not stack.cards or (len(stack.cards)!=1 and action=='attack_plain'):
                raise RuntimeHalt('BASIC_BOARD_STACK_UNSUPPORTED: ' + owner)
            if type(stack.statuses) is not dict:
                raise RuntimeHalt('BASIC_BOARD_STATUS_UNSUPPORTED: ' + owner)
            if stack.statuses:
                if set(stack.statuses) != {'effect_grants'} or action == 'attack_plain':
                    raise RuntimeHalt('BASIC_BOARD_STATUS_UNSUPPORTED: ' + owner)
                from effect_grants import validate_grants
                validate_grants(runtime, owner, anchor)
            if (type(stack.suspended) is not bool or type(stack.instance_id) is not str
                    or (stack.played_turn is not None
                        and (type(stack.played_turn) is not int or stack.played_turn < 0))
                    or (stack.ready_since_turn is not None
                        and (type(stack.ready_since_turn) is not int or stack.ready_since_turn < 0))):
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: stack ' + owner)
            physical = stack.cards[-1]
            if (type(physical) is not PhysicalCard or set(vars(physical)) != _CARD_FIELDS
                    or physical.owner != owner or type(physical.card_number) is not str
                    or type(physical.index) is not int or physical.index < 1
                    or type(anchor) is not str or anchor != physical.key):
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: card ' + owner)
            if action!='attack_plain':
                from basic_event_dependencies import require_inert_for_event
                for index,source in enumerate(stack.cards):
                    if (type(source) is not PhysicalCard or set(vars(source))!=_CARD_FIELDS
                            or source.owner!=owner or type(source.index) is not int or source.index<1):
                        raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: source '+owner)
                    definition=runtime.context.card(owner,source.card_number)
                    field='main_text' if index==len(stack.cards)-1 else 'inherited_text'
                    require_inert_for_event(runtime,owner,source,field,action,event)
                    if source.card_number not in checked:
                        try:
                            _source_evidence(root,definition.to_dict()['official_source'],
                                '#'+source.card_number+' '+field+' at actual '+action+' event').manifest()
                        except (OSError,ValueError,KeyError,TypeError) as exc:
                            raise RuntimeHalt('BASIC_BOARD_OFFICIAL_SOURCE_UNAVAILABLE: '+source.card_number) from exc
                        checked.add(source.card_number)
                continue
            inert_option=physical.card_number in _INERT_OPTION_TOPS
            resolved_play=physical.card_number in _RESOLVED_PLAY_TOPS and action!='attack_plain'
            other_timing=((physical.card_number in _OTHER_TIMINGS_TOPS or resolved_play) and action!='attack_plain')
            if physical.card_number not in _PLAIN_TOPS | _SEARCH_TOPS and not other_timing and not inert_option:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number)
            try:
                definition = runtime.context.card(owner, physical.card_number)
            except (ValueError, StopIteration) as exc:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number) from exc
            expected_main=''
            if physical.card_number in _SEARCH_TOPS:
                from search_effects import SEARCH_SPECS
                expected_main=SEARCH_SPECS[physical.card_number][1]
            if other_timing:
                from printed_triggers import trigger_lines
                # Original context/hash pin above fixes the complete wording.
                # These audited cards have no play observer, cost replacement or
                # breeding exception. Their own later triggers do not activate
                # here. BT17-016's self-immunity doesn't affect these actions,
                # which apply no opponent effect to that Digimon.
                if trigger_lines(definition.effect_text('main_text'),'On Play') and not resolved_play:
                    raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: unexpected On Play')
                expected_main=definition.effect_text('main_text')
            if inert_option:
                if physical.card_number not in OPTION_SPECS or stack.suspended:
                    raise RuntimeHalt('BASIC_BOARD_OPTION_UNSUPPORTED')
                expected_main=definition.effect_text('main_text')
            allowed_kinds=('Option',) if inert_option else (('Digimon','Tamer') if other_timing else ('Digimon',))
            if definition.kind not in allowed_kinds or definition.effect_text('main_text') != expected_main:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number)
            if physical.card_number not in checked:
                try:
                    _source_evidence(root, definition.to_dict()['official_source'],
                                     '#' + physical.card_number + ' main effects at the selected basic-action timing; '
                                     'unrelated self triggers do not activate, and no active text changes this action. '
                                     'Inherited effect is not active on a singleton top (15-3-1).').manifest()
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise RuntimeHalt('BASIC_BOARD_OFFICIAL_SOURCE_UNAVAILABLE: '
                                      + physical.card_number) from exc
                checked.add(physical.card_number)
