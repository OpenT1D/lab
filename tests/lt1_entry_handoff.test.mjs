/** Tooling Node and invented in-memory streams only; no native launch. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {PassThrough,Writable} from 'node:stream';
import {test} from 'node:test';
import {performance} from 'node:perf_hooks';
import {encodeInvented,digest} from '../experiments/lt1_diagnostic/entry_observation.mjs';
import {handoffInvented,handoffCurrent,acknowledge,ACK_MAGIC,ACK_LIMIT,AUTHORITY}
 from '../experiments/lt1_diagnostic/entry_handoff.mjs';
if(process.argv.includes('--ack')){
 process.stdout.write(acknowledge(fs.readFileSync(0)));
}else{
 const grant={schema:'opent1d.lt1-entry-observation-grant/1',
 packet_sha256:Object.fromEntries(['grant.json','integration-grant.json','integration_host_receipt.json',
 'plan.json','setup_receipt.json','host_receipt.json','rights_receipt.json','security_receipt.json'].map(k=>[k,'a'.repeat(64)])),
 runtime:{node:'v22.23.4',platform:'darwin',arch:'arm64',executable_sha256:'b'.repeat(64)},
 entry_executable:'/invented/stage/runtime/bin/node',owner_pid:12345,owner_start:'darwin:1:2',
 attempt:'invented-handoff',nonce_sha256:'c'.repeat(64),profile_sha256:'d'.repeat(64),
 producer_sha256:'e'.repeat(64),reader_identity:{invented:true},
 process_argv:['/invented/stage/runtime/bin/node','/invented/entry.mjs']};
 const facts={pid:54321,ppid:12345,exec_path:grant.entry_executable,...grant.runtime,
 exec_argv:[],environment_keys:['LANG','LC_ALL','PATH'],environment:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'},
 producer_sha256:grant.producer_sha256,stdio:'unobserved',process_argv:grant.process_argv};
 const raw=Buffer.from(JSON.stringify(grant)),at='2026-11-04T00:00:00.000Z';
 const frame=encodeInvented(raw,facts,at),ack=acknowledge(frame);
 const pair=()=>({input:new PassThrough(),output:new PassThrough({highWaterMark:1})});
 const run=(p,options={})=>handoffInvented(raw,facts,at,p.input,p.output,{timeout_ms:100,...options});
 const falseFlags=result=>{for(const k of Object.keys(AUTHORITY))assert.equal(result[k],false,k);};
 async function receive(p,answer){
  const parts=[];for await(const value of p.output)parts.push(value);
  assert.deepEqual(Buffer.concat(parts),frame);answer(p.input);
 }
 test('separate channels drain a fragmented ACK and EOF with backpressure',async()=>{
  const p=pair(),peer=receive(p,s=>{for(let n=0;n<ack.length;n+=16)s.write(ack.subarray(n,n+16));s.end();});
  // A caller's extra argument cannot promote invented origin.
  const result=await handoffInvented(raw,facts,at,p.input,p.output,{timeout_ms:1000},'observed');
  await peer;assert.equal(result.status,'acknowledged');assert.equal(result.kind,'invented');
  assert.deepEqual(result.ack_raw,ack);assert.equal(result.frame_sha256,digest(frame));
  assert.equal(result.ack_eof,true);assert.equal(result.frame_write_finished,true);falseFlags(result);
  assert.equal(p.input.destroyed,true);assert.equal(p.output.destroyed,true);
 });
 test('complete ACK without EOF never acknowledges',async()=>{
  const p=pair(),peer=receive(p,s=>s.write(ack));const r=await run(p,{timeout_ms:30});await peer;
  assert.equal(r.status,'timeout');assert.equal(r.ack_eof,false);assert.deepEqual(r.ack_raw,ack);falseFlags(r);
 });
 test('missing ACK and blocked frame writes meet the handoff deadline',async()=>{
  const p=pair(),r=await run(p,{timeout_ms:20});assert.equal(r.status,'timeout');
  assert.equal(r.frame_write_attempted,true);assert.equal(r.frame_write_finished,false);
  assert.equal(r.ack_raw.length,0);assert.equal(p.output.destroyed,true);
 });
 test('wrong frame/grant/nonce/attempt/kind refuse even with complete EOF',async()=>{
  for(const key of ['frame_sha256','grant_sha256','nonce_sha256','attempt','kind']){
   const p=pair(),v=JSON.parse(ack.toString().split('\n')[1]);v[key]='wrong';
   const changed=Buffer.from(ACK_MAGIC+JSON.stringify(v)+'\n');
   const peer=receive(p,s=>s.end(changed)),r=await run(p);await peer;
   assert.equal(r.status,'failed',key);assert.equal(r.reason,'acknowledgment-bytes');falseFlags(r);
  }
 });
 test('torn, extra, duplicate, noncanonical and invalid UTF8 ACK bytes refuse',async()=>{
  const line=ack.toString(),variants=[ack.subarray(0,-1),Buffer.concat([ack,ack]),
   Buffer.from(line.replace('"kind":"invented"','"kind":"observed","kind":"invented"')),
   Buffer.from(line.replace('{','{ ')),Buffer.from([0xff])];
  for(const changed of variants){const p=pair(),peer=receive(p,s=>s.end(changed));
   const r=await run(p);await peer;assert.equal(r.status,'failed');falseFlags(r);}
 });
 test('oversized acknowledgment retains only a bounded prefix',async()=>{
  const p=pair(),peer=receive(p,s=>s.end(Buffer.alloc(ACK_LIMIT+1,65))),r=await run(p);await peer;
  assert.equal(r.reason,'acknowledgment-bound');assert.equal(r.ack_raw.length,ACK_LIMIT);
 });
 test('chunk budget refuses a small endless fragmented stream',async()=>{
  const p=pair(),peer=receive(p,s=>{for(let n=0;n<65&&!s.destroyed;n++)s.write(Buffer.from('x'));});
  const r=await run(p);await peer;assert.equal(r.reason,'acknowledgment-bound');assert.equal(r.ack_raw.length,65);
 });
 test('cancellation before write and after partial ACK retains evidence',async()=>{
  let p=pair(),c=new AbortController();c.abort();let r=await run(p,{signal:c.signal});
  assert.equal(r.status,'cancelled');assert.equal(r.frame_write_attempted,false);
  p=pair();c=new AbortController();const peer=receive(p,s=>{s.write(ack.subarray(0,12));c.abort();});
  r=await run(p,{signal:c.signal});await peer;assert.equal(r.status,'cancelled');assert.equal(r.ack_raw.length,12);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(p.input.listenerCount('data'),0);assert.equal(p.input.listenerCount('error'),0);falseFlags(r);
 });
 test('stream errors and premature close preserve bounded prefixes',async()=>{
  for(const mode of ['error','close']){const p=pair(),peer=receive(p,s=>{
   s.write(ack.subarray(0,10));mode==='error'?s.destroy(new Error('invented')):s.destroy();});
   const r=await run(p);await peer;assert.equal(r.status,'failed');assert.equal(r.ack_raw.length,10);falseFlags(r);}
 });
 test('an I/O error during endpoint destruction stays owned',async()=>{
  const p=pair(),c=new AbortController();c.abort();
  p.input._destroy=(_error,done)=>done(new Error('invented close failure'));
  const r=await run(p,{signal:c.signal});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(r.status,'cancelled');assert.equal(p.input.listenerCount('error'),0);
  assert.equal(p.input.listenerCount('close'),0);
 });
 test('a sink may not mutate the retained intended frame and ACK binding',async()=>{
  const p=pair();p.output=new Writable({write(chunk,_encoding,done){
   const received=Buffer.from(chunk);chunk.fill(0);p.input.end(acknowledge(received));done();}});
  const r=await run(p);
  assert.equal(r.status,'acknowledged');assert.deepEqual(r.frame_raw,frame);
  assert.equal(r.frame_sha256,digest(frame));assert.deepEqual(r.ack_raw,ack);
 });
 test('delayed destroy errors are consumed even without close events',async()=>{
  const p=pair(),c=new AbortController();c.abort();p.input=new PassThrough({emitClose:false});
  p.input._destroy=(_error,done)=>setTimeout(()=>done(new Error('delayed close failure')),15);
  const r=await run(p,{signal:c.signal});assert.equal(r.status,'cancelled');
  await new Promise(resolve=>setTimeout(resolve,30));
  assert.equal(p.input.listenerCount('error'),0);assert.equal(p.input.listenerCount('close'),0);
 });
 test('a silent endpoint cannot force a cleanup poller or closure claim',async()=>{
  const p=pair(),c=new AbortController();c.abort();p.input._destroy=()=>{};
  const r=await run(p,{signal:c.signal});assert.equal(r.status,'cancelled');
  assert.equal(r.endpoint_close_verified,false);assert.equal(p.input.closed,false);falseFlags(r);
  // The bounded passive guard consumes a later terminal report without a timer.
  p.input.emit('error',new Error('later terminal report'));
  assert.equal(p.input.listenerCount('error'),0);assert.equal(p.input.listenerCount('close'),0);
 });
 test('text-decoded ACK endpoints refuse',async()=>{
  const p=pair();p.input.setEncoding('utf8');const peer=receive(p,s=>s.end(ack)),r=await run(p);await peer;
  assert.equal(r.reason,'byte-channel-required');
 });
 test('invalid budgets, shared endpoints and process stdio do not take ownership',()=>{
  for(const options of [{timeout_ms:0},{timeout_ms:Infinity},{timeout_ms:'10'},{other:true}]){
   const p=pair();assert.throws(()=>run(p,options));assert.equal(p.input.destroyed,false);p.input.destroy();p.output.destroy();}
  const p=pair();assert.throws(()=>handoffInvented(raw,facts,at,p.input,p.input));
  assert.throws(()=>handoffInvented(raw,facts,at,p.input,process.stdout));
  assert.equal(p.input.destroyed,false);p.input.destroy();p.output.destroy();
 });
 test('closed production gate does not inspect endpoints, packet or options',()=>{
  const trap=new Proxy({}, {get(){throw Error('endpoint touched');},ownKeys(){throw Error('packet touched');}});
  assert.throws(()=>handoffCurrent(Buffer.from('unknown'),trap,trap,trap,trap),/no reviewed observation grant/);
 });
 test('all process stdio references refuse in either endpoint position',async()=>{
  const accepted=[];
  for(const name of ['stdin','stdout','stderr'])for(const position of ['input','output']){
   const descriptor=Object.getOwnPropertyDescriptor(process,name),fake=new PassThrough(),p=pair();
   // Substitute only a fresh in-memory reference during synchronous intake.
   // Restore real stdio before any asynchronous work or test-harness reporting.
   let result,error;
   Object.defineProperty(process,name,{value:fake,configurable:true});
   try{result=run({...p,[position]:fake},{timeout_ms:5});}catch(e){error=e;}
   finally{Object.defineProperty(process,name,descriptor);}
   if(result){await result;accepted.push(name+':'+position);}
   else assert.match(error.message,/owned endpoints/);
   fake.destroy();p.input.destroy();p.output.destroy();
  }
  assert.deepEqual(accepted,[]);
 });
 test('late event-loop ACK cannot beat elapsed monotonic budget',async()=>{
  const p=pair();p.output.resume();const promise=run(p,{timeout_ms:20});
  const until=performance.now()+35;while(performance.now()<until){}
  p.input.end(ack);const r=await promise;assert.equal(r.status,'timeout');falseFlags(r);
 });
 test('ACK helper refuses torn frames and promoted authority',()=>{
  assert.throws(()=>acknowledge(frame.subarray(0,-1)));
  assert.throws(()=>acknowledge(Buffer.from(frame.toString().replace('"native_acceptance":false','"native_acceptance":true'))));
 });
}
