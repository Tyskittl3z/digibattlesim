"""The actual checked Ulforce card uses security timing and printed DP."""
import copy
import gzip
import json
from pathlib import Path
import unittest

from attack_flow import confirm_attack, end_attack
from context_runtime import ContextRuntime, RuntimeHalt
from imported_attempts import _apply
from matchup_readiness import load_context_file
from selected_mechanics import build_selected_registry

ROOT=Path(__file__).resolve().parents[1]


class RecordedSecurityTests(unittest.TestCase):
    def recorded(self):
        path=ROOT/'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-0008.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,record['seed'],record['first'],
            build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        expected=copy.deepcopy(record['halts'][-1]['before']['state'])
        expected.setdefault('resolving_option',None)
        self.assertEqual(runtime.snapshot()['state'],expected)
        return runtime

    def test_actual_security_ulforce_does_not_activate_its_battle_area_effects(self):
        runtime=self.recorded()
        attacker=runtime.state.attack['attacker']
        checked=runtime.state.zones['B']['security'][-1].key
        self.assertEqual(checked,'B:EX13-023#2')
        before=len(runtime.state.zones['B']['security'])
        try:
            result=confirm_attack(runtime,'A',ROOT)
        except RuntimeHalt as exc:
            self.fail('Plain checked Digimon must use its DP at security timing: '+str(exc))
        self.assertTrue(result['attacker_deleted'])
        self.assertNotIn(attacker,runtime.state.battle['A'])
        self.assertIn(attacker,[c.key for c in runtime.state.zones['A']['trash']])
        self.assertIn(checked,[c.key for c in runtime.state.zones['B']['trash']])
        self.assertEqual(len(runtime.state.zones['B']['security']),before-1)
        self.assertEqual(runtime.state.memory,5)
        self.assertFalse(runtime.state.pending)
        self.assertFalse(runtime.state.terminal)
        end_attack(runtime,'A',ROOT)
        self.assertEqual(runtime.state.phase,'MAIN')
        runtime.verify()

    def test_actual_security_effect_is_still_not_silently_skipped(self):
        runtime=self.recorded()
        old=runtime.state.zones['B']['security'].pop()
        runtime.state.zones['B']['deck'].append(old)
        option=next(c for c in runtime.state.zones['B']['deck'] if c.card_number=='P-104')
        runtime.state.zones['B']['deck'].remove(option)
        runtime.state.zones['B']['security'].append(option)
        before=runtime.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'SECURITY_CARD_UNSUPPORTED'):
            confirm_attack(runtime,'A',ROOT)
        self.assertEqual(runtime.snapshot()['state'],before)


if __name__=='__main__':
    unittest.main()
