/** Fixed ordinary-tooling loader. No compiler, native packet or LT1 import. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const need = (ok, why) => { if (!ok) throw Error('C20 tooling refused: ' + why); };
const digest = raw => createHash('sha256').update(raw).digest('hex');
const key = 'OPENT1D_C20_TOOLING';
need(process.argv.length === 2 && process.argv[1] === fileURLToPath(import.meta.url), 'fixed ABI');
const entry = JSON.parse(process.env[key] ?? 'null');
delete process.env[key];
need(entry && Object.keys(entry).sort().join(',') === 'kind,nonce_sha256,owner_pid,slot,targets', 'closed context');
need(entry.kind === 'invented' && ['validity-control', 'base', 'allow-twin'].includes(entry.slot)
  && /^[a-f0-9]{64}$/.test(entry.nonce_sha256)
  && Number.isSafeInteger(entry.owner_pid) && entry.owner_pid > 1, 'fixed slot');
need(typeof entry.targets === 'string' && entry.targets.startsWith('/')
  && !entry.targets.includes('/../') && fs.realpathSync(entry.targets) === entry.targets, 'fixed root');

const failed = error => ({status: 'error', sha256: null, value: null,
  error_code: typeof error?.code === 'string' ? error.code.slice(0, 64) : 'UNKNOWN',
  error_message: String(error?.message ?? error).slice(0, 1024)});
const succeeded = (sha256, value) => ({status: 'ok', sha256, value, error_code: null, error_message: null});
function read(name) {
  let fd;
  try {
    const path = join(entry.targets, name);
    fd = fs.openSync(path, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    const before = fs.fstatSync(fd, {bigint: true});
    need(before.isFile() && before.nlink === 1n && before.uid === BigInt(process.getuid())
      && (before.mode & 0o777n) === 0o400n && before.size <= 16777216n, 'immutable bounded target');
    const raw = fs.readFileSync(fd);
    const after = fs.fstatSync(fd, {bigint: true}), named = fs.lstatSync(path, {bigint: true});
    need(raw.length === Number(before.size) && before.dev === after.dev && before.ino === after.ino
      && before.size === after.size && before.mtimeNs === after.mtimeNs && before.ctimeNs === after.ctimeNs
      && named.dev === after.dev && named.ino === after.ino && !named.isSymbolicLink()
      && named.nlink === 1n, 'stable target');
    return succeeded(digest(raw), null);
  } catch (error) { return failed(error); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
const operations = {module_read: read('module.mjs'), addon_read: read('addon.node')};
try {
  const value = await import(pathToFileURL(join(entry.targets, 'module.mjs')).href);
  operations.module_import = succeeded(null, value.marker);
} catch (error) { operations.module_import = failed(error); }
try {
  const value = createRequire(import.meta.url)(join(entry.targets, 'addon.node'));
  operations.addon_load = succeeded(null, value.marker);
} catch (error) { operations.addon_load = failed(error); }
const report = {schema: 'opent1d.lt1-c20-loader-operations/1', kind: 'invented',
  slot: entry.slot, nonce_sha256: entry.nonce_sha256, completed: true,
  runtime: {pid: process.pid, ppid: process.ppid, exec_path: process.execPath,
    node: process.version, platform: process.platform, arch: process.arch, napi: process.versions.napi},
  operations, native_host_qualified: false, native_execution_authorized: false};
process.stdout.write(JSON.stringify(report) + '\n');
