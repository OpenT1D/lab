/** Numerical/process ownership checks in the locked Node 22.22.2 LT1 environment. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { START, ARMS, configuration, meanAppearanceTime, deliveryAmount, carbohydrateAmount,
  nativeModules, attachAbsorption, prepare, runPrepared, runCase } from './coupling.mjs';

const config = (arm = 'cambridge_native', events = true) => ({ arm, horizon_min: 40,
  sample_step_min: 1, max_step_min: 0.25, relative_tolerance: 0.001,
  equilibrium_glucose_mg_dl: 124.91784824923789,
  insulin_segments: events ? [{ start_min: 10, end_min: 15, extra_u_h: 24 }] : [],
  meals: events ? [{ start_min: 10, duration_min: 15, grams: 40 }] : [],
  absorption: { tau_min: 5.62, ka1_per_min: 0.000134, kd_per_min: 0.0283, ka2_per_min: 0.0128 },
});
const close = (actual, expected, tolerance = 1e-10) => assert(Math.abs(actual - expected) <= tolerance,
  `${actual} differs from ${expected} by more than ${tolerance}`);

test('configuration rejects unsupported, nonfinite, ambiguous and unbounded inputs', () => {
  for (const changes of [{ arm: 'lispro_validated' }, { horizon_min: Infinity }, { horizon_min: true },
    { sample_step_min: 0 }, { max_step_min: 0.000001 }, { relative_tolerance: 0.1 }, { extra: 1 },
    { insulin_segments: [{ start_min: 10, end_min: 15, extra_u_h: -1 }] },
    { meals: [{ start_min: 35, duration_min: 15, grams: 40 }] },
    { absorption: { ...config().absorption, VI: 0.135 } },
  ]) assert.throws(() => configuration({ ...config(), ...changes }));
});

test('mean matching includes delay and both appearance paths; schedules conserve amount', () => {
  const cfg = config();
  close(meanAppearanceTime(cfg.absorption) / 2, 59.27299324752058);
  close(deliveryAmount(cfg, 1, 0, 40), 2 + 40 / 60);
  close(deliveryAmount(cfg, 1, -5.62, 0), 5.62 / 60);
  close(carbohydrateAmount(cfg, 40), 40);
  close(carbohydrateAmount(cfg, 17.5), 20);
});

test('replacement changes only native SC derivatives and the plasma appearance term', async () => {
  const { Cambridge } = await nativeModules();
  const patient = new Cambridge();
  const time = new Date(START);
  const state = { Q1: 80, Q2: 60, S1: 1000, S2: 2000, I: 12, x1: 0.03, x2: 0.01, x3: 0.3, D1: 30, D2: 10 };
  const input = { iir: 25, carbs: 2, lit002_delayed_iir: 1 };
  const original = patient.computeDerivatives(time, state, input);
  attachAbsorption(patient, config().absorption);
  const actual = patient.computeDerivatives(time, state, input);
  for (const key of ['Q1', 'Q2', 'x1', 'x2', 'x3', 'D1', 'D2']) assert.equal(actual[key], original[key]);
  close(actual.S1, 1000 / 60 - (0.000134 + 0.0283) * state.S1);
  close(actual.S2, 0.0283 * state.S1 - 0.0128 * state.S2);
  close(actual.I, (0.000134 * state.S1 + 0.0128 * state.S2) / (0.12 * 75) - 0.138 * state.I);
  assert.notEqual(actual.I, original.I);
  assert.throws(() => patient.computeDerivatives(time, state, { iir: 1, carbs: 0 }), /delayed/);
});

test('all arms start at one plasma/action/glucose equilibrium with appropriate SC prehistory', async () => {
  const engines = await Promise.all(ARMS.map(arm => prepare(config(arm, false))));
  const baseline = engines[0];
  for (const engine of engines) {
    assert.equal(engine.basal, baseline.basal);
    for (const key of ['Q1', 'Q2', 'I', 'x1', 'x2', 'x3', 'D1', 'D2']) assert.equal(engine.initial[key], baseline.initial[key]);
    const derivatives = engine.patient.computeDerivatives(new Date(START), engine.initial,
      { iir: engine.basal, carbs: 0, lit002_delayed_iir: engine.basal });
    for (const value of Object.values(derivatives)) close(value, 0);
    const rows = []; runPrepared(engine, row => rows.push(row));
    for (const row of rows) {
      close(row.glucose_mg_dl, config().equilibrium_glucose_mg_dl);
      close(row.insulin_mU_L, baseline.initial.I);
      close(row.appearance_mU_min, baseline.basal * 1000 / 60);
    }
  }
  const matched = engines[1].initial.S1 + engines[1].initial.S2;
  const hybrid = engines[2].initial.S1 + engines[2].initial.S2 + baseline.basal * 1000 / 60 * config().absorption.tau_min;
  close(matched, hybrid);
});

test('native baseline wrapper is exactly the unmodified native patient under identical clock and input', async () => {
  const cfg = config();
  const wrapped = await prepare(cfg);
  const rows = []; runPrepared(wrapped, row => rows.push(row));
  const { Cambridge, Solver } = await nativeModules();
  const direct = new Cambridge({ Gpeq: cfg.equilibrium_glucose_mg_dl });
  const basal = direct.computeIIR(cfg.equilibrium_glucose_mg_dl, new Date(START));
  direct.setInitialState(direct.computeSteadyState({ iir: basal }, new Date(START)));
  const solver = new Solver(); solver._tol = 0.001; solver.reset(0.25);
  direct.reset(new Date(START), 101, solver);
  const times = new Set([0, 15.62 * 60000, 20.62 * 60000]);
  for (let i = 0; i <= 160; i += 1) times.add(i * 15000);
  const ordered = [...times].sort((a, b) => a - b);
  let previous = 0;
  const expected = new Map();
  for (const elapsed of ordered) {
    if (elapsed > previous) {
      const midpoint = (elapsed + previous) / 120000;
      const input = { iir: basal + (midpoint >= 10 && midpoint < 15 ? 24 : 0),
        carbs: midpoint >= 10 && midpoint < 25 ? 40 / 15 : 0 };
      direct.update(new Date(START + elapsed), () => input);
    }
    previous = elapsed;
    expected.set(elapsed / 60000, { ...direct.getState() });
  }
  for (const row of rows) assert.deepEqual(row.state, expected.get(row.time_min));
});

test('all arms have identical event timestamps, actual delivery and meals; delay is causal', async () => {
  const traces = [];
  for (const arm of ARMS) {
    const rows = [];
    await runCase(config(arm), { onRow: row => rows.push(row) });
    traces.push(rows);
  }
  for (const rows of traces) {
    assert.deepEqual(rows.map(row => row.time_min), traces[0].map(row => row.time_min));
    assert.deepEqual(rows.map(row => row.delivered_u_h), traces[0].map(row => row.delivered_u_h));
    assert.deepEqual(rows.map(row => row.intake_g_min), traces[0].map(row => row.intake_g_min));
    close(rows.at(-1).cumulative_delivered_mU - rows[0].delivered_u_h * 1000 * 40 / 60, 2000);
    close(rows.at(-1).cumulative_carbohydrates_g, 40);
  }
  const hybrid = traces[2];
  const first = hybrid[0];
  for (const row of hybrid.filter(row => row.time_min <= 15.62)) {
    close(row.state.S1, first.state.S1);
    close(row.state.S2, first.state.S2);
    close(row.insulin_mU_L, first.insulin_mU_L);
  }
  assert(hybrid.find(row => row.time_min === 16).state.S1 > first.state.S1);
  for (const row of hybrid) close(row.cumulative_delivered_mU - row.cumulative_delayed_delivered_mU,
    row.delay_queue_mU - first.delay_queue_mU, 1e-9);
});
