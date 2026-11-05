/** Versioned staging verifier. A supplied manifest is evidence, never authority. */
import {createHash} from 'node:crypto';
import {lstatSync, readFileSync, readdirSync, realpathSync} from 'node:fs';
import {isAbsolute, join, relative, sep} from 'node:path';
import {pathToFileURL} from 'node:url';
import {validatePlan} from './protocol.mjs';

export const REVISION = '9a6092065bd821f88691cd8d03b0550acd665573';
export const WORKER_FILES = Object.freeze(['native_worker.mjs', 'native_loader.mjs',
  'direct.mjs', 'wrapped.mjs', 'protocol.mjs', '../adapter_audit/lt1_sampled.mjs', '../m0/lt1/record.mjs']);
export const ENTRIES = Object.freeze({
  Simulator: 'source/src/core/Simulator.ts',
  Cambridge: 'source/src/core/models/Cambridge.ts',
  IdealCGM: 'source/src/core/sensors/IdealCGM.ts',
  Pump: 'source/src/core/actuators/StaticInsulinPump.ts',
});
export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
function requireThat(ok, reason) { if (!ok) throw Error(`LT1 admission refused: ${reason}`); }
function keys(value, expected) {
  requireThat(value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).sort().join(',') === expected.slice().sort().join(','), 'fields');
}
function safePath(value) {
  return typeof value === 'string' && value.length > 0 && !value.includes('\\') &&
    !isAbsolute(value) && value.split('/').every(part => part && part !== '.' && part !== '..');
}

/** Closed inventory: all staging bytes, including resolver/config/loader inputs. */
export function inventory(root) {
  requireThat(isAbsolute(root) && realpathSync(root) === root, 'canonical staging root');
  const found = Object.create(null);
  function visit(folder, prefix = '') {
    requireThat(lstatSync(folder).isDirectory() && !lstatSync(folder).isSymbolicLink(), 'directory');
    for (const name of readdirSync(folder).sort()) {
      const path = join(folder, name), label = prefix + name, stat = lstatSync(path);
      requireThat(safePath(label) && !stat.isSymbolicLink(), 'symlink or path');
      if (stat.isDirectory()) visit(path, label + '/');
      else {
        requireThat(stat.isFile() && stat.size <= 128 * 1024 * 1024, 'regular bounded file');
        found[label] = digest(readFileSync(path));
      }
    }
  }
  visit(root); return found;
}

/** Pure policy validation; registry is trusted by the caller, not taken from a request. */
export function verifyGrant(raw, registry, context) {
  keys(registry, ['schema', 'setup', 'execution']);
  requireThat(registry.schema === 'opent1d.lt1-native-admissions/1' &&
    Array.isArray(registry.setup) && Array.isArray(registry.execution) &&
    registry.setup.every(hash) && registry.execution.every(hash), 'registry');
  // Refuse an unknown grant before parsing it or reading its staging/plan paths.
  requireThat(registry.execution.includes(digest(raw)), 'no reviewed execution grant');
  const grant = JSON.parse(raw);
  keys(grant, ['schema', 'source_revision', 'node', 'platform', 'arch', 'host', 'staging_root', 'mode',
    'plan_sha256', 'setup_receipt_sha256', 'host_receipt_sha256', 'rights_receipt_sha256',
    'security_receipt_sha256', 'files', 'worker_files']);
  requireThat(grant.schema === 'opent1d.lt1-native-grant/1' && grant.source_revision === REVISION,
    'source identity');
  requireThat(grant.node === 'v22.23.4' && grant.platform === 'darwin' && grant.arch === 'arm64', 'runtime candidate');
  requireThat(['direct', 'wrapped'].includes(grant.mode), 'mode');
  for (const name of ['plan', 'setup_receipt', 'host_receipt', 'rights_receipt', 'security_receipt']) {
    requireThat(hash(grant[`${name}_sha256`]) && digest(context[name]) === grant[`${name}_sha256`], `${name} bytes`);
  }
  requireThat(registry.setup.includes(grant.setup_receipt_sha256), 'no reviewed setup receipt');
  requireThat(context.node === grant.node && context.platform === grant.platform && context.arch === grant.arch,
    'running host/runtime');
  requireThat(typeof grant.host === 'string' && grant.host.length > 0 && context.host === grant.host &&
    typeof grant.staging_root === 'string' && isAbsolute(grant.staging_root) &&
    context.staging_root === grant.staging_root, 'named host/staging root');
  keys(grant.files, Object.keys(context.files));
  requireThat(Object.keys(grant.files).length > 0 && Object.entries(grant.files).every(([path, sha]) =>
    safePath(path) && hash(sha) && context.files[path] === sha), 'staging inventory');
  for (const path of [...Object.values(ENTRIES), 'source/LICENSE.md', 'runtime/bin/node',
    'runtime/LICENSE', 'toolchain/node_modules/ts-node/esm.mjs', 'toolchain/tsconfig.json',
    'toolchain/package.json', 'toolchain/package-lock.json']) {
    requireThat(Object.hasOwn(grant.files, path), 'required staging input');
  }
  requireThat(context.executable_sha256 === grant.files['runtime/bin/node'], 'running executable');
  keys(grant.worker_files, WORKER_FILES);
  requireThat(WORKER_FILES.every(path => hash(grant.worker_files[path]) &&
    context.worker_files[path] === grant.worker_files[path]), 'worker source');
  validatePlan(JSON.parse(context.plan));
  return Object.freeze({mode: grant.mode, grant_sha256: digest(raw), plan: JSON.parse(context.plan)});
}

/** Called only after admission in the worker. Importer injection is for controlled tests. */
export async function loadConstructors(root, importer = specifier => import(specifier)) {
  const loaded = {};
  for (const [name, path] of Object.entries(ENTRIES)) {
    const module = await importer(pathToFileURL(join(root, path)).href);
    requireThat(typeof module.default === 'function', `constructor ${name}`);
    loaded[name] = module.default;
  }
  return loaded;
}

export function executableWithin(root, executable) {
  const path = realpathSync(executable), location = relative(root, path);
  requireThat(location === ['runtime', 'bin', 'node'].join(sep), 'executable location');
  return digest(readFileSync(path));
}
