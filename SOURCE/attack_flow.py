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
    if (not isinstance(a,dict) or set(a)!=ATTACK_FIELDS
            or a['controller'] not in ('A','B') or a['defender'] not in ('A','B')
            or a['controller']==a['defender'] or a['controller']!=state.active
            or a['window'] not in ('COUNTER','BLOCK','CONFIRM','END')
            or not all(isinstance(a[k],str) and a[k] for k in ('attacker','attacker_instance','target'))
            or not isinstance(a['target_instance'],str)
            or type(a['counter_used']) is not bool or type(a['block_used']) is not bool
            or (a['checked'] is not None and not isinstance(a['checked'],str))):
        raise RuntimeHalt('ATTACK_SCHEMA_INVALID')


def _scope(r,root,stage,*,attacker=None,target=None):
    attack=r.state.attack
    actor=r.state.active
    if attack is not None:
        actor=attack['controller'];attacker=attack['attacker'];target=attack['target']
    assert_basic_board_scope(r,'attack_plain',root,
                            event={'stage':stage,'seat':actor,'attacker':attacker,'target':target})


def _instance(r,stack):
    if not stack.instance_id:
        r.state.entity_sequence+=1;stack.instance_id='entity-'+str(r.state.entity_sequence)
    return stack.instance_id


def _declare(r,seat,c,root):
    s=r.state
    if seat!=s.active or s.phase!='MAIN' or s.memory<0:
        raise RuntimeHalt('ATTACK_DECLARATION_WINDOW_NOT_OPEN')
    stack=s.battle[seat].get(c['attacker'])
    if stack is None or stack.suspended:raise RuntimeHalt('ATTACKER_NOT_READY')
    if r.context.card(seat,stack.cards[-1].card_number).kind!='Digimon':
        raise RuntimeHalt('ATTACKER_NOT_DIGIMON')
    from effect_grants import active_restriction
    if stack.statuses.get('cannot_suspend',False) or ('effect_grants' in stack.statuses
            and active_restriction(r,seat,c['attacker'],'cannot_suspend')):
        raise RuntimeHalt('ATTACKER_CANNOT_SUSPEND')
    _scope(r,root,'DECLARE',attacker=c['attacker'],target=c['target'])
    if stack.played_turn is not None and (stack.played_turn>s.turn or
            (stack.ready_since_turn is not None and stack.ready_since_turn<=stack.played_turn)):
        raise RuntimeHalt('ATTACK_HISTORY_UNVERIFIED')
    if stack.played_turn==s.turn:raise RuntimeHalt('ATTACKER_PLAYED_THIS_TURN')
    if stack.ready_since_turn is None:
        if stack.played_turn is None:raise RuntimeHalt('ATTACK_HISTORY_UNVERIFIED')
    elif stack.ready_since_turn>s.turn:raise RuntimeHalt('ATTACKER_NOT_READY_THIS_TURN')
    other='B' if seat=='A' else 'A';target=c['target'];target_instance=''
    if target!='PLAYER':
        defender=s.battle[other].get(target)
        if defender is None or not defender.suspended:raise RuntimeHalt('ATTACK_TARGET_NOT_LEGAL')
        if r.context.card(other,defender.cards[-1].card_number).kind!='Digimon':
            raise RuntimeHalt('ATTACK_TARGET_NOT_DIGIMON')
        target_instance=_instance(r,defender)
    instance=_instance(r,stack)
    stack.suspended=True
    s.attack={'attacker':c['attacker'],'attacker_instance':instance,'target':target,
              'target_instance':target_instance,'controller':seat,'defender':other,
              'window':'COUNTER','counter_used':False,'block_used':False,'checked':None}
    from printed_triggers import trigger_lines
    from tamer_play_effects import PLAY_EFFECT,PLAY_LINE,tamer_play_usage
    from effect_scheduler import queue_effects
    top=stack.cards[-1]
    effects=[]
    if trigger_lines(r.context.card(seat,top.card_number).effect_text('main_text'),'When Attacking'):
        # Scope above proved this exact supported line; usage is shared with
        # the same printed effect's On Play and When Digivolving activations.
        if top.card_number!='EX13-022' or PLAY_LINE not in r.context.card(seat,top.card_number).effect_text('main_text').splitlines():
            raise RuntimeHalt('ATTACK_TRIGGER_UNSUPPORTED: '+top.card_number+' source='+top.key)
        effects.append({'seat':seat,'source':top.key,'effect_id':PLAY_EFFECT,'field':'main_text',
            'usage':list(tamer_play_usage(r,seat,top.key,PLAY_EFFECT)),
            'trigger':{'kind':'When Attacking','attacker':top.key,'target':target}})
    before=len(s.pending);queue_effects(r,effects)
    result={'attacker':c['attacker'],'target':target,'window':'COUNTER','full_match_credit':0}
    if len(s.pending)>before:result['triggered_effects']=[e['effect_id'] for e in s.pending[before:]]
    return result


def declare_attack(runtime,seat,attacker,target,root):
    return runtime._control_command('DECLARE_ATTACK',seat,
        {'attacker':attacker,'target':target,'rules':_evidence(root)},
        lambda r,s,c:_declare(r,s,c,root))


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
    if c['card'] is not None:raise RuntimeHalt('BLOCKER_NOT_LEGAL_IN_PLAIN_SCOPE')
    from printed_triggers import effect_headers
    from effect_grants import active_keyword,active_restriction
    for key,stack in r.state.battle[seat].items():
        if (r.context.card(seat,stack.cards[-1].card_number).kind!='Digimon' or stack.suspended
                or stack.statuses.get('cannot_suspend',False)
                or active_restriction(r,seat,key,'cannot_suspend')):
            continue
        printed=any(not effect_headers(line) and '＜Blocker＞' in line
            for index,source in enumerate(stack.cards)
            for line in r.context.card(seat,source.card_number).effect_text(
                'main_text' if index==len(stack.cards)-1 else 'inherited_text').splitlines())
        if printed or active_keyword(r,seat,key,'Blocker'):
            raise RuntimeHalt('BLOCKER_CHOICE_UNIMPLEMENTED: '+key)
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
    if 'effect_grants' in stack.statuses:
        from effect_grants import active_dp_bonus
        if active_dp_bonus(r,seat,stack.cards[-1].key):
            raise RuntimeHalt('BATTLE_DP_GRANT_UNSUPPORTED: '+stack.cards[-1].key)
    return r.context.card(seat,stack.cards[-1].card_number).to_dict()['dp']


def _confirm(r,seat,c,root):
    a=_window(r,seat,'CONFIRM');_scope(r,root,'CONFIRM');s=r.state;other=a['defender']
    attacker=s.battle[seat].get(a['attacker'])
    if attacker is None or attacker.instance_id!=a['attacker_instance']:
        a['window']='END';return {'success':False,'reason':'ATTACKER_LEFT_BATTLE'}
    if a['target']!='PLAYER':
        defender=s.battle[other].get(a['target'])
        if defender is None or defender.instance_id!=a['target_instance']:
            a['window']='END';return {'success':False,'reason':'TARGET_LEFT_BATTLE'}
        losses=battle_losers(_dp(r,seat,attacker),_dp(r,other,defender))
        from battlefield_scope import assert_combat_consequences_scope
        assert_combat_consequences_scope(r,[(owner,key) for label,owner,key in (
            ('ATTACKER',seat,a['attacker']),('DEFENDER',other,a['target'])) if label in losses])
        if 'ATTACKER' in losses:_delete(r,seat,a['attacker'])
        if 'DEFENDER' in losses:_delete(r,other,a['target'])
        a['window']='END';return {'success':True,'battle_losers':losses}
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
    from battlefield_scope import assert_combat_consequences_scope
    assert_combat_consequences_scope(r,[(seat,a['attacker'])] if 'ATTACKER' in losses else [],
                                     security_owner=other)
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
