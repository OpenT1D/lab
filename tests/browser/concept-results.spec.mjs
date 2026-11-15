import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect } from './installed-fixtures.mjs';

// Exercise the results module against a real noneditable SDK independently of
// the shared shell. The integration family owns Study/Results navigation.
const assets = fileURLToPath(new URL('../../packaging/sdk/opent1d_lab/_gui_assets/', import.meta.url));
async function harness(page, app) {
  const html = await (await page.request.get(app.url)).text();
  const token = html.match(/name="opent1d-token" content="([a-f0-9]+)"/)[1];
  for (const name of ['workbench-results.js', 'workbench-results.css']) await page.route('**/' + name, route => route.fulfill({ path: path.join(assets, name), contentType: name.endsWith('.js') ? 'text/javascript' : 'text/css' }));
  await page.route('**/results-harness', route => route.fulfill({ contentType: 'text/html', body: `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="opent1d-token" content="${token}"><link rel="stylesheet" href="/workbench.css"><link rel="stylesheet" href="/workbench-results.css"><title>Results module check</title></head><body><main id="results-body"></main><script type="module">
    import { WorkbenchStore } from '/workbench-store.js';
    import { createResultsView } from '/workbench-results.js';
    globalThis.resultsStore = new WorkbenchStore({ token: '${token}', notify: () => globalThis.resultsView?.render() });
    globalThis.resultsView = createResultsView({ store: resultsStore, container: document.querySelector('main') });
    await resultsStore.refresh(); await resultsView.show(); globalThis.resultsReady = true;
    </script></body></html>` }));
  await page.goto(new URL('/results-harness', app.url).href);
  await expect.poll(() => page.evaluate(() => !!globalThis.resultsReady)).toBe(true);
}
async function prepare(page, name, task = 'mmtt-sensitivity', example = 'complete') {
  return page.evaluate(async ({ name, task, example }) => {
    const store = globalThis.resultsStore;
    const created = await store.action('create', { name }, null);
    await store.openProject(created.project);
    const draft = await store.action('prepare', { task, case: example }); store.accept(draft);
    const settings = JSON.parse(store.files['settings.json']); settings.uncertainty.draws = 32;
    store.edit(name, { ...store.files, 'settings.json': JSON.stringify(settings) }, false);
    await store.save(); await store.review();
    const frozen = await store.action('freeze', { draft: store.record.id, revision: store.record.revision, name, parent: null });
    await globalThis.resultsView.show();
    return { project: store.project.path, handle: store.projectId, plan: frozen.plan };
  }, { name, task, example });
}
async function run(page, plan, retryOf = null) {
  return page.evaluate(async ({ plan, retryOf }) => (await globalThis.resultsStore.action('run', { plan, retry_of: retryOf })), { plan, retryOf });
}
async function download(page, name) {
  const waiting = page.waitForEvent('download');
  await page.getByRole('button', { name, exact: true }).click();
  const saved = await waiting;
  return { filename: saved.suggestedFilename(), text: await readFile(await saved.path(), 'utf8') };
}
async function addMember(page, variant, label) {
  await page.locator('#results-member-selector').selectOption({ label: variant });
  await page.locator('#results-member-label').fill(label);
  await page.locator('#results-member-add').click();
}

test('native paired attempts retain earlier evidence and withdraw refused exports and late reports', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await harness(page, app);
  await expect(page.locator('#results-attempt-summary')).toContainText('No saved attempts yet');
  const study = await prepare(page, 'Paired result control');
  const first = await run(page, study.plan);
  await expect(page.locator('#results-attempt-summary')).toContainText('planned slots complete');
  await page.locator('#results-verify').click();
  await expect(page.locator('#results-report')).toBeVisible();
  await expect(page.locator('#results-report-completeness')).toHaveText('complete');
  await expect(page.locator('#results-limits')).toContainText('Synthetic observations only');
  const original = await download(page, 'Export report JSON');
  expect(original.filename).toBe('report.json');
  const firstId = await page.locator('#results-attempt').inputValue();
  await run(page, study.plan, firstId);
  await expect(page.locator('#results-attempt option')).toHaveCount(2);
  await page.locator('#results-attempt').selectOption({ label: (await page.locator('#results-attempt option').first().textContent()) });
  await expect(page.locator('#results-report')).not.toBeVisible();
  await page.locator('#results-attempt').selectOption(firstId);
  await page.locator('#results-verify').click();
  await expect(page.locator('#results-report-context')).toContainText(firstId);
  expect((await download(page, 'Export report JSON')).text).toBe(original.text);
  expect(first.result.completeness).toBe('complete');

  // The authenticated native reader refuses a modified convenience copy. A
  // delayed state cannot make the module offer that known-invalid copy again.
  const pointer = await page.evaluate(() => globalThis.resultsStore.data.reports.at(-1));
  await writeFile(path.join(app.workspace, 'reports', pointer.id, 'report.md'), 'Changed report copy');
  await page.getByRole('button', { name: 'Export report JSON', exact: true }).click();
  await expect(page.locator('#results-message')).toHaveAttribute('role', 'alert');
  await expect(page.locator('#results-report')).not.toBeVisible();
  await page.evaluate(pointer => { const store = globalThis.resultsStore; store.data.reports = store.data.reports.map(record => record.id === pointer.id ? { ...record, valid: true } : record); globalThis.resultsView.render(); }, pointer);
  await expect(page.locator('#results-report')).not.toBeVisible();

  // Hold only the report GET, then leave the view. Its eventual response must
  // not reopen a report or restore export controls after navigation.
  let release; const held = new Promise(resolve => { release = resolve; });
  let requested; const arrived = new Promise(resolve => { requested = resolve; });
  await page.route('**/api/reports/*/report.md', async route => { requested(); await held; await route.continue(); });
  await page.locator('#results-verify').click();
  await arrived;
  await page.evaluate(() => globalThis.resultsView.hide());
  release();
  await expect.poll(() => page.evaluate(() => globalThis.resultsStore.busy)).toBe(false);
  await page.evaluate(() => globalThis.resultsView.show());
  await expect(page.locator('#results-report')).not.toBeVisible();
  expect(errors).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('paired-results.png') });
});

test('sampling native reports keep planned denominator, child reports, incomplete evidence and keyboard reflow', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await harness(page, app);
  const study = await prepare(page, 'Sampling result control', 'mmtt-sampling', 'incomplete');
  const result = await run(page, study.plan);
  await expect(page.locator('#results-attempt-summary')).toContainText('incomplete');
  await expect(page.locator('#results-allow-failed')).toBeVisible();
  await page.locator('#results-allow-failed').check();
  await page.locator('#results-verify').click();
  await expect(page.locator('#results-report')).toBeVisible();
  await expect(page.locator('#results-report-completeness')).toHaveText('incomplete');
  const slots = Object.entries(result.result.slot_statuses);
  await page.getByText('All planned slots', { exact: true }).click();
  await expect(page.locator('#results-attempt-summary tbody tr')).toHaveCount(slots.length);
  await expect(page.locator('#results-limits')).toContainText('Full curves are references');
  await expect(page.locator('#results-child-reports details')).toHaveCount(4);
  const full = page.locator('#results-child-reports details').filter({ hasText: 'schedule full' });
  await full.locator('summary').click();
  await full.getByRole('button', { name: 'Read native analysis', exact: true }).click();
  await expect(full.locator('.results-report-text')).toContainText('32');
  const waiting = page.waitForEvent('download');
  await full.getByRole('button', { name: 'Export schedule JSON', exact: true }).click();
  const child = await waiting;
  expect(child.suggestedFilename()).toBe('studies-full-report.json');
  expect(JSON.parse(await readFile(await child.path(), 'utf8')).task).toBe('mmtt-sensitivity');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('#results-verify').focus(); await page.keyboard.press('Tab');
  await expect(page.locator('#results-back-study')).toBeFocused();
  await page.screenshot({ path: testInfo.outputPath('sampling-incomplete-narrow.png') });
  expect(errors).toEqual([]);
});

test('comparison freezes the question and complete roster prospectively and reconstructs exact first-attempt snapshots', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await harness(page, app);
  const study = await prepare(page, 'Prospective comparison');
  await page.locator('#results-comparison-mode').click();
  await page.getByText('Plan a new comparison', { exact: true }).click();
  await page.locator('#results-comparison-name').fill('Frozen synthetic assumptions');
  await page.locator('#results-comparison-question').fill('How do these fixed assumptions change the paired estimate?');
  await page.locator('#results-member-options').click();
  await expect(page.locator('#results-member-selector option')).toHaveCount(3);
  await addMember(page, 'nominal', 'Baseline');
  await addMember(page, 'volume-120', 'Increased volume');
  await page.locator('#results-comparison-freeze').click();
  await expect(page.locator('#results-comparison-summary')).toContainText('2 planned members');
  await expect(page.locator('#results-comparison-summary')).toContainText('How do these fixed assumptions');
  await expect(page.locator('#results-comparison-summary tbody tr')).toHaveCount(2);
  await expect(page.locator('#results-comparison-summary')).toContainText('unattempted');
  await page.locator('#results-comparison-verify').click();
  await expect(page.locator('#results-report-completeness')).toHaveText('incomplete');
  const before = (await download(page, 'Export report JSON')).text, unattempted = JSON.parse(before);
  expect(unattempted.coverage.planned_members).toBe(2);
  expect(unattempted.members.every(member => member.attempt.status === 'unattempted')).toBe(true);
  const tip = unattempted.definition.snapshot.tip;
  await page.locator('#results-comparison-next').click();
  await expect(page.locator('#results-comparison-next')).toBeDisabled();
  await page.locator('#results-comparison-verify').click();
  await expect(page.locator('#results-report-completeness')).toHaveText('complete');
  const complete = JSON.parse((await download(page, 'Export report JSON')).text);
  expect(complete.coverage.planned_members).toBe(2);
  expect(complete.members[0].attempt.attempt).toBe(complete.members[1].attempt.attempt);
  const csv = await download(page, 'Export comparison table');
  expect(csv.filename).toBe('comparison.csv'); expect(csv.text).toContain('member-2');
  await expect(page.locator('#results-member-plan option')).toHaveCount(0);
  await page.getByText('Reconstruct an earlier saved snapshot', { exact: true }).click();
  await page.locator('#results-comparison-tip').fill(tip);
  await page.locator('#results-comparison-replay').click();
  await expect(page.locator('#results-report-completeness')).toHaveText('incomplete');
  expect((await download(page, 'Export report JSON')).text).toBe(before);
  // Later retries remain inspectable, but cannot replace the frozen first one.
  await run(page, study.plan, complete.members[0].attempt.attempt);
  await page.locator('#results-comparison-verify').click();
  const retried = JSON.parse((await download(page, 'Export report JSON')).text);
  expect(retried.members[0].attempt.attempt).toBe(complete.members[0].attempt.attempt);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('comparison-narrow.png') });
  expect(errors).toEqual([]);
});

test('an incompatible prospective comparison refuses without losing the editable question, baseline or roster', async ({ page, app }) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await harness(page, app);
  const study = await prepare(page, 'Comparison refusal control');
  const incompatible = await page.evaluate(async plan => {
    const store = globalThis.resultsStore;
    store.accept(await store.action('derive', { plan }));
    const settings = JSON.parse(store.files['settings.json']); settings.visit_order.reverse();
    store.edit('Reversed synthetic visit support', { ...store.files, 'settings.json': JSON.stringify(settings) }, false);
    await store.save(); await store.review();
    return (await store.action('freeze', { draft: store.record.id, revision: store.record.revision, name: store.name, parent: plan })).plan;
  }, study.plan);
  await page.locator('#results-comparison-mode').click();
  await page.getByText('Plan a new comparison', { exact: true }).click();
  await page.locator('#results-comparison-name').fill('Retain my refused comparison');
  await page.locator('#results-comparison-question').fill('Does changing paired visit support remain admissible?');
  for (const [plan, label] of [[study.plan, 'Original support'], [incompatible, 'Reversed support']]) {
    await page.locator('#results-member-plan').selectOption(plan);
    await page.locator('#results-member-options').click();
    await addMember(page, 'nominal', label);
  }
  await page.locator('#results-comparison-baseline').selectOption('member-2');
  await page.locator('#results-comparison-freeze').click();
  await expect(page.locator('#results-message')).toHaveAttribute('role', 'alert');
  await expect(page.locator('#results-message')).toContainText('Incompatible observations');
  await expect(page.locator('#results-comparison-name')).toHaveValue('Retain my refused comparison');
  await expect(page.locator('#results-comparison-question')).toHaveValue('Does changing paired visit support remain admissible?');
  await expect(page.locator('#results-comparison-baseline')).toHaveValue('member-2');
  await expect(page.locator('#results-roster .results-roster-row')).toHaveCount(2);
  await expect(page.locator('#results-roster')).toContainText('Original support');
  await expect(page.locator('#results-roster')).toContainText('Reversed support');
  await expect(page.locator('#results-comparison-freeze')).toBeEnabled();
  expect(app.command('info', '--project', study.project).comparisons).toHaveLength(0);
  expect(app.command('info', '--project', study.project).attempts).toHaveLength(0);
  expect(errors).toEqual([]);
});
