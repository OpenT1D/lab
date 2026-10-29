// QA authority is an authenticated endpoint plus the retained `open -W -n`
// invocation. A process-list snapshot never grants authority over an app.
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { closeSync, openSync } from 'node:fs';
import * as files from 'node:fs/promises';

async function bounded(promise, milliseconds, message) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(message)), milliseconds);
    })]);
  } finally { clearTimeout(timer); }
}

export function observeApplication(application, args, logPath, spawnProcess = spawn) {
  const descriptor = openSync(logPath, 'wx', 0o600);
  let child;
  try {
    child = spawnProcess('/usr/bin/open', ['-W', '-n', application, '--args', ...args], {
      env: { ...process.env, PATH: '/nonexistent', PYTHONPATH: '/nonexistent', VIRTUAL_ENV: '/nonexistent' },
      stdio: ['ignore', descriptor, descriptor],
    });
  } finally { closeSync(descriptor); }
  let outcome, exitDeadline, cancelled = false;
  const ended = new Promise(resolve => {
    const finish = value => { if (!outcome) { outcome = value; resolve(value); } };
    child.once('error', error => finish({ error: error.message }));
    child.once('close', (code, signal) => finish({ code, signal }));
  });
  return {
    async wait(milliseconds = 45_000) {
      exitDeadline ??= Date.now() + milliseconds;
      const result = await bounded(ended, Math.max(0, exitDeadline - Date.now()),
        `Native application exit was not confirmed: ${application}; observer log: ${logPath}`);
      if (cancelled || result.error || result.code !== 0 || result.signal) {
        throw new Error(`LaunchServices observer did not confirm native exit: ${JSON.stringify({ application, cancelled, ...result })}`);
      }
      return { application, launch_services_exit_observed: true,
        observer_exit_code: result.code, observer_signal: result.signal };
    },
    async dispose() {
      if (outcome) return;
      // This is only our retained read-only `open` helper, never the application.
      // Cancelling it cannot establish that the application exited.
      cancelled = true;
      try {
        if (!child.kill('SIGTERM')) throw new Error(`Could not cancel open observer: ${logPath}`);
        await bounded(ended, 2_000, `Open observer did not finish: ${logPath}`);
      } finally { child.unref(); }
    },
  };
}

export async function waitForApplications(observers, milliseconds = 45_000) {
  const results = await Promise.allSettled(observers.map(observer => observer.wait(milliseconds)));
  const errors = results.filter(result => result.status === 'rejected').map(result => result.reason);
  if (errors.length) throw new AggregateError(errors, 'Native application exit is unconfirmed');
  return results.map(result => result.value);
}

export async function disposeObservers(observers) {
  const results = await Promise.allSettled(observers.map(observer => observer.dispose()));
  const errors = results.filter(result => result.status === 'rejected').map(result => result.reason);
  if (errors.length) throw new AggregateError(errors, 'Read-only observer disposal failed');
}

export function errorDetails(error) {
  return {
    name: error.name, message: error.message, stack: error.stack,
    ...(error.code ? { code: error.code } : {}),
    ...(error.cause ? { cause: errorDetails(error.cause) } : {}),
    ...(error.errors ? { errors: Array.from(error.errors, errorDetails) } : {}),
  };
}

export function receiptPublication(receiptPath, io = files) {
  // The caller exclusively owns a fresh evidence directory. Identity checks
  // detect replaced files; this is not a transaction over a hostile namespace.
  const pendingPath = `${receiptPath}.${randomUUID()}.pending`;
  let pendingIdentity, receiptIdentity, started = false;
  async function removeOwned(file, identity) {
    if (!identity) return;
    let actual;
    try { actual = await io.lstat(file, { bigint: true }); }
    catch (error) { if (error.code === 'ENOENT') return; throw error; }
    if (!actual.isFile() || actual.dev !== identity.dev || actual.ino !== identity.ino) {
      throw new Error(`Receipt path changed; refusing to remove another file: ${file}`);
    }
    await io.unlink(file);
  }
  return {
    async publish(value) {
      if (started) throw new Error('Receipt publication was already attempted');
      started = true;
      const handle = await io.open(pendingPath, 'wx', 0o600);
      let writeError;
      try {
        pendingIdentity = await handle.stat({ bigint: true });
        await handle.writeFile(JSON.stringify(value, null, 2) + '\n');
      }
      catch (error) { writeError = error; }
      try { await handle.close(); }
      catch (error) {
        if (writeError) throw new AggregateError([writeError, error], 'Receipt write and close failed', { cause: writeError });
        throw error;
      }
      if (writeError) throw writeError;
      // Atomic no-replace publication on this same-filesystem QA directory.
      // Keep ownership identity before the call so post-operation errors can
      // still roll back our inode. No directory-wide cleanup is permitted.
      receiptIdentity = pendingIdentity;
      try { await io.link(pendingPath, receiptPath); }
      catch (error) { if (error.code === 'EEXIST') receiptIdentity = undefined; throw error; }
      await removeOwned(pendingPath, pendingIdentity);
    },
    async rollback() {
      const errors = [];
      for (const [file, identity] of [[receiptPath, receiptIdentity], [pendingPath, pendingIdentity]]) {
        try { await removeOwned(file, identity); }
        catch (error) { errors.push(error); }
      }
      if (errors.length) throw new AggregateError(errors, 'Owned receipt rollback failed');
    },
  };
}

export async function completeProbe({ primaryError, cleanup, commit, rollback, dispose, recordFailure,
  cleanupTimeoutMs = 60_000 }) {
  const errors = primaryError ? [primaryError] : [];
  let commitAttempted = false;
  const deadline = Date.now() + cleanupTimeoutMs;
  for (const [name, action] of cleanup) {
    try {
      await bounded(Promise.resolve().then(action), Math.max(0, deadline - Date.now()),
        `Cleanup deadline exceeded: ${name}`);
    }
    catch (error) { errors.push(new Error(`Probe cleanup failed: ${name}`, { cause: error })); }
  }
  if (!errors.length) {
    // Never race a non-cancellable write against a timeout: a late write could
    // otherwise leave a PASS file after this function had reported failure.
    try {
      if (typeof rollback !== 'function') throw new Error('Owned receipt rollback is required');
      commitAttempted = true;
      await commit(); return;
    }
    catch (error) { errors.push(new Error('Probe receipt commit failed', { cause: error })); }
  }
  if (commitAttempted) {
    try { await rollback(); }
    catch (error) { errors.push(new Error('Probe receipt rollback failed', { cause: error })); }
  }
  try { await bounded(Promise.resolve().then(dispose), 5_000, 'Observer disposal timed out'); }
  catch (error) { errors.push(new Error('Probe observer disposal failed', { cause: error })); }
  const failure = new AggregateError(errors, 'Mac application probe failed', { cause: errors[0] });
  try { await bounded(Promise.resolve().then(() => recordFailure(failure)), 5_000,
    'Failure evidence write timed out'); }
  catch (error) {
    throw new AggregateError([failure, error], 'Mac probe failed; failure evidence could not be saved', { cause: failure });
  }
  throw failure;
}
