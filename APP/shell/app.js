/* Static, local-only browser application. No gameplay outcomes are generated. */
(function(){'use strict';
const $=id=>document.getElementById(id),core=window.DeckCompare,identity=window.DeckIdentity;
const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=String(text);if(cls)n.className=cls;return n;};
const state={A:{text:'',filename:'',kind:'PASTE',file_sha256:null,encoding:null},B:{text:'',filename:'',kind:'PASTE',file_sha256:null,encoding:null}};
const fileVersions={A:0,B:0};let restoreVersion=0;let saving=false;let generation=0,manifest,lock,metadata,catalog,store,currentWorkspace=null,toastTimer,installEvent,dependencies,current=null,dirty=false;
window.currentReport=null;window.appReady=false;
const stages=[
 ['Verified mechanics','Every interaction available to the loaded decks needs verified mechanics and official rulings. Unknown mandatory effects must halt.'],
 ['60 reviewed full matches','At least 60 complete fact-finding matches, with equal starting-player counts and independent rules review. Scenarios do not count as full matches.'],
 ['Best / medium / worst routes','Evidence-backed GREEN, YELLOW and RED routes need evaluated legal alternatives and uncertainty. Unknown situations remain unverified.'],
 ['Freeze the exact inputs','Lock decks, rules, both pilots, roadmaps and engine hashes. Any frozen input change requires a new freeze and a full restart.'],
 ['10,000 final matches','Actually play 10,000 matches with 5,000 starts per deck. Preserve original HALT seeds and traces. No learning or inferred outcomes.']
];
const announce=message=>{$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,6500);};
const input=seat=>({...state[seat],filename:state[seat].filename||'Pasted deck '+seat});
const setActions=ready=>{const usable=ready&&state.A.text.trim()&&state.B.text.trim();$('download').disabled=!usable;$('export-request').disabled=!usable||!current?.statistics;for(const id of ['save-workspace','new-workspace'])$(id).disabled=!usable||!store||saving;};
function setSeat(seat,value){fileVersions[seat]++;state[seat]={text:value.text||'',filename:value.filename||'',kind:value.kind||'PASTE',file_sha256:value.file_sha256||null,encoding:value.encoding||null};$('text'+seat).value=state[seat].text;}
function renderFeedback(seat,deck,stats){
 $('meta'+seat).textContent=state[seat].filename||(state[seat].text?'Pasted decklist':'No file loaded');
 const node=$('feedback'+seat);node.classList.toggle('error',Boolean(deck.errors.length&&state[seat].text));
 node.textContent=!state[seat].text?'Your exact quantities stay intact.':deck.errors.length?deck.errors.map(e=>(e.line?'Line '+e.line+': ':'')+e.message).join(' '):stats.total+' cards · '+stats.distinct+' distinct · '+(stats.unknown_count?stats.unknown_count+' without card data':stats.main_count+' main + '+stats.egg_count+' eggs');
}
function bars(id,a,b,levels){const node=$(id);node.replaceChildren();const keys=[...new Set([...Object.keys(a),...Object.keys(b)])].sort((x,y)=>x.localeCompare(y,undefined,{numeric:true}));const max=Math.max(1,...Object.values(a),...Object.values(b));
 if(!keys.length){node.append(make('p','No known card details for this breakdown.','small'));return;}
 for(const key of keys){const row=make('div',null,'bar-row');row.append(make('span',levels?'Lv. '+key:key));const track=make('div',null,'bar-track');for(const [v,cls] of [[a[key]||0,'bar'],[b[key]||0,'bar b']]){const bar=make('div',null,cls);bar.style.width=(100*v/max)+'%';track.append(bar);}const values=make('div',null,'bar-values');values.append(make('span',a[key]||0,'a-text'),make('span',b[key]||0,'b-text'));row.append(track,values);node.append(row);}
}
function renderRows(){const body=$('card-rows');body.replaceChildren();if(!current?.statistics)return;const all=current.statistics.comparison.rows,query=$('search').value.trim().toLowerCase();const rows=all.filter(r=>(!query||(r.name+' '+r.id).toLowerCase().includes(query))&&(!$('differences-only').checked||r.delta!==0));
 for(const row of rows){const tr=make('tr'),card=make('td');card.append(make('strong',row.name),make('small',row.id));tr.append(card,make('td',row.type||'Data missing'),make('td',row.A,'a-text'),make('td',row.B,'b-text'),make('td',row.delta>0?'+'+row.delta:row.delta));body.append(tr);}
 $('row-count').textContent=rows.length+' of '+all.length+' cards shown. Downloads always include the complete comparison.';
}
function renderStats(report){const stats=report.statistics;$('empty-state').hidden=Boolean(stats);$('stats-content').hidden=!stats;if(!stats)return;
 $('stat-grid').replaceChildren();const stat=(label,a,b,note)=>{const n=make('div',null,'stat');n.append(make('span',label));const val=make('strong');val.append(make('span',a??'—','a-text'),make('span','/','divider'),make('span',b??'—','b-text'));n.append(val,make('p',note));$('stat-grid').append(n);};
 stat('Cards imported',stats.A.total,stats.B.total,'Includes Digi-Eggs');stat('Main-deck cards',stats.A.main_count,stats.B.main_count,'Eggs: '+(stats.A.egg_count??'?')+' / '+(stats.B.egg_count??'?'));stat('Distinct cards',stats.A.distinct,stats.B.distinct,stats.comparison.shared_distinct+' distinct in common');stat('Average play cost',stats.A.average_play_cost,stats.B.average_play_cost,'Known main cards only');
 const missing=[...new Set([...stats.A.unknown_ids,...stats.B.unknown_ids])];$('data-note').textContent=missing.length?'Missing card details: '+missing.join(', ')+'. Quantities are retained; unknown types and costs are never guessed.':'All imported codes have official catalog records. Card statistics do not certify legality or predict a winner.';
 bars('type-bars',stats.A.types,stats.B.types,false);bars('level-bars',stats.A.levels,stats.B.levels,true);renderRows();
}
function renderLegality(report){$('legality-grid').replaceChildren();for(const seat of ['A','B']){const l=report.legality[seat],panel=make('article',null,'panel');const heading=make('div',null,'legality-heading');heading.append(make('h3','Deck '+seat),make('span',l.status.replaceAll('_',' '),'legal-state'+(l.status==='CHECKS_PASSED'?' passed':'')));panel.append(heading);
 panel.append(make('p',l.main_count+' main · '+l.egg_count+' eggs · '+lock.as_of+' snapshot'));const list=make('ul',null,'issues');const messages=[...l.issues.map(i=>i.message),...l.unverified];if(!messages.length)messages.push('Count, copy-limit and pinned restriction checks passed. Event/release eligibility remains separate.');messages.forEach(s=>list.append(make('li',s)));panel.append(list);$('legality-grid').append(panel);}}
function renderEngine(report){
 const r=report.engine_readiness,d=r.diagnostic;const labels={LOADED_PAIR_BLOCKED:'Loaded pair: verification blocked',SEAT_MAPPING_REQUIRED:'Swap the decks for the current engine',UNSUPPORTED_PAIRING:'Pairing needs its own engine support',INPUT_ERRORS:'Fix the deck import errors'};
 $('engine-scope').textContent=labels[r.scope]||'Verification unavailable';
 $('engine-diagnostic').textContent=d?'Previous diagnostic cohort: '+d.attempted+' attempts · '+d.software_completed+' software completions · '+d.halts+' HALTs. '+(d.source_current?'':'Source changed; these records are stale. ')+d.reviewed_matches+' independently reviewed valid matches.':'No diagnostic records or results are assigned to these inputs.';
 $('engine-drift').replaceChildren();if(r.metadata_drift.length){const n=make('div',null,'notice error');n.append(make('strong','Official card data differs from the engine snapshot'));for(const item of r.metadata_drift)n.append(make('p',item.card+' · '+item.field+': engine '+JSON.stringify(item.engine)+'; official '+JSON.stringify(item.official)));$('engine-drift').append(n);}
 $('engine-blockers').replaceChildren();const groups=new Map();for(const blocker of r.blockers){if(!groups.has(blocker.code))groups.set(blocker.code,[]);groups.get(blocker.code).push(blocker.detail);}
 for(const [code,details] of groups){const n=make('details',null,'readiness-blocker');n.append(make('summary',code.replaceAll('_',' ').toLowerCase()+(details.length>1?' ('+details.length+')':'')));const list=make('ul',null,'issues');details.forEach(text=>list.append(make('li',text)));n.append(list);$('engine-blockers').append(n);}
}
async function refresh(){
 const version=++generation;current=null;window.currentReport=null;setActions(false);$('comparison-status').textContent='Checking the exact inputs…';
 const a=core.parseDeck(state.A.text),b=core.parseDeck(state.B.text);const snapshots={A:input('A'),B:input('B')};let loadError=null;
 try{await catalog.ensure([a,b]);}catch(error){loadError=error.message;}
 if(version!==generation)return;
 try{
  const report=await core.buildReport(snapshots.A,snapshots.B,{...metadata,catalog:catalog.cards});
  report.schema='digimon-workspace-report-v1';report.identity=await identity.identify(a,b,dependencies);report.dependencies=dependencies;
  report.legality={A:DeckLegality.check(a,catalog.cards,lock),B:DeckLegality.check(b,catalog.cards,lock)};
  report.catalog_snapshot={card_count:manifest.card_count,category_count:manifest.category_count,chunk_count:Object.keys(manifest.chunks).length,snapshot_date:manifest.snapshot_date,manifest_sha256:dependencies.catalog,errata:manifest.errata,source_files:manifest.sources.filter(s=>[...a.entries,...b.entries].some(e=>catalog.cards[e.id]?.source_category===s.category))};
  report.catalog_records=Object.fromEntries([...new Set([...a.entries,...b.entries].map(e=>e.id))].filter(id=>Object.hasOwn(catalog.cards,id)).map(id=>[id,catalog.cards[id]]));
  report.restriction_snapshot=lock;report.data_load_errors=loadError?[loadError]:[];
  const missingMechanics=[...new Set([...a.entries,...b.entries].map(c=>c.id))].sort();
  report.simulation_missing_mechanics=missingMechanics;
  report.evidence_stages=stages.map(([name,blocker],i)=>({stage:i+1,name,status:'LOCKED',blockers:[blocker]}));
  report.simulation.status=a.errors.length||b.errors.length?'INPUT_ERRORS':'MECHANICS_UNVERIFIED';report.simulation.supported_pairing=false;
  report.evidence_stages[0].blockers=missingMechanics.length?['Missing verified mechanic packs: '+missingMechanics.join(', '),'Official gameplay rules and format lock are unverified.']:['Load both exact decks before verifying mechanics.'];
  report.simulation.blockers=['Verified mechanics and independent rules review are missing for the exact loaded decks.',...stages.slice(1).map(s=>s[1])];
  report.simulation.message='No verified gameplay evidence is loaded for this pairing. Win rates are unavailable.';
  const scope=EngineBridge.scope(a,b,metadata.engine_readiness),matched=scope==='LOADED_PAIR_BLOCKED';
  report.engine_readiness={schema:metadata.engine_readiness.schema,source_snapshot_sha256:metadata.engine_readiness.source_snapshot_sha256,scope,execution_enabled:false,
   diagnostic:matched?metadata.engine_readiness.diagnostic:null,metadata_drift:matched?metadata.engine_readiness.metadata_drift:[],
   blockers:matched?metadata.engine_readiness.blockers:[{code:scope,detail:scope==='INPUT_ERRORS'?'Fix the deck import errors.':scope==='SEAT_MAPPING_REQUIRED'?'The current engine requires Jupitermon in seat A and Amaterasumon-Toho in seat B.':'This pairing needs its own verified mechanics and match evidence.'}]};
  report.simulation.status=scope;report.simulation.blockers=report.engine_readiness.blockers.map(b=>b.detail);
  report.data_provenance.official_rule_verification='UNVERIFIED';
  if(version!==generation)return;
  current=report;window.currentReport=report;
  for(const [seat,deck] of [['A',a],['B',b]])renderFeedback(seat,deck,core.summarize(deck,catalog.cards));
  renderStats(report);renderLegality(report);renderEngine(report);setActions(true);$('pairing-status').textContent=missingMechanics.length?'This pairing is locked. Missing verified mechanic packs for '+missingMechanics.length+' card codes: '+missingMechanics.join(', ')+'. No reviewed match records are loaded.':'Load both decks to identify the exact missing mechanics.';
  $('comparison-status').textContent=loadError?'Catalog unavailable: '+loadError:!state.A.text.trim()||!state.B.text.trim()?'Add two lists to begin.':report.statistics?report.statistics.comparison.shared_copies+' shared copies · comparison updated':'Fix import errors. Exact inputs can still be downloaded.';
 }catch(error){if(version===generation){$('comparison-status').textContent='Comparison unavailable: '+error.message;announce(error.message);}}
}
function changed(){restoreVersion++;dirty=true;$('storage-status').textContent=currentWorkspace?'Unsaved changes to '+currentWorkspace.name+'.':'Not saved. Download a report for a portable backup.';refresh();}
async function loadFile(seat,file){restoreVersion++;const version=++fileVersions[seat];if(file.size>1000000){announce('Use a UTF-8 decklist smaller than 1 MB.');return;}
 try{const bytes=await file.arrayBuffer(),text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes),hash=await identity.hash(bytes);if(version!==fileVersions[seat])return;state[seat]={text,filename:file.name,file_sha256:hash,encoding:'UTF-8',kind:'FILE'};$('text'+seat).value=text;changed();}catch(error){announce('File could not be read as UTF-8 text: '+error.message);}}
function files(list,seat){if(list.length===2){loadFile('A',list[0]);loadFile('B',list[1]);}else if(list.length===1&&seat)loadFile(seat,list[0]);else announce('Drop one file into a deck panel, or two files to fill both.');}
function download(report){const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const details='<h2>Construction checks and verification</h2>'+['A','B'].map(seat=>'<h3>Deck '+seat+': '+esc(report.legality[seat].status)+'</h3><ul>'+[...report.legality[seat].issues.map(i=>i.message),...report.legality[seat].unverified].map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>').join('')+'<p>'+esc(report.legality.A.notice)+'</p><h2>Locked evidence stages</h2><ol>'+report.evidence_stages.map(s=>'<li><strong>'+esc(s.name)+'</strong>: '+esc(s.blockers.join(' '))+'</li>').join('')+'</ol><p>Matchup identity: <code>'+esc(report.identity)+'</code></p>';
 const html=core.reportHtml(report).replace('<h2>Data limits</h2>',details+'<h2>Data limits</h2>'),url=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));const a=make('a');a.href=url;a.download='DigiBattle-after-report-'+report.created_at_utc.slice(0,19).replaceAll(':','-')+'.html';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
}
async function save(asNew=false){if(!current||!store||saving)return;saving=true;const captured=current,version=generation,selection=currentWorkspace,old=asNew?null:currentWorkspace;const id=old?.id||crypto.randomUUID();$('save-workspace').disabled=true;$('new-workspace').disabled=true;
 try{const workspace=await store.save({id,name:$('workspace-name').value.trim()||'Untitled matchup',expectedRevision:old?.revision||0,report:captured});
  if(currentWorkspace!==selection){announce('The previous workspace was saved. Your newly selected workspace was kept.');return;}currentWorkspace=workspace;dirty=version!==generation;$('storage-status').textContent='Saved '+workspace.name+' · revision '+workspace.revision+(dirty?' · New edits are not saved.':' · Exact inputs and report stored.');announce('Workspace saved in this browser. Download an after-report for a portable backup.');
 }catch(error){if(currentWorkspace===selection)$('storage-status').textContent='Not saved: '+error.message;announce('Workspace not saved: '+error.message);}finally{saving=false;setActions(Boolean(current));}}
async function workspaceList(){const container=$('workspace-list');container.replaceChildren();if(!store){container.append(make('p','Persistent storage is unavailable. Download an after-report to retain your inputs.'));return;}
 try{const list=await store.list();if(!list.length)container.append(make('div','No saved workspaces yet. Import two decks and save a workspace from Deck comparison.','panel'));
 for(const w of list){const card=make('article',null,'panel workspace-card'),info=make('div');info.append(make('h2',w.name),make('p',(w.archived?'Archived · ':'')+'Revision '+w.revision+' · '+new Date(w.updated_at).toLocaleString()),make('p',(w.identity||'No identity').slice(0,24)+'…','small'));const actions=make('div',null,'workspace-actions'),restore=make('button','Restore','button');restore.setAttribute('aria-label','Restore '+w.name);
 restore.addEventListener('click',async()=>{const operation=++restoreVersion,inputsAtStart=generation;try{const {workspace,report}=await store.restore(w.id);if(operation!==restoreVersion||inputsAtStart!==generation){announce('Restore canceled because newer inputs or another workspace were selected.');return;}currentWorkspace=workspace;for(const seat of ['A','B']){const saved=report.inputs[seat];setSeat(seat,{text:saved.raw_text,filename:saved.filename,kind:saved.input_kind,file_sha256:saved.original_file_sha256,encoding:saved.text_encoding});}$('workspace-name').value=workspace.name;dirty=false;const stale=identity.canonical(report.dependencies)!==identity.canonical(dependencies);$('storage-status').textContent=stale?'Restored inputs. Dependencies changed; previous evidence is stale. Recomputed comparison needs a new save.':'Restored '+workspace.name+' · revision '+workspace.revision+'.';showView('compare');await refresh();announce(stale?'Sources changed. Inputs restored; evidence remains locked.':'Exact workspace inputs restored.');}catch(error){announce(error.message);}});actions.append(restore);
 if(!w.archived){const archive=make('button','Archive','quiet');archive.setAttribute('aria-label','Archive '+w.name);archive.addEventListener('click',async()=>{try{const archived=await store.archive(w.id,w.revision);if(currentWorkspace?.id===w.id)currentWorkspace=archived;await workspaceList();}catch(error){announce(error.message);}});actions.append(archive);}card.append(info,actions);container.append(card);}
 }catch(error){container.append(make('p','Cannot read workspaces: '+error.message));}}
let browseVersion=0;
async function browse(){const version=++browseVersion,prefix=$('catalog-prefix').value;try{await catalog.load(prefix);if(version!==browseVersion)return;const query=$('catalog-query').value.toLowerCase().trim(),cards=Object.values(catalog.cards).filter(c=>c.id.split('-')[0]===prefix&&(!query||(c.id+' '+c.name+' '+c.type).toLowerCase().includes(query)));$('catalog-status').textContent=cards.length+' records · official English snapshot '+manifest.snapshot_date+' · mechanics unverified';$('catalog-results').replaceChildren();
 for(const card of cards){const n=make('article',null,'panel catalog-card');n.append(make('span',card.id,'code'),make('h2',card.name),make('p',card.type+' · '+card.colors.join(' / ')+(card.level?' · Lv. '+card.level:'')),make('p','Play cost: '+(card.play_cost??'—')+' · DP: '+(card.dp??'—')));if(!card.deck_card)n.append(make('p','Not a deck card.','legal-state'));if(card.effect){const details=make('details');details.append(make('summary','Card text'),make('p',card.effect,'effect'));n.append(details);}if(card.errata?.length){const errata=make('details');errata.append(make('summary','Official errata'));card.errata.forEach(e=>errata.append(make('p',e.heading),make('p',e.after||e.notice,'effect')));n.append(errata);}
 n.append(make('p','Simulation: unverified','small'));const link=make('a','Official source ↗');link.href='https://world.digimoncard.com/cards/?search=true&category='+encodeURIComponent(card.source_category);link.target='_blank';link.rel='noopener noreferrer';n.append(link);$('catalog-results').append(n);}
 }catch(error){$('catalog-status').textContent='Catalog unavailable: '+error.message;}}
function showView(view){if(!['compare','catalog','workspaces','evidence'].includes(view))view='compare';document.querySelectorAll('.view').forEach(n=>n.hidden=n.id!=='view-'+view);document.querySelectorAll('[data-view]').forEach(n=>{const active=n.dataset.view===view;n.classList.toggle('active',active);if(active)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});history.replaceState(null,'','#'+view);if(view==='workspaces')workspaceList();if(view==='catalog')browse();}
async function offline(){if(window.__portableData){$('offline-status').textContent='Portable · offline';return;}if(!('serviceWorker'in navigator)){ $('offline-status').textContent='Offline install unavailable';return;}
 try{const registration=await navigator.serviceWorker.register('./service-worker.js');
  await new Promise((resolve,reject)=>{const watched=new WeakSet();
   const watch=worker=>{if(!worker||watched.has(worker))return;watched.add(worker);
    const inspect=()=>{if(worker.state==='redundant'){if(registration.active){announce('The offline update failed. The previous cached version is still available.');resolve();}else reject(new Error('Offline assets could not be verified or cached. Reload while online to retry.'));}
     if(worker.state==='installed'&&navigator.serviceWorker.controller)announce('An app update is ready. Save your workspace, then close all app tabs and reopen.');
     if(worker.state==='activated')resolve();};
    worker.addEventListener('statechange',inspect);inspect();};
   registration.addEventListener('updatefound',()=>watch(registration.installing));
   watch(registration.installing);watch(registration.waiting);
   if(registration.active?.state==='activated')resolve();else if(registration.active)watch(registration.active);
   else if(!registration.installing&&!registration.waiting)reject(new Error('Offline installation did not complete. Reload while online to retry.'));
  });$('offline-status').textContent='Ready offline';
 }catch(error){$('offline-status').textContent='Offline access unavailable';announce('Offline cache could not be prepared: '+error.message);}}

async function start(){
 try{const urls=['./catalog/manifest.json','./catalog/restrictions.json','./app-data.json'];const raws=window.__portableData?window.__portableData.raws:await Promise.all(urls.map(async url=>{const r=await fetch(url);if(!r.ok)throw new Error('Required app data unavailable: '+url);return r.text();}));
 [manifest,lock,metadata]=raws.map(JSON.parse);catalog=new OfficialCatalog(manifest);dependencies={catalog:await identity.hash(raws[0]),restrictions:await identity.hash(raws[1]),app:metadata.source_files,mechanics:'UNVERIFIED',rules:'UNVERIFIED',pilots:'UNVERIFIED',roadmaps:'UNVERIFIED',engine_readiness:await identity.hash(identity.canonical(metadata.engine_readiness))};
 $('catalog-count').textContent=manifest.card_count.toLocaleString()+' cards';$('snapshot-date').textContent=manifest.category_count+' categories · '+manifest.snapshot_date;$('legality-note').textContent='English constructed · restrictions effective '+lock.effective_date+' · snapshot '+lock.as_of+'. Event and release eligibility require separate verification.';
 try{store=new WorkspaceStorage.Workspaces(await BrowserDB.open());}catch(error){$('storage-status').textContent='Persistent storage unavailable: '+error.message;}
 for(const prefix of Object.keys(manifest.chunks).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}))){const o=make('option',prefix);o.value=prefix;$('catalog-prefix').append(o);}$('catalog-prefix').value='BT1';
 stages.forEach(([name,blocker],i)=>{const n=make('article',null,'stage'),text=make('div');text.append(make('h2',name),make('p',blocker));n.append(make('span',String(i+1).padStart(2,'0'),'stage-number'),text,make('span','LOCKED','tag'));$('evidence-stages').append(n);});
 for(const seat of ['A','B']){
  $('text'+seat).addEventListener('input',()=>{fileVersions[seat]++;state[seat]={text:$('text'+seat).value,filename:'',kind:'PASTE',file_sha256:null,encoding:null};changed();});
  $('clear'+seat).addEventListener('click',()=>{setSeat(seat,{});changed();});$('file'+seat).addEventListener('change',e=>{files([...e.target.files],seat);e.target.value='';});
  const zone=document.querySelector('.drop-target[data-seat='+seat+']');zone.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('file'+seat).click();}});zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('dragging');});zone.addEventListener('dragleave',()=>zone.classList.remove('dragging'));zone.addEventListener('drop',e=>{e.preventDefault();e.stopPropagation();zone.classList.remove('dragging');files([...e.dataTransfer.files],seat);});
 }
 document.addEventListener('dragover',e=>e.preventDefault());document.addEventListener('drop',e=>{e.preventDefault();files([...e.dataTransfer.files]);});
 $('examples').addEventListener('click',()=>{for(const seat of ['A','B'])setSeat(seat,{text:metadata.samples[seat].text,filename:metadata.samples[seat].name+'.txt',kind:'EXAMPLE'});changed();});
 $('swap').addEventListener('click',()=>{const a=input('A'),b=input('B');setSeat('A',b);setSeat('B',a);changed();});
 $('search').addEventListener('input',renderRows);$('differences-only').addEventListener('change',renderRows);$('download').addEventListener('click',()=>{if(current)download(structuredClone(current));});
 $('export-request').addEventListener('click',async()=>{if(!current?.statistics)return;const captured=structuredClone(current);try{const request=await EngineBridge.prepare(captured),url=URL.createObjectURL(new Blob([JSON.stringify(request,null,2)+'\n'],{type:'application/json'})),link=make('a');link.href=url;link.download='DigiBattle-'+request.request_id.slice(0,12)+'.battle-request.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);announce('Preparation request exported. No battle was started.');}catch(error){announce('Request could not be exported: '+error.message);}});
 $('save-workspace').addEventListener('click',()=>save(false));$('new-workspace').addEventListener('click',()=>save(true));$('workspace-name').addEventListener('input',()=>{restoreVersion++;dirty=true;});
 document.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>{restoreVersion++;showView(n.dataset.view);}));
 document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();showView('compare');});
 $('catalog-prefix').addEventListener('change',browse);$('catalog-query').addEventListener('input',browse);
 window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installEvent=e;$('install').hidden=false;});$('install').addEventListener('click',async()=>{if(installEvent){await installEvent.prompt();installEvent=null;$('install').hidden=true;}});
 showView(location.hash.slice(1)||'compare');await refresh();window.appReady=true;offline();
 }catch(error){$('fatal').textContent='The app could not start: '+error.message+'. Open it through the included local launcher, or use the single-file fallback.';$('fatal').hidden=false;$('offline-status').textContent='Not ready';}
}
start();
})();
