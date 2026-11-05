/** Fixed invented tooling-host fixture; never loads the selected Node/LT1 engine. */
import fs from 'node:fs';
import net from 'node:net';
import {spawn,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {once} from 'node:events';
import {withFixedChannels} from './entry_channels.mjs';
import {handoffInvented} from './entry_handoff.mjs';

const self=fileURLToPath(import.meta.url);
const [mode,input,output,outside,portRaw,nonce,profileSHA]=process.argv.slice(2);
const env={LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'};
const save=(name,value)=>{
 const fd=fs.openSync(output+'/'+name,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL,0o600);
 try{fs.writeFileSync(fd,JSON.stringify(value)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
};
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const denied=async operation=>{try{await operation();return {denied:false};}
 catch(e){return {denied:['EPERM','EACCES'].includes(e.code),code:e.code??null};}};
async function connect(){
 await new Promise((resolve,reject)=>{const socket=net.createConnection({host:'127.0.0.1',port:Number(portRaw)});
  socket.setTimeout(1000,()=>socket.destroy(Error('network control timeout')));
  socket.once('error',reject);socket.once('connect',()=>{socket.destroy();resolve();});});
}
function shell(){
 // Inherit descriptors; a failed /dev/null open must not masquerade as exec denial.
 const result=spawnSync('/bin/sh',['-c','exit 0'],{stdio:'inherit',env,timeout:1000});
 if(result.error)throw result.error;
 if(result.status!==0)throw Error('fixed shell did not exit zero');
}
async function observations(role){
 const writeRole=role==='control'?output.split('/').at(-1):role;
 const operations={outside_read:()=>fs.readFileSync(outside+'/secret.txt'),
  outside_write:()=>fs.writeFileSync(outside+'/'+writeRole+'-new.txt','invented outside write\n',{flag:'wx',mode:0o600}),
  network:connect,nonallowlisted_exec:shell};
 const checks={};for(const [name,operation] of Object.entries(operations))checks[name]=await denied(operation);
 checks.allowed_input=fs.readFileSync(input+'/invented.txt','utf8')==='invented input\n';
 const fd=fs.openSync(output+'/'+role+'-allowed.txt','wx',0o600);
 fs.writeFileSync(fd,'invented allowed write\n');fs.fsyncSync(fd);fs.closeSync(fd);
 checks.allowed_scratch=fs.readFileSync(output+'/'+role+'-allowed.txt','utf8')==='invented allowed write\n';
 checks.environment_keys=Object.keys(process.env).sort();
 checks.clean_declared_environment=Object.entries(env).every(([k,v])=>process.env[k]===v)&&
 checks.environment_keys.every(k=>Object.hasOwn(env,k)||(process.platform==='darwin'&&k==='__CF_USER_TEXT_ENCODING'));
 checks.pid=process.pid;checks.ppid=process.ppid;
 save(role+'-boundary.json',checks);return checks;
}
function groupPassed(checks,controlled){
 return ['outside_read','outside_write','network','nonallowlisted_exec']
 .every(k=>checks[k].denied===controlled&&(controlled||!Object.hasOwn(checks[k],'code')))&&
 checks.allowed_input&&checks.allowed_scratch&&checks.clean_declared_environment;
}
async function handshake(){
 const grant={schema:'opent1d.lt1-entry-observation-grant/1',
  packet_sha256:Object.fromEntries(['grant.json','integration-grant.json','integration_host_receipt.json',
  'plan.json','setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'].map(n=>[n,'a'.repeat(64)])),
  runtime:{node:'invented-tooling',platform:'invented',arch:'invented',executable_sha256:'b'.repeat(64)},
  entry_executable:'/invented/node',owner_pid:process.ppid,owner_start:'invented-tooling-owner',
  attempt:'tooling-host-'+mode,nonce_sha256:nonce,profile_sha256:profileSHA,
  producer_sha256:'c'.repeat(64),reader_identity:{invented:true},process_argv:['/invented/node','/invented/entry']};
 const facts={pid:process.pid,ppid:process.ppid,exec_path:grant.entry_executable,...grant.runtime,
  exec_argv:[],environment_keys:['LANG','LC_ALL','PATH'],environment:env,
  producer_sha256:grant.producer_sha256,stdio:'unobserved',process_argv:grant.process_argv};
 const result=await withFixedChannels((ack,frame)=>handoffInvented(Buffer.from(JSON.stringify(grant)),facts,
  new Date().toISOString(),ack,frame,{timeout_ms:2000}));
 save('handshake.json',{...result,frame_raw:result.frame_raw.toString('base64'),ack_raw:result.ack_raw.toString('base64')});
 if(result.status!=='acknowledged')throw Error('tooling-host handoff failed');
}
try{
 if(!['controls','complete','cancel','child-complete','child-cancel'].includes(mode))throw Error('fixed fixture mode required');
 const child=mode.startsWith('child-');
 if(!child&&mode!=='controls')await handshake();
 const checks=await observations(child?'child':mode==='controls'?'control':'parent');
 if(!groupPassed(checks,mode!=='controls')){process.exitCode=17;}
 else if(mode==='controls'){/* Successful unconfined operation twins are required. */}
 else if(child){
  if(mode==='child-cancel')process.on('SIGTERM',()=>{});
  save('child-ready.json',{pid:process.pid,ppid:process.ppid});
  const tick=()=>fs.writeFileSync(output+'/heartbeat.txt',String(process.hrtime.bigint()),{mode:0o600});
  tick();const timer=setInterval(tick,20);
  if(mode==='child-complete'){await pause(300);clearInterval(timer);}
 }else{
  if(mode==='cancel')process.on('SIGTERM',()=>{});
  const worker=spawn(process.execPath,[self,'child-'+mode,input,output,outside,portRaw,nonce,profileSHA],
   {stdio:['ignore','inherit','inherit'],env});
  const ended=once(worker,'exit');const until=Date.now()+3000;
  while(!fs.existsSync(output+'/child-ready.json')){
   if(worker.exitCode!==null||Date.now()>=until)throw Error('fixed tooling child not ready');await pause(10);}
  save('ready.json',{pid:process.pid,child_pid:worker.pid});
  if(mode==='complete'){
   const [code,signal]=await ended;if(code!==0||signal)throw Error('tooling child failed');
   save('completed.json',{kind:'invented',status:'completed'});
  }else setInterval(()=>{},50);
 }
}catch(e){process.stderr.write(String(e)+'\n');process.exitCode=1;}
