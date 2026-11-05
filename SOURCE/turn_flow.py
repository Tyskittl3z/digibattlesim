"""Explicit selected-pair pass and main-phase turn-end processing.

BT22-023 has an explicit pending end choice. Other end effects and untyped
status durations halt before committing memory, phase, OPT, or seat changes.
Validated grants expire only after all end processing actually finishes.
This module supplies no result handling, automatic pilot, or full-match credit.
"""
from context_runtime import RuntimeHalt
from aero_effects import END_EFFECT, END_LINE, end_turn_usage
from effect_scheduler import queue_effects
from effect_grants import GRANT_STATUS, expire_turn_grants, validate_grants
from match_preparation import _rules
from printed_triggers import trigger_lines


def _turn_rules(root):
    return {**_rules(root), 'locator': (
        'Comprehensive rules v4.3: 6-1-3; 6-1-4; 6-5-1-7-1; 6-6; '
        '15-8-3-6; 15-11-1; 15-13; 15-14-1-5-1; 15-16-12')}


def _actor(runtime, seat):
    if seat != runtime.state.active:
        raise RuntimeHalt('ACTIVE_PLAYER_REQUIRED')


def _end_dependencies(runtime, seat):
    """Fail closed on live end timings, including optional printed processing.

    Unsupported effects must not be represented as automatic declines.
    Only a stack's top main text and its lower cards' inherited text are active;
    the opponent's [End of Your Turn] text does not trigger on this turn.
    """
    sources = []
    for owner in ('A', 'B'):
        timing = 'End of Your Turn' if owner == seat else "End of Opponent's Turn"
        for target_key, stack in runtime.state.battle[owner].items():
            if type(stack.statuses) is not dict or stack.statuses:
                # Existing booleans carry no grant/source or expiry metadata.
                # Neither clearing nor retaining them across a turn is justified.
                if type(stack.statuses) is not dict or set(stack.statuses) - {GRANT_STATUS}:
                    raise RuntimeHalt('TURN_END_STATUS_UNSUPPORTED: ' + stack.cards[-1].key)
                validate_grants(runtime, owner, target_key)
            for index, card in enumerate(stack.cards):
                field = 'main_text' if index == len(stack.cards) - 1 else 'inherited_text'
                text = runtime.context.card(owner, card.card_number).effect_text(field)
                timings = (timing, 'End of All Turns')
                for trigger in timings:
                    lines = trigger_lines(text, trigger)
                    if not lines:
                        continue
                    if (owner == seat and card.card_number == 'BT22-023'
                            and field == 'main_text' and trigger == 'End of Your Turn'
                            and lines == (END_LINE,)):
                        runtime.registry.lookup(card.card_number, END_EFFECT, field)
                        sources.append((owner, card.key))
                        continue
                    raise RuntimeHalt('TURN_END_TRIGGER_UNSUPPORTED: ' + card.card_number
                                      + ' ' + field + ' ' + trigger + ' source=' + card.key)
    return sources


def _queue_end_effects(runtime, sources):
    before = len(runtime.state.pending)
    queue_effects(runtime, [{'seat': owner, 'source': source, 'effect_id': END_EFFECT,
        'field': 'main_text', 'usage': list(end_turn_usage(runtime, owner, source)),
        'trigger': {'kind': 'End of Your Turn', 'phase': runtime.state.phase,
                    'turn': runtime.state.turn}} for owner, source in sources])
    return len(runtime.state.pending) - before


def _pass(runtime, seat, choice):
    _actor(runtime, seat)
    state = runtime.state
    if state.phase != 'MAIN' or state.memory < 0:
        raise RuntimeHalt('PASS_WINDOW_NOT_OPEN')
    sources = _end_dependencies(runtime, seat)
    before = state.memory
    # 6-5-1-7-1 sets the gauge, rather than paying or losing three memory.
    state.memory = -3
    state.phase = 'END_OF_TURN'
    queued = _queue_end_effects(runtime, sources)
    return {'phase': state.phase, 'memory_before': before, 'memory_after': -3,
            'turn_postponed': False, 'pending_end_effects': queued,
            'rules_source': choice['rules'], 'full_match_credit': 0}


def pass_turn(runtime, seat, root):
    """Declare a pass explicitly; finish_turn closes its end window separately."""
    return runtime._control_command('PASS_TURN', seat, {'rules': _turn_rules(root)}, _pass)


def _finish(runtime, seat, choice):
    _actor(runtime, seat)
    state = runtime.state
    if state.phase != 'END_OF_TURN':
        raise RuntimeHalt('TURN_END_WINDOW_NOT_OPEN')
    sources = _end_dependencies(runtime, seat)
    before = state.memory
    queued = _queue_end_effects(runtime, sources)
    if queued:
        return {'phase': state.phase, 'memory_before': before, 'memory_after': before,
                'end_processing_pending': True, 'pending_end_effects': queued,
                'turn_postponed': False, 'rules_source': choice['rules'], 'full_match_credit': 0}
    if before >= 0:
        # This engine enters END_OF_TURN only from MAIN. Rule 6-6-4
        # resumes that phase, preserving uses consumed earlier in this turn.
        state.phase = 'MAIN'
        return {'phase': state.phase, 'memory_before': before, 'memory_after': before,
                'turn_postponed': True, 'rules_source': choice['rules'], 'full_match_credit': 0}
    # The control-command pending guard enforces 6-6-2/3: every pending
    # activation must finish even if an earlier effect regained memory.
    expire_turn_grants(runtime, seat)
    state.active = 'B' if seat == 'A' else 'A'
    state.memory = -before
    state.turn += 1
    state.once_used.clear()
    state.phase = 'START_OF_TURN'
    return {'phase': state.phase, 'memory_before': before, 'memory_after': state.memory,
            'next_controller': state.active, 'turn': state.turn, 'turn_postponed': False,
            'rules_source': choice['rules'], 'full_match_credit': 0}


def finish_turn(runtime, seat, root):
    """Finish an open main-phase end window after all effects have resolved."""
    return runtime._control_command('FINISH_TURN', seat, {'rules': _turn_rules(root)}, _finish)
