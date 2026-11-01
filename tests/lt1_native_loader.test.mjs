/** All positive paths use invented trust roots and scripted constructors. */
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, symlinkSync, rmSync, readFileSync, realpathSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
import {digest, verifyGrant, inventory, loadConstructors, ENTRIES, REVISION, WORKER_FILES}
  from '../experiments/lt1_diagnostic/native_loader.mjs';
import {fixtureModules} from './lt1_diagnostic_fixture.mjs';
import {assembleDirect} from '../experiments/lt1_diagnostic/direct.mjs';
import {assembleWrapped} from '../experiments/lt1_diagnostic/wrapped.mjs';

const plan = readFileSync(new URL('../experiments/lt1_diagnostic/plan.json', import.meta.url));
function fixture(mode = 'wrapped') {
  const context = {node:'v22.23.4', platform:'darwin', arch:'arm64', host:'invented-host', staging_root:'/invented', plan,
    setup_receipt:Buffer.from('invented setup'), host_receipt:Buffer.from('invented host'),
    rights_receipt:Buffer.from('invented rights'), security_receipt:Buffer.from('invented security')};
  const required = [...Object.values(ENTRIES), 'source/LICENSE.md', 'runtime/bin/node', 'runtime/LICENSE',
    'toolchain/node_modules/ts-node/esm.mjs', 'toolchain/tsconfig.json', 'toolchain/package.json', 'toolchain/package-lock.json'];
  context.files = Object.fromEntries(required.map(path => [path, digest(Buffer.from(path))]));
  context.worker_files = Object.fromEntries(WORKER_FILES.map(path => [path, digest(Buffer.from(path))]));
  context.executable_sha256 = context.files['runtime/bin/node'];
  const grant = {schema:'opent1d.lt1-native-grant/1', source_revision:REVISION,
    node:context.node, platform:context.platform, arch:context.arch, host:context.host, staging_root:context.staging_root, mode,
    files:context.files, worker_files:context.worker_files};
  for (const name of ['plan','setup_receipt','host_receipt','rights_receipt','security_receipt']) {
    grant[name+'_sha256'] = digest(context[name]);
  }
  const raw = Buffer.from(JSON.stringify(grant));
  const registry = {schema:'opent1d.lt1-native-admissions/1', setup:[grant.setup_receipt_sha256], execution:[digest(raw)]};
  return {grant, raw, registry, context};
}

test('positive verifier and fixed constructor loading preserve direct/wrapped scripted sessions', async () => {
  for (const mode of ['direct','wrapped']) {
    const {raw, registry, context} = fixture(mode);
    const selected = verifyGrant(raw, registry, context), modules = fixtureModules(selected.plan), calls = [];
    const loaded = await loadConstructors('/invented', async url => {
      calls.push(url); const name = Object.keys(ENTRIES).find(name => url.endsWith(ENTRIES[name]));
      return {default: modules[name]};
    });
    assert.equal(calls.length,4);
    const built = (mode === 'direct' ? assembleDirect : assembleWrapped)(loaded, selected.plan);
    const first = built.run();
    assert.equal(first.status,'completed'); assert.equal(first.rows.length,32);
    assert.deepEqual(built.run(), first);
  }
});

test('untrusted bytes cannot authorize themselves and refuse before context access', () => {
  const {raw, registry} = fixture(); registry.execution = [];
  assert.throws(() => verifyGrant(raw, registry, new Proxy({}, {get(){throw Error('context read');}})), /no reviewed execution/);
  registry.execution = [digest(raw)]; registry.setup = [];
  assert.throws(() => verifyGrant(raw, registry, fixture().context), /no reviewed setup/);
});

test('each receipt, plan, runtime, worker and complete staging identity is mandatory', () => {
  const changes = [c=>c.node='v22.22.2', c=>c.platform='linux', c=>c.arch='x64',
    c=>c.host='another-host', c=>c.staging_root='/relocated',
    c=>c.executable_sha256=digest('different'), c=>c.files.extra=digest('ambient import'),
    c=>delete c.files['source/LICENSE.md'], c=>c.files['source/src/core/Simulator.ts']=digest('modified'),
    c=>c.worker_files['native_worker.mjs']=digest('changed worker'),
    c=>c.worker_files['../m0/lt1/record.mjs']=digest('changed transitive recorder'),
    ...['plan','setup_receipt','host_receipt','rights_receipt','security_receipt'].map(name=>c=>c[name]=Buffer.from('changed'))];
  for (const change of changes) {
    const {raw, registry, context} = fixture();
    // Separate actual inventories from the grant's original in-memory objects.
    context.files = {...context.files}; context.worker_files = {...context.worker_files};
    change(context); assert.throws(()=>verifyGrant(raw,registry,context), /refused/);
  }
});

test('even trusted malformed/unsupported grant cannot widen paths, fields or mode', () => {
  for (const change of [g=>g.mode='mpc',g=>g.source_revision='other',g=>g.execution_authorized=true,
    g=>g.files['../escape']=digest('x'),g=>delete g.files['toolchain/tsconfig.json']]) {
    const {grant,registry,context} = fixture(); change(grant);
    const raw = Buffer.from(JSON.stringify(grant)); registry.execution=[digest(raw)];
    assert.throws(()=>verifyGrant(raw,registry,context), /refused/);
  }
});

test('inventory consumes exact bytes including hidden files and refuses symlinks', () => {
  const root = realpathSync(mkdtempSync(join(tmpdir(),'lt1-invented-staging-')));
  try {
    mkdirSync(join(root,'child')); writeFileSync(join(root,'child','.config'),'one');
    assert.deepEqual({...inventory(root)}, {'child/.config':digest('one')});
    writeFileSync(join(root,'child','.config'),'two');
    assert.deepEqual({...inventory(root)}, {'child/.config':digest('two')});
    writeFileSync(join(root,'__proto__'),'hidden');
    assert.equal(inventory(root).__proto__,digest('hidden'));
    assert.ok(Object.hasOwn(inventory(root),'__proto__'));
    symlinkSync(join(root,'child','.config'),join(root,'link'));
    assert.throws(()=>inventory(root),/symlink/);
  } finally { rmSync(root,{recursive:true,force:true}); }
});

test('production worker refuses before inspecting supplied paths or loading a native module', () => {
  const worker = new URL('../experiments/lt1_diagnostic/native_worker.mjs',import.meta.url);
  const result = spawnSync(process.execPath,[worker.pathname,'/nonexistent/staging','/nonexistent/private'],
    {encoding:'utf8',timeout:5000});
  assert.equal(result.status,1); assert.equal(result.stdout,'');
  assert.match(result.stderr,/no reviewed execution grant/); assert.doesNotMatch(result.stderr,/ENOENT/);
});

test('a missing default export cannot be substituted by a namespace or partial load', async () => {
  await assert.rejects(loadConstructors('/invented', async()=>({default:{}})), /constructor Simulator/);
});

test('reviewed worker roster includes its current relative static import closure', () => {
  const base = new URL('../experiments/lt1_diagnostic/',import.meta.url), found = new Set();
  function visit(url) {
    if (found.has(url.href)) return;
    found.add(url.href);
    const source = readFileSync(url,'utf8');
    for (const match of source.matchAll(/import\s+[\s\S]*?\sfrom\s+['"]([^'"]+)['"]/g)) {
      if (match[1].startsWith('.')) visit(new URL(match[1],url));
    }
  }
  visit(new URL('native_worker.mjs',base));
  assert.deepEqual([...found].sort(), WORKER_FILES.map(path=>new URL(path,base).href).sort());
});
