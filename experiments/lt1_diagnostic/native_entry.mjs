/** Versioned trusted-code continuation. No launcher, native CLI or alternate authority. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {withFixedChannels,handoffCurrentOnFixedChannels} from './entry_channels.mjs';
import {handoffInvented} from './entry_handoff.mjs';

const ROOT=resolve(fileURLToPath(new URL('../../',import.meta.url)));
const ENTRY='experiments/lt1_diagnostic/native_entry.mjs';
const SOURCE_KEYS='experiments/lt1_diagnostic/native_entry_sources.json';
const FIXTURE='tests/lt1_native_entry_fixture.mjs';
const PACKET=['grant.json','integration-grant.json','integration_host_receipt.json','plan.json',
 'setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'];
const KEYS=['schema','kind','observation_sha256','engine_sha256','integration_sha256',
 'setup_sha256','entry_sources','roots','profile_sha256','owner_pid','owner_start','attempt',
 'nonce_sha256','process_argv','new_host_qualification_required'];
const REQUIRED=['native_entry.py','native_entry.mjs','native_host_plan.py','native_launcher.py',
 'native_worker.mjs','integration_worker.mjs','native_loader.mjs','reader.py','journal_reader.py',
 'entry_channels.mjs','entry_handoff.mjs','entry_observation.mjs','native_entry_sources.json'];
const AUTHORITY_SOURCES=['native-admissions.json','setup-request-admissions.json','removal-admissions.json']
 .map(n=>'experiments/lt1_diagnostic/'+n);
const ENV={LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'};
export const AUTHORITY=Object.freeze({native_host_qualified:false,native_acceptance:false,
 setup_admitted:false,native_execution_authorized:false,
 effective_erasure_verified:false,phase_verified:false,endpoint_identity_verified:false,
 new_authority_granted:false});
const need=(ok,why)=>{if(!ok)throw Error('LT1 native entry refused: '+why);};
const sha=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const fields=(v,keys)=>need(v&&typeof v==='object'&&!Array.isArray(v)&&
 Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k)),'closed fields');
function same(a,b){
 if(a===b)return true;
 if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;
 const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));
}
function bytes(raw,max=1024*1024){need(Buffer.isBuffer(raw)&&raw.length>0&&raw.length<=max,'bounded raw grant');return raw;}
function decoded(raw){
 const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes(raw));
 const value=JSON.parse(text);
 need(Buffer.from(JSON.stringify(value)).equals(raw),'canonical grant bytes');return value;
}
function registry(value){
 fields(value,['schema','setup','execution']);
 need(value.schema==='opent1d.lt1-native-admissions/1','canonical authority schema');
 for(const key of ['setup','execution'])need(Array.isArray(value[key])&&value[key].length<=4096&&
 value[key].every(sha)&&new Set(value[key]).size===value[key].length,'bounded exact authority');
 return value;
}
function admit(entryRaw,observationRaw,authority,invented){
 for(const raw of [entryRaw,observationRaw])need(authority.execution.includes(digest(bytes(raw))),'exact entry/observation membership');
 const entry=decoded(entryRaw);fields(entry,KEYS);
 need(entry.schema==='opent1d.lt1-native-entry-continuation-grant/1'&&
  entry.kind===(invented?'invented':'native-preparation')&&entry.new_host_qualification_required===true,'versioned entry purpose');
 need(['observation_sha256','engine_sha256','integration_sha256','setup_sha256'].every(k=>sha(entry[k]))&&
  entry.observation_sha256===digest(observationRaw)&&authority.execution.includes(entry.engine_sha256)&&
  authority.execution.includes(entry.integration_sha256)&&authority.setup.includes(entry.setup_sha256),
  'exact declared engine/integration/setup membership');
}
function sourceFile(name){
 need(typeof name==='string'&&name.startsWith('experiments/')&&name.length<=512&&
 !name.includes('\\')&&!name.includes('\0')&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'),'public source path');
 const path=resolve(ROOT,name);need(fs.realpathSync(path)===path,'canonical public source');
 const fd=fs.openSync(path,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
 try{
  const before=fs.fstatSync(fd,{bigint:true});
  need(before.isFile()&&before.nlink===1n&&before.size<=4n*1024n*1024n,'bounded ordinary source');
  const h=createHash('sha256'),part=Buffer.alloc(65536);let total=0;
  for(;;){const n=fs.readSync(fd,part,0,Math.min(part.length,4*1024*1024+1-total),null);
   if(!n)break;total+=n;need(total<=4*1024*1024,'source grew');h.update(part.subarray(0,n));}
  const after=fs.fstatSync(fd,{bigint:true}),named=fs.lstatSync(path,{bigint:true});
  const sig=s=>[s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs,s.nlink].join(':');
  need(sig(before)===sig(after)&&sig(after)===sig(named)&&BigInt(total)===before.size&&!named.isSymbolicLink(),'source changed');
  return h.digest('hex');
 }finally{fs.closeSync(fd);}
}
function checkSources(sources,expected,authorityDigest){
 fields(expected,['source_identity','profile_sha256','process_argv']);
 fields(expected.source_identity,['implementation','python','executable_sha256']);
 const audit=expected.source_identity.implementation;
 need(audit&&typeof audit==='object'&&!Array.isArray(audit)&&Object.keys(audit).length<=4096&&
  AUTHORITY_SOURCES.every(n=>sha(audit[n])),'complete external authority audit');
 const keyRaw=fs.readFileSync(new URL('./native_entry_sources.json',import.meta.url));
 bytes(keyRaw);need(sha(audit[SOURCE_KEYS])&&digest(keyRaw)===audit[SOURCE_KEYS],'source-key manifest bytes');
 const keys=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(keyRaw));
 fields(keys,['schema','sources']);
 need(keys.schema==='opent1d.lt1-native-entry-source-keys/1'&&Array.isArray(keys.sources)&&
  same(keys.sources,[...new Set(Object.keys(audit))].sort()),'versioned complete source-key manifest');
 const code=Object.fromEntries(Object.entries(audit).filter(([n])=>!AUTHORITY_SOURCES.includes(n)));
 need(sources&&typeof sources==='object'&&!Array.isArray(sources)&&
 Object.keys(sources).length>0&&Object.keys(sources).length<=4096&&
 same(sources,code)&&
 REQUIRED.every(n=>Object.hasOwn(sources,'experiments/lt1_diagnostic/'+n)),'complete externally pinned entry/base sources');
 if(authorityDigest!==undefined)need(audit[AUTHORITY_SOURCES[0]]===authorityDigest,'canonical authority snapshot changed');
 // Hash the full independently supplied audit, including mutable authorities.
 // Those values are intentionally outside grant bytes to avoid a registry hash cycle.
 for(const [name,hash]of Object.entries(audit))need(sha(hash)&&sourceFile(name)===hash,'current public entry/base bytes');
}
function absolute(value){need(typeof value==='string'&&value.length>0&&value.length<=1024&&
 value.startsWith('/')&&!value.startsWith('//')&&!value.includes('\0')&&resolve(value)===value&&
 value.split('/').slice(1).every(p=>p&&p!=='.'&&p!=='..'),'absolute lexical root');return value;}
const nested=(a,b)=>a===b||a.startsWith(b+'/');
function packetBindings(entryRaw,observationRaw,packet,authority){
 fields(packet,PACKET);
 need(Object.values(packet).every(v=>Buffer.isBuffer(v)&&v.length>0&&v.length<=4*1024*1024)&&
 Object.values(packet).reduce((n,v)=>n+v.length,0)<=32*1024*1024,'bounded packet buffers');
 const hashes=Object.fromEntries(PACKET.map(n=>[n,digest(packet[n])]));
 need(authority.execution.includes(hashes['grant.json'])&&authority.execution.includes(hashes['integration-grant.json'])&&
 authority.setup.includes(hashes['setup_receipt.json']),'exact engine/integration/setup memberships');
 const entry=decoded(entryRaw),observation=decoded(observationRaw);
 need(same(observation.packet_sha256,hashes)&&entry.engine_sha256===hashes['grant.json']&&
  entry.integration_sha256===hashes['integration-grant.json']&&entry.setup_sha256===hashes['setup_receipt.json'],
  'complete actual packet binding before context intake');
 return {entry,observation,hashes};
}
function validate(entryRaw,observationRaw,packet,args,expected,authority,invented,authorityDigest){
 admit(entryRaw,observationRaw,authority,invented);
 const {entry,observation,hashes}=packetBindings(entryRaw,observationRaw,packet,authority);fields(entry,KEYS);
 need(entry.schema==='opent1d.lt1-native-entry-continuation-grant/1'&&
 entry.kind===(invented?'invented':'native-preparation')&&entry.new_host_qualification_required===true,'versioned entry purpose');
 checkSources(entry.entry_sources,expected,authorityDigest);
 fields(entry.roots,['staging','packet','output','evidence']);const roots=Object.values(entry.roots).map(absolute);
 need(roots.every((p,i)=>!nested(p,ROOT)&&!nested(ROOT,p)&&roots.every((q,j)=>i===j||(!nested(p,q)&&!nested(q,p)))),'separate lexical roots');
 need(Array.isArray(args)&&same(args,['staging','packet','output'].map(k=>entry.roots[k])),'fixed continuation arguments');
 need(sha(entry.profile_sha256)&&entry.profile_sha256===expected.profile_sha256&&
 entry.observation_sha256===digest(observationRaw)&&entry.engine_sha256===hashes['grant.json']&&
 entry.integration_sha256===hashes['integration-grant.json']&&entry.setup_sha256===hashes['setup_receipt.json'],'entry grant bindings');
 need(Number.isSafeInteger(entry.owner_pid)&&entry.owner_pid>1&&process.ppid===entry.owner_pid&&
 typeof entry.owner_start==='string'&&entry.owner_start.length>0&&entry.owner_start.length<=512&&
 typeof entry.attempt==='string'&&/^[a-z0-9][a-z0-9-]{0,63}$/.test(entry.attempt)&&sha(entry.nonce_sha256),'current owner/nonce');
 need(Array.isArray(entry.process_argv)&&entry.process_argv.length>=2&&entry.process_argv.length<=16&&
 entry.process_argv.every(v=>typeof v==='string'&&v.length>0&&v.length<=1024&&!v.includes('\0'))&&
 same(entry.process_argv,expected.process_argv)&&same(entry.process_argv,process.argv),'current fixed process arguments');
 if(invented)need(entry.process_argv[1]===resolve(ROOT,FIXTURE),'fixed invented entry');
 else need(same(entry.process_argv,[entry.roots.staging+'/runtime/bin/node',resolve(ROOT,ENTRY),...args]),'fixed future entry convention');
 need(observation.schema==='opent1d.lt1-entry-observation-grant/1'&&same(observation.packet_sha256,hashes)&&
 observation.profile_sha256===entry.profile_sha256&&observation.producer_sha256===entry.entry_sources['experiments/lt1_diagnostic/entry_observation.mjs']&&
 ['owner_pid','owner_start','attempt','nonce_sha256','process_argv'].every(k=>same(observation[k],entry[k])),'observation entry/owner/nonce binding');
 const host=decoded(packet['integration_host_receipt.json']);
 need(host.schema==='opent1d.lt1-native-entry-host/1'&&host.kind===(invented?'invented':'observed')&&
 host.purpose==='qualification-only'&&host.profile_sha256===entry.profile_sha256&&same(host.entry_sources,entry.entry_sources)&&
 same(host.owner_context?.observer,{pid:entry.owner_pid,start:entry.owner_start}),'new entry host namespace; old receipt cannot qualify it');
 const integration=decoded(packet['integration-grant.json']),engine=decoded(packet['grant.json']);
 need(integration.engine_grant_sha256===hashes['grant.json']&&integration.host_receipt_sha256===hashes['integration_host_receipt.json']&&
 integration.owner_pid===entry.owner_pid&&integration.attempt===entry.attempt&&
 same(integration.reader_identity,observation.reader_identity)&&engine.setup_receipt_sha256===hashes['setup_receipt.json'],'underlying packet bindings');
 return {entry,observation};
}
let inventedCalls=0;
function benignContinuation(args){
 inventedCalls+=1;
 return {kind:'invented-benign-continuation',call_ordinal:inventedCalls,pid:process.pid,args:[...args]};
}
async function run(entryRaw,observationRaw,packet,args,expected,authority,invented,options,authorityDigest){
 admit(entryRaw,observationRaw,authority,invented);
 // Own and re-admit grant copies before any caller getter can run.
 const originalEntry=entryRaw,originalObservation=observationRaw;
 entryRaw=Buffer.from(entryRaw);observationRaw=Buffer.from(observationRaw);
 admit(entryRaw,observationRaw,authority,invented);
 need(options&&typeof options==='object'&&!Array.isArray(options)&&
 Object.keys(options).every(k=>['timeout_ms','signal'].includes(k)),'handoff options');
 const originalOptions=options,signal=options.signal,timeout=options.timeout_ms;
 need(signal===undefined||signal instanceof AbortSignal,'cancellation signal');
 options={...(timeout===undefined?{}:{timeout_ms:timeout}),...(signal===undefined?{}:{signal})};
 need(originalEntry.equals(entryRaw)&&originalObservation.equals(observationRaw),
  'API grant bytes changed before packet intake');
 // Preserve API ownership across ACK waits; never dispatch a caller-owned mutable array.
 bytes(entryRaw);bytes(observationRaw);fields(packet,PACKET);
 for(const raw of Object.values(packet))bytes(raw,4*1024*1024);
 const original={entryRaw:originalEntry,observationRaw:originalObservation,packet,args,expected};
 packet=Object.fromEntries(PACKET.map(n=>[n,Buffer.from(packet[n])]));
 packetBindings(entryRaw,observationRaw,packet,authority);
 need(Array.isArray(args),'fixed continuation arguments');args=[...args];
 expected=JSON.parse(JSON.stringify(expected));
 const {entry,observation}=validate(entryRaw,observationRaw,packet,args,expected,authority,invented,authorityDigest);
 function stableInputs(){
  need(original.entryRaw.equals(entryRaw)&&original.observationRaw.equals(observationRaw)&&
   same(original.args,args)&&same(original.expected,expected)&&
   PACKET.every(n=>Buffer.isBuffer(original.packet[n])&&original.packet[n].equals(packet[n])),
   'API input changed before continuation');
  need(originalOptions.signal===signal&&originalOptions.timeout_ms===timeout,'handoff options changed before continuation');
 }
 let continued=false,continuationReturned=false,continuationError=null,cancelledBeforeContinuation=false;
 let continuationCount=0,continuationValue=null;
 const exchange=invented?await withFixedChannels((input,output)=>{
  const facts={pid:process.pid,ppid:process.ppid,exec_path:process.execPath,...observation.runtime,
   exec_argv:[...process.execArgv],environment_keys:Object.keys(ENV).sort(),environment:{...ENV},
   producer_sha256:observation.producer_sha256,stdio:'unobserved',process_argv:[...process.argv]};
  return handoffInvented(observationRaw,facts,new Date().toISOString(),input,output,options);
 }):await handoffCurrentOnFixedChannels(observationRaw,packet,options);
 // Revalidate the complete public closure after the async exchange and before continuation.
 if(exchange.status==='acknowledged'){
  stableInputs();
  checkSources(entry.entry_sources,expected,authorityDigest);
  need(process.ppid===entry.owner_pid,'owner changed before continuation');
  // A later ACK end-listener may abort after handoff settles but before this microtask.
  cancelledBeforeContinuation=Boolean(signal?.aborted);
  if(cancelledBeforeContinuation){} // ACK success supplies no permission to continue after cancellation.
  else if(invented){
   continuationCount+=1;continuationValue=benignContinuation(args);continued=true;continuationReturned=true;
  }
  else{
   const {main}=await import('./integration_worker.mjs');
   stableInputs();checkSources(entry.entry_sources,expected,authorityDigest);
   need(process.ppid===entry.owner_pid,'owner changed during continuation import');
   cancelledBeforeContinuation=Boolean(signal?.aborted);
   if(!cancelledBeforeContinuation){
    continuationCount+=1;continued=true;
    try{await main(args);continuationReturned=true;}catch(error){continuationError=String(error);}
   }
  }
 }
 // "continued" records invocation only, never native attempt/journal/model completion.
 return {schema:'opent1d.lt1-native-entry-continuation/1',kind:entry.kind,
  status:cancelledBeforeContinuation?'cancelled':continuationError?'continuation-error':continued?'continued':exchange.status,
  cancelled_before_continuation:cancelledBeforeContinuation,
  continuation_count:continuationCount,continuation_value:continuationValue,continuation_returned:continuationReturned,
  continuation_error:continuationError,new_native_process_started_by_this_library:false,
  native_attempt_completion_verified:false,
  saved_outputs_require_private_accounting:true,
  continuation_pid:continued?process.pid:null,frame_raw:exchange.frame_raw,
  ack_raw:exchange.ack_raw,exchange_status:exchange.status,...AUTHORITY};
}
export async function continueNativeEntry(entryRaw,observationRaw,packet,args,expected,options={}){
 const authorityRaw=fs.readFileSync(new URL('./native-admissions.json',import.meta.url),'utf8');
 const authority=registry(JSON.parse(authorityRaw));
 need(authority.setup.length&&authority.execution.length,'no reviewed entry continuation grant');
 admit(entryRaw,observationRaw,authority,false);
 return run(entryRaw,observationRaw,packet,args,expected,authority,false,options,digest(Buffer.from(authorityRaw)));
}
export async function continueInventedEntry(entryRaw,observationRaw,packet,args,expected,options={}){
 // A source-fixed invented continuation only. This is not an alternate native registry.
 bytes(entryRaw);bytes(observationRaw);fields(packet,PACKET);for(const raw of Object.values(packet))bytes(raw);
 const authority={schema:'opent1d.lt1-native-admissions/1',setup:[digest(packet['setup_receipt.json'])],
 execution:[...new Set([entryRaw,observationRaw,packet['grant.json'],packet['integration-grant.json']].map(digest))]};
 return run(entryRaw,observationRaw,packet,args,expected,authority,true,options);
}
