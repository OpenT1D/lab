import { readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export function presentApplicationFiles(directory) {
  const root = directory instanceof URL ? fileURLToPath(directory) : directory;
  return readdirSync(root, { recursive: true, withFileTypes: true })
    .filter(entry => entry.isFile() && entry.name.endsWith('.spec.mjs') && !entry.name.startsWith('documentation'))
    .map(entry => path.relative(root, path.join(entry.parentPath, entry.name)).split(path.sep).join('/'))
    .filter(name => !name.split('/').includes('node_modules'));
}

// Whole-file groups balance the measured 37ee62a Linux flows (~200s/group).
// A new configured file must be assigned explicitly; it cannot disappear.
const groups = [
  ['connected.spec.mjs', 'internal-candidate.spec.mjs'],
  ['comparisons.spec.mjs', 'integrated-candidate.spec.mjs', 'mmtt.spec.mjs'],
  ['workbench.spec.mjs', 'installed-sampling.spec.mjs', 'm3-workbench.spec.mjs'],
];

export function applicationFiles(files, shard, present = files) {
  const assigned = groups.flat();
  if (!Array.isArray(files) || new Set(files).size !== files.length || new Set(assigned).size !== assigned.length || [...files].sort().join('\n') !== [...assigned].sort().join('\n') || [...present].sort().join('\n') !== [...files].sort().join('\n')) {
    throw new Error('Every configured application file must belong to exactly one CI group');
  }
  if (shard === undefined) return [...files];
  if (!/^[1-3]\/3$/.test(shard)) throw new Error('Application group must be 1/3, 2/3 or 3/3');
  return [...groups[Number(shard[0]) - 1]];
}
