"""Bot C observes field state; it neither resolves cards nor rates strategy.

Audit snapshots/movements are PRIVATE. player_view and public_metrics alone are
player inputs. Continuity and a hash chain identify changed/missing stateful
observations; identical no-op retries need an external index to distinguish.
"""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
from context_runtime import RuntimeHalt
from match_context import canonical, digest

_SEATS = ('A', 'B')
_ZONES = frozenset(('deck', 'eggdeck', 'hand', 'security', 'trash'))
_VERSION = 'bot-c-field-tracker-v1'
_STACK_FIELDS = frozenset(('cards', 'suspended', 'statuses', 'instance_id',
                          'played_turn', 'ready_since_turn'))
_ATTACK_FIELDS = frozenset(('attacker', 'attacker_instance', 'target', 'target_instance',
                           'controller', 'defender', 'window', 'counter_used', 'block_used', 'checked'))
_GRANT_FIELDS = frozenset(('controller', 'source', 'source_instance', 'source_field',
    'source_kind', 'source_definition_sha256', 'source_text_sha256', 'target',
    'target_owner', 'target_instance', 'effect', 'created_turn', 'expires'))


class FieldTracker:
    def __init__(self, context):
        self._context = context
        self._inventory = {s: Counter(f'{s}:{n}#{i}' for n, i in context.inventory(s)) for s in _SEATS}
        self._manifest = {'name': 'Bot C', 'role': 'FIELD_TRACKER', 'version': _VERSION,
            'context_id': context.matchup_id,
            'physical_card_count': sum(sum(c.values()) for c in self._inventory.values()),
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'audit_visibility': 'PRIVATE', 'player_inputs': ['player_view', 'public_metrics']}
        self._manifest['tracker_id'] = digest(self._manifest)
        self._snapshot, self._chain = None, None
        self._observations = []
        self._checks = dict.fromkeys(_SEATS, 0)

    def manifest(self):
        return copy.deepcopy(self._manifest)

    @property
    def observations(self):
        """Detached PRIVATE ledger, never a player input."""
        return copy.deepcopy(self._observations)

    def _started(self):
        if self._snapshot is None:
            raise RuntimeHalt('TRACKER_NOT_STARTED')

    def _card(self, owner, key):
        if not isinstance(key, str) or key not in self._inventory[owner]:
            raise RuntimeHalt('TRACKER_PHYSICAL_CARD_OWNER_OR_ID: ' + str(key))
        return self._context.card(owner, key.split(':', 1)[1].split('#', 1)[0])

    def _public_statuses(self, owner, statuses, turn):
        """Fail closed on metadata outside the current public status contract."""
        if set(statuses) - {'cannot_suspend', 'cannot_unsuspend', 'effect_grants'}:
            raise RuntimeHalt('TRACKER_PUBLIC_STATUS_UNSUPPORTED')
        for name in ('cannot_suspend', 'cannot_unsuspend'):
            if name in statuses and type(statuses[name]) is not bool:
                raise RuntimeHalt('TRACKER_PUBLIC_STATUS_TYPE_INVALID')
        grants = statuses.get('effect_grants', [])
        if not isinstance(grants, list):
            raise RuntimeHalt('TRACKER_PUBLIC_GRANT_SCHEMA_INVALID')
        for record in grants:
            if (not isinstance(record, dict) or set(record) != _GRANT_FIELDS
                    or record['controller'] not in _SEATS or record['target_owner'] != owner
                    or record['source_field'] not in ('main_text', 'inherited_text')
                    or type(record['created_turn']) is not int or not 0 <= record['created_turn'] <= turn
                    or any(not isinstance(record[key], str) or not record[key]
                           for key in ('source_instance', 'target_instance'))):
                raise RuntimeHalt('TRACKER_PUBLIC_GRANT_SCHEMA_INVALID')
            definition = self._card(record['controller'], record['source'])
            self._card(owner, record['target'])
            kind = 'Digimon' if record['source_field'] == 'inherited_text' else definition.kind
            if (record['source_kind'] != kind
                    or record['source_definition_sha256'] != definition.definition_sha256
                    or record['source_text_sha256'] != hashlib.sha256(
                        definition.effect_text(record['source_field']).encode()).hexdigest()):
                raise RuntimeHalt('TRACKER_PUBLIC_GRANT_SOURCE_INVALID')
            effect = record['effect']
            valid = False
            if isinstance(effect, dict):
                if set(effect) == {'dp_bonus'}:
                    valid = type(effect['dp_bonus']) is int and effect['dp_bonus'] > 0
                for key, allowed in (('keywords', ('Blocker', 'Evade', 'Jamming')),
                                     ('restrictions', ('cannot_suspend',))):
                    if set(effect) == {key}:
                        values = effect[key]
                        valid = (isinstance(values, list) and bool(values)
                                 and all(isinstance(item, str) and item in allowed for item in values)
                                 and len(values) == len(set(values)))
            if not valid:
                raise RuntimeHalt('TRACKER_PUBLIC_GRANT_EFFECT_INVALID')
            expiry = record['expires']
            if (not isinstance(expiry, dict) or set(expiry) != {'turn', 'controller', 'boundary'}
                    or type(expiry['turn']) is not int
                    or expiry['turn'] not in (record['created_turn'], record['created_turn'] + 1)
                    or expiry['controller'] not in (record['controller'],
                        'B' if record['controller'] == 'A' else 'A')
                    or (expiry['controller'] == record['controller']
                        and expiry['turn'] != record['created_turn'])
                    or expiry['boundary'] != 'turn_end'):
                raise RuntimeHalt('TRACKER_PUBLIC_GRANT_EXPIRY_INVALID')

    def _normalise(self, snapshot):
        try:
            v = json.loads(canonical(snapshot))
        except (TypeError, ValueError) as exc:
            raise RuntimeHalt('TRACKER_SNAPSHOT_NOT_SERIALIZABLE') from exc
        if not isinstance(v, dict) or not isinstance(v.get('state'), dict):
            raise RuntimeHalt('TRACKER_SNAPSHOT_SCHEMA_INVALID')
        v.pop('execution_id', None)
        v['state'].setdefault('resolving_option', None)
        if (v.get('context_id') != self._context.matchup_id or type(v.get('seed')) is not int
                or v['seed'] < 0 or v.get('first') not in _SEATS or not isinstance(v.get('rng_state'), list)):
            raise RuntimeHalt('TRACKER_SNAPSHOT_IDENTITY_INVALID')
        s = v['state']
        required = {'zones', 'battle', 'breeding', 'active', 'memory', 'turn', 'terminal',
                    'phase', 'attack', 'pending', 'winner', 'resolving_option'}
        if (not required <= set(s) or not isinstance(s.get('phase'), str) or not s['phase']
                or not isinstance(s.get('pending'), list) or s.get('winner') not in (None, 'A', 'B')
                or s.get('active') not in _SEATS or type(s.get('memory')) is not int
                or not -10 <= s['memory'] <= 10 or type(s.get('turn')) is not int
                or s['turn'] < 0 or type(s.get('terminal')) is not bool):
            raise RuntimeHalt('TRACKER_STATE_SCHEMA_INVALID')
        attack = s['attack']
        if attack is not None:
            if not isinstance(attack, dict) or set(attack) - _ATTACK_FIELDS:
                raise RuntimeHalt('TRACKER_ATTACK_SCHEMA_INVALID')
            for name, item in attack.items():
                if name in ('counter_used', 'block_used'):
                    valid = type(item) is bool
                elif name == 'checked':
                    valid = item is None or isinstance(item, str)
                else:
                    valid = isinstance(item, str)
                if not valid:
                    raise RuntimeHalt('TRACKER_ATTACK_FIELD_INVALID: ' + name)
        for name in ('zones', 'battle', 'breeding'):
            if not isinstance(s.get(name), dict) or set(s[name]) != set(_SEATS):
                raise RuntimeHalt('TRACKER_PHYSICAL_PLAYER_SCHEMA: ' + name)
        seen, entities = {seat: [] for seat in _SEATS}, set()

        def stack(owner, value, anchor=None, resolving=False):
            if (not isinstance(value, dict) or set(value) != _STACK_FIELDS
                    or not isinstance(value.get('cards'), list) or not value['cards']
                    or type(value.get('suspended')) is not bool or not isinstance(value.get('statuses'), dict)
                    or not isinstance(value.get('instance_id'), str)
                    or any(value[name] is not None and type(value[name]) is not int
                           for name in ('played_turn', 'ready_since_turn'))
                    or (anchor is not None and value['cards'][-1] != anchor)
                    or (resolving and len(value['cards']) != 1)):
                raise RuntimeHalt('TRACKER_PHYSICAL_STACK_SCHEMA')
            identity = value['instance_id']
            if identity:
                if identity in entities:
                    raise RuntimeHalt('TRACKER_PHYSICAL_DUPLICATE_ENTITY: ' + identity)
                entities.add(identity)
            for key in value['cards']:
                self._card(owner, key)
            self._public_statuses(owner, value['statuses'], s['turn'])
            seen[owner].extend(value['cards'])

        for owner in _SEATS:
            zones = s['zones'][owner]
            if not isinstance(zones, dict) or set(zones) != _ZONES:
                raise RuntimeHalt('TRACKER_PHYSICAL_ZONE_SCHEMA')
            for zone, cards in zones.items():
                if not isinstance(cards, list):
                    raise RuntimeHalt('TRACKER_PHYSICAL_ZONE_CARDS')
                for key in cards:
                    if self._card(owner, key).kind != 'Digi-Egg' and zone == 'eggdeck':
                        raise RuntimeHalt('TRACKER_PHYSICAL_EGG_DECK_TYPE')
                seen[owner].extend(cards)
            if not isinstance(s['breeding'][owner], list) or not isinstance(s['battle'][owner], dict):
                raise RuntimeHalt('TRACKER_PHYSICAL_AREA_SCHEMA')
            for key in s['breeding'][owner]:
                self._card(owner, key)
            seen[owner].extend(s['breeding'][owner])
            for anchor, value in s['battle'][owner].items():
                stack(owner, value, anchor)
        resolving = s['resolving_option']
        if resolving is not None:
            if (not isinstance(resolving, dict) or set(resolving) != {'seat', 'stack'}
                    or resolving['seat'] not in _SEATS):
                raise RuntimeHalt('TRACKER_PHYSICAL_RESOLVING_OPTION_SCHEMA')
            owner = resolving['seat']
            stack(owner, resolving['stack'], resolving=True)
            if self._card(owner, resolving['stack']['cards'][0]).kind != 'Option':
                raise RuntimeHalt('TRACKER_PHYSICAL_RESOLVING_OPTION_TYPE')
        for owner in _SEATS:
            if Counter(seen[owner]) != self._inventory[owner]:
                raise RuntimeHalt('TRACKER_PHYSICAL_CARD_MISMATCH: ' + owner)
        return v

    def start(self, snapshot):
        if self._snapshot is not None:
            raise RuntimeHalt('TRACKER_ALREADY_STARTED')
        value = self._normalise(snapshot)
        self._snapshot = value
        self._chain = digest({'version': _VERSION, 'tracker_id': self._manifest['tracker_id'],
                              'context_id': self._context.matchup_id, 'initial_snapshot': value})
        return self.manifest()

    def audit_snapshot(self):
        self._started()
        return copy.deepcopy(self._snapshot)

    def player_view(self, seat):
        self._started()
        if seat not in _SEATS:
            raise RuntimeHalt('TRACKER_PLAYER_SEAT_REQUIRED')
        s, players = self._snapshot['state'], {}
        for owner in _SEATS:
            z = s['zones'][owner]
            players[owner] = {'hand': list(z['hand']) if owner == seat else {'count': len(z['hand'])},
                'deck': {'count': len(z['deck'])}, 'eggdeck': {'count': len(z['eggdeck'])},
                'security': {'count': len(z['security'])}, 'trash': list(z['trash']),
                'battle': copy.deepcopy(s['battle'][owner]), 'breeding': list(s['breeding'][owner])}
        return {**{name: copy.deepcopy(s[name]) for name in ('active', 'memory', 'turn', 'phase',
                'attack', 'terminal', 'resolving_option', 'winner')}, 'players': players}

    def _metrics(self, snapshot, checks):
        board = {}
        for owner in _SEATS:
            stacks = snapshot['state']['battle'][owner]
            kinds = Counter(self._card(owner, x['cards'][-1]).kind for x in stacks.values())
            sizes = [len(x['cards']) for x in stacks.values()]
            board[owner] = {'battle_card_count': len(stacks), 'digimon_count': kinds['Digimon'],
                'tamer_count': kinds['Tamer'], 'option_count': kinds['Option'], 'total_stack_cards': sum(sizes),
                'digivolution_card_count': sum(n - 1 for n in sizes), 'largest_stack_size': max(sizes, default=0)}
        return {'successful_security_checks': dict(checks), 'board': board}

    def public_metrics(self):
        self._started()
        return self._metrics(self._snapshot, self._checks)

    @staticmethod
    def _locations(snapshot):
        s, locations = snapshot['state'], {}
        for owner in _SEATS:
            for zone, cards in s['zones'][owner].items():
                for key in cards:
                    locations[key] = {'owner': owner, 'zone': zone}
            for key in s['breeding'][owner]:
                locations[key] = {'owner': owner, 'zone': 'breeding'}
            for anchor, stack in s['battle'][owner].items():
                for key in stack['cards']:
                    locations[key] = {'owner': owner, 'zone': 'battle', 'entity': stack['instance_id'] or 'anchor:' + anchor}
        resolving = s['resolving_option']
        if resolving is not None:
            for key in resolving['stack']['cards']:
                locations[key] = {'owner': resolving['seat'], 'zone': 'resolving_option'}
        return locations

    @staticmethod
    def _accepted(command, judge):
        if command.get('status') not in (None, 'EXPERIMENTAL_RESOLVED'):
            return False
        rejected = ('UNRESOLVED', 'REJECTED', 'ILLEGAL', 'HALT', 'SOFTWARE_GAP',
                    'FAILED', 'DIAGNOSTIC_SOFTWARE_ERROR')
        if judge.get('accepted') is False or any(judge.get(name) in rejected for name in ('status', 'verdict')):
            return False
        return judge.get('accepted') is True or judge.get('status') in ('PASS', 'RUNTIME_VALIDATED',
                'ENGINE_CHECKED_EXPERIMENTAL', 'ACCEPTED', 'SUPPORTED')

    @staticmethod
    def _security_check(command, before, after, result):
        if (command['command'] != 'CONFIRM_ATTACK' or not isinstance(result, dict)
                or result.get('success') is not True or result.get('checked_card') is None):
            return None
        actor = command.get('seat'); defender = 'B' if actor == 'A' else 'A'
        a, b = before['state'].get('attack'), after['state'].get('attack')
        key = result['checked_card']
        old = before['state']['zones'][defender]['security']; new = after['state']['zones'][defender]['security']
        if (actor not in _SEATS or not isinstance(a, dict) or not isinstance(b, dict)
                or a.get('controller') != actor or a.get('defender') != defender
                or a.get('target') != 'PLAYER' or a.get('window') != 'CONFIRM' or a.get('checked') is not None
                or b.get('controller') != actor or b.get('defender') != defender
                or b.get('target') != 'PLAYER' or b.get('window') != 'END' or b.get('checked') != key
                or (a.get('attacker_instance') and b.get('attacker_instance') != a['attacker_instance'])
                or (not a.get('attacker_instance') and b.get('attacker') != a.get('attacker'))
                or not old or old[-1] != key or new != old[:-1] or key in new):
            raise RuntimeHalt('TRACKER_SECURITY_CHECK_RESULT_MISMATCH')
        return actor

    @staticmethod
    def _field(snapshot):
        s, counts, entities = snapshot['state'], {}, {}
        for owner in _SEATS:
            counts[owner] = {zone: len(cards) for zone, cards in s['zones'][owner].items()}
            counts[owner].update({'breeding': len(s['breeding'][owner]), 'battle': len(s['battle'][owner])})
            entities[owner] = [{**copy.deepcopy(stack), 'anchor': anchor, 'top': stack['cards'][-1],
                               'sources': list(stack['cards'][:-1])}
                              for anchor, stack in sorted(s['battle'][owner].items())]
        return {'zone_counts': counts, 'battle_entities': entities, 'breeding': copy.deepcopy(s['breeding']),
                **{name: copy.deepcopy(s[name]) for name in ('active', 'memory', 'turn', 'phase', 'attack',
                      'pending', 'terminal', 'winner', 'resolving_option')}}

    def observe(self, command, before, after, result, judge_verdict):
        self._started()
        try:
            command, result, judge = json.loads(canonical([command, result, judge_verdict]))
        except (TypeError, ValueError) as exc:
            raise RuntimeHalt('TRACKER_OBSERVATION_NOT_SERIALIZABLE') from exc
        if (not isinstance(command, dict) or not isinstance(command.get('command'), str)
                or not command['command'] or not isinstance(judge, dict)):
            raise RuntimeHalt('TRACKER_OBSERVATION_SCHEMA_INVALID')
        prior, current = self._normalise(before), self._normalise(after)
        if canonical(prior) != canonical(self._snapshot):
            raise RuntimeHalt('TRACKER_STALE_BEFORE_SNAPSHOT')
        if any(prior[name] != current[name] for name in ('context_id', 'seed', 'first')):
            raise RuntimeHalt('TRACKER_GAME_IDENTITY_CHANGED')
        accepted = self._accepted(command, judge)
        if not accepted and canonical(prior) != canonical(current):
            raise RuntimeHalt('TRACKER_FAILED_COMMAND_CHANGED_STATE')
        if accepted and prior['state']['terminal']:
            raise RuntimeHalt('TRACKER_ACTION_AFTER_TERMINAL')
        checks = dict(self._checks)
        if accepted:
            actor = self._security_check(command, prior, current, result)
            if actor is not None:
                checks[actor] += 1
        old, new = self._locations(prior), self._locations(current)
        observation = {'sequence': len(self._observations) + 1, 'previous_observation_sha256': self._chain,
            'before_snapshot_sha256': digest(prior), 'after_snapshot_sha256': digest(current),
            'command': command, 'result': result, 'judge_verdict': judge,
            'status': 'COMMITTED' if accepted else 'FAILED_UNRATED',
            'rating_status': 'NOT_SCORED' if accepted else 'UNRATED',
            'zone_movements': [{'card': key, 'from': old[key], 'to': new[key]} for key in sorted(old) if old[key] != new[key]],
            'field': self._field(current), 'public_metrics_before': self._metrics(prior, self._checks),
            'public_metrics_after': self._metrics(current, checks)}
        observation['observation_sha256'] = digest(observation)
        self._snapshot, self._checks, self._chain = current, checks, observation['observation_sha256']
        self._observations.append(observation)
        return copy.deepcopy(observation)
