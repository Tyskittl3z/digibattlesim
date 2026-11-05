"""Saved-context selection never grants new effects or transfers evidence."""
import contextlib
import copy
import gzip
import hashlib
import io
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from context_runtime import RuntimeHalt
import imported_attempts as runner


ROOT = Path(__file__).resolve().parents[1]
MIRROR = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
MIRROR_ID = '9dd326339d64f263c7570a33b03e4ab9d57c1cd466ec0fddffcec4d7ea5bcd8d'
ORIGINAL_ID = '53f4e043b49fca0bf6e691754098e73774995cfee182e7c8245cf446e2d70733'


class ImportedContextSelectionTests(unittest.TestCase):
    def attempt(self, context_file=MIRROR):
        return runner.run_attempt(0, ROOT, 1, context_file=context_file)

    def test_mirror_attempt_records_selected_bytes_and_fresh_context_identities(self):
        mirror = self.attempt()
        original = runner.run_attempt(0, ROOT, 1)
        self.assertEqual(mirror['context_id'], MIRROR_ID)
        self.assertEqual(original['context_id'], ORIGINAL_ID)
        self.assertNotEqual(mirror['seed'], original['seed'])
        self.assertNotEqual(mirror['pilot_id'], original['pilot_id'])
        self.assertEqual(mirror['replay_provenance']['context_file'], MIRROR)
        self.assertEqual(mirror['replay_provenance']['context_file_sha256'],
                         hashlib.sha256((ROOT / MIRROR).read_bytes()).hexdigest())
        self.assertEqual(mirror['initial']['context_id'], MIRROR_ID)
        self.assertEqual(mirror['commands'][0]['command'], 'BEGIN_PREPARATION')
        self.assertEqual(mirror['commands'][0]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(mirror['status'], 'HALT')
        self.assertEqual(mirror['accepted_fact_finding_credit'], 0)
        self.assertEqual(mirror['final_evaluation_credit'], 0)
        for pilot in mirror['pilots'].values():
            self.assertEqual(pilot['context_id'], MIRROR_ID)
            self.assertEqual(pilot['training_data'], [])
            self.assertIsNone(pilot['roadmap'])

    def test_explicit_mirror_replay_is_exact_without_mutating_caller_record(self):
        record = self.attempt()
        before = copy.deepcopy(record)
        replay = runner.replay_attempt(record, ROOT)
        self.assertTrue(replay['exact_match'])
        self.assertEqual(replay['saved_record_sha256'], replay['replayed_record_sha256'])
        self.assertEqual(record, before)

    def test_replay_rejects_changed_file_bytes_before_rerunning(self):
        record = self.attempt()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / MIRROR
            path.parent.mkdir(parents=True)
            path.write_bytes((ROOT / MIRROR).read_bytes() + b'\n')
            with patch.object(runner, 'run_attempt', side_effect=AssertionError('replay started')):
                with self.assertRaisesRegex(RuntimeHalt, 'REPLAY_CONTEXT_FILE_CHANGED'):
                    runner.replay_attempt(record, root)

    def test_replay_rejects_context_identity_mismatch_before_rerunning(self):
        record = self.attempt()
        record['context_id'] = ORIGINAL_ID
        before = copy.deepcopy(record)
        with patch.object(runner, 'run_attempt', side_effect=AssertionError('replay started')):
            with self.assertRaisesRegex(RuntimeHalt, 'REPLAY_CONTEXT_ID_MISMATCH'):
                runner.replay_attempt(record, ROOT)
        self.assertEqual(record, before)

    def test_replay_rejects_context_replaced_between_preflight_and_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / 'RULES', root / 'RULES')
            for relative in (MIRROR, runner.CONTEXT_FILE):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            selected = root / 'selected.json'
            selected.write_bytes((ROOT / MIRROR).read_bytes())
            record = runner.run_attempt(0, root, 1, context_file='selected.json')
            real_run = runner.run_attempt
            executed = []

            def replace_before_rerun(*args, **kwargs):
                selected.write_bytes((ROOT / runner.CONTEXT_FILE).read_bytes())
                replayed = real_run(*args, **kwargs)
                executed.append(replayed)
                return replayed

            with patch.object(runner, 'run_attempt', side_effect=replace_before_rerun):
                with self.assertRaisesRegex(RuntimeHalt, 'REPLAY_CONTEXT_FILE_CHANGED'):
                    runner.replay_attempt(record, root)
            self.assertEqual(executed, [], 'Changed replay inputs must fail before a game runs')

    def test_context_selection_uses_the_same_bytes_for_hash_and_definition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (MIRROR, runner.CONTEXT_FILE):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            selected = root / 'selected.json'
            mirror_bytes = (ROOT / MIRROR).read_bytes()
            selected.write_bytes(mirror_bytes)
            real_load = runner.load_context_file

            def swap_during_second_read(path):
                selected.write_bytes((ROOT / runner.CONTEXT_FILE).read_bytes())
                context = real_load(path)
                selected.write_bytes(mirror_bytes)
                return context

            with patch.object(runner, 'load_context_file', side_effect=swap_during_second_read):
                context, _, recorded_hash = runner._load_context_selection(root, 'selected.json')
            self.assertEqual(context.matchup_id, MIRROR_ID)
            self.assertEqual(recorded_hash, hashlib.sha256(mirror_bytes).hexdigest())

    def test_missing_saved_context_hash_cannot_disable_replay_source_checks(self):
        record = self.attempt()
        del record['replay_provenance']['context_file_sha256']
        with patch.object(runner, 'run_attempt', side_effect=AssertionError('replay started')):
            with self.assertRaisesRegex(RuntimeHalt, 'REPLAY_CONTEXT_PROVENANCE_INVALID'):
                runner.replay_attempt(record, ROOT)

    def test_original_default_and_legacy_path_fallback_use_original_context(self):
        record = runner.run_attempt(0, ROOT, 1)
        self.assertEqual(record['context_id'], ORIGINAL_ID)
        self.assertEqual(record['replay_provenance']['context_file'], runner.CONTEXT_FILE)
        self.assertTrue(runner.replay_attempt(record, ROOT)['exact_match'])
        del record['replay_provenance']['context_file']
        replay = runner.replay_attempt(record, ROOT)
        self.assertFalse(replay['exact_match'])
        self.assertEqual(replay['index'], 0)

    def test_context_path_escape_and_symlink_escape_are_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'root'
            root.mkdir()
            external = Path(temporary) / 'external.json'
            external.write_bytes((ROOT / MIRROR).read_bytes())
            (root / 'escaped.json').symlink_to(external)
            for context_file in ('../external.json', 'escaped.json', external):
                with self.subTest(context_file=context_file):
                    output = root / 'out'
                    with self.assertRaisesRegex(RuntimeHalt, 'CONTEXT_PATH_OUTSIDE_ROOT'):
                        runner.write_attempts(output, root, 2, 1, context_file=context_file)
                    self.assertFalse(output.exists())

    def test_edited_source_ids_are_not_authorized_by_an_input_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            # A temporary root can hold the edited input, but cannot create an
            # approved capability by changing its saved source identities.
            root = Path(temporary)
            edited = json.loads((ROOT / MIRROR).read_bytes())
            edited['context']['decks']['B']['source_id'] = 'unselected-list'
            (root / 'edited.json').write_text(json.dumps(edited))
            with self.assertRaisesRegex(RuntimeHalt, 'SELECTED_CONTEXT_REQUIRED'):
                runner.run_attempt(0, root, 1, context_file='edited.json')

    def test_mirror_cohort_records_both_starts_and_preserves_original_before_failed_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'cohort'
            summary = runner.write_attempts(out, ROOT, 2, 1, context_file=MIRROR)
            self.assertEqual(summary['first_counts'], {'A': 1, 'B': 1})
            self.assertEqual(summary['exact_replay_matches'], 2)
            self.assertEqual(summary['accepted_fact_finding_credit'], 0)
            for index in range(2):
                record = json.loads(gzip.decompress((out / f'attempt-{index:04d}.json.gz').read_bytes()))
                self.assertEqual(record['context_id'], MIRROR_ID)
                self.assertEqual(record['replay_provenance']['context_file'], MIRROR)
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'failed-cohort'
            with patch.object(runner, 'replay_attempt', side_effect=RuntimeHalt('injected interruption')):
                with self.assertRaisesRegex(RuntimeHalt, 'injected interruption'):
                    runner.write_attempts(out, ROOT, 2, 1, context_file=MIRROR)
            record = json.loads(gzip.decompress((out / 'attempt-0000.json.gz').read_bytes()))
            failure = json.loads((out / 'replay-failure-0000.json').read_bytes())
            self.assertEqual(record['context_id'], MIRROR_ID)
            self.assertEqual(failure['seed'], record['seed'])
            self.assertFalse((out / 'attempt-0001.json.gz').exists())

    def test_cli_selects_mirror_context_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'cli-cohort'
            with contextlib.redirect_stdout(io.StringIO()):
                status = runner.main(['--out', str(out), '--count', '2', '--max-commands', '1',
                                      '--root', str(ROOT), '--context-file', MIRROR])
            self.assertEqual(status, 0)
            record = json.loads(gzip.decompress((out / 'attempt-0000.json.gz').read_bytes()))
            self.assertEqual(record['context_id'], MIRROR_ID)

    def test_context_switch_during_cohort_cannot_create_a_mixed_summary(self):
        # Exercise the real runner for both records, then inject an unintended
        # selected-context switch at the per-attempt boundary.
        mirror = self.attempt()
        original = runner.run_attempt(1, ROOT, 1)
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'cohort'
            with patch.object(runner, 'run_attempt', side_effect=[mirror, mirror, original]):
                with self.assertRaisesRegex(RuntimeHalt, 'COHORT_CONTEXT_CHANGED'):
                    runner.write_attempts(out, ROOT, 2, 1, context_file=MIRROR)
            self.assertFalse((out / 'summary.json').exists())
            saved = json.loads(gzip.decompress((out / 'attempt-0001.json.gz').read_bytes()))
            failure = json.loads((out / 'replay-failure-0001.json').read_bytes())
            self.assertEqual(saved['context_id'], ORIGINAL_ID)
            self.assertEqual(failure['seed'], original['seed'])
            self.assertEqual(failure['reason'], 'COHORT_CONTEXT_CHANGED')


if __name__ == '__main__':
    unittest.main()
