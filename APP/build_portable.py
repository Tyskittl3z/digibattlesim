"""Embed the same app, data and verified catalog into one portable HTML file."""
from pathlib import Path
import hashlib,json,re
APP=Path(__file__).resolve().parent

def build():
    manifest=json.loads((APP/'catalog/manifest.json').read_bytes())
    bundle={'raws':[(APP/p).read_text() for p in ['catalog/manifest.json','catalog/restrictions.json','app-data.json']],
            'chunks':{prefix:(APP/'catalog'/chunk['path']).read_text() for prefix,chunk in manifest['chunks'].items()}}
    html=(APP/'index.html').read_text()
    html=re.sub(r'<link rel="(?:manifest|icon)"[^>]*>','',html)
    html=html.replace('<link rel="stylesheet" href="shell/style.css">','<style>'+(APP/'shell/style.css').read_text()+'</style>')
    def embed(match):
        code=(APP/match[1]).read_text();code=re.sub(r'</script',lambda _:r'<\/script',code,flags=re.I)
        return '<script>'+code+'</script>'
    html=re.sub(r'<script src="([^"]+)"></script>',embed,html)
    data=json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    html=html.replace('<script>', '<script type="application/json" id="portable-data">'+data+'</script><script>window.__portableData=JSON.parse(document.getElementById("portable-data").textContent);</script><script>',1)
    html=html.replace('<a href="DeckCompare.html">Single-file fallback ↗</a>','<span>PORTABLE EDITION · FULL CATALOG</span>')
    path=APP/'DigiBattle-DeckLab.html';path.write_text(html,encoding='utf-8');print(f'Built {path.name}: {path.stat().st_size:,} bytes; all 4,481 card records embedded.')
    release_path=APP/'release-manifest.json'
    release=json.loads(release_path.read_bytes())
    release['generated']={name:hashlib.sha256((APP/name).read_bytes()).hexdigest() for name in ['service-worker.js','DigiBattle-DeckLab.html']}
    release_path.write_text(json.dumps(release,sort_keys=True,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return path
if __name__=='__main__':build()
