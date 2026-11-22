"""Versioned, seat-specific policy over current public field and own card text."""
import copy
import hashlib
from pathlib import Path

from board_text_player import BoardTextPlayerBot
from interaction_learning import _PROCEDURAL
from match_context import canonical, digest


VERSION = 'styled-public-board-hand-text-history-v2'
_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_STYLE = {'A': 'AGGRESSIVE_BOARD_TEXT', 'B': 'DEFENSIVE_BOARD_TEXT'}


def styled_state_key(features, view, decision):
    """Validate the full view, then group comparable public tempo positions."""
    features._state_key(view, decision)
    own = features.seat
    other = 'B' if own == 'A' else 'A'

    def band(value):
        return 0 if value == 0 else 1 if value <= 2 else 3

    def field(owner):
        stacks = list(view['players'][owner]['battle'].values())
        return {'units': band(len(stacks)),
                'largest_stack': band(max((len(stack['cards']) for stack in stacks), default=0))}

    selected = decision.get('selected_pending', {})
    source = decision.get('source', selected.get('source'))
    checks = decision.get('public_metrics', {}).get('successful_security_checks')
    check_gap = None if checks is None else max(-2, min(2, checks[own] - checks[other]))
    memory = view['memory'] if view['active'] == own else -view['memory']
    return digest({'version': VERSION, 'context_id': features.context.matchup_id,
        'seat': own, 'decision_kind': decision.get('kind'),
        'effect_id': decision.get('effect_id', selected.get('effect_id')),
        'effect_source_number': source.split(':', 1)[1].split('#', 1)[0] if source else None,
        'active_role': 'OWN' if view['active'] == own else 'OPPONENT',
        'phase': view['phase'], 'memory_band': -band(-memory) if memory < 0 else band(memory),
        'own_security_band': band(view['players'][own]['security']['count']),
        'opponent_security_band': band(view['players'][other]['security']['count']),
        'own_field': field(own), 'opponent_field': field(other),
        'completed_check_gap': check_gap})


def styled_board_text_player_manifest(context, seat, input_state_id, policy_seed, report_sha256):
    from board_text_player import board_text_player_manifest
    base = board_text_player_manifest(context, seat, input_state_id, policy_seed, report_sha256)
    body = {key: base[key] for key in ('context_id', 'seat', 'name', 'input_state_id',
        'policy_seed', 'history_report_sha256')}
    body.update({'version': VERSION, 'style': _STYLE[seat], 'source_sha256': _SOURCE_SHA256})
    return {**body, 'bot_id': digest(body), 'policy_status': 'STYLED_PUBLIC_STATE_TEXT_WITH_HISTORY',
            'information_policy': base['information_policy'], 'random_exploration': False,
            'preloaded_routes': False, 'probability_claim': False, 'strategic_approval': 'NONE'}


class StyledBoardTextPlayerBot(BoardTextPlayerBot):
    def __init__(self, context, seat, learning_state, policy_seed, report_sha256):
        super().__init__(context, seat, learning_state, policy_seed, report_sha256)
        self._manifest = styled_board_text_player_manifest(
            context, seat, self._input_state_id, policy_seed, report_sha256)

    def _rank(self, view, candidate, decision):
        score, basis = super()._rank(view, candidate, decision)
        if not isinstance(candidate, dict):
            return score, basis
        kind = candidate.get('kind')
        if self.seat == 'A' and kind == 'DECLARE_ATTACK':
            return score + 0.5, basis + '; aggressive pressure'
        if self.seat == 'B':
            if kind == 'DECLARE_ATTACK' and len(view['players']['B']['battle']) <= 1:
                return score - 2.0, basis + '; preserve single exposed field unit'
            if kind in ('PLAY_CARD', 'BATTLE_EVOLUTION', 'BREEDING_EVOLUTION'):
                return score + 0.3, basis + '; defensive field development'
        return score, basis

    def choose(self, view, candidates, decision=None):
        from context_runtime import RuntimeHalt
        from interaction_learning import _decision
        decision = _decision({} if decision is None else decision)
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeHalt('STYLED_BOARD_TEXT_CANDIDATES_REQUIRED')
        state_key = styled_state_key(self._features, view, decision)
        keys = [digest(self._features._action(view, candidate)) for candidate in candidates]
        table = self._model._tables[self.seat].get(state_key, {})
        evaluated = []
        for index, candidate in enumerate(candidates):
            live, basis = self._rank(view, candidate, decision)
            past = table.get(keys[index], {})
            support = past.get('independent_games', 0)
            history = max(-2.0, min(2.0, past.get('mean_reward', 0.0))) * 0.5 if support >= 3 else 0.0
            evaluated.append((live + history, support, canonical(candidate), index, basis, history))
        selected = min(evaluated, key=lambda row: (-row[0], -row[1], row[2]))
        index, support, basis, history = selected[3], selected[1], selected[4], selected[5]
        before = self.export_rng()
        chosen = copy.deepcopy(candidates[index])
        self._last_view_hash = digest(view)
        reason = basis + '; prior matched games=' + str(support) + '; history adjustment=' + str(history)
        self._log(self._last_view_hash, candidates, chosen, decision, state_key, keys[index],
                  'PUBLIC_STATE_TEXT', support, len(set(keys)) > 1 and
                  decision.get('kind') not in _PROCEDURAL, before,
                  {'random': False, 'randrange': None, 'chosen_index': None}, reason,
                  epsilon=0.0)
        return chosen
