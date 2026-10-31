import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { test, expect } from './installed-fixtures.mjs';

async function jobFinished(page) { await expect(page.locator('#job')).toBeHidden(); }
async function downloadJSON(page) {
  const waiting = page.waitForEvent('download');
  await page.locator('[data-download="report.json"]').click();
  return readFile(await (await waiting).path(), 'utf8');
}

test('frozen comparison: variants and derived plans, first attempts, snapshots and restart', async ({ page, app }, testInfo) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto(app.url);
  await page.locator('#project-name').fill('Reproducible synthetic contrasts');
  await page.locator('#create-project button').click();
  await expect(page.locator('#project-view')).toBeVisible();
  const project = await page.locator('#selected-path').textContent();
  const source = app.command('example', '--task', 'mmtt-sensitivity', '--case', 'complete', '--output', path.join(app.folder, 'inputs')).inputs;
  const settings = JSON.parse(await readFile(source['settings.json'], 'utf8')); settings.uncertainty.draws = 32;
  await writeFile(source['settings.json'], JSON.stringify(settings));
  const freeze = parent => app.command('freeze', '--project', project, '--task', 'mmtt-sensitivity', '--package', source['package.json'], '--csv', source['observations.csv'], '--settings', source['settings.json'], ...(parent ? ['--parent', parent] : [])).plan;
  const baseline = freeze(); settings.variants[0].volume_l = 5.1;
  await writeFile(source['settings.json'], JSON.stringify(settings));
  const derived = freeze(baseline);
  await page.locator('#refresh-project').click(); await jobFinished(page);
  await expect(page.locator('#comparison-plan option')).toHaveCount(2);
  await page.locator('#comparison-name').fill('Frozen volumes and assumptions');
  await page.locator('#comparison-question').fill('How do fixed synthetic assumptions change estimated secretion?');
  for (const [plan, variant, label] of [[baseline, 'nominal', 'Baseline'], [baseline, 'volume-120', 'Within-plan volume'], [derived, 'nominal', 'Derived volume']]) {
    await page.locator('#comparison-plan').selectOption(plan);
    await page.locator('#comparison-options').click();
    await expect(page.locator('#comparison-selector option')).toHaveCount(3);
    await page.locator('#comparison-selector').selectOption({ label: variant });
    await page.locator('#comparison-label').fill(label);
    await page.locator('#comparison-add').click();
  }
  await expect(page.locator('#comparison-roster')).toContainText('Within-plan volume');
  await page.locator('#comparison-freeze').click();
  await expect(page.locator('#comparison-status')).toContainText('Frozen comparison');
  await expect(page.locator('#comparison-changes')).toContainText('/selected_assumptions/volume_l');
  await expect(page.locator('#comparison-changes')).toContainText('5.502');
  await page.locator('#comparison-verify').click();
  await expect(page.locator('#report-completeness')).toHaveText('incomplete');
  const before = await downloadJSON(page), original = JSON.parse(before);
  expect(original.coverage.planned_members).toBe(3);
  expect(original.members.every(m => m.attempt.status === 'unattempted')).toBe(true);
  const comparison = await page.locator('#comparison-select').inputValue();
  for (let i = 0; i < 2; i++) {
    await expect(page.locator('#comparison-next')).toBeEnabled();
    await page.locator('#comparison-next').click();
    await jobFinished(page);
    await expect(page.locator('#comparison-status')).toContainText('Frozen comparison');
  }
  await expect(page.locator('#comparison-next')).toBeDisabled();
  await page.locator('#comparison-verify').click();
  await expect(page.locator('#report-completeness')).toHaveText('complete');
  const complete = JSON.parse(await downloadJSON(page));
  expect(complete.coverage.planned_members).toBe(3);
  expect(complete.members[0].attempt.attempt).toBe(complete.members[1].attempt.attempt);
  expect(complete.members[2].attempt.attempt).not.toBe(complete.members[0].attempt.attempt);
  const csvWaiting = page.waitForEvent('download'); await page.locator('#download-comparison').click();
  expect(await readFile(await (await csvWaiting).path(), 'utf8')).toContain('member-3');
  await page.locator('#comparison-tip').fill(original.definition.snapshot.tip);
  await page.locator('#comparison-replay').click();
  await expect(page.locator('#report-completeness')).toHaveText('incomplete');
  expect(await downloadJSON(page)).toBe(before);
  await app.restart(); await page.goto(app.url);
  await page.locator('#project-list button').click();
  await page.locator('#comparison-select').selectOption(comparison);
  await page.locator('#comparison-open').click();
  await expect(page.locator('#comparison-members')).toContainText('Derived volume');
  await page.locator('#comparison-verify').click();
  await expect(page.locator('#report-completeness')).toHaveText('complete');
  await page.setViewportSize({ width: 520, height: 900 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  await page.locator('#comparison-open').focus(); await page.keyboard.press('Tab');
  await expect(page.locator('#comparison-verify')).toBeFocused();
  await page.screenshot({ path: testInfo.outputPath('comparison-narrow.png'), fullPage: false });
  expect(errors).toEqual([]);
});
