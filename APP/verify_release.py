"""Verify the saved release assets and the portable HTML's executable scripts."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,subprocess,sys
APP=Path(__file__).resolve().parent
class Scripts(HTMLParser):
    def __init__(self):super().__init__();self.current=None;self.scripts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script':self.current={'attrs':dict(attrs),'text':''}
    def handle_data(self,text):
        if self.current is not None:self.current['text']+=text
    def handle_endtag(self,tag):
        if tag=='script' and self.current is not None:self.scripts.append(self.current);self.current=None

def verify():
    subprocess.run([sys.executable,str(APP.parent/'TOOLS/engine/readiness.py'),'--check'],check=True,capture_output=True,text=True)
    release=json.loads((APP/'release-manifest.json').read_bytes())
    for name,expected in release['assets'].items():
        assert hashlib.sha256((APP/name).read_bytes()).hexdigest()==expected,'Release asset changed: '+name
    for name in ['service-worker.js','DigiBattle-DeckLab.html']:
        expected=release.get('generated',{}).get(name)
        assert expected and hashlib.sha256((APP/name).read_bytes()).hexdigest()==expected,'Generated release artifact changed or not rebuilt: '+name
    for name in ['index.html','DigiBattle-DeckLab.html']:
        html=(APP/name).read_text();parser=Scripts();parser.feed(html)
        assert '<!-- TODO' not in html
        for s in parser.scripts:
            if s['attrs'].get('type')=='application/json':json.loads(s['text']);continue
            if 'src' in s['attrs']:
                path=APP/s['attrs']['src'];assert path.is_file();code=path.read_text()
            else:code=s['text']
            subprocess.run(['node','--check'],input=code,text=True,check=True,capture_output=True)
    portable=Scripts();portable.feed((APP/'DigiBattle-DeckLab.html').read_text())
    data=json.loads(next(s['text'] for s in portable.scripts if s['attrs'].get('id')=='portable-data'))
    for raw,name in zip(data['raws'],['catalog/manifest.json','catalog/restrictions.json','app-data.json']):assert raw==(APP/name).read_text(),'Portable data is stale: '+name
    index_parser=Scripts();index_parser.feed((APP/'index.html').read_text())
    expected_scripts=[re.sub(r'</script',lambda _:r'<\/script',(APP/s['attrs']['src']).read_text(),flags=re.I) for s in index_parser.scripts if 'src' in s['attrs']]
    executable=[s['text'] for s in portable.scripts if s['attrs'].get('type')!='application/json']
    assert executable[1:]==expected_scripts,'Portable executable scripts are stale'
    assert '<style>'+(APP/'shell/style.css').read_text()+'</style>' in (APP/'DigiBattle-DeckLab.html').read_text(),'Portable styles are stale'
    manifest=json.loads(data['raws'][0])
    for prefix,chunk in manifest['chunks'].items():assert hashlib.sha256(data['chunks'][prefix].encode()).hexdigest()==chunk['sha256']
    print(f"Verified PWA release {release['version']}: {len(release['assets'])} assets; portable scripts and all embedded catalog hashes pass.")
if __name__=='__main__':verify()
