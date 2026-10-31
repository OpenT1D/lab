import { test, expect } from './installed-fixtures.mjs';

test.use({ mmttOnly: true });

test('bounded candidate exposes two MMTT tasks and preserves work across relaunch', async ({ page, app }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(app.url);
  await expect(page.locator('#candidate-capabilities')).toContainText('separately qualified candidate');
  await expect(page.locator('#native-card')).toBeHidden();
  await page.getByLabel('New project name').fill('Internal candidate exercise');
  await page.getByRole('button', { name: 'Create project', exact: true }).click();
  await expect(page.locator('#selected-name')).toHaveText('Internal candidate exercise');
  await expect(page.locator('#task option')).toHaveCount(2);
  await expect(page.locator('#connected-nav')).toBeHidden();
  await expect(page.locator('#connected-study')).toBeHidden();
  await expect(page.locator('#runtime-controls')).toBeHidden();
  await page.getByLabel('Research task', { exact: true }).selectOption('mmtt-sensitivity');
  await page.getByRole('button', { name: 'Prepare and validate inputs' }).click();
  await expect(page.locator('#draft')).toBeVisible();
  await expect(page.locator('#freeze-draft')).toBeEnabled();
  await page.getByRole('button', { name: 'Freeze plan', exact: true }).click();
  await expect(page.locator('#plan-select option')).toHaveCount(1);
  await page.getByRole('button', { name: 'Run plan', exact: true }).click();
  await expect(page.locator('#attempt-list')).toContainText('Execution: completed');
  await page.getByRole('button', { name: 'Verify saved report', exact: true }).click();
  await expect(page.locator('#saved-report')).toBeVisible();
  await expect(page.locator('#report-completeness')).toContainText('complete');
  await app.restart();
  await page.goto(app.url);
  await page.getByRole('button', { name: 'Internal candidate exercise', exact: true }).click();
  await expect(page.locator('#attempt-list')).toContainText('Execution: completed');
  await expect(page.locator('#task option')).toHaveCount(2);
  await page.setViewportSize({ width: 520, height: 900 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
