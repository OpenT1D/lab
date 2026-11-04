/** Fixed POSIX inherited sockets. No spawn, CLI, worker or native authority. */
import fs from 'node:fs';
import {Socket} from 'node:net';
import {collectCurrent} from './entry_observation.mjs';
import {handoffCurrent} from './entry_handoff.mjs';

const need=(ok,why)=>{if(!ok)throw Error('LT1 entry channels refused: '+why);};
const token=fd=>{
 const s=fs.fstatSync(fd,{bigint:true});
 return {key:s.dev+':'+s.ino,socket:s.isSocket()};
};
function own(stream){
 // Own close errors even if the callback destroys its endpoint before returning.
 // These guards retain no exchange data and have no timer or polling loop.
 const ignore=()=>{};
 stream.on('error',ignore);
 stream.once('close',()=>stream.removeListener('error',ignore));
 return stream;
}
function dispose(stream){
 if(!stream.destroyed)stream.destroy();
}

export async function withFixedChannels(exchange){
 // Trusted application callback, never selected by packet text or a command.
 need(typeof exchange==='function'&&process.platform!=='win32','trusted POSIX exchange');
 const ack=token(3),frame=token(4),stdio=[];
 for(const fd of [0,1,2]){
  try{stdio.push(token(fd).key);}catch(e){if(e.code!=='EBADF')throw e;}
 }
 need(ack.socket&&frame.socket&&ack.key!==frame.key&&
 !stdio.includes(ack.key)&&!stdio.includes(frame.key),'separate socket identities outside stdio');
 // Both identities are validated before either descriptor is adopted.
 let input,output;
 try{
  input=own(new Socket({fd:3,readable:true,writable:false}));
  output=own(new Socket({fd:4,readable:false,writable:true}));
  return await exchange(input,output);
 }finally{
  try{if(input)dispose(input);else fs.closeSync(3);}
  finally{if(output)dispose(output);else fs.closeSync(4);}
 }
}

export async function handoffCurrentOnFixedChannels(grantRaw,packet,options={}){
 // Admission and complete observation happen BEFORE fstat or descriptor adoption.
 // Handoff repeats its own admission/capture; both are outside its async budget.
 collectCurrent(grantRaw,packet);
 return withFixedChannels((input,output)=>handoffCurrent(grantRaw,packet,input,output,options));
}
