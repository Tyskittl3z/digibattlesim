"""Fresh, bounded experimental games; no CLI or automatic cohort execution.

Snapshots and engine RNG are private audit evidence. Only Bot C projections and
explicit public decision metadata reach the separately seeded frozen policies.
"""
import copy
import hashlib
import json
from pathlib import Path
import random

from context_runtime import ContextRuntime, RuntimeHalt
from field_tracker import FieldTracker
from imported_attempts import (ROOT, _apply, _load_context_selection, breeding_candidates,
                               counter_options, main_candidates, pending_choice, pending_options)
from interaction_learning import LearningPlayerBot, LearningState, verify_decision_rng, verify_decision_input, learning_player_manifest
from board_text_player import BoardTextPlayerBot, board_text_player_manifest
from interaction_scoring import criteria_manifest, score_transition
from match_context import canonical, digest
from named_bot_continuation import _plain_block_options
from selected_mechanics import build_selected_registry


SCHEMA = 'fresh-learning-game-v1'
CONTEXT_FILE = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
GENERATORS = frozenset(('SELECT_NEXT_COMMAND', 'GENERATE_PENDING_CHOICES',
    'GENERATE_BREEDING_CHOICES', 'GENERATE_MAIN_CANDIDATES',
    'GENERATE_COUNTER_CHOICES', 'GENERATE_BLOCK_CHOICES'))
PROCEDURAL = frozenset(('BEGIN_PREPARATION', 'REDRAW_CHOICE', 'ADVANCE_PHASE',
    'FINISH_TURN', 'END_ATTACK', 'SETTLE_PENDING'))
from judge_ledger import judge_action


def _clone(value):
    return json.loads(canonical(value))


def _same(left, right, name):
    if canonical(left) != canonical(right):
        raise RuntimeHalt('FRESH_' + name + '_MISMATCH')


def make_schedule(context_id, campaign_id, count=60):
    if (not isinstance(context_id, str) or not context_id or not isinstance(campaign_id, str)
            or not campaign_id or type(count) is not int or count < 2 or count % 2):
        raise ValueError('Context, campaign and positive even schedule count required')
    manifest = {'schema': 'fresh-learning-schedule-v1', 'context_id': context_id,
        'campaign_id': campaign_id, 'count': count,
        'games': [{'index': i, 'seed': int(digest({'domain': 'fresh-learning-seed-v1',
            'context_id': context_id, 'campaign_id': campaign_id, 'index': i})[:16], 16),
            'first': 'A' if i % 2 == 0 else 'B'} for i in range(count)]}
    return {**manifest, 'schedule_sha256': digest(manifest)}


def _source_bytes(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / 'SOURCE').glob('*.py')) if not p.name.startswith('test_')}


_LOADED_SOURCES = _source_bytes(ROOT)


def _sources(root):
    value = _source_bytes(root)
    _same(value, _LOADED_SOURCES, 'LOADED_SOURCES')
    return value


def _policy_seeds(context_id, campaign_id, index, state_id):
    return {seat: int(digest({'domain': 'fresh-learning-policy-v1', 'context_id': context_id,
        'campaign_id': campaign_id, 'index': index, 'seat': seat,
        'input_state_id': state_id})[:16], 16) for seat in ('A', 'B')}


def _history_binding(root, player_policy, history_report):
    if player_policy not in ('NAMED_LEGACY', 'BOARD_TEXT_HISTORY'):
        raise ValueError('Unknown player policy')
    if player_policy == 'NAMED_LEGACY':
        if history_report is not None:
            raise ValueError('Legacy policy does not bind a match report')
        return None
    if history_report is None:
        return None
    path = (root / history_report).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise RuntimeHalt('FRESH_HISTORY_REPORT_MISSING')
    return {'file': str(path.relative_to(root)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _initial_rng(context_id, seat, seed, state_id):
    value = {'version': 1, 'context_id': context_id, 'seat': seat, 'policy_seed': seed,
             'input_state_id': state_id, 'state': _clone(random.Random(seed).getstate())}
    return {**value, 'rng_sha256': digest(value)}


def _prove_rng(command, current):
    """Prove saved draw transitions without constructing or choosing a policy."""
    _same(command.get('policy_rng_before_choice'), current, 'POLICY_CHAIN')
    for d in command.get('decisions', []):
        meta = d.get('learning', {})
        seat = meta.get('seat')
        if seat not in current:
            raise RuntimeHalt('FRESH_DECISION_SEAT_MISMATCH')
        _same(meta.get('rng_before'), current[seat], 'DECISION_RNG_BEFORE')
        try:
            after_rng = verify_decision_rng(d, current[seat])
        except (RuntimeHalt, ValueError, TypeError, KeyError) as exc:
            raise RuntimeHalt('FRESH_DECISION_RNG_MISMATCH: ' + str(exc)) from exc
        _same(after_rng, meta.get('rng_after'), 'DECISION_RNG_TRANSITION')
        current[seat] = copy.deepcopy(meta['rng_after'])
    _same(command.get('policy_rng_after_choice'), current, 'POLICY_CHAIN_AFTER')



def _bind_choices(command, tracker, context, pilots):
    """Bind saved learning evidence to its actual view and selected command."""
    for decision in command['decisions']:
        seat = decision.get('learning', {}).get('seat')
        if seat != command['seat']:
            raise RuntimeHalt('FRESH_DECISION_ACTOR_MISMATCH')
        try:
            verify_decision_input(decision, tracker.player_view(seat), context, pilots[seat])
        except (RuntimeHalt, TypeError, ValueError, KeyError) as exc:
            raise RuntimeHalt('FRESH_DECISION_INPUT_MISMATCH: ' + str(exc)) from exc
        if 'public_metrics' in decision['decision']:
            _same(decision['decision']['public_metrics'], tracker.public_metrics(), 'DECISION_METRICS')
    decisions = command['decisions']
    if not decisions:
        return
    kind, args = command['command'], command.get('args', {})
    direct = {'REDRAW_CHOICE', 'BREEDING_CHOICE', 'COUNTER_CHOICE', 'BLOCK_CHOICE',
              'PLAY_CARD', 'USE_OPTION', 'OPTION_DELAY', 'BATTLE_EVOLUTION',
              'BREEDING_EVOLUTION', 'PASS_TURN', 'DECLARE_ATTACK',
              'UNKNOWN_OPTION_ACTION', 'UNKNOWN_DELAY_ACTION', 'UNKNOWN_BATTLE_EVOLUTION'}
    if kind in direct:
        _same(decisions[-1]['chosen'], args, 'SELECTED_ARGUMENTS')
    if 'selected_pending' in command:
        selected = command['selected_pending']
        public = {k: v for k, v in selected.items() if k not in ('trigger', 'usage')}
        _same(decisions[0]['chosen'], public, 'SELECTED_PENDING')
        actual = next((p for p in command['before']['state']['pending'] if p['id'] == selected['id']), None)
        _same(actual, selected, 'SELECTED_PENDING_STATE')
        if kind == 'RESOLVE_PENDING':
            _same(args.get('pending_id'), selected['id'], 'PENDING_ARGUMENT')
            values = decisions[1:]
            if values and values[-1]['decision']['kind'] == 'BOTTOM_ORDER':
                value = values[-2]['chosen'] if len(values) > 1 else None
                expected = ({'activate': True, 'bottom_order': values[-1]['chosen']}
                            if value is True else {'selected': value, 'bottom_order': values[-1]['chosen']})
            else:
                expected = values[-1]['chosen'] if values else None
            _same(args.get('choice'), expected, 'PENDING_VALUE')


def _rating(command, tracker, before_view, metrics, context):
    rating = score_transition(before_view, tracker.player_view(command['seat']), command['seat'],
        command={k: command[k] for k in ('command', 'seat', 'status')}, result=command['result'], context=context,
        public_metrics_before=metrics, public_metrics_after=tracker.public_metrics())
    rating['learning_eligible'] = (command['command'] not in PROCEDURAL
        and any(d.get('learning', {}).get('eligible_choice', False) for d in command['decisions']))
    return rating


def _resolve_decisions(command):
    eligible = command['rating'].get('learning_eligible', False)
    for decision in command['decisions']:
        decision.update({'status': 'EXPERIMENTAL_RESOLVED', 'reward': command['rating']['reward'],
            'learning_eligible': bool(eligible and decision['learning'].get('eligible_choice', False))})


def _revalidate(record, root, context, context_file, context_hash, learning_input, schedule, sources,
                player_policy='NAMED_LEGACY', history_binding=None):
    """Replay saved successes and prove the complete audit checkpoint first."""
    _same(record.get('record_sha256'), digest({k: v for k, v in record.items() if k != 'record_sha256'}), 'RECORD_HASH')
    if 'repair_lineage' in record:
        from fresh_repair_migration import verify_repair_lineage
        verify_repair_lineage(record, root)
    if record.get('schema') != SCHEMA:
        raise RuntimeHalt('FRESH_SCHEMA_MISMATCH')
    for key, value in {'context_id': context.matchup_id, 'context_file': context_file,
        'context_file_sha256': context_hash, 'schedule': schedule, 'sources': sources,
        'criteria': criteria_manifest(), 'certification': 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED',
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
        'learning_state_before': learning_input,
        'learning_state_after': learning_input, 'learning_state_id': LearningState.from_dict(learning_input).state_id}.items():
        _same(record.get(key), value, key.upper())
    _same(record.get('player_policy', 'NAMED_LEGACY'), player_policy, 'PLAYER_POLICY')
    _same(record.get('history_report'), history_binding, 'HISTORY_REPORT')
    game = schedule['games'][record['index']]
    for key in ('index', 'seed', 'first'):
        _same(record.get(key), game[key], key.upper())
    _same(record.get('campaign_id'), schedule['campaign_id'], 'CAMPAIGN')
    model_id = LearningState.from_dict(learning_input).state_id
    seeds = _policy_seeds(context.matchup_id, schedule['campaign_id'], game['index'], model_id)
    rng = {s: _initial_rng(context.matchup_id, s, seeds[s], model_id) for s in seeds}
    _same(record.get('policy_rng_initial'), rng, 'INITIAL_POLICY_RNG')
    report_sha = history_binding['sha256'] if history_binding else None
    expected_pilots = {s: (board_text_player_manifest(context, s, model_id, seeds[s], report_sha)
        if player_policy == 'BOARD_TEXT_HISTORY' else learning_player_manifest(context, s, model_id, seeds[s]))
        for s in seeds}
    _same(record.get('pilots'), expected_pilots, 'PILOTS')
    runtime = ContextRuntime(context, game['seed'], game['first'], build_selected_registry(context, root),
                             allow_experimental=True)
    initial = runtime.snapshot()
    _same(record.get('initial'), initial, 'INITIAL')
    tracker = FieldTracker(context)
    tracker.start(initial)
    _same(record.get('tracker'), tracker.manifest(), 'TRACKER_MANIFEST')
    commands = record.get('commands')
    if not isinstance(commands, list):
        raise RuntimeHalt('FRESH_COMMANDS_MISMATCH')
    for i, saved in enumerate(commands):
        _prove_rng(saved, rng)
        _same(saved.get('before'), runtime.snapshot(), 'PREFIX_BEFORE')
        _same(saved.get('public_view'), tracker.player_view(saved['seat']), 'PREFIX_VIEW')
        _bind_choices(saved, tracker, context, record['pilots'])
        if saved.get('status') != 'EXPERIMENTAL_RESOLVED':
            if i != len(commands) - 1 or record.get('status') not in ('HALT', 'DIAGNOSTIC_SOFTWARE_ERROR'):
                raise RuntimeHalt('FRESH_FAILURE_POSITION_MISMATCH')
            _same(saved.get('after'), runtime.snapshot(), 'FAILED_STATE')
            continue
        before_view, metrics = tracker.player_view(saved['seat']), tracker.public_metrics()
        result = _apply(runtime, saved['command'], saved['seat'], copy.deepcopy(saved['args']), root)
        _same(result, saved.get('result'), 'PREFIX_RESULT')
        _same(runtime.snapshot(), saved.get('after'), 'PREFIX_AFTER')
        judge = judge_action(runtime, saved['tracker_command'], saved['before'], saved['after'], result, root=root, tracker=tracker)
        post_failure = record.get('status') == 'JUDGE_AUDIT_FAILURE' and i == len(commands) - 1
        if post_failure and not saved.get('observation'):
            break  # Failed post-commit guard is preserved, never rolled back.
        _same(judge, saved.get('judge'), 'PREFIX_JUDGE')
        observation = tracker.observe(saved['tracker_command'], saved['before'], saved['after'], result, judge)
        _same(observation, saved.get('observation'), 'PREFIX_OBSERVATION')
        _same(tracker.player_view(saved['seat']), saved.get('public_view_after'), 'PREFIX_AFTER_VIEW')
        if post_failure:
            break
        _same(_rating(saved, tracker, before_view, metrics, context), saved.get('rating'), 'PREFIX_RATING')
        resolved = copy.deepcopy(saved)
        _resolve_decisions(resolved)
        _same(resolved['decisions'], saved['decisions'], 'DECISION_RESOLUTION')
    _same(runtime.snapshot(), record.get('final'), 'FINAL_STATE_RNG')
    events = record.get('events', [])
    if commands and commands[-1].get('status') != 'EXPERIMENTAL_RESOLVED':
        _same(events[:len(runtime.events)], runtime.events, 'EVENTS_PREFIX')
        tail = events[len(runtime.events):]
        if len(tail) > 1:
            raise RuntimeHalt('FRESH_FAILED_EVENTS_MISMATCH')
        if tail:
            event = tail[0]
            for key, value in {'type': 'HALT', 'before': commands[-1]['before'],
                    'reason': commands[-1]['reason'], 'seed': runtime.seed,
                    'context_id': context.matchup_id}.items():
                _same(event.get(key), value, 'FAILED_EVENT_' + key.upper())
    else:
        _same(runtime.events, events, 'EVENTS')
    _same(tracker.observations, record.get('tracker_observations'), 'TRACKER_OBSERVATIONS')
    _same(rng, record.get('policy_rng_final'), 'FINAL_POLICY_RNG')
    _same(record.get('winner'), runtime.state.winner, 'WINNER')
    _same(record.get('terminal_reason'), runtime.state.terminal_reason, 'TERMINAL_REASON')
    if record.get('status') == 'EXPERIMENTAL_SOFTWARE_TERMINAL':
        _same(runtime.state.terminal, True, 'TERMINAL_STATUS')
    elif record.get('status') == 'PAUSED':
        _same(runtime.state.terminal, False, 'PAUSED_STATUS')
    elif record.get('status') not in ('HALT', 'DIAGNOSTIC_SOFTWARE_ERROR', 'JUDGE_AUDIT_FAILURE'):
        raise RuntimeHalt('FRESH_STATUS_MISMATCH')
    return runtime, tracker, initial


class _Adapter:
    """Reuse pending schemas while replacing their player input with Bot C."""
    def __init__(self, choose, bot, tracker, selected, cached=()):
        self.choose_policy, self.bot, self.tracker = choose, bot, tracker
        self.selected, self.cached = selected, list(copy.deepcopy(cached))

    def choose(self, _engine_view, candidates):
        decision = {'kind': 'PENDING_CHOICE', 'selected_pending': {k: v for k, v in self.selected.items() if k not in ('trigger', 'usage')},
                    'effect_id': self.selected['effect_id'], 'source': self.selected['source']}
        if self.cached:
            saved = self.cached.pop(0)
            _same(saved['candidates'], candidates, 'SAVED_PENDING_CANDIDATES')
            _same(saved['decision'], {**decision, 'public_metrics': self.tracker.public_metrics()},
                  'SAVED_PENDING_METADATA')
            return copy.deepcopy(saved['chosen'])
        return self.choose_policy(self.bot.seat, candidates, decision)

    def bottom_order(self, remainder):
        if self.cached:
            saved = self.cached.pop(0)
            _same(saved['candidates'], remainder, 'SAVED_BOTTOM_CANDIDATES')
            return copy.deepcopy(saved['chosen'])
        return self.bot.bottom_order(copy.deepcopy(remainder), public_view=self.tracker.player_view(self.bot.seat))


def run_game(index, root=ROOT, *, context_file=CONTEXT_FILE, campaign_id,
             learning_state, max_commands=2000, previous_record=None,
             player_policy='NAMED_LEGACY', history_report=None):
    """Run a bounded private/authorized game segment; never update the model."""
    if type(index) is not int or index < 0 or index >= 60:
        raise ValueError('Schedule index 0..59 required')
    if type(max_commands) is not int or max_commands < 1:
        raise ValueError('Positive command budget required')
    root = Path(root).resolve()
    history_binding = _history_binding(root, player_policy, history_report)
    if previous_record is not None and 'repair_lineage' in previous_record:
        from fresh_repair_migration import _SOURCE_ONLY_WORKER, _current_source_worker
        if not _SOURCE_ONLY_WORKER:
            frozen = _clone(learning_state.export())
            result = _current_source_worker('resume', root, {'index': index,
                'context_file': str(context_file), 'campaign_id': campaign_id,
                'learning_state': frozen, 'max_commands': max_commands,
                'previous_record': previous_record, 'player_policy': player_policy,
                'history_report': history_report})
            _same(learning_state.export(), frozen, 'MODEL_MUTATION')
            return result
    context, context_file, context_hash = _load_context_selection(root, context_file)
    schedule, sources = make_schedule(context.matchup_id, campaign_id), _sources(root)
    frozen = _clone(learning_state.export())
    if player_policy == 'BOARD_TEXT_HISTORY' and history_binding is None:
        if index != 0 or LearningState.from_dict(frozen)._games:
            raise RuntimeHalt('FRESH_NO_HISTORY_IS_GAME_ONE')
    state_id, game = LearningState.from_dict(frozen).state_id, schedule['games'][index]
    seeds = _policy_seeds(context.matchup_id, campaign_id, index, state_id)
    initial_rng = {s: _initial_rng(context.matchup_id, s, seeds[s], state_id) for s in seeds}
    previous, retry = _clone(previous_record), None
    if previous is not None:
        _same(previous.get('index'), index, 'INDEX')
        runtime, tracker, initial = _revalidate(previous, root, context, context_file, context_hash,
                                                frozen, schedule, sources, player_policy, history_binding)
        if previous['status'] not in ('PAUSED', 'HALT', 'DIAGNOSTIC_SOFTWARE_ERROR') or runtime.state.terminal:
            raise RuntimeHalt('FRESH_RESUMABLE_STATUS_MISMATCH')
        history = copy.deepcopy(previous['commands'])
        if history and history[-1]['status'] != 'EXPERIMENTAL_RESOLVED':
            retry = history.pop()
        final_rng = previous['policy_rng_final']
    else:
        runtime = ContextRuntime(context, game['seed'], game['first'], build_selected_registry(context, root),
                                 allow_experimental=True)
        initial = runtime.snapshot()
        tracker = FieldTracker(context)
        tracker.start(initial)
        history, final_rng = [], initial_rng
    # No player exists until replay, input/model and engine/policy RNG proofs pass.
    bots = {s: (BoardTextPlayerBot(context, s, LearningState.from_dict(frozen), seeds[s],
                                  history_binding['sha256'] if history_binding else None)
                if player_policy == 'BOARD_TEXT_HISTORY' else
                LearningPlayerBot(context, s, LearningState.from_dict(frozen), seeds[s])) for s in seeds}
    for seat, bot in bots.items():
        bot.restore_rng(final_rng[seat])
    manifests = {s: bot.manifest() for s, bot in bots.items()}
    if previous is not None:
        _same(previous.get('pilots'), manifests, 'PILOTS')
    offsets = {s: 0 for s in bots}
    current, status, reason, used = None, 'PAUSED', None, 0

    def rng():
        return {s: bot.export_rng() for s, bot in bots.items()}

    def collect():
        for seat, bot in bots.items():
            current['decisions'].extend(copy.deepcopy(bot.decision_log[offsets[seat]:]))
            offsets[seat] = len(bot.decision_log)
        current['policy_rng_after_choice'] = rng()

    def choose(seat, candidates, decision):
        decision = {**copy.deepcopy(decision), 'public_metrics': tracker.public_metrics()}
        chosen = bots[seat].choose(tracker.player_view(seat), copy.deepcopy(candidates), decision=decision)
        collect()
        if not any(canonical(chosen) == canonical(c) for c in candidates):
            raise RuntimeHalt('FRESH_NONCANDIDATE_MISMATCH')
        return copy.deepcopy(chosen)

    def start(kind, seat):
        return {'command': kind, 'seat': seat, 'public_view': tracker.player_view(seat),
            'before': runtime.snapshot(), 'decisions': [], 'policy_rng_before_choice': rng(),
            'policy_rng_after_choice': rng()}

    def call(kind, seat, args=None):
        nonlocal used
        current.update({'command': kind, 'seat': seat, 'args': copy.deepcopy(args or {}),
                        'public_view': tracker.player_view(seat)})
        collect()
        history.append(current)  # Selection, exact arguments and post-choice RNG precede mutation.
        used += 1
        before_view, metrics = tracker.player_view(seat), tracker.public_metrics()
        result = _apply(runtime, kind, seat, copy.deepcopy(current['args']), root)
        current.update({'status': 'EXPERIMENTAL_RESOLVED', 'result': copy.deepcopy(result),
                        'after': runtime.snapshot(), 'rating': {'status': 'UNRATED'}})
        current['tracker_command'] = {k: copy.deepcopy(current[k]) for k in ('command', 'seat', 'args', 'status')}
        current['judge'] = judge_action(runtime, current['tracker_command'], current['before'], current['after'], result, root=root, tracker=tracker)
        if current['judge'].get('accepted') is not True:
            raise RuntimeHalt('FRESH_POST_APPLY_JUDGE_AUDIT: ' + str(current['judge'].get('reason')))
        current['observation'] = tracker.observe(current['tracker_command'], current['before'],
            current['after'], result, current['judge'])
        current['public_view_after'] = tracker.player_view(seat)
        current['rating'] = _rating(current, tracker, before_view, metrics, context)
        _resolve_decisions(current)

    def resolve_pending(selected, owner, cached=()):
        options = pending_options(runtime, owner)
        if selected not in options:
            raise RuntimeHalt('FRESH_SELECTED_PENDING_MISMATCH')
        adapter = _Adapter(choose, bots[owner], tracker, selected, cached)
        value = pending_choice(runtime, owner, selected, adapter)
        if adapter.cached:
            raise RuntimeHalt('FRESH_UNUSED_PENDING_SELECTION_MISMATCH')
        collect()
        call('RESOLVE_PENDING', owner, {'pending_id': selected['id'], 'choice': value})

    try:
        if retry is not None and (retry['command'] not in GENERATORS or retry.get('selected_pending')):
            current = {k: copy.deepcopy(v) for k, v in retry.items()
                       if k not in ('status', 'reason', 'exception', 'result', 'judge', 'rating', 'after')}
            for d in current['decisions']:
                for key in ('status', 'reward', 'rating', 'learning_eligible'):
                    d.pop(key, None)
            if retry['command'] == 'GENERATE_PENDING_CHOICES':
                resolve_pending(retry['selected_pending'], retry['seat'], retry['decisions'][1:])
            else:
                call(retry['command'], retry['seat'], retry['args'])
        while not runtime.state.terminal and used < max_commands:
            seat = runtime.state.active
            view = tracker.player_view(seat)
            current = start('SELECT_NEXT_COMMAND', seat)
            if view['phase'] == 'SCENARIO':
                call('BEGIN_PREPARATION', game['first'])
            elif view['phase'] == 'INITIAL_HANDS':
                owner = game['first'] if not runtime.state.preparation['choices'] else ('B' if game['first'] == 'A' else 'A')
                current = start('REDRAW_CHOICE', owner)
                chosen = choose(owner, [{'redraw': False}, {'redraw': True}], {'kind': 'REDRAW_CHOICE'})
                call('REDRAW_CHOICE', owner, chosen)
            elif runtime.state.pending and (not runtime.state.attack or any(
                    pending_options(runtime, owner) for owner in bots)):
                current['command'] = 'GENERATE_PENDING_CHOICES'
                options = {s: pending_options(runtime, s) for s in bots}
                owner = next((s for s in bots if options[s]), None)
                if owner is None:
                    call('SETTLE_PENDING', seat)
                else:
                    current = start('GENERATE_PENDING_CHOICES', owner)
                    current['pending_candidates'] = copy.deepcopy(options[owner])
                    public_options = [{k: v for k, v in option.items() if k not in ('trigger', 'usage')}
                                      for option in options[owner]]
                    selected_public = choose(owner, public_options, {'kind': 'PENDING_EFFECT_ORDER'})
                    selected = next(option for option in options[owner] if option['id'] == selected_public['id'])
                    current['selected_pending'] = selected
                    resolve_pending(selected, owner)
            elif view['attack']:
                attack, window = view['attack'], view['attack']['window']
                if window in ('COUNTER', 'BLOCK'):
                    owner = attack['defender']
                    current = start('GENERATE_' + window + '_CHOICES', owner)
                    options = counter_options(runtime, owner) if window == 'COUNTER' else _plain_block_options(runtime, owner)
                    chosen = choose(owner, options, {'kind': window + '_CHOICE'})
                    call(window + '_CHOICE', owner, chosen)
                elif window in ('CONFIRM', 'END'):
                    call(window + '_ATTACK', attack['controller'])
                else:
                    raise RuntimeHalt('FRESH_ATTACK_WINDOW_UNSUPPORTED: ' + str(window))
            elif view['phase'] in ('BREEDING', 'MAIN'):
                breeding = view['phase'] == 'BREEDING'
                current['command'] = 'GENERATE_BREEDING_CHOICES' if breeding else 'GENERATE_MAIN_CANDIDATES'
                options = breeding_candidates(context, view, seat) if breeding else main_candidates(runtime, seat, root)
                chosen = choose(seat, options, {'kind': 'BREEDING_ACTION' if breeding else 'MAIN_ACTION'})
                call('BREEDING_CHOICE' if breeding else chosen['kind'], seat, chosen)
            else:
                call('FINISH_TURN' if view['phase'] == 'END_OF_TURN' else 'ADVANCE_PHASE', seat)
        runtime.verify()
        if runtime.state.terminal:
            status = 'EXPERIMENTAL_SOFTWARE_TERMINAL'
    except Exception as exc:
        reason = str(exc)
        collect()
        current['after'] = runtime.snapshot()
        current['rating'] = {'status': 'UNRATED', 'learning_eligible': False}
        if current.get('status') == 'EXPERIMENTAL_RESOLVED' or current['after'] != current['before']:
            status = 'JUDGE_AUDIT_FAILURE'
            current['audit_failure'] = {'reason': reason, 'exception': type(exc).__name__}
        else:
            status = 'HALT' if isinstance(exc, RuntimeHalt) else 'DIAGNOSTIC_SOFTWARE_ERROR'
            current.update({'status': status, 'reason': reason, 'exception': type(exc).__name__})
            current['judge'] = judge_action(runtime, current, current['before'], current['after'], None, exc, root=root, tracker=tracker)
        if not history or history[-1] is not current:
            history.append(current)
    _same(learning_state.export(), frozen, 'MODEL_MUTATION')
    record = {'schema': SCHEMA, **game, 'campaign_id': campaign_id, 'context_id': context.matchup_id,
        'player_policy': player_policy, 'history_report': history_binding,
        'context_file': context_file, 'context_file_sha256': context_hash, 'schedule': schedule,
        'sources': sources, 'criteria': criteria_manifest(), 'learning_state_id': state_id,
        'learning_state_before': frozen, 'learning_state_after': frozen,
        'pilots': manifests, 'policy_rng_initial': initial_rng, 'policy_rng_final': rng(),
        'tracker': tracker.manifest(), 'tracker_observations': tracker.observations,
        'status': status, 'halt_reason': reason, 'commands': history, 'events': runtime.events,
        'initial': initial, 'final': runtime.snapshot(), 'winner': runtime.state.winner,
        'terminal_reason': runtime.state.terminal_reason, 'max_commands': max_commands,
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
        'certification': 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED'}
    if previous is not None and 'repair_lineage' in previous:
        record['repair_lineage'] = copy.deepcopy(previous['repair_lineage'])
    return _clone({**record, 'record_sha256': digest(record)})


def replay_game(record, root=ROOT):
    """Read-only replay of saved commands; never invoke a player policy."""
    root = Path(root).resolve()
    if 'repair_lineage' in record:
        from fresh_repair_migration import _SOURCE_ONLY_WORKER, _current_source_worker
        if not _SOURCE_ONLY_WORKER:
            return _current_source_worker('replay', root, {'record': record})
    context, context_file, context_hash = _load_context_selection(root, record['context_file'])
    schedule = make_schedule(context.matchup_id, record['campaign_id'])
    player_policy = record.get('player_policy', 'NAMED_LEGACY')
    history = record.get('history_report')
    history_binding = _history_binding(root, player_policy, history['file'] if history else None)
    _revalidate(record, root, context, context_file, context_hash,
                record['learning_state_before'], schedule, _sources(root), player_policy, history_binding)
    return {'exact_match': True, 'record_sha256': digest(record),
            'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}


def commit_completed_game(record, learning_state, root=ROOT):
    """Explicit between-game update, with a stable ID independent of log repair.

    The returned receipt carries the whole-record hash separately. No caller
    inside this module invokes this function or starts the next scheduled game.
    """
    if (record.get('schema') != SCHEMA or record.get('status') != 'EXPERIMENTAL_SOFTWARE_TERMINAL'
            or record.get('winner') not in ('A', 'B') or not record.get('terminal_reason')
            or record.get('final', {}).get('state', {}).get('terminal') is not True
            or record['final']['state'].get('winner') != record['winner']
            or record['final']['state'].get('terminal_reason') != record['terminal_reason']
            or not record.get('commands')):
        raise RuntimeHalt('FRESH_COMPLETED_GAME_REQUIRED')
    decisions = []
    for command in record['commands']:
        if (command.get('status') != 'EXPERIMENTAL_RESOLVED'
                or command.get('judge', {}).get('accepted') is not True
                or command['judge'].get('status') != 'RUNTIME_VALIDATED'
                or command.get('rating', {}).get('status') == 'UNRATED'
                or 'audit_failure' in command):
            raise RuntimeHalt('FRESH_COMPLETED_ACCEPTED_COMMANDS_REQUIRED')
        for decision in command.get('decisions', []):
            if (decision.get('status') != 'EXPERIMENTAL_RESOLVED'
                    or type(decision.get('learning_eligible')) is not bool
                    or decision.get('learning', {}).get('input_state_id') != record['learning_state_id']):
                raise RuntimeHalt('FRESH_COMPLETED_DECISION_MISMATCH')
            decisions.append(copy.deepcopy(decision))
    proof = replay_game(record, root)
    if proof.get('exact_match') is not True:
        raise RuntimeHalt('FRESH_COMPLETED_REPLAY_MISMATCH')
    game_id = digest({k: record[k] for k in ('campaign_id', 'context_id', 'index', 'seed')})
    model = learning_state.export()
    if game_id not in model['games']:
        _same(model, record['learning_state_before'], 'COMMIT_MODEL_INPUT')
    updated = learning_state.update_completed(game_id, record['winner'], decisions, eligible=True)
    return {'schema': 'fresh-learning-commit-v1', 'game_id': game_id, 'updated': updated,
            'record_sha256': digest(record), 'learning_state_id': learning_state.state_id,
            'certification': 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED'}
