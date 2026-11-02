"""Stable browser/Python canonicalization and independent deck-text parsing."""
import hashlib,json,re

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(value):return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()
def hash_object(value):return sha(canonical(value))
def composition(entries):return sorted([[c['id'],c['count']] for c in entries])
def parse_deck(raw):
    if not isinstance(raw,str) or len(raw)>1000000:raise ValueError('Deck text must be a string smaller than 1 MB.')
    grouped={}
    for source in raw.removeprefix('\ufeff').splitlines():
        line=source.strip()
        if not line or re.match(r'^(//|#|;)',line):continue
        if re.fullmatch(r'\[?(main(?: deck)?|deck|digi[- ]?eggs?(?: deck)?)\]?:?',line,re.I):continue
        m=re.fullmatch(r'(\d+)\s*[x×]?\s+(.+)',line,re.I);leading=bool(m)
        if m:count,body=int(m[1]),m[2]
        else:
            m=re.fullmatch(r'(.+?)\s+[x×]\s*(\d+)',line,re.I) or re.fullmatch(r'([A-Z][A-Z0-9]*-\d{2,3})\s+(\d+)',line,re.I)
            if not m:raise ValueError('Invalid deck row: '+source)
            body,count=m[1],int(m[2])
        ids=list(re.finditer(r'(?<![A-Z0-9_-])([A-Z][A-Z0-9]*-\d{2,3})(?![A-Z0-9_-])',body,re.I))
        tail=body[ids[0].end():].strip() if len(ids)==1 else ''
        extra=leading and (re.fullmatch(r'[\])}]*\s*(?:[x×]\s*)?\d+\s*',tail,re.I) or re.match(r'^[x×]\s*\d+\b',body,re.I))
        if count<1 or count>999 or len(ids)!=1 or extra:raise ValueError('Ambiguous deck row: '+source)
        code=ids[0][1].upper();grouped[code]=grouped.get(code,0)+count
    if not grouped:raise ValueError('No card entries found.')
    return [{'id':code,'count':count} for code,count in sorted(grouped.items())]
