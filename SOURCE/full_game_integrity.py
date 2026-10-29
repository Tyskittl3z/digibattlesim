"""Fix post-victory continuation; source-bound, fail-closed game result."""
from __future__ import annotations
import collections,json
from pathlib import Path
from security_attack_layer import AttackMatch,JudgeHalt,src
from seeded_opening_probe import _select_main_action, COSTS

class FullGame(AttackMatch):
 def hard_play(self,p):
  if getattr(self,'selected_main_card',None) is None and any(c.key() not in p.suspended and (c.key() not in p.sick or p.z.statuses.get(c.key(),{}).get('rush')) and
   not p.z.statuses.get(c.key(),{}).get('cant_attack') for c in p.digimon()):
   return False
  c=getattr(self,'selected_main_card',None) or _select_main_action(p.z)
  if not c:return False
  if c.card not in ('BT25-033','EX12-031','EX12-036','EX12-065','BT26-016',
                   'BT26-029','EX12-046','BT26-014','EX12-047','BT25-025','EX12-063'):
   return super().hard_play(p)
  price=COSTS[c.card]['play_cost']
  if not isinstance(price,int):raise JudgeHalt('PLAY_COST_UNVERIFIED '+c.card)
  p.z.hand.remove(c);p.z.battle.append(c)
  if 'Digimon' in src(p.seat,c.card)['type']:
   p.stacks[c.key()]=[c];p.sick.add(c.key())
  self.mem=max(-10,min(10,self.mem-price))
  self.event('PAID_PLAY',player=p.seat,card=c.key(),play_cost=price,memory_after=self.mem)
  if c.card in ('BT25-033','EX12-031','EX12-036','EX12-065','BT26-016','BT26-029'):
   self.declining(p,c.card,'On Play')
  else:self._resolve_target_effect(p,c.card)
  return True
 def run(self):
  try:
   for t in range(1,self.max_turns+1):
    self.turn=t;p=self.ps[self.active];nxt='B' if self.active=='A' else 'A'
    p.suspended={k for k in p.suspended if p.z.statuses.get(k,{}).get('cant_unsuspend')}
    
    for x in self.ps.values():x.once_used.clear()
    p.sick.clear()
    self.event('TURN_START',memory=self.mem)
    if t>1:
     self.draw_phase(p)
     if self.winner:break
    self.start_phase(p)
    for a in range(40):
     evolved=self.evolution_candidates(p)
     if hasattr(self,'choose_turn_action'):
      action=self.choose_turn_action(p,evolved)
      if action[0]=='EVOLVE':self.evolve(p,action[1]);self.actions+=1;self.verify()
      elif action[0]=='PLAY':
       self.selected_main_card=action[1]
       try:
        if not self.hard_play(p):raise JudgeHalt('SELECTED_MAIN_ACTION_NOT_EXECUTED')
       finally:self.selected_main_card=None
       self.actions+=1;self.verify()
      elif action[0]=='ATTACK':
       if not self.try_attack(p):raise JudgeHalt('SELECTED_ATTACK_NOT_EXECUTED')
       self.actions+=1;self.verify()
      elif action[0]=='PASS':self.event('PASS');self.mem=-3
      else:raise JudgeHalt('UNKNOWN_BOT_ACTION')
     elif evolved and (self.mem>0 or evolved[0][0]==0):
      self.evolve(p,evolved[0]);self.actions+=1;self.verify()
     elif self.mem>=0 and self.hard_play(p):
      self.actions+=1;self.verify()
     elif self.try_attack(p):
      self.actions+=1;self.verify()
     else:
      self.event('PASS');self.mem=-3
     self.mem=max(-10,min(10,self.mem))
     if self.winner:break
     if self.mem<0:break
    else:raise JudgeHalt('TURN_ACTION_BUDGET_EXCEEDED')
    if self.winner:
     self.verify()
     if sum(e['type']=='GAME_END' for e in self.events)==0 and not any(e['type']=='WIN_DRAW_PHASE_DECKOUT' for e in self.events):
      raise JudgeHalt('GAME_WIN_WITHOUT_END_EVENT')
     break
    self.end_turn_check(p)
    if self.winner:
     self.verify()
     # An end-of-turn effect can win via an actual attack.  Do not append
     # TURN_END or start another turn after the terminal event.
     break
    self.verify();self.event('TURN_END',memory=self.mem)
    # Expiring statuses on affected player's end turn, as printed.
    for k in list(p.z.statuses):
     if p.z.statuses[k].get('expires')=='end_of_affected_player_next_turn':
      del p.z.statuses[k]
    for other_player in self.ps.values():
     for k,status in list(other_player.z.statuses.items()):
      if status.get('p213_expires_after_seat')==self.active:
       status.pop('p213_dp_bonus',None)
       status.pop('rush',None)
       status.pop('p213_expires_after_seat',None)
       if not status:del other_player.z.statuses[k]
    self.mem=min(10,max(1,-self.mem));self.active=nxt
   else:raise JudgeHalt('TURN_LIMIT_REACHED_NO_VALID_WINNER')
   self.verify()
   status='VALID_COMPLETE_GAME' if self.winner else 'JUDGE_HALT'
   reason=None
  except (JudgeHalt,AssertionError,ValueError,KeyError,TypeError) as e:
   status='JUDGE_HALT';reason=f'{type(e).__name__}: {e}'
   self.event('JUDGE_HALT',reason=reason)
  return {'index':self.i,'seed':self.seed,'first':self.first,'status':status,
    'winner':self.winner if status=='VALID_COMPLETE_GAME' else None,
    'turn':self.turn,'actions':self.actions,'halt_reason':reason,
    'judge_path_count':len(self.checks),'judge_paths':self.checks,'events':self.events}

def run_60():
 rows=[FullGame(i).run() for i in range(60)]
 return {'schema':'jup-toho-full-game-corrected-run-v1',
 'attempted':60, 'valid_complete_matches':sum(r['status']=='VALID_COMPLETE_GAME' for r in rows),
 'starts':dict(collections.Counter(r['first'] for r in rows)),
 'winners':dict(collections.Counter(r['winner'] for r in rows if r['winner'])),
 'halts':dict(collections.Counter(r['halt_reason'] for r in rows if r['halt_reason'])),
 'judge_paths_exercised':sum(r['judge_path_count'] for r in rows),
 'rows':rows}
if __name__=='__main__':
 out=run_60();Path('FULL_GAME_V4_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
