import { test as base, expect } from '@playwright/test';
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import { cp, mkdir, mkdtemp, readFile, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const python = process.env.OPENT1D_BROWSER_PYTHON || path.join(root, '.venv/bin/python');

function command(executable, args, options) {
  const result = spawnSync(executable, args, { ...options, encoding: 'utf8', timeout: 90_000 });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${executable} failed: ${result.stdout}\n${result.stderr}`);
  return result.stdout;
}

export const test = base.extend({
  mmttOnly: [false, { option: true }],
  app: async ({ mmttOnly }, use, testInfo) => {
    const folder = await realpath(await mkdtemp(path.join(tmpdir(), 'opent1d-installed-browser-')));
    const env = { ...process.env, UV_CACHE_DIR: path.join(folder, 'cache'), PYTHONNOUSERSITE: '1' };
    delete env.PYTHONPATH;
    const options = { env, cwd: folder };
    const workspace = path.join(folder, 'workspace');
    await mkdir(testInfo.outputDir, { recursive: true });
    const log = createWriteStream(testInfo.outputPath('installed-server.log'));
    let child, exited, failed = false;
    async function stop() {
      if (!child) return;
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
      let timer;
      try {
        await Promise.race([exited, new Promise((_, reject) => {
          timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error('Installed server cleanup exceeded 45 seconds')); }, 45_000);
        })]);
      } finally { clearTimeout(timer); child = null; }
    }
    async function start(cli) {
      child = spawn(cli, ['gui', '--workspace', workspace], { ...options, stdio: ['ignore', 'pipe', 'pipe'] });
      exited = new Promise(resolve => { child.once('exit', resolve); child.once('error', resolve); });
      child.stdout.on('data', chunk => log.write(chunk));
      child.stderr.on('data', chunk => log.write(chunk));
      const lines = createInterface({ input: child.stdout });
      let timer;
      try {
        return await new Promise((resolve, reject) => {
          timer = setTimeout(() => reject(new Error('Installed server did not become ready')), 30_000);
          child.once('error', reject);
          child.once('exit', code => reject(new Error(`Installed server exited before readiness: ${code}`)));
          lines.on('line', line => { if (line.startsWith('OpenT1D project GUI: ')) resolve(line.slice('OpenT1D project GUI: '.length)); });
        });
      } finally { clearTimeout(timer); lines.close(); }
    }
    try {
      const retained = mmttOnly && process.env.OPENT1D_READER_CANDIDATE_RECEIPT;
      const receipt = retained ? await readFile(retained, 'utf8') : command(python, [path.join(root, 'scripts/build_sdk.py'), '--output', path.join(folder, 'build'), '--allow-dirty', '--build-label', 'sampling-browser-regression', ...(mmttOnly ? ['--mmtt-only'] : [])], options);
      if (retained && createHash('sha256').update(await readFile(JSON.parse(receipt).wheel)).digest('hex') !== JSON.parse(receipt).wheel_sha256) throw new Error('Retained candidate wheel differs from its receipt');
      await writeFile(testInfo.outputPath('build-receipt.json'), receipt);
      const installedPython = path.join(folder, 'sdk/bin/python');
      command('uv', ['venv', '--offline', '--python', python, path.join(folder, 'sdk')], options);
      command('uv', ['pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', installedPython, JSON.parse(receipt).wheel], options);
      const cli = path.join(folder, 'sdk/bin/opent1d-lab');
      if (retained) {
        const expected = JSON.parse(receipt), actual = JSON.parse(command(cli, ['installation'], options));
        if (expected.source.dirty !== false || actual.source.dirty !== false || actual.source.revision !== expected.source.revision || actual.build_label !== expected.build_label || actual.descriptor_sha256 !== expected.descriptor_sha256 || actual.schema !== 'opent1d.installed-sdk/4' || actual.schema !== expected.descriptor_schema || JSON.stringify(actual.tasks) !== JSON.stringify(['mmtt-sensitivity', 'mmtt-sampling']) || JSON.stringify(actual.tasks) !== JSON.stringify(expected.tasks) || actual.native_execution !== 'unavailable-public-policy' || actual.native_execution !== expected.native_execution) throw new Error('Installed candidate descriptor differs from the retained clean two-task receipt');
      }
      const app = { folder, workspace, cli, installedPython, env, command: (...args) => JSON.parse(command(cli, args.map(String), options)), url: await start(cli), restart: async () => { await stop(); app.url = await start(cli); } };
      await use(app);
    } catch (error) { failed = true; throw error; }
    finally {
      try { await stop(); }
      finally {
        log.end();
        if (failed || testInfo.status !== testInfo.expectedStatus) await cp(folder, testInfo.outputPath('installed-workspace'), { recursive: true });
        await rm(folder, { recursive: true, force: true });
      }
    }
  },
});

export { expect };
