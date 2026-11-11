"""Export the completed first game's readable ledger and explicit model update."""
import argparse
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

# The isolated -I -S -B process and direct .py loader preserve source identity
# without an extra time-limited worker around the long final replay.
migration._SOURCE_ONLY_WORKER = True


def write_json(name, value):
    with (OUT / name).open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')


def short(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def lineage_rows(record):
    rows = []
    child = record
    while 'repair_lineage' in child:
        line = child['repair_lineage']
        parent = line['parent_record']
        last = parent['commands'][-1] if parent['commands'] else None
        rows.append({'parent_record_sha256':parent['record_sha256'],
                     'parent_status':parent['status'],
                     'accepted_before_repair':line['successful_prefix_count'],
                     'saved_command':last['command'] if last else None,
                     'saved_reason':parent['halt_reason'],
                     'approved_source_changes':sorted(line['approved_changes']),
                     'original_replay_exact':line['original_replay_receipt']['exact_match']})
        child = parent
    rows.reverse()
    return rows


def report(record, replay):
    commands = record['commands']
    final = record['final']['state']
    labels = Counter(c['rating']['label'] for c in commands)
    actors = {seat:Counter(c['rating']['label'] for c in commands if c['seat']==seat)
              for seat in ('A','B')}
    checks = commands[-1]['observation']['public_metrics_after']['successful_security_checks']
    turns = defaultdict(list)
    for i, command in enumerate(commands, 1):
        before = command['before']['state']
        turns[(before['turn'], before['active'])].append((i,command))
    lines = [
        '# Game 0000: Bot A versus Bot B', '',
        f"**Result:** Bot {record['winner']} won by {record['terminal_reason'].replace('_',' ').lower()}.", '',
        f"**Record:** {len(commands)} accepted actions across {final['turn']} turns. "
        f"Bot C recorded {len(record['tracker_observations'])} field observations; "
        f"the automated judge accepted {sum(c['judge']['accepted'] is True for c in commands)} actions.", '',
        f"**Replay:** {'exact' if replay['exact_match'] else 'failed'} against the final saved source map. "
        f"Record SHA-256: `{record['record_sha256']}`.", '',
        f"**Locked setup:** seed {record['seed']}; Bot A aggressive and first, "
        'Bot B defensive; Federico Nine 123129 versus Bern 122110.', '',
        f"**Board-impact labels:** green {labels['GREEN']}, yellow {labels['YELLOW']}, "
        f"red {labels['RED']}. These are measured board changes under provisional criteria, "
        'not verdicts on long-term strategy.', '',
        f"**Successful Security checks:** Bot A {checks['A']}, Bot B {checks['B']}. "
        f"Final Security: A {len(final['zones']['A']['security'])}, "
        f"B {len(final['zones']['B']['security'])}.", '',
        'The complete action-by-action log is in `game-0000-actions.csv`. The gzipped '
        'final record contains each full before/after state, bot decision, RNG state, '
        'judge receipt, Bot C observation, and exact replay lineage.', '',
        '## Turn record', '',
        '| Turn | Active bot | Actions | Security checks by A / B after turn | Last action |',
        '|---:|:---:|---:|:---:|:---|'
    ]
    for (turn,seat), entries in sorted(turns.items()):
        last = entries[-1][1]
        after_checks = last['observation']['public_metrics_after']['successful_security_checks']
        lines.append(f"| {turn} | {seat} | {len(entries)} | {after_checks['A']} / {after_checks['B']} | "
                     f"{last['command']} |")
    lines += ['', '## Interpretation limits', '',
        'This is a completed experimental software game with an automated judge. '
        'Its result has no independent card-rules certification, accepted 60-match '
        'fact-finding credit, roadmap, or 10,000-match evaluation credit. Earlier '
        'development HALTs remain embedded in the verified repair lineage; the '
        'final 182-action game ledger contains only accepted actions.', '',
        f"Bot A labels: green {actors['A']['GREEN']}, yellow {actors['A']['YELLOW']}, "
        f"red {actors['A']['RED']}. Bot B labels: green {actors['B']['GREEN']}, "
        f"yellow {actors['B']['YELLOW']}, red {actors['B']['RED']}.", '']
    return '\n'.join(lines)


def export_csv(record):
    columns = ['action','turn','phase','seat','command','choice_json','result_json',
               'judge_accepted','board_color','learning_eligible','memory_before','memory_after',
               'security_a_before','security_a_after','security_b_before','security_b_after',
               'battle_stacks_a_before','battle_stacks_a_after','battle_stacks_b_before',
               'battle_stacks_b_after','bot_decisions_json','zone_movements_json']
    with (OUT / 'game-0000-actions.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for i, c in enumerate(record['commands'], 1):
            before, after = c['before']['state'], c['after']['state']
            writer.writerow({'action':i,'turn':before['turn'],'phase':before['phase'],
                'seat':c['seat'],'command':c['command'],'choice_json':short(c['args']),
                'result_json':short(c['result']),'judge_accepted':c['judge']['accepted'],
                'board_color':c['rating']['label'],
                'learning_eligible':c['rating']['learning_eligible'],
                'memory_before':before['memory'],'memory_after':after['memory'],
                'security_a_before':len(before['zones']['A']['security']),
                'security_a_after':len(after['zones']['A']['security']),
                'security_b_before':len(before['zones']['B']['security']),
                'security_b_after':len(after['zones']['B']['security']),
                'battle_stacks_a_before':len(before['battle']['A']),
                'battle_stacks_a_after':len(after['battle']['A']),
                'battle_stacks_b_before':len(before['battle']['B']),
                'battle_stacks_b_after':len(after['battle']['B']),
                'bot_decisions_json':short([{
                    'decision':d.get('decision'), 'candidates':d.get('candidates'),
                    'chosen':d.get('chosen'), 'reason':d.get('reason'),
                    'learning_mode':d.get('learning',{}).get('mode')}
                    for d in c['decisions']]),
                'zone_movements_json':short(c['observation']['zone_movements'])})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-only', action='store_true')
    args = parser.parse_args()
    path = OUT / 'game-0000-segment-0023.json.gz'
    with gzip.open(path, 'rt') as handle:
        record = json.load(handle)
    replay = json.loads((OUT / 'game-0000-replay-0023.json').read_text())
    if (record['index'] != 0 or record['status'] != 'EXPERIMENTAL_SOFTWARE_TERMINAL'
            or record['winner'] != 'A' or len(record['commands']) != 182
            or replay['exact_match'] is not True
            or replay['record_sha256'] != digest(record)
            or record['record_sha256'] != digest({k:v for k,v in record.items() if k!='record_sha256'})
            or any(c['status'] != 'EXPERIMENTAL_RESOLVED' or
                   c['judge']['accepted'] is not True for c in record['commands'])
            or len(record['tracker_observations']) != len(record['commands'])):
        raise RuntimeError('GAME_0000_FINAL_RECORD_INTEGRITY_FAILED')
    export_csv(record)
    with (OUT / 'game-0000-report.md').open('x') as handle:
        handle.write(report(record,replay))
    write_json('game-0000-repair-lineage-summary.json', lineage_rows(record))
    if not args.report_only:
        model = LearningState.from_dict(record['learning_state_before'])
        receipt = commit_completed_game(record, model, ROOT)
        if receipt['certification'] != 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED':
            raise RuntimeError('GAME_0000_LEARNING_CERTIFICATION_CHANGED')
        write_json('game-0000-learning-commit.json', receipt)
        write_json('game-0000-learning-model-after.json', model.export())
    print(json.dumps({'winner':record['winner'],'actions':len(record['commands']),
                      'replay_exact':replay['exact_match'],
                      'learning_committed':not args.report_only},sort_keys=True))


if __name__ == '__main__':
    main()
