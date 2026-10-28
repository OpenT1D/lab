// Execute unmodified, hash-checked external R functions on invented inputs.
// The external package/runtime is not vendored or added to repository tooling.
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const [runtimeDir, sourceDir, output] = process.argv.slice(2);
if (!runtimeDir || !sourceDir || !output) {
  throw new Error('Usage: node webr-probe.mjs WEBR_PACKAGE_DIR SOURCE_DIR NEW_OUTPUT');
}
const here = dirname(fileURLToPath(import.meta.url));
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const manifest = JSON.parse(await readFile(resolve(here, 'source-manifest.json'), 'utf8'));
const sources = new Map();
for (const [name, spec] of Object.entries(manifest.files)) {
  const bytes = await readFile(resolve(sourceDir, name));
  if (digest(bytes) !== spec.sha256) throw new Error(`Source hash mismatch: ${name}`);
  sources.set(name, bytes);
}
const runtime = JSON.parse(await readFile(resolve(runtimeDir, 'package.json'), 'utf8'));
if (runtime.version !== '0.6.0') throw new Error('This probe requires WebR 0.6.0');
const runtimeLock = await readFile(resolve(runtimeDir, '../../package-lock.json'));
const expectedLock = await readFile(resolve(here, 'webr-runtime/package-lock.json'));
if (digest(runtimeLock) !== digest(expectedLock)) throw new Error('Runtime lock mismatch');
const { WebR } = await import(pathToFileURL(resolve(runtimeDir, 'dist/webr.mjs')).href);
const webR = new WebR({ baseUrl: resolve(runtimeDir, 'dist') + '/' });
await webR.init();
try {
  for (const name of ['R/isr.deconv.R', 'R/isr.volume.R']) {
    await webR.FS.writeFile('/' + name.split('/').pop(), sources.get(name));
  }
  await webR.evalRVoid(`
    source('/isr.deconv.R')
    source('/isr.volume.R')
    k1 <- .037; k2 <- .031; k3 <- .052
    z <- k1+k2+k3
    alpha <- (z+sqrt(z*z-4*k2*k3))/2
    beta <- (z-sqrt(z*z-4*k2*k3))/2
    shl <- log(2)/alpha; lhl <- log(2)/beta
    frc <- (alpha-k2)/(alpha-beta)
    captured_warnings <- character()
    run_constant <- function(times, volume=4585) {
      withCallingHandlers(
        isr.deconv(times, rep(.2,length(times)), volume, shl, lhl, frc, method='linear'),
        warning=function(w) {
          captured_warnings <<- c(captured_warnings, conditionMessage(w))
          invokeRestart('muffleWarning')
        }
      )
    }
  `);
  const analytical = JSON.parse(await readFile(resolve(here, 'probe-results.json'), 'utf8'));
  const cases = [];
  for (const times of [[0,15,30,60,90,120], [0,30,60,90,120], [0,60,120]]) {
    await webR.evalRVoid(`result <- run_constant(c(${times.join(',')}))`);
    const rates = await (await webR.evalR('result$y')).toArray();
    const midpoints = await (await webR.evalR('result$x')).toArray();
    const error = Math.max(...rates.map((q) => Math.abs(q / 47.684 - 1)));
    const reference = analytical.exponential_quadrature_controls[cases.length];
    if (Math.abs(error - reference.max_absolute_relative_rate_error) > 1e-5) {
      throw new Error('R linear routine disagrees with the analytical quadrature control');
    }
    cases.push({ times_min: times, midpoints_min: midpoints, rates_pmol_min: rates,
      max_absolute_relative_rate_error: error });
  }
  const volume = await webR.evalRNumber('isr.volume("m",86.2,181.5)');
  if (Math.abs(volume - 4620.555619742381) > 1e-8) throw new Error('Volume control failed');
  const negativeVolumeReturnsNegativeRates = await webR.evalRBoolean(
    'all(run_constant(c(0,30,60,90,120), -4585)$y < 0)');
  const duplicateTimesReturnNonfinite = await webR.evalRBoolean(
    'any(!is.finite(run_constant(c(0,30,30,60,120))$y))');
  const runtimeFiles = {};
  for (const name of ['package.json','dist/R.js','dist/R.wasm','dist/webr.mjs',
    'dist/webr-worker.js','dist/libRblas.so','dist/libRlapack.so']) {
    runtimeFiles[name] = digest(await readFile(resolve(runtimeDir, name)));
  }
  const result = {
    schema: 'ot053-webr-linear-probe/1', upstream_commit: manifest.commit,
    scope: 'unmodified external source functions in WebAssembly R; invented inputs only',
    node_version: process.version, webr_version: runtime.version,
    r_version: await webR.evalRString('R.version.string'),
    native_rscript_executed: false, full_package_installed: false, spline_executed: false,
    runtime_sha256: runtimeFiles,
    runtime_npm_lock_sha256: digest(runtimeLock),
    probe_sha256: digest(await readFile(fileURLToPath(import.meta.url))),
    cases, volume_helper_result_ml: volume,
    negative_volume_returns_negative_rates: negativeVolumeReturnsNegativeRates,
    duplicate_times_return_nonfinite: duplicateTimesReturnNonfinite,
    captured_r_warnings: await (await webR.evalR('captured_warnings')).toArray(),
  };
  await writeFile(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log(`WebAssembly R linear controls passed; saved ${output}`);
} finally {
  await webR.close();
}
