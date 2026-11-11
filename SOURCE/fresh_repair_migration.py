"""Explicit, exact-prefix engine repair; no player calls or failed-action retry.

Lineage is content-addressed software evidence, not independent rules approval.
The verified original source tree must remain available for the explicit migration;
ordinary replay uses the embedded immutable parent and current strict source pins.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from context_runtime import ContextRuntime, RuntimeHalt
from field_tracker import FieldTracker
from match_context import canonical, digest

SCHEMA = 'fresh-repair-lineage-v1'
_SOURCE_ONLY_WORKER = False
_LINEAGE_RUNNER = '395d0822e362ad5ee856cb01c3632c33fe90e5b4769b55da337f4ed8128f2344'
_BOOTSTRAP_RUNNER = 'dd5cd17e718097c69e391c09e9b9d9c7c62b8021cc261b696f57543320889718'
_TRACKER_EXTENSION_BASE = 'fc3fcdcc639b5551729f8d752131661a468028ffe3de66b8345e18151e292a4e'
_BLOCKER_EXTENSION_BASE = 'a9cfc58ba2499d8aed6438dfc9f3d3cddb12378f41927429e39add20a34b42dc'
_CHOICE_ROUTER_BASE = '13402f5987663e0df17c64453328d218b3574a6babc0390df8b02f448fc4f0d4'
# Explicit engine surface. Context, policies, schedule, judge, scorer, tracker and
# evidence/freeze tooling are intentionally outside this list.
_ENGINE = frozenset(('context_runtime.py', 'effect_scheduler.py', 'match_preparation.py',
    'phase_flow.py', 'breeding_evolution.py', 'main_actions.py', 'context_evolution.py',
    'search_effects.py', 'selected_mechanics.py', 'turn_flow.py', 'battlefield_scope.py',
    'attack_flow.py', 'printed_triggers.py', 'on_play_effects.py', 'effect_grants.py',
    'option_actions.py', 'aero_effects.py', 'battle_evolution.py', 'basic_event_dependencies.py',
    'tamer_play_effects.py', 'security_tamer.py', 'rina_unsuspend_effects.py',
    'ex13_ulforce_effects.py', 'rina_reactivation.py', 'return_effects.py',
    'field_tracker.py'))
_IDENTITY = ('schema', 'index', 'seed', 'first', 'campaign_id', 'context_id', 'context_file',
    'context_file_sha256', 'schedule', 'criteria', 'learning_state_id', 'learning_state_before',
    'learning_state_after', 'pilots', 'policy_rng_initial', 'certification',
    'accepted_fact_finding_credit', 'final_evaluation_credit', 'player_policy', 'history_report')
_SECURITY_POLICY_EXTENSION_BASE = '489f93f21debe54046b2d8512c7b24ed4fe1c8e08696a27b71337158764604bb'


def _same(left, right, label):
    if canonical(left) != canonical(right):
        raise RuntimeHalt('REPAIR_' + label + '_MISMATCH')


def _hash_record(record):
    _same(record.get('record_sha256'), digest({k: v for k, v in record.items()
                                               if k != 'record_sha256'}), 'RECORD_HASH')


def _snapshot(value):
    result = copy.deepcopy(value)
    result.pop('execution_id', None)
    return result


def _event(value):
    result = copy.deepcopy(value)
    result.pop('execution_id', None)
    if 'before' in result:
        result['before'] = _snapshot(result['before'])
    return result


def _judge(value):
    result = copy.deepcopy(value)
    result.pop('receipt_sha256', None)
    if isinstance(result.get('binding'), dict):
        result['binding'].pop('handler_module_sha256', None)
    if isinstance(result.get('predecessor_binding'), dict):
        result['predecessor_binding'].pop('tracker_id', None)
    return result


def _observation(value):
    result = copy.deepcopy(value)
    for key in ('previous_observation_sha256', 'observation_sha256'):
        result.pop(key, None)
    if 'judge_verdict' in result:
        result['judge_verdict'] = _judge(result['judge_verdict'])
    return result


def _command(value):
    result = copy.deepcopy(value)
    for key in ('before', 'after'):
        if key in result:
            result[key] = _snapshot(result[key])
    if 'judge' in result:
        result['judge'] = _judge(result['judge'])
    if 'observation' in result:
        result['observation'] = _observation(result['observation'])
    return result


def _decisions(values):
    result = copy.deepcopy(values)
    for decision in result:
        for key in ('status', 'reward', 'rating', 'learning_eligible'):
            decision.pop(key, None)
    return result


def _selection(command):
    # Only resolution annotations are excluded; literal aliases/arguments remain.
    result = {k: copy.deepcopy(v) for k, v in command.items() if k not in (
        'status', 'reason', 'exception', 'after', 'result', 'judge', 'rating',
        'tracker_command', 'observation', 'public_view_after', 'audit_failure')}
    result['before'] = _snapshot(result['before'])
    result['decisions'] = _decisions(result['decisions'])
    return result


def _dependencies(root, context_file):
    root = Path(root).resolve()
    context = (root / context_file).resolve()
    try:
        context.relative_to(root)
    except ValueError as exc:
        raise RuntimeHalt('REPAIR_DEPENDENCY_OUTSIDE_ROOT') from exc
    paths = set(p for p in (root / 'RULES').rglob('*') if p.is_file())
    paths.add(context)
    # Preserve non-Python source assets too, without treating caches as inputs.
    paths.update(p for p in (root / 'SOURCE').iterdir() if p.is_file()
                 and p.suffix not in ('.py', '.pyc'))
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def _differences(before, after, approved, *, bootstrap_sources=None):
    actual = {name: {'before': before.get(name), 'after': after.get(name)}
              for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)}
    _same(approved, actual, 'APPROVED_CHANGES')
    if not actual:
        raise RuntimeHalt('REPAIR_NO_SOURCE_CHANGES')
    bootstrap = (before.get('fresh_learning_campaign.py') == _BOOTSTRAP_RUNNER
        and 'fresh_repair_migration.py' not in before
        and {'fresh_learning_campaign.py', 'fresh_repair_migration.py'} <= set(actual))
    if bootstrap:
        _same(after.get('fresh_learning_campaign.py'), _LINEAGE_RUNNER, 'BOOTSTRAP_RUNNER')
    if bootstrap and bootstrap_sources is not None:
        for name in ('fresh_learning_campaign.py', 'fresh_repair_migration.py'):
            _same(after.get(name), bootstrap_sources[name], 'BOOTSTRAP_SOURCE')
    # One reviewed tracker-schema extension may update this migration tool.
    # Subsequent infrastructure edits remain protected; exact older command,
    # policy, judge, color and Bot C evidence must still replay unchanged.
    tracker_extension = (before.get('fresh_repair_migration.py') == _TRACKER_EXTENSION_BASE
                         and 'field_tracker.py' in actual
                         and 'fresh_repair_migration.py' in actual)
    blocker_extension = (before.get('fresh_repair_migration.py') == _BLOCKER_EXTENSION_BASE
                         and 'named_bot_continuation.py' in actual
                         and 'fresh_repair_migration.py' in actual)
    choice_router_extension = (before.get('fresh_repair_migration.py') == _CHOICE_ROUTER_BASE
                               and 'imported_attempts.py' in actual
                               and 'fresh_repair_migration.py' in actual)
    security_policy_extension = (before.get('fresh_repair_migration.py') == _SECURITY_POLICY_EXTENSION_BASE
                                 and {'interaction_learning.py', 'fresh_repair_migration.py'} <= set(actual))
    allowed = _ENGINE | ({'fresh_learning_campaign.py', 'fresh_repair_migration.py'} if bootstrap else set())
    if tracker_extension:
        allowed |= {'fresh_repair_migration.py'}
    if blocker_extension:
        allowed |= {'named_bot_continuation.py', 'fresh_repair_migration.py'}
    if choice_router_extension:
        allowed |= {'imported_attempts.py', 'fresh_repair_migration.py'}
    if security_policy_extension:
        allowed |= {'interaction_learning.py', 'fresh_repair_migration.py'}
    if set(actual) - allowed or any(before.get(k) is None or after.get(k) is None
                                    for k in actual if k in _ENGINE):
        raise RuntimeHalt('REPAIR_PROTECTED_SOURCE_CHANGE')
    return actual


def _boundary(record):
    if record.get('status') not in ('PAUSED', 'HALT', 'DIAGNOSTIC_SOFTWARE_ERROR'):
        raise RuntimeHalt('REPAIR_RESUMABLE_STATUS_MISMATCH')
    if record['final']['state']['terminal']:
        raise RuntimeHalt('REPAIR_TERMINAL_RECORD')
    commands = record.get('commands')
    if not isinstance(commands, list):
        raise RuntimeHalt('REPAIR_COMMANDS_MISMATCH')
    failed = [i for i, item in enumerate(commands) if item.get('status') != 'EXPERIMENTAL_RESOLVED']
    if record['status'] == 'PAUSED':
        if failed:
            raise RuntimeHalt('REPAIR_FAILURE_POSITION_MISMATCH')
    else:
        if failed != [len(commands) - 1] or not commands:
            raise RuntimeHalt('REPAIR_FAILURE_POSITION_MISMATCH')
        last = commands[-1]
        _same(last.get('status'), record['status'], 'FAILED_STATUS')
        _same(last.get('before'), last.get('after'), 'FAILED_STATE')
        _same(last.get('after'), record['final'], 'FAILED_CHECKPOINT')
        if last.get('rating', {}).get('status') != 'UNRATED' or 'audit_failure' in last:
            raise RuntimeHalt('REPAIR_FAILED_RATING_MISMATCH')
    return len(commands) - len(failed)


def _retry_relation(saved, current):
    if not saved['command'].startswith('GENERATE_') and saved['command'] != 'SELECT_NEXT_COMMAND':
        _same(_selection(saved), _selection(current), 'FAILED_SELECTION')
        return
    # A generator may have selected the pending order and some choice values.
    for key in ('seat', 'public_view', 'policy_rng_before_choice', 'selected_pending', 'pending_candidates'):
        if key in saved:
            _same(saved[key], current.get(key), 'PARTIAL_SELECTION_' + key.upper())
    _same(_snapshot(saved['before']), _snapshot(current['before']), 'PARTIAL_BEFORE')
    choices = _decisions(saved['decisions'])
    _same(choices, _decisions(current['decisions'])[:len(choices)], 'PARTIAL_DECISIONS')
    if saved.get('selected_pending') and current['command'] == 'RESOLVE_PENDING':
        _same(saved['selected_pending']['id'], current['args']['pending_id'], 'PARTIAL_PENDING_ID')


def _relationship(record, line):
    parent = line['parent_record']
    count = _boundary(parent)
    _same(count, line['successful_prefix_count'], 'PREFIX_COUNT')
    for key in _IDENTITY:
        _same(parent.get(key), record.get(key), 'IDENTITY_' + key.upper())
    if parent['tracker'] == record['tracker']:
        _same(line.get('original_tracker'), None, 'UNCHANGED_TRACKER_LINEAGE')
    else:
        _same(line.get('original_tracker'), parent['tracker'], 'ORIGINAL_TRACKER')
        _same(line.get('repaired_tracker'), record['tracker'], 'REPAIRED_TRACKER')
        _same({k:v for k,v in parent['tracker'].items() if k not in ('source_sha256','tracker_id')},
              {k:v for k,v in record['tracker'].items() if k not in ('source_sha256','tracker_id')},
              'TRACKER_CONTRACT')
        if 'field_tracker.py' not in line['approved_changes']:
            raise RuntimeHalt('REPAIR_TRACKER_SOURCE_UNAPPROVED')
    _same(_snapshot(parent['initial']), _snapshot(record['initial']), 'INITIAL')
    if len(record['commands']) < count:
        raise RuntimeHalt('REPAIR_SHORT_PREFIX')
    for old, new in zip(parent['commands'][:count], record['commands'][:count]):
        _same(_command(old), _command(new), 'SUCCESSFUL_PREFIX')
    if len(parent['commands']) > count:
        failed = parent['commands'][count]
        _same(digest(_selection(failed)), line['failed_selection_sha256'], 'FAILED_SELECTION_DIGEST')
        if len(record['commands']) <= count:
            raise RuntimeHalt('REPAIR_LOST_FAILED_SELECTION')
        _retry_relation(failed, record['commands'][count])
    else:
        _same(line['failed_selection_sha256'], None, 'FAILED_SELECTION_DIGEST')
    # Bind the migrated checkpoint even when the child has continued beyond it.
    checkpoint = record['commands'][count - 1]['after'] if count else record['initial']
    _same(_snapshot(checkpoint), _snapshot(parent['final']), 'CHECKPOINT')
    _same(digest(_snapshot(parent['final'])), line['checkpoint_sha256'], 'CHECKPOINT_DIGEST')
    _same(digest(parent['final']['rng_state']), line['engine_rng_sha256'], 'ENGINE_RNG')
    _same(digest(parent['policy_rng_final']), line['policy_rng_sha256'], 'POLICY_RNG')
    boundary_rng = (parent['commands'][-1]['policy_rng_after_choice']
                    if parent['commands'] else parent['policy_rng_initial'])
    _same(parent['policy_rng_final'], boundary_rng, 'PARENT_POLICY_RNG_CHECKPOINT')
    _same([_observation(v) for v in parent['tracker_observations']],
          [_observation(v) for v in record['tracker_observations'][:count]],
          'PARENT_TRACKER_OBSERVATIONS')
    _same(parent['initial']['execution_id'], line['original_execution_id'], 'OLD_EXECUTION_ID')
    _same(record['initial']['execution_id'], line['repaired_execution_id'], 'NEW_EXECUTION_ID')
    # Only successful engine events are a live prefix after a consumed failure.
    old_events = parent['events']
    if (len(parent['commands']) > count and len(record['commands']) == count + 1
            and record['commands'][count]['status'] != 'EXPERIMENTAL_RESOLVED'):
        _same([_event(v) for v in old_events], [_event(v) for v in record['events']],
              'UNCONSUMED_FAILURE_EVENTS')
    if old_events and old_events[-1].get('type') == 'HALT':
        old_events = old_events[:-1]
    _same([_event(v) for v in old_events],
          [_event(v) for v in record['events'][:len(old_events)]], 'EVENT_PREFIX')


def _verify_line(record, dependencies):
    _hash_record(record)
    if 'repair_lineage' not in record:
        return
    line = record['repair_lineage']
    if not isinstance(line, dict) or line.get('schema') != SCHEMA:
        raise RuntimeHalt('REPAIR_LINEAGE_SCHEMA_MISMATCH')
    _same(line.get('lineage_sha256'), digest({k: v for k, v in line.items()
                                           if k != 'lineage_sha256'}), 'LINEAGE_HASH')
    parent = line['parent_record']
    _hash_record(parent)
    _same(digest(parent), line['parent_record_sha256'], 'PARENT_HASH')
    _same(parent['record_sha256'], line['parent_record_field_sha256'], 'PARENT_FIELD_HASH')
    _same(parent['sources'], line['original_sources'], 'OLD_SOURCES')
    _same(record['sources'], line['repaired_sources'], 'NEW_SOURCES')
    _differences(line['original_sources'], line['repaired_sources'], line['approved_changes'])
    _same(line['dependency_hashes'], dependencies, 'DEPENDENCIES')
    proof = line['original_replay_receipt']
    _same(proof, {'exact_match': True, 'record_sha256': digest(parent),
                 'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}, 'ORIGINAL_REPLAY_RECEIPT')
    _same(line['certification'], 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED', 'CERTIFICATION')
    _same(line['accepted_fact_finding_credit'], 0, 'FACT_FINDING_CREDIT')
    _same(line['final_evaluation_credit'], 0, 'FINAL_CREDIT')
    if not isinstance(line['repair_note'], str) or not line['repair_note'].strip():
        raise RuntimeHalt('REPAIR_NOTE_REQUIRED')
    _relationship(record, line)
    _verify_line(parent, dependencies)


def verify_repair_lineage(record, root):
    """Validate the embedded parent chain and its still-preserved command prefix."""
    try:
        _verify_line(record, _dependencies(Path(root).resolve(), record['context_file']))
    except (KeyError, TypeError, ValueError, OSError, RecursionError) as exc:
        raise RuntimeHalt('REPAIR_MALFORMED_LINEAGE: ' + str(exc)) from exc
    return {'lineage_valid': True, 'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}



def _current_source_worker(operation, root, payload):
    """Execute repaired operations from .py bytes in a fresh interpreter.

    Hashing disk alone cannot attest already-imported code or timestamp-valid
    caches. The source-only finder remains installed for dynamic handler imports.
    Workers never reuse caller module objects or recursively spawn themselves.
    """
    root = Path(root).resolve()
    code = """import sys,json,importlib.machinery
from pathlib import Path
root=Path(sys.argv[1]); source=str(root/'SOURCE')
class VerifiedSource(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)
sys.path_importer_cache[source]=importlib.machinery.FileFinder(source,
    (VerifiedSource, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0,source)
import fresh_repair_migration as migration
migration._SOURCE_ONLY_WORKER=True
import fresh_learning_campaign as runner
from context_runtime import RuntimeHalt
from interaction_learning import LearningState
operation=sys.argv[2]; data=json.load(sys.stdin)
def forbid_policy(*args,**kwargs):
    raise RuntimeHalt('REPAIR_POLICY_USE_FORBIDDEN')
try:
    if operation in ('migrate','replay'):
        # Guards live in the child; parent-process patches cannot enforce this.
        runner.LearningPlayerBot.__init__=forbid_policy
        runner.LearningPlayerBot.choose=forbid_policy
        runner.LearningPlayerBot.bottom_order=forbid_policy
    if operation=='migrate':
        result=migration.migrate_repaired_game(data['record'],root=root,
            original_source_root=Path(data['original_source_root']),
            approved_changes=data['approved_changes'],repair_note=data['repair_note'])
    elif operation=='replay':
        result=runner.replay_game(data['record'],root)
    elif operation=='resume':
        previous=data['previous_record']; history=previous['commands']
        if 'repair_lineage' not in previous:
            raise RuntimeHalt('REPAIR_WORKER_MIGRATED_RECORD_REQUIRED')
        if (data['max_commands']==1 and history
                and history[-1]['status']!='EXPERIMENTAL_RESOLVED'
                and history[-1]['command'] not in runner.GENERATORS):
            # A fully selected one-command retry consumes no new choice.
            runner.LearningPlayerBot.choose=forbid_policy
            runner.LearningPlayerBot.bottom_order=forbid_policy
        state=LearningState.from_dict(data['learning_state'])
        result=runner.run_game(data['index'],root,context_file=data['context_file'],
            campaign_id=data['campaign_id'],learning_state=state,
            max_commands=data['max_commands'],previous_record=previous,
            player_policy=data.get('player_policy','NAMED_LEGACY'),
            history_report=data.get('history_report'))
        runner._same(state.export(),data['learning_state'],'MODEL_MUTATION')
    else:
        raise RuntimeHalt('REPAIR_WORKER_OPERATION_INVALID')
    print(json.dumps({'result':result}))
except Exception as error:
    print(json.dumps({'error':str(error),'exception':type(error).__name__}))
"""
    try:
        done = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code, str(root), operation],
            input=canonical(payload), capture_output=True, timeout=120, check=False, cwd=root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeHalt('REPAIR_CURRENT_SOURCE_WORKER_FAILED: ' + str(exc)) from exc
    if done.returncode:
        raise RuntimeHalt('REPAIR_CURRENT_SOURCE_WORKER_FAILED: ' + done.stderr.decode(errors='replace')[-2000:])
    try:
        envelope = json.loads(done.stdout)
        if 'error' in envelope:
            raise RuntimeHalt(envelope['error'])
        return envelope['result']
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeHalt('REPAIR_CURRENT_SOURCE_WORKER_RESULT_INVALID') from exc


def _original_replay(record, original_root):
    # -I removes cwd/PYTHONPATH/user site influence. Only the verified original
    # SOURCE is added; the script imports no modules from the repaired tree.
    code = """import sys,json,importlib.machinery
from pathlib import Path
root=Path(sys.argv[1]); source=str(root/'SOURCE')
class VerifiedSource(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)
sys.path_importer_cache[source]=importlib.machinery.FileFinder(source,
    (VerifiedSource, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0,source)
from fresh_learning_campaign import replay_game
if (root/'SOURCE/fresh_repair_migration.py').is_file():
    import fresh_repair_migration
    fresh_repair_migration._SOURCE_ONLY_WORKER=True
from interaction_learning import LearningPlayerBot
from context_runtime import RuntimeHalt
def forbid_policy(*args,**kwargs):
    raise RuntimeHalt('REPAIR_POLICY_USE_FORBIDDEN')
LearningPlayerBot.__init__=forbid_policy
LearningPlayerBot.choose=forbid_policy
LearningPlayerBot.bottom_order=forbid_policy
print(json.dumps(replay_game(json.load(sys.stdin),root)))
"""
    try:
        done = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code, str(original_root)],
            input=canonical(record), capture_output=True, timeout=120, check=False,
            cwd=original_root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeHalt('REPAIR_ORIGINAL_REPLAY_FAILED: ' + str(exc)) from exc
    if done.returncode:
        raise RuntimeHalt('REPAIR_ORIGINAL_REPLAY_FAILED: ' + done.stderr.decode(errors='replace')[-2000:])
    try:
        proof = json.loads(done.stdout)
    except ValueError as exc:
        raise RuntimeHalt('REPAIR_ORIGINAL_REPLAY_RECEIPT_INVALID') from exc
    _same(proof, {'exact_match': True, 'record_sha256': digest(record),
                 'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}, 'ORIGINAL_REPLAY_RECEIPT')
    return proof


def migrate_repaired_game(record, *, root, original_source_root, approved_changes, repair_note):
    """Return an exact-prefix record under an explicitly approved repaired build.

    No writes, policy construction, choices, failed action application or model
    updates occur. Failed judge receipts remain original evidence in both records.
    """
    if not _SOURCE_ONLY_WORKER:
        return _current_source_worker('migrate', root, {'record': record,
            'original_source_root': str(Path(original_source_root).resolve()),
            'approved_changes': approved_changes, 'repair_note': repair_note})
    import fresh_learning_campaign as runner
    root, old_root = Path(root).resolve(), Path(original_source_root).resolve()
    parent = copy.deepcopy(record)
    try:
        _hash_record(parent)
        count = _boundary(parent)
        if not isinstance(repair_note, str) or not repair_note.strip():
            raise RuntimeHalt('REPAIR_NOTE_REQUIRED')
        before, after = runner._source_bytes(old_root), runner._sources(root)
        _same(parent['sources'], before, 'ORIGINAL_SOURCES')
        changes = _differences(before, after, approved_changes, bootstrap_sources=runner._LOADED_SOURCES)
        old_deps = _dependencies(old_root, parent['context_file'])
        dependencies = _dependencies(root, parent['context_file'])
        _same(old_deps, dependencies, 'DEPENDENCIES')
        proof = _original_replay(parent, old_root)
        _same(runner._source_bytes(old_root), before, 'ORIGINAL_SOURCES_AFTER_REPLAY')
        _same(_dependencies(old_root, parent['context_file']), old_deps, 'ORIGINAL_DEPENDENCIES_AFTER_REPLAY')
        context, context_file, context_hash = runner._load_context_selection(root, parent['context_file'])
        _same(context_hash, parent['context_file_sha256'], 'CONTEXT_BYTES')
        runtime = ContextRuntime(context, parent['seed'], parent['first'],
            runner.build_selected_registry(context, root), allow_experimental=True)
        initial = runtime.snapshot()
        _same(_snapshot(initial), _snapshot(parent['initial']), 'INITIAL')
        tracker = FieldTracker(context)
        tracker.start(initial)
        migrated = copy.deepcopy(parent)
        migrated.update({'sources': after, 'initial': initial, 'tracker': tracker.manifest()})
        commands = []
        for saved in parent['commands'][:count]:
            current = copy.deepcopy(saved)
            current['before'] = runtime.snapshot()
            _same(_snapshot(saved['before']), _snapshot(current['before']), 'PREFIX_BEFORE')
            _same(saved['public_view'], tracker.player_view(saved['seat']), 'PREFIX_VIEW')
            before_view, metrics = tracker.player_view(saved['seat']), tracker.public_metrics()
            result = runner._apply(runtime, saved['command'], saved['seat'], copy.deepcopy(saved['args']), root)
            _same(result, saved['result'], 'PREFIX_RESULT')
            current.update({'result': result, 'after': runtime.snapshot()})
            _same(_snapshot(current['after']), _snapshot(saved['after']), 'PREFIX_AFTER')
            current['judge'] = runner.judge_action(runtime, current['tracker_command'], current['before'],
                                                  current['after'], result, root=root, tracker=tracker)
            if current['judge'].get('accepted') is not True:
                raise RuntimeHalt('REPAIR_CURRENT_JUDGE_REJECTED')
            current['observation'] = tracker.observe(current['tracker_command'], current['before'],
                                                    current['after'], result, current['judge'])
            current['public_view_after'] = tracker.player_view(saved['seat'])
            current['rating'] = runner._rating(current, tracker, before_view, metrics, context)
            _same(_command(current), _command(saved), 'PREFIX_EVIDENCE')
            commands.append(current)
        _same(_snapshot(runtime.snapshot()), _snapshot(parent['final']), 'FINAL_STATE_RNG')
        if count < len(parent['commands']):
            failed = copy.deepcopy(parent['commands'][count])
            failed['before'] = failed['after'] = runtime.snapshot()
            commands.append(failed)
        # Preserve original HALT evidence, rebinding only its snapshot execution stamp.
        events = copy.deepcopy(runtime.events)
        old_events = parent['events']
        if old_events and old_events[-1].get('type') == 'HALT':
            tail = copy.deepcopy(old_events[-1])
            if 'before' in tail:
                tail['before'] = runtime.snapshot()
            if 'execution_id' in tail:
                tail['execution_id'] = runtime.execution_id
            events.append(tail)
        _same([_event(v) for v in events], [_event(v) for v in old_events], 'EVENTS')
        migrated.update({'commands': commands, 'events': events, 'final': runtime.snapshot(),
                         'tracker_observations': tracker.observations})
        line = {'schema': SCHEMA, 'parent_record': parent, 'parent_record_sha256': digest(parent),
            'parent_record_field_sha256': parent['record_sha256'], 'original_sources': before,
            'repaired_sources': after, 'dependency_hashes': dependencies, 'approved_changes': changes,
            'original_replay_receipt': proof, 'original_execution_id': parent['initial']['execution_id'],
            'repaired_execution_id': initial['execution_id'], 'successful_prefix_count': count,
            'failed_selection_sha256': digest(_selection(parent['commands'][count])) if count < len(parent['commands']) else None,
            'repair_note': repair_note, 'checkpoint_sha256': digest(_snapshot(parent['final'])),
            'engine_rng_sha256': digest(parent['final']['rng_state']), 'policy_rng_sha256': digest(parent['policy_rng_final']),
            'certification': 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED',
            'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0}
        if parent['tracker'] != migrated['tracker']:
            line.update({'original_tracker':parent['tracker'], 'repaired_tracker':migrated['tracker']})
        migrated['repair_lineage'] = {**line, 'lineage_sha256': digest(line)}
        migrated['record_sha256'] = digest({k: v for k, v in migrated.items() if k != 'record_sha256'})
        runner.replay_game(migrated, root)
        _same(runner._sources(root), after, 'CURRENT_SOURCES_AFTER_REPLAY')
        _same(runner._source_bytes(old_root), before, 'ORIGINAL_SOURCES_AFTER_VERIFICATION')
        _same(_dependencies(root, context_file), dependencies, 'CURRENT_DEPENDENCIES_AFTER_REPLAY')
        _same(_dependencies(old_root, context_file), old_deps, 'ORIGINAL_DEPENDENCIES_AFTER_VERIFICATION')
        return json.loads(canonical(migrated))
    except (KeyError, TypeError, ValueError, OSError, RecursionError) as exc:
        raise RuntimeHalt('REPAIR_MALFORMED_RECORD: ' + str(exc)) from exc
