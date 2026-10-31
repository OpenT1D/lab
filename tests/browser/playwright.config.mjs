import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

if (!process.env.PLAYWRIGHT_BROWSERS_PATH || !path.isAbsolute(process.env.PLAYWRIGHT_BROWSERS_PATH)) {
  throw new Error('Set PLAYWRIGHT_BROWSERS_PATH to an explicit temporary browser cache.');
}

const output = fileURLToPath(new URL('../../output/playwright/', import.meta.url));

export default defineConfig({
  testDir: '.',
  testMatch: ['mmtt.spec.mjs', 'installed-sampling.spec.mjs', 'workbench.spec.mjs', 'comparisons.spec.mjs', 'connected.spec.mjs', 'internal-candidate.spec.mjs', 'integrated-candidate.spec.mjs'],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 90_000,
  globalTimeout: 480_000,
  expect: { timeout: 30_000 },
  outputDir: `${output}/test-results`,
  reporter: [['list'], ['json', { outputFile: `${output}/results.json` }]],
  use: {
    actionTimeout: 15_000,
    navigationTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
