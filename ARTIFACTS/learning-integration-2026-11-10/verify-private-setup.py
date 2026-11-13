"""Short private integration fixture, not a campaign match or training game."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'SOURCE'))
from context_runtime import RuntimeHalt
from fresh_learning_campaign import run_game, replay_game, commit_completed_game
from interaction_learning import LearningState, LearningPlayerBot
from interaction_scoring import criteria_manifest
import imported_attempts
from match_context import canonical, digest


def write_json(name, value):
    with (OUT / name).open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_record(name, record):
    with (OUT / name).open('xb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
            zipped.write(canonical(record) + b'\n')


started = time.monotonic()
source_bytes = {str(p.relative_to(ROOT)): p.read_bytes() for p in sorted((ROOT / 'SOURCE').glob('*.py'))}
source_hashes = {name: hashlib.sha256(body).hexdigest() for name, body in source_bytes.items()}
old_path = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-04-02/game-0000-segment.json.gz'
old_bytes = old_path.read_bytes()
state = LearningState()
before_model = state.export()
kwargs = {'context_file': 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',
          'campaign_id': 'PRIVATE_PREMATCH_INTEGRATION_FIXTURE_2026_11_10',
          'learning_state': state}
with patch.object(imported_attempts, 'ReferencePilot', side_effect=AssertionError('No reference policy allowed')):
    opening = run_game(0, ROOT, max_commands=3, **kwargs)
    assert opening['status'] == 'PAUSED'
    assert [c['command'] for c in opening['commands']] == ['BEGIN_PREPARATION', 'REDRAW_CHOICE', 'REDRAW_CHOICE']
    write_record('private-opening-fixture.json.gz', opening)
    with patch.object(LearningPlayerBot, 'choose', side_effect=AssertionError('Stored replay cannot reselect')):
        replay_opening = replay_game(opening, ROOT)
        assert replay_opening['exact_match']
        # Only automatic private phase commands follow this fixture's opening.
        resumed = run_game(0, ROOT, max_commands=2, previous_record=opening, **kwargs)
        assert resumed['status'] == 'PAUSED'
        assert resumed['commands'][:3] == opening['commands']
        assert resumed['policy_rng_final'] == opening['policy_rng_final']
        write_record('private-resumed-fixture.json.gz', resumed)
        replay_resumed = replay_game(resumed, ROOT)
        assert replay_resumed['exact_match']
    try:
        commit_completed_game(resumed, state, ROOT)
    except RuntimeHalt as exc:
        assert 'COMPLETED_GAME_REQUIRED' in str(exc)
    else:
        raise AssertionError('A paused fixture must not update learning')

assert state.export() == before_model
assert opening['learning_state_before'] == opening['learning_state_after'] == before_model
assert resumed['learning_state_before'] == resumed['learning_state_after'] == before_model
assert len(resumed['commands']) == len(resumed['tracker_observations']) == 5
assert all(c['judge']['accepted'] is True for c in resumed['commands'])
assert all(c['judge']['certification'] == 'EXPERIMENTAL_NOT_INDEPENDENTLY_CERTIFIED' for c in resumed['commands'])
assert all(c['rating']['learning_eligible'] is False for c in resumed['commands'])
assert old_path.read_bytes() == old_bytes
assert source_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((ROOT / 'SOURCE').glob('*.py'))}
write_json('criteria-manifest.json', criteria_manifest())
write_json('private-fixture-replay.json', {'opening': replay_opening, 'resumed': replay_resumed})
write_json('source-manifest.json', {'schema': 'source-checkpoint-v1', 'files': source_hashes})
with (OUT / 'source-checkpoint.tar.gz').open('xb') as handle:
    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w|') as archive:
            for name, body in source_bytes.items():
                info = tarfile.TarInfo(name)
                info.size = len(body)
                info.mtime = 0
                archive.addfile(info, io.BytesIO(body))
proof = {
    'status': 'PASS', 'mode': 'PRIVATE_PREMATCH_TEST_FIXTURE_ONLY', 'date': '2026-11-10',
    'fixture_commands': 5, 'tracker_observations': 5,
    'named_profiles': {s: opening['pilots'][s]['style'] for s in ('A', 'B')},
    'only_tracker_views_and_public_metadata_to_players': True,
    'opening_and_resumed_exact_replay': True, 'stored_replay_calls_choose': False,
    'saved_choices_and_policy_rng_preserved': True, 'paused_commit_rejected': True,
    'model_unchanged': True, 'criterion_sha256': criteria_manifest()['criterion_sha256'],
    'all_judges_experimental_without_independent_certification': True,
    'all_procedural_steps_ineligible_for_learning': True,
    'historical_record_bytes_unchanged': True, 'source_files': len(source_hashes),
    'source_bytes_stable': True, 'production_campaigns_started': 0,
    'production_games_started': 0, 'production_learning_updates': 0,
    'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
    'same_build_resume_only': True, 'repaired_build_migration_supported': False,
    'seconds': round(time.monotonic() - started, 3),
}
write_json('private-setup-proof.json', proof)
print(json.dumps(proof, indent=2))
