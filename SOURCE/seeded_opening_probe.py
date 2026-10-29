"""Run 60 reproducible *opening-turn probes*, not 60 valid games.

This test uses only the two user's loaded decks. It exercises actual seeded
opening hands, security, hatch, optional zero-cost rookie evolutions, and
pay-to-play On Play effects currently verified for these cards. Any unsupported
trigger is reported as HALT and no game/win is credited. No old roadmap is used.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib,json,random,re
from loaded_digivolution import MANIFEST, BY_SEAT, legal_printed_evolutions
from loaded_effects import (Copy,MatchZones,options_for_search,resolve_search,discard_candidates,
                            resolve_discard_draw,TWO_CATEGORY_SEARCH,SINGLE_CATEGORY_SEARCH,
                            DISCARD_DRAW,JudgeHalt,resolve_analog_youth,resolve_aegiomon_tamer,
                            eligible_free_tamers,EMPTY_OPPONENT_ONLY,resolve_no_target_branch)

ROOT=Path(__file__).resolve().parent
COSTS=json.loads((ROOT/'LOADED_EXACT_COSTS.json').read_text())
SEED_SALT='jup-toho-fresh-v1-opening-probe'

def seed_for(i):
    return int(hashlib.sha256(f'{SEED_SALT}|{i}'.encode()).hexdigest()[:16],16)

def setup(seat,rng):
    data=MANIFEST['decks'][seat]
    main=[Copy(c['card_number'],i) for c in data['card_manifest'] if c['zone']=='main' for i in range(1,c['qty']+1)]
    eggs=[Copy(c['card_number'],i) for c in data['card_manifest'] if c['zone']=='eggs' for i in range(1,c['qty']+1)]
    assert len(main)==50 and len(eggs)==4
    rng.shuffle(main);rng.shuffle(eggs)
    security=[main.pop() for _ in range(5)];hand=[main.pop() for _ in range(5)]
    z=MatchZones(seat,main,hand,[],security,[],[])
    return z,eggs

def _select_main_action(z):
    """Deterministic diagnostic play choice; does NOT represent learned strategy."""
    playable=[c for c in z.hand if COSTS[c.card]['type'] in ('Digimon','Tamer')]
    if not playable:return None
    return min(playable,key=lambda c:(COSTS[c.card]['play_cost'],c.card,c.index))

def _search_choice(options):
    allowed_1=[None,*options['category_1']];allowed_2=[None,*options['category_2']]
    valid=[(a,b) for a in allowed_1 for b in allowed_2 if a is None or b is None or a!=b]
    maximum=max(sum(x is not None for x in p) for p in valid)
    return sorted((p for p in valid if sum(x is not None for x in p)==maximum),key=lambda p:(p[0] or '',p[1] or ''))[0]

def run_opening(i):
    seed=seed_for(i);rng=random.Random(seed)
    first='A' if i%2==0 else 'B'
    z,eggs=setup(first,rng)
    base_count=z.count()
    events=[{'type':'SETUP','first':first,'seed':seed,'hand':[c.key() for c in z.hand],
             'security_count':len(z.security),'deck_count':len(z.deck)}]
    egg=eggs.pop()
    # Breeding hatch is always available, as the egg deck still has cards.
    events.append({'type':'HATCH','egg':egg.key()})
    rookie_choices=[]
    for c in z.hand:
        if BY_SEAT[first][c.card]['level']==3 and legal_printed_evolutions(first,egg.card,c.card,security_count=5):
            rookie_choices.append(c)
    if rookie_choices:
        chosen=sorted(rookie_choices,key=lambda c:(c.card,c.index))[0]
        z.hand.remove(chosen)
        # Separate breeding source: not in the battle area, cannot attack/trigger on play.
        breeding=[egg,chosen]
        events.append({'type':'BREEDING_EVOLVE','from':egg.key(),'to':chosen.key(),
                       'cost':legal_printed_evolutions(first,egg.card,chosen.card,5)[0].cost})
        # Every digivolution draws one, including evolution in breeding.
        if z.deck:
            drawn=z.deck.pop();z.hand.append(drawn)
            events.append({'type':'EVOLUTION_DRAW','card':drawn.key()})
    else:
        breeding=[egg]
    # First player skips draw phase; true current game turn is 1.
    played=_select_main_action(z)
    if played is None:
        events.append({'type':'PASS','reason':'no Digimon/Tamer in remaining hand'})
        return {'index':i,'first':first,'seed':seed,'verified_effects':0,'status':'PARTIAL_OPENING_ONLY',
                'events':events,'no_winner':True}
    z.hand.remove(played);z.battle.append(played)
    events.append({'type':'PAID_PLAY','card':played.key(),'printed_play_cost':COSTS[played.card]['play_cost']})
    txt=BY_SEAT[first][played.card]['card_text']
    # Match a trigger tag in the line-leading tag run, not references to
    # '[On Play]' buried in another effect's text (e.g. Homeros).
    has_onplay=any('[On Play]' in (re.match(r'^\s*(?:\[[^\]]+\]\s*)+',line) or [''])[0]
                   for line in txt.splitlines())
    verified=0
    if has_onplay:
        if played.card in TWO_CATEGORY_SEARCH or played.card in SINGLE_CATEGORY_SEARCH:
            opts=options_for_search(z,played.card)
            a,b=_search_choice(opts)
            events.append(resolve_search(z,played.card,a,b))
            verified+=1
        elif played.card in DISCARD_DRAW:
            candidates=discard_candidates(z,played.card)
            paid=min(candidates) if candidates else None
            events.append(resolve_discard_draw(z,played.card,paid))
            verified+=1
        elif played.card=='EX1-066':
            revealed=z.deck[-3:][::-1]
            eligible=sorted(x.key() for x in revealed if 'Digimon' in BY_SEAT[first][x.card]['type'])
            events.append(resolve_analog_youth(z,eligible[0] if eligible else None))
            verified+=1
        elif played.card=='BT24-034':
            tamer_options=eligible_free_tamers(z,include_top_security=True) if z.security else []
            target=min(tamer_options) if tamer_options else None
            events.append(resolve_aegiomon_tamer(z,target))
            verified+=1
            if target:
                tamer_id=target.split('#')[0]
                if tamer_id in SINGLE_CATEGORY_SEARCH:
                    opts=options_for_search(z,tamer_id)
                    a,b=_search_choice(opts)
                    events.append(resolve_search(z,tamer_id,a,b))
                    verified+=1
                elif tamer_id in DISCARD_DRAW:
                    discards=discard_candidates(z,tamer_id)
                    events.append(resolve_discard_draw(z,tamer_id,min(discards) if discards else None))
                    verified+=1
        elif played.card in EMPTY_OPPONENT_ONLY:
            # First-player turn: opposing board is empty from setup.
            events.append(resolve_no_target_branch(z,played.card))
            verified+=1
        else:
            events.append({'type':'UNVERIFIED_ON_PLAY','card':played.card,'text_sha256':BY_SEAT[first][played.card]['card_text_sha256']})
    # All off-turn/continuous and newly triggered effects remain outside this scoped probe.
    assert z.count()+len(breeding)-1==base_count,(z.count(),len(breeding),base_count)
    events.append({'type':'HALT_BEFORE_UNIMPLEMENTED_FULL_TURN','unverified_on_play':bool(has_onplay and not verified),
                   'frozen_game_count':0})
    return {'index':i,'first':first,'seed':seed,'verified_effects':verified,
            'status':'PARTIAL_OPENING_ONLY','events':events,'no_winner':True}

def report(count=60):
    rows=[run_opening(i) for i in range(count)]
    counts=Counter(e['type'] for row in rows for e in row['events'])
    side=Counter(x['first'] for x in rows)
    return {'schema':'jup-toho-opening-probe-v1','description':'Seeded incomplete opening-turn probes; not full games',
            'requested_probes':count,'first_side_counts':dict(side),'valid_fact_finding_games':0,
            'match_results':None,'event_counts':dict(sorted(counts.items())),
            'first_unverified_cards':dict(Counter(e['card'] for row in rows for e in row['events'] if e['type']=='UNVERIFIED_ON_PLAY')),
            'rows':rows}

if __name__=='__main__':
    data=report()
    (ROOT/'OPENING_60_PROBES.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'},indent=2))
