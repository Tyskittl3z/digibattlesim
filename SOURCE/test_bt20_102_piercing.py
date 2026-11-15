"""BT20-102 checks Security after deleting a Digimon in attack battle."""
import copy
import gzip
import json
import unittest

from attack_flow import choose_blocker, choose_counter, confirm_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from field_tracker import FieldTracker
from imported_attempts import _apply
from interaction_scoring import score_transition
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry, selected_pending_choices
from test_selected_mechanics import ROOT


class OmnimonPiercingTests(unittest.TestCase):
    def test_piercing_check_rejects_mismatched_nested_result(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0011/segment-0004.json.gz', 'rt') as handle:
            record = json.load(handle)
        action = next(command for command in record['commands']
                      if command['result'].get('processing') == 'MANDATORY_PIERCING_SECURITY_CHECK')
        context = load_context_file(ROOT / record['context_file'])
        tracker = FieldTracker(context)
        tracker.start(action['before'])
        result = copy.deepcopy(action['result'])
        result['check']['checked_card'] = 'A:wrong-card#1'
        with self.assertRaisesRegex(Exception, 'TRACKER_SECURITY_CHECK_RESULT_MISMATCH'):
            tracker.observe(action['tracker_command'], action['before'], action['after'],
                            result, action['judge'])

    def test_saved_piercing_check_updates_bot_c_and_tempo(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0011/segment-0004.json.gz', 'rt') as handle:
            record = json.load(handle)
        action = next(command for command in record['commands']
                      if command['result'].get('processing') == 'MANDATORY_PIERCING_SECURITY_CHECK')
        context = load_context_file(ROOT / record['context_file'])
        tracker = FieldTracker(context)
        tracker.start(action['before'])
        before_metrics = tracker.public_metrics()
        observation = tracker.observe(action['tracker_command'], action['before'], action['after'],
                                      action['result'], action['judge'])
        after_metrics = tracker.public_metrics()
        self.assertEqual(observation['public_metrics_after']['successful_security_checks']['B'], 1)
        self.assertEqual(after_metrics['successful_security_checks']['B'], 1)
        rating = score_transition(action['public_view'], action['public_view_after'], 'B',
                                  command=action['tracker_command'], result=action['result'], context=context,
                                  public_metrics_before=before_metrics, public_metrics_after=after_metrics)
        self.assertEqual(rating['components']['security_checks']['delta'], 1)

    def test_saved_end_turn_digimon_battle_queues_mandatory_security_check(self):
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0011/segment-0000.json.gz', 'rt') as handle:
            record = json.load(handle)
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
            build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        failed = record['commands'][-1]
        self.assertEqual(runtime.snapshot()['state'], failed['before']['state'])
        source = 'B:BT20-102#1'
        attack = resolve_pending(runtime, 'B', failed['args']['pending_id'], failed['args']['choice'])
        self.assertEqual(attack['target'], 'A:BT12-029#1')
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        choose_counter(runtime, 'A', None, ROOT)
        choose_blocker(runtime, 'A', None, ROOT)
        before_security = len(runtime.state.zones['A']['security'])
        battle = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(battle['battle_losers'], ['DEFENDER'])
        self.assertIn(source, runtime.state.battle['B'])
        piercing = [p for p in pending_options(runtime, 'B')
            if p['effect_id'] == 'BT20-102.piercing_check']
        self.assertEqual(len(piercing), 1)
        self.assertEqual(selected_pending_choices(runtime, 'B', piercing[0]), [None])
        check = resolve_pending(runtime, 'B', piercing[0]['id'], None)
        self.assertEqual(check['checked_card'], 'A:EX13-019#1')
        self.assertEqual(len(runtime.state.zones['A']['security']), before_security - 1)
        self.assertEqual(runtime.state.attack['window'], 'END')
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
