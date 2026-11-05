/** Fixed tooling-Node process fixture. Invented facts; never loads LT1. */
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {once} from 'node:events';
import {withFixedChannels,handoffCurrentOnFixedChannels}
 from '../experiments/lt1_diagnostic/entry_channels.mjs';
import {handoffInvented,acknowledge,AUTHORITY}
 from '../experiments/lt1_diagnostic/entry_handoff.mjs';
import {LIMIT,digest} from '../experiments/lt1_diagnostic/entry_observation.mjs';

const self=fileURLToPath(import.meta.url);
const [role,behavior,folder]=process.argv.slice(2);
const put=(name,value)=>fs.writeFileSync(join(folder,name),JSON.stringify(value)+'\n',{flag:'wx',mode:0o600});
const ready=()=>put('ready.json',{ready:true});
const check=(ok,why)=>{if(!ok)throw Error('fixture: '+why);};
const record=result=>({...result,frame_raw:result.frame_raw?.toString('base64'),
 ack_raw:result.ack_raw?.toString('base64')});
const grant={schema:'opent1d.lt1-entry-observation-grant/1',
 packet_sha256:Object.fromEntries(['grant.json','integration-grant.json','integration_host_receipt.json',
 'plan.json','setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'].map(n=>[n,'a'.repeat(64)])),
 runtime:{node:'tooling-invented',platform:'invented',arch:'invented',executable_sha256:'b'.repeat(64)},
 entry_executable:'/invented/node',owner_pid:12345,owner_start:'invented-owner-start',
 attempt:'invented-process-channel',nonce_sha256:'c'.repeat(64),profile_sha256:'d'.repeat(64),
 producer_sha256:'e'.repeat(64),reader_identity:{invented:true},
 process_argv:['/invented/node','/invented/entry']};
const facts={pid:54321,ppid:12345,exec_path:grant.entry_executable,...grant.runtime,
 exec_argv:[],environment_keys:['LANG','LC_ALL','PATH'],environment:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'},
 producer_sha256:grant.producer_sha256,stdio:'unobserved',process_argv:grant.process_argv};
const raw=Buffer.from(JSON.stringify(grant)),at='2026-11-04T00:00:00.000Z';

async function entry(){
 if(behavior==='closed-gate'){
  const trap=new Proxy({}, {get(){throw Error('packet touched');},ownKeys(){throw Error('packet touched');}});
  try{await handoffCurrentOnFixedChannels(Buffer.from('not-admitted'),trap,trap);}
  catch(e){check(e.message.includes('no reviewed observation grant'),'gate before FD inspection');
   put('gate.json',{refused:true,reason:'no-reviewed-observation-grant',...AUTHORITY});return;}
  throw Error('closed production gate accepted');
 }
 if(behavior==='descriptor-refusal'){
  let called=false;
  try{await withFixedChannels(()=>{called=true;});}
  catch(e){check(!called&&e.message.includes('socket identities'),'refuse before exchange');
   fs.fstatSync(3);fs.fstatSync(4);
   put('descriptor.json',{refused:true,descriptors_retained:true,...AUTHORITY});return;}
  throw Error('unsafe descriptors accepted');
 }
 if(behavior==='callback-error'){
  try{await withFixedChannels(input=>{input.destroy(new Error('owned callback close'));
   throw Error('primary callback error');});}
  catch(e){check(e.message==='primary callback error','preserve callback error');}
  await new Promise(resolve=>setImmediate(resolve));
  put('callback.json',{primary_preserved:true,...AUTHORITY});return;
 }
 const controller=new AbortController();
 if(behavior==='cancel')setTimeout(()=>controller.abort(),250);
 const result=await withFixedChannels((input,output)=>handoffInvented(raw,facts,at,input,output,
  {timeout_ms:behavior==='cancel'?3000:1500,signal:controller.signal}));
 put('entry.json',{...record(result),fixture_process:{pid:process.pid,ppid:process.ppid}});
 process.stdout.write('tooling-entry-stdout\n');process.stderr.write('tooling-entry-stderr\n');
 if(behavior==='hang'){
  check(result.status==='acknowledged','handoff precedes owned stop');ready();
  process.on('SIGTERM',()=>{});setInterval(()=>{},50);return;
 }
 process.exitCode=result.status==='acknowledged'?0:23;
}

async function parent(){
 if(behavior==='closed-gate'){
  const child=spawn(process.execPath,[self,'entry',behavior,folder],
   {stdio:['ignore','inherit','inherit'],env:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'}});
  const [code]=await once(child,'exit');process.exitCode=code;return;
 }
 const child=spawn(process.execPath,[self,'entry',behavior,folder],
  {stdio:['ignore','pipe','pipe','pipe','pipe'],env:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'}});
 const exit=once(child,'exit'),closed=once(child,'close');
 let frame=[],bytes=0,stdout=[],stderr=[],sawEOF=false;
 child.stdout.on('data',v=>stdout.push(Buffer.from(v)));child.stderr.on('data',v=>stderr.push(Buffer.from(v)));
 child.stdio[3].on('error',()=>{});child.stdio[4].on('error',()=>{});
 child.stdio[4].on('data',v=>{
  bytes+=v.length;if(bytes>LIMIT){child.kill('SIGKILL');throw Error('oversize fixture frame');}
  frame.push(Buffer.from(v));
 });
 child.stdio[4].on('end',()=>{
  if(behavior==='callback-error')return;
  sawEOF=true;const full=Buffer.concat(frame),ack=acknowledge(full);
  if(behavior==='wrong-ack')child.stdio[3].end(Buffer.from('wrong\n'));
  else if(['no-eof','cancel'].includes(behavior)){child.stdio[3].write(ack);ready();}
  else if(behavior==='close')child.stdio[3].destroy();
  else{child.stdio[3].write(ack.subarray(0,17));child.stdio[3].end(ack.subarray(17));}
 });
 const [code,signal]=await exit;
 child.stdio[3].destroy();child.stdio[4].destroy();
 await closed;
 if(behavior==='callback-error'){check(code===0,'callback cleanup error stayed owned');return;}
 put('parent.json',{code,signal,frame_eof:sawEOF,frame_sha256:digest(Buffer.concat(frame)),
  frame_bytes:bytes,stdout:Buffer.concat(stdout).toString(),stderr:Buffer.concat(stderr).toString(),
  ...AUTHORITY});
 process.exitCode=code===0?0:23;
}
try{check(['entry','parent'].includes(role),'fixed role');
 await (role==='entry'?entry():parent());}
catch(e){process.stderr.write(String(e)+'\n');process.exitCode=1;}
