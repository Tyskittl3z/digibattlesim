import unittest

from context_runtime import ContextRuntime, RuntimeHalt
from effect_scheduler import queue_effects, pending_options, resolve_pending
from test_context_runtime import context_with_effect, registry, put_source, gain_memory, corrupt_then_fail


class SchedulerTests(unittest.TestCase):
    def runtime(self):
        c=context_with_effect()
        return ContextRuntime(c,71,'A',registry(c),allow_experimental=True)

    def effect(self,source,seat='A'):
        return {'seat':seat,'source':source,'effect_id':'test-effect','field':'main_text',
                'trigger':{'kind':'SOFTWARE_TEST_EVENT'}}

    def test_pending_requires_explicit_controller_choice(self):
        r=self.runtime(); source=put_source(r)
        queue_effects(r,[self.effect(source)])
        self.assertEqual(r.state.memory,0)
        opts=pending_options(r,'A');self.assertEqual(len(opts),1)
        self.assertEqual(pending_options(r,'B'),[])
        resolve_pending(r,'A',opts[0]['id'],'activate')
        self.assertEqual(r.state.memory,1);self.assertEqual(r.state.pending,[])
        self.assertEqual(r.events[-1]['pending_id'],opts[0]['id'])

    def test_handler_receives_validated_pending_proof_only_during_activation(self):
        import copy
        def capture_pending(runtime,seat,source,choice):
            return {'proof':copy.deepcopy(runtime._activated_pending)}
        c=context_with_effect()
        r=ContextRuntime(c,71,'A',registry(c,capture_pending),allow_experimental=True)
        source=put_source(r);queue_effects(r,[self.effect(source)])
        selected=pending_options(r,'A')[0]
        result=resolve_pending(r,'A',selected['id'],None)
        self.assertEqual(result['proof'],selected)
        self.assertFalse(hasattr(r,'_activated_pending'))
        self.assertEqual(r.dispatch('test-effect','A',source,None)['proof'],None)
        self.assertFalse(hasattr(r,'_activated_pending'))

    def test_direct_dispatch_cannot_bypass_pending_choice(self):
        r=self.runtime(); source=put_source(r);queue_effects(r,[self.effect(source)])
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PENDING_EFFECTS_REQUIRE_RESOLUTION'):
            r.dispatch('test-effect','A',source,'activate')
        self.assertEqual(before,r.snapshot()['state'])

    def test_source_leave_and_reentry_cannot_reuse_pending_effect(self):
        r=self.runtime();source=put_source(r);queue_effects(r,[self.effect(source)])
        old=r.state.battle['A'].pop(source)
        from context_runtime import Stack
        r.state.battle['A'][source]=Stack(list(old.cards))
        self.assertEqual(pending_options(r,'A'),[])
        before=r.state.memory
        resolve_pending(r,'A','stale','activate')
        self.assertEqual(r.state.memory,before)
        self.assertEqual(r.state.pending,[])
        self.assertTrue(any(e['type']=='PENDING_CANCELLED' for e in r.events))

    def test_ids_and_pending_snapshots_are_deterministic_and_detached(self):
        a,b=self.runtime(),self.runtime()
        for r in (a,b):
            source=put_source(r);queue_effects(r,[self.effect(source),self.effect(source)])
        self.assertEqual(a.snapshot(),b.snapshot())
        choices=pending_options(a,'A');self.assertEqual(len({e['id'] for e in choices}),2)
        choices[0]['trigger']['kind']='tampered'
        self.assertEqual(a.state.pending[0]['trigger']['kind'],'SOFTWARE_TEST_EVENT')

    def test_derived_group_precedes_older_sibling_and_can_belong_to_nonturn_player(self):
        # Queue shape uses real bindings at both seats by using an A definition
        # in both validated deck seats, rather than fabricating unknown handlers.
        c=context_with_effect()
        from match_context import MatchContext
        c=MatchContext.create(c.deck_a,c.deck_a,{x.number:x for x in c.cards},c.to_dict()['rules'])
        r=ContextRuntime(c,71,'A',registry(c),allow_experimental=True)
        a=put_source(r); b=put_source(r,'B')
        queue_effects(r,[self.effect(a),self.effect(b,'B')])
        self.assertEqual(len(pending_options(r,'A')),1);self.assertEqual(pending_options(r,'B'),[])
        r._resolution_depth=0
        queue_effects(r,[self.effect(b,'B')]);del r._resolution_depth
        self.assertEqual(pending_options(r,'A'),[])
        options=pending_options(r,'B');self.assertEqual(len(options),1)
        self.assertEqual(options[0]['depth'],1)

    def test_wrong_effect_or_id_cannot_resolve_another_pending_source(self):
        r=self.runtime();source=put_source(r);queue_effects(r,[self.effect(source)])
        before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'PENDING_CHOICE_INVALID'):
            resolve_pending(r,'B',r.state.pending[0]['id'],'activate')
        self.assertEqual(before,r.snapshot()['state'])

    def test_failed_pending_command_preserves_exact_requested_id(self):
        r=self.runtime();source=put_source(r);queue_effects(r,[self.effect(source)])
        with self.assertRaisesRegex(RuntimeHalt,'PENDING_CHOICE_INVALID'):
            resolve_pending(r,'A','UNIQUE_WRONG_ID',None)
        self.assertEqual(r.events[-1]['pending_id'],'UNIQUE_WRONG_ID')
        c=context_with_effect();r=ContextRuntime(c,71,'A',registry(c,corrupt_then_fail),allow_experimental=True)
        source=put_source(r);queue_effects(r,[self.effect(source)])
        effect=pending_options(r,'A')[0];before=r.snapshot()['state']
        with self.assertRaisesRegex(RuntimeHalt,'UNRESOLVED_DEPENDENT_EFFECT'):
            resolve_pending(r,'A',effect['id'],'activate')
        self.assertEqual(r.events[-1]['pending_id'],effect['id'])
        self.assertEqual(before,r.snapshot()['state'])


if __name__=='__main__':unittest.main()
