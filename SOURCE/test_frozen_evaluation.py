"""Final-runner tests use synthetic eligibility; they never certify gameplay."""
from __future__ import annotations

import gzip
import hashlib
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from match_evidence import ROOT, canonical_bytes, digest, provenance, record_match

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
            'gate': self.synthetic_gate(),
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

    def create_synthetic_freeze(self, schedule=None):
        schedule = self.schedule if schedule is None else schedule
        preparation = self.make_preparation(schedule=schedule)
        output = self.temp / ('run-' + str(len(list(self.temp.iterdir()))))
        rules, strategy = self.review_files()
        with patch.object(frozen, 'assess_eligibility', return_value=self.synthetic_gate()):
            frozen.create_freeze(ROOT, ROOT / 'ARTIFACTS/current-2026-10-29-02',
                                 preparation, output, rules, strategy)
        return output

    def schedule_with_completed_first_match(self):
        schedule = [dict(row) for row in self.schedule]
        complete_position = next(i for i, row in enumerate(schedule) if row['index'] == 62)
        schedule[0], schedule[complete_position] = schedule[complete_position], schedule[0]
        return schedule

    def completed_runner(self, index, provenance_sha256):
        record = record_match(index, provenance_sha256)
        self.assertEqual(record['status'], 'SOFTWARE_COMPLETED')
        return record

    def halted_runner(self, index, provenance_sha256):
        record = record_match(index, provenance_sha256)
        transcript = record['transcript']
        if transcript['events'] and transcript['events'][-1]['type'] in (
                'GAME_END', 'WIN_DRAW_PHASE_DECKOUT'):
            transcript['events'].pop()
        record['status'] = 'HALT'
        record['judge_certified'] = False
        record['rule_check_status'] = 'HALT'
        transcript['status'] = 'JUDGE_HALT'
        transcript['winner'] = None
        transcript['halt_reason'] = 'JudgeHalt: SYNTHETIC_RULES_HALT'
        transcript['events'].append({
            't': transcript['turn'], 'actor': record['final_state']['runtime']['active'],
            'type': 'JUDGE_HALT', 'reason': transcript['halt_reason'],
        })
        record['final_state']['runtime']['winner'] = None
        return record

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
        self.assertEqual(
            [(judge['name'], judge['role']) for judge in manifest['judge_layers']],
            [('Justitia', 'RUNTIME_INTEGRITY'),
             ('Dike', 'INDEPENDENT_RULES'),
             ('Týr', 'FINAL_EVIDENCE_AUDIT')],
        )
        self.assertEqual(manifest['bots'], [
            {'name': 'Bot A', 'seat': 'A', 'deck': 'Jupitermon'},
            {'name': 'Bot B', 'seat': 'B', 'deck': 'Amaterasumon/Toho'},
        ])
        self.assertEqual(set(manifest['frozen_inputs']), set(frozen.FROZEN_COMPONENTS))
        self.assertTrue(all(len(value) == 64 for value in manifest['frozen_inputs'].values()))
        self.assertEqual(manifest['frozen_inputs']['schedule'], digest(self.schedule))
        loaded, schedule = frozen.load_freeze(output)
        self.assertEqual(loaded, manifest)
        self.assertEqual(schedule, self.schedule)
        self.assertEqual(len(schedule), 10000)

    def test_one_valid_match_is_credited_at_its_exact_schedule_position(self):
        run = self.create_synthetic_freeze(self.schedule_with_completed_first_match())
        result = frozen.run_frozen(run, match_runner=self.completed_runner, stop_after=1)
        self.assertEqual(result['status'], 'PAUSED')
        self.assertEqual(result['credited_matches'], 1)
        checkpoint = json.loads((run / 'CHECKPOINT.json').read_bytes())
        self.assertEqual(checkpoint['schedule_position'], 1)
        self.assertEqual(checkpoint['next_match']['index'], 61)
        records = list((run / 'records').glob('*.json.gz'))
        self.assertEqual(len(records), 1)
        record = json.loads(gzip.decompress(records[0].read_bytes()))
        self.assertEqual(record['index'], 62)
        self.assertEqual(record['seed'], frozen.seed_for(62))

    def test_wrong_record_identity_never_advances_checkpoint(self):
        run = self.create_synthetic_freeze()

        def wrong_runner(index, provenance_sha256):
            return record_match(62, provenance_sha256)

        with self.assertRaisesRegex(ValueError, 'identity'):
            frozen.run_frozen(run, match_runner=wrong_runner, stop_after=1)
        checkpoint = json.loads((run / 'CHECKPOINT.json').read_bytes())
        self.assertEqual(checkpoint['schedule_position'], 0)
        self.assertEqual(list((run / 'records').glob('*')), [])

    def test_malformed_checkpoint_fails_closed_with_a_validation_error(self):
        run = self.create_synthetic_freeze()
        (run / 'CHECKPOINT.json').write_bytes(b'[]\n')
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            frozen.status_frozen(run)

    def test_rules_halt_is_preserved_without_seed_replacement_or_credit(self):
        run = self.create_synthetic_freeze()
        result = frozen.run_frozen(run, match_runner=self.halted_runner)
        self.assertEqual(result['status'], 'BLOCKED_HALT')
        self.assertEqual(result['credited_matches'], 0)
        self.assertEqual(result['halted_match'], self.schedule[0])
        checkpoint = json.loads((run / 'CHECKPOINT.json').read_bytes())
        self.assertEqual(checkpoint['schedule_position'], 0)
        self.assertEqual(checkpoint['next_match'], self.schedule[0])
        self.assertEqual(checkpoint['halt_kind'], 'RULES')
        halt_files = list((run / 'halts').glob('*.json.gz'))
        self.assertEqual(len(halt_files), 1)
        envelope = json.loads(gzip.decompress(halt_files[0].read_bytes()))
        self.assertEqual(envelope['scheduled_match'], self.schedule[0])
        self.assertEqual(envelope['record']['seed'], self.schedule[0]['seed'])

    def test_interruption_orphan_replays_same_seed_before_credit(self):
        run = self.create_synthetic_freeze(self.schedule_with_completed_first_match())
        calls = []

        def runner(index, provenance_sha256):
            calls.append(index)
            return self.completed_runner(index, provenance_sha256)

        def interrupt_after_record(_record):
            raise RuntimeError('synthetic infrastructure interruption')

        with self.assertRaisesRegex(RuntimeError, 'infrastructure interruption'):
            frozen.run_frozen(run, match_runner=runner, stop_after=1,
                              interruption_hook=interrupt_after_record)
        checkpoint = json.loads((run / 'CHECKPOINT.json').read_bytes())
        self.assertEqual(checkpoint['schedule_position'], 0)
        self.assertEqual(len(list((run / 'records').glob('*.json.gz'))), 1)
        result = frozen.resume_frozen(run, match_runner=runner, stop_after=1)
        self.assertEqual(result['credited_matches'], 1)
        self.assertEqual(calls, [62, 62])
        self.assertEqual(len(list((run / 'records').glob('*.json.gz'))), 1)

    def test_credited_record_is_bound_to_immutable_receipt_on_resume(self):
        run = self.create_synthetic_freeze(self.schedule_with_completed_first_match())
        frozen.run_frozen(run, match_runner=self.completed_runner, stop_after=1)
        record_path = next((run / 'records').glob('*.json.gz'))
        record = json.loads(gzip.decompress(record_path.read_bytes()))
        replacement = 'B' if record['transcript']['winner'] == 'A' else 'A'
        record['transcript']['winner'] = replacement
        record['final_state']['runtime']['winner'] = replacement
        record['transcript']['events'][-1]['winner'] = replacement
        raw = canonical_bytes(record)
        packed = gzip.compress(raw, mtime=0)
        record_path.write_bytes(packed)
        receipt_path = next((run / 'receipts').glob('*.json'))
        receipt = json.loads(receipt_path.read_bytes())
        receipt['record_sha256'] = hashlib.sha256(raw).hexdigest()
        receipt['file_sha256'] = hashlib.sha256(packed).hexdigest()
        receipt_path.write_bytes(canonical_bytes(receipt))

        def forbidden_runner(_index, _provenance_sha256):
            self.fail('tampered credited evidence must be rejected before another match')

        with self.assertRaisesRegex(ValueError, 'hash|chain'):
            frozen.resume_frozen(run, match_runner=forbidden_runner, stop_after=1)
        self.assertEqual(len(list((run / 'receipts').glob('*.json'))), 1)

    def test_orphan_halt_is_recovered_before_replaying_or_finalizing(self):
        run = self.create_synthetic_freeze()
        original_write_checkpoint = frozen._write_checkpoint
        with patch.object(frozen, '_write_checkpoint', side_effect=OSError('checkpoint interrupted')):
            with self.assertRaisesRegex(OSError, 'checkpoint interrupted'):
                frozen.run_frozen(run, match_runner=self.halted_runner)
        self.assertEqual(len(list((run / 'halts').glob('*.json.gz'))), 1)

        def forbidden_runner(_index, _provenance_sha256):
            self.fail('a preserved orphan HALT must block before replay')

        with patch.object(frozen, '_write_checkpoint', wraps=original_write_checkpoint):
            result = frozen.resume_frozen(run, match_runner=forbidden_runner)
        self.assertEqual(result['status'], 'BLOCKED_HALT')
        self.assertEqual(result['halted_match'], self.schedule[0])
        checkpoint = json.loads((run / 'CHECKPOINT.json').read_bytes())
        self.assertEqual(checkpoint['halt_kind'], 'RULES')

    def test_atomic_write_failure_does_not_leave_a_blocking_temp_file(self):
        target = self.temp / 'atomic.json'
        with patch.object(frozen.os, 'replace', side_effect=OSError('replace interrupted')):
            with self.assertRaisesRegex(OSError, 'replace interrupted'):
                frozen.atomic_write(target, b'first')
        self.assertEqual(list(self.temp.glob('atomic.json*.tmp')), [])
        frozen.atomic_write(target, b'second')
        self.assertEqual(target.read_bytes(), b'second')

    def test_integrity_failed_halt_is_preserved_as_blocking_diagnostic(self):
        run = self.create_synthetic_freeze()

        def integrity_halt(index, provenance_sha256):
            record = self.halted_runner(index, provenance_sha256)
            record['physical_integrity'] = {
                'status': 'FAIL', 'reason': 'PHYSICAL_CARD_MISMATCH fixture'}
            return record

        result = frozen.run_frozen(run, match_runner=integrity_halt)
        self.assertEqual(result['status'], 'BLOCKED_HALT')
        self.assertEqual(result['credited_matches'], 0)
        halt_path = next((run / 'halts').glob('*.json.gz'))
        envelope = json.loads(gzip.decompress(halt_path.read_bytes()))
        self.assertEqual(envelope['scheduled_match'], self.schedule[0])
        self.assertIn('physical integrity', envelope['validation_error'])
        self.assertEqual(envelope['record']['physical_integrity']['status'], 'FAIL')

    def test_preparation_must_bind_live_cohort_and_exclude_all_training_seeds(self):
        preparation = self.make_preparation()
        report_path = preparation / 'PREPARATION.json'
        report = json.loads(report_path.read_bytes())
        report['gate']['cohort_sha256'] = '2' * 64
        report_path.write_bytes(canonical_bytes(report))
        rules, strategy = self.review_files()
        output = self.temp / 'stale-gate-run'
        with patch.object(frozen, 'assess_eligibility', return_value=self.synthetic_gate()):
            with self.assertRaisesRegex(ValueError, 'cohort|preparation'):
                frozen.create_freeze(ROOT, ROOT / 'ARTIFACTS/current-2026-10-29-02',
                                     preparation, output, rules, strategy)
        self.assertFalse(output.exists())

        preparation = self.make_preparation()
        cohort = self.temp / 'expanded-cohort'
        cohort.mkdir()
        (cohort / 'cohort.json').write_bytes(canonical_bytes({
            'records': [{'index': self.schedule[0]['index'],
                         'seed': self.schedule[0]['seed']}]}))
        output = self.temp / 'overlap-run'
        with patch.object(frozen, 'assess_eligibility', return_value=self.synthetic_gate()):
            with self.assertRaisesRegex(ValueError, 'overlap'):
                frozen.create_freeze(ROOT, cohort, preparation, output, rules, strategy)
        self.assertFalse(output.exists())

    def test_changed_frozen_input_requires_full_restart_without_running_match(self):
        run = self.create_synthetic_freeze(self.schedule_with_completed_first_match())
        manifest, schedule = frozen.load_freeze(run)
        changed = dict(manifest['frozen_inputs'], engine='f' * 64)

        def forbidden_runner(_index, _provenance_sha256):
            self.fail('match runner must not execute after frozen input change')

        with patch.object(frozen, '_component_hashes', return_value=changed):
            result = frozen.resume_frozen(run, match_runner=forbidden_runner, stop_after=1)
        self.assertEqual(result['status'], 'RESTART_FULL_EVALUATION')
        self.assertTrue(result['invalidate_all_prior_results'])
        self.assertEqual(result['restart_schedule_from_position'], 0)

    def test_final_aggregate_reports_exact_numerical_totals(self):
        records = []
        for position, row in enumerate(self.schedule):
            winner = 'A' if position < 6000 else 'B'
            events = [{'type': 'PAID_PLAY', 'card': 'BT24-031#1'}]
            if position % 2 == 0:
                events.append({'type': 'JUDGE_PATH', 'kind': 'FIXTURE_PATH',
                               'card': 'BT24-031'})
            if position % 4 == 0:
                events.append({'type': 'BOT_DECISION', 'decision_type': 'FIXTURE',
                               'source': 'BT24-031', 'chosen': 'ACTIVATE',
                               'lane_id': 'fixture-green',
                               'combo_id': 'fixture-combo'})
            records.append({'index': row['index'], 'seed': row['seed'],
                            'first': row['first'], 'winner': winner,
                            'turn': position % 3 + 5, 'events': events})
        result = frozen.aggregate_results(records)
        self.assertEqual(result['matches_played'], 10000)
        self.assertEqual(result['wins'], {'A': 6000, 'B': 4000})
        self.assertEqual(result['losses'], {'A': 4000, 'B': 6000})
        self.assertEqual(result['win_rate'], {'A': 0.6, 'B': 0.4})
        self.assertEqual(result['starts'], {'A': 5000, 'B': 5000})
        self.assertEqual(result['wins_by_starting_deck'], {
            'A': {'A': 3000, 'B': 2000}, 'B': {'A': 3000, 'B': 2000}})
        self.assertEqual(result['first_player_wins'], 5000)
        self.assertEqual(result['turn_distribution'], {'5': 3334, '6': 3333, '7': 3333})
        self.assertEqual(result['mean_turns'], 5.9999)
        self.assertEqual(result['card_play_frequency'], {'BT24-031': 10000})
        self.assertEqual(result['interaction_frequency'], {'BT24-031|FIXTURE_PATH': 5000})
        self.assertEqual(result['combo_frequency'], {'fixture-combo': 2500})
        self.assertEqual(result['lane_frequency'], {'fixture-green': 2500})

    def test_incomplete_or_halted_run_cannot_emit_final_results(self):
        incomplete = self.create_synthetic_freeze()
        with self.assertRaisesRegex(ValueError, '10000'):
            frozen.summarize_completed_run(incomplete)
        halted = self.create_synthetic_freeze()
        frozen.run_frozen(halted, match_runner=self.halted_runner)
        with self.assertRaisesRegex(ValueError, '10000|halt'):
            frozen.summarize_completed_run(halted)

    def test_final_summary_and_cli_apis_exist(self):
        self.assertTrue(callable(frozen.aggregate_results))
        self.assertTrue(callable(frozen.summarize_completed_run))
        self.assertTrue(callable(frozen.main))


class FrozenEvaluationMissingModuleTest(unittest.TestCase):
    def test_frozen_evaluation_module_is_present(self):
        self.assertIsNotNone(frozen, 'frozen_evaluation module is missing')


if __name__ == '__main__':
    unittest.main()
