import { test as base, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import { cp, mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const launcher = fileURLToPath(new URL('serve.py', import.meta.url));
const python = process.env.OPENT1D_BROWSER_PYTHON || path.join(
  root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);

async function bounded(promise, milliseconds, message) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(message)), milliseconds); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

export const test = base.extend({
  app: async ({}, use, testInfo) => {
    const workspace = await mkdtemp(path.join(tmpdir(), 'opent1d-browser-'));
    await mkdir(testInfo.outputDir, { recursive: true });
    const log = createWriteStream(testInfo.outputPath('server.log'));
    let child, exited, failed = false;

    async function stop() {
      if (!child) return;
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
      try {
        await bounded(exited, 45_000, 'The local server did not finish owned-process cleanup.');
      } catch (error) {
        child.kill('SIGKILL');
        await bounded(exited, 5_000, 'The local server did not exit after forced termination.');
        throw error;
      } finally {
        child = null;
      }
    }

    async function start() {
      child = spawn(python, ['-B', '-S', launcher, '--workspace', workspace], {
        cwd: root,
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONNOUSERSITE: '1' },
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      exited = new Promise(resolve => {
        child.once('exit', resolve);
        child.once('error', resolve);
      });
      child.stdout.on('data', chunk => log.write(chunk));
      child.stderr.on('data', chunk => log.write(chunk));
      const lines = createInterface({ input: child.stdout });
      try {
        return await bounded(new Promise((resolve, reject) => {
          child.once('error', reject);
          child.once('exit', code => reject(new Error(`The local server exited before readiness: ${code}`)));
          lines.on('line', line => {
            if (line.startsWith('OPENT1D_BROWSER_URL=')) resolve(line.split('=')[1]);
          });
        }), 30_000, 'The real local server did not become ready.');
      } finally {
        lines.close();
      }
    }

    const app = { workspace, url: null, restart: async () => { await stop(); app.url = await start(); } };
    try {
      app.url = await start();
      await use(app);
    } catch (error) {
      failed = true;
      throw error;
    } finally {
      try {
        await stop();
      } catch (error) {
        failed = true;
        throw error;
      } finally {
        try {
          if (failed || testInfo.status !== testInfo.expectedStatus) {
            await cp(workspace, testInfo.outputPath('workspace'), { recursive: true });
          }
        } finally {
          log.end();
          await rm(workspace, { recursive: true, force: true });
        }
      }
    }
  },
});

export { expect };
