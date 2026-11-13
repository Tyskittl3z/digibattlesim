import unittest
import gzip
import json
from unittest.mock import patch

from context_runtime import ContextRuntime,RuntimeHalt
from effect_scheduler import pending_options,resolve_pending
from selected_mechanics import build_selected_registry,ORIENTATION_EFFECT
from test_selected_mechanics import selected_context,stage,ROOT


class ReactionTests(unittest.TestCase):
    def runtime(self):
        c=selected_context()
        return ContextRuntime(c,321,'A',build_selected_registry(c,ROOT),allow_experimental=True)

    def test_suspend_then_explicit_inherited_unsuspend_then_memory_reaction(self):
        r=self.runtime();source=stage(r,'A',['P-138','EX13-022','EX13-023'])
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        self.assertTrue(r.state.battle['A'][source].suspended)
        first=pending_options(r,'A');self.assertEqual(len(first),1)
        self.assertEqual(first[0]['effect_id'],'EX13-022.inherited_unsuspend')
        resolve_pending(r,'A',first[0]['id'],True)
        self.assertFalse(r.state.battle['A'][source].suspended)
        memory=pending_options(r,'A');self.assertEqual(len(memory),1)
        self.assertEqual(memory[0]['effect_id'],'P-138.unsuspend_memory')
        self.assertEqual(memory[0]['depth'],1)
        self.assertEqual(r.state.memory,0)
        resolve_pending(r,'A',memory[0]['id'],None)
        self.assertEqual(r.state.memory,1);self.assertEqual(r.state.pending,[])
        self.assertEqual(r.matches_played,0)

    def test_optional_inherited_unsuspend_is_not_automatically_activated(self):
        r=self.runtime();source=stage(r,'A',['EX13-022','EX13-023'])
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        pending=pending_options(r,'A')[0]
        resolve_pending(r,'A',pending['id'],False)
        self.assertTrue(r.state.battle['A'][source].suspended)
        self.assertEqual(r.state.pending,[])
        self.assertEqual(len(r.state.once_used),2)

    def test_two_sources_are_independently_pending_and_controller_chooses_order(self):
        r=self.runtime();source=stage(r,'A',['P-138','P-138','EX13-023'],suspended=True)
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        opts=pending_options(r,'A');self.assertEqual(len(opts),2)
        self.assertNotEqual(opts[0]['source'],opts[1]['source'])
        resolve_pending(r,'A',opts[1]['id'],None)
        self.assertEqual(r.state.memory,1)
        resolve_pending(r,'A',pending_options(r,'A')[0]['id'],None)
        self.assertEqual(r.state.memory,2)

    def test_your_turn_and_main_phase_are_trigger_conditions(self):
        for active,phase,want in [('A','MAIN',1),('A','DRAW',0),('B','MAIN',0)]:
            r=self.runtime();r.state.active=active;r.state.phase=phase
            source=stage(r,'A',['EX1-013','EX13-023'],suspended=True)
            r.dispatch(ORIENTATION_EFFECT,'A',source,source)
            self.assertEqual(len(r.state.pending),want)

    def test_bt22_processing_condition_checked_at_activation(self):
        r=self.runtime();source=stage(r,'A',['BT22-023','EX13-023'])
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        self.assertEqual(len(r.state.pending),1)
        resolve_pending(r,'A',pending_options(r,'A')[0]['id'],True)
        self.assertTrue(r.state.battle['A'][source].suspended)
        self.assertEqual(r.events[-1]['result']['processing'],'BLUE_TAMER_CONDITION_FAILED')

    def test_bt22_can_unsuspend_with_blue_tamer_that_has_no_orientation_reaction(self):
        r=self.runtime();source=stage(r,'A',['BT22-023','EX13-023']);stage(r,'A',['BT22-085'])
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        resolve_pending(r,'A',pending_options(r,'A')[0]['id'],True)
        self.assertFalse(r.state.battle['A'][source].suspended)

    def test_memory_caps_and_no_phantom_reactions_from_prohibited_change(self):
        r=self.runtime();r.state.memory=10
        source=stage(r,'A',['P-138','EX13-023'],suspended=True)
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        resolve_pending(r,'A',pending_options(r,'A')[0]['id'],None)
        self.assertEqual(r.state.memory,10)
        r=self.runtime();source=stage(r,'A',['P-138','EX13-023'],suspended=True)
        r.state.battle['A'][source].statuses['cannot_unsuspend']=True
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        self.assertEqual(r.state.pending,[])

    def test_invalid_optional_choice_preserves_pending_effect_and_board(self):
        r=self.runtime();source=stage(r,'A',['EX13-022','EX13-023'])
        r.dispatch(ORIENTATION_EFFECT,'A',source,source)
        effect=pending_options(r,'A')[0];before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'BOOLEAN_PROCESSING_CHOICE'):
            resolve_pending(r,'A',effect['id'],'yes')
        self.assertEqual(before,r.snapshot()['state'])

    def test_tamer_orientation_does_not_trigger_digimon_observers_or_later_cost_words(self):
        from selected_mechanics import _set_orientation
        r=self.runtime();r.state.phase='END_OF_TURN'
        tamer=stage(r,'A',['EX13-069'],suspended=True)
        stage(r,'A',['BT11-112']);stage(r,'A',['EX13-022'])
        result=_set_orientation(r,'A',r.state.battle['A'][tamer],False)
        self.assertTrue(result['changed']);self.assertEqual(r.state.pending,[])
        result=_set_orientation(r,'A',r.state.battle['A'][tamer],True)
        self.assertTrue(result['changed']);self.assertEqual(r.state.pending,[]);r.verify()

    def test_bt12_self_unsuspend_queues_its_registered_return(self):
        from selected_mechanics import _set_orientation
        r=self.runtime();source=stage(r,'A',['BT12-029'],suspended=True)
        result=_set_orientation(r,'A',r.state.battle['A'][source],False)
        self.assertTrue(result['changed'])
        self.assertFalse(r.state.battle['A'][source].suspended)
        self.assertTrue(any(p['effect_id']=='BT12-029.unsuspend_return_lowest'
            for p in pending_options(r,'A')))


class EncounteredEndUnsuspendTests(unittest.TestCase):
    def actual(self):
        from imported_attempts import _apply
        from matchup_readiness import load_context_file
        path=ROOT/'ARTIFACTS/gameplay-continuations-2026-11-03-05/game-0000-segment.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        context=load_context_file(ROOT/record['replay_provenance']['context_file'])
        r=ContextRuntime(context,record['seed'],record['first'],
                         build_selected_registry(context,ROOT),allow_experimental=True)
        for command in record['commands'][:-1]:
            _apply(r,command['command'],command['seat'],command['args'],ROOT)
        self.assertEqual(r.snapshot()['state'],record['halts'][-1]['before']['state'])
        self.assertEqual(r.snapshot()['rng_state'],record['halts'][-1]['before']['rng_state'])
        return r,record['commands'][-1]['args']

    def test_saved_end_choice_unsuspends_only_selected_aero_and_queues_three_rinas_together(self):
        import selected_mechanics
        r,args=self.actual();target=args['choice']
        self.assertEqual((r.state.turn,r.state.active,r.state.phase,r.state.memory),
                         (6,'B','END_OF_TURN',-3))
        before=r.snapshot()
        with patch('selected_mechanics.queue_effects',wraps=selected_mechanics.queue_effects) as queue:
            result=resolve_pending(r,'B',args['pending_id'],target)
        self.assertTrue(result['changed']);self.assertFalse(r.state.battle['B'][target].suspended)
        self.assertTrue(r.state.battle['B']['B:EX13-022#1'].suspended)
        self.assertEqual(queue.call_count,1)
        options=pending_options(r,'B')
        self.assertEqual({(e['source'],e['effect_id']) for e in options},
                         {('B:BT11-112#3','BT11-112.unsuspend_memory'),
                          ('B:EX13-069#3','EX13-069.unsuspend_draw'),
                          ('B:EX13-069#4','EX13-069.unsuspend_draw')})
        self.assertEqual({e['depth'] for e in options},{1})
        self.assertEqual(pending_options(r,'A'),[])
        self.assertEqual(r.state.memory,-3)
        self.assertEqual(r.snapshot()['rng_state'],before['rng_state'])
        memory=next(e for e in options if e['effect_id']=='BT11-112.unsuspend_memory')
        resolve_pending(r,'B',memory['id'],None)
        self.assertEqual(r.state.memory,-2)
        while r.state.pending:
            resolve_pending(r,'B',pending_options(r,'B')[0]['id'],False)
        self.assertEqual(r.state.phase,'END_OF_TURN');r.verify()


if __name__=='__main__':unittest.main()
