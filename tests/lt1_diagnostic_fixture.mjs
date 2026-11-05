/** Scripted interface fixtures, not physiology, a pump model or native outputs. */
import assert from 'node:assert/strict';
import {START, HORIZON, STEP, MINUTE, GPEQ, STATE, snapshot} from '../experiments/lt1_diagnostic/protocol.mjs';
import {assembleWrapped} from '../experiments/lt1_diagnostic/wrapped.mjs';
import {assembleDirect} from '../experiments/lt1_diagnostic/direct.mjs';

export function fixtureModules(plan, {failAfter = null, badRaw = false, basal = plan.basal_u_h} = {}) {
  // Hand-specified callback prefix for the selected 2.5/1.5-minute case.
  const fractional = plan.meals[0]?.start_ms === 150000;
  const times = fractional ? [0,60000,120000,150000,210000,240000,
    ...Array.from({length:26}, (_, i) => (i+5)*MINUTE)] :
    Array.from({length:31}, (_, i) => i*MINUTE);
  class Cambridge {
    constructor(parameters) { assert.deepEqual(parameters, {Gpeq:GPEQ}); }
    computeIIR(glucose, date) { assert.equal(glucose, GPEQ); assert.equal(+date, START); return basal; }
    reset(t, seed) { this.seed = seed; this.time = +t - START; }
    update(t) { this.time = +t - START; }
    getState() { return Object.fromEntries(STATE.map((name, i) => [name, i + this.time/MINUTE])); }
    getOutput() { return {Gp:[120,180,60,150,100,120,130][Math.floor(this.time/STEP)]}; }
  }
  class IdealCGM {
    reset(_t, seed) { this.seed = seed; this.calls = 0; }
    update(t, y) { this.calls++; return (+t - START) % STEP ? {} : {CGM:badRaw ? NaN : y.Gp}; }
    getNextUpdateTime(t) { return new Date(+t + STEP - (+t - START) % STEP); }
  }
  class Pump {
    reset(_t, seed) { this.seed = seed; this.calls = 0; }
    update(t) {
      this.calls++; const time = +t - START;
      // Independent scripted rates make callback-duration integration distinguishable.
      const rate = time === 150000 ? 0.3 : time === 210000 ? 0.6 :
        [0.9,1.2,1.2,1.5,0.6,1,30][Math.floor(time/STEP)];
      return {iir:rate};
    }
    getNextUpdateTime() { return undefined; }
  }
  class Simulator {
    setPatient(v) { this.patient=v; }
    setSensor(v) { this.sensor=v; }
    setController(v) { this.controller=v; }
    setActuator(v) { this.pump=v; }
    setMeals(v) { this.meals=v; }
    setOptions(v) { this.options=v; }
    setCallback(v) { this.callback=v; }
    runSimulation() {
      assert.deepEqual(this.options, {t0:new Date(START), tmax:new Date(START+HORIZON), dt:1,seed:101});
      this.reset_order = ['solver','sensor','controller','pump','patient'];
      this.solver = {fixture:true};
      this.sensor.reset(this.options.t0,102,this.solver);
      this.controller.reset(this.options.t0,103,this.solver);
      this.pump.reset(this.options.t0,104,this.solver);
      this.patient.reset(this.options.t0,105,this.solver);
      for (const [index,time] of times.entries()) {
        const t = new Date(START+time);
        this.patient.update(t); const y=this.patient.getOutput();
        const s=this.sensor.update(t,y);
        this.controller.update(t,this.sensor.getOutput(),{untrusted_actual_meal:999});
        assert.ok(+this.controller.getNextUpdateTime(t)>+t, 'strict future native stop');
        const c=this.controller.getOutput(), medication=this.pump.update(t,c);
        assert.deepEqual(Object.keys(c), ['iir']);
        const carbs=this.meals.filter(m=>t>=m.start && +t<+m.start+m.duration*MINUTE)
          .reduce((sum,m)=>sum+m.carbs/m.duration,0);
        const meal=this.meals.filter(m=>+m.start===+t).reduce((sum,m)=>sum+m.carbs,0);
        this.callback({t,x:this.patient.getState(),y,s,c,u:{...medication,carbs,meal,exercise:0}});
        if (index === failAfter) throw Error('fixture primary failure');
      }
    }
  }
  return {Cambridge,IdealCGM,Pump,Simulator};
}

export function generate(plan, options = {}) {
  const builds = {};
  for (const [mode, assemble] of [['direct',assembleDirect], ['wrapped',assembleWrapped]]) {
    const built=assemble(fixtureModules(plan, options),snapshot(plan));
    builds[mode]={built, session:built.run(options.exporter ?? null)};
  }
  return builds;
}
