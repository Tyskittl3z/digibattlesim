"""Rules timing checkpoint: security-effect priority and deferred DP-zero rule checks."""
from __future__ import annotations
import collections,json
from pathlib import Path
from matchup_v6 import MatchV6
from loaded_effects import JudgeHalt

class MatchV7(MatchV6):
 def __init__(self,index,max_turns=100):
  super().__init__(index,max_turns)
  self._security_pending=[]
  self._dp_zero_pending=[]
 def _apply_dp(self,p,target,delta,source):
  result=self._dp(p,target)+delta
  st=p.z.statuses.setdefault(target.key(),{})
  st['dp_delta']=st.get('dp_delta',0)+delta
  st['expires']='end_of_affected_player_next_turn'
  self.audited('DP_CHANGE_PENDING_RULE_CHECK',p.seat,target.card,source=source,delta=delta,dp_after=result)
  if result<=0:self._dp_zero_pending.append((p,target))
 def _flush_dp_check(self):
  seen=set()
  for p,target in self._dp_zero_pending:
   if target.key() in seen:continue
   seen.add(target.key())
   if target in p.z.battle and self._dp(p,target)<=0:
    self._delete(p,target,'ZERO_DP_RULE_CHECK')
  self._dp_zero_pending.clear()
 def _process_security_events(self):
  while self._security_pending:
   p=self._security_pending.pop(0)
   super()._after_security_removed(p)
   self._flush_dp_check()
 def _trash_top_security(self,p,source):
  self._preflight_security_remove(p)
  c=p.z.security.pop() if p.z.security else None
  if c:
   p.z.trash.append(c);self._security_pending.append(p)
  self.audited('TRASH_TOP_SECURITY',p.seat,source,removed=c.key() if c else None)
 def _add_top_security_hand(self,p,source):
  self._preflight_security_remove(p)
  c=p.z.security.pop() if p.z.security else None
  if c:
   p.z.hand.append(c);self._security_pending.append(p)
  self.audited('ADD_TOP_SECURITY_HAND',p.seat,source,removed=c.key() if c else None)
 def _after_security_removed(self,owner):
  super()._after_security_removed(owner)
  self._flush_dp_check()
 def _resolve_target_effect(self,p,card):
  super()._resolve_target_effect(p,card)
  self._flush_dp_check()
 def _digivolving_effect(self,p,card):
  super()._digivolving_effect(p,card)
  self._flush_dp_check()
  self._process_security_events()

if __name__=='__main__':
 rows=[MatchV7(i).run() for i in range(60)]
 data={'schema':'fresh-matchup-turn-by-turn-timing-correction-v7',
  'games_run':60,'starts':dict(collections.Counter(x['first'] for x in rows)),
  'engine_complete_pending_judge':sum(x['status']=='VALID_COMPLETE_GAME' for x in rows),
  'judge_certified':0,
  'engine_winners_only':dict(collections.Counter(x['winner'] for x in rows if x['winner'])),
  'halt_reasons':dict(collections.Counter(x['halt_reason'] for x in rows if x['halt_reason'])),
  'rows':rows}
 Path('V7_MATCHES.json').write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({k:v for k,v in data.items() if k!='rows'},indent=2))
