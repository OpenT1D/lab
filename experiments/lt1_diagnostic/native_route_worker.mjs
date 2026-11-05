/** Fixed owned-buffer consumer: never reacquires packet bytes by pathname. */
import fs from 'node:fs';
import {hostname} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {register} from 'node:module';
import {spawn} from 'node:child_process';
import {verifyIntegration,readerSourcePaths,INTEGRATION_FILES} from './integration_gate.mjs';
import {inventory,executableWithin,loadConstructors,WORKER_FILES} from './native_loader.mjs';
import {AttemptJournal,runJournaled} from './attempt_journal.mjs';
import {assembleDirect} from './direct.mjs';
import {assembleWrapped} from './wrapped.mjs';
import {digest,decoded,need,ROOT,PACKET,registry,admit,validate,checkSources,same} from './native_route_contract.mjs';
function sources(names){return Object.fromEntries(names.map(n=>[n,digest(fs.readFileSync(new URL(n,import.meta.url)))]));}
function blocked(){for(;;)Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,1000);}
function context(state,invented){
 const {packet,entry}=state,e=JSON.parse(packet['grant.json']),i=JSON.parse(packet['integration-grant.json']);
 const engine={node:invented?e.node:process.version,platform:invented?e.platform:process.platform,arch:invented?e.arch:process.arch,host:invented?e.host:hostname(),staging_root:entry.roots.staging,
  executable_sha256:invented?e.files['runtime/bin/node']:executableWithin(entry.roots.staging,process.execPath),
  files:invented?e.files:inventory(entry.roots.staging),worker_files:sources(WORKER_FILES)};
 for(const n of ['plan','setup_receipt','host_receipt','rights_receipt','security_receipt'])engine[n]=packet[n+'.json'];
 const reader_files=Object.fromEntries(readerSourcePaths(i.reader_identity).map(n=>{const p=resolve(ROOT,n);need(fs.realpathSync(p)===p,'canonical reader source');return [n,digest(fs.readFileSync(p))];}));
 return {engine,output_root:entry.roots.output,owner_pid:process.ppid,reader_files,host_receipt:packet['integration_host_receipt.json'],implementation:sources(INTEGRATION_FILES)};
}
async function run(state,invented){
 // Snapshot even the trusted entry's packet so no async import can replace it.
 const packet=Object.fromEntries(PACKET.map(n=>[n,Buffer.from(state.packet[n])]));state={...state,packet};
 const {entry}=state;need(entry.kind===(invented?'invented':'native-unadmitted'),'fixed worker origin');
 const admitted=verifyIntegration(packet['integration-grant.json'],packet['grant.json'],state.authority,context(state,invented));
 const slot=entry.slot,definition=JSON.parse(fs.readFileSync(new URL('./native_route_cases.json',import.meta.url)));
 need(definition.schema==='opent1d.lt1-native-route-cases/2','fixed case contract');const valid=definition.slots;
 need(Object.hasOwn(valid,entry.case_id)&&valid[entry.case_id].includes(slot),'fixed qualification slot');
 const reference=JSON.parse(fs.readFileSync(new URL('./plan.json',import.meta.url)));reference.basal_u_h=admitted.plan.basal_u_h;
 if(entry.case_id==='C15')Object.assign(reference,{meals:[],announcements:[],release_rules:[]});
 if(entry.case_id==='C16'&&!slot.includes('fractional')){
  Object.assign(reference.meals[0],{start_ms:900000,duration_ms:900000,grams:slot.includes('future80')?80:40});
  Object.assign(reference.announcements[0],{start_ms:900000,available_ms:900000});if(slot.includes('unfiltered'))reference.release_rules=[];
 }
 if(entry.case_id!=='attempt')need(same(reference,admitted.plan),'fixed case scientific plan');
 if(['C15','C16'].includes(entry.case_id))need(slot.startsWith(admitted.mode+'-'),'fixed case mode');
 let modules=null,loadError=null,basal=null,constructionCount=0,child=null,patientResets=0,nonfiniteProbe=false;
 const count=entry.case_id==='C15'?2:1,results=[];let built=null;
 for(let ordinal=0;ordinal<count;ordinal++){
  const name='session-'+String(ordinal).padStart(4,'0'),folder=join(entry.roots.output,name);fs.mkdirSync(folder,{mode:0o700});
  const journal=new AttemptJournal(folder,{kind:invented?'invented':'native-unadmitted',mode:admitted.mode,identity:admitted.reader_identity,
   attempt:admitted.attempt,output_root:folder,owner_pid:process.ppid,engine_grant_sha256:digest(packet['grant.json']),integration_sha256:digest(packet['integration-grant.json'])});
  let session;
  try{
   if(entry.case_id==='C18'&&ordinal===0){
    child=spawn(process.execPath,[fileURLToPath(new URL('./native_route_descendant.mjs',import.meta.url)),entry.roots.output],{stdio:'ignore',env:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'}});
    fs.writeFileSync(join(entry.roots.output,'descendant-root.json'),JSON.stringify({pid:child.pid,ppid:process.pid}),{flag:'wx',mode:0o600});
    const until=performance.now()+3000;while(!fs.existsSync(join(entry.roots.output,'grandchild.json'))){need(performance.now()<until,'C18 descendant initialization deadline');await new Promise(r=>setTimeout(r,10));}
   }
   if(slot==='before-init-block')blocked();
   if(ordinal===0){
    try{
  if(slot==='loader-error')throw Error('Fixed qualification loader failure');
  if(invented){const fixed=await import('../../tests/lt1_native_route_models.mjs');modules=fixed.routeFixtureModules(admitted.plan);}
  else{
   process.env.TS_NODE_PROJECT=join(entry.roots.staging,'toolchain/tsconfig.json');process.env.TS_NODE_CWD=join(entry.roots.staging,'toolchain');
   register(pathToFileURL(join(entry.roots.staging,'toolchain/node_modules/ts-node/esm.mjs')),pathToFileURL(join(entry.roots.staging,'toolchain/')));
   modules=await loadConstructors(entry.roots.staging);
  }
 }catch(error){loadError=String(error);}
   }
   if(loadError)throw Error(loadError);
   checkSources(entry.entry_sources,state.expected,state.authorityHash);need(process.ppid===entry.owner_pid&&!state.signal?.aborted,'owner/cancellation before construction');
   if(ordinal===0&&modules){
    const Native=modules.Cambridge;modules={...modules,Cambridge:class extends Native{computeIIR(...args){const value=super.computeIIR(...args);basal={value:Number.isFinite(value)?value:null,finite:Number.isFinite(value),unit:'U/h',source:invented?'fixed invented Cambridge fixture computeIIR':'unchanged Cambridge.computeIIR at frozen GPEQ/START',source_revision:invented?null:'9a6092065bd821f88691cd8d03b0550acd665573',calls:(basal?.calls??0)+1};return value;}reset(...args){patientResets+=1;return super.reset(...args);}}};
   }
   if(!built){
    constructionCount+=1;built=(admitted.mode==='direct'?assembleDirect:assembleWrapped)(modules,admitted.plan);
    if(slot==='invalid-init'){
     const fields=['Q1','Q2','S1','S2','I','x1','x2','x3','D1','D2'];
     need(typeof built.patient.computeSteadyState==='function'&&typeof built.patient.setInitialState==='function','pinned native initialization API');const baseline=built.patient.computeSteadyState({iir:admitted.plan.basal_u_h},new Date('2024-07-20T00:00:00Z'));
     need(same(Object.keys(baseline).sort(),[...fields].sort())&&Object.values(baseline).every(Number.isFinite),'finite steady-state probe baseline');
     built.patient.setInitialState({...baseline,Q1:NaN});nonfiniteProbe=true;
    }
    if(slot==='diagnostic-error'){const original=built.run;built.run=()=>original(()=>{throw Error('Fixed qualification diagnostic export failure');});}
    if(slot==='terminal-tail'){const original=built.sim.setCallback;built.sim.setCallback=function(callback){return original.call(this,raw=>callback(+raw.t===Date.parse('2024-07-20T00:00:00Z')+1800000?{...raw,u:{...raw.u,iir:NaN}}:raw));};}
   }
   session=runJournaled(built,journal,{ownerCheck:()=>{if(process.ppid!==entry.owner_pid)throw Error('Supervisor disappeared');},afterRow:n=>{
    if(['after-two','diagnostic-error'].includes(slot)&&n===3)throw Error('Fixed qualification failure after two intervals');
    if(slot==='blocked'&&n===3)blocked();}});

  }catch(error){const prior=built?.sessions.at(-1);session={status:'failed',primary_error:prior?.primary_error??String(error),diagnostic_error:prior?.diagnostic_error??null,rows:prior?.rows??[],diagnostic_tail:prior?.diagnostic_tail??[]};}
  try{journal.finish(session);}finally{journal.close();}
  if(slot==='corrupt-output')fs.appendFileSync(join(folder,'events.jsonl'),'invented-corrupt-tail');
  if(slot==='after-finish-block')blocked();
  results.push({name,status:session.status,rows:session.rows.length,journal_sha256:digest(fs.readFileSync(join(folder,'events.jsonl')))});
 }
 if(child&&slot==='complete'){fs.writeFileSync(join(entry.roots.output,'descendant-stop'),'fixed stop',{flag:'wx',mode:0o600});const until=performance.now()+3000;while(child.exitCode===null&&child.signalCode===null){need(performance.now()<until,'C18 child cooperative stop deadline');await new Promise(r=>setTimeout(r,10));}}
 return {schema:'opent1d.lt1-buffer-worker/2',kind:entry.kind,case_id:entry.case_id,slot,verification_context_origin:invented?'invented':'current-runtime',
  completed:results.every(r=>r.status==='completed'),construction_count:constructionCount,patient_reset_calls:patientResets,nonfinite_initial_state_probe:nonfiniteProbe,initial_state_consumed_observation:invented&&nonfiniteProbe?built.patient.initialStateConsumed:null,native_basal:basal,sessions:results,packet_sha256:Object.fromEntries(PACKET.map(n=>[n,digest(packet[n])])),native_acceptance:false,native_execution_authorized:false};
}
function own(state,authority,invented,authorityHash){
 admit(state.entryRaw,state.observationRaw,authority,invented);
 const entryRaw=Buffer.from(state.entryRaw),observationRaw=Buffer.from(state.observationRaw);
 admit(entryRaw,observationRaw,authority,invented);
 const packet=Object.fromEntries(PACKET.map(n=>[n,Buffer.from(state.packet[n])])),entry=decoded(entryRaw);
 const args=['staging','packet','output'].map(k=>entry.roots[k]),expected=JSON.parse(JSON.stringify(state.expected));
 validate(entryRaw,observationRaw,packet,args,expected,authority,invented,authorityHash);
 const signal=state.signal;need(signal===undefined||signal instanceof AbortSignal,'worker cancellation signal');
 return {entryRaw,observationRaw,packet,entry,observation:decoded(observationRaw),expected,authority,authorityHash,signal};
}
export async function runNative(state){
 const raw=fs.readFileSync(new URL('./native-admissions.json',import.meta.url));
 const authority=registry(JSON.parse(raw));need(authority.setup.length&&authority.execution.length,'no reviewed native worker grants');
 return run(own(state,authority,false,digest(raw)),false);
}
export async function runInvented(state){return run(own(state,state.authority,true),true);}

