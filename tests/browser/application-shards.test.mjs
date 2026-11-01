import assert from 'node:assert/strict';
import { test } from 'node:test';
import { applicationFiles, presentApplicationFiles } from './application-shards.mjs';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

const files = ['mmtt.spec.mjs', 'installed-sampling.spec.mjs', 'workbench.spec.mjs', 'comparisons.spec.mjs', 'connected.spec.mjs', 'internal-candidate.spec.mjs', 'integrated-candidate.spec.mjs', 'm3-workbench.spec.mjs'];
test('complete canonical file multiset, including M3, is selected exactly once', () => {
  const all = [1, 2, 3].flatMap(i => applicationFiles(files, `${i}/3`));
  assert.deepEqual(all.sort(), [...files].sort());
  assert.deepEqual(applicationFiles(files), files);
  assert.ok(applicationFiles(files, '3/3').includes('m3-workbench.spec.mjs'));
});
test('new, missing, duplicate files and invalid groups fail closed', () => {
  for (const changed of [[...files, 'new-task.spec.mjs'], files.slice(1), [...files, files[0]]]) {
    assert.throws(() => applicationFiles(changed, '1/3'), /exactly one/);
  }
  for (const shard of ['0/3', '4/3', '1/4', '', '1']) assert.throws(() => applicationFiles(files, shard));
  assert.throws(() => applicationFiles(files, '1/3', [...files, 'unlisted.spec.mjs']), /exactly one/);
});
test('caller mutation does not contaminate later file selections', () => {
  applicationFiles(files, '1/3').pop();
  assert.equal(applicationFiles(files, '1/3').length, 2);
});

test('recursive inventory detects an unlisted nested app spec and ignores dependency/docs specs', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'opent1d-browser-roster-'));
  try {
    mkdirSync(path.join(root, 'flows'));
    mkdirSync(path.join(root, 'node_modules'));
    for (const file of files) writeFileSync(path.join(root, file), '');
    writeFileSync(path.join(root, 'documentation-extra.spec.mjs'), '');
    writeFileSync(path.join(root, 'node_modules/ignored.spec.mjs'), '');
    assert.deepEqual(presentApplicationFiles(root).sort(), [...files].sort());
    writeFileSync(path.join(root, 'flows/unlisted.spec.mjs'), '');
    assert.throws(() => applicationFiles(files, '1/3', presentApplicationFiles(root)), /exactly one/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
