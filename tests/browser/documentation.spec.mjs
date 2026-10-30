import { test, expect } from '@playwright/test';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertClean, auditDocument, inspectRendering, monitor } from './documentation-audit.mjs';

const site = fileURLToPath(new URL('../../_build/documentation-preview/lab/', import.meta.url));
const files = readdirSync(site, { recursive: true, withFileTypes: true })
  .filter(entry => entry.isFile())
  .map(entry => path.relative(site, path.join(entry.parentPath, entry.name)).split(path.sep).join('/'))
  .sort();
const pages = files.filter(name => name.endsWith('.html'));
for (const required of ['index.html', 'docs/index.html', 'search.html']) {
  if (!pages.includes(required)) throw new Error(`Missing staged documentation entry: ${required}`);
}
const encoded = name => name.split('/').map(encodeURIComponent).join('/');

for (const name of pages) {
  test(`page: ${name}`, async ({ page, request, baseURL }, testInfo) => {
    let receipt;
    try {
      receipt = await auditDocument(page, new URL(encoded(name), baseURL).href, request);
    } catch (error) {
      receipt = error.receipt;
      throw error;
    } finally {
      if (receipt) await testInfo.attach('browser-audit.json', {
        body: JSON.stringify(receipt, null, 2), contentType: 'application/json',
      });
    }
  });
}

test('all staged assets and downloads return their exact bytes', async ({ request, baseURL }) => {
  const assets = files.filter(name => !name.endsWith('.html'));
  expect(assets.length).toBeGreaterThan(0);
  let cursor = 0;
  await Promise.all(Array.from({ length: 4 }, async () => {
    while (cursor < assets.length) {
      const name = assets[cursor++];
      const response = await request.get(new URL(encoded(name), baseURL).href);
      try {
        expect(response.status(), name).toBe(200);
        expect(await response.body(), name).toEqual(readFileSync(path.join(site, name)));
      } finally {
        await response.dispose();
      }
    }
  }));
});

test('search finishes and opens a result', async ({ page, baseURL }, testInfo) => {
  const { receipt, stop } = monitor(page);
  try {
    await page.goto(new URL('docs/index.html', baseURL).href);
    await page.getByRole('searchbox').or(page.getByRole('textbox', { name: 'Search', exact: true })).fill('MMTT');
    await page.keyboard.press('Enter');
    await expect(page.locator('#search-results h2')).toHaveText('Search Results');
    const result = page.locator('#search-results a').first();
    await expect(result).toBeVisible();
    const target = await result.getAttribute('href');
    const expected = new URL(target, page.url()).href;
    await result.click();
    await expect(page).toHaveURL(expected);
    await expect(page.locator('article h1')).toBeVisible();
    await page.waitForLoadState('networkidle');
    assertClean(receipt);
  } finally {
    stop();
    await testInfo.attach('search-audit.json', { body: JSON.stringify(receipt), contentType: 'application/json' });
  }
});

test('Mermaid renders again after switching to dark theme', async ({ page, baseURL }, testInfo) => {
  const { receipt, stop } = monitor(page);
  try {
    await page.goto(new URL('docs/research/project-design.html', baseURL).href);
    await inspectRendering(page, receipt);
    await expect(page.locator('.mermaid svg')).toHaveCount(1);
    const initialDiagram = await page.locator('.mermaid svg').elementHandle();
    await page.getByRole('button', { name: 'Toggle Light / Dark / Auto color theme' }).click();
    await expect(page.locator('body')).toHaveAttribute('data-theme', 'dark');
    await expect.poll(() => initialDiagram.evaluate(node => node.isConnected)).toBe(false);
    await initialDiagram.dispose();
    await inspectRendering(page, receipt);
    await expect(page.locator('.mermaid svg')).toHaveCount(1);
    assertClean(receipt);
  } finally {
    stop();
    await testInfo.attach('theme-audit.json', { body: JSON.stringify(receipt), contentType: 'application/json' });
  }
});
