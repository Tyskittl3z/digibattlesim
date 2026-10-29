"""Fresh loaded-deck Ryugumon mandatory suppression; no cross-matchup state."""
from __future__ import annotations
import json,collections
from pathlib import Path
from matchup_v7 import MatchV7
from full_match_attempt import src
from loaded_effects import JudgeHalt

class MatchV8(MatchV7):
 def evolution_candidates(self,p):
  choices=super().evolution_candidates(p)
  updated=[]
  for cost,zone,base,card in choices:
   if (p.seat=='B' and zone=='battle' and base.card=='EX12-020' and
        'TB' in src(p.seat,card.card)['traits']):
    updated.append((max(0,cost-1),zone,base,card))
   else:updated.append((cost,zone,base,card))
  return sorted(updated,key=lambda x:(x[0],x[2].key(),x[3].key()))
 def _ryugumon_trigger(self,who):
  if who.seat!='B':return
  attackers=[x for x in who.digimon() if x.card=='EX12-036']
  if not attackers:return
  foe=self.ps['A']
  for ryu in attackers:
   once='ryugumon_on_own_play_or_evolve:'+ryu.key()
   if once in who.once_used:continue
   candidates=foe.digimon()
   if not candidates:continue
   target=self.choose_enemy_target(foe,candidates,ryu.card) if hasattr(self,"choose_enemy_target") else min(candidates)
   status=foe.z.statuses.setdefault(target.key(),{})
   status.update(cant_suspend=True,cant_when_digivolve=True,
                 expires='end_of_affected_player_next_turn')
   who.once_used.add(once)
   self.audited('RYUGUMON_MANDATORY_SUPPRESSION',who.seat,ryu.card,target=target.key(),
                target_affected_through_digivolution=True)
 def _digivolving_effect(self,p,card):
  x=next((x for x in p.digimon() if x.card==card),None)
  if x and p.z.statuses.get(x.key(),{}).get('cant_when_digivolve'):
   self.audited('WHEN_DIGIVOLVING_PREVENTED_BY_RYUGUMON',p.seat,card,source_card=x.key())
   return
  return super()._digivolving_effect(p,card)
 def evolve(self,p,action):
  oldevents=len(self.events)
  if p.seat=='B' and action[1]=='battle' and action[2].card=='EX12-020' and 'TB' in src(p.seat,action[3].card)['traits']:
   self.audited('GASAMON_TB_DIGIVOLVE_COST_MINUS_ONE',p.seat,'EX12-020',resulting_cost=action[0],target=action[3].key())
  result=super().evolve(p,action)
  if p.seat=='B' and action[1]=='battle':self._ryugumon_trigger(p)
  return result
 def hard_play(self,p):
  before={x.key() for x in p.digimon()}
  r=super().hard_play(p)
  if r and p.seat=='B':
   after={x.key() for x in p.digimon()}
   if after-before:self._ryugumon_trigger(p)
  return r
 def _delete(self,p,c,why):
  prior=len(self.events)
  r=super()._delete(p,c,why)
  if p.seat=='B' and any(e.get('kind')=='KAGUYAMON_FORTITUDE_REPLAY' for e in self.events[prior:]):
   self._ryugumon_trigger(p)
  return r

def batch():
 rows=[MatchV8(i).run() for i in range(60)]
 return {'schema':'fresh-matches-after-ryugumon-mandatory-trigger-v8',
   'attempted':60,'software_completed':sum(x['status']=='VALID_COMPLETE_GAME' for x in rows),
   'judge_certified':0,'starts':dict(collections.Counter(x['first'] for x in rows)),
   'engine_wins':dict(collections.Counter(x['winner'] for x in rows if x['winner'])),
   'halts':dict(collections.Counter(x['halt_reason'] for x in rows if x['halt_reason'])),
   'ryugumon_suppressions':sum(p['kind']=='RYUGUMON_MANDATORY_SUPPRESSION' for r in rows for p in r['judge_paths']),
   'rows':rows}
if __name__=='__main__':
 report=batch();Path('V8_MATCHES.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
