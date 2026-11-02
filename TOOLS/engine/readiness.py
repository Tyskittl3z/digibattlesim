"""Read-only engine readiness. Never runs a game or manufactures certification."""
from collections import Counter
from pathlib import Path
import argparse,gzip,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'SOURCE'))
from evaluation_gate import assess_eligibility,read_records
from match_evidence import provenance
from protocol import canonical,sha,hash_object,parse_deck,composition


def snapshot(root=ROOT):
    root=Path(root).resolve();cohort=root/'ARTIFACTS/current-2026-10-29-02'
    gate=assess_eligibility(root,cohort);files=provenance(root)['files'].copy()
    for folder in ['TOOLS/engine','RULES','ROADMAPS']:
        for p in sorted((root/folder).glob('*')):
            if p.is_file() and (p.suffix in {'.py','.json'}) and not p.name.startswith('test_'):
                files[p.relative_to(root).as_posix()]=sha(p.read_bytes())
    paths=['APP/catalog/manifest.json','APP/catalog/restrictions.json']
    manifest=json.loads((root/'SOURCE/EXACT_CARD_MANIFEST.json').read_bytes());costs=json.loads((root/'SOURCE/LOADED_EXACT_COSTS.json').read_bytes())
    official={};drift=[];codes={c['card_number'] for d in manifest['decks'].values() for c in d['card_manifest']}
    for prefix in sorted({c.split('-')[0] for c in codes}):
        path='APP/catalog/chunks/'+prefix+'.json';paths.append(path);official.update(json.loads((root/path).read_bytes()))
    for path in paths:files[path]=sha((root/path).read_bytes())
    for code in sorted(codes):
        loaded=next(c for d in manifest['decks'].values() for c in d['card_manifest'] if c['card_number']==code)
        card=official.get(code)
        if not card:drift.append({'card':code,'field':'record','engine':'PRESENT','official':None});continue
        for field in ['name','type','level','colors']:
            before,after=loaded.get(field),card.get(field)
            if field=='colors':before,after=sorted(before or []),sorted(after or [])
            if before!=after:drift.append({'card':code,'field':field,'engine':before,'official':after})
        before=costs[code].get('play_cost');after=card.get('play_cost') if isinstance(before,int) else card.get('printed_cost')
        if before!=after:drift.append({'card':code,'field':'play_cost','engine':before,'official':after})
    summary=json.loads((cohort/'cohort.json').read_bytes());records,issues=read_records(cohort,summary)
    halts=Counter(record['transcript'].get('halt_reason') for _,record in records if record['status']=='HALT')
    blockers=gate['blockers']+[{'code':'CARD_METADATA_DRIFT','detail':f"{d['card']} {d['field']}: engine={d['engine']!r}; official={d['official']!r}"} for d in drift]
    supported={}
    for seat,filename in [('A','JUPITERMON.txt'),('B','AMATERASUMON_TOHO.txt')]:
        raw=(root/'DECKS'/filename).read_bytes();entries=parse_deck(raw.decode('utf-8'));comp=composition(entries)
        supported[seat]={'filename':filename,'composition':comp,'composition_sha256':sha(canonical(comp)),'raw_sha256':sha(raw)}
    return {'schema':'digibattle-engine-readiness-v1','protocol_version':1,'status':'BLOCKED','execution_enabled':False,
        'source_snapshot_sha256':hash_object(files),'source_files':files,'supported_decks':supported,
        'catalog_sha256':files['APP/catalog/manifest.json'],'restrictions_sha256':files['APP/catalog/restrictions.json'],
        'diagnostic':{'cohort':'ARTIFACTS/current-2026-10-29-02','cohort_sha256':sha((cohort/'cohort.json').read_bytes()),
            'attempted':len(records),'software_completed':sum(r['status']=='SOFTWARE_COMPLETED' for _,r in records),
            'halts':sum(r['status']=='HALT' for _,r in records),'starts':dict(Counter(r['first'] for _,r in records)),
            'source_current':not issues and not any(b['code'] in {'SOURCE_OR_DECK_CHANGED','PROVENANCE_HASH_MISMATCH'} for b in blockers),
            'reviewed_matches':0,'approved_routes':0,'final_matches':0,'halt_reasons':[{'reason':r,'count':n} for r,n in sorted(halts.items())]},
        'metadata_drift':drift,'blockers':blockers,
        'notice':'Snapshot of software diagnostics, not certified match evidence. PREPARE_MATCHUP never executes games.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--stdout',action='store_true');args=p.parse_args()
    ready=snapshot();raw=(canonical(ready)+'\n').encode();output=ROOT/'APP/engine/readiness.json'
    if args.stdout:print(json.dumps(ready,indent=2));return
    if args.check:
        if not output.exists() or output.read_bytes()!=raw:raise SystemExit('Engine readiness is stale. Run python TOOLS/engine/readiness.py and rebuild the app.')
        print('Engine readiness snapshot matches current source; execution remains blocked.');return
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
    print(f"Readiness snapshot: {len(ready['blockers'])} blockers, {len(ready['metadata_drift'])} metadata differences, no execution.")
if __name__=='__main__':main()
