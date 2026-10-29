import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import match_evidence as evidence


class MatchEvidenceTests(unittest.TestCase):
    def test_snapshot_covers_zones_pending_queues_once_state_and_rng(self):
        self.assertTrue(hasattr(evidence, 'snapshot_match'), 'structured snapshots are required')
        m = evidence.EvidenceMatch(12)
        p = m.ps['A']
        p.once_used.add('example-once')
        m._security_pending.append(p)
        state = evidence.snapshot_match(m)
        self.assertEqual(state['runtime']['_security_pending'], [{'player_ref': 'A'}])
        self.assertEqual(state['players']['A']['once_used'], ['example-once'])
        self.assertEqual(len(state['players']['A']['zones']['security']), 5)
        self.assertEqual(state['rng_state'][0], 3)
        p.z.hand.clear()
        m._security_pending.clear()
        self.assertEqual(len(state['players']['A']['zones']['hand']), 5)
        self.assertEqual(state['runtime']['_security_pending'], [{'player_ref': 'A'}])

    def test_replayed_cohort_streams_hash_bound_records_without_certification(self):
        self.assertTrue(hasattr(evidence, 'run_evidence_cohort'), 'evidence runner is required')
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            report = evidence.run_evidence_cohort(out, count=2)
            self.assertEqual(report['attempted'], 2)
            self.assertEqual(report['starts'], {'A': 1, 'B': 1})
            self.assertEqual(report['judge_certified'], 0)
            self.assertEqual(report['valid_fact_finding_matches'], 0)
            self.assertEqual(report['replays_verified'], 2)
            records = sorted(out.glob('MATCH_*.json.gz'))
            self.assertEqual(len(records), 2)
            for path in records:
                row = json.loads(gzip.decompress(path.read_bytes()))
                self.assertEqual(row['rule_check_status'], 'UNVERIFIED')
                self.assertIn('initial_state', row)
                self.assertIn('final_state', row)
                self.assertIn('provenance_sha256', row)
                self.assertTrue(row['transcript']['events'])
            with self.assertRaises(FileExistsError):
                evidence.run_evidence_cohort(out, count=2)

    def test_copied_deck_text_must_equal_locked_source(self):
        self.assertTrue(hasattr(evidence, 'validate_locked_inputs'), 'deck lock validation is required')
        root = Path(__file__).resolve().parent.parent
        report = evidence.validate_locked_inputs(root)
        self.assertEqual(report['A']['main'], 50)
        self.assertEqual(report['A']['eggs'], 4)
        self.assertEqual(report['B']['main'], 50)
        self.assertEqual(report['B']['eggs'], 4)
        self.assertEqual(report['format_restrictions'], 'UNVERIFIED')

    def test_decision_context_records_board_but_not_facedown_zones(self):
        m = evidence.EvidenceMatch(0)
        m._log_choice('EXAMPLE', 'A', [{'action': 'PASS'}], 'PASS')
        event = m.events[-1]
        self.assertIn('position', event)
        position = event['position']
        self.assertEqual(position['players']['A']['security_count'], 5)
        self.assertEqual(position['players']['B']['hand_count'], 5)
        self.assertNotIn('deck', position['players']['B'])
        self.assertNotIn('security', position['players']['A'])
        self.assertNotIn('hand', position['players']['B'])
        self.assertEqual(position['own_hand'], [c.key() for c in m.ps['A'].z.hand])


if __name__ == '__main__':
    unittest.main()
