"""Replay only segment09's 139 saved successful commands at archived bytes.

Run from any directory with Python 3.  No new action or policy choice is made.
The JSON result is written next to this script; SOURCE and prior evidence remain
read-only. This is software/physical replay evidence, not rules certification.
"""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import time


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_suffix('.json')
SEGMENT = ROOT / 'ARTIFACTS/gameplay-continuations-2026-11-03-09'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def main():
    started = time.monotonic()
    manifest_path = SEGMENT / 'source-manifest.json'
    archive_path = SEGMENT / 'source-checkpoint.tar.gz'
    record_path = SEGMENT / 'game-0000-segment.json.gz'
    manifest = json.loads(manifest_path.read_bytes())
    record_bytes = record_path.read_bytes()
    record = json.loads(gzip.decompress(record_bytes))
    assert record['seed'] == 12017913134550805276
    assert len(record['commands']) == 140
    assert all(c['status'] == 'EXPERIMENTAL_RESOLVED' for c in record['commands'][:-1])
    assert record['commands'][-1]['status'] == 'HALT'
    assert record['commands'][-1]['command'] == 'DECLARE_ATTACK'
    assert record['commands'][-1]['args'] == {
        'attacker': 'B:BT11-032#1', 'kind': 'DECLARE_ATTACK', 'target': 'PLAYER'}
    expected = manifest['source_sha256']
    with tempfile.TemporaryDirectory(prefix='archive09-proof-') as scratch:
        archived_root = Path(scratch)
        with tarfile.open(archive_path, 'r:gz') as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            assert len(names) == len(set(names)), 'Duplicate archive members'
            assert set(names) == set(expected), 'Archive/manifest names differ'
            for member in members:
                assert member.isfile(), 'Unexpected non-file archive member'
                relative = Path(member.name)
                assert not relative.is_absolute() and '..' not in relative.parts
                body = archive.extractfile(member).read()
                assert sha(body) == expected[member.name], member.name
                target = archived_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
        # Context/source paths intentionally reject symlinks escaping the root.
        # Copy exact inputs into the temporary root, leaving originals read-only.
        context_relative = Path(record['replay_provenance']['context_file'])
        context_target = archived_root / context_relative
        context_target.parent.mkdir(parents=True, exist_ok=True)
        context_target.write_bytes((ROOT / context_relative).read_bytes())
        shutil.copytree(ROOT / 'RULES', archived_root / 'RULES')
        sys.path.insert(0, str(archived_root / 'SOURCE'))
        import imported_attempts as runner
        from context_runtime import ContextRuntime
        from match_context import canonical, digest
        from selected_mechanics import build_selected_registry

        assert Path(runner.__file__).resolve().is_relative_to(archived_root)
        context, context_file, context_sha = runner._load_context_selection(
            archived_root, record['replay_provenance']['context_file'])
        assert context_sha == record['replay_provenance']['context_file_sha256']
        assert context.matchup_id == record['context_id']
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, archived_root),
                                 allow_experimental=True)
        assert canonical(runtime.snapshot()) == canonical(record['initial'])
        comparisons = []
        for index, command in enumerate(record['commands'][:-1]):
            assert canonical(runtime.public_view(command['seat'])) == canonical(command['public_view']), (
                'Pre-command public view mismatch', index)
            result = runner._apply(runtime, command['command'], command['seat'],
                                   command['args'], archived_root)
            assert canonical(result) == canonical(command['result']), ('Result mismatch', index)
            runtime.verify()
            comparisons.append({'index': index, 'command': command['command'],
                                'public_view_exact': True, 'result_exact': True,
                                'physical_verify_passed': True})
        final = runtime.snapshot()
        assert canonical(final) == canonical(record['final'])
        assert canonical(final) == canonical(record['halts'][-1]['before'])
        assert runtime.execution_id == manifest['execution_id']
        # This final saved HALT is deliberately not executed.
        assert canonical(runtime.public_view(record['commands'][-1]['seat'])) == canonical(
            record['commands'][-1]['public_view'])
        physical = []
        for owner in ('A', 'B'):
            physical.extend(card.key for cards in runtime.state.zones[owner].values() for card in cards)
            physical.extend(card.key for card in runtime.state.breeding[owner])
            physical.extend(card.key for stack in runtime.state.battle[owner].values() for card in stack.cards)
        counts = Counter(key.split(':')[0] for key in physical)
        assert len(physical) == len(set(physical)) == 108
        assert counts == {'A': 54, 'B': 54}
        assert runtime.state.attack is None and not runtime.state.pending
        assert (runtime.state.turn, runtime.state.active, runtime.state.memory,
                runtime.state.phase) == (10, 'B', 5, 'MAIN')
        result = {
            'schema': 'ARCHIVED_SAVED_PREFIX_PROOF_V1',
            'status': 'PASS',
            'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
            'elapsed_seconds': round(time.monotonic() - started, 3),
            'record': str(record_path.relative_to(ROOT)),
            'record_gzip_sha256': sha(record_bytes),
            'record_canonical_sha256': digest(record),
            'archive': str(archive_path.relative_to(ROOT)),
            'archive_sha256': sha(archive_path.read_bytes()),
            'manifest': str(manifest_path.relative_to(ROOT)),
            'manifest_sha256': sha(manifest_path.read_bytes()),
            'archive_file_count': len(members),
            'manifest_source_count': len(expected),
            'all_archived_source_hashes_match_manifest': True,
            'execution_id': runtime.execution_id,
            'initial_snapshot_exact': True,
            'saved_successful_commands_replayed': len(comparisons),
            'every_precommand_public_view_exact': True,
            'every_command_result_exact': True,
            'physical_verify_after_each_saved_command': True,
            'final_full_snapshot_exact': True,
            'final_before_halt_snapshot_exact': True,
            'final_state_sha256': digest(final['state']),
            'final_rng_sha256': digest(final['rng_state']),
            'unique_physical_cards': len(set(physical)),
            'physical_cards_by_owner': dict(counts),
            'seed': runtime.seed,
            'first': runtime.first,
            'turn': runtime.state.turn,
            'active': runtime.state.active,
            'memory': runtime.state.memory,
            'phase': runtime.state.phase,
            'stopped_before_saved_halt_command_index': len(comparisons),
            'halt_command_executed': False,
            'new_gameplay_commands': 0,
            'certification': 'SOFTWARE_REPLAY_ONLY_NOT_RULES_CERTIFICATION',
            'accepted_fact_finding_credit': 0,
            'final_evaluation_credit': 0,
            'commands': comparisons,
        }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'commands'}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
