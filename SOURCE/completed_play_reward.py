"""Derive between-game attack learning from saved observed command boundaries."""
import copy
import math


def attack_learning_rewards(commands):
    """Return signed whole-attack rewards keyed by declaration command index."""
    rewards = {}
    for start, opening in enumerate(commands):
        if opening['command'] != 'DECLARE_ATTACK':
            continue
        attacker = opening['seat']
        if attacker not in ('A', 'B'):
            raise ValueError('ATTACKER_SEAT_REQUIRED')
        total = 0.0
        for index in range(start, len(commands)):
            command = commands[index]
            if index > start and command['command'] == 'DECLARE_ATTACK':
                break
            reward = command['rating']['reward']
            if type(reward) not in (int, float) or not math.isfinite(reward):
                raise ValueError('RESOLVED_ATTACK_REWARD_REQUIRED')
            total += reward if command['seat'] == attacker else -reward
            if command['command'] == 'END_ATTACK':
                break
        rewards[start] = round(total, 10)
    return rewards


def learning_decisions(commands, player_policy):
    """Copy logged decisions, changing only new-policy attack learning reward."""
    attacks = attack_learning_rewards(commands) if player_policy == 'BOARD_TEXT_HISTORY_STYLED' else {}
    decisions = []
    for index, command in enumerate(commands):
        for logged in command.get('decisions', []):
            row = copy.deepcopy(logged)
            if index in attacks and isinstance(row.get('chosen'), dict) and row['chosen'].get('kind') == 'DECLARE_ATTACK':
                row['reward'] = attacks[index]
            decisions.append(row)
    return decisions
