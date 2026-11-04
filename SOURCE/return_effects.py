"""Shared, fail-closed checks and movement for the encountered deck returns.

This does not resolve replacements or protections. A relevant unsupported
dependency halts before any member of a simultaneous return moves.
"""
import re

from context_runtime import RuntimeHalt
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


def preflight_deck_bottom_return(runtime, actor, owner, target_key, *, halt_prefix='RETURN'):
    """Inspect active fields and actual leaving cards without changing state."""
    from effect_grants import validate_grants
    target = runtime.state.battle[owner][target_key]
    target_definition = runtime.context.card(owner, target.cards[-1].card_number)
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


def return_to_deck_bottom(runtime, actor, owner, target_keys, bottom_order, *, halt_prefix='RETURN'):
    """Move already-selected targets after all dependencies pass preflight.

    Callers validate eligibility and the explicit action-controller bottom order.
    The first ordered top becomes bottommost; source cards go to their trash.
    """
    for key in target_keys:
        preflight_deck_bottom_return(runtime, actor, owner, key, halt_prefix=halt_prefix)
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
