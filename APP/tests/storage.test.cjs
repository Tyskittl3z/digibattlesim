const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
function storage(){assert.ok(fs.existsSync(__dirname+'/../storage/workspaces.js'),'workspace storage exists');require('../core/identity.js');return require('../storage/workspaces.js');}
test('immutable records, reload, revision conflict and archive are atomic',async()=>{
 const {Workspaces,MemoryDB}=storage();const db=new MemoryDB(),s=new Workspaces(db);const r={inputs:{A:{raw_text:'\ufeff4 BT1-010\r\n'},B:{raw_text:'4 BT1-001'}},identity:'pair1'};
 const one=await s.save({id:'one',name:'First',expectedRevision:0,report:r});assert.equal(one.revision,1);
 const reload=await new Workspaces(db).restore('one');assert.deepEqual(reload.report,r);
 await assert.rejects(s.save({id:'one',name:'stale',expectedRevision:0,report:{...r,identity:'pair2'}}),/changed/);
 assert.equal((await s.list())[0].name,'First');assert.equal(db.data.reports.size,1);
 await s.archive('one',1);assert.equal((await s.list())[0].archived,true);
});
test('refused storage leaves record and workspace unchanged',async()=>{
 const {Workspaces,MemoryDB}=storage();const db=new MemoryDB(),s=new Workspaces(db);
 await s.save({id:'one',name:'First',expectedRevision:0,report:{identity:'a'}});db.refuse=true;
 await assert.rejects(s.save({id:'one',name:'Second',expectedRevision:1,report:{identity:'b'}}),/Quota/);
 db.refuse=false;assert.equal((await s.restore('one')).report.identity,'a');assert.equal(db.data.reports.size,1);
});
test('concurrent saves have one winner and never overwrite stale data',async()=>{
 const {Workspaces,MemoryDB}=storage();const db=new MemoryDB(),s=new Workspaces(db);
 const results=await Promise.allSettled([s.save({id:'x',expectedRevision:0,name:'A',report:{identity:'a'}}),s.save({id:'x',expectedRevision:0,name:'B',report:{identity:'b'}})]);
 assert.equal(results.filter(x=>x.status==='fulfilled').length,1);assert.equal(db.data.reports.size,1);
});
