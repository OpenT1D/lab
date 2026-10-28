/** Fetch source only: the Cambridge import graph uses no external runtime packages. */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export const HERE = dirname(fileURLToPath(import.meta.url));
export const ROOT = resolve(HERE, '../../..');
export const SOURCE = resolve(ROOT, 'results/m0/lt1-upstream');
export const REVISION = '9a6092065bd821f88691cd8d03b0550acd665573';
export function git(...args) {
  return execFileSync('git', args, { encoding: 'utf8' }).trim();
}
export function verifySource() {
  if (git('-C', SOURCE, 'rev-parse', 'HEAD') !== REVISION) throw Error('Unexpected LT1 revision');
  if (git('-C', SOURCE, 'status', '--porcelain', '--untracked-files=all', '--ignored=matching')) {
    throw Error('LT1 source modifications or extra files are not allowed');
  }
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (!existsSync(SOURCE)) {
    mkdirSync(SOURCE, { recursive: true });
    git('-C', SOURCE, 'init', '--quiet');
    git('-C', SOURCE, 'remote', 'add', 'origin', 'https://github.com/hpeuscher/loopinsight1');
    git('-C', SOURCE, 'fetch', '--depth', '1', 'origin', REVISION);
    git('-C', SOURCE, 'checkout', '--detach', 'FETCH_HEAD');
  }
  verifySource();
  console.log(`Verified LT1 ${REVISION}`);
}
