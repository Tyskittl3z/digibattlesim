"""Fresh Jupitermon vs Toho: reproducible, public-information decision scorer.

This is a candidate evaluator, not a trained or certified competitive pilot.
Illegal actions stay in the inherited judge's jurisdiction. It does NOT
invent rulings or import older matchup pilot knowledge.  The only newly
executed optional effect here is printed BT25-030 (start of main).
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from matchup_v8 import MatchV8
from full_match_attempt import src
from loaded_effects import JudgeHalt
from seeded_opening_probe import COSTS
from verified_full_match import verified_text

class MatchV9(MatchV8):
    SCORER_ID='loaded-pair-public-metrics-v1'
    def __init__(self,index,max_turns=100):
        super().__init__(index,max_turns)
        self.selected_main_card=None
        self.bot_choice_counts=Counter()

    def _log_choice(self,choice_type,seat,candidates,chosen,**kw):
        self.bot_choice_counts[choice_type]+=1
        # Immutable, auditable candidates; no hidden opponent hand information.
        self.event('BOT_DECISION',decision_type=choice_type,seat=seat,
                   scorer_id=self.SCORER_ID,chosen=chosen,
                   candidates=candidates,**kw)

    def _level(self,seat,copy):
        v=src(seat,copy.card).get('level')
        return v if isinstance(v,int) else 0

    def _ready(self,p):
        return [x for x in p.digimon() if x.key() not in p.suspended
                and (x.key() not in p.sick or p.z.statuses.get(x.key(),{}).get('rush'))
                and not p.z.statuses.get(x.key(),{}).get('cant_attack')
                and not p.z.statuses.get(x.key(),{}).get('cant_suspend')]

    def choose_breeding_rookie(self,p,options):
        # Use own hand only. Count legal follow-up digivolutions already in hand.
        from loaded_digivolution import legal_printed_evolutions
        scored=[]
        for c in options:
            follow=sum(bool(legal_printed_evolutions(p.seat,c.card,x.card,len(p.z.security)))
                for x in p.z.hand if x!=c)
            score=5*follow
            scored.append((score,c))
        result=max(scored,key=lambda v:(v[0],v[1].key()))[1]
        self._log_choice('BREEDING_ROOKIE',p.seat,
            [{'card':c.key(),'score':s} for s,c in scored],result.key())
        return result

    def _attacker_score(self,p,copy):
        dp=self._dp(p,copy)
        target=self.ps['B' if p.seat=='A' else 'A']
        # A successful attack on zero security wins. Remaining scores are
        # heuristics, not assertions that an attack is guaranteed to succeed.
        if len(target.z.security)==0:return 1000+max(0,dp)//1000
        return 24+max(0,dp)//1000 + 2*min(2,len(target.z.security))

    def choose_attacker(self,p,eligible):
        scores=[(self._attacker_score(p,c),c) for c in eligible]
        chosen=max(scores,key=lambda v:(v[0],v[1].key()))[1]
        self._log_choice('ATTACKER',p.seat,
            [{'card':c.key(),'score':s} for s,c in scores],chosen.key())
        return chosen

    def choose_enemy_target(self,defender,candidates,source):
        if not candidates:raise JudgeHalt('NO_TARGET_CANDIDATES')
        # Only evaluate candidates already filtered for this card's legal target.
        # The attacker's pilot sees opposing board/DP/level, NOT hidden zones.
        scored=[]
        for c in candidates:
            score=4*self._level(defender.seat,c)
            if 'Digimon' in src(defender.seat,c.card)['type']:
                score+=max(0,self._dp(defender,c))//1000
            if c.key() not in defender.suspended:score+=3
            if c.key() not in defender.sick:score+=2
            scored.append((score,c))
        chosen=max(scored,key=lambda v:(v[0],v[1].key()))[1]
        self._log_choice('OPPONENT_TARGET',self.active,
            [{'card':c.key(),'score':s} for s,c in scored],chosen.key(),source=source)
        return chosen

    def _evolution_score(self,p,cost,zone,base,new):
        lv=self._level(p.seat,new)
        growth=lv-self._level(p.seat,base)
        score=22 + 5*max(0,growth) + 2*lv - 3*cost
        if zone=='breeding':score-=6  # development in breeding, not immediate pressure
        if self.mem-cost<0:score-=9
        if zone=='battle' and p.z.statuses.get(base.key(),{}).get('cant_when_digivolve'):
            score-=8
        return score

    def _play_score(self,p,c):
        info=src(p.seat,c.card)
        cost=COSTS[c.card]['play_cost']
        level=info.get('level') or 0
        score=20+2*level-2*cost
        if info['type']=='Tamer':score+=8
        if '[On Play]' in info['card_text']:score+=4
        if self.mem-cost<0:score-=8
        return score

    def choose_turn_action(self,p,evolves):
        options=[]
        # A legal Digimon evolution is possible at nonnegative memory; the
        # existing resolver ends the turn when memory crosses to opponent.
        for cost,zone,base,card in evolves:
            if self.mem>=0:
                score=self._evolution_score(p,cost,zone,base,card)
                options.append((score,'EVOLVE',(cost,zone,base,card),
                    f'{base.key()}->{card.key()}@{zone}'))
        if self.mem>=0:
            for c in p.z.hand:
                if src(p.seat,c.card)['type'] in ('Digimon','Tamer','Digimon/Tamer'):
                    if isinstance(COSTS[c.card]['play_cost'],int):
                        options.append((self._play_score(p,c),'PLAY',c,c.key()))
        ready=self._ready(p)
        if self.mem>=0 and ready:
            best=max(self._attacker_score(p,c) for c in ready)
            options.append((best,'ATTACK',None,'ATTACK_AVAILABLE'))
        options.append((0,'PASS',None,'PASS'))
        # A stable tie break avoids automatic first-card selection while
        # maintaining byte-for-byte replay determinism.
        winner=max(options,key=lambda v:(v[0],v[1],v[3]))
        self._log_choice('MAIN_ACTION',p.seat,
            [{'action':kind,'label':name,'score':score} for score,kind,_,name in options],
            winner[3],memory=self.mem)
        return winner[1],winner[2]

    def _aegiomon_tamer_score(self,card):
        # A value assigned only to a legal, already owned, visible hand card.
        info=src('A',card.card)
        result=3*int(info.get('play_cost') or 0)
        if '[On Play]' in info['card_text']:result+=6
        return result

    def resolve_aegiomon_ability(self,p,source_copy,trigger):
        # Printed BT24-034 security cost and free TS Tamer selection. No
        # outside-card or speculative effect execution is permitted.
        from loaded_effects import (eligible_free_tamers,resolve_aegiomon_tamer,
            options_for_search,resolve_search,discard_candidates,
            resolve_discard_draw,SINGLE_CATEGORY_SEARCH,DISCARD_DRAW)
        from seeded_opening_probe import _search_choice
        verified_text(p.seat,'BT24-034')
        choices=eligible_free_tamers(p.z,include_top_security=True) if p.z.security else []
        possible=[c for c in p.z.hand+p.z.security[-1:] if c.key() in choices]
        candidates=[{'target':None,'score':0}]
        if len(p.z.security)>=3:
            for c in possible:
                candidates.append({'target':c.key(),'score':self._aegiomon_tamer_score(c)})
        selected=max(candidates,key=lambda x:(x['score'],x['target'] or ''))
        self._log_choice('AEGIOMON_SECURITY_TAMER',p.seat,candidates,
            selected['target'] or 'DECLINE',source=source_copy.key(),trigger=trigger)
        if not selected['target']:
            self.audited('OPTIONAL_DECLINED',p.seat,'BT24-034',source_copy=source_copy.key(),
                         trigger=trigger,evaluated=True)
            return
        ev=resolve_aegiomon_tamer(p.z,selected['target'])
        self.event('AEGIOMON_TAMER_CHOICE_RESOLVED',**ev)
        self._after_security_removed(p)
        tamer=next((c for c in p.z.battle if c.key()==selected['target']),None)
        if tamer is None:raise JudgeHalt('AEGIOMON_CHOSEN_TAMER_NOT_PLAYED')
        tamer_id=tamer.card
        if tamer_id in SINGLE_CATEGORY_SEARCH:
            opts=options_for_search(p.z,tamer_id)
            a,b=_search_choice(opts)
            outcome=resolve_search(p.z,tamer_id,a,b)
            self.event('FREE_TAMER_ON_PLAY',effect=outcome)
        elif tamer_id in DISCARD_DRAW:
            options=discard_candidates(p.z,tamer_id)
            discard=max(options) if options else None
            outcome=resolve_discard_draw(p.z,tamer_id,discard)
            self.event('FREE_TAMER_ON_PLAY',effect=outcome)
        elif __import__('two_player_prefix')._triggered_on_play(tamer_id,p.seat):
            raise JudgeHalt('FREE_TAMER_ON_PLAY_NOT_CERTIFIED: '+tamer_id)
        self.audited('AEGIOMON_TAMER_PLAY_PAID',p.seat,'BT24-034',
                     source_copy=source_copy.key(),tamer=tamer.key(),trigger=trigger)

    def _digivolving_effect(self,p,card):
        if card=='BT24-034':
            top=next((x for x in p.digimon() if x.card==card),None)
            if top is None:raise JudgeHalt('AEGIOMON_DIGIVOLVE_SOURCE_MISSING')
            self.resolve_aegiomon_ability(p,top,'When Digivolving')
            return
        return super()._digivolving_effect(p,card)

    def hard_play(self,p):
        chosen=getattr(self,'selected_main_card',None)
        if chosen is None or chosen.card!='BT24-034':return super().hard_play(p)
        if chosen not in p.z.hand:raise JudgeHalt('AEGIOMON_NOT_IN_HAND')
        value=COSTS[chosen.card]['play_cost']
        p.z.hand.remove(chosen);p.z.battle.append(chosen)
        p.stacks[chosen.key()]=[chosen];p.sick.add(chosen.key())
        self.mem=max(-10,min(10,self.mem-value))
        self.event('PAID_PLAY',player=p.seat,card=chosen.key(),play_cost=value,memory_after=self.mem)
        self.resolve_aegiomon_ability(p,chosen,'On Play')
        return True

    def resolve_elecm_start_main(self,p,copy):
        # Called in the normal start-of-main trigger order, not retroactively.
        verified_text(p.seat,'BT25-030')
        candidates=[{'pay':False,'score':0}]
        if p.z.security:
            # Explicitly priced security resource, not a blanket decline.
            score=10 if len(p.z.security)>=3 else -12
            score+=(4 if self.mem<=2 else 0)
            score-=(20 if len(p.z.security)==1 else 0)
            candidates.append({'pay':True,'score':score})
        selected=max(candidates,key=lambda c:(c['score'],not c['pay']))
        self._log_choice('ELECMON_START_MAIN',p.seat,candidates,
            'PAY' if selected['pay'] else 'DECLINE',source=copy.key())
        if selected['pay']:
            self._add_top_security_hand(p,'BT25-030')
            self.mem=min(10,self.mem+1)
            self.audited('ELECMON_START_MAIN_PAID',p.seat,'BT25-030',
                source_copy=copy.key(),memory_after=self.mem)
            self._process_security_events()
        else:self.audited('OPTIONAL_DECLINED',p.seat,'BT25-030',
                         source_copy=copy.key(),trigger='Start of Your Main Phase',
                         evaluated=True)

    def run(self):
        r=super().run()
        r['bot_decision_counts']=dict(sorted(self.bot_choice_counts.items()))
        r['decision_policy_id']=self.SCORER_ID
        return r


def run_cohort(n=60):
    rows=[MatchV9(i).run() for i in range(n)]
    return {'schema':'jup-toho-v9-experimental-decision-policy','attempts':n,
     'software_completed':sum(r['status']=='VALID_COMPLETE_GAME' for r in rows),
     'judge_certified':0,'firsts':dict(Counter(r['first'] for r in rows)),
     'experimental_winners':dict(Counter(r['winner'] for r in rows if r['winner'])),
     'halts':dict(Counter(r['halt_reason'] for r in rows if r['halt_reason'])),
     'decisions':dict(sum((Counter(r['bot_decision_counts']) for r in rows),Counter())),
     'rows':rows}

if __name__=='__main__':
    report=run_cohort()
    Path('V9_DECISION_MATCHES.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
