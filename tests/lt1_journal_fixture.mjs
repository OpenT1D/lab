/** Fixed invented constructor process. Never imports or grants a native engine. */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {AttemptJournal,runJournaled} from '../experiments/lt1_diagnostic/attempt_journal.mjs';
import {digest} from '../experiments/lt1_diagnostic/native_loader.mjs';
import {assembleDirect} from '../experiments/lt1_diagnostic/direct.mjs';
import {assembleWrapped} from '../experiments/lt1_diagnostic/wrapped.mjs';
import {fixtureModules} from './lt1_diagnostic_fixture.mjs';
const [behavior,mode,configPath,folder]=process.argv.slice(2);
if(!['complete','failure','hang','owner','late-hang'].includes(behavior)||!['direct','wrapped'].includes(mode))throw Error('fixture selection');
const config=JSON.parse(readFileSync(configPath));
const journal=new AttemptJournal(resolve(folder),{kind:'invented',mode,identity:config.identity,
 attempt:'invented-attempt',output_root:resolve(folder),owner_pid:process.ppid,
 engine_grant_sha256:digest('invented engine grant'),integration_sha256:digest('invented integration grant')});
const built=(mode==='direct'?assembleDirect:assembleWrapped)(fixtureModules(config.plan,{failAfter:behavior==='failure'?2:null}),config.plan);
const block=()=>{while(true)Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,1000);};
try {
 const session=runJournaled(built,journal,{
  ownerCheck:()=>{if(behavior==='owner'&&journal.count===3)throw Error('Supervisor disappeared');},
  afterRow:count=>{if(behavior==='hang'&&count===3)block();}});
 journal.finish(session);
 if(behavior==='late-hang')block();
 if(session.status!=='completed')process.exitCode=1;
} finally {journal.close();}
