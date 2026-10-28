/** Native equivalence checks run in the locked LT1 environment. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { encode } from '../m0/lt1/record.mjs';
import { build, point, config, SensorBoundary, ControllerBoundary, numericTree, START } from './cambridge.mjs';
const cfg=(controller='lt1_mpc',condition='A')=>({engine:'lt1_cambridge',profile:'reference',seed:101,controller,condition});
const collect=engine=>{
  const native=[],trace=[];
  engine.sim.setCallback(row=>{native.push(encode(row));if(engine.sim.controller===engine.bounded) trace.push(point(row,engine.bounded));});
  engine.sim.runSimulation();return {native,trace};
};
for (const controller of ['lt1_pid','lt1_mpc']) {
  for (const condition of ['A','B','C','D']) test(`native, boundary and reset exact: ${controller}/${condition}`,async()=>{
    const direct=await build(cfg(controller,condition),{direct:true});
    if(condition==='D') {
      // Independent reference filter, applied to actual sampled values before native control.
      let value;const update=direct.sensor.update.bind(direct.sensor);
      direct.sensor.update=(t,y)=>{const sample=update(t,y);const m=(t-START)/60000;
        if('CGM' in sample && !(m>=2160&&m<2190)) value=sample.CGM;return sample;};
      direct.sensor.getOutput=()=>({CGM:()=>value});
    }
    const expected=collect(direct);
    const adapted=await build(cfg(controller,condition));
    const actual=collect(adapted);
    assert.deepEqual(actual.native,expected.native);
    assert.deepEqual(collect(adapted),actual);
    assert.equal(actual.trace.length,2881);
    assert.equal(actual.trace.filter(r=>r.raw_cgm_mg_dl!==null).length,577);
    const announced=actual.trace.flatMap(r=>r.new_announcements);
    assert.equal(new Set(announced.map(a=>a.id)).size,announced.length);
    assert.equal(announced.reduce((s,a)=>s+a.carbs,0),{A:440,B:220,C:330,D:440}[condition]);
    if(condition==='D') {
      assert.equal(actual.trace.find(r=>r.time_min===2189).controller_source_min,2155);
      assert.equal(actual.trace.find(r=>r.time_min===2190).controller_source_min,2190);
    }
  });
}
test('boundary copies inputs and delivers announcements once; reset clears memory',()=>{
  const calls=[];const native={reset(){},getOutput:()=>({iir:1}),_eIntegral:0,_eOld:0,
    update(t,s,a){calls.push({t,s,a});},getInternals:()=>({})};
  const sensor={last:{minute:420}};const boundary=new ControllerBoundary(native,sensor,'A','lt1_pid');
  boundary.reset();boundary.update(new Date(START+420*60000),{CGM:()=>120,hidden:()=>{throw Error('leak');}},{future:'forbidden'});
  assert.deepEqual(Object.keys(calls[0].s),['CGM']);assert.deepEqual(Object.keys(calls[0].a),['420']);
  boundary.update(new Date(START+420*60000),{CGM:()=>120},{});
  assert.equal(boundary.audit.new_announcements.length,0);
  calls[0].a['420'].carbs=999;
  assert.equal(boundary.memory['420'].carbs,45);
  boundary.reset();assert.deepEqual(boundary.memory,{});
});
test('masking does not skip random-stream generation, including reset',()=>{
  let state=0;const native={reset(_t,seed){state=seed;},update(){state=(state*16807)%2147483647;return {CGM:state/1e7};}};
  const sensor=new SensorBoundary(native,'D');sensor.reset(new Date(START),2);
  sensor.update(new Date(START+2155*60000),{});const old=sensor.getOutput().CGM();
  sensor.update(new Date(START+2160*60000),{});assert.equal(state,(2*16807*16807)%2147483647);assert.equal(sensor.getOutput().CGM(),old);
  sensor.update(new Date(START+2190*60000),{});assert.notEqual(sensor.getOutput().CGM(),old);
  sensor.reset(new Date(START),2);assert.throws(()=>sensor.getOutput(),/initial/);
});
test('invalid combinations and internal states cannot be hidden by finite actions',()=>{
  for(const change of [{seed:0},{seed:true},{controller:'pid'},{controller:'basal_bolus'},{profile:'adult#001'},{engine:'uva'},{extra:1}]) assert.throws(()=>config({...cfg(),...change}));
  for(const value of [null,true,'1',Infinity,NaN,[],[[]],[1,NaN]]) assert.throws(()=>numericTree(value,'state'));
  const native={reset(){},update(){},getOutput:()=>({iir:1}),_eIntegral:Infinity,_eOld:1};
  const b=new ControllerBoundary(native,{last:{minute:0}},'A','lt1_pid');b.reset();
  assert.throws(()=>b.update(new Date(START),{CGM:()=>120},{}),/integral/);
});
test('native event scheduler shortens an interval without duplicate meal or delivery',async()=>{
  const meals=[{start:new Date(START+2.5*60000),carbs:40,duration:1.5}];
  const direct=await build(cfg('lt1_pid'),{direct:true,meals,options:{tmax:new Date(START+10*60000)}});
  const rows=[];direct.sim.setCallback(r=>rows.push(JSON.parse(encode(r))));direct.sim.runSimulation();
  const times=rows.map(r=>(Date.parse(r.t)-START)/60000);
  assert(times.includes(2.5));assert(times.includes(4));
  assert.equal(rows.filter(r=>r.u.meal>0).length,1);
  let carbs=0,insulin=0;
  for(let i=0;i<rows.length-1;i++){const dt=times[i+1]-times[i];carbs+=rows[i].u.carbs*dt;insulin+=rows[i].u.iir*dt/60;}
  assert.equal(carbs,40);assert(Number.isFinite(insulin)&&insulin>0);
});

test('actual boundary preserves original M0 historical reference',async()=>{
  const {createHash}=await import('node:crypto');
  const {readFileSync}=await import('node:fs');
  const meals=[{start:new Date(START+480*60000),carbs:40,duration:15,
    announcement:{start:new Date(START+480*60000),carbs:40,time:new Date(START)}}];
  const engine=await build(cfg(),{meals,options:{seed:1,tmax:new Date(START+1440*60000)}});
  const result=collect(engine);
  const digest=createHash('sha256').update(result.native.join('\n')+'\n').digest('hex');
  const baseline=JSON.parse(readFileSync(new URL('../m0/lt1/baseline.json',import.meta.url),'utf8'));
  assert.equal(digest,baseline.environments[`${process.platform}/${process.arch}`].output_sha256);
});
