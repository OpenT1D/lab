import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

if (!process.env.PLAYWRIGHT_BROWSERS_PATH || !path.isAbsolute(process.env.PLAYWRIGHT_BROWSERS_PATH)) {
  throw new Error('Set PLAYWRIGHT_BROWSERS_PATH to an explicit temporary browser cache.');
}

const cli = fileURLToPath(new URL('node_modules/playwright/cli.js', import.meta.url));
const args = process.argv.slice(2);
if (!args.some(arg => ['chromium', 'firefox', 'webkit'].includes(arg))) args.unshift('chromium');
const result = spawnSync(process.execPath, [cli, 'install', ...args], {
  stdio: 'inherit',
  timeout: 300_000,
});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
