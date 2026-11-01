import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,mkdirSync,rmSync,realpathSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
import {verifyIntegration,INTEGRATION_FILES} from '../experiments/lt1_diagnostic/integration_gate.mjs';
import {digest,WORKER_FILES,ENTRIES,REVISION} from '../experiments/lt1_diagnostic/native_loader.mjs';
import {AttemptJournal} from '../experiments/lt1_diagnostic/attempt_journal.mjs';
import {runJournaled} from '../experiments/lt1_diagnostic/attempt_journal.mjs';
import {assembleWrapped} from '../experiments/lt1_diagnostic/wrapped.mjs';
import {fixtureModules} from './lt1_diagnostic_fixture.mjs';
function fixture(){
 const plan=readFileSync(new URL('../experiments/lt1_diagnostic/plan.json',import.meta.url));
 const engine={node:'v22.23.4',platform:'darwin',arch:'arm64',host:'invented-host',staging_root:'/invented',plan,
  setup_receipt:Buffer.from('setup'),host_receipt:Buffer.from('host'),rights_receipt:Buffer.from('rights'),security_receipt:Buffer.from('security')};
 const paths=[...Object.values(ENTRIES),'source/LICENSE.md','runtime/bin/node','runtime/LICENSE',
  'toolchain/node_modules/ts-node/esm.mjs','toolchain/tsconfig.json','toolchain/package.json','toolchain/package-lock.json'];
 engine.files=Object.fromEntries(paths.map(p=>[p,digest(p)]));engine.worker_files=Object.fromEntries(WORKER_FILES.map(p=>[p,digest(p)]));engine.executable_sha256=engine.files['runtime/bin/node'];
 const grant={schema:'opent1d.lt1-native-grant/1',source_revision:REVISION,node:engine.node,platform:engine.platform,arch:engine.arch,
  host:engine.host,staging_root:engine.staging_root,mode:'wrapped',files:engine.files,worker_files:engine.worker_files};
 for(const n of ['plan','setup_receipt','host_receipt','rights_receipt','security_receipt'])grant[n+'_sha256']=digest(engine[n]);
 const engineRaw=Buffer.from(JSON.stringify(grant));
 const context={engine,owner_pid:123,output_root:'/invented/output',host_receipt:Buffer.from('integration host'),
  implementation:Object.fromEntries(INTEGRATION_FILES.map(p=>[p,digest(p)]))};
 context.reader_files={'experiments/lt1_diagnostic/reader.py':digest('invented reader'),'experiments/lt1_diagnostic/journal_reader.py':digest('invented journal reader')};
 const reader_identity={protocol:{source_revision:REVISION,runtime_candidate:'lt1-cambridge-audit1-node22.23.4-darwin-arm64-preparation-1',
  selected_runtime_artifact_sha256:'c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428',plan_bytes_sha256:digest(plan),
  implementation_sha256:{'experiments/lt1_diagnostic/reader.py':context.reader_files['experiments/lt1_diagnostic/reader.py']}},implementation:context.reader_files};
 const outer={schema:'opent1d.lt1-integration-grant/1',engine_grant_sha256:digest(engineRaw),host_receipt_sha256:digest(context.host_receipt),
  output_root:context.output_root,owner_pid:context.owner_pid,attempt:'invented-attempt',reader_identity,implementation:context.implementation};
 const raw=Buffer.from(JSON.stringify(outer));
 const registry={schema:'opent1d.lt1-native-admissions/1',setup:[grant.setup_receipt_sha256],execution:[digest(raw),digest(engineRaw)]};
 return {raw,engineRaw,registry,context,outer};
}
test('positive invented envelope requires both independently reviewed grants and setup',()=>{
 const f=fixture();assert.equal(verifyIntegration(f.raw,f.engineRaw,f.registry,f.context).attempt,'invented-attempt');
 for(const missing of [digest(f.raw),digest(f.engineRaw)]){
  const registry={...f.registry,execution:f.registry.execution.filter(x=>x!==missing)};
  assert.throws(()=>verifyIntegration(f.raw,f.engineRaw,registry,f.context),/refused/);
 }
 assert.throws(()=>verifyIntegration(f.raw,f.engineRaw,{...f.registry,setup:[]},f.context),/setup receipt/);
});
test('unknown integration grant refuses before parsing engine or accessing context',()=>{
 const f=fixture();assert.throws(()=>verifyIntegration(Buffer.from('not JSON'),null,{execution:[]},new Proxy({},{get(){throw Error('context accessed');}})),/no reviewed integration/);
});
test('output, owner, integration receipt and all consumed code are bound',()=>{
 for(const mutate of [c=>c.output_root='/elsewhere',c=>c.owner_pid=124,c=>c.host_receipt=Buffer.from('changed'),
  c=>c.implementation['attempt_journal.mjs']=digest('changed journal'),c=>c.reader_files={'experiments/lt1_diagnostic/reader.py':digest('changed')}]){
  const f=fixture();f.context.implementation={...f.context.implementation};mutate(f.context);
  assert.throws(()=>verifyIntegration(f.raw,f.engineRaw,f.registry,f.context),/refused/);
 }
});
test('private journal refuses existing data and cannot append after finish',()=>{
 const root=realpathSync(mkdtempSync(join(tmpdir(),'lt1-journal-'))),folder=join(root,'attempt');mkdirSync(folder,{mode:0o700});
 try{
  const journal=new AttemptJournal(folder,{output_root:folder});
  journal.finish({status:'failed',primary_error:'invented',diagnostic_error:null,rows:[],diagnostic_tail:[]});
  assert.throws(()=>journal.row({}),/closed/);journal.close();
  assert.throws(()=>new AttemptJournal(folder,{output_root:folder}),/empty attempt/);
 }finally{rmSync(root,{recursive:true,force:true});}
});
test('production integration entry refuses with empty registry before supplied paths',()=>{
 const worker=fileURLToPath(new URL('../experiments/lt1_diagnostic/integration_worker.mjs',import.meta.url));
 const r=spawnSync(process.execPath,[worker,'/missing/source','/missing/packet','/missing/output'],{encoding:'utf8',timeout:5000});
 assert.equal(r.status,1);assert.equal(r.stdout,'');assert.match(r.stderr,/no reviewed integration grant/);assert.doesNotMatch(r.stderr,/ENOENT/);
});
test('integration roster equals current relative static JavaScript imports',()=>{
 const base=new URL('../experiments/lt1_diagnostic/',import.meta.url),found=new Set();
 function visit(url){if(found.has(url.href))return;found.add(url.href);
  for(const match of readFileSync(url,'utf8').matchAll(/import\s+[\s\S]*?\sfrom\s+['"]([^'"]+)['"]/g))if(match[1].startsWith('.'))visit(new URL(match[1],url));}
 visit(new URL('integration_worker.mjs',base));assert.deepEqual([...found].sort(),INTEGRATION_FILES.map(p=>new URL(p,base).href).sort());
});
test('row export failure stops before later callbacks and restores native callback setter',()=>{
 const plan=JSON.parse(readFileSync(new URL('../experiments/lt1_diagnostic/plan.json',import.meta.url)));
 const built=assembleWrapped(fixtureModules(plan),plan),original=built.sim.setCallback,committed=[];
 const session=runJournaled(built,{row(row){if(committed.length===3)throw Error('invented row export failure');committed.push(row);}});
 assert.equal(session.status,'failed');assert.match(session.primary_error,/row export failure/);
 assert.equal(committed.length,3);assert.equal(session.rows.length,4);assert.equal(built.sim.setCallback,original);
});
