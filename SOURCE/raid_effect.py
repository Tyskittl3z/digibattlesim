"""Explicit BT20-102 Raid target switch at its attack timing."""
import hashlib

from context_runtime import MechanicBinding,RuntimeHalt
from effect_scheduler import pending_options
from match_context import require

EFFECT='BT20-102.raid_target'
LINE='＜Raid＞ ＜Piercing＞ ＜Blocker＞'


def raid_choices(runtime,seat,source_key):
    source=runtime._source(seat,source_key,'main_text')
    attack=runtime.state.attack
    expected=(EFFECT,seat,source_key,'main_text')
    activated=getattr(runtime,'_activated_effect',None)
    inside=isinstance(activated,tuple) and len(activated)==5 and activated[:4]==expected and activated[4] is not None
    if (source.card_number!='BT20-102' or attack is None
            or attack['controller']!=seat or attack['attacker']!=source_key
            or attack['window']!='COUNTER'
            or (not inside and not any(tuple(p[k] for k in
                ('effect_id','seat','source','field'))==expected for p in pending_options(runtime,seat)))):
        raise RuntimeHalt('RAID_ATTACK_WINDOW_REQUIRED')
    from attack_flow import _dp
    owner=attack['defender']
    targets=[(key,_dp(runtime,owner,stack)) for key,stack in runtime.state.battle[owner].items()
             if not stack.suspended
             and runtime.context.card(owner,stack.cards[-1].card_number).kind=='Digimon']
    if not targets:return [None]
    highest=max(dp for _,dp in targets)
    return [None]+sorted(key for key,dp in targets if dp==highest)


def resolve_raid(runtime,seat,source_key,choice):
    if choice not in raid_choices(runtime,seat,source_key):
        raise RuntimeHalt('RAID_TARGET_INVALID')
    attack=runtime.state.attack
    previous=attack['target']
    if choice is None:
        return {'processing':'OPTIONAL_RAID_DECLINED','previous_target':previous,
                'target':previous,'full_match_credit':0}
    from attack_flow import _instance
    target=runtime.state.battle[attack['defender']][choice]
    attack['target']=choice
    attack['target_instance']=_instance(runtime,target)
    return {'processing':'RAID_TARGET_SWITCHED','previous_target':previous,
            'target':choice,'full_match_credit':0}


def raid_bindings(context,root,rules):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number!='BT20-102':continue
        require(LINE in card.effect_text('main_text').splitlines(),
                'BT20-102 Raid keyword wording changed')
        evidence=_source_evidence(root,card.to_dict()['official_source'],
            '#BT20-102 Raid; CR16-23-1 through 16-23-4')
        bindings.append(MechanicBinding(card.number,EFFECT,'main_text',card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence,rules),resolve_raid))
    return tuple(bindings)
