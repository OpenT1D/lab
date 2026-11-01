import { readFile } from 'node:fs/promises';
import { test, expect } from './installed-fixtures.mjs';

async function finished(page) { await expect(page.locator('#job')).toBeHidden(); }
async function reportJSON(page) {
  const pending = page.waitForEvent('download');
  await page.locator('[data-download="report.json"]').click();
  return readFile(await (await pending).path(), 'utf8');
}

test('connected study: prospective stages, absent native admission, fixed failures and prefix replay', async ({ page, app }, testInfo) => {
  // Same-source hosted runs: 134s passed; 150s expired during restart loading.
  // Retain bounded job waits/actions; allow 20% over the expired total budget.
  test.setTimeout(180_000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto(app.url);
  await page.locator('#project-name').fill('Connected synthetic boundary');
  await page.locator('#create-project button').click();
  await expect(page.locator('#project-view')).toBeVisible();
  await page.locator('#connected-name').fill('Known input through C-peptide');
  await page.locator('#connected-question').fill('Can the fixed matched inverse recover its known synthetic input?');
  await page.locator('#connected-freeze').click();
  await expect(page.locator('#connected-status')).toContainText('Run fixed forward plan');
  const study = await page.locator('#connected-select').inputValue();
  await expect(page.locator('#connected-stages')).toContainText('unattempted');
  await page.locator('#connected-verify').click();
  await expect(page.locator('#report-completeness')).toHaveText('incomplete · point checks unavailable');
  const initial = await reportJSON(page), original = JSON.parse(initial);
  expect(original.coverage.planned_rows).toBe(72);
  expect(original.coverage.unavailable_point_rows).toBe(72);
  expect(original.rows.every(row => row.value === null)).toBe(true);
  await expect(page.locator('#report-context')).toContainText('connected study');
  const csvPending = page.waitForEvent('download'); await page.locator('#download-study').click();
  const csv = await readFile(await (await csvPending).path(), 'utf8');
  expect(csv.trim().split('\n')).toHaveLength(73);
  // This public/root test deliberately has no native attachment. It must retain
  // a genuine failed first attempt and all downstream rows, without a fake chain.
  await page.locator('#connected-next').click(); await finished(page);
  await expect(page.locator('#connected-next')).toBeDisabled();
  await expect(page.locator('#connected-stages')).toContainText('failed');
  await page.locator('#connected-verify').click();
  await finished(page);
  await expect(page.locator('#report-context')).not.toContainText(original.definition.snapshot.tip);
  const failedText = await reportJSON(page), failed = JSON.parse(failedText);
  expect(failed.coverage.unavailable_point_rows).toBe(72);
  expect(failed.definition.stages.forward.status).toBe('failed');
  expect(failed.definition.sampling_plan).toBeNull();
  // Programmatically selecting a newly frozen study must withdraw the old report.
  await page.locator('#connected-name').fill('Missing observation control');
  await page.locator('#connected-case').selectOption('missing-evaluation');
  await page.locator('#connected-freeze').click(); await finished(page);
  await expect(page.locator('#saved-report')).toBeHidden();
  await page.locator('#connected-select').selectOption(study);
  await page.locator('#connected-open').click(); await finished(page);
  await page.locator('#connected-tip').fill(original.definition.snapshot.tip);
  await page.locator('#connected-replay').click(); await finished(page);
  expect(await reportJSON(page)).toBe(initial);
  await app.restart(); await page.goto(app.url);
  await page.locator('#project-list button').click();
  await page.locator('#connected-select').selectOption(study);
  await page.locator('#connected-open').click(); await finished(page);
  await expect(page.locator('#connected-stages')).toContainText('failed');
  await page.locator('#connected-tip').fill(failed.definition.snapshot.tip);
  await page.locator('#connected-replay').click(); await finished(page);
  await expect(page.locator('#saved-report')).toBeVisible();
  await expect(page.locator('#report-context')).toContainText(failed.definition.snapshot.tip);
  expect(await reportJSON(page)).toBe(failedText);
  await page.setViewportSize({ width: 520, height: 900 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  await page.locator('.attempt h3').evaluateAll(headings => {
    for (const heading of headings) heading.style.fontFamily = 'monospace';
  });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(await page.locator('.attempt h3').evaluateAll(headings => headings.every(heading =>
    heading.getBoundingClientRect().right <= heading.parentElement.getBoundingClientRect().right + 0.5,
  ))).toBe(true);
  await page.locator('#connected-open').focus(); await page.keyboard.press('Tab');
  await expect(page.locator('#connected-next')).not.toBeFocused(); // Disabled stages are skipped.
  await expect(page.locator('#connected-verify')).toBeFocused();
  await page.screenshot({ path: testInfo.outputPath('connected-narrow.png'), fullPage: false });
  await page.evaluate(() => { document.documentElement.style.fontSize = ''; });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
