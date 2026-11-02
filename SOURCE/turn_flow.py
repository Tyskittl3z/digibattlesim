"""Explicit selected-pair pass and main-phase turn-end processing.

End-of-turn card effects and status durations remain unsupported. Encountering
one halts the whole command before committing memory, phase, OPT, or seat changes.
This module supplies no result handling, automatic pilot, or full-match credit.
"""
from context_runtime import RuntimeHalt
from match_preparation import _rules


def _turn_rules(root):
    return {**_rules(root), 'locator': (
        'Comprehensive rules v4.3: 6-1-3; 6-1-4; 6-5-1-7-1; 6-6; '
        '15-8-3-6; 15-14-1-5-1; 15-16-12')}


def _actor(runtime, seat):
    if seat != runtime.state.active:
        raise RuntimeHalt('ACTIVE_PLAYER_REQUIRED')


def _end_dependencies(runtime, seat):
    """Fail closed on live end timings, including optional printed processing.

    BT22-023 and BT20-102 have no end-timing handlers in the selected registry.
    Their unsupported effects must not be represented as automatic declines.
    Only a stack's top main text and its lower cards' inherited text are active;
    the opponent's [End of Your Turn] text does not trigger on this turn.
    """
    for owner in ('A', 'B'):
        timing = 'End of Your Turn' if owner == seat else "End of Opponent's Turn"
        for stack in runtime.state.battle[owner].values():
            if stack.statuses:
                # Existing booleans carry no grant/source or expiry metadata.
                # Neither clearing nor retaining them across a turn is justified.
                raise RuntimeHalt('TURN_END_STATUS_UNSUPPORTED: ' + stack.cards[-1].key)
            for index, card in enumerate(stack.cards):
                field = 'main_text' if index == len(stack.cards) - 1 else 'inherited_text'
                text = runtime.context.card(owner, card.card_number).effect_text(field)
                timings = (timing, 'End of All Turns')
                for trigger in timings:
                    if '[' + trigger + ']' in text:
                        raise RuntimeHalt('TURN_END_TRIGGER_UNSUPPORTED: ' + card.card_number
                                          + ' ' + field + ' ' + trigger + ' source=' + card.key)


def _pass(runtime, seat, choice):
    _actor(runtime, seat)
    state = runtime.state
    if state.phase != 'MAIN' or state.memory < 0:
        raise RuntimeHalt('PASS_WINDOW_NOT_OPEN')
    _end_dependencies(runtime, seat)
    before = state.memory
    # 6-5-1-7-1 sets the gauge, rather than paying or losing three memory.
    state.memory = -3
    state.phase = 'END_OF_TURN'
    return {'phase': state.phase, 'memory_before': before, 'memory_after': -3,
            'turn_postponed': False, 'rules_source': choice['rules'], 'full_match_credit': 0}


def pass_turn(runtime, seat, root):
    """Declare a pass explicitly; finish_turn closes its end window separately."""
    return runtime._control_command('PASS_TURN', seat, {'rules': _turn_rules(root)}, _pass)


def _finish(runtime, seat, choice):
    _actor(runtime, seat)
    state = runtime.state
    if state.phase != 'END_OF_TURN':
        raise RuntimeHalt('TURN_END_WINDOW_NOT_OPEN')
    _end_dependencies(runtime, seat)
    before = state.memory
    if before >= 0:
        # This engine enters END_OF_TURN only from MAIN. Rule 6-6-4
        # resumes that phase, preserving uses consumed earlier in this turn.
        state.phase = 'MAIN'
        return {'phase': state.phase, 'memory_before': before, 'memory_after': before,
                'turn_postponed': True, 'rules_source': choice['rules'], 'full_match_credit': 0}
    # The control-command pending guard enforces 6-6-2/3: every pending
    # activation must finish even if an earlier effect regained memory.
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
