"""Parse official English card pages without executing markup or guessing fields."""
from html.parser import HTMLParser
import re

class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return re.sub(r'\s+', ' ', ' '.join(c.text() if isinstance(c, Node) else c for c in self.children)).strip()
    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, Node): yield from c.walk()
    def has(self, name): return name in self.attrs.get('class', '').split()

class Tree(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.root = Node(); self.stack = [self.root]; self.feed(raw)
    def handle_starttag(self, tag, attrs):
        n=Node(tag, attrs); self.stack[-1].children.append(n)
        if tag not in self.VOID: self.stack.append(n)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]; break
    def handle_data(self, data): self.stack[-1].children.append(data)

def categories(raw):
    result={}
    for n in Tree(raw).root.walk():
        if n.tag=='select' and n.attrs.get('name')=='category':
            for o in n.walk():
                if o.tag=='option' and o.attrs.get('value'): result[o.attrs['value']]=o.text()
    return result

def parse_cards(raw):
    result=[]
    for n in Tree(raw).root.walk():
        if not n.has('popupCol'): continue
        def cls(c): return next((x.text() for x in n.walk() if x.has(c)), '')
        card_id=cls('cardNo')
        if not card_id or n.attrs.get('id') != card_id: continue  # only base art
        fields={}
        for dl in n.walk():
            if dl.tag!='dl': continue
            dt=next((c for c in dl.children if isinstance(c,Node) and c.tag=='dt'), None)
            dd=next((c for c in dl.children if isinstance(c,Node) and c.tag=='dd'), None)
            if dt and dd: fields[dt.text()]=dd.text()
        def number(s):
            m=re.fullmatch(r'(?:Lv\.)?(\d+)',s or '')
            return int(m[1]) if m else None
        typ=cls('cardType')
        if typ.lower()=='digi-egg': typ='Digi-Egg'
        effects={k:v for k,v in fields.items() if k not in {'Notes','Color','Play Cost','Use Cost','DP','Form','Attribute','Type'} and ('Effect' in k or 'Text' in k)}
        result.append({'id':card_id,'name':cls('cardTitle'),'type':typ,'level':number(cls('cardLv')),
            'colors':fields.get('Color','').split(), 'play_cost':number(fields.get('Cost',fields.get('Play Cost',fields.get('Use Cost','')))),
            'special_conditions':{k:v for k,v in fields.items() if 'Condition' in k or 'Digivolve Cost' in k},
            'printed_cost':fields.get('Cost',fields.get('Play Cost',fields.get('Use Cost'))),
            'dp':number(fields.get('DP','')), 'form':fields.get('Form'), 'attribute':fields.get('Attribute'),
            'traits':fields.get('Type'), 'effect':'\n'.join(effects.values()), 'effects':effects,
            'deck_card':typ in {'Digimon','Digi-Egg','Tamer','Option','Digimon/Option','Digimon/Tamer'}, 'simulation_support':'UNVERIFIED'})
    return result

def has_card_markup(raw):
    return any(n.has('popupCol') for n in Tree(raw).root.walk())

def parse_errata(raw):
    result={}
    for section in Tree(raw).root.walk():
        if section.tag!='section':continue
        header=next((n for n in section.children if isinstance(n,Node) and n.tag=='h4'),None)
        if not header:continue
        ids=list(dict.fromkeys(re.findall(r'\b(?:BT|EX|ST|LM|P)\d*-\d{2,3}\b',header.text())))
        if not ids:continue
        after=[n.text().removeprefix('After').strip() for n in section.walk() if n.has('afterCol')]
        before=[n.text().removeprefix('Before').strip() for n in section.walk() if n.has('beforeCol')]
        for card_id in ids:
            result.setdefault(card_id,[]).append({'heading':header.text(),'before':'\n'.join(before),'after':'\n'.join(after),'notice':'Official correction; apply in addition to catalog text. Image-only changes may have no text.'})
    return result

def parse_restrictions(raw):
    marker='List of Currently Affected Cards'
    if marker not in raw: raise ValueError('Missing current restriction section')
    raw=raw[raw.rfind(marker):]
    limits={};pairs=[];mode=''
    for n in Tree(raw).root.walk():
        if n.tag=='h5':mode=n.text()
        if n.has('noticeFrame'):
            codes=list(dict.fromkeys(re.findall(r'\b(?:BT|EX|ST|LM|P)\d*-\d{2,3}\b',n.text())))
            if len(codes)<2:raise ValueError('Incomplete banned-pair record')
            pairs.extend([[codes[0],other] for other in codes[1:]])
        if n.has('num'):
            card=n.text()
            if not re.fullmatch(r'(?:BT|EX|ST|LM|P)\d*-\d{2,3}',card):raise ValueError('Invalid restricted code '+card)
            if mode.startswith('Banned cards'):limits[card]=0
            elif mode.startswith('Restricted Cards'):limits[card]=1
            else:raise ValueError('Restricted code outside recognized heading')
    if not limits:raise ValueError('No current restrictions parsed')
    return {'limits':limits,'pairs':pairs}
