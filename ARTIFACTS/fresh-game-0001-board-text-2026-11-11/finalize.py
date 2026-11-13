"""Export the second completed match and its next-game history checkpoint."""
from collections import Counter, defaultdict
import csv
import gzip
import importlib.machinery
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = str(ROOT / 'SOURCE')


class DirectSource(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


sys.path_importer_cache[SOURCE] = importlib.machinery.FileFinder(
    SOURCE, (DirectSource, importlib.machinery.SOURCE_SUFFIXES))
sys.path.insert(0, SOURCE)

import fresh_repair_migration as migration
from fresh_learning_campaign import commit_completed_game
from interaction_learning import LearningState
from match_context import digest

migration._SOURCE_ONLY_WORKER = True


def write_json(name, value):
    with (OUT / name).open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')


def lineage_rows(record):
    rows = []
    child = record
    while 'repair_lineage' in child:
        line = child['repair_lineage']
        parent = line['parent_record']
        rows.append({'parent_record_sha256': parent['record_sha256'],
            'parent_status': parent['status'],
            'accepted_before_repair': line['successful_prefix_count'],
            'saved_reason': parent['halt_reason'],
            'approved_source_changes': sorted(line['approved_changes']),
            'original_replay_exact': line['original_replay_receipt']['exact_match']})
        child = parent
    return list(reversed(rows))


def export_actions(record):
    columns = ['action', 'turn', 'phase', 'seat', 'command', 'choice_json',
        'result_json', 'judge_accepted', 'board_color', 'learning_eligible',
        'memory_before', 'memory_after', 'security_a_before', 'security_a_after',
        'security_b_before', 'security_b_after', 'battle_stacks_a_before',
        'battle_stacks_a_after', 'battle_stacks_b_before', 'battle_stacks_b_after',
        'bot_decisions_json', 'zone_movements_json']
    short = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))
    with (OUT / 'game-0001-actions.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for index, command in enumerate(record['commands'], 1):
            before, after = command['before']['state'], command['after']['state']
            writer.writerow({'action': index, 'turn': before['turn'], 'phase': before['phase'],
                'seat': command['seat'], 'command': command['command'],
                'choice_json': short(command['args']), 'result_json': short(command['result']),
                'judge_accepted': command['judge']['accepted'],
                'board_color': command['rating']['label'],
                'learning_eligible': command['rating']['learning_eligible'],
                'memory_before': before['memory'], 'memory_after': after['memory'],
                'security_a_before': len(before['zones']['A']['security']),
                'security_a_after': len(after['zones']['A']['security']),
                'security_b_before': len(before['zones']['B']['security']),
                'security_b_after': len(after['zones']['B']['security']),
                'battle_stacks_a_before': len(before['battle']['A']),
                'battle_stacks_a_after': len(after['battle']['A']),
                'battle_stacks_b_before': len(before['battle']['B']),
                'battle_stacks_b_after': len(after['battle']['B']),
                'bot_decisions_json': short([{'decision': d['decision'],
                    'candidates': d['candidates'], 'chosen': d['chosen'],
                    'reason': d['reason'], 'mode': d['learning']['mode']}
                    for d in command['decisions']]),
                'zone_movements_json': short(command['observation']['zone_movements'])})


def report(record):
    commands = record['commands']
    colors = Counter(command['rating']['label'] for command in commands)
    checks = commands[-1]['observation']['public_metrics_after']['successful_security_checks']
    turns = defaultdict(list)
    for index, command in enumerate(commands, 1):
        before = command['before']['state']
        turns[(before['turn'], before['active'])].append((index, command))
    lines = ['# Game 0001: Bot A versus Bot B', '',
        f"**Result:** Bot {record['winner']} won by {record['terminal_reason'].replace('_', ' ').lower()} on turn {record['final']['state']['turn']}.", '',
        f"**Locked game:** seed {record['seed']}; Bot B moved first. Both seats used the same public-board, own-hand, printed-text policy and loaded the Game 0000 history model. Their report hash was `{record['history_report']['sha256']}`.", '',
        f"**Audit:** {len(commands)} accepted commands, {len(record['tracker_observations'])} Bot C observations, and exact replay under record `{record['record_sha256']}`. No random player-policy choices were drawn.", '',
        f"**Board-impact labels:** green {colors['GREEN']}, yellow {colors['YELLOW']}, red {colors['RED']}. These labels measure immediate field changes under the recorded provisional criteria; they do not prove a choice was strategically optimal.", '',
        f"**Security checks:** A {checks['A']}; B {checks['B']}. Final Security counts: A {len(record['final']['state']['zones']['A']['security'])}; B {len(record['final']['state']['zones']['B']['security'])}.", '',
        'Every action, choice, judge receipt, board label, memory change, and zone movement is in `game-0001-actions.csv`. The gzipped final segment includes complete before/after states, Bot C observations, policy inputs, and repair lineage.', '',
        '## Turn record', '',
        '| Turn | Active bot | Logged actions | Last action |', '|---:|:---:|---:|:---|']
    for (turn, seat), entries in sorted(turns.items()):
        lines.append(f"| {turn} | {seat} | {len(entries)} | {entries[-1][1]['command']} |")
    lines += ['', '## Observed card interactions', '',
        '- Bot A checked LM-056 in Security, chose LM-034 from two revealed cards, returned P-104 to the deck bottom, and placed LM-056 in the battle area.',
        '- Bot A attempted EX13-023’s return. Bot B chose EX13-017’s inherited suspend replacement and kept its Veedramon stack in play.',
        '- BT12-029 later returned A’s EX13-023 to hand. Official EX13-023 ruling Q7265 allows returning the Digimon itself while protecting its stacked cards.', '',
        '## Evidence limits', '',
        'This is a completed experimental software match with an automated judge and exact replay. It has no independent rules certification or accepted 60-match or 10,000-match evaluation credit. The development halts are preserved in the repair lineage; all commands in the final match ledger were accepted.', '']
    return '\n'.join(lines)


def main():
    with gzip.open(OUT / 'segment-0012.json.gz', 'rt') as handle:
        record = json.load(handle)
    if (record['index'] != 1 or record['status'] != 'EXPERIMENTAL_SOFTWARE_TERMINAL'
            or record['winner'] != 'B' or len(record['commands']) != 132
            or record['record_sha256'] != digest({k: v for k, v in record.items() if k != 'record_sha256'})
            or len(record['tracker_observations']) != len(record['commands'])
            or any(c['status'] != 'EXPERIMENTAL_RESOLVED' or
                   c['judge']['accepted'] is not True for c in record['commands'])):
        raise RuntimeError('GAME_0001_FINAL_RECORD_INTEGRITY_FAILED')
    export_actions(record)
    with (OUT / 'game-0001-report.md').open('x') as handle:
        handle.write(report(record))
    write_json('game-0001-repair-lineage-summary.json', lineage_rows(record))
    model = LearningState.from_dict(record['learning_state_before'])
    receipt = commit_completed_game(record, model, ROOT)
    if not receipt['updated'] or len(model.export()['games']) != 2:
        raise RuntimeError('GAME_0001_MODEL_UPDATE_FAILED')
    write_json('game-0001-learning-commit.json', receipt)
    write_json('game-0001-learning-model-after.json', model.export())
    print(json.dumps({'winner': record['winner'], 'actions': len(record['commands']),
        'judge_accepted': len(record['commands']), 'model_games': 2,
        'record_sha256': record['record_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
