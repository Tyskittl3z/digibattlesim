"""Cross-build private fixtures, with zero production or match credit."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'


def run_python(root, body, payload=None):
    code = "import sys,json; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,str(root/'SOURCE')); data=json.load(sys.stdin)\n" + body
    result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(root)],
        input=json.dumps(payload), capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def sources(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / 'SOURCE').glob('*.py')) if not p.name.startswith('test_')}


def approve(old, new):
    before, after = sources(old), sources(new)
    return {k: {'before': before.get(k), 'after': after.get(k)}
            for k in before.keys() | after.keys() if before.get(k) != after.get(k)}


class RepairMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='private-repair-builds-')
        cls.base = Path(cls.temp.name)
        cls.old = cls.base / 'old'
        cls.old.mkdir()
        with tarfile.open(ROOT / 'ARTIFACTS/learning-integration-2026-11-10/source-checkpoint.tar.gz') as archive:
            for member in archive.getmembers():
                if member.isfile() and member.name.startswith('SOURCE/'):
                    target = cls.old / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
        for asset in (ROOT / 'SOURCE').iterdir():
            if asset.is_file() and asset.suffix != '.py':
                shutil.copy2(asset, cls.old / 'SOURCE' / asset.name)
        shutil.copytree(ROOT / 'RULES', cls.old / 'RULES')
        path = cls.old / CONTEXT
        path.parent.mkdir(parents=True)
        shutil.copy2(ROOT / CONTEXT, path)
        engine = cls.old / 'SOURCE/match_preparation.py'
        engine.write_text(engine.read_text().replace('def _redraw(runtime,seat,choice):',
            "def _redraw(runtime,seat,choice):\n    raise RuntimeHalt('PRIVATE_OLD_ONLY_UNIMPLEMENTED_REDRAW')"))
        cls.stopped = run_python(cls.old, """
from fresh_learning_campaign import run_game
from interaction_learning import LearningState
record=run_game(0,root,context_file='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',campaign_id='private-repair-migration',learning_state=LearningState(),max_commands=3)
print(json.dumps(record))
""")
        assert cls.stopped['status'] == 'HALT'
        assert len(cls.stopped['commands']) == 2

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('fresh_repair_migration'),
                             'explicit migration API must exist')
        self.new = self.base / self._testMethodName
        shutil.copytree(self.old, self.new)
        for path in (ROOT / 'SOURCE').glob('*.py'):
            if not path.name.startswith('test_'):
                shutil.copy2(path, self.new / 'SOURCE' / path.name)

    def migrate(self, record=None, approved=None):
        return run_python(self.new, """
import fresh_learning_campaign as runner
from fresh_repair_migration import migrate_repaired_game
from context_runtime import RuntimeHalt
class NoPlayer:
    def __init__(self,*a,**kw): raise AssertionError('player constructed during migration')
runner.LearningPlayerBot=NoPlayer
try:
    result=migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='private verified engine repair')
    print(json.dumps({'record':result}))
except RuntimeHalt as error:
    print(json.dumps({'error':str(error)}))
""", {'record': self.stopped if record is None else record, 'old': str(self.old),
        'approved': approve(self.old, self.new) if approved is None else approved})

    def test_real_old_gap_migrates_and_retries_exact_selection_once_without_choice(self):
        original = copy.deepcopy(self.stopped)
        result = self.migrate()
        self.assertNotIn('error', result)
        migrated = result['record']
        self.assertEqual(self.stopped, original)
        line = migrated['repair_lineage']
        self.assertEqual(line['parent_record'], original)
        self.assertEqual(line['successful_prefix_count'], 1)
        self.assertNotEqual(migrated['sources'], original['sources'])
        self.assertNotEqual(migrated['final']['execution_id'], original['final']['execution_id'])
        for key in ('state', 'rng_state', 'seed', 'first'):
            self.assertEqual(migrated['final'][key], original['final'][key])
        for key in ('args', 'decisions', 'policy_rng_after_choice', 'selected_pending'):
            self.assertEqual(migrated['commands'][-1].get(key), original['commands'][-1].get(key))
        self.assertEqual(migrated['commands'][-1]['rating']['status'], 'UNRATED')
        resumed = run_python(self.new, """
import fresh_learning_campaign as runner
from interaction_learning import LearningState
runner.LearningPlayerBot.choose=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('saved choice rerolled'))
assert runner.replay_game(data,root)['exact_match']
result=runner.run_game(0,root,context_file=data['context_file'],campaign_id=data['campaign_id'],learning_state=LearningState.from_dict(data['learning_state_before']),previous_record=data,max_commands=1)
assert runner.replay_game(result,root)['exact_match']
print(json.dumps(result))
""", migrated)
        self.assertEqual(len(resumed['commands']), 2)
        self.assertEqual(resumed['commands'][-1]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(resumed['commands'][-1]['args'], original['commands'][-1]['args'])
        self.assertEqual(resumed['policy_rng_final'], original['policy_rng_final'])
        self.assertEqual(resumed['repair_lineage'], line)
        self.assertEqual(resumed['learning_state_after'], original['learning_state_before'])

    def test_unapproved_source_difference_is_rejected(self):
        self.assertIn('APPROVED', self.migrate(approved={}).get('error', ''))

    def test_approved_protected_policy_changes_are_rejected(self):
        for name in ('interaction_learning.py', 'named_player_bots.py', 'interaction_scoring.py',
                     'judge_ledger.py', 'match_context.py', 'imported_attempts.py'):
            path = self.new / 'SOURCE' / name
            original = path.read_bytes()
            path.write_bytes(original + b'\n# forbidden fixture change\n')
            with self.subTest(name=name):
                self.assertIn('PROTECTED', self.migrate().get('error', ''))
            path.write_bytes(original)

    def test_rules_context_and_criterion_byte_changes_are_rejected(self):
        for relative in ('SOURCE/EXACT_CARD_MANIFEST.json', 'RULES/RULES_LOCK.json', 'RULES/learning-2026-11-10/INTERACTION_CRITERIA.json', CONTEXT):
            path = self.new / relative
            original = path.read_bytes()
            path.write_bytes(original + b'\n')
            with self.subTest(path=relative):
                self.assertIn('DEPENDENC', self.migrate().get('error', ''))
            path.write_bytes(original)

    def test_rehashed_original_state_result_rng_and_failure_mutations_are_rejected(self):
        from match_context import digest
        for mutation in ('result', 'state', 'rng', 'model', 'status', 'failure'):
            record = copy.deepcopy(self.stopped)
            if mutation == 'result': record['commands'][0]['result']['private_bad'] = 1
            elif mutation == 'state': record['commands'][0]['after']['state']['memory'] += 1
            elif mutation == 'rng': record['final']['rng_state'][1][0] ^= 1
            elif mutation == 'model': record['learning_state_before']['unexpected'] = 1
            elif mutation == 'status': record['status'] = 'EXPERIMENTAL_SOFTWARE_TERMINAL'
            else: record['commands'][-1]['after']['state']['memory'] += 1
            record['record_sha256'] = digest({k:v for k,v in record.items() if k != 'record_sha256'})
            with self.subTest(mutation=mutation):
                self.assertIn('error', self.migrate(record))

    def test_rehashed_lineage_tampering_is_rejected_by_ordinary_replay(self):
        migrated = self.migrate()['record']
        result = run_python(self.new, """
from match_context import digest
from fresh_learning_campaign import replay_game
from context_runtime import RuntimeHalt
errors=[]
for field in ('parent','prefix','receipt','dependencies'):
    import copy
    record=copy.deepcopy(data)
    line=record['repair_lineage']
    if field=='parent': line['parent_record']['seed']+=1
    elif field=='prefix': record['commands'][0]['args']['tamper']=True
    elif field=='receipt': line['original_replay_receipt']['exact_match']=False
    else: line['dependency_hashes']['RULES/RULES_LOCK.json']='0'*64
    record['record_sha256']=digest({k:v for k,v in record.items() if k!='record_sha256'})
    try: replay_game(record,root)
    except RuntimeHalt: errors.append(field)
print(json.dumps(errors))
""", migrated)
        self.assertEqual(result, ['parent', 'prefix', 'receipt', 'dependencies'])

    def test_bootstrap_exemption_rejects_any_other_runner_bytes_even_if_approved(self):
        path = self.new / 'SOURCE/fresh_learning_campaign.py'
        path.write_bytes(path.read_bytes() + b'\n# not the approved lineage-aware runner\n')
        self.assertIn('BOOTSTRAP', self.migrate().get('error', ''))

    def test_real_repair_that_changes_an_earlier_result_is_rejected(self):
        path = self.new / 'SOURCE/match_preparation.py'
        path.write_text(path.read_text().replace("'initial_hands':{'A':5,'B':5}", "'initial_hands':{'A':4,'B':5}"))
        self.assertIn('PREFIX_RESULT', self.migrate().get('error', ''))

    def test_second_engine_only_repair_keeps_first_parent_and_strict_framework(self):
        first = self.migrate()['record']
        second_root = self.base / (self._testMethodName + '-second')
        shutil.copytree(self.new, second_root)
        path = second_root / 'SOURCE/context_runtime.py'
        path.write_bytes(path.read_bytes() + b'\n# private second engine repair\n')
        second = run_python(second_root, """
from fresh_repair_migration import migrate_repaired_game
from fresh_learning_campaign import replay_game
result=migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='second private engine repair')
assert replay_game(result,root)['exact_match']
print(json.dumps(result))
""", {'record': first, 'old': str(self.new), 'approved': approve(self.new, second_root)})
        self.assertEqual(second['repair_lineage']['parent_record'], first)
        self.assertEqual(second['repair_lineage']['parent_record']['repair_lineage']['parent_record'], self.stopped)
        path = second_root / 'SOURCE/fresh_repair_migration.py'
        path.write_bytes(path.read_bytes() + b'\n# forbidden framework change\n')
        blocked = run_python(second_root, """
from fresh_repair_migration import migrate_repaired_game
from context_runtime import RuntimeHalt
try:
    migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='forbidden')
    print(json.dumps('accepted'))
except RuntimeHalt as error: print(json.dumps(str(error)))
""", {'record': first, 'old': str(self.new), 'approved': approve(self.new, second_root)})
        self.assertIn('PROTECTED', blocked)

    def mechanic_roots(self, fail=False):
        # Source-bound synthetic initial state with one real printed effect.
        old = self.base / (self._testMethodName + '-mechanic-old')
        new = self.base / (self._testMethodName + '-mechanic-new')
        shutil.copytree(self.new, old)
        path = old / 'SOURCE/context_runtime.py'
        needle = '        self._pack_manifest = canonical(self.registry.manifest())'
        path.write_text(path.read_text().replace(needle, """        card = next(c for c in self.state.zones['A']['deck'] if c.card_number == 'BT11-112')
        self.state.zones['A']['deck'].remove(card)
        self.state.battle['A'][card.key] = Stack([card])
        self.state.phase = 'MAIN'
        from effect_scheduler import queue_effects
        queue_effects(self, [{'seat':'A','source':card.key,'field':'main_text',
            'effect_id':'BT11-112.on_play_grant','trigger':{'kind':'On Play'}}])
""" + needle))
        shutil.copytree(old, new)
        path = old / 'SOURCE/on_play_effects.py'
        path.write_bytes(path.read_bytes() + b'\n# old handler module stamp\n')
        if fail:
            path = old / 'SOURCE/context_runtime.py'
            path.write_text(path.read_text().replace('            result = binding.handler(trial, seat, source_key, copy.deepcopy(choice))',
                "            raise RuntimeHalt('PRIVATE_OLD_ONLY_UNIMPLEMENTED_PENDING')\n            result = binding.handler(trial, seat, source_key, copy.deepcopy(choice))"))
        record = run_python(old, """
from fresh_learning_campaign import run_game
from interaction_learning import LearningState
result=run_game(0,root,context_file='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json',campaign_id='private-mechanic-migration',learning_state=LearningState(),max_commands=1)
print(json.dumps(result))
""")
        return old, new, record

    def test_successful_mechanic_rebinds_only_handler_stamp_and_receipt_chain(self):
        old, new, record = self.mechanic_roots()
        self.assertEqual(record['status'], 'PAUSED')
        self.assertEqual(record['commands'][0]['command'], 'RESOLVE_PENDING')
        self.assertIsNotNone(record['commands'][0]['judge']['binding'])
        migrated = run_python(new, """
from fresh_repair_migration import migrate_repaired_game
from fresh_learning_campaign import replay_game
result=migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='private handler-source-only repair')
assert replay_game(result,root)['exact_match']
print(json.dumps(result))
""", {'record': record, 'old': str(old), 'approved': approve(old, new)})
        before, after = record['commands'][0], migrated['commands'][0]
        self.assertNotEqual(before['judge']['binding']['handler_module_sha256'], after['judge']['binding']['handler_module_sha256'])
        self.assertNotEqual(before['judge']['receipt_sha256'], after['judge']['receipt_sha256'])
        self.assertNotEqual(before['observation']['observation_sha256'], after['observation']['observation_sha256'])
        for key in ('result', 'decisions', 'public_view', 'public_view_after', 'rating'):
            self.assertEqual(before[key], after[key])
        self.assertEqual(record['final']['state'], migrated['final']['state'])

    def test_failed_pending_choice_values_are_preserved_and_retried_without_choice(self):
        old, new, record = self.mechanic_roots(fail=True)
        self.assertEqual(record['status'], 'HALT')
        self.assertEqual(record['commands'][0]['command'], 'RESOLVE_PENDING')
        self.assertEqual(len(record['commands'][0]['decisions']), 2)
        result = run_python(new, """
import fresh_learning_campaign as runner
from interaction_learning import LearningState
from fresh_repair_migration import migrate_repaired_game
runner.LearningPlayerBot.choose=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('pending choice rerolled'))
migrated=migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='private pending gap repair')
result=runner.run_game(0,root,context_file=migrated['context_file'],campaign_id=migrated['campaign_id'],learning_state=LearningState.from_dict(migrated['learning_state_before']),previous_record=migrated,max_commands=1)
assert runner.replay_game(result,root)['exact_match']
print(json.dumps({'migrated':migrated,'continued':result}))
""", {'record': record, 'old': str(old), 'approved': approve(old, new)})
        self.assertEqual(result['migrated']['commands'][0]['args'], record['commands'][0]['args'])
        self.assertEqual(result['migrated']['commands'][0]['selected_pending'], record['commands'][0]['selected_pending'])
        self.assertEqual(result['continued']['commands'][0]['args'], record['commands'][0]['args'])
        self.assertEqual(result['continued']['commands'][0]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertEqual(result['continued']['policy_rng_final'], record['policy_rng_final'])

    def test_original_replay_ignores_unverified_bytecode(self):
        # A valid timestamp/size .pyc may contain different code than its .py.
        # Only the verified source bytes may establish the original replay proof.
        import importlib.util
        import marshal
        import struct
        from match_context import digest
        old = self.base / (self._testMethodName + '-cached-old')
        shutil.copytree(self.old, old)
        source = old / 'SOURCE/fresh_learning_campaign.py'
        evil = source.read_text().replace('def replay_game(record, root=ROOT):',
            "def replay_game(record, root=ROOT):\n    return {'exact_match':True,'record_sha256':digest(record),'certification':'NONE_SOFTWARE_REPLAY_ONLY'}")
        cache = Path(importlib.util.cache_from_source(str(source)))
        cache.parent.mkdir(parents=True, exist_ok=True)
        header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, int(source.stat().st_mtime), source.stat().st_size)
        cache.write_bytes(header + marshal.dumps(compile(evil, str(source), 'exec')))
        record = copy.deepcopy(self.stopped)
        record['commands'][0]['result']['tamper'] = True
        record['record_sha256'] = digest({k:v for k,v in record.items() if k != 'record_sha256'})
        result = run_python(self.new, """
from fresh_repair_migration import migrate_repaired_game
from context_runtime import RuntimeHalt
try:
    migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='private bytecode isolation check')
    print(json.dumps('accepted'))
except RuntimeHalt as error: print(json.dumps(str(error)))
""", {'record': record, 'old': str(old), 'approved': approve(old, self.new)})
        self.assertIn('ORIGINAL_REPLAY_FAILED', result)

    def test_rehashed_lineage_relationship_and_dependency_tampering_is_rejected(self):
        migrated = self.migrate()['record']
        result = run_python(self.new, """
from match_context import digest
from fresh_learning_campaign import replay_game
from context_runtime import RuntimeHalt
import copy
errors=[]
for field in ('selection','parent_prefix','parent_rng','parent_observations','dependency','checkpoint','source_map','failed_digest'):
    record=copy.deepcopy(data); line=record['repair_lineage']; parent=line['parent_record']
    if field=='selection': record['commands'][-1]['args']['redraw']=not record['commands'][-1]['args']['redraw']
    elif field=='parent_prefix':
        parent['commands'][0]['result']['tamper']=True
        parent['record_sha256']=digest({k:v for k,v in parent.items() if k!='record_sha256'})
        line['parent_record_field_sha256']=parent['record_sha256']
        line['parent_record_sha256']=digest(parent)
        line['original_replay_receipt']['record_sha256']=digest(parent)
    elif field in ('parent_rng','parent_observations'):
        if field=='parent_rng':
            parent['policy_rng_final']['A']['state'][1][0]^=1
            line['policy_rng_sha256']=digest(parent['policy_rng_final'])
        else: parent['tracker_observations'][0]['result']['tamper']=True
        parent['record_sha256']=digest({k:v for k,v in parent.items() if k!='record_sha256'})
        line['parent_record_field_sha256']=parent['record_sha256']
        line['parent_record_sha256']=digest(parent)
        line['original_replay_receipt']['record_sha256']=digest(parent)
    elif field=='dependency': line['dependency_hashes']['RULES/RULES_LOCK.json']='0'*64
    elif field=='checkpoint': line['checkpoint_sha256']='0'*64
    elif field=='source_map': line['original_sources']['interaction_learning.py']='0'*64
    else: line['failed_selection_sha256']='0'*64
    line['lineage_sha256']=digest({k:v for k,v in line.items() if k!='lineage_sha256'})
    record['record_sha256']=digest({k:v for k,v in record.items() if k!='record_sha256'})
    try: replay_game(record,root)
    except RuntimeHalt: errors.append(field)
print(json.dumps(errors))
""", migrated)
        self.assertEqual(result, ['selection','parent_prefix','parent_rng','parent_observations','dependency','checkpoint','source_map','failed_digest'])

    def test_audit_failure_and_malformed_failure_positions_are_rejected(self):
        from match_context import digest
        for mutation in ('audit', 'missing_failed', 'interior_failed', 'rated_failed'):
            record = copy.deepcopy(self.stopped)
            if mutation == 'audit': record['status'] = 'JUDGE_AUDIT_FAILURE'
            elif mutation == 'missing_failed': record['commands'].pop()
            elif mutation == 'interior_failed': record['commands'].append(copy.deepcopy(record['commands'][0]))
            else: record['commands'][-1]['rating']['status'] = 'GREEN'
            record['record_sha256'] = digest({k:v for k,v in record.items() if k != 'record_sha256'})
            with self.subTest(mutation=mutation):
                self.assertIn('error', self.migrate(record))

    @staticmethod
    def cached_code(source, text):
        import importlib.util
        import marshal
        import struct
        cache = Path(importlib.util.cache_from_source(str(source)))
        cache.parent.mkdir(parents=True, exist_ok=True)
        header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0,
            int(source.stat().st_mtime), source.stat().st_size)
        cache.write_bytes(header + marshal.dumps(compile(text, str(source), 'exec')))
        return cache

    def test_repaired_source_prefix_change_cannot_hide_in_valid_stale_bytecode(self):
        source = self.new / 'SOURCE/match_preparation.py'
        original = source.read_text()
        source.write_text(original.replace("return {'initial_hands':",
            "return {'review_changed_prefix':True,'initial_hands':", 1))
        cache = self.cached_code(source, original)
        cached = self.migrate()
        cache.unlink()
        uncached = self.migrate()
        self.assertIn('PREFIX_RESULT', cached.get('error', ''))
        self.assertEqual(cached, uncached)

    def test_already_imported_engine_cannot_mask_a_different_approved_source(self):
        result = run_python(self.new, """
import match_preparation
source=root/'SOURCE/match_preparation.py'
source.write_text(source.read_text().replace("return {'initial_hands':", "return {'review_changed_prefix':True,'initial_hands':",1))
import hashlib
before=data['record']['sources']
after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'SOURCE').glob('*.py') if not p.name.startswith('test_')}
approved={k:{'before':before.get(k),'after':after.get(k)} for k in before.keys()|after.keys() if before.get(k)!=after.get(k)}
from fresh_repair_migration import migrate_repaired_game
from context_runtime import RuntimeHalt
try:
    migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=approved,repair_note='preloaded old engine fixture')
    print(json.dumps('accepted'))
except RuntimeHalt as error: print(json.dumps(str(error)))
""", {'record': self.stopped, 'old': str(self.old)})
        self.assertIn('PREFIX_RESULT', result)

    def test_migrated_resume_and_replay_execute_source_instead_of_stale_bytecode(self):
        migrated = self.migrate()['record']
        source = self.new / 'SOURCE/match_preparation.py'
        evil = source.read_text().replace("return {'redraw':choice['redraw'],'phase':state.phase,'full_match_credit':0}",
            "return {'redraw':choice['redraw'],'phase':state.phase,'full_match_credit':0,'review_stale':True}")
        self.cached_code(source, evil)
        result = run_python(self.new, """
import fresh_learning_campaign as runner
from interaction_learning import LearningState
result=runner.run_game(0,root,context_file=data['context_file'],campaign_id=data['campaign_id'],learning_state=LearningState.from_dict(data['learning_state_before']),previous_record=data,max_commands=1)
assert runner.replay_game(result,root)['exact_match']
print(json.dumps(result))
""", migrated)
        self.assertEqual(result['commands'][-1]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertNotIn('review_stale', result['commands'][-1]['result'])
        self.assertEqual(result['policy_rng_final'], migrated['policy_rng_final'])
        self.assertEqual(result['learning_state_after'], migrated['learning_state_before'])

    def test_source_only_migrated_retry_covers_dynamically_imported_handler_cache(self):
        old, new, record = self.mechanic_roots(fail=True)
        source = new / 'SOURCE/on_play_effects.py'
        evil = source.read_text().replace("return {'target': None, 'processing': 'NO_ELIGIBLE_TARGET', 'full_match_credit': 0}",
            "return {'target': None, 'processing': 'NO_ELIGIBLE_TARGET', 'full_match_credit': 0,'review_stale_handler': True}")
        self.cached_code(source, evil)
        result = run_python(new, """
import on_play_effects
import fresh_learning_campaign as runner
from interaction_learning import LearningState
from fresh_repair_migration import migrate_repaired_game
migrated=migrate_repaired_game(data['record'],root=root,original_source_root=Path(data['old']),approved_changes=data['approved'],repair_note='dynamic handler cache fixture')
result=runner.run_game(0,root,context_file=migrated['context_file'],campaign_id=migrated['campaign_id'],learning_state=LearningState.from_dict(migrated['learning_state_before']),previous_record=migrated,max_commands=1)
assert runner.replay_game(result,root)['exact_match']
print(json.dumps(result))
""", {'record': record, 'old': str(old), 'approved': approve(old, new)})
        self.assertEqual(result['commands'][-1]['status'], 'EXPERIMENTAL_RESOLVED')
        self.assertNotIn('review_stale_handler', result['commands'][-1]['result'])
        self.assertEqual(result['policy_rng_final'], record['policy_rng_final'])
        self.assertEqual(result['commands'][-1]['args'], record['commands'][-1]['args'])
