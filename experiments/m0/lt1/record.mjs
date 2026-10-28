/** Recording/validation only; synthetic tests do not establish model validity. */
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export const START = Date.parse('2024-07-20T00:00:00Z');
export const hash = (path) => createHash('sha256').update(readFileSync(path)).digest('hex');
export const encode = (value) => JSON.stringify(value, (_key, v) =>
  typeof v === 'number' && !Number.isFinite(v) ? { nonfinite: String(v) } : v);
export function finite(value) {
  if (typeof value === 'number' && !Number.isFinite(value)) throw Error('Non-finite numeric signal');
  if (value && typeof value === 'object') {
    if ('nonfinite' in value) throw Error('Non-finite numeric signal');
    for (const v of Object.values(value)) finite(v);
  }
}
// This is the pinned Cambridge/MPC fixture's schema, not a generic LT1 contract.
const SIGNALS = {
  x: ['Q1', 'Q2', 'S1', 'S2', 'I', 'x1', 'x2', 'x3', 'D1', 'D2'],
  y: ['Gp'], u: ['iir', 'carbs', 'meal', 'exercise'], c: ['iir'],
};
export function validateSignals(row, index) {
  const schema = { ...SIGNALS, s: index % 5 === 0 ? ['CGM'] : [] };
  for (const [group, fields] of Object.entries(schema)) {
    const values = row[group];
    if (!values || Array.isArray(values) || typeof values !== 'object' ||
        Object.keys(values).length !== fields.length) throw Error(`Invalid signal schema ${group}`);
    for (const field of fields) {
      if (!Number.isFinite(values[field])) throw Error(`Missing or non-finite signal ${group}.${field}`);
    }
  }
}
export const textHash = text => createHash('sha256').update(text).digest('hex');
export function checkBaseline(path, manifest, baseline = JSON.parse(readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), 'baseline.json'), 'utf8'))) {
  if (!Object.hasOwn(baseline.environments, manifest.platform)) {
    throw Error(`No reviewed baseline for ${manifest.platform}`);
  }
  const expected = baseline.environments[manifest.platform];
  for (const [key, value] of Object.entries(expected)) {
    if ((key === 'output_sha256' ? hash(path) : manifest[key]) !== value) {
      throw Error(`Historical baseline differs: ${key}; investigate before updating`);
    }
  }
  return { matched: true, platform: manifest.platform, output_sha256: hash(path) };
}
export function readRows(path) {
  const text = readFileSync(path, 'utf8').trim();
  return text ? text.split('\n').map((line) => JSON.parse(line)) : [];
}
export function validateRows(rows) {
  if (rows.length !== 1441) throw Error('Expected 1441 native state rows');
  let insulin = 0;
  let carbs = 0;
  for (const [i, r] of rows.entries()) {
    if (Date.parse(r.t) !== START + i * 60000) throw Error('Unexpected timestamp or cadence');
    validateSignals(r, i);
    if (r.u.iir < 0) throw Error('Negative delivered insulin');
    const mealRate = i >= 480 && i < 495 ? 40 / 15 : 0;
    if (r.u.carbs !== mealRate) throw Error('Meal ingestion differs from reference');
    if (r.u.meal !== (i === 480 ? 40 : 0)) throw Error('Meal event differs from reference');
    const announcement = r.a?.['0'];
    if (Object.keys(r.a ?? {}).length !== 1 || announcement?.carbs !== 40 ||
        Date.parse(announcement?.start) !== START + 480 * 60000 ||
        Date.parse(announcement?.time) !== START) throw Error('Announcement differs from reference');
    if (i % 5 === 0) {
      if (r.s.CGM !== r.y.Gp) throw Error('IdealCGM sampling differs from reference');
    } else if ('CGM' in r.s) throw Error('Unexpected sensor sample');
    if (i < 1440) {
      insulin += r.u.iir / 60;
      carbs += r.u.carbs;
    }
  }
  return {
    rows: rows.length, duration_minutes: 1440, meal_total_g: carbs,
    delivered_insulin_U: insulin, final_Gp_mg_dL: rows.at(-1).y.Gp,
    min_Gp_mg_dL: Math.min(...rows.map(r => r.y.Gp)),
    max_Gp_mg_dL: Math.max(...rows.map(r => r.y.Gp)),
    glucose_semantics: 'instantaneous plasma Gp; IdealCGM samples every five minutes',
  };
}
export function record(output, simulate, metadata = {}) {
  mkdirSync(output, { recursive: false });
  const path = resolve(output, 'native.jsonl');
  writeFileSync(path, '');
  const manifest = { ...metadata, status: 'started' };
  const save = () => writeFileSync(resolve(output, 'manifest.json'), encode(manifest) + '\n');
  save();
  const started = performance.now();
  try {
    simulate((row) => {
      appendFileSync(path, encode(row) + '\n');
      validateSignals(row, manifest.rows_recorded ?? 0);
      manifest.rows_recorded = (manifest.rows_recorded ?? 0) + 1;
    });
    const rows = readRows(path);
    manifest.summary = validateRows(rows);
    // Same G/u fields as the upstream helper; full records remain available.
    writeFileSync(resolve(output, 'reference.csv'), 'Time,G,u\n' + rows.map((r, i) =>
      `${i},${r.y.Gp},${r.u.iir}\n`).join(''));
    manifest.native_sha256 = hash(path);
    manifest.status = 'completed';
  } catch (error) {
    manifest.status = 'failed';
    manifest.error = String(error);
    writeFileSync(resolve(output, 'failure.log'), error.stack ?? String(error));
    throw error;
  } finally {
    manifest.elapsed_seconds = (performance.now() - started) / 1000;
    save();
  }
  return manifest;
}
export function compare(left, right, reportOnly = false) {
  const a = readRows(left); const b = readRows(right);
  validateRows(a); validateRows(b);
  const identical = encode(a) === encode(b);
  const report = { exact_native_replay: identical, tolerance_applied: false,
    max_absolute_Gp_mg_dL: Math.max(...a.map((r, i) => Math.abs(r.y.Gp - b[i].y.Gp))),
    max_absolute_iir_U_h: Math.max(...a.map((r, i) => Math.abs(r.u.iir - b[i].u.iir))),
  };
  if (!identical && !reportOnly) throw Error(`Replay differs: ${encode(report)}`);
  return report;
}
