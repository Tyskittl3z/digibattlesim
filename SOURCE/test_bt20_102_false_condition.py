"""Q4725 keeps BT20-102's Then clause after an unmet If."""
import unittest

from context_runtime import ContextRuntime
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT, stage
from effect_scheduler import pending_options, resolve_pending
from battle_evolution import choose_battle_evolution


class OmnimonConditionalDigivolveTests(unittest.TestCase):
    def test_x_antibody_in_a_longer_name_does_not_satisfy_exact_bracket_name(self):
        # Comprehensive Rules v4.3 2-3-1-2/3 distinguishes [X Antibody]
        # from "with [X Antibody] in its name". BT12-029 qualifies only
        # for that longer-name wording.
        context=load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,182,'B',build_selected_registry(context,ROOT),allow_experimental=True)
        runtime.state.phase='MAIN';runtime.state.turn=4;runtime.state.memory=6
        source=stage(runtime,'B',['BT12-029'])
        target=stage(runtime,'A',['EX1-013'])
        hand=next(card for card in runtime.state.zones['B']['deck'] if card.card_number=='BT20-102')
        runtime.state.zones['B']['deck'].remove(hand);runtime.state.zones['B']['hand'].append(hand)
        result=choose_battle_evolution(runtime,'B',source,hand.key,0,ROOT)
        self.assertEqual(result['triggered_effects'],['BT20-102.on_play_digivolving'])
        pending=pending_options(runtime,'B')
        self.assertEqual(len(pending),1)
        resolved=resolve_pending(runtime,'B',pending[0]['id'],target)
        self.assertEqual(resolved['returned'],target)
        self.assertEqual(runtime.state.zones['A']['deck'][0].key,target)
        runtime.verify()

    def test_q4725_then_return_remains_mandatory_when_if_clause_is_false(self):
        context=load_context_file(ROOT / 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,181,'B',build_selected_registry(context,ROOT),allow_experimental=True)
        runtime.state.phase='MAIN';runtime.state.turn=4;runtime.state.memory=6
        source=stage(runtime,'B',['EX13-023'])
        target=stage(runtime,'A',['EX1-013'])
        hand=next(card for card in runtime.state.zones['B']['deck'] if card.card_number=='BT20-102')
        runtime.state.zones['B']['deck'].remove(hand);runtime.state.zones['B']['hand'].append(hand)
        result=choose_battle_evolution(runtime,'B',source,hand.key,0,ROOT)
        self.assertEqual(result['triggered_effects'],['BT20-102.on_play_digivolving'])
        pending=pending_options(runtime,'B')
        self.assertEqual(len(pending),1)
        resolved=resolve_pending(runtime,'B',pending[0]['id'],target)
        self.assertEqual(resolved['returned'],target)
        self.assertEqual(runtime.state.zones['A']['deck'][0].key,target)
        runtime.verify()

if __name__ == '__main__':
    unittest.main()
