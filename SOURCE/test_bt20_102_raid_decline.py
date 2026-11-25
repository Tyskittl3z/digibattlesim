"""An explicit player attack may decline optional Raid (rule 16-23-3)."""
import unittest

from attack_flow import declare_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options,resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT,stage


class RaidDeclineTests(unittest.TestCase):
    def test_player_target_stays_player_after_explicit_decline_with_unsuspended_enemy(self):
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime = ContextRuntime(context, 17, 'B',
            build_selected_registry(context, ROOT), allow_experimental=True)
        runtime.state.phase='MAIN';runtime.state.turn=3;runtime.state.memory=3
        attacker=stage(runtime,'B',['BT20-102'])
        runtime.state.battle['B'][attacker].played_turn=1
        runtime.state.battle['B'][attacker].ready_since_turn=2
        stage(runtime,'A',['EX1-013'])
        declare_attack(runtime,'B',attacker,'PLAYER',ROOT)
        pending=pending_options(runtime,'B')
        self.assertEqual(len(pending),1)
        result = resolve_pending(runtime, 'B', pending[0]['id'], None)
        self.assertEqual(result['processing'],'OPTIONAL_RAID_DECLINED')
        self.assertEqual(runtime.state.attack['target'], 'PLAYER')
        self.assertEqual(runtime.state.attack['window'], 'COUNTER')
        runtime.verify()


if __name__ == '__main__':
    unittest.main()
