/** Actual fixed entry v2. The private startup carrier never appears in argv. */
import fs from 'node:fs';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {registry,admit,decoded,validate,checkSources,digest,same,fields,need,ROOT,PACKET,ENV} from './native_route_contract.mjs';
import {withFixedChannels} from './entry_channels.mjs';
import {collectCurrent,encodeInvented} from './native_route_observation.mjs';
import {handoffInvented,handoffCurrent} from './native_route_handoff.mjs';
const CARRIER='OPENT1D_LT1_ROUTE_CONTROL';
function readPacket(folder){
 const path=resolve(folder),root=fs.lstatSync(path,{bigint:true});
 need(fs.realpathSync(path)===path&&root.isDirectory()&&!root.isSymbolicLink()&&root.uid===BigInt(process.getuid())&&(root.mode&0o777n)===0o500n,'frozen packet root');
 need(same(fs.readdirSync(path).sort(),[...PACKET].sort()),'closed packet namespace');
 const result={};let total=0;
 for(const name of PACKET){
  const file=join(path,name),fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  try{
   const a=fs.fstatSync(fd,{bigint:true});
   need(a.isFile()&&a.nlink===1n&&a.uid===BigInt(process.getuid())&&[0o400n,0o600n].includes(a.mode&0o777n)&&a.size<=4n*1024n*1024n,'private bounded packet member');
   const raw=fs.readFileSync(fd),b=fs.fstatSync(fd,{bigint:true}),c=fs.lstatSync(file,{bigint:true});
   const sig=s=>[s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs,s.mode,s.nlink].join(':');
   need(raw.length===Number(a.size)&&sig(a)===sig(b)&&sig(b)===sig(c)&&!c.isSymbolicLink(),'packet member changed');
   total+=raw.length;need(total<=32*1024*1024,'packet aggregate');result[name]=Buffer.from(raw);
  }finally{fs.closeSync(fd);}
 }
 const end=fs.lstatSync(path,{bigint:true});need(end.dev===root.dev&&end.ino===root.ino&&end.mode===root.mode,'packet root rebound');
 return result;
}
function consume(invented,authority,authorityHash){
 const startup=Object.keys(process.env).sort();
 need(same(startup,[...Object.keys(ENV),CARRIER,...(Object.hasOwn(process.env,'__CF_USER_TEXT_ENCODING')?['__CF_USER_TEXT_ENCODING']:[])].sort())&&Object.keys(ENV).every(k=>process.env[k]===ENV[k]),'exact four-key startup environment');
 const raw=process.env[CARRIER];need(typeof raw==='string'&&Buffer.byteLength(raw)<=65536&&raw.length>0,'64KiB carrier');
 const control=JSON.parse(raw);fields(control,['schema','entry','observation','audit','bootstrap']);
 need(control.schema==='opent1d.lt1-route-carrier/2'&&typeof control.entry==='string'&&typeof control.observation==='string','carrier schema');
 const entryRaw=Buffer.from(control.entry),observationRaw=Buffer.from(control.observation);
 if(invented){
  const e=decoded(entryRaw);
  authority=registry({schema:'opent1d.lt1-native-admissions/1',setup:[e.setup_sha256],execution:[digest(entryRaw),digest(observationRaw),e.engine_sha256,e.integration_sha256]});
 }
 admit(entryRaw,observationRaw,authority,invented);
 // Own the source context, then remove the carrier before the old collector.
 const audit=JSON.parse(JSON.stringify(control.audit)),entry=decoded(entryRaw);
 delete process.env[CARRIER];
 need(same(Object.keys(process.env).sort(),Object.keys(entry.kind==='invented'?JSON.parse(control.observation).runtime_environment:JSON.parse(control.observation).runtime_environment).sort()),'explicit post-clear runtime environment');
 const expected={source_identity:audit,profile_sha256:entry.profile_sha256,process_argv:[...entry.process_argv]};
 checkSources(entry.entry_sources,expected,authorityHash);
 const args=process.argv.slice(2);
 need(same(process.argv,entry.process_argv)&&same(args,['staging','packet','output'].map(k=>entry.roots[k])),'fixed actual CLI argv');
 const packet=readPacket(entry.roots.packet);
 validate(entryRaw,observationRaw,packet,args,expected,authority,invented,authorityHash);
 const host=decoded(packet['integration_host_receipt.json']);
 for(const [key,value]of Object.entries(host.roots)){
  const stat=fs.lstatSync(value.path,{bigint:true});
  need(value.path===entry.roots[key]&&fs.realpathSync(value.path)===value.path&&same(value.identity,[Number(stat.dev),Number(stat.ino),Number(stat.uid),Number(stat.mode&0o7777n)])&&value.identity.every(Number.isSafeInteger),'bound physical root');
 }
 return {entryRaw,observationRaw,entry,observation:decoded(observationRaw),packet,args,expected,authority,authorityHash,startup,bootstrap:control.bootstrap};
}
async function execute(invented,authority,authorityHash){
 const state=consume(invented,authority,authorityHash),{entry,observation}=state;
 const abort=new AbortController();state.signal=abort.signal;const stop=()=>abort.abort();process.on('SIGTERM',stop);process.on('SIGINT',stop);
 let exchange,worker=null;
 try{
  const options={timeout_ms:Math.min(30000,decoded(state.packet['integration_host_receipt.json']).timeout_seconds*1000),signal:abort.signal};
  if(invented){
   const facts={pid:process.pid,ppid:process.ppid,exec_path:process.execPath,node:process.version,platform:process.platform,arch:process.arch,
    executable_sha256:digest(fs.readFileSync(process.execPath)),producer_sha256:observation.producer_sha256,
    process_argv:[...process.argv],exec_argv:[...process.execArgv],environment_keys:Object.keys(process.env).sort(),environment:{...process.env},startup_environment_keys:[...state.startup],stdio:'unobserved'};
   encodeInvented(state.observationRaw,facts,new Date().toISOString());
   exchange=await withFixedChannels((input,output)=>handoffInvented(state.observationRaw,facts,new Date().toISOString(),input,output,options));
  }else{collectCurrent(state.observationRaw,state.packet,state.startup);exchange=await withFixedChannels((input,output)=>handoffCurrent(state.observationRaw,state.packet,state.startup,input,output,options));}
  if(exchange.status==='acknowledged'&&entry.case_id==='C17'&&entry.slot==='after-ack-cancel')abort.abort();
  if(exchange.status==='acknowledged'&&!abort.signal.aborted){
   checkSources(entry.entry_sources,state.expected,authorityHash);need(process.ppid===entry.owner_pid,'owner changed after ACK');
   const fixed=await import('./native_route_worker.mjs');
   checkSources(entry.entry_sources,state.expected,authorityHash);need(process.ppid===entry.owner_pid,'owner changed during worker import');
   if(!abort.signal.aborted)worker=await (invented?fixed.runInvented:fixed.runNative)(state);
  }
  const report={schema:'opent1d.lt1-native-route-child/2',kind:entry.kind,pid:process.pid,ppid:process.ppid,
   startup_environment_keys:state.startup,post_clear_environment_keys:Object.keys(observation.runtime_environment).sort(),bootstrap:state.bootstrap,
   startup_confinement_qualified:false,frame_sha256:digest(exchange.frame_raw??Buffer.alloc(0)),ack_sha256:digest(exchange.ack_raw??Buffer.alloc(0)),
   exchange_status:exchange.status,worker,case_id:entry.case_id,slot:entry.slot,native_acceptance:false,native_execution_authorized:false};
  fs.writeFileSync(join(entry.roots.output,'route.json'),JSON.stringify(report),{flag:'wx',mode:0o600});
  if(exchange.status!=='acknowledged'||!worker?.completed)process.exitCode=1;
  return report;
 }finally{process.removeListener('SIGTERM',stop);process.removeListener('SIGINT',stop);}
}
export async function mainNative(){
 const raw=fs.readFileSync(new URL('./native-admissions.json',import.meta.url));
 const authority=registry(JSON.parse(raw));need(authority.setup.length&&authority.execution.length,'no reviewed route grants');
 return execute(false,authority,digest(raw));
}
export async function mainInvented(){return execute(true);}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{await mainNative();}catch(error){process.stderr.write(String(error)+'\n');process.exitCode=1;}
}
