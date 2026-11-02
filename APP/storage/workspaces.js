(function(root){'use strict';
const clone=v=>v===undefined?undefined:structuredClone(v);
class MemoryDB{
 constructor(){this.data={workspaces:new Map(),reports:new Map()};this.queue=Promise.resolve();this.refuse=false;}
 run(mode,fn){const task=this.queue.then(async()=>{
  const data={workspaces:new Map(this.data.workspaces),reports:new Map(this.data.reports)};
  const api={get:async(s,k)=>clone(data[s].get(k)),all:async s=>[...data[s].values()].map(clone),put:async(s,v)=>data[s].set(v.id,clone(v)),add:async(s,v)=>{if(data[s].has(v.id))throw new Error('Immutable record collision');data[s].set(v.id,clone(v));}};
  const result=await fn(api);if(mode==='readwrite'){if(this.refuse)throw new Error('QuotaExceededError: storage refused');this.data=data;}return result;
 });this.queue=task.catch(()=>{});return task;}
}
class Workspaces{
 constructor(db){this.db=db;}
 async save({id,name,expectedRevision,report}){
  const body=root.DeckIdentity.canonical(report),recordId=await root.DeckIdentity.hash(body);
  return this.db.run('readwrite',async tx=>{
   const previous=await tx.get('workspaces',id);
   if((previous?.revision||0)!==expectedRevision)throw new Error('Workspace changed in another tab. Restore its latest revision or save a new workspace.');
   const record=await tx.get('reports',recordId);
   if(record&&record.body!==body)throw new Error('Immutable report collision.');
   if(!record)await tx.add('reports',{id:recordId,body});
   const workspace={id,name:name||'Untitled matchup',revision:expectedRevision+1,record_id:recordId,identity:report.identity,
    archived:false,updated_at:new Date().toISOString()};
   await tx.put('workspaces',workspace);return workspace;
  });
 }
 async list(){return (await this.db.run('readonly',tx=>tx.all('workspaces'))).sort((a,b)=>b.updated_at.localeCompare(a.updated_at));}
 async restore(id){
  const loaded=await this.db.run('readonly',async tx=>{const workspace=await tx.get('workspaces',id);if(!workspace)throw new Error('Workspace not found.');const record=await tx.get('reports',workspace.record_id);if(!record)throw new Error('Saved report is missing.');return {workspace,record};});
  if(await root.DeckIdentity.hash(loaded.record.body)!==loaded.record.id)throw new Error('Saved report integrity check failed.');
  return {workspace:loaded.workspace,report:JSON.parse(loaded.record.body)};
 }
 archive(id,expectedRevision){return this.db.run('readwrite',async tx=>{const w=await tx.get('workspaces',id);if(!w||w.revision!==expectedRevision)throw new Error('Workspace changed. Restore before archiving.');w.archived=true;w.revision++;w.updated_at=new Date().toISOString();await tx.put('workspaces',w);return w;});}
}
const api={MemoryDB,Workspaces};root.WorkspaceStorage=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
