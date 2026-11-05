/** Fixed tooling-Node child; invented frames, no selected runtime or worker. */
import fs from 'node:fs';
import {withFixedChannels,handoffCurrentOnFixedChannels}
 from '../experiments/lt1_diagnostic/entry_channels.mjs';
import {handoffInvented} from '../experiments/lt1_diagnostic/entry_handoff.mjs';
import {encodeInvented,LIMIT} from '../experiments/lt1_diagnostic/entry_observation.mjs';

const [behavior,folder,extraFD]=process.argv.slice(2);
const put=(name,value)=>fs.writeFileSync(folder+'/'+name,JSON.stringify(value)+'\n',{flag:'wx',mode:0o600});
const grant={schema:'opent1d.lt1-entry-observation-grant/1',
 packet_sha256:Object.fromEntries(['grant.json','integration-grant.json','integration_host_receipt.json',
 'plan.json','setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'].map(n=>[n,'a'.repeat(64)])),
 runtime:{node:'invented-tooling',platform:'invented',arch:'invented',executable_sha256:'b'.repeat(64)},
 entry_executable:'/invented/node',owner_pid:12345,owner_start:'invented-owner-start',
 attempt:'owned-invented-entry',nonce_sha256:'c'.repeat(64),profile_sha256:'d'.repeat(64),
 producer_sha256:'e'.repeat(64),reader_identity:{invented:true},process_argv:['/invented/node','/invented/entry']};
const facts={pid:54321,ppid:12345,exec_path:grant.entry_executable,...grant.runtime,
 exec_argv:[],environment_keys:['LANG','LC_ALL','PATH'],environment:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'},
 producer_sha256:grant.producer_sha256,stdio:'unobserved',process_argv:grant.process_argv};
const raw=Buffer.from(JSON.stringify(grant)),at='2026-11-04T00:00:00.000Z';
let inherited=null;
if(extraFD){try{const s=fs.fstatSync(Number(extraFD),{bigint:true});inherited=[String(s.dev),String(s.ino)];}catch{}}
put('startup.json',{pid:process.pid,ppid:process.ppid,stdin_bytes:fs.readFileSync(0).length,
 environment:{...process.env},exec_argv:[...process.execArgv],extra_descriptor:inherited});
try{
 if(behavior==='closed-gate'){
  const trap=new Proxy({}, {get(){throw Error('packet touched');},ownKeys(){throw Error('packet touched');}});
  try{await handoffCurrentOnFixedChannels(Buffer.from('unknown'),trap,trap);throw Error('gate accepted');}
  catch(e){if(!e.message.includes('no reviewed observation grant'))throw e;}
 }else if(['oversize','bad-frame','no-eof'].includes(behavior)){
  await withFixedChannels(async(input,output)=>{
   input.resume();
   if(behavior==='no-eof'){
    output.write(encodeInvented(raw,facts,at));put('ready.json',{ready:true});
    setInterval(()=>{},50);await new Promise(()=>{});
   }else{
    await new Promise(resolve=>{output.on('error',resolve);output.end(
     behavior==='oversize'?Buffer.alloc(LIMIT+1,65):Buffer.from('wrong\n'),resolve);});
   }
  });
 }else{
  const result=await withFixedChannels((input,output)=>handoffInvented(raw,facts,at,input,output,{timeout_ms:400}));
  put('entry.json',{...result,frame_raw:result.frame_raw.toString('base64'),ack_raw:result.ack_raw.toString('base64')});
  process.stdout.write('owned-entry-stdout\n');process.stderr.write('owned-entry-stderr\n');
  if(behavior==='hang'&&result.status==='acknowledged'){
   put('ready.json',{ready:true});process.on('SIGTERM',()=>{});setInterval(()=>{},50);
  }
  else process.exitCode=result.status==='acknowledged'?0:23;
 }
}catch(e){process.stderr.write(String(e)+'\n');process.exitCode=1;}
