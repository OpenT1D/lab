/** LIT-002 exploratory absorption boundary around the pinned native Cambridge patient.
 * OpenT1D code, Apache-2.0. Native LT1 source remains in its separate MIT checkout.
 * This is a synthetic structural sensitivity experiment, not a lispro validation.
 */
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { SOURCE, REVISION, verifySource } from '../../../m0/lt1/setup.mjs';

export const START = Date.parse('2024-07-20T00:00:00Z');
export const ARMS = ['cambridge_native', 'cambridge_mean_matched', 'faggionato_sc'];
const STATE_KEYS = ['Q1', 'Q2', 'S1', 'S2', 'I', 'x1', 'x2', 'x3', 'D1', 'D2'];
const INPUT_KEYS = ['arm', 'horizon_min', 'sample_step_min', 'max_step_min',
  'relative_tolerance', 'equilibrium_glucose_mg_dl', 'insulin_segments', 'meals', 'absorption'];
const finite = (value, name, minimum = 0, strictly = false) => {
  if (typeof value !== 'number' || !Number.isFinite(value) ||
      (strictly ? value <= minimum : value < minimum)) {
    throw Error(`Invalid ${name}: finite number ${strictly ? '>' : '>='} ${minimum} required`);
  }
  return value;
};
const keys = (value, expected, name) => {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join() !== [...expected].sort().join()) {
    throw Error(`Invalid ${name}: expected ${expected.join(', ')}`);
  }
};
const milliseconds = (minutes, name) => {
  finite(minutes, name);
  const ms = Math.round(minutes * 60000);
  if (!Number.isSafeInteger(ms) || Math.abs(ms - minutes * 60000) > 1e-7) {
    throw Error(`${name} must be representable in whole milliseconds`);
  }
  return ms;
};

export function configuration(value) {
  keys(value, INPUT_KEYS, 'configuration');
  if (!ARMS.includes(value.arm)) throw Error('Unsupported absorption arm');
  for (const name of ['horizon_min', 'sample_step_min', 'max_step_min',
    'relative_tolerance', 'equilibrium_glucose_mg_dl']) finite(value[name], name, 0, true);
  for (const name of ['horizon_min', 'sample_step_min', 'max_step_min']) milliseconds(value[name], name);
  if (value.horizon_min > 2880 || value.sample_step_min > 5 || value.max_step_min > 1 ||
      value.max_step_min < 0.01 || value.sample_step_min < 0.01 ||
      value.max_step_min > value.sample_step_min || value.relative_tolerance > 0.001) {
    throw Error('Outside bounded LIT-002 horizon, clock or solver support');
  }
  keys(value.absorption, ['tau_min', 'ka1_per_min', 'kd_per_min', 'ka2_per_min'], 'absorption');
  finite(value.absorption.tau_min, 'tau_min');
  milliseconds(value.absorption.tau_min, 'tau_min');
  finite(value.absorption.ka1_per_min, 'ka1_per_min');
  for (const name of ['kd_per_min', 'ka2_per_min']) finite(value.absorption[name], name, 0, true);
  if (!Array.isArray(value.insulin_segments) || !Array.isArray(value.meals)) throw Error('Schedules must be arrays');
  for (const segment of value.insulin_segments) {
    keys(segment, ['start_min', 'end_min', 'extra_u_h'], 'insulin segment');
    milliseconds(segment.start_min, 'start_min'); milliseconds(segment.end_min, 'end_min');
    finite(segment.extra_u_h, 'extra_u_h');
    if (segment.end_min <= segment.start_min || segment.end_min > value.horizon_min) throw Error('Invalid infusion interval');
  }
  for (const meal of value.meals) {
    keys(meal, ['start_min', 'duration_min', 'grams'], 'meal');
    milliseconds(meal.start_min, 'meal.start_min'); milliseconds(meal.duration_min, 'meal.duration_min');
    finite(meal.duration_min, 'meal.duration_min', 0, true); finite(meal.grams, 'meal.grams');
    if (meal.start_min + meal.duration_min > value.horizon_min) throw Error('Meal extends past horizon');
  }
  return structuredClone(value);
}

export function meanAppearanceTime(absorption) {
  const { tau_min: tau, ka1_per_min: k1, kd_per_min: kd, ka2_per_min: k2 } = absorption;
  return tau + 1 / (k1 + kd) + kd / (k1 + kd) / k2;
}

/** Integrate the already-delivered infusion; before zero, history is constant basal. */
export function deliveryAmount(config, basal, start, end) {
  return basal * (end - start) / 60 + config.insulin_segments.reduce((sum, segment) =>
    sum + Math.max(0, Math.min(end, segment.end_min) - Math.max(start, segment.start_min)) * segment.extra_u_h / 60, 0);
}

export function infusionAt(config, basal, minute) {
  return basal + config.insulin_segments.reduce((sum, segment) => sum +
    (minute >= segment.start_min && minute < segment.end_min ? segment.extra_u_h : 0), 0);
}

export function carbohydratesAt(config, minute) {
  return config.meals.reduce((sum, meal) => sum +
    (minute >= meal.start_min && minute < meal.start_min + meal.duration_min ? meal.grams / meal.duration_min : 0), 0);
}

export function carbohydrateAmount(config, minute) {
  return config.meals.reduce((sum, meal) => sum + Math.max(0,
    Math.min(minute, meal.start_min + meal.duration_min) - meal.start_min) * meal.grams / meal.duration_min, 0);
}

export async function nativeModules() {
  verifySource();
  const upstream = path => import(pathToFileURL(resolve(SOURCE, path)).href);
  const [{ default: Cambridge }, { default: Solver }] = await Promise.all([
    upstream('src/core/models/Cambridge.ts'), upstream('src/core/solvers/SolverRK1_2.ts'),
  ]);
  return { Cambridge, Solver };
}

/** Only the absorption states and the appearance input to plasma are replaced. */
export function attachAbsorption(patient, absorption) {
  const nativeDerivatives = patient.computeDerivatives.bind(patient);
  const { ka1_per_min: k1, kd_per_min: kd, ka2_per_min: k2 } = absorption;
  patient.computeDerivatives = (time, state, input) => {
    const original = nativeDerivatives(time, state, input);
    const parameters = patient.evaluateParameterValuesAt(time);
    const rate = finite(input.lit002_delayed_iir, 'delayed delivered U/h') * 1000 / 60;
    const appearance = k1 * state.S1 + k2 * state.S2;
    return { ...original,
      S1: rate - (k1 + kd) * state.S1,
      S2: kd * state.S1 - k2 * state.S2,
      I: appearance / (parameters.VI * parameters.BW) - parameters.ke * state.I,
    };
  };
  return nativeDerivatives;
}

export async function prepare(value) {
  const config = configuration(value);
  const { Cambridge, Solver } = await nativeModules();
  const common = { Gpeq: config.equilibrium_glucose_mg_dl };
  const reference = new Cambridge(common);
  const time = new Date(START);
  const basal = reference.computeIIR(common.Gpeq, time);
  finite(basal, 'common equilibrium basal U/h', 0, true);
  const referenceInitial = reference.computeSteadyState({ iir: basal }, time);
  const tmaxI = meanAppearanceTime(config.absorption) / 2;
  const patient = new Cambridge({ ...common,
    ...(config.arm === 'cambridge_mean_matched' ? { tmaxI } : {}),
  });
  const initial = { ...referenceInitial };
  const r = basal * 1000 / 60;
  if (config.arm === 'cambridge_mean_matched') initial.S1 = initial.S2 = r * tmaxI;
  if (config.arm === 'faggionato_sc') {
    const { ka1_per_min: k1, kd_per_min: kd, ka2_per_min: k2 } = config.absorption;
    initial.S1 = r / (k1 + kd); initial.S2 = kd * initial.S1 / k2;
    attachAbsorption(patient, config.absorption);
  }
  patient.setInitialState(initial);
  const solver = new Solver();
  // Native protected tolerance is configured on this instance only; source is unchanged.
  solver._tol = config.relative_tolerance;
  solver.reset(config.max_step_min);
  patient.reset(time, 101, solver);
  const parameters = patient.getParameterValues();
  return { config, patient, solver, basal, initial, parameters, metadata: {
    upstream_revision: REVISION,
    model: config.arm === 'faggionato_sc' ? 'native LT1 Cambridge with OpenT1D experimental SC replacement' : 'native LT1 Cambridge',
    arm: config.arm,
    native_parameters: parameters,
    absorption_parameters: config.absorption,
    mean_matched_tmaxI_min: tmaxI,
    basal_u_h: basal,
    initial_state: initial,
    start_utc: new Date(START).toISOString(),
    prehistory: 'Constant common equilibrium basal from the indefinite past; no prior meals or extra infusion.',
    solver: { name: 'native SolverRK1_2', relative_error_target: config.relative_tolerance,
      maximum_external_interval_min: config.max_step_min },
    process_ownership: {
      absorption: config.arm === 'faggionato_sc' ? 'Faggionato fixed-effect SC equations and delay; native absorption replaced' : 'native Cambridge',
      systemic_insulin: 'native Cambridge VI, BW and ke',
      insulin_action_glucose_and_meals: 'unchanged native Cambridge derivatives',
      input: 'predetermined already-delivered U/h and ingested g/min; no controller, pump or sensor',
    },
  } };
}

function clock(config) {
  const horizon = milliseconds(config.horizon_min, 'horizon');
  const maxStep = milliseconds(config.max_step_min, 'max_step');
  const sampleStep = milliseconds(config.sample_step_min, 'sample_step');
  const delay = milliseconds(config.absorption.tau_min, 'delay');
  const boundaries = new Set([0, horizon]);
  const samples = new Set([0, horizon]);
  for (let time = 0; time <= horizon; time += maxStep) boundaries.add(time);
  for (let time = 0; time <= horizon; time += sampleStep) { boundaries.add(time); samples.add(time); }
  const event = time => { if (time >= 0 && time <= horizon) { boundaries.add(time); samples.add(time); } };
  for (const segment of config.insulin_segments) {
    for (const minute of [segment.start_min, segment.end_min]) {
      const time = milliseconds(minute, 'infusion event');
      event(time); event(time + delay);
    }
  }
  for (const meal of config.meals) {
    event(milliseconds(meal.start_min, 'meal event'));
    event(milliseconds(meal.start_min + meal.duration_min, 'meal end'));
  }
  return { times: [...boundaries].sort((a, b) => a - b), samples };
}

export function validateRow(row) {
  keys(row.state, STATE_KEYS, 'native state');
  for (const [key, value] of Object.entries(row.state)) finite(value, `state.${key}`, -1e-8);
  for (const [key, value] of Object.entries(row)) if (key !== 'state') finite(value, key);
}

export function runPrepared(engine, onRow = () => {}) {
  const { config, patient, basal, initial, parameters } = engine;
  const { times, samples } = clock(config);
  const delay = config.arm === 'faggionato_sc' ? config.absorption.tau_min : 0;
  let previous = 0;
  let count = 0;
  for (const elapsed of times) {
    const minute = elapsed / 60000;
    if (elapsed > previous) {
      const midpoint = (previous + elapsed) / 120000;
      // All input discontinuities are explicit stops. The old interval's value
      // is held through its right endpoint for both Heun stages.
      const input = { iir: infusionAt(config, basal, midpoint), carbs: carbohydratesAt(config, midpoint),
        lit002_delayed_iir: infusionAt(config, basal, midpoint - delay) };
      patient.update(new Date(START + elapsed), () => ({ ...input }));
    }
    previous = elapsed;
    if (!samples.has(elapsed)) continue;
    const state = { ...patient.getState() };
    const appearance = config.arm === 'faggionato_sc'
      ? config.absorption.ka1_per_min * state.S1 + config.absorption.ka2_per_min * state.S2
      : state.S2 / parameters.tmaxI;
    const delivered = deliveryAmount(config, basal, 0, minute) * 1000;
    const delayedDelivery = deliveryAmount(config, basal, -delay, minute - delay) * 1000;
    const queue = delay ? deliveryAmount(config, basal, minute - delay, minute) * 1000 : 0;
    const row = { time_min: minute, glucose_mg_dl: patient.getOutput().Gp,
      insulin_mU_L: state.I, appearance_mU_min: appearance,
      delivered_u_h: infusionAt(config, basal, minute),
      delayed_delivered_u_h: infusionAt(config, basal, minute - delay),
      intake_g_min: carbohydratesAt(config, minute),
      depot_mU: state.S1 + state.S2, delay_queue_mU: queue,
      total_subcutaneous_mU: state.S1 + state.S2 + queue,
      cumulative_delivered_mU: delivered, cumulative_delayed_delivered_mU: delayedDelivery,
      cumulative_carbohydrates_g: carbohydrateAmount(config, minute),
      // A balance-derived quantity, not an independent mass-conservation test.
      balance_derived_absorbed_mU: delayedDelivery - ((state.S1 + state.S2) - (initial.S1 + initial.S2)),
      state,
    };
    onRow(row);
    validateRow(row);
    count += 1;
  }
  return { status: 'completed', rows: count, final_minute: previous / 60000 };
}

export async function runCase(value, { onRow } = {}) {
  const engine = await prepare(value);
  return { ...runPrepared(engine, onRow), metadata: engine.metadata };
}
