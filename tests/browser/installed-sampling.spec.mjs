import { test as base, expect } from '@playwright/test';
import { spawn, spawnSync } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import { cp, mkdir, mkdtemp, readFile, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const python = process.env.OPENT1D_BROWSER_PYTHON || path.join(root, '.venv/bin/python');

function command(executable, args, options) {
  const result = spawnSync(executable, args, { ...options, encoding: 'utf8', timeout: 90_000 });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${executable} failed: ${result.stdout}\n${result.stderr}`);
  return result.stdout;
}

const test = base.extend({
  app: async ({}, use, testInfo) => {
    const folder = await realpath(await mkdtemp(path.join(tmpdir(), 'opent1d-installed-browser-')));
    const env = { ...process.env, UV_CACHE_DIR: path.join(folder, 'cache'), PYTHONNOUSERSITE: '1' };
    delete env.PYTHONPATH;
    const options = { env, cwd: folder };
    const workspace = path.join(folder, 'workspace');
    await mkdir(testInfo.outputDir, { recursive: true });
    const log = createWriteStream(testInfo.outputPath('installed-server.log'));
    let child, exited, failed = false;
    async function stop() {
      if (!child) return;
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
      let timer;
      try {
        await Promise.race([exited, new Promise((_, reject) => {
          timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error('Installed server cleanup exceeded 45 seconds')); }, 45_000);
        })]);
      } finally { clearTimeout(timer); child = null; }
    }
    async function start(cli) {
      child = spawn(cli, ['gui', '--workspace', workspace], { ...options, stdio: ['ignore', 'pipe', 'pipe'] });
      exited = new Promise(resolve => { child.once('exit', resolve); child.once('error', resolve); });
      child.stdout.on('data', chunk => log.write(chunk));
      child.stderr.on('data', chunk => log.write(chunk));
      const lines = createInterface({ input: child.stdout });
      let timer;
      try {
        return await new Promise((resolve, reject) => {
          timer = setTimeout(() => reject(new Error('Installed server did not become ready')), 30_000);
          child.once('error', reject);
          child.once('exit', code => reject(new Error(`Installed server exited before readiness: ${code}`)));
          lines.on('line', line => { if (line.startsWith('OpenT1D project GUI: ')) resolve(line.slice('OpenT1D project GUI: '.length)); });
        });
      } finally { clearTimeout(timer); lines.close(); }
    }
    try {
      const receipt = command(python, [path.join(root, 'scripts/build_sdk.py'), '--output', path.join(folder, 'build'), '--allow-dirty', '--build-label', 'sampling-browser-regression'], options);
      await writeFile(testInfo.outputPath('build-receipt.json'), receipt);
      const installedPython = path.join(folder, 'sdk/bin/python');
      command('uv', ['venv', '--offline', '--python', python, path.join(folder, 'sdk')], options);
      command('uv', ['pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', installedPython, JSON.parse(receipt).wheel], options);
      const cli = path.join(folder, 'sdk/bin/opent1d-lab');
      const app = { folder, workspace, url: await start(cli), restart: async () => { await stop(); app.url = await start(cli); } };
      await use(app);
    } catch (error) { failed = true; throw error; }
    finally {
      try { await stop(); }
      finally {
        log.end();
        if (failed || testInfo.status !== testInfo.expectedStatus) await cp(folder, testInfo.outputPath('installed-workspace'), { recursive: true });
        await rm(folder, { recursive: true, force: true });
      }
    }
  },
});

test('installed sampling: native children, relocation, restart and tamper withdrawal', async ({ page, app }, testInfo) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(app.url);
  await page.locator('#project-name').fill('Installed sampling browser control');
  await page.locator('#create-project button').click();
  await expect(page.locator('#project-view')).toBeVisible();
  const original = await page.locator('#selected-path').textContent();
  await page.locator('#task').selectOption('mmtt-sampling');
  await expect(page.locator('#example-case option')).toHaveCount(4);
  await expect(page.locator('#task-context')).toContainText('Development-only selection');
  await page.locator('#prepare-form button').click();
  await expect(page.locator('#draft')).toBeVisible();
  await page.locator('#freeze-form button').click();
  await expect(page.locator('#run-plan')).toBeEnabled();
  await page.locator('#inspect-plan').click();
  await expect(page.locator('#plan-details')).toContainText('design.json');
  await page.locator('#check-plan').click();
  await expect(page.locator('#readiness')).toContainText('Ready for explicit execution');
  await page.locator('#run-plan').click();
  await expect(page.locator('#attempt-list')).toContainText('60/60 planned slots complete');
  await page.getByRole('button', { name: 'Verify saved report', exact: true }).click();
  await expect(page.locator('#saved-report')).toBeVisible();
  await expect(page.locator('#report-completeness')).toHaveText('complete');
  await expect(page.locator('#child-reports details')).toHaveCount(4);
  await expect(page.locator('#report-text')).toContainText('evaluation');
  const full = page.locator('#child-reports details').filter({ has: page.getByText('Schedule: full', { exact: true }) });
  await full.locator('summary').click();
  await full.getByRole('button', { name: 'Read native analysis', exact: true }).click();
  await expect(full.locator('.report-text')).toContainText('128');
  const downloadEvent = page.waitForEvent('download');
  await full.getByRole('button', { name: 'Download schedule JSON', exact: true }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe('studies-full-report.json');
  const downloaded = testInfo.outputPath('full-report.json');
  await download.saveAs(downloaded);
  const report = JSON.parse(await readFile(downloaded));
  expect(report.task).toBe('mmtt-sensitivity');
  await page.screenshot({ path: testInfo.outputPath('installed-sampling-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('installed-sampling-narrow.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.setViewportSize({ width: 1280, height: 900 });

  const moved = path.join(app.folder, 'moved-project');
  await page.locator('#relocate-path').fill(moved);
  await page.locator('#relocate-form button').click();
  await expect(page.locator('#selected-path')).toHaveText(moved);
  await app.restart();
  await rename(original, original + '-unavailable');
  await page.goto(app.url);
  await page.getByRole('button', { name: 'Installed sampling browser control — copy', exact: true }).click();
  await page.getByRole('button', { name: 'Verify saved report', exact: true }).click();
  await expect(page.locator('#saved-report')).toBeVisible();
  const token = await page.locator('meta[name="opent1d-token"]').getAttribute('content');
  const state = await (await page.request.get(new URL('/api/state', app.url).href, { headers: { 'X-OpenT1D-Token': token } })).json();
  const pointer = state.reports.find(item => item.valid);
  const child = path.join(app.workspace, 'reports', pointer.id, 'studies/full/report.md');
  await writeFile(child, 'Changed synthetic report copy');
  const reopened = page.locator('#child-reports details').filter({ has: page.getByText('Schedule: full', { exact: true }) });
  await reopened.locator('summary').click();
  await reopened.getByRole('button', { name: 'Read native analysis', exact: true }).click();
  await expect(page.locator('#notice')).toHaveClass(/error/);
  await expect(page.locator('#saved-report')).toBeHidden();
  expect(errors).toEqual([]);
});
