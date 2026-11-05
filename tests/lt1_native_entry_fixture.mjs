/** Ordinary tooling Node and fixed invented continuation; never a native delegate. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Socket} from 'node:net';
import {fileURLToPath} from 'node:url';
import {continueNativeEntry,continueInventedEntry} from '../experiments/lt1_diagnostic/native_entry.mjs';
const [mode,folder]=process.argv.slice(2);
const put=(name,value)=>fs.writeFileSync(folder+'/'+name,JSON.stringify(value)+'\n',{flag:'wx',mode:0o600});
const descriptor=fd=>{try{const s=fs.fstatSync(fd,{bigint:true});return {key:s.dev+':'+s.ino,socket:s.isSocket(),regular:s.isFile()};}catch(e){return {error:e.code};}};
put('startup.json',{pid:process.pid,ppid:process.ppid,exec_path:process.execPath,node:process.version,
 argv:[...process.argv],environment:{...process.env},exec_argv:[...process.execArgv],
 descriptors:Object.fromEntries([0,1,2,3,4].map(fd=>[fd,descriptor(fd)]))});
let restore=()=>{};
try{
 if(mode==='closed-gate'||mode==='nonempty-unreviewed'){
  const trap=new Proxy({}, {get(){throw Error('caller intake');},ownKeys(){throw Error('caller intake');}});
  const oldRead=fs.readFileSync,oldStat=fs.fstatSync;
  fs.readFileSync=(path,...args)=>{if(!String(path).endsWith('/native-admissions.json'))throw Error('private path intake');
   if(mode==='nonempty-unreviewed')return JSON.stringify({schema:'opent1d.lt1-native-admissions/1',setup:['a'.repeat(64)],execution:['b'.repeat(64)]});
   return oldRead(path,...args);};
  fs.fstatSync=()=>{throw Error('descriptor intake');};
  restore=()=>{fs.readFileSync=oldRead;fs.fstatSync=oldStat;};
  try{await continueNativeEntry(mode==='closed-gate'?trap:Buffer.from('{}'),mode==='closed-gate'?trap:Buffer.from('{}'),trap,trap,trap,trap);throw Error('gate accepted');}
  catch(error){if(!error.message.includes(mode==='closed-gate'?'no reviewed entry continuation grant':'exact entry/observation membership'))throw error;}
  restore();put('entry.json',{status:'gate-refused',continuation_count:0});
 }else{
  const payload=JSON.parse(fs.readFileSync(folder+'/payload.json','utf8'));
  const entry=Buffer.from(payload.entry,'base64'),observation=Buffer.from(payload.observation,'base64');
  const packet=Object.fromEntries(Object.entries(payload.packet).map(([name,value])=>[name,Buffer.from(value,'base64')]));
  const args=payload.args,expected=payload.expected,options={timeout_ms:400};
  if(['declared-unreviewed','native-before-fd','early-buffer-mutation','actual-packet-unreviewed'].includes(mode)){
   const h=value=>createHash('sha256').update(value).digest('hex');
   const declared=JSON.parse(entry);
   const fake={schema:'opent1d.lt1-native-admissions/1',setup:[mode==='declared-unreviewed'?'f'.repeat(64):declared.setup_sha256],
    execution:[h(entry),h(observation),declared.engine_sha256,declared.integration_sha256]};
   const oldRead=fs.readFileSync,oldStat=fs.fstatSync,oldOpen=fs.openSync,oldArgv=process.argv;
   const oldReadSync=fs.readSync,oldLstat=fs.lstatSync,oldClose=fs.closeSync;
   const virtual=Buffer.from(JSON.stringify(fake)),virtualFD=new Map();
   if(mode==='native-before-fd')expected.source_identity.implementation['experiments/lt1_diagnostic/native-admissions.json']=h(virtual);
   const trap=new Proxy({}, {get(){throw Error('caller intake');},ownKeys(){throw Error('caller intake');}});
   fs.readFileSync=(path,...rest)=>{if(String(path).endsWith('/native_entry_sources.json'))return oldRead(path,...rest);
    if(!String(path).endsWith('/native-admissions.json'))throw Error('private path intake');return virtual.toString();};
   const virtualStat=s=>new Proxy(s,{get(target,key){if(key==='size')return typeof target.size==='bigint'?BigInt(virtual.length):virtual.length;const v=Reflect.get(target,key);return typeof v==='function'?v.bind(target):v;}});
   fs.fstatSync=(fd,...rest)=>{if(fd===3||fd===4)throw Error('descriptor intake');const value=oldStat(fd,...rest);return virtualFD.has(fd)?virtualStat(value):value;};
   const publicRoot=new URL('../',import.meta.url).pathname;
   fs.openSync=(name,...rest)=>{const path=name instanceof URL?fileURLToPath(name):String(name);
    if(!path.startsWith(publicRoot))throw Error('private executable intake');
    const fd=oldOpen(name,...rest);if(path.endsWith('/native-admissions.json'))virtualFD.set(fd,0);return fd;};
   fs.readSync=(fd,buffer,offset,length,position)=>{
    if(!virtualFD.has(fd))return oldReadSync(fd,buffer,offset,length,position);
    const at=position===null?virtualFD.get(fd):position,n=Math.min(length,virtual.length-at);
    if(n>0)virtual.copy(buffer,offset,at,at+n);virtualFD.set(fd,at+n);return n;
   };
   fs.lstatSync=(path,...rest)=>{const value=oldLstat(path,...rest);return String(path).endsWith('/native-admissions.json')?virtualStat(value):value;};
   fs.closeSync=fd=>{virtualFD.delete(fd);return oldClose(fd);};
   if(mode==='native-before-fd')process.argv=[...declared.process_argv];
   restore=()=>{fs.readFileSync=oldRead;fs.fstatSync=oldStat;fs.openSync=oldOpen;fs.readSync=oldReadSync;fs.lstatSync=oldLstat;fs.closeSync=oldClose;process.argv=oldArgv;};
   const earlyOptions={};
   if(mode==='early-buffer-mutation')Object.defineProperty(earlyOptions,'signal',{enumerable:true,get(){entry[1]^=1;return undefined;}});
   if(mode==='actual-packet-unreviewed')packet['grant.json']=Buffer.from('unreviewed actual engine');
   try{await continueNativeEntry(entry,observation,['native-before-fd','actual-packet-unreviewed'].includes(mode)?packet:trap,
    mode==='native-before-fd'?args:trap,mode==='native-before-fd'?expected:trap,
    ['native-before-fd','actual-packet-unreviewed'].includes(mode)?{}:mode==='early-buffer-mutation'?earlyOptions:trap);throw Error('gate accepted');}
   catch(error){const reason=mode==='native-before-fd'?'current process identity':mode==='early-buffer-mutation'?'API grant bytes changed before packet intake':mode==='actual-packet-unreviewed'?'exact engine/integration/setup memberships':'exact declared engine/integration/setup membership';if(!error.message.includes(reason))throw error;}
   restore();put('entry.json',{status:'gate-refused',continuation_count:0});
  }else{
  let timer;
  if(mode==='cancel'){
   const stop=new AbortController();options.signal=stop.signal;timer=setTimeout(()=>stop.abort(),50);
  }else if(mode==='mutate-args')timer=setTimeout(()=>{args[0]='/invented/changed';},50);
  else if(mode==='mutate-buffer')timer=setTimeout(()=>{entry[1]^=1;},50);
  else if(mode==='mutate-source-map')timer=setTimeout(()=>{expected.source_identity.implementation['experiments/lt1_diagnostic/native_entry.mjs']='a'.repeat(64);},50);
  else if(mode==='switch-signal'){
   options.signal=new AbortController().signal;
   timer=setTimeout(()=>{options.signal=new AbortController().signal;},50);
  }else if(mode==='late-abort'){
   const stop=new AbortController();options.signal=stop.signal;
   const emit=Socket.prototype.emit;
   Socket.prototype.emit=function(event,...args){
    const ackEnd=event==='end'&&this._handle?.fd===3;
    const result=emit.call(this,event,...args);
    if(ackEnd)stop.abort();
    return result;
   };
   restore=()=>{Socket.prototype.emit=emit;};
  }
  if(mode==='source-after-ack'){
   const oldOpen=fs.openSync,oldRead=fs.readSync,oldClose=fs.closeSync;
   const targets=new Set();let opened=0;
   fs.openSync=(name,...rest)=>{const fd=oldOpen(name,...rest);if(String(name).endsWith('/native_entry.mjs')&&++opened===2)targets.add(fd);return fd;};
   fs.readSync=(fd,buffer,...rest)=>{const count=oldRead(fd,buffer,...rest);if(count&&targets.has(fd)){buffer[0]^=1;targets.delete(fd);}return count;};
   fs.closeSync=fd=>{targets.delete(fd);return oldClose(fd);};
   restore=()=>{fs.openSync=oldOpen;fs.readSync=oldRead;fs.closeSync=oldClose;};
  }
  try{
   const result=await continueInventedEntry(entry,observation,packet,args,expected,options);
   put('entry.json',{...result,frame_raw:result.frame_raw.toString('base64'),ack_raw:result.ack_raw.toString('base64')});
   process.exitCode=result.continuation_count===1?0:23;
  }finally{clearTimeout(timer);restore();}
  }
 }
}catch(error){restore();put('entry.json',{status:'refused',reason:String(error),continuation_count:0});process.exitCode=23;}
