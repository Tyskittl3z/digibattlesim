"""Audit source identity and unresolved pins for one matchup rules snapshot."""
from datetime import date
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from matchup_readiness import load_context_file


CONTEXT='ARTIFACTS/ulforce-bootstrap-2026-11-02/context.json'


def inspect_lock(lock,root):
    root=Path(root).resolve()
    blockers=[]
    bad_hashes=[]
    ids=set()
    context=load_context_file(root/CONTEXT)
    expected={card.number for card in context.cards
              if any(card.number==n for seat in ('A','B')
                     for n,_ in context.deck(seat).main+context.deck(seat).eggs)}
    expected_sources={card.number:card.to_dict()['official_source'] for card in context.cards
                      if card.number in expected}
    card_pages=set()
    if (lock.get('schema')!='matchup-rules-lock-v1'
            or lock.get('ordered_decks')!=['123129','122110']
            or lock.get('format')!={'name':'English version worldwide','region':'worldwide'}
            or lock.get('language')!='English'):
        blockers.append('LOCK_IDENTITY_INVALID')
    try:as_of=date.fromisoformat(lock['as_of_date'])
    except (KeyError,TypeError,ValueError):
        as_of=None;blockers.append('AS_OF_DATE_INVALID')
    for doc in lock.get('documents',[]):
        doc_id=doc.get('id')
        if not isinstance(doc_id,str) or doc_id in ids:
            blockers.append('DOCUMENT_ID_INVALID')
        ids.add(doc_id)
        if doc_id and doc_id.startswith('card-'):
            number=doc_id[5:]
            card_pages.add(number)
            source=expected_sources.get(number)
            if (source is None or doc.get('local_file')!=source['file']
                    or doc.get('official_url')!=source['url']
                    or doc.get('sha256')!=source['sha256']
                    or set(doc.get('kind',[]))!={'CARD_TEXT','CARD_QA'}):
                blockers.append('DOCUMENT_CARD_SOURCE_MISMATCH')
        url=urlparse(doc.get('official_url',''))
        if (url.scheme!='https' or url.hostname not in
                ('digimoncard.com','world.digimoncard.com')):
            blockers.append('OFFICIAL_URL_INVALID')
        path=(root/doc.get('local_file','')).resolve()
        if not path.is_relative_to(root/'RULES') or not path.is_file():
            bad_hashes.append(doc_id)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=doc.get('sha256'):
            bad_hashes.append(doc_id)
        if not doc.get('edition') or not doc.get('citation'):
            blockers.append('EDITION_OR_CITATION_MISSING')
        try:effective=date.fromisoformat(doc['effective_date'])
        except (KeyError,TypeError,ValueError):
            blockers.append('EFFECTIVE_DATE_MISSING')
        else:
            if as_of and effective>as_of:blockers.append('EFFECTIVE_AFTER_AS_OF')
    if card_pages!=expected or not {'rules','restrictions','errata'}<=ids:
        blockers.append('REQUIRED_DOCUMENTS_MISSING')
    if bad_hashes:blockers.append('SOURCE_HASH_MISMATCH')
    if not isinstance(lock.get('review'),dict) or lock['review'].get('verdict')!='VERIFIED':
        blockers.append('SEPARATE_REVIEW_MISSING')
    blockers=sorted(set(blockers))
    return {'status':'VERIFIED' if not blockers and lock.get('status')=='VERIFIED' else 'UNVERIFIED',
            'matched_card_pages':len(card_pages&expected),'bad_hashes':bad_hashes,
            'blockers':blockers}
