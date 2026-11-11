"""Serializable Rina grants and EX13-022's encountered opponent restriction.

Card handlers own printed targets and timing. These trusted primitives bind
provenance to the active source field and effects to the target's incarnation.
An applied grant lingers after its source leaves and survives normal
digivolution (rules 15-11-1 and 15-13); it does not follow a new incarnation.
Only a completed turn boundary removes a duration, after pending end processing
and the memory postponement check (rules 6-6-2 through 6-6-4).
"""
import copy
import hashlib

from context_runtime import RuntimeHalt
from effect_scheduler import source_stack


GRANT_STATUS = 'effect_grants'
_KEYWORDS = frozenset(('Blocker', 'Evade', 'Jamming'))
_RESTRICTIONS = frozenset(('cannot_suspend',))
_FIELDS = frozenset(('controller', 'source', 'source_instance', 'source_field',
    'source_kind', 'source_definition_sha256', 'source_text_sha256', 'target',
    'target_owner', 'target_instance', 'effect', 'created_turn', 'expires'))


def _effect(effect):
    if type(effect) is dict:
        if set(effect) == {'dp_bonus'} and type(effect['dp_bonus']) is int and effect['dp_bonus'] > 0:
            return copy.deepcopy(effect)
        if set(effect) == {'keywords'}:
            keywords = effect['keywords']
            if (type(keywords) is list and keywords
                    and all(type(keyword) is str and keyword in _KEYWORDS for keyword in keywords)
                    and len(set(keywords)) == len(keywords)):
                return copy.deepcopy(effect)
        if set(effect) == {'restrictions'}:
            restrictions = effect['restrictions']
            if (type(restrictions) is list and restrictions
                    and all(type(item) is str and item in _RESTRICTIONS for item in restrictions)
                    and len(set(restrictions)) == len(restrictions)):
                return copy.deepcopy(effect)
    raise RuntimeHalt('GRANT_EFFECT_UNSUPPORTED')


def _target(runtime, controller, target_key):
    runtime._source(controller, target_key, 'main_text')
    return runtime.state.battle[controller][target_key]


def _definitions(runtime, controller):
    return {f'{controller}:{number}#{index}': runtime.context.card(controller, number)
            for number, index in runtime.context.inventory(controller)}


def validate_grants(runtime, target_owner, target_key):
    """Validate only this known status schema; return detached grant records.

    Original source/target physical keys remain provenance after source loss or
    target reanchoring. The target instance, rather than its original top card,
    determines whether an otherwise valid record currently applies.
    """
    stack = _target(runtime, target_owner, target_key)
    if type(stack.statuses) is not dict or set(stack.statuses) - {GRANT_STATUS}:
        raise RuntimeHalt('GRANT_STATUS_UNSUPPORTED: ' + target_key)
    records = stack.statuses.get(GRANT_STATUS, [])
    if type(records) is not list:
        raise RuntimeHalt('GRANT_SCHEMA_INVALID: ' + target_key)
    target_definitions = _definitions(runtime, target_owner)
    for record in records:
        if type(record) is not dict or set(record) != _FIELDS:
            raise RuntimeHalt('GRANT_SCHEMA_INVALID: ' + target_key)
        if (record['controller'] not in ('A', 'B') or record['target_owner'] != target_owner
                or not all(type(record[key]) is str and record[key] for key in
                           ('source', 'source_instance', 'target', 'target_instance'))
                or record['target'] not in target_definitions
                or record['source_field'] not in ('main_text', 'inherited_text')
                or type(record['created_turn']) is not int
                or not 0 <= record['created_turn'] <= runtime.state.turn):
            raise RuntimeHalt('GRANT_SCHEMA_INVALID: ' + target_key)
        controller = record['controller']
        definitions = _definitions(runtime, controller)
        if record['source'] not in definitions:
            raise RuntimeHalt('GRANT_SCHEMA_INVALID: ' + target_key)
        definition = definitions[record['source']]
        kind = 'Digimon' if record['source_field'] == 'inherited_text' else definition.kind
        if (record['source_kind'] != kind
                or record['source_definition_sha256'] != definition.definition_sha256
                or record['source_text_sha256'] != hashlib.sha256(
                    definition.effect_text(record['source_field']).encode()).hexdigest()):
            raise RuntimeHalt('GRANT_SOURCE_BINDING_INVALID: ' + record['source'])
        _effect(record['effect'])
        expiry = record['expires']
        if (type(expiry) is not dict or set(expiry) != {'turn', 'controller', 'boundary'}
                or expiry['controller'] not in (controller, 'B' if controller == 'A' else 'A')
                or expiry['boundary'] != 'turn_end' or type(expiry['turn']) is not int
                or expiry['turn'] not in (record['created_turn'], record['created_turn'] + 1)
                or (expiry['controller'] == controller and expiry['turn'] != record['created_turn'])):
            raise RuntimeHalt('GRANT_SCHEMA_INVALID: ' + target_key)
    return copy.deepcopy(records)


def grant_effect(runtime, controller, target_key, effect, source_key,
                 duration='end_of_opponent_turn', *, source_field='main_text', target_owner=None):
    """Apply a semantic grant, keeping source controller and target owner distinct.

    Call from a source-bound card handler or another trusted rules command.
    This is not a public pilot action and does not choose a printed target.
    """
    if runtime.halted or runtime.state.terminal:
        raise RuntimeHalt('GRANT_AFTER_HALT_OR_TERMINAL')
    if duration not in ('end_of_opponent_turn','end_of_controller_turn'):
        raise RuntimeHalt('GRANT_DURATION_UNSUPPORTED: ' + str(duration))
    effect = _effect(effect)
    target_owner = controller if target_owner is None else target_owner
    source = runtime._source(controller, source_key, source_field)
    source_entity = source_stack(runtime, controller, source_key, source_field)
    target_entity = _target(runtime, target_owner, target_key)
    validate_grants(runtime, target_owner, target_key)
    for entity in (source_entity, target_entity):
        if type(entity.instance_id) is not str:
            raise RuntimeHalt('GRANT_INSTANCE_INVALID')
    definition = runtime.context.card(controller, source.card_number)
    opponent = 'B' if controller == 'A' else 'A'
    # Validate everything above before assigning identities or storing a grant.
    for entity in (source_entity, target_entity):
        if not entity.instance_id:
            runtime.state.entity_sequence += 1
            entity.instance_id = 'entity-' + str(runtime.state.entity_sequence)
    record = {'controller': controller, 'source': source_key,
        'source_instance': source_entity.instance_id, 'source_field': source_field,
        'source_kind': 'Digimon' if source_field == 'inherited_text' else definition.kind,
        'source_definition_sha256': definition.definition_sha256,
        'source_text_sha256': hashlib.sha256(definition.effect_text(source_field).encode()).hexdigest(),
        'target': target_key, 'target_owner': target_owner, 'target_instance': target_entity.instance_id,
        'effect': effect, 'created_turn': runtime.state.turn,
        'expires': {'turn': runtime.state.turn if duration=='end_of_controller_turn'
                    else runtime.state.turn + (runtime.state.active != opponent),
                    'controller': controller if duration=='end_of_controller_turn' else opponent,
                    'boundary': 'turn_end'}}
    target_entity.statuses.setdefault(GRANT_STATUS, []).append(record)
    return copy.deepcopy(record)


def _active(runtime, controller, target_key):
    stack = _target(runtime, controller, target_key)
    return [record for record in validate_grants(runtime, controller, target_key)
            if record['target_instance'] == stack.instance_id
            and runtime.state.turn <= record['expires']['turn']]


def active_keyword(runtime, controller, target_key, keyword):
    """Whether an active applied grant gives this entity the named keyword."""
    granted = any(keyword in record['effect'].get('keywords', [])
                  for record in _active(runtime, controller, target_key))
    if granted:
        return True
    # The encountered EX13-023 prints both keywords in one exact main-text
    # line. They remain active on that Digimon even without an applied grant.
    stack = _target(runtime, controller, target_key)
    top = stack.cards[-1]
    if keyword == 'Jamming':
        inherited = '＜Jamming＞ (This Digimon can\'t be deleted in battles against Security Digimon.)'
        if any(card.card_number == 'EX13-019' and runtime.context.card(
                controller, card.card_number).effect_text('inherited_text') == inherited
               for card in stack.cards[:-1]):
            return True
        if (top.card_number == 'EX13-019'
                and runtime.context.card(controller, top.card_number).effect_text('main_text') ==
                ('＜Jamming＞\n[When Attacking] [Once Per Turn] You may play 1 Tamer card '
                 'with [Veedramon] in its text from your hand with the cost reduced by 2.')):
            return True
    return (top.card_number == 'EX13-023' and keyword in ('Blocker', 'Evade')
            and '＜Blocker＞ ＜Evade＞' in runtime.context.card(
                controller, top.card_number).effect_text('main_text').splitlines())


def active_dp_bonus(runtime, controller, target_key):
    """Sum the entity's active applied positive-DP grants."""
    return sum(record['effect'].get('dp_bonus', 0)
               for record in _active(runtime, controller, target_key))


def active_restriction(runtime, target_owner, target_key, restriction):
    """Whether this target incarnation currently has the named applied restriction."""
    return any(restriction in record['effect'].get('restrictions', [])
               for record in _active(runtime, target_owner, target_key))


def expire_turn_grants(runtime, ending_controller):
    """Close the actual turn boundary, never merely its trigger window.

    finish_turn calls this only after its pending guard and postponement check.
    Validate the whole board before dropping any record. Old untyped statuses
    remain unsupported; this does not guess their duration.
    """
    checked = [(owner, key, stack, validate_grants(runtime, owner, key))
               for owner in ('A', 'B')
               for key, stack in runtime.state.battle[owner].items()]
    for _, _, stack, records in checked:
        retained = [record for record in records
                    if record['target_instance'] == stack.instance_id
                    and not (record['expires']['turn'] < runtime.state.turn
                        or (record['expires']['turn'] == runtime.state.turn
                            and record['expires']['controller'] == ending_controller))]
        if retained:
            stack.statuses[GRANT_STATUS] = retained
        else:
            stack.statuses.pop(GRANT_STATUS, None)
