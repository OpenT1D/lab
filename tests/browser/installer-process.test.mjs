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

test('deadline waits for delayed owned-group SIGKILL delivery before returning', async () => {
  const folder = await mkdtemp(path.join(tmpdir(), 'opent1d-install-delayed-kill-'));
  const heartbeat = path.join(folder, 'heartbeat');
  const originalKill = process.kill;
  let target, delivery, delivered = false;
  process.kill = (pid, kind) => {
    if (pid < 0 && kind === 'SIGKILL') {
      target = pid;
      delivery ||= new Promise(resolve => setTimeout(() => {
        delivered = true;
        try { originalKill(pid, kind); }
        catch (error) { assert.equal(error.code, 'ESRCH'); }
        resolve();
      }, 80));
      return true;
    }
    return originalKill(pid, kind);
  };
  try {
    const childCode = `const fs=require('node:fs');process.on('SIGTERM',()=>{});setInterval(()=>fs.writeFileSync(${JSON.stringify(heartbeat)},String(Date.now())),5);`;
    const parentCode = `require('node:child_process').spawn(process.execPath,['-e',${JSON.stringify(childCode)}],{stdio:'inherit'});setInterval(()=>{},1000);`;
    await assert.rejects(runPhase('delayed owned kill', process.execPath, ['-e', parentCode], { timeout: 500, grace: 200 }), error => {
      assert.equal(error.exitCode, 124);
      assert.equal(delivered, true, 'phase returned before owned SIGKILL delivery');
      return true;
    });
    const before = await readFile(heartbeat, 'utf8');
    await delay(150);
    assert.equal(await readFile(heartbeat, 'utf8'), before);
  } finally {
    process.kill = originalKill;
    await delivery;
    if (target) {
      try { originalKill(target, 'SIGKILL'); }
      catch (error) { assert.equal(error.code, 'ESRCH'); }
    }
    await rm(folder, { recursive: true, force: true });
  }
});

test('unconfirmed group cleanup remains bounded and preserves the primary deadline', async () => {
  const originalKill = process.kill;
  let target;
  process.kill = (pid, kind) => {
    if (pid < 0) {
      target = pid;
      if (kind === 0) return true; // A group that never becomes observably absent.
    }
    return originalKill(pid, kind);
  };
  const started = performance.now();
  try {
    await assert.rejects(runPhase('unconfirmed cleanup', process.execPath, ['-e', 'setInterval(()=>{},1000)'], { timeout: 100, grace: 50 }), error => {
      assert.equal(error.exitCode, 124);
      assert.equal(error.cleanupConfirmed, false);
      assert.match(error.message, /deadline exceeded; owned process-group cleanup unconfirmed/);
      assert.match(error.cleanupError.message, /still observable after SIGKILL deadline/);
      return true;
    });
    assert.ok(performance.now() - started < 2000, 'cleanup observation must have a finite deadline');
  } finally {
    process.kill = originalKill;
    if (target) {
      try { originalKill(target, 'SIGKILL'); }
      catch (error) { assert.equal(error.code, 'ESRCH'); }
    }
  }
});

test('cleanup signal errors cannot escape the deadline callback or replace its primary failure', async () => {
  const originalKill = process.kill;
  let denied = false;
  process.kill = (pid, kind) => {
    if (pid < 0 && kind === 'SIGTERM') {
      denied = true;
      throw Object.assign(new Error('fixture signal denied'), { code: 'EPERM' });
    }
    return originalKill(pid, kind);
  };
  try {
    await assert.rejects(runPhase('denied graceful stop', process.execPath, ['-e', 'setInterval(()=>{},1000)'], { timeout: 100, grace: 50 }), error => {
      assert.equal(denied, true);
      assert.equal(error.exitCode, 124);
      assert.equal(error.cleanupConfirmed, false);
      assert.equal(error.cleanupError.code, 'EPERM');
      assert.match(error.message, /deadline exceeded; owned process-group cleanup unconfirmed/);
      return true;
    });
  } finally {
    process.kill = originalKill;
  }
});

test('denied TERM and KILL bound direct-child exit observation without claiming cleanup', async () => {
  const originalKill = process.kill;
  let target, phase;
  const signals = new Set();
  process.kill = (pid, kind) => {
    if (pid < 0 && (kind === 'SIGTERM' || kind === 'SIGKILL')) {
      target = pid;
      signals.add(kind);
      throw Object.assign(new Error('fixture all signals denied'), { code: 'EPERM' });
    }
    return originalKill(pid, kind);
  };
  try {
    phase = runPhase('denied every stop', process.execPath, ['-e', 'setInterval(()=>{},1000)'], { timeout: 100, grace: 50 });
    const outcome = await Promise.race([
      phase.then(() => ({ unexpectedSuccess: true }), error => ({ error })),
      delay(1000).then(() => ({ hung: true })),
    ]);
    assert.equal(outcome.hung, undefined, 'direct-child exit observation must be bounded');
    assert.equal(outcome.error.exitCode, 124);
    assert.equal(outcome.error.cleanupConfirmed, false);
    assert.equal(outcome.error.cleanupError.code, 'EPERM');
    assert.deepEqual([...signals].sort(), ['SIGKILL', 'SIGTERM']);
    assert.match(outcome.error.message, /deadline exceeded; owned process-group cleanup unconfirmed/);
    assert.equal(originalKill(target, 0), true, 'denied stop must not be described as a reaped child');
  } finally {
    process.kill = originalKill;
    if (target) {
      try { originalKill(target, 'SIGKILL'); }
      catch (error) { assert.equal(error.code, 'ESRCH'); }
    }
    await phase?.catch(() => {});
  }
});
