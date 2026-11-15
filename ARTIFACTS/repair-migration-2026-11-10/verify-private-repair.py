"""Cross-build private setup proof. Never starts a production campaign."""
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASELINE = ROOT / 'ARTIFACTS/learning-integration-2026-11-10'
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
CAMPAIGN = 'PRIVATE_CROSS_BUILD_REPAIR_FIXTURE_2026_11_10'
sys.path.insert(0, str(ROOT / 'SOURCE'))


def raw_hash(body):
    return hashlib.sha256(body).hexdigest()


def source_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted((root / 'SOURCE').glob('*.py'))}


def save_json(name, value):
    with (OUT / name).open('x') as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


def save_record(name, value):
    with (OUT / name).open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n')


def save_sources(name, files):
    with (OUT / name).open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|') as archive:
                for path, body in sorted(files.items()):
                    info = tarfile.TarInfo(path)
                    info.size, info.mtime = len(body), 0
                    archive.addfile(info, io.BytesIO(body))


def physical(snapshot):
    value = copy.deepcopy(snapshot)
    value.pop('execution_id')
    return value


started = time.monotonic()
frozen = source_bytes(ROOT)
old_history = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-04-02/game-0000-segment.json.gz'
old_history_bytes = old_history.read_bytes()
baseline_manifest = json.loads((BASELINE / 'source-manifest.json').read_text())['files']

from context_runtime import RuntimeHalt
from fresh_learning_campaign import run_game, replay_game
from fresh_repair_migration import migrate_repaired_game, verify_repair_lineage
from interaction_learning import LearningPlayerBot, LearningState
from match_context import canonical

state = LearningState()
input_model = state.export()

with tempfile.TemporaryDirectory(prefix='private-engine-repair-') as directory:
    original = Path(directory)
    with tarfile.open(BASELINE / 'source-checkpoint.tar.gz', 'r:gz') as archive:
        assert {member.name for member in archive.getmembers()} == set(baseline_manifest)
        for name, expected in baseline_manifest.items():
            body = archive.extractfile(name).read()
            assert raw_hash(body) == expected
            path = original / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    for asset in (ROOT / 'SOURCE').iterdir():
        if asset.is_file() and asset.suffix not in ('.py', '.pyc'):
            shutil.copyfile(asset, original / 'SOURCE' / asset.name)
    shutil.copytree(ROOT / 'RULES', original / 'RULES')
    (original / CONTEXT).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / CONTEXT, original / CONTEXT)
    gap_path = original / 'SOURCE/match_preparation.py'
    marker = 'def _redraw(runtime,seat,choice):\n'
    text = gap_path.read_text()
    assert text.count(marker) == 1
    gap_path.write_text(text.replace(marker, marker +
        "    raise RuntimeHalt('PRIVATE_FIXTURE_ONLY_ENGINE_GAP')\n", 1))
    original_sources = source_bytes(original)
    save_sources('private-original-gap-source.tar.gz', original_sources)
    save_json('original-source-manifest.json', {
        'schema': 'source-checkpoint-v1',
        'files': {name: raw_hash(body) for name, body in original_sources.items()},
        'fixture_only_engine_gap': 'SOURCE/match_preparation.py:_redraw',
        'published_baseline_archive_sha256': raw_hash((BASELINE / 'source-checkpoint.tar.gz').read_bytes()),
    })
    program = """
import json
from pathlib import Path
import sys
from unittest.mock import patch
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'SOURCE'))
import imported_attempts
from fresh_learning_campaign import run_game
from interaction_learning import LearningState
with patch.object(imported_attempts, 'ReferencePilot', side_effect=AssertionError('No reference policy allowed')):
    record = run_game(0, root, context_file=sys.argv[2], campaign_id=sys.argv[3],
                      learning_state=LearningState(), max_commands=2)
print(json.dumps(record, sort_keys=True))
"""
    produced = subprocess.run([sys.executable, '-I', '-B', '-c', program,
        str(original), CONTEXT, CAMPAIGN], check=True, capture_output=True, text=True)
    parent = json.loads(produced.stdout)
    assert parent['status'] == 'HALT'
    assert [row['command'] for row in parent['commands']] == ['BEGIN_PREPARATION', 'REDRAW_CHOICE']
    assert parent['commands'][0]['status'] == 'EXPERIMENTAL_RESOLVED'
    assert parent['commands'][1]['status'] == 'HALT'
    assert parent['commands'][1]['rating']['status'] == 'UNRATED'
    assert 'PRIVATE_FIXTURE_ONLY_ENGINE_GAP' in parent['halt_reason']
    parent_bytes = canonical(parent)
    save_record('private-original-stopped.json.gz', parent)
    current_map = {Path(name).name: raw_hash(body) for name, body in frozen.items()
                   if not Path(name).name.startswith('test_')}
    old_map = parent['sources']
    observed_changes = {name: {'before': old_map.get(name), 'after': current_map.get(name)}
                        for name in sorted(set(old_map) | set(current_map))
                        if old_map.get(name) != current_map.get(name)}
    changes = json.loads((OUT / 'approved-private-source-changes.json').read_text())
    assert set(changes) == {'match_preparation.py', 'fresh_learning_campaign.py', 'fresh_repair_migration.py'}
    assert observed_changes == changes, 'Build differences must match the separately reviewed, frozen map'
    with patch.object(LearningPlayerBot, '__init__', side_effect=AssertionError('No learning actor during migration')), \
            patch.object(LearningPlayerBot, 'choose', side_effect=AssertionError('No policy choice during migration')):
        migrated = migrate_repaired_game(parent, root=ROOT, original_source_root=original,
            approved_changes=changes, repair_note='Private on-disk fixture: remove the injected _redraw gap; preserve the selected redraw.')
        verify_repair_lineage(migrated, ROOT)
        migrated_replay = replay_game(migrated, ROOT)
    assert canonical(parent) == parent_bytes
    assert migrated['status'] == 'HALT'
    assert len(migrated['commands']) == len(parent['commands']) == 2
    assert migrated['initial']['execution_id'] != parent['initial']['execution_id']
    assert physical(migrated['final']) == physical(parent['final'])
    for field in ('seed', 'first', 'campaign_id', 'context_id', 'schedule', 'pilots',
                  'learning_state_before', 'learning_state_after', 'policy_rng_final'):
        assert migrated[field] == parent[field]
    for field in ('command', 'seat', 'args', 'decisions', 'policy_rng_after_choice'):
        assert migrated['commands'][-1][field] == parent['commands'][-1][field]
    assert migrated_replay['exact_match']
    save_record('private-migrated-stopped.json.gz', migrated)
    with patch.object(LearningPlayerBot, 'choose', side_effect=AssertionError('Saved choice cannot be rerolled')):
        resumed = run_game(0, ROOT, context_file=CONTEXT, campaign_id=CAMPAIGN,
            learning_state=state, max_commands=1, previous_record=migrated)
        resumed_replay = replay_game(resumed, ROOT)
    assert resumed['status'] == 'PAUSED'
    assert len(resumed['commands']) == 2
    retry, failed = resumed['commands'][-1], parent['commands'][-1]
    assert retry['status'] == 'EXPERIMENTAL_RESOLVED'
    assert retry['judge']['accepted'] is True
    assert retry['command'] == failed['command'] and retry['args'] == failed['args']
    assert retry['seat'] == failed['seat']
    assert retry['policy_rng_after_choice'] == failed['policy_rng_after_choice']
    assert resumed['policy_rng_final'] == parent['policy_rng_final']
    assert [row['chosen'] for row in retry['decisions']] == [row['chosen'] for row in failed['decisions']]
    assert resumed_replay['exact_match']
    assert resumed['repair_lineage'] == migrated['repair_lineage']
    save_record('private-retried-selection.json.gz', resumed)
    save_json('replay.json', {'migrated': migrated_replay, 'retried': resumed_replay})

assert state.export() == input_model
assert old_history.read_bytes() == old_history_bytes
assert frozen == source_bytes(ROOT)
save_sources('source-checkpoint.tar.gz', frozen)
save_json('source-manifest.json', {'schema': 'source-checkpoint-v1',
    'files': {name: raw_hash(body) for name, body in frozen.items()}})
proof = {
    'date': '2026-11-10', 'status': 'PASS',
    'mode': 'PRIVATE_CROSS_BUILD_REPAIR_FIXTURE_ONLY',
    'original_build_verified_in_separate_process': True,
    'actual_on_disk_engine_source_changed': True,
    'different_execution_ids': True,
    'migration_did_not_retry_failure_or_construct_learning_actor_or_choose': True,
    'immutable_parent_preserved': True,
    'seed_and_complete_physical_checkpoint_rng_preserved': True,
    'policy_identities_choices_rng_and_model_preserved': True,
    'selected_failed_redraw_retried_without_choice': True,
    'migrated_and_retried_records_exact_replay': True,
    'lineage_preserved_after_retry': True,
    'historical_record_bytes_unchanged': True,
    'source_files': len(frozen), 'source_bytes_stable': True,
    'production_games_started': 0, 'production_learning_updates': 0,
    'production_ratings_assigned': 0, 'accepted_fact_finding_credit': 0,
    'final_evaluation_credit': 0,
    'certification': 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED',
    'seconds': round(time.monotonic() - started, 3),
}
save_json('private-repair-proof.json', proof)
print(json.dumps(proof, sort_keys=True, indent=2))
