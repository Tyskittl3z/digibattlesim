"""Context-bound physical state and transactional mechanic dispatch.

This is experimental infrastructure, not a full-match runner. It cannot credit
a match or certify rules. A binding's official evidence pins source bytes; it
does not establish that its Python handler correctly implements those rules.
"""
from collections import Counter
import copy
from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import json
import random
from urllib.parse import urlparse

from match_context import MatchContext, canonical, digest, require, nonempty


class RuntimeHalt(RuntimeError):
    pass


@dataclass(frozen=True, order=True)
class PhysicalCard:
    owner: str
    card_number: str
    index: int

    @property
    def key(self):
        return f'{self.owner}:{self.card_number}#{self.index}'


@dataclass
class Stack:
    cards: list[PhysicalCard]
    suspended: bool = False
    statuses: dict = field(default_factory=dict)
    instance_id: str = ''
    played_turn: int | None = None
    ready_since_turn: int | None = None


@dataclass
class PhysicalState:
    zones: dict
    battle: dict
    breeding: dict
    active: str
    memory: int = 0
    turn: int = 0
    terminal: bool = False
    once_used: set = field(default_factory=set)
    pending: list = field(default_factory=list)
    effect_sequence: int = 0
    entity_sequence: int = 0
    phase: str = 'SCENARIO'
    preparation: dict = field(default_factory=lambda:{'started':False,'choices':[]})
    attack: dict | None = None
    resolving_option: dict | None = None
    winner: str | None = None
    terminal_reason: str | None = None


@dataclass(frozen=True)
class OfficialEvidence:
    url: str
    sha256: str
    locator: str
    _body: bytes

    @classmethod
    def from_bytes(cls, url, body, expected_sha256, locator):
        parsed = urlparse(url)
        require(parsed.scheme == 'https' and parsed.hostname is not None
                and (parsed.hostname == 'digimoncard.com'
                     or parsed.hostname.endswith('.digimoncard.com')),
                'Official HTTPS Digimon source required')
        require(isinstance(body, bytes) and bool(body), 'Nonempty source bytes required')
        require(hashlib.sha256(body).hexdigest() == expected_sha256, 'Official source hash mismatch')
        require(nonempty(locator), 'Meaningful source locator required')
        return cls(url, expected_sha256, locator, body)

    def manifest(self):
        # Revalidate even a directly constructed instance.
        self.from_bytes(self.url, self._body, self.sha256, self.locator)
        return {'url': self.url, 'sha256': self.sha256, 'locator': self.locator}


@dataclass(frozen=True)
class MechanicBinding:
    card_number: str
    effect_id: str
    field: str
    definition_sha256: str
    text_sha256: str
    evidence: tuple[OfficialEvidence, ...]
    handler: object

    def manifest(self):
        require(self.field in ('main_text', 'inherited_text', 'security_text'), 'Unknown effect field')
        require(nonempty(self.effect_id) and callable(self.handler), 'Effect identity/handler required')
        require(isinstance(self.evidence, tuple) and bool(self.evidence), 'Pinned official evidence required')
        require(all(isinstance(e, OfficialEvidence) for e in self.evidence), 'Invalid official evidence')
        # Bind full module bytes as well as the function, so helper edits also
        # invalidate the software pack. There is no runtime effect inference.
        module = inspect.getmodule(self.handler)
        require(module is not None and nonempty(getattr(module, '__file__', None)),
                'Handler must come from an inspectable source module')
        from pathlib import Path
        module_sha = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        return {'card_number': self.card_number, 'effect_id': self.effect_id, 'field': self.field,
                'definition_sha256': self.definition_sha256, 'text_sha256': self.text_sha256,
                'evidence': [e.manifest() for e in self.evidence],
                'handler': self.handler.__module__ + '.' + self.handler.__qualname__,
                'handler_module_sha256': module_sha, 'status': 'EXPERIMENTAL_UNREVIEWED'}


@dataclass(frozen=True)
class MechanicRegistry:
    bindings: tuple[MechanicBinding, ...] = ()

    def __post_init__(self):
        require(isinstance(self.bindings, tuple), 'Immutable bindings tuple required')
        seen = set()
        for binding in self.bindings:
            binding.manifest()
            key = (binding.card_number, binding.effect_id, binding.field)
            require(key not in seen, 'Duplicate mechanic binding')
            seen.add(key)

    def manifest(self):
        return sorted((b.manifest() for b in self.bindings),
                      key=lambda b: (b['card_number'], b['effect_id'], b['field']))

    def lookup(self, number, effect_id, field_):
        for binding in self.bindings:
            if (binding.card_number, binding.effect_id, binding.field) == (number, effect_id, field_):
                return binding
        raise RuntimeHalt(f'UNSUPPORTED_MECHANIC: {number} {field_} {effect_id}')


def state_value(value):
    if isinstance(value, PhysicalCard):
        return value.key
    if isinstance(value, Stack):
        return {'cards': [c.key for c in value.cards], 'suspended': value.suspended,
                'statuses': state_value(value.statuses), 'instance_id': value.instance_id,
                'played_turn':value.played_turn,'ready_since_turn':value.ready_since_turn}
    if isinstance(value, dict):
        return {k: state_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [state_value(v) for v in value]
    if isinstance(value, set):
        return sorted(state_value(v) for v in value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise RuntimeHalt('UNSERIALIZABLE_STATE: ' + type(value).__name__)


def audit_value(value):
    """Invalid API inputs still receive a serializable diagnostic envelope."""
    try:
        return json.loads(canonical(state_value(value)))
    except (RuntimeHalt, TypeError, ValueError, RecursionError):
        return {'unrecordable_type': type(value).__module__ + '.' + type(value).__qualname__,
                'status': 'INVALID_INPUT_NOT_REPLAYABLE'}


class ContextRuntime:
    """No automatic pilot, phase loop, result counter or certification path.

    The initial state is an undealt shuffled physical deck; it is not a completed
    opening, forced mulligan decline, partial match or fact-finding match.
    """
    certification = 'EXPERIMENTAL'
    matches_played = 0

    def __init__(self, context, seed, first, registry=None, *, allow_experimental=False):
        require(isinstance(context, MatchContext), 'MatchContext required')
        require(type(seed) is int and seed >= 0, 'Nonnegative integer seed required')
        require(first in ('A', 'B'), 'Starting seat required')
        require(type(allow_experimental) is bool, 'Explicit experimental flag required')
        self.context, self.seed, self.first = context, seed, first
        self.registry = registry or MechanicRegistry()
        self.allow_experimental = allow_experimental
        self.rng = random.Random(seed)
        self.events = []
        self.halted = False
        zones = {}
        for seat in ('A', 'B'):
            deck = context.deck(seat)
            zones[seat] = {'deck': [PhysicalCard(seat, n, i) for n, q in deck.main for i in range(1, q+1)],
                           'eggdeck': [PhysicalCard(seat, n, i) for n, q in deck.eggs for i in range(1, q+1)],
                           'hand': [], 'security': [], 'trash': []}
            self.rng.shuffle(zones[seat]['deck'])
            self.rng.shuffle(zones[seat]['eggdeck'])
        self.state = PhysicalState(zones, {'A': {}, 'B': {}}, {'A': [], 'B': []}, first)
        self._pack_manifest = canonical(self.registry.manifest())
        self.verify()

    @property
    def execution_id(self):
        from pathlib import Path
        code = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in ('context_runtime.py', 'match_context.py', 'effect_scheduler.py','match_preparation.py',
                             'phase_flow.py','breeding_evolution.py','main_actions.py',
                             'context_evolution.py','search_effects.py','selected_mechanics.py',
                             'turn_flow.py','battlefield_scope.py','attack_flow.py','printed_triggers.py',
                             'selected_contexts.py','matchup_readiness.py',
                             'on_play_effects.py','effect_grants.py','option_actions.py',
                             'aero_effects.py','battle_evolution.py','basic_event_dependencies.py',
                             'tamer_play_effects.py','security_tamer.py','rina_unsuspend_effects.py',
                             'ex13_ulforce_effects.py','rina_reactivation.py','return_effects.py')}
        return digest({'context_id': self.context.matchup_id, 'packs': self.registry.manifest(),
                       'engine': code, 'allow_experimental': self.allow_experimental})

    def snapshot(self):
        # RNG and hidden contents are audit-only, never a pilot input.
        return {'context_id': self.context.matchup_id, 'execution_id': self.execution_id,
                'seed': self.seed, 'first': self.first,
                'rng_state': state_value(self.rng.getstate()),
                'state': {k: state_value(v) for k, v in vars(self.state).items()}}

    def public_view(self, seat):
        self.context.deck(seat)
        players = {}
        for owner in ('A', 'B'):
            zones = self.state.zones[owner]
            players[owner] = {
                'hand': [c.key for c in zones['hand']] if seat == owner else {'count': len(zones['hand'])},
                'deck': {'count': len(zones['deck'])},
                'eggdeck': {'count': len(zones['eggdeck'])},
                'security': {'count': len(zones['security'])},
                'trash': [c.key for c in zones['trash']],
                'battle': state_value(self.state.battle[owner]),
                'breeding': [c.key for c in self.state.breeding[owner]],
            }
        return {'active': self.state.active, 'memory': self.state.memory, 'turn': self.state.turn,
                'phase':self.state.phase,
                'attack':({k: state_value(v) for k, v in self.state.attack.items()
                           if k != 'deferred_depth'} if self.state.attack is not None else None),
                'terminal':self.state.terminal,
                'resolving_option':state_value(self.state.resolving_option),
                'winner':self.state.winner,
                'players': players}

    def verify(self):
        state = self.state
        if any(not isinstance(getattr(state, name), dict)
               or set(getattr(state, name)) != {'A', 'B'}
               for name in ('zones', 'battle', 'breeding')):
            raise RuntimeHalt('PHYSICAL_PLAYER_SCHEMA_INVALID')
        if type(state.memory) is not int or not -10 <= state.memory <= 10:
            raise RuntimeHalt('MEMORY_GAUGE_INVALID')
        if state.active not in ('A', 'B') or type(state.terminal) is not bool:
            raise RuntimeHalt('TURN_STATE_INVALID')
        if type(state.turn) is not int or state.turn<0 or state.phase not in (
                'SCENARIO','INITIAL_HANDS','START_OF_TURN','TURN_START_EFFECTS','UNSUSPEND','DRAW','BREEDING',
                'BREEDING_MOVING_EFFECTS','MAIN','END_OF_TURN'):
            raise RuntimeHalt('TURN_PHASE_INVALID')
        resolving = state.resolving_option
        if resolving is not None:
            if (not isinstance(resolving, dict) or set(resolving) != {'seat','stack'}
                    or resolving['seat'] not in ('A','B')
                    or not isinstance(resolving['stack'], Stack)
                    or len(resolving['stack'].cards) != 1
                    or not isinstance(resolving['stack'].cards[0], PhysicalCard)
                    or resolving['stack'].cards[0].owner != resolving['seat']
                    or self.context.card(resolving['seat'], resolving['stack'].cards[0].card_number).kind != 'Option'):
                raise RuntimeHalt('RESOLVING_OPTION_SCHEMA_INVALID')
        for seat in ('A', 'B'):
            if set(state.zones[seat]) != {'deck', 'eggdeck', 'hand', 'security', 'trash'}:
                raise RuntimeHalt('PHYSICAL_ZONE_SCHEMA_INVALID')
            observed = [c for zone in state.zones[seat].values() for c in zone]
            observed.extend(state.breeding[seat])
            if resolving is not None and resolving['seat'] == seat:
                observed.extend(resolving['stack'].cards)
            for anchor, stack in state.battle[seat].items():
                if not isinstance(stack, Stack) or not stack.cards or stack.cards[-1].key != anchor:
                    raise RuntimeHalt('STACK_ANCHOR_MISMATCH: ' + seat + ' ' + anchor)
                if type(stack.suspended) is not bool:
                    raise RuntimeHalt('STACK_ORIENTATION_INVALID')
                observed.extend(stack.cards)
            if any(not isinstance(c, PhysicalCard) or c.owner != seat for c in observed):
                raise RuntimeHalt('PHYSICAL_CARD_OWNER_MISMATCH: ' + seat)
            expected = Counter(PhysicalCard(seat, n, i) for n, i in self.context.inventory(seat))
            actual = Counter(observed)
            if expected != actual:
                raise RuntimeHalt('PHYSICAL_CARD_MISMATCH: ' + seat)
            if any(self.context.card(seat, c.card_number).kind != 'Digi-Egg'
                   for c in state.zones[seat]['eggdeck']):
                raise RuntimeHalt('EGG_DECK_TYPE_INVALID')
        # Also fail on unrecordable status, pending-choice or OPT state.
        canonical(state_value(vars(state)))
        from effect_scheduler import validate_pending
        validate_pending(self)
        from attack_flow import validate_attack
        validate_attack(state)
        if state.winner is not None and (not state.terminal or state.winner not in ('A','B') or not isinstance(state.terminal_reason,str)):
            raise RuntimeHalt('TERMINAL_RESULT_INVALID')

    def _source(self, seat, source_key, field_):
        self.context.deck(seat)
        if field_ not in ('main_text', 'inherited_text', 'security_text'):
            raise RuntimeHalt('UNKNOWN_EFFECT_FIELD')
        resolving = self.state.resolving_option
        if resolving is not None and resolving['seat'] == seat and field_ in ('main_text', 'security_text'):
            physical = resolving['stack'].cards[-1]
            if physical.key == source_key and (field_ != 'security_text' or
                    (self.state.attack is not None and self.state.attack['checked'] == source_key)):
                return physical
        for stack in self.state.battle[seat].values():
            pool = stack.cards[:-1] if field_ == 'inherited_text' else stack.cards[-1:]
            for card in pool:
                if card.key == source_key:
                    return card
        raise RuntimeHalt('SOURCE_NOT_ACTIVE: ' + str(source_key))

    def dispatch(self, effect_id, seat, source_key, choice, *, field_='main_text', pending_id=None):
        """Resolve a scenario effect atomically or preserve a reproducible halt.

        Pending trigger scheduling and full game timing are not implemented here.
        A handler must halt if it cannot close its dependent effects itself.
        """
        if self.halted:
            raise RuntimeHalt('ALREADY_HALTED')
        before = None
        try:
            before = self.snapshot()
            # Validate before invoking any handler. JSON roundtrip also detaches
            # caller-owned data and rejects NaN or unrecordable objects.
            choice = json.loads(canonical(choice))
            self.verify()
            if self.state.terminal:
                raise RuntimeHalt('ACTION_AFTER_TERMINAL')
            if self.state.attack and pending_id is None:
                raise RuntimeHalt('ATTACK_PROCESSING_PENDING')
            selected_pending = None
            if pending_id is not None:
                from effect_scheduler import pending_options
                selected_pending = next((p for p in pending_options(self,seat) if p['id']==pending_id),None)
                if (selected_pending is None or (selected_pending['effect_id'], selected_pending['source'],
                        selected_pending['field']) != (effect_id,source_key,field_)):
                    raise RuntimeHalt('PENDING_CHOICE_INVALID')
            elif self.state.pending:
                raise RuntimeHalt('PENDING_EFFECTS_REQUIRE_RESOLUTION')
            if canonical(self.registry.manifest()) != self._pack_manifest:
                raise RuntimeHalt('PACK_CHANGED_RESTART_REQUIRED')
            source = self._source(seat, source_key, field_)
            definition = self.context.card(seat, source.card_number)
            binding = self.registry.lookup(source.card_number, effect_id, field_)
            if binding.definition_sha256 != definition.definition_sha256 or binding.text_sha256 != hashlib.sha256(
                    definition.effect_text(field_).encode('utf-8')).hexdigest():
                raise RuntimeHalt('PACK_TEXT_BINDING_MISMATCH')
            if not self.allow_experimental:
                raise RuntimeHalt('UNREVIEWED_MECHANIC_PACK')
            # A failed handler receives only a trial state and RNG. Its partial
            # zone movements and decisions can never leak into the live trace.
            trial = copy.deepcopy(self)
            if selected_pending:
                trial.state.pending = [p for p in trial.state.pending if p['id']!=pending_id]
            trial._resolution_depth = selected_pending['depth'] if selected_pending else -1
            trial._activated_effect=(effect_id,seat,source_key,field_,pending_id)
            trial._activated_pending=copy.deepcopy(selected_pending)
            result = binding.handler(trial, seat, source_key, copy.deepcopy(choice))
            from effect_scheduler import prune_pending
            prune_pending(trial)
            trial._finish_main_processing()
            trial.verify()
            event = json.loads(canonical({
                'type': 'MECHANIC_RESOLVED', 'status': 'EXPERIMENTAL',
                'context_id': self.context.matchup_id, 'execution_id': self.execution_id,
                'turn': trial.state.turn, 'seat': seat, 'source': source_key,
                'effect_id': effect_id, 'field': field_, 'choice': choice, 'result': result,
                'pending_id': pending_id}))
            # Validate the whole future trace BEFORE committing physical state.
            canonical(trial.events + [event])
            self.state = trial.state
            self.rng = trial.rng
            self.events = trial.events + [event]
            return copy.deepcopy(event['result'])
        except Exception as exc:
            self.halted = True
            self.events.append({'type': 'HALT', 'status': 'HALT', 'seed': self.seed,
                                'first': self.first, 'context_id': self.context.matchup_id,
                                'turn': self.state.turn, 'seat': audit_value(seat), 'source': audit_value(source_key),
                                'effect_id': audit_value(effect_id), 'field': audit_value(field_),
                                'pending_id':audit_value(pending_id),
                                'choice': audit_value(choice), 'reason': str(exc),
                                'exception': type(exc).__name__,
                                'before': before if before is not None else {
                                    'status': 'SNAPSHOT_UNAVAILABLE_INVALID_STATE',
                                    'state_diagnostic': audit_value(vars(self.state))}})
            if isinstance(exc, RuntimeHalt):
                raise
            raise RuntimeHalt('MECHANIC_ERROR: ' + str(exc)) from exc

    def settle_pending(self):
        """Apply automatic source-loss/OPT cancellations, never optional choices."""
        if self.halted or self.state.terminal:
            raise RuntimeHalt('SETTLE_AFTER_HALT_OR_TERMINAL')
        from effect_scheduler import prune_pending
        def settle(trial,seat,choice):
            return {'cancelled':prune_pending(trial)}
        return self._control_command('SETTLE_PENDING',self.state.active,None,settle,allow_pending=True)

    def _control_command(self,kind,seat,choice,operation,*,allow_pending=False,allow_attack=False):
        """Atomic trusted rules primitive; never an unbound pilot action API."""
        if self.halted:
            raise RuntimeHalt('ALREADY_HALTED')
        before=None
        try:
            before=self.snapshot()
            choice=json.loads(canonical(choice))
            self.context.deck(seat)
            self.verify()
            if self.state.terminal:
                raise RuntimeHalt('ACTION_AFTER_TERMINAL')
            if self.state.attack is not None and not allow_attack:
                raise RuntimeHalt('ATTACK_PROCESSING_PENDING')
            deferred = (self.state.attack or {}).get('deferred_depth') if allow_attack else None
            attack_pending_ok = (deferred is not None and all(
                effect['depth'] <= deferred for effect in self.state.pending))
            if self.state.pending and not allow_pending and not attack_pending_ok:
                raise RuntimeHalt('PENDING_EFFECTS_REQUIRE_RESOLUTION')
            if canonical(self.registry.manifest())!=self._pack_manifest:
                raise RuntimeHalt('PACK_CHANGED_RESTART_REQUIRED')
            trial=copy.deepcopy(self)
            result=operation(trial,seat,choice)
            trial._finish_main_processing()
            trial.verify()
            event=json.loads(canonical({'type':'CONTROL_RESOLVED','kind':kind,'status':'EXPERIMENTAL',
                    'context_id':self.context.matchup_id,'execution_id':self.execution_id,
                    'seat':seat,'choice':choice,'result':result,'turn':trial.state.turn}))
            canonical(trial.events+[event])
            self.state,self.rng,self.events=trial.state,trial.rng,trial.events+[event]
            return copy.deepcopy(event['result'])
        except Exception as exc:
            self.halted=True
            self.events.append({'type':'HALT','status':'HALT','seed':self.seed,'first':self.first,
                'context_id':self.context.matchup_id,'command':kind,'seat':audit_value(seat),
                'choice':audit_value(choice),'reason':str(exc),'exception':type(exc).__name__,
                'before':before if before is not None else {'status':'SNAPSHOT_UNAVAILABLE_INVALID_STATE'}})
            if isinstance(exc,RuntimeHalt):raise
            raise RuntimeHalt('CONTROL_COMMAND_ERROR: '+str(exc)) from exc

    def _finish_main_processing(self):
        # Turn-end conditions are checked after all current processing, including
        # derived effects. END_OF_TURN is an explicit unimplemented window.
        if self.state.phase=='MAIN' and self.state.memory<0 and not self.state.pending and not self.state.attack and not self.state.resolving_option and not self.state.terminal:
            self.state.phase='END_OF_TURN'
