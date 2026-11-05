"""Two actual plays blocked only because unrelated stacks existed."""
import copy
import gzip
import json
from pathlib import Path
import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import pending_options, resolve_pending
from imported_attempts import _apply
from matchup_readiness import load_context_file
from search_effects import search_choices
from selected_mechanics import build_selected_registry

ROOT=Path(__file__).resolve().parents[1]


class RecordedStackPlayTests(unittest.TestCase):
    def actual(self,index):
        path=ROOT/f'ARTIFACTS/ulforce-bootstrap-diagnostic-2026-11-02-02/attempt-{index:04d}.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context=load_context_file(ROOT/'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json')
        runtime=ContextRuntime(context,record['seed'],record['first'],
            build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(runtime,command['command'],command['seat'],command['args'],ROOT)
        expected=copy.deepcopy(record['halts'][-1]['before']['state'])
        expected.setdefault('resolving_option',None)
        self.assertEqual(runtime.snapshot()['state'],expected)
        return runtime,record['commands'][-1]

    def test_actual_digimon_plays_do_not_trigger_unrelated_tamer_or_orientation_effects(self):
        for index in (2,52):
            with self.subTest(index=index):
                runtime,command=self.actual(index)
                before_memory=runtime.state.memory
                before_board=copy.deepcopy(runtime.snapshot()['state']['battle'])
                try:
                    result=_apply(runtime,'PLAY_CARD',command['seat'],command['args'],ROOT)
                except RuntimeHalt as exc:
                    self.fail('Actual Digimon play with unrelated inherited text is legal: '+str(exc))
                self.assertEqual(runtime.state.memory,before_memory-result['cost'])
                source=command['args']['hand_key']
                for owner,stacks in before_board.items():
                    for key,old in stacks.items():
                        self.assertEqual(runtime.snapshot()['state']['battle'][owner][key],old)
                pending=pending_options(runtime,command['seat'])
                if index==2:
                    self.assertEqual([p['effect_id'] for p in pending],['BT11-023.on_play_search'])
                    choices=search_choices(runtime,command['seat'],source)
                    selected=choices['selections'][0]
                    bottom=[k for k in choices['revealed'] if k not in selected]
                    resolve_pending(runtime,command['seat'],pending[0]['id'],
                        {'selected':selected,'bottom_order':bottom})
                else:
                    self.assertEqual(pending,[])
                self.assertEqual(runtime.state.memory,before_memory-result['cost'])
                runtime.verify()


if __name__=='__main__':
    unittest.main()
