import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { test, expect } from './fixtures.mjs';

const tasks = [
  { prefix: 'obs', view: 'observations', example: 'increase', task: 'mmtt-sensitivity' },
  { prefix: 'sam', view: 'sampling', example: 'information-loss', task: 'mmtt-sampling' },
];

async function prepare(page, app, task, draws = 32) {
  const p = task.prefix;
  await page.goto(app.url);
  await page.locator(`#open-${task.view}`).click();
  await page.locator(`#${p}-case`).selectOption(task.example);
  await page.locator(`#${p}-example`).click();
  await expect(page.locator(`#${p}-plan-form`)).toBeVisible();
  await expect(page.locator(`#${p}-validation`)).toContainText('visits loaded');
  await expect(page.locator(`#${p}-run`)).toBeDisabled();
  await page.locator(`#${p}-display-name`).fill(`Browser ${task.task}`);
  await page.locator(`#${p}-settings-details > summary`).click();
  await page.locator(`#${p}-draws`).fill(String(draws));
}

async function freeze(page, task) {
  await page.locator(`#${task.prefix}-freeze`).click();
  await expect(page.locator(`#${task.prefix}-plan-state`)).toContainText('Ready to run');
  await expect(page.locator(`#${task.prefix}-run`)).toBeEnabled();
}

async function download(page, prefix, kind, testInfo, suffix = '') {
  const event = page.waitForEvent('download');
  await page.locator(`#${prefix}-download-${kind === 'json' ? 'json' : 'md'}`).click();
  const downloaded = await event;
  expect(downloaded.suggestedFilename()).toBe(`report.${kind}`);
  const target = testInfo.outputPath(`${prefix}-${suffix}report.${kind}`);
  await downloaded.saveAs(target);
  expect(await downloaded.failure()).toBeNull();
  return readFile(target);
}

async function inventory(folder) {
  const result = {};
  async function visit(directory) {
    for (const item of await readdir(directory, { withFileTypes: true })) {
      const target = path.join(directory, item.name);
      if (item.isDirectory()) await visit(target);
      else result[path.relative(folder, target)] = createHash('sha256').update(await readFile(target)).digest('hex');
    }
  }
  await visit(folder);
  return result;
}

for (const task of tasks) {
  test(`${task.task}: example, freeze, run, download, restart and reconstruct`, async ({ page, app }, testInfo) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await prepare(page, app, task);
    await freeze(page, task);
    await page.locator(`#${task.prefix}-run`).click();
    await expect(page.locator(`#${task.prefix}-execution`)).toHaveText('Analysis finished · results complete');
    await expect(page.locator(`#${task.prefix}-report`)).toContainText('Invented');
    const entry = page.locator(`#${task.prefix}-analysis-list button`).filter({ hasText: `Browser ${task.task}` });
    await expect(entry).toHaveCount(1);
    const identity = await entry.getAttribute('data-entry-id');
    const archive = path.join(app.workspace, 'results/gui', task.view, 'archives', identity, 'archive');
    const before = await inventory(archive);
    const json = await download(page, task.prefix, 'json', testInfo);
    const markdown = await download(page, task.prefix, 'md', testInfo);
    expect(json).toEqual(await readFile(path.join(archive, 'report.json')));
    expect(markdown).toEqual(await readFile(path.join(archive, 'report.md')));
    const report = JSON.parse(json);
    expect(report.task).toBe(task.task);
    expect(report.kind).toBe('synthetic');
    expect(report.human_evaluation).toBe(false);
    expect(report.execution_status).toBe('completed');
    expect(report.coverage.complete_cohort).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`${task.prefix}-complete.png`), fullPage: true });

    await app.restart();
    await page.goto(`${app.url}#${task.view}`);
    await page.locator(`#${task.prefix}-analysis-list button[data-entry-id="${identity}"]`).click();
    await expect(page.locator(`#${task.prefix}-execution`)).toHaveText('Analysis finished · results complete');
    await page.locator(`#${task.prefix}-reconstruct`).click();
    await expect(page.locator(`#${task.prefix}-result-detail`)).toContainText('Saved report checked');
    expect(await download(page, task.prefix, 'json', testInfo, 'reopened-')).toEqual(json);
    expect(await inventory(archive)).toEqual(before);
    expect(errors).toEqual([]);
  });
}

test('invalid assumptions and missing observation input remain visible and cannot run', async ({ page, app }) => {
  const task = tasks[0];
  await prepare(page, app, task);
  await page.locator('#obs-draws').fill('31');
  await page.locator('#obs-freeze').click();
  await expect(page.locator('#obs-form-error')).toContainText('32 to 1024');
  await expect(page.locator('#obs-draws')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#obs-run')).toBeDisabled();
  await expect(page.locator('#obs-saved-plan option')).toHaveCount(1);
  await page.locator('#obs-input-form').locator('..').locator('summary').click();
  await page.locator('#obs-csv').fill('missing-observations.csv');
  await page.locator('#obs-inspect').click();
  await expect(page.locator('#obs-notice')).toBeVisible();
  await expect(page.locator('#obs-plan-form')).toBeHidden();
  await expect(page.locator('#obs-run')).toBeDisabled();
  await expect(page.locator('#obs-analysis-list button')).toHaveCount(0);
});

test('sampling cancellation retains an interrupted report that can be checked', async ({ page, app }, testInfo) => {
  const task = tasks[1];
  await prepare(page, app, task, 1024);
  await freeze(page, task);
  const response = page.waitForResponse(value => value.request().method() === 'POST'
    && /\/api\/v1\/sampling\/configurations\/[^/]+\/run$/.test(value.url()));
  await page.locator('#sam-run').click();
  const launched = await response;
  expect(launched.status()).toBe(202);
  const job = await launched.json();
  const phase = path.join(app.workspace, 'results/gui/sampling/archives', job.sampling_entry_id,
    'archive/studies/full/execution.json');
  await expect.poll(async () => {
    try { return JSON.parse(await readFile(phase)).phase; } catch { return null; }
  }, { intervals: [20, 50, 100], timeout: 30_000 }).toBe('analysis');
  await page.locator('#sam-cancel').click();
  await expect(page.locator('#sam-execution')).toHaveText('Analysis interrupted');
  const report = JSON.parse(await download(page, 'sam', 'json', testInfo));
  expect(report.execution_status).toBe('interrupted');
  expect(report.coverage.complete_cohort).toBe(false);
  expect(report.coverage.not_attempted_draw_pairs).toBeGreaterThan(0);
  const journal = JSON.parse(await readFile(path.join(app.workspace, 'results/gui', job.id, 'job.json')));
  expect(journal.state).toBe('cancelled');
  expect(journal.cleanup_forced).toBe(false);
  expect(journal.remaining_owned_processes || []).toEqual([]);
  await page.locator('#sam-reconstruct').click();
  await expect(page.locator('#sam-result-detail')).toContainText('Saved report checked');
  expect(JSON.parse(await download(page, 'sam', 'json', testInfo, 'checked-'))).toEqual(report);
});
