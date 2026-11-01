/** Versioned durable successor. No task/store dispatch or native host admission is added. */
import {readFileSync,lstatSync,realpathSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {register} from 'node:module';
import {hostname} from 'node:os';
import {digest,inventory,executableWithin,loadConstructors,WORKER_FILES} from './native_loader.mjs';
import {verifyIntegration,readerSourcePaths,INTEGRATION_FILES} from './integration_gate.mjs';
import {AttemptJournal,runJournaled} from './attempt_journal.mjs';
import {assembleDirect} from './direct.mjs';
import {assembleWrapped} from './wrapped.mjs';
function read(path,max=16*1024*1024){const stat=lstatSync(path);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>max)throw Error('bounded regular intake');return readFileSync(path);}
export async function main(args){
 const registry=JSON.parse(read(new URL('./native-admissions.json',import.meta.url)));
 if(!Array.isArray(registry.execution)||!registry.execution.length)throw Error('LT1 integration refused: no reviewed integration grant');
 if(args.length!==3)throw Error('Expected staging, private packet and owned output');
 const [root,packet,output]=args.map(value=>resolve(value));
 const raw=read(join(packet,'integration-grant.json'));
 if(!registry.execution.includes(digest(raw)))throw Error('LT1 integration refused: no reviewed integration grant');
 if(process.execArgv.length||Object.keys(process.env).some(k=>/^(NODE_|TS_NODE|TS_CONFIG)/.test(k)))throw Error('ambient loader configuration');
 const engineRaw=read(join(packet,'grant.json'));
 const sourceRoot=fileURLToPath(new URL('../../',import.meta.url));
 const readerFiles=Object.fromEntries(readerSourcePaths(JSON.parse(raw).reader_identity).map(path=>{
  const file=resolve(sourceRoot,path);
  if(realpathSync(file)!==file)throw Error('canonical reader source required');
  return [path,digest(read(file))];
 }));
 const engine={node:process.version,platform:process.platform,arch:process.arch,host:hostname(),staging_root:root,
  executable_sha256:executableWithin(root,process.execPath),files:inventory(root),
  worker_files:Object.fromEntries(WORKER_FILES.map(path=>[path,digest(read(new URL(path,import.meta.url)))]))};
 for(const name of ['plan','setup_receipt','host_receipt','rights_receipt','security_receipt'])engine[name]=read(join(packet,name+'.json'));
 const admitted=verifyIntegration(raw,engineRaw,registry,{engine,output_root:output,owner_pid:process.ppid,reader_files:readerFiles,
  host_receipt:read(join(packet,'integration_host_receipt.json')),
  implementation:Object.fromEntries(INTEGRATION_FILES.map(path=>[path,digest(read(new URL(path,import.meta.url)))]))});
 const journal=new AttemptJournal(output,{kind:'native-unadmitted',mode:admitted.mode,identity:admitted.reader_identity,
  attempt:admitted.attempt,output_root:output,owner_pid:admitted.owner_pid,engine_grant_sha256:admitted.engine_grant_sha256,integration_sha256:admitted.integration_sha256});
 let built,session;
 try {
  process.env.TS_NODE_PROJECT=join(root,'toolchain/tsconfig.json');process.env.TS_NODE_CWD=join(root,'toolchain');
  register(pathToFileURL(join(root,'toolchain/node_modules/ts-node/esm.mjs')),pathToFileURL(join(root,'toolchain/')));
  const modules=await loadConstructors(root);
  built=(admitted.mode==='direct'?assembleDirect:assembleWrapped)(modules,admitted.plan);
  session=runJournaled(built,journal,{ownerCheck:()=>{if(process.ppid!==admitted.owner_pid)throw Error('Supervisor disappeared');}});
 } catch(error){
  const prior=built?.sessions.at(-1);
  session={status:'failed',primary_error:prior?.primary_error??String(error),diagnostic_error:prior?.diagnostic_error??null,
   rows:prior?.rows??[],diagnostic_tail:prior?.diagnostic_tail??[]};
 }
 try {journal.finish(session);}
 catch(error){process.stderr.write(JSON.stringify({primary_error:session.primary_error,export_error:String(error)})+'\n');process.exitCode=1;}
 finally {try{journal.close();}catch(error){process.stderr.write('journal close: '+String(error)+'\n');process.exitCode=1;}}
 if(session.status!=='completed')process.exitCode=1;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{await main(process.argv.slice(2));}catch(error){process.stderr.write(String(error)+'\n');process.exitCode=1;}
}
