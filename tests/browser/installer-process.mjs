import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';

export async function runPhase(label, executable, args, { timeout, grace = 5000 } = {}) {
  if (!(timeout > 0) || !(grace > 0)) throw new Error('Installer deadlines must be positive');
  const started = performance.now();
  console.log(`Browser installation phase: ${label}; budget ${Math.ceil(timeout / 1000)}s`);
  const grouped = process.platform !== 'win32';
  const child = spawn(executable, args, { stdio: 'inherit', detached: grouped });
  let failure, escalation;
  function signal(kind) {
    try {
      if (grouped && child.pid) process.kill(-child.pid, kind);
      else child.kill(kind);
    } catch (error) { if (error.code !== 'ESRCH') throw error; }
  }
  function groupExists() {
    if (!grouped || !child.pid) return false;
    try { process.kill(-child.pid, 0); return true; }
    catch (error) { if (error.code === 'ESRCH') return false; throw error; }
  }
  function stop(message, code) {
    failure ||= Object.assign(new Error(`${label}: ${message}`), { exitCode: code });
    signal('SIGTERM');
    escalation ||= setTimeout(() => signal('SIGKILL'), grace);
  }
  const interrupt = () => stop('interrupted', 130);
  const terminate = () => stop('terminated', 143);
  process.once('SIGINT', interrupt);
  process.once('SIGTERM', terminate);
  const deadline = setTimeout(() => stop('deadline exceeded', 124), timeout);
  try {
    const result = await new Promise(resolve => {
      child.once('error', error => resolve({ error }));
      child.once('exit', (code, signal) => resolve({ code, signal }));
    });
    clearTimeout(deadline);
    if (groupExists()) {
      stop('left running descendants', 1);
      const until = performance.now() + grace;
      while (groupExists() && performance.now() < until) await delay(20);
      if (groupExists()) signal('SIGKILL');
    }
    if (failure) throw failure;
    if (result.error) throw new Error(`${label}: ${result.error.message}`);
    if (result.code !== 0) throw Object.assign(new Error(`${label}: exit ${result.code}, signal ${result.signal}`), { exitCode: result.code || 1 });
    return { phase: label, elapsedSeconds: (performance.now() - started) / 1000 };
  } finally {
    clearTimeout(deadline);
    clearTimeout(escalation);
    process.removeListener('SIGINT', interrupt);
    process.removeListener('SIGTERM', terminate);
    console.log(`Browser installation phase finished: ${label}; elapsed ${((performance.now() - started) / 1000).toFixed(3)}s`);
  }
}
