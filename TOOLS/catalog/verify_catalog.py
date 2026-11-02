"""Verify generated catalog completeness, official source pins and sample coverage."""
from pathlib import Path
import gzip,hashlib,json,re
from parse_official import categories,parse_cards,parse_restrictions
ROOT=Path(__file__).resolve().parents[2]
def verify(root=ROOT):
    out=root/'APP/catalog';sources=root/'TOOLS/catalog/sources';manifest=json.loads((out/'manifest.json').read_bytes())
    cats=categories(gzip.decompress((sources/'index.html.gz').read_bytes()).decode())
    assert len(cats)==manifest['category_count']
    assert set(cats)=={s['category'] for s in manifest['sources']}
    for source in manifest['sources']:
        raw=gzip.decompress((sources/(source['category']+'.html.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==source['sha256'],source['category']+' source hash'
        assert len(parse_cards(raw.decode()))==source['records']
    cards={}
    for prefix,chunk in manifest['chunks'].items():
        raw=(out/chunk['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==chunk['sha256'],prefix+' chunk hash'
        group=json.loads(raw);assert len(group)==chunk['count']
        for key,c in group.items():
            assert key==c['id'] and key.split('-')[0]==prefix
            assert c['name'] and c['type']
            assert c['simulation_support']=='UNVERIFIED'
            assert key not in cards
        cards.update(group)
    assert len(cards)==manifest['card_count']
    for deck in ['JUPITERMON.txt','AMATERASUMON_TOHO.txt']:
        ids=set(re.findall(r'\b[A-Z]+\d*-\d{2,3}\b',(root/'DECKS'/deck).read_text()))
        assert ids<=cards.keys(), ids-cards.keys()
    lock=json.loads((out/'restrictions.json').read_bytes());raw=gzip.decompress((sources/'restrictions.html.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==lock['source_sha256']
    current=parse_restrictions(raw.decode());assert current['limits']==lock['limits'] and current['pairs']==lock['pairs']
    raw=gzip.decompress((sources/'errata.html.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==manifest['errata']['sha256']
    assert set(lock['limits'])<=cards.keys()
    print(f"Verified {len(cards)} cards, {len(cats)} categories, {len(manifest['chunks'])} chunks, {len(lock['limits'])} restricted/banned IDs and {len(lock['pairs'])} banned pairs.")
if __name__=='__main__':verify()
