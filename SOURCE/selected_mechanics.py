"""First selected EX13 mechanics; experimental scenarios, never full matches.

Only the exact EX13-023 orientation processing is implemented. Trigger-window
creation, simultaneous ordering, inherited reactions, persistent-status rule
checks, Assembly, return-to-deck and other abilities are NOT certified here.
An encountered dependency halts before the transaction commits.
"""
import hashlib
import json
from pathlib import Path
import re

from context_runtime import MechanicBinding, MechanicRegistry, OfficialEvidence, RuntimeHalt
from match_context import require

ORIENTATION_EFFECT = 'EX13-023.orientation'
ORIENTATION_LINE = ('[On Play] [When Digivolving] [When Attacking] [Once Per Turn] '
                    '1 of your Digimon may change orientation.')


def orientation_candidates(runtime, seat, source_key):
    source = runtime._source(seat, source_key, 'main_text')
    if source.card_number != 'EX13-023':
        raise RuntimeHalt('ORIENTATION_SOURCE_MISMATCH')
    return [None] + sorted(key for key, stack in runtime.state.battle[seat].items()
                          if runtime.context.card(seat, stack.cards[-1].card_number).kind == 'Digimon')


def _orientation_dependencies(runtime):
    # Conservative scope barrier, not a claim that each matching effect triggers
    # in this position. Until timing/conditions are implemented, retain the
    # precise source rather than silently suppress a potentially live reaction.
    reaction = re.compile(r'\bwhen\b[^\n]*\b(?:unsuspend|unsuspends|suspend|suspends|suspended|unsuspended)\b', re.I)
    for seat in ('A', 'B'):
        for stack in runtime.state.battle[seat].values():
            for index, card in enumerate(stack.cards):
                field_ = 'main_text' if index == len(stack.cards) - 1 else 'inherited_text'
                text = runtime.context.card(seat, card.card_number).effect_text(field_)
                if reaction.search(text):
                    raise RuntimeHalt('ORIENTATION_DEPENDENT_TRIGGER_UNIMPLEMENTED: '
                                      + card.card_number + ' ' + field_)
            if set(stack.statuses) - {'cannot_suspend', 'cannot_unsuspend'}:
                # Includes DP reduction: EX13-023 Q7269 says a 0-DP rule check
                # precedes triggered effects; an unsuspend cannot rescue it.
                raise RuntimeHalt('ORIENTATION_STATUS_UNSUPPORTED: ' + stack.cards[-1].key)
            if any(type(v) is not bool for v in stack.statuses.values()):
                raise RuntimeHalt('ORIENTATION_STATUS_UNSUPPORTED: non-boolean prohibition')


def resolve_orientation(runtime, seat, source_key, target):
    """Resolve an already activated effect in a closed, verified-scope scenario.

    target=None declines optional processing AFTER activation, consuming OPT
    under comprehensive rule 15-14-1-4. This is distinct from declining to
    activate a pending effect; no automatic decline or learning occurs here.
    """
    if target not in orientation_candidates(runtime, seat, source_key):
        raise RuntimeHalt('ORIENTATION_TARGET_INVALID')
    usage = (runtime.state.turn, seat, source_key, ORIENTATION_EFFECT)
    if usage in runtime.state.once_used:
        raise RuntimeHalt('ONCE_PER_TURN_ALREADY_USED: ' + source_key)
    if target is None:
        runtime.state.once_used.add(usage)
        return {'changed': False, 'processing': 'OPTIONAL_PROCESSING_DECLINED_AFTER_ACTIVATION',
                'once_per_turn_consumed': True}
    _orientation_dependencies(runtime)
    stack = runtime.state.battle[seat][target]
    before = stack.suspended
    prohibition = 'cannot_unsuspend' if before else 'cannot_suspend'
    blocked = stack.statuses.get(prohibition, False)
    if not blocked:
        stack.suspended = not before
    runtime.state.once_used.add(usage)
    return {'target': target, 'suspended_before': before, 'suspended_after': stack.suspended,
            'changed': not blocked, 'prohibition': prohibition if blocked else None,
            'once_per_turn_consumed': True}


def _source_evidence(root, source, locator):
    root = Path(root).resolve()
    base = (root / 'RULES').resolve()
    path = (root / source['file']).resolve()
    require(path.is_relative_to(base) and base.is_relative_to(root), 'Official source escapes RULES')
    return OfficialEvidence.from_bytes(source['url'], path.read_bytes(), source['sha256'], locator)


def build_selected_registry(context, root):
    cards = {c.number: c for c in context.cards}
    if 'EX13-023' not in cards:
        return MechanicRegistry()
    card = cards['EX13-023']
    require(ORIENTATION_LINE in card.effect_text('main_text').splitlines(),
            'EX13-023 exact orientation text changed')
    raw = card.to_dict()
    evidence = [_source_evidence(root, raw['official_source'],
                                '#EX13-023 effect 1 and Q7267; dependencies Q7266/Q7269')]
    index = json.loads((Path(root) / 'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json').read_bytes())
    source = next(d for d in index['sources'] if d['id'] == 'rules')
    evidence.append(_source_evidence(root, source,
                                    'Comprehensive rules v4.3: 4-13; 15-1-7; 15-14-1-1 through 15-14-1-5'))
    binding = MechanicBinding(card.number, ORIENTATION_EFFECT, 'main_text', card.definition_sha256,
                             hashlib.sha256(card.effect_text('main_text').encode('utf-8')).hexdigest(),
                             tuple(evidence), resolve_orientation)
    return MechanicRegistry((binding,))
