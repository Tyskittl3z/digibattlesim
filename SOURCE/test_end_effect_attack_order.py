"""An end-turn attack defers the other same-depth end effect."""
import unittest

from attack_flow import choose_counter, choose_blocker, confirm_attack, end_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from field_tracker import FieldTracker
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage
from turn_flow import finish_turn


class EndEffectAttackOrderTests(unittest.TestCase):
    def test_end_attack_defers_other_same_depth_effect(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 20, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.turn = 3
        runtime.state.memory = -1
        attacker = stage(runtime, 'B', ['BT20-102'], suspended=True)
        observer = stage(runtime, 'B', ['BT22-023'], suspended=True)
        runtime.state.battle['B'][attacker].played_turn = 1
        runtime.state.battle['B'][attacker].ready_since_turn = 2
        runtime.state.battle['B'][observer].played_turn = 1
        runtime.state.battle['B'][observer].ready_since_turn = 2
        card = next(c for c in runtime.state.zones['A']['deck'] if c.card_number == 'BT11-032')
        runtime.state.zones['A']['deck'].remove(card)
        runtime.state.zones['A']['security'].append(card)
        finish_turn(runtime, 'B', ROOT)
        pending = pending_options(runtime, 'B')
        self.assertEqual({p['effect_id'] for p in pending},
                         {'BT20-102.end_turn_rush_attack', 'BT22-023.end_turn_unsuspend'})
        chosen = next(p for p in pending if p['effect_id'] == 'BT20-102.end_turn_rush_attack')
        result = resolve_pending(runtime, 'B', chosen['id'],
                                 {'kind': 'DECLARE_ATTACK', 'attacker': attacker, 'target': 'PLAYER'})
        self.assertEqual(result['processing'], 'RUSH_AND_ATTACK_WITHOUT_SUSPENDING')
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        tracker = FieldTracker(context)
        tracker.start(runtime.snapshot())
        self.assertNotIn('deferred_depth', tracker.player_view('B')['attack'])
        raid = [p for p in runtime.state.pending if p['effect_id'] == 'BT20-102.raid_target']
        if raid:
            resolve_pending(runtime, 'B', raid[0]['id'], None)
        self.assertEqual([p['effect_id'] for p in runtime.state.pending],
                         ['BT22-023.end_turn_unsuspend'])
        self.assertEqual(pending_options(runtime, 'B'), [])
        choose_counter(runtime, 'A', None, ROOT)
        choose_blocker(runtime, 'A', None, ROOT)
        confirm_attack(runtime, 'B', ROOT)
        end_attack(runtime, 'B', ROOT)
        self.assertEqual([p['effect_id'] for p in pending_options(runtime, 'B')],
                         ['BT22-023.end_turn_unsuspend'])
        runtime.verify()
