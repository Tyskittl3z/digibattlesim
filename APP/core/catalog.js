(function(root){'use strict';
class Catalog {
 constructor(manifest,base='./catalog/'){this.manifest=manifest;this.base=base;this.cards=Object.create(null);this.pending=new Map();}
 async load(prefix){
  if(this.pending.has(prefix))return this.pending.get(prefix);
  const info=this.manifest.chunks[prefix];if(!info)return;
  const promise=(async()=>{let raw;if(root.__portableData){raw=root.__portableData.chunks[prefix];if(typeof raw!=='string')throw new Error('Embedded catalog chunk unavailable: '+prefix);}else{const response=await fetch(this.base+info.path);if(!response.ok)throw new Error('Catalog chunk unavailable: '+prefix);raw=await response.text();}
   if(await root.DeckIdentity.hash(raw)!==info.sha256)throw new Error('Catalog integrity check failed: '+prefix);
   const cards=JSON.parse(raw);for(const [id,card] of Object.entries(cards)){if(!id.startsWith(prefix+'-')||card.id!==id)throw new Error('Invalid catalog record '+id);}Object.assign(this.cards,cards);return cards;
  })();this.pending.set(prefix,promise);try{return await promise;}catch(error){this.pending.delete(prefix);throw error;}
 }
 async ensure(decks){const prefixes=new Set(decks.flatMap(d=>d.entries.map(e=>e.id.split('-')[0])));await Promise.all([...prefixes].map(p=>this.load(p)));return this.cards;}
}
root.OfficialCatalog=Catalog;if(typeof module!=='undefined')module.exports=Catalog;
})(globalThis);
