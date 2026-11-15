import path from 'node:path';
import { test, expect } from './installed-fixtures.mjs';

async function state(page, app) {
  const token = await page.locator('meta[name="opent1d-token"]').getAttribute('content');
  return (await page.request.get(new URL('/api/state', app.url).href, { headers: { 'X-OpenT1D-Token': token } })).json();
}
async function create(page, app, name, task = 'mmtt-sensitivity', mode = 'guided') {
  await page.goto(new URL('/workbench', app.url).href);
  await page.locator(mode === 'empty' ? '#start-empty' : mode === 'template' ? '#use-template' : '#new-project').click();
  await page.locator('#project-name').fill(name);
  await page.locator('#new-approach').selectOption(task);
  await page.locator('#confirm-project').click();
  await expect(page.locator('#project-dialog')).not.toBeVisible();
  await expect(page.locator('#workspace')).toBeVisible();
  await expect(page.locator('#project-title')).toHaveText(name);
}
async function saved(page, question) {
  await page.locator('#research-question').fill(question);
  await page.keyboard.press('ControlOrMeta+s');
  await expect(page.locator('#save-state')).toHaveText('');
  await expect(page.locator('#notice')).not.toBeVisible();
}
async function currentDraft(page, app) {
  const incoming = await state(page, app);
  const project = incoming.projects.find(p => p.name === 'Concept persistence');
  const summary = incoming.drafts.filter(d => d.project === project.id).sort((a, b) => b.saved_at.localeCompare(a.saved_at))[0];
  const token = await page.locator('meta[name="opent1d-token"]').getAttribute('content');
  return (await page.request.get(new URL('/api/drafts/' + summary.id, app.url).href, { headers: { 'X-OpenT1D-Token': token } })).json();
}

test('reopening holds navigation until the saved concept and execution history are loaded', async ({ page, app }) => {
  await create(page, app, 'Opening saved work');
  const incoming = await state(page, app), project = incoming.projects.find(value => value.name === 'Opening saved work');
  const draft = incoming.drafts.find(value => value.project === project.id);
  await page.locator('#all-projects').click();
  let release, requested;
  const held = new Promise(resolve => { release = resolve; }), arrived = new Promise(resolve => { requested = resolve; });
  await page.route('**/api/drafts/' + draft.id, async route => { requested(); await held; await route.continue(); });
  await page.locator('#recent-projects button').filter({ hasText: 'Opening saved work' }).click();
  await arrived;
  try {
    await expect(page.locator('#tree-results')).toBeDisabled();
    await expect(page.locator('#tree-study')).toBeDisabled();
    await expect(page.locator('#project-loading')).toBeVisible();
    await expect(page.locator('#study-empty')).not.toBeVisible();
  } finally { release(); }
  await expect(page.locator('#project-loading')).not.toBeVisible();
  await expect(page.locator('#tree-results')).toBeEnabled();
  await page.locator('#tree-results').click();
  await expect(page.locator('#results-body')).toBeVisible();
  await expect(page.locator('#results-heading')).toBeFocused();
});

test('both MMTT approaches persist through close, browser reload and actual installed-server restart', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [task, title] of [['mmtt-sensitivity', 'Paired study'], ['mmtt-sampling', 'Sampling study']]) {
    await create(page, app, title, task);
    await saved(page, title + ': edited research question');
    await page.locator('#assumptions').click();
    await page.locator('#draws').fill('64');
    await page.locator('#files-form button[type=submit]').click();
    await page.keyboard.press('ControlOrMeta+s');
    await expect(page.locator('#save-state')).toHaveText('');
    await page.locator('#all-projects').click();
    await expect(page.locator('#startup')).toBeVisible();
    await page.locator('#recent-projects button').filter({ hasText: title }).click();
    await expect(page.locator('#research-question')).toHaveValue(title + ': edited research question');
    await page.locator('#assumptions').click();
    await expect(page.locator('#draws')).toHaveValue('64');
    await page.locator('#files-dialog .dialog-close').first().click();
    await app.restart();
    await page.goto(new URL('/workbench', app.url).href);
    await page.locator('#recent-projects button').filter({ hasText: title }).click();
    await expect(page.locator('#research-question')).toHaveValue(title + ': edited research question');
    await expect(page.locator('#approach')).toHaveValue(task);
    await page.locator('#review-study').click();
    await expect(page.locator('#information-dialog')).toContainText('passed the existing task validation');
    await page.locator('#information-dialog .dialog-close').first().click();
    await page.screenshot({ path: testInfo.outputPath(task + '-study.png') });
  }
  await page.locator('#all-projects').click();
  await page.screenshot({ path: testInfo.outputPath('startup.png') });
  await page.locator('#recent-projects button').filter({ hasText: 'Paired study' }).click();
  await expect(page.locator('#research-question')).toHaveValue('Paired study: edited research question');
  await page.locator('#close-study').click();
  await expect(page.locator('#study-body')).not.toBeVisible();
  await page.locator('#tree-study').click();
  await expect(page.locator('#study-body')).toBeVisible();
  await page.locator('#close-study').click();
  await page.locator('#all-projects').click();
  await page.locator('#recent-projects button').filter({ hasText: 'Paired study' }).click();
  await expect(page.locator('#study-body')).toBeVisible();
  const imageChecks = await page.locator('#workspace img').evaluateAll(images => images.filter(i => i.getBoundingClientRect().width).map(i => ({ src: i.getAttribute('src'), width: i.width, height: i.height, loaded: i.complete && i.naturalWidth > 0, matchingSlot: i.naturalWidth === i.width && i.naturalHeight === i.height && i.getBoundingClientRect().width === i.width && i.getBoundingClientRect().height === i.height })));
  expect(imageChecks.every(i => i.loaded)).toBe(true);
  expect(imageChecks.every(i => i.matchingSlot)).toBe(true);
  expect(await page.evaluate(() => document.fonts.check('16px Inter'))).toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#review-study')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator('#explorer')).not.toBeVisible();
  await page.locator('#show-project').click();
  await expect(page.locator('#explorer')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#explorer')).not.toBeVisible();
  await expect(page.locator('#show-project')).toBeFocused();
  await testInfo.attach('visible-assets.json', { body: JSON.stringify(imageChecks, null, 2), contentType: 'application/json' });
  expect(errors).toEqual([]);
});

test('empty and template creation, real validation errors and opening an existing project use shared services', async ({ page, app }) => {
  await create(page, app, 'Empty project', 'mmtt-sampling', 'empty');
  await expect(page.locator('#observations-description')).toContainText('Add your');
  await saved(page, 'My blank sampling question');
  await page.locator('#review-study').click();
  await expect(page.locator('#information-title')).toHaveText('Check the study inputs');
  await page.locator('#information-dialog .dialog-close').first().click();
  await page.locator('#all-projects').click();
  await create(page, app, 'From template', 'mmtt-sensitivity', 'template');
  const incoming = await state(page, app);
  expect(incoming.drafts.filter(d => d.project === incoming.projects.find(p => p.name === 'From template').id)).toHaveLength(1);
  const external = app.command('create', '--project', path.join(app.folder, 'external'), '--name', 'External project');
  expect(external).toBeTruthy();
  await page.locator('#all-projects').click();
  await page.locator('#open-project').click();
  await page.locator('#project-name').fill(path.join(app.folder, 'external'));
  await page.locator('#confirm-project').click();
  await expect(page.locator('#study-empty')).toBeVisible();
  expect(app.command('info', '--project', path.join(app.folder, 'external')).plans).toHaveLength(0);
  await page.locator('#create-study').click();
  await page.locator('#confirm-project').click();
  await expect(page.locator('#study-form')).toBeVisible();
  await page.locator('#all-projects').click();
  await expect(page.locator('#recent-projects button')).toHaveCount(3);
  expect((await page.locator('.start-window').boundingBox()).height).toBeLessThanOrEqual(424);
  expect(await page.locator('#recent-projects').evaluate(e => e.scrollHeight > e.clientHeight)).toBe(true);
  await page.locator('#recent-projects button').filter({ hasText: 'Empty project' }).click();
  await expect(page.locator('#research-question')).toHaveValue('My blank sampling question');
});

test('failed saves retain edits and refuse navigation; retry preserves untouched source bytes', async ({ page, app }) => {
  await create(page, app, 'Concept persistence');
  const before = await currentDraft(page, app);
  await page.route('**/api/drafts', route => route.abort('failed'));
  await page.locator('#research-question').fill('Retained after failed save');
  await expect(page.locator('#notice')).toBeVisible();
  await page.locator('#all-projects').click();
  await expect(page.locator('#workspace')).toBeVisible();
  await expect(page.locator('#research-question')).toHaveValue('Retained after failed save');
  expect((await currentDraft(page, app)).name).toBe(before.name);
  await page.unroute('**/api/drafts');
  await page.locator('#retry-save').click();
  await expect(page.locator('#save-state')).toHaveText('');
  const after = await currentDraft(page, app);
  expect(after.revision).toBeGreaterThan(before.revision);
  expect(after.name).toBe('Retained after failed save');
  expect(after.files).toEqual(before.files);
  const project = (await state(page, app)).projects.find(p => p.id === after.project);
  expect(app.command('info', '--project', project.path).plans).toHaveLength(0);
});

test('two-tab conflict preserves both revisions and permits a separate saved study', async ({ page, app, context }) => {
  await create(page, app, 'Concept persistence');
  const other = await context.newPage();
  await other.goto(new URL('/workbench', app.url).href);
  await other.locator('#recent-projects button').filter({ hasText: 'Concept persistence' }).click();
  await expect(other.locator('#research-question')).toBeVisible();
  await saved(page, 'Saved in the first tab');
  await other.locator('#research-question').fill('Different edits in the second tab');
  await other.keyboard.press('ControlOrMeta+s');
  await expect(other.locator('#save-copy')).toBeVisible();
  await expect(other.locator('#research-question')).toHaveValue('Different edits in the second tab');
  expect((await currentDraft(page, app)).name).toBe('Saved in the first tab');
  await other.locator('#save-copy').click();
  await expect(other.locator('#notice')).not.toBeVisible();
  const drafts = (await state(other, app)).drafts;
  expect(drafts.map(d => d.name)).toEqual(expect.arrayContaining(['Saved in the first tab', 'Different edits in the second tab']));
  await other.close();
});

test('raw and uploaded inputs preserve large integers, BOM and line endings', async ({ page, app }) => {
  await create(page, app, 'Concept persistence');
  const before = await currentDraft(page, app);
  await page.locator('#assumptions').click();
  await page.locator('#input-text').fill('\uFEFF' + before.files['settings.json']);
  await expect(page.locator('#draws')).toBeVisible();
  await page.locator('#draws').fill('64');
  await expect(page.locator('#file-error')).not.toBeVisible();
  await page.locator('#files-form button[type=submit]').click();
  await page.keyboard.press('ControlOrMeta+s');
  await expect(page.locator('#save-state')).toHaveText('');
  const changedSettings = (await currentDraft(page, app)).files['settings.json'];
  expect(JSON.parse(changedSettings).uncertainty.draws).toBe(64);
  const exactSettings = '\uFEFF' + changedSettings.replace(/"seed":\s*\d+/, '"seed":9007199254740993');
  expect(exactSettings).toContain('9007199254740993');
  await page.locator('#assumptions').click();
  await page.locator('#input-text').fill(exactSettings);
  await expect(page.locator('#structured-warning')).toBeVisible();
  await expect(page.locator('#draws')).not.toBeVisible();
  await page.locator('#files-form button[type=submit]').click();
  await page.keyboard.press('ControlOrMeta+s');
  await expect(page.locator('#save-state')).toHaveText('');
  await page.locator('#observations').click();
  const exactObservations = '\uFEFF' + before.files['observations.csv'].replace(/\r\n?|\n/g, '\r\n');
  await page.locator('#input-upload').setInputFiles({ name: 'observations.csv', mimeType: 'text/csv', buffer: Buffer.from(exactObservations) });
  await expect(page.locator('#input-text')).toHaveValue(exactObservations.replaceAll('\r\n', '\n'));
  await page.locator('#files-form button[type=submit]').click();
  await page.keyboard.press('ControlOrMeta+s');
  await expect(page.locator('#save-state')).toHaveText('');
  const after = await currentDraft(page, app);
  expect(after.files['settings.json']).toBe(exactSettings);
  expect(after.files['observations.csv']).toBe(exactObservations);
  await page.locator('#assumptions').click();
  await expect(page.locator('#structured-warning')).toBeVisible();
  await expect(page.locator('#input-text')).toHaveValue(exactSettings);
});
