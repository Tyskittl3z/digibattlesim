(function(root){'use strict';
function check(deck,catalog,lock={}) {
 const issues=[],unverified=[];let main=0,eggs=0;const counts=new Map(deck.entries.map(c=>[c.id,c.count]));
 const issue=(code,message,id=null)=>issues.push({code,message,id});
 if(deck.errors.length)issue('INPUT_ERRORS','Fix all invalid decklist rows before legality can be checked.');
 for(const entry of deck.entries){
  const card=Object.hasOwn(catalog,entry.id)?catalog[entry.id]:null;
  if(!card){issue('UNKNOWN_CARD','No official catalog record for '+entry.id,entry.id);continue;}
  if(card.deck_card===false){issue('NON_DECK_CARD',entry.id+' is not a playable deck card.',entry.id);continue;}
  if(card.type==='Digi-Egg')eggs+=entry.count;else main+=entry.count;
  const extra=card.effect?.match(/(?:can|may) include (up to (\d+)|any number of) copies of (?:this card|cards with this card's card number) in your deck/i);
  const printed=extra?(extra[2]?Number(extra[2]):Infinity):4;
  const restricted=lock.limits?.[entry.id];const limit=restricted===undefined?printed:Math.min(printed,restricted);
  if(entry.count>limit)issue(restricted!==undefined?'RESTRICTED':'COPY_LIMIT',entry.id+': '+entry.count+' copies; maximum '+limit+'.',entry.id);
  const alias=card.effect?.match(/Card Number: Also treated as \[([A-Z0-9]+-\d{2,3})\]/i);
  if(alias){const total=entry.count+(counts.get(alias[1])||0),sharedLimit=Math.min(4,lock.limits?.[alias[1]]??4,lock.limits?.[entry.id]??4);if(total>sharedLimit)issue('SHARED_COPY_LIMIT',entry.id+' and '+alias[1]+': '+total+' total copies; shared maximum '+sharedLimit+'.',entry.id);}
  if(card.source_conflict)unverified.push(entry.id+': official reprint records differ; text requires review.');
 }
 if(main!==50)issue('MAIN_COUNT','Main deck must contain exactly 50 known playable cards; found '+main+'.');
 if(eggs>5)issue('EGG_COUNT','Digi-Egg deck may contain at most 5 cards; found '+eggs+'.');
 for(const [a,b] of lock.pairs||[])if(counts.has(a)&&counts.has(b))issue('BANNED_PAIR',a+' and '+b+' cannot be included together.');
 if(!lock.verified||!lock.format||!lock.as_of)unverified.push('Format/date and official restriction snapshot have not been pinned.');
 return {status:issues.length?'INVALID':unverified.length?'UNVERIFIED':'CHECKS_PASSED',main_count:main,egg_count:eggs,issues,unverified,format:lock.format||null,as_of:lock.as_of||null,
  notice:'Construction checks are not judge certification. Release eligibility and event-specific rules require separate verification.'};
}
const api={check};root.DeckLegality=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
