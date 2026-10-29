"""Matchup-only end-of-turn options; exact sources, no outside-deck actions.

Implements supported BT24-085/BT24-102/BT26-104 ability branches,
refuses to treat automatic declines as learned strategy. No certifications.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
from matchup_v10_active_choices import MatchV10
from full_match_attempt import src
from verified_full_match import verified_text
from loaded_effects import options_for_search,resolve_search
from seeded_opening_probe import COSTS,_search_choice

class MatchV11(MatchV10):
    SCORER_ID='loaded-pair-v11-defender-and-eot-options'

    def choose_attacker(self,p,eligible):
        if getattr(self,'_end_turn_ts_only',False):
            eligible=[c for c in eligible if 'TS' in src(p.seat,c.card)['traits']]
            if not eligible:raise RuntimeError('NO_LEGAL_TS_ATTACKER')
        return super().choose_attacker(p,eligible)
    def end_turn_check(self,p):
        # Process only the three loaded Tamers' end-of-turn effects.
        # All other printed end-of-turn triggers retain fail-closed behavior.
        for tamer in list(p.z.battle):
            if self.winner:break
            if tamer not in p.z.battle:continue
            card=tamer.card
            if card not in ('BT24-085','BT24-102','BT26-104'):
                if '[End of Your Turn]' in src(p.seat,card)['card_text']:
                    raise RuntimeError('UNSUPPORTED_END_TURN_SOURCE: '+card)
                continue
            verified_text(p.seat,card,card+':end')
            options=[{'effect':'DECLINE','target':None,'score':0}]
            unsuspended=(tamer.key() not in p.suspended and
                         not p.z.statuses.get(tamer.key(),{}).get('cant_suspend'))
            if unsuspended and card=='BT24-085':
                # Opponent's memory is the opposite sign at EOT.
                oppmem=max(0,-self.mem)
                for c in p.z.hand:
                    t=src(p.seat,c.card)
                    if t['type']=='Option' and 'TS' in t['traits'] and COSTS[c.card]['play_cost']<=oppmem:
                        if c.card=='BT24-100':
                            options.append({'effect':'FREE_TS_OPTION','target':c.key(),
                                            'score':8})
                        # Other loaded TS Options remain unexecuted, not faked.
            elif unsuspended and card=='BT24-102':
                # The current judge path for BT24-101's On Play/When Digivolving
                # effect is usable outside evolution; other routes are not.
                for c in p.digimon():
                    info=src(p.seat,c.card)
                    if 'Olympos XII' in info['traits'] and c.card=='BT24-101':
                        if p.z.security:
                            options.append({'effect':'REACTIVATE_JUPITER','target':c.key(),
                                            'score':12+(10 if self.ps['B'].digimon() else 0)})
            elif unsuspended and card=='BT26-104':
                has_tentei=any('Tentei Hachibushu' in src(p.seat,c.card)['traits'] for c in p.digimon())
                if has_tentei:
                    for c in p.z.hand:
                        info=src(p.seat,c.card)
                        if info['type']=='Option' and 'Shambala' in info['traits']:
                            if c.card=='EX12-075':
                                options.append({'effect':'FREE_SHAMBALA_SEARCH','target':c.key(),
                                                'score':8})
            chosen=max(options,key=lambda a:(a['score'],a['effect'],a['target'] or ''))
            self._log_choice('END_OF_TURN',p.seat,options,
                             chosen['effect'],tamer=tamer.key(),target=chosen['target'])
            if chosen['effect']=='DECLINE':
                self.audited('END_OF_TURN_EVALUATED_DECLINE',p.seat,card,
                             tamer=tamer.key(),available_branches=len(options)-1)
                continue
            tamer_copy=tamer.key()
            p.suspended.add(tamer_copy)
            if chosen['effect'] in ('FREE_TS_OPTION','FREE_SHAMBALA_SEARCH'):
                option=next(c for c in p.z.hand if c.key()==chosen['target'])
                p.z.hand.remove(option);p.z.battle.append(option)
                search=options_for_search(p.z,option.card)
                first,second=_search_choice(search)
                resolved=resolve_search(p.z,option.card,first,second)
                self.event('END_TURN_OPTION_USED',tamer=tamer_copy,
                           option=option.key(),effect=resolved)
                self.audited('END_OF_TURN_FREE_OPTION_USED',p.seat,card,
                             tamer=tamer_copy,option=option.key())
                if card=='BT24-085':
                    # Q5673 permits declining this follow-up attack.  Offer a
                    # choice only if a TS Digimon is legally ready to attack.
                    attackers=[x for x in self._ready(p)
                               if 'TS' in src(p.seat,x.card)['traits']]
                    possible=[{'attacker':None,'score':0}]
                    for attacker in attackers:
                        possible.append({'attacker':attacker.key(),
                                         'score':self._attacker_score(p,attacker)})
                    follow=max(possible,key=lambda v:(v['score'],v['attacker'] or ''))
                    self._log_choice('DAN_KANAN_FOLLOWUP_ATTACK',p.seat,possible,
                                     follow['attacker'] or 'DECLINE',tamer=tamer_copy)
                    if follow['attacker']:
                        # Record the choice before resolving: an attack may win
                        # immediately, and GAME_END must be the final event.
                        self.audited('DAN_KANAN_FOLLOWUP_ATTACK_USED',p.seat,card,
                                     tamer=tamer_copy,attacker=follow['attacker'])
                        self._end_turn_ts_only=True
                        try:
                            if not self.try_attack(p):raise RuntimeError('END_TURN_TS_ATTACK_NOT_RESOLVED')
                        finally:self._end_turn_ts_only=False
                    else:
                        self.audited('DAN_KANAN_FOLLOWUP_ATTACK_DECLINED',p.seat,card,
                                     tamer=tamer_copy,official_ruling='Q5673')
            elif chosen['effect']=='REACTIVATE_JUPITER':
                self._digivolving_effect(p,'BT24-101')
                self.audited('HOMEROS_OLYMPOS_EFFECT_USED',p.seat,card,
                             tamer=tamer_copy,target=chosen['target'])
            self.verify()

def run_cohort(n=60):
    rows=[MatchV11(i).run() for i in range(n)]
    return {'schema':'jup-toho-v11-active-choices-experimental','attempted':n,
            'software_completed':sum(r['status']=='VALID_COMPLETE_GAME' for r in rows),
            'judge_certified':0,'starts':dict(Counter(r['first'] for r in rows)),
            'winners_unverified':dict(Counter(r['winner'] for r in rows if r['winner'])),
            'halts':dict(Counter(r['halt_reason'] for r in rows if r['halt_reason'])),
            'decisions':dict(sum((Counter(r['bot_decision_counts']) for r in rows),Counter())),
            'rows':rows}

if __name__=='__main__':
    r=run_cohort()
    Path('V11_GAMES.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
