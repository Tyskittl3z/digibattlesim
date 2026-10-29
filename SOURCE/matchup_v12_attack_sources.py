"""Loaded Jupitermon/Toho pair: source-scoped When Attacking choices.

Separates printed main [When Attacking] text from inherited [When Attacking].
Only these loaded cards are eligible. This is an experimental policy, NOT
an approved three-lane roadmap or independent full-game judge certificate.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
from matchup_v11_endturn_choices import MatchV11
from full_match_attempt import src
from seeded_opening_probe import COSTS
from loaded_effects import JudgeHalt
from verified_full_match import verified_text


class MatchV12(MatchV11):
    SCORER_ID = 'loaded-pair-v12-attack-source-scope-and-elecmon'

    def choose_turn_action(self,p,evolves):
        # The memory gauge cannot cross beyond the opponent's 10.  In
        # particular, do not offer a 12-cost Dianamon from zero memory.
        options=[]
        for cost,zone,base,card in evolves:
            if self.mem>=0 and cost<=self.mem+10:
                options.append((self._evolution_score(p,cost,zone,base,card),
                                'EVOLVE',(cost,zone,base,card),
                                f'{base.key()}->{card.key()}@{zone}'))
        if self.mem>=0:
            foe=self.ps['B' if p.seat=='A' else 'A']
            for c in p.z.hand:
                info=src(p.seat,c.card)
                if info['type'] not in ('Digimon','Tamer','Digimon/Tamer'):
                    continue
                cost=COSTS[c.card].get('play_cost')
                if not isinstance(cost,int):continue
                if c.card=='BT25-028' and any((src(foe.seat,x.card).get('level') or 0)>=6 for x in foe.digimon()):
                    cost=max(0,cost-5)
                if cost>self.mem+10:continue
                score=self._play_score(p,c)+2*(COSTS[c.card]['play_cost']-cost)
                options.append((score,'PLAY',c,c.key()))
        ready=self._ready(p)
        if self.mem>=0 and ready:
            best=max(self._attacker_score(p,c) for c in ready)
            options.append((best,'ATTACK',None,'ATTACK_AVAILABLE'))
        options.append((0,'PASS',None,'PASS'))
        winner=max(options,key=lambda v:(v[0],v[1],v[3]))
        self._log_choice('MAIN_ACTION',p.seat,
                         [{'action':kind,'label':label,'score':score} for score,kind,_,label in options],
                         winner[3],memory=self.mem)
        return winner[1],winner[2]

    def hard_play(self,p):
        chosen=getattr(self,'selected_main_card',None)
        if chosen is None or chosen.card!='BT25-028':
            return super().hard_play(p)
        if chosen not in p.z.hand:
            raise JudgeHalt('DIANAMON_NOT_IN_HAND')
        opponent=self.ps['B' if p.seat=='A' else 'A']
        discount=5 if any((src(opponent.seat,x.card).get('level') or 0)>=6 for x in opponent.digimon()) else 0
        value=max(0,COSTS['BT25-028']['play_cost']-discount)
        if value>self.mem+10:
            raise JudgeHalt('DIANAMON_COST_BEYOND_MEMORY_GAUGE')
        p.z.hand.remove(chosen);p.z.battle.append(chosen)
        p.stacks[chosen.key()]=[chosen];p.sick.add(chosen.key())
        self.mem-=value
        self.event('PAID_PLAY',player=p.seat,card=chosen.key(),play_cost=value,
                   discount=discount,memory_after=self.mem)
        self._resolve_target_effect(p,'BT25-028')
        self._flush_dp_check()
        self.audited('DIANAMON_ALL_TURNS_OPTION_DECLINED',p.seat,chosen.card,
                     reason='NO_GRACENOVAMON_IN_LOADED_HAND')
        return True

    def _when_attacking(self,p,attacker):
        stack = list(p.stacks.get(attacker.key(),[attacker]))
        other = self.ps['B' if p.seat == 'A' else 'A']
        for pos,copy in enumerate(stack):
            if attacker not in p.z.battle:
                return
            card=copy.card
            text=src(p.seat,card)['card_text']
            main, sep, inherited = text.partition('[Inherited Effect]')
            is_top=(pos == len(stack)-1)
            active_text=main if is_top else (inherited if sep else '')
            if '[When Attacking]' not in active_text:
                continue
            key=f'{attacker.key()}:{copy.key()}:when_attacking'
            if key in p.once_used:
                continue
            mark_used=True
            if not is_top and card in ('BT24-031','BT25-030'):
                verified_text(p.seat,card,card+':attack')
                securities=len(p.z.security)
                choices=[{'action':'DECLINE','score':0}]
                can_recover=bool(p.z.deck) and securities <= 1
                # A zero-security effect is executable even without paying an
                # impossible security-to-hand action: Q5611 / Q6297.
                score=(13 if can_recover else 6 if securities >= 4 else -6)
                if p.z.security or can_recover:
                    choices.append({'action':'ACTIVATE','score':score})
                selected=max(choices,key=lambda v:(v['score'],v['action']))
                self._log_choice('ELECMON_INHERITED_ATTACK',p.seat,choices,selected['action'],
                                 attacker=attacker.key(),source=copy.key(),security_before=securities)
                if selected['action']=='ACTIVATE':
                    if p.z.security:
                        self._add_top_security_hand(p,card)
                    if not p.z.security:
                        self._recover_deck(p,1,card)
                    # Resolve the current effect completely before other
                    # pending security-removal triggers (Q5611/Q6297).
                    self._process_security_events()
                    self.audited('ELECMON_INHERITED_ATTACK_USED',p.seat,card,
                                 attacker=attacker.key(),source=copy.key(),
                                 security_before=securities,security_after=len(p.z.security),
                                 official_ruling='Q5611' if card=='BT24-031' else 'Q6297')
                else:
                    mark_used=False
                    self.audited('ELECMON_INHERITED_ATTACK_DECLINED',p.seat,card,
                                 attacker=attacker.key(),source=copy.key(),security_before=securities)
            elif is_top and card=='EX12-076':
                verified_text(p.seat,card,card+':attack')
                candidates=other.digimon()
                chosen=self.choose_enemy_target(other,candidates,card) if candidates else None
                if chosen:
                    target_stack=other.stacks.get(chosen.key(),[chosen])
                    # The loaded pair has replacement/Decode abilities that
                    # must be resolved before moving the target. Do not invent
                    # their controller's optional decision.
                    if any('＜Decode' in src(other.seat,x.card)['card_text'] for x in target_stack):
                        raise JudgeHalt('SUSANOOMON_TARGET_DECODE_DECISION_UNVERIFIED: '+chosen.card)
                    if any(x.card in ('BT24-101','BT26-033','BT26-016','BT26-103') for x in other.digimon()):
                        raise JudgeHalt('SUSANOOMON_TARGET_LEAVE_REPLACEMENT_UNVERIFIED')
                    other.z.battle.remove(chosen)
                    other.stacks.pop(chosen.key(),None)
                    other.z.trash.extend(target_stack[:-1])
                    other.z.security.append(chosen)
                    other.suspended.discard(chosen.key());other.sick.discard(chosen.key())
                self.audited('SUSANOOMON_ATTACK_DIGIMON_TO_SECURITY',p.seat,card,
                             attacker=attacker.key(),target=chosen.key() if chosen else None)
                colors={color for c in stack[:-1] for color in src(p.seat,c.card)['colors']}
                if len(colors)>=4 and attacker in p.z.battle:
                    # Resolve the whole effect (trash then Recovery) before
                    # processing newly pending security removal triggers.
                    removed=other.z.security.pop() if other.z.security else None
                    if removed:
                        other.z.trash.append(removed)
                    self._recover_deck(p,1,card)
                    if removed:self._after_security_removed(other)
                    self.audited('SUSANOOMON_FOUR_COLOR_BONUS',p.seat,card,
                                 removed=removed.key() if removed else None,
                                 source_colors=sorted(colors),official_ruling='Q7194')
            elif not is_top and card=='BT26-012':
                verified_text(p.seat,card,card+':attack')
                candidates=other.digimon()
                selected=self.choose_enemy_target(other,candidates,card) if candidates else None
                if selected:
                    self._apply_dp(other,selected,-2000,card)
                    self._flush_dp_check()
                self.audited('MANEKIMON_INHERITED_ATTACK_DP',p.seat,card,
                             attacker=attacker.key(),target=selected.key() if selected else None)
            elif not is_top and card=='BT25-028':
                verified_text(p.seat,card,card+':attack')
                candidates=[x for x in other.z.battle if src(other.seat,x.card)['type'] in ('Tamer','Digimon','Digimon/Tamer')]
                selected=self.choose_enemy_target(other,candidates,card) if candidates else None
                if selected:
                    st=other.z.statuses.setdefault(selected.key(),{})
                    st['cant_suspend']=True
                    st['expires']='end_of_affected_player_next_turn'
                self.audited('DIANAMON_INHERITED_ATTACK_LOCK',p.seat,card,
                             attacker=attacker.key(),target=selected.key() if selected else None)
            elif not is_top and card in ('EX12-020','EX12-026'):
                if len(p.z.hand)<=7:
                    drawn=p.z.deck.pop() if p.z.deck else None
                    if drawn:p.z.hand.append(drawn)
                    self.audited('INHERITED_ATTACK_DRAW',p.seat,card,source=copy.key(),
                                 drawn=drawn.key() if drawn else None)
            elif not is_top and card in ('EX12-061','EX12-062'):
                drawn=p.z.deck.pop() if p.z.deck else None
                if drawn:p.z.hand.append(drawn)
                discarded=min(p.z.hand) if p.z.hand else None
                if discarded:p.z.hand.remove(discarded);p.z.trash.append(discarded)
                self.audited('INHERITED_ATTACK_DRAW_DISCARD',p.seat,card,
                             source=copy.key(),drawn=drawn.key() if drawn else None,
                             trashed=discarded.key() if discarded else None)
            elif is_top and card in ('EX12-036','EX12-065','BT26-016'):
                # Optional effect is legally declinable. This is NOT learned
                # strategy and must stay visible in the coverage report.
                self.audited('TOP_ATTACK_OPTIONAL_UNMODELED_DECLINED',p.seat,card,
                             source=copy.key(),attacker=attacker.key())
            else:
                # Particularly EX12-076 Susanoomon's mandatory When Attacking;
                # NEVER silently omit it or use its buried main text.
                raise JudgeHalt('WHEN_ATTACKING_UNSUPPORTED_ACTIVE_SOURCE: '+card)
            if mark_used:p.once_used.add(key)


def run_cohort(n=60):
    rows=[MatchV12(i).run() for i in range(n)]
    return {'schema':'jup-toho-v12-source-scoped-attack-experimental',
            'attempted':n,'software_completed':sum(r['status']=='VALID_COMPLETE_GAME' for r in rows),
            'judge_certified':0,'starts':dict(Counter(r['first'] for r in rows)),
            'winners_unverified':dict(Counter(r['winner'] for r in rows if r['winner'])),
            'halts':dict(Counter(r['halt_reason'] for r in rows if r['halt_reason'])),
            'decisions':dict(sum((Counter(r['bot_decision_counts']) for r in rows),Counter())),
            'rows':rows}

if __name__=='__main__':
    data=run_cohort()
    Path('V12_GAMES.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'},indent=2))
