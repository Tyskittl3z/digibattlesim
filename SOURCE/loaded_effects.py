"""Fresh loaded Jupitermon/Toho on-play effects: exact-card, event-sourced judge.

Only effects whose trigger, eligible selections, and zone movements are implemented
are accepted. This is a reusable gameplay component, NOT a completed match engine.

A card is represented by a unique (card_number, physical copy number) tuple so
multi-trait search choices cannot accidentally select the same physical card twice.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import hashlib, json
from loaded_digivolution import BY_SEAT

class JudgeHalt(RuntimeError): pass
class IllegalSelection(ValueError): pass

@dataclass(frozen=True,order=True)
class Copy:
    card: str
    index: int
    def key(self):return f'{self.card}#{self.index}'

# Source-text-specific path whitelist; never infer rules for an unfamiliar card.
TWO_CATEGORY_SEARCH={
  'BT24-031':('Iliad','TS'),
  'BT25-022':('Iliad','TS'),
  'EX12-009':('Shambala','TB'),
}
SINGLE_CATEGORY_SEARCH={
  'BT24-083':'TS',
  'BT24-100':'TS',
  'EX12-075':'Shambala',
}
DISCARD_DRAW={
  'EX12-061':('Puppet','TB'),
  'BT24-088':('TS',), # Asuna also allows a card with Three Musketeers in its text; special rule below
  'BT26-104':('Shambala',),
}
EXPECTED_PHRASES={
  'BT24-031':'Reveal the top 3 cards of your deck. Add 1 card with the [Iliad] trait and 1 card with the [TS] trait',
  'BT25-022':'Reveal the top 3 cards of your deck. Add 1 [Iliad] trait card and 1 [TS] trait card',
  'EX12-009':'Reveal the top 3 cards of your deck. Add 1 card with the [Shambala] trait and 1 card with the [TB] trait',
  'BT24-083':'Reveal the top 3 cards of your deck. Add 1 card with the [TS] trait',
  'BT24-100':'Reveal the top 3 cards of your deck. Add 1 card with the [TS] trait',
  'EX12-075':'Reveal the top 3 cards of your deck. Add 1 [Shambala] trait card',
  'EX12-061':'By trashing 1 card with the [Puppet] or [TB] trait from your hand,',
  'BT24-088':'By trashing 1 card with [Three Musketeers] in its text or the [TS] trait from your hand,',
  'BT26-104':'By trashing 1 [Shambala] trait card from your hand,',
  'EX1-066':'Reveal the top 3 cards of your deck. Add 1 Digimon card among them to your hand. Trash the remaining cards.',
  'BT24-034':'By adding your top security card to the hand, you may play 1 [TS] trait Tamer card from your hand',
}

def _lookup(seat,card):
    if card not in BY_SEAT[seat]:raise IllegalSelection('Card not in owner\'s loaded deck')
    return BY_SEAT[seat][card]

def source_hash(seat,card):
    c=_lookup(seat,card)
    phrase=EXPECTED_PHRASES.get(card)
    if phrase is None or phrase not in c['card_text']:
        raise JudgeHalt('Effect source changed or effect not implemented: '+card)
    digest=hashlib.sha256(c['card_text'].encode('utf-8')).hexdigest()
    if digest!=c['card_text_sha256']:raise JudgeHalt('Card text sha mismatch: '+card)
    return digest

def matches(seat,copy,category):
    c=_lookup(seat,copy.card)
    return category in c['traits']

@dataclass
class MatchZones:
    seat:str
    deck:list[Copy]  # top of deck = last element
    hand:list[Copy]
    trash:list[Copy]
    security:list[Copy]
    battle:list[Copy]
    effects:list[dict]
    statuses:dict=field(default_factory=dict)
    def count(self):return len(self.deck)+len(self.hand)+len(self.trash)+len(self.security)+len(self.battle)
    def fingerprint(self):
        value={k:[x.key() for x in getattr(self,k)] for k in ('deck','hand','trash','security','battle')}
        value['statuses']=self.statuses
        return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def options_for_search(z,source):
    source_hash(z.seat,source)
    if source in TWO_CATEGORY_SEARCH:
        a,b=TWO_CATEGORY_SEARCH[source]
        preview=z.deck[-3:][::-1]
        return {'revealed':[c.key() for c in preview],
                'category_1':[c.key() for c in preview if matches(z.seat,c,a)],
                'category_2':[c.key() for c in preview if matches(z.seat,c,b)]}
    if source in SINGLE_CATEGORY_SEARCH:
        a=SINGLE_CATEGORY_SEARCH[source]
        preview=z.deck[-3:][::-1]
        return {'revealed':[c.key() for c in preview],
                'category_1':[c.key() for c in preview if matches(z.seat,c,a)],
                'category_2':[]}
    raise JudgeHalt('No search effect handler: '+source)

def resolve_search(z,source,choose1=None,choose2=None,bottom_order=None):
    """Selection is optional up to one in each category; distinct physical copies.
    Any unselected cards return to deck bottom in player's selected order.
    """
    before=z.count();digest=source_hash(z.seat,source);valid=options_for_search(z,source)
    chosen=[c for c in (choose1,choose2) if c is not None]
    # Official Q3489/Q1822: a non-optional 'Add 1 ... and 1 ...'
    # instruction must add the maximum possible number of eligible cards.
    candidates_1=[None,*valid['category_1']]
    candidates_2=[None,*valid['category_2']]
    max_pick=max((int(a is not None)+int(b is not None) for a in candidates_1 for b in candidates_2
                  if a is None or b is None or a!=b),default=0)
    if len(chosen)!=max_pick:raise IllegalSelection(f'Must add {max_pick} eligible physical cards')
    if choose1 is not None and choose1 not in valid['category_1']:
        raise IllegalSelection('First search pick does not qualify')
    if choose2 is not None and choose2 not in valid['category_2']:
        raise IllegalSelection('Second search pick does not qualify')
    if len(set(chosen))!=len(chosen):raise IllegalSelection('Same physical card cannot be selected twice')
    extras=[x for x in valid['revealed'] if x not in chosen]
    if bottom_order is None:bottom_order=extras
    if sorted(bottom_order)!=sorted(extras) or len(bottom_order)!=len(extras):
        raise IllegalSelection('Deck-bottom order must contain exactly unselected revealed cards')
    # The official bottom order lists first bottom card first. Top is list[-1].
    pre=z.fingerprint();reveal_count=len(valid['revealed']);revealed=[z.deck.pop() for _ in range(reveal_count)]
    available={c.key():c for c in revealed}
    z.hand.extend(available[k] for k in chosen)
    z.deck[:0]=[available[k] for k in bottom_order]
    assert z.count()==before
    event={'type':'JUDGE_SEARCH_RESOLVED','owner':z.seat,'source':source,'source_sha256':digest,
           'reveal':valid['revealed'],'to_hand':chosen,'to_bottom':bottom_order,'state_before':pre,'state_after':z.fingerprint()}
    z.effects.append(event)
    return event

def discard_candidates(z,source):
    source_hash(z.seat,source)
    if source not in DISCARD_DRAW:raise JudgeHalt('Discard/draw handler not implemented')
    categories=DISCARD_DRAW[source]
    return [c.key() for c in z.hand if any(matches(z.seat,c,t) for t in categories) or
            (source=='BT24-088' and 'Three Musketeers' in _lookup(z.seat,c.card)['card_text'])]

def resolve_discard_draw(z,source,discard=None):
    """Decline by discard=None; if paid, discard one qualifying card, then draw two."""
    before=z.count();digest=source_hash(z.seat,source)
    allowed=discard_candidates(z,source)
    if discard is not None and discard not in allowed:raise IllegalSelection('Ineligible card for discard/draw cost')
    pre=z.fingerprint();drawn=[]
    if discard is not None:
        choice=next(c for c in z.hand if c.key()==discard)
        z.hand.remove(choice);z.trash.append(choice)
        for _ in range(2):
            if z.deck:
                card=z.deck.pop();z.hand.append(card);drawn.append(card.key())
    assert z.count()==before
    event={'type':'JUDGE_DISCARD_DRAW_RESOLVED','owner':z.seat,'source':source,'source_sha256':digest,
           'discarded':discard,'drawn':drawn,'state_before':pre,'state_after':z.fingerprint()}
    z.effects.append(event)
    return event

ANALOG_YOUTH_ID='EX1-066'
AEGIOMON_FREE_TAMER_ID='BT24-034'

def resolve_analog_youth(z,chosen=None):
    """EX1-066: reveal three, add one Digimon if any, trash remaining."""
    if z.seat!='B':raise IllegalSelection('Analog Youth outside loaded owner deck')
    source_hash(z.seat,ANALOG_YOUTH_ID)
    revealed=z.deck[-3:][::-1]
    eligible=[c.key() for c in revealed if 'Digimon' in _lookup(z.seat,c.card)['type']]
    if chosen not in eligible and chosen is not None:raise IllegalSelection('Analog Youth selection not a revealed Digimon')
    if bool(eligible)!=(chosen is not None):raise IllegalSelection('Analog Youth must take a Digimon if available')
    before=z.count();pre=z.fingerprint();for_trash=[]
    for _ in range(len(revealed)):
        c=z.deck.pop()
        if c.key()==chosen:z.hand.append(c)
        else:
            z.trash.append(c);for_trash.append(c.key())
    assert z.count()==before
    event={'type':'ANALOG_YOUTH_ON_PLAY','source':ANALOG_YOUTH_ID,'owner':z.seat,
           'reveal':[c.key() for c in revealed],'added':chosen,'trashed':for_trash,
           'source_sha256':source_hash(z.seat,ANALOG_YOUTH_ID),
           'state_before':pre,'state_after':z.fingerprint()}
    z.effects.append(event)
    return event


def eligible_free_tamers(z,include_top_security=False):
    if z.seat!='A':raise IllegalSelection('Aegiomon effect outside loaded owner deck')
    source_hash(z.seat,AEGIOMON_FREE_TAMER_ID)
    names={_lookup(z.seat,c.card)['name'] for c in z.battle
           if _lookup(z.seat,c.card)['type']=='Tamer'}
    options=list(z.hand)
    if include_top_security and z.security:
        options.append(z.security[-1])
    return [c.key() for c in options if _lookup(z.seat,c.card)['type']=='Tamer'
            and 'TS' in _lookup(z.seat,c.card)['traits']
            and _lookup(z.seat,c.card)['name'] not in names]


def resolve_aegiomon_tamer(z,selected=None,pay_security_only=False):
    """BT24-034: optional security-to-hand cost to play eligible TS Tamer.

    Only the movement is resolved here; the newly played Tamer's separate On
    Play trigger must be resolved by the caller before advancing the game.
    """
    before=z.count();digest=source_hash(z.seat,AEGIOMON_FREE_TAMER_ID)
    legal=eligible_free_tamers(z,include_top_security=True)
    if selected is not None and selected not in legal:raise IllegalSelection('Ineligible TS Tamer')
    if (selected is not None or pay_security_only) and not z.security:
        raise IllegalSelection('Cannot pay security card cost')
    pre=z.fingerprint();security_removed=None
    if selected is not None or pay_security_only:
        sec=z.security.pop();z.hand.append(sec);security_removed=sec.key()
    if selected is not None:
        selected_card=next(c for c in z.hand if c.key()==selected)
        z.hand.remove(selected_card);z.battle.append(selected_card)
    assert z.count()==before
    event={'type':'AEGIOMON_PLAY_TAMER','owner':z.seat,'source':AEGIOMON_FREE_TAMER_ID,
           'source_sha256':digest,'selected':selected,'security_to_hand':security_removed,
           'requires_tamer_on_play_resolution':selected is not None,
           'state_before':pre,'state_after':z.fingerprint()}
    z.effects.append(event)
    return event

# Precisely scoped no-target branches observed on first-turn openings.
# This deliberately is NOT a fallback for later board states.
EMPTY_OPPONENT_ONLY={
  'EX12-046':'Give 1 of your opponent\'s Digimon',
  'EX12-062':'By deleting 1 of your Digimon, delete 1 of your opponent\'s level 4 or lower Digimon',
  'EX12-026':'Trash the bottom 2 digivolution cards of 1 of your opponent\'s Digimon',
  'BT26-013':'By trashing 1 card in your hand, delete 1 of your opponent\'s Digimon',
  'EX12-063':'Suspend 1 of your opponent\'s Digimon or Tamers',
}
EXPECTED_PHRASES.update(EMPTY_OPPONENT_ONLY)

def resolve_no_target_branch(z,source,opponent_has_digimon=False,opponent_has_tamer=False):
    """Only a no-target, declined-cost On Play branch.

    If the opponent has a target, the full card interaction must be judged.
    The verifier MUST NOT use this branch in nonempty opposing board states.
    """
    digest=source_hash(z.seat,source)
    if source not in EMPTY_OPPONENT_ONLY:
        raise JudgeHalt('Not an approved no-target branch')
    if opponent_has_digimon or opponent_has_tamer:
        raise JudgeHalt(f'Full targeted interaction still unverified for {source}')
    ev={'type':'VERIFIED_EMPTY_OPPONENT_BRANCH','owner':z.seat,'source':source,
        'source_sha256':digest,'no_targets':True,
        'optional_cost_paid':False,'state_sha256':z.fingerprint()}
    z.effects.append(ev)
    return ev


def _on_deletion_trigger(seat,card):
    import re
    txt=_lookup(seat,card)['card_text']
    return any('[On Deletion]' in (re.match(r'^\s*(?:\[[^\]]+\]\s*)+',line) or [''])[0]
               for line in txt.splitlines())

def _delete_plain_digimon(z,key):
    """Only hard-played single-card Digimon with no On Deletion effect.
    Anything with an unresolved replacement, protective, source or trigger path HALTS.
    """
    cards=[c for c in z.battle if c.key()==key]
    if len(cards)!=1:raise IllegalSelection('Target not a single-card Digimon')
    c=cards[0]
    if _lookup(z.seat,c.card)['type'] not in ('Digimon','Digimon/Tamer'):
        raise IllegalSelection('Target must be Digimon')
    if _on_deletion_trigger(z.seat,c.card):
        raise JudgeHalt('On Deletion resolution required for '+c.card)
    z.battle.remove(c);z.trash.append(c)
    return c.key()


def resolve_encountered_target(z,opponent,source,paid=True):
    """Targeted first-paid-action branches for Toho's observed cards only.

    Limitation: opponent's battlefield Digimon are one-card hard plays; no
    digivolution sources, effects which prevent deletion, or nested triggers.
    Unmodeled board state must be rejected before calling this handler.
    """
    if z.seat!='B' or source not in ('BT26-013','EX12-026','EX12-062'):
        raise JudgeHalt('Targeted handler only certified for observed Toho sources')
    digest=source_hash('B',source)
    own_before=z.count();op_before=opponent.count()
    pre=(z.fingerprint(),opponent.fingerprint())
    targets=[c for c in opponent.battle if _lookup(opponent.seat,c.card)['type'] in ('Digimon','Digimon/Tamer')]
    if not targets:
        return resolve_no_target_branch(z,source)
    if any(_on_deletion_trigger(opponent.seat,c.card) for c in targets):
        raise JudgeHalt('Opponent has unresolved On Deletion effect')
    if source=='EX12-026':
        # Opening board target has no stacked cards. Bottom-2 trash is empty.
        chosen=sorted(targets)[0]
        opponent.statuses[chosen.key()]={'cant_attack':True,'cant_block':True,
              'expires':'end_of_affected_player_next_turn'}
        ev={'type':'SHELLMON_NO_SOURCES_ATTACK_BLOCK_LOCK','source':source,
            'affected':chosen.key(),'trashed_sources':[],
            'source_sha256':digest}
    elif source=='BT26-013':
        qualified=[c for c in targets if int(_lookup(opponent.seat,c.card)['level'] or 0)>0]
        # DP comes from the exact loaded card's pinned numeric metadata.
        from seeded_opening_probe import COSTS
        qualified=[c for c in qualified if COSTS[c.card]['dp'] is not None and COSTS[c.card]['dp']<=6000]
        if not qualified or not z.hand or not paid:
            ev={'type':'MUSYAMON_DECLINED','source':source,'source_sha256':digest}
        else:
            discarded=min(z.hand);z.hand.remove(discarded);z.trash.append(discarded)
            target=min(qualified)
            deleted=_delete_plain_digimon(opponent,target.key())
            ev={'type':'MUSYAMON_DISCARD_DELETE','source':source,'source_sha256':digest,
                 'discarded':discarded.key(),'deleted':deleted}
    else:  # EX12-062 Kokeshimon
        targetable=[c for c in targets if (_lookup(opponent.seat,c.card)['level'] or 99)<=4]
        own_eligible=[c for c in z.battle if _lookup(z.seat,c.card)['type'] in ('Digimon','Digimon/Tamer')]
        if not paid or not targetable or not own_eligible:
            ev={'type':'KOKESHIMON_DECLINED','source':source,'source_sha256':digest}
        else:
            sacrificed=min(own_eligible)
            own_key=_delete_plain_digimon(z,sacrificed.key())
            destroyed=min(targetable)
            opp_key=_delete_plain_digimon(opponent,destroyed.key())
            ev={'type':'KOKESHIMON_COST_DELETE','source':source,'source_sha256':digest,
                 'own_deleted':own_key,'opponent_deleted':opp_key}
    assert own_before==z.count() and op_before==opponent.count()
    ev.update({'owner':z.seat,'opponent':opponent.seat,
               'self_before':pre[0],'opponent_before':pre[1],
               'self_after':z.fingerprint(),'opponent_after':opponent.fingerprint()})
    z.effects.append(ev)
    return ev
