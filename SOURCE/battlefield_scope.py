"""Conservative battlefield capability for selected experimental basic actions.

The official EX1-013, ST7-05 and BT9-011 definitions have no main effect.
Their inherited effects do not apply while those cards are singleton tops.
BT9-011's printed special digivolution route does not create a battlefield
effect. Attack calls name their actual window and participants: unrelated
self triggers remain inert, while live observers and unsupported combat
participants remain explicit dependencies.

This guard grants no rules certification or full-match credit. Callers own
physical-state validation, legal action windows, and the new action's effects.
It inspects neither hidden zones nor breeding contents and never mutates state,
events, RNG or halt flags, including on failure.
"""
import re

from context_runtime import PhysicalCard, PhysicalState, RuntimeHalt, Stack
from option_actions import OPTION_SPECS
from selected_contexts import require_selected_context


_ACTIONS = frozenset(('play_plain', 'play_search', 'breeding_evolve', 'battle_evolve','attack_plain', 'use_option'))
_PLAIN_TOPS = frozenset(('EX1-013', 'ST7-05', 'BT9-011'))
_SEARCH_TOPS = frozenset(('BT11-023','P-138','EX13-017','EX2-008','EX8-009'))
_OTHER_TIMINGS_TOPS = frozenset(('BT12-016','BT12-029','BT17-013','BT17-016','BT19-007',
    'BT19-009','BT19-080','BT22-022','EX13-019','EX13-069','EX8-012','EX8-015'))
_RESOLVED_PLAY_TOPS = frozenset(('BT11-112','BT22-085','BT22-023'))
_INERT_OPTION_TOPS = frozenset(OPTION_SPECS)
# Keep explicit schemas: a newly added effect-bearing dataclass field must not
# silently acquire support merely because the dataclass accepted it.
_STATE_FIELDS = frozenset(('zones', 'battle', 'breeding', 'active', 'memory', 'turn',
                           'terminal', 'once_used', 'pending', 'effect_sequence',
                           'entity_sequence', 'phase', 'preparation','attack','winner','terminal_reason',
                           'resolving_option'))
_STACK_FIELDS = frozenset(('cards', 'suspended', 'statuses', 'instance_id', 'played_turn','ready_since_turn'))
_CARD_FIELDS = frozenset(('owner', 'card_number', 'index'))
_ATTACK_STAGES = frozenset(('DECLARE','COUNTER','BLOCK','CONFIRM','END'))
_AERO_KEYWORD_LINE = '＜Blocker＞ ＜Evade＞'
_AERO_PROTECTION_LINE = ("[All Turns] Your opponent's effects can't reduce this unsuspended "
                         "Digimon's DP, return its stacked cards to the hand or deck, or trash them.")
_EX13_019_INHERITED_JAMMING = "＜Jamming＞ (This Digimon can't be deleted in battles against Security Digimon.)"
_EX13_019_MAIN_JAMMING = '＜Jamming＞'


def _exact_aero_main(definition):
    from selected_mechanics import ORIENTATION_LINE
    from ex13_ulforce_effects import RETURN_LINE
    return definition.effect_text('main_text').splitlines() == [
        _AERO_KEYWORD_LINE, ORIENTATION_LINE, RETURN_LINE, _AERO_PROTECTION_LINE]


def _assert_selected_context(runtime, root):
    require_selected_context(runtime.context, root)


def _persistent_field_is_self_only(body):
    """Recognize a self modifier/protection, failing closed on other targets.

    An orientation adjective does not change the affected entity. A mention of
    that entity in a condition, however, does not make a global modifier local.
    Unknown wording stays a dependency rather than acquiring inferred support.
    """
    predicate=re.sub(r'^(?:While|If)\s+[^,]+,\s*','',body, count=1, flags=re.I)
    reference=r'\bthis\s+(?:(?:un)?suspended\s+)?Digimon(?:[\'’]s)?\b'
    predicate,count=re.subn(reference,'SELF',predicate,flags=re.I)
    if not count:return False
    predicate=re.sub(r'\b(?:your opponent[\'’]s|your|opponent[\'’]s) effects?\b',
                     'effects',predicate,flags=re.I)
    if re.search(r'＜|\b(?:Digimon|Tamer|security|players?|you|your|opponent|their|'
                 r'all|each|every|both|other|only|attacks?|attacking|battle|costs?|memory)\b',
                 predicate,re.I):
        return False
    return bool(re.match(r'^SELF\s+(?:gets?|gains?|is|isn\'t|can\'t|cannot|may)\b',predicate,re.I)
                or re.match(r'^effects?\s+(?:can\'t|cannot)\b[^.]*\bSELF\b',predicate,re.I))


def _attack_source_dependencies(runtime, owner, anchor, source, field, event):
    """Inspect the actual attack/suspension, keeping unrelated self text inert.

    Every active main/inherited field is checked at its actual event. Stack
    composition alone does not add an ability or make a known one unsupported.
    """
    from printed_triggers import effect_headers, effect_body
    definition=runtime.context.card(owner,source.card_number)
    actor=event['seat'];attacker=event['attacker'];stage=event['stage']
    attacker_stack=runtime.state.battle[actor].get(attacker)
    if attacker_stack is None:
        return
    attacker_definition=runtime.context.card(actor,attacker_stack.cards[-1].card_number)
    participant=(owner==actor and anchor==attacker or owner!=actor and anchor==event['target'])
    if participant and stage=='CONFIRM':
        # Printed play/evolution routes do not apply to an ordinary attack.
        # Unknown special fields may change battle or leaving and need support.
        for label,text in definition.to_dict()['special_conditions'].items():
            if text and label not in ('[Special Digivolution Condition]','[Special Play Condition]'):
                raise RuntimeHalt('ATTACK_SPECIAL_CONDITION_UNIMPLEMENTED: '+source.card_number
                                  +' special_conditions '+label+' source='+source.key)
    for line in definition.effect_text(field).splitlines():
        if line.lstrip().startswith(('・','•')):
            continue
        headers=effect_headers(line);body=effect_body(line)
        if ('Your Turn' in headers and owner!=runtime.state.active
                or "Opponent's Turn" in headers and owner==runtime.state.active):
            continue
        if headers and not any(h in ('Your Turn',"Opponent's Turn",'All Turns') for h in headers):
            if (participant and stage=='CONFIRM' and not any(h in (
                    'On Play','When Digivolving','When Attacking','End of Attack','On Deletion',
                    'Start of Your Turn','End of Your Turn','Start of Your Main Phase',
                    'When Moving','Security','Counter','Main') for h in headers)):
                raise RuntimeHalt('ATTACK_PRINTED_FIELD_UNIMPLEMENTED: '+source.card_number
                                  +' '+field+' source='+source.key)
            if stage=='DECLARE' and 'When Attacking' in headers and owner==actor and anchor==attacker:
                from tamer_play_effects import PLAY_EFFECT,PLAY_LINE
                from selected_mechanics import ORIENTATION_EFFECT,ORIENTATION_LINE
                if source.card_number=='EX13-022' and field=='main_text' and line==PLAY_LINE:
                    runtime.registry.lookup(source.card_number,PLAY_EFFECT,field)
                elif source.card_number=='EX13-023' and field=='main_text' and line==ORIENTATION_LINE:
                    runtime.registry.lookup(source.card_number,ORIENTATION_EFFECT,field)
                else:
                    raise RuntimeHalt('ATTACK_TRIGGER_UNSUPPORTED: '+source.card_number+' '+field+' source='+source.key)
            elif stage=='END' and 'End of Attack' in headers and owner==actor and anchor==attacker:
                raise RuntimeHalt('ATTACK_END_TRIGGER_UNSUPPORTED: '+source.card_number+' '+field+' source='+source.key)
            continue
        clause=body.split(',',1)[0]
        if clause.startswith('When '):
            if stage!='DECLARE':
                continue
            suspension=bool(re.search(r'\bsuspend(?:s|ed)?\b',clause,re.I))
            attacking=bool(re.search(r'\battack(?:s|ing)?\b',clause,re.I))
            # The shared actual-orientation preflight below owns every
            # suspension clause, including registered Rina/inherited reactions.
            if suspension or not attacking:
                continue
            if 'this Digimon' in clause and (owner!=actor or anchor!=attacker):
                continue
            if 'this Tamer' in clause:
                continue
            if 'opponent' in clause.lower():
                if actor==owner:continue
            elif any(p in clause for p in ('your ','you attack')) and actor!=owner:
                continue
            names=re.findall(r'\[([^\]]+)\]',clause)
            if names and not any(name in attacker_definition.name for name in names):
                continue
            if 'blue' in clause.lower() and 'Blue' not in attacker_definition.to_dict()['colors']:
                continue
            from selected_mechanics import RINA_JAMMING_EFFECT,RINA_JAMMING_LINE
            if (source.card_number=='BT22-085' and field=='main_text' and line==RINA_JAMMING_LINE
                    and owner==actor and 'Veedramon' in attacker_definition.name):
                runtime.registry.lookup(source.card_number,RINA_JAMMING_EFFECT,field)
                continue
            raise RuntimeHalt('ATTACK_OBSERVER_UNIMPLEMENTED: '+source.card_number+' '+field+' source='+source.key)
        if stage in ('DECLARE','CONFIRM') and participant and not headers and line.strip():
            if (source.card_number=='EX13-023' and field=='main_text'
                    and line==_AERO_KEYWORD_LINE and _exact_aero_main(definition)):
                continue
            if (source.card_number=='EX13-019' and field=='inherited_text'
                    and line==_EX13_019_INHERITED_JAMMING
                    and definition.effect_text(field)==line):
                continue
            if (source.card_number=='EX13-019' and field=='main_text'
                    and line==_EX13_019_MAIN_JAMMING
                    and definition.effect_text(field).splitlines()[:1]==[line]):
                continue
            # A keyword can add declaration timing (for example Raid). Do not
            # suspend/open Counter before unsupported participant text is known.
            reason='ATTACK_KEYWORD_UNSUPPORTED' if '＜' in line else 'ATTACK_PRINTED_FIELD_UNIMPLEMENTED'
            raise RuntimeHalt(reason+': '+source.card_number+' '+field+' source='+source.key)
        if stage=='CONFIRM' and headers and re.search(r'\b(?:DP|attack|Digimon|security)\b',body,re.I):
            if (source.card_number=='EX13-023' and field=='main_text'
                    and line==_AERO_PROTECTION_LINE and _exact_aero_main(definition)):
                # A plain attack is not an opponent effect that reduces DP or
                # returns/trashes sources. Counter effects remain unsupported.
                continue
            if participant or not _persistent_field_is_self_only(body):
                raise RuntimeHalt('ATTACK_PERSISTENT_EFFECT_UNSUPPORTED: '+source.card_number+' '+field+' source='+source.key)


def assert_combat_consequences_scope(runtime, deletions, *, security_owner=None):
    """Preflight the actual deletion/security footprint before any card moves.

    Attack scope already verifies the pinned source bytes and metadata. Battle
    deletion is rules processing, so an opponent-effect-only replacement does
    not apply. A payable Evade or live unimplemented observer remains a HALT.
    """
    from effect_grants import active_keyword,active_restriction
    from printed_triggers import effect_headers,effect_body
    removed=set(deletions)
    for owner,key in removed:
        stack=runtime.state.battle[owner][key]
        if (active_keyword(runtime,owner,key,'Evade') and not stack.suspended
                and not stack.statuses.get('cannot_suspend',False)
                and not active_restriction(runtime,owner,key,'cannot_suspend')):
            raise RuntimeHalt('BATTLE_EVADE_CHOICE_UNIMPLEMENTED: '+key)
    for owner in ('A','B'):
        for anchor,stack in runtime.state.battle[owner].items():
            for index,source in enumerate(stack.cards):
                field='main_text' if index==len(stack.cards)-1 else 'inherited_text'
                for line in runtime.context.card(owner,source.card_number).effect_text(field).splitlines():
                    headers=effect_headers(line);body=effect_body(line)
                    if ('Your Turn' in headers and owner!=runtime.state.active
                            or "Opponent's Turn" in headers and owner==runtime.state.active):
                        continue
                    if 'On Deletion' in headers and (owner,anchor) in removed:
                        raise RuntimeHalt('BATTLE_DELETION_TRIGGER_UNIMPLEMENTED: '+source.card_number+' '+field+' source='+source.key)
                    clause=body.split(',',1)[0]
                    if not clause.startswith('When '):continue
                    security=security_owner is not None and bool(re.search(r'\bsecurity\b',clause,re.I))
                    leave=bool(removed) and bool(re.search(r'\b(?:delet\w*|leav\w*)\b',clause,re.I))
                    if not security and not leave:continue
                    # This atomic slice performs no opponent card effect.
                    if (('other than' not in clause.lower() and re.search(
                            r"(?:by|from) (?:an?|your opponent's|your) effects?",clause,re.I))
                            or re.search(r"^When (?:an?|your|your opponent's) effects?\b",clause,re.I)):
                        continue
                    affected={security_owner} if security else {seat for seat,_ in removed}
                    if 'this Digimon' in clause and (owner,anchor) not in removed:continue
                    if 'opponent' in clause.lower():
                        if not any(seat!=owner for seat in affected):continue
                    elif 'your ' in clause.lower() and owner not in affected:
                        continue
                    if 'other Digimon' in clause and not any(
                            seat==owner and key!=anchor for seat,key in removed):continue
                    reason='SECURITY_OBSERVER_UNIMPLEMENTED' if security else 'BATTLE_LEAVE_OBSERVER_UNIMPLEMENTED'
                    raise RuntimeHalt(reason+': '+source.card_number+' '+field+' source='+source.key)


def assert_basic_board_scope(runtime, action, root, *, event=None, within_effect=False):
    """Validate source metadata and dependencies at the selected action timing.

    ``action`` must explicitly name one supported basic action. The five search
    tops require their complete pinned main text to equal a known self-search
    effect. Attack event records inspect participants' active combat fields;
    unrelated inherited sources are checked against the actual event.
    ``root`` supplies the locked context and hash-bound official source bytes.
    """
    if type(action) is not str or action not in _ACTIONS:
        raise RuntimeHalt('BASIC_BOARD_ACTION_UNSUPPORTED')
    if runtime.allow_experimental is not True:
        raise RuntimeHalt('BASIC_BOARD_EXPERIMENTAL_OPT_IN_REQUIRED')
    _assert_selected_context(runtime, root)
    state = runtime.state
    attack_event=action=='attack_plain' and event is not None
    if attack_event and (type(event) is not dict or event.get('stage') not in _ATTACK_STAGES
            or event.get('seat')!=state.active
            or not all(isinstance(event.get(key),str) for key in ('attacker','target'))):
        raise RuntimeHalt('ATTACK_EVENT_SCOPE_UNSUPPORTED')
    if type(state) is not PhysicalState or set(vars(state)) != _STATE_FIELDS:
        raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: state')
    if type(state.battle) is not dict or set(state.battle) != {'A', 'B'}:
        raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: battle')
    if within_effect and not getattr(runtime,'_activated_effect',None):
        raise RuntimeHalt('BASIC_BOARD_ACTIVE_EFFECT_REQUIRED')
    if state.pending and not within_effect:
        raise RuntimeHalt('BASIC_BOARD_PENDING_EFFECTS_UNSUPPORTED')
    if state.resolving_option is not None and not within_effect:
        raise RuntimeHalt('BASIC_BOARD_OPTION_PROCESSING_PENDING')

    from selected_mechanics import _source_evidence

    checked = set()
    for owner in ('A', 'B'):
        if type(state.battle[owner]) is not dict:
            raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: ' + owner)
        for anchor, stack in state.battle[owner].items():
            if type(stack) is not Stack or set(vars(stack)) != _STACK_FIELDS:
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: stack ' + owner)
            if type(stack.cards) is not list or not stack.cards or (len(stack.cards)!=1 and action=='attack_plain' and not attack_event):
                raise RuntimeHalt('BASIC_BOARD_STACK_UNSUPPORTED: ' + owner)
            if type(stack.statuses) is not dict:
                raise RuntimeHalt('BASIC_BOARD_STATUS_UNSUPPORTED: ' + owner)
            if stack.statuses:
                if set(stack.statuses) != {'effect_grants'} or action == 'attack_plain' and not attack_event:
                    raise RuntimeHalt('BASIC_BOARD_STATUS_UNSUPPORTED: ' + owner)
                from effect_grants import validate_grants
                validate_grants(runtime, owner, anchor)
            if (type(stack.suspended) is not bool or type(stack.instance_id) is not str
                    or (stack.played_turn is not None
                        and (type(stack.played_turn) is not int or stack.played_turn < 0))
                    or (stack.ready_since_turn is not None
                        and (type(stack.ready_since_turn) is not int or stack.ready_since_turn < 0))):
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: stack ' + owner)
            physical = stack.cards[-1]
            if (type(physical) is not PhysicalCard or set(vars(physical)) != _CARD_FIELDS
                    or physical.owner != owner or type(physical.card_number) is not str
                    or type(physical.index) is not int or physical.index < 1
                    or type(anchor) is not str or anchor != physical.key):
                raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: card ' + owner)
            if action!='attack_plain' or attack_event:
                from basic_event_dependencies import require_inert_for_event
                for index,source in enumerate(stack.cards):
                    if (type(source) is not PhysicalCard or set(vars(source))!=_CARD_FIELDS
                            or source.owner!=owner or type(source.index) is not int or source.index<1):
                        raise RuntimeHalt('BASIC_BOARD_METADATA_UNSUPPORTED: source '+owner)
                    definition=runtime.context.card(owner,source.card_number)
                    field='main_text' if index==len(stack.cards)-1 else 'inherited_text'
                    if attack_event:
                        _attack_source_dependencies(runtime,owner,anchor,source,field,event)
                    else:
                        require_inert_for_event(runtime,owner,source,field,action,event)
                    if source.card_number not in checked:
                        try:
                            _source_evidence(root,definition.to_dict()['official_source'],
                                '#'+source.card_number+' '+field+' at actual '+action+' event').manifest()
                        except (OSError,ValueError,KeyError,TypeError) as exc:
                            raise RuntimeHalt('BASIC_BOARD_OFFICIAL_SOURCE_UNAVAILABLE: '+source.card_number) from exc
                        checked.add(source.card_number)
                continue
            inert_option=physical.card_number in _INERT_OPTION_TOPS
            resolved_play=physical.card_number in _RESOLVED_PLAY_TOPS and action!='attack_plain'
            other_timing=((physical.card_number in _OTHER_TIMINGS_TOPS or resolved_play) and action!='attack_plain')
            if physical.card_number not in _PLAIN_TOPS | _SEARCH_TOPS and not other_timing and not inert_option:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number)
            try:
                definition = runtime.context.card(owner, physical.card_number)
            except (ValueError, StopIteration) as exc:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number) from exc
            expected_main=''
            if physical.card_number in _SEARCH_TOPS:
                from search_effects import SEARCH_SPECS
                expected_main=SEARCH_SPECS[physical.card_number][1]
            if other_timing:
                from printed_triggers import trigger_lines
                # Original context/hash pin above fixes the complete wording.
                # These audited cards have no play observer, cost replacement or
                # breeding exception. Their own later triggers do not activate
                # here. BT17-016's self-immunity doesn't affect these actions,
                # which apply no opponent effect to that Digimon.
                if trigger_lines(definition.effect_text('main_text'),'On Play') and not resolved_play:
                    raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: unexpected On Play')
                expected_main=definition.effect_text('main_text')
            if inert_option:
                if physical.card_number not in OPTION_SPECS or stack.suspended:
                    raise RuntimeHalt('BASIC_BOARD_OPTION_UNSUPPORTED')
                expected_main=definition.effect_text('main_text')
            allowed_kinds=('Option',) if inert_option else (('Digimon','Tamer') if other_timing else ('Digimon',))
            if definition.kind not in allowed_kinds or definition.effect_text('main_text') != expected_main:
                raise RuntimeHalt('BASIC_BOARD_TOP_UNSUPPORTED: ' + owner + ' ' + physical.card_number)
            if physical.card_number not in checked:
                try:
                    _source_evidence(root, definition.to_dict()['official_source'],
                                     '#' + physical.card_number + ' main effects at the selected basic-action timing; '
                                     'unrelated self triggers do not activate, and no active text changes this action. '
                                     'Inherited effect is not active on a singleton top (15-3-1).').manifest()
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise RuntimeHalt('BASIC_BOARD_OFFICIAL_SOURCE_UNAVAILABLE: '
                                      + physical.card_number) from exc
                checked.add(physical.card_number)

    if attack_event and event['stage']=='DECLARE':
        attacker=state.battle[event['seat']].get(event['attacker'])
        if attacker is not None:
            from selected_mechanics import _orientation_dependencies
            _orientation_dependencies(runtime,event['seat'],attacker,attacker.suspended,True)
