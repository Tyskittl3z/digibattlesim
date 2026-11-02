(function(root){'use strict';
const request=r=>new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
class BrowserDB{
 static async open(name='digimon-workspaces-v1'){
  const r=indexedDB.open(name,1);r.onupgradeneeded=()=>{for(const store of ['workspaces','reports'])r.result.createObjectStore(store,{keyPath:'id'});};
  const db=await new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.onblocked=()=>reject(new Error('Close other app tabs to open workspace storage.'));});
  db.onversionchange=()=>db.close();return new BrowserDB(db);
 }
 constructor(db){this.db=db;}
 async run(mode,fn){
  const tx=this.db.transaction(['workspaces','reports'],mode);
  const done=new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error||new Error('Storage transaction aborted.'));tx.onerror=()=>{};});
  const api={get:(s,k)=>request(tx.objectStore(s).get(k)),all:s=>request(tx.objectStore(s).getAll()),put:(s,v)=>request(tx.objectStore(s).put(v)),add:(s,v)=>request(tx.objectStore(s).add(v))};
  try{const result=await fn(api);await done;return result;}catch(error){try{tx.abort();}catch(_){}await done.catch(()=>{});throw error;}
 }
 close(){this.db.close();}
}
root.BrowserDB=BrowserDB;if(typeof module!=='undefined')module.exports=BrowserDB;
})(globalThis);
