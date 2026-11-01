/** Additional reviewed authority for a durable attempt; cannot replace engine admission. */
import {digest,verifyGrant,WORKER_FILES,REVISION} from './native_loader.mjs';
export const INTEGRATION_FILES=Object.freeze([...WORKER_FILES.filter(p=>p!=='native_worker.mjs'),
 'attempt_journal.mjs','integration_gate.mjs','integration_worker.mjs']);
function requireThat(value,reason){if(!value)throw Error('LT1 integration refused: '+reason);}
function fields(value,names){requireThat(value&&typeof value==='object'&&!Array.isArray(value)&&
 JSON.stringify(Object.keys(value).sort())===JSON.stringify(names.slice().sort()),'fields');}
export function readerSourcePaths(identity) {
 fields(identity,['protocol','implementation']);
 fields(identity.protocol,['source_revision','runtime_candidate','selected_runtime_artifact_sha256','plan_bytes_sha256','implementation_sha256']);
 const paths=new Set();
 for(const map of [identity.implementation,identity.protocol.implementation_sha256]){
  requireThat(map&&typeof map==='object'&&!Array.isArray(map)&&Object.keys(map).length>0,'reader source map');
  for(const [path,sha] of Object.entries(map)){
   requireThat(path.startsWith('experiments/')&&!path.includes('\\')&&path.split('/').every(p=>p&&p!=='.'&&p!=='..')&&/^[a-f0-9]{64}$/.test(sha),'reader source path');
   paths.add(path);
  }
 }
 requireThat(Object.hasOwn(identity.protocol.implementation_sha256,'experiments/lt1_diagnostic/reader.py')&&
  Object.hasOwn(identity.implementation,'experiments/lt1_diagnostic/journal_reader.py'),'required reader source');
 return [...paths].sort();
}
export function verifyIntegration(raw,engineRaw,registry,context) {
 requireThat(Array.isArray(registry.execution)&&registry.execution.includes(digest(raw)),'no reviewed integration grant');
 const grant=JSON.parse(raw);
 fields(grant,['schema','engine_grant_sha256','host_receipt_sha256','output_root','attempt','owner_pid','reader_identity','implementation']);
 requireThat(grant.schema==='opent1d.lt1-integration-grant/1','schema');
 requireThat(grant.engine_grant_sha256===digest(engineRaw),'engine grant bytes');
 const engine=verifyGrant(engineRaw,registry,context.engine);
 requireThat(grant.host_receipt_sha256===digest(context.host_receipt),'integration host receipt');
 requireThat(grant.output_root===context.output_root&&typeof grant.output_root==='string'&&grant.output_root.startsWith('/'),'output binding');
 requireThat(typeof grant.attempt==='string'&&/^[a-z0-9][a-z0-9-]{0,63}$/.test(grant.attempt),'attempt');
 requireThat(Number.isSafeInteger(grant.owner_pid)&&grant.owner_pid>1&&grant.owner_pid===context.owner_pid,'owner');
 fields(grant.implementation,INTEGRATION_FILES);
 requireThat(INTEGRATION_FILES.every(path=>/^[a-f0-9]{64}$/.test(grant.implementation[path])&&
  context.implementation[path]===grant.implementation[path]),'integration source');
 const paths=readerSourcePaths(grant.reader_identity);
 const protocol=grant.reader_identity.protocol;
 requireThat(protocol.source_revision===REVISION&&protocol.runtime_candidate==='lt1-cambridge-audit1-node22.23.4-darwin-arm64-preparation-1'&&
  protocol.selected_runtime_artifact_sha256==='c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428'&&
  protocol.plan_bytes_sha256===digest(context.engine.plan),'reader protocol');
 requireThat(paths.every(path=>[grant.reader_identity.implementation,protocol.implementation_sha256].every(map=>
  !Object.hasOwn(map,path)||map[path]===context.reader_files[path])),'current reader bytes');
 return {...engine,attempt:grant.attempt,owner_pid:grant.owner_pid,reader_identity:grant.reader_identity,
  integration_sha256:digest(raw),engine_grant_sha256:digest(engineRaw)};
}
