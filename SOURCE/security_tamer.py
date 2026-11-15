"""The encountered exact-text immediate Security Tamer play (CR15-16-10-2).

The checked card is briefly outside every area inside one atomic attack
command. Its mandatory Security effect has no player choice or pending record;
ordinary effects caused by its play are queued after it enters the battle area.
"""
from dataclasses import dataclass,replace
import hashlib
from pathlib import Path

from context_runtime import MechanicBinding,PhysicalCard,RuntimeHalt
from match_context import require

SECURITY_TAMER_LINE = '[Security] Play this card without paying the cost.'
SECURITY_TAMER_MEMORY_LINE = '[Security] Play this card without paying its memory cost.'
RULE_LOCATOR = ('Comprehensive rules v4.3: 3-4-3; 7-1-3; 13-1-6; 13-1-8-1; '
                '13-1-8-2; 13-1-8-4; 15-4; 15-16-2-1; 15-16-10-1 through 15-16-10-2')


def security_tamer_spec(definition):
    """One pinned wording template, scoped to the selected context's Tamers."""
    text = definition.effect_text('security_text')
    if definition.kind=='Tamer' and text in (SECURITY_TAMER_LINE, SECURITY_TAMER_MEMORY_LINE):
        return definition.number+'.security_play',text
    return None


@dataclass(frozen=True)
class _SecurityActivation:
    physical: PhysicalCard
    effect_id: str
    attack: dict
    definition_sha256: str
    text_sha256: str
    root: Path


def _confirm_window(runtime,seat):
    attack=runtime.state.attack
    if (runtime.halted or runtime.state.terminal or not runtime.allow_experimental
            or attack is None or attack['window']!='CONFIRM' or attack['target']!='PLAYER'
            or attack['defender']!=seat or attack['controller']!=runtime.state.active):
        raise RuntimeHalt('SECURITY_TAMER_WINDOW_REQUIRED')
    return attack


def validate_security_activation(runtime,seat,source_key):
    """A checked no-area card can be played only by its active Security effect."""
    attack=_confirm_window(runtime,seat)
    proof=getattr(runtime,'_security_activation',None)
    activated=getattr(runtime,'_activated_effect',None)
    if (not isinstance(proof,_SecurityActivation) or proof.attack is not attack
            or proof.physical.owner!=seat or proof.physical.key!=source_key
            or attack['checked']!=source_key
            or activated!=(proof.effect_id,seat,source_key,'security_text',None)):
        raise RuntimeHalt('SECURITY_TAMER_WINDOW_REQUIRED')
    physical=proof.physical
    definition=runtime.context.card(seat,physical.card_number)
    spec=security_tamer_spec(definition)
    if (spec is None or spec[0]!=proof.effect_id or definition.kind!='Tamer'
            or definition.effect_text('security_text')!=spec[1]
            or definition.definition_sha256!=proof.definition_sha256
            or hashlib.sha256(definition.effect_text('security_text').encode()).hexdigest()!=proof.text_sha256):
        raise RuntimeHalt('SECURITY_TAMER_WINDOW_REQUIRED')
    # The proof names the card removed from the actual checked position. It
    # isn't a second copy in hand, trash, security or an existing field object.
    present=[c for zone in runtime.state.zones[seat].values() for c in zone]
    present += runtime.state.breeding[seat]
    present += [c for stack in runtime.state.battle[seat].values() for c in stack.cards]
    if any(c.key==source_key for c in present):
        raise RuntimeHalt('SECURITY_TAMER_WINDOW_REQUIRED')
    binding=runtime.registry.lookup(physical.card_number,proof.effect_id,'security_text')
    if (binding.definition_sha256!=proof.definition_sha256 or binding.text_sha256!=proof.text_sha256
            or binding.handler is not resolve_security_tamer):
        raise RuntimeHalt('SECURITY_TAMER_BINDING_MISMATCH')
    return physical


def resolve_security_tamer(runtime,seat,source_key,choice):
    if choice is not None:raise RuntimeHalt('SECURITY_TAMER_CHOICE_INVALID')
    validate_security_activation(runtime,seat,source_key)
    from main_actions import play_tamer_from_security
    return play_tamer_from_security(runtime,seat,source_key,runtime._security_activation.root)


def resolve_checked_tamer(runtime,seat,physical,root):
    """Resolve this sole mandatory Security effect inside CONFIRM_ATTACK."""
    attack=_confirm_window(runtime,seat)
    security=runtime.state.zones[seat]['security']
    if not security or physical!=security[-1] or attack['checked'] is not None:
        raise RuntimeHalt('SECURITY_TAMER_CHECKED_SOURCE_REQUIRED')
    definition=runtime.context.card(seat,physical.card_number)
    spec=security_tamer_spec(definition)
    if spec is None or definition.kind!='Tamer' or definition.effect_text('security_text')!=spec[1]:
        raise RuntimeHalt('SECURITY_CARD_UNSUPPORTED: '+physical.card_number+' source='+physical.key)
    effect=spec[0];text_sha=hashlib.sha256(spec[1].encode()).hexdigest()
    binding=runtime.registry.lookup(physical.card_number,effect,'security_text')
    if (binding.definition_sha256!=definition.definition_sha256 or binding.text_sha256!=text_sha
            or binding.handler is not resolve_security_tamer):
        raise RuntimeHalt('SECURITY_TAMER_BINDING_MISMATCH')
    from selected_mechanics import _source_evidence
    evidence=_source_evidence(root,definition.to_dict()['official_source'],
        '#'+physical.card_number+' exact mandatory Security play; '+RULE_LOCATOR).manifest()
    proof=_SecurityActivation(physical,effect,attack,definition.definition_sha256,text_sha,Path(root))
    security.pop();attack['checked']=physical.key
    missing=object()
    previous={name:getattr(runtime,name,missing) for name in ('_security_activation','_activated_effect','_resolution_depth')}
    runtime._security_activation=proof
    runtime._activated_effect=(effect,seat,physical.key,'security_text',None)
    runtime._resolution_depth=getattr(runtime,'_resolution_depth',-1)+1
    try:
        play=binding.handler(runtime,seat,physical.key,None)
    finally:
        for name,value in previous.items():
            if value is missing:delattr(runtime,name)
            else:setattr(runtime,name,value)
    attack['window']='END'
    return {'success':True,'checked_card':physical.key,'security_effect':effect,
            'attacker_deleted':False,'security_card_deleted':False,'source':evidence,
            'play':play,'steps':[{'operation':'REVEAL_SECURITY_CARD','card':physical.key},
                {'operation':'ACTIVATE_SECURITY_EFFECT_IMMEDIATELY','effect_id':effect,
                 'field':'security_text','source_area':None},
                {'operation':'PLAY_CHECKED_TAMER','card':physical.key,'cost':0}],
            'full_match_credit':0}


def security_tamer_bindings(context,root,rules):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        spec=security_tamer_spec(card)
        if spec is None:continue
        effect,line=spec
        require(card.kind=='Tamer' and card.effect_text('security_text')==line,
                'Exact Security Tamer wording changed: '+card.number)
        evidence=_source_evidence(root,card.to_dict()['official_source'],
                                  '#'+card.number+' mandatory Security play from checked no-area card')
        bindings.append(MechanicBinding(card.number,effect,'security_text',card.definition_sha256,
            hashlib.sha256(line.encode()).hexdigest(),(evidence,replace(rules,locator=RULE_LOCATOR)),
            resolve_security_tamer))
    return tuple(bindings)
