"""Paired two-seat early-game diagnostic; never generates match winners.

Real physical 50+4 zones for both decks, with a single shared seeded shuffle,
actual draw/evolution checks, and verified On Play handlers for loaded cards.
It stops after each seat's first paid main action or when an effect has no
certified targeted path. The action selector is deterministic, NOT trained.
"""
from __future__ import annotations
import json,random,re
from collections import Counter
from pathlib import Path
from loaded_effects import (options_for_search,resolve_search,resolve_discard_draw,
  discard_candidates,resolve_aegiomon_tamer,eligible_free_tamers,
  resolve_analog_youth,resolve_no_target_branch,EMPTY_OPPONENT_ONLY,
  TWO_CATEGORY_SEARCH,SINGLE_CATEGORY_SEARCH,DISCARD_DRAW,JudgeHalt,resolve_encountered_target)
from seeded_opening_probe import setup,seed_for,_search_choice,_select_main_action,COSTS
from loaded_digivolution import BY_SEAT,legal_printed_evolutions
ROOT=Path(__file__).resolve().parent

def _triggered_on_play(source,seat):
    txt=BY_SEAT[seat][source]['card_text']
    return any('[On Play]' in (re.match(r'^\s*(?:\[[^\]]+\]\s*)+',line) or [''])[0]
               for line in txt.splitlines())

def play_with_effects(seat,z,opponent,events,selected=None):
    card=selected if selected is not None else _select_main_action(z)
    if selected is not None and selected not in z.hand:
        raise JudgeHalt('SELECTED_CARD_NOT_IN_HAND')
    if card is None:
        events.append({'type':'PASS_NO_DIGIMON_TAMER','player':seat})
        return 0,None
    z.hand.remove(card);z.battle.append(card)
    cost=COSTS[card.card]['play_cost']
    events.append({'type':'PAID_PLAY','player':seat,'card':card.key(),'play_cost':cost})
    if not _triggered_on_play(card.card,seat):
        return cost,None
    source=card.card
    if source in TWO_CATEGORY_SEARCH or source in SINGLE_CATEGORY_SEARCH:
        o=options_for_search(z,source);a,b=_search_choice(o)
        events.append(resolve_search(z,source,a,b));return cost,None
    if source in DISCARD_DRAW:
        c=discard_candidates(z,source)
        events.append(resolve_discard_draw(z,source,min(c) if c else None));return cost,None
    if source=='EX1-066':
        options=sorted(x.key() for x in z.deck[-3:][::-1] if 'Digimon' in BY_SEAT[seat][x.card]['type'])
        events.append(resolve_analog_youth(z,options[0] if options else None));return cost,None
    if source=='BT24-034':
        choices=eligible_free_tamers(z,include_top_security=True) if z.security else []
        selected=min(choices) if choices else None
        events.append(resolve_aegiomon_tamer(z,selected))
        if selected:
            nested=selected.split('#')[0]
            if _triggered_on_play(nested,seat):
                if nested in SINGLE_CATEGORY_SEARCH:
                    o=options_for_search(z,nested);a,b=_search_choice(o)
                    events.append(resolve_search(z,nested,a,b))
                elif nested in DISCARD_DRAW:
                    opts=discard_candidates(z,nested)
                    events.append(resolve_discard_draw(z,nested,min(opts) if opts else None))
                else:
                    return cost,'Nested Tamer On Play effect not verified: '+nested
        return cost,None
    if source in ('BT26-013','EX12-026','EX12-062'):
        try:
            events.append(resolve_encountered_target(z,opponent,source))
            return cost,None
        except JudgeHalt as exc:
            return cost,str(exc)
    if source in EMPTY_OPPONENT_ONLY:
        if opponent.battle:
            return cost,'Opposing board occupied; target branch unverified for '+source
        events.append(resolve_no_target_branch(z,source))
        return cost,None
    return cost,'On Play effect unverified for '+source

def breeding(seat,z,eggdeck,events):
    egg=eggdeck.pop()
    events.append({'type':'HATCH','player':seat,'card':egg.key()})
    eligible=[c for c in z.hand if BY_SEAT[seat][c.card]['level']==3 and
              legal_printed_evolutions(seat,egg.card,c.card,security_count=len(z.security))]
    if not eligible:return egg.key(),None
    rookie=sorted(eligible,key=lambda c:(c.card,c.index))[0];z.hand.remove(rookie)
    assert legal_printed_evolutions(seat,egg.card,rookie.card,len(z.security))[0].cost==0
    events.append({'type':'BREEDING_EVOLVE','player':seat,'from':egg.key(),'to':rookie.key(),'cost':0})
    if z.deck:
        c=z.deck.pop();z.hand.append(c)
        events.append({'type':'EVOLUTION_DRAW','player':seat,'card':c.key()})
    return egg.key(),rookie.key()

def run_pair(i):
    seed=seed_for(i);rng=random.Random(seed);first='A' if i%2==0 else 'B';second='B' if first=='A' else 'A'
    a,ae=setup('A',rng);b,be=setup('B',rng)
    players={'A':a,'B':b};eggs={'A':ae,'B':be};events=[];bad=None
    for round_idx,pid in enumerate((first,second)):
        current=players[pid];other=players['B' if pid=='A' else 'A']
        events.append({'type':'TURN_START','player':pid,'turn':round_idx+1})
        # Player going first skips only the game's first draw phase.
        if round_idx==1:
            if not current.deck:bad='DRAW_PHASE_DECK_OUT';break
            c=current.deck.pop();current.hand.append(c)
            events.append({'type':'DRAW_PHASE','player':pid,'card':c.key()})
        breeding(pid,current,eggs[pid],events)
        cost,bad=play_with_effects(pid,current,other,events)
        if bad:
            events.append({'type':'JUDGE_HALT','reason':bad,'player':pid})
            break
        # A paid action is not automatically a turn end. The opposing side
        # receives memory only when the gauge actually crosses zero.
        opening_memory=0 if round_idx==0 else next((e['play_cost'] for e in events if e.get('type')=='PAID_PLAY' and e['player']==first),0)
        remaining=opening_memory-cost
        events.append({'type':'FIRST_PAID_ACTION_RESOLVED','player':pid,'memory_before':opening_memory,
                       'cost':cost,'memory_after':remaining,'passed_turn':remaining<0})
    return {'index':i,'seed':seed,'first':first,'status':'JUDGE_HALT' if bad else 'TWO_SEAT_FIRST_ACTIONS_ONLY',
            'halt_reason':bad,'events':events,'valid_full_game':False}

def report(n=60):
    rows=[run_pair(i) for i in range(n)]
    return {'schema':'loaded-pair-two-turn-diagnostics-v1','mode':'early-turn prefix only',
            'fact_finding_games_accepted':0,'first_side_counts':dict(Counter(r['first'] for r in rows)),
            'judge_halts':dict(sorted(Counter(r['halt_reason'] for r in rows if r['halt_reason']).items())),
            'event_counts':dict(sorted(Counter(e['type'] for r in rows for e in r['events']).items())),
            'completed_two_seat_first_actions':sum(r['status']=='TWO_SEAT_FIRST_ACTIONS_ONLY' for r in rows),
            'rows':rows}

if __name__=='__main__':
    data=report()
    (ROOT/'TWO_SIDED_60_PREFIXES.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'},indent=2))
