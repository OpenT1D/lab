// These are adversarial QA lifecycle fixtures, not a simulated MMTT backend.
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import * as files from 'node:fs/promises';
import { mkdtemp, readFile, readdir, rename, rm, stat, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { completeProbe, disposeObservers, errorDetails, observeApplication, receiptPublication, waitForApplications } from './mac_probe_lifecycle.mjs';

async function folder(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'opent1d-probe-unit-'));
  t.after(() => rm(root, { recursive: true }));
  return root;
}

class OpenFixture extends EventEmitter {
  signals = [];
  kill(signal) { this.signals.push(signal); this.emit('close', null, signal); return true; }
  unref() {}
}

test('PASS commits only after every cleanup stage succeeds', async t => {
  const root = await folder(t), order = [];
  const publication = receiptPublication(path.join(root, 'receipt.json'));
  await completeProbe({
    cleanup: ['authenticated shutdown', 'native exits', 'trace', 'browser'].map(name =>
      [name, async () => { order.push(name); }]),
    commit: async () => {
      assert.deepEqual(order, ['authenticated shutdown', 'native exits', 'trace', 'browser']);
      order.push('PASS');
      await publication.publish({ passed: true });
    },
    rollback: () => publication.rollback(),
    dispose: async () => { assert.fail('Successful observers need no cancellation'); },
    recordFailure: async () => { assert.fail('No failure is expected'); },
  });
  assert.equal(JSON.parse(await readFile(path.join(root, 'receipt.json'))).passed, true);
  assert.equal(order.at(-1), 'PASS');
  assert.deepEqual(await readdir(root), ['receipt.json']);
});

test('A complete pending write followed by close EIO is never published', async t => {
  const root = await folder(t), target = path.join(root, 'receipt.json');
  const cause = Object.assign(new Error('Invented close EIO'), { code: 'EIO' });
  const publication = receiptPublication(target, { ...files, open: async (...args) => {
    const handle = await files.open(...args);
    return { stat: (...args) => handle.stat(...args), writeFile: (...args) => handle.writeFile(...args),
      close: async () => {
        await handle.close();
        assert.equal(JSON.parse(await readFile(args[0])).checks.length, 7);
        await assert.rejects(stat(target), { code: 'ENOENT' });
        throw cause;
      } };
  } });
  await assert.rejects(completeProbe({ cleanup: [],
    commit: () => publication.publish({ checks: Array(7).fill('controlled'), cleanup: 'confirmed' }),
    rollback: () => publication.rollback(), dispose: async () => {},
    recordFailure: error => writeFile(path.join(root, 'failure.json'), JSON.stringify(errorDetails(error))),
  }), error => error.errors[0].cause === cause);
  await assert.rejects(stat(target), { code: 'ENOENT' });
  assert.deepEqual(await readdir(root), ['failure.json']);
});

test('A published valid receipt is rolled back when commit subsequently rejects EIO', async t => {
  const root = await folder(t), target = path.join(root, 'receipt.json');
  const cause = Object.assign(new Error('Invented post-publication EIO'), { code: 'EIO' });
  let fail = true;
  const publication = receiptPublication(target, { ...files, unlink: async file => {
    if (file.endsWith('.pending') && fail) {
      fail = false;
      const visible = JSON.parse(await readFile(target));
      assert.equal(visible.checks.length, 7);
      assert.equal(visible.cleanup, 'confirmed');
      throw cause;
    }
    return files.unlink(file);
  } });
  await assert.rejects(completeProbe({ cleanup: [],
    commit: () => publication.publish({ checks: Array(7).fill('controlled'), cleanup: 'confirmed' }),
    rollback: () => publication.rollback(), dispose: async () => {},
    recordFailure: async error => {
      await assert.rejects(stat(target), { code: 'ENOENT' });
      await writeFile(path.join(root, 'failure.json'), JSON.stringify(errorDetails(error)));
    },
  }), error => error.errors[0].cause === cause);
  assert.deepEqual(await readdir(root), ['failure.json']);
  assert.equal(JSON.parse(await readFile(path.join(root, 'failure.json'))).errors[0].cause.code, 'EIO');
});

test('Exclusive publication preserves an existing unrelated receipt', async t => {
  const root = await folder(t), target = path.join(root, 'receipt.json');
  await writeFile(target, 'unrelated evidence');
  const publication = receiptPublication(target);
  await assert.rejects(completeProbe({ cleanup: [],
    commit: () => publication.publish({ passed: true }), rollback: () => publication.rollback(),
    dispose: async () => {}, recordFailure: async () => {},
  }), error => error.errors[0].cause.code === 'EEXIST');
  assert.equal(await readFile(target, 'utf8'), 'unrelated evidence');
  assert.deepEqual(await readdir(root), ['receipt.json']);
});

test('Rollback refuses a replaced file and retains both commit and rollback evidence', async t => {
  const root = await folder(t), target = path.join(root, 'receipt.json');
  const publication = receiptPublication(target), cause = new Error('Invented commit rejection');
  await assert.rejects(completeProbe({ cleanup: [],
    commit: async () => {
      await publication.publish({ passed: true });
      await rename(target, path.join(root, 'retained-original'));
      await writeFile(target, 'unrelated replacement');
      throw cause;
    },
    rollback: () => publication.rollback(), dispose: async () => {},
    recordFailure: error => writeFile(path.join(root, 'failure.json'), JSON.stringify(errorDetails(error))),
  }), error => error.errors[0].cause === cause && error.errors[1].message === 'Probe receipt rollback failed');
  assert.equal(await readFile(target, 'utf8'), 'unrelated replacement');
  assert.match(await readFile(path.join(root, 'failure.json'), 'utf8'), /refusing to remove another file/);
});

test('Filesystem rollback denial stays failed and keeps the original commit cause', async t => {
  const root = await folder(t), target = path.join(root, 'receipt.json');
  const cause = Object.assign(new Error('Invented commit EIO'), { code: 'EIO' });
  const denied = Object.assign(new Error('Invented rollback denial'), { code: 'EACCES' });
  const publication = receiptPublication(target, { ...files, unlink: file => {
    if (file === target) return Promise.reject(denied);
    return files.unlink(file);
  } });
  await assert.rejects(completeProbe({ cleanup: [],
    commit: async () => { await publication.publish({ passed: true }); throw cause; },
    rollback: () => publication.rollback(), dispose: async () => {},
    recordFailure: error => writeFile(path.join(root, 'failure.json'), JSON.stringify(errorDetails(error))),
  }), error => error.errors[0].cause === cause && error.errors[1].cause.errors[0] === denied);
  const failure = JSON.parse(await readFile(path.join(root, 'failure.json')));
  assert.equal(failure.errors[0].cause.code, 'EIO');
  assert.equal(failure.errors[1].cause.errors[0].code, 'EACCES');
});

for (const failing of ['authenticated shutdown', 'native exits', 'trace', 'browser']) {
  test(`Rejected ${failing} retains evidence and cannot leave a PASS receipt`, async t => {
    const root = await folder(t), attempted = [], cause = new Error(`Invented ${failing} failure`);
    await assert.rejects(completeProbe({
      cleanup: ['authenticated shutdown', 'native exits', 'trace', 'browser'].map(name =>
        [name, async () => { attempted.push(name); if (name === failing) throw cause; }]),
      commit: () => writeFile(path.join(root, 'receipt.json'), '{"passed":true}\n'),
      dispose: async () => { attempted.push('observer disposal'); },
      recordFailure: error => writeFile(path.join(root, 'failure.json'), JSON.stringify(errorDetails(error))),
    }), error => error instanceof AggregateError && error.errors[0].cause === cause);
    await assert.rejects(stat(path.join(root, 'receipt.json')), { code: 'ENOENT' });
    assert.deepEqual(attempted, ['authenticated shutdown', 'native exits', 'trace', 'browser', 'observer disposal']);
    assert.equal(JSON.parse(await readFile(path.join(root, 'failure.json'))).errors[0].cause.message, cause.message);
  });
}

test('An earlier flow error stays the first cause alongside shutdown failure', async t => {
  await folder(t);
  const primary = new Error('Original UI assertion'), shutdown = new Error('Shutdown denied');
  let saved;
  await assert.rejects(completeProbe({
    primaryError: primary,
    cleanup: [['authenticated shutdown', async () => { throw shutdown; }]],
    commit: async () => { assert.fail('A failed flow cannot commit'); },
    dispose: async () => {},
    recordFailure: async error => { saved = error; },
  }), error => error.cause === primary && error.errors[1].cause === shutdown);
  assert.equal(saved.errors[0], primary);
});

test('A stalled cleanup is bounded, attempts later cleanup and cannot commit PASS', async t => {
  const root = await folder(t);
  let browserAttempted = false;
  await assert.rejects(completeProbe({
    cleanupTimeoutMs: 10,
    cleanup: [
      ['stalled trace', () => new Promise(() => {})],
      ['browser', async () => { browserAttempted = true; }],
    ],
    commit: () => writeFile(path.join(root, 'receipt.json'), '{"passed":true}\n'),
    dispose: async () => {},
    recordFailure: async () => {},
  }), error => error.errors[0].cause.message === 'Cleanup deadline exceeded: stalled trace');
  assert.equal(browserAttempted, true);
  await assert.rejects(stat(path.join(root, 'receipt.json')), { code: 'ENOENT' });
});

test('Each new-instance observer waits independently; a secondary exit is insufficient', async t => {
  const root = await folder(t), children = [], calls = [];
  const create = (...args) => { calls.push(args); const child = new OpenFixture(); children.push(child); return child; };
  const first = observeApplication('/owned/OpenT1D.app', ['--no-browser'], path.join(root, 'first.log'), create);
  const second = observeApplication('/owned/OpenT1D.app', ['--no-browser'], path.join(root, 'second.log'), create);
  assert.deepEqual(calls[0][1], ['-W', '-n', '/owned/OpenT1D.app', '--args', '--no-browser']);
  children[1].emit('close', 0, null);
  await assert.rejects(waitForApplications([first, second], 10), /unconfirmed/);
  assert.deepEqual(children.map(child => child.signals), [[], []]);
  children[0].emit('close', 0, null);
  const observations = await waitForApplications([first, second], 10);
  assert.equal(observations.length, 2);
  assert.deepEqual(observations[0], { application: '/owned/OpenT1D.app',
    launch_services_exit_observed: true, observer_exit_code: 0, observer_signal: null });
});

test('Cancelling only the retained open helper never confirms native app exit', async t => {
  const root = await folder(t), child = new OpenFixture(), unrelated = new OpenFixture();
  const observer = observeApplication('/owned/removed/OpenT1D.app', [], path.join(root, 'open.log'), () => child);
  await disposeObservers([observer]);
  assert.deepEqual(child.signals, ['SIGTERM']);
  assert.deepEqual(unrelated.signals, []);
  await assert.rejects(observer.wait(10), /did not confirm native exit/);
});

test('An unconfirmed native exit prevents PASS even after server shutdown succeeded', async t => {
  const root = await folder(t), child = new OpenFixture();
  const observer = observeApplication('/owned/deleted/OpenT1D.app', [], path.join(root, 'open.log'), () => child);
  let shutdownAccepted = false;
  await assert.rejects(completeProbe({
    cleanup: [
      ['authenticated shutdown', async () => { shutdownAccepted = true; }],
      ['native exits', () => waitForApplications([observer], 10)],
    ],
    commit: () => writeFile(path.join(root, 'receipt.json'), '{"passed":true}\n'),
    dispose: () => disposeObservers([observer]),
    recordFailure: error => writeFile(path.join(root, 'failure.json'), JSON.stringify(errorDetails(error))),
  }), /Mac application probe failed/);
  assert.equal(shutdownAccepted, true);
  await assert.rejects(stat(path.join(root, 'receipt.json')), { code: 'ENOENT' });
  assert.deepEqual(child.signals, ['SIGTERM']); // The open helper only.
  await assert.rejects(observer.wait(10), /did not confirm native exit/);
  assert.match(await readFile(path.join(root, 'failure.json'), 'utf8'), /unconfirmed/);
});

test('Nonzero observer completion remains a failure and is never signalled again', async t => {
  const root = await folder(t), child = new OpenFixture();
  const observer = observeApplication('/owned/OpenT1D.app', [], path.join(root, 'open.log'), () => child);
  child.emit('close', 1, null);
  await assert.rejects(observer.wait(10), /did not confirm native exit/);
  await observer.dispose();
  assert.deepEqual(child.signals, []);
});
