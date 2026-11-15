import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const assets = process.argv[2] || fileURLToPath(new URL('../packaging/sdk/opent1d_lab/_gui_assets/', import.meta.url));
const source = readFileSync(path.join(assets, 'workbench-store.js'), 'utf8');
const { WorkbenchStore } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const plan = 'a'.repeat(64), previous = 'b'.repeat(64), attempt = 'c'.repeat(64);
const saved = (extra = {}) => ({ id: 'd'.repeat(32), project: 'project', task: 'mmtt-sensitivity', name: 'Paired response', revision: 3, parent: null, frozen_plan: plan, validation: { valid: true, revision: 3 }, files: { 'package.json': '{}', 'observations.csv': 'saved observations', 'settings.json': '{}' }, ...extra });
const complete = { completeness: 'complete', execution_status: 'succeeded', payload: 'native', slot_statuses: { paired: 'complete' } };
const memory = () => { const values = new Map(); return { setItem: (key, value) => values.set(key, value), getItem: key => values.get(key) || null, removeItem: key => values.delete(key) }; };
function create(fetcher = async () => { throw new Error('Unexpected request'); }) {
  const store = new WorkbenchStore({ token: 'controlled-token', storage: memory(), fetcher });
  store.data = { workspace: '/synthetic-execution-fixture', runtime_revision: 0, installation: { tasks: ['mmtt-sensitivity', 'mmtt-sampling'] }, active: null, jobs: [], drafts: [], projects: [{ id: 'project', name: 'Execution fixture', info: { plans: [{ id: plan, task: 'mmtt-sensitivity' }, { id: previous, task: 'mmtt-sensitivity' }], attempts: [] } }] };
  store.projectId = 'project'; store.accept(saved());
  store.readiness = { project: 'project', plan, runtime: 0, result: { metadata_valid: true, runtimes_ready: true } };
  return store;
}
const response = value => ({ ok: true, json: async () => value });
const until = async predicate => { for (let i = 0; i < 100; i++) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 5)); } throw new Error('Fixture condition was not observed'); };

test('reviewed saved inputs freeze without starting an analysis', async () => {
  const store = create(), calls = [];
  store.accept(saved({ frozen_plan: null }));
  store.action = async (operation, args) => { calls.push([operation, args]); return { plan }; };
  store.request = async () => saved({ revision: 4, validation: { valid: true, revision: 4 } });
  assert.deepEqual(await store.freeze(), { plan });
  assert.deepEqual(calls, [['freeze', { draft: saved().id, revision: 3, name: 'Paired response', parent: null }]]);
  assert.equal(store.record.revision, 4); assert.equal(store.selectedPlanId, plan); assert.equal(store.ready, false);
});

test('editing reviewed scientific input invalidates the old ready selection', async () => {
  const store = create(), calls = [];
  assert.equal(store.ready, true);
  store.edit(store.name, { ...store.files, 'observations.csv': 'new observations' }, false);
  store.action = async (operation, args) => { calls.push(operation); return saved({ revision: 4, frozen_plan: null, validation: null, files: args.files }); };
  assert.equal(store.selectedPlanId, null); assert.equal(store.ready, false);
  await assert.rejects(store.runPlan(), /Check this frozen plan/);
  assert.deepEqual(calls, ['draft_save']); assert.equal(store.files['observations.csv'], 'new observations');
  assert.equal(store.plans.length, 2, 'frozen plans must remain available after editing');
});

test('a late freeze annotation cannot select old inputs after a newer edit', async () => {
  const store = create(), calls = [];
  store.accept(saved({ frozen_plan: null }));
  let finish, requested = false;
  store.action = async (operation, args) => {
    calls.push(operation);
    return operation === 'freeze' ? { plan } : saved({ revision: 4, frozen_plan: null, validation: null, files: args.files });
  };
  store.request = async () => { requested = true; return new Promise(resolve => { finish = resolve; }); };
  const freezing = store.freeze();
  await until(() => requested);
  store.edit(store.name, { ...store.files, 'observations.csv': 'newer than frozen inputs' }, false);
  finish(saved({ revision: 4 })); await freezing;
  assert.equal(store.selectedPlanId, null); assert.equal(store.ready, false);
  await assert.rejects(store.runPlan(), /Check this frozen plan/);
  assert.deepEqual(calls, ['freeze', 'draft_save']);
  assert.equal(store.record.files['observations.csv'], 'newer than frozen inputs');
});

test('recovered post-freeze input bytes cannot silently run the older plan', async () => {
  const store = create(), calls = [];
  store.storage.setItem(store.key(), JSON.stringify({ revision: 3, name: store.name, files: { ...store.files, 'observations.csv': 'recovered new observations' }, parent: null }));
  store.accept(saved(), true);
  assert.equal(store.dirty, true); assert.equal(store.conflict, false);
  assert.equal(store.selectedPlanId, null); assert.equal(store.ready, false);
  store.action = async (operation, args) => { calls.push(operation); return saved({ revision: 4, frozen_plan: null, validation: null, files: args.files }); };
  await assert.rejects(store.runPlan(), /Check this frozen plan/);
  assert.deepEqual(calls, ['draft_save']); assert.equal(store.record.files['observations.csv'], 'recovered new observations');
});

test('a ready check belongs only to the explicitly selected plan and runtime', async () => {
  const store = create();
  store.selectPlan(previous); assert.equal(store.ready, false);
  store.action = async () => ({ metadata_valid: true, runtimes_ready: true });
  await store.checkPlan(); assert.equal(store.ready, true);
  store.data.runtime_revision++; assert.equal(store.ready, false);
  store.selectPlan(plan); assert.equal(store.ready, false);
});

test('actual unfinished outcome requires explicit stopped-executor recovery before retry', async () => {
  const store = create(), calls = [];
  store.project.info.attempts.push({ id: attempt, plan, ordinal: 1, outcome: 'unfinished' });
  store.action = async (operation, args) => { calls.push([operation, args]); return { attempt }; };
  await assert.rejects(store.runPlan(), /unfinished attempt/);
  for (const consent of [false, 1, 'true', undefined]) await assert.rejects(store.recoverAttempt(attempt, consent), /previous executor has stopped/);
  assert.deepEqual(calls, []);
  await store.recoverAttempt(attempt, true);
  assert.deepEqual(calls, [['recover', { attempt, execution_stopped: true }]]);
});

test('retry records latest retained attempt and leaves earlier attempts intact', async () => {
  const store = create(), first = { id: previous, plan, ordinal: 1, outcome: complete }, last = { id: attempt, plan, ordinal: 2, retry_of: previous, outcome: { ...complete, completeness: 'incomplete', execution_status: 'interrupted' } };
  store.project.info.attempts.push(first, last);
  let args;
  store.action = async (operation, values) => { assert.equal(operation, 'run'); args = values; return { attempt: 'e'.repeat(64) }; };
  await store.runPlan();
  assert.deepEqual(args, { plan, retry_of: attempt }); assert.deepEqual(store.attempts, [first, last]);
});

test('terminal execution failure rereads the authoritative ledger and retains partial attempts', async () => {
  let operation, store; const calls = [];
  store = create(async (route, options) => {
    if (route === '/api/actions') { operation = JSON.parse(options.body).operation; calls.push(operation); return response({ id: operation, project: 'project', operation, status: 'running' }); }
    if (route === '/api/jobs/run') return response({ id: 'run', project: 'project', operation: 'run', status: 'error', error: 'Controlled worker interrupted' });
    if (route === '/api/jobs/refresh') return response({ id: 'refresh', project: 'project', operation: 'refresh', status: 'done', result: {} });
    assert.equal(route, '/api/state');
    return response({ ...store.data, active: null, projects: [{ ...store.project, info: operation === 'run' ? null : { plans: [{ id: plan, task: 'mmtt-sensitivity' }], attempts: [{ id: attempt, plan, ordinal: 1, outcome: 'unfinished' }] } }] });
  });
  await assert.rejects(store.action('run', { plan, retry_of: null }), /Controlled worker interrupted/);
  assert.deepEqual(calls, ['run', 'refresh']); assert.equal(store.attempts[0].outcome, 'unfinished');
  assert.equal(store.locked, false); assert.equal(store.lastAction.status, 'error');
});

test('owned running action exposes cancellation and records its incomplete terminal outcome', async () => {
  let store, cancelled = false; const seen = [];
  const job = { id: 'running-job', project: 'project', operation: 'run', arguments: { plan }, phase: 'Calling installed worker', cancelable: true, status: 'running' };
  store = create(async route => {
    if (route === '/api/actions') return response(job);
    if (route === '/api/jobs/running-job/cancel') { cancelled = true; return response({ requested: true }); }
    if (route === '/api/jobs/running-job') return response(cancelled ? { ...job, status: 'done', cancelable: false, result: { attempt, result: { completeness: 'incomplete', execution_status: 'interrupted' } } } : { ...job, elapsed_seconds: 0.2 });
    assert.equal(route, '/api/state'); return response({ ...store.data, active: cancelled ? null : job.id, jobs: [job] });
  });
  store.notify = value => seen.push(value.activeJob?.phase);
  const running = store.action('run', { plan, retry_of: null });
  await until(() => store.activeJob?.cancelable);
  assert.equal(store.locked, true); assert.equal(await store.cancelRun(), true);
  const result = await running;
  assert.equal(result.result.completeness, 'incomplete'); assert.equal(store.locked, false);
  assert.ok(seen.includes('Calling installed worker')); assert.ok(seen.includes('Stop requested; waiting for SDK cleanup'));
});

test('reopening a server-restored project reads its saved plans and all attempts without execution', async () => {
  const store = create(), calls = [];
  store.project.info = null;
  store.action = async operation => { calls.push(operation); store.project.info = { plans: [{ id: plan, task: 'mmtt-sensitivity' }], attempts: [{ id: previous, plan, ordinal: 1, outcome: complete }, { id: attempt, plan, ordinal: 2, outcome: 'unfinished' }] }; };
  assert.equal(await store.openProject('project'), true);
  assert.deepEqual(calls, ['refresh']); assert.equal(store.plans.length, 1); assert.equal(store.attempts.length, 2);
});

test('project loading stays explicit until saved concept hydration finishes', async () => {
  const store = create();
  store.project.info = null;
  store.data.drafts = [{ id: saved().id, project: 'project', task: 'mmtt-sensitivity', saved_at: '2026-11-15' }];
  store.action = async () => { store.project.info = { plans: [{ id: plan, task: 'mmtt-sensitivity' }], attempts: [] }; };
  let finish;
  store.request = () => new Promise(resolve => { finish = resolve; });
  const opening = store.openProject('project');
  await until(() => !!finish);
  assert.equal(store.loadingProject, true); assert.equal(store.record, null);
  finish(saved()); await opening;
  assert.equal(store.loadingProject, false); assert.equal(store.record.id, saved().id);
});
