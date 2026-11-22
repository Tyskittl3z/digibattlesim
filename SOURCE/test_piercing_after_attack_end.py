"""Piercing resolves during attack processing, before the attack ends."""
import copy
import unittest

from attack_flow import confirm_attack, end_attack
from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class PiercingAfterAttackEndTests(unittest.TestCase):
    def test_piercing_check_uses_queued_battle_record_before_attack_end(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 24, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'END_OF_TURN'
        runtime.state.turn = 3
        attacker = stage(runtime, 'B', ['BT20-102'])
        defender = stage(runtime, 'A', ['BT12-029'], suspended=True)
        runtime.state.battle['B'][attacker].instance_id = 'entity-b'
        runtime.state.battle['A'][defender].instance_id = 'entity-a'
        card = next(c for c in runtime.state.zones['A']['deck'] if c.card_number == 'BT11-032')
        runtime.state.zones['A']['deck'].remove(card)
        runtime.state.zones['A']['security'].append(card)
        runtime.state.attack = {'attacker': attacker, 'attacker_instance': 'entity-b',
                                'target': defender, 'target_instance': 'entity-a',
                                'controller': 'B', 'defender': 'A', 'window': 'CONFIRM',
                                'counter_used': False, 'block_used': False,
                                'checked': None, 'deferred_depth': 0}
        battle = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(battle['battle_losers'], ['DEFENDER'])
        piercing = next(p for p in pending_options(runtime, 'B')
                        if p['effect_id'] == 'BT20-102.piercing_check')
        with self.assertRaisesRegex(RuntimeHalt, 'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            end_attack(copy.deepcopy(runtime), 'B', ROOT)
        before = len(runtime.state.zones['A']['security'])
        result = resolve_pending(runtime, 'B', piercing['id'], None)
        self.assertEqual(result['processing'], 'MANDATORY_PIERCING_SECURITY_CHECK')
        self.assertEqual(len(runtime.state.zones['A']['security']), before - 1)
        end_attack(runtime, 'B', ROOT)
        self.assertIsNone(runtime.state.attack)
        runtime.verify()
