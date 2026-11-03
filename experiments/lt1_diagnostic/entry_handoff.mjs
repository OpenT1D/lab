/** One owned frame/ACK exchange. No launch, worker import, path selection or CLI. */
import {Readable,Writable} from 'node:stream';
import {performance} from 'node:perf_hooks';
import {MAGIC,LIMIT,digest,encodeInvented,collectCurrent} from './entry_observation.mjs';

export const ACK_MAGIC='OPENT1D-LT1-ACK-1\n';
export const ACK_LIMIT=1024;
export const CHUNK_LIMIT=64;
export const AUTHORITY=Object.freeze({native_host_qualified:false,native_acceptance:false,
 setup_admitted:false,native_execution_authorized:false,new_authority_granted:false,
 phase_verified:false,endpoint_identity_verified:false,stdio_verified:false,
 live_owner_revalidated:false,attempt_completion_checked:false,effective_erasure_verified:false});
const need=(ok,why)=>{if(!ok)throw Error('LT1 entry handoff refused: '+why);};
const sha=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const FRAME_FIELDS=['schema','kind','phase','observed_at','grant_sha256','attempt','nonce_sha256',
 'facts','native_host_qualified','native_acceptance','setup_admitted','native_execution_authorized'];

export function acknowledge(raw){
 need(Buffer.isBuffer(raw)&&raw.length>0&&raw.length<=LIMIT,'bounded frame');
 const text=new TextDecoder('utf-8',{fatal:true}).decode(raw),parts=text.split('\n');
 need(parts.length===3&&parts[0]===MAGIC.slice(0,-1)&&parts[2]==='','single frame EOF');
 const v=JSON.parse(parts[1]);
 need(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===FRAME_FIELDS.length&&
 FRAME_FIELDS.every(k=>Object.hasOwn(v,k))&&JSON.stringify(v)===parts[1],'canonical frame fields');
 need(v.schema==='opent1d.lt1-entry-observation/1'&&['invented','observed'].includes(v.kind)&&
 v.phase==='unqualified-current-process-observation'&&sha(v.grant_sha256)&&sha(v.nonce_sha256)&&
 typeof v.attempt==='string'&&/^[a-z0-9][a-z0-9-]{0,63}$/.test(v.attempt)&&
 ['native_host_qualified','native_acceptance','setup_admitted','native_execution_authorized']
 .every(k=>v[k]===false),'frame origin/binding/authority');
 return Buffer.from(ACK_MAGIC+JSON.stringify({schema:'opent1d.lt1-entry-ack/1',kind:v.kind,
 frame_sha256:digest(raw),grant_sha256:v.grant_sha256,attempt:v.attempt,
 nonce_sha256:v.nonce_sha256})+'\n');
}

function destroyEndpoint(stream,terminalObserved){
 // Closing itself can fail asynchronously. These tiny passive guards retain
 // only the endpoint, never the exchange/frame/peer. Unknown close stays unproved.
 if(!terminalObserved){
  const clear=()=>{stream.removeListener('error',clear);stream.removeListener('close',clear);};
  stream.once('error',clear);stream.once('close',clear);
 }
 try{stream.destroy();}catch{return false;}
 return true;
}

function transfer(frame,ackInput,frameOutput,options){
 // Trusted stream implementations; ownership starts only after all intake checks.
 need(options&&typeof options==='object'&&!Array.isArray(options)&&
 Object.keys(options).every(k=>['timeout_ms','signal'].includes(k)),'handoff options');
 const {timeout_ms=1000,signal}=options;
 need(Number.isSafeInteger(timeout_ms)&&timeout_ms>0&&timeout_ms<=30000,'finite handoff budget');
 need(signal===undefined||signal instanceof AbortSignal,'cancellation signal');
 need(ackInput instanceof Readable&&frameOutput instanceof Writable&&ackInput!==frameOutput&&
 ![process.stdin,process.stdout,process.stderr].includes(ackInput)&&
 ![process.stdin,process.stdout,process.stderr].includes(frameOutput)&&
 !ackInput.destroyed&&!ackInput.readableEnded&&!frameOutput.destroyed&&
 !frameOutput.writableEnded&&!frameOutput.writableFinished,'separate fresh owned endpoints');
 const expected=acknowledge(frame),kind=JSON.parse(frame.toString().split('\n')[1]).kind;
 const start=performance.now(),until=start+timeout_ms;
 let chunks=[],bytes=0,count=0,sent=false,eof=false,settled=false,writeAttempted=false;
 let readTerminal=false,writeTerminal=false;
 return new Promise(resolve=>{
  let timer;
  function finish(status,reason){
   if(settled)return;settled=true;
   clearTimeout(timer);signal?.removeEventListener('abort',cancelled);
   for(const [stream,event,handler] of listeners)stream.removeListener(event,handler);
   // These are exclusively transferred endpoints, never a process or caller log.
   const readDestroy=destroyEndpoint(ackInput,readTerminal);
   const writeDestroy=destroyEndpoint(frameOutput,writeTerminal);
   const ack=Buffer.concat(chunks,bytes);
   resolve({schema:'opent1d.lt1-entry-handoff/1',kind,status,reason,
    frame_raw:Buffer.from(frame),ack_raw:ack,frame_sha256:digest(frame),ack_sha256:digest(ack),
    frame_write_attempted:writeAttempted,frame_write_finished:sent,ack_eof:eof,
    elapsed_ms:performance.now()-start,endpoint_destroy_requested:true,
    synchronous_destroy_error:!readDestroy||!writeDestroy,
    endpoint_close_verified:false,...AUTHORITY});
  }
  function expired(){if(performance.now()>=until){finish('timeout','handoff-deadline');return true;}return false;}
  function complete(){
   if(settled||expired()||!sent||!eof)return;
   finish(Buffer.concat(chunks,bytes).equals(expected)?'acknowledged':'failed',
    Buffer.concat(chunks,bytes).equals(expected)?null:'acknowledgment-bytes');
  }
  function data(value){
   if(settled)return;
   if(!Buffer.isBuffer(value)&&!(value instanceof Uint8Array)){finish('failed','byte-channel-required');return;}
   const room=ACK_LIMIT-bytes,take=Math.min(room,value.byteLength);
   if(take){chunks.push(Buffer.from(value.subarray(0,take)));bytes+=take;}
   count+=1;
   if(value.byteLength>room||count>CHUNK_LIMIT){finish('failed','acknowledgment-bound');return;}
   expired();
  }
  function ended(){eof=true;complete();}
  function flushed(){sent=true;complete();}
  function failed(){
   if(this===ackInput&&this.destroyed)readTerminal=true;
   if(this===frameOutput&&this.destroyed)writeTerminal=true;
   finish('failed','channel-error');
  }
  function readClosed(){readTerminal=true;if(!eof)finish('failed','premature-ack-close');}
  function writeClosed(){writeTerminal=true;if(!sent)finish('failed','premature-frame-close');}
  function cancelled(){finish('cancelled','handoff-cancelled');}
  const listeners=[[ackInput,'data',data],[ackInput,'end',ended],[ackInput,'error',failed],
   [ackInput,'close',readClosed],[frameOutput,'finish',flushed],[frameOutput,'error',failed],
   [frameOutput,'close',writeClosed]];
  for(const [stream,event,handler] of listeners)stream.on(event,handler);
  signal?.addEventListener('abort',cancelled,{once:true});
  timer=setTimeout(()=>finish('timeout','handoff-deadline'),timeout_ms);
  if(signal?.aborted){cancelled();return;}
  try {writeAttempted=true;frameOutput.end(Buffer.from(frame));}catch{failed();}
 });
}

export function handoffInvented(grantRaw,facts,at,ackInput,frameOutput,options={}){
 return transfer(encodeInvented(grantRaw,facts,at),ackInput,frameOutput,options);
}
export function handoffCurrent(grantRaw,packet,ackInput,frameOutput,options={}){
 // No endpoint/options intake or handoff timer precedes the production gate.
 // Capture is synchronous and outside the asynchronous handoff time budget.
 return transfer(collectCurrent(grantRaw,packet),ackInput,frameOutput,options);
}
