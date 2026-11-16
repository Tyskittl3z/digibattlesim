"""BT20-102 checks Security after deleting a Digimon in attack battle."""
import copy
import gzip
import json
import unittest

from attack_flow import confirm_attack, end_attack
from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, queue_effects, resolve_pending
from field_tracker import FieldTracker
from imported_attempts import has_attack_child_pending
from interaction_scoring import score_transition
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class OmnimonPiercingTests(unittest.TestCase):
    def test_deferred_attack_can_settle_ineligible_child_before_ending(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 314, 'B',
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        runtime.state.phase = 'END_OF_TURN'
        attacker = stage(runtime, 'B', ['BT20-102'])
        observer = stage(runtime, 'B', ['BT22-023', 'EX13-023'], suspended=True)
        source = runtime.state.battle['B'][observer].cards[0].key
        runtime.state.attack = {'attacker': attacker, 'attacker_instance': 'entity-1',
                                'target': 'PLAYER', 'target_instance': '',
                                'controller': 'B', 'defender': 'A', 'window': 'END',
                                'counter_used': False, 'block_used': False,
                                'checked': None, 'deferred_depth': 0}
        queue_effects(runtime, [{'seat': 'B', 'source': source,
                                 'effect_id': 'BT22-023.inherited_unsuspend',
                                 'field': 'inherited_text',
                                 'trigger': {'kind': 'ORIENTATION_CHANGED',
                                             'entity': observer, 'suspended_before': False,
                                             'suspended_after': True}}])
        self.assertEqual(runtime.state.pending[0]['depth'], 1)
        self.assertTrue(has_attack_child_pending(runtime))
        self.assertEqual(pending_options(runtime, 'B'), [])
        settled = runtime.settle_pending()
        self.assertEqual(settled['cancelled'], 1)
        self.assertEqual(runtime.state.pending, [])
        self.assertEqual(runtime.state.attack['window'], 'END')
        end_attack(runtime, 'B', ROOT)
        self.assertIsNone(runtime.state.attack)

    def test_ordinary_attack_can_settle_ineligible_child_before_ending(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 315, 'B',
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        runtime.state.phase = 'MAIN'
        attacker = stage(runtime, 'B', ['BT22-023', 'EX13-023'], suspended=True)
        source = runtime.state.battle['B'][attacker].cards[0].key
        runtime.state.attack = {'attacker': attacker, 'attacker_instance': 'entity-1',
                                'target': 'PLAYER', 'target_instance': '',
                                'controller': 'B', 'defender': 'A', 'window': 'END',
                                'counter_used': False, 'block_used': False,
                                'checked': None}
        queue_effects(runtime, [{'seat': 'B', 'source': source,
                                 'effect_id': 'BT22-023.inherited_unsuspend',
                                 'field': 'inherited_text',
                                 'trigger': {'kind': 'ORIENTATION_CHANGED',
                                             'entity': attacker, 'suspended_before': False,
                                             'suspended_after': True}}])
        self.assertTrue(has_attack_child_pending(runtime))
        self.assertEqual(pending_options(runtime, 'B'), [])
        self.assertEqual(runtime.settle_pending()['cancelled'], 1)
        end_attack(runtime, 'B', ROOT)
        self.assertIsNone(runtime.state.attack)

    def test_end_turn_piercing_must_resolve_before_end_attack(self):
        # Comprehensive Rules v4.3 section 16-7-4: Piercing is pending
        # processing immediately before transition to end of attack timing.
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 313, 'B',
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.turn = 3
        attacker = stage(runtime, 'B', ['BT20-102'])
        defender = stage(runtime, 'A', ['BT12-029'], suspended=True)
        runtime.state.battle['B'][attacker].instance_id = 'entity-b'
        runtime.state.battle['A'][defender].instance_id = 'entity-a'
        security = next(card for card in runtime.state.zones['A']['deck']
                        if card.card_number == 'BT11-032')
        runtime.state.zones['A']['deck'].remove(security)
        runtime.state.zones['A']['security'].append(security)
        runtime.state.attack = {'attacker': attacker, 'attacker_instance': 'entity-b',
                                'target': defender, 'target_instance': 'entity-a',
                                'controller': 'B', 'defender': 'A', 'window': 'CONFIRM',
                                'counter_used': False, 'block_used': False,
                                'checked': None, 'deferred_depth': 0}
        battle = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(battle['battle_losers'], ['DEFENDER'])
        self.assertEqual(runtime.state.attack['window'], 'END')
        self.assertEqual(runtime.state.attack['deferred_depth'], 0)
        piercing = [p for p in pending_options(runtime, 'B')
                    if p['effect_id'] == 'BT20-102.piercing_check']
        self.assertEqual(len(piercing), 1)
        self.assertGreater(piercing[0]['depth'], runtime.state.attack['deferred_depth'])
        with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            end_attack(copy.deepcopy(runtime), 'B', ROOT)
        invalid = copy.deepcopy(runtime)
        invalid.state.attack = None
        with self.assertRaisesRegex(RuntimeHalt, 'OMNIMON_PIERCING_WINDOW_REQUIRED'):
            resolve_pending(invalid, 'B', piercing[0]['id'], None)
        check = resolve_pending(runtime, 'B', piercing[0]['id'], None)
        self.assertEqual(check['checked_card'], security.key)
        self.assertEqual(runtime.state.attack['window'], 'END')
        end_attack(runtime, 'B', ROOT)
        self.assertIsNone(runtime.state.attack)

    def test_historical_closed_attack_piercing_is_counted_as_diagnostic(self):
        # Bot C reports what the old software did; this archive is not a
        # legal attack-timing example after the section 16-7-4 review.
        with gzip.open(ROOT / 'ARTIFACTS/board-text-60-2026-11-11/game-0024/segment-0002.json.gz', 'rt') as handle:
            record = json.load(handle)
        action = next(command for command in record['commands']
                      if command['result'].get('processing') == 'MANDATORY_PIERCING_SECURITY_CHECK')
        self.assertIsNone(action['before']['state']['attack'])
        context = load_context_file(ROOT / record['context_file'])
        tracker = FieldTracker(context)
        tracker.start(action['before'])
        tracker.observe(action['tracker_command'], action['before'], action['after'],
                        action['result'], action['judge'])
        self.assertEqual(tracker.public_metrics()['successful_security_checks']['B'], 1)

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

if __name__ == '__main__':
    unittest.main()
