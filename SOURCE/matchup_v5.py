"""Fresh Jupitermon/Toho midgame effects and security-trigger queue.

Experimental bot decisions; effects checked against pinned loaded-card text.
The game engine cannot claim judge-certified match outcomes without independent
full-transcript review.
"""
from __future__ import annotations
import collections,json
from pathlib import Path
from full_game_integrity import FullGame
from verified_full_match import verified_text
from loaded_effects import JudgeHalt
from full_match_attempt import src

class MatchV5(FullGame):
 def _delete(self,p,c,why):
  stack=p.stacks.get(c.key(),[c])
  for index,d in enumerate(stack):
   t=src(p.seat,d.card)['card_text']
   # A buried card exposes only its Inherited Effect, not its printed main effects.
   if index<len(stack)-1:
    t=t.split('[Inherited Effect]',1)[-1] if '[Inherited Effect]' in t else ''
   if '＜Overflow' in t:raise JudgeHalt('ON_LEAVING_OVERFLOW_UNRESOLVED: '+d.card)
   if index==len(stack)-1 and ('＜Fortitude＞' in t):
    raise JudgeHalt('FORTITUDE_REPLACEMENT_UNVERIFIED: '+d.card)
   if '[On Deletion]' in t:
    # All these explicitly say "you may" on the loaded card, so declining
    # is legal. Non-optional triggers still fail closed.
    if d.card not in ('BT26-013','BT26-014','EX12-047','EX12-063'):
     raise JudgeHalt('MANDATORY_ON_DELETION_NOT_JUDGED: '+d.card)
    self.audited('OPTIONAL_ON_DELETION_DECLINED',p.seat,d.card,reason=why)
  p.z.battle.remove(c);p.stacks.pop(c.key(),None)
  p.z.trash.extend(stack)
  p.suspended.discard(c.key());p.sick.discard(c.key())
  self.audited('DIGIMON_DELETED',p.seat,c.card,cards=[x.key() for x in stack],cause=why)
 def _apply_dp(self,p,target,delta,source):
  after=self._dp(p,target)+delta
  status=p.z.statuses.setdefault(target.key(),{})
  status['dp_delta']=status.get('dp_delta',0)+delta
  status['expires']='end_of_affected_player_next_turn'
  self.audited('DP_CHANGE',p.seat,target.card,source=source,delta=delta,dp_after=after)
  if after<=0:self._delete(p,target,'ZERO_DP')
 def _dedigivolve_one(self,defender,source,owner_seat):
  enemy=defender.digimon()
  eligible=[x for x in enemy if len(defender.stacks.get(x.key(),[x]))>1 and
     (src(defender.seat,defender.stacks[x.key()][-2].card)['level'] or 0)>=3]
  if not eligible:
   self.audited('DEDIGIVOLVE_NO_ELIGIBLE_TARGET',owner_seat,source);return
  chosen=self.choose_enemy_target(defender,eligible,source) if hasattr(self,"choose_enemy_target") else min(eligible);stack=defender.stacks.pop(chosen.key());old=stack.pop()
  if '＜Overflow' in src(defender.seat,old.card)['card_text']:
   raise JudgeHalt('DEDIGIVOLVE_OVERFLOW_UNRESOLVED: '+old.card)
  new=stack[-1]
  defender.z.battle.remove(chosen);defender.z.battle.append(new)
  defender.z.trash.append(old);defender.stacks[new.key()]=stack
  if chosen.key() in defender.suspended:defender.suspended.remove(chosen.key());defender.suspended.add(new.key())
  if chosen.key() in defender.sick:defender.sick.remove(chosen.key());defender.sick.add(new.key())
  self.audited('DEDIGIVOLVE_ONE',owner_seat,source,removed=old.key(),revealed=new.key())
 def _preflight_security_remove(self,owner):
  # Only the loaded Jup deck has the following mandatory security-removal
  # triggers. Check for unsupported Succession branches before mutation.
  for p in self.ps.values():
   for digimon in p.digimon():
    for c in p.stacks.get(digimon.key(),[digimon]):
     text=src(p.seat,c.card)['card_text']
     if ('[All Turns]' in text and 'When ' in text and
         ('security stack is removed from' in text or 'security stacks are removed from' in text)):
      if c.card not in ('BT24-101','BT26-029','BT26-103','BT25-025'):
       raise JudgeHalt('SECURITY_REMOVAL_OTHER_TRIGGER: '+c.card)
 def _security_removal_eligible(self,defender):
  self._preflight_security_remove(defender)
 def _after_security_removed(self,owner):
  enemy=self.ps['B' if owner.seat=='A' else 'A']
  self._preflight_security_remove(owner)
  for digimon in list(owner.digimon()):
   stack=owner.stacks.get(digimon.key(),[digimon])
   for i,copy in enumerate(stack):
    card=copy.card
    # Topmost card exposes its main text; lower card exposes inherited text.
    if card=='BT25-025' and i<len(stack)-1:
     self.audited('AEGIOCHUSMON_BLUE_INHERITED_UNSUSPEND_DECLINED',owner.seat,card)
    if card=='BT24-101' and i==len(stack)-1:
     key='security_removed:'+copy.key()
     if key in owner.once_used:continue
     owner.once_used.add(key)
     removed=enemy.z.security.pop() if enemy.z.security else None
     self.audited('JUPITERMON_TRASH_OPPONENT_SECURITY',owner.seat,card,
        trashed=removed.key() if removed else None)
     if removed:
      enemy.z.trash.append(removed)
      # Opponent-side security triggers also resolve when applicable.
      self._after_security_removed(enemy)
    if card=='BT26-103' and i==len(stack)-1:
     # Succession grants effects of the topmost literal Jupitermon source.
     inherited=next((x for x in reversed(stack[:-1]) if src(owner.seat,x.card)['name']=='Jupitermon'),None)
     if inherited and inherited.card=='BT24-101':
      key='succession_security_removed:'+copy.key()
      if key not in owner.once_used:
       owner.once_used.add(key)
       removed=enemy.z.security.pop() if enemy.z.security else None
       self.audited('WRATH_SUCCESSION_JUPITER_SECURITY_TRASH',owner.seat,card,
          source=inherited.card,trashed=removed.key() if removed else None)
       if removed:
        enemy.z.trash.append(removed)
        self._after_security_removed(enemy)
     elif inherited and inherited.card=='BT26-033':
      self.audited('WRATH_SUCCESSION_JUPITER_PROTECTION_UNUSED',owner.seat,card,source=inherited.card)
    if card=='BT26-029':
     key='security_removed:'+copy.key()
     if key in owner.once_used:continue
     owner.once_used.add(key)
     if i==len(stack)-1:
      for target in sorted(list(enemy.digimon()))[:3]:
       if target in enemy.z.battle:self._apply_dp(enemy,target,-5000,card)
      self.audited('HOLY_AEGIOCHUSMON_SECURITY_REACTION',owner.seat,card)
     else:self._dedigivolve_one(enemy,card,owner.seat)
  # Wrath Mode observes either security stack, not only its owner's.
  for p in self.ps.values():
   foe=self.ps['B' if p.seat=='A' else 'A']
   for top in p.digimon():
    if top.card!='BT26-103':continue
    key='security_removed:'+top.key()
    if key in p.once_used:continue
    p.once_used.add(key)
    if foe.digimon():self._apply_dp(foe,self.choose_enemy_target(foe,foe.digimon(),top.card) if hasattr(self,"choose_enemy_target") else min(foe.digimon()),-15000,top.card)
    self.audited('WRATH_MODE_ANY_SECURITY_REACTION',p.seat,top.card)
  for tam in list(owner.z.battle):
   if tam.card=='BT24-084':
    if hasattr(self,'resolve_inori_security'):self.resolve_inori_security(owner,tam)
    else:self.audited('INORI_SECURITY_REACTION_DECLINED',owner.seat,tam.card)
 def _trash_top_security(self,p,source):
  self._preflight_security_remove(p)
  c=p.z.security.pop() if p.z.security else None
  if c:
   p.z.trash.append(c);self._after_security_removed(p)
  self.audited('TRASH_TOP_SECURITY',p.seat,source,removed=c.key() if c else None)
 def _add_top_security_hand(self,p,source):
  self._preflight_security_remove(p)
  c=p.z.security.pop() if p.z.security else None
  if c:
   p.z.hand.append(c);self._after_security_removed(p)
  self.audited('ADD_TOP_SECURITY_HAND',p.seat,source,removed=c.key() if c else None)
 def _recover_deck(self,p,n,source):
  cards=[]
  for _ in range(n):
   if not p.z.deck:break
   c=p.z.deck.pop();p.z.security.append(c);cards.append(c.key())
  self.audited('RECOVERY_FROM_DECK',p.seat,source,cards=cards)
 def _resolve_target_effect(self,p,card):
  other=self.ps['B' if p.seat=='A' else 'A']
  if card=='BT25-028':
   for c in other.digimon():
    if len(other.stacks.get(c.key(),[c]))-1<=1:
     status=other.z.statuses.setdefault(c.key(),{})
     status.update(cant_suspend=True,expires='end_of_affected_player_next_turn')
   legal=[x for x in other.digimon() if x.key() not in other.suspended]
   if legal:self._delete(other,self.choose_enemy_target(other,legal,card) if hasattr(self,"choose_enemy_target") else min(legal),card)
   self.audited('DIANAMON_SUPPRESS_AND_DELETE',p.seat,card,unsuspended=len(legal))
   return
  if card=='EX12-076':
   # 1 debuff for each distinct color appearing across evolution-source cards.
   digimon=next((x for x in p.digimon() if x.card==card),None)
   if digimon is None:raise JudgeHalt('SUSANOOMON_TARGET_UNLOCATED')
   sources=p.stacks.get(digimon.key(),[digimon])[:-1]
   colors={color for x in sources for color in src(p.seat,x.card)['colors']}
   for target in list(other.digimon()):
    if target in other.z.battle:self._apply_dp(other,target,-3000*len(colors),card)
   self.audited('SUSANOOMON_SOURCE_COLOR_DEBUFF',p.seat,card,colors=sorted(colors))
   return
  if card=='EX12-046' and other.digimon():
   target=self.choose_enemy_target(other,other.digimon(),card) if hasattr(self,"choose_enemy_target") else min(other.digimon())
   self._apply_dp(other,target,-3000,card)
   if target in other.z.battle:
    other.z.statuses.setdefault(target.key(),{})['security_attack_delta']=-1
   return self.audited('SHISHIMAMON_DEBUFF',p.seat,card,target=target.key())
  return super()._resolve_target_effect(p,card)
 def _digivolving_effect(self,p,card):
  if card=='BT24-101':
   self._trash_top_security(p,card)
   other=self.ps['B' if p.seat=='A' else 'A']
   if other.digimon():self._apply_dp(other,self.choose_enemy_target(other,other.digimon(),card) if hasattr(self,"choose_enemy_target") else min(other.digimon()),-13000,card)
   if len(p.z.security)<=1:self._recover_deck(p,2,card)
   return
  if card=='BT26-033':
   self._add_top_security_hand(p,card)
   self.audited('JUPITERMON_DISCOUNTED_PLAY_DECLINED',p.seat,card)
   return
  if card=='BT25-028':return self._resolve_target_effect(p,card)
  if card=='EX12-076':return self._resolve_target_effect(p,card)
  if card=='BT26-103':
   self._trash_top_security(p,card)
   self._recover_deck(p,2,card)
   top=next(x for x in p.digimon() if x.card=='BT26-103')
   st=p.stacks.get(top.key(),[top])
   copied=next((x for x in reversed(st[:-1]) if src(p.seat,x.card)['name']=='Jupitermon'),None)
   if copied and copied.card=='BT24-101':
    self._trash_top_security(p,copied.card)
    other=self.ps['B' if p.seat=='A' else 'A']
    if other.digimon():self._apply_dp(other,self.choose_enemy_target(other,other.digimon(),copied.card) if hasattr(self,"choose_enemy_target") else min(other.digimon()),-13000,copied.card)
    if len(p.z.security)<=1:self._recover_deck(p,2,copied.card)
    self.audited('SUCCESSION_WHEN_DIGIVOLVING_JUPITER',p.seat,card,source=copied.card)
   elif copied and copied.card=='BT26-033':
    self._add_top_security_hand(p,copied.card)
    self.audited('SUCCESSION_DISCOUNT_PLAY_DECLINED',p.seat,card,source=copied.card)
   return
  return super()._digivolving_effect(p,card)
 def hard_play(self,p):
  from seeded_opening_probe import _select_main_action,COSTS
  c=getattr(self,'selected_main_card',None) or _select_main_action(p.z)
  if c and c.card=='BT24-101' and not any(x.key() not in p.suspended and (x.key() not in p.sick or p.z.statuses.get(x.key(),{}).get('rush')) for x in p.digimon()):
   value=COSTS[c.card]['play_cost']
   p.z.hand.remove(c);p.z.battle.append(c);p.stacks[c.key()]=[c];p.sick.add(c.key())
   self.mem=max(-10,min(10,self.mem-value))
   self.event('PAID_PLAY',player=p.seat,card=c.key(),play_cost=value,memory_after=self.mem)
   self._digivolving_effect(p,c.card)
   return True
  return super().hard_play(p)

if __name__=='__main__':
 rows=[MatchV5(i).run() for i in range(60)]
 results={'attempts':60,'starts':dict(collections.Counter(x['first'] for x in rows)),
  'engine_completed':sum(x['status']=='VALID_COMPLETE_GAME' for x in rows),
  'judge_certified_completed':0,
  'winners_engine_only':dict(collections.Counter(x['winner'] for x in rows if x['winner'])),
  'halts':dict(collections.Counter(x['halt_reason'] for x in rows if x['halt_reason'])),
  'rows':rows}
 Path('V5_60_ATTEMPTS.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps({k:v for k,v in results.items() if k!='rows'},indent=2))
