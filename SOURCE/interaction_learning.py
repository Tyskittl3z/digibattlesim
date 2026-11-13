"""Fresh context-bound public-board learning, updated only between eligible games.

Mean observed board reward drives preferences. Wins/losses are separate outcome
associations, never winning probabilities or judge/strategy certification.
"""
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import re

from context_runtime import RuntimeHalt
from field_tracker import FieldTracker
from interaction_scoring import CRITERIA, CRITERIA_SHA256, criteria_manifest, score_transition
from match_context import canonical, digest
from named_player_bots import NamedPlayerBot


VERSION = 'fresh-observed-board-learning-v1'
_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
EPSILON = 0.10
MINIMUM_SUPPORT = 3
_CONFIG = {'epsilon': EPSILON, 'minimum_independent_games': MINIMUM_SUPPORT,
           'reward': 'PER_GAME_MEAN_IMMEDIATE_OBSERVED_BOARD_REWARD',
           'outcome_association': 'SEPARATE_WINS_LOSSES', 'future_return': None,
           'keys': 'WHITELISTED_OWN_PUBLIC_FEATURES_WITHOUT_PHYSICAL_COPY_OR_TRANSIENT_IDS'}
_HEX = re.compile(r'[0-9a-f]{64}\Z')
_PHYSICAL = re.compile(r'([AB]):([A-Z][A-Z0-9]*-\d+)#([1-9]\d*)\Z')
_NUMBER = re.compile(r'[A-Z][A-Z0-9]*-\d+\Z')
_EFFECT = re.compile(r'[A-Z][A-Z0-9]*-\d+\.[a-z][a-z0-9_]*\Z')
_PENDING = frozenset(('id', 'seat', 'source', 'effect_id', 'field', 'instance', 'depth'))
_VIEW = frozenset(('active', 'memory', 'turn', 'phase', 'attack', 'terminal', 'winner', 'players', 'resolving_option'))
_PLAYER = frozenset(('hand', 'deck', 'eggdeck', 'security', 'trash', 'battle', 'breeding'))
_STACK = frozenset(('cards', 'suspended', 'statuses', 'instance_id', 'played_turn', 'ready_since_turn'))
_ATTACK = frozenset(('attacker', 'attacker_instance', 'target', 'target_instance', 'controller',
                     'defender', 'window', 'counter_used', 'block_used', 'checked', 'deferred_depth'))
_METRIC_BOARD = frozenset(('battle_card_count', 'digimon_count', 'tamer_count', 'option_count',
                          'total_stack_cards', 'digivolution_card_count', 'largest_stack_size'))
_BASE_RECORD = frozenset(('decision', 'public_view_sha256', 'candidates', 'chosen', 'reason', 'bot_id'))
_LEARNING = frozenset(('context_id', 'seat', 'state_key', 'action_key', 'input_state_id', 'mode',
                      'support', 'epsilon', 'eligible_choice', 'rng_before', 'rng_after', 'rng_draw_protocol'))
_MODES = frozenset(('NAMED_PRIOR', 'LEARNED_BOARD_REWARD', 'EXPLORATION',
                    'FIXED_BOTTOM_ORDER', 'PUBLIC_STATE_TEXT'))
_PROCEDURAL = frozenset(('BEGIN_PREPARATION', 'REDRAW_CHOICE', 'ADVANCE_PHASE', 'FINISH_TURN',
                        'END_ATTACK', 'SETTLE_PENDING', 'BOTTOM_ORDER'))


def _require(condition, message):
    if not condition:
        raise RuntimeHalt('LEARNING_' + message)


def _hash(value):
    return isinstance(value, str) and _HEX.fullmatch(value) is not None


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _json(value):
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeHalt('LEARNING_JSON_SCHEMA') from exc


def _physical(value, seat):
    match = _PHYSICAL.fullmatch(value) if isinstance(value, str) else None
    _require(match is not None, 'PHYSICAL_CARD_REQUIRED')
    return {'role': 'OWN' if match[1] == seat else 'OPPONENT', 'card': match[2]}


def _pending(value):
    _require(isinstance(value, dict) and not set(value) - _PENDING, 'PUBLIC_PENDING_SCHEMA')
    for key, item in value.items():
        if key == 'depth': valid = type(item) is int and item >= 0
        elif key == 'seat': valid = item in ('A', 'B')
        elif key == 'field': valid = item in ('main_text', 'inherited_text', 'security_text')
        elif key == 'source': valid = isinstance(item, str) and _PHYSICAL.fullmatch(item) is not None
        elif key == 'effect_id': valid = isinstance(item, str) and _EFFECT.fullmatch(item) is not None
        else: valid = isinstance(item, str) and bool(item)
        _require(valid, 'PUBLIC_PENDING_FIELD')
    return copy.deepcopy(value)


def _decision(value):
    _require(isinstance(value, dict) and not set(value) - {'kind', 'effect_id', 'source', 'selected_pending', 'public_metrics'},
             'PUBLIC_DECISION_SCHEMA')
    if 'kind' in value:
        _require(isinstance(value['kind'], str) and bool(value['kind']), 'DECISION_KIND')
    if 'effect_id' in value:
        _require(isinstance(value['effect_id'], str) and _EFFECT.fullmatch(value['effect_id']) is not None, 'DECISION_EFFECT')
    if 'source' in value:
        _physical(value['source'], 'A')
    if 'selected_pending' in value:
        _pending(value['selected_pending'])
    if 'public_metrics' in value:
        _metrics(value['public_metrics'])
    return _json(value)


def _metrics(value):
    _require(isinstance(value, dict) and set(value) == {'board', 'successful_security_checks'}, 'PUBLIC_METRICS_SCHEMA')
    for key in ('board', 'successful_security_checks'):
        _require(isinstance(value[key], dict) and set(value[key]) == {'A', 'B'}, 'PUBLIC_METRICS_SEATS')
    for seat in ('A', 'B'):
        _require(type(value['successful_security_checks'][seat]) is int and value['successful_security_checks'][seat] >= 0,
                 'PUBLIC_METRICS_CHECKS')
        board = value['board'][seat]
        _require(isinstance(board, dict) and set(board) == _METRIC_BOARD
                 and all(type(n) is int and n >= 0 for n in board.values()), 'PUBLIC_METRICS_BOARD')
    return copy.deepcopy(value)


def _action(candidate, seat):
    """Explicit action grammar; no recursive canonicalization of metadata."""
    if candidate is None or type(candidate) is bool:
        return candidate
    if isinstance(candidate, str):
        if _PHYSICAL.fullmatch(candidate): return _physical(candidate, seat)
        _require(candidate == 'PAY_NO_EFFECT' or _EFFECT.fullmatch(candidate) is not None, 'ACTION_STRING')
        return candidate
    if isinstance(candidate, list):
        normalized = [_physical(key, seat) for key in candidate]
        _require(len(set(candidate)) == len(candidate), 'ACTION_DUPLICATE_PHYSICAL_CARD')
        return sorted(normalized, key=canonical)
    _require(isinstance(candidate, dict), 'ACTION_SCHEMA')
    if 'effect_id' in candidate and 'id' in candidate:
        _pending(candidate)
        _require({'id', 'seat', 'source', 'effect_id', 'field'} <= set(candidate), 'ACTION_PENDING_REQUIRED_FIELDS')
        return {k: (_physical(candidate[k], seat) if k == 'source' else
                    ('OWN' if candidate[k] == seat else 'OPPONENT') if k == 'seat' else candidate[k])
                for k in ('seat', 'source', 'effect_id', 'field') if k in candidate}
    if set(candidate) == {'redraw'}:
        _require(type(candidate['redraw']) is bool, 'ACTION_REDRAW')
        return copy.deepcopy(candidate)
    if set(candidate) == {'card', 'status'}:
        _require(isinstance(candidate['status'], str), 'ACTION_RESPONSE')
        return {'card': None if candidate['card'] is None else _physical(candidate['card'], seat), 'status': candidate['status']}
    if 'kind' in candidate:
        fields = {
            'PASS_TURN': {'kind'}, 'DECLARE_ATTACK': {'kind', 'attacker', 'target'},
            'PLAY_CARD': {'kind', 'hand_key', 'printed_cost', 'legality'},
            'USE_OPTION': {'kind', 'hand_key', 'printed_cost', 'legality'},
            'UNKNOWN_OPTION_ACTION': {'kind', 'hand_key', 'printed_cost', 'legality'},
            'OPTION_DELAY': {'kind', 'source_key', 'legality'},
            'UNKNOWN_DELAY_ACTION': {'kind', 'source_key', 'legality'},
            'BREEDING_CHOICE': {'kind', 'action'},
        }
        evolution = {'kind', 'source_key', 'hand_key', 'route_index', 'cost', 'basis', 'printed_condition',
                     'definition_sha256', 'status', 'legality'}
        for kind in ('BATTLE_EVOLUTION', 'BREEDING_EVOLUTION', 'UNKNOWN_BATTLE_EVOLUTION'):
            fields[kind] = evolution
        kind = candidate['kind']
        _require(isinstance(kind, str) and kind in fields and not set(candidate) - fields[kind], 'ACTION_FIELDS')
        required = {
            'PASS_TURN': {'kind'}, 'DECLARE_ATTACK': {'kind', 'attacker', 'target'},
            'PLAY_CARD': {'kind', 'hand_key'}, 'USE_OPTION': {'kind', 'hand_key'},
            'UNKNOWN_OPTION_ACTION': {'kind', 'hand_key'},
            'OPTION_DELAY': {'kind', 'source_key'}, 'UNKNOWN_DELAY_ACTION': {'kind', 'source_key'},
            'BREEDING_CHOICE': {'kind', 'action'},
        }
        _require(required.get(kind, {'kind', 'source_key', 'hand_key', 'route_index'}) <= set(candidate),
                 'ACTION_REQUIRED_FIELDS')
        if kind == 'BREEDING_CHOICE':
            _require(candidate['action'] in ('skip', 'hatch', 'promote'), 'ACTION_BREEDING_ACTION')
    elif {'source_key', 'hand_key', 'route_index'} <= set(candidate):
        _require(set(candidate) == {'source_key', 'hand_key', 'route_index'}, 'ACTION_EVOLUTION_FIELDS')
    else:
        _require(not set(candidate) - {'activate', 'evolution', 'return_key', 'play_key'}
                 and type(candidate.get('activate')) is bool
                 and set(candidate) in ({'activate'}, {'activate', 'evolution'},
                                        {'activate', 'return_key', 'play_key'}), 'ACTION_DELAY_FIELDS')
    result = {}
    for key, item in candidate.items():
        if key in ('attacker', 'target', 'hand_key', 'source_key', 'return_key', 'play_key'):
            _require(item is not None or key in ('return_key', 'play_key'), 'ACTION_PHYSICAL_CARD_REQUIRED')
            result[key] = item if key == 'target' and item == 'PLAYER' else None if item is None else _physical(item, seat)
        elif key == 'evolution':
            _require(item is None or isinstance(item, dict) and set(item) == {'source_key', 'hand_key', 'route_index'},
                     'ACTION_DELAY_EVOLUTION_SCHEMA')
            result[key] = None if item is None else _action(item, seat)
        elif key in ('route_index', 'cost', 'printed_cost'):
            _require(type(item) is int and item >= 0, 'ACTION_COST_OR_ROUTE')
            result[key] = item
        elif key == 'activate':
            _require(type(item) is bool, 'ACTION_ACTIVATE'); result[key] = item
        else:
            _require(isinstance(item, str), 'ACTION_FIELD_TYPE')
            if key not in ('legality', 'definition_sha256', 'status'):
                result[key] = item
    return result


def _action_cards(candidate):
    """Physical leaves of the already validated, explicit action grammar."""
    if isinstance(candidate, str):
        return [candidate] if _PHYSICAL.fullmatch(candidate) else []
    if isinstance(candidate, list):
        return list(candidate)
    if not isinstance(candidate, dict):
        return []
    keys = ('source', 'attacker', 'target', 'card', 'hand_key', 'source_key', 'return_key', 'play_key')
    cards = [candidate[k] for k in keys if isinstance(candidate.get(k), str) and _PHYSICAL.fullmatch(candidate[k])]
    if candidate.get('evolution') is not None:
        cards.extend(_action_cards(candidate['evolution']))
    return cards


def _rng(envelope):
    expected = {'version', 'context_id', 'seat', 'policy_seed', 'input_state_id', 'state', 'rng_sha256'}
    _require(isinstance(envelope, dict) and set(envelope) == expected, 'RNG_SCHEMA')
    _require(envelope['version'] == 1 and type(envelope['version']) is int
             and _hash(envelope['context_id']) and envelope['seat'] in ('A', 'B')
             and type(envelope['policy_seed']) is int and envelope['policy_seed'] >= 0
             and _hash(envelope['input_state_id']) and _hash(envelope['rng_sha256']), 'RNG_IDENTITY')
    state = envelope['state']
    _require(isinstance(state, list) and len(state) == 3 and type(state[0]) is int and state[0] == 3
             and isinstance(state[1], list) and len(state[1]) == 625
             and all(type(n) is int and 0 <= n <= 0xffffffff for n in state[1][:-1])
             and type(state[1][-1]) is int and 0 <= state[1][-1] <= 624
             and (state[2] is None or type(state[2]) is float and math.isfinite(state[2])), 'RNG_STATE')
    _require(digest({k: v for k, v in envelope.items() if k != 'rng_sha256'}) == envelope['rng_sha256'], 'RNG_HASH')
    generator = random.Random()
    try:
        generator.setstate((state[0], tuple(state[1]), state[2]))
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeHalt('LEARNING_RNG_STATE') from exc
    return generator


def verify_decision_rng(record, before_rng=None):
    """Verify saved policy randomness without calling a bot or choosing again."""
    _require(isinstance(record, dict) and isinstance(record.get('learning'), dict), 'RNG_RECORD')
    learning = record['learning']
    _require(set(learning) == _LEARNING and isinstance(learning['mode'], str) and learning['mode'] in _MODES
             and type(learning['epsilon']) is float and learning['epsilon'] ==
             (0.0 if learning['mode'] == 'PUBLIC_STATE_TEXT' else EPSILON)
             and type(learning['support']) is int and learning['support'] >= 0
             and type(learning['eligible_choice']) is bool
             and all(_hash(learning[k]) for k in ('context_id', 'state_key', 'action_key', 'input_state_id')),
             'RNG_LEARNING_SCHEMA')
    decision = _decision(record.get('decision'))
    before, after = learning['rng_before'], learning['rng_after']
    generator = _rng(before); _rng(after)
    if before_rng is not None:
        _require(before == before_rng, 'RNG_CHAIN')
    _require(all(before[k] == after[k] for k in ('version', 'context_id', 'seat', 'policy_seed', 'input_state_id')),
             'RNG_IDENTITY_CHANGED')
    _require(all(before[k] == learning[k] for k in ('context_id', 'seat', 'input_state_id')), 'RNG_RECORD_IDENTITY')
    choices = record.get('candidates')
    fixed = learning['mode'] == 'FIXED_BOTTOM_ORDER'
    _require(isinstance(choices, list) and (fixed or bool(choices)), 'RNG_CANDIDATES')
    for candidate in choices:
        _action(candidate, learning['seat'])
    draw = len(choices) > 1 and not fixed and learning['mode'] != 'PUBLIC_STATE_TEXT'
    explored = generator.random() < EPSILON if draw else False
    index = generator.randrange(len(choices)) if explored else None
    protocol = {'random': draw, 'randrange': len(choices) if explored else None,
                'chosen_index': index}
    _require(learning['rng_draw_protocol'] == protocol and (learning['mode'] == 'EXPLORATION') == explored,
             'RNG_DRAW_PROTOCOL')
    if fixed:
        _require(decision.get('kind') == 'BOTTOM_ORDER'
                 and all(isinstance(key, str) and _PHYSICAL.fullmatch(key) for key in choices)
                 and record.get('chosen') == sorted(choices) and not learning['eligible_choice'], 'RNG_BOTTOM_ORDER')
    else:
        _require(any(canonical(record.get('chosen')) == canonical(c) for c in choices), 'RNG_CHOSEN_NONCANDIDATE')
        if explored:
            _require(canonical(record['chosen']) == canonical(choices[index]), 'RNG_EXPLORATION_CHOICE')
    _require(_json(generator.getstate()) == after['state'], 'RNG_TRANSITION')
    return copy.deepcopy(after)


def _tables(games):
    tables = {'A': {}, 'B': {}}
    for game_id in sorted(games):
        game = games[game_id]
        for row in game['observations']:
            seat, state, action = row['seat'], row['state_key'], row['action_key']
            entry = tables[seat].setdefault(state, {}).setdefault(action,
                {'independent_games': 0, 'reward_sum': 0.0, 'mean_reward': 0.0, 'wins': 0, 'losses': 0})
            entry['independent_games'] += 1
            entry['reward_sum'] += row['mean_reward']
            _require(_number(entry['reward_sum']), 'REWARD_OVERFLOW')
            entry['mean_reward'] = entry['reward_sum'] / entry['independent_games']
            entry['wins' if game['winner'] == seat else 'losses'] += 1
    return tables


class LearningState:
    def __init__(self):
        self._context_id, self._games, self._tables = None, {}, {'A': {}, 'B': {}}

    def _body(self):
        return {'version': VERSION, 'context_id': self._context_id, 'criterion_sha256': CRITERIA_SHA256,
                'configuration': copy.deepcopy(_CONFIG), 'games': copy.deepcopy(self._games), 'tables': copy.deepcopy(self._tables)}

    @property
    def state_id(self):
        return digest(self._body())

    def export(self):
        body = self._body()
        return {**body, 'state_id': digest(body)}

    @classmethod
    def from_dict(cls, exported):
        value = _json(exported)
        _require(isinstance(value, dict) and set(value) == {'version', 'context_id', 'criterion_sha256', 'configuration', 'games', 'tables', 'state_id'}, 'STATE_SCHEMA')
        _require(value['version'] == VERSION and value['criterion_sha256'] == CRITERIA_SHA256
                 and canonical(value['configuration']) == canonical(_CONFIG) and _hash(value['state_id'])
                 and digest({k: v for k, v in value.items() if k != 'state_id'}) == value['state_id'], 'STATE_HASH_OR_CONFIGURATION')
        games, context = value['games'], value['context_id']
        _require(isinstance(games, dict) and (context is None or _hash(context))
                 and bool(games) == (context is not None), 'STATE_CONTEXT')
        for game_id, game in games.items():
            _require(_hash(game_id) and isinstance(game, dict)
                     and set(game) == {'context_id', 'ordinal', 'winner', 'payload_sha256', 'input_state_id', 'observations'}
                     and game['context_id'] == context and type(game['ordinal']) is int and game['ordinal'] >= 0
                     and game['winner'] in ('A', 'B') and _hash(game['payload_sha256'])
                     and _hash(game['input_state_id']) and isinstance(game['observations'], list), 'STATE_GAME_SCHEMA')
            seen = set()
            for row in game['observations']:
                _require(isinstance(row, dict) and set(row) == {'seat', 'state_key', 'action_key', 'mean_reward'}
                         and row['seat'] in ('A', 'B') and _hash(row['state_key']) and _hash(row['action_key'])
                         and _number(row['mean_reward']), 'STATE_OBSERVATION_SCHEMA')
                key = row['seat'], row['state_key'], row['action_key']
                _require(key not in seen, 'STATE_DUPLICATE_OBSERVATION'); seen.add(key)
        _require(canonical(value['tables']) == canonical(_tables(games)), 'STATE_TABLES_MISMATCH')
        state = cls()
        for ordinal, (game_id, game) in enumerate(sorted(games.items(), key=lambda pair: pair[1]['ordinal'])):
            _require(game['ordinal'] == ordinal and game['input_state_id'] == state.state_id, 'STATE_INPUT_CHAIN')
            state._context_id = context
            state._games[game_id] = game
            state._tables = _tables(state._games)
        _require(state.export() == value, 'STATE_RECONSTRUCTION')
        return state

    def update_completed(self, game_id, winner, decisions, *, eligible=True):
        _require(type(eligible) is bool, 'ELIGIBILITY_REQUIRED')
        if not eligible:
            return False
        _require(_hash(game_id) and winner in ('A', 'B') and isinstance(decisions, list) and bool(decisions), 'COMPLETED_GAME_REQUIRED')
        records, contexts, inputs, groups = [], set(), set(), defaultdict(list)
        for raw in decisions:
            _require(isinstance(raw, dict) and _BASE_RECORD | {'learning', 'status'} <= set(raw)
                     and not set(raw) - (_BASE_RECORD | {'learning', 'status', 'reward', 'rating', 'learning_eligible'}), 'DECISION_RECORD_SCHEMA')
            _require(raw['status'] == 'EXPERIMENTAL_RESOLVED', 'NONRESOLVED_GAME')
            decision = _decision(raw['decision'])
            learning = raw['learning']
            _require(isinstance(learning, dict) and set(learning) == _LEARNING
                     and learning['seat'] in ('A', 'B')
                     and all(_hash(learning[k]) for k in ('context_id', 'state_key', 'action_key', 'input_state_id'))
                     and type(learning['support']) is int and learning['support'] >= 0
                     and type(learning['eligible_choice']) is bool, 'DECISION_LEARNING_SCHEMA')
            _require(_hash(raw['public_view_sha256']) or decision.get('kind') == 'BOTTOM_ORDER' and raw['public_view_sha256'] is None,
                     'DECISION_PUBLIC_VIEW_HASH')
            _require(_hash(raw['bot_id']) and isinstance(raw['reason'], str), 'DECISION_IDENTITY')
            _require(isinstance(raw['candidates'], list)
                     and (bool(raw['candidates']) or decision.get('kind') == 'BOTTOM_ORDER'), 'DECISION_CANDIDATES')
            keys = [digest(_action(candidate, learning['seat'])) for candidate in raw['candidates']]
            if decision.get('kind') != 'BOTTOM_ORDER':
                _require(digest(_action(raw['chosen'], learning['seat'])) == learning['action_key'], 'DECISION_ACTION_KEY')
            verify_decision_rng(raw)
            if 'learning_eligible' in raw:
                _require(type(raw['learning_eligible']) is bool, 'DECISION_ELIGIBILITY')
            rating = raw.get('rating')
            _require(rating is None or isinstance(rating, dict), 'DECISION_RATING')
            if rating is not None and 'learning_eligible' in rating:
                _require(type(rating['learning_eligible']) is bool, 'RATING_ELIGIBILITY')
            reward = raw.get('reward', rating.get('reward') if rating else None)
            _require(_number(reward), 'FINITE_BOARD_REWARD_REQUIRED')
            if rating is not None and 'reward' in rating:
                _require(_number(rating['reward']) and rating['reward'] == reward, 'REWARD_MISMATCH')
            if rating is not None and 'criterion_sha256' in rating:
                _require(rating['criterion_sha256'] == CRITERIA_SHA256, 'REWARD_CRITERION_MISMATCH')
            contexts.add(learning['context_id']); inputs.add(learning['input_state_id'])
            strategic = (learning['eligible_choice'] and len(set(keys)) > 1
                         and decision.get('kind') not in _PROCEDURAL and raw.get('learning_eligible', True)
                         and (rating is None or rating.get('learning_eligible', True)))
            if strategic:
                groups[(learning['seat'], learning['state_key'], learning['action_key'])].append(float(reward))
            records.append(_json(raw))
        _require(len(contexts) == 1 and len(inputs) == 1, 'MIXED_CONTEXT_OR_INPUT_STATE')
        context = next(iter(contexts)); input_id = next(iter(inputs))
        _require(self._context_id in (None, context), 'CONTEXT_MISMATCH')
        payload = digest({'game_id': game_id, 'winner': winner, 'decisions': records, 'eligible': True})
        if game_id in self._games:
            _require(self._games[game_id]['payload_sha256'] == payload, 'CONFLICTING_DUPLICATE_GAME')
            return False
        _require(input_id == self.state_id, 'INPUT_STATE_MISMATCH')
        observations = [{'seat': seat, 'state_key': state, 'action_key': action,
                         'mean_reward': sum(rewards) / len(rewards)}
                        for (seat, state, action), rewards in sorted(groups.items())]
        games = copy.deepcopy(self._games)
        games[game_id] = {'context_id': context, 'ordinal': len(games), 'winner': winner,
                         'payload_sha256': payload, 'input_state_id': input_id, 'observations': observations}
        tables = _tables(games)
        _require(all(_number(row['reward_sum']) and _number(row['mean_reward'])
                     for states in tables.values() for actions in states.values() for row in actions.values()), 'REWARD_OVERFLOW')
        self._context_id, self._games, self._tables = context, games, tables
        return True


class _PublicFeatures:
    def __init__(self, context, seat):
        self.context, self.seat, self._validator = context, seat, FieldTracker(context)

    def _card(self, owner, key):
        return self._validator._card(owner, key)

    def _visible(self, view, owner, key):
        player = view['players'][owner]
        visible = list(player['trash']) + list(player['breeding'])
        if owner == self.seat:
            visible.extend(player['hand'])
        for stack in player['battle'].values():
            visible.extend(stack['cards'])
        resolving = view['resolving_option']
        if resolving is not None and resolving['seat'] == owner:
            visible.extend(resolving['stack']['cards'])
        return key in visible

    def _action(self, view, candidate):
        normalized = _action(candidate, self.seat)
        for key in _action_cards(candidate):
            self._card(key[0], key)
            _require(key[0] == self.seat or self._visible(view, key[0], key), 'HIDDEN_OPPONENT_ACTION_CARD')
        return normalized

    def _state_key(self, view, decision):
        _require(isinstance(view, dict) and set(view) == _VIEW and view['active'] in ('A', 'B')
                 and type(view['memory']) is int and -10 <= view['memory'] <= 10
                 and type(view['turn']) is int and view['turn'] >= 0
                 and isinstance(view['phase'], str) and type(view['terminal']) is bool
                 and view['winner'] in (None, 'A', 'B'), 'PUBLIC_VIEW_SCHEMA')
        _require(isinstance(view['players'], dict) and set(view['players']) == {'A', 'B'}, 'PUBLIC_PLAYERS')
        features = {}
        board = {}
        seen, hidden_counts, entities = {'A': [], 'B': []}, {'A': 0, 'B': 0}, set()
        for owner in ('A', 'B'):
            player = view['players'][owner]
            _require(isinstance(player, dict) and set(player) == _PLAYER, 'PUBLIC_PLAYER_SCHEMA')
            public = {}
            for zone in ('deck', 'eggdeck', 'security') + (() if owner == self.seat else ('hand',)):
                hidden = player[zone]
                _require(isinstance(hidden, dict) and set(hidden) == {'count'}
                         and type(hidden['count']) is int and hidden['count'] >= 0, 'PUBLIC_HIDDEN_ZONE')
                public[zone] = hidden['count']
                hidden_counts[owner] += hidden['count']
            for zone in ('trash', 'breeding') + (('hand',) if owner == self.seat else ()):
                _require(isinstance(player[zone], list), 'PUBLIC_ZONE_SCHEMA')
                for key in player[zone]: self._card(owner, key)
                seen[owner].extend(player[zone])
                public[zone] = sorted(Counter(_physical(key, self.seat)['card'] for key in player[zone]).items())
            _require(isinstance(player['battle'], dict), 'PUBLIC_BATTLE_SCHEMA')
            stacks, kinds, sizes = [], [], []
            for anchor, stack in player['battle'].items():
                stacks.append(self._stack_features(owner, stack, view['turn'], anchor))
                kinds.append(self._card(owner, stack['cards'][-1]).kind); sizes.append(len(stack['cards']))
                seen[owner].extend(stack['cards'])
                if stack['instance_id']:
                    _require(stack['instance_id'] not in entities, 'PUBLIC_DUPLICATE_ENTITY')
                    entities.add(stack['instance_id'])
            public['battle'] = sorted(stacks, key=canonical)
            role = 'own' if owner == self.seat else 'opponent'
            features[role] = public
            board[owner] = {'battle_card_count': len(stacks), 'digimon_count': kinds.count('Digimon'),
                'tamer_count': kinds.count('Tamer'), 'option_count': kinds.count('Option'), 'total_stack_cards': sum(sizes),
                'digivolution_card_count': sum(n - 1 for n in sizes), 'largest_stack_size': max(sizes, default=0)}
        attack = view['attack']
        if attack is not None:
            _require(isinstance(attack, dict) and not set(attack) - _ATTACK, 'PUBLIC_ATTACK_SCHEMA')
            for key, item in attack.items():
                valid = (type(item) is bool if key in ('counter_used', 'block_used') else
                    type(item) is int and item >= 0 if key == 'deferred_depth' else
                    item is None or isinstance(item, str) if key == 'checked' else isinstance(item, str))
                _require(valid, 'PUBLIC_ATTACK_FIELD')
        resolving = view['resolving_option']
        if resolving is not None:
            _require(isinstance(resolving, dict) and set(resolving) == {'seat', 'stack'} and resolving['seat'] in ('A', 'B'), 'PUBLIC_RESOLVING_SCHEMA')
            self._stack_features(resolving['seat'], resolving['stack'], view['turn'])
            seen[resolving['seat']].extend(resolving['stack']['cards'])
            identity = resolving['stack']['instance_id']
            _require(not identity or identity not in entities, 'PUBLIC_DUPLICATE_ENTITY')
        for owner in ('A', 'B'):
            _require(len(seen[owner]) == len(set(seen[owner]))
                     and hidden_counts[owner] + len(seen[owner]) == sum(self._validator._inventory[owner].values()),
                     'PUBLIC_CARD_CONSERVATION')
        metrics = decision.get('public_metrics')
        checks = None
        if metrics is not None:
            _require(metrics['board'] == board, 'PUBLIC_METRICS_MISMATCH')
            checks = {'own' if s == self.seat else 'opponent': n for s, n in metrics['successful_security_checks'].items()}
        selected = decision.get('selected_pending', {})
        effect = {'kind': decision.get('kind'), 'effect_id': decision.get('effect_id', selected.get('effect_id')),
                  'field': selected.get('field')}
        source = decision.get('source', selected.get('source'))
        if source is not None:
            effect['source'] = _physical(source, self.seat)
            self._card(source[0], source)
            _require(self._visible(view, source[0], source), 'HIDDEN_DECISION_SOURCE')
        return digest({'context_id': self.context.matchup_id, 'seat': self.seat, 'features': features,
            'active_role': 'OWN' if view['active'] == self.seat else 'OPPONENT',
            'memory': view['memory'] if view['active'] == self.seat else -view['memory'],
            'phase': view['phase'], 'terminal': view['terminal'], 'decision': effect,
            'completed_security_checks': checks})

    def _stack_features(self, owner, stack, turn, anchor=None):
        _require(isinstance(stack, dict) and set(stack) == _STACK and isinstance(stack['cards'], list) and bool(stack['cards'])
                 and type(stack['suspended']) is bool and isinstance(stack['statuses'], dict)
                 and isinstance(stack['instance_id'], str)
                 and all(n is None or type(n) is int for n in (stack['played_turn'], stack['ready_since_turn']))
                 and (anchor is None or stack['cards'][-1] == anchor), 'PUBLIC_STACK_SCHEMA')
        for key in stack['cards']: self._card(owner, key)
        self._validator._public_statuses(owner, stack['statuses'], turn)
        grants = []
        for grant in stack['statuses'].get('effect_grants', []):
            if grant['target_instance'] == stack['instance_id'] and grant['expires']['turn'] >= turn:
                grants.append({'effect': copy.deepcopy(grant['effect']),
                               'expires_after_turn': grant['expires']['turn'] - turn})
        return {'top': _physical(stack['cards'][-1], self.seat)['card'],
                'sources': sorted(_physical(key, self.seat)['card'] for key in stack['cards'][:-1]),
                'suspended': stack['suspended'], 'played_this_turn': stack['played_turn'] == turn,
                'ready_now': stack['ready_since_turn'] is None or stack['ready_since_turn'] <= turn,
                'cannot_suspend': stack['statuses'].get('cannot_suspend', False),
                'cannot_unsuspend': stack['statuses'].get('cannot_unsuspend', False),
                'grants': sorted(grants, key=canonical)}


def learning_player_manifest(context, seat, input_state_id, policy_seed):
    """Derive the frozen policy identity without constructing a learning bot."""
    _require(seat in ('A', 'B') and _hash(input_state_id)
             and type(policy_seed) is int and policy_seed >= 0, 'MANIFEST_INPUTS')
    prior = NamedPlayerBot(context, seat).manifest()
    identity = {'version': VERSION, 'context_id': context.matchup_id, 'seat': seat,
                'name': 'Bot ' + seat, 'style': prior['style'], 'prior': prior,
                'input_state_id': input_state_id, 'configuration': copy.deepcopy(_CONFIG),
                'criterion_sha256': CRITERIA_SHA256, 'policy_seed': policy_seed,
                'source_sha256': _SOURCE_SHA256}
    return {**identity, 'bot_id': digest(identity),
            'policy_status': 'EXPERIMENTAL_OBSERVED_BOARD_LEARNING',
            'information_policy': 'PUBLIC_VIEW_OWN_HAND_AND_EXPLICIT_REVEALS_ONLY',
            'probability_claim': False, 'strategic_approval': 'NONE'}


class LearningPlayerBot:
    def __init__(self, context, seat, learning_state, policy_seed):
        _require(seat in ('A', 'B') and isinstance(learning_state, LearningState)
                 and type(policy_seed) is int and policy_seed >= 0, 'BOT_INPUTS')
        self.context, self.seat = context, seat
        self._model = LearningState.from_dict(learning_state.export())
        _require(self._model._context_id in (None, context.matchup_id), 'BOT_CONTEXT_MISMATCH')
        self._input_state_id, self._seed = learning_state.state_id, policy_seed
        self._random, self._prior = random.Random(policy_seed), NamedPlayerBot(context, seat)
        self._features = _PublicFeatures(context, seat)
        self._manifest = learning_player_manifest(context, seat, self._input_state_id, policy_seed)
        self.decision_log, self._last_view_hash = [], None

    def manifest(self):
        return copy.deepcopy(self._manifest)

    def export_rng(self):
        body = {'version': 1, 'context_id': self.context.matchup_id, 'seat': self.seat,
                'policy_seed': self._seed, 'input_state_id': self._input_state_id, 'state': _json(self._random.getstate())}
        return {**body, 'rng_sha256': digest(body)}

    def restore_rng(self, envelope):
        generator = _rng(envelope)
        _require(all(envelope[k] == self.export_rng()[k] for k in ('context_id', 'seat', 'policy_seed', 'input_state_id')), 'RNG_BOT_IDENTITY')
        self._random.setstate(generator.getstate())

    def _log(self, view_hash, candidates, chosen, decision, state_key, action_key, mode, support,
             eligible_choice, before_rng, protocol, reason, *, epsilon=EPSILON):
        self.decision_log.append({'decision': copy.deepcopy(decision), 'public_view_sha256': view_hash,
            'candidates': copy.deepcopy(candidates), 'chosen': copy.deepcopy(chosen), 'reason': reason,
            'bot_id': self._manifest['bot_id'], 'learning': {'context_id': self.context.matchup_id,
                'seat': self.seat, 'state_key': state_key, 'action_key': action_key,
                'input_state_id': self._input_state_id, 'mode': mode, 'support': support,
                'epsilon': epsilon, 'eligible_choice': eligible_choice,
                'rng_before': before_rng, 'rng_after': self.export_rng(), 'rng_draw_protocol': protocol}})

    def choose(self, view, candidates, decision=None):
        decision = _decision({} if decision is None else decision)
        state_key = self._features._state_key(view, decision)
        _require(isinstance(candidates, list) and bool(candidates), 'NONEMPTY_CANDIDATES_REQUIRED')
        keys = [digest(self._features._action(view, candidate)) for candidate in candidates]
        # Validate every choice through the actual aggressive/defensive prior
        # before touching policy randomness, including alternatives to None.
        evaluated = [(self._prior._preference(view, candidate, decision), i) for i, candidate in enumerate(candidates)]
        best = max(preference for (preference, _reason), _index in evaluated)
        index = min((i for (preference, _reason), i in evaluated if preference == best), key=lambda i: canonical(candidates[i]))
        reason = evaluated[index][0][1]
        table = self._model._tables[self.seat].get(state_key, {})
        support = lambda i: table.get(keys[i], {}).get('independent_games', 0)
        baseline = table[keys[index]]['mean_reward'] if support(index) >= MINIMUM_SUPPORT else 0.0
        supported = [i for i in range(len(candidates)) if support(i) >= MINIMUM_SUPPORT and table[keys[i]]['mean_reward'] > baseline]
        mode = 'NAMED_PRIOR'
        if supported:
            index = min(supported, key=lambda i: (-table[keys[i]]['mean_reward'], canonical(candidates[i])))
            mode, reason = 'LEARNED_BOARD_REWARD', 'prefer higher observed mean board reward with independent-game support'
        before = self.export_rng()
        draw = len(candidates) > 1
        explored = self._random.random() < EPSILON if draw else False
        if explored:
            index = self._random.randrange(len(candidates))
            mode, reason = 'EXPLORATION', 'epsilon 0.10 exploration among validated offered actions using private policy RNG'
        chosen = candidates[index]
        self._last_view_hash = digest(view)
        eligible = len(set(keys)) > 1 and decision.get('kind') not in _PROCEDURAL
        self._log(self._last_view_hash, candidates, chosen, decision, state_key, keys[index], mode,
                  support(index), eligible, before,
                  {'random': draw, 'randrange': len(candidates) if explored else None, 'chosen_index': index if explored else None}, reason)
        return copy.deepcopy(chosen)

    def bottom_order(self, remainder, *, public_view=None):
        _require(isinstance(remainder, list) and all(isinstance(key, str) for key in remainder)
                 and len(set(remainder)) == len(remainder), 'BOTTOM_ORDER_SCHEMA')
        if public_view is not None:
            self._features._state_key(public_view, {})
        for key in remainder:
            _physical(key, self.seat)
            if public_view is not None:
                self._features._action(public_view, key)
            else:
                self._features._card(self.seat, key)
        if public_view is not None:
            self._last_view_hash = digest(public_view)
        chosen = sorted(remainder)
        decision = {'kind': 'BOTTOM_ORDER'}
        before = self.export_rng()
        self._log(self._last_view_hash, remainder, chosen, decision,
                  digest({'context_id': self.context.matchup_id, 'seat': self.seat, 'kind': 'BOTTOM_ORDER'}),
                  digest(_action(chosen, self.seat)), 'FIXED_BOTTOM_ORDER', 0, False, before,
                  {'random': False, 'randrange': None, 'chosen_index': None},
                  'stable physical-key order; no inferred future draws')
        return list(chosen)


def verify_decision_input(record, view, context, expected_manifest):
    """Check saved public features/identity before a resumed policy is built."""
    _require(isinstance(record, dict) and _BASE_RECORD | {'learning'} <= set(record)
             and isinstance(expected_manifest, dict), 'INPUT_PROOF_SCHEMA')
    learning = record['learning']
    _require(isinstance(learning, dict) and set(learning) == _LEARNING, 'INPUT_PROOF_LEARNING')
    seat = expected_manifest.get('seat')
    _require(seat in ('A', 'B') and expected_manifest.get('context_id') == context.matchup_id
             and learning['context_id'] == context.matchup_id and learning['seat'] == seat
             and learning['input_state_id'] == expected_manifest.get('input_state_id')
             and record['bot_id'] == expected_manifest.get('bot_id') and _hash(record['bot_id']), 'INPUT_PROOF_IDENTITY')
    if expected_manifest.get('policy_status') == 'PUBLIC_STATE_TEXT_WITH_HISTORY':
        from board_text_player import board_text_player_manifest
        rebuilt = board_text_player_manifest(context, seat, expected_manifest['input_state_id'],
            expected_manifest.get('policy_seed'), expected_manifest.get('history_report_sha256'))
    else:
        rebuilt = learning_player_manifest(context, seat, expected_manifest['input_state_id'],
            expected_manifest.get('policy_seed'))
    _require(expected_manifest == rebuilt, 'INPUT_PROOF_MANIFEST')
    decision = _decision(record['decision'])
    features = _PublicFeatures(context, seat)
    _require(record['public_view_sha256'] == digest(view)
             or decision.get('kind') == 'BOTTOM_ORDER' and record['public_view_sha256'] is None, 'INPUT_PROOF_VIEW_HASH')
    if decision.get('kind') == 'BOTTOM_ORDER':
        features._state_key(view, {})  # Validate the supplied public projection.
        state_key = digest({'context_id': context.matchup_id, 'seat': seat, 'kind': 'BOTTOM_ORDER'})
    else:
        state_key = features._state_key(view, decision)
    for candidate in record['candidates']:
        features._action(view, candidate)
    _require(state_key == learning['state_key']
             and digest(features._action(view, record['chosen'])) == learning['action_key'], 'INPUT_PROOF_FEATURE_KEYS')
    verify_decision_rng(record)
    return True
