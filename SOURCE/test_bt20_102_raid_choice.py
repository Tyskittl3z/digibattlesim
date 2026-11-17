"""BT20-102 Raid is an explicit choice before Counter timing."""
import unittest

from attack_flow import declare_attack,choose_counter,choose_blocker,confirm_attack,end_attack
from context_runtime import ContextRuntime
from effect_scheduler import pending_options, resolve_pending
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage


class RaidChoiceTests(unittest.TestCase):
    def test_player_attack_can_switch_to_highest_dp_unsuspended_digimon(self):
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,211,'B',build_selected_registry(context,ROOT),allow_experimental=True)
        runtime.state.phase='MAIN';runtime.state.turn=3;runtime.state.memory=3
        attacker=stage(runtime,'B',['BT20-102'])
        stack=runtime.state.battle['B'][attacker]
        stack.played_turn=1;stack.ready_since_turn=2
        target=stage(runtime,'A',['EX13-023'])
        stage(runtime,'A',['EX1-013'])
        declare_attack(runtime,'B',attacker,'PLAYER',ROOT)
        pending=pending_options(runtime,'B')
        self.assertEqual([effect['effect_id'] for effect in pending],['BT20-102.raid_target'])
        from raid_effect import raid_choices
        self.assertEqual(raid_choices(runtime,'B',attacker),[None,target])
        resolved=resolve_pending(runtime,'B',pending[0]['id'],target)
        self.assertEqual(resolved['target'],target)
        self.assertEqual(runtime.state.attack['target'],target)
        self.assertEqual(runtime.state.attack['window'],'COUNTER')
        runtime.verify()

    def test_raid_battle_deletion_processes_piercing_before_attack_end(self):
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,33,'B',build_selected_registry(context,ROOT),allow_experimental=True)
        runtime.state.phase='MAIN';runtime.state.turn=3;runtime.state.memory=3
        attacker=stage(runtime,'B',['BT20-102'])
        runtime.state.battle['B'][attacker].played_turn=1
        runtime.state.battle['B'][attacker].ready_since_turn=2
        target=stage(runtime,'A',['EX1-013'])
        deck=runtime.state.zones['A']['deck']
        checked=next(card for card in deck if card.card_number=='BT11-023')
        deck.remove(checked);runtime.state.zones['A']['security'].append(checked)
        declare_attack(runtime,'B',attacker,'PLAYER',ROOT)
        raid=pending_options(runtime,'B')[0]
        resolve_pending(runtime,'B',raid['id'],target)
        choose_counter(runtime,'A',None,ROOT)
        choose_blocker(runtime,'A',None,ROOT)
        battle=confirm_attack(runtime,'B',ROOT)
        self.assertEqual(battle['battle_losers'],['DEFENDER'])
        piercing=pending_options(runtime,'B')
        self.assertEqual([item['effect_id'] for item in piercing],['BT20-102.piercing_check'])
        result=resolve_pending(runtime,'B',piercing[0]['id'],None)
        self.assertEqual(result['checked_card'],checked.key)
        self.assertEqual(end_attack(runtime,'B',ROOT)['attack_ended'],True)
        runtime.verify()


if __name__=='__main__':unittest.main()
