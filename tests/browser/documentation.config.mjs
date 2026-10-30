import { defineConfig } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import common from './playwright.config.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const python = process.env.OPENT1D_BROWSER_PYTHON || path.join(
  root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);
const output = path.join(root, 'output/playwright/documentation');

export default defineConfig({
  ...common,
  testMatch: 'documentation*.spec.mjs',
  fullyParallel: true,
  workers: 4,
  timeout: 45_000,
  globalTimeout: 300_000,
  outputDir: `${output}/test-results`,
  reporter: [['list'], ['json', { outputFile: `${output}/results.json` }]],
  use: { ...common.use, baseURL: 'http://127.0.0.1:8766/lab/' },
  webServer: {
    command: `"${python}" -B -S -m http.server 8766 --bind 127.0.0.1 --directory _build/documentation-preview`,
    cwd: root,
    url: 'http://127.0.0.1:8766/lab/index.html',
    reuseExistingServer: false,
    timeout: 15_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
