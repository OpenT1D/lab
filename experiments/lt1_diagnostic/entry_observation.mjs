/** Fixed current-process observation library. No CLI, native launch or transport. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

export const MAGIC = 'OPENT1D-LT1-ENTRY-1\n';
export const LIMIT = 64 * 1024;
const PACKET = ['grant.json','integration-grant.json','integration_host_receipt.json',
 'plan.json','setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'];
const GRANT_FIELDS = ['schema','packet_sha256','runtime','entry_executable','owner_pid',
 'owner_start','attempt','nonce_sha256','profile_sha256','producer_sha256','reader_identity','process_argv'];
const FACT_FIELDS = ['pid','ppid','exec_path','node','platform','arch','exec_argv',
 'environment_keys','environment','executable_sha256','producer_sha256','stdio','process_argv'];
const ENV = {LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'};
const need = (ok, reason) => {if (!ok) throw Error('LT1 entry observation refused: '+reason);};
export const digest = value => createHash('sha256').update(value).digest('hex');
const sha = value => typeof value==='string' && /^[a-f0-9]{64}$/.test(value);
const fields = (value, keys) => {
 need(value && !Array.isArray(value) && typeof value==='object','closed fields');
 need(Object.keys(value).length===keys.length && keys.every(key=>Object.hasOwn(value,key)),
  'closed fields');
};
function decode(raw) {
 need(Buffer.isBuffer(raw) && raw.length>0 && raw.length<=1024*1024,'grant bytes');
 return JSON.parse(raw.toString('utf8'));
}
function grantValue(raw) {
 const grant=decode(raw);
 need(Buffer.from(JSON.stringify(grant),'utf8').equals(raw),'canonical observation grant bytes');
 fields(grant,GRANT_FIELDS);fields(grant.packet_sha256,PACKET);
 fields(grant.runtime,['node','platform','arch','executable_sha256']);
 need(grant.schema==='opent1d.lt1-entry-observation-grant/1' &&
 Object.values(grant.packet_sha256).every(sha) && sha(grant.runtime.executable_sha256) &&
 ['node','platform','arch'].every(k=>typeof grant.runtime[k]==='string') &&
 sha(grant.nonce_sha256) && sha(grant.profile_sha256) && sha(grant.producer_sha256) &&
 Number.isSafeInteger(grant.owner_pid) && grant.owner_pid>1 &&
 typeof grant.owner_start==='string' && grant.owner_start.length>0 && grant.owner_start.length<=512 &&
 typeof grant.attempt==='string' && /^[a-z0-9][a-z0-9-]{0,63}$/.test(grant.attempt) &&
 typeof grant.entry_executable==='string' && grant.entry_executable.startsWith('/') &&
 resolve(grant.entry_executable)===grant.entry_executable &&
 grant.reader_identity && typeof grant.reader_identity==='object' &&
 Array.isArray(grant.process_argv) && grant.process_argv.length>=2 && grant.process_argv.length<=16 &&
 grant.process_argv[0]===grant.entry_executable &&
 grant.process_argv.every(v=>typeof v==='string'&&v.length>0&&v.length<=1024&&!v.includes('\0')),'grant identity');
 return grant;
}
function factsValue(facts,grant) {
 fields(facts,FACT_FIELDS);fields(facts.environment,Object.keys(ENV));
 need(Number.isSafeInteger(facts.pid) && facts.pid>1 && facts.pid!==grant.owner_pid &&
 facts.ppid===grant.owner_pid && facts.exec_path===grant.entry_executable &&
 ['node','platform','arch'].every(k=>facts[k]===grant.runtime[k]) &&
 JSON.stringify(facts.process_argv)===JSON.stringify(grant.process_argv) &&
 facts.executable_sha256===grant.runtime.executable_sha256 &&
 facts.producer_sha256===grant.producer_sha256 && facts.stdio==='unobserved' &&
 Array.isArray(facts.exec_argv) && facts.exec_argv.length===0 &&
 Array.isArray(facts.environment_keys) &&
 JSON.stringify(facts.environment_keys)===JSON.stringify(Object.keys(ENV).sort()) &&
 Object.keys(ENV).every(k=>facts.environment[k]===ENV[k]),'process/runtime/ambient facts');
}
function frame(raw,facts,at,kind) {
 const grant=grantValue(raw);factsValue(facts,grant);
 need(typeof at==='string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(at) &&
 Number.isFinite(Date.parse(at)) && new Date(at).getUTCFullYear()>=1 &&
 new Date(at).toISOString()===at,'canonical UTC observation time');
 const result=Buffer.from(MAGIC+JSON.stringify({schema:'opent1d.lt1-entry-observation/1',kind,
 phase:'unqualified-current-process-observation',observed_at:at,grant_sha256:digest(raw),
 attempt:grant.attempt,nonce_sha256:grant.nonce_sha256,facts,
 native_host_qualified:false,native_acceptance:false,setup_admitted:false,
 native_execution_authorized:false})+'\n');
 need(result.length<=LIMIT,'frame bound');return result;
}
export function encodeInvented(raw,facts,at) {
 // Supplied facts can never select observed origin or a bootstrap-phase claim.
 return frame(raw,facts,at,'invented');
}
function hashFile(path,limit) {
 const fd=fs.openSync(path,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
 try {
  const first=fs.fstatSync(fd,{bigint:true});
  need(first.isFile() && first.nlink===1n && first.size<=BigInt(limit),'ordinary bounded source');
  const state=createHash('sha256'),buffer=Buffer.alloc(64*1024);let count=0;
  for (;;) {
   const n=fs.readSync(fd,buffer,0,Math.min(buffer.length,limit+1-count),null);
   if(!n)break;count+=n;need(count<=limit,'read grew');state.update(buffer.subarray(0,n));
  }
  const last=fs.fstatSync(fd,{bigint:true}),named=fs.lstatSync(path,{bigint:true});
  const signature=s=>[s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs,s.nlink].join(':');
  need(signature(first)===signature(last) && signature(last)===signature(named) &&
   BigInt(count)===first.size && !named.isSymbolicLink(),'source changed');
  return state.digest('hex');
 } finally {fs.closeSync(fd);}
}
export function collectCurrent(raw,packet) {
 // Only this source-local authority is consulted; no caller command/path is opened.
 const registry=JSON.parse(fs.readFileSync(new URL('./native-admissions.json',import.meta.url),'utf8'));
 need(registry.schema==='opent1d.lt1-native-admissions/1' && Array.isArray(registry.execution) &&
 Array.isArray(registry.setup) && Buffer.isBuffer(raw) && raw.length<=1024*1024 &&
 registry.execution.includes(digest(raw)),'no reviewed observation grant');
 const grant=grantValue(raw);
 need(registry.execution.includes(grant.packet_sha256['grant.json']) &&
 registry.execution.includes(grant.packet_sha256['integration-grant.json']) &&
 registry.setup.includes(grant.packet_sha256['setup_receipt.json']),
 'no reviewed engine/integration/setup membership');
 fields(packet,PACKET);
 need(Object.values(packet).every(v=>Buffer.isBuffer(v)&&v.length>0&&v.length<=4*1024*1024) &&
 Object.values(packet).reduce((n,v)=>n+v.length,0)<=32*1024*1024 &&
 PACKET.every(k=>digest(packet[k])===grant.packet_sha256[k]),'packet byte binding');
 const engine=decode(packet['grant.json']),integration=decode(packet['integration-grant.json']);
 const host=decode(packet['integration_host_receipt.json']);
 need(engine.schema==='opent1d.lt1-native-grant/1' &&
 integration.schema==='opent1d.lt1-integration-grant/1' &&
 integration.engine_grant_sha256===grant.packet_sha256['grant.json'] &&
 engine.setup_receipt_sha256===grant.packet_sha256['setup_receipt.json'] &&
 integration.host_receipt_sha256===grant.packet_sha256['integration_host_receipt.json'] &&
 integration.owner_pid===grant.owner_pid && integration.attempt===grant.attempt &&
 host.owner_context?.observer?.pid===grant.owner_pid &&
 host.owner_context?.observer?.start===grant.owner_start && host.profile_sha256===grant.profile_sha256 &&
 resolve(engine.staging_root,'runtime/bin/node')===grant.entry_executable &&
 ['node','platform','arch'].every(k=>engine[k]===grant.runtime[k]) &&
 engine.files?.['runtime/bin/node']===grant.runtime.executable_sha256,'packet identity');
 need(process.execPath===grant.entry_executable && process.ppid===grant.owner_pid &&
 process.version===grant.runtime.node && process.platform===grant.runtime.platform &&
 process.arch===grant.runtime.arch,'current process identity');
 const facts={pid:process.pid,ppid:process.ppid,exec_path:process.execPath,node:process.version,
 process_argv:[...process.argv],
 platform:process.platform,arch:process.arch,exec_argv:[...process.execArgv],
 environment_keys:Object.keys(process.env).sort(),
 environment:Object.fromEntries(Object.keys(ENV).map(k=>[k,process.env[k]])),
 executable_sha256:hashFile(process.execPath,128*1024*1024),
 producer_sha256:hashFile(fileURLToPath(import.meta.url),1024*1024),stdio:'unobserved'};
 return frame(raw,facts,new Date().toISOString(),'observed');
}
