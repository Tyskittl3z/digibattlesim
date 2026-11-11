"""Shared, fail-closed checks and movement for the encountered deck returns.

This does not resolve replacements or protections. A relevant unsupported
dependency halts before any member of a simultaneous return moves.
"""
import re
import hashlib
from dataclasses import replace

from context_runtime import MechanicBinding, RuntimeHalt
from printed_triggers import effect_body, effect_headers


_LEAVE = re.compile(r'\b(?:leav\w*|left|remov\w*|return\w*|trash\w*)\b', re.I)
_KEYWORD = re.compile(r'\b(?:Overflow|Decode|Partition)\b', re.I)
_SELF = re.compile(r'\bthis (?:(unsuspended|suspended) )?Digimon\b', re.I)
_OTHER_SUBJECT = re.compile(
    r'\b(?:all|any|each)\b|\b(?:your|opponent\x27s) (?:other )?(?:Digimon|cards|Tamers)\b|'
    r'\b\d+ of (?:your|their)\b|\bother Digimon\b', re.I)
_OTHER_TIMINGS = frozenset(('On Play', 'When Digivolving', 'When Attacking',
    'On Deletion', 'When Moving', 'Security', 'Start of Your Turn',
    'Start of Your Main Phase', 'End of Your Turn', "End of Opponent's Turn"))
REPLACEMENT_EFFECT = 'EX13-017.return_replacement'
REPLACEMENT_LINE = ('[All Turns] [Once Per Turn] When this Digimon with [Veedramon] in its name '
    "would leave the battle area by your opponent's effects, by suspending it, it doesn't leave.")


def replacement_usage(runtime, owner, source_key, stack):
    return (runtime.state.turn, owner, source_key, stack.instance_id, REPLACEMENT_EFFECT)


def inherited_return_replacement(runtime, actor, owner, target_key):
    """The exact printed, currently payable replacement on this affected stack."""
    stack = runtime.state.battle[owner][target_key]
    top = runtime.context.card(owner, stack.cards[-1].card_number)
    if (actor == owner or 'Veedramon' not in top.name or stack.suspended
            or stack.statuses.get('cannot_suspend', False)):
        return None
    from effect_grants import active_restriction
    if active_restriction(runtime, owner, target_key, 'cannot_suspend'):
        return None
    found = []
    for source in stack.cards[:-1]:
        definition = runtime.context.card(owner, source.card_number)
        if source.card_number == 'EX13-017' and definition.effect_text('inherited_text') == REPLACEMENT_LINE:
            usage = replacement_usage(runtime, owner, source.key, stack)
            if usage not in runtime.state.once_used:
                found.append((source.key, usage))
    if len(found) > 1:
        raise RuntimeHalt('RETURN_MULTIPLE_REPLACEMENTS_UNIMPLEMENTED')
    return found[0] if found else None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _active_line(line, observer_owner, active):
    headers = effect_headers(line)
    return not (('Your Turn' in headers and observer_owner != active)
        or ("Opponent's Turn" in headers and observer_owner == active)
        or any(header in _OTHER_TIMINGS for header in headers))


def _self_only(body):
    """Prove the affected object is this Digimon, retaining mixed/global text."""
    return _SELF.search(body) is not None and not _OTHER_SUBJECT.search(body)


def preflight_deck_bottom_return(runtime, actor, owner, target_key, *, halt_prefix='RETURN',
                                 replacement_handled=False):
    """Inspect active fields and actual leaving cards without changing state."""
    from effect_grants import validate_grants
    target = runtime.state.battle[owner][target_key]
    target_definition = runtime.context.card(owner, target.cards[-1].card_number)
    if inherited_return_replacement(runtime, actor, owner, target_key) and not replacement_handled:
        raise RuntimeHalt(halt_prefix + '_REPLACEMENT_CHOICE_REQUIRED: ' + target_key)
    if target.statuses:
        validate_grants(runtime, owner, target_key)

    def halt(kind, physical, field):
        raise RuntimeHalt(halt_prefix + '_' + kind + '_UNIMPLEMENTED: '
                          + physical.card_number + ' ' + field + ' source=' + physical.key)

    # Overflow is a card's leave rule even while that card is a source. Do not
    # confuse other inactive main/inherited text with an active stack effect.
    for physical in target.cards:
        definition = runtime.context.card(owner, physical.card_number)
        raw = definition.to_dict()
        if any(re.search(r'\bOverflow\b', text, re.I)
               for field in ('main_text', 'inherited_text', 'special_conditions')
               for text in _strings(raw.get(field))):
            halt('LEAVE_KEYWORD', physical, 'Overflow')
        if any(_KEYWORD.search(text) or _LEAVE.search(text)
               for text in _strings(raw.get('special_conditions', {}))):
            halt('LEAVE_SPECIAL_CONDITION', physical, 'special_conditions')

    for observer_owner in ('A', 'B'):
        for observer in runtime.state.battle[observer_owner].values():
            for index, physical in enumerate(observer.cards):
                field = 'main_text' if index == len(observer.cards) - 1 else 'inherited_text'
                definition = runtime.context.card(observer_owner, physical.card_number)
                for line in definition.effect_text(field).splitlines():
                    if not _active_line(line, observer_owner, runtime.state.active):
                        continue
                    if (observer is target and field == 'inherited_text'
                            and physical.card_number == 'EX13-017' and line == REPLACEMENT_LINE):
                        continue
                    body = effect_body(line).replace('’', "'")
                    if observer is target and _KEYWORD.search(body):
                        halt('LEAVE_KEYWORD', physical, field)
                    clause = body.split(',', 1)[0]
                    if re.match(r'\s*(?:When|Whenever|If)\b', clause, re.I) and _LEAVE.search(clause):
                        subject = clause.split(' by ', 1)[0]
                        self_subject = re.match(r'\s*(?:When|Whenever|If)\s+this '
                            r'(?:(?:unsuspended|suspended) )?(Digimon|Tamer)\b', subject, re.I)
                        if self_subject and (self_subject[1].lower() == 'tamer' or observer is not target):
                            continue
                        if 'opponent' in subject.lower():
                            if owner == observer_owner:
                                continue
                        elif ('your ' in subject.lower() or self_subject) and owner != observer_owner:
                            continue
                        if "opponent's effects" in clause and actor == observer_owner:
                            continue
                        if 'by your effects' in clause and actor != observer_owner:
                            continue
                        if 'other Digimon' in subject and observer is target:
                            continue
                        if re.search(r'digivolution cards?|sources?', subject, re.I) and len(target.cards) == 1:
                            continue
                        # Only an explicit name filter can exclude by name.
                        # Bracketed traits/levels must not be mistaken for names.
                        names = re.search(r'with ((?:\[[^\]]+\](?: or )?)+) in (?:its|their) name', subject)
                        if names and not any(name in target_definition.name
                                for name in re.findall(r'\[([^\]]+)\]', names[1])):
                            continue
                        halt('LEAVE_DEPENDENCY', physical, field)
                    lower = body.lower()
                    protection = (any(word in lower for word in
                        ("can't", 'cannot', "isn't affected", 'unaffected', "doesn't leave", 'does not leave'))
                        and (_LEAVE.search(body) or 'affect' in lower))
                    if not protection:
                        continue
                    if _self_only(body):
                        if observer is not target:
                            continue
                        orientation = _SELF.search(body)[1]
                        if (orientation == 'unsuspended' and target.suspended
                                or orientation == 'suspended' and not target.suspended):
                            continue
                    if lower.startswith("your opponent's effects") and actor == observer_owner:
                        continue
                    if lower.startswith('your effects') and actor != observer_owner:
                        continue
                    halt('PROTECTION', physical, field)


def return_to_deck_bottom(runtime, actor, owner, target_keys, bottom_order, *, halt_prefix='RETURN',
                          replacement_handled=False):
    """Move already-selected targets after all dependencies pass preflight.

    Callers validate eligibility and the explicit action-controller bottom order.
    The first ordered top becomes bottommost; source cards go to their trash.
    """
    for key in target_keys:
        preflight_deck_bottom_return(runtime, actor, owner, key, halt_prefix=halt_prefix,
                                     replacement_handled=replacement_handled)
    returned, trashed, steps, tops = [], [], [], {}
    for key in target_keys:
        stack = runtime.state.battle[owner].pop(key)
        top, lower = stack.cards[-1], stack.cards[:-1]
        tops[top.key] = top
        runtime.state.zones[owner]['trash'].extend(lower)
        returned.append(top.key)
        trashed.extend(card.key for card in lower)
        steps.append({'operation': 'RETURN_DIGIMON_TO_DECK_BOTTOM', 'owner': owner,
                      'card': top.key, 'trashed_sources': [card.key for card in lower]})
    runtime.state.zones[owner]['deck'][:0] = [tops[key] for key in bottom_order]
    return {'returned': returned, 'trashed_sources': trashed, 'steps': steps}


def return_to_hand(runtime, actor, owner, target_key, *, halt_prefix='RETURN'):
    """Return one selected Digimon's top card to hand and trash its sources."""
    preflight_deck_bottom_return(runtime, actor, owner, target_key, halt_prefix=halt_prefix)
    stack = runtime.state.battle[owner].pop(target_key)
    top, lower = stack.cards[-1], stack.cards[:-1]
    runtime.state.zones[owner]['hand'].append(top)
    runtime.state.zones[owner]['trash'].extend(lower)
    return {'returned': top.key, 'trashed_sources': [card.key for card in lower],
            'steps': [{'operation': 'RETURN_DIGIMON_TO_HAND', 'owner': owner,
                       'card': top.key, 'trashed_sources': [card.key for card in lower]}]}


def _replacement_window(runtime, seat, source_key):
    from effect_scheduler import pending_options, source_stack
    expected = (REPLACEMENT_EFFECT, seat, source_key, 'inherited_text')
    activated = getattr(runtime, '_activated_effect', None)
    if activated is not None and activated[:4] == expected and activated[4] is not None:
        record = getattr(runtime, '_activated_pending', None)
    else:
        record = next((p for p in pending_options(runtime, seat)
            if tuple(p[k] for k in ('effect_id', 'seat', 'source', 'field')) == expected), None)
    if record is None or tuple(record.get(k) for k in ('effect_id', 'seat', 'source', 'field')) != expected:
        raise RuntimeHalt('RETURN_REPLACEMENT_WINDOW_REQUIRED')
    stack = source_stack(runtime, seat, source_key, 'inherited_text')
    trigger = record['trigger']
    target = trigger.get('target')
    if (target not in runtime.state.battle[seat] or stack is not runtime.state.battle[seat][target]
            or trigger.get('target_instance') != stack.instance_id
            or trigger.get('actor') == seat or trigger.get('source_effect') != 'EX13-023.return_fewest'):
        raise RuntimeHalt('RETURN_REPLACEMENT_WINDOW_REQUIRED')
    return record, stack


def return_replacement_choices(runtime, seat, source_key):
    record, stack = _replacement_window(runtime, seat, source_key)
    target = record['trigger']['target']
    return [False, True] if inherited_return_replacement(runtime,
        record['trigger']['actor'], seat, target) is not None else [False]


def resolve_return_replacement(runtime, seat, source_key, choice):
    offered = return_replacement_choices(runtime, seat, source_key)
    if type(choice) is not bool or choice not in offered:
        raise RuntimeHalt('RETURN_REPLACEMENT_CHOICE_INVALID')
    record, stack = _replacement_window(runtime, seat, source_key)
    trigger = record['trigger']
    target, actor = trigger['target'], trigger['actor']
    if choice:
        stack.suspended = True
        usage = replacement_usage(runtime, seat, source_key, stack)
        runtime.state.once_used.add(usage)
        return {'prevented_return': True, 'suspended': target,
                'once_per_turn_consumed': True, 'full_match_credit': 0}
    moved = return_to_deck_bottom(runtime, actor, seat, [target], [target],
        halt_prefix='ULFORCE_RETURN', replacement_handled=True)
    return {'prevented_return': False, **moved, 'full_match_credit': 0}


def inherited_return_replacement_bindings(context, root, rules):
    from match_context import require
    from selected_mechanics import _source_evidence
    bindings = []
    for card in context.cards:
        if card.number != 'EX13-017':
            continue
        require(card.effect_text('inherited_text') == REPLACEMENT_LINE,
                'Exact inherited return replacement text changed')
        evidence = _source_evidence(root, card.to_dict()['official_source'],
            '#EX13-017 inherited once-per-turn leave replacement')
        bindings.append(MechanicBinding(card.number, REPLACEMENT_EFFECT, 'inherited_text',
            card.definition_sha256,
            hashlib.sha256(card.effect_text('inherited_text').encode()).hexdigest(),
            (evidence, replace(rules, locator='Comprehensive rules v4.3: replacement and suspension timing')),
            resolve_return_replacement))
    return tuple(bindings)
