"""Strict full-match ATTEMPT runner for ONLY Jupitermon vs Toho loaded decks.

No win/loss is credited unless a legal end condition is achieved without any
unsupported interaction. Unsupported relevant mechanics halt with an explicit
reason. Prior 60 opening probes are NOT full games and are never counted.
"""
from __future__ import annotations
import json, random, re, hashlib, collections, argparse
from dataclasses import dataclass, field
from pathlib import Path
from seeded_opening_probe import setup, seed_for, COSTS, _search_choice
from loaded_digivolution import BY_SEAT, legal_printed_evolutions
from loaded_effects import JudgeHalt, Copy, MatchZones
from two_player_prefix import play_with_effects, _triggered_on_play

ROOT=Path(__file__).resolve().parent

def leadtags(text):
    return set(tag for line in text.splitlines() for tag in re.findall(r'\[([^\]]+)\]',(re.match(r'^\s*(?:\[[^\]]+\]\s*)+',line) or [''])[0]))

def src(seat, card):return BY_SEAT[seat][card]

def name(seat,c): return src(seat,c)['name']

def cost(card):
    v=COSTS[card]['play_cost']
    if not isinstance(v,int):raise JudgeHalt('PRINTED_PLAY_COST_UNRESOLVED: '+card)
    return v

@dataclass
class Player:
    seat:str
    z:MatchZones
    eggdeck:list[Copy]
    breeding:list[Copy]=field(default_factory=list)  # ordered bottom->top
    stacks:dict[str,list[Copy]]=field(default_factory=dict)
    suspended:set[str]=field(default_factory=set)
    sick:set[str]=field(default_factory=set)
    once_used:set[str]=field(default_factory=set)
    def ensure(self):
        actual=(self.z.count()+len(self.eggdeck)+len(self.breeding)+sum(len(v)-1 for v in self.stacks.values()))
        assert actual==54,(self.seat,actual, self.z.count(),len(self.eggdeck),len(self.breeding),self.stacks)
    def t(self, c):return src(self.seat,c.card)['type']
    def digimon(self):
        return [c for c in self.z.battle if 'Digimon' in self.t(c)]

class FullMatch:
    def __init__(self,index,max_turns=100):
        self.i=index;self.seed=seed_for(index);self.rng=random.Random(self.seed)
        az,ae=setup('A',self.rng); bz,be=setup('B',self.rng)
        self.ps={'A':Player('A',az,ae),'B':Player('B',bz,be)}
        self.first='A' if index%2==0 else 'B'
        self.events=[];self.turn=0;self.mem=0;self.max_turns=max_turns
        self.active=self.first
        self.winner=None
        self.actions=0
    def event(self,typ,**kw):
        self.events.append({'t':self.turn,'actor':self.active,'type':typ,**kw})
    def verify(self):
        for p in self.ps.values():p.ensure()
    def trigger_check(self,p,tags,where):
        for c in p.z.battle:
            if tags.intersection(leadtags(src(p.seat,c.card)['card_text'])):
                raise JudgeHalt(f'{where}: unverified trigger on {c.card}: {sorted(tags)}')
    def draw_phase(self,p):
        if not p.z.deck:
            self.winner='B' if p.seat=='A' else 'A'
            self.event('WIN_DRAW_PHASE_DECKOUT',loser=p.seat)
            return
        c=p.z.deck.pop();p.z.hand.append(c)
        self.event('DRAW_PHASE',card=c.key())
    def breeding_phase(self,p):
        if p.breeding and len(p.breeding)>1:
            top=p.breeding[-1]
            # Moving effects may trigger after promotion. Judge must resolve these.
            tags=leadtags(src(p.seat,top.card)['card_text'])
            if 'When Moving' in tags:
                raise JudgeHalt('BREEDING_PROMOTION_WHEN_MOVING_UNVERIFIED: '+top.card)
            stack=p.breeding;p.breeding=[]
            p.z.battle.append(top);p.stacks[top.key()]=stack
            self.event('PROMOTE',stack=[x.key() for x in stack]);return
        if not p.breeding and p.eggdeck:
            egg=p.eggdeck.pop();p.breeding=[egg];self.event('HATCH',card=egg.key())
        if p.breeding and len(p.breeding)==1:
            base=p.breeding[-1]
            options=[c for c in p.z.hand if src(p.seat,c.card)['level']==3 and
                     legal_printed_evolutions(p.seat,base.card,c.card,len(p.z.security)) and
                     legal_printed_evolutions(p.seat,base.card,c.card,len(p.z.security))[0].cost==0]
            if options:
                c=(self.choose_breeding_rookie(p,options) if hasattr(self,'choose_breeding_rookie')
                   else min(options,key=lambda x:x.key()));p.z.hand.remove(c)
                p.breeding.append(c);self.event('BREEDING_EVOLVE',from_card=base.key(),to_card=c.key(),memory_cost=0)
                if p.z.deck:
                    drawn=p.z.deck.pop();p.z.hand.append(drawn);self.event('EVOLVE_DRAW',card=drawn.key())
                # If breeding evolved card has a When Digivolving triggered effect,
                # ignore only if the effect is not active in breeding.
    def start_phase(self,p):
        # Until supported, all trigger effects at start of turn/main phase that
        # currently apply on exposed battle cards must halt, not be skipped.
        self.trigger_check(p,{'Start of Your Turn'},'START_OF_TURN')
        self.breeding_phase(p)
        self.trigger_check(p,{'Start of Your Main Phase'},'START_MAIN')
    def evolution_candidates(self,p):
        result=[]
        bases=[('breeding',p.breeding[-1])] if p.breeding and len(p.breeding)>1 else []
        bases += [('battle',b) for b in p.digimon()]
        for zone,base in bases:
            for c in p.z.hand:
                routes=legal_printed_evolutions(p.seat,base.card,c.card,len(p.z.security))
                if routes:
                    result.append((routes[0].cost,zone,base,c))
        return sorted(result,key=lambda x:(x[0],x[2].key(),x[3].key()))
    def evolve(self,p,action):
        evo_cost,zone,base,c=action
        p.z.hand.remove(c)
        if zone=='breeding':
            p.breeding.append(c)
        else:
            stack=p.stacks.pop(base.key(),[base]);stack.append(c)
            p.z.battle.remove(base);p.z.battle.append(c)
            p.stacks[c.key()]=stack
            if base.key() in p.suspended:p.suspended.remove(base.key());p.suspended.add(c.key())
            if base.key() in p.sick:p.sick.remove(base.key());p.sick.add(c.key())
            # Temporary effects and prohibitions affect a Digimon entity,
            # surviving a digivolution of that same Digimon.
            if base.key() in p.z.statuses:
                carried=p.z.statuses.pop(base.key())
                p.z.statuses.setdefault(c.key(),{}).update(carried)
        self.mem=max(-10,min(10,self.mem-evo_cost))
        self.event('DIGIVOLVE',base=base.key(),card=c.key(),zone=zone,cost=evo_cost,memory_after=self.mem)
        if p.z.deck:
            d=p.z.deck.pop();p.z.hand.append(d);self.event('DIGIVOLVE_DRAW',card=d.key())
        if zone=='battle':
            # Digivolution-triggered effects require a verified handler. No
            # approximation from the opening On Play path is assumed.
            tags=leadtags(src(p.seat,c.card)['card_text'])
            if 'When Digivolving' in tags:
                raise JudgeHalt('WHEN_DIGIVOLVING_UNVERIFIED: '+c.card)
    def hard_play(self,p):
        playable=[]
        for c in p.z.hand:
            if src(p.seat,c.card)['type'] in ('Digimon','Tamer','Digimon/Tamer'):
                try:playable.append((cost(c.card),c))
                except JudgeHalt:continue
        if not playable:return False
        selected=getattr(self,'selected_main_card',None)
        if selected is not None:
            matched=[(v,c) for v,c in playable if c==selected]
            if not matched:raise JudgeHalt('BOT_SELECTED_ILLEGAL_HARD_PLAY')
            value,c=matched[0]
        else:value,c=min(playable,key=lambda x:(x[0],x[1].key()))
        other=self.ps['B' if p.seat=='A' else 'A']
        charged,halt=play_with_effects(p.seat,p.z,other.z,self.events,selected=c)
        if halt:raise JudgeHalt(halt)
        if charged!=value:raise JudgeHalt('MAIN_ACTION_SELECTION_MISMATCH')
        self.mem=max(-10,min(10,self.mem-charged))
        self.event('PLAY_RESOLVED',card=c.key(),cost=charged,memory_after=self.mem)
        if 'Digimon' in src(p.seat,c.card)['type']:
            p.stacks[c.key()]=[c];p.sick.add(c.key())
        return True
    def try_attack(self,p):
        eligible=[c for c in p.digimon() if c.key() not in p.sick and c.key() not in p.suspended]
        if not eligible:return False
        attacker=min(eligible,key=lambda x:x.key())
        stack=p.stacks.get(attacker.key(),[attacker]);other=self.ps['B' if p.seat=='A' else 'A']
        for source in stack:
            tags=leadtags(src(p.seat,source.card)['card_text'])
            if 'When Attacking' in tags:
                raise JudgeHalt('WHEN_ATTACKING_UNVERIFIED: '+source.card)
        if other.digimon():
            if any('Blocker' in src(other.seat,c.card)['card_text'] for c in other.digimon()):
                raise JudgeHalt('DEFENDER_BLOCKER_DECISION_UNVERIFIED')
        # Security attacks still need the full Security Effect/DP/keyword judge
        # pipeline. Check it explicitly, and HALT before consuming security.
        if other.z.security:
            card=other.z.security[-1]
            if '[Security' in src(other.seat,card.card)['card_text']:
                raise JudgeHalt('SECURITY_EFFECT_UNVERIFIED: '+card.card)
            if any(k in src(p.seat,attacker.card)['card_text'] for k in ('Security A.', 'Jamming', 'Piercing', 'Alliance', 'Raid')):
                raise JudgeHalt('SECURITY_ATTACK_KEYWORD_UNVERIFIED: '+attacker.card)
        # No unsupported attack should be silently treated as complete.
        raise JudgeHalt('SECURITY_BATTLE_AND_DAMAGE_PIPELINE_NOT_CERTIFIED')
    def end_turn_check(self,p):
        self.trigger_check(p,{'End of Your Turn'},'END_OF_TURN')
    def run(self):
        try:
            for turn_idx in range(1,self.max_turns+1):
                self.turn=turn_idx;p=self.ps[self.active];other='B' if self.active=='A' else 'A'
                p.suspended.clear();p.once_used.clear();p.sick.clear()
                self.event('TURN_START',memory=self.mem)
                if turn_idx>1:
                    self.draw_phase(p)
                    if self.winner:break
                self.start_phase(p)
                # Deliberate finite budget stops runaway loops; not a game result.
                for action_num in range(40):
                    # Construct a deterministic turn-taking pilot from the cards
                    # in the loaded hand. This pilot is not trained or certified.
                    evolves=self.evolution_candidates(p)
                    if evolves and (self.mem>0 or evolves[0][0]==0):
                        self.evolve(p,evolves[0]);self.actions+=1;self.verify()
                    elif self.mem>=0 and self.hard_play(p):
                        self.actions+=1;self.verify()
                    elif self.try_attack(p):
                        self.actions+=1;self.verify()
                    else:
                        self.event('PASS');self.mem=-3
                    if self.mem<0:break
                else:raise JudgeHalt('TURN_ACTION_BUDGET_EXCEEDED')
                self.end_turn_check(p)
                self.verify()
                self.event('TURN_END',memory=self.mem)
                self.mem=max(1,-self.mem);self.active=other
            else:raise JudgeHalt('TURN_LIMIT_REACHED_NO_VALID_WINNER')
            self.verify()
            status='VALID_COMPLETE_GAME' if self.winner else 'JUDGE_HALT'
            reason=None
        except (JudgeHalt,AssertionError,ValueError,KeyError,TypeError) as e:
            status='JUDGE_HALT';reason=f'{type(e).__name__}: {e}'
            self.event('JUDGE_HALT',reason=reason)
        return {'index':self.i,'seed':self.seed,'first':self.first,'status':status,
                'winner':self.winner if status=='VALID_COMPLETE_GAME' else None,
                'turn':self.turn,'actions':self.actions,'halt_reason':reason,'events':self.events}

def run_batch(n=60):
    runs=[FullMatch(i).run() for i in range(n)]
    return {'schema':'jup-toho-fresh-full-match-attempts-v1','decks':{'A':'Jupitermon','B':'Amaterasumon/Toho'},
            'requested_complete_matches':n,'attempted_seeds':n,
            'valid_complete_matches':sum(x['status']=='VALID_COMPLETE_GAME' for x in runs),
            'first_counts':dict(collections.Counter(x['first'] for x in runs)),
            'halt_reason_counts':dict(collections.Counter(x['halt_reason'] for x in runs if x['halt_reason'])),
            'winner_counts':dict(collections.Counter(x['winner'] for x in runs if x['winner'])),
            'rows':runs}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=60);ap.add_argument('--out',default=str(ROOT/'FULL_MATCH_ATTEMPTS_60.json'))
    args=ap.parse_args();r=run_batch(args.n)
    Path(args.out).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
