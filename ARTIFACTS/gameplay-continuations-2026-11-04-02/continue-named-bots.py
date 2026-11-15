"""Save one bounded same-game named-bot segment; never launch a cohort."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'SOURCE'))
import imported_attempts as diagnostic
from match_context import canonical, digest
from named_bot_continuation import continue_with_named_bots, replay_named_bot_continuation


def write_json(name, value):
    with (OUT / name).open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


previous_path = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-04-01/game-0000-segment.json.gz'
destination = OUT / 'game-0000-segment.json.gz'
if destination.exists():
    raise SystemExit('Refusing to overwrite a saved game segment')
previous_bytes = previous_path.read_bytes()
previous = json.loads(gzip.decompress(previous_bytes))
assert previous['seed'] == 12017913134550805276
assert previous['status'] == 'PAUSED_AFTER_SAVED_ACTION'
assert len(previous['commands']) == 152
source_bytes = {str(path.relative_to(ROOT)): path.read_bytes()
                for path in sorted((ROOT / 'SOURCE').glob('*.py'))}
source_hashes = {name: hashlib.sha256(body).hexdigest() for name, body in source_bytes.items()}

with patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('Reference substitution forbidden')), \
        patch.object(diagnostic, 'run_attempt', side_effect=AssertionError('No fresh attempt allowed')), \
        patch.object(diagnostic, 'continue_attempt', side_effect=AssertionError('Random continuation forbidden')):
    record = continue_with_named_bots(previous, ROOT, max_new_commands=12)
    with destination.open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(canonical(record) + b'\n')
    assert record['commands'][:152] == previous['commands']
    assert record['seed'] == previous['seed'] and record['first'] == previous['first']
    proof = record['continuation_provenance']['physical_state_proof']
    assert proof['original_before_sha256'] == proof['revalidated_before_sha256']
    assert proof['original_rng_sha256'] == proof['revalidated_rng_sha256']
    summary = {
        'date': '2026-11-04', 'status': record['status'], 'seed': record['seed'],
        'first': record['first'], 'turn': record['final']['state']['turn'],
        'active': record['final']['state']['active'], 'phase': record['final']['state']['phase'],
        'memory': record['final']['state']['memory'], 'commands': len(record['commands']),
        'successful_commands': sum(c['status'] == 'EXPERIMENTAL_RESOLVED' for c in record['commands']),
        'new_commands': len(record['commands']) - 152,
        'new_decisions': len(record['new_decisions']), 'active_pilots': record['active_pilots'],
        'halt_reason': record.get('halt_reason'), 'winner': record.get('winner'),
        'original_152_command_prefix_unchanged': True,
        'original_complete_physical_state_and_RNG_revalidated': True,
        'record_sha256': digest(record), 'previous_record': str(previous_path.relative_to(ROOT)),
        'previous_record_sha256': digest(previous),
        'execution_id': record['replay_provenance']['execution_id'],
        'user_bot_whole_match_credit': 0, 'accepted_fact_finding_credit': 0,
        'final_evaluation_credit': 0, 'outcome_ratings_assigned': False,
        'mixed_history': 'HISTORICAL_RANDOM_PREFIX_THEN_EXPLICIT_NAMED_BOT_SEGMENT',
    }
    write_json('checkpoint.json', summary)
    write_json('bot-decisions.json', record['new_decisions'])
    write_json('source-manifest.json', {
        'schema': 'source-checkpoint-v1', 'execution_id': summary['execution_id'],
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'files': source_hashes,
    })
    with (OUT / 'source-checkpoint.tar.gz').open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|') as archive:
                for name, body in source_bytes.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(body)
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(body))
    lines = ['# Game0000: named-bot continuation', '',
             'Original seed: 12017913134550805276. First152 commands retained unchanged.',
             'Bot A: aggressive. Bot B: defensive. These are fresh untrained policies.',
             'Mixed-history whole-match/fact-finding/final credit:0. No outcome ratings.', '',
             '| Index | Turn | Seat | Command | Arguments | Observed result |',
             '|---:|---:|---|---|---|---|']
    for index, command in enumerate(record['commands']):
        result = command.get('result', {})
        description = command.get('reason') or result.get('processing') or result.get('phase') or command['status']
        lines.append('|' + '|'.join(str(item).replace('|', '/') for item in
                     (index, command.get('public_view', {}).get('turn', ''), command.get('seat', ''),
                      command['command'], json.dumps(command.get('args', {}), sort_keys=True), description)) + '|')
    with (OUT / 'game-0000-turns.md').open('x') as handle:
        handle.write('\n'.join(lines) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'active_pilots'}), flush=True)
    replay = replay_named_bot_continuation(record, ROOT)
    write_json('replay.json', replay)
    assert replay['exact_match'], 'Actual record/source archive retained; exact replay failed'

assert previous_path.read_bytes() == previous_bytes
assert source_hashes == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted((ROOT / 'SOURCE').glob('*.py'))}
print(json.dumps(replay), flush=True)
