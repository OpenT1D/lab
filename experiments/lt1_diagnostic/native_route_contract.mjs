/** Version2 closed contract shared by the executable entry and buffered worker. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {withFixedChannels,handoffCurrentOnFixedChannels} from './entry_channels.mjs';
import {handoffInvented} from './entry_handoff.mjs';

const ROOT=resolve(fileURLToPath(new URL('../../',import.meta.url)));
const ENTRY='experiments/lt1_diagnostic/native_route_cli.mjs';
const SOURCE_KEYS='experiments/lt1_diagnostic/native_route_sources.json';
const FIXTURE='tests/lt1_native_route_fixture.mjs';
const PACKET=['grant.json','integration-grant.json','integration_host_receipt.json','plan.json',
 'setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'];
const KEYS=['schema','kind','observation_sha256','engine_sha256','integration_sha256',
 'setup_sha256','entry_sources','roots','profile_sha256','owner_pid','owner_start','attempt',
 'nonce_sha256','process_argv','case_id','slot'];
const REQUIRED=['native_entry.py','native_entry.mjs','native_host_plan.py','native_launcher.py',
 'native_worker.mjs','integration_worker.mjs','native_loader.mjs','reader.py','journal_reader.py',
 'entry_channels.mjs','entry_handoff.mjs','entry_observation.mjs','native_entry_sources.json','native_route.py','native_route_exec.py','native_route_transport.py','native_route_reader.py','native_route_sources.json','native_route_cli.mjs','native_route_contract.mjs','native_route_worker.mjs','native_route_descendant.mjs'];
const AUTHORITY_SOURCES=['native-admissions.json','setup-request-admissions.json','removal-admissions.json']
 .map(n=>'experiments/lt1_diagnostic/'+n);
const ENV={LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'};
export const AUTHORITY=Object.freeze({native_host_qualified:false,native_acceptance:false,
 setup_admitted:false,native_execution_authorized:false,
 effective_erasure_verified:false,phase_verified:false,endpoint_identity_verified:false,
 new_authority_granted:false});
const need=(ok,why)=>{if(!ok)throw Error('LT1 native entry refused: '+why);};
const sha=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export const digest=raw=>createHash('sha256').update(raw).digest('hex');
const fields=(v,keys)=>need(v&&typeof v==='object'&&!Array.isArray(v)&&
 Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k)),'closed fields');
export function same(a,b){
 if(a===b)return true;
 if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;
 const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));
}
function bytes(raw,max=1024*1024){need(Buffer.isBuffer(raw)&&raw.length>0&&raw.length<=max,'bounded raw grant');return raw;}
export function decoded(raw){
 const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes(raw));
 const value=JSON.parse(text);
 need(Buffer.from(JSON.stringify(value)).equals(raw),'canonical grant bytes');return value;
}
export function registry(value){
 fields(value,['schema','setup','execution']);
 need(value.schema==='opent1d.lt1-native-admissions/1','canonical authority schema');
 for(const key of ['setup','execution'])need(Array.isArray(value[key])&&value[key].length<=4096&&
 value[key].every(sha)&&new Set(value[key]).size===value[key].length,'bounded exact authority');
 return value;
}
export function admit(entryRaw,observationRaw,authority,invented){
 for(const raw of [entryRaw,observationRaw])need(authority.execution.includes(digest(bytes(raw))),'exact entry/observation membership');
 const entry=decoded(entryRaw);fields(entry,KEYS);
 need(entry.schema==='opent1d.lt1-native-route-grant/2'&&
  entry.kind===(invented?'invented':'native-unadmitted'),'versioned entry purpose');
 need(['observation_sha256','engine_sha256','integration_sha256','setup_sha256'].every(k=>sha(entry[k]))&&
  entry.observation_sha256===digest(observationRaw)&&authority.execution.includes(entry.engine_sha256)&&
  authority.execution.includes(entry.integration_sha256)&&authority.setup.includes(entry.setup_sha256),
  'exact declared engine/integration/setup membership');
}
function sourceFile(name){
 need(typeof name==='string'&&(name.startsWith('experiments/')||['tests/lt1_native_route_fixture.mjs','tests/lt1_native_route_fixture.py','tests/lt1_native_route_exec.py','tests/lt1_diagnostic_fixture.mjs','tests/lt1_native_route_coordinator.py','tests/lt1_native_route_models.mjs'].includes(name))&&name.length<=512&&
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
export function checkSources(sources,expected,authorityDigest){
 fields(expected,['source_identity','profile_sha256','process_argv']);
 fields(expected.source_identity,['implementation','python','executable_sha256']);
 const audit=expected.source_identity.implementation;
 need(audit&&typeof audit==='object'&&!Array.isArray(audit)&&Object.keys(audit).length<=4096&&
  AUTHORITY_SOURCES.every(n=>sha(audit[n])),'complete external authority audit');
 const keyRaw=fs.readFileSync(new URL('./native_route_sources.json',import.meta.url));
 bytes(keyRaw);need(sha(audit[SOURCE_KEYS])&&digest(keyRaw)===audit[SOURCE_KEYS],'source-key manifest bytes');
 const keys=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(keyRaw));
 fields(keys,['schema','sources']);
 need(keys.schema==='opent1d.lt1-native-route-sources/2'&&Array.isArray(keys.sources)&&
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
export function validate(entryRaw,observationRaw,packet,args,expected,authority,invented,authorityDigest){
 admit(entryRaw,observationRaw,authority,invented);
 const {entry,observation,hashes}=packetBindings(entryRaw,observationRaw,packet,authority);fields(entry,KEYS);
 need(entry.schema==='opent1d.lt1-native-route-grant/2'&&
 entry.kind===(invented?'invented':'native-unadmitted'),'versioned entry purpose');
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
 need(observation.schema==='opent1d.lt1-route-observation-grant/2'&&same(observation.packet_sha256,hashes)&&
 observation.profile_sha256===entry.profile_sha256&&observation.producer_sha256===entry.entry_sources['experiments/lt1_diagnostic/native_route_observation.mjs']&&
 ['owner_pid','owner_start','attempt','nonce_sha256','process_argv'].every(k=>same(observation[k],entry[k])),'observation entry/owner/nonce binding');
 const host=decoded(packet['integration_host_receipt.json']);
 need(host.schema==='opent1d.lt1-native-route-host/2'&&host.kind===(invented?'invented':'observed')&&
 host.purpose==='qualification-only'&&host.profile_sha256===entry.profile_sha256&&same(host.entry_sources,entry.entry_sources)&&
 same(host.owner_context?.observer,{pid:entry.owner_pid,start:entry.owner_start}),'new entry host namespace; old receipt cannot qualify it');
 const integration=decoded(packet['integration-grant.json']),engine=decoded(packet['grant.json']);
 need(integration.engine_grant_sha256===hashes['grant.json']&&integration.host_receipt_sha256===hashes['integration_host_receipt.json']&&
 integration.owner_pid===entry.owner_pid&&integration.attempt===entry.attempt&&
 same(integration.reader_identity,observation.reader_identity)&&engine.setup_receipt_sha256===hashes['setup_receipt.json'],'underlying packet bindings');
 return {entry,observation};
}

export {ROOT,ENTRY,FIXTURE,PACKET,ENV,fields,need};
