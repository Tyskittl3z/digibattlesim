"""Live selected-pair diagnostics, with fresh random pilots and zero match credit.

Unknown choices stop their original seed. Software terminals and exact replay
never establish judge certification, fact-finding eligibility, or final results.
"""
import argparse
from collections import Counter
import copy
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import random

from attack_flow import (counter_options, declare_attack, choose_counter, choose_blocker,
                         confirm_attack, end_attack)
from battlefield_scope import assert_basic_board_scope
from breeding_evolution import breeding_evolution_choices, choose_breeding_evolution
from context_evolution import printed_evolution_options, UnsupportedEvolutionCondition
from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
from main_actions import choose_play
from match_context import canonical, digest
from match_preparation import begin_preparation, choose_redraw
from matchup_readiness import load_context_file, load_context_bytes
from phase_flow import advance_phase, choose_breeding_action
from search_effects import SEARCH_SPECS, search_choices
from selected_mechanics import build_selected_registry, INHERITED_REACTIONS, PHASE_EFFECTS
from turn_flow import pass_turn, finish_turn


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FILE = 'ARTIFACTS/ex13-engine-2026-10-30/context.json'
POLICY = 'fresh-untrained-uniform-random-reference-v1'


def seed_for(index, context_id):
    if type(index) is not int or index < 0:
        raise ValueError('Nonnegative attempt index required')
    return int(digest({'domain': 'imported-live-diagnostic-v1',
                       'context_id': context_id, 'index': index})[:16], 16)


def _number(key):
    return key.split(':', 1)[1].split('#', 1)[0]


class ReferencePilot:
    """A new policy instance per attempt/seat; no runtime or audit-state input."""
    def __init__(self, context_id, index, seat, *, policy_segment=None):
        if seat not in ('A', 'B'):
            raise ValueError('Pilot seat required')
        self.seat = seat
        self._identity = {'policy': POLICY, 'context_id': context_id,
                          'attempt_index': index, 'seat': seat,
                          'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        if policy_segment is not None:
            self._identity['policy_segment'] = copy.deepcopy(policy_segment)
        self._seed = int(digest({'domain': 'pilot-rng', **self._identity})[:16], 16)
        self.rng = random.Random(self._seed)

    def manifest(self):
        return {**self._identity, 'pilot_id': digest(self._identity),
                'pilot_seed': self._seed,
                'strategy_status': 'FRESH_UNTRAINED_RANDOM_REFERENCE',
                'training_data': [], 'roadmap': None,
                'information_policy': 'PUBLIC_VIEW_OWN_HAND_AND_EXPLICIT_REVEALS_ONLY'}

    def choose(self, public_view, candidates):
        # The only state accepted by the policy is the requesting seat's view.
        if not isinstance(public_view['players'][self.seat]['hand'], list):
            raise RuntimeHalt('PILOT_OWN_PUBLIC_VIEW_REQUIRED')
        other = 'B' if self.seat == 'A' else 'A'
        if not isinstance(public_view['players'][other]['hand'], dict):
            raise RuntimeHalt('PILOT_OPPONENT_HAND_MUST_BE_HIDDEN')
        if not candidates:
            raise RuntimeHalt('PILOT_EMPTY_CANDIDATES')
        return copy.deepcopy(candidates[self.rng.randrange(len(candidates))])

    def bottom_order(self, revealed_remainder):
        ordered = list(revealed_remainder)
        self.rng.shuffle(ordered)
        return ordered


def breeding_candidates(context, view, seat):
    own = view['players'][seat]
    choices = [{'kind': 'BREEDING_CHOICE', 'action': 'skip'}]
    if not own['breeding']:
        if own['eggdeck']['count']:
            choices.append({'kind': 'BREEDING_CHOICE', 'action': 'hatch'})
    else:
        card = context.card(seat, _number(own['breeding'][-1])).to_dict()
        if card['type'] == 'Digimon' and type(card['level']) is int and card['level'] >= 3:
            # Promotion effects are deliberately left for the transactional API
            # to reject. A pilot never filters this choice by software support.
            choices.append({'kind': 'BREEDING_CHOICE', 'action': 'promote'})
    return choices


def main_candidates(runtime, seat, root=ROOT):
    """Printed-payable plays/evolutions plus supported plain attacks.

    Printed affordability is not complete legality. No hand card is excluded
    because the selected mechanic pack lacks its effect implementation.
    """
    view = runtime.public_view(seat)
    if (view['active'] != seat or view['phase'] != 'MAIN'
            or view['memory'] < 0 or view['terminal']):
        raise RuntimeHalt('DIAGNOSTIC_MAIN_WINDOW_REQUIRED')
    own = view['players'][seat]
    other = 'B' if seat == 'A' else 'A'
    choices = [{'kind': 'PASS_TURN'}]
    for key in own['hand']:
        card = runtime.context.card(seat, _number(key)).to_dict()
        cost = card['play_cost']
        if type(cost) is not int or cost < 0 or cost > view['memory'] + 10:
            continue
        if card['type'] in ('Digimon', 'Tamer'):
            choices.append({'kind': 'PLAY_CARD', 'hand_key': key, 'printed_cost': cost,
                            'legality': 'PRINTED_PAYABLE_NOT_FULL_LEGALITY'})
        elif card['type'] == 'Option':
            from option_actions import OPTION_SPECS, option_colors_met
            known=card['card_number'] in OPTION_SPECS
            if known and not option_colors_met(runtime,seat,runtime.context.card(seat,card['card_number'])):
                continue
            choices.append({'kind': 'USE_OPTION' if known else 'UNKNOWN_OPTION_ACTION', 'hand_key': key,
                            'printed_cost': cost, 'legality': 'UNVERIFIED_OPTION_ACTION'})
    # Generate possible actions first; validate the chosen action at its actual
    # timing. An unimplemented attack must not block choosing to play or pass.
    if own['breeding']:
        source=own['breeding'][-1]
        for target in own['hand']:
            routes=printed_evolution_options(runtime.context,seat,_number(source),_number(target))
            for route_index,route in enumerate(routes):
                if route.cost<=view['memory']+10:
                    choices.append({'kind':'BREEDING_EVOLUTION','source_key':source,'hand_key':target,
                                    'route_index':route_index,**asdict(route),
                                    'legality':'PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY'})
    for stack in own['battle'].values():
        source = stack['cards'][-1]
        if runtime.context.card(seat,_number(source)).kind=='Option':
            from option_actions import OPTION_SPECS
            if (_number(source) in OPTION_SPECS
                    and (stack['played_turn'] is None or stack['played_turn']<view['turn'])):
                choices.append({'kind':'UNKNOWN_DELAY_ACTION','source_key':source,
                    'legality':'DELAY_TIMING_CANDIDATE_NOT_FULL_EFFECT_LEGALITY'})
        if runtime.context.card(seat, _number(source)).kind != 'Digimon':
            continue
        for target in own['hand']:
            try:
                routes = printed_evolution_options(runtime.context, seat, _number(source), _number(target))
            except UnsupportedEvolutionCondition as exc:
                raise RuntimeHalt('PRINTED_BATTLE_EVOLUTION_ROUTE_UNSUPPORTED: source=' + source
                                  + ' target=' + target + ' ' + str(exc)) from exc
            for route_index, route in enumerate(routes):
                if route.cost <= view['memory'] + 10:
                    choices.append({'kind': 'BATTLE_EVOLUTION', 'source_key': source,
                                    'hand_key': target, 'route_index': route_index, **asdict(route),
                                    'legality': 'PRINTED_CANDIDATE_NOT_FULL_ACTION_LEGALITY'})
    targets = ['PLAYER'] + [key for key, stack in view['players'][other]['battle'].items()
                            if stack['suspended']]
    for key, stack in own['battle'].items():
        card = runtime.context.card(seat, _number(stack['cards'][-1]))
        if (card.kind != 'Digimon' or stack['suspended']
                or stack['played_turn'] == view['turn']):
            continue
        ready = stack['ready_since_turn']
        if ready is None and stack['played_turn'] is None:
            raise RuntimeHalt('ATTACK_HISTORY_UNVERIFIED: ' + key)
        if ready is not None and ready > view['turn']:
            continue
        choices.extend({'kind': 'DECLARE_ATTACK', 'attacker': key, 'target': target}
                       for target in targets)
    return choices


def pending_choice(runtime, seat, selected, pilot):
    """Only explicit known choice schemas; searches expose their own reveals."""
    effect = selected['effect_id']
    view = runtime.public_view(seat)
    unsuspend = {spec[0] for number, spec in INHERITED_REACTIONS.items()
                 if number in ('EX13-022', 'BT22-023')}
    memory = ({spec[0] for number, spec in INHERITED_REACTIONS.items()
               if number in ('P-138', 'EX1-013')}
              | {spec[0] for spec in PHASE_EFFECTS.values()})
    if effect in unsuspend:
        return pilot.choose(view, [False, True])
    if effect in memory:
        return None
    from on_play_effects import ON_PLAY_SPECS, on_play_choices
    if effect in {spec[0] for spec in ON_PLAY_SPECS.values()}:
        return pilot.choose(view, on_play_choices(runtime, seat, selected['source']))
    from option_actions import OPTION_SPECS, option_choices
    if effect in {spec[0] for spec in OPTION_SPECS.values()}:
        exposed=option_choices(runtime,seat,selected['source'])
        chosen=pilot.choose(view,exposed['selections'])
        remainder=[key for key in exposed['revealed'] if key not in chosen]
        return {'selected':chosen,'bottom_order':pilot.bottom_order(remainder)}
    from aero_effects import PLAY_EFFECT,DIGIVOLVE_EFFECT,END_EFFECT,aero_choices
    if effect in (PLAY_EFFECT,DIGIVOLVE_EFFECT,END_EFFECT):
        return pilot.choose(view,aero_choices(runtime,seat,selected['source'],effect))
    from tamer_play_effects import PLAY_EFFECT, OBSERVER_EFFECT, tamer_play_choices
    if effect in (PLAY_EFFECT, OBSERVER_EFFECT):
        return pilot.choose(view, tamer_play_choices(runtime, seat, selected['source'], effect))
    if effect in {spec[0] for spec in SEARCH_SPECS.values()}:
        exposed = search_choices(runtime, seat, selected['source'])
        chosen = pilot.choose(view, exposed['selections'])
        remainder = [key for key in exposed['revealed'] if key not in chosen]
        return {'selected': chosen, 'bottom_order': pilot.bottom_order(remainder)}
    raise RuntimeHalt('PENDING_EFFECT_CHOICE_UNSUPPORTED: ' + effect)


def _apply(runtime, kind, seat, args, root):
    if kind == 'BEGIN_PREPARATION':
        return begin_preparation(runtime, root)
    if kind == 'REDRAW_CHOICE':
        return choose_redraw(runtime, seat, args['redraw'], root)
    if kind == 'ADVANCE_PHASE':
        return advance_phase(runtime, seat, root)
    if kind == 'BREEDING_CHOICE':
        return choose_breeding_action(runtime, seat, args['action'], root)
    if kind == 'PLAY_CARD':
        return choose_play(runtime, seat, args['hand_key'], root)
    if kind == 'USE_OPTION':
        from option_actions import choose_use_option
        return choose_use_option(runtime,seat,args['hand_key'],root)
    if kind == 'UNKNOWN_OPTION_ACTION':
        raise RuntimeHalt('UNKNOWN_OPTION_ACTION: ' + args['hand_key']
                          + ' OPTION_LEGALITY_AND_EFFECT_UNVERIFIED')
    if kind == 'UNKNOWN_DELAY_ACTION':
        raise RuntimeHalt('DELAY_EFFECT_UNIMPLEMENTED: '+args['source_key'])
    if kind == 'BREEDING_EVOLUTION':
        return choose_breeding_evolution(runtime, seat, args['hand_key'], args['route_index'], root)
    if kind == 'BATTLE_EVOLUTION':
        from battle_evolution import choose_battle_evolution
        return choose_battle_evolution(runtime,seat,args['source_key'],args['hand_key'],args['route_index'],root)
    if kind == 'UNKNOWN_BATTLE_EVOLUTION':
        raise RuntimeHalt('BATTLE_EVOLUTION_UNIMPLEMENTED: source=' + args['source_key']
                          + ' target=' + args['hand_key'] + ' route_index=' + str(args['route_index'])
                          + ' cost=' + str(args['cost']))
    if kind == 'PASS_TURN':
        return pass_turn(runtime, seat, root)
    if kind == 'FINISH_TURN':
        return finish_turn(runtime, seat, root)
    if kind == 'DECLARE_ATTACK':
        return declare_attack(runtime, seat, args['attacker'], args['target'], root)
    if kind == 'COUNTER_CHOICE':
        if args['card'] is not None:
            raise RuntimeHalt('COUNTER_LEGALITY_UNVERIFIED: ' + args['card'])
        return choose_counter(runtime, seat, None, root)
    if kind == 'BLOCK_CHOICE':
        return choose_blocker(runtime, seat, args['card'], root)
    if kind == 'CONFIRM_ATTACK':
        return confirm_attack(runtime, seat, root)
    if kind == 'END_ATTACK':
        return end_attack(runtime, seat, root)
    if kind == 'RESOLVE_PENDING':
        return resolve_pending(runtime, seat, args['pending_id'], args['choice'])
    if kind == 'SETTLE_PENDING':
        return runtime.settle_pending()
    raise RuntimeHalt('DIAGNOSTIC_COMMAND_UNSUPPORTED: ' + kind)


def _context_path(root, context_file):
    """Normalize a contained input path; a path itself grants no capability."""
    path = (root / Path(context_file)).resolve()
    if not path.is_relative_to(root):
        raise RuntimeHalt('CONTEXT_PATH_OUTSIDE_ROOT')
    return path, path.relative_to(root).as_posix()


def _load_context_selection(root, context_file, *, expected_context=None):
    from selected_contexts import require_selected_context

    path, relative = _context_path(root, context_file)
    body = path.read_bytes()
    body_sha256 = hashlib.sha256(body).hexdigest()
    if expected_context is not None and body_sha256 != expected_context[1]:
        raise RuntimeHalt('REPLAY_CONTEXT_FILE_CHANGED')
    context = load_context_bytes(body)
    if expected_context is not None and context.matchup_id != expected_context[0]:
        raise RuntimeHalt('REPLAY_CONTEXT_ID_MISMATCH')
    require_selected_context(context, root)
    return context, relative, body_sha256


def _physical_snapshot(snapshot):
    """Compare physical state/RNG across engine revisions, retaining all fields.

    execution_id identifies the deliberately changed software, not game state.
    The sole legacy state migration is the new, initially empty Option slot.
    """
    value = copy.deepcopy(snapshot)
    if not isinstance(value, dict) or not isinstance(value.get('state'), dict):
        raise RuntimeHalt('CONTINUATION_PHYSICAL_SNAPSHOT_INVALID')
    value.pop('execution_id', None)
    value['state'].setdefault('resolving_option', None)
    return value


def _comparable_public_view(view):
    value = copy.deepcopy(view)
    if not isinstance(value, dict):
        raise RuntimeHalt('CONTINUATION_PREFIX_PUBLIC_VIEW_INVALID')
    value.setdefault('resolving_option', None)
    return value


def _saved_context_inputs(record, root):
    provenance = record.get('replay_provenance', {})
    if not isinstance(provenance, dict):
        raise RuntimeHalt('REPLAY_CONTEXT_PROVENANCE_INVALID')
    path, context_file = _context_path(root, provenance.get('context_file', CONTEXT_FILE))
    expected_sha256 = provenance.get('context_file_sha256')
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(c not in '0123456789abcdef' for c in expected_sha256)):
        raise RuntimeHalt('REPLAY_CONTEXT_PROVENANCE_INVALID')
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected_sha256:
        raise RuntimeHalt('REPLAY_CONTEXT_FILE_CHANGED')
    if load_context_bytes(body).matchup_id != record.get('context_id'):
        raise RuntimeHalt('REPLAY_CONTEXT_ID_MISMATCH')
    return context_file, expected_sha256


def _verify_previous_record_hash(record):
    lineage = record.get('continuation_provenance')
    if lineage is not None:
        if (not isinstance(lineage, dict) or not isinstance(lineage.get('previous_record'), dict)
                or digest(lineage['previous_record']) != lineage.get('previous_record_sha256')):
            raise RuntimeHalt('CONTINUATION_PREVIOUS_RECORD_HASH_MISMATCH')
        _verify_previous_record_hash(lineage['previous_record'])


def continue_attempt(previous_record, root=ROOT, max_commands=2000):
    """Revalidate a saved HALT's decisions, then continue the same physical game.

    This discovery-only operation retains the predecessor and its identities.
    A fresh, explicitly seeded policy segment makes decisions only after the
    recorded prefix; neither policy receives snapshots or hidden audit data.
    """
    if type(max_commands) is not int or max_commands < 1:
        raise ValueError('Positive command budget required')
    root = Path(root).resolve()
    previous = json.loads(canonical(previous_record))
    _verify_previous_record_hash(previous)
    context_file, context_sha256 = _saved_context_inputs(previous, root)
    commands = previous.get('commands')
    if (previous.get('status') not in ('HALT', 'DIAGNOSTIC_SOFTWARE_ERROR')
            or not isinstance(commands, list) or not commands
            or any(command.get('status') != 'EXPERIMENTAL_RESOLVED' for command in commands[:-1])
            or commands[-1].get('status') != previous['status']):
        raise RuntimeHalt('CONTINUATION_HALTED_PREFIX_REQUIRED')
    if len(commands) > max_commands:
        raise ValueError('Continuation command budget must exceed the successful prefix')
    if (type(previous.get('index')) is not int or previous['index'] < 0
            or type(previous.get('seed')) is not int or previous['seed'] < 0
            or previous.get('first') not in ('A', 'B')):
        raise RuntimeHalt('CONTINUATION_ORIGINAL_GAME_INPUTS_INVALID')
    halts = previous.get('halts')
    if not isinstance(halts, list) or not halts or not isinstance(halts[-1].get('before'), dict):
        raise RuntimeHalt('CONTINUATION_BEFORE_HALT_REQUIRED')
    before = _physical_snapshot(halts[-1]['before'])
    if (canonical(before) != canonical(_physical_snapshot(previous.get('final')))
            or before.get('context_id') != previous['context_id']
            or before.get('seed') != previous['seed'] or before.get('first') != previous['first']
            or before['state'].get('terminal')):
        raise RuntimeHalt('CONTINUATION_ORIGINAL_CHECKPOINT_INVALID')
    return run_attempt(previous['index'], root, max_commands, context_file=context_file,
                       _expected_context=(previous['context_id'], context_sha256),
                       _previous_record=previous)


def run_attempt(index, root=ROOT, max_commands=300, *, context_file=CONTEXT_FILE,
                _expected_context=None, _previous_record=None):
    if type(max_commands) is not int or max_commands < 1:
        raise ValueError('Positive command budget required')
    root = Path(root).resolve()
    context, context_file, context_file_sha256 = _load_context_selection(
        root, context_file, expected_context=_expected_context)
    seed = seed_for(index, context.matchup_id) if _previous_record is None else _previous_record['seed']
    first = ('A' if index % 2 == 0 else 'B') if _previous_record is None else _previous_record['first']
    runtime = ContextRuntime(context, seed, first, build_selected_registry(context, root),
                             allow_experimental=True)
    previous_hash = digest(_previous_record) if _previous_record is not None else None
    segment = None if _previous_record is None else {
        'kind': 'FRESH_POLICY_AFTER_REVALIDATED_PREFIX',
        'previous_record_sha256': previous_hash,
        'context_id': context.matchup_id, 'attempt_index': index,
        'seed_derivation': 'SHA256(pilot-rng,current-policy-identity,previous-record-sha256)[:16]'}
    pilots = {seat: ReferencePilot(context.matchup_id, index, seat, policy_segment=segment)
              for seat in ('A', 'B')}
    initial = runtime.snapshot()  # Audit only: never supplied to either pilot.
    commands = []
    current = None
    redraw_count = 0
    status = 'HALT'
    halt_reason = None
    continuation = None

    def call(kind, seat, args=None, candidates=None, *, decision_origin=None, recorded_pilot_id=None):
        nonlocal current
        current = {'command': kind, 'seat': seat, 'args': copy.deepcopy(args or {}),
                   'public_view': runtime.public_view(seat)}
        if candidates is not None:
            current['candidates'] = copy.deepcopy(candidates)
            current['pilot_id'] = recorded_pilot_id or pilots[seat].manifest()['pilot_id']
        if decision_origin is not None:
            current['decision_origin'] = copy.deepcopy(decision_origin)
        commands.append(current)
        result = _apply(runtime, kind, seat, current['args'], root)
        current['status'] = 'EXPERIMENTAL_RESOLVED'
        current['result'] = copy.deepcopy(result)

    retry = None
    if _previous_record is not None:
        if canonical(_physical_snapshot(initial)) != canonical(_physical_snapshot(_previous_record['initial'])):
            raise RuntimeHalt('CONTINUATION_INITIAL_PHYSICAL_MISMATCH')
        for command_index, saved in enumerate(_previous_record['commands'][:-1]):
            seat = saved.get('seat')
            if seat not in pilots or canonical(_comparable_public_view(saved.get('public_view'))) != canonical(
                    _comparable_public_view(runtime.public_view(seat))):
                raise RuntimeHalt('CONTINUATION_PREFIX_PUBLIC_VIEW_MISMATCH: command=' + str(command_index))
            origin = {'kind': 'REVALIDATED_SAVED_COMMAND', 'previous_record_sha256': previous_hash,
                      'previous_command_index': command_index, 'previous_command_sha256': digest(saved),
                      'candidates_origin': 'SAVED_DECISION_CONTEXT'}
            try:
                call(saved['command'], seat, saved['args'], saved.get('candidates'),
                     decision_origin=origin, recorded_pilot_id=saved.get('pilot_id'))
            except Exception as exc:
                raise RuntimeHalt('CONTINUATION_PREFIX_ACTION_FAILED: command=' + str(command_index)
                                  + ' ' + str(exc)) from exc
            redraw_count += saved['command'] == 'REDRAW_CHOICE'
        original_before = _physical_snapshot(_previous_record['halts'][-1]['before'])
        revalidated_before = _physical_snapshot(runtime.snapshot())
        if canonical(original_before) != canonical(revalidated_before):
            raise RuntimeHalt('CONTINUATION_BEFORE_HALT_PHYSICAL_MISMATCH')
        failed = _previous_record['commands'][-1]
        if 'public_view' in failed and canonical(_comparable_public_view(failed['public_view'])) != canonical(
                _comparable_public_view(runtime.public_view(failed['seat']))):
            raise RuntimeHalt('CONTINUATION_FAILED_ACTION_PUBLIC_VIEW_MISMATCH')
        generators = {'SELECT_NEXT_COMMAND', 'GENERATE_MAIN_CANDIDATES', 'GENERATE_PENDING_CHOICES',
                      'GENERATE_COUNTER_CHOICES', 'COMMAND_BUDGET'}
        retry = None if failed['command'] in generators and 'selected_pending' not in failed else failed
        continuation = {
            'schema': 'imported-live-game-continuation-v1',
            'previous_record_sha256': previous_hash, 'previous_record': copy.deepcopy(_previous_record),
            'previous_execution_id': _previous_record['replay_provenance']['execution_id'],
            'previous_runner_sha256': _previous_record['replay_provenance']['runner_sha256'],
            'previous_pilots': copy.deepcopy(_previous_record['pilots']),
            'successful_commands_revalidated': len(commands),
            'physical_state_proof': {
                'comparison': 'ALL_SNAPSHOT_FIELDS_EXCEPT_EXECUTION_ID',
                'legacy_defaults': {'state.resolving_option': None},
                'original_before_sha256': digest(original_before),
                'revalidated_before_sha256': digest(revalidated_before),
                'original_rng_sha256': digest(original_before['rng_state']),
                'revalidated_rng_sha256': digest(revalidated_before['rng_state'])},
            'retry': {'kind': 'RESUME_GENERATOR_WINDOW' if retry is None else 'RETRY_SAVED_SELECTION',
                      'previous_command_index': len(commands), 'original_command': failed['command']},
            'policy_segment': {'first_new_decision_command_index': len(commands) + (
                                   retry is not None and retry['command'] != 'GENERATE_PENDING_CHOICES'),
                               'pilots': {seat: pilots[seat].manifest() for seat in pilots}},
            'certification': 'NONE_REVALIDATION_IS_SOFTWARE_EVIDENCE_ONLY',
            'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0}

    try:
        if retry is not None:
            kind, seat, args = retry['command'], retry['seat'], copy.deepcopy(retry.get('args', {}))
            candidates = retry.get('candidates')
            if kind == 'UNKNOWN_OPTION_ACTION':
                from option_actions import OPTION_SPECS
                if _number(args['hand_key']) in OPTION_SPECS:
                    kind = 'USE_OPTION'
            elif kind == 'UNKNOWN_BATTLE_EVOLUTION':
                kind = 'BATTLE_EVOLUTION'
            elif kind == 'GENERATE_PENDING_CHOICES':
                current = copy.deepcopy(retry)
                selected = retry['selected_pending']
                candidates = pending_options(runtime, seat)
                if selected not in candidates:
                    raise RuntimeHalt('CONTINUATION_SELECTED_PENDING_NO_LONGER_AVAILABLE')
                kind = 'RESOLVE_PENDING'
                args = {'pending_id': selected['id'],
                        'choice': pending_choice(runtime, seat, selected, pilots[seat])}
            continuation['retry']['current_command'] = kind
            call(kind, seat, args, candidates,
                 decision_origin={'kind': 'RETRIED_SAVED_SELECTION', 'previous_record_sha256': previous_hash,
                                  'previous_command_index': len(commands),
                                  'original_command': retry['command'],
                                  'candidates_origin': ('CURRENT_PENDING_WINDOW' if retry['command'] ==
                                                        'GENERATE_PENDING_CHOICES' else 'SAVED_DECISION_CONTEXT')},
                 recorded_pilot_id=retry.get('pilot_id'))
        while not runtime.public_view(first)['terminal']:
            if len(commands) >= max_commands:
                current = {'command': 'COMMAND_BUDGET', 'max_commands': max_commands}
                raise RuntimeHalt('DIAGNOSTIC_COMMAND_LIMIT: ' + str(max_commands))
            active_view = runtime.public_view(first)
            seat = active_view['active']
            view = runtime.public_view(seat)
            current = {'command': 'SELECT_NEXT_COMMAND', 'seat': seat, 'public_view': view}
            if view['phase'] == 'SCENARIO':
                call('BEGIN_PREPARATION', first)
            elif view['phase'] == 'INITIAL_HANDS':
                owner = first if redraw_count == 0 else ('B' if first == 'A' else 'A')
                candidates = [{'redraw': False}, {'redraw': True}]
                choice = pilots[owner].choose(runtime.public_view(owner), candidates)
                call('REDRAW_CHOICE', owner, choice, candidates)
                redraw_count += 1
            elif runtime.state.pending:  # Scheduler routing, not pilot input.
                current['command'] = 'GENERATE_PENDING_CHOICES'
                options = {owner: pending_options(runtime, owner) for owner in ('A', 'B')}
                owner = next((owner for owner in ('A', 'B') if options[owner]), None)
                if owner is None:
                    call('SETTLE_PENDING', seat)
                else:
                    selected = pilots[owner].choose(runtime.public_view(owner), options[owner])
                    current.update({'seat': owner, 'public_view': runtime.public_view(owner),
                                    'pending_candidates': options[owner], 'selected_pending': selected})
                    choice = pending_choice(runtime, owner, selected, pilots[owner])
                    call('RESOLVE_PENDING', owner, {'pending_id': selected['id'], 'choice': choice},
                         options[owner])
            elif view['attack']:
                attack = view['attack']
                window = attack['window']
                if window == 'COUNTER':
                    owner = attack['defender']
                    current.update({'command': 'GENERATE_COUNTER_CHOICES', 'seat': owner,
                                    'public_view': runtime.public_view(owner)})
                    options = counter_options(runtime, owner)
                    choice = pilots[owner].choose(runtime.public_view(owner), options)
                    call('COUNTER_CHOICE', owner, choice, options)
                elif window == 'BLOCK':
                    owner = attack['defender']
                    options = [{'card': None, 'status': 'EXPLICIT_NO_BLOCK_IN_PLAIN_SCOPE'}]
                    choice = pilots[owner].choose(runtime.public_view(owner), options)
                    call('BLOCK_CHOICE', owner, choice, options)
                elif window == 'CONFIRM':
                    call('CONFIRM_ATTACK', attack['controller'])
                elif window == 'END':
                    call('END_ATTACK', attack['controller'])
                else:
                    raise RuntimeHalt('DIAGNOSTIC_ATTACK_WINDOW_UNSUPPORTED: ' + str(window))
            elif view['phase'] == 'BREEDING':
                options = breeding_candidates(context, view, seat)
                choice = pilots[seat].choose(view, options)
                call('BREEDING_CHOICE', seat, choice, options)
            elif view['phase'] == 'MAIN':
                current['command'] = 'GENERATE_MAIN_CANDIDATES'
                options = main_candidates(runtime, seat, root)
                choice = pilots[seat].choose(view, options)
                call(choice['kind'], seat, choice, options)
            elif view['phase'] == 'END_OF_TURN':
                call('FINISH_TURN', seat)
            else:
                call('ADVANCE_PHASE', seat)
        runtime.verify()
        status = 'EXPERIMENTAL_SOFTWARE_TERMINAL'
    except Exception as exc:
        halt_reason = str(exc)
        status = 'HALT' if isinstance(exc, RuntimeHalt) else 'DIAGNOSTIC_SOFTWARE_ERROR'
        if current is None:
            current = {'command': 'DIAGNOSTIC_INITIALIZATION'}
        current.update({'status': status, 'reason': halt_reason, 'exception': type(exc).__name__})
        if not commands or commands[-1] is not current:
            commands.append(current)
        # Engine failures already contain their transactional before snapshot.
        # Generator/unknown-action failures need an equally explicit halt event.
        if not runtime.events or runtime.events[-1].get('type') != 'HALT':
            runtime.events.append({'type': 'HALT', 'status': 'HALT', 'seed': seed, 'first': first,
                                   'context_id': context.matchup_id,
                                   'command': copy.deepcopy(current), 'reason': halt_reason,
                                   'exception': type(exc).__name__, 'before': runtime.snapshot()})
        runtime.halted = True
    final = runtime.snapshot()  # Audit only.
    provenance = {'context_file': context_file,
                  'context_file_sha256': context_file_sha256,
                  'execution_id': runtime.execution_id,
                  'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'seed_schedule': 'SHA256(context_id,index,imported-live-diagnostic-v1)[:16]',
                  'replay_method': 'RERUN_SAME_INDEX_INPUTS_AND_COMPARE_ENTIRE_RECORD',
                  'certification': 'NONE_EXACT_REPLAY_IS_SOFTWARE_EVIDENCE_ONLY'}
    record = {
        'schema': 'imported-live-diagnostic-attempt-v1', 'index': index,
        'context_id': context.matchup_id, 'seed': seed, 'first': first,
        'max_commands': max_commands, 'status': status,
        'certification': 'EXPERIMENTAL_UNREVIEWED',
        'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
        'pilot_id': {seat: pilots[seat].manifest()['pilot_id'] for seat in ('A', 'B')},
        'pilots': {seat: pilots[seat].manifest() for seat in ('A', 'B')},
        'winner': runtime.state.winner if status == 'EXPERIMENTAL_SOFTWARE_TERMINAL' else None,
        'terminal_reason': runtime.state.terminal_reason,
        'halt_reason': halt_reason, 'commands': commands, 'events': runtime.events,
        'halts': [event for event in runtime.events if event.get('type') == 'HALT'],
        'initial': initial, 'final': final, 'replay_provenance': provenance}
    if continuation is not None:
        provenance['replay_method'] = 'REVALIDATE_SAVED_PREFIX_RUN_EXPLICIT_POLICY_SEGMENT_COMPARE_ENTIRE_RECORD'
        record['continuation_provenance'] = continuation
    return json.loads(canonical(record))


def replay_attempt(record, root=ROOT):
    root = Path(root).resolve()
    context_file, expected_sha256 = _saved_context_inputs(record, root)
    _verify_previous_record_hash(record)
    # Legacy records without a saved path use the original default only. A
    # matching context ID is still required before any gameplay can rerun.
    if 'continuation_provenance' in record:
        previous = record['continuation_provenance']['previous_record']
        if (previous['context_id'] != record['context_id'] or previous['seed'] != record['seed']
                or previous['first'] != record['first'] or previous['index'] != record['index']):
            raise RuntimeHalt('CONTINUATION_ORIGINAL_GAME_INPUTS_MISMATCH')
        replay = continue_attempt(previous, root, record['max_commands'])
    else:
        replay = run_attempt(record['index'], root, record['max_commands'], context_file=context_file,
                             _expected_context=(record['context_id'], expected_sha256))
    return {'index': record['index'], 'exact_match': canonical(record) == canonical(replay),
            'saved_record_sha256': digest(record), 'replayed_record_sha256': digest(replay),
            'certification': 'NONE_SOFTWARE_REPLAY_ONLY'}


def write_attempts(out, root=ROOT, count=60, max_commands=300, *, context_file=CONTEXT_FILE):
    if type(count) is not int or count < 2 or count % 2:
        raise ValueError('Positive even attempt count of at least two required for balanced starts')
    if type(max_commands) is not int or max_commands < 1:
        raise ValueError('Positive command budget required')
    root = Path(root).resolve()
    context, context_file, context_file_sha256 = _load_context_selection(root, context_file)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    replays = []
    for index in range(count):
        record = run_attempt(index, root, max_commands, context_file=context_file,
                             _expected_context=(context.matchup_id, context_file_sha256))
        body = canonical(record) + b'\n'
        name = f'attempt-{index:04d}.json.gz'
        with (out / name).open('xb') as handle:
            with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as compressed:
                compressed.write(body)
        # Preserve the actual attempted seed and trace BEFORE any replay can
        # fail or be interrupted. A failed verification never replaces a seed.
        try:
            if (record['context_id'] != context.matchup_id
                    or record['replay_provenance']['context_file_sha256'] != context_file_sha256):
                raise RuntimeHalt('COHORT_CONTEXT_CHANGED')
            replay = replay_attempt(record, root)
            if not replay['exact_match']:
                raise RuntimeHalt('EXACT_REPLAY_MISMATCH: index=' + str(index))
        except Exception as exc:
            failure={'status':'REPLAY_FAILED_OR_INTERRUPTED','index':index,'seed':record['seed'],
                     'first':record['first'],'original_file':name,'record_sha256':digest(record),
                     'exception':type(exc).__name__,'reason':str(exc),'accepted_fact_finding_credit':0}
            with (out/f'replay-failure-{index:04d}.json').open('x',encoding='utf-8') as handle:
                json.dump(failure,handle,indent=2,sort_keys=True,allow_nan=False)
                handle.write('\n')
            raise
        rows.append({'index': index, 'seed': record['seed'], 'first': record['first'],
                     'status': record['status'], 'winner': record['winner'],
                     'halt_reason': record['halt_reason'], 'file': name,
                     'record_sha256': digest(record)})
        replays.append(replay)
    summary = {'schema': 'imported-live-diagnostic-summary-v1',
               'status': 'DIAGNOSTIC_ONLY', 'attempted_seeds': len(rows),
               'first_counts': dict(sorted(Counter(row['first'] for row in rows).items())),
               'status_counts': dict(sorted(Counter(row['status'] for row in rows).items())),
               'software_terminal_attempts': sum(row['status'] == 'EXPERIMENTAL_SOFTWARE_TERMINAL'
                                                 for row in rows),
               'experimental_terminal_winner_counts': dict(sorted(Counter(
                   row['winner'] for row in rows if row['winner'] is not None).items())),
               'halt_reason_counts': dict(sorted(Counter(
                   row['halt_reason'] for row in rows if row['halt_reason']).items())),
               'judge_certified_matches': 0, 'accepted_fact_finding_credit': 0,
               'final_evaluation_credit': 0,
               'exact_replay_matches': sum(replay['exact_match'] for replay in replays),
               'certification': 'NONE_SOFTWARE_REPLAY_ONLY',
               'attempts': rows, 'replays': replays}
    with (out / 'summary.json').open('x', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='New evidence directory; never overwritten')
    parser.add_argument('--count', type=int, default=60)
    parser.add_argument('--max-commands', type=int, default=300)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--context-file', type=Path, default=CONTEXT_FILE,
                        help='Saved context under --root; defaults to the original pairing')
    args = parser.parse_args(argv)
    try:
        summary = write_attempts(args.out, args.root, args.count, args.max_commands,
                                 context_file=args.context_file)
    except (OSError, ValueError, RuntimeHalt) as exc:
        print(json.dumps({'status': 'DIAGNOSTIC_OUTPUT_ERROR', 'reason': str(exc)}))
        return 2
    print(json.dumps({key: value for key, value in summary.items()
                      if key not in ('attempts', 'replays')}, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
