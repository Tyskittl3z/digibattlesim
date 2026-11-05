"""Independent source-hashed audit of actual Ulforce implementation; ARTIFACTS only."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'SOURCE'))
import imported_attempts as ia
from context_runtime import ContextRuntime
from selected_mechanics import build_selected_registry
from match_context import canonical,digest
from effect_scheduler import pending_options,resolve_pending
from on_play_effects import on_play_choices,ON_PLAY_SPECS
from effect_grants import active_restriction,active_keyword
from tamer_play_effects import tamer_play_choices,ULFORCE_PLAY_EFFECT,ULFORCE_TAMER_EFFECT
OUT=Path(__file__).resolve().parent
RECORD='ARTIFACTS/gameplay-continuations-2026-11-03-07/game-0000-segment.json.gz'
source_paths=['SOURCE/tamer_play_effects.py','SOURCE/battle_evolution.py','SOURCE/test_tamer_play_effects.py',
              'SOURCE/main_actions.py','SOURCE/basic_event_dependencies.py','SOURCE/effect_scheduler.py',
              'SOURCE/selected_mechanics.py','SOURCE/effect_grants.py','SOURCE/context_runtime.py']
def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}
before_hashes=hashes()
r=json.loads(gzip.decompress((ROOT/RECORD).read_bytes()))
context,_,_=ia._load_context_selection(ROOT,r['replay_provenance']['context_file'],
    expected_context=(r['context_id'],r['replay_provenance']['context_file_sha256']))
rt=ContextRuntime(context,r['seed'],r['first'],build_selected_registry(context,ROOT),allow_experimental=True)
assert canonical(ia._physical_snapshot(rt.snapshot()))==canonical(ia._physical_snapshot(r['initial']))
rows=[];snapshots={};after_evolve=None
for n,c in enumerate(r['commands'][:-1],1):
    assert c['status']=='EXPERIMENTAL_RESOLVED'
    assert canonical(ia._comparable_public_view(rt.public_view(c['seat'])))==canonical(ia._comparable_public_view(c['public_view'])),n
    result=ia._apply(rt,c['command'],c['seat'],c['args'],ROOT)
    assert canonical(result)==canonical(c['result']),n
    rt.verify()
    snapshot=rt.snapshot()
    rows.append({'command':n,'public_view_match':True,'result_match':True,
                 'physical_integrity_valid':True,'state_sha256':digest(snapshot['state']),
                 'rng_sha256':digest(snapshot['rng_state'])})
    if n>=93:snapshots[n]=snapshot
    if n==94:after_evolve=copy.deepcopy(rt)
assert len(rows)==103
assert canonical(ia._physical_snapshot(rt.snapshot()))==canonical(ia._physical_snapshot(r['final']))
assert canonical(ia._physical_snapshot(rt.snapshot()))==canonical(ia._physical_snapshot(r['halts'][-1]['before']))
assert snapshots[94]['state']['memory']==-1
assert snapshots[94]['state']['battle']['A']['A:BT11-032#1']['instance_id']=='entity-9'
assert snapshots[94]['state']['zones']['A']['hand'][-1]=='A:BT11-112#3'
assert snapshots[95]['state']['memory']==-1
assert {p['effect_id'] for p in snapshots[95]['state']['pending']}=={ON_PLAY_SPECS['BT11-112'][0],ULFORCE_TAMER_EFFECT}
assert snapshots[97]['state']['once_used']==[]
assert snapshots[97]['state']['memory']==-1
assert snapshots[97]['state']['pending']==[]
assert snapshots[97]['state']['battle']['A']['A:BT11-032#1']['suspended'] is False
assert snapshots[98]['state']['turn']==8 and snapshots[98]['state']['active']=='B'
assert snapshots[98]['state']['memory']==1
assert snapshots[98]['state']['battle']['A']['A:BT11-032#1']['statuses']=={}
assert len(snapshots[97]['state']['battle']['A']['A:BT12-029#2']['statuses']['effect_grants'])==2
assert len(snapshots[98]['state']['battle']['A']['A:BT12-029#2']['statuses']['effect_grants'])==1
remaining=snapshots[98]['state']['battle']['A']['A:BT12-029#2']['statuses']['effect_grants'][0]
assert remaining['source']=='A:BT11-112#3'
assert remaining['expires']=={'turn':8,'controller':'B','boundary':'turn_end'}
source='A:BT11-032#1';rina='A:BT11-112#3';grant_effect=ON_PLAY_SPECS['BT11-112'][0]
p=pending_options(after_evolve,'A')[0]
assert p['effect_id']==ULFORCE_PLAY_EFFECT and p['usage']==[]
assert tamer_play_choices(after_evolve,'A',source,ULFORCE_PLAY_EFFECT)==[None,rina]
branch=copy.deepcopy(after_evolve);before_opt=set(branch.state.once_used)
resolve_pending(branch,'A',p['id'],None)
assert branch.state.once_used==before_opt and branch.state.memory==-1 and not branch.state.pending
resolve_pending(after_evolve,'A',p['id'],rina)
choices=on_play_choices(after_evolve,'A',rina)
assert choices==['A:BT11-032#1','A:BT12-029#2']
assert pending_options(after_evolve,'B')==[]
assert {p['depth'] for p in pending_options(after_evolve,'A')}=={1}
branches=[]
for target in choices:
    for order in ((grant_effect,ULFORCE_TAMER_EFFECT),(ULFORCE_TAMER_EFFECT,grant_effect)):
        branch=copy.deepcopy(after_evolve)
        initial_opt=set(branch.state.once_used);initial_rng=branch.snapshot()['rng_state']
        results=[]
        for effect in order:
            pending=next(p for p in pending_options(branch,'A') if p['effect_id']==effect)
            assert pending['usage']==[]
            result=resolve_pending(branch,'A',pending['id'],target if effect==grant_effect else None)
            results.append({'effect':effect,'result':result})
            if effect==ULFORCE_TAMER_EFFECT:
                assert result['changed'] is False and result['suspended_before'] is False and result['suspended_after'] is False
        assert branch.state.memory==-1 and branch.state.phase=='END_OF_TURN' and branch.state.pending==[]
        assert branch.state.once_used==initial_opt and branch.snapshot()['rng_state']==initial_rng
        assert active_restriction(branch,'A',source,'cannot_suspend')
        assert active_keyword(branch,'A',target,'Blocker') and active_keyword(branch,'A',target,'Evade')
        grant=next(g for g in branch.state.battle['A'][target].statuses['effect_grants'] if g['source']==rina)
        assert grant['expires']=={'turn':8,'controller':'B','boundary':'turn_end'}
        branch.verify()
        branches.append({'on_play_target':target,'processing_order':list(order),'results':results,
                         'no_actual_unsuspend_or_extra_triggers':True,'memory':-1,'once_used_unchanged':True,
                         'rng_unchanged':True,'original_restriction_preserved':True,'grant_expiry':grant['expires']})
manifest=[b.manifest() for b in rt.registry.bindings if b.card_number=='BT11-032']
assert {b['effect_id'] for b in manifest}=={ULFORCE_PLAY_EFFECT,ULFORCE_TAMER_EFFECT}
assert all(b['handler_module_sha256']==before_hashes['SOURCE/tamer_play_effects.py'] for b in manifest)
for binding in manifest:
    definition=context.card('A','BT11-032')
    assert binding['definition_sha256']==definition.definition_sha256
    assert binding['text_sha256']==hashlib.sha256(definition.effect_text('main_text').encode()).hexdigest()
index=json.loads((ROOT/'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json').read_text())['sources']
source_pins=[]
for sid in ('card-BT11-032','card-BT11-112','card-EX13-022','card-EX13-069','card-EX1-013','rules'):
    pin=next(x for x in index if x['id']==sid)
    assert hashlib.sha256((ROOT/pin['file']).read_bytes()).hexdigest()==pin['sha256']
    source_pins.append({k:pin[k] for k in ('id','file','url','sha256')})
assert before_hashes==hashes()
proof={'schema':'bt11-ulforce-implementation-independent-addendum-v1','date':'2026-11-03',
       'status':'NO_CONCRETE_DEFECT_FOUND_FOR_ACTUAL_SOURCE_CASE','certification':'NONE_EXPERIMENTAL_ENCOUNTER_REVIEW_ONLY',
       'full_match_credit':0,'accepted_fact_finding_credit':0,'final_evaluation_credit':0,'strategy_assessment':'NONE',
       'record':RECORD,'record_file_sha256':hashlib.sha256((ROOT/RECORD).read_bytes()).hexdigest(),
       'seed':r['seed'],'context_id':r['context_id'],'source_hashes_unchanged_during_audit':True,
       'reviewed_source_sha256':before_hashes,'source_files_edited':[],
       'independent_unit_test_execution':{'command':'python3 -m unittest test_tamer_play_effects.EncounteredUlforceBlueTamerTests -v',
           'cwd':'SOURCE','tests':3,'seconds':21.666,'result':'OK','exit_code':0,
           'note':'Observed independent tool execution; the worker-reported13-test run is separate and not claimed here.'},
       'source_assessment':[
           'BT11-032 exact WhenDigivolving line maps to source-bound PLAY_SPECS; no support is inferred for another card wording.',
           'Cost and stack placement precede actual bonus draw; only then is the WhenDigivolving effect queued. Choices inspect current own hand, filtered by Tamer type and Blue color.',
           'Optional play and mandatory own-blue-Tamer-play self-unsuspend have empty usage and no invented OPT consumption.',
           'Reaction collection requires observer ownership equal to the played Tamer owner, active YourTurn timing and Blue Tamer color; it reads only active main/inherited fields.',
           'Rina OnPlay and Ulforce self-unsuspend are queued together by the shared actual-play procedure, at the same derived depth, retaining explicit next-effect order.',
           'Mandatory self-unsuspend accepts only the no-target command None; False is rejected transactionally. Shared orientation procedure skips changes/reactions when already unsuspended.',
           'A future actual false->true suspension or true->false unsuspension requires its real observers. BT11 own bounce is unimplemented, so a genuine new Ulforce unsuspend still HALTs precisely before orientation mutation; this is a software dependency, not an illegality ruling.'
       ],
       'actual_new_commands':{'range':'94-98','evolution_cost':4,'memory_path':[3,-1],
           'bonus_draw':'A:BT11-112#3','play_selected':True,'played_card':'A:BT11-112#3','play_cost':0,
           'selected_simultaneous_order':[grant_effect,ULFORCE_TAMER_EFFECT],
           'selected_grant_target':'A:BT12-029#2','grant_expiry':remaining['expires'],
           'self_unsuspend_changed':False,'new_opt_uses':[],'extra_unsuspend_memory_draw_bounce':False,
           'actual_turn7_end':{'expired_original_restrictions':True,'expired_old_B_blocker_evade':True,
                              'new_Rina_grant_retained_through_B_turn8':True}},
       'targeted_actual_state_branches':{'explicit_free_play_decline_verified':True,'on_play_targets':choices,
           'both_orders_for_each_actual_target':branches,'case_count':len(branches)},
       'new_record_prefix_replay':{'successful_commands':len(rows),'all_saved_public_views_and_results_match':True,
           'all_commands_verify_108_card_conservation':True,'final_physical_and_rng_exact':True,
           'final_state_sha256':digest(rt.snapshot()['state']),'final_rng_sha256':digest(rt.snapshot()['rng_state']),
           'new_command104_not_executed':True,'per_command':rows},
       'bindings':manifest,'official_source_hashes':source_pins,
       'limits':'Only actual encountered Ulforce play/unsuspend behavior reviewed. Current new EX13-023 halt, future bounce resolution, complete-game validity, branch completeness and strategy remain outside this addendum.'}
(OUT/'bt11-ulforce-implementation-addendum.json').write_text(json.dumps(proof,indent=2)+'\n')
md='''# Ulforce implementation addendum

**No concrete defect found for the actual saved Ulforce interaction.** Independently ran the new EncounteredUlforceBlueTamerTests class: **3 tests passed,21.666s**. The reviewed source hashes remained unchanged during this audit; both BT11 bindings match the pinned card definition, main-text hash and official-source evidence.

Read new bindings in tamer_play_effects.py and battle_evolution.py with the shared play, pending-effect, orientation, grant and transaction procedures. WhenDigivolving queues only after the real bonus draw; optional free play filters own current-hand Blue Tamers. The observer requires the played card's owner, that owner's YourTurn and Blue color. Both effects have no printed OPT. Mandatory self-unsuspend accepts no decline and uses the existing orientation procedure, which emits no change or reaction for an already-unsuspended Digimon. Future true unsuspend still stops precisely at the unimplemented own bounce dependency before state mutation.

The actual saved segment07 now records the expected path: cost4 takes3→−1; draw Rina#3; play her for0; choose her OnPlay grant first targeting A:BT12-029#2; then process Ulforce's mandatory no-change unsuspend. No memory, Draw, bounce or OPT use was invented. Actual Aturn7 completion removes the old restrictions and old BBlocker/Evade, while the new Rina grant remains through Bturn8 end.

Independently verified the optional decline and **four branches** covering both simultaneous orders for each of the two actual Rina targets. Every branch preserves memory−1, RNG, unused OPT and entity-9's existing restriction; every new grant expires at actual Bturn8 end. Replayed all**103** successful commands of the newly saved segment with exact public views/results,108-card conservation after every action and exact final physical state/RNG. Command104 was not executed by this audit.

Full source hashes, binding manifests, branch results, source pins and replay hashes: [bt11-ulforce-implementation-addendum.json](bt11-ulforce-implementation-addendum.json). The earlier phase review was clarified: all A cards were already unsuspended at its turn7 unsuspend phase, so no actual orientation change occurred there; genuine normal-phase unsuspension can trigger the appropriate observers.

No SOURCE edits; this remains experimental encounter evidence with **zero complete-match, strategic-lane or final-evaluation credit**. The next EX13-023 stop and future bounce implementation are outside this addendum.
'''
(OUT/'bt11-ulforce-implementation-addendum.md').write_text(md)
print(json.dumps({'review':'bt11-ulforce-implementation-addendum.json','source_hashes_stable':True,
                  'independent_new_class_tests_passed':3,'actual_state_branches':len(branches),
                  'saved_successful_commands_replayed':len(rows),'exact_final_physical_rng':True,
                  'source_edits':[]},indent=2))
