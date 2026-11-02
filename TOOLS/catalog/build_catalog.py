"""Fetch and pin official category HTML; reproducibly compile browser chunks."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip, hashlib, json, re, subprocess, sys
from parse_official import categories, parse_cards, has_card_markup, parse_errata, parse_restrictions
ROOT=Path(__file__).resolve().parents[2]
SOURCES=ROOT/'TOOLS/catalog/sources'
OUT=ROOT/'APP/catalog'
def encode(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def digest(b): return hashlib.sha256(b).hexdigest()
def fetch(category):
    path=SOURCES/(category+'.html.gz')
    if path.exists(): return
    url='https://world.digimoncard.com/cards/?search=true&category='+category
    p=subprocess.run(['curl','-sSL','--fail','--retry','3','--max-time','90',url],capture_output=True)
    if p.returncode: raise RuntimeError(f'Fetch {category} failed: {p.stderr.decode()[:120]}')
    text=p.stdout.decode('utf-8')
    if not has_card_markup(text): raise ValueError('No cards in '+category)
    path.write_bytes(gzip.compress(p.stdout,mtime=0))
    print('Pinned',category,flush=True)
def build(download=False):
    SOURCES.mkdir(parents=True,exist_ok=True); (OUT/'chunks').mkdir(parents=True,exist_ok=True)
    index=SOURCES/'index.html.gz'
    if not index.exists():
        if not download: raise ValueError('Run --fetch first')
        raw=subprocess.check_output(['curl','-sSL','--fail','--max-time','90','https://world.digimoncard.com/cardlist/'])
        index.write_bytes(gzip.compress(raw,mtime=0))
    cats=categories(gzip.decompress(index.read_bytes()).decode())
    if download:
        for name,url in [('errata','https://world.digimoncard.com/rule/errata_card/'),('restrictions','https://world.digimoncard.com/rule/restriction_card/')]:
            path=SOURCES/(name+'.html.gz')
            if not path.exists():
                raw=subprocess.check_output(['curl','-sSL','--fail','--retry','3','--max-time','90',url])
                path.write_bytes(gzip.compress(raw,mtime=0))
        with ThreadPoolExecutor(max_workers=6) as pool: list(pool.map(fetch,cats))
    cards={}; source_records=[]; conflicts=[]; total=0
    for category,title in cats.items():
        raw=gzip.decompress((SOURCES/(category+'.html.gz')).read_bytes())
        parsed=parse_cards(raw.decode()); total+=len(parsed)
        source_records.append({'category':category,'title':title,'url':'https://world.digimoncard.com/cards/?search=true&category='+category,'sha256':digest(raw),'records':len(parsed)})
        for card in parsed:
            card['source_category']=category
            if card['id'] in cards:
                old=cards[card['id']]
                changed=[k for k in ['name','type','level','colors','play_cost','effect'] if old[k]!=card[k]]
                if changed: conflicts.append({'id':card['id'],'fields':changed,'preferred_source':old['source_category'],'other_source':category})
            else: cards[card['id']]=card
    # Newest displayed category wins for display only; conflicts never certify rules.
    conflicted={c['id'] for c in conflicts}
    for card in cards.values(): card['source_conflict']=card['id'] in conflicted
    errata_raw=gzip.decompress((SOURCES/'errata.html.gz').read_bytes())
    errata=parse_errata(errata_raw.decode())
    for card_id,records in errata.items():
        if card_id in cards: cards[card_id]['errata']=records
    chunks={}
    for prefix in sorted({key.split('-')[0] for key in cards}):
        group={k:v for k,v in cards.items() if k.split('-')[0]==prefix}; raw=encode(group)
        path='chunks/'+prefix+'.json'; (OUT/path).write_bytes(raw)
        chunks[prefix]={'path':path,'sha256':digest(raw),'count':len(group)}
    manifest={'schema':'digimon-official-catalog-v1','language':'en','region':'English official site',
        'snapshot_date':'2026-11-02','card_count':len(cards),'category_records':total,'category_count':len(cats),
        'chunks':chunks,'sources':source_records,'conflicts':conflicts,'simulation_support':'UNVERIFIED',
        'errata':{'url':'https://world.digimoncard.com/rule/errata_card/','sha256':digest(errata_raw),'affected_ids':sorted(errata)},
        'notice':'Official card metadata is not verified executable gameplay. Conflicting reprint text remains flagged.'}
    restriction_raw=gzip.decompress((SOURCES/'restrictions.html.gz').read_bytes())
    restrictions=parse_restrictions(restriction_raw.decode())
    lock={**restrictions,'schema':'english-construction-snapshot-v1','format':'English constructed','as_of':'2026-11-02','verified':True,'source_url':'https://world.digimoncard.com/rule/restriction_card/','source_sha256':digest(restriction_raw),'effective_date':'2026-09-01','limitations':['Release eligibility and event-specific rules are not certified.','Construction checks do not certify gameplay rules.']}
    (OUT/'restrictions.json').write_bytes(encode(lock))
    (OUT/'manifest.json').write_bytes(encode(manifest))
    print(json.dumps({'cards':len(cards),'categories':len(cats),'chunks':len(chunks),'conflicts':len(conflicts)},sort_keys=True))
if __name__=='__main__': build('--fetch' in sys.argv)
