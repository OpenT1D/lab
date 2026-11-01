/** Wrapped audit-1 boundary. Native generation always precedes filtering. */
import {SampledAudit1} from '../adapter_audit/lt1_sampled.mjs';
import {START, HORIZON, STEP, MINUTE, GPEQ, clock, elapsed, fields, number,
  validatePlan, validateRules, snapshot, nativeMeals, recordSession} from './protocol.mjs';

export class ReleaseQueue {
  constructor(rules) { validateRules(rules); this.rules = new Map(rules.map(r => [r.measured_ms, r.available_ms])); this.reset(); }
  reset() { this.time = -1; this.samples = []; }
  advance(time, raw) {
    clock(time);
    if (time <= this.time) throw Error('generation-clock');
    if (time % STEP === 0) number(raw); else if (raw !== null) throw Error('raw-cadence');
    const available = this.rules.has(time) ? this.rules.get(time) : time;
    if (raw !== null) this.samples.push({measured_ms: time, available_ms: available, glucose_mg_dl: raw});
    this.time = time;
  }
  asOf(time) {
    clock(time); if (time > this.time) throw Error('future-query');
    const eligible = this.samples.filter(s => s.available_ms !== null && s.available_ms <= time);
    const selected = eligible.reduce((a, b) => !a || b.measured_ms > a.measured_ms ? b : a, null);
    if (!selected) throw Error('initial-observation');
    return {...selected};
  }
}

export class RecordingSensor {
  constructor(native, queue) { this.native = native; this.queue = queue; }
  reset(...args) { this.queue.reset(); this.last_generation = null; this.native.reset(...args); }
  getNextUpdateTime(t) { return this.native.getNextUpdateTime(t); }
  update(t, y) {
    const raw = this.native.update(t, y);
    this.last_generation = {phase: 'last-sensor-generation', t, raw};
    const time = elapsed(t); fields(raw, time % STEP === 0 ? 'CGM' : '');
    this.queue.advance(time, raw.CGM ?? null);
    return raw;
  }
  getOutput() {
    const sample = this.queue.asOf(this.queue.time);
    return {CGM: () => sample.glucose_mg_dl};
  }
}

export class WrappedController {
  constructor(basal, queue, announcements) {
    this.kernel = new SampledAudit1(basal); this.queue = queue;
    this.announcements = snapshot(announcements); this.reset();
  }
  reset() { this.kernel.reset(); this.last = null; this.seen = new Set(); this.audit = null; }
  getNextUpdateTime(t) {
    return new Date(START + (Math.floor(elapsed(t) / STEP) + 1) * STEP);
  }
  update(t, measurements, _nativeAnnouncements) {
    const time = elapsed(t), sampled = time % STEP === 0 && time < HORIZON;
    if (this.queue.time !== time) throw Error('measurement-clock');
    const observation = sampled ? this.queue.asOf(time) : null;
    if (sampled) {
      fields(measurements, 'CGM');
      if (typeof measurements.CGM !== 'function' || measurements.CGM() !== observation.glucose_mg_dl) throw Error('measurement-boundary');
    }
    const result = this.kernel.update(time / MINUTE, observation ? {
      measured_min: observation.measured_ms / MINUTE,
      available_min: observation.available_ms / MINUTE, glucose_mg_dl: observation.glucose_mg_dl,
    } : null);
    let transition = null;
    if (result.transition) {
      const ids = this.announcements.filter(a => a.available_ms <= time && !this.seen.has(a.id)).map(a => a.id);
      ids.forEach(id => this.seen.add(id));
      if (result.transition.fresh) this.last = {...observation};
      transition = {observation, fresh: result.transition.fresh,
        memory_before_mg_dl: result.transition.previous_mg_dl, new_announcements: ids};
    }
    this.audit = {callback_ms: time, transition, memory: {previous_mg_dl: this.kernel.previous,
      source_ms: this.kernel.source < 0 ? null : this.kernel.source * MINUTE,
      last_sample: this.last ? {...this.last} : null, next_tick_ms: this.kernel.next * MINUTE}};
  }
  getOutput() { return {iir: this.kernel.rate}; }
  getInternals() { return snapshot(this.audit); }
}

/** Trusted constructor injection for fixture qualification, not an execution entry. */
export function assembleWrapped(modules, supplied) {
  const p = snapshot(validatePlan(supplied));
  const patient = new modules.Cambridge({Gpeq: GPEQ});
  const basal = number(patient.computeIIR(GPEQ, new Date(START)), 0, 3);
  if (basal !== p.basal_u_h) throw Error('native-basal');
  const queue = new ReleaseQueue(p.release_rules);
  const sensor = new RecordingSensor(new modules.IdealCGM(), queue);
  const controller = new WrappedController(basal, queue, p.announcements);
  const pump = new modules.Pump(), sim = new modules.Simulator(), sessions = [];
  sim.setPatient(patient); sim.setSensor(sensor); sim.setController(controller); sim.setActuator(pump);
  sim.setMeals(nativeMeals(p));
  sim.setOptions({t0: new Date(START), tmax: new Date(START + HORIZON), dt: 1, seed: p.seed});
  return {sim, patient, sensor, controller, pump, sessions,
    run: (exporter = null) => recordSession(sim, controller, sensor, sessions, exporter)};
}

export async function loadNative() {
  // No receipt, environment flag or archived JSON can grant a missing admission.
  throw Error('LT1 native loading refused: runtime, rights, setup receipt and host admission remain open');
}
