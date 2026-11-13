"""Explicit attack windows with scoped participants and actual live observers.

Official v4.3 sections 7-1-2-1 and 11 through 14. This implementation grants no
rules certification. Unsupported counters/security/keywords remain precise HALTs;
explicit Counter declines are recorded as choices, never as learned strategy.
"""
from context_runtime import RuntimeHalt
from battlefield_scope import assert_basic_board_scope
from match_preparation import _rules

PLAIN_SECURITY = frozenset(('EX1-013','ST7-05','BT9-011'))
ATTACK_FIELDS = frozenset(('attacker','attacker_instance','target','target_instance',
                          'controller','defender','window','counter_used','block_used','checked'))


def _evidence(root):
    return {**_rules(root),'locator':'Comprehensive rules v4.3: 1-2; 7-1-2-1; 11; 12; 13; 14; 15-3-1'}


def validate_attack(state):
    a=state.attack
    if a is None:return
    if (not isinstance(a,dict) or set(a) not in (ATTACK_FIELDS, ATTACK_FIELDS | {'deferred_depth'})
            or a['controller'] not in ('A','B') or a['defender'] not in ('A','B')
            or a['controller']==a['defender'] or a['controller']!=state.active
            or a['window'] not in ('COUNTER','BLOCK','CONFIRM','END')
            or not all(isinstance(a[k],str) and a[k] for k in ('attacker','attacker_instance','target'))
            or not isinstance(a['target_instance'],str)
            or type(a['counter_used']) is not bool or type(a['block_used']) is not bool
            or (a['checked'] is not None and not isinstance(a['checked'],str))
            or ('deferred_depth' in a and (type(a['deferred_depth']) is not int
                or a['deferred_depth'] < 0 or state.phase != 'END_OF_TURN'))):
        raise RuntimeHalt('ATTACK_SCHEMA_INVALID')


def _scope(r,root,stage,*,attacker=None,target=None,within_effect=False):
    attack=r.state.attack
    actor=r.state.active
    if attack is not None:
        actor=attack['controller'];attacker=attack['attacker'];target=attack['target']
        within_effect = within_effect or 'deferred_depth' in attack
    assert_basic_board_scope(r,'attack_plain',root,
                            event={'stage':stage,'seat':actor,'attacker':attacker,'target':target},
                            within_effect=within_effect)


def _instance(r,stack):
    if not stack.instance_id:
        r.state.entity_sequence+=1;stack.instance_id='entity-'+str(r.state.entity_sequence)
    return stack.instance_id


def _declare(r,seat,c,root,*,from_end_effect=False):
    s=r.state
    if from_end_effect:
        from selected_mechanics import OMNIMON_END_EFFECT
        activated = getattr(r, '_activated_effect', None)
        if (activated is None or activated[0] != OMNIMON_END_EFFECT
                or activated[1] != seat or activated[4] is None
                or s.phase != 'END_OF_TURN' or s.attack is not None):
            raise RuntimeHalt('OMNIMON_END_ATTACK_WINDOW_REQUIRED')
    elif seat!=s.active or s.phase!='MAIN' or s.memory<0:
        raise RuntimeHalt('ATTACK_DECLARATION_WINDOW_NOT_OPEN')
    if seat != s.active:
        raise RuntimeHalt('ACTIVE_PLAYER_REQUIRED')
    stack=s.battle[seat].get(c['attacker'])
    if stack is None or (stack.suspended and not from_end_effect):raise RuntimeHalt('ATTACKER_NOT_READY')
    if r.context.card(seat,stack.cards[-1].card_number).kind!='Digimon':
        raise RuntimeHalt('ATTACKER_NOT_DIGIMON')
    from effect_grants import active_restriction
    if not from_end_effect and (stack.statuses.get('cannot_suspend',False) or ('effect_grants' in stack.statuses
            and active_restriction(r,seat,c['attacker'],'cannot_suspend'))):
        raise RuntimeHalt('ATTACKER_CANNOT_SUSPEND')
    _scope(r,root,'DECLARE',attacker=c['attacker'],target=c['target'],
           within_effect=from_end_effect)
    from effect_grants import active_keyword
    rush = active_keyword(r, seat, c['attacker'], 'Rush')
    if stack.played_turn is not None and (stack.played_turn>s.turn or
            (not rush and stack.ready_since_turn is not None and stack.ready_since_turn<=stack.played_turn)):
        raise RuntimeHalt('ATTACK_HISTORY_UNVERIFIED')
    if stack.played_turn==s.turn and not rush:raise RuntimeHalt('ATTACKER_PLAYED_THIS_TURN')
    if stack.ready_since_turn is None:
        if stack.played_turn is None:raise RuntimeHalt('ATTACK_HISTORY_UNVERIFIED')
    elif stack.ready_since_turn>s.turn and not rush:raise RuntimeHalt('ATTACKER_NOT_READY_THIS_TURN')
    other='B' if seat=='A' else 'A';target=c['target'];target_instance=''
    if target!='PLAYER':
        defender=s.battle[other].get(target)
        if defender is None or not defender.suspended:raise RuntimeHalt('ATTACK_TARGET_NOT_LEGAL')
        if r.context.card(other,defender.cards[-1].card_number).kind!='Digimon':
            raise RuntimeHalt('ATTACK_TARGET_NOT_DIGIMON')
        target_instance=_instance(r,defender)
    instance=_instance(r,stack)
    suspended_before = stack.suspended
    if not from_end_effect:
        stack.suspended=True
    s.attack={'attacker':c['attacker'],'attacker_instance':instance,'target':target,
              'target_instance':target_instance,'controller':seat,'defender':other,
              'window':'COUNTER','counter_used':False,'block_used':False,'checked':None}
    if from_end_effect and s.pending:
        pending = getattr(r, '_activated_pending', None)
        if pending is None or pending['effect_id'] != 'BT20-102.end_turn_rush_attack':
            raise RuntimeHalt('END_ATTACK_ORIGIN_REQUIRED')
        s.attack['deferred_depth'] = pending['depth']
    from printed_triggers import trigger_lines
    from tamer_play_effects import (PLAY_EFFECT,PLAY_LINE,ATTACK_TAMER_EFFECT,
                                    ATTACK_TAMER_LINE,tamer_play_usage)
    from effect_scheduler import queue_effects
    top=stack.cards[-1]
    from selected_mechanics import _collect_orientation_reactions,collect_rina_attack_jamming
    effects=_collect_orientation_reactions(r,seat,stack,suspended_before)
    effects.extend(collect_rina_attack_jamming(r,seat,c['attacker']))
    if trigger_lines(r.context.card(seat,top.card_number).effect_text('main_text'),'When Attacking'):
        # Scope above proved the exact printed line. Shared once-per-turn
        # usage covers the same effect's other printed activation windows.
        if top.card_number=='EX13-022' and PLAY_LINE in r.context.card(seat,top.card_number).effect_text('main_text').splitlines():
            effects.append({'seat':seat,'source':top.key,'effect_id':PLAY_EFFECT,'field':'main_text',
                'usage':list(tamer_play_usage(r,seat,top.key,PLAY_EFFECT)),
                'trigger':{'kind':'When Attacking','attacker':top.key,'target':target}})
        elif (top.card_number=='EX13-019' and ATTACK_TAMER_LINE in
              r.context.card(seat,top.card_number).effect_text('main_text').splitlines()):
            effects.append({'seat':seat,'source':top.key,'effect_id':ATTACK_TAMER_EFFECT,
                'field':'main_text','usage':list(tamer_play_usage(r,seat,top.key,ATTACK_TAMER_EFFECT)),
                'trigger':{'kind':'When Attacking','attacker':top.key,'target':target}})
        elif top.card_number=='EX13-023':
            from selected_mechanics import ORIENTATION_EFFECT,ORIENTATION_LINE
            if ORIENTATION_LINE not in r.context.card(seat,top.card_number).effect_text('main_text').splitlines():
                raise RuntimeHalt('ATTACK_TRIGGER_UNSUPPORTED: '+top.card_number+' source='+top.key)
            effects.append({'seat':seat,'source':top.key,'effect_id':ORIENTATION_EFFECT,'field':'main_text',
                'usage':[s.turn,seat,top.key,ORIENTATION_EFFECT],
                'trigger':{'kind':'When Attacking','attacker':top.key,'target':target}})
        else:
            raise RuntimeHalt('ATTACK_TRIGGER_UNSUPPORTED: '+top.card_number+' source='+top.key)
    before=len(s.pending);queue_effects(r,effects)
    result={'attacker':c['attacker'],'target':target,'window':'COUNTER','full_match_credit':0}
    if from_end_effect:
        result['suspended_to_attack'] = False
    if len(s.pending)>before:result['triggered_effects']=[e['effect_id'] for e in s.pending[before:]]
    return result


def declare_attack(runtime,seat,attacker,target,root):
    return runtime._control_command('DECLARE_ATTACK',seat,
        {'attacker':attacker,'target':target,'rules':_evidence(root)},
        lambda r,s,c:_declare(r,s,c,root))


def trusted_end_attack(runtime, seat, attacker, target, root):
    """The bound BT20-102 handler declares its chosen immediate attack."""
    return _declare(runtime, seat, {'attacker': attacker, 'target': target}, root,
        from_end_effect=True)


def _window(r,seat,window,defending=False):
    a=r.state.attack
    if a is None or a['window']!=window:raise RuntimeHalt('ATTACK_WINDOW_NOT_OPEN: '+window)
    if seat!=a['defender' if defending else 'controller']:raise RuntimeHalt('ATTACK_CONTROLLER_REQUIRED')
    return a


def counter_options(runtime,seat):
    _window(runtime,seat,'COUNTER',True)
    # Only the defender can inspect their own hand. These are unverified
    # candidates, not an assertion that every Blast digivolution route is legal.
    options=[{'card':None,'status':'EXPLICIT_DECLINE'}]
    for card in runtime.state.zones[seat]['hand']:
        text=runtime.context.card(seat,card.card_number).effect_text('main_text')
        if '[Counter]' in text:
            options.append({'card':card.key,'status':'UNVERIFIED_COUNTER_CANDIDATE'})
    return options


def _counter(r,seat,c,root):
    a=_window(r,seat,'COUNTER',True);_scope(r,root,'COUNTER')
    if c['card'] is not None:raise RuntimeHalt('COUNTER_EFFECT_UNSUPPORTED: '+str(c['card']))
    a['window']='BLOCK'
    return {'choice':'EXPLICIT_COUNTER_DECLINE','window':'BLOCK','strategy_status':'UNTRAINED'}


def choose_counter(runtime,seat,card,root):
    return runtime._control_command('COUNTER_CHOICE',seat,{'card':card,'rules':_evidence(root)},
        lambda r,s,c:_counter(r,s,c,root),allow_attack=True)


def _block(r,seat,c,root):
    a=_window(r,seat,'BLOCK',True);_scope(r,root,'BLOCK')
    from effect_grants import active_keyword,active_restriction
    if c['card'] is not None:
        key = c['card']
        stack = r.state.battle[seat].get(key)
        if (stack is None or r.context.card(seat,stack.cards[-1].card_number).kind!='Digimon'
                or stack.suspended or stack.statuses.get('cannot_suspend',False)
                or active_restriction(r,seat,key,'cannot_suspend')
                or not active_keyword(r,seat,key,'Blocker')):
            raise RuntimeHalt('BLOCKER_NOT_LEGAL: '+str(key))
        from selected_mechanics import _set_orientation
        changed = _set_orientation(r,seat,stack,True)
        if not changed['changed']:
            raise RuntimeHalt('BLOCKER_SUSPENSION_FAILED: '+key)
        a['target']=key;a['target_instance']=_instance(r,stack);a['block_used']=True
        a['window']='CONFIRM'
        return {'choice':'BLOCK_WITH_DIGIMON','blocker':key,'window':'CONFIRM',
                'target':key,'suspended':True}
    a['window']='CONFIRM'
    return {'choice':'EXPLICIT_NO_BLOCK','window':'CONFIRM'}


def choose_blocker(runtime,seat,card,root):
    return runtime._control_command('BLOCK_CHOICE',seat,{'card':card,'rules':_evidence(root)},
        lambda r,s,c:_block(r,s,c,root),allow_attack=True)


def battle_losers(attacker_dp,defender_dp,*,security=False):
    if type(attacker_dp) is not int or type(defender_dp) is not int or min(attacker_dp,defender_dp)<=0:
        raise RuntimeHalt('BATTLE_DP_UNVERIFIED')
    losers=[]
    if attacker_dp<=defender_dp:losers.append('ATTACKER')
    if not security and defender_dp<=attacker_dp:losers.append('DEFENDER')
    return losers


def _delete(r,seat,key):
    stack=r.state.battle[seat].pop(key)
    r.state.zones[seat]['trash'].extend(stack.cards)


def _dp(r,seat,stack):
    printed = r.context.card(seat,stack.cards[-1].card_number).to_dict()['dp']
    if 'effect_grants' in stack.statuses:
        from effect_grants import active_dp_bonus
        return printed + active_dp_bonus(r,seat,stack.cards[-1].key)
    return printed


def _offer_printed_evade(r, deletions, decision):
    """Pause one witnessed EX13-023 deletion for its owner's Evade choice."""
    from effect_grants import _active, active_keyword, active_restriction
    from effect_scheduler import queue_effects, source_stack
    from selected_mechanics import (EVADE_EFFECT, EVADE_LINE,
        GRANTED_EVADE_EFFECT, GRANTED_EVADE_LINE)
    payable = []
    for owner, key in deletions:
        stack = r.state.battle[owner][key]
        if ((owner, key) == (decision[:2] if decision is not None else (None, None))
                or stack.suspended or stack.statuses.get('cannot_suspend', False)
                or active_restriction(r, owner, key, 'cannot_suspend')
                or not active_keyword(r, owner, key, 'Evade')):
            continue
        top = stack.cards[-1]
        if (top.card_number == 'EX13-023' and EVADE_LINE in
                r.context.card(owner, top.card_number).effect_text('main_text').splitlines()):
            payable.append((owner, key, stack, top.key, EVADE_EFFECT))
            continue
        grants = [item for item in _active(r, owner, key)
                  if 'Evade' in item['effect'].get('keywords', [])]
        if len(grants) != 1:
            raise RuntimeHalt('BATTLE_EVADE_GRANT_SOURCE_UNVERIFIED: ' + key)
        grant = grants[0]
        try:
            source = r._source(owner, grant['source'], 'main_text')
            source_stack(r, owner, grant['source'], 'main_text')
        except RuntimeHalt as exc:
            raise RuntimeHalt('BATTLE_EVADE_GRANT_SOURCE_UNAVAILABLE: ' + key) from exc
        if (source.card_number != 'BT11-112' or GRANTED_EVADE_LINE not in
                r.context.card(owner, source.card_number).effect_text('main_text').splitlines()):
            raise RuntimeHalt('BATTLE_EVADE_GRANT_SOURCE_UNVERIFIED: ' + key)
        payable.append((owner, key, stack, source.key, GRANTED_EVADE_EFFECT))
    if not payable:
        return None
    if len(payable) != 1:
        raise RuntimeHalt('BATTLE_MULTIPLE_EVADE_CHOICES_UNIMPLEMENTED')
    owner, key, stack, source_key, effect_id = payable[0]
    queue_effects(r, [{'seat': owner, 'source': source_key, 'effect_id': effect_id,
        'field': 'main_text', 'trigger': {'kind': 'WOULD_BE_DELETED',
            'target': key, 'target_instance': stack.instance_id,
            'attack': dict(r.state.attack)}}])
    return {'processing': 'EVADE_CHOICE_PENDING', 'target': key,
            'evade_owner': owner, 'full_match_credit': 0}


def resolve_printed_evade(runtime, seat, source_key, choice, root):
    """Resolve the optional immediate Evade, then finish the paused battle."""
    from effect_grants import _active
    from selected_mechanics import (EVADE_EFFECT, EVADE_LINE,
        GRANTED_EVADE_EFFECT, _set_orientation)
    if type(choice) is not bool:
        raise RuntimeHalt('EVADE_CHOICE_INVALID')
    record = getattr(runtime, '_activated_pending', None)
    attack = runtime.state.attack
    if (record is None or record['effect_id'] not in (EVADE_EFFECT, GRANTED_EVADE_EFFECT)
            or record['seat'] != seat or record['source'] != source_key
            or record['field'] != 'main_text' or attack is None
            or attack['window'] != 'CONFIRM' or record['trigger'].get('attack') != attack
            or record['trigger'].get('kind') != 'WOULD_BE_DELETED'):
        raise RuntimeHalt('EVADE_WINDOW_REQUIRED')
    key = record['trigger']['target']
    stack = runtime.state.battle[seat].get(key)
    if (stack is None or stack.instance_id != record['trigger']['target_instance']
            or stack.suspended):
        raise RuntimeHalt('EVADE_TARGET_CHANGED')
    if record['effect_id'] == EVADE_EFFECT:
        if (stack.cards[-1].key != source_key or
                EVADE_LINE not in runtime.context.card(seat, 'EX13-023').effect_text('main_text').splitlines()):
            raise RuntimeHalt('EVADE_TARGET_CHANGED')
    elif not any(item['source'] == source_key and 'Evade' in item['effect'].get('keywords', [])
                 for item in _active(runtime, seat, key)):
        raise RuntimeHalt('EVADE_GRANT_EXPIRED')
    if choice:
        changed = _set_orientation(runtime, seat, stack, True)
        if not changed['changed']:
            raise RuntimeHalt('EVADE_SUSPEND_FAILED')
    finished = _confirm(runtime, attack['controller'], {}, root,
                        evade_decision=(seat, key, choice))
    return {'prevented_deletion': choice, 'evade_target': key,
            'battle': finished, 'full_match_credit': 0}


def _confirm(r,seat,c,root,*,evade_decision=None):
    a=_window(r,seat,'CONFIRM');_scope(r,root,'CONFIRM',within_effect=evade_decision is not None);s=r.state;other=a['defender']
    attacker=s.battle[seat].get(a['attacker'])
    if attacker is None or attacker.instance_id!=a['attacker_instance']:
        a['window']='END';return {'success':False,'reason':'ATTACKER_LEFT_BATTLE'}
    if a['target']!='PLAYER':
        defender=s.battle[other].get(a['target'])
        if defender is None or defender.instance_id!=a['target_instance']:
            a['window']='END';return {'success':False,'reason':'TARGET_LEFT_BATTLE'}
        losses=battle_losers(_dp(r,seat,attacker),_dp(r,other,defender))
        from battlefield_scope import assert_combat_consequences_scope
        deletions = [(owner,key) for label,owner,key in (
            ('ATTACKER',seat,a['attacker']),('DEFENDER',other,a['target'])) if label in losses]
        offered = _offer_printed_evade(r, deletions, evade_decision)
        if offered is not None:
            return offered
        if evade_decision is not None and evade_decision[2]:
            label = 'ATTACKER' if evade_decision[:2] == (seat,a['attacker']) else 'DEFENDER'
            losses.remove(label)
            deletions = [item for item in deletions if item != evade_decision[:2]]
        assert_combat_consequences_scope(r,deletions,
            evade_declined=[evade_decision[:2]] if evade_decision is not None and not evade_decision[2] else ())
        if 'ATTACKER' in losses:_delete(r,seat,a['attacker'])
        if 'DEFENDER' in losses:_delete(r,other,a['target'])
        a['window']='END'
        result={'success':True,'battle_losers':losses}
        if 'DEFENDER' in losses and 'ATTACKER' not in losses:
            from selected_mechanics import OMNIMON_KEYWORDS_LINE, OMNIMON_PIERCE_EFFECT
            top = attacker.cards[-1]
            if (top.card_number == 'BT20-102' and
                    OMNIMON_KEYWORDS_LINE in r.context.card(seat, top.card_number).effect_text('main_text').splitlines()):
                from effect_scheduler import queue_effects
                queue_effects(r, [{'seat': seat, 'source': top.key,
                    'effect_id': OMNIMON_PIERCE_EFFECT, 'field': 'main_text',
                    'trigger': {'kind': 'Piercing', 'deleted_digimon': a['target']}}])
                result['triggered_effects'] = [OMNIMON_PIERCE_EFFECT]
        return result
    if not s.zones[other]['security']:
        s.terminal=True;s.winner=seat;s.terminal_reason='SUCCESSFUL_DIRECT_ATTACK'
        s.attack=None
        return {'success':True,'winner':seat,'status':'EXPERIMENTAL_TERMINAL','full_match_credit':0}
    checked=s.zones[other]['security'][-1]
    definition=r.context.card(other,checked.card_number)
    from security_tamer import security_tamer_spec,resolve_checked_tamer
    if security_tamer_spec(definition) is not None:
        from battlefield_scope import assert_combat_consequences_scope
        assert_combat_consequences_scope(r,[],security_owner=other)
        return resolve_checked_tamer(r,other,checked,root)
    from option_actions import security_option_spec, resolve_checked_security_option
    if security_option_spec(definition) is not None:
        from battlefield_scope import assert_combat_consequences_scope
        assert_combat_consequences_scope(r,[],security_owner=other)
        return resolve_checked_security_option(r,other,checked,root)
    from printed_triggers import trigger_lines
    # CR13/14: a checked Digimon battles using printed DP. Its ordinary battle
    # area abilities do not become Security effects merely because it has text.
    if (definition.kind!='Digimon' or definition.effect_text('security_text')
            or trigger_lines(definition.effect_text('main_text'),'Security')
            or type(definition.to_dict()['dp']) is not int):
        raise RuntimeHalt('SECURITY_CARD_UNSUPPORTED: '+checked.card_number+' source='+checked.key)
    from selected_mechanics import _source_evidence
    evidence=_source_evidence(root,definition.to_dict()['official_source'],
                              '#'+checked.card_number+' plain Security Digimon printed DP').manifest()
    # The checked card is temporarily in no area (13-1-6). No unsupported
    # processing occurs in this atomic slice; it is conserved again on commit.
    losses=battle_losers(_dp(r,seat,attacker),definition.to_dict()['dp'],security=True)
    from effect_grants import active_keyword
    if 'ATTACKER' in losses and active_keyword(r,seat,a['attacker'],'Jamming'):
        losses.remove('ATTACKER')
    from battlefield_scope import assert_combat_consequences_scope
    deletions = [(seat,a['attacker'])] if 'ATTACKER' in losses else []
    offered = _offer_printed_evade(r, deletions, evade_decision)
    if offered is not None:
        return offered
    if evade_decision is not None and evade_decision[2]:
        losses.remove('ATTACKER')
        deletions = []
    assert_combat_consequences_scope(r,deletions, security_owner=other,
        evade_declined=[evade_decision[:2]] if evade_decision is not None and not evade_decision[2] else ())
    s.zones[other]['security'].pop()
    if 'ATTACKER' in losses:_delete(r,seat,a['attacker'])
    s.zones[other]['trash'].append(checked)
    a['checked']=checked.key;a['window']='END'
    return {'success':True,'checked_card':checked.key,'attacker_deleted':'ATTACKER' in losses,
            'security_card_deleted':False,'source':evidence}


def confirm_attack(runtime,seat,root):
    return runtime._control_command('CONFIRM_ATTACK',seat,{'rules':_evidence(root)},
        lambda r,s,c:_confirm(r,s,c,root),allow_attack=True)


def _end(r,seat,c,root):
    _window(r,seat,'END');_scope(r,root,'END')
    r.state.attack=None
    return {'attack_ended':True,'full_match_credit':0}


def end_attack(runtime,seat,root):
    return runtime._control_command('END_ATTACK',seat,{'rules':_evidence(root)},
        lambda r,s,c:_end(r,s,c,root),allow_attack=True)
