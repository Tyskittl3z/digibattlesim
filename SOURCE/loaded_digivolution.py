"""Exact loaded-deck printed digivolution validation, no other deck knowledge.

Purpose: create a *preparation* gate for the Jupitermon/Toho loaded pair.
NOT a complete Digimon rules engine. This module never produces game results.

Sources: EXACT_CARD_MANIFEST.json, from exact card text and digivolution
metadata in the source catalog. Manual verification of card-specific rules
remains required before a played game may be accepted as fact-finding.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from dataclasses import dataclass

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/'EXACT_CARD_MANIFEST.json').read_text(encoding='utf8'))
NORMAL_METADATA=json.loads((ROOT/'LOADED_PRINTED_NORMAL_COSTS.json').read_text(encoding='utf8'))
BY_SEAT={seat:{c['card_number']:c for c in obj['card_manifest']} for seat,obj in MANIFEST['decks'].items()}

class UnsupportedPrintedCondition(ValueError):
    pass

@dataclass(frozen=True)
class EvolutionOption:
    cost:int
    source:str
    condition:str


def _is_digimon(c):
    return bool(c['type'] and 'Digimon' in c['type'])

def _can_be_base(c):
    return _is_digimon(c) or c['type']=='Digi-Egg'


def standard_cost(base, target):
    """Only matches an explicitly enumerated printed from-level/color route."""
    if not _is_digimon(target) or not _can_be_base(base):
        return None
    raw=NORMAL_METADATA[target['card_number']]['raw']
    if not raw:
        return None
    match=re.fullmatch(r'([A-Za-z ]+)\s+(\d+)\s+from\s+Lv\.(\d+)',raw.strip())
    if not match:
        raise UnsupportedPrintedCondition(f'Cannot parse printed regular digivolution: {target["card_number"]}: {raw}')
    colors, cost, reqlevel=match.groups()
    accepted={x for x in colors.split() if x in {'Red','Blue','Yellow','Green','Purple','Black','White'}}
    if not accepted or base['level']!=int(reqlevel) or not accepted.intersection(base.get('colors') or []):
        return None
    return EvolutionOption(int(cost),'printed_regular',raw)


def _special_matches(base, condition):
    """Only handles syntax present on the two loaded decks; other text halts."""
    condition=condition.strip()
    possibilities=[]
    match=re.fullmatch(r'\[([^\]]+)\](?:/(.*))?',condition)
    if match:
        possibilities.append(('exact_name',match.group(1)))
        condition=match.group(2) or ''
    if condition:
        m=re.fullmatch(r'(Non-white )?Lv\.(\d+) w/((?:\[[^\]]+\]/?)+) (trait|in name)',condition)
        if m:
            nonwhite, level_s, tags, qual=m.groups()
            leveln=int(level_s)
            if nonwhite and 'White' in (base.get('colors') or []):
                possibilities.append(('no_match',None))
            elif base['level']==leveln:
                values=re.findall(r'\[([^\]]+)\]',tags)
                possibilities += [('trait' if qual=='trait' else 'name_contains',t) for t in values]
        elif re.fullmatch(r'Lv\.(\d+)',condition):
            possibilities.append(('level',int(condition[3:])))
        else:
            raise UnsupportedPrintedCondition(f'Unrecognized loaded-deck evolution predicate: {condition}')
    return any(
        (kind=='exact_name' and value==base['name']) or
        (kind=='trait' and value in base['traits']) or
        (kind=='name_contains' and value in base['name']) or
        (kind=='level' and value==base['level'])
        for kind,value in possibilities
    )


def special_options(base,target,security_count):
    if not _is_digimon(target) or not _can_be_base(base): return []
    results=[]
    for rawline in target.get('card_text','').splitlines():
        line=rawline.strip()
        if not line.startswith('[Digivolve] '):continue
        m=re.fullmatch(r'\[Digivolve\]\s+(.*?)\s*:\s*Cost\s+(\d+)( for each of your security cards)?',line)
        if not m:
            raise UnsupportedPrintedCondition(f'Unknown special digivolution {target["card_number"]}: {line}')
        condition,num,per_security=m.groups()
        if _special_matches(base,condition):
            if per_security and security_count is None:raise UnsupportedPrintedCondition('security_count required')
            count = int(num) * security_count if per_security else int(num)
            results.append(EvolutionOption(count,'printed_special',line))
    return results


def legal_printed_evolutions(seat,base_id,target_id,security_count=5):
    cards=BY_SEAT[seat]
    if base_id not in cards or target_id not in cards:
        raise ValueError('Only this loaded deck may be used')
    base,target=cards[base_id],cards[target_id]
    opts=special_options(base,target,security_count)
    normal=standard_cost(base,target)
    if normal is not None:opts.append(normal)
    return sorted(opts,key=lambda z:(z.cost,z.source,z.condition))


def report():
    results={}
    for seat,cards in BY_SEAT.items():
        evolutions=[]
        for a in cards:
            for b in cards:
                if a==b:continue
                try:
                    routes=legal_printed_evolutions(seat,a,b)
                except UnsupportedPrintedCondition as exc:
                    raise UnsupportedPrintedCondition(f'{seat}: {exc}') from exc
                if routes:
                    evolutions.append({'from':a,'to':b,'cost_min':routes[0].cost,'rules':[r.__dict__ for r in routes]})
        results[seat]={'printed_evolution_edges':len(evolutions),'edges':evolutions}
    return results

if __name__=='__main__':
    out=report()
    (ROOT/'PRINTED_EVOLUTION_COVERAGE.json').write_text(json.dumps(out,indent=2)+'\n')
    for k,v in out.items():print(k,len(BY_SEAT[k]),'loaded cards,',v['printed_evolution_edges'],'candidate printed evolutions')
