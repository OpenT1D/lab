/** Execute one frozen LIT-002 case in the existing locked native LT1 runtime. */
import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { SOURCE, REVISION, git, verifySource } from '../../../m0/lt1/setup.mjs';
import { encode, hash } from '../../../m0/lt1/record.mjs';
import { prepare, runPrepared } from './coupling.mjs';

if (process.argv.length !== 3) throw Error('Usage: worker.mjs OUTPUT_DIRECTORY_WITH_CONFIG_JSON');
const output = resolve(process.argv[2]);
for (const name of ['runtime.json', 'trace.jsonl', 'result.json', 'failure.log']) {
  if (existsSync(resolve(output, name))) throw Error(`Refusing to overwrite prior case artifact: ${name}`);
}
const save = (name, value) => writeFileSync(resolve(output, name), encode(value) + '\n');
try {
  if (process.version !== 'v22.22.2') throw Error('Use the locked Node 22.22.2 runtime');
  verifySource();
  const config = JSON.parse(readFileSync(resolve(output, 'config.json'), 'utf8'));
  const files = git('-C', SOURCE, 'ls-files', 'src', 'LICENSE.md').split('\n');
  const runtime = { upstream_revision: REVISION, node: process.version,
    platform: `${process.platform}/${process.arch}`,
    source_sha256: Object.fromEntries(files.map(path => [path, hash(resolve(SOURCE, path))])),
    packages: JSON.parse(readFileSync(new URL('../../../m0/lt1/package-lock.json', import.meta.url), 'utf8')).packages,
  };
  save('runtime.json', runtime);
  const engine = await prepare(config);
  runtime.settings = engine.metadata;
  save('runtime.json', runtime);
  const result = runPrepared(engine, row => {
    if (process.env.OPENT1D_PARENT_PID && process.ppid !== Number(process.env.OPENT1D_PARENT_PID)) {
      throw Error('Supervisor disappeared; stopping at native output boundary');
    }
    // Keep the diagnostic row before validation so a failed native state is auditable.
    appendFileSync(resolve(output, 'trace.jsonl'), encode(row) + '\n');
  });
  save('result.json', result);
} catch (error) {
  save('result.json', { status: 'failed', error: String(error) });
  writeFileSync(resolve(output, 'failure.log'), error.stack ?? String(error));
  process.exitCode = 1;
}
