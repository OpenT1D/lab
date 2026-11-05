/** Independent audit-1 reference: no wrapped queue or sampled-kernel imports. */
import {START, HORIZON, STEP, MINUTE, GPEQ, elapsed, fields, number, validatePlan, validateRules,
  snapshot, recordSession} from './protocol.mjs';

export class ReferenceSensor {
  constructor(native, rules) { validateRules(rules); this.native = native; this.rules = snapshot(rules); this.clear(); }
  clear() { this.generated = []; this.time = -1; this.last_generation = null; }
  reset(...args) { this.clear(); this.native.reset(...args); }
  getNextUpdateTime(t) { return this.native.getNextUpdateTime(t); }
  update(t, output) {
    const raw = this.native.update(t, output), time = elapsed(t);
    this.last_generation = {phase: 'last-sensor-generation', t, raw};
    if (time <= this.time) throw Error('generation-clock');
    fields(raw, time % STEP ? '' : 'CGM');
    if (Object.hasOwn(raw, 'CGM')) {
      number(raw.CGM);
      const rule = this.rules.find(r => r.measured_ms === time);
      this.generated.push({measured_ms: time, available_ms: rule ? rule.available_ms : time,
        glucose_mg_dl: raw.CGM});
    }
    this.time = time;
    return raw;
  }
  observation() {
    const released = this.generated.filter(s => s.available_ms !== null && s.available_ms <= this.time);
    released.sort((a, b) => b.measured_ms - a.measured_ms);
    if (!released.length) throw Error('initial-observation');
    return {...released[0]};
  }
  getOutput() { const value = this.observation().glucose_mg_dl; return {CGM: () => value}; }
}

export class ReferenceController {
  constructor(basal, sensor, announcements) {
    this.basal = number(basal,0,3); this.sensor = sensor; this.announcements = snapshot(announcements); this.reset();
  }
  reset() {
    this.memory = {previous_mg_dl: 120, source_ms: null, last_sample: null, next_tick_ms: 0};
    this.command = this.basal; this.seen = []; this.callback = -1; this.audit = null;
  }
  getNextUpdateTime(t) { return new Date(+t + STEP - elapsed(t) % STEP); }
  update(t, input, _nativeAnnouncements) {
    const time = elapsed(t);
    if (this.sensor.time !== time) throw Error('measurement-clock');
    if (time <= this.callback || (time > this.memory.next_tick_ms && this.memory.next_tick_ms < HORIZON)) throw Error('callback-clock');
    let transition = null;
    if (time % STEP === 0 && time < HORIZON) {
      const observation = this.sensor.observation(); fields(input, 'CGM');
      if (typeof input.CGM !== 'function' || input.CGM() !== observation.glucose_mg_dl) throw Error('measurement-boundary');
      const fresh = this.memory.source_ms === null || observation.measured_ms > this.memory.source_ms;
      const prior = this.memory.previous_mg_dl;
      this.command = fresh ? Math.min(3, Math.max(0, this.basal + 0.01 * (prior - 120))) : this.basal;
      const ids = this.announcements.filter(a => a.available_ms <= time && !this.seen.includes(a.id)).map(a => a.id);
      this.seen.push(...ids);
      transition = {observation, fresh, memory_before_mg_dl: prior, new_announcements: ids};
      if (fresh) {
        this.memory.previous_mg_dl = observation.glucose_mg_dl;
        this.memory.source_ms = observation.measured_ms; this.memory.last_sample = {...observation};
      }
      this.memory.next_tick_ms += STEP;
    }
    this.callback = time; this.audit = {callback_ms: time, transition, memory: snapshot(this.memory)};
  }
  getOutput() { return {iir: this.command}; }
  getInternals() { return snapshot(this.audit); }
}

/** Direct construction is inspected separately; it never calls assembleWrapped. */
export function assembleDirect(modules, supplied) {
  const p = snapshot(validatePlan(supplied));
  const patient = new modules.Cambridge({Gpeq: GPEQ});
  const basal = number(patient.computeIIR(GPEQ, new Date(START)), 0, 3);
  if (basal !== p.basal_u_h) throw Error('native-basal');
  const sensor = new ReferenceSensor(new modules.IdealCGM(), p.release_rules);
  const controller = new ReferenceController(basal, sensor, p.announcements);
  const sim = new modules.Simulator(), pump = new modules.Pump(), sessions = [];
  sim.setPatient(patient); sim.setSensor(sensor); sim.setActuator(pump); sim.setController(controller);
  const meals = p.meals.map(m => {
    const meal = {start: new Date(START + m.start_ms), duration: m.duration_ms / MINUTE, carbs: m.grams};
    const a = p.announcements.find(a => a.event_id === m.id);
    if (a) meal.announcement = {time: new Date(START + a.available_ms), start: new Date(START + a.start_ms), carbs: a.grams};
    return meal;
  });
  sim.setMeals(meals);
  sim.setOptions({t0: new Date(START), tmax: new Date(START + HORIZON), seed: 101, dt: 1});
  return {sim, patient, sensor, controller, pump, sessions,
    run: (exporter = null) => recordSession(sim, controller, sensor, sessions, exporter)};
}
