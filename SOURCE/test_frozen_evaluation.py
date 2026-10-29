"""Final-runner tests use synthetic eligibility; they never certify gameplay."""
from __future__ import annotations

from contextlib import ExitStack
import gzip
import hashlib
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from match_evidence import ROOT, canonical_bytes, digest, provenance

try:
    frozen = importlib.import_module('frozen_evaluation')
except ModuleNotFoundError:
    frozen = None


@unittest.skipUnless(frozen is not None, 'frozen_evaluation module is required')
class FrozenEvaluationFreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.temp = Path(self.tmp.name)
        schedule_file = ROOT / 'EVALUATION/preparation-2026-10-29-02/SEEDS.json.gz'
        self.schedule_bytes = schedule_file.read_bytes()
        self.schedule = json.loads(gzip.decompress(self.schedule_bytes))

    def make_preparation(self, schedule=None, packed=None):
        schedule = self.schedule if schedule is None else schedule
        packed = gzip.compress(canonical_bytes(schedule), mtime=0) if packed is None else packed
        folder = self.temp / ('preparation-' + str(len(list(self.temp.iterdir()))))
        folder.mkdir()
        (folder / 'SEEDS.json.gz').write_bytes(packed)
        report = {
            'schema': 'loaded-pair-evaluation-preparation-v1',
            'status': 'ELIGIBLE_PENDING_FREEZE',
            'frozen': False,
            'evaluation_matches_played': 0,
            'target_matches': 10000,
            'planned_starts': {'A': 5000, 'B': 5000},
            'schedule_file_sha256': hashlib.sha256(packed).hexdigest(),
            'schedule_sha256': digest(schedule),
        }
        (folder / 'PREPARATION.json').write_bytes(canonical_bytes(report))
        return folder

    def synthetic_gate(self):
        inputs = provenance(ROOT)
        return {
            'schema': 'loaded-pair-evaluation-gate-v1',
            'eligible': True,
            'status': 'ELIGIBLE_PENDING_FREEZE',
            'blockers': [],
            'cohort_sha256': '1' * 64,
            'provenance_sha256': digest(inputs),
            'review_separation': {
                'rules_review': 'BOUND_ATTESTATION_PRESENT',
                'strategy_review': 'BOUND_ATTESTATION_PRESENT',
            },
        }

    def review_files(self):
        rules = self.temp / 'rules-review.json'
        strategy = self.temp / 'strategy-review.json'
        rules.write_bytes(canonical_bytes({'kind': 'INDEPENDENT_RULES_REVIEW'}))
        strategy.write_bytes(canonical_bytes({'kind': 'STRATEGY_EVALUATION_REVIEW'}))
        return rules, strategy

    def test_api_exists(self):
        self.assertTrue(callable(frozen.create_freeze))
        self.assertTrue(callable(frozen.load_freeze))
        self.assertTrue(callable(frozen.validate_schedule))

    def test_current_blocked_gate_cannot_create_a_freeze(self):
        output = self.temp / 'blocked-run'
        with self.assertRaisesRegex(ValueError, 'eligib'):
            frozen.create_freeze(
                ROOT,
                ROOT / 'ARTIFACTS/current-2026-10-29-02',
                ROOT / 'EVALUATION/preparation-2026-10-29-02',
                output,
                None,
                None,
            )
        self.assertFalse(output.exists())

    def test_schedule_rejects_changed_seed_duplicate_and_unbalanced_starts(self):
        mutations = []
        changed = [dict(row) for row in self.schedule]
        changed[0]['seed'] += 1
        mutations.append(changed)
        duplicate = [dict(row) for row in self.schedule]
        duplicate[1] = dict(duplicate[0])
        mutations.append(duplicate)
        unbalanced = [dict(row) for row in self.schedule]
        unbalanced[1]['index'] = 10060
        unbalanced[1]['seed'] = frozen.seed_for(10060)
        unbalanced[1]['first'] = 'A'
        mutations.append(unbalanced)
        for schedule in mutations:
            with self.subTest(first_rows=schedule[:2]):
                with self.assertRaises(ValueError):
                    frozen.validate_schedule(schedule, digest(schedule))

    def test_schedule_file_hash_mismatch_is_rejected_before_output_creation(self):
        preparation = self.make_preparation()
        report_path = preparation / 'PREPARATION.json'
        report = json.loads(report_path.read_bytes())
        report['schedule_file_sha256'] = '0' * 64
        report_path.write_bytes(canonical_bytes(report))
        output = self.temp / 'bad-schedule-run'
        rules, strategy = self.review_files()
        with patch.object(frozen, 'assess_eligibility', return_value=self.synthetic_gate()):
            with self.assertRaisesRegex(ValueError, 'schedule file hash'):
                frozen.create_freeze(ROOT, ROOT / 'ARTIFACTS/current-2026-10-29-02',
                                     preparation, output, rules, strategy)
        self.assertFalse(output.exists())

    def test_eligible_freeze_binds_all_components_and_loads_exact_schedule(self):
        preparation = self.make_preparation()
        output = self.temp / 'frozen-run'
        rules, strategy = self.review_files()
        gate = self.synthetic_gate()
        with patch.object(frozen, 'assess_eligibility', return_value=gate):
            manifest = frozen.create_freeze(
                ROOT,
                ROOT / 'ARTIFACTS/current-2026-10-29-02',
                preparation,
                output,
                rules,
                strategy,
            )
        self.assertEqual(manifest['status'], 'FROZEN_READY')
        self.assertEqual(set(manifest['frozen_inputs']), set(frozen.FROZEN_COMPONENTS))
        self.assertTrue(all(len(value) == 64 for value in manifest['frozen_inputs'].values()))
        self.assertEqual(manifest['frozen_inputs']['schedule'], digest(self.schedule))
        loaded, schedule = frozen.load_freeze(output)
        self.assertEqual(loaded, manifest)
        self.assertEqual(schedule, self.schedule)
        self.assertEqual(len(schedule), 10000)


class FrozenEvaluationMissingModuleTest(unittest.TestCase):
    def test_frozen_evaluation_module_is_present(self):
        self.assertIsNotNone(frozen, 'frozen_evaluation module is missing')


if __name__ == '__main__':
    unittest.main()
