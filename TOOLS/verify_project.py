"""One-command software verification. Passing does not certify gameplay rules."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skip-browser',action='store_true',help='Skip real-browser checks; not a release verification.');args=p.parse_args()
 work=ROOT/'work/verification';work.mkdir(parents=True,exist_ok=True)
 commands=[
  ('checksum tests',[sys.executable,'-m','unittest','discover','-s','TOOLS/tests','-q'],ROOT),
  ('catalog fixtures',[sys.executable,'-m','unittest','discover','-s','TOOLS/catalog/tests','-q'],ROOT),
  ('catalog integrity',[sys.executable,'TOOLS/catalog/verify_catalog.py'],ROOT),
  ('engine readiness',[sys.executable,'TOOLS/engine/readiness.py','--check'],ROOT),
  ('legacy build',[sys.executable,'APP/build.py'],ROOT),
  ('PWA build',[sys.executable,'APP/build_pwa.py'],ROOT),
  ('portable build',[sys.executable,'APP/build_portable.py'],ROOT),
  ('release integrity',[sys.executable,'APP/verify_release.py'],ROOT),
  ('JavaScript behavior',['node','--test',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'APP/tests').glob('*.test.cjs'))]],ROOT),
  ('engine handoff',[sys.executable,'-m','unittest','discover','-s','TOOLS/engine/tests','-q'],ROOT),
  ('engine regressions',[sys.executable,'-m','unittest','discover','-p','test_*.py','-q'],ROOT/'SOURCE'),
  ('app checks',[sys.executable,'-m','unittest','discover','-s','APP/tests','-p','test_build.py' if args.skip_browser else 'test_*.py','-q'],ROOT),
 ]
 record={'status':'RUNNING','browser_checks_included':not args.skip_browser,'checks':[],'tests_passed':0};report=work/'results.json';report.write_text(json.dumps(record,indent=2)+'\n')
 for index,(name,command,cwd) in enumerate(commands):
  started=time.monotonic();result=subprocess.run(command,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  log=work/(f'{index+1:02d}-'+name.replace(' ','-')+'.txt');log.write_text(result.stdout)
  count=re.search(r'Ran (\d+) tests?',result.stdout) or re.search(r'ℹ tests (\d+)',result.stdout)
  tests=int(count[1]) if count else 0
  record['checks'].append({'name':name,'log':log.name,'exit_code':result.returncode,'tests':tests,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
  if result.returncode==0:record['tests_passed']+=tests
  else:record['status']='FAILED'
  report.write_text(json.dumps(record,indent=2)+'\n')
  print(f"{'PASS' if result.returncode==0 else 'FAIL'} {name} ({time.monotonic()-started:.1f}s)",flush=True)
  if result.returncode:print(result.stdout);raise SystemExit(result.returncode)
 record['status']='PASSED';report.write_text(json.dumps(record,indent=2)+'\n')
 print('Software checks passed. Battle execution remains blocked by engine readiness; no matches were played.')
 if args.skip_browser:print('Browser checks were skipped. Run without --skip-browser before release.')
if __name__=='__main__':main()
