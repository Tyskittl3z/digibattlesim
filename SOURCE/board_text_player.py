"""A public-board and own-hand policy with a bound prior match report.

It ranks only currently offered actions. Card numbers identify printed cards;
there are no deck routes, opening scripts, opponent hidden cards or random
exploration. History is consulted for a matching public state/action only.
"""
import copy
import hashlib
from pathlib import Path
import re
import random

from context_runtime import RuntimeHalt
from interaction_learning import (LearningPlayerBot, LearningState, _PROCEDURAL,
                                  _PublicFeatures, _action, _decision, _require)
from match_context import canonical, digest


VERSION = 'public-board-hand-text-history-v1'
_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_CARD = re.compile(r'([AB]):([A-Z][A-Z0-9]*-\d+)#[1-9]\d*\Z')


def board_text_player_manifest(context, seat, input_state_id, policy_seed, report_sha256):
    if (seat not in ('A', 'B') or (report_sha256 is not None and
            (not isinstance(report_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', report_sha256)))):
        raise RuntimeHalt('BOARD_TEXT_MANIFEST_INPUT')
    body = {'version': VERSION, 'context_id': context.matchup_id, 'seat': seat,
            'name': 'Bot ' + seat, 'style': 'BOARD_AND_CARD_TEXT',
            'input_state_id': input_state_id, 'policy_seed': policy_seed,
            'history_report_sha256': report_sha256, 'source_sha256': _SOURCE_SHA256}
    return {**body, 'bot_id': digest(body), 'policy_status': 'PUBLIC_STATE_TEXT_WITH_HISTORY',
            'information_policy': 'PUBLIC_FIELD_OWN_HAND_PRINTED_TEXT_ONLY',
            'random_exploration': False, 'preloaded_routes': False,
            'probability_claim': False, 'strategic_approval': 'NONE'}


class BoardTextPlayerBot(LearningPlayerBot):
    def __init__(self, context, seat, learning_state, policy_seed, report_sha256):
        _require(seat in ('A', 'B') and isinstance(learning_state, LearningState)
                 and type(policy_seed) is int and policy_seed >= 0, 'BOT_INPUTS')
        self.context, self.seat = context, seat
        self._model = LearningState.from_dict(learning_state.export())
        _require(self._model._context_id in (None, context.matchup_id), 'BOT_CONTEXT_MISMATCH')
        self._input_state_id, self._seed = learning_state.state_id, policy_seed
        self._random = random.Random(policy_seed)
        self._features = _PublicFeatures(context, seat)
        self._manifest = board_text_player_manifest(
            context, seat, self._input_state_id, policy_seed, report_sha256)
        self.decision_log, self._last_view_hash = [], None

    def _card(self, key):
        match = _CARD.fullmatch(key) if isinstance(key, str) else None
        if match is None:
            raise RuntimeHalt('BOARD_TEXT_CARD_KEY_REQUIRED')
        return self.context.card(match[1], match[2]).to_dict()

    def _stack(self, view, key):
        for owner in ('A', 'B'):
            for anchor, stack in view['players'][owner]['battle'].items():
                if key == anchor or key in stack['cards']:
                    return owner, stack
        return None, None

    def _printed_value(self, key, *, trigger=None):
        card = self._card(key)
        text = card['main_text']
        ready_text = ('[' + trigger + ']') in text if trigger else False
        return ((2.0 if card['type'] == 'Digimon' else 1.0 if card['type'] == 'Tamer' else 0.5)
                + (card.get('dp') or 0) / 10000.0
                + (0.5 if ready_text else 0.0))

    def _rank(self, view, candidate, decision):
        own, other = self.seat, 'B' if self.seat == 'A' else 'A'
        if candidate is None:
            return 0.0, 'no target or decline'
        if type(candidate) is bool:
            if decision.get('kind') == 'REDRAW_CHOICE':
                return (0.0 if not candidate else -0.1), 'current opening hand'
            return (0.5 if candidate else 0.0), 'printed optional effect'
        if isinstance(candidate, str):
            if candidate == 'PAY_NO_EFFECT':
                return -1.0, 'no resulting effect'
            if _CARD.fullmatch(candidate):
                owner, stack = self._stack(view, candidate)
                if owner == other:
                    top = self._card(stack['cards'][-1])
                    return (2.0 + len(stack['cards']) * 0.5
                            + (top.get('dp') or 0) / 10000.0), 'visible opposing stack'
                if owner == own:
                    return (2.0 if stack['suspended'] else -0.5) + len(stack['cards']) * 0.3, 'visible own stack orientation'
                if candidate in view['players'][own]['hand']:
                    return self._printed_value(candidate) - (self._card(candidate).get('play_cost') or 0) * 0.2, 'own hand printed card'
                return self._printed_value(candidate), 'visible printed card'
            return 0.5, 'currently offered printed effect'
        if isinstance(candidate, list):
            return sum(self._printed_value(key) for key in candidate), 'currently revealed printed cards'
        if not isinstance(candidate, dict):
            raise RuntimeHalt('BOARD_TEXT_CANDIDATE_SHAPE')
        kind = candidate.get('kind')
        if kind == 'PASS_TURN':
            return -0.5, 'end current action opportunity'
        if kind == 'DECLARE_ATTACK':
            target = candidate['target']
            if target == 'PLAYER':
                security = view['players'][other]['security']['count']
                return (100.0 if security == 0 else 3.0), 'current opposing Security count'
            attacker = self._card(candidate['attacker'])
            defender = self._card(target)
            delta = (attacker.get('dp') or 0) - (defender.get('dp') or 0)
            return (3.5 if delta > 0 else 0.0 if delta == 0 else -2.0), 'visible printed DP comparison'
        if kind in ('PLAY_CARD', 'USE_OPTION', 'UNKNOWN_OPTION_ACTION'):
            key = candidate['hand_key']
            card = self._card(key)
            return (self._printed_value(key, trigger='On Play')
                    - (card.get('play_cost') or 0) * 0.25), 'own hand text and paid memory'
        if kind in ('BATTLE_EVOLUTION', 'BREEDING_EVOLUTION', 'UNKNOWN_BATTLE_EVOLUTION'):
            key = candidate['hand_key']
            return (self._printed_value(key, trigger='When Digivolving') + 0.5
                    - candidate.get('cost', 0) * 0.25), 'own hand evolution text and memory'
        if kind == 'BREEDING_CHOICE':
            if candidate['action'] == 'skip':
                return 0.0, 'current breeding state'
            if candidate['action'] == 'hatch':
                return 0.5, 'available breeding space'
            return 2.0 if not view['players'][own]['battle'] else 1.0, 'move existing breeding stack to field'
        if kind in ('OPTION_DELAY', 'UNKNOWN_DELAY_ACTION'):
            return 0.5, 'visible option effect'
        if 'effect_id' in candidate and 'id' in candidate:
            return 0.0, 'current simultaneous effect order'
        if set(candidate) == {'redraw'}:
            return (0.0 if not candidate['redraw'] else -0.1), 'current opening hand'
        if set(candidate) == {'card', 'status'}:
            if candidate['card'] is None:
                return 0.0, 'no response'
            owner, stack = self._stack(view, candidate['card'])
            return (2.0 + len(stack['cards']) * 0.2 if owner == own else 0.5), 'current defensive field'
        if {'source_key', 'hand_key', 'route_index'} <= set(candidate):
            return self._printed_value(candidate['hand_key'], trigger='When Digivolving'), 'offered hand evolution'
        if 'activate' in candidate:
            return (0.5 if candidate['activate'] else 0.0), 'offered printed processing'
        raise RuntimeHalt('BOARD_TEXT_CANDIDATE_UNSUPPORTED')

    def choose(self, view, candidates, decision=None):
        decision = _decision({} if decision is None else decision)
        state_key = self._features._state_key(view, decision)
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeHalt('BOARD_TEXT_CANDIDATES_REQUIRED')
        keys = [digest(self._features._action(view, candidate)) for candidate in candidates]
        table = self._model._tables[self.seat].get(state_key, {})
        evaluated = []
        for index, candidate in enumerate(candidates):
            live_score, basis = self._rank(view, candidate, decision)
            past = table.get(keys[index], {})
            support = past.get('independent_games', 0)
            history_score = past.get('mean_reward', 0.0) if support else 0.0
            evaluated.append((live_score, history_score, support, canonical(candidate), index, basis))
        best_live = max(row[0] for row in evaluated)
        eligible = [row for row in evaluated if row[0] == best_live]
        selected = min(eligible, key=lambda row: (-row[1], -row[2], row[3]))
        index, basis = selected[4], selected[5]
        before = self.export_rng()
        chosen = copy.deepcopy(candidates[index])
        self._last_view_hash = digest(view)
        reason = basis + '; prior report checked, matching action support=' + str(selected[2])
        self._log(self._last_view_hash, candidates, chosen, decision, state_key, keys[index],
                  'PUBLIC_STATE_TEXT', selected[2], len(set(keys)) > 1 and
                  decision.get('kind') not in _PROCEDURAL, before,
                  {'random': False, 'randrange': None, 'chosen_index': None}, reason,
                  epsilon=0.0)
        return chosen
