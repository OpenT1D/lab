import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { test } from 'node:test';
import { runPhase } from './installer-process.mjs';

test('installer preserves success, nonzero exit and spawn failure', async () => {
  const result = await runPhase('control', process.execPath, ['-e', ''], { timeout: 2000 });
  assert.equal(result.phase, 'control');
  await assert.rejects(runPhase('failed dependency', process.execPath, ['-e', 'process.exit(7)'], { timeout: 2000 }), error => error.exitCode === 7);
  await assert.rejects(runPhase('missing dependency', '/opent1d-no-such-command', [], { timeout: 2000 }), /missing dependency/);
});

test('deadline kills owned descendants even when the parent exits first, preserving unrelated processes', async () => {
  const folder = await mkdtemp(path.join(tmpdir(), 'opent1d-install-process-'));
  const heartbeat = path.join(folder, 'heartbeat');
  const unrelated = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)']);
  try {
    const childCode = `const fs=require('node:fs'); process.on('SIGTERM',()=>{});setInterval(()=>fs.writeFileSync(${JSON.stringify(heartbeat)},String(Date.now())),10);`;
    const parentCode = `const {spawn}=require('node:child_process');spawn(process.execPath,['-e',${JSON.stringify(childCode)}],{stdio:'inherit'});setInterval(()=>{},1000);`;
    await assert.rejects(runPhase('stalled acquisition', process.execPath, ['-e', parentCode], { timeout: 500, grace: 100 }), error => error.exitCode === 124);
    const before = await readFile(heartbeat, 'utf8');
    await delay(150);
    assert.equal(await readFile(heartbeat, 'utf8'), before);
    assert.equal(unrelated.exitCode, null);
    assert.equal(unrelated.signalCode, null);
  } finally {
    unrelated.kill('SIGKILL');
    await new Promise(resolve => unrelated.once('exit', resolve));
    await rm(folder, { recursive: true, force: true });
  }
});
