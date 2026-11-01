/** Append-only single-attempt data. Neither a project-store seal nor admission. */
import {openSync,writeFileSync,fsyncSync,closeSync,lstatSync,readdirSync,realpathSync} from 'node:fs';
import {isAbsolute,join} from 'node:path';
export const JOURNAL_SCHEMA='opent1d.lt1-attempt-journal/1';
export class AttemptJournal {
 constructor(folder,header) {
  const stat=lstatSync(folder);
  if(header.output_root!==folder)throw Error('journal output binding');
  if(!isAbsolute(folder)||realpathSync(folder)!==folder||!stat.isDirectory()||stat.isSymbolicLink()||
    stat.uid!==process.getuid()||(stat.mode&0o077)!==0||readdirSync(folder).length) throw Error('private empty attempt directory');
  this.fd=openSync(join(folder,'events.jsonl'),'wx',0o600);this.count=0;this.finished=false;this.poisoned=false;
  try {this.append({...header,type:'start',schema:JOURNAL_SCHEMA});}
  catch(error){closeSync(this.fd);this.fd=null;throw error;}
 }
 append(value) {
  if(this.fd===null||this.finished||this.poisoned)throw Error('journal closed or poisoned');
  try {
   const line=JSON.stringify(value)+'\n';
   if(Buffer.byteLength(line)>1024*1024)throw Error('journal record bound');
   writeFileSync(this.fd,line);fsyncSync(this.fd);
  } catch(error){this.poisoned=true;throw error;}
 }
 row(row){this.append({type:'row',ordinal:this.count,row});this.count++;}
 finish(session){
  this.append({type:'finish',rows_in_memory:session.rows.length,status:session.status,
   primary_error:session.primary_error,diagnostic_error:session.diagnostic_error,diagnostic_tail:session.diagnostic_tail});
  this.finished=true;
 }
 close(){if(this.fd!==null){const fd=this.fd;this.fd=null;closeSync(fd);}}
}
/** Trusted constructed engine only; native reset/solver/callback order stays owned upstream. */
export function runJournaled(built,journal,{ownerCheck=()=>{},afterRow=()=>{}}={}) {
 const original=built.sim.setCallback;
 built.sim.setCallback=function(callback){return original.call(this,raw=>{
  ownerCheck();callback(raw);
  const session=built.sessions.at(-1);
  journal.row(session.rows.at(-1));afterRow(journal.count);
 });};
 try {return built.run();} finally {built.sim.setCallback=original;}
}
