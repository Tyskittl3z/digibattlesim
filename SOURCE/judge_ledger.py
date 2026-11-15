"""Receipts for engine transactions, official source pins and physical audits.

These are experimental automated checks. Source hashes and a passing engine
transaction do not independently certify a card implementation or a whole game.
"""
from collections import Counter
import copy
import hashlib
from pathlib import Path
import re

from context_runtime import OfficialEvidence, RuntimeHalt
from field_tracker import FieldTracker
from match_context import canonical, digest
from match_preparation import _rules


ROOT = Path(__file__).resolve().parents[1]
_SEATS = ('A', 'B')
_PHYSICAL = re.compile(r'([AB]):([A-Z][A-Z0-9]*-\d+)#[1-9]\d*\Z')
JUDGE_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_ROUTE_META = {'kind', 'legality', 'cost', 'basis', 'printed_condition', 'definition_sha256', 'status'}
_ARGUMENTS = {
    'BEGIN_PREPARATION': (set(), set()), 'REDRAW_CHOICE': ({'redraw'}, set()),
    'ADVANCE_PHASE': (set(), set()), 'BREEDING_CHOICE': ({'action'}, {'kind'}),
    'PLAY_CARD': ({'hand_key'}, {'kind', 'legality', 'printed_cost'}),
    'USE_OPTION': ({'hand_key'}, {'kind', 'legality', 'printed_cost'}),
    'OPTION_DELAY': ({'source_key'}, {'kind', 'legality'}),
    'BATTLE_EVOLUTION': ({'source_key', 'hand_key', 'route_index'}, _ROUTE_META),
    'BREEDING_EVOLUTION': ({'hand_key', 'route_index'}, _ROUTE_META | {'source_key'}),
    'PASS_TURN': (set(), {'kind'}), 'FINISH_TURN': (set(), set()),
    'DECLARE_ATTACK': ({'attacker', 'target'}, {'kind'}),
    'COUNTER_CHOICE': ({'card'}, {'status'}), 'BLOCK_CHOICE': ({'card'}, {'status'}),
    'CONFIRM_ATTACK': (set(), set()), 'END_ATTACK': (set(), set()),
    'SETTLE_PENDING': (set(), set()), 'RESOLVE_PENDING': ({'pending_id', 'choice'}, set()),
}


def _same(left, right):
    return canonical(left) == canonical(right)


def _physical(snapshot):
    value = copy.deepcopy(snapshot)
    value.pop('execution_id', None)
    value['state'].setdefault('resolving_option', None)
    return value


def _audit_cards(context, snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('context_id') != context.matchup_id:
        raise RuntimeHalt('JUDGE_CONTEXT_MISMATCH')
    state = snapshot.get('state')
    if not isinstance(state, dict):
        raise RuntimeHalt('JUDGE_STATE_SCHEMA_INVALID')
    for name in ('zones', 'battle', 'breeding'):
        if not isinstance(state.get(name), dict) or set(state[name]) != set(_SEATS):
            raise RuntimeHalt('JUDGE_PHYSICAL_AREA_SCHEMA_INVALID')
    observed = {seat: [] for seat in _SEATS}
    for seat in _SEATS:
        zones = state['zones'][seat]
        if (not isinstance(zones, dict)
                or set(zones) != {'deck', 'eggdeck', 'hand', 'security', 'trash'}):
            raise RuntimeHalt('JUDGE_PHYSICAL_ZONE_SCHEMA_INVALID')
        for cards in zones.values():
            if not isinstance(cards, list):
                raise RuntimeHalt('JUDGE_PHYSICAL_CARD_LIST_REQUIRED')
            observed[seat].extend(cards)
        if not isinstance(state['breeding'][seat], list) or not isinstance(state['battle'][seat], dict):
            raise RuntimeHalt('JUDGE_PHYSICAL_FIELD_SCHEMA_INVALID')
        observed[seat].extend(state['breeding'][seat])
        for anchor, stack in state['battle'][seat].items():
            if (not isinstance(stack, dict) or not isinstance(stack.get('cards'), list)
                    or not stack['cards'] or stack['cards'][-1] != anchor):
                raise RuntimeHalt('JUDGE_PHYSICAL_STACK_INVALID')
            observed[seat].extend(stack['cards'])
    resolving = state.get('resolving_option')
    if resolving is not None:
        if (not isinstance(resolving, dict) or set(resolving) != {'seat', 'stack'}
                or resolving['seat'] not in _SEATS or not isinstance(resolving['stack'], dict)
                or not isinstance(resolving['stack'].get('cards'), list)
                or len(resolving['stack']['cards']) != 1):
            raise RuntimeHalt('JUDGE_RESOLVING_OPTION_INVALID')
        observed[resolving['seat']].extend(resolving['stack']['cards'])
    count = 0
    for seat in _SEATS:
        expected = Counter(f'{seat}:{number}#{index}' for number, index in context.inventory(seat))
        if any(not isinstance(key, str) for key in observed[seat]) or Counter(observed[seat]) != expected:
            raise RuntimeHalt('JUDGE_PHYSICAL_CONSERVATION_FAILED: ' + seat)
        count += len(observed[seat])
    return count


def _references(value):
    if isinstance(value, str) and _PHYSICAL.fullmatch(value):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _references(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _references(item)


def _engine_event(runtime, command, before, result):
    if not runtime.events:
        raise RuntimeHalt('JUDGE_ENGINE_EVENT_REQUIRED')
    event = runtime.events[-1]
    kind, seat, args = command['command'], command['seat'], command.get('args', {})
    if kind not in _ARGUMENTS or not isinstance(args, dict):
        raise RuntimeHalt('JUDGE_COMMAND_ARGUMENTS_INVALID')
    required, metadata = _ARGUMENTS[kind]
    if not required <= set(args) or set(args) - required - metadata:
        raise RuntimeHalt('JUDGE_COMMAND_ARGUMENTS_INVALID')
    if 'kind' in args and args['kind'] != kind:
        raise RuntimeHalt('JUDGE_COMMAND_KIND_MISMATCH')
    if event.get('seat') != seat or not _same(event.get('result'), result):
        raise RuntimeHalt('JUDGE_ENGINE_RESULT_MISMATCH')
    binding = None
    if kind == 'RESOLVE_PENDING':
        selected = next((item for item in before['state'].get('pending', [])
                         if item.get('id') == args.get('pending_id')), None)
        if (selected is None or event.get('type') != 'MECHANIC_RESOLVED'
                or event.get('pending_id') != selected['id']
                or event.get('source') != selected['source']
                or event.get('effect_id') != selected['effect_id']
                or event.get('field') != selected['field']
                or not _same(event.get('choice'), args.get('choice'))):
            raise RuntimeHalt('JUDGE_PENDING_EVENT_MISMATCH')
        match = _PHYSICAL.fullmatch(selected['source'])
        if match is None or match[1] != seat:
            raise RuntimeHalt('JUDGE_EFFECT_SOURCE_INVALID')
        definition = runtime.context.card(seat, match[2])
        binding = runtime.registry.lookup(match[2], selected['effect_id'], selected['field']).manifest()
        if (binding['definition_sha256'] != definition.definition_sha256
                or binding['text_sha256'] != hashlib.sha256(
                    definition.effect_text(selected['field']).encode()).hexdigest()):
            raise RuntimeHalt('JUDGE_EFFECT_BINDING_MISMATCH')
    else:
        if event.get('type') != 'CONTROL_RESOLVED' or event.get('kind') != kind:
            raise RuntimeHalt('JUDGE_CONTROL_EVENT_MISMATCH')
        actual = event.get('choice') or {}
        for name in required:
            if name not in actual or not _same(args[name], actual[name]):
                raise RuntimeHalt('JUDGE_CONTROL_CHOICE_MISMATCH')
        if kind == 'BREEDING_EVOLUTION' and 'source_key' in args and args['source_key'] != result.get('source_key'):
            raise RuntimeHalt('JUDGE_BREEDING_SOURCE_MISMATCH')
    return event, binding


def _sources(runtime, command, before, result, event, root):
    rules = _rules(root)
    specific = (event.get('choice') or {}).get('rules') if isinstance(event.get('choice'), dict) else None
    if specific is not None:
        if specific.get('sha256') != rules['sha256'] or specific.get('url') != rules['url']:
            raise RuntimeHalt('JUDGE_RULE_SNAPSHOT_MISMATCH')
        rules = copy.deepcopy(specific)
    evidence = [dict(rules, role='COMPREHENSIVE_RULE_SNAPSHOT')]
    refs = set(_references(command.get('args', {}))) | set(_references(result))
    if command['command'] == 'RESOLVE_PENDING':
        selected = next(item for item in before['state']['pending']
                        if item['id'] == command['args']['pending_id'])
        refs.add(selected['source'])
    attack = before['state'].get('attack')
    if attack:
        refs.update(_references([attack.get('attacker'), attack.get('target')]))
    for key in sorted(refs):
        owner, number = _PHYSICAL.fullmatch(key).group(1, 2)
        definition = runtime.context.card(owner, number)
        source = definition.to_dict()['official_source']
        path = (root / source['file']).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RuntimeHalt('JUDGE_SOURCE_OUTSIDE_ROOT') from exc
        pinned = OfficialEvidence.from_bytes(source['url'], path.read_bytes(), source['sha256'],
                                             source.get('locator') or '#' + number).manifest()
        evidence.append({**pinned, 'role': 'PRINTED_CARD_SOURCE', 'card': number,
                         'owner': owner, 'file': source['file'],
                         'definition_sha256': definition.definition_sha256})
    return evidence


def judge_action(runtime, command, before, after, result, error=None, *, root=ROOT, tracker=None):
    """Describe checks that actually ran; a failed audit never authorizes play.

    The engine checks rules transactionally before commit. This receipt checks
    the committed event, pinned evidence and conserved state afterwards. The
    trusted tracker's unadvanced state anchors the supplied predecessor; this
    function cannot independently recover a predecessor from a result alone.
    """
    root = Path(root).resolve()
    receipt = {'schema': 'experimental-judge-receipt-v1',
               'status': 'AUDIT_FAILED', 'accepted': False,
               'certification': 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED',
               'independent_semantic_certification': False,
               'judge_source_sha256': JUDGE_SOURCE_SHA256,
               'layers': {}, 'sources': [], 'binding': None,
               'rollback_unchanged': _same(_physical(before), _physical(after))}
    try:
        if (not isinstance(command, dict) or not isinstance(command.get('command'), str)
                or command.get('seat') not in _SEATS):
            raise RuntimeHalt('JUDGE_COMMAND_SCHEMA_INVALID')
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != JUDGE_SOURCE_SHA256:
            raise RuntimeHalt('JUDGE_SOURCE_CHANGED_RESTART_REQUIRED')
        if not isinstance(tracker, FieldTracker):
            raise RuntimeHalt('JUDGE_TRACKER_ANCHOR_REQUIRED')
        if not _same(tracker.audit_snapshot(), _physical(before)):
            raise RuntimeHalt('JUDGE_TRACKER_PREDECESSOR_MISMATCH')
        receipt['predecessor_binding'] = {'scope': 'TRUSTED_TRACKER_CHECKPOINT',
                                         'tracker_id': tracker.manifest()['tracker_id']}
        if any(before.get(name) != after.get(name) for name in ('context_id', 'seed', 'first')):
            raise RuntimeHalt('JUDGE_GAME_IDENTITY_MISMATCH')
        _audit_cards(runtime.context, before)
        count = _audit_cards(runtime.context, after)
        if not _same(runtime.snapshot(), after):
            raise RuntimeHalt('JUDGE_LIVE_SNAPSHOT_MISMATCH')
        runtime.verify()
        receipt['physical_card_count'] = count
        receipt['layers']['Tyr'] = {'status': 'PHYSICAL_AUDIT_PASSED',
                                    'scope': 'CONSERVATION_AND_SNAPSHOT_INTEGRITY'}
        if error is not None:
            if not receipt['rollback_unchanged']:
                raise RuntimeHalt('JUDGE_FAILED_TRANSACTION_CHANGED_STATE')
            reason = str(error)
            gap = any(word in reason.upper() for word in
                      ('UNSUPPORTED', 'UNIMPLEMENTED', 'UNVERIFIED', 'MISSING', 'RESTART_REQUIRED'))
            receipt.update({'status': 'SOFTWARE_GAP' if gap else 'REJECTED', 'reason': reason})
            receipt['layers'].update({
                'Justitia': {'status': 'TRANSACTION_REJECTED_UNCHANGED', 'reason': reason},
                'Dike': {'status': 'NO_SUCCESSFUL_RULE_RESOLUTION_CERTIFIED'}})
        else:
            if before['state'].get('terminal') or command.get('status') not in (None, 'EXPERIMENTAL_RESOLVED'):
                raise RuntimeHalt('JUDGE_SUCCESS_WINDOW_INVALID')
            event, binding = _engine_event(runtime, command, before, result)
            sources = _sources(runtime, command, before, result, event, root)
            receipt.update({'status': 'RUNTIME_VALIDATED', 'accepted': True,
                            'sources': sources, 'binding': binding,
                            'engine_event_index': len(runtime.events) - 1})
            receipt['layers'].update({
                'Justitia': {'status': 'TRANSACTION_RULES_CHECK_PASSED',
                             'scope': 'EXISTING_ENGINE_VALIDATORS'},
                'Dike': {'status': 'OFFICIAL_SOURCES_AND_BINDINGS_VERIFIED',
                         'independent_semantic_review': 'NOT_PERFORMED_BY_THIS_LEDGER'}})
    except (RuntimeHalt, ValueError, KeyError, TypeError, OSError) as exc:
        receipt.update({'status': 'AUDIT_FAILED', 'accepted': False,
                        'reason': str(exc), 'exception': type(exc).__name__})
    receipt['command_sha256'] = digest(command)
    receipt['before_snapshot_sha256'] = digest(_physical(before))
    receipt['after_snapshot_sha256'] = digest(_physical(after))
    receipt['receipt_sha256'] = digest(receipt)
    return copy.deepcopy(receipt)
