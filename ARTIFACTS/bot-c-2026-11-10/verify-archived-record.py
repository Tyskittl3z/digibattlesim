"""Verify Bot C against stored commands only; no new player decisions/games."""
import copy
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

from context_runtime import ContextRuntime
from field_tracker import FieldTracker
import imported_attempts as diagnostic
from match_context import canonical, digest
from matchup_readiness import load_context_file
import named_player_bots
from selected_mechanics import build_selected_registry


def write_json(name, value):
    with (OUT / name).open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def physical(snapshot):
    value = copy.deepcopy(snapshot)
    value.pop('execution_id', None)
    value['state'].setdefault('resolving_option', None)
    return value


started = time.monotonic()
path = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-04-02/game-0000-segment.json.gz'
original_bytes = path.read_bytes()
record = json.loads(gzip.decompress(original_bytes))
assert len(record['commands']) == 164
source_bytes = {str(p.relative_to(ROOT)): p.read_bytes() for p in sorted((ROOT / 'SOURCE').glob('*.py'))}
source_hashes = {name: hashlib.sha256(body).hexdigest() for name, body in source_bytes.items()}
context = load_context_file(ROOT / record['replay_provenance']['context_file'])
runtime = ContextRuntime(context, record['seed'], record['first'],
                         build_selected_registry(context, ROOT), allow_experimental=True)
assert runtime.snapshot() == record['initial']
tracker = FieldTracker(context)
tracker.start(runtime.snapshot())
frames, expected_checks = [], {'A': 0, 'B': 0}
judge = {'status': 'ENGINE_CHECKED_EXPERIMENTAL', 'accepted': True,
         'evidence': 'ARCHIVED_COMMAND_RESULTS_AND_EXISTING_RECORDED_SUFFIX_REVIEW',
         'new_rules_certification': False}

with patch.object(diagnostic, 'ReferencePilot', side_effect=AssertionError('No reference policy allowed')), \
        patch.object(named_player_bots, 'NamedPlayerBot', side_effect=AssertionError('No player policy allowed')):
    for index, saved in enumerate(record['commands']):
        assert saved['status'] == 'EXPERIMENTAL_RESOLVED'
        for seat in ('A', 'B'):
            assert tracker.player_view(seat) == runtime.public_view(seat), index
        assert tracker.player_view(saved['seat']) == saved['public_view'], index
        before = runtime.snapshot()
        result = diagnostic._apply(runtime, saved['command'], saved['seat'],
                                   copy.deepcopy(saved['args']), ROOT)
        assert canonical(result) == canonical(saved['result']), index
        after = runtime.snapshot()
        observation = tracker.observe(saved, before, after, result, judge)
        assert observation['sequence'] == index + 1
        assert tracker.audit_snapshot() == physical(after)
        for seat in ('A', 'B'):
            assert tracker.player_view(seat) == runtime.public_view(seat), index
        if (saved['command'] == 'CONFIRM_ATTACK' and result.get('success') is True
                and result.get('checked_card')):
            expected_checks[saved['seat']] += 1
        assert tracker.public_metrics()['successful_security_checks'] == expected_checks
        frames.append((copy.deepcopy(saved), before, after, copy.deepcopy(result)))

assert runtime.snapshot() == record['final']
assert runtime.events == record['events']
assert tracker.audit_snapshot() == physical(record['final'])
assert len(tracker.observations) == 164
second = FieldTracker(context)
second.start(record['initial'])
for command, before, after, result in frames:
    second.observe(command, before, after, result, judge)
assert second.observations == tracker.observations
assert second.public_metrics() == tracker.public_metrics()
assert second.audit_snapshot() == tracker.audit_snapshot()
assert path.read_bytes() == original_bytes
assert source_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((ROOT / 'SOURCE').glob('*.py'))}
manifest = tracker.manifest()
write_json('tracker-manifest.json', manifest)
write_json('public-metrics.json', tracker.public_metrics())
with (OUT / 'private-tracker-ledger.json.gz').open('xb') as handle:
    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
        zipped.write(canonical(tracker.observations) + b'\n')
write_json('source-manifest.json', {'schema': 'source-checkpoint-v1', 'files': source_hashes,
                                 'engine_execution_id': runtime.execution_id,
                                 'tracker_source_sha256': manifest['source_sha256']})
with (OUT / 'source-checkpoint.tar.gz').open('xb') as handle:
    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w|') as archive:
            for name, body in source_bytes.items():
                info = tarfile.TarInfo(name)
                info.size = len(body)
                info.mtime = 0
                archive.addfile(info, io.BytesIO(body))
proof = {
    'status': 'PASS', 'date': '2026-11-10', 'mode': 'STORED_COMMAND_VERIFICATION_ONLY',
    'record': str(path.relative_to(ROOT)), 'record_sha256': digest(record),
    'commands_replayed': 164, 'player_views_compared_after_every_command': True,
    'all_saved_results_events_state_and_RNG_exact': True,
    'tracker_physical_snapshot_exact_after_every_command': True,
    'deterministic_observer_ledger_replay': True, 'observations': 164,
    'successful_security_checks': expected_checks,
    'physical_cards_conserved': manifest['physical_card_count'],
    'original_record_bytes_unchanged': True, 'source_bytes_stable': True,
    'source_files': len(source_hashes), 'player_policy_calls': 0,
    'new_actual_gameplay_commands': 0, 'fresh_matches_started': 0,
    'learning_updates': 0, 'strategic_ratings': 0,
    'whole_game_judge_certification': False, 'full_match_credit': 0,
    'seconds': round(time.monotonic() - started, 3),
}
write_json('archived-observer-proof.json', proof)
print(json.dumps(proof, indent=2))
