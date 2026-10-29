"""Software completion, stale evidence, and proposals cannot authorize final play."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from seeded_opening_probe import seed_for

import match_evidence as evidence

try:
    import evaluation_gate as gate
except ImportError:
    gate = None


class EvaluationGateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(gate, 'fail-closed evaluation gate is required')
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'cohort'
        evidence.run_evidence_cohort(self.out, count=2)

    def codes(self, result):
        return {issue['code'] for issue in result['blockers']}

    def test_software_completed_or_replayed_records_are_not_certificates(self):
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(result['eligible'])
        self.assertIn('FACT_FINDING_COHORT_NOT_60', self.codes(result))
        self.assertIn('INDEPENDENT_JUDGE_REVIEW_MISSING', self.codes(result))
        self.assertIn('ROADMAPS_NOT_APPROVED', self.codes(result))

    def test_modified_transcript_is_rejected_even_if_software_flag_is_true(self):
        path = self.out / 'MATCH_001.json.gz'
        row = json.loads(gzip.decompress(path.read_bytes()))
        row['status'] = 'SOFTWARE_COMPLETED'
        row['transcript']['events'].append({'type': 'FABRICATED'})
        path.write_bytes(gzip.compress(evidence.canonical_bytes(row), mtime=0))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('TRANSCRIPT_HASH_MISMATCH', self.codes(result))
        self.assertFalse(result['eligible'])

    def test_stale_source_hash_is_rejected(self):
        path = self.out / 'provenance.json'
        data = json.loads(path.read_bytes())
        data['files']['SOURCE/match_evidence.py'] = '0' * 64
        path.write_bytes(evidence.canonical_bytes(data))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('PROVENANCE_HASH_MISMATCH', self.codes(result))
        self.assertIn('SOURCE_OR_DECK_CHANGED', self.codes(result))

    def test_duplicate_seed_or_index_is_rejected(self):
        path = self.out / 'cohort.json'
        data = json.loads(path.read_bytes())
        data['records'][1] = dict(data['records'][0])
        path.write_bytes(evidence.canonical_bytes(data))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('DUPLICATE_MATCH_ID_OR_SEED', self.codes(result))

    def test_empty_review_cannot_promote_unverified_games(self):
        path = Path(self.tmp.name) / 'review.json'
        path.write_text('{}')
        result = gate.assess_eligibility(evidence.ROOT, self.out, path)
        self.assertFalse(result['eligible'])
        self.assertIn('JUDGE_REVIEW_INVALID', self.codes(result))

    def test_malformed_review_returns_structured_blocker(self):
        path = Path(self.tmp.name) / 'review.json'
        for value in (None, [], 'review'):
            with self.subTest(value=value):
                path.write_text(json.dumps(value))
                result = gate.assess_eligibility(evidence.ROOT, self.out, path)
                self.assertIn('JUDGE_REVIEW_INVALID', self.codes(result))

    def rewrite_first(self, edit):
        summary_path = self.out / 'cohort.json'
        summary = json.loads(summary_path.read_bytes())
        path = self.out / summary['records'][0]['file']
        row = json.loads(gzip.decompress(path.read_bytes()))
        edit(row)
        raw = evidence.canonical_bytes(row)
        packed = gzip.compress(raw, mtime=0)
        path.write_bytes(packed)
        entry = summary['records'][0]
        for key in ('index', 'seed', 'first', 'status'):
            entry[key] = row[key]
        entry['record_sha256'] = hashlib.sha256(raw).hexdigest()
        entry['file_sha256'] = hashlib.sha256(packed).hexdigest()
        summary_path.write_bytes(evidence.canonical_bytes(summary))

    def test_full_snapshots_are_required_even_when_hashes_match(self):
        self.rewrite_first(lambda row: row.pop('initial_state'))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('MATCH_SCHEMA_INVALID', self.codes(result))

    def test_transcript_identity_must_match_record_identity(self):
        self.rewrite_first(lambda row: row['transcript'].update(seed=123))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('MATCH_SCHEMA_INVALID', self.codes(result))

    def test_seed_mapping_is_checked(self):
        self.rewrite_first(lambda row: row.update(seed=seed_for(60)))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('SEED_MAPPING_INVALID', self.codes(result))

    def test_prepared_schedule_excludes_actual_cohort_seeds(self):
        self.rewrite_first(lambda row: row.update(seed=seed_for(60)))
        destination = Path(self.tmp.name) / 'actual-seed-preparation'
        gate.prepare_evaluation(evidence.ROOT, self.out, destination)
        schedule = json.loads(gzip.decompress((destination / 'SEEDS.json.gz').read_bytes()))
        self.assertNotIn(seed_for(60), {row['seed'] for row in schedule})
        self.assertEqual(sum(row['first'] == 'A' for row in schedule), 5000)
        self.assertEqual(sum(row['first'] == 'B' for row in schedule), 5000)

    def test_transcript_path_cannot_escape_the_cohort(self):
        path = self.out / 'cohort.json'
        data = json.loads(path.read_bytes())
        data['records'][0]['file'] = '../outside.json.gz'
        path.write_bytes(evidence.canonical_bytes(data))
        result = gate.assess_eligibility(evidence.ROOT, self.out)
        self.assertIn('INVALID_TRANSCRIPT_PATH', self.codes(result))

    def test_preparation_is_not_a_freeze_or_played_evaluation(self):
        destination = Path(self.tmp.name) / 'preparation'
        result = gate.prepare_evaluation(evidence.ROOT, self.out, destination)
        self.assertEqual(result['status'], 'BLOCKED_NOT_FROZEN')
        self.assertEqual(result['evaluation_matches_played'], 0)
        self.assertFalse(result['frozen'])
        schedule = json.loads(gzip.decompress((destination / 'SEEDS.json.gz').read_bytes()))
        self.assertEqual(len(schedule), 10000)
        self.assertEqual(sum(row['first'] == 'A' for row in schedule), 5000)
        self.assertEqual(sum(row['first'] == 'B' for row in schedule), 5000)
        self.assertEqual(len({row['seed'] for row in schedule}), 10000)
        self.assertTrue(all(row['index'] >= 60 for row in schedule))
        self.assertNotIn('freeze_sha256', result)
        self.assertFalse((destination / 'RESULTS.json').exists())

    def test_candidate_roadmaps_do_not_promote_heuristics_to_lanes(self):
        destination = Path(self.tmp.name) / 'candidate-root'
        maps = gate.write_candidate_roadmaps(destination, self.out)
        for seat in ('A', 'B'):
            roadmap = maps[seat]
            self.assertEqual(roadmap['entries'], [])
            self.assertEqual(roadmap['illegal'], [])
            self.assertTrue(roadmap['unknown'])
            self.assertEqual(roadmap['approved_counts'], {'GREEN': 0, 'YELLOW': 0, 'RED': 0})
            for situation in roadmap['unknown']:
                self.assertEqual(situation['legality'], 'UNVERIFIED')
                self.assertTrue(situation['condition'])
                for ref in situation['evidence']:
                    self.assertIn(ref['index'], (0, 1))
                    self.assertEqual(len(ref['record_sha256']), 64)


class OfficialEvidenceTests(unittest.TestCase):
    """Review-schema fixtures are temporary test data, never match certification."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'repo'
        for folder in ('SOURCE', 'DECKS'):
            shutil.copytree(evidence.ROOT / folder, cls.root / folder,
                            ignore=shutil.ignore_patterns('__pycache__'))
        cls.out = Path(cls.tmp.name) / 'cohort'
        cls.summary = evidence.run_evidence_cohort(cls.out, count=60)
        (cls.root / 'RULES').mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def review(self, content=b'Test-only source bytes', citation='Rule 1', match_citations=None):
        source_path = self.root / 'RULES' / 'fixture.txt'
        source_path.write_bytes(content)
        source = {'id': 'rules', 'url': 'https://world.digimoncard.com/rule/',
                  'file': 'RULES/fixture.txt', 'sha256': gate.file_hash(source_path),
                  'citation': citation}
        checks = ['physical_cards', 'memory', 'timing', 'counter_windows',
                  'once_per_turn', 'optional_choices', 'terminal_state', 'card_rules']
        matches = [{'index': row['index'], 'record_sha256': row['record_sha256'],
                    'verdict': 'JUDGE_CERTIFIED', 'verified_checks': checks,
                    'citations': match_citations if match_citations is not None else
                    [{'source_id': 'rules', 'locator': 'Rule 1'}]}
                   for row in self.summary['records']]
        return {'kind': 'INDEPENDENT_RULES_REVIEW', 'reviewer': 'TEST FIXTURE ONLY',
                'cohort_sha256': gate.file_hash(self.out / 'cohort.json'),
                'provenance_sha256': self.summary['provenance_sha256'],
                'deck_restrictions': 'VERIFIED', 'official_sources': [source], 'matches': matches}

    def assess(self, review):
        path = Path(self.tmp.name) / 'review.json'
        path.write_bytes(evidence.canonical_bytes(review))
        return gate.assess_eligibility(self.root, self.out, path)

    def test_nonempty_review_binding_is_the_control(self):
        result = self.assess(self.review())
        # Other required gates remain blocked; this checks only review parsing.
        self.assertNotIn('JUDGE_REVIEW_INVALID', {r['code'] for r in result['blockers']})
        self.assertFalse(result['eligible'])

    def test_empty_official_source_cannot_satisfy_review(self):
        result = self.assess(self.review(content=b''))
        self.assertIn('JUDGE_REVIEW_INVALID', {r['code'] for r in result['blockers']})

    def test_whitespace_citation_cannot_satisfy_review(self):
        for review in (self.review(citation=' '), self.review(match_citations=[' '])):
            result = self.assess(review)
            self.assertIn('JUDGE_REVIEW_INVALID', {r['code'] for r in result['blockers']})

    def test_match_citation_must_reference_a_bound_source(self):
        result = self.assess(self.review(match_citations=[{'source_id': 'absent', 'locator': 'Rule 1'}]))
        self.assertIn('JUDGE_REVIEW_INVALID', {r['code'] for r in result['blockers']})


if __name__ == '__main__':
    unittest.main()
