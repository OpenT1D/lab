import { test as base, expect } from '../browser/node_modules/@playwright/test/index.mjs';
import { _electron } from '../browser/node_modules/playwright/index.mjs';
import { readFile, writeFile, mkdtemp, mkdir, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

if (process.platform !== 'darwin' || !process.env.OPENT1D_DESKTOP_BUILD) throw new Error('Select a real Mac build-result.json with OPENT1D_DESKTOP_BUILD.');
const build = JSON.parse(await readFile(process.env.OPENT1D_DESKTOP_BUILD, 'utf8'));
if (build.target !== 'darwin-arm64' || build.sdk.descriptor_schema !== 'opent1d.installed-sdk/4' ||
    (build.source.dirty && process.env.OPENT1D_DESKTOP_ALLOW_DIRTY !== '1')) throw new Error('Select the current clean Mac SDK/4 build; dirty builds require explicit development opt-in.');

const test = base.extend({
  desktop: async ({}, use, testInfo) => {
    const folder = await realpath(await mkdtemp(path.join(tmpdir(), 'opent1d-native-comparison-')));
    const workspace = path.join(folder, 'workspace'), downloads = path.join(folder, 'downloads'), apps = [];
    await mkdir(downloads);
    const launch = async () => {
      const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE; delete env.PYTHONPATH;
      const app = await _electron.launch({ executablePath: build.executable, args: ['--workspace', workspace], env, timeout: 45000 });
      apps.push({ app, process: app.process() });
      const page = await app.firstWindow();
      // Keep real session downloads inside this invented workspace and avoid a
      // native Save dialog. Production download behavior remains unchanged.
      await app.evaluate(({ BrowserWindow }, { downloads, firstOrdinal }) => {
        let ordinal = firstOrdinal; globalThis.comparisonDownloads = [];
        BrowserWindow.getAllWindows()[0].webContents.session.on('will-download', (_event, item) => {
          const filename = item.getFilename(); item.setSavePath(downloads + '/' + ++ordinal + '-' + filename);
          item.once('done', (_event, status) => { globalThis.comparisonDownloads.push({ filename, path: item.getSavePath(), status }); });
        });
      }, { downloads, firstOrdinal: apps.length * 1000 });
      await expect(page.locator('#new-project')).toBeEnabled();
      return { app, page };
    };
    try { await use({ launch, workspace, downloads }); }
    finally {
      for (const owned of apps) {
        if (owned.process.exitCode !== null || owned.process.signalCode !== null) continue;
        try {
          await owned.app.evaluate(({ dialog }) => { dialog.showMessageBox = async () => ({ response: 1 }); });
          await owned.app.close();
        } catch { /* The original failure and invented workspace remain available. */ }
      }
      if (testInfo.status === testInfo.expectedStatus) await rm(folder, { recursive: true, force: true });
      else await testInfo.attach('retained-workspace.txt', { body: workspace, contentType: 'text/plain' });
    }
  },
});

async function state(page) {
  return page.evaluate(async () => {
    const response = await fetch('/api/state', { headers: { 'X-OpenT1D-Token': document.querySelector('meta[name="opent1d-token"]').content } });
    if (!response.ok) throw new Error('Packaged project state read was refused');
    return response.json();
  });
}
async function finished(page, count) {
  await expect.poll(async () => {
    const incoming = await state(page), attempts = incoming.projects[0]?.info?.attempts || [];
    return incoming.active === null && attempts.length === count && attempts.every(attempt => typeof attempt.outcome === 'object');
  }, { timeout: 45000 }).toBe(true);
  await expect(page.locator('#execution-attempts article')).toHaveCount(count);
  return (await state(page)).projects[0].info.attempts;
}
async function verify(page, completeness) {
  await page.locator('#results-comparison-verify').click();
  await expect(page.locator('#results-report')).toBeVisible();
  await expect(page.locator('#results-report-completeness')).toHaveText(completeness);
  await expect(page.getByRole('button', { name: 'Export report JSON', exact: true })).toBeEnabled();
  const incoming = await state(page), comparison = await page.locator('#results-comparison-select').inputValue();
  const record = incoming.reports.filter(item => item.valid && item.comparison === comparison).at(-1);
  expect(record).toBeTruthy(); return record;
}
async function exportExact(app, page, testInfo, desktop, record, label, filename, savedName) {
  const before = await app.evaluate(() => globalThis.comparisonDownloads.length);
  await page.getByRole('button', { name: label, exact: true }).click();
  await expect.poll(() => app.evaluate(() => globalThis.comparisonDownloads.length)).toBe(before + 1);
  const download = await app.evaluate(index => globalThis.comparisonDownloads[index], before);
  expect(download).toMatchObject({ filename, status: 'completed' });
  expect(path.dirname(download.path)).toBe(desktop.downloads);
  const bytes = await readFile(download.path); await writeFile(testInfo.outputPath(savedName), bytes);
  expect(bytes).toEqual(await readFile(path.join(desktop.workspace, 'reports', record.id, filename)));
  return bytes;
}

test('packaged prospective comparison runs through Study and preserves first-attempt exports after restart', async ({ desktop }, testInfo) => {
  test.setTimeout(90000);
  let { app, page } = await desktop.launch();
  const errors = []; const watch = page => page.on('pageerror', error => errors.push(error.message)); watch(page);
  const title = 'Native planned comparison', question = 'How do the frozen synthetic volumes change the paired estimate?';
  await page.locator('#new-project').click();
  await page.locator('#project-name').fill(title);
  await page.locator('#new-approach').selectOption('mmtt-sensitivity');
  await page.locator('#confirm-project').click();
  await expect(page.locator('#workspace')).toBeVisible();
  await page.locator('#assumptions').click(); await page.locator('#draws').fill('32');
  await page.locator('#files-form button[type=submit]').click();
  await app.evaluate(({ Menu }) => Menu.getApplicationMenu().items.find(item => item.label === 'File').submenu.items.find(item => item.label === 'Save').click());
  await expect(page.locator('#save-state')).toHaveText('');
  await page.locator('#review-study').click();
  await expect(page.getByRole('dialog', { name: 'Review study', exact: true })).toBeVisible();
  await page.locator('#freeze-study').click();
  await expect(page.locator('#information-dialog')).not.toBeVisible();
  const plan = await page.locator('#execution-plan').inputValue(); expect(plan).toMatch(/^[a-f0-9]{64}$/);

  await page.locator('#tree-results').click(); await page.locator('#results-comparison-mode').click();
  await page.getByText('Plan a new comparison', { exact: true }).click();
  await page.locator('#results-comparison-name').fill('Frozen paired volumes');
  await page.locator('#results-comparison-question').fill(question);
  await page.locator('#results-member-plan').selectOption(plan); await page.locator('#results-member-options').click();
  await expect(page.locator('#results-member-selector option')).toHaveCount(3);
  for (const [variant, label] of [['nominal', 'Baseline'], ['volume-120', 'Increased volume']]) {
    await page.locator('#results-member-selector').selectOption({ label: variant });
    await page.locator('#results-member-label').fill(label); await page.locator('#results-member-add').click();
  }
  await page.locator('#results-comparison-baseline').selectOption('member-1');
  await expect(page.locator('#results-roster .results-roster-row')).toHaveCount(2);
  expect((await state(page)).projects[0].info.attempts).toHaveLength(0);
  await page.locator('#results-comparison-freeze').click();
  await expect(page.locator('#results-comparison-summary')).toContainText(question);
  await expect(page.locator('#results-comparison-summary')).toContainText('2 planned members · baseline Baseline');
  await expect(page.locator('#results-comparison-summary tbody tr')).toHaveCount(2);
  const comparison = await page.locator('#results-comparison-select').inputValue();
  const initialRecord = await verify(page, 'incomplete');
  const initial = JSON.parse(await exportExact(app, page, testInfo, desktop, initialRecord, 'Export report JSON', 'report.json', 'unattempted-report.json'));
  expect(initial.definition.question).toBe(question); expect(initial.definition.baseline).toBe('member-1');
  expect(initial.coverage.planned_members).toBe(2); expect(initial.coverage.complete_cases).toBe(0);
  expect(initial.coverage.unavailable_contrasts).toBe(initial.coverage.planned_cases);
  expect(initial.members.every(member => member.attempt.status === 'unattempted')).toBe(true);

  await page.locator('#results-comparison-next').click();
  await expect(page.locator('#study-body')).toBeVisible(); await expect(page.locator('#results-body')).not.toBeVisible();
  const running = await page.waitForFunction(plan => {
    const cancel = document.querySelector('#cancel-study'), status = document.querySelector('#execution-status');
    return cancel && !cancel.hidden && !cancel.disabled && status?.getBoundingClientRect().height > 0 && status.textContent.includes(plan)
      ? { status: status.textContent, cancel: cancel.textContent } : false;
  }, plan, { polling: 25, timeout: 15000 });
  const observed = await running.jsonValue(); expect(observed.cancel).toBe('Cancel analysis');
  const [first] = await finished(page, 1); expect(first.plan).toBe(plan); expect(first.outcome.completeness).toBe('complete');
  await page.locator('#results-tab').click();
  await expect(page.locator('#results-comparison-select')).toHaveValue(comparison);
  await page.locator('#results-comparison-open').click();
  await expect(page.locator('#results-comparison-summary')).toContainText(first.id);
  const completeRecord = await verify(page, 'complete');
  const complete = JSON.parse(await exportExact(app, page, testInfo, desktop, completeRecord, 'Export report JSON', 'report.json', 'complete-report.json'));
  await exportExact(app, page, testInfo, desktop, completeRecord, 'Export comparison table', 'comparison.csv', 'complete-comparison.csv');
  expect(complete.coverage.complete_cases).toBe(complete.coverage.planned_cases);
  expect(complete.members.every(member => member.attempt.attempt === first.id)).toBe(true);
  expect(complete.difference_convention).toBe('member minus explicitly frozen baseline');
  await page.screenshot({ path: testInfo.outputPath('native-comparison-complete.png'), scale: 'css' });

  await page.locator('#study-tab').click();
  await page.locator(`#execution-attempts article[data-attempt="${first.id}"]`).getByRole('button', { name: 'Run a new attempt', exact: true }).click();
  const attempts = await finished(page, 2), retry = attempts[1];
  expect(attempts[0]).toEqual(first); expect(retry).toMatchObject({ plan, ordinal: 2, retry_of: first.id });
  expect(retry.outcome.completeness).toBe('complete');
  await page.locator('#results-tab').click(); await page.locator('#results-comparison-open').click();
  const retriedRecord = await verify(page, 'complete');
  const beforeRestart = await exportExact(app, page, testInfo, desktop, retriedRecord, 'Export report JSON', 'report.json', 'after-retry-report.json');
  const beforeRestartCSV = await exportExact(app, page, testInfo, desktop, retriedRecord, 'Export comparison table', 'comparison.csv', 'after-retry-comparison.csv');
  expect(JSON.parse(beforeRestart).members.every(member => member.attempt.attempt === first.id)).toBe(true);
  const project = (await state(page)).projects[0], head = await readFile(path.join(project.path, 'HEAD.json'));
  await app.close(); ({ app, page } = await desktop.launch()); watch(page);
  await page.locator('#recent-projects button').filter({ hasText: title }).click();
  await page.locator('#tree-results').click(); await page.locator('#results-comparison-mode').click();
  await page.locator('#results-comparison-select').selectOption(comparison); await page.locator('#results-comparison-open').click();
  await expect(page.locator('#results-comparison-summary')).toContainText(question);
  await expect(page.locator('#results-comparison-summary tbody tr')).toHaveCount(2);
  const reopenedRecord = await verify(page, 'complete');
  expect(await exportExact(app, page, testInfo, desktop, reopenedRecord, 'Export report JSON', 'report.json', 'reopened-report.json')).toEqual(beforeRestart);
  expect(await exportExact(app, page, testInfo, desktop, reopenedRecord, 'Export comparison table', 'comparison.csv', 'reopened-comparison.csv')).toEqual(beforeRestartCSV);
  const reopened = await state(page);
  expect(reopened.jobs.some(job => job.operation === 'run')).toBe(false);
  expect(reopened.projects[0].info.attempts).toHaveLength(2);
  expect(await readFile(path.join(project.path, 'HEAD.json'))).toEqual(head);
  expect(errors).toEqual([]);
  await testInfo.attach('packaged-comparison-identities.json', { body: JSON.stringify({ source: build.source, project: project.id, plan, comparison, first: first.id, retry: retry.id, observed, coverage: complete.coverage, snapshot: reopenedRecord.snapshot }, null, 2), contentType: 'application/json' });
});
