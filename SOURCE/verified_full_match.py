"""Jupitermon vs Toho: incremental loaded-deck judge paths.

No prior matchup pilot, knowledge or training is imported. Declining a true
optional ability is a valid rule-compliant pilot decision (not evidence of skill).
Mandatory effects/uncertified paths halt. Complete games are only reported if
FULL security and attack resolution succeeds; not currently established.
"""
from __future__ import annotations
import json, collections, re
from pathlib import Path
from full_match_attempt import FullMatch, JudgeHalt, src, leadtags, name
from loaded_effects import resolve_encountered_target, resolve_no_target_branch, source_hash, resolve_aegiomon_tamer, eligible_free_tamers

# Source text assertions guard against unannounced changes in pinned card text.
FRAGMENTS={
 'EX12-076:attack':"[When Attacking] [Once Per Turn] Place 1 of your opponent's Digimon as the top security card.",
 'BT24-031:attack':"[When Attacking] [Once Per Turn] You may add your top security card to the hand. Then, if you have 0 security cards, ＜Recovery +1",
 'BT25-030:attack':"[When Attacking] [Once Per Turn] You may add your top security card to the hand. Then, if you have 0 security cards, ＜Recovery +1",
 'BT26-012:attack':"[When Attacking] [Once Per Turn] 1 of your opponent's Digimon gets -2000 DP",
 'BT25-028:attack':"[When Attacking] [Once Per Turn] 1 of your opponent's Digimon or Tamers can't suspend",
 'BT24-083':'[Start of Your Turn] If you have 4 or less memory, by returning this Tamer to the bottom of the deck',
 'BT24-088':'[Start of Your Turn] If you have 4 or less memory, by returning this Tamer to the bottom of the deck',
 'BT24-084':'[Start of Your Main Phase] If you have 4 or less memory, gain 1 memory.',
 'BT24-085':'[Start of Your Main Phase] If you have 4 or less memory, gain 1 memory.',
 'BT24-102':'[Start of Your Main Phase] Gain 1 memory. Then, if you have 5 or more memory, suspend this Tamer and ＜Draw 1＞.',
 'BT26-104':'[Start of Your Main Phase] Gain 1 memory.',
 'BT25-030':'[Start of Your Main Phase] By adding your top security card to the hand, gain 1 memory.',
 'BT24-034':'[When Moving] [On Play] [When Digivolving] By adding your top security card to the hand',
 'BT25-033':'[On Play] [When Digivolving] By adding your top security card to the hand',
 'BT26-029':'[On Play] [When Digivolving] By trashing your top security card',
 'EX12-062':'[On Play] [When Digivolving] By deleting 1 of your Digimon',
 'EX12-031':'[On Play] [When Digivolving] By placing 1 level 6 or lower card',
 'EX12-036':'[On Play] [When Digivolving] [When Attacking] [Once Per Turn] By placing 1 level 6 or lower card',
 'EX12-065':'[On Play] [When Digivolving] [When Attacking] [Once Per Turn] You may play 1 play cost 5 or lower',
 'BT26-016':'[On Play] [When Digivolving] [When Attacking] [Once Per Turn] You may delete 1',
 'BT24-085:end':'[End of Your Turn] By suspending this Tamer, you may use 1 [TS] trait Option card',
 'BT24-102:end':'[End of Your Turn] By suspending this Tamer, you may activate 1 [On Play]',
 'BT26-104:end':'[End of Your Turn] If you have a Digimon with the [Tentei Hachibushu] trait',
 "EX12-046":"[On Play] [When Digivolving] Give 1 of your opponent's Digimon",
 "EX12-063":"[On Play] [When Digivolving] Suspend 1 of your opponent's Digimon",
 "BT26-014":"[On Play] [When Digivolving] Delete 1 of your opponent's Digimon with 7000 DP or less.",
 'BT25-025':'[On Play] [When Digivolving] ＜De-Digivolve 1＞',
 "EX12-047":"[On Play] [When Digivolving] Delete 1 of your opponent's lowest DP Digimon.",
 "EX12-076":"[On Play] [When Digivolving] To all of your opponent's Digimon,",
 'P-213':'[When Digivolving] If you have 3 or fewer security cards',
}

def verified_text(seat,card,pattern=None):
 text=src(seat,card)['card_text']; fragment=FRAGMENTS.get(pattern or card)
 if not fragment or fragment not in text:raise JudgeHalt('PINNED_TEXT_NOT_MATCHING '+card)
 return src(seat,card)['card_text_sha256']

class AuditedMatch(FullMatch):
 def __init__(self,index,max_turns=100):
  super().__init__(index,max_turns)
  self.checks=[]
 def audited(self,kind,seat,card,**fields):
  digest=src(seat,card)['card_text_sha256']
  self.checks.append({'turn':self.turn,'seat':seat,'card':card,'kind':kind,'card_text_sha256':digest,**fields})
  self.event('JUDGE_PATH',owner=seat,card=card,kind=kind,**fields)
 def declining(self,p,card,trigger):
  verified_text(p.seat,card)
  self.audited('OPTIONAL_DECLINED',p.seat,card,trigger=trigger)
 def _start_turn_effects(self,p):
  # All matching Tamers have optional activation costs. Do not remove a Tamer
  # unless the pilot actually elects to pay that cost.
  for c in list(p.z.battle):
   card=c.card
   if card in ('BT24-083','BT24-088'):
    if self.mem<=4:self.declining(p,card,'Start of Your Turn')
   elif 'Start of Your Turn' in leadtags(src(p.seat,card)['card_text']):
    raise JudgeHalt('START_OF_TURN_UNSUPPORTED: '+card)
 def _start_main_effects(self,p):
  for c in list(p.z.battle):
   card=c.card
   if card in ('BT24-084','BT24-085'):
    verified_text(p.seat,card)
    gain=1 if self.mem<=4 else 0
    self.mem=min(10,self.mem+gain);self.audited('MEMORY_GAIN_START_MAIN',p.seat,card,gain=gain,memory_after=self.mem)
   elif card in ('BT24-102','BT26-104'):
    verified_text(p.seat,card)
    self.mem=min(10,self.mem+1);self.audited('MEMORY_GAIN_START_MAIN',p.seat,card,gain=1,memory_after=self.mem)
    if card=='BT24-102' and self.mem>=5:
     if c.key() not in p.suspended:
      p.suspended.add(c.key());drawn=None
      if p.z.deck:
       drawn=p.z.deck.pop();p.z.hand.append(drawn)
      self.audited('HOMEROS_SUSPEND_DRAW',p.seat,card,drawn=drawn.key() if drawn else None)
   elif card=='BT25-030':
    if hasattr(self,'resolve_elecm_start_main'):
     self.resolve_elecm_start_main(p,c)
    else:self.declining(p,card,'Start of Your Main Phase')
   elif 'Start of Your Main Phase' in leadtags(src(p.seat,card)['card_text']):
    raise JudgeHalt('START_OF_MAIN_UNSUPPORTED: '+card)
 def start_phase(self,p):
  self._start_turn_effects(p)
  self.breeding_phase(p)
  self._start_main_effects(p)
 def breeding_phase(self,p):
  if p.breeding and len(p.breeding)>1:
   c=p.breeding[-1]
   if c.card=='BT24-034' and 'When Moving' in leadtags(src(p.seat,c.card)['card_text']):
    if not hasattr(self,'resolve_aegiomon_ability'):
     self.declining(p,c.card,'When Moving')
  # Suppress strict parent halt for only verified voluntary-decline path.
  if p.breeding and len(p.breeding)>1 and p.breeding[-1].card=='BT24-034':
   from_copy=p.breeding[-1]; stack=p.breeding;p.breeding=[]
   p.z.battle.append(from_copy);p.stacks[from_copy.key()]=stack
   self.event('PROMOTE',stack=[x.key() for x in stack])
   if hasattr(self,'resolve_aegiomon_ability'):
    self.resolve_aegiomon_ability(p,from_copy,'When Moving')
   return
  return super().breeding_phase(p)
 def evolve(self,p,action):
  ev_before=len(self.events)
  try:
   super().evolve(p,action)
  except JudgeHalt as exc:
   # Only the precise final triggered-effect halt can be handled here.
   card=action[3].card
   if str(exc)!='WHEN_DIGIVOLVING_UNVERIFIED: '+card:raise
   if not any(e.get('type')=='DIGIVOLVE' and e.get('card')==action[3].key() for e in self.events[ev_before:]):raise
   self._digivolving_effect(p,card)
 def _dp(self,p,c):
  from seeded_opening_probe import COSTS
  printed=COSTS[c.card].get('dp')
  if not isinstance(printed,int):raise JudgeHalt('DP_UNAVAILABLE: '+c.card)
  # Apply recorded temporary negative DP, plus Homeros field bonus.
  modifications=p.z.statuses.get(c.key(),{}).get('dp_delta',0)
  t=src(p.seat,c.card).get('traits',[])
  if c in p.z.battle and 'TS' in t and any(x.card=='BT24-102' for x in p.z.battle):modifications+=1000
  return printed+modifications+p.z.statuses.get(c.key(),{}).get('p213_dp_bonus',0)
 def _delete(self,p,c,why):
  # Only judge paths with no unimplemented mandatory On Deletion/Overflow effects.
  stack=p.stacks.get(c.key(),[c])
  for d in stack:
   txt=src(p.seat,d.card)['card_text']
   if '[On Deletion]' in txt or '＜Overflow' in txt:
    raise JudgeHalt('DELETE_DEPENDENT_TRIGGER_UNVERIFIED: '+d.card)
  p.z.battle.remove(c);p.stacks.pop(c.key(),None)
  p.z.trash.extend(stack)
  p.suspended.discard(c.key());p.sick.discard(c.key())
  self.audited('DIGIMON_DELETED',p.seat,c.card,cards=[x.key() for x in stack],cause=why)
 def _resolve_target_effect(self,p,card):
  opp=self.ps['B' if p.seat=='A' else 'A']
  enemy=opp.digimon()
  if card=='BT26-014':
   verified_text(p.seat,card)
   eligible=[x for x in enemy if self._dp(opp,x)<=7000]
   if eligible:self._delete(opp,self.choose_enemy_target(opp,eligible,card) if hasattr(self,"choose_enemy_target") else min(eligible),card)
   self.audited('DARUMAMON_TARGET_CHECK',p.seat,card,eligible=len(eligible))
   return
  if card=='EX12-047':
   verified_text(p.seat,card)
   if enemy:
    lowest=min(self._dp(opp,x) for x in enemy)
    chosen=(self.choose_enemy_target(opp,[x for x in enemy if self._dp(opp,x)==lowest],card) if hasattr(self,"choose_enemy_target") else min(x for x in enemy if self._dp(opp,x)==lowest))
    self._delete(opp,chosen,card)
   self.audited('AMATERASUMON_DELETE_CHECK_AND_OPTIONAL_COST_DECLINED',p.seat,card)
   return
  if card=='EX12-046':
   verified_text(p.seat,card)
   if enemy:
    chosen=self.choose_enemy_target(opp,enemy,card) if hasattr(self,"choose_enemy_target") else min(enemy)
    dp_after=self._dp(opp,chosen)-3000
    if dp_after<=0:raise JudgeHalt('SHISHIMAMON_DP_ZERO_DELETION_NOT_JUDGED')
    status=opp.z.statuses.setdefault(chosen.key(),{})
    status['dp_delta']=status.get('dp_delta',0)-3000
    status['security_attack_delta']=status.get('security_attack_delta',0)-1
    status['expires']='end_of_affected_player_next_turn'
   self.audited('SHISHIMAMON_DP_SECURITY_MODIFIER',p.seat,card,target=chosen.key() if enemy else None)
   return
  if card=='EX12-063':
   verified_text(p.seat,card)
   candidates=[x for x in opp.z.battle if src(opp.seat,x.card)['type'] in ('Tamer','Digimon','Digimon/Tamer')]
   if candidates:
    chosen=self.choose_enemy_target(opp,candidates,card) if hasattr(self,"choose_enemy_target") else min(candidates);opp.suspended.add(chosen.key())
    status=opp.z.statuses.setdefault(chosen.key(),{})
    status['cant_unsuspend']=True;status['expires']='end_of_affected_player_next_turn'
   self.audited('KARAKURUMON_SUSPEND_LOCK',p.seat,card,target=chosen.key() if candidates else None)
   return
  if card=='BT25-025':
   verified_text(p.seat,card)
   withsources=[x for x in enemy if len(opp.stacks.get(x.key(),[x]))>1 and (src(opp.seat,opp.stacks.get(x.key(),[x])[-2].card)['level'] or 0)>=3]
   if withsources:
    chosen=self.choose_enemy_target(opp,withsources,card) if hasattr(self,"choose_enemy_target") else min(withsources)
    stack=opp.stacks.pop(chosen.key())
    oldtop=stack.pop()
    if '＜Overflow' in src(opp.seat,oldtop.card)['card_text']:
     raise JudgeHalt('DEDIGIVOLVE_OVERFLOW_NOT_JUDGED')
    # De-digivolve 1, no level-3 reduction; Digi-Egg-only is invalid battle state.
    if stack[-1].card and src(opp.seat,stack[-1].card)['level']<3:
     raise JudgeHalt('DEDIGIVOLVE_LEVEL_TWO_BATTLE_UNVERIFIED')
    newtop=stack[-1]
    opp.z.battle.remove(chosen);opp.z.battle.append(newtop)
    opp.z.trash.append(oldtop);opp.stacks[newtop.key()]=stack
    if chosen.key() in opp.suspended:opp.suspended.remove(chosen.key());opp.suspended.add(newtop.key())
    if chosen.key() in opp.sick:opp.sick.remove(chosen.key());opp.sick.add(newtop.key())
    self.audited('BLUE_AEGIOCHUSMON_DEDIGIVOLVE',p.seat,card,removed=oldtop.key(),revealed=newtop.key())
   else:self.audited('BLUE_AEGIOCHUSMON_NO_SOURCES_TO_REMOVE',p.seat,card)
   if len(p.z.security)<=3:
    suspended=[x for x in p.digimon() if x.key() in p.suspended]
    if suspended:
     selected=min(suspended);p.suspended.discard(selected.key())
     self.audited('BLUE_AEGIOCHUSMON_UNSUSPEND',p.seat,card,target=selected.key())
   return
  if card=='EX12-026':
   # Bottom two digivolution cards of one opposing Digimon; resulting Digimon
   # with <=1 source cannot attack/block. Source-selection for target is fixed.
   if not enemy:return self.audited('SHELLMON_NO_TARGET',p.seat,card)
   chosen=self.choose_enemy_target(opp,enemy,card) if hasattr(self,"choose_enemy_target") else min(enemy);stack=opp.stacks.get(chosen.key(),[chosen]);removed=[]
   if len(stack)>1:
    count=min(2,len(stack)-1)
    removed=stack[:count]
    if any('＜Overflow' in src(opp.seat,x.card)['card_text'] for x in removed):
     raise JudgeHalt('SHELLMON_STACK_TRASH_OVERFLOW_UNVERIFIED')
    opp.stacks[chosen.key()]=stack[count:]
    opp.z.trash.extend(removed)
   elig=[x for x in enemy if len(opp.stacks.get(x.key(),[x]))-1<=1]
   if elig:
    target=self.choose_enemy_target(opp,elig,card) if hasattr(self,"choose_enemy_target") else min(elig)
    status=opp.z.statuses.setdefault(target.key(),{})
    status.update(cant_attack=True,cant_block=True,expires='end_of_affected_player_next_turn')
   self.audited('SHELLMON_TRASH_AND_LOCK',p.seat,card,removed=[x.key() for x in removed],target=target.key() if elig else None)
   return
  raise JudgeHalt('UNSUPPORTED_TARGET_EFFECT: '+card)
 def _digivolving_effect(self,p,card):
  opp=self.ps['B' if p.seat=='A' else 'A']
  declined={'BT24-034','BT25-033','BT26-029','EX12-062','EX12-031','EX12-036','EX12-065','BT26-016'}
  if card in declined:
   self.declining(p,card,'When Digivolving')
   return
  if card in ('EX12-026','BT26-014','EX12-047','EX12-046','EX12-063','BT25-025'):
   return self._resolve_target_effect(p,card)
  if card=='P-213':
   verified_text(p.seat,card)
   if len(p.z.security)<=3:
    top=next((x for x in p.digimon() if x.card==card),None)
    if top is None:raise JudgeHalt('P213_DIGIVOLVE_SOURCE_MISSING')
    status=p.z.statuses.setdefault(top.key(),{})
    status['p213_dp_bonus']=3000
    status['rush']=True
    status['p213_expires_after_seat']='B' if p.seat=='A' else 'A'
    self.audited('P213_GRANTED_3000_DP_AND_RUSH',p.seat,card,card_copy=top.key())
   self.audited('P213_DIGIVOLVE_FREE_ATTACK_DECLINED',p.seat,card,security_count=len(p.z.security))
   return
  raise JudgeHalt('WHEN_DIGIVOLVING_UNVERIFIED: '+card)
 def end_turn_check(self,p):
  for c in list(p.z.battle):
   card=c.card
   if card in ('BT24-085','BT24-102','BT26-104'):
    verified_text(p.seat,card,card+':end')
    self.audited('END_OF_TURN_OPTION_DECLINED',p.seat,card)
   elif 'End of Your Turn' in leadtags(src(p.seat,card)['card_text']):
    raise JudgeHalt('END_TURN_UNSUPPORTED: '+card)
 def run(self):
  r=super().run()
  r['judge_path_count']=len(self.checks)
  r['judge_paths']=self.checks
  return r

def batch(n=60):
 rows=[AuditedMatch(i).run() for i in range(n)]
 return {'schema':'jup-toho-loaded-match-engine-progress-v2','attempts':n,
  'valid_complete_matches':sum(x['status']=='VALID_COMPLETE_GAME' for x in rows),
  'starting_positions':dict(collections.Counter(x['first'] for x in rows)),
  'first_halt_reasons':dict(collections.Counter(x['halt_reason'] for x in rows if x['halt_reason'])),
  'average_attempted_turns':sum(x['turn'] for x in rows)/len(rows),
  'judge_paths_exercised':sum(x['judge_path_count'] for x in rows),
  'rows':rows}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=60);p.add_argument('--out',default='JUDGE_MATCH_ATTEMPTS_V2.json')
 a=p.parse_args();out=batch(a.n);Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
