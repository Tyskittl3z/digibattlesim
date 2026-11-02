"""Package current committed source and successful verification logs without nesting backups."""
from pathlib import Path
import hashlib,io,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT)
    if git('status','--porcelain','--untracked-files=no').strip():raise SystemExit('Commit source changes before packaging.')
    report=json.loads((ROOT/'work/verification/results.json').read_bytes())
    if report['status']!='PASSED' or not report['browser_checks_included']:raise SystemExit('Run the complete software verification before packaging.')
    commit=git('rev-parse','HEAD').decode().strip();prefix='DigiBattle-Rebuilt/'
    output=ROOT/'BACKUPS/DigiBattle-Rebuilt-2026-11-02.zip';output.parent.mkdir(exist_ok=True)
    archive=git('archive','--format=zip','--prefix='+prefix,'HEAD')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as target:
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            for item in source.infolist():
                if item.filename.startswith(prefix+'BACKUPS/'):continue
                target.writestr(item,source.read(item.filename))
        target.writestr(prefix+'START-HERE.md',f'''# DigiBattle Deck Lab

Open APP/DigiBattle-DeckLab.html for the full portable app. For the installable
PWA and stable saved-workspace storage, follow APP/README.md.

The source is prepared for battle-simulation integration. It exports exact-input
preparation requests and shows actual engine readiness blockers. No unverified
battles or win rates are provided. See docs/ENGINE_HANDOFF.md for the next engine
work and request-validation command.

Source commit: {commit}
Automated tests passed: {report['tests_passed']}

This ZIP contains the complete current source, official source snapshots, built
apps and verification logs. Nested prior ZIPs are intentionally excluded. Complete
Git history remains on the GitHub general-browser-simulator branch. To initialize
a new local checkout from this extracted source, run git init and git add . before
committing; do not overwrite any existing engine-chat branch or worktree.
''')
        target.writestr(prefix+'VERIFICATION/results.json',json.dumps(report,indent=2)+'\n')
        for check in report['checks']:
            log=ROOT/'work/verification'/check['log']
            if hashlib.sha256(log.read_bytes()).hexdigest()!=check['log_sha256']:raise ValueError('Verification log changed: '+log.name)
            target.write(log,prefix+'VERIFICATION/'+log.name)
        target.writestr(prefix+'VERIFICATION/source-commit.txt',commit+'\n')
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity failure.')
        if z.read(prefix+'APP/DigiBattle-DeckLab.html')!=(ROOT/'APP/DigiBattle-DeckLab.html').read_bytes():raise ValueError('Portable app mismatch.')
    (ROOT/'BACKUPS/SHA256SUMS.txt').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n'+hashlib.sha256((ROOT/'APP/DigiBattle-DeckLab.html').read_bytes()).hexdigest()+'  ../APP/DigiBattle-DeckLab.html\n')
    print(f'Verified backup: {output.stat().st_size:,} bytes, source {commit}, {report["tests_passed"]} tests.')
if __name__=='__main__':main()
