"""Reproduce the independent read-only saved-prefix proof; writes ARTIFACTS only."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'SOURCE'))
import imported_attempts as ia
from context_runtime import ContextRuntime
from match_context import canonical, digest
from selected_mechanics import build_selected_registry

OUT = Path(__file__).resolve().parent
RECORD = 'ARTIFACTS/gameplay-continuations-2026-11-03-06/game-0000-segment.json.gz'
CONTEXT = 'ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'
INDEX = 'RULES/matchups/123129-vs-124303/SOURCE_INDEX.json'
r = json.loads(gzip.decompress((ROOT / RECORD).read_bytes()))
context, _, _ = ia._load_context_selection(
    ROOT, r['replay_provenance']['context_file'],
    expected_context=(r['context_id'], r['replay_provenance']['context_file_sha256']))
rt = ContextRuntime(context, r['seed'], r['first'],
                    build_selected_registry(context, ROOT), allow_experimental=True)
assert canonical(ia._physical_snapshot(rt.snapshot())) == canonical(ia._physical_snapshot(r['initial']))
rows = []
observations = {}
for number, command in enumerate(r['commands'][:-1], 1):
    assert command['status'] == 'EXPERIMENTAL_RESOLVED'
    assert canonical(ia._comparable_public_view(rt.public_view(command['seat']))) == canonical(
        ia._comparable_public_view(command['public_view'])), number
    result = ia._apply(rt, command['command'], command['seat'], command['args'], ROOT)
    assert canonical(result) == canonical(command['result']), number
    rt.verify()
    snapshot = rt.snapshot()
    rows.append({'command_number': number, 'command': command['command'],
                 'saved_public_view_match': True, 'saved_result_match': True,
                 'physical_integrity_valid': True, 'state_sha256': digest(snapshot['state']),
                 'rng_sha256': digest(snapshot['rng_state'])})
    if number >= 82:
        observations[number] = snapshot['state']
final = rt.snapshot()
assert len(rows) == 93
assert canonical(ia._physical_snapshot(final)) == canonical(ia._physical_snapshot(r['final']))
assert canonical(ia._physical_snapshot(final)) == canonical(ia._physical_snapshot(r['halts'][-1]['before']))
assert observations[83]['battle']['B']['B:EX13-022#3']['suspended'] is False
assert observations[83]['memory'] == -3
assert sorted(x['effect_id'] for x in observations[83]['pending']) == sorted([
    'BT11-112.unsuspend_memory', 'EX13-069.unsuspend_draw', 'EX13-069.unsuspend_draw'])
assert observations[84]['memory'] == -2
for n in (85, 86):
    assert observations[n]['zones']['B']['hand'] == observations[84]['zones']['B']['hand']
    assert observations[n]['battle']['B']['B:EX13-069#3']['suspended'] is False
    assert observations[n]['battle']['B']['B:EX13-069#4']['suspended'] is False
assert observations[87]['turn'] == 7 and observations[87]['active'] == 'A'
assert observations[87]['memory'] == 2 and observations[87]['once_used'] == []
assert len(observations[86]['battle']['B']['B:EX13-022#3']['statuses']['effect_grants']) == 2
assert len(observations[87]['battle']['B']['B:EX13-022#3']['statuses']['effect_grants']) == 1
assert observations[87]['battle']['B']['B:EX13-022#3']['statuses']['effect_grants'][0]['effect'] == {'keywords': ['Blocker', 'Evade']}
assert observations[89]['zones']['A']['deck'][-1] == 'A:P-138#4'
assert observations[89]['zones']['A']['trash'][-1] == 'A:LM-028#1'
assert observations[91]['zones']['A']['hand'][-1] == 'A:P-138#4'
assert observations[92]['breeding']['A'] == observations[91]['breeding']['A']
assert observations[93]['memory'] == 3
assert final['state']['once_used'] == []
assert final['state']['zones']['A']['deck'][-1] == 'A:BT11-112#3'
assert r['commands'][-1]['args']['source_key'] == 'A:EX13-022#1'
assert r['commands'][-1]['args']['hand_key'] == 'A:BT11-032#1'
assert final['state']['battle']['A']['A:EX13-022#1']['instance_id'] == 'entity-9'
assert final['state']['battle']['A']['A:EX13-022#1']['suspended'] is False

source_index = json.loads((ROOT / INDEX).read_text())['sources']
source_ids = ['card-BT11-032', 'card-BT11-112', 'card-EX13-022', 'card-EX13-069',
              'card-EX13-002', 'card-BT12-029', 'card-EX1-013', 'card-BT22-023',
              'card-LM-028', 'rules']
sources = []
for sid in source_ids:
    entry = next(x for x in source_index if x['id'] == sid)
    actual = hashlib.sha256((ROOT / entry['file']).read_bytes()).hexdigest()
    assert actual == entry['sha256'], sid
    sources.append({k: entry[k] for k in ('id', 'file', 'url', 'sha256')})
locators = {
    'card-BT11-032': '#BT11-032 printed Blue Lv5 evolution cost4; When Digivolving optional blue-Tamer play; Your Turn mandatory self-unsuspend on own blue-Tamer play; separate actual-unsuspend OPT bounce',
    'card-BT11-112': '#BT11-112 On Play name-eligible Digimon Blocker/Evade through opponent turn end; All Turns own Veedramon suspension; Your Turn blue-Digimon actual-unsuspend OPT memory',
    'card-EX13-022': '#EX13-022 Lv5 Blue; top-only Tamer-play restriction; inherited actual self-suspension optional unsuspend',
    'card-EX13-069': '#EX13-069 Start of Your Main Phase memory; optional self-suspension on own Digimon actual-unsuspend; Q7437-Q7439',
    'card-EX13-002': '#EX13-002 inherited own-blue-Tamer-play timing, only active beneath appropriate field Digimon',
    'card-BT12-029': '#BT12-029 self actual-unsuspend timing; its existing top is a name-eligible Rina On Play target',
    'card-EX1-013': '#EX1-013 Q3203: already-unsuspended processing does not activate an actual-unsuspend trigger',
    'card-BT22-023': '#BT22-023 End of Your Turn OPT optional own-blue-Digimon-or-Tamer unsuspend',
    'card-LM-028': '#LM-028 Start of Your Turn Delay return blue trash Digimon to deck top; optional play only without own Digimon; Q4041-Q4042',
    'rules': 'Cover: Ver4.3 last updated2026/09/18; 1-3-3;1-3-11-1;3-1-2;3-1-3-1-3;3-4-3;4-2;6-3;6-4;6-5-1;6-6-2 through6-6-4;8-1-2-3;8-1-3-1 through8-1-3-3;15-3;15-4;15-7;15-11-1;15-13-2;15-14-1;15-16-2;15-16-3;15-16-8'
}
for source in sources:
    source['locator'] = locators[source['id']]
for relative in (RECORD, CONTEXT, INDEX):
    sources.append({'file': relative, 'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                    'locator': 'Preserved saved gameplay/context/source-index bytes'})
proof = {
    'schema': 'read-only-saved-prefix-command-replay-proof-v1',
    'date': '2026-11-03', 'record': RECORD, 'record_file_sha256': sources[-3]['sha256'],
    'record_canonical_sha256': digest(r), 'seed': r['seed'], 'context_id': r['context_id'],
    'successful_commands_replayed': len(rows), 'initial_physical_snapshot_match': True,
    'all_saved_public_views_match': True, 'all_saved_results_match': True,
    'physical_verification_after_each_command': True, 'cards_conserved': {'A': 54, 'B': 54, 'total': 108},
    'final_snapshot_matches_saved_final_and_before_halt': True, 'final_rng_match': True,
    'physical_snapshot_comparison': 'All snapshot fields except execution_id, legacy resolving_option None default',
    'final_snapshot_sha256': digest(ia._physical_snapshot(final)),
    'final_state_sha256': digest(final['state']), 'final_rng_sha256': digest(final['rng_state']),
    'intermediate_state_limitation': 'Record saves each pre-action public view/result, not every full hidden snapshot. Per-command replay hashes below record reconstructed hidden states; final full hidden state/RNG matches the saved checkpoint.',
    'no_command94_or_new_gameplay_executed': True, 'certification': 'NONE_SOFTWARE_PREFIX_PROOF_ONLY',
    'source_files_edited': [], 'per_command': rows,
    'engine_source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted((ROOT / 'SOURCE').glob('*.py'))}
}
(OUT / 'bt11-ulforce-actual-prefix-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
review = {
    'schema': 'bt11-ulforce-actual-saved-encounter-independent-review-v1',
    'date': '2026-11-03',
    'status': 'LEGAL_SAVED_EVOLUTION_REQUIRES_ACTUAL_POST_DRAW_WHEN_DIGIVOLVING_CHOICE',
    'certification': 'NONE_SOURCE_BACKED_ENCOUNTER_REVIEW_ONLY',
    'full_match_credit': 0, 'accepted_fact_finding_credit': 0, 'final_evaluation_credit': 0,
    'source_record': RECORD, 'seed': r['seed'], 'context_id': r['context_id'],
    'prefix_proof': 'bt11-ulforce-actual-prefix-proof.json',
    'prefix_result': {'commands': 93, 'all_saved_public_views_and_results_match': True,
                      'all_commands_conserve_108_cards': True, 'exact_final_physical_state_and_rng': True},
    'review_scope': 'Official-source assessment of actual saved command94 and newly resolved commands83-93; prefix replay does not establish full-game certification or historical universal branch coverage.',
    'actual_state': {'turn': 7, 'active': 'A', 'phase': 'MAIN', 'memory': 3,
                     'source': 'A:EX13-022#1', 'source_instance': 'entity-9', 'source_suspended': False,
                     'target_in_hand': 'A:BT11-032#1', 'route_index': 0, 'printed_route': 'Blue4 fromLv5',
                     'pending_effects': [], 'once_used': [],
                     'source_restriction': final['state']['battle']['A']['A:EX13-022#1']['statuses']['effect_grants'][0]},
    'new_prefix_commands_83_to_93': [
        {'commands': [83], 'assessment': 'BT22 optional EndYourTurn effect legally unsuspends selected own blue B:EX13-022#3, true->false, while cannot_suspend remains. Consume this BT22 source-incarnation OPT. Three B Rina effects trigger simultaneously.'},
        {'commands': [84], 'assessment': 'B chooses BT11Rina memory effect first; mandatory gain1 takes-3 to-2 and consumes its current-turn OPT.'},
        {'commands': [85, 86], 'assessment': 'B explicitly declines each EX13Rina optional self-suspension. Both Tamers remain unsuspended; no Draw, no After evolution, no invented EX13Rina OPT. Q7437 applies.'},
        {'commands': [87], 'assessment': 'With effects complete and memory-2, actual Bturn6 ends; Aturn7 starts at2. Clear old-turn OPT. Expire A restriction on BEX13#3 at actual Bturn6 end; retain BBlocker/Evade through Aturn7 and B restrictions on A entities through Aturn7.'},
        {'commands': [88, 89], 'assessment': 'A StartYourTurn BlueScramble Delay can activate: B has Digimon. Trash Option; return selected blue A:P-138#4 from trash to deck top. A has battle Digimon, so no optional trash play is available.'},
        {'commands': [90, 91], 'assessment': 'A reaches Draw and draws the actual just-returned A:P-138#4; all A field cards were already unsuspended, so phase progression causes no actual orientation change and no unsuspend reactions.'},
        {'commands': [92], 'assessment': 'A explicitly skips breeding; existing breeding stack remains. Enter Main and trigger actual EX13Rina StartMain memory condition.'},
        {'commands': [93], 'assessment': 'A has Veedramon-name battle Digimon; existing EX13Rina mandatory gain1 takes2 to3. No further pending effects or current-turn OPT uses remain.'}
    ],
    'selected_command94_assessment': {
        'legality': 'LEGAL', 'requirement': 'Source is own BlueLv5; hand target requires BlueLv5 cost4; no unresolved effect or rule prevents ordinary Main digivolution.',
        'procedure': ['Pay4: memory3->-1', 'Place A:BT11-032#1 on A:EX13-022#1', 'Preserve entity-9, orientation, play history and individual restriction', 'Draw actual next card as mandatory digivolution bonus', 'Queue new-top BT11-032 actual When Digivolving effect; choose from actual post-draw hand'],
        'no_premature_turn_change': 'Finish pending/derived processing before actual end-turn boundary despite memory-1.'
    },
    'judge_only_post_draw_expectation': {
        'information_policy': 'Hidden deck order is audit-only; never supply this review or pre-draw identity to pilot input. Recompute choices only after bonus draw actually executes.',
        'bonus_draw_if_no_other_action_intervenes': 'A:BT11-112#3',
        'actual_post_bonus_free_play_choices': [None, 'A:BT11-112#3'],
        'decline': 'Legal explicit decline; no Tamer play or play observers occur; memory stays-1.',
        'play': 'Play selected blue Tamer from own actual hand for0 cost; memory stays-1. Queue its mandatory OnPlay grant and Ulforce mandatory self-unsuspend as simultaneous derived effects controlled by A.',
        'rina_on_play_targets': ['A:BT11-032#1', 'A:BT12-029#2'],
        'rina_on_play_choice': 'Mandatory choose1 of these field Digimon; both names contain Veedramon. No optional None when a legal target exists. Breeding Veemon is ineligible.',
        'rina_grant_duration': {'controller': 'B', 'turn': 8, 'boundary': 'turn_end'},
        'simultaneous_order': 'A explicitly chooses the next pending effect after each resolution; grant and mandatory self-unsuspend both resolve before turn completion.',
        'already_unsuspended': 'Ulforce remains unsuspended; no actual unsuspend event, memory gain, EX13Rina Draw/After evolution, or Ulforce bounce occurs merely from this self-unsuspend processing.',
        'unrelated_your_turn_sources': 'B sources are not in their YourTurn timing; A egg/EX1 are in breeding; no egg/EX1 is under the new Ulforce.'
    },
    'carryover_and_nontriggers': [
        'The cannot_suspend restriction on entity-9 expires only at actual Aturn7 end and survives ordinary evolution; it does not prohibit evolution or attempted unsuspend processing.',
        'Ordinary evolution changes no orientation and is not a Tamer play. No suspension, unsuspension, Tamer-play observer, Rina AllTurns activation or inherited Aero unsuspend fires just from evolution.',
        'After evolution, EX13-022 main-text Tamer-play restriction is not active under Ulforce. It cannot retroactively observe the later Rina play. Its inherited self-suspension effect is active but sees no suspension.',
        'BT11-032 own blue-Tamer-play self-unsuspend has no printed OPT. Resolve it mandatorily, even already unsuspended. Its separate bounce OPT does not trigger or consume a use without a genuine suspended->unsuspended change.',
        'Neither existing nor newly played BT11Rina memory OPT is consumed by processing an already-unsuspended Digimon. EX13Rina has no printed OPT.',
        'A current-turn restriction also remains on BT12-029 through actual Aturn7 end; BBlocker/Evade remains on BEX13#3 through that same boundary. A new Rina grant would instead remain through actual Bturn8 end.'
    ],
    'official_rules_excerpts': [
        {'locator': 'CR1-3-3', 'text': 'If a card in a given state is requested to be changed to that same state, the card remains in its current state.'},
        {'locator': 'CR3-1-3-1-3', 'text': "Even if a card on the field becomes the bottom card in a stack due to cards being placed on top of it, it isn't considered to be a new card."},
        {'locator': 'CR8-1-2-3', 'text': 'A digivolved Digimon carries over its orientation from before the digivolution.'},
        {'locator': 'CR8-1-3-3', 'text': 'The player places the Digimon for the digivolution on top of the chosen card, draws 1 card, and the digivolution process is resolved.'},
        {'locator': 'CR15-13-2', 'text': 'When an effect is gained, the effect and the state of the effect at that time will be carried over, even if a card is placed on top of that card or a card is removed from its stack.'},
        {'locator': 'EX1-013 Q3203', 'text': 'The Digimon is already unsuspended, so this card\u2019s inherited effect doesn\u2019t activate. The Digimon must go from suspended to unsuspended for the effect to activate.'}
    ],
    'verification': {'new_ulforce_resolution_executed': False, 'source_files_edited': [],
                     'strategy_assessment': 'NONE', 'complete_game_assessment': 'NONE',
                     'findings': 'No concrete rules defect identified in newly resolved saved commands83-93; actual command94 is a legal evolution halted by missing printed-trigger implementation.'},
    'sources': sources
}
(OUT / 'bt11-ulforce-actual-stop.json').write_text(json.dumps(review, indent=2) + '\n')
md = '''# Actual BT11 Ulforce stop — independent archived-source review

**The saved evolution is legal.** Game0000, seed12017913134550805276, remains Aturn7/Main at memory3 before command94: A:EX13-022#1 → A:BT11-032#1 using printed BlueLv5 cost4. The stop is missing software for the actual new-top When Digivolving effect.

Replayed all93 successful saved commands from the original seed and choices. Every saved pre-action public view and result matched; physical verification passed after every command, conserving all108 cards. Full final hidden physical state and RNG match the saved pre-command94 checkpoint. The replay records per-command reconstructed state hashes; intermediate full hidden snapshots are not separately saved in the original record. Proof: [bt11-ulforce-actual-prefix-proof.json](bt11-ulforce-actual-prefix-proof.json).

Commands83–93 legally resolve the selected B unsuspend, mandatory BT11Rina memory, two explicit EX13Rina declines, actual Bturn6 completion, A BlueScramble Delay return of P138, its real Draw, breeding skip and EX13Rina StartMain gain. The Bturn6 restriction expired at the actual boundary; Aturn7 restrictions and BBlocker/Evade remain. No concrete defect was identified in these newly resolved commands. This does not recertify every historical branch.

Command94 must pay4 (memory3→−1), preserve entity-9 and its unsuspended orientation/restriction, stack Ulforce, take the mandatory bonus draw, then expose the actual post-draw optional blue-Tamer-play choice. Hidden draw expectations are retained only in the JSON judge audit and must not enter pilot input before the draw.

If a blue Rina is actually played, her mandatory On Play grant and Ulforce's mandatory self-unsuspend trigger simultaneously; A chooses their processing order. The Rina grant has exactly two eligible current targets: new BT11-032 and existing BT12-029. It lasts through actual Bturn8 end. Ulforce is already unsuspended, so processing its unsuspend produces no real unsuspend event, Rina memory/Draw, or bounce, and consumes no bounce OPT. Its blue-Tamer-play self-unsuspend has no printed OPT.

The existing cannot_suspend grant persists on entity-9 through normal evolution until actual Aturn7 end. It forbids suspension, not evolution or unsuspend processing. EX13-022's former main-text Tamer observer is inactive beneath Ulforce; its newly active inherited effect sees no suspension. No effect retroactively triggers merely because text became active.

Authority: pinned official BT11-032, BT11-112, EX13-022, EX13-069, EX13-002, BT12-029, EX1-013 (Q3203), BT22-023 and LM-028 pages; Comprehensive Rules **v4.3, updated2026/09/18**, especially1-3-3,3-1-3-1-3,8-1-2-3,8-1-3-3,15-4,15-11-1,15-13-2 and15-14-1. All cited archived files match SOURCE_INDEX hashes. Full URLs, hashes, locators and branch-specific expectations: [bt11-ulforce-actual-stop.json](bt11-ulforce-actual-stop.json).

No SOURCE files or saved gameplay records were edited; command94/new gameplay was not executed by this review. **Zero complete-match, fact-finding, strategy-lane or final-evaluation credit.**
'''
(OUT / 'bt11-ulforce-actual-stop-assessment.md').write_text(md)
print(json.dumps({'review': str(OUT.relative_to(ROOT) / 'bt11-ulforce-actual-stop.json'),
                  'commands_replayed': len(rows), 'exact_physical_and_rng': True,
                  'final_state_sha256': proof['final_state_sha256'],
                  'official_source_hashes_verified': len(source_ids), 'source_edits': []}, indent=2))
