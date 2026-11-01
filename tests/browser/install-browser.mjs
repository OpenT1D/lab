import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runPhase } from './installer-process.mjs';

if (!process.env.PLAYWRIGHT_BROWSERS_PATH || !path.isAbsolute(process.env.PLAYWRIGHT_BROWSERS_PATH)) {
  throw new Error('Set PLAYWRIGHT_BROWSERS_PATH to an explicit temporary browser cache.');
}

const cli = fileURLToPath(new URL('node_modules/playwright/cli.js', import.meta.url));
const args = process.argv.slice(2);
if (args.includes('--with-deps') && process.platform === 'linux' && process.getuid() !== 0) {
  throw new Error('Linux --with-deps requires the bounded installer to run as root, so it can clean up apt descendants. Preserve only PLAYWRIGHT_BROWSERS_PATH with sudo.');
}
if (!args.some(arg => ['chromium', 'firefox', 'webkit'].includes(arg))) args.unshift('chromium');
const browsers = args.filter(arg => ['chromium', 'firefox', 'webkit'].includes(arg));
const until = performance.now() + 300_000; // Preserve the combined installation budget.
try {
  if (args.includes('--with-deps')) {
    await runPhase('Linux/system dependencies', process.execPath, [cli, 'install-deps', ...browsers], { timeout: until - performance.now() });
  }
  await runPhase('browser download', process.execPath, [cli, 'install', ...args.filter(arg => arg !== '--with-deps')], { timeout: until - performance.now() });
} catch (error) {
  console.error(error.message);
  process.exitCode = error.exitCode || 1;
}
