"""Fresh public-view Bot A/B preferences, not learned strategy or play ratings.

The engine supplies current candidates and judges the selected command. These
bots never inspect runtime state, resolve card text, preload routes, or filter
choices according to mechanic implementation status.
"""
import copy
import hashlib
from pathlib import Path
import re

from context_runtime import RuntimeHalt
from match_context import canonical, digest


VERSION = 'fresh-named-public-preferences-v1'
CONFIG = {
    'A': {'name': 'Bot A', 'style': 'AGGRESSIVE',
          'priorities': ['zero-security player attack', 'security pressure',
                         'favorable printed-DP battle', 'development'],
          'unsuspend': ['suspended Digimon', 'suspended Tamer']},
    'B': {'name': 'Bot B', 'style': 'DEFENSIVE',
          'priorities': ['zero-security player attack', 'favorable printed-DP battle',
                         'development and ready Blockers', 'security pressure'],
          'unsuspend': ['suspended Blocker', 'suspended All Turns Tamer',
                        'suspended Digimon', 'suspended other Tamer']},
    'shared': {'tie_break': 'CANONICAL_CANDIDATE_ASCENDING',
               'bottom_order': 'PHYSICAL_KEY_ASCENDING', 'planning_depth': 0,
               'outcome_ratings': 'NONE', 'training_data': [], 'roadmaps': []}}
_PHYSICAL = re.compile(r'([AB]):([A-Z][A-Z0-9]*-\d+)#([1-9]\d*)\Z')
_EFFECT = re.compile(r'([A-Z][A-Z0-9]*-\d+)\.[a-z][a-z0-9_]*\Z')


class NamedPlayerBot:
    def __init__(self, context, seat):
        if seat not in ('A', 'B'):
            raise RuntimeHalt('BOT_SEAT_REQUIRED')
        self.context, self.seat = context, seat
        self.other = 'B' if seat == 'A' else 'A'
        profile = copy.deepcopy(CONFIG[seat])
        identity = {'version': VERSION, 'context_id': context.matchup_id, 'seat': seat,
                    'name': profile['name'], 'style': profile['style'],
                    'configuration': {**profile, **copy.deepcopy(CONFIG['shared'])},
                    'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        self._manifest = {**identity, 'bot_id': digest(identity),
                          'policy_status': 'FRESH_UNTRAINED_HEURISTIC_PREFERENCES',
                          'training_data': [], 'roadmap': None,
                          'information_policy': 'PUBLIC_VIEW_OWN_HAND_AND_EXPLICIT_REVEALS_ONLY'}
        self.decision_log = []
        self._last_view_sha256 = None

    def manifest(self):
        return copy.deepcopy(self._manifest)

    def _view(self, view):
        allowed = {'active', 'memory', 'turn', 'phase', 'attack', 'terminal',
                   'winner', 'players', 'resolving_option'}
        if not isinstance(view, dict) or set(view) - allowed:
            raise RuntimeHalt('BOT_PUBLIC_VIEW_ONLY_REQUIRED')
        players = view.get('players')
        if not isinstance(players, dict) or set(players) != {'A', 'B'}:
            raise RuntimeHalt('BOT_PUBLIC_VIEW_PLAYERS_REQUIRED')
        for owner, player in players.items():
            for zone in ('deck', 'eggdeck', 'security') + (() if owner == self.seat else ('hand',)):
                hidden = player.get(zone)
                if (not isinstance(hidden, dict) or set(hidden) != {'count'}
                        or type(hidden['count']) is not int or hidden['count'] < 0):
                    raise RuntimeHalt('BOT_PUBLIC_VIEW_HIDDEN_ZONE: ' + owner + ' ' + zone)
        if not isinstance(players[self.seat].get('hand'), list):
            raise RuntimeHalt('BOT_PUBLIC_VIEW_OWN_HAND_REQUIRED')
        return players[self.seat], players[self.other]

    def _definition(self, key):
        match = _PHYSICAL.fullmatch(key) if isinstance(key, str) else None
        if match is None:
            raise RuntimeHalt('BOT_CHOICE_PHYSICAL_KEY_REQUIRED: ' + str(key))
        try:
            return self.context.card(match[1], match[2]).to_dict()
        except (ValueError, StopIteration) as exc:
            raise RuntimeHalt('BOT_CHOICE_CARD_OUTSIDE_CONTEXT: ' + key) from exc

    def _stack(self, view, key):
        for player in view['players'].values():
            for stack in player['battle'].values():
                if key in stack['cards']:
                    return stack
        return None

    def _blocker(self, view, key):
        definition = self._definition(key)
        if definition['type'] != 'Digimon':
            return False
        if any(line.strip().startswith(('＜Blocker＞', '<Blocker>'))
               for line in definition['main_text'].splitlines()):
            return True
        stack = self._stack(view, key)
        return bool(stack and any(
            record.get('target_instance') == stack.get('instance_id')
            and record.get('expires', {}).get('turn', -1) >= view['turn']
            and 'Blocker' in record.get('effect', {}).get('keywords', [])
            for record in stack.get('statuses', {}).get('effect_grants', [])))

    def _card_preference(self, view, key):
        card = self._definition(key)
        level, dp, cost = card.get('level') or 0, card.get('dp') or 0, card.get('play_cost') or 0
        if self.seat == 'B':
            category = 3 if self._blocker(view, key) else 2 if (
                card['type'] == 'Tamer' and '[All Turns]' in card['main_text']) else 1 if (
                card['type'] == 'Digimon') else 0
        else:
            category = 2 if card['type'] == 'Digimon' else 1 if card['type'] == 'Tamer' else 0
        return category, level, dp, -cost

    def _text(self, decision):
        source = decision.get('source')
        if not source:
            return ''
        definition = self._definition(source)
        field = decision.get('selected_pending', {}).get('field', 'main_text')
        return definition.get(field, '')

    def _physical_preference(self, view, key, decision):
        card = self._definition(key)
        stack = self._stack(view, key)
        owner = key[0]
        if owner != self.seat:
            if stack is None:
                raise RuntimeHalt('BOT_CHOICE_HIDDEN_OPPONENT_CARD: ' + key)
            return (60, card.get('level') or 0, card.get('dp') or 0,
                    int(not stack['suspended'])), 'prioritize visible opposing threat'
        unsuspend = ('unsuspend' in decision.get('effect_id', '')
                     or decision.get('kind') == 'UNSUSPEND'
                     or decision.get('effect_id', '').endswith('.orientation'))
        if unsuspend and stack is not None:
            if not stack['suspended']:
                return (-1,), 'already ready; prefer preserving optional orientation'
            if self.seat == 'B':
                category = 4 if self._blocker(view, key) else 3 if (
                    card['type'] == 'Tamer' and '[All Turns]' in card['main_text']) else 2 if (
                    card['type'] == 'Digimon') else 1
            else:
                category = 2 if card['type'] == 'Digimon' else 1
            return (60, category, card.get('dp') or 0), 'restore ' + (
                'Blocker or reactive resource' if self.seat == 'B' else 'attacking body or Tamer')
        return (30, *self._card_preference(view, key)), 'prefer current printed card resources'

    def _main(self, view, candidate):
        kind = candidate['kind']
        if kind == 'PASS_TURN':
            return (0,), 'pass only behind current preferred actions'
        if kind == 'DECLARE_ATTACK':
            attacker, target = candidate['attacker'], candidate['target']
            attack_dp = self._definition(attacker).get('dp') or 0
            if target == 'PLAYER':
                zero = view['players'][self.other]['security']['count'] == 0
                return (1000 if zero else 90 if self.seat == 'A' else 40, attack_dp), (
                    'pressure player at zero visible security; judge resolves responses' if zero
                    else 'security pressure preference')
            target_dp = self._definition(target).get('dp') or 0
            favorable = attack_dp > target_dp
            return (95 if self.seat == 'B' and favorable else 85 if favorable else 10,
                    target_dp, attack_dp), 'visible printed-DP battle preference; effects remain judge-owned'
        if kind in ('BATTLE_EVOLUTION', 'BREEDING_EVOLUTION', 'UNKNOWN_BATTLE_EVOLUTION'):
            key = candidate['hand_key']
            cost = candidate.get('cost', 0)
            return (75 if self.seat == 'B' else 70, *self._card_preference(view, key), -cost), 'develop current offered evolution'
        if kind in ('PLAY_CARD', 'USE_OPTION', 'UNKNOWN_OPTION_ACTION', 'OPTION_DELAY', 'UNKNOWN_DELAY_ACTION'):
            key = candidate.get('hand_key', candidate.get('source_key'))
            return (65, *self._card_preference(view, key)), 'develop current printed resource'
        if kind == 'BREEDING_CHOICE':
            preference = {'skip': 0, 'hatch': 30, 'promote': 50 if self.seat == 'A' else 20}
            if candidate.get('action') not in preference:
                raise RuntimeHalt('BOT_CHOICE_BREEDING_ACTION_UNSUPPORTED')
            return (preference[candidate['action']],), 'current breeding development preference'
        raise RuntimeHalt('BOT_CHOICE_ACTION_UNSUPPORTED: ' + str(kind))

    def _preference(self, view, candidate, decision):
        if candidate is None:
            return (0,), 'explicit no-target or optional decline candidate'
        if type(candidate) is bool:
            if not decision:
                raise RuntimeHalt('BOT_CHOICE_BOOLEAN_CONTEXT_REQUIRED')
            if decision.get('kind') == 'REDRAW_CHOICE':
                return (int(not candidate),), 'keep current opening; no redraw prediction'
            text = self._text(decision)
            if not text:
                raise RuntimeHalt('BOT_CHOICE_BOOLEAN_EFFECT_CONTEXT_REQUIRED')
            if 'unsuspend' in decision.get('effect_id', '') and 'draw' not in decision.get('effect_id', ''):
                stack = self._stack(view, decision.get('source'))
                benefit = bool(stack and stack['suspended'])
            elif 'return' in decision.get('effect_id', ''):
                benefit = any(self._definition(key)['type'] == 'Digimon'
                              for key in view['players'][self.other]['battle'])
            elif any(word in text.lower() for word in ('draw', 'digivolve', 'play ', 'memory')):
                benefit = True
            else:
                raise RuntimeHalt('BOT_CHOICE_BOOLEAN_PROCESSING_UNSUPPORTED')
            return (int(candidate == benefit),), 'explicit optional processing preference from present state'
        if isinstance(candidate, str):
            if _PHYSICAL.fullmatch(candidate):
                return self._physical_preference(view, candidate, decision)
            if candidate == 'PAY_NO_EFFECT':
                return (-1,), 'preserve Tamer rather than pay with no effect'
            if _EFFECT.fullmatch(candidate):
                return (20,), 'activate one offered current effect; stable effect tie break'
            raise RuntimeHalt('BOT_CHOICE_STRING_UNSUPPORTED: ' + candidate)
        if isinstance(candidate, list) and all(isinstance(key, str) and _PHYSICAL.fullmatch(key) for key in candidate):
            ranks = sorted((self._card_preference(view, key) for key in candidate), reverse=True)
            return (20 + len(candidate), *sum((tuple(rank) for rank in ranks), ())), 'select current explicitly revealed card resources'
        if isinstance(candidate, dict):
            if 'effect_id' in candidate and 'id' in candidate:
                return (10,), 'stable ordering of offered simultaneous effects'
            if 'kind' in candidate:
                return self._main(view, candidate)
            if set(candidate) == {'redraw'} and type(candidate['redraw']) is bool:
                return (int(not candidate['redraw']),), 'keep current opening; no redraw prediction'
            if {'source_key', 'hand_key', 'route_index'} <= set(candidate):
                return (50, *self._card_preference(view, candidate['hand_key'])), 'choose current offered effect evolution'
            if set(candidate) == {'card', 'status'}:
                if candidate['card'] is None:
                    return (0,), 'explicit no response candidate'
                return (20 if self.seat == 'B' else 10, *self._card_preference(view, candidate['card'])), 'current offered defensive response'
            if set(candidate) <= {'activate', 'evolution', 'return_key', 'play_key'} and type(candidate.get('activate')) is bool:
                active = candidate['activate']
                key = candidate.get('play_key') or candidate.get('return_key')
                if candidate.get('evolution'):
                    evolution = candidate['evolution']
                    if (not isinstance(evolution, dict)
                            or set(evolution) != {'source_key', 'hand_key', 'route_index'}):
                        raise RuntimeHalt('BOT_CHOICE_DELAY_EVOLUTION_SHAPE_UNSUPPORTED')
                    key = evolution['hand_key']
                return (int(active), *(self._card_preference(view, key) if key else ())), 'explicit currently offered Delay processing'
        raise RuntimeHalt('BOT_CHOICE_SHAPE_UNSUPPORTED')

    def choose(self, public_view, candidates, *, decision=None):
        self._view(public_view)
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeHalt('BOT_CHOICE_NONEMPTY_CANDIDATES_REQUIRED')
        if decision is not None and not isinstance(decision, dict):
            raise RuntimeHalt('BOT_CHOICE_DECISION_CONTEXT_REQUIRED')
        decision = copy.deepcopy(decision or {})
        # Evaluate every shape before selection, including alternatives to None.
        evaluated = [(self._preference(public_view, choice, decision), choice) for choice in candidates]
        best = max(preference for (preference, _reason), _choice in evaluated)
        tied = [(choice, reason) for (preference, reason), choice in evaluated if preference == best]
        chosen, reason = min(tied, key=lambda pair: canonical(pair[0]))
        self._last_view_sha256 = digest(public_view)
        self.decision_log.append({'decision': decision, 'public_view_sha256': self._last_view_sha256,
            'candidates': copy.deepcopy(candidates), 'chosen': copy.deepcopy(chosen),
            'reason': reason, 'bot_id': self._manifest['bot_id']})
        return copy.deepcopy(chosen)

    def bottom_order(self, remainder):
        if (not isinstance(remainder, list)
                or any(not isinstance(key, str) or not _PHYSICAL.fullmatch(key) for key in remainder)
                or len(set(remainder)) != len(remainder)):
            raise RuntimeHalt('BOT_CHOICE_BOTTOM_ORDER_PHYSICAL_KEYS_REQUIRED')
        chosen = sorted(remainder)
        self.decision_log.append({'decision': {'kind': 'BOTTOM_ORDER'},
            'public_view_sha256': self._last_view_sha256, 'candidates': copy.deepcopy(remainder),
            'chosen': chosen, 'reason': 'stable physical-key order; no inferred future draws',
            'bot_id': self._manifest['bot_id']})
        return list(chosen)
