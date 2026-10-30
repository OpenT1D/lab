import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { test, expect } from './installed-fixtures.mjs';

async function state(page, app) {
  const token = await page.locator('meta[name="opent1d-token"]').getAttribute('content');
  return (await page.request.get(new URL('/api/state', app.url).href,
    { headers: { 'X-OpenT1D-Token': token } })).json();
}
async function create(page, app, name) {
  await page.goto(app.url);
  await page.locator('#project-name').fill(name);
  await page.locator('#create-project button').click();
  await expect(page.locator('#project-view')).toBeVisible();
}
async function saved(page) {
  await expect(page.locator('#draft-status')).toContainText('Saved revision');
  await expect(page.locator('#job')).toBeHidden();
}
async function upload(page, name, text) {
  await page.locator('#source-' + name.replaceAll('.', '-') + '-upload').setInputFiles({
    name, mimeType: name.endsWith('.csv') ? 'text/csv' : 'application/json', buffer: Buffer.from(text),
  });
}
async function inputs(app, task, example) {
  const result = app.command('example', '--task', task, '--case', example, '--output', path.join(app.folder, example + '-source'));
  const files = {};
  for (const [name, filename] of Object.entries(result.inputs)) {
    if (name === 'development') {
      files['development-package.json'] = await readFile(path.join(filename, 'package.json'), 'utf8');
      files['development-observations.csv'] = await readFile(path.join(filename, 'observations.csv'), 'utf8');
    } else files[name] = await readFile(filename, 'utf8');
  }
  const settings = JSON.parse(files['settings.json']); settings.uncertainty.draws = 32;
  files['settings.json'] = JSON.stringify(settings);
  return files;
}

test('own synthetic input: autosave, correction, exact bytes and immutable derivation', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const files = await inputs(app, 'mmtt-sensitivity', 'complete');
  const package_ = JSON.parse(files['package.json']); package_.provenance = 'Own invented browser study';
  files['package.json'] = JSON.stringify(package_);
  files['observations.csv'] = '\uFEFF' + files['observations.csv'].replaceAll('\n', '\r\n');
  await create(page, app, 'Own synthetic browser study');
  await page.locator('#new-draft').click();
  await expect(page.locator('#draft')).toBeVisible();
  for (const [name, text] of Object.entries(files)) await upload(page, name, text);
  await saved(page);
  await page.locator('#assumption-draws').fill('31');
  await saved(page);
  await page.locator('#validate-draft').click();
  await expect(page.locator('#draft-details')).toContainText('32–1024');
  await expect(page.locator('#freeze-draft')).toBeDisabled();
  await page.locator('#assumption-draws').fill('32');
  await saved(page);
  await expect(page.locator('#assumption-draws')).toBeFocused();
  const draftId = (await state(page, app)).drafts[0].id;
  await app.restart();
  await page.goto(app.url);
  await page.locator('#project-list button').click();
  await page.locator('#draft-select').selectOption(draftId);
  await page.locator('#open-draft').click();
  await expect(page.locator('#assumption-draws')).toHaveValue('32');
  await page.locator('#validate-draft').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await page.locator('#freeze-draft').click();
  await expect(page.locator('#run-plan')).toBeEnabled();
  const project = await page.locator('#selected-path').textContent();
  const original = await page.locator('#plan-select').inputValue();
  const detail = app.command('plan', '--project', project, '--plan', original);
  expect(detail.original_sha256['observations.csv']).toBe(createHash('sha256').update(Buffer.from(files['observations.csv'])).digest('hex'));
  await page.locator('#run-plan').click();
  await expect(page.locator('#attempt-list')).toContainText('3/3 planned slots complete');
  await page.getByRole('button', { name: 'Verify saved report', exact: true }).click();
  await expect(page.locator('#saved-report')).toBeVisible();
  const before = app.command('export-inputs', '--project', project, '--plan', original, '--output', path.join(app.folder, 'before-derive'));
  await page.locator('#derive-plan').click();
  await expect(page.locator('#parent-plan')).toHaveValue(original);
  await page.locator('#variant-0-volume_l').fill('5.1');
  await saved(page);
  await expect(page.locator('#run-plan')).toBeDisabled();
  await expect(page.locator('#readiness')).toContainText('editable concept');
  await page.locator('#validate-draft').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await page.locator('#freeze-draft').click();
  await expect(page.locator('#draft')).toBeHidden();
  const derived = await page.locator('#plan-select').inputValue();
  expect(derived).not.toBe(original);
  expect(app.command('plan', '--project', project, '--plan', derived).parent).toBe(original);
  const after = app.command('export-inputs', '--project', project, '--plan', original, '--output', path.join(app.folder, 'after-derive'));
  for (const name of Object.keys(before.inputs)) expect(await readFile(after.inputs[name])).toEqual(await readFile(before.inputs[name]));
  await page.screenshot({ path: testInfo.outputPath('derived-workbench.png'), fullPage: false });
  expect(errors).toEqual([]);
});

test('cross-tab concept recovery, explicit restore and exact large-seed raw editing', async ({ page, context, app }) => {
  await create(page, app, 'Concept conflict control');
  await page.locator('#prepare-form button[type="submit"]').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  const original = (await state(page, app)).drafts[0];
  const other = await context.newPage();
  await other.goto(app.url);
  await other.locator('#project-list button').click();
  await other.locator('#draft-select').selectOption(original.id);
  await other.locator('#open-draft').click();
  await other.locator('#assumption-draws').fill('64');
  await saved(other);
  await expect(page.locator('#draft-conflict')).toBeVisible();
  await page.locator('#assumption-draws').fill('32');
  await expect(page.locator('#freeze-draft')).toBeDisabled();
  await page.locator('#fork-draft').click();
  await saved(page);
  expect((await state(page, app)).drafts).toHaveLength(2);
  await page.locator('#close-draft').click();
  await page.locator('#draft-select').selectOption(original.id);
  await page.locator('#open-draft').click();
  await expect(page.locator('#assumption-draws')).toHaveValue('64');
  await page.locator('#draft-revision').selectOption(String(original.revision));
  await page.locator('#restore-draft').click();
  await expect(page.locator('#assumption-draws')).toHaveValue('128');
  await expect(page.locator('#freeze-draft')).toBeDisabled();
  const files = await inputs(app, 'mmtt-sensitivity', 'complete');
  const exact = files['settings.json'].replace('"seed":117', '"seed":9007199254740993');
  await page.locator('#raw-inputs > summary').click();
  await page.locator('#source-settings-json').fill(exact);
  await saved(page);
  await expect(page.locator('#assumptions')).toContainText('exact integer range');
  await expect(page.locator('#assumption-draws')).toHaveCount(0);
  await page.locator('#validate-draft').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await page.locator('#freeze-draft').click();
  await expect(page.locator('#draft')).toBeHidden();
  const project = await page.locator('#selected-path').textContent();
  const plan = await page.locator('#plan-select').inputValue();
  const exported = app.command('export-inputs', '--project', project, '--plan', plan, '--output', path.join(app.folder, 'large-seed-export'));
  expect(await readFile(exported.inputs['settings.json'], 'utf8')).toBe(exact);
  await page.locator('#inspect-plan').click();
  await expect(page.locator('#plan-details')).toContainText('9007199254740993');
  await expect(page.locator('#plan-details')).not.toContainText('9007199254740992');
  await other.close();
});

test('own sampling development split, editable schedules, keyboard and reflow', async ({ page, app }, testInfo) => {
  const files = await inputs(app, 'mmtt-sampling', 'information-loss');
  await create(page, app, 'Own sampling editor');
  await page.locator('#task').selectOption('mmtt-sampling');
  await page.locator('#new-draft').click();
  await expect(page.locator('#draft')).toBeVisible();
  for (const [name, text] of Object.entries(files)) await upload(page, name, name === 'development-package.json' ? files['package.json'] : text);
  await saved(page);
  await page.locator('#validate-draft').click();
  await expect(page.locator('#draft-details')).toContainText('development-only');
  await expect(page.locator('#freeze-draft')).toBeDisabled();
  await upload(page, 'development-package.json', files['development-package.json']);
  await page.locator('#schedule-three-times').fill('[0,30,120]');
  await saved(page);
  await expect(page.locator('#schedule-three-times')).toBeFocused();
  await page.locator('#schedule-three-times').press('Tab');
  await expect(page.locator('#selection-rationale')).toBeFocused();
  await page.locator('#validate-draft').click();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await expect(page.getByRole('spinbutton', { name: 'Uncertainty draws', exact: true })).toHaveAccessibleName('Uncertainty draws');
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  await page.locator('#draft-status').scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('concept-200-percent-text.png'), fullPage: false });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.evaluate(() => { document.documentElement.style.fontSize = ''; });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#draft-status').scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('concept-narrow.png'), fullPage: false });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator('#freeze-draft').click();
  await expect(page.locator('#run-plan')).toBeEnabled();
  const project = await page.locator('#selected-path').textContent();
  const plan = await page.locator('#plan-select').inputValue();
  expect(app.command('plan', '--project', project, '--plan', plan).scientific_input.design.subsets['three-times']).toEqual([0, 30, 120]);
});
