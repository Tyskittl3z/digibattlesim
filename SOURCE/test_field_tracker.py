"""Bot C shadows committed physical states; these scenarios play no matches."""
import copy
import importlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from context_runtime import ContextRuntime, RuntimeHalt, Stack
from match_context import digest
from match_preparation import begin_preparation, choose_redraw
from matchup_readiness import load_context_file


ROOT = Path(__file__).resolve().parents[1]


class FieldTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('field_tracker'),
                             'Bot C needs an independent physical-state tracker')
        self.Tracker = importlib.import_module('field_tracker').FieldTracker

    def runtime(self):
        return ContextRuntime(self.context, 313, 'A', allow_experimental=True)

    def take(self, runtime, seat, number):
        for zone in ('deck', 'eggdeck'):
            cards = runtime.state.zones[seat][zone]
            physical = next((card for card in cards if card.card_number == number), None)
            if physical is not None:
                cards.remove(physical)
                return physical
        self.fail('Fixture card missing: ' + number)

    def stage(self, runtime, seat, numbers, entity='entity-test'):
        cards = [self.take(runtime, seat, number) for number in numbers]
        runtime.state.battle[seat][cards[-1].key] = Stack(cards, instance_id=entity)
        return cards[-1].key

    def observe(self, tracker, before, after, *, command='TEST_MOVE', result=None, status='EXPERIMENTAL_RESOLVED'):
        return tracker.observe({'command': command, 'seat': 'A', 'args': {}, 'status': status},
                               before, after, result or {}, {'status': 'ENGINE_CHECKED_EXPERIMENTAL'})

    def test_start_public_views_and_manifest_are_exact_and_detached(self):
        runtime = self.runtime()
        runtime.state.zones['A']['hand'].append(self.take(runtime, 'A', 'EX1-013'))
        runtime.state.zones['B']['security'].append(self.take(runtime, 'B', 'EX13-069'))
        tracker = self.Tracker(self.context)
        original = runtime.snapshot()
        tracker.start(original)
        for seat in ('A', 'B'):
            self.assertEqual(tracker.player_view(seat), runtime.public_view(seat))
        self.assertEqual(tracker.player_view('A')['players']['B']['security'], {'count': 1})
        self.assertNotIn('rng_state', tracker.player_view('A'))
        physical = copy.deepcopy(original); physical.pop('execution_id')
        self.assertEqual(tracker.audit_snapshot(), physical)
        original['state']['memory'] = 9
        detached = tracker.audit_snapshot(); detached['state']['zones']['A']['hand'].clear()
        self.assertEqual(tracker.player_view('A'), runtime.public_view('A'))
        manifest = tracker.manifest()
        self.assertEqual((manifest['name'], manifest['role']), ('Bot C', 'FIELD_TRACKER'))
        self.assertEqual(manifest['context_id'], self.context.matchup_id)
        self.assertEqual(manifest['physical_card_count'], 108)
        self.assertEqual(len(manifest['source_sha256']), 64)
        manifest.clear(); self.assertEqual(tracker.manifest()['name'], 'Bot C')

    def test_opening_transactions_have_chained_private_moves_and_exact_views(self):
        runtime = self.runtime(); tracker = self.Tracker(self.context)
        tracker.start(runtime.snapshot())
        before = runtime.snapshot(); result = begin_preparation(runtime, ROOT)
        first = self.observe(tracker, before, runtime.snapshot(), command='BEGIN_PREPARATION', result=result)
        self.assertEqual(first['sequence'], 1)
        self.assertEqual(first['status'], 'COMMITTED')
        self.assertEqual(len(first['zone_movements']), 10)
        self.assertEqual(first['field']['zone_counts']['A']['hand'], 5)
        before = runtime.snapshot(); result = choose_redraw(runtime, 'A', True, ROOT)
        second = self.observe(tracker, before, runtime.snapshot(), command='REDRAW_CHOICE', result=result)
        self.assertEqual(second['previous_observation_sha256'], first['observation_sha256'])
        self.assertEqual(second['sequence'], 2)
        body = copy.deepcopy(second); claimed = body.pop('observation_sha256')
        self.assertEqual(digest(body), claimed)
        self.assertEqual(tracker.player_view('A'), runtime.public_view('A'))
        self.assertEqual(tracker.player_view('B'), runtime.public_view('B'))
        self.assertEqual(tracker.observations, [first, second])

    def test_duplicate_missing_and_wrong_owner_cards_fail_without_advancing(self):
        for corruption in ('duplicate', 'missing', 'wrong_owner'):
            runtime = self.runtime(); tracker = self.Tracker(self.context)
            before = runtime.snapshot(); tracker.start(before)
            after = copy.deepcopy(before)
            if corruption == 'duplicate':
                after['state']['zones']['A']['hand'].append(after['state']['zones']['A']['deck'][0])
                after['state']['zones']['A']['deck'].pop()
            elif corruption == 'missing': after['state']['zones']['A']['deck'].pop()
            else: after['state']['zones']['B']['hand'].append(after['state']['zones']['A']['deck'].pop())
            with self.subTest(corruption=corruption), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_PHYSICAL'):
                self.observe(tracker, before, after)
            self.assertEqual(tracker.observations, [])
            self.assertEqual(tracker.player_view('A'), runtime.public_view('A'))

    def test_start_rejects_wrong_context_and_unknown_zone_schema(self):
        for corruption in ('context', 'zone'):
            snapshot = self.runtime().snapshot()
            if corruption == 'context': snapshot['context_id'] = 'wrong'
            else: snapshot['state']['zones']['A']['extra'] = []
            with self.subTest(corruption=corruption), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                self.Tracker(self.context).start(snapshot)

    def test_stale_snapshot_changed_seed_and_rng_are_rejected(self):
        runtime = self.runtime(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        for corruption in ('memory', 'rng', 'seed', 'first'):
            stale = copy.deepcopy(before)
            if corruption == 'memory': stale['state']['memory'] += 1
            elif corruption == 'rng': stale['rng_state'][1][0] ^= 1
            elif corruption == 'seed': stale['seed'] += 1
            else: stale['first'] = 'B'
            with self.subTest(corruption=corruption), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                self.observe(tracker, stale, stale)
        self.assertEqual(tracker.observations, [])

    def test_resolving_option_and_breeding_sources_are_counted_once(self):
        runtime = self.runtime()
        runtime.state.breeding['A'] = [self.take(runtime, 'A', 'EX13-002'), self.take(runtime, 'A', 'EX1-013')]
        option = self.take(runtime, 'B', 'LM-028')
        runtime.state.resolving_option = {'seat': 'B', 'stack': Stack([option])}
        tracker = self.Tracker(self.context); tracker.start(runtime.snapshot())
        self.assertEqual(tracker.player_view('B'), runtime.public_view('B'))
        duplicate = runtime.snapshot(); duplicate['state']['zones']['B']['trash'].append(option.key)
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_PHYSICAL'):
            self.Tracker(self.context).start(duplicate)

    def test_evolution_reanchors_one_entity_without_false_zone_departure(self):
        runtime = self.runtime(); base = self.stage(runtime, 'A', ['EX1-013'], entity='same-entity')
        target = self.take(runtime, 'A', 'BT22-022'); runtime.state.zones['A']['hand'].append(target)
        tracker = self.Tracker(self.context); before = runtime.snapshot(); tracker.start(before)
        runtime.state.zones['A']['hand'].remove(target)
        stack = runtime.state.battle['A'].pop(base); stack.cards.append(target)
        runtime.state.battle['A'][target.key] = stack
        observed = self.observe(tracker, before, runtime.snapshot())
        self.assertEqual([move['card'] for move in observed['zone_movements']], [target.key])
        entity = observed['field']['battle_entities']['A'][0]
        self.assertEqual((entity['instance_id'], entity['anchor'], entity['top'], entity['sources']),
                         ('same-entity', target.key, target.key, [base]))
        self.assertEqual(tracker.public_metrics()['board']['A']['largest_stack_size'], 2)
        self.assertEqual(tracker.public_metrics()['board']['A']['digivolution_card_count'], 1)

    def test_failed_command_is_unrated_and_cannot_commit_partial_changes(self):
        runtime = self.runtime(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        failed = self.observe(tracker, before, before, status='HALT')
        self.assertEqual((failed['status'], failed['rating_status']), ('FAILED_UNRATED', 'UNRATED'))
        self.assertEqual(failed['zone_movements'], [])
        corrupt = copy.deepcopy(before); corrupt['state']['memory'] = 1
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_FAILED_COMMAND_CHANGED_STATE'):
            self.observe(tracker, before, corrupt, status='HALT')
        self.assertEqual(len(tracker.observations), 1)

    def test_judge_rejection_also_requires_unchanged_physical_state(self):
        runtime = self.runtime(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        observation = tracker.observe({'command': 'TEST', 'seat': 'A'}, before, before, None,
                                      {'verdict': 'UNRESOLVED'})
        self.assertEqual(observation['status'], 'FAILED_UNRATED')
        self.assertEqual(tracker.public_metrics()['successful_security_checks'], {'A': 0, 'B': 0})

    def test_returned_observations_and_inputs_do_not_alias_tracker(self):
        runtime = self.runtime(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        command = {'command': 'TEST', 'seat': 'A'}; result = {'details': []}; judge = {'status': 'PASS'}
        observation = tracker.observe(command, before, before, result, judge)
        command['command'] = 'CHANGED'; result['details'].append(1); judge['status'] = 'CHANGED'
        observation['field']['zone_counts']['A']['deck'] = 0
        detached = tracker.observations; detached.clear()
        self.assertEqual(tracker.observations[0]['command']['command'], 'TEST')
        self.assertEqual(tracker.observations[0]['result'], {'details': []})
        self.assertEqual(tracker.observations[0]['judge_verdict'], {'status': 'PASS'})
        self.assertEqual(tracker.observations[0]['field']['zone_counts']['A']['deck'], 50)

    def test_execution_revision_is_excluded_but_all_physical_fields_are_retained(self):
        runtime = self.runtime(); before = runtime.snapshot()
        one, two = self.Tracker(self.context), self.Tracker(self.context)
        other = copy.deepcopy(before); other['execution_id'] = 'different-engine-revision'
        one.start(before); two.start(other)
        first = self.observe(one, before, before); second = self.observe(two, other, other)
        self.assertEqual(first, second)
        self.assertEqual(one.audit_snapshot(), two.audit_snapshot())
        self.assertNotIn('execution_id', one.audit_snapshot())

    def check_fixture(self, card='P-138'):
        runtime = self.runtime(); attacker = self.stage(runtime, 'A', ['BT11-032'])
        checked = self.take(runtime, 'B', card); runtime.state.zones['B']['security'].append(checked)
        runtime.state.phase = 'MAIN'; runtime.state.turn = 3
        runtime.state.attack = {'attacker': attacker, 'controller': 'A', 'defender': 'B',
            'target': 'PLAYER', 'window': 'CONFIRM', 'checked': None}
        return runtime, checked

    def test_completed_security_digimon_check_counts_even_if_attacker_loses(self):
        runtime, checked = self.check_fixture(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        runtime.state.zones['B']['security'].pop(); runtime.state.zones['B']['trash'].append(checked)
        attacker = runtime.state.battle['A'].pop(runtime.state.attack['attacker'])
        runtime.state.zones['A']['trash'].extend(attacker.cards)
        runtime.state.attack.update({'window': 'END', 'checked': checked.key})
        observation = self.observe(tracker, before, runtime.snapshot(), command='CONFIRM_ATTACK',
                                   result={'success': True, 'checked_card': checked.key, 'attacker_deleted': True})
        self.assertEqual(tracker.public_metrics()['successful_security_checks'], {'A': 1, 'B': 0})
        self.assertEqual(observation['public_metrics_after']['successful_security_checks']['A'], 1)
        view = tracker.player_view('A'); self.assertNotIn('successful_security_checks', view)

    def test_completed_security_tamer_play_counts_and_enters_board_metrics(self):
        runtime, checked = self.check_fixture('EX13-069'); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        runtime.state.zones['B']['security'].pop()
        runtime.state.battle['B'][checked.key] = Stack([checked], instance_id='security-tamer')
        runtime.state.attack.update({'window': 'END', 'checked': checked.key})
        self.observe(tracker, before, runtime.snapshot(), command='CONFIRM_ATTACK',
                     result={'success': True, 'checked_card': checked.key, 'security_effect': 'EX13-069.security_play'})
        self.assertEqual(tracker.public_metrics()['successful_security_checks']['A'], 1)
        self.assertEqual(tracker.public_metrics()['board']['B']['tamer_count'], 1)
        self.assertEqual(tracker.player_view('B'), runtime.public_view('B'))

    def test_declarations_failed_checks_and_direct_wins_do_not_count_security_cards(self):
        runtime, checked = self.check_fixture(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        after = copy.deepcopy(before); after['state']['attack']['window'] = 'END'
        self.observe(tracker, before, after, command='CONFIRM_ATTACK', result={'success': False})
        self.observe(tracker, after, after, command='DECLARE_ATTACK', result={'success': True})
        self.observe(tracker, after, after, command='CONFIRM_ATTACK',
                     result={'success': True, 'checked_card': checked.key}, status='HALT')
        self.assertEqual(tracker.public_metrics()['successful_security_checks'], {'A': 0, 'B': 0})
        direct = self.runtime(); direct.state.phase = 'MAIN'; direct.state.turn = 3
        direct.state.attack = {'controller': 'A', 'defender': 'B', 'target': 'PLAYER', 'window': 'CONFIRM', 'checked': None}
        before = direct.snapshot(); other = self.Tracker(self.context); other.start(before)
        direct.state.terminal = True; direct.state.winner = 'A'; direct.state.attack = None
        self.observe(other, before, direct.snapshot(), command='CONFIRM_ATTACK', result={'success': True, 'winner': 'A'})
        self.assertEqual(other.public_metrics()['successful_security_checks'], {'A': 0, 'B': 0})

    def test_unbacked_successful_security_claim_cannot_inflate_counter(self):
        runtime, checked = self.check_fixture(); before = runtime.snapshot()
        tracker = self.Tracker(self.context); tracker.start(before)
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_SECURITY_CHECK_RESULT_MISMATCH'):
            self.observe(tracker, before, before, command='CONFIRM_ATTACK',
                         result={'success': True, 'checked_card': checked.key})
        self.assertEqual(tracker.observations, [])
        self.assertEqual(tracker.public_metrics()['successful_security_checks']['A'], 0)

    def test_after_snapshot_cannot_change_game_identity(self):
        runtime = self.runtime(); before = runtime.snapshot()
        for field, changed in (('context_id', 'wrong'), ('seed', before['seed'] + 1), ('first', 'B')):
            tracker = self.Tracker(self.context); tracker.start(before)
            after = copy.deepcopy(before); after[field] = changed
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                self.observe(tracker, before, after)
            self.assertEqual(tracker.observations, [])
            self.assertEqual(tracker.audit_snapshot(), {k: v for k, v in before.items() if k != 'execution_id'})

    def test_nonempty_entity_identity_must_be_unique(self):
        runtime = self.runtime()
        self.stage(runtime, 'A', ['EX1-013'], entity='same')
        self.stage(runtime, 'B', ['BT11-032'], entity='same')
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_PHYSICAL_DUPLICATE_ENTITY'):
            self.Tracker(self.context).start(runtime.snapshot())

    def test_security_claim_requires_matching_actor_top_card_and_attack_windows(self):
        for corruption in ('actor', 'defender', 'top', 'already_checked', 'before_window',
                           'after_window', 'after_actor', 'after_target', 'extra_removed'):
            runtime, checked = self.check_fixture()
            extra = self.take(runtime, 'B', 'EX1-013')
            runtime.state.zones['B']['security'].insert(0, extra)
            before = runtime.snapshot(); after = copy.deepcopy(before)
            after['state']['zones']['B']['security'].pop()
            after['state']['zones']['B']['trash'].append(checked.key)
            after['state']['attack'].update({'window': 'END', 'checked': checked.key})
            command = {'command': 'CONFIRM_ATTACK', 'seat': 'A', 'status': 'EXPERIMENTAL_RESOLVED'}
            if corruption == 'actor': command['seat'] = 'B'
            elif corruption == 'defender': before['state']['attack']['defender'] = 'A'
            elif corruption == 'top':
                before['state']['zones']['B']['security'].reverse()
            elif corruption == 'already_checked': before['state']['attack']['checked'] = checked.key
            elif corruption == 'before_window': before['state']['attack']['window'] = 'COUNTER'
            elif corruption == 'after_window': after['state']['attack']['window'] = 'CONFIRM'
            elif corruption == 'after_actor': after['state']['attack']['controller'] = 'B'
            elif corruption == 'after_target': after['state']['attack']['target'] = 'not-player'
            else:
                after['state']['zones']['B']['security'].remove(extra.key)
                after['state']['zones']['B']['trash'].append(extra.key)
            tracker = self.Tracker(self.context); tracker.start(before)
            with self.subTest(corruption=corruption), self.assertRaisesRegex(
                    RuntimeHalt, 'TRACKER_SECURITY_CHECK_RESULT_MISMATCH'):
                tracker.observe(command, before, after, {'success': True, 'checked_card': checked.key},
                                {'status': 'PASS'})
            self.assertEqual(tracker.observations, [])
            self.assertEqual(tracker.public_metrics()['successful_security_checks'], {'A': 0, 'B': 0})

    def test_same_card_recovered_and_checked_in_new_attack_counts_again(self):
        runtime, checked = self.check_fixture(); tracker = self.Tracker(self.context)
        tracker.start(runtime.snapshot())
        for occurrence in range(2):
            before = runtime.snapshot()
            runtime.state.zones['B']['security'].pop(); runtime.state.zones['B']['trash'].append(checked)
            runtime.state.attack.update({'window': 'END', 'checked': checked.key})
            after = runtime.snapshot()
            self.observe(tracker, before, after, command='CONFIRM_ATTACK',
                         result={'success': True, 'checked_card': checked.key})
            self.assertEqual(tracker.public_metrics()['successful_security_checks']['A'], occurrence + 1)
            with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_SECURITY_CHECK_RESULT_MISMATCH'):
                self.observe(tracker, after, after, command='CONFIRM_ATTACK',
                             result={'success': True, 'checked_card': checked.key})
            if occurrence == 0:
                before = runtime.snapshot()
                runtime.state.zones['B']['trash'].remove(checked); runtime.state.zones['B']['security'].append(checked)
                runtime.state.attack.update({'window': 'CONFIRM', 'checked': None})
                self.observe(tracker, before, runtime.snapshot(), command='TEST_RECOVERY_AND_NEXT_ATTACK')

    def test_hidden_permutations_do_not_leak_into_views_or_public_metrics(self):
        runtime = self.runtime()
        runtime.state.zones['B']['hand'].append(self.take(runtime, 'B', 'EX1-013'))
        first = runtime.snapshot(); second = copy.deepcopy(first)
        second['state']['zones']['B']['hand'][0], second['state']['zones']['B']['deck'][0] = (
            second['state']['zones']['B']['deck'][0], second['state']['zones']['B']['hand'][0])
        one, two = self.Tracker(self.context), self.Tracker(self.context)
        one.start(first); two.start(second)
        self.assertEqual(one.player_view('A'), two.player_view('A'))
        self.assertEqual(one.public_metrics(), two.public_metrics())
        metrics = one.public_metrics(); metrics['board']['A']['battle_card_count'] = 999
        metrics['successful_security_checks']['A'] = 999
        self.assertEqual(one.public_metrics()['board']['A']['battle_card_count'], 0)
        self.assertEqual(one.public_metrics()['successful_security_checks']['A'], 0)

    def test_accepted_actions_after_terminal_are_rejected_but_failed_attempt_can_be_logged(self):
        runtime = self.runtime(); runtime.state.terminal = True; runtime.state.winner = 'A'
        before = runtime.snapshot(); tracker = self.Tracker(self.context); tracker.start(before)
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_ACTION_AFTER_TERMINAL'):
            self.observe(tracker, before, before)
        self.assertEqual(tracker.observations, [])
        self.assertEqual(self.observe(tracker, before, before, status='HALT')['status'], 'FAILED_UNRATED')

    def test_missing_or_malformed_projected_fields_reject_start_atomically(self):
        runtime = self.runtime(); valid = runtime.snapshot()
        cases = [(name, None, True) for name in ('phase', 'attack', 'pending', 'winner')]
        cases += [('phase', None, False), ('attack', 4, False), ('pending', {}, False), ('winner', 'C', False)]
        for name, bad, missing in cases:
            snapshot = copy.deepcopy(valid)
            if missing: snapshot['state'].pop(name)
            else: snapshot['state'][name] = bad
            tracker = self.Tracker(self.context)
            with self.subTest(field=name, missing=missing):
                with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                    tracker.start(snapshot)
                tracker.start(valid)
                self.assertEqual(tracker.player_view('A'), runtime.public_view('A'))

    def test_negative_judge_status_overrides_an_accepted_flag(self):
        runtime = self.runtime(); snapshot = runtime.snapshot()
        for status in ('HALT', 'REJECTED', 'ILLEGAL', 'UNRESOLVED', 'SOFTWARE_GAP'):
            tracker = self.Tracker(self.context); tracker.start(snapshot)
            observed = tracker.observe({'command': 'TEST', 'seat': 'A', 'status': 'EXPERIMENTAL_RESOLVED'},
                snapshot, snapshot, {}, {'accepted': True, 'status': status})
            self.assertEqual(observed['status'], 'FAILED_UNRATED')
            self.assertEqual(observed['rating_status'], 'UNRATED')

    def test_initial_chain_is_bound_to_tracker_source_identity(self):
        snapshot = self.runtime().snapshot()
        first = self.Tracker(self.context)
        read_bytes = Path.read_bytes
        def changed_tracker_source(path):
            body = read_bytes(path)
            return body + b'\n# different tracker implementation\n' if path.name == 'field_tracker.py' else body
        with patch.object(Path, 'read_bytes', changed_tracker_source):
            second = self.Tracker(self.context)
        self.assertNotEqual(first.manifest()['tracker_id'], second.manifest()['tracker_id'])
        first.start(snapshot); second.start(snapshot)
        a = self.observe(first, snapshot, snapshot); b = self.observe(second, snapshot, snapshot)
        self.assertNotEqual(a['previous_observation_sha256'], b['previous_observation_sha256'])

    def test_unknown_projected_stack_and_attack_fields_cannot_leak_private_data(self):
        runtime, _ = self.check_fixture(); before = runtime.snapshot()
        for container in ('battle', 'attack', 'resolving_option'):
            snapshot = copy.deepcopy(before)
            if container == 'battle':
                value = next(iter(snapshot['state']['battle']['A'].values()))
            elif container == 'attack': value = snapshot['state']['attack']
            else:
                option = self.take(runtime, 'B', 'LM-028')
                runtime.state.resolving_option = {'seat': 'B', 'stack': Stack([option])}
                snapshot = runtime.snapshot(); value = snapshot['state']['resolving_option']['stack']
            value['private_deck_order'] = list(snapshot['state']['zones']['B']['deck'])
            with self.subTest(container=container), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                self.Tracker(self.context).start(snapshot)

    def test_projected_public_scalar_fields_reject_nested_private_payloads(self):
        runtime, _ = self.check_fixture(); before = runtime.snapshot()
        hidden = {'private_deck_order': list(before['state']['zones']['B']['deck'])}
        for area, field in (('battle', 'played_turn'), ('battle', 'ready_since_turn'),
                            ('attack', 'checked'), ('attack', 'target'), ('attack', 'counter_used')):
            snapshot = copy.deepcopy(before)
            value = (next(iter(snapshot['state']['battle']['A'].values()))
                     if area == 'battle' else snapshot['state']['attack'])
            value[field] = hidden
            with self.subTest(area=area, field=field), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                self.Tracker(self.context).start(snapshot)

    def grant_fixture(self):
        from effect_grants import grant_effect
        runtime = self.runtime(); runtime.state.turn = 3
        target = self.stage(runtime, 'A', ['EX1-013'], entity='granted-body')
        source = self.stage(runtime, 'A', ['BT11-112'], entity='public-tamer')
        grant_effect(runtime, 'A', target, {'keywords': ['Blocker', 'Evade']}, source)
        return runtime, target, source

    def test_supported_public_statuses_and_engine_grants_remain_exact(self):
        runtime, target, source = self.grant_fixture()
        runtime.state.battle['A'][source].statuses.update({'cannot_suspend': False, 'cannot_unsuspend': True})
        tracker = self.Tracker(self.context); tracker.start(runtime.snapshot())
        self.assertEqual(tracker.player_view('A'), runtime.public_view('A'))
        self.assertEqual(tracker.player_view('B'), runtime.public_view('B'))
        self.assertEqual(tracker.player_view('B')['players']['A']['battle'][target]['statuses'],
                         runtime.public_view('B')['players']['A']['battle'][target]['statuses'])

    def test_private_payloads_at_any_public_status_layer_are_rejected(self):
        runtime, target, _ = self.grant_fixture(); valid = runtime.snapshot()
        hidden = {'private_deck_order': list(valid['state']['zones']['B']['deck'])}
        for layer in ('status', 'grant', 'effect', 'expires', 'bool', 'source_hash', 'expiry_turn', 'keyword'):
            snapshot = copy.deepcopy(valid)
            status = snapshot['state']['battle']['A'][target]['statuses']; grant = status['effect_grants'][0]
            if layer == 'status': status.update(hidden)
            elif layer == 'grant': grant.update(hidden)
            elif layer in ('effect', 'expires'): grant[layer].update(hidden)
            elif layer == 'bool': status['cannot_suspend'] = hidden
            elif layer == 'source_hash': grant['source_definition_sha256'] = hidden
            elif layer == 'expiry_turn': grant['expires']['turn'] = hidden
            else: grant['effect']['keywords'] = [hidden]
            with self.subTest(layer=layer), self.assertRaisesRegex(RuntimeHalt, 'TRACKER_'):
                self.Tracker(self.context).start(snapshot)

    def test_security_result_cannot_switch_attacking_entity(self):
        for with_instance in (False, True):
            runtime, checked = self.check_fixture()
            replacement = self.stage(runtime, 'A', ['EX1-013'], entity='other-attacker')
            if with_instance: runtime.state.attack['attacker_instance'] = 'entity-test'
            before = runtime.snapshot(); after = copy.deepcopy(before)
            after['state']['zones']['B']['security'].pop()
            after['state']['zones']['B']['trash'].append(checked.key)
            after['state']['attack'].update({'window': 'END', 'checked': checked.key})
            if with_instance: after['state']['attack']['attacker_instance'] = 'other-attacker'
            else: after['state']['attack']['attacker'] = replacement
            tracker = self.Tracker(self.context); tracker.start(before)
            with self.subTest(with_instance=with_instance):
                with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_SECURITY_CHECK_RESULT_MISMATCH'):
                    self.observe(tracker, before, after, command='CONFIRM_ATTACK',
                                 result={'success': True, 'checked_card': checked.key})
                self.assertEqual(tracker.public_metrics()['successful_security_checks']['A'], 0)

    def test_lifecycle_guards_do_not_silently_reset_tracking(self):
        tracker = self.Tracker(self.context)
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_NOT_STARTED'): tracker.player_view('A')
        tracker.start(self.runtime().snapshot())
        with self.assertRaisesRegex(RuntimeHalt, 'TRACKER_ALREADY_STARTED'): tracker.start(self.runtime().snapshot())


if __name__ == '__main__':
    unittest.main()
