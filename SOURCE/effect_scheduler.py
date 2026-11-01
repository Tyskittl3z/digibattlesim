"""Explicit pending/derived effect choices; comprehensive rules 15-4.

This schedules already identified effects. It never infers card abilities or
auto-declines an optional effect. Card-specific trigger collection is separate.
"""
import copy
import hashlib
import json

from context_runtime import RuntimeHalt
from match_context import canonical


def source_stack(runtime, seat, source, field):
    runtime._source(seat, source, field)
    for stack in runtime.state.battle[seat].values():
        if any(c.key == source for c in stack.cards):
            return stack
    raise RuntimeHalt('SOURCE_NOT_ACTIVE: ' + source)


def validate_pending(runtime):
    state = runtime.state
    if type(state.effect_sequence) is not int or state.effect_sequence < 0 or type(state.entity_sequence) is not int or state.entity_sequence < 0:
        raise RuntimeHalt('PENDING_SEQUENCE_INVALID')
    if not isinstance(state.pending, list):
        raise RuntimeHalt('PENDING_SCHEMA_INVALID')
    seen = set()
    for effect in state.pending:
        if not isinstance(effect, dict) or set(effect) != {
                'id','seat','source','effect_id','field','instance','depth','trigger','usage'}:
            raise RuntimeHalt('PENDING_SCHEMA_INVALID')
        if (not isinstance(effect['id'], str) or effect['id'] in seen
                or effect['seat'] not in ('A','B') or effect['field'] not in ('main_text','inherited_text')
                or not all(isinstance(effect[k], str) and effect[k] for k in ('source','effect_id','instance'))
                or type(effect['depth']) is not int or effect['depth'] < 0
                or not isinstance(effect['trigger'], dict) or not isinstance(effect['usage'], list)
                or any(not isinstance(x, (str, int)) or isinstance(x,bool) for x in effect['usage'])):
            raise RuntimeHalt('PENDING_SCHEMA_INVALID')
        seen.add(effect['id'])
    canonical(state.pending)


def queue_effects(runtime, effects):
    """Queue a simultaneous group only after all bindings/records validate."""
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('QUEUE_AFTER_HALT_OR_TERMINAL')
    records = []
    for raw in effects:
        raw = json.loads(canonical(raw))
        seat, source, field = raw['seat'],raw['source'],raw['field']
        physical = runtime._source(seat,source,field)
        binding = runtime.registry.lookup(physical.card_number,raw['effect_id'],field)
        definition = runtime.context.card(seat,physical.card_number)
        if (binding.definition_sha256 != definition.definition_sha256 or binding.text_sha256 !=
                hashlib.sha256(definition.effect_text(field).encode()).hexdigest()):
            raise RuntimeHalt('PACK_TEXT_BINDING_MISMATCH')
        trigger,usage = raw.get('trigger'),raw.get('usage',[])
        if not isinstance(trigger,dict) or not isinstance(usage,list):
            raise RuntimeHalt('PENDING_SCHEMA_INVALID')
        if usage and tuple(usage) in runtime.state.once_used:
            continue
        stack = source_stack(runtime,seat,source,field)
        records.append((raw,stack,trigger,usage))
    # No validation below can fail after this point for a valid runtime.
    for raw,stack,trigger,usage in records:
        if not stack.instance_id:
            runtime.state.entity_sequence += 1
            stack.instance_id = 'entity-' + str(runtime.state.entity_sequence)
        runtime.state.effect_sequence += 1
        effect = {'id':'effect-'+str(runtime.state.effect_sequence),
                  'seat':raw['seat'],'source':raw['source'],'effect_id':raw['effect_id'],
                  'field':raw['field'],'instance':stack.instance_id,
                  'depth':getattr(runtime,'_resolution_depth',-1)+1,
                  'trigger':copy.deepcopy(trigger),'usage':copy.deepcopy(usage)}
        runtime.state.pending.append(effect)
        runtime.events.append({'type':'EFFECT_PENDING','context_id':runtime.context.matchup_id,
                               'turn':runtime.state.turn,'effect':copy.deepcopy(effect)})


def _inactive_reason(runtime,effect):
    try:
        stack = source_stack(runtime,effect['seat'],effect['source'],effect['field'])
    except RuntimeHalt:
        return 'SOURCE_OR_EFFECT_LOST'
    if stack.instance_id != effect['instance']:
        return 'SOURCE_BECAME_NEW_CARD'
    if effect['usage'] and tuple(effect['usage']) in runtime.state.once_used:
        return 'ONCE_PER_TURN_EXHAUSTED'
    return None


def pending_options(runtime,seat):
    runtime.context.deck(seat)
    validate_pending(runtime)
    active = [e for e in runtime.state.pending if _inactive_reason(runtime,e) is None]
    if not active:
        return []
    depth = max(e['depth'] for e in active)
    group = [e for e in active if e['depth'] == depth]
    controller = runtime.state.active if any(e['seat']==runtime.state.active for e in group) else (
        'B' if runtime.state.active=='A' else 'A')
    return copy.deepcopy([e for e in group if e['seat']==seat]) if seat==controller else []


def prune_pending(runtime):
    validate_pending(runtime)
    retained,cancelled = [],[]
    for effect in runtime.state.pending:
        reason = _inactive_reason(runtime,effect)
        if reason:
            cancelled.append({'type':'PENDING_CANCELLED','turn':runtime.state.turn,
                              'effect':copy.deepcopy(effect),'reason':reason})
        else:
            retained.append(effect)
    runtime.state.pending = retained
    runtime.events.extend(cancelled)
    return len(cancelled)


def resolve_pending(runtime,seat,pending_id,choice):
    options = pending_options(runtime,seat)
    selected = next((e for e in options if e['id']==pending_id),None)
    if selected is None:
        if runtime.state.pending and not pending_options(runtime,'A') and not pending_options(runtime,'B'):
            return runtime.settle_pending()
        # Use dispatch's audit/rollback boundary for invalid player commands.
        return runtime.dispatch('',seat,'',choice,pending_id=pending_id)
    return runtime.dispatch(selected['effect_id'],seat,selected['source'],choice,
                            field_=selected['field'],pending_id=pending_id)
