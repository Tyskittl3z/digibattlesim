"""Encountered Game 0000 attack; this fixture is not a completed match."""
import gzip
import json
import unittest

from attack_flow import declare_attack
from attack_flow import _dp
from context_runtime import ContextRuntime
from effect_grants import active_keyword
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry
from test_selected_mechanics import ROOT


class RinaJammingAttackTests(unittest.TestCase):
    def saved_attack(self):
        path = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0003.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        self.assertEqual(runtime.snapshot()['rng_state'], record['commands'][-1]['before']['rng_state'])
        return runtime, record['commands'][-1]

    def test_encountered_attack_queues_rina_choice_without_changing_saved_selection(self):
        runtime, saved = self.saved_attack()
        result = _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        self.assertEqual(result['attacker'], 'B:EX13-022#2')
        self.assertEqual(result['target'], 'A:EX1-013#1')
        offered = [p for p in pending_options(runtime, 'B')
                   if p['effect_id'] == 'BT22-085.attack_jamming']
        self.assertEqual(len(offered), 1)
        self.assertEqual(offered[0]['source'], 'B:BT22-085#2')
        self.assertFalse(active_keyword(runtime, 'B', result['attacker'], 'Jamming'))

    def test_explicit_decline_preserves_tamer_and_grants_nothing(self):
        runtime, saved = self.saved_attack()
        _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        effect = next(p for p in pending_options(runtime, 'B')
                      if p['effect_id'] == 'BT22-085.attack_jamming')
        resolve_pending(runtime, 'B', effect['id'], None)
        self.assertIn(effect['source'], runtime.state.battle['B'])
        self.assertFalse(active_keyword(runtime, 'B', saved['args']['attacker'], 'Jamming'))

    def test_pay_return_to_hand_grants_attacker_jamming_for_turn(self):
        runtime, saved = self.saved_attack()
        _apply(runtime, saved['command'], saved['seat'], saved['args'], ROOT)
        effect = next(p for p in pending_options(runtime, 'B')
                      if p['effect_id'] == 'BT22-085.attack_jamming')
        resolve_pending(runtime, 'B', effect['id'], effect['source'])
        self.assertNotIn(effect['source'], runtime.state.battle['B'])
        self.assertIn(effect['source'], [c.key for c in runtime.state.zones['B']['hand']])
        self.assertTrue(active_keyword(runtime, 'B', saved['args']['attacker'], 'Jamming'))
        runtime.verify()

    def test_saved_confirmation_uses_live_dp_bonus(self):
        path = ROOT / 'ARTIFACTS/fresh-game-0000-2026-11-11/game-0000-segment-0008.json.gz'
        record = json.loads(gzip.decompress(path.read_bytes()))
        context = load_context_file(ROOT / record['context_file'])
        runtime = ContextRuntime(context, record['seed'], record['first'],
                                 build_selected_registry(context, ROOT), allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime, command['command'], command['seat'], command['args'], ROOT)
        self.assertEqual(runtime.snapshot()['state'], record['commands'][-1]['before']['state'])
        attacker = record['commands'][-1]['before']['state']['attack']['attacker']
        self.assertEqual(_dp(runtime, 'B', runtime.state.battle['B'][attacker]), 10000)
        result = _apply(runtime, 'CONFIRM_ATTACK', 'B', {}, ROOT)
        self.assertEqual(result['battle_losers'], ['DEFENDER'])
        self.assertNotIn('A:EX1-013#1', runtime.state.battle['A'])


if __name__ == '__main__':
    unittest.main()
