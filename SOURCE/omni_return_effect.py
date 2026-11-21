"""BT20-102's mandatory Then return, including a false preceding If."""
import hashlib

from context_runtime import MechanicBinding, RuntimeHalt
from effect_scheduler import pending_options, queue_effects
from match_context import require
from return_effects import inherited_return_replacements, replacement_effect_id, return_to_deck_bottom

EFFECT = 'BT20-102.on_play_digivolving'
LINE = ("[On Play] [When Digivolving] If [Omnimon] or [X Antibody] "
        "is in this Digimon's digivolution cards, choose 1 of both players' Digimon and "
        "delete all other Digimon. Then, return 1 of your opponent's Digimon to the bottom of the deck.")


def omni_return_choices(runtime, seat, source_key):
    source=runtime._source(seat,source_key,'main_text')
    expected=(EFFECT,seat,source_key,'main_text')
    activated=getattr(runtime,'_activated_effect',None)
    inside=isinstance(activated,tuple) and len(activated)==5 and activated[:4]==expected and activated[4] is not None
    if source.card_number!='BT20-102' or (not inside and not any(
            tuple(p[k] for k in ('effect_id','seat','source','field'))==expected
            for p in pending_options(runtime,seat))):
        raise RuntimeHalt('OMNIMON_RETURN_WINDOW_REQUIRED')
    opponent='B' if seat=='A' else 'A'
    targets=[key for key,stack in runtime.state.battle[opponent].items()
             if runtime.context.card(opponent,stack.cards[-1].card_number).kind=='Digimon']
    return sorted(targets) if targets else [None]


def resolve_omni_return(runtime,seat,source_key,choice):
    if choice not in omni_return_choices(runtime,seat,source_key):
        raise RuntimeHalt('OMNIMON_RETURN_TARGET_INVALID')
    if choice is None:
        return {'processing':'NO_ELIGIBLE_TARGET','returned':None,'full_match_credit':0}
    opponent='B' if seat=='A' else 'A'
    replacements=inherited_return_replacements(runtime,seat,opponent,choice)
    if replacements:
        stack=runtime.state.battle[opponent][choice]
        queue_effects(runtime,[{'seat':opponent,'source':replacement_source,
            'effect_id':replacement_effect_id(runtime,opponent,replacement_source),
            'field':'inherited_text','trigger':{'kind':'OPPONENT_EFFECT_RETURN',
                'actor':seat,'target':choice,'target_instance':stack.instance_id,
                'source_effect':EFFECT}}
            for replacement_source,_ in replacements])
        return {'processing':'RETURN_REPLACEMENT_PENDING','target':choice,
                'returned':None,'full_match_credit':0}
    moved=return_to_deck_bottom(runtime,seat,opponent,[choice],[choice],
                                halt_prefix='OMNIMON_RETURN')
    return {'processing':'RETURNED_TO_DECK_BOTTOM','target':choice,
            'returned':moved['returned'][0],'trashed_sources':moved['trashed_sources'],
            'full_match_credit':0}


def omni_return_bindings(context,root,rules):
    from selected_mechanics import _source_evidence
    bindings=[]
    for card in context.cards:
        if card.number!='BT20-102':continue
        require(LINE in card.effect_text('main_text').splitlines(),
                'BT20-102 On Play/When Digivolving wording changed')
        evidence=_source_evidence(root,card.to_dict()['official_source'],
            '#BT20-102 On Play/When Digivolving, Q4725; CR15-8-3')
        bindings.append(MechanicBinding(card.number,EFFECT,'main_text',card.definition_sha256,
            hashlib.sha256(card.effect_text('main_text').encode()).hexdigest(),
            (evidence,rules),resolve_omni_return))
    return tuple(bindings)
