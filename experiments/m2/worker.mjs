/** Native worker; launch through experiments.m2.run for deadlines and lifecycle. */
import { appendFileSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { SOURCE, REVISION, git, verifySource } from '../m0/lt1/setup.mjs';
import { encode, hash } from '../m0/lt1/record.mjs';
import { build, point } from './cambridge.mjs';
const output=resolve(process.argv[2]);
const save=(name,value)=>writeFileSync(resolve(output,name),encode(value)+'\n');
try {
  if (process.version !== 'v22.22.2') throw Error('Use the locked Node 22.22.2 runtime');
  verifySource();
  const cfg=JSON.parse(readFileSync(resolve(output,'config.json'),'utf8'));
  const files=git('-C',SOURCE,'ls-files','src','examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts','LICENSE.md').split('\n');
  const provenance={upstream_revision:REVISION,node:process.version,platform:`${process.platform}/${process.arch}`,
    source_sha256:Object.fromEntries(files.map(p=>[p,hash(resolve(SOURCE,p))])),
    packages:JSON.parse(readFileSync(new URL('../m0/lt1/package-lock.json',import.meta.url),'utf8')).packages};
  save('runtime.json',provenance);
  const engine=await build(cfg);
  provenance.settings=engine.settings;
  save('runtime.json',provenance);
  let previous=null;
  engine.sim.setCallback(row=>{
    if (process.env.OPENT1D_PARENT_PID && process.ppid !== Number(process.env.OPENT1D_PARENT_PID)) throw Error('Supervisor disappeared; stopping at native callback');
    // Retain native diagnostic bytes before validating a potentially failing row.
    appendFileSync(resolve(output,'native.jsonl'),encode(row)+'\n');
    const current=point(row,engine.bounded);
    if (previous===null ? current.time_min!==0 : current.time_min<=previous) throw Error('Non-increasing native time');
    previous=current.time_min;
    appendFileSync(resolve(output,'trace.jsonl'),encode(current)+'\n');
  });
  engine.sim.runSimulation();
  if(previous!==2880) throw Error('Native loop did not reach the requested horizon');
  save('result.json',{status:'completed'});
} catch(error) {
  save('result.json',{status:'failed',error:String(error)});
  writeFileSync(resolve(output,'failure.log'),error.stack??String(error));
  process.exitCode=1;
}
