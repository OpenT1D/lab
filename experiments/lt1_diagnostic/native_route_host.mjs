/** Source-fixed C19 operations. No packet paths, targets or policy selectors. */
import fs from 'node:fs';
import net from 'node:net';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const need=(ok,why)=>{if(!ok)throw Error('C19 fixed probe refused: '+why);};
export const PORT=57321;
const name={output_read:'c19-allowed-read.txt',output_write:'c19-allowed-write.txt',evidence_read:'c19-denied-read.txt',evidence_write:'c19-denied-write.txt'};
export const writeBytes=(entry)=>Buffer.from('opent1d-c19-write:'+entry.slot+':'+entry.nonce_sha256+'\n');
export const challenge=(entry)=>Buffer.from('opent1d-c19:'+entry.slot+':'+entry.nonce_sha256+'\n');
const failed=(error)=>({status:'error',error_code:typeof error?.code==='string'?error.code.slice(0,64):'UNKNOWN',sha256:null});
function fileOperation(entry,operation){
 const path=join(entry.roots[operation.startsWith('output')?'output':'evidence'],name[operation]);let fd;
 try{
  fd=fs.openSync(path,(operation.endsWith('read')?fs.constants.O_RDONLY:fs.constants.O_WRONLY)|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  const before=fs.fstatSync(fd,{bigint:true});
  need(before.isFile()&&before.nlink===1n&&before.uid===BigInt(process.getuid())&&(before.mode&0o777n)===0o600n&&before.size<=4096n,'fixed C19 canary');
  let data;
  if(operation.endsWith('read'))data=fs.readFileSync(fd);
  else{data=writeBytes(entry);let written=0;while(written<data.length){const n=fs.writeSync(fd,data,written,data.length-written,null);need(n>0,'C19 write progress');written+=n;}fs.ftruncateSync(fd,data.length);fs.fsyncSync(fd);}
  const after=fs.fstatSync(fd,{bigint:true}),named=fs.lstatSync(path,{bigint:true});
  need(after.dev===before.dev&&after.ino===before.ino&&named.dev===after.dev&&named.ino===after.ino&&!named.isSymbolicLink()&&named.nlink===1n,'C19 canary identity');
  return {status:'ok',error_code:null,sha256:digest(data)};
 }catch(error){return failed(error);}finally{if(fd!==undefined)fs.closeSync(fd);}
}
async function network(entry,signal){
 const sent=challenge(entry),expected=Buffer.from('ack:'+digest(sent)+'\n');
 return new Promise(resolve=>{
  let data=Buffer.alloc(0),settled=false;
  const socket=new net.Socket();
  const done=result=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);socket.destroy();resolve(result);};
  const abort=()=>done(failed({code:'ABORT_ERR'}));
  const timer=setTimeout(()=>done(failed({code:'ETIMEDOUT'})),1500);
  socket.on('error',error=>done(failed(error)));
  socket.on('connect',()=>socket.end(sent));
  socket.on('data',part=>{data=Buffer.concat([data,part]);if(data.length>128)done(failed({code:'BAD_REPLY'}));});
  socket.on('end',()=>done(data.equals(expected)?{status:'ok',error_code:null,sha256:digest(data)}:failed({code:'BAD_REPLY'})));
  signal?.addEventListener('abort',abort,{once:true});
  if(signal?.aborted)abort();else socket.connect({host:'127.0.0.1',port:PORT});
 });
}
export async function probe(entry,signal){
 need(entry.case_id==='C19'&&['base','allow-twin'].includes(entry.slot),'fixed host probe slot');
 const operations={};
 for(const operation of Object.keys(name))operations[operation]=fileOperation(entry,operation);
 operations.loopback=await network(entry,signal);
 return {schema:'opent1d.lt1-c19-operations/1',kind:entry.kind,slot:entry.slot,nonce_sha256:entry.nonce_sha256,
  completed:true,operations,native_host_qualified:false};
}
