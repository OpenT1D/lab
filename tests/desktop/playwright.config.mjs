import { defineConfig } from '../browser/node_modules/@playwright/test/index.mjs';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  testDir: '.', testMatch: ['mac.spec.mjs', 'comparison.spec.mjs'], workers: 1, fullyParallel: false,
  forbidOnly: true, retries: 0, timeout: 120000, globalTimeout: 600000,
  expect: { timeout: 15000 },
  outputDir: fileURLToPath(new URL('../../results/concept-desktop-tests/artifacts', import.meta.url)),
  reporter: [['list'], ['json', { outputFile: fileURLToPath(new URL('../../results/concept-desktop-tests/results.json', import.meta.url)) }]],
});
