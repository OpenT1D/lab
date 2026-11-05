/** Standard-library kernel checks; no simulator is installed or imported. */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {SampledAudit1} from './lt1_sampled.mjs';
const fixture = JSON.parse(readFileSync(new URL('./cases.json', import.meta.url))).lt1_cambridge;
const sample = (measured, available, glucose) => ({measured_min: measured,
  available_min: available, glucose_mg_dl: glucose});
// New arithmetic-only criterion: two operations, bounded fixture values.
// Keep binary output untouched; native direct/wrapped parity must still be exact.
const arithmetic = (actual, expected) => assert.ok(
  Math.abs(actual - expected) <= 2 * Number.EPSILON * Math.max(1, Math.abs(expected)));

test('independent Decimal transcript, reset, off-grid and terminal hold', () => {
  const kernel = new SampledAudit1(1.2, 20);
  for (let repeat = 0; repeat < 2; repeat++) {
    kernel.reset();
    for (const row of fixture.rows) {
      const {fresh, ...observation} = row.observation;
      const result = kernel.update(row.time_min, observation);
      arithmetic(result.command_u_h, row.command_u_h);
      assert.equal(result.transition.previous_mg_dl, row.previous_mg_dl);
      assert.equal(result.transition.fresh, fresh);
      for (const offset of [2.5, 3.5, 4]) {
        assert.deepEqual(kernel.update(row.time_min + offset),
          {command_u_h: result.command_u_h, transition: null});
      }
    }
    const held = kernel.rate;
    assert.deepEqual(kernel.update(20), {command_u_h: held, transition: null});
    arithmetic(held, 1.8);
    assert.equal(kernel.previous, 60);
  }
});

test('six ticks in thirty minutes, no terminal memory transition', () => {
  const kernel = new SampledAudit1(1.2);
  for (let t = 0; t < 30; t += 5) kernel.update(t, sample(t, t, 120));
  assert.equal(kernel.next, 30);
  assert.deepEqual(kernel.update(30), {command_u_h: 1.2, transition: null});
  assert.equal(kernel.source, 25);
});

test('full reset state equals fresh construction, including failed initialization', () => {
  const kernel = new SampledAudit1(1.2);
  const fresh = new SampledAudit1(1.2);
  assert.deepEqual(kernel, fresh);
  kernel.update(0, sample(0, 0, 180));
  kernel.update(5, sample(5, 5, 60));
  kernel.reset();
  assert.deepEqual(kernel, fresh);
  assert.throws(() => kernel.update(0, sample(0, 5, 999)), /observation-clock/);
  assert.deepEqual(kernel, fresh);
  assert.equal(kernel.update(0, sample(0, 0, 120)).command_u_h, 1.2);
});

test('duplicate, reversed and missed ticks refuse before state changes', () => {
  const kernel = new SampledAudit1(1.2);
  kernel.update(0, sample(0, 0, 180));
  for (const t of [0, 6]) {
    assert.throws(() => kernel.update(t, sample(5, 5, 60)), /clock|missed-tick/);
    assert.equal(kernel.previous, 180);
  }
  kernel.update(5, sample(5, 5, 60));
  assert.throws(() => kernel.update(4), /callback-clock/);
});

test('causal availability, changed stale sample and old release refuse', () => {
  const kernel = new SampledAudit1(1.2);
  kernel.update(0, sample(0, 0, 120));
  for (const value of [sample(5, 10, 60), sample(0, 0, 180), sample(false, 0, 120),
    {...sample(5, 5, 60), actual_meal: 40}]) {
    assert.throws(() => kernel.update(5, value), /observation-clock|changed-sample|number|fields/);
  }
  kernel.update(5, sample(5, 5, 180));
  assert.throws(() => kernel.update(10, sample(0, 0, 120)), /observation-clock/);
  assert.throws(() => kernel.update(7, sample(5, 5, 180)), /non-tick-observation/);
});

test('reset memory precedes initial observation; both clamps are required', () => {
  for (const [basal, initial, expected] of [[1.2, 1000, 3], [0.6, 0, 0]]) {
    const kernel = new SampledAudit1(basal);
    assert.equal(kernel.update(0, sample(0, 0, initial)).command_u_h, basal);
    assert.equal(kernel.update(5, sample(5, 5, 120)).command_u_h, expected);
  }
  for (const basal of [NaN, Infinity, -1, 3.1, true]) {
    assert.throws(() => new SampledAudit1(basal), /number|settings/);
  }
});
