/** Selected protocol only; no engine imports or admission mechanism. */
import {encode} from '../m0/lt1/record.mjs';
export const START = Date.parse('2024-07-20T00:00:00Z');
export const HORIZON = 1800000, STEP = 300000, MINUTE = 60000;
export const GPEQ = 124.91784824923789;
export const REVISION = '9a6092065bd821f88691cd8d03b0550acd665573';
export const STATE = ['Q1','Q2','S1','S2','I','x1','x2','x3','D1','D2'];
export const fields = (v, names) => {
  const expected = names ? names.split(' ') : [];
  if (!v || typeof v !== 'object' || Array.isArray(v) ||
    Object.keys(v).length !== expected.length || !expected.every(k => Object.hasOwn(v, k))) throw Error('fields');
};
export const number = (v, lo = 0, hi = Infinity) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v < lo || v > hi) throw Error('number');
  return v;
};
export const clock = (v, hi = HORIZON) => {
  number(v, 0, hi); if (!Number.isInteger(v)) throw Error('clock'); return v;
};
const id = v => { if (typeof v !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/.test(v)) throw Error('id'); };
export function validatePlan(p) {
  fields(p, 'schema engine source_revision seed horizon_ms basal_u_h meals announcements release_rules');
  if (p.schema !== 'opent1d.lt1-diagnostic-plan/1' || p.engine !== 'lt1_cambridge' ||
    p.source_revision !== REVISION || p.seed !== 101 || p.horizon_ms !== HORIZON) throw Error('identity');
  number(p.basal_u_h, 0, 3);
  for (const name of ['meals','announcements','release_rules']) {
    if (!Array.isArray(p[name])) throw Error('plan-list');
  }
  if (p.meals.length > 1 || p.announcements.length > 1 || p.release_rules.length > 7) throw Error('scope');
  for (const m of p.meals) {
    fields(m, 'id start_ms duration_ms grams'); id(m.id); clock(m.start_ms); clock(m.duration_ms);
    if (m.duration_ms < MINUTE || (m.duration_ms / MINUTE) * MINUTE !== m.duration_ms ||
      m.start_ms + m.duration_ms > HORIZON) throw Error('native-duration');
    number(m.grams);
  }
  for (const a of p.announcements) {
    fields(a, 'id event_id start_ms available_ms grams'); id(a.id);
    if (!p.meals.some(m => m.id === a.event_id)) throw Error('announcement-event');
    clock(a.start_ms); clock(a.available_ms, HORIZON - STEP); number(a.grams);
    if (a.available_ms % STEP) throw Error('announcement-clock');
  }
  validateRules(p.release_rules);
  return p;
}
export function validateRules(rules) {
  if (!Array.isArray(rules) || rules.length > 7) throw Error('scope');
  const seen = new Set();
  for (const r of rules) {
    fields(r, 'measured_ms available_ms'); clock(r.measured_ms);
    if (r.measured_ms % STEP || seen.has(r.measured_ms)) throw Error('release-clock');
    seen.add(r.measured_ms);
    if (r.available_ms !== null) {
      clock(r.available_ms, HORIZON + STEP);
      if (r.available_ms < r.measured_ms) throw Error('release-clock');
    }
    if (r.measured_ms === 0 && r.available_ms !== 0) throw Error('initial-release');
  }
}
export function elapsed(t) {
  if (!(t instanceof Date) || !Number.isFinite(+t)) throw Error('date');
  return clock(+t - START);
}
export function snapshot(v) { return JSON.parse(JSON.stringify(v)); }
export function diagnosticSnapshot(v) { return JSON.parse(encode(v)); }
export function nativeMeals(p) {
  return p.meals.map(m => {
    const a = p.announcements.find(a => a.event_id === m.id);
    return {start: new Date(START + m.start_ms), duration: m.duration_ms / MINUTE, carbs: m.grams,
      ...(a ? {announcement: {start: new Date(START + a.start_ms),
        time: new Date(START + a.available_ms), carbs: a.grams}} : {})};
  });
}
export function row(native, controller) {
  const time_ms = elapsed(native.t);
  for (const group of ['x','y','u','s','c']) {
    if (!native[group] || Array.isArray(native[group]) || typeof native[group] !== 'object') throw Error('native-fields');
  }
  fields(native.x, STATE.join(' ')); fields(native.y, 'Gp'); fields(native.u, 'iir carbs meal exercise');
  fields(native.c, 'iir'); fields(native.s, time_ms % STEP === 0 ? 'CGM' : '');
  for (const v of Object.values(native.x)) number(v, -Infinity);
  number(native.y.Gp); number(native.u.iir); number(native.u.carbs); number(native.u.meal);
  if (native.u.exercise !== 0 || native.c.iir !== controller.getOutput().iir) throw Error('native-action');
  if (time_ms % STEP === 0 && native.s.CGM !== native.y.Gp) throw Error('raw-sensor');
  const audit = controller.getInternals(); fields(audit, 'transition memory callback_ms');
  if (audit.callback_ms !== time_ms) throw Error('controller-callback');
  return snapshot({time_ms, state: native.x, plasma_mg_dl: native.y.Gp,
    raw_cgm_mg_dl: native.s.CGM ?? null, command_u_h: native.c.iir,
    delivered_u_h: native.u.iir, intake_g_min: native.u.carbs, meal_g: native.u.meal,
    transition: audit.transition, memory: audit.memory});
}

/** In-memory recording around trusted injected fixtures; no process or native loader. */
export function recordSession(sim, controller, sensor, sessions, exportDiagnostic = null) {
  const session = {status: 'started', primary_error: null, diagnostic_error: null, rows: [], diagnostic_tail: []};
  sessions.push(session);
  // Only recorder metadata is cleared. Native reset remains Simulator-owned.
  sensor.last_generation = null;
  const diagnosticFailure = error => {
    const text = String(error);
    session.diagnostic_error = session.diagnostic_error ? session.diagnostic_error + '\n' + text : text;
  };
  sim.setCallback(native => {
    try { session.rows.push(row(native, controller)); }
    catch (error) {
      try { session.diagnostic_tail.push(diagnosticSnapshot(native)); }
      catch (diagnostic) { diagnosticFailure(diagnostic); }
      throw error;
    }
  });
  try {
    sim.runSimulation();
    if (session.rows.at(-1)?.time_ms !== HORIZON) throw Error('horizon-not-reached');
    session.status = 'completed';
  } catch (error) {
    session.status = 'failed'; session.primary_error = String(error);
    if (!session.diagnostic_tail.length && sensor.last_generation) {
      try { session.diagnostic_tail.push(diagnosticSnapshot(sensor.last_generation)); }
      catch (diagnostic) { diagnosticFailure(diagnostic); }
    }
  }
  try { if (exportDiagnostic) exportDiagnostic(diagnosticSnapshot(session)); }
  catch (error) { session.status = 'failed'; diagnosticFailure(error); }
  return session;
}
