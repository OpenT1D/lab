/** Invented facts only; the production observer remains closed. */
import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import {encodeInvented,collectCurrent,MAGIC,digest} from '../experiments/lt1_diagnostic/entry_observation.mjs';
if(process.argv.includes('--emit')){
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 process.stdout.write(encodeInvented(Buffer.from(input.grant,'base64'),input.facts,input.at));
}else{
 const grant={schema:'opent1d.lt1-entry-observation-grant/1',
 packet_sha256:Object.fromEntries(['grant.json','integration-grant.json','integration_host_receipt.json',
  'plan.json','setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'].map(k=>[k,'a'.repeat(64)])),
 runtime:{node:'v22.23.4',platform:'darwin',arch:'arm64',executable_sha256:'b'.repeat(64)},
 entry_executable:'/invented/stage/runtime/bin/node',owner_pid:12345,owner_start:'darwin:1:2',
 attempt:'invented-attempt',nonce_sha256:'c'.repeat(64),profile_sha256:'d'.repeat(64),
 producer_sha256:'e'.repeat(64),reader_identity:{invented:true},
 process_argv:['/invented/stage/runtime/bin/node','/invented/entry.mjs']};
 const facts={pid:54321,ppid:12345,exec_path:grant.entry_executable,node:grant.runtime.node,
 platform:'darwin',arch:'arm64',exec_argv:[],environment_keys:['LANG','LC_ALL','PATH'],
 environment:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'},executable_sha256:grant.runtime.executable_sha256,
 producer_sha256:grant.producer_sha256,stdio:'unobserved',process_argv:[...grant.process_argv]};
 const raw=Buffer.from(JSON.stringify(grant));
 test('supplied facts force invented and a single complete frame',()=>{
  const bytes=encodeInvented(raw,facts,'2026-11-03T12:00:00.000Z','observed');
  assert(bytes.toString().startsWith(MAGIC));assert.equal(bytes.toString().split('\n').length,3);
  const row=JSON.parse(bytes.toString().split('\n')[1]);assert.equal(row.kind,'invented');
  assert.equal(row.phase,'unqualified-current-process-observation');
  assert.equal(row.native_host_qualified,false);assert.equal(row.native_acceptance,false);
 });
 test('unknown production grant refuses before packet intake',()=>{
  const packet=new Proxy({}, {ownKeys(){throw Error('packet touched');}});
  assert.throws(()=>collectCurrent(Buffer.from('unknown'),packet),/no reviewed observation grant/);
 });
 test('an observation grant alone cannot touch packet intake',()=>{
  const original=fs.readFileSync;
  fs.readFileSync=(...args)=>args[0] instanceof URL && args[0].pathname.endsWith('/native-admissions.json') ?
   JSON.stringify({schema:'opent1d.lt1-native-admissions/1',execution:[digest(raw)],setup:[]}) : original(...args);
  try {
   const packet=new Proxy({}, {ownKeys(){throw Error('packet touched');}});
   assert.throws(()=>collectCurrent(raw,packet),/no reviewed engine\/integration\/setup membership/);
  } finally {fs.readFileSync=original;}
 });
 test('ambient flags/environment, owner-as-entry and changed executable refuse',()=>{
  for(const change of [{pid:grant.owner_pid},{exec_argv:['--require','outside']},
   {environment_keys:['LANG','LC_ALL','PATH','NODE_OPTIONS']},{executable_sha256:'f'.repeat(64)},
   {process_argv:['/invented/other','/invented/entry.mjs']},{stdio:'verified'}]){
   assert.throws(()=>encodeInvented(raw,{...facts,...change},'2026-11-03T12:00:00.000Z'));
  }
 });
 test('noncanonical new grants and noncanonical UTC times refuse',()=>{
  const text=raw.toString();
  for(const value of [text.replace('"owner_pid":12345','"owner_pid":12345.0'),
   text.replace('"owner_pid":12345','"owner_pid":12345,"owner_pid":12345'),
   ' '+text])assert.throws(()=>encodeInvented(Buffer.from(value),facts,'2026-11-03T12:00:00.000Z'));
  for(const at of ['2026-11-03T14:00:00+02:00','2026-11-03T12:00:00',
   '2026-02-31T12:00:00.000Z','0000-01-01T00:00:00.000Z']){
   assert.throws(()=>encodeInvented(raw,facts,at));
  }
 });
 test('NUL-joined field names cannot impersonate two required keys',()=>{
  const changed=structuredClone(grant),a='grant.json',b='host_receipt.json';
  const value=changed.packet_sha256[a];delete changed.packet_sha256[a];delete changed.packet_sha256[b];
  changed.packet_sha256[a+'\0'+b]=value;
  assert.throws(()=>encodeInvented(Buffer.from(JSON.stringify(changed)),facts,'2026-11-03T12:00:00.000Z'),/closed fields/);
 });
 test('unknown grant/fact fields and unsafe metadata refuse',()=>{
  assert.throws(()=>encodeInvented(Buffer.from(JSON.stringify({...grant,command:'outside'})),facts,'2026-11-03T12:00:00.000Z'));
  assert.throws(()=>encodeInvented(raw,{...facts,private_value:'not allowed'},'2026-11-03T12:00:00.000Z'));
  assert.throws(()=>encodeInvented(raw,{...facts,pid:true},'2026-11-03T12:00:00.000Z'));
 });
}
