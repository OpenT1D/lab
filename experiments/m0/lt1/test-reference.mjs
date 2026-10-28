import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { START, checkBaseline, compare, encode, finite, hash, readRows, record, validateRows } from './record.mjs';

function fixture() {
  return Array.from({ length: 1441 }, (_, i) => ({
    t: new Date(START + i * 60000).toISOString(), x: Object.fromEntries(['Q1', 'Q2', 'S1', 'S2', 'I', 'x1', 'x2', 'x3', 'D1', 'D2'].map(k => [k, 100])), y: { Gp: 100 },
    u: { iir: 1, exercise: 0, carbs: i >= 480 && i < 495 ? 40 / 15 : 0, meal: i === 480 ? 40 : 0 },
    s: i % 5 === 0 ? { CGM: 100 } : {}, c: { iir: 1 },
    a: { 0: { start: new Date(START + 480 * 60000).toISOString(),
      time: new Date(START).toISOString(), carbs: 40 } },
  }));
}
function temporary(t) {
  const path = mkdtempSync(join(tmpdir(), 'opent1d-lt1-test-'));
  t.after(() => rmSync(path, { recursive: true, force: true }));
  return path;
}
test('synthetic amount/rate integration excludes terminal interval', () => {
  const result = validateRows(fixture());
  assert.ok(Math.abs(result.delivered_insulin_U - 24) < 1e-10);
  assert.ok(Math.abs(result.meal_total_g - 40) < 1e-10);
});
test('missing file and incomplete traces fail', () => {
  assert.throws(() => readRows('/nonexistent/opent1d-lt1-record.jsonl'));
  assert.throws(() => validateRows(fixture().slice(0, 100)), /1441/);
});
test('bad cadence, missing glucose and wrong announcements fail', () => {
  const rows = fixture(); rows[1].t = rows[0].t;
  assert.throws(() => validateRows(rows), /timestamp/);
  const missing = fixture(); delete missing[0].y.Gp;
  assert.throws(() => validateRows(missing), /signal schema y/);
  const announcement = fixture(); announcement[0].a[0].carbs = 20;
  assert.throws(() => validateRows(announcement), /Announcement/);
});
test('nonfinite values are tagged and rejected, not turned into null', () => {
  const serialized = encode({ y: { Gp: NaN } });
  assert.match(serialized, /nonfinite/);
  assert.throws(() => finite(JSON.parse(serialized)), /Non-finite/);
});
test('failure retains partial records and manifest', t => {
  const out = join(temporary(t), 'failed');
  assert.throws(() => record(out, callback => {
    callback(fixture()[0]); throw Error('injected solver failure');
  }), /injected/);
  assert.equal(readRows(join(out, 'native.jsonl')).length, 1);
  assert.equal(JSON.parse(readFileSync(join(out, 'manifest.json'))).status, 'failed');
  assert.match(readFileSync(join(out, 'failure.log'), 'utf8'), /injected/);
});
test('existing output is never overwritten', t => {
  const out = temporary(t); writeFileSync(join(out, 'sentinel'), 'keep');
  assert.throws(() => record(out, () => {}), /EEXIST/);
  assert.equal(readFileSync(join(out, 'sentinel'), 'utf8'), 'keep');
});
test('replay differences are diagnosed without a pass tolerance', t => {
  const root = temporary(t);
  const a = join(root, 'a'); const b = join(root, 'b');
  record(a, callback => fixture().forEach(callback));
  record(b, callback => {
    const rows = fixture(); rows[1].y.Gp += 0.1; rows.forEach(callback);
  });
  assert.throws(() => compare(join(a, 'native.jsonl'), join(b, 'native.jsonl')), /Replay differs/);
  const result = compare(join(a, 'native.jsonl'), join(b, 'native.jsonl'), true);
  assert.equal(result.exact_native_replay, false);
  assert.equal(result.tolerance_applied, false);
});

test('every required native signal rejects missing, null, strings and nonfinite values', () => {
  for (const group of ['x', 'y', 'u', 's', 'c']) {
    for (const field of Object.keys(fixture()[0][group])) {
      for (const invalid of [undefined, null, 'broken', NaN, Infinity, {}, []]) {
        const rows = fixture(); rows[0][group][field] = invalid;
        assert.throws(() => validateRows(rows), /signal/);
      }
    }
    for (const invalid of [{}, [], null]) {
      const rows = fixture(); rows[0][group] = invalid;
      assert.throws(() => validateRows(rows), /signal/);
    }
  }
  // Empty sensor output between sample instants is native and remains valid.
  assert.equal(validateRows(fixture()).rows, 1441);
});
test('malformed callback is retained and fails immediately', t => {
  const output = join(temporary(t), 'bad');
  const row = fixture()[0]; row.x.Q1 = null;
  assert.throws(() => record(output, cb => cb(row)), /signal x.Q1/);
  assert.equal(readRows(join(output, 'native.jsonl'))[0].x.Q1, null);
  assert.equal(JSON.parse(readFileSync(join(output, 'manifest.json'))).status, 'failed');
});
test('historical baseline rejects deterministic drift and changed context', t => {
  const root = temporary(t), path = join(root, 'reference.jsonl');
  writeFileSync(path, fixture().map(encode).join('\n'));
  const context = { platform: 'test', lock_sha256: 'locked' };
  const baseline = { environments: { test: { output_sha256: hash(path), lock_sha256: 'locked' } } };
  assert.equal(checkBaseline(path, context, baseline).matched, true);
  const rows = fixture(); rows.forEach(r => { r.u.iir = 0; });
  writeFileSync(path, rows.map(encode).join('\n'));
  assert.equal(compare(path, path).exact_native_replay, true);
  assert.throws(() => checkBaseline(path, context, baseline), /Historical baseline/);
  for (const platform of ['unknown', '__proto__', 'constructor']) {
    assert.throws(() => checkBaseline(path, { platform }, baseline), /No reviewed baseline/);
  }
  const revised = { environments: { test: { output_sha256: hash(path), lock_sha256: 'locked' } } };
  assert.throws(() => checkBaseline(path, { ...context, lock_sha256: 'changed' }, revised), /lock_sha256/);
});
