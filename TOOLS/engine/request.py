"""Validate a browser preparation request. Does not start or certify matches."""
from pathlib import Path
import argparse,json,sys
from protocol import canonical,sha,hash_object,parse_deck,composition
from readiness import snapshot,ROOT


def validate(value,root=ROOT):
    result={'schema':'digibattle-engine-preflight-v1','status':'INVALID_REQUEST','request_valid':False,'can_execute':False,'supported_pairing':False,'diagnostic':None,'blockers':[]}
    def block(code,detail):result['blockers'].append({'code':code,'detail':detail})
    try:
        if not isinstance(value,dict) or set(value)!={'schema','request_id','payload'} or value['schema']!='digibattle-engine-request-v1':raise ValueError('Unknown or malformed request envelope.')
        p=value['payload'];fields={'protocol_version','operation','execution_requested','matchup_identity','inputs','dependencies','engine_snapshot_sha256','catalog_sha256','restrictions_sha256'}
        if not isinstance(p,dict) or set(p)!=fields:raise ValueError('Unknown or missing preparation fields.')
        if type(p['protocol_version']) is not int or p['protocol_version']!=1 or p['operation']!='PREPARE_MATCHUP' or p['execution_requested'] is not False:raise ValueError('Only non-executing PREPARE_MATCHUP requests are supported.')
        if value['request_id']!=hash_object(p):raise ValueError('Preparation request hash mismatch.')
        inputs=p['inputs']
        if not isinstance(inputs,dict) or set(inputs)!={'A','B'}:raise ValueError('Exactly two seated deck inputs are required.')
        comps={}
        for seat in ['A','B']:
            data=inputs[seat]
            if not isinstance(data,dict) or set(data)!={'raw_text','raw_sha256','composition_sha256','filename','original_file_sha256','input_kind','entries'}:raise ValueError('Malformed input '+seat)
            if not isinstance(data['filename'],str) or data['input_kind'] not in ['FILE','PASTE','EXAMPLE']:raise ValueError('Malformed input metadata: '+seat)
            if data['input_kind']=='FILE':
                if data['original_file_sha256']!=data['raw_sha256']:raise ValueError('Original UTF-8 file-byte hash mismatch: '+seat)
            elif data['original_file_sha256'] is not None:raise ValueError('Non-file inputs cannot claim original file-byte hashes: '+seat)
            if not isinstance(data['raw_text'],str) or data['raw_sha256']!=sha(data['raw_text']):raise ValueError('Preserved text hash mismatch: '+seat)
            entries=data['entries']
            if not isinstance(entries,list) or not entries or not all(isinstance(e,dict) and set(e)=={'id','count'} and isinstance(e['id'],str) and type(e['count']) is int and e['count']>0 for e in entries):raise ValueError('Invalid entry schema: '+seat)
            parsed=parse_deck(data['raw_text']);comp=composition(parsed)
            if comp!=composition(entries) or len({e['id'] for e in entries})!=len(entries):raise ValueError('Raw text and declared composition disagree: '+seat)
            if data['composition_sha256']!=sha(canonical(comp)):raise ValueError('Composition hash mismatch: '+seat)
            comps[seat]=comp
        deps=p['dependencies']
        dependency_keys={'catalog','restrictions','app','engine_readiness','mechanics','rules','pilots','roadmaps'}
        if not isinstance(deps,dict) or set(deps)!=dependency_keys or any(deps[k]!='UNVERIFIED' for k in ['mechanics','rules','pilots','roadmaps']):raise ValueError('Unknown dependencies or client certification claims are not allowed.')
        if not isinstance(deps,dict) or p['matchup_identity']!=hash_object({'schema':'seated-matchup-v1','A':comps['A'],'B':comps['B'],'dependencies':deps}):raise ValueError('Matchup identity mismatch.')
        ready=snapshot(root);meta=json.loads((Path(root)/'APP/app-data.json').read_bytes())
        app_files=meta['source_files'];app_current=all(sha((Path(root)/name).read_bytes())==digest for name,digest in app_files.items()) and hash_object(meta.get('engine_readiness'))==hash_object(ready)
        expected={'engine_snapshot_sha256':ready['source_snapshot_sha256'],'catalog_sha256':ready['catalog_sha256'],'restrictions_sha256':ready['restrictions_sha256']}
        stale=any(p[k]!=v for k,v in expected.items()) or deps.get('engine_readiness')!=hash_object(ready) or deps.get('catalog')!=ready['catalog_sha256'] or deps.get('restrictions')!=ready['restrictions_sha256'] or deps.get('app')!=app_files or not app_current
        result['request_valid']=True
        if stale:
            result['status']='STALE_REQUEST';block('STALE_DEPENDENCY','Rebuild/reopen the current app and export a fresh request.');return result
        a,b=ready['supported_decks']['A']['composition'],ready['supported_decks']['B']['composition']
        if comps['A']!=a or comps['B']!=b:
            result['status']='SEAT_MAPPING_REQUIRED' if comps['A']==b and comps['B']==a else 'UNSUPPORTED_PAIRING'
            block(result['status'],'This engine is scoped to exact Jupitermon A / Amaterasumon-Toho B inputs. No other matchup evidence is reused.');return result
        result.update(status='BLOCKED',supported_pairing=True,diagnostic=ready['diagnostic'],source_snapshot_sha256=ready['source_snapshot_sha256'])
        result['blockers']=ready['blockers']+[{'code':'PREPARATION_ONLY','detail':'Request validated. No game was started; verified gameplay and review gates remain required.'}]
    except (OSError,ValueError,KeyError,TypeError,AttributeError,UnicodeError) as error:
        block('INVALID_REQUEST',str(error))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request',type=Path);args=p.parse_args()
    try:
        if args.request.stat().st_size>4000000:raise ValueError('Request exceeds 4 MB limit.')
        data=json.loads(args.request.read_bytes())
    except (OSError,ValueError) as error:
        print(json.dumps({'status':'INVALID_REQUEST','can_execute':False,'error':str(error)}));raise SystemExit(1)
    result=validate(data);print(json.dumps(result,indent=2));raise SystemExit(2 if result['request_valid'] else 1)
if __name__=='__main__':main()
