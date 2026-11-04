import { readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { test, expect } from './installed-fixtures.mjs';

async function state(page, app) {
  const token = await page.locator('meta[name="opent1d-token"]').getAttribute('content');
  return (await page.request.get(new URL('/api/state', app.url).href,
    { headers: { 'X-OpenT1D-Token': token } })).json();
}

async function create(page, app, name) {
  await page.goto(app.url);
  await expect(page.locator('#nav-projects')).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#nav-study')).toBeDisabled();
  await expect(page.locator('#nav-results')).toBeDisabled();
  await page.locator('#project-name').fill(name);
  await page.locator('#create-project button').click();
  await expect(page.locator('#nav-study')).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#study-screen')).toBeVisible();
}

async function downloadJSON(page) {
  const waiting = page.waitForEvent('download');
  await page.locator('[data-download="report.json"]').click();
  return readFile(await (await waiting).path());
}

test('three screens retain local concept edits before autosave and disclose local storage', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await create(page, app, 'Navigation retains my study');
  await page.locator('#prepare-form button[type="submit"]').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  const original = (await state(page, app)).drafts[0];

  // Stop the actual autosave timer: all navigation below happens while the
  // edited value exists only in the live editor, not a completed server save.
  const instant = new Date('2026-11-04T12:00:00Z');
  await page.clock.install({ time: instant });
  await page.clock.pauseAt(new Date(instant.getTime() + 1000));
  await page.locator('#assumption-draws').fill('64');
  await expect(page.locator('#draft-status')).toContainText('Unsaved changes');
  await page.locator('#nav-results').click();
  await expect(page.locator('#results-screen')).toBeVisible();
  await expect(page.locator('#study-screen')).toBeHidden();
  await expect(page.locator('#attempt-list')).toContainText('No attempts');
  await page.locator('#nav-projects').click();
  await expect(page.locator('#projects-screen')).toBeVisible();
  await expect(page.locator('#project-view')).toBeHidden();
  await page.locator('#nav-study').click();
  await expect(page.locator('#assumption-draws')).toHaveValue('64');
  await expect(page.locator('#draft-status')).toContainText('Unsaved changes');
  expect((await state(page, app)).drafts[0].revision).toBe(original.revision);

  await page.clock.resume();
  await expect(page.locator('#draft-status')).toContainText('Saved revision');
  await expect.poll(async () => (await state(page, app)).drafts[0].revision).toBeGreaterThan(original.revision);
  await page.locator('#storage-details > summary').click();
  const storage = page.locator('#storage-details');
  await expect(storage).toContainText(app.workspace);
  await expect(page.locator('#selected-path')).toBeVisible();
  await expect(page.locator('#relocate-form')).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('three-screens-research-narrow.png'), fullPage: false });
  expect(errors).toEqual([]);
});

test('an actual sampling execution stays visible and cancellable across all three screens', async ({ page, app }) => {
  test.setTimeout(150_000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await create(page, app, 'Visible running study');
  await page.locator('#task').selectOption('mmtt-sampling');
  await page.locator('#prepare-form button[type="submit"]').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await page.locator('#assumption-draws').fill('1024');
  await expect(page.locator('#draft-status')).toContainText('Saved revision');
  await page.locator('#validate-draft').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await page.locator('#freeze-draft').click();
  await expect(page.locator('#run-plan')).toBeEnabled();
  const project = await page.locator('#selected-path').textContent();
  await page.locator('#run-plan').click();
  await expect(page.locator('#job')).toBeVisible();
  await expect.poll(async () => {
    try {
      for (const attempt of await readdir(path.join(project, 'work'))) {
        try {
          const execution = JSON.parse(await readFile(path.join(project, 'work', attempt, 'native/studies/full/execution.json')));
          if (execution.phase === 'analysis') return execution.phase;
        } catch { /* The native child has not published its phase yet. */ }
      }
    } catch { /* No attempt workspace has been created yet. */ }
    return null;
  }, { intervals: [20, 50, 100], timeout: 30_000 }).toBe('analysis');
  await expect.poll(async () => (await state(page, app)).active).toBeTruthy();
  const active = (await state(page, app)).active;
  for (const screen of ['results', 'projects', 'study']) {
    await page.locator('#nav-' + screen).click();
    await expect(page.locator('#nav-' + screen)).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('#job')).toBeVisible();
    await expect(page.locator('#cancel-run')).toBeEnabled();
    expect((await state(page, app)).active).toBe(active);
  }
  await page.locator('#nav-results').click();
  await page.locator('#cancel-run').click();
  await expect(page.locator('#job')).toBeHidden({ timeout: 60_000 });
  await expect(page.locator('#nav-results')).toHaveAttribute('aria-current', 'page');
  const settled = await state(page, app);
  expect(settled.active).toBeNull();
  const job = settled.jobs.find(item => item.id === active);
  expect(job.status).not.toBe('running');
  expect(app.command('info', '--project', project).attempts).toHaveLength(1);
  await expect(page.locator('#attempt-list .attempt')).toHaveCount(1);
  expect(errors).toEqual([]);
});

test('selected execution binds used inputs, variant parent and report; delayed verification does not change screens', async ({ page, app }, testInfo) => {
  test.setTimeout(150_000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await create(page, app, 'Explicit execution identity');
  const project = await page.locator('#selected-path').textContent();
  const inputs = app.command('example', '--task', 'mmtt-sensitivity', '--case', 'complete', '--output', path.join(app.folder, 'identity-inputs')).inputs;
  const settings = JSON.parse(await readFile(inputs['settings.json'], 'utf8'));
  settings.uncertainty.draws = 32;
  await writeFile(inputs['settings.json'], JSON.stringify(settings));
  const freeze = () => app.command('freeze', '--project', project, '--task', 'mmtt-sensitivity', '--package', inputs['package.json'], '--csv', inputs['observations.csv'], '--settings', inputs['settings.json']).plan;
  const firstPlan = freeze();
  const first = app.command('run', '--project', project, '--plan', firstPlan);
  settings.variants[0].volume_l = 5.1;
  await writeFile(inputs['settings.json'], JSON.stringify(settings));
  const secondPlan = freeze();
  const second = app.command('run', '--project', project, '--plan', secondPlan);
  await page.locator('#refresh-project').click();
  await expect(page.locator('#plan-select option')).toHaveCount(2);
  await page.locator('#plan-select').selectOption(secondPlan);
  await page.locator('#prepare-form button[type="submit"]').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  const openDraft = (await state(page, app)).drafts[0].id;

  await page.locator('#nav-results').click();
  await page.locator('#attempt-select').selectOption(first.attempt);
  await page.locator('#inspect-used-plan').click();
  await expect(page.locator('#nav-study')).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#used-plan-inspector')).toBeVisible();
  await expect(page.locator('#used-plan-inspector')).toContainText(firstPlan);
  await expect(page.locator('#plan-select')).toHaveValue(secondPlan);
  await expect(page.locator('#assumption-draws')).toHaveValue('128');
  expect((await state(page, app)).drafts[0].id).toBe(openDraft);
  await page.locator('#nav-results').click();
  await page.locator('#derive-used-plan').click();
  await expect(page.locator('#nav-study')).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#parent-plan')).toHaveValue(firstPlan);
  await expect(page.locator('#assumption-draws')).toHaveValue('32');
  await page.locator('#close-draft').click();

  await page.locator('#nav-results').click();
  await page.locator('#attempt-select').selectOption(first.attempt);
  await page.getByRole('button', { name: 'Verify saved report', exact: true }).click();
  await expect(page.locator('#saved-report')).toBeVisible();
  await expect(page.locator('#report-context')).toContainText(first.attempt.slice(0, 12));
  expect(await downloadJSON(page)).toEqual(await readFile(path.join(first.evidence, 'native/report.json')));

  await page.locator('#attempt-select').selectOption(second.attempt);
  await expect(page.locator('#saved-report')).toBeHidden();
  let release, requested;
  const held = new Promise(resolve => { release = resolve; });
  const started = new Promise(resolve => { requested = resolve; });
  const route = '**/api/reports/*/report.md';
  await page.route(route, async request => {
    const response = await request.fetch();
    requested();
    await held;
    await request.fulfill({ response });
  });
  try {
    await page.getByRole('button', { name: 'Verify saved report', exact: true }).click();
    await started;
    await page.locator('#nav-study').click();
    release();
    await expect(page.locator('#report-context')).toContainText(second.attempt.slice(0, 12));
    await expect(page.locator('#job')).toBeHidden();
    await expect(page.locator('#nav-study')).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('#study-screen')).toBeVisible();
    await expect(page.locator('#saved-report')).toBeHidden();
    await page.locator('#nav-results').click();
    await expect(page.locator('#saved-report')).toBeVisible();
    expect(await downloadJSON(page)).toEqual(await readFile(path.join(second.evidence, 'native/report.json')));
    await page.screenshot({ path: testInfo.outputPath('three-screens-results.png'), fullPage: false });
  } finally {
    release();
    await page.unroute(route);
  }
  expect(errors).toEqual([]);
});
