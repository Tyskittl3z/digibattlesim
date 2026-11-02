"""Actual JS/Python handoff, with no gameplay execution or certification."""
import copy,hashlib,importlib.util,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ENGINE=ROOT/'TOOLS/engine'
sys.path.insert(0,str(ENGINE))

def module(name):
 path=ENGINE/(name+'.py');assert path.exists(),name+' implementation is missing'
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def hashed(v):return hashlib.sha256(canonical(v).encode()).hexdigest()

class HandoffTests(unittest.TestCase):
 def ready(self):return module('readiness').snapshot(ROOT)
 def request(self,mode='exact'):
  ready=self.ready()
  script=r'''
const fs=require('node:fs');require('./APP/core/identity.js');const core=require('./APP/compare.js');const Bridge=require('./APP/core/engine.js');
(async()=>{const ready=JSON.parse(fs.readFileSync(0,'utf8')),meta=JSON.parse(fs.readFileSync('APP/app-data.json')),catalog={};for(const f of fs.readdirSync('APP/catalog/chunks'))Object.assign(catalog,JSON.parse(fs.readFileSync('APP/catalog/chunks/'+f)));
let a=fs.readFileSync('DECKS/JUPITERMON.txt','utf8'),b=fs.readFileSync('DECKS/AMATERASUMON_TOHO.txt','utf8');
const mode=process.argv[1];if(mode==='swap')[a,b]=[b,a];if(mode==='unknown')a='4 BT1-010';if(mode==='bom')a='\ufeff'+a.replaceAll('\n','\r\n');
const deps={catalog:await DeckIdentity.hash(fs.readFileSync('APP/catalog/manifest.json')),restrictions:await DeckIdentity.hash(fs.readFileSync('APP/catalog/restrictions.json')),app:meta.source_files,engine_readiness:await DeckIdentity.hash(DeckIdentity.canonical(ready)),mechanics:'UNVERIFIED',rules:'UNVERIFIED',pilots:'UNVERIFIED',roadmaps:'UNVERIFIED'};
const report=await core.buildReport({text:a,filename:'deck A.txt'},{text:b,filename:'deck B.txt'},{...meta,catalog});report.dependencies=deps;report.identity=await DeckIdentity.identify(core.parseDeck(a),core.parseDeck(b),deps);report.engine_readiness=ready;
process.stdout.write(JSON.stringify(await Bridge.prepare(report)));})();
'''
  self.assertTrue((ROOT/'APP/core/engine.js').exists(),'JS handoff is missing')
  p=subprocess.run(['node','-e',script,mode],cwd=ROOT,input=json.dumps(ready),capture_output=True,text=True,check=True)
  return json.loads(p.stdout)
 def validate(self,request):return module('request').validate(request,ROOT)
 def resign(self,r):r['request_id']=hashed(r['payload']);return r
 def test_readiness_reports_actual_blockers_without_promoting_diagnostics(self):
  ready=self.ready();self.assertFalse(ready['execution_enabled']);self.assertEqual(ready['diagnostic']['attempted'],60);self.assertEqual(ready['diagnostic']['software_completed'],29);self.assertEqual(ready['diagnostic']['halts'],31);self.assertEqual(ready['diagnostic']['reviewed_matches'],0)
  self.assertTrue(any(x['card']=='EX12-062' and x['field']=='colors' for x in ready['metadata_drift']))
  self.assertIn('SOURCE_OR_DECK_CHANGED',{x['code'] for x in ready['blockers']})
 def test_actual_js_request_validates_but_is_blocked_from_running(self):
  result=self.validate(self.request());self.assertTrue(result['request_valid']);self.assertFalse(result['can_execute']);self.assertEqual(result['status'],'BLOCKED');self.assertTrue(result['supported_pairing']);self.assertTrue(result['blockers'])
 def test_exact_bom_and_crlf_survive_browser_to_python_handoff(self):
  r=self.request('bom');self.assertTrue(r['payload']['inputs']['A']['raw_text'].startswith('\ufeff'));self.assertIn('\r\n',r['payload']['inputs']['A']['raw_text']);self.assertEqual(self.validate(r)['status'],'BLOCKED')
 def test_raw_text_tampering_is_rejected(self):
  r=self.request();r['payload']['inputs']['A']['raw_text']+='\n1 BT1-010';result=self.validate(r);self.assertEqual(result['status'],'INVALID_REQUEST');self.assertFalse(result['can_execute'])
 def test_rehashed_forged_entries_still_fail_independent_raw_reparse(self):
  r=self.request();r['payload']['inputs']['A']['entries'][0]['count']+=1;result=self.validate(self.resign(r));self.assertEqual(result['status'],'INVALID_REQUEST')
 def test_stale_source_and_dependency_are_refused(self):
  for field in ['engine_snapshot_sha256','catalog_sha256']:
   r=self.request();r['payload'][field]='0'*64;result=self.validate(self.resign(r));self.assertEqual(result['status'],'STALE_REQUEST');self.assertFalse(result['can_execute'])
 def test_swapped_and_other_decks_never_inherit_matchup_evidence(self):
  for mode,status in [('swap','SEAT_MAPPING_REQUIRED'),('unknown','UNSUPPORTED_PAIRING')]:
   result=self.validate(self.request(mode));self.assertEqual(result['status'],status);self.assertEqual(result['diagnostic'],None);self.assertFalse(result['can_execute'])
 def test_client_cannot_request_execution_or_claim_a_passed_gate(self):
  r=self.request();r['payload']['execution_requested']=True;r['payload']['eligible']=True;result=self.validate(self.resign(r));self.assertEqual(result['status'],'INVALID_REQUEST');self.assertFalse(result['can_execute'])
 def test_dependency_certification_claims_are_rejected_even_with_valid_hashes(self):
  for extra in [{'mechanics':'JUDGE_CERTIFIED'},{'eligible':True}]:
   r=self.request();p=r['payload'];p['dependencies'].update(extra)
   comps={seat:sorted([[e['id'],e['count']] for e in p['inputs'][seat]['entries']]) for seat in ['A','B']}
   p['matchup_identity']=hashed({'schema':'seated-matchup-v1','A':comps['A'],'B':comps['B'],'dependencies':p['dependencies']})
   result=self.validate(self.resign(r));self.assertFalse(result['request_valid']);self.assertEqual(result['status'],'INVALID_REQUEST')
 def test_original_file_hash_must_match_preserved_utf8_bytes(self):
  r=self.request();data=r['payload']['inputs']['A'];data['input_kind']='FILE';data['original_file_sha256']='0'*64
  self.assertEqual(self.validate(self.resign(r))['status'],'INVALID_REQUEST')
  data['original_file_sha256']=data['raw_sha256'];self.assertEqual(self.validate(self.resign(r))['status'],'BLOCKED')
 def test_malformed_payloads_fail_closed(self):
  for value in [None,[],{}, {'schema':'digibattle-engine-request-v1','payload':None}]:
   self.assertEqual(self.validate(value)['status'],'INVALID_REQUEST')
