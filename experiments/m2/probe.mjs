/** Bounded host feasibility check: native LT1 loop behind a controller boundary. */
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { SOURCE, verifySource } from '../m0/lt1/setup.mjs';
import { encode, hash, record, compare } from '../m0/lt1/record.mjs';

verifySource();
const output = resolve(process.argv[2]);
mkdirSync(output);
const upstream = p => import(pathToFileURL(resolve(SOURCE, p)).href);
const { default: Simulator } = await upstream('src/core/Simulator.ts');
const { patient, sensor, controller, pump, meals, simOptions } = await upstream(
  'examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts');
const sim = new Simulator();
sim.setPatient(patient); sim.setSensor(sensor); sim.setActuator(pump);
sim.setMeals(meals); sim.setOptions(simOptions); sim.setController(controller);
const execute = callback => { sim.setCallback(callback); sim.runSimulation(); };
record(resolve(output, 'direct'), execute);
let updates = 0;
const boundary = {
  reset: (...args) => { updates = 0; controller.reset(...args); },
  getNextUpdateTime: t => controller.getNextUpdateTime(t),
  update: (t, s, announcements) => {
    // Copy only the allowed measurement and already delivered announcements.
    const glucose = s.CGM();
    assert(Number.isFinite(glucose));
    const memory = Object.fromEntries(Object.entries(announcements).map(([id, a]) => {
      assert(a.time <= t);
      return [id, { time: new Date(a.time), start: new Date(a.start), carbs: a.carbs }];
    }));
    updates++;
    return controller.update(t, { CGM: () => glucose }, memory);
  },
  getOutput: () => controller.getOutput(),
  getInternals: () => controller.getInternals(),
};
sim.setController(boundary);
record(resolve(output, 'bounded'), execute);
const comparison = compare(resolve(output, 'direct/native.jsonl'), resolve(output, 'bounded/native.jsonl'));
const baseline = JSON.parse(await (await import('node:fs/promises')).readFile(
  new URL('../m0/lt1/baseline.json', import.meta.url), 'utf8'));
assert.equal(hash(resolve(output, 'bounded/native.jsonl')), baseline.environments[`${process.platform}/${process.arch}`].output_sha256);
writeFileSync(resolve(output, 'probe.json'), encode({ comparison, updates, historical_output_match: true,
  limitation: 'Native announcement policy only; not yet an M2 adapter or controlled comparison.' }) + '\n');
console.log(encode({ comparison, updates, historical_output_match: true }));
