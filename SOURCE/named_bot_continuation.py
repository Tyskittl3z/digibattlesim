"""Bounded named-player continuation of saved mixed-policy engineering games."""
import copy
import hashlib
import json
from pathlib import Path

from context_runtime import ContextRuntime, RuntimeHalt
from imported_attempts import (ROOT, _apply, _comparable_public_view, _load_context_selection,
                               _physical_snapshot, _saved_context_inputs,
                               _verify_previous_record_hash, breeding_candidates,
                               counter_options, main_candidates, pending_choice, pending_options)
from match_context import canonical, digest
from named_player_bots import NamedPlayerBot
from selected_mechanics import build_selected_registry


SCHEMA = 'named-bot-game-continuation-v1'
PAUSED = 'PAUSED_AFTER_NAMED_BOT_SEGMENT'
GENERATORS = frozenset(('GENERATE_MAIN_CANDIDATES', 'GENERATE_PENDING_CHOICES',
                        'GENERATE_BREEDING_CHOICES', 'GENERATE_COUNTER_CHOICES',
                        'GENERATE_BLOCK_CHOICES', 'SELECT_NEXT_COMMAND'))


def _choose(bot, view, candidates, decision):
    chosen = bot.choose(copy.deepcopy(view), copy.deepcopy(candidates), decision=copy.deepcopy(decision))
    if not any(canonical(chosen) == canonical(candidate) for candidate in candidates):
        raise RuntimeHalt('NAMED_BOT_SELECTED_NONCANDIDATE')
    return copy.deepcopy(chosen)


class _BoundAdapter:
    """Only public pending metadata supplements the requesting seat's view."""
    def __init__(self, bot, selected):
        self.bot = bot
        self.decision = {'kind': 'PENDING_CHOICE', 'selected_pending': copy.deepcopy(selected),
                         'effect_id': selected['effect_id'], 'source': selected['source']}

    def choose(self, view, candidates):
        return _choose(self.bot, view, candidates, self.decision)

    def bottom_order(self, remainder):
        ordered = self.bot.bottom_order(copy.deepcopy(remainder))
        if (not isinstance(ordered, list) or len(ordered) != len(remainder)
                or sorted(ordered) != sorted(remainder)):
            raise RuntimeHalt('NAMED_BOT_BOTTOM_ORDER_INVALID')
        return ordered


def _plain_block_options(runtime, seat):
    """Do not turn a missing Blocker-choice implementation into a decline."""
    from effect_grants import active_keyword, active_restriction
    from printed_triggers import effect_headers
    for key, stack in runtime.state.battle[seat].items():
        if (runtime.context.card(seat, stack.cards[-1].card_number).kind != 'Digimon'
                or stack.suspended or stack.statuses.get('cannot_suspend', False)
                or active_restriction(runtime, seat, key, 'cannot_suspend')):
            continue
        printed = any(not effect_headers(line) and '＜Blocker＞' in line
                      for index, card in enumerate(stack.cards)
                      for line in runtime.context.card(seat, card.card_number).effect_text(
                          'main_text' if index == len(stack.cards) - 1 else 'inherited_text').splitlines())
        if printed or active_keyword(runtime, seat, key, 'Blocker'):
            raise RuntimeHalt('NAMED_BOT_BLOCK_CHOICES_UNIMPLEMENTED: ' + key)
    return [{'card': None, 'status': 'NO_ELIGIBLE_BLOCKER'}]


def continue_with_named_bots(previous_record, root=ROOT, max_new_commands=12):
    """Revalidate a saved game, run a bounded named-policy segment, save gaps."""
    if type(max_new_commands) is not int or max_new_commands < 1:
        raise ValueError('Positive new-command budget required')
    root = Path(root).resolve()
    previous = json.loads(canonical(previous_record))
    _verify_previous_record_hash(previous)
    commands = previous.get('commands')
    paused = ((previous.get('schema') == 'recorded-selected-action-checkpoint-v1'
               and previous.get('status') == 'PAUSED_AFTER_SAVED_ACTION')
              or (previous.get('schema') == SCHEMA and previous.get('status') == PAUSED))
    stopped = previous.get('schema') == SCHEMA and previous.get('status') in ('HALT', 'DIAGNOSTIC_SOFTWARE_ERROR')
    if (not (paused or stopped) or not isinstance(commands, list) or not commands
            or (paused and any(c.get('status') != 'EXPERIMENTAL_RESOLVED' for c in commands))
            or (stopped and (any(c.get('status') != 'EXPERIMENTAL_RESOLVED' for c in commands[:-1])
                            or commands[-1].get('status') != previous['status']))):
        raise RuntimeHalt('NAMED_BOT_SAVED_CHECKPOINT_REQUIRED')
    if (type(previous.get('index')) is not int or previous['index'] < 0
            or type(previous.get('seed')) is not int or previous['seed'] < 0
            or previous.get('first') not in ('A', 'B')):
        raise RuntimeHalt('NAMED_BOT_ORIGINAL_INPUTS_INVALID')
    retry = commands[-1] if stopped else None
    if retry and retry['command'] in GENERATORS and not retry.get('selected_pending'):
        raise RuntimeHalt('NAMED_BOT_UNSELECTED_GENERATOR_CHECKPOINT')
    if stopped:
        halts = previous.get('halts')
        if (not isinstance(halts, list) or not halts
                or canonical(_physical_snapshot(halts[-1]['before']))
                != canonical(_physical_snapshot(previous['final']))):
            raise RuntimeHalt('NAMED_BOT_SAVED_HALT_SNAPSHOT_MISMATCH')
    context_file, expected_hash = _saved_context_inputs(previous, root)
    context, context_file, context_hash = _load_context_selection(
        root, context_file, expected_context=(previous['context_id'], expected_hash))
    runtime = ContextRuntime(context, previous['seed'], previous['first'],
                             build_selected_registry(context, root), allow_experimental=True)
    initial = runtime.snapshot()
    if canonical(_physical_snapshot(initial)) != canonical(_physical_snapshot(previous['initial'])):
        raise RuntimeHalt('NAMED_BOT_INITIAL_PHYSICAL_MISMATCH')
    successful = commands[:-1] if stopped else commands
    for index, saved in enumerate(successful):
        seat = saved.get('seat')
        if (seat not in ('A', 'B') or canonical(_comparable_public_view(saved.get('public_view')))
                != canonical(_comparable_public_view(runtime.public_view(seat)))):
            raise RuntimeHalt('NAMED_BOT_PREFIX_PUBLIC_VIEW_MISMATCH: command=' + str(index))
        result = _apply(runtime, saved['command'], seat, copy.deepcopy(saved['args']), root)
        if canonical(result) != canonical(saved.get('result')):
            raise RuntimeHalt('NAMED_BOT_PREFIX_RESULT_MISMATCH: command=' + str(index))
        runtime.verify()
    original_before = _physical_snapshot(previous['final'])
    revalidated_before = _physical_snapshot(runtime.snapshot())
    if (canonical(original_before) != canonical(revalidated_before)
            or original_before.get('context_id') != previous['context_id']
            or original_before.get('seed') != previous['seed']
            or original_before.get('first') != previous['first']):
        raise RuntimeHalt('NAMED_BOT_FINAL_PHYSICAL_MISMATCH')
    if runtime.state.terminal:
        raise RuntimeHalt('NAMED_BOT_TERMINAL_CHECKPOINT')
    if retry and retry.get('public_view') != runtime.public_view(retry['seat']):
        raise RuntimeHalt('NAMED_BOT_RETRY_PUBLIC_VIEW_MISMATCH')

    # Construction happens after the complete prefix/state/RNG proof.
    bots = {seat: NamedPlayerBot(context, seat) for seat in ('A', 'B')}
    active_pilots = {seat: bot.manifest() for seat, bot in bots.items()}
    history = copy.deepcopy(successful)
    new_decisions = []
    offsets = {seat: 0 for seat in bots}
    decision_command_indices = []
    new_commands = 0
    current = None
    status, halt_reason = PAUSED, None

    def collect_decisions(command):
        collected = []
        for owner, bot in bots.items():
            added = copy.deepcopy(bot.decision_log[offsets[owner]:])
            offsets[owner] = len(bot.decision_log)
            collected.extend(added)
        if collected:
            command['decisions'] = collected
            command['bot_id'] = active_pilots[command['seat']]['bot_id']
            new_decisions.extend(copy.deepcopy(collected))
            index = len(history) - 1 if history and history[-1] is command else len(history)
            decision_command_indices.append(index)

    def call(kind, seat, args=None, candidates=None, saved_retry=None, saved_pending=None):
        nonlocal current, new_commands
        current = ({key: copy.deepcopy(value) for key, value in saved_retry.items()
                    if key not in ('status', 'reason', 'exception', 'result')}
                   if saved_retry is not None else
                   {'command': kind, 'seat': seat, 'args': copy.deepcopy(args or {}),
                    'public_view': runtime.public_view(seat)})
        if candidates is not None:
            current['candidates'] = copy.deepcopy(candidates)
        if saved_pending is not None:
            current['selected_pending'] = copy.deepcopy(saved_pending['selected_pending'])
            current['saved_selection_decisions'] = copy.deepcopy(saved_pending.get('decisions', []))
            current['decision_origin'] = {'kind': 'RETRIED_SAVED_PENDING_SELECTION',
                                          'previous_record_sha256': digest(previous)}
        collect_decisions(current)
        history.append(current)
        new_commands += 1
        result = _apply(runtime, kind, seat, copy.deepcopy(current['args']), root)
        current.update({'status': 'EXPERIMENTAL_RESOLVED', 'result': copy.deepcopy(result)})

    try:
        if retry is not None:
            if retry['command'] == 'GENERATE_PENDING_CHOICES':
                current = copy.deepcopy(retry)
                selected, seat = retry['selected_pending'], retry['seat']
                options = pending_options(runtime, seat)
                if selected not in options:
                    raise RuntimeHalt('NAMED_BOT_SAVED_PENDING_SELECTION_UNAVAILABLE')
                choice = pending_choice(runtime, seat, selected, _BoundAdapter(bots[seat], selected))
                call('RESOLVE_PENDING', seat, {'pending_id': selected['id'], 'choice': choice},
                     options, saved_pending=retry)
            else:
                call(retry['command'], retry['seat'], retry['args'], saved_retry=retry)
        while not runtime.state.terminal and new_commands < max_new_commands:
            seat = runtime.state.active
            view = runtime.public_view(seat)
            current = {'command': 'SELECT_NEXT_COMMAND', 'seat': seat, 'public_view': view}
            if runtime.state.pending:
                current['command'] = 'GENERATE_PENDING_CHOICES'
                options = {owner: pending_options(runtime, owner) for owner in ('A', 'B')}
                owner = next((owner for owner in ('A', 'B') if options[owner]), None)
                if owner is None:
                    call('SETTLE_PENDING', seat)
                else:
                    view = runtime.public_view(owner)
                    current.update({'seat': owner, 'public_view': view, 'pending_candidates': options[owner]})
                    selected = _choose(bots[owner], view, options[owner], {'kind': 'PENDING_EFFECT_ORDER'})
                    current['selected_pending'] = copy.deepcopy(selected)
                    choice = pending_choice(runtime, owner, selected, _BoundAdapter(bots[owner], selected))
                    call('RESOLVE_PENDING', owner, {'pending_id': selected['id'], 'choice': choice}, options[owner])
            elif view['attack']:
                attack = view['attack']
                if attack['window'] in ('COUNTER', 'BLOCK'):
                    owner = attack['defender']
                    kind = attack['window']
                    view = runtime.public_view(owner)
                    current.update({'command': 'GENERATE_' + kind + '_CHOICES', 'seat': owner, 'public_view': view})
                    options = counter_options(runtime, owner) if kind == 'COUNTER' else _plain_block_options(runtime, owner)
                    chosen = _choose(bots[owner], view, options, {'kind': kind + '_CHOICE'})
                    call(kind + '_CHOICE', owner, chosen, options)
                elif attack['window'] == 'CONFIRM': call('CONFIRM_ATTACK', attack['controller'])
                elif attack['window'] == 'END': call('END_ATTACK', attack['controller'])
                else: raise RuntimeHalt('NAMED_BOT_ATTACK_WINDOW_UNSUPPORTED: ' + str(attack['window']))
            elif view['phase'] == 'BREEDING':
                current['command'] = 'GENERATE_BREEDING_CHOICES'
                options = breeding_candidates(context, view, seat)
                chosen = _choose(bots[seat], view, options, {'kind': 'BREEDING_ACTION'})
                call('BREEDING_CHOICE', seat, chosen, options)
            elif view['phase'] == 'MAIN':
                current['command'] = 'GENERATE_MAIN_CANDIDATES'
                options = main_candidates(runtime, seat, root)
                chosen = _choose(bots[seat], view, options, {'kind': 'MAIN_ACTION'})
                call(chosen['kind'], seat, chosen, options)
            elif view['phase'] == 'END_OF_TURN': call('FINISH_TURN', seat)
            else: call('ADVANCE_PHASE', seat)
        runtime.verify()
        if runtime.state.terminal:
            status = 'EXPERIMENTAL_SOFTWARE_TERMINAL'
    except Exception as exc:
        halt_reason = str(exc)
        status = 'HALT' if isinstance(exc, RuntimeHalt) else 'DIAGNOSTIC_SOFTWARE_ERROR'
        if current is None: current = {'command': 'SELECT_NEXT_COMMAND', 'seat': runtime.state.active}
        collect_decisions(current)
        current.update({'status': status, 'reason': halt_reason, 'exception': type(exc).__name__})
        if not history or history[-1] is not current:
            history.append(current)
        if not runtime.events or runtime.events[-1].get('type') != 'HALT':
            runtime.events.append({'type': 'HALT', 'status': status, 'seed': runtime.seed,
                                   'first': runtime.first, 'context_id': context.matchup_id,
                                   'command': copy.deepcopy(current), 'reason': halt_reason,
                                   'exception': type(exc).__name__, 'before': runtime.snapshot()})
        runtime.halted = True

    previous_hash = digest(previous)
    record = {key: copy.deepcopy(previous[key]) for key in
              ('index', 'context_id', 'seed', 'first', 'pilots', 'pilot_id')}
    record.update({
        'schema': SCHEMA, 'status': status, 'max_new_commands': max_new_commands,
        'certification': 'EXPERIMENTAL_UNREVIEWED_MIXED_POLICY_HISTORY',
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
        'user_bot_evidence_credit': 0, 'ratings_assigned': False,
        'active_pilots': active_pilots, 'new_decisions': new_decisions,
        'commands': history, 'events': runtime.events,
        'halts': [event for event in runtime.events if event.get('type') == 'HALT'],
        'initial': initial, 'final': runtime.snapshot(), 'halt_reason': halt_reason,
        'winner': runtime.state.winner, 'terminal_reason': runtime.state.terminal_reason,
        'continuation_provenance': {
            'schema': 'named-policy-segment-v1', 'previous_record': previous,
            'previous_record_sha256': previous_hash,
            'previous_execution_id': previous['replay_provenance']['execution_id'],
            'previous_active_pilots': copy.deepcopy(previous.get('active_pilots')),
            'successful_commands_revalidated': len(successful),
            'first_segment_command_index': len(successful),
            'first_new_policy_decision_command_index': (decision_command_indices[0]
                                                       if decision_command_indices else None),
            'physical_state_proof': {
                'comparison': 'ALL_SNAPSHOT_FIELDS_EXCEPT_EXECUTION_ID',
                'original_before_sha256': digest(original_before),
                'revalidated_before_sha256': digest(revalidated_before),
                'original_rng_sha256': digest(original_before['rng_state']),
                'revalidated_rng_sha256': digest(revalidated_before['rng_state'])}},
        'replay_provenance': {
            'context_file': context_file, 'context_file_sha256': context_hash,
            'execution_id': runtime.execution_id,
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dispatcher_sha256': hashlib.sha256(Path(__file__).with_name('imported_attempts.py').read_bytes()).hexdigest(),
            'profile_source_sha256': hashlib.sha256(Path(__file__).with_name('named_player_bots.py').read_bytes()).hexdigest(),
            'replay_method': 'REVALIDATE_PREFIX_RUN_NAMED_BOT_SEGMENT_COMPARE_ENTIRE_RECORD',
            'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}})
    return json.loads(canonical(record))


def replay_named_bot_continuation(record, root=ROOT):
    if record.get('schema') != SCHEMA:
        raise RuntimeHalt('NAMED_BOT_CONTINUATION_RECORD_REQUIRED')
    _verify_previous_record_hash(record)
    replayed = continue_with_named_bots(record['continuation_provenance']['previous_record'],
                                       root, record['max_new_commands'])
    return {'index': record['index'], 'exact_match': canonical(record) == canonical(replayed),
            'saved_record_sha256': digest(record), 'replayed_record_sha256': digest(replayed),
            'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}
