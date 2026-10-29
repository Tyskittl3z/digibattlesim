"""Strict, limited attack/security paths for the two loaded decks.

Unsupported interactions fail closed, never yielding credited games.
"""
from __future__ import annotations
from verified_full_match import AuditedMatch, JudgeHalt, src, leadtags
from loaded_effects import (resolve_search,resolve_discard_draw,discard_candidates,
    options_for_search,resolve_analog_youth,resolve_aegiomon_tamer,
    TWO_CATEGORY_SEARCH,SINGLE_CATEGORY_SEARCH,DISCARD_DRAW)
from seeded_opening_probe import _search_choice

class AttackMatch(AuditedMatch):
 def _security_removal_eligible(self,defender):
  # Block any mandatory, currently unresolved all-turn security-removal effects.
  for seat,p in self.ps.items():
   for digimon in p.digimon():
    for copy in p.stacks.get(digimon.key(),[digimon]):
     t=src(seat,copy.card)['card_text']
     if ('[All Turns]' in t and 'When ' in t and
         ('security stack is removed from' in t or 'security stacks are removed from' in t)):
      if copy.card=='BT25-025':
       self.audited('BLUE_AEGIOCHUSMON_SECURITY_UNSUSPEND_DECLINED',seat,copy.card)
       continue
      raise JudgeHalt('SECURITY_REMOVAL_TRIGGER_UNVERIFIED: '+copy.card)
  # Inori decisions trigger after security actually leaves, not at preflight.
 def _when_attacking(self,p,attacker):
  from loaded_digivolution import BY_SEAT
  stack=p.stacks.get(attacker.key(),[attacker])
  for copy in stack:
   card=copy.card
   txt=src(p.seat,card)['card_text']
   # Top-level keywords don't create a mandatory activated attack trigger.
   if '[When Attacking]' not in leadtags(txt):continue
   key=f'{attacker.key()}:{copy.key()}:when_attacking'
   if key in p.once_used:continue
   if card in ('BT24-031','BT25-030','EX12-036','EX12-065','BT26-016'):
    self.audited('ATTACK_OPTIONAL_DECLINED',p.seat,card,attacker=attacker.key())
   elif card in ('EX12-020','EX12-026'):
    if len(p.z.hand)<=7:
     drawn=p.z.deck.pop() if p.z.deck else None
     if drawn:p.z.hand.append(drawn)
     self.audited('INHERITED_ATTACK_DRAW',p.seat,card,drawn=drawn.key() if drawn else None)
   elif card in ('EX12-061','EX12-062'):
    drawn=p.z.deck.pop() if p.z.deck else None
    if drawn:p.z.hand.append(drawn)
    trashcard=min(p.z.hand) if p.z.hand else None
    if trashcard:p.z.hand.remove(trashcard);p.z.trash.append(trashcard)
    self.audited('INHERITED_ATTACK_DRAW_DISCARD',p.seat,card,
      drawn=drawn.key() if drawn else None,trashed=trashcard.key() if trashcard else None)
   else:raise JudgeHalt('WHEN_ATTACKING_UNSUPPORTED: '+card)
   p.once_used.add(key)
 def _security_effect(self,defender,checked):
  c=checked; card=c.card;txt=src(defender.seat,card)['card_text']
  if '[Security Effect]' not in txt:return False
  if 'Play this card without paying' in txt and src(defender.seat,card)['type']=='Tamer':
   defender.z.battle.append(c)
   self.audited('SECURITY_TAMER_PLAY',defender.seat,card)
   if card in TWO_CATEGORY_SEARCH or card in SINGLE_CATEGORY_SEARCH:
    opts=options_for_search(defender.z,card);first,second=_search_choice(opts)
    self.event('SECURITY_TAMER_ON_PLAY_EFFECT',detail=resolve_search(defender.z,card,first,second))
   elif card in DISCARD_DRAW:
    allowed=discard_candidates(defender.z,card)
    self.event('SECURITY_TAMER_ON_PLAY_EFFECT',detail=resolve_discard_draw(defender.z,card,min(allowed) if allowed else None))
   elif card=='EX1-066':
    qualified=sorted(x.key() for x in defender.z.deck[-3:][::-1] if 'Digimon' in src(defender.seat,x.card)['type'])
    self.event('SECURITY_TAMER_ON_PLAY_EFFECT',detail=resolve_analog_youth(defender.z, qualified[0] if qualified else None))
   else:
    from two_player_prefix import _triggered_on_play
    if _triggered_on_play(card,defender.seat):raise JudgeHalt('SECURITY_TAMER_ON_PLAY_UNIMPLEMENTED: '+card)
   return True
  if '[Security] Place this card in the battle area.' in txt:
   defender.z.battle.append(c);self.audited('SECURITY_DELAY_PLACED',defender.seat,card)
   return True
  if card=='EX12-070':
   # Printed EX12-070 Main is activated by its Security effect. Official Q6883:
   # the "After" placement requires payment of its "By" trash cost.
   eligible=sorted(x for x in defender.z.hand if 'TB' in src(defender.seat,x.card)['traits'])
   if eligible:
    discarded=eligible[0]
    defender.z.hand.remove(discarded);defender.z.trash.append(discarded)
    drawn=[]
    for _ in range(2):
     if defender.z.deck:
      d=defender.z.deck.pop();defender.z.hand.append(d);drawn.append(d.key())
    defender.z.battle.append(c)
    self.audited('SANMYOJIN_SECURITY_MAIN_PAID_AND_PLACED',defender.seat,card,
       discarded=discarded.key(),drawn=drawn,official_ruling='Q6883')
   else:
    defender.z.trash.append(c)
    self.audited('SANMYOJIN_SECURITY_MAIN_COST_UNPAID',defender.seat,card,
       official_ruling='Q6883')
   return True
  if card=='EX12-074':
   defender.z.trash.append(c);self.audited('GENSHI_SECURITY_OPTIONAL_PLAY_DECLINED',defender.seat,card)
   return True
  raise JudgeHalt('SECURITY_EFFECT_NOT_CERTIFIED: '+card)
 def try_attack(self,p):
  eligible=[c for c in p.digimon() if c.key() not in p.suspended
            and (c.key() not in p.sick or p.z.statuses.get(c.key(),{}).get('rush'))
            and not p.z.statuses.get(c.key(),{}).get('cant_attack') and not p.z.statuses.get(c.key(),{}).get('cant_suspend')]
  if not eligible:return False
  atk=(self.choose_attacker(p,eligible) if hasattr(self,'choose_attacker') else min(eligible));enemy=self.ps['B' if p.seat=='A' else 'A']
  p.suspended.add(atk.key())
  self.event('ATTACK_DECLARED',attacker=atk.key(),target='PLAYER')
  self._when_attacking(p,atk)
  # A triggered effect may remove the attacker before the defender reacts.
  if atk not in p.z.battle:
   self.audited("ATTACK_TERMINATED_AFTER_ATTACK_EFFECTS",p.seat,atk.card,attacker=atk.key())
   return True
  # After attacking effects and before security checks: Counter then Block
  # timing. Counter paths are handled by the loaded engine; unsupported
  # Counter effects must fail closed before verified certification.
  if hasattr(self,'resolve_block_timing'):
   result=self.resolve_block_timing(p,atk,enemy)
   if result:return True
  else:
   for b in enemy.digimon():
    if b.key() not in enemy.suspended and any(
         '＜Blocker＞' in src(enemy.seat,x.card)['card_text']
         for x in enemy.stacks.get(b.key(),[b])):
     self.audited('BLOCKER_OPTION_DECLINED',enemy.seat,b.card)
  if not enemy.z.security:
   self.winner=p.seat
   self.event('GAME_END',winner=p.seat,reason='SUCCESSFUL_PLAYER_ATTACK_WITH_EMPTY_SECURITY')
   return True
  stack=p.stacks.get(atk.key(),[atk]);top=src(p.seat,atk.card)
  checks=1+(1 if '＜Security A. +1＞' in top['card_text'] else 0)
  checks+=p.z.statuses.get(atk.key(),{}).get('security_attack_delta',0)
  if checks<=0:
   self.audited('ZERO_SECURITY_CHECKS',p.seat,atk.card);return True
  for _ in range(checks):
   if not enemy.z.security:break
   self._security_removal_eligible(enemy)
   card=enemy.z.security[-1]
   if '[Security' in src(enemy.seat,card.card)['card_text']:
    # Preflight supported resolution before consuming security.
    t=src(enemy.seat,card.card)['card_text']
    if '[Security Effect]' in t and not (
      ('Play this card without paying' in t and src(enemy.seat,card.card)['type']=='Tamer') or
      '[Security] Place this card in the battle area.' in t or card.card in ('EX12-074','EX12-070')):
      raise JudgeHalt('SECURITY_EFFECT_NOT_CERTIFIED: '+card.card)
   enemy.z.security.pop()
   self.event('SECURITY_CHECK',card=card.key(),attacker=atk.key())
   # Official Q5717: immediately process [Security] before pending triggers
   # from removing a security card.
   if self._security_effect(enemy,card):
    if hasattr(self,'_after_security_removed'):self._after_security_removed(enemy)
    if atk not in p.z.battle:return True
    continue
   if 'Digimon' in src(enemy.seat,card.card)['type']:
    if atk not in p.z.battle:
     enemy.z.trash.append(card)
    else:
     defender_dp=self._dp(enemy,card)
     atk_dp=self._dp(p,atk)
     enemy.z.trash.append(card)
     if defender_dp>=atk_dp:
      self._delete(p,atk,'SECURITY_BATTLE')
      self.audited('SECURITY_BATTLE_ATTACKER_DELETED',p.seat,atk.card,
          attacker_dp=atk_dp,security_dp=defender_dp)
     else:
      self.audited('SECURITY_BATTLE_ATTACKER_SURVIVED',p.seat,atk.card,
         attacker_dp=atk_dp,security_dp=defender_dp)
   else:
    enemy.z.trash.append(card)
   if hasattr(self,'_after_security_removed'):self._after_security_removed(enemy)
   if atk not in p.z.battle:return True
  return True
 def hard_play(self,p):
  # Decision heuristic: when a ready attacker exists, attempt the attack
  # before playing yet another Digimon. Strategy is preliminary, not trained.
  if getattr(self,'selected_main_card',None) is None and any(c.key() not in p.suspended and (c.key() not in p.sick or p.z.statuses.get(c.key(),{}).get('rush')) and
    not p.z.statuses.get(c.key(),{}).get('cant_attack') for c in p.digimon()):
   return False
  return super().hard_play(p)

if __name__=='__main__':
 import collections,json
 from pathlib import Path
 rows=[AttackMatch(i).run() for i in range(60)]
 info={'first_counts':dict(collections.Counter(r['first'] for r in rows)),
       'valid_complete_matches':sum(r['status']=='VALID_COMPLETE_GAME' for r in rows),
       'halts':dict(collections.Counter(r['halt_reason'] for r in rows if r['halt_reason'])),
       'mean_turns':sum(r['turn'] for r in rows)/60,
       'judge_path_count':sum(r['judge_path_count'] for r in rows), 'rows':rows}
 Path('ATTACK_LAYER_60.json').write_text(json.dumps(info,indent=2)+'\n')
 print(json.dumps({k:v for k,v in info.items() if k!='rows'},indent=2))
