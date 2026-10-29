"""Kaguyamon Fortitude and mandatory On Deletion branches, limited matchup."""
from matchup_v5 import MatchV5
from full_match_attempt import src
from loaded_effects import JudgeHalt
from pathlib import Path
import collections,json

class MatchV6(MatchV5):
 def _delete(self,p,c,why):
  if c.card=='EX12-065':
   stack=p.stacks.get(c.key(),[c]);op=self.ps['B' if p.seat=='A' else 'A']
   # Fortitude requires at least one evolution card. Resolve it first when
   # possible; Bandai Q6866/Q3648: moving the top card out of trash prevents
   # its pending On Deletion effect from activating.
   p.z.battle.remove(c);p.stacks.pop(c.key(),None)
   p.suspended.discard(c.key());p.sick.discard(c.key())
   if len(stack)>1:
    p.z.trash.extend(stack[:-1]);p.z.battle.append(c);p.stacks[c.key()]=[c]
    p.sick.add(c.key())
    self.audited('KAGUYAMON_FORTITUDE_REPLAY',p.seat,c.card,
       source_card=c.key(),original_sources=[x.key() for x in stack[:-1]],
       source_ruling='Q6866/Q3648')
    self.audited('KAGUYAMON_ON_PLAY_OPTION_DECLINED',p.seat,c.card)
   else:
    p.z.trash.append(c)
    targets=op.digimon()
    if targets:
     minlvl=min(src(op.seat,x.card)['level'] for x in targets)
     victim=min(x for x in targets if src(op.seat,x.card)['level']==minlvl)
     vst=op.stacks.get(victim.key(),[victim])
     # Prevent unknown replacement/Overflow branches.
     if any('＜Overflow' in src(op.seat,x.card)['card_text'] for x in vst):
      raise JudgeHalt('KAGUYAMON_ON_DELETION_TARGET_OVERFLOW')
     op.z.battle.remove(victim);op.stacks.pop(victim.key(),None)
     op.z.deck.insert(0,victim)
     op.z.trash.extend(vst[:-1])
     op.suspended.discard(victim.key());op.sick.discard(victim.key())
     self.audited('KAGUYAMON_MANDATORY_ON_DELETION_BOTTOM_DECK',p.seat,c.card,
       returned=victim.key())
    else:self.audited('KAGUYAMON_ON_DELETION_NO_DIGIMON_TARGET',p.seat,c.card)
   return
  return super()._delete(p,c,why)

def attempt(n=60):
 rows=[MatchV6(i).run() for i in range(n)]
 return {'schema':'jup-toho-v6-match-attempts','attempted_games':n,
 'engine_completed_pending_independent_judge_review':sum(x['status']=='VALID_COMPLETE_GAME' for x in rows),
 'judge_certified_complete_games':0,
 'first':dict(collections.Counter(x['first'] for x in rows)),
 'engine_winner_observations':dict(collections.Counter(x['winner'] for x in rows if x['winner'])),
 'halts':dict(collections.Counter(x['halt_reason'] for x in rows if x['halt_reason'])),
 'rows':rows}
if __name__=='__main__':
 report=attempt();Path('V6_MATCH_ATTEMPTS.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
