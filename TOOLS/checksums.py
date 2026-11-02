"""Refresh or check the current tracked-file inventory, excluding backup archives."""
from pathlib import Path
import argparse,hashlib,re,subprocess
ROOT=Path(__file__).resolve().parents[1];MANIFEST=ROOT/'CURRENT_SHA256SUMS.txt'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def tracked():
 result=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True)
 if result.returncode:return None
 return sorted(n for n in result.stdout.decode().split('\0') if n and n!='CURRENT_SHA256SUMS.txt' and not n.startswith('BACKUPS/'))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
 if args.check:
  rows=MANIFEST.read_text().splitlines();errors=[];names=[]
  if not rows:raise SystemExit('Current checksum inventory is empty.')
  for row in rows:
   if not re.fullmatch(r'[a-f0-9]{64}  .+',row):raise SystemExit('Malformed current checksum row.')
   expected,name=row.split('  ',1);names.append(name);path=(ROOT/name).resolve()
   if not path.is_relative_to(ROOT) or not path.is_file() or digest(path)!=expected:errors.append(name)
  if len(names)!=len(set(names)):raise SystemExit('Duplicate current checksum entries.')
  expected_names=tracked()
  if expected_names is not None and set(names)!=set(expected_names):raise SystemExit('Current checksum inventory differs from tracked files: '+', '.join(sorted(set(names)^set(expected_names))))
  if errors:raise SystemExit('Stale current checksums: '+', '.join(errors))
  print(f'Current checksums verified: {len(rows)} tracked files.');return
 names=tracked()
 if names is None:raise SystemExit('Refreshing the inventory requires a Git checkout.')
 MANIFEST.write_text(''.join(digest(ROOT/name)+'  '+name+'\n' for name in names));print(f'Recorded {len(names)} current tracked-file hashes; backup archives excluded.')
if __name__=='__main__':main()
