const {test} = require('node:test'); const assert = require('node:assert/strict');
const fs = require('node:fs'); const path = require('node:path');
const core = require('../compare.js');
const modulePath = x => path.join(__dirname,'..','core',x+'.js');
const catalog = {'BT1-010': {name:'Agumon',type:'Digimon',deck_card:true},'BT1-001':{name:'Koromon',type:'Digi-Egg',deck_card:true},'EX2-007':{name:'Mother',type:'Digi-Egg',deck_card:true},'EX7-064':{name:'Shoto',type:'Tamer',deck_card:true}};
function legality() {assert.ok(fs.existsSync(modulePath('legality')),'legality module exists');return require(modulePath('legality'));}
test('legality keeps deck size, unknowns and excessive copies explicit',()=>{
 const legal=legality(); let result=legal.check(core.parseDeck('50 BT1-010\n6 BT1-001'),catalog,{});
 assert.equal(result.status,'INVALID'); assert.ok(result.issues.some(i=>i.code==='COPY_LIMIT'));assert.ok(result.issues.some(i=>i.code==='EGG_COUNT'));
 result=legal.check(core.parseDeck('4 XX1-099'),catalog,{});assert.ok(result.issues.some(i=>i.code==='UNKNOWN_CARD'));
});
test('official restriction and pair checks cannot be waived by printed copy exception',()=>{
 const legal=legality(); const lock={limits:{'BT1-010':1},pairs:[['EX2-007','EX7-064']],verified:true,format:'English constructed',as_of:'2026-11-02'};
 const result=legal.check(core.parseDeck('2 BT1-010\n1 EX2-007\n1 EX7-064'),catalog,lock);
 assert.ok(result.issues.some(i=>i.code==='RESTRICTED'));assert.ok(result.issues.some(i=>i.code==='BANNED_PAIR'));
});
test('well-sized decks still require format and date verification',()=>{
 const legal=legality(); const cards={};let raw='';for(let i=10;i<23;i++){const id='BT1-'+String(i).padStart(3,'0');cards[id]={type:'Digimon',deck_card:true};raw+=(i===22?2:4)+' '+id+'\n';}
 assert.equal(legal.check(core.parseDeck(raw),cards,{}).status,'UNVERIFIED');
 assert.equal(legal.check(core.parseDeck(raw),cards,{verified:true,format:'English constructed',as_of:'2026-11-02'}).status,'CHECKS_PASSED');
});
test('match identities change with seats or any frozen dependency',async()=>{
 assert.ok(fs.existsSync(modulePath('identity')),'identity module exists');const {identify}=require(modulePath('identity'));
 const a=core.parseDeck('4 BT1-010'), b=core.parseDeck('4 BT1-001');const one=await identify(a,b,{catalog:'one'});
 assert.notEqual(one,await identify(b,a,{catalog:'one'}));assert.notEqual(one,await identify(a,b,{catalog:'two'}));
 assert.equal(one,await identify(core.parseDeck('2 BT1-010\n2 BT1-010'),b,{catalog:'one'}));
});
test('arbitrary pairing reports generic bots and no sample deck identities',()=>{
 const r=core.simulationStatus(core.parseDeck('4 BT1-010'),core.parseDeck('4 BT1-001'),{catalog,samples:{A:{text:'4 XX1-010'},B:{text:'4 XX1-011'}}});
 assert.equal(r.bots[0].deck,null);assert.equal(r.bots[1].deck,null);assert.equal(r.win_rate,null);assert.equal(r.matches_played,0);
});
test('official high-copy rule and shared card-number groups are respected',()=>{
 const legal=legality();const c={'EX2-046':{type:'Digimon',deck_card:true,effect:"You can include up to 50 copies of cards with this card's card number in your deck."},'RB1-004':{type:'Digimon',deck_card:true,effect:'Card Number: Also treated as [P-009]. A deck may not have more than 4 total copies of this and [P-009].'},'P-009':{type:'Digimon',deck_card:true}};
 const lock={verified:true,format:'English constructed',as_of:'2026-11-02'};
 assert.equal(legal.check(core.parseDeck('50 EX2-046'),c,lock).status,'CHECKS_PASSED');
 assert.ok(legal.check(core.parseDeck('3 RB1-004\n3 P-009'),c,lock).issues.some(i=>i.code==='SHARED_COPY_LIMIT'));
});
test('official token records can be browsed without accepting them as deck cards',async()=>{
 require('../core/identity.js');const Catalog=require('../core/catalog.js');const raw=JSON.stringify({TOKEN:{id:'TOKEN',type:'Digimon',deck_card:false}})+'\n';const sha=await globalThis.DeckIdentity.hash(raw),original=globalThis.fetch;
 globalThis.fetch=async()=>({ok:true,text:async()=>raw});try{const c=new Catalog({chunks:{TOKEN:{path:'TOKEN.json',sha256:sha}}});await c.load('TOKEN');assert.equal(c.cards.TOKEN.deck_card,false);}finally{globalThis.fetch=original;}
});
test('catalog chunks with the wrong bytes are refused before records are exposed',async()=>{
 require('../core/identity.js');const Catalog=require('../core/catalog.js'),original=globalThis.fetch;globalThis.fetch=async()=>({ok:true,text:async()=>'{}'});
 try{const c=new Catalog({chunks:{BT1:{path:'BT1.json',sha256:'bad'}}});await assert.rejects(c.load('BT1'),/integrity/);assert.equal(Object.keys(c.cards).length,0);}finally{globalThis.fetch=original;}
});
test('match identity never depends on the browser locale collation',async()=>{
 const {identify}=require('../core/identity.js'),original=String.prototype.localeCompare;String.prototype.localeCompare=function(){throw Error('Locale collation must not be consulted for protocol identities');};
 try{assert.match(await identify({entries:[{id:'BT10-010',count:4},{id:'BT1-010',count:4}]},{entries:[{id:'EX1-001',count:4}]},{catalog:'x'}),/^[a-f0-9]{64}$/);}finally{String.prototype.localeCompare=original;}
});
