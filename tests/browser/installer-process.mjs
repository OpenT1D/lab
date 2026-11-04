import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';

export async function runPhase(label, executable, args, { timeout, grace = 5000 } = {}) {
  if (!(timeout > 0) || !(grace > 0)) throw new Error('Installer deadlines must be positive');
  const started = performance.now();
  console.log(`Browser installation phase: ${label}; budget ${Math.ceil(timeout / 1000)}s`);
  const grouped = process.platform !== 'win32';
  const child = spawn(executable, args, { stdio: 'inherit', detached: grouped });
  let failure, escalation, cleanupDeadline, cleanupError, abandonExit;
  let exitObserved = false;
  const exitUnconfirmed = new Promise(resolve => { abandonExit = resolve; });
  function signal(kind) {
    try {
      if (grouped && child.pid) process.kill(-child.pid, kind);
      else child.kill(kind);
    } catch (error) { if (error.code !== 'ESRCH') cleanupError ||= error; }
  }
  function groupExists() {
    if (!grouped || !child.pid) return false;
    try { process.kill(-child.pid, 0); return true; }
    catch (error) {
      if (error.code === 'ESRCH') return false;
      cleanupError ||= error;
      return true; // A failed probe does not establish disappearance.
    }
  }
  async function waitForGroup() {
    const until = performance.now() + grace;
    let remains = groupExists();
    while (remains && performance.now() < until) {
      await delay(Math.min(20, Math.max(1, until - performance.now())));
      remains = groupExists();
    }
    return !remains;
  }
  function stop(message, code) {
    failure ||= Object.assign(new Error(`${label}: ${message}`), { exitCode: code });
    signal('SIGTERM');
    escalation ||= setTimeout(() => {
      signal('SIGKILL');
      if (!exitObserved) cleanupDeadline ||= setTimeout(() => {
        cleanupError ||= new Error('direct child exit unconfirmed after SIGKILL deadline');
        abandonExit({ unconfirmed: true });
      }, grace);
    }, grace);
  }
  const interrupt = () => stop('interrupted', 130);
  const terminate = () => stop('terminated', 143);
  process.once('SIGINT', interrupt);
  process.once('SIGTERM', terminate);
  const deadline = setTimeout(() => stop('deadline exceeded', 124), timeout);
  try {
    const exited = new Promise(resolve => {
      child.once('error', error => { exitObserved = true; resolve({ error }); });
      child.once('exit', (code, signal) => { exitObserved = true; resolve({ code, signal }); });
    });
    const result = await Promise.race([exited, exitUnconfirmed]);
    clearTimeout(deadline);
    clearTimeout(cleanupDeadline);
    if (groupExists()) {
      stop('left running descendants', 1);
      if (!await waitForGroup()) {
        signal('SIGKILL');
        if (!await waitForGroup()) cleanupError ||= new Error('owned process group still observable after SIGKILL deadline');
      }
    }
    if (failure) {
      failure.cleanupConfirmed = !cleanupError;
      if (cleanupError) {
        failure.cleanupError = cleanupError;
        failure.message += `; owned process-group cleanup unconfirmed: ${cleanupError.message}`;
      }
      throw failure;
    }
    if (result.error) throw new Error(`${label}: ${result.error.message}`);
    if (result.code !== 0) throw Object.assign(new Error(`${label}: exit ${result.code}, signal ${result.signal}`), { exitCode: result.code || 1 });
    return { phase: label, elapsedSeconds: (performance.now() - started) / 1000 };
  } finally {
    clearTimeout(deadline);
    clearTimeout(escalation);
    clearTimeout(cleanupDeadline);
    process.removeListener('SIGINT', interrupt);
    process.removeListener('SIGTERM', terminate);
    console.log(`Browser installation phase finished: ${label}; elapsed ${((performance.now() - started) / 1000).toFixed(3)}s`);
  }
}
