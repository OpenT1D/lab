import { test as base, expect } from '../browser/node_modules/@playwright/test/index.mjs';
import { _electron } from '../browser/node_modules/playwright/index.mjs';
import { readFile, mkdtemp, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
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
      const app = await _electron.launch({ executablePath: build.executable, args: ['--workspace', workspace], env, timeout: 45000 });
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
