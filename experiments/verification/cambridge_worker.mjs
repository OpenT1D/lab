/** IV-001 native host probe. The native Simulator owns every physiological step. */
import {appendFileSync, readFileSync, writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {build, START, validateNative, number} from '../m2/cambridge.mjs';
import {SOURCE, REVISION, git, verifySource} from '../m0/lt1/setup.mjs';
import {encode, hash} from '../m0/lt1/record.mjs';
const output=resolve(process.argv[2]);
const save=(name,v)=>writeFileSync(resolve(output,name),encode(v)+'\n');
try {
  if(process.version!=='v22.22.2') throw Error('Use locked Node 22.22.2');
  verifySource();
  const cfg=JSON.parse(readFileSync(resolve(output,'config.json'),'utf8'));
  const robust=cfg.schema==='iv001.robust-case/1';
  if(Object.keys(cfg).sort().join()!==(robust?'controller,engine,factor,mode,profile,schema,seed,variant,warmup':'controller,engine,factor,mode,profile,schema,seed,warmup') ||
      !['iv001.case/1','iv001.robust-case/1'].includes(cfg.schema) || cfg.engine!=='lt1_cambridge' || cfg.profile!=='reference' || cfg.seed!==101 ||
      !['lt1_pid','lt1_mpc'].includes(cfg.controller) || ![1,10,100].includes(cfg.factor) ||
      ![0,1440,2880].includes(cfg.warmup) || !['feedback','replay'].includes(cfg.mode)) throw Error('Invalid IV-001 Cambridge configuration');
  const boundary=robust?JSON.parse(readFileSync(resolve(output,'boundary.json'),'utf8')):null;
  const variants=['baseline','meal-half','meal-one-half','meal-early','meal-late','announcement-none','announcement-half','announcement-late','gap-15','gap-60','gap-evening','parameter-1-low','parameter-1-high','parameter-2-low','parameter-2-high','warmup-0','warmup-48'];
  if(robust && (cfg.factor!==1 || cfg.mode!=='feedback' || !variants.includes(cfg.variant) ||
      cfg.warmup!==({'warmup-0':0,'warmup-48':2880}[cfg.variant]??1440))) throw Error('Robustness uses prescribed native feedback cases');
  const available=minute=>!boundary?.gap || !(minute>=boundary.gap[0] && minute<boundary.gap[1]);
  const replay=cfg.mode==='replay'?JSON.parse(readFileSync(resolve(output,'replay.json'),'utf8')):null;
  if(replay && (cfg.warmup!==1440 || !['completed','terminated'].includes(replay.status) ||
      !replay.rows?.length || Object.keys(cfg).some(k=>replay.config[k]!==({...cfg,factor:1,mode:'feedback'})[k]))) throw Error('Invalid nominal replay input');
  const files=git('-C',SOURCE,'ls-files','src','examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts','LICENSE.md').split('\n');
  const runtime={upstream_revision:REVISION,node:process.version,platform:`${process.platform}/${process.arch}`,
    source_sha256:Object.fromEntries(files.map(p=>[p,hash(resolve(SOURCE,p))])),
    packages:JSON.parse(readFileSync(new URL('../m0/lt1/package-lock.json',import.meta.url),'utf8')).packages};
  save('runtime.json',runtime);
  const t0=START+(1440-cfg.warmup)*60000;
  const horizon=cfg.warmup+1440;
  const limit=replay?replay.rows.at(-1).time_min:horizon;
  const events=[];
  for(let d=0;d<horizon;d+=1440) for(const [m,g] of [[420,45],[720,70],[960,15],[1080,80],[1380,10]]) {
    const start=new Date(t0+(d+m)*60000);
    events.push({start,carbs:g,duration:15,announcement:{time:start,start,carbs:g}});
  }
  if(boundary) {
    events.length=0;
    for(const [minute,g] of boundary.meals) {
      const start=new Date(t0+minute*60000);
      const announcement=boundary.announcements.find(a=>a[1]===minute);
      events.push({start,carbs:g,duration:15,...(announcement?{announcement:{time:new Date(t0+announcement[0]*60000),start,carbs:announcement[2]}}:{})});
    }
  }
  const engine=await build({engine:cfg.engine,profile:cfg.profile,seed:cfg.seed,controller:cfg.controller,condition:'A'},
    {meals:events,options:{t0:new Date(t0),tmax:new Date(t0+limit*60000)}});
  const originalParameters=structuredClone(engine.patient.getParameterValues());
  if(boundary?.parameter) {
    const {name,factor}=boundary.parameter;
    if(!['SIT','tmaxG'].includes(name) || ![.9,1.1].includes(factor)) throw Error('Unsupported local parameter');
    engine.patient.setParameterValues({[name]:number(originalParameters[name],'original parameter',0)*factor});
  }
  if(boundary) {
    const update=engine.filtered.update.bind(engine.filtered);
    engine.filtered.update=(t,y)=>{
      const previous=engine.filtered.last;
      const sample=update(t,y); // every native sample is generated before masking
      appendFileSync(resolve(output,'sensor-audit.jsonl'),encode({time_min:(t-t0)/60000,raw:sample.CGM??null})+'\n');
      if(!available((t-t0)/60000)) {
        engine.filtered.last=previous;
        if(engine.filtered.sample) engine.filtered.sample.available=false;
      }
      return sample;
    };
  }
  const {default:Solver}=await import(pathToFileURL(resolve(SOURCE,'src/core/solvers/SolverRK1_2.ts')).href);
  const solver=new Solver();
  if(solver._tol!==0.001) throw Error('Native solver tolerance hook changed');
  if(cfg.factor!==1) solver._tol/=cfg.factor;
  engine.sim.setSolver(solver);
  runtime.settings={...engine.settings,start:new Date(t0),solver:{name:'SolverRK1_2',native_relative:0.001,
    effective_relative:solver._tol,outer_minutes:1,access:'checked protected _tol on native instance'},
    mpc_prediction_solver:'unchanged private SolverRK1, reset step 5 min'};
  if(boundary) {
    runtime.settings.patient=structuredClone(engine.patient.getParameterValues());
    runtime.settings.parameter_probe={change:boundary.parameter,original:originalParameters,
      reset:'native equilibrium recomputed; controller and MPC predictor settings unchanged'};
  }
  save('runtime.json',runtime);
  let audit=null;
  if(replay) {
    engine.sim.setController({
      reset(){this.command=null;},getNextUpdateTime(t){return engine.controller.getNextUpdateTime(t);},
      update(t,s){
        const minute=(t-t0)/60000;
        const p=replay.rows[minute];
        if(!p || p.time_min!==minute) throw Error('Replay clock mismatch');
        this.command={iir:number(p.command_u_h,'replayed command')};
        audit={time_min:minute,controller_cgm_mg_dl:number(s.CGM(),'observed CGM',0),
          controller_source_min:engine.filtered.last.minute-(1440-cfg.warmup),
          new_announcements:p.new_announcements,announced_history:p.announced_history};
      },getOutput(){return this.command;},getInternals(){return {};}
    });
  }
  let previous=-1;
  engine.sim.setCallback(row=>{
    if(process.env.OPENT1D_PARENT_PID && process.ppid!==Number(process.env.OPENT1D_PARENT_PID)) throw Error('Supervisor disappeared');
    appendFileSync(resolve(output,'native.jsonl'),encode(row)+'\n');
    validateNative(row);
    const minute=(row.t-t0)/60000;
    if(minute!==previous+1) throw Error('Unexpected outer cadence');
    previous=minute;
    if(!replay) audit={...engine.bounded.audit,time_min:minute,
      controller_source_min:engine.bounded.audit.controller_source_min-(1440-cfg.warmup)};
    if(!audit || audit.time_min!==minute) throw Error('Observation/control ordering');
    if(minute%5===0) number(row.s.CGM,'required raw sample',0);
    appendFileSync(resolve(output,'trace.jsonl'),encode({...audit,glucose_mg_dl:row.y.Gp,
      raw_cgm_mg_dl:row.s.CGM??null,sensor_available:available(minute),command_u_h:row.c.iir,
      delivered_u_h:row.u.iir,intake_g_min:row.u.carbs,true_meal_g:row.u.meal})+'\n');
  });
  engine.sim.runSimulation();
  if(previous!==limit) throw Error('Native loop ended early');
  save('result.json',{status:previous===horizon?'completed':'input_exhausted'});
} catch(error) {
  save('result.json',{status:'failed',error:String(error)});
  writeFileSync(resolve(output,'failure.log'),error.stack??String(error));
  process.exitCode=1;
}
