(function(root){'use strict';
function canonical(value){if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';return JSON.stringify(value);}
async function hash(value){if(!root.crypto?.subtle)throw new Error('SHA-256 requires localhost or HTTPS.');const bytes=typeof value==='string'?new TextEncoder().encode(value):value;return [...new Uint8Array(await root.crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');}
async function identify(a,b,dependencies){const compose=d=>d.entries.map(c=>[c.id,c.count]).sort((x,y)=>x[0]<y[0]?-1:x[0]>y[0]?1:0);return hash(canonical({schema:'seated-matchup-v1',A:compose(a),B:compose(b),dependencies}));}
const api={canonical,hash,identify};root.DeckIdentity=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
