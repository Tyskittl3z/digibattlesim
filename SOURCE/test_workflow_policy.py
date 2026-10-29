"""Policy fixtures are temporary attestations, never gameplay certification."""
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from match_evidence import canonical_bytes, digest
from seeded_opening_probe import seed_for
try:
    import workflow_policy as policy
except ImportError:
    policy = None


class WorkflowPolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(policy, 'workflow policy enforcement is required')
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'RULES').mkdir()
        self.citations = [{'source_id': 'official', 'locator': 'Fixture rule 1'}]
        self.records = []
        for index in (0, 1):
            sha = str(index + 1) * 64
            self.records.append(({'record_sha256': sha}, {
                'index': index, 'seed': seed_for(index),
                'transcript': {'events': [{'type': 'BOT_DECISION',
                                           'decision_type': 'AEGIOMON_SECURITY_TAMER',
                                           'seat': 'A', 'source': 'BT24-034',
                                           'chosen': 'ACTIVATE' if index == 0 else 'DECLINE'},
                                          {'type': 'JUDGE_PATH', 'card': 'BT24-034',
                                           'owner': 'A', 'kind': 'MANDATORY_EFFECT'}]}}))
        self.refs = [self.ref(index, offset) for index in (0, 1) for offset in (0, 1)]

    def ref(self, index, offset=0):
        return {'kind': 'MATCH', 'index': index, 'seed': seed_for(index),
                'record_sha256': str(index + 1) * 64, 'event_index': offset}

    def pin(self):
        documents = []
        for kind in ('RULES', 'ERRATA', 'RESTRICTIONS', 'CARD_TEXT', 'CARD_QA'):
            path = self.root / 'RULES' / (kind + '.txt')
            path.write_text('Temporary test fixture: ' + kind)
            documents.append({'id': kind, 'kind': kind, 'edition': 'Fixture edition 1',
                              'effective_date': '2026-10-01', 'file': 'RULES/' + path.name,
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                              'url': 'https://world.digimoncard.com/rule/', 'citation': kind})
        value = {'schema': 'loaded-pair-rules-lock-v1', 'status': 'PINNED',
                 'as_of_date': '2026-10-29', 'format': {'name': 'Fixture', 'region': 'Fixture'},
                 'language': 'Fixture', 'documents': documents,
                 'review': {'reviewer': 'TEST ONLY', 'verdict': 'VERIFIED'}}
        self.write('RULES/RULES_LOCK.json', value)
        return value

    def write(self, filename, value):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(value))

    def coverage(self):
        value = {'schema': 'loaded-pair-interaction-coverage-v1', 'status': 'VERIFIED',
                 'provenance_sha256': 'p' * 64, 'entries': [{
                     'interaction_id': 'fixture-choice', 'card': 'BT24-034',
                     'encounters': [self.ref(0), self.ref(1)],
                     'inventory_review': {'reviewer': 'TEST ONLY', 'verdict': 'VERIFIED',
                                          'complete': True, 'citations': self.citations},
                     'branches': [{'id': 'ACTIVATE', 'legality': 'LEGAL',
                                   'citations': self.citations, 'evidence': [self.ref(0)]},
                                  {'id': 'DECLINE', 'legality': 'LEGAL',
                                   'citations': self.citations, 'evidence': [self.ref(1)]}]}]}
        value['entries'].append({
            'interaction_id': 'fixture-path', 'card': 'BT24-034',
            'encounters': [self.ref(0, 1), self.ref(1, 1)],
            'inventory_review': {'reviewer': 'TEST ONLY', 'verdict': 'VERIFIED',
                                 'complete': True, 'citations': self.citations},
            'branches': [{'id': 'MANDATORY_EFFECT', 'legality': 'LEGAL',
                          'citations': self.citations, 'evidence': [self.ref(0, 1)]}]})
        self.write('RULES/INTERACTION_COVERAGE.json', value)
        return value

    def criteria(self):
        return json.loads((Path(__file__).resolve().parent.parent /
                           'ROADMAPS/APPROVAL_CRITERIA.json').read_bytes())

    def lane(self):
        return {'lane': 'GREEN', 'legality': 'LEGAL', 'condition': {'security': 1},
                'criteria_sha256': 'c' * 64, 'objective': 'Fixture objective',
                'metric': 'fixture_score', 'direction': 'MAXIMIZE',
                'uncertainty': 'Two seeds are a weak evidence floor, not confidence proof.',
                'approval_basis': 'TEST FIXTURE comparison only', 'evidence': [self.ref(0), self.ref(1)],
                'compared_alternatives': [
                    {'id': 'ACTIVATE', 'metrics': {'fixture_score': 1}, 'evidence': [self.ref(0)]},
                    {'id': 'DECLINE', 'metrics': {'fixture_score': 0}, 'evidence': [self.ref(1)]}]}

    def test_complete_pin_control_and_changed_document_rejection(self):
        self.pin()
        policy.validate_rules_pin(self.root)
        (self.root / 'RULES/RULES.txt').write_text('Changed fixture')
        with self.assertRaisesRegex(ValueError, 'hash'):
            policy.validate_rules_pin(self.root)

    def test_unselected_format_and_future_effective_date_block_pin(self):
        for mutate in (lambda v: v['format'].update(name=None),
                       lambda v: v['documents'][0].update(effective_date='2026-10-30')):
            value = self.pin()
            mutate(value)
            self.write('RULES/RULES_LOCK.json', value)
            with self.assertRaises(ValueError):
                policy.validate_rules_pin(self.root)

    def test_branch_inventory_requires_all_encounters_and_evidenced_legal_choices(self):
        self.coverage()
        policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})
        for mutate in (lambda v: v['entries'][0]['encounters'].pop(),
                       lambda v: v['entries'][0]['branches'][1].update(evidence=[]),
                       lambda v: v['entries'][0]['inventory_review'].update(complete=False)):
            value = self.coverage()
            mutate(value)
            self.write('RULES/INTERACTION_COVERAGE.json', value)
            with self.assertRaises(ValueError):
                policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})

    def test_unknown_branch_cannot_be_promoted_by_coverage_label(self):
        value = self.coverage()
        value['entries'][0]['branches'][0]['legality'] = 'UNKNOWN'
        self.write('RULES/INTERACTION_COVERAGE.json', value)
        with self.assertRaises(ValueError):
            policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})

    def test_decline_trace_does_not_cover_activate_branch(self):
        value = self.coverage()
        value['entries'][0]['branches'][0]['evidence'] = [self.ref(1)]
        self.write('RULES/INTERACTION_COVERAGE.json', value)
        with self.assertRaisesRegex(ValueError, 'branch'):
            policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})

    def test_same_choice_from_another_card_cannot_cover_this_interaction(self):
        self.coverage()
        self.records[0][1]['transcript']['events'][0]['source'] = 'BT25-028'
        with self.assertRaises(ValueError):
            policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})

    def test_branch_evidence_must_belong_to_its_own_declared_encounters(self):
        value = self.coverage()
        extra = copy.deepcopy(value['entries'][0])
        extra['interaction_id'] = 'different-situation'
        extra['encounters'] = [self.ref(0)]
        extra['branches'] = extra['branches'][:1]
        value['entries'].append(extra)
        value['entries'][0]['encounters'] = [self.ref(1)]
        self.write('RULES/INTERACTION_COVERAGE.json', value)
        with self.assertRaises(ValueError):
            policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})

    def test_observed_branch_cannot_be_omitted_or_classified_illegal(self):
        for illegal in (False, True):
            value = self.coverage()
            if illegal:
                value['entries'][0]['branches'][0]['legality'] = 'ILLEGAL'
            else:
                value['entries'][0]['branches'].pop()
            self.write('RULES/INTERACTION_COVERAGE.json', value)
            with self.assertRaises(ValueError):
                policy.validate_coverage(self.root, 'p' * 64, self.records, {'official'})

    def test_strategy_review_binds_criteria_pilots_and_roadmaps_separately(self):
        gate = {'cohort_sha256': 'a' * 64, 'provenance_sha256': 'b' * 64}
        pilots = {'A': {'sha256': 'd' * 64}, 'B': {'sha256': 'e' * 64}}
        maps = {'A': '1' * 64, 'B': '2' * 64}
        valid = {'kind': 'STRATEGY_EVALUATION_REVIEW', 'reviewer': 'TEST ONLY', **gate,
                 'criteria_sha256': 'c' * 64, 'pilot_sha256': {'A': 'd' * 64, 'B': 'e' * 64},
                 'roadmap_sha256': maps, 'roadmap_verdicts': {'A': 'APPROVED', 'B': 'APPROVED'}}
        policy.validate_strategy_review(valid, gate, pilots, 'c' * 64, maps)
        for field in ('criteria_sha256', 'pilot_sha256', 'roadmap_sha256', 'cohort_sha256'):
            altered = copy.deepcopy(valid)
            altered[field] = None
            with self.assertRaises(ValueError):
                policy.validate_strategy_review(altered, gate, pilots, 'c' * 64, maps)

    def test_evidence_folder_symlink_cannot_escape_the_repository(self):
        outside = self.root.parent / (self.root.name + '-outside')
        outside.mkdir()
        self.addCleanup(outside.rmdir)
        (self.root / 'RULES/scenarios').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            policy.source_file(self.root, 'RULES/scenarios/fixture.json', 'RULES/scenarios')

    def test_lane_requires_evaluated_alternatives_uncertainty_and_independent_seeds(self):
        policy.validate_strategy_lane(self.lane(), self.criteria(), 'c' * 64, self.records)
        for mutate in (lambda v: v.pop('uncertainty'),
                       lambda v: v.update(compared_alternatives=[]),
                       lambda v: v['compared_alternatives'][1].update(metrics={}),
                       lambda v: v.update(evidence=[self.ref(0)]),
                       lambda v: v.update(criteria_sha256='old')):
            lane = self.lane()
            mutate(lane)
            with self.assertRaises(ValueError):
                policy.validate_strategy_lane(lane, self.criteria(), 'c' * 64, self.records)

    def test_rules_review_cannot_authorize_strategy(self):
        review = {'kind': 'INDEPENDENT_RULES_REVIEW', 'reviewer': 'TEST ONLY'}
        with self.assertRaises(ValueError):
            policy.validate_strategy_review(review, {}, {}, 'c' * 64, {})

    def test_lane_cannot_compare_choice_labels_from_unrelated_interactions(self):
        self.records[1][1]['transcript']['events'][0]['source'] = 'BT25-028'
        with self.assertRaises(ValueError):
            policy.validate_strategy_lane(self.lane(), self.criteria(), 'c' * 64, self.records)

    def test_resume_preserves_original_seed_and_blocks_unresolved_rules(self):
        frozen = {key: str(i + 1) * 64 for i, key in enumerate(policy.FROZEN_COMPONENTS)}
        schedule = [{'index': i, 'seed': seed_for(i), 'first': 'A' if i % 2 == 0 else 'B'}
                    for i in range(60, 10060)]
        frozen['schedule'] = digest(schedule)
        checkpoint = {'frozen_inputs': frozen, 'next_match': {
            'index': 60, 'seed': seed_for(60), 'first': 'A'}, 'schedule_position': 0,
            'halt_kind': 'INFRASTRUCTURE'}
        result = policy.assess_resume(checkpoint, frozen, frozen_schedule=schedule)
        self.assertEqual(result['status'], 'REPLAY_ORIGINAL_MATCH')
        self.assertEqual(result['match']['seed'], seed_for(60))
        with self.assertRaises(ValueError):
            policy.assess_resume(checkpoint, frozen, requested_seed=seed_for(61), frozen_schedule=schedule)
        checkpoint['halt_kind'] = 'RULES'
        self.assertEqual(policy.assess_resume(checkpoint, frozen, frozen_schedule=schedule)['status'], 'BLOCKED_HALT')
        changed = dict(frozen, engine='f' * 64)
        result = policy.assess_resume(checkpoint, changed, frozen_schedule=schedule)
        self.assertEqual(result['status'], 'RESTART_FULL_EVALUATION')
        self.assertTrue(result['invalidate_all_prior_results'])
        self.assertEqual(result['restart_schedule_from_position'], 0)

    def test_resume_requires_sealed_schedule_not_just_seed_mapping(self):
        frozen = {key: str(i + 1) * 64 for i, key in enumerate(policy.FROZEN_COMPONENTS)}
        checkpoint = {'frozen_inputs': frozen, 'next_match': {
            'index': 60, 'seed': seed_for(60), 'first': 'A'}, 'halt_kind': 'INFRASTRUCTURE'}
        with self.assertRaises(ValueError):
            policy.assess_resume(checkpoint, frozen)


if __name__ == '__main__':
    unittest.main()
