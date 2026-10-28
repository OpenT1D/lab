// Opt-in real macOS/Chromium probe; never use a researcher's existing workspace.
// node tests/mac_app_probe.mjs APP FRESH_EVIDENCE_DIR PLAYWRIGHT_PROJECT_DIR
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

assert.equal(process.platform, 'darwin');
assert.equal(process.arch, 'arm64');
const [application, evidence, browserProject] = process.argv.slice(2).map(value => path.resolve(value));
assert(application && evidence && browserProject, 'Supply app, fresh evidence and browser project');
assert(!evidence.startsWith(application + path.sep), 'Evidence must be outside the app');
await mkdir(evidence); // Deliberately refuse an existing directory.
const require = createRequire(path.join(browserProject, 'package.json'));
const { chromium, expect: baseExpect } = require('@playwright/test');
const expect = baseExpect.configure({ timeout: 30_000 });
const workspace = path.join(evidence, 'workspace');
await mkdir(workspace);
const marker = path.join(workspace, 'user-marker.txt');
await writeFile(marker, 'This user evidence must survive application replacement and removal.\n');
const markerBytes = await readFile(marker);
const statePath = path.join(evidence, 'session.json');
const timeout = setTimeout(() => { console.error('Mac application probe exceeded 300 seconds'); process.exit(1); }, 300_000);
let state, browser, context, page;
const errors = [], ownedApps = new Set([application]), checks = [];

async function until(read, test, milliseconds = 30_000) {
  const end = Date.now() + milliseconds;
  while (Date.now() < end) {
    try { const value = await read(); if (test(value)) return value; } catch { /* bounded startup */ }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('The expected application state did not arrive');
}
async function api(route, body) {
  const response = await fetch(new URL(route, state.url), {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'X-OpenT1D-Token': state.token, Origin: state.url.replace(/\/$/, ''), 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return response;
}
async function launch(app) {
  ownedApps.add(app);
  await rm(statePath, { force: true });
  execFileSync('/usr/bin/open', ['-n', app, '--args', '--data-dir', workspace, '--state-file', statePath, '--no-browser'], {
    env: { ...process.env, PATH: '/nonexistent', PYTHONPATH: '/nonexistent', VIRTUAL_ENV: '/nonexistent' },
  });
  state = await until(async () => JSON.parse(await readFile(statePath)), value => Number.isInteger(value.pid));
  const bootstrap = await until(async () => (await api('/api/v1/bootstrap')).json(), value => value.schema === 'opent1d.gui-session/2');
  assert.deepEqual(bootstrap.capabilities, ['mmtt-sensitivity', 'mmtt-sampling']);
  assert.equal(bootstrap.profile, 'desktop');
  const actualPython = execFileSync('/bin/ps', ['-p', String(state.pid), '-o', 'command='], { encoding: 'utf8' });
  assert(actualPython.startsWith(path.join(app, 'Contents/Resources/payload/runtime/bin/python3.12') + ' '));
  return state;
}
async function stop() {
  if (!state) return;
  const pid = state.pid;
  const response = await api('/api/desktop/shutdown', {});
  assert.equal(response.status, 202);
  await until(async () => {
    try { process.kill(pid, 0); return false; } catch (error) { if (error.code === 'ESRCH') return true; throw error; }
  }, Boolean, 45_000);
  state = undefined;
}
async function inventory(folder) {
  const result = {};
  async function visit(directory) {
    for (const item of await readdir(directory, { withFileTypes: true })) {
      const target = path.join(directory, item.name);
      if (item.isDirectory()) await visit(target);
      else {
        assert(item.isFile(), 'Only regular bundle/evidence files are expected');
        result[path.relative(folder, target)] = createHash('sha256').update(await readFile(target)).digest('hex');
      }
    }
  }
  await visit(folder);
  return result;
}
async function download(prefix, suffix) {
  const event = page.waitForEvent('download');
  await page.locator(`#${prefix}-download-json`).click();
  const file = await event;
  const target = path.join(evidence, `${suffix}-report.json`);
  await file.saveAs(target);
  assert.equal(await file.failure(), null);
  return readFile(target);
}
async function prepare(task, draws = 32) {
  await page.goto(state.url);
  await page.locator(`#open-${task.view}`).click();
  await page.locator(`#${task.prefix}-case`).selectOption(task.example);
  await page.locator(`#${task.prefix}-example`).click();
  await expect(page.locator(`#${task.prefix}-validation`)).toContainText('visits loaded');
  await page.locator(`#${task.prefix}-display-name`).fill(`Mac probe ${task.task} ${draws}`);
  await page.locator(`#${task.prefix}-settings-details > summary`).click();
  await page.locator(`#${task.prefix}-draws`).fill(String(draws));
}
async function freeze(task) {
  await page.locator(`#${task.prefix}-freeze`).click();
  await expect(page.locator(`#${task.prefix}-plan-state`)).toContainText('Ready to run');
}
const tasks = [
  { prefix: 'obs', view: 'observations', example: 'increase', task: 'mmtt-sensitivity' },
  { prefix: 'sam', view: 'sampling', example: 'information-loss', task: 'mmtt-sampling' },
];
const saved = [];
let original;
try {
  original = await inventory(application);
  await launch(application);
  const initialPid = state.pid;
  await launch(application);
  assert.equal(state.pid, initialPid);
  checks.push('LaunchServices opens included interpreter with hostile PATH/PYTHONPATH; double launch reuses server');
  for (const route of ['files', 'm3/bootstrap', 'campaigns/configurations', 'library/roots', 'durable/bootstrap']) {
    assert.equal((await api('/api/v1/' + route)).status, 403);
    assert.equal((await api('/api/v1/' + route, {})).status, 403);
  }
  browser = await chromium.launch();
  context = await browser.newContext({ acceptDownloads: true });
  await context.tracing.start({ screenshots: true, snapshots: true });
  page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(state.url);
  for (const id of ['open-m3', 'new-study', 'open-library', 'workspace-more']) await expect(page.locator(`#${id}`)).toBeHidden();
  checks.push('Only two tasks exposed; native/library/campaign/export APIs refused');
  await prepare(tasks[0]);
  await page.locator('#obs-draws').fill('31');
  await page.locator('#obs-freeze').click();
  await expect(page.locator('#obs-form-error')).toContainText('32 to 1024');
  await expect(page.locator('#obs-run')).toBeDisabled();
  checks.push('Invalid draw count remains visible and cannot run');
  for (const task of tasks) {
    await prepare(task);
    await freeze(task);
    await page.locator(`#${task.prefix}-run`).click();
    await expect(page.locator(`#${task.prefix}-execution`)).toHaveText('Analysis finished · results complete');
    const entry = page.locator(`#${task.prefix}-analysis-list button`).filter({ hasText: `Mac probe ${task.task} 32` });
    const id = await entry.getAttribute('data-entry-id');
    const archive = path.join(workspace, 'results/gui', task.view, 'archives', id, 'archive');
    const bytes = await download(task.prefix, task.prefix);
    assert.deepEqual(bytes, await readFile(path.join(archive, 'report.json')));
    const report = JSON.parse(bytes);
    assert.equal(report.task, task.task);
    assert.equal(report.execution_status, 'completed');
    assert.equal(report.kind, 'synthetic');
    assert.equal(report.human_evaluation, false);
    saved.push({ task, id, archive, bytes, inventory: await inventory(archive) });
    await page.screenshot({ path: path.join(evidence, `${task.prefix}-complete.png`), fullPage: true });
    checks.push(`${task.task}: example → freeze → real worker → download`);
  }
  await prepare(tasks[1], 1024);
  await freeze(tasks[1]);
  const launched = page.waitForResponse(value => value.request().method() === 'POST' && /\/sampling\/configurations\/[^/]+\/run$/.test(value.url()));
  await page.locator('#sam-run').click();
  const job = await (await launched).json();
  const phase = path.join(workspace, 'results/gui/sampling/archives', job.sampling_entry_id, 'archive/studies/full/execution.json');
  await until(async () => JSON.parse(await readFile(phase)).phase, value => value === 'analysis');
  await page.locator('#sam-cancel').click();
  await expect(page.locator('#sam-execution')).toHaveText('Analysis interrupted');
  const interrupted = JSON.parse(await download('sam', 'interrupted'));
  assert.equal(interrupted.execution_status, 'interrupted');
  assert(interrupted.coverage.not_attempted_draw_pairs > 0);
  await page.locator('#sam-reconstruct').click();
  await expect(page.locator('#sam-result-detail')).toContainText('Saved report checked');
  const journal = JSON.parse(await readFile(path.join(workspace, 'results/gui', job.id, 'job.json')));
  assert.equal(journal.cleanup_forced, false);
  assert.deepEqual(journal.remaining_owned_processes || [], []);
  checks.push('Controlled analysis-phase cancellation retains reconstructable partial evidence');
  await stop();
  const relocated = path.join(evidence, 'relocated', 'OpenT1D.app');
  await cp(application, relocated, { recursive: true });
  await launch(relocated);
  for (const item of saved) {
    await page.goto(`${state.url}#${item.task.view}`);
    await page.locator(`#${item.task.prefix}-analysis-list button[data-entry-id="${item.id}"]`).click();
    await expect(page.locator(`#${item.task.prefix}-execution`)).toHaveText('Analysis finished · results complete');
    await page.locator(`#${item.task.prefix}-reconstruct`).click();
    await expect(page.locator(`#${item.task.prefix}-result-detail`)).toContainText('Saved report checked');
    assert.deepEqual(await download(item.task.prefix, item.task.prefix + '-reopened'), item.bytes);
    assert.deepEqual(await inventory(item.archive), item.inventory);
  }
  await stop();
  assert.deepEqual(await inventory(application), original);
  await rm(relocated, { recursive: true });
  assert.deepEqual(await readFile(marker), markerBytes);
  for (const item of saved) assert.deepEqual(await inventory(item.archive), item.inventory);
  await cp(application, relocated, { recursive: true });
  await launch(relocated);
  for (const task of tasks) {
    const response = await api(`/api/v1/${task.view}/entries`);
    assert.equal(response.status, 200);
  }
  await stop();
  await rm(relocated, { recursive: true });
  assert.deepEqual(await readFile(marker), markerBytes);
  checks.push('Relocation, app removal/replacement and reopening preserve old report bytes and unrelated user file');
  assert.deepEqual(errors, []);
  const manifest = JSON.parse(await readFile(path.join(application, 'Contents/Resources/payload/package-manifest.json')));
  await writeFile(path.join(evidence, 'receipt.json'), JSON.stringify({
    build_id: manifest.build_id, source_revision: manifest.source.revision,
    runtime: manifest.runtime.version, browser: browser.version(), checks,
    page_errors: errors, signed_developer_id: false, notarised: false,
  }, null, 2) + '\n');
  console.log(JSON.stringify({ evidence, checks: checks.length, build_id: manifest.build_id }));
} catch (error) {
  if (page) await page.screenshot({ path: path.join(evidence, 'failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  clearTimeout(timeout);
  if (context) await context.tracing.stop({ path: path.join(evidence, 'trace.zip') });
  if (browser) await browser.close();
  if (state) await stop().catch(() => {});
  // Only native launchers from this invocation's explicit app paths are owned.
  const processes = execFileSync('/bin/ps', ['-axo', 'pid=,command='], { encoding: 'utf8' });
  for (const line of processes.split('\n')) {
    const match = line.trim().match(/^(\d+)\s+(.+)$/);
    if (match && [...ownedApps].some(app => match[2] === path.join(app, 'Contents/MacOS/OpenT1D'))) {
      try { process.kill(Number(match[1]), 'SIGTERM'); } catch { /* already exited */ }
    }
  }
}
