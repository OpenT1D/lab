/** Native worker successor. No installer, launcher, sandbox or project-store route. */
import {readFileSync, lstatSync} from 'node:fs';
import {join, resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {register} from 'node:module';
import {hostname} from 'node:os';
import {digest, inventory, verifyGrant, executableWithin, loadConstructors, WORKER_FILES} from './native_loader.mjs';
import {assembleDirect} from './direct.mjs';
import {assembleWrapped} from './wrapped.mjs';

function read(path, limit = 16 * 1024 * 1024) {
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > limit) throw Error('LT1 bounded regular intake');
  return readFileSync(path);
}

export async function main(args) {
  // Registry location is compiled into this worker; never a request/env argument.
  const registry = JSON.parse(read(new URL('./native-admissions.json', import.meta.url)));
  if (!registry.execution.length) throw Error('LT1 admission refused: no reviewed execution grant');
  if (args.length !== 2) throw Error('Expected staging root and private packet directory');
  const [root, packet] = args.map(value => resolve(value));
  const raw = read(join(packet, 'grant.json'));
  if (!registry.execution.includes(digest(raw))) throw Error('LT1 admission refused: no reviewed execution grant');
  // Detect a misconfigured launch. The future supervisor must prevent preloads
  // before process startup; code here cannot undo an already executed preload.
  if (process.execArgv.length || Object.keys(process.env).some(key =>
    /^(NODE_|TS_NODE|TS_CONFIG)/.test(key))) throw Error('LT1 ambient loader configuration');
  const context = {node: process.version, platform: process.platform, arch: process.arch,
    host: hostname(), staging_root: root,
    executable_sha256: executableWithin(root, process.execPath), files: inventory(root),
    worker_files: Object.fromEntries(WORKER_FILES.map(path =>
      [path, digest(read(new URL(path, import.meta.url)))]))};
  for (const name of ['plan', 'setup_receipt', 'host_receipt', 'rights_receipt', 'security_receipt']) {
    context[name] = read(join(packet, name + '.json'));
  }
  const admitted = verifyGrant(raw, registry, context);
  // Host review must establish immutable staging and external filesystem/network
  // confinement. A child process, receipt hash or loader is not that confinement.
  process.env.TS_NODE_PROJECT = join(root, 'toolchain/tsconfig.json');
  process.env.TS_NODE_CWD = join(root, 'toolchain');
  register(pathToFileURL(join(root, 'toolchain/node_modules/ts-node/esm.mjs')),
    pathToFileURL(join(root, 'toolchain/')));
  const modules = await loadConstructors(root);
  const built = (admitted.mode === 'direct' ? assembleDirect : assembleWrapped)(modules, admitted.plan);
  const session = built.run();
  // Single-attempt data only: never manufacture a reader identity or store seal.
  process.stdout.write(JSON.stringify({schema: 'opent1d.lt1-native-worker-result/1',
    grant_sha256: admitted.grant_sha256, mode: admitted.mode, session}) + '\n');
  if (session.status !== 'completed') process.exitCode = 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(String(error) + '\n'); process.exitCode = 1; }
}
