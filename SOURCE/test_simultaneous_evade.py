"""A tied battle offers each EX13-023 controller an Evade choice."""
import copy
import unittest

from attack_flow import confirm_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class SimultaneousEvadeTests(unittest.TestCase):
    def test_turn_player_then_defender_each_choose(self):
        context = load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 28, 'B', build_selected_registry(context, ROOT),
                                 allow_experimental=True)
        runtime.state.phase = 'MAIN'
        runtime.state.turn = 3
        attacker = stage(runtime, 'B', ['EX13-023'])
        defender = stage(runtime, 'A', ['EX13-023'])
        runtime.state.battle['B'][attacker].instance_id = 'entity-attacker'
        runtime.state.battle['A'][defender].instance_id = 'entity-defender'
        # A card effect has declared this battle without suspending its attacker.
        # Both Digimon are therefore able to pay Evade on a tie.
        runtime.state.attack = {'attacker': attacker,
                                'attacker_instance': runtime.state.battle['B'][attacker].instance_id,
                                'target': defender,
                                'target_instance': runtime.state.battle['A'][defender].instance_id,
                                'controller': 'B', 'defender': 'A', 'window': 'CONFIRM',
                                'counter_used': False, 'block_used': False, 'checked': None}
        offered = confirm_attack(runtime, 'B', ROOT)
        self.assertEqual(offered['processing'], 'EVADE_CHOICE_PENDING')
        first = pending_options(runtime, 'B')
        self.assertEqual([p['effect_id'] for p in first], ['EX13-023.evade'])
        self.assertEqual(first[0]['source'], attacker)
        protected_first = copy.deepcopy(runtime)
        yes_first = resolve_pending(protected_first, 'B', first[0]['id'], True)
        self.assertTrue(yes_first['prevented_deletion'])
        self.assertIn(defender, protected_first.state.battle['A'])
        self.assertTrue(any(p['effect_id'] == 'EX13-023.evade' and p['seat'] == 'A'
                            for p in protected_first.state.pending))
        no = resolve_pending(runtime, 'B', first[0]['id'], False)
        self.assertFalse(no['prevented_deletion'])
        second = pending_options(runtime, 'A')
        self.assertEqual([p['effect_id'] for p in second], ['EX13-023.evade'])
        self.assertEqual(second[0]['source'], defender)
        both_decline = copy.deepcopy(runtime)
        resolve_pending(both_decline, 'A', second[0]['id'], False)
        self.assertNotIn(attacker, both_decline.state.battle['B'])
        self.assertNotIn(defender, both_decline.state.battle['A'])
        yes = resolve_pending(runtime, 'A', second[0]['id'], True)
        self.assertTrue(yes['prevented_deletion'])
        self.assertNotIn(attacker, runtime.state.battle['B'])
        self.assertIn(defender, runtime.state.battle['A'])
        self.assertTrue(runtime.state.battle['A'][defender].suspended)
        runtime.verify()
