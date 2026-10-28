/** OT-014 LT1 boundary. Native Simulator owns all physiological scheduling. */
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { SOURCE, verifySource } from '../m0/lt1/setup.mjs';

export const START = Date.parse('2024-07-20T00:00:00Z');
export const MEALS = [0, 1440].flatMap(day => [[420,45],[720,70],[960,15],[1080,80],[1380,10]]
  .map(([t, grams]) => ({ minute: day+t, grams })));
export const number = (v, name, minimum = -Infinity) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v < minimum) throw Error(`Invalid ${name}: finite number >= ${minimum} required`);
  return v;
};
export function numericTree(v, name) {
  if (Array.isArray(v)) { if (!v.length) throw Error(`Empty ${name}`); v.forEach(x => numericTree(x,name)); }
  else number(v,name);
}
export function config(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join() !== 'condition,controller,engine,profile,seed') throw Error('Expected engine, profile, controller, condition and seed only');
  if (value.engine !== 'lt1_cambridge' || value.profile !== 'reference' ||
      !['lt1_pid','lt1_mpc'].includes(value.controller)) throw Error('Supported Cambridge combinations: reference with lt1_pid or lt1_mpc; no bolus controller or matched cohort');
  if (!['A','B','C','D'].includes(value.condition) || value.seed !== 101) throw Error('Cambridge structural demonstration requires A–D and seed 101 (one deterministic parameterization)');
  return {...value};
}
export const available = (condition, minute) => !(condition === 'D' && minute >= 2160 && minute < 2190);
export function scenario(condition) {
  return MEALS.map(({minute,grams}) => {
    const fraction = minute < 1440 ? 1 : {A:1,B:0,C:0.5,D:1}[condition];
    const start = new Date(START+minute*60000);
    return { start, carbs: grams, duration: 15, ...(fraction ? {
      announcement: { start, time: start, carbs: grams*fraction },
    } : {}) };
  });
}

/** Native sample generation always precedes observation filtering. */
export class SensorBoundary {
  constructor(native, condition) { this.native=native; this.condition=condition; }
  reset(...args) { this.last=null; this.sample=null; this.native.reset(...args); }
  getNextUpdateTime(t) { return this.native.getNextUpdateTime(t); }
  update(t,y) {
    const sample = this.native.update(t,y);
    const minute=(t-START)/60000;
    this.sample = null;
    if (Object.hasOwn(sample,'CGM')) {
      number(sample.CGM,'raw CGM',0);
      this.sample = {minute, value:sample.CGM, available:available(this.condition,minute)};
      if (this.sample.available) this.last={minute,value:sample.CGM};
    }
    return sample; // native callback keeps the real sample even during masking
  }
  getOutput() {
    if (!this.last) throw Error('No available initial sensor observation');
    const value=this.last.value;
    return {CGM:()=>value};
  }
}

export class ControllerBoundary {
  constructor(native, sensor, condition, kind, events=scenario(condition)) {
    this.native=native; this.sensor=sensor; this.condition=condition; this.kind=kind; this.events=events;
  }
  reset(...args) { this.memory={}; this.seen=new Set(); this.audit=null; this.native.reset(...args); }
  getNextUpdateTime(t) { return this.native.getNextUpdateTime(t); }
  update(t,s,_nativeAnnouncements) {
    const minute=(t-START)/60000;
    const newly=[];
    // Independent protocol schedule; do not forward the native information object.
    for (const meal of this.events) {
      const a=meal.announcement;
      if (!a || a.time > t) continue;
      const id=String((a.time-START)/60000);
      if (!this.seen.has(id)) {
        if (+a.time !== +t) throw Error('Missed announcement boundary');
        this.seen.add(id); newly.push(id);
        this.memory[id]={time:new Date(a.time),start:new Date(a.start),carbs:a.carbs};
      }
    }
    const glucose=number(s.CGM(),'controller CGM',0);
    const history=Object.fromEntries(Object.entries(this.memory).map(([id,a])=>
      [id,{time:new Date(a.time),start:new Date(a.start),carbs:a.carbs}]));
    this.native.update(new Date(t), {CGM:()=>glucose}, history);
    const action=this.native.getOutput();
    if (Object.keys(action).join() !== 'iir') throw Error('Only basal infusion controllers supported; bolus amount U is not an infusion rate');
    number(action.iir,'command U/h');
    if (this.kind === 'lt1_pid') {
      number(this.native._eIntegral,'PID integral'); number(this.native._eOld,'PID previous error');
    } else {
      numericTree(this.native.u_opt_last,'MPC optimal sequence');
      numericTree(this.native.ekf.x,'MPC estimator state');
      numericTree(this.native.ekf.P,'MPC estimator covariance');
      for (const x of Object.values(this.native.patient.getState())) number(x,'MPC predictor state');
    }
    this.audit={time_min:minute,controller_cgm_mg_dl:glucose,controller_source_min:this.sensor.last.minute,
      new_announcements:newly.map(id=>({id,...this.memory[id]})),announced_history:history};
  }
  getOutput() { return this.native.getOutput(); }
  getInternals() { return this.native.getInternals(); }
}

export async function build(value, {direct=false, meals=null, options={}}={}) {
  const cfg=config(value);
  verifySource();
  const upstream=p=>import(pathToFileURL(resolve(SOURCE,p)).href);
  const [{default:Simulator},{default:Cambridge},{default:IdealCGM},{default:Pump},{default:PID},{default:MPC},reference] = await Promise.all([
    upstream('src/core/Simulator.ts'),upstream('src/core/models/Cambridge.ts'),upstream('src/core/sensors/IdealCGM.ts'),
    upstream('src/core/actuators/StaticInsulinPump.ts'),upstream('src/core/controllers/PID.ts'),
    upstream('src/core/controllers/MPC_Hovorka2004.ts'),upstream('examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts')]);
  const patient=new Cambridge({Gpeq:124.91784824923789});
  const sensor=new IdealCGM(); const pump=new Pump();
  const controller=cfg.controller==='lt1_pid' ? new PID() : new MPC(reference.controller.getParameterValues());
  const filtered=new SensorBoundary(sensor,cfg.condition);
  const bounded=new ControllerBoundary(controller,filtered,cfg.condition,cfg.controller,meals ?? scenario(cfg.condition));
  const sim=new Simulator();
  sim.setPatient(patient); sim.setSensor(direct?sensor:filtered); sim.setController(direct?controller:bounded); sim.setActuator(pump);
  sim.setMeals(meals ?? scenario(cfg.condition));
  sim.setOptions({t0:new Date(START),tmax:new Date(START+2880*60000),dt:1,seed:cfg.seed,...options});
  return {sim,patient,sensor,pump,controller,filtered,bounded,settings:{patient:patient.getParameterValues(),sensor:sensor.getParameterValues(),
    pump:pump.getParameterValues(),controller:controller.getParameterValues(),seeds:{base:cfg.seed,sensor:cfg.seed+1,controller:cfg.seed+2,pump:cfg.seed+3,patient:cfg.seed+4},
    solver:{name:'SolverRK1_2',relative_error_target:0.001,default_dt_minutes:1},
    time:'UTC',glucose:'instantaneous plasma Gp mg/dL',insulin:'modeled infusion U/h; terminal action excluded'}};
}

export function validateNative(row) {
  for (const group of ['x','y','u','c','s']) {
    if (!row[group] || typeof row[group]!=='object') throw Error(`Missing native ${group}`);
    for (const [key,v] of Object.entries(row[group])) number(v,`${group}.${key}`);
  }
  const expected=['Q1','Q2','S1','S2','I','x1','x2','x3','D1','D2'];
  if (Object.keys(row.x).sort().join()!==expected.sort().join()) throw Error('Missing Cambridge state');
  number(row.y.Gp,'plasma glucose',0); number(row.u.iir,'modeled delivery U/h',0);
  for (const field of ['carbs','meal','exercise']) number(row.u[field],field,0);
  number(row.c.iir,'command U/h');
}

export function point(row, boundary) {
  validateNative(row);
  const time_min=(row.t-START)/60000;
  number(time_min,'time',0);
  if (time_min%5===0) number(row.s.CGM,'required sampled CGM',0);
  else if (Object.keys(row.s).length) throw Error('Unexpected native sensor sampling');
  if (!boundary.audit || boundary.audit.time_min!==time_min) throw Error('Controller event ordering mismatch');
  return { ...boundary.audit,glucose_mg_dl:row.y.Gp,raw_cgm_mg_dl:row.s.CGM ?? null,
    sensor_available:available(boundary.condition,time_min),command_u_h:row.c.iir,delivered_u_h:row.u.iir,
    intake_g_min:row.u.carbs,true_meal_g:row.u.meal };
}
