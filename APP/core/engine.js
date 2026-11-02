(function(root){'use strict';
async function prepare(report){
 if(!report?.statistics||!report.inputs||report.inputs.A.errors.length||report.inputs.B.errors.length)throw new Error('Fix deck import errors before preparing a simulation request.');
 if(!report.engine_readiness||!report.dependencies?.engine_readiness)throw new Error('Current engine readiness is missing. Reopen the latest app.');
 const inputs={};for(const seat of ['A','B']){const v=report.inputs[seat];if(!v.raw_sha256||!v.composition_sha256)throw new Error('Exact input hashes are required.');inputs[seat]={raw_text:v.raw_text,raw_sha256:v.raw_sha256,composition_sha256:v.composition_sha256,filename:v.filename,original_file_sha256:v.original_file_sha256,input_kind:v.input_kind,entries:v.entries.map(({id,count})=>({id,count}))};}
 const payload={protocol_version:1,operation:'PREPARE_MATCHUP',execution_requested:false,matchup_identity:report.identity,inputs,dependencies:report.dependencies,
  engine_snapshot_sha256:report.engine_readiness.source_snapshot_sha256,catalog_sha256:report.dependencies.catalog,restrictions_sha256:report.dependencies.restrictions};
 return {schema:'digibattle-engine-request-v1',request_id:await root.DeckIdentity.hash(root.DeckIdentity.canonical(payload)),payload};
}
function scope(a,b,ready){const composition=d=>d.entries.map(c=>[c.id,c.count]).sort((x,y)=>x[0]<y[0]?-1:x[0]>y[0]?1:0);const key=d=>JSON.stringify(composition(d));
 if(a.errors.length||b.errors.length)return 'INPUT_ERRORS';const left=JSON.stringify(ready.supported_decks.A.composition),right=JSON.stringify(ready.supported_decks.B.composition);
 if(key(a)===left&&key(b)===right)return 'LOADED_PAIR_BLOCKED';if(key(a)===right&&key(b)===left)return 'SEAT_MAPPING_REQUIRED';return 'UNSUPPORTED_PAIRING';}
root.EngineBridge={prepare,scope};if(typeof module!=='undefined')module.exports=root.EngineBridge;
})(globalThis);
