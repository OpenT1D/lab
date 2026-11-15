import { test as base, expect } from '../browser/node_modules/@playwright/test/index.mjs';
import { _electron } from '../browser/node_modules/playwright/index.mjs';
import { readFile, readdir, mkdtemp, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';

if (process.platform !== 'darwin' || !process.env.OPENT1D_DESKTOP_BUILD) throw new Error('Select a real Mac build-result.json with OPENT1D_DESKTOP_BUILD.');
const build = JSON.parse(await readFile(process.env.OPENT1D_DESKTOP_BUILD, 'utf8'));
if (build.target !== 'darwin-arm64' || build.sdk.descriptor_schema !== 'opent1d.installed-sdk/4' ||
    (build.source.dirty && process.env.OPENT1D_DESKTOP_ALLOW_DIRTY !== '1')) throw new Error('Select the current clean Mac SDK/4 build; dirty builds require explicit development opt-in.');

// Playwright disposes the application channel on close; retain its ChildProcess
// while the application is alive so cleanup and crash assertions can inspect it.
const processes = new WeakMap();
const ownedProcess = app => processes.get(app);

const test = base.extend({
  desktop: async ({}, use, testInfo) => {
    const folder = await realpath(await mkdtemp(path.join(tmpdir(), 'opent1d-native-window-')));
    const workspace = path.join(folder, 'workspace'), apps = [];
    const launch = async () => {
      const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE; delete env.PYTHONPATH;
      const app = await _electron.launch({ executablePath: build.executable, args: ['--workspace', workspace], env, acceptDownloads: true, timeout: 45000 });
      processes.set(app, app.process());
      apps.push(app);
      const page = await app.firstWindow();
      await expect(page.locator('#new-project')).toBeEnabled();
      return { app, page };
    };
    try { await use({ launch, folder, workspace }); }
    finally {
      for (const app of apps) {
        if (ownedProcess(app).exitCode !== null || ownedProcess(app).signalCode !== null) continue;
        try {
          await app.evaluate(({ dialog }) => { dialog.showMessageBox = async () => ({ response: 1 }); });
          await app.close();
        } catch { /* A test may deliberately crash its owned application. */ }
      }
      // Retain invented workspace state for a failed test's diagnosis.
      if (testInfo.status === testInfo.expectedStatus) await rm(folder, { recursive: true, force: true });
    }
  },
});

async function create(page, title, task = 'mmtt-sensitivity') {
  await page.locator('#new-project').click();
  await page.locator('#project-name').fill(title);
  await page.locator('#new-approach').selectOption(task);
  await page.locator('#confirm-project').click();
  await expect(page.locator('#project-dialog')).not.toBeVisible();
  await expect(page.locator('#workspace')).toBeVisible();
}
async function menu(app, label) {
  await app.evaluate(({ Menu }, label) => {
    const item = Menu.getApplicationMenu().items.find(i => i.label === 'File').submenu.items.find(i => i.label === label);
    if (!item) throw new Error('Missing native menu item: ' + label);
    item.click();
  }, label);
}
async function state(page) {
  return page.evaluate(async () => (await fetch('/api/state', { headers: { 'X-OpenT1D-Token': document.querySelector('meta[name="opent1d-token"]').content } })).json());
}
async function backendPID(app) {
  return app.evaluate(() => process._getActiveHandles().find(h => h.constructor.name === 'ChildProcess' && h.spawnargs?.includes('--workspace'))?.pid);
}
async function gone(pid) {
  await expect.poll(() => { try { process.kill(pid, 0); return false; } catch (error) { if (error.code === 'ESRCH') return true; throw error; } }, { timeout: 15000 }).toBe(true);
}

test('packaged own window, compact/project bounds, both approaches and save-on-native-quit persist', async ({ desktop }, info) => {
  let { app, page } = await desktop.launch();
  const identity = await app.evaluate(({ app, BrowserWindow }) => {
    const window = BrowserWindow.getAllWindows()[0], prefs = window.webContents.getLastWebPreferences();
    return { packaged: app.isPackaged, name: app.name, windows: BrowserWindow.getAllWindows().length, nativeHandle: window.getNativeWindowHandle().length, size: window.getContentSize(), isolated: prefs.contextIsolation, sandbox: prefs.sandbox, node: prefs.nodeIntegration };
  });
  expect(identity).toMatchObject({ packaged: true, name: 'OpenT1D', windows: 1, size: [920, 420], isolated: true, sandbox: true, node: false });
  expect(identity.nativeHandle).toBeGreaterThan(0);
  await page.screenshot({ path: info.outputPath('native-startup.png'), scale: 'css' });
  for (const [task, title] of [['mmtt-sensitivity', 'Paired desktop'], ['mmtt-sampling', 'Sampling desktop']]) {
    await create(page, title, task);
    await expect.poll(async () => (await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].getContentSize()))[0]).toBeGreaterThan(920);
    await page.locator('#research-question').fill(title + ' saved on native quit');
    const pid = await backendPID(app); expect(pid).toBeGreaterThan(0);
    await app.close(); await gone(pid);
    ({ app, page } = await desktop.launch());
    await page.locator('#recent-projects button').filter({ hasText: title }).click();
    await expect(page.locator('#research-question')).toHaveValue(title + ' saved on native quit');
    await expect(page.locator('#approach')).toHaveValue(task);
    await page.locator('#review-study').click();
    await expect(page.locator('#information-dialog')).toContainText('passed the existing task validation');
    await page.locator('#information-dialog .dialog-close').first().click();
    await page.screenshot({ path: info.outputPath(task + '-native-study.png'), scale: 'css' });
    await menu(app, 'Close Project');
    await expect(page.locator('#startup')).toBeVisible();
    await expect.poll(() => app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].getContentSize())).toEqual([920, 420]);
  }
  await info.attach('native-window.json', { body: JSON.stringify({ source: build.source, identity }, null, 2), contentType: 'application/json' });
});

test('native menus protect unapplied inputs and the native folder picker reopens saved work', async ({ desktop }) => {
  const { app, page } = await desktop.launch();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await create(page, 'Native menus');
  const project = (await state(page)).projects[0];
  await page.locator('#assumptions').click();
  await page.locator('#draws').fill('64');
  await app.evaluate(({ dialog }) => {
    globalThis.dialogCalls = [];
    dialog.showMessageBox = async (_window, options) => { globalThis.dialogCalls.push(options); return { response: 2 }; };
    dialog.showOpenDialog = async () => { throw new Error('Cancelled editor must not open a picker'); };
  });
  for (const [index, label] of ['Open Project…', 'New Project…', 'Close Project'].entries()) {
    await menu(app, label);
    await expect.poll(() => app.evaluate(() => globalThis.dialogCalls.length)).toBe(index + 1);
    await expect(page.locator('#files-dialog')).toBeVisible();
    await expect(page.locator('#draws')).toHaveValue('64');
  }
  await menu(app, 'Save');
  await expect(page.locator('#files-dialog')).not.toBeVisible();
  await expect(page.locator('#save-state')).toHaveText('');
  await menu(app, 'Close Project');
  await expect(page.locator('#startup')).toBeVisible();
  await app.evaluate(({ dialog }, projectPath) => {
    dialog.showOpenDialog = async (_window, options) => { globalThis.pickerOptions = options; return { canceled: false, filePaths: [projectPath] }; };
  }, project.path);
  // Same-document anchors must not revoke the main frame's native bridge.
  await page.evaluate(() => { location.hash = 'study-heading'; });
  await menu(app, 'Open Project…');
  await expect(page.locator('#workspace')).toBeVisible();
  expect(await app.evaluate(() => globalThis.pickerOptions.properties)).toEqual(['openDirectory']);
  await page.locator('#assumptions').click();
  await expect(page.locator('#draws')).toHaveValue('64');
  await page.locator('#draws').fill('96');
  await app.evaluate(({ dialog }) => { dialog.showMessageBox = async () => ({ response: 0 }); });
  const pid = await backendPID(app);
  await app.close(); await gone(pid);
  const reopened = await desktop.launch();
  await reopened.page.locator('#recent-projects button').filter({ hasText: 'Native menus' }).click();
  await reopened.page.locator('#assumptions').click();
  await expect(reopened.page.locator('#draws')).toHaveValue('96');
  await reopened.page.locator('#files-dialog .dialog-close').first().click();
  expect(errors).toEqual([]);
});

test('renderer failure can quit without a renderer reply and saved work reopens', async ({ desktop }) => {
  const { app, page } = await desktop.launch();
  await create(page, 'Renderer recovery');
  await page.locator('#research-question').fill('Retained before renderer failure');
  await menu(app, 'Save');
  await expect(page.locator('#save-state')).toHaveText('');
  const pid = await backendPID(app);
  await app.evaluate(({ dialog, BrowserWindow }) => {
    dialog.showMessageBox = async () => ({ response: 1 });
    BrowserWindow.getAllWindows()[0].webContents.forcefullyCrashRenderer();
  }).catch(error => { if (!/closed|crash|disposed/i.test(error.message)) throw error; });
  await expect.poll(() => ownedProcess(app).exitCode !== null || ownedProcess(app).signalCode !== null, { timeout: 15000 }).toBe(true);
  await gone(pid);
  const reopened = await desktop.launch();
  await reopened.page.locator('#recent-projects button').filter({ hasText: 'Renderer recovery' }).click();
  await expect(reopened.page.locator('#research-question')).toHaveValue('Retained before renderer failure');
});

test('native owner crash closes its private service and preserves the saved project', async ({ desktop }) => {
  const { app, page } = await desktop.launch();
  await create(page, 'Owner recovery');
  await page.locator('#research-question').fill('Retained before owner failure');
  await menu(app, 'Save');
  await expect(page.locator('#save-state')).toHaveText('');
  const pid = await backendPID(app);
  ownedProcess(app).kill('SIGKILL');
  await expect.poll(() => ownedProcess(app).signalCode).toBe('SIGKILL');
  await gone(pid);
  const reopened = await desktop.launch();
  await reopened.page.locator('#recent-projects button').filter({ hasText: 'Owner recovery' }).click();
  await expect(reopened.page.locator('#research-question')).toHaveValue('Retained before owner failure');
});


async function savedDraft(page, project) {
  const incoming = await state(page), summary = incoming.drafts.filter(draft => draft.project === project.id).sort((a, b) => b.saved_at.localeCompare(a.saved_at))[0];
  expect(summary).toBeTruthy();
  return page.evaluate(async id => {
    const response = await fetch('/api/drafts/' + id, { headers: { 'X-OpenT1D-Token': document.querySelector('meta[name="opent1d-token"]').content } });
    if (!response.ok) throw new Error('Saved draft read was refused');
    return response.json();
  }, summary.id);
}
async function draws(page, app, count) {
  await page.locator('#assumptions').click();
  await page.locator('#draws').fill(String(count));
  await page.locator('#files-form button[type=submit]').click();
  await menu(app, 'Save');
  await expect(page.locator('#save-state')).toHaveText('');
  await expect(page.locator('#notice')).not.toBeVisible();
}
async function freezeAndCheck(page) {
  await page.locator('#review-study').click();
  await expect(page.getByRole('dialog', { name: 'Review study', exact: true })).toBeVisible();
  await page.locator('#freeze-study').click();
  await expect(page.locator('#information-dialog')).not.toBeVisible();
  await expect(page.locator('#check-study')).toBeEnabled();
  const frozen = await page.locator('#execution-plan').inputValue(); expect(frozen).toMatch(/^[a-f0-9]{64}$/);
  await expect(page.locator('#execution-plan-identity')).toContainText(frozen);
  await page.locator('#check-study').click();
  await expect(page.locator('#run-study')).toBeEnabled();
  await expect(page.locator('#run-study')).toBeFocused();
  return frozen;
}
async function finished(page, count) {
  await expect.poll(async () => {
    const incoming = await state(page), attempts = incoming.projects[0]?.info?.attempts || [];
    return incoming.active === null && attempts.length === count && attempts.every(attempt => typeof attempt.outcome === 'object');
  }, { timeout: 90000 }).toBe(true);
  await expect(page.locator('#execution-attempts article')).toHaveCount(count);
  return (await state(page)).projects[0].info.attempts;
}
async function nativeEvidence(project, attempt) {
  for (const entry of await readdir(path.join(project.path, 'events'))) {
    const folder = path.join(project.path, 'events', entry), event = JSON.parse(await readFile(path.join(folder, 'event.json')));
    if (event.kind === 'finish' && event.data.attempt === attempt) return { ...event.data, native: path.join(folder, 'evidence', 'native') };
  }
  throw new Error('No saved finish evidence for attempt ' + attempt);
}
async function exportExact(page, testInfo, label, filename, original) {
  const waiting = page.waitForEvent('download');
  await page.getByRole('button', { name: label, exact: true }).click();
  const download = await waiting;
  expect(download.suggestedFilename()).toBe(filename);
  const target = testInfo.outputPath(filename);
  await download.saveAs(target);
  expect(await readFile(target)).toEqual(await readFile(original));
}
function processTable() {
  const text = execFileSync('/bin/ps', ['-axo', 'pid=,ppid=,pgid=,lstart=,stat=,command='], { encoding: 'utf8' });
  return text.split('\n').flatMap(line => {
    const match = line.match(/^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+\s+\S+\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4})\s+(\S+)\s+(.*)$/);
    return match ? [{ pid: Number(match[1]), ppid: Number(match[2]), pgid: Number(match[3]), start: match[4], status: match[5], command: match[6] }] : [];
  });
}
function descendants(table, parent) {
  const owned = new Set([parent]);
  for (let i = 0; i < table.length; i++) {
    let changed = false;
    for (const item of table) if (owned.has(item.ppid) && !owned.has(item.pid)) { owned.add(item.pid); changed = true; }
    if (!changed) break;
  }
  return table.filter(item => item.pid !== parent && owned.has(item.pid) && !item.status.startsWith('Z'));
}
async function liveAnalysis(page, app, project) {
  const backend = await backendPID(app); expect(backend).toBeGreaterThan(0);
  let observed;
  await expect.poll(async () => {
    try {
      for (const attempt of await readdir(path.join(project.path, 'work'))) {
        const native = path.join(project.path, 'work', attempt, 'native');
        const execution = JSON.parse(await readFile(path.join(native, 'execution.json')));
        if (execution.phase !== 'analysis' || execution.status !== 'started') continue;
        const table = processTable(), owned = descendants(table, backend);
        const worker = owned.find(item => item.command.includes('--native mmtt-sensitivity run') && item.command.includes(native));
        if (!worker) continue;
        observed = { attempt, backend: table.find(item => item.pid === backend), worker, owned, execution };
        return true;
      }
    } catch (error) { if (!(error instanceof SyntaxError) && !['ENOENT', 'ENOTDIR'].includes(error.code)) throw error; }
    return false;
  }, { intervals: [20, 50, 100], timeout: 30000 }).toBe(true);
  expect(observed.backend).toBeTruthy(); expect(observed.owned.length).toBeGreaterThan(0);
  await expect(page.locator('#cancel-study')).toBeEnabled();
  const incoming = await state(page), job = incoming.jobs.find(job => job.id === incoming.active);
  expect(job).toMatchObject({ operation: 'run', status: 'running', cancelable: true });
  await expect(page.locator('#execution-status')).toContainText(job.id);
  await expect(page.locator('#execution-status')).toContainText(job.arguments.plan);
  return { ...observed, job: job.id };
}
async function identitiesGone(identities) {
  await expect.poll(() => {
    const table = processTable();
    return identities.every(identity => !table.some(item => item.pid === identity.pid && item.start === identity.start && !item.status.startsWith('Z')));
  }, { timeout: 45000 }).toBe(true);
}
function expectSentinel(identity) {
  expect(processTable().find(item => item.pid === identity.pid && item.start === identity.start && !item.status.startsWith('Z'))).toBeTruthy();
}
async function withSentinel(use) {
  const sentinel = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { detached: true, stdio: 'ignore' });
  await once(sentinel, 'spawn');
  const identity = processTable().find(item => item.pid === sentinel.pid); expect(identity).toBeTruthy();
  try { await use(identity); }
  finally {
    if (sentinel.exitCode === null && sentinel.signalCode === null) { const exited = once(sentinel, 'exit'); sentinel.kill('SIGTERM'); await exited; }
  }
}
async function slowStudy(page, app, title) {
  await create(page, title);
  const project = (await state(page)).projects[0], draft = await savedDraft(page, project);
  const supplied = JSON.parse(draft.files['package.json']), prototype = supplied.participants[0];
  expect(supplied.participants).toHaveLength(1);
  const lines = draft.files['observations.csv'].trimEnd().split(/\r?\n/), header = lines.shift(), rows = [];
  expect(lines).toHaveLength(10);
  // Keep complete retry reports below the unchanged shared reader's 16 MiB
  // record limit while retaining enough real numerical work to observe a stop.
  supplied.participants = Array.from({ length: 4 }, (_, index) => {
    const id = 'invented-lifecycle-' + String(index + 1).padStart(2, '0');
    for (const line of lines) rows.push(id + line.slice(line.indexOf(',')));
    return { ...structuredClone(prototype), id };
  });
  await page.locator('#observations').click();
  await page.locator('#input-file').selectOption('package.json');
  await page.locator('#input-text').fill(JSON.stringify(supplied, null, 2) + '\n');
  await page.locator('#input-file').selectOption('observations.csv');
  await page.locator('#input-text').fill([header, ...rows].join('\n') + '\n');
  await page.locator('#files-form button[type=submit]').click();
  await draws(page, app, 1024);
  const plan = await freezeAndCheck(page);
  await page.locator('#run-study').click();
  return { project, plan, observed: await liveAnalysis(page, app, project) };
}
async function reopenPassive(desktop, project, plan, count) {
  const head = await readFile(path.join(project.path, 'HEAD.json'));
  const reopened = await desktop.launch(), { page } = reopened;
  await page.locator('#recent-projects button').filter({ hasText: project.name }).click();
  await expect(page.locator('#execution-attempts article')).toHaveCount(count);
  const incoming = await state(page), restored = incoming.projects.find(item => item.id === project.id);
  expect(incoming.active).toBeNull(); expect(incoming.jobs.some(job => job.operation === 'run')).toBe(false);
  expect(restored.info.plans.some(item => item.id === plan)).toBe(true); expect(restored.info.attempts).toHaveLength(count);
  expect(await readFile(path.join(project.path, 'HEAD.json'))).toEqual(head);
  return { ...reopened, restored };
}

for (const [task, title] of [['mmtt-sensitivity', 'Native paired analysis'], ['mmtt-sampling', 'Native sampling analysis']]) {
  test('packaged ' + task + ' explicitly freezes, runs and exports exact native evidence', async ({ desktop }, testInfo) => {
    const { app, page } = await desktop.launch(), errors = []; page.on('pageerror', error => errors.push(error.message));
    await expect(page.locator('.skip')).toHaveAttribute('href', '#projects-heading');
    await create(page, title, task);
    await draws(page, app, 32);
    await page.locator('#review-study').click();
    await expect(page.getByRole('dialog', { name: 'Review study', exact: true })).toBeVisible();
    expect((await state(page)).projects[0].info.plans).toHaveLength(0);
    await page.locator('#information-dialog .dialog-close').first().click();
    await expect(page.locator('#review-study')).toBeFocused();
    const plan = await freezeAndCheck(page), beforeRun = await state(page);
    expect(beforeRun.projects[0].info.attempts).toHaveLength(0); expect(beforeRun.jobs.some(job => job.operation === 'run')).toBe(false);
    await page.locator('#run-study').click();
    const [attempt] = await finished(page, 1), project = (await state(page)).projects[0];
    expect(attempt.plan).toBe(plan); expect(attempt.outcome.completeness).toBe('complete');
    const evidence = await nativeEvidence(project, attempt.id);
    expect(evidence.receipt.remaining_owned_processes).toEqual([]);
    await page.locator(`#execution-attempts article[data-attempt="${attempt.id}"]`).getByRole('button', { name: 'Open results', exact: true }).click();
    await expect(page.locator('#results-heading')).toBeFocused();
    await expect(page.locator('#tree-results')).toHaveClass(/active/);
    await expect(page.locator('#tree-study')).not.toHaveClass(/active/);
    await expect(page.locator('#results-plan')).toHaveValue(plan); await expect(page.locator('#results-attempt')).toHaveValue(attempt.id);
    await page.locator('#results-inspect-inputs').click();
    await expect(page.locator('.results-used-inputs')).toContainText(plan);
    await page.locator('#results-verify').click();
    await expect(page.locator('#results-report')).toBeVisible(); await expect(page.locator('#results-report-completeness')).toHaveText('complete');
    await expect(page.locator('#results-report-context')).toContainText(attempt.id); await expect(page.locator('#results-report-context')).toContainText(plan);
    await exportExact(page, testInfo, 'Export report JSON', 'report.json', path.join(evidence.native, 'report.json'));
    await exportExact(page, testInfo, 'Export report', 'report.md', path.join(evidence.native, 'report.md'));
    if (task === 'mmtt-sampling') {
      const child = page.locator('#results-child-reports details').filter({ hasText: 'schedule full' }); await child.locator('summary').click();
      const waiting = page.waitForEvent('download'); await child.getByRole('button', { name: 'Export schedule JSON', exact: true }).click();
      const download = await waiting, target = testInfo.outputPath('studies-full-report.json'); await download.saveAs(target);
      expect(download.suggestedFilename()).toBe('studies-full-report.json'); expect(await readFile(target)).toEqual(await readFile(path.join(evidence.native, 'studies/full/report.json')));
    }
    await page.screenshot({ path: testInfo.outputPath(task + '-native-results.png'), scale: 'css' });
    const size = await app.evaluate(({ BrowserWindow }) => { const window = BrowserWindow.getAllWindows()[0], size = window.getContentSize(); window.setContentSize(800, 900); window.webContents.setZoomFactor(2); return size; });
    await expect.poll(() => page.evaluate(() => innerWidth)).toBeLessThan(650);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.locator('#results-back-study').click();
    await expect(page.locator('#study-heading')).toBeFocused(); await expect(page.locator('.skip')).toHaveAttribute('href', '#study-heading');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.locator('#show-project').click(); await expect(page.locator('#explorer')).toBeVisible();
    await page.keyboard.press('Escape'); await expect(page.locator('#explorer')).not.toBeVisible(); await expect(page.locator('#show-project')).toBeFocused();
    await app.evaluate(({ BrowserWindow }, size) => { const window = BrowserWindow.getAllWindows()[0]; window.webContents.setZoomFactor(1); window.setContentSize(...size); }, size);
    expect(errors).toEqual([]);
    await testInfo.attach('saved-identities.json', { body: JSON.stringify({ source: build.source, project: project.id, plan, attempt: attempt.id, receipt: evidence.receipt }, null, 2), contentType: 'application/json' });
  });
}

test('live numerical cancellation preserves an attempt and retry adds a same-plan outcome', async ({ desktop }, testInfo) => {
  await withSentinel(async sentinel => {
    const { app, page } = await desktop.launch(), { project, plan, observed } = await slowStudy(page, app, 'Native live cancellation');
    expectSentinel(sentinel); await page.locator('#cancel-study').click();
    const [first] = await finished(page, 1); expect(first.id).toBe(observed.attempt); expect(first.outcome.completeness).toBe('incomplete');
    const initial = await nativeEvidence(project, first.id); expect(initial.receipt.remaining_owned_processes).toEqual([]);
    await identitiesGone(observed.owned); expectSentinel(sentinel);
    await page.locator('#run-study').click();
    const attempts = await finished(page, 2), retried = attempts[1];
    expect(attempts[0]).toEqual(first); expect(retried).toMatchObject({ plan, ordinal: 2, retry_of: first.id }); expect(retried.id).not.toBe(first.id);
    expect(retried.outcome.completeness).toBe('complete'); expect((await nativeEvidence(project, retried.id)).receipt.remaining_owned_processes).toEqual([]);
    expect(await nativeEvidence(project, first.id)).toEqual(initial); expectSentinel(sentinel);
    await testInfo.attach('cancel-retry-ownership.json', { body: JSON.stringify({ source: build.source, observed, sentinel, first, retried }, null, 2), contentType: 'application/json' });
  });
});

test('observed numerical worker failure retains forensic evidence and an explicit retry', async ({ desktop }, testInfo) => {
  await withSentinel(async sentinel => {
    const { app, page } = await desktop.launch(), { project, plan, observed } = await slowStudy(page, app, 'Native worker failure');
    const current = processTable().find(item => item.pid === observed.worker.pid && item.start === observed.worker.start && !item.status.startsWith('Z'));
    expect(current).toBeTruthy(); expectSentinel(sentinel);
    // Only this live child of the test-owned backend is signalled. The app,
    // service, unrelated sentinel and saved scientific inputs remain intact.
    process.kill(current.pid, 'SIGKILL');
    const [first] = await finished(page, 1);
    expect(first.id).toBe(observed.attempt); expect(first.outcome).toMatchObject({ completeness: 'incomplete', payload: 'forensic', execution_status: 'failed' });
    const evidence = await nativeEvidence(project, first.id); expect(evidence.receipt.status).toBe('failed'); expect(evidence.receipt.remaining_owned_processes).toEqual([]);
    await identitiesGone(observed.owned); expectSentinel(sentinel);
    await page.locator(`#execution-attempts article[data-attempt="${first.id}"]`).getByRole('button', { name: 'Open results', exact: true }).click();
    await expect(page.locator('#results-attempt-summary')).toContainText('No admissible native report');
    await expect(page.locator('#results-verify')).toBeDisabled();
    await expect(page.locator('#results-allow-failed')).not.toBeVisible();
    await expect(page.locator('#results-report')).not.toBeVisible();
    await page.locator('#results-back-study').click(); await expect(page.locator('#run-study')).toBeEnabled(); await page.locator('#run-study').click();
    const attempts = await finished(page, 2), retried = attempts[1];
    expect(attempts[0]).toEqual(first); expect(retried).toMatchObject({ plan, ordinal: 2, retry_of: first.id }); expect(retried.outcome.completeness).toBe('complete');
    expect(await nativeEvidence(project, first.id)).toEqual(evidence); expect((await nativeEvidence(project, retried.id)).receipt.remaining_owned_processes).toEqual([]); expectSentinel(sentinel);
    await testInfo.attach('worker-failure-retry.json', { body: JSON.stringify({ source: build.source, observed, sentinel, first, retried, receipt: evidence.receipt }, null, 2), contentType: 'application/json' });
  });
});

for (const mode of ['native quit', 'owner crash']) {
  test('active ' + mode + ' cleans owned numerical workers and reopens without execution', async ({ desktop }, testInfo) => {
    await withSentinel(async sentinel => {
      const { app, page } = await desktop.launch(), { project, plan, observed } = await slowStudy(page, app, 'Native active ' + mode);
      expectSentinel(sentinel);
      if (mode === 'native quit') {
        await app.evaluate(({ dialog, app }) => { globalThis.quitDialogs = []; dialog.showMessageBox = async (_window, options) => { globalThis.quitDialogs.push(options); return { response: 0 }; }; app.quit(); });
        await expect.poll(() => app.evaluate(() => globalThis.quitDialogs.length)).toBe(1);
        expect(await app.evaluate(() => globalThis.quitDialogs[0].buttons)).toEqual(['Keep working', 'Stop and quit']);
        expect((await state(page)).active).toBe(observed.job); expectSentinel(sentinel);
        expect(processTable().some(item => item.pid === observed.worker.pid && item.start === observed.worker.start && !item.status.startsWith('Z'))).toBe(true);
        await app.evaluate(({ dialog, app }) => { dialog.showMessageBox = async () => ({ response: 1 }); app.quit(); }).catch(error => { if (!/closed|disposed/i.test(error.message)) throw error; });
      } else ownedProcess(app).kill('SIGKILL');
      await expect.poll(() => ownedProcess(app).exitCode !== null || ownedProcess(app).signalCode !== null, { timeout: 45000 }).toBe(true);
      await identitiesGone([observed.backend, ...observed.owned]); expectSentinel(sentinel);
      const { restored } = await reopenPassive(desktop, project, plan, 1), [attempt] = restored.info.attempts;
      expect(attempt.id).toBe(observed.attempt); expect(attempt.outcome.completeness).toBe('incomplete');
      const evidence = await nativeEvidence(project, attempt.id); expect(evidence.receipt.remaining_owned_processes).toEqual([]); expectSentinel(sentinel);
      await testInfo.attach('active-shutdown-ownership.json', { body: JSON.stringify({ source: build.source, mode, observed, sentinel, attempt, receipt: evidence.receipt }, null, 2), contentType: 'application/json' });
    });
  });
}
