"""Revalidate and resolve one saved selection, without invoking any policy.

This produces a paused engineering checkpoint. Historical reference-pilot
identities remain historical; replay does not turn them into user-bot evidence.
"""
import copy
import hashlib
import json
from pathlib import Path

from context_runtime import ContextRuntime, RuntimeHalt
from imported_attempts import (ROOT, _apply, _comparable_public_view,
                               _load_context_selection, _physical_snapshot,
                               _saved_context_inputs, _verify_previous_record_hash)
from match_context import canonical, digest
from selected_mechanics import build_selected_registry


def continue_selected_action(previous_record, root=ROOT):
    """Replay the successful prefix, retry exactly its saved pending choice, pause.

    There is deliberately no candidate generation, policy construction, action
    loop, or automatic next-window processing in this operation.
    """
    root = Path(root).resolve()
    previous = json.loads(canonical(previous_record))
    _verify_previous_record_hash(previous)
    commands = previous.get('commands')
    if (previous.get('status') not in ('HALT', 'DIAGNOSTIC_SOFTWARE_ERROR')
            or not isinstance(commands, list) or not commands
            or any(command.get('status') != 'EXPERIMENTAL_RESOLVED' for command in commands[:-1])
            or commands[-1].get('status') != previous['status']):
        raise RuntimeHalt('SAVED_ACTION_HALTED_PREFIX_REQUIRED')
    selected = commands[-1]
    if (selected.get('command') != 'RESOLVE_PENDING' or selected.get('seat') not in ('A', 'B')
            or not isinstance(selected.get('args'), dict)
            or set(selected['args']) != {'pending_id', 'choice'}
            or not isinstance(selected['args']['pending_id'], str)
            or not selected['args']['pending_id']):
        raise RuntimeHalt('SAVED_ACTION_RESOLVE_SELECTION_REQUIRED')
    if (type(previous.get('index')) is not int or previous['index'] < 0
            or type(previous.get('seed')) is not int or previous['seed'] < 0
            or previous.get('first') not in ('A', 'B')):
        raise RuntimeHalt('SAVED_ACTION_ORIGINAL_INPUTS_INVALID')
    halts = previous.get('halts')
    if not isinstance(halts, list) or not halts or not isinstance(halts[-1].get('before'), dict):
        raise RuntimeHalt('SAVED_ACTION_BEFORE_HALT_REQUIRED')
    before = _physical_snapshot(halts[-1]['before'])
    if (canonical(before) != canonical(_physical_snapshot(previous.get('final')))
            or before.get('context_id') != previous['context_id']
            or before.get('seed') != previous['seed'] or before.get('first') != previous['first']
            or before['state'].get('terminal')):
        raise RuntimeHalt('SAVED_ACTION_ORIGINAL_CHECKPOINT_INVALID')
    context_file, expected_sha256 = _saved_context_inputs(previous, root)
    context, context_file, context_sha256 = _load_context_selection(
        root, context_file, expected_context=(previous['context_id'], expected_sha256))
    runtime = ContextRuntime(context, previous['seed'], previous['first'],
                             build_selected_registry(context, root), allow_experimental=True)
    initial = runtime.snapshot()
    if canonical(_physical_snapshot(initial)) != canonical(_physical_snapshot(previous['initial'])):
        raise RuntimeHalt('SAVED_ACTION_INITIAL_PHYSICAL_MISMATCH')
    for index, command in enumerate(commands[:-1]):
        seat = command.get('seat')
        if (seat not in ('A', 'B') or canonical(_comparable_public_view(command.get('public_view')))
                != canonical(_comparable_public_view(runtime.public_view(seat)))):
            raise RuntimeHalt('SAVED_ACTION_PREFIX_PUBLIC_VIEW_MISMATCH: command=' + str(index))
        result = _apply(runtime, command['command'], seat, copy.deepcopy(command['args']), root)
        if canonical(result) != canonical(command.get('result')):
            raise RuntimeHalt('SAVED_ACTION_PREFIX_RESULT_MISMATCH: command=' + str(index))
        runtime.verify()
    revalidated_before = _physical_snapshot(runtime.snapshot())
    if canonical(before) != canonical(revalidated_before):
        raise RuntimeHalt('SAVED_ACTION_BEFORE_HALT_PHYSICAL_MISMATCH')
    seat = selected['seat']
    if canonical(_comparable_public_view(selected.get('public_view'))) != canonical(
            _comparable_public_view(runtime.public_view(seat))):
        raise RuntimeHalt('SAVED_ACTION_SELECTED_PUBLIC_VIEW_MISMATCH')

    # The exact stored selection is the sole new command. Leave the next
    # scheduler/turn window for the actual player policies to select later.
    result = _apply(runtime, selected['command'], seat, copy.deepcopy(selected['args']), root)
    runtime.verify()
    retried = {key: copy.deepcopy(value) for key, value in selected.items()
               if key not in ('status', 'reason', 'exception', 'result')}
    retried.update({'status': 'EXPERIMENTAL_RESOLVED', 'result': copy.deepcopy(result)})
    previous_hash = digest(previous)
    lineage = {
        'schema': 'recorded-selected-action-continuation-v1',
        'previous_record_sha256': previous_hash, 'previous_record': previous,
        'previous_execution_id': previous['replay_provenance']['execution_id'],
        'previous_pilots': copy.deepcopy(previous['pilots']),
        'successful_commands_revalidated': len(commands) - 1,
        'retried_command_index': len(commands) - 1,
        'retried_selection_sha256': digest(selected),
        'physical_state_proof': {
            'comparison': 'ALL_SNAPSHOT_FIELDS_EXCEPT_EXECUTION_ID',
            'legacy_defaults': {'state.resolving_option': None},
            'original_before_sha256': digest(before),
            'revalidated_before_sha256': digest(revalidated_before),
            'original_rng_sha256': digest(before['rng_state']),
            'revalidated_rng_sha256': digest(revalidated_before['rng_state'])}}
    record = {key: copy.deepcopy(previous[key]) for key in
              ('index', 'context_id', 'seed', 'first', 'pilots', 'pilot_id')}
    record.update({
        'schema': 'recorded-selected-action-checkpoint-v1',
        'status': 'PAUSED_AFTER_SAVED_ACTION', 'certification': 'EXPERIMENTAL_UNREVIEWED',
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
        'user_bot_evidence_credit': 0,
        'policy_execution': {'mode': 'SAVED_SELECTION_ONLY', 'policy_invocations': 0,
                             'new_policy_decisions': 0,
                             'historical_pilots_usage': 'PROVENANCE_ONLY'},
        'commands': copy.deepcopy(commands[:-1]) + [retried],
        'events': copy.deepcopy(runtime.events), 'halts': [],
        'initial': initial, 'final': runtime.snapshot(),
        'winner': runtime.state.winner, 'terminal_reason': runtime.state.terminal_reason,
        'continuation_provenance': lineage,
        'replay_provenance': {
            'context_file': context_file, 'context_file_sha256': context_sha256,
            'execution_id': runtime.execution_id,
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dispatcher_sha256': hashlib.sha256(Path(__file__).with_name('imported_attempts.py').read_bytes()).hexdigest(),
            'replay_method': 'REVALIDATE_PREFIX_RETRY_EXACT_SAVED_ACTION_PAUSE_COMPARE_ENTIRE_RECORD',
            'certification': 'NONE_EXACT_REPLAY_IS_SOFTWARE_EVIDENCE_ONLY'}})
    return json.loads(canonical(record))


def replay_selected_action(record, root=ROOT):
    """Recreate and compare the complete bounded checkpoint, including provenance."""
    if (record.get('schema') != 'recorded-selected-action-checkpoint-v1'
            or record.get('status') != 'PAUSED_AFTER_SAVED_ACTION'):
        raise RuntimeHalt('SAVED_ACTION_PAUSED_CHECKPOINT_REQUIRED')
    _verify_previous_record_hash(record)
    previous = record['continuation_provenance']['previous_record']
    replayed = continue_selected_action(previous, root)
    return {'index': record['index'], 'exact_match': canonical(record) == canonical(replayed),
            'saved_record_sha256': digest(record), 'replayed_record_sha256': digest(replayed),
            'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}
