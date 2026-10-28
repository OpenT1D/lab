/** Execute the unmodified upstream Cambridge reference through its native API. */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { HERE, ROOT, SOURCE, REVISION, git, verifySource } from './setup.mjs';
import { checkBaseline, compare, encode, hash, record, textHash } from './record.mjs';

const args = process.argv.slice(2);
if (args[0] === '--compare' && args.length >= 3) {
  console.log(encode(compare(resolve(args[1]), resolve(args[2]), args.includes('--report-differences'))));
} else if (args[0] === '--output' && args.length === 2) {
  const output = resolve(args[1]);
  mkdirSync(output); // Never overwrite another attempt.
  const manifest = { status: 'started', node: process.version, platform: `${process.platform}/${process.arch}`,
    upstream_revision: REVISION, opent1d_revision: git('-C', ROOT, 'rev-parse', 'HEAD'),
    worktree_dirty: Boolean(git('-C', ROOT, 'status', '--porcelain')), command: process.argv,
    lock_sha256: hash(resolve(HERE, 'package-lock.json')),
    harness_sha256: hash(resolve(HERE, 'run.mjs')), recorder_sha256: hash(resolve(HERE, 'record.mjs')),
    baseline_sha256: hash(resolve(HERE, 'baseline.json')),
    toolchain: JSON.parse(readFileSync(resolve(HERE, 'package.json'), 'utf8')).devDependencies,
  };
  const save = () => writeFileSync(resolve(output, 'manifest.json'), encode(manifest) + '\n');
  save();
  try {
    verifySource();
    const upstream = (path) => import(pathToFileURL(resolve(SOURCE, path)).href);
    const { default: Simulator } = await upstream('src/core/Simulator.ts');
    const reference = 'examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts';
    const { patient, sensor, controller, pump, meals, simOptions } = await upstream(reference);
    manifest.reference_sha256 = hash(resolve(SOURCE, reference));
    manifest.source_files_sha256 = Object.fromEntries(
      git('-C', SOURCE, 'ls-files', 'src', reference, 'LICENSE.md').split('\n')
        .filter(Boolean).map(path => [path, hash(resolve(SOURCE, path))]));
    manifest.configuration = { meals, simOptions, patient: patient.getParameterValues(),
      sensor: sensor.getParameterValues(), controller: controller.getParameterValues(),
      pump: pump.getParameterValues(),
      solver: { name: 'native SolverRK1_2', relative_error_target: 1e-3, default_dt_minutes: 1 },
      seeds: { default_base: 1, sensor: 2, controller: 3, pump: 4, patient: 5 },
    };
    manifest.configuration_sha256 = textHash(encode(manifest.configuration));
    manifest.source_files_digest = textHash(encode(Object.fromEntries(
      Object.entries(manifest.source_files_sha256).sort(([a], [b]) => a.localeCompare(b, 'en')))));
    save();
    const sim = new Simulator();
    sim.setPatient(patient); sim.setSensor(sensor); sim.setController(controller);
    sim.setActuator(pump); sim.setMeals(meals); sim.setOptions(simOptions);
    const execute = (callback) => { sim.setCallback(callback); sim.runSimulation(); };
    manifest.first = record(resolve(output, 'first'), execute);
    // runSimulation performs native reset of the same modules and solver.
    manifest.reset = record(resolve(output, 'reset'), execute);
    manifest.comparison = compare(resolve(output, 'first/native.jsonl'), resolve(output, 'reset/native.jsonl'));
    manifest.baseline = checkBaseline(resolve(output, 'first/native.jsonl'), manifest);
    manifest.status = 'completed';
    console.log(encode({ status: manifest.status, summary: manifest.first.summary, comparison: manifest.comparison }));
  } catch (error) {
    manifest.status = 'failed'; manifest.error = String(error);
    writeFileSync(resolve(output, 'failure.log'), error.stack ?? String(error));
    throw error;
  } finally { save(); }
} else {
  throw Error('Use --output NEW_DIRECTORY or --compare LEFT_JSONL RIGHT_JSONL [--report-differences]');
}
