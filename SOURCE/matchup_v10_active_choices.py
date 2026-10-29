"""Loaded-pair V10: explicit defender Blocker and Inori security responses.

Both choices use only information available to the acting player. Source
rules: Comprehensive Rules Block Timing; BT24-084 and its Q5669. Deliberately
experimental until the full-match independent judge checks pass.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
from matchup_v9_decision_policy import MatchV9
from full_match_attempt import src
from loaded_digivolution import legal_printed_evolutions
from loaded_effects import JudgeHalt

class MatchV10(MatchV9):
    SCORER_ID='loaded-pair-defender-inori-decisions-v2'

    def _has_blocker(self,p,top):
        if top.key() in p.suspended:return False
        if p.z.statuses.get(top.key(),{}).get('cant_block'):return False
        if p.z.statuses.get(top.key(),{}).get('cant_suspend'):return False
        stack=p.stacks.get(top.key(),[top])
        for index,c in enumerate(stack):
            t=src(p.seat,c.card)['card_text']
            # A card under a Digimon exposes its inherited text only.
            if index<len(stack)-1:t=t.split('[Inherited Effect]',1)[-1] if '[Inherited Effect]' in t else ''
            if '＜Blocker＞' in t:return True
        # EX12-065 grants Blocker to all owner's Puppet or TB Digimon.
        if any(x.card=='EX12-065' for x in p.digimon()):
            traits=src(p.seat,top.card)['traits']
            if 'Puppet' in traits or 'TB' in traits:return True
        return False

    def resolve_block_timing(self,attacking_player,attacker,defender):
        possible=[b for b in defender.digimon() if self._has_blocker(defender,b)]
        if not possible:return False
        adp=self._dp(attacking_player,attacker)
        # The threatened player's decision. Choice 0 means no block.
        # No use of opponent's hand, deck, or facedown security contents.
        options=[{'target':None,'score':0}]
        for b in possible:
            bdp=self._dp(defender,b)
            score=18 if bdp>=adp else (-8 if len(defender.z.security)>1 else 12)
            if not defender.z.security:score+=100
            options.append({'target':b.key(),'score':score})
        selected=max(options,key=lambda v:(v['score'],v['target'] or ''))
        self._log_choice('BLOCK_TIMING',defender.seat,options,
                         selected['target'] or 'DECLINE',attacker=attacker.key())
        if selected['target'] is None:
            self.audited('BLOCKER_DECLINED_AFTER_ATTACK',defender.seat,possible[0].card,
                         legal_blockers=[x.key() for x in possible]);return False
        blocker=next(x for x in possible if x.key()==selected['target'])
        defender.suspended.add(blocker.key())
        self.event('BLOCK_DECLARED',blocker=blocker.key(),attacker=attacker.key(),
                   original_target='PLAYER',new_target=blocker.key())
        self.audited('BLOCKER_ACTIVATED',defender.seat,blocker.card,
                     attacker=attacker.key(),blocker_dp=self._dp(defender,blocker),attacker_dp=adp)
        # Battle resolves against blocker, not the player's security stack.
        # Blocker and attacker can be deleted simultaneously in a tie.
        bdp=self._dp(defender,blocker)
        if adp>=bdp and blocker in defender.z.battle:
            self._delete(defender,blocker,'BLOCK_BATTLE')
        if bdp>=adp and attacker in attacking_player.z.battle:
            self._delete(attacking_player,attacker,'BLOCK_BATTLE')
        self.audited('BLOCK_BATTLE_RESOLVED',defender.seat,blocker.card,
                     attacker_survived=attacker in attacking_player.z.battle,
                     blocker_survived=blocker in defender.z.battle)
        return True

    def resolve_inori_security(self,p,tamer):
        if tamer not in p.z.battle:return
        if tamer.key() in p.suspended or p.z.statuses.get(tamer.key(),{}).get('cant_suspend'):
            return
        sources=[x for x in p.digimon() if src(p.seat,x.card)['name']=='Aegiomon']
        legal=[]
        for base in sources:
            for c in p.z.hand:
                if 'Aegiochusmon' not in src(p.seat,c.card)['name']:continue
                if legal_printed_evolutions(p.seat,base.card,c.card,len(p.z.security)):
                    legal.append((base,c))
        options=[{'base':None,'target':None,'score':0}]
        for base,c in legal:
            info=src(p.seat,c.card)
            score=15+(info.get('level') or 0)*3+(info.get('dp') or 0)//2000
            options.append({'base':base.key(),'target':c.key(),'score':score})
        selected=max(options,key=lambda x:(x['score'],x['target'] or ''))
        self._log_choice('INORI_SECURITY_EVOLVE',p.seat,options,
            selected['target'] or 'DECLINE',tamer=tamer.key(),base=selected['base'])
        if not selected['target']:
            self.audited('INORI_SECURITY_REACTION_DECLINED',p.seat,tamer.card,
                         tamer_copy=tamer.key(),evaluated=True)
            return
        base,c=next((base,c) for base,c in legal if base.key()==selected['base'] and c.key()==selected['target'])
        p.suspended.add(tamer.key())
        self.audited('INORI_SECURITY_COST_PAID',p.seat,tamer.card,
                    tamer_copy=tamer.key(),base=base.key(),target=c.key())
        # The effect's special digivolution is explicitly cost-free, but the
        # normal digivolution draw and triggered effects still resolve.
        self.evolve(p,(0,'battle',base,c))
        self.audited('INORI_SECURITY_EVOLVE_RESOLVED',p.seat,tamer.card,
                    evolved_into=c.key(),memory_after=self.mem)


def run_cohort(n=60):
    rows=[MatchV10(i).run() for i in range(n)]
    return {'schema':'jup-toho-v10-active-choices-experimental',
            'attempted':n,'software_completed':sum(r['status']=='VALID_COMPLETE_GAME' for r in rows),
            'judge_certified':0,'starts':dict(Counter(r['first'] for r in rows)),
            'winners_unverified':dict(Counter(r['winner'] for r in rows if r['winner'])),
            'halts':dict(Counter(r['halt_reason'] for r in rows if r['halt_reason'])),
            'decisions':dict(sum((Counter(r['bot_decision_counts']) for r in rows),Counter())),
            'rows':rows}

if __name__=='__main__':
    r=run_cohort()
    Path('V10_GAMES.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
