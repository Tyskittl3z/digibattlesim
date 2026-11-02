"""Check effects relevant to one actual basic event, not hypothetical routes.

Self On Play/When Digivolving/When Attacking text on an existing object does not
observe another card's ordinary play. Unimplemented live observers remain
explicit dependencies instead of silently being skipped.
"""
import re
from context_runtime import RuntimeHalt
from printed_triggers import effect_headers, effect_body


def require_inert_for_event(runtime, owner, physical, field, action, event=None):
    definition=runtime.context.card(owner,physical.card_number)
    event=event or {}
    actor=event.get('seat',runtime.state.active)
    played_kind=None
    played_colors=None
    if event.get('card_number'):
        card=runtime.context.card(actor,event['card_number'])
        played_kind=card.kind
        played_colors=card.to_dict()['colors']
    elif action=='play_search':
        played_kind='Digimon'
    for line in definition.effect_text(field).splitlines():
        if line.lstrip().startswith(('・','•')):
            # Continuation of a separately activated Main/Delay effect.
            continue
        headers=effect_headers(line)
        if ('Your Turn' in headers and owner!=runtime.state.active
                or "Opponent's Turn" in headers and owner==runtime.state.active):
            continue
        # These timings refer to the source itself. No such event happened to
        # an existing source merely because a different card was played.
        if headers and not any(h in ('Your Turn',"Opponent's Turn",'All Turns') for h in headers):
            continue
        body=effect_body(line)
        clause=body.split(',',1)[0]
        if clause.startswith('When '):
            applies=False
            if action in ('play_plain','play_search') and re.search(r'\bplay(?:ed|s|ing)?\b',clause,re.I):
                if 'this card' in clause.lower() or 'this Digimon' in clause:
                    # The played hand card is not an already existing source.
                    continue
                if 'opponent' in clause.lower():
                    if actor==owner:continue
                elif any(p in clause for p in ('your ','you play','you would play')) and actor!=owner:
                    continue
                if 'Tamer' in clause and played_kind is not None and played_kind!='Tamer':continue
                if 'Digimon' in clause and played_kind is not None and played_kind!='Digimon':continue
                if 'blue' in clause.lower() and played_colors is not None and 'Blue' not in played_colors:continue
                applies=True
            elif action=='use_option' and re.search(r'\buse(?:d|s)?\b',clause,re.I):
                applies=True
            if applies:
                from tamer_play_effects import known_play_observer,OBSERVER_EFFECT
                if known_play_observer(physical.card_number,field,line):
                    runtime.registry.lookup(physical.card_number,OBSERVER_EFFECT,field)
                    continue
                raise RuntimeHalt('BASIC_EVENT_OBSERVER_UNIMPLEMENTED: '+physical.card_number
                                  +' '+field+' source='+physical.key+' event='+action)
            continue
        # The pinned contexts have no unimplemented persistent cost/prohibition
        # modifier for these procedures. Fail explicitly if one is present.
        if re.search(r"(?:can(?:not|'t)\s+(?:play|use|digivolve))|(?:play|use|digivolution) costs?",body,re.I):
            raise RuntimeHalt('BASIC_EVENT_COST_DEPENDENCY_UNIMPLEMENTED: '+physical.key)
