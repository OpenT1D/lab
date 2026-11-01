import { setTimeout as delay } from 'node:timers/promises';

const monitors = new WeakMap();

// Listen before navigation, including the root entry's meta refresh. Keep
// failures from the earlier document even after the browser has redirected.
export function monitor(page) {
  const receipt = { errors: [], warnings: [], responses: [], requestFailures: [], redirectCancellations: [] };
  const documents = [];
  const requests = new Map();
  const browserResponses = new Map();
  let order = 0;
  let requestId = 0;
  function record(request) {
    if (!requests.has(request)) {
      let mainFrame = false;
      try { mainFrame = request.frame() === page.mainFrame(); } catch (_) { /* Service worker. */ }
      requests.set(request, {
        id: ++requestId,
        url: request.url(), type: request.resourceType(),
        referer: request.headers().referer, mainFrame,
      });
    }
    return requests.get(request);
  }
  const listeners = {
    request: request => { record(request).started = ++order; },
    pageerror: error => receipt.errors.push(`JavaScript: ${error.message}`),
    console: message => {
      if (message.type() === 'error') receipt.errors.push(`Console: ${message.text()}`);
      if (message.type() === 'warning') receipt.warnings.push(message.text());
    },
    requestfailed: request => {
      const item = record(request);
      item.failure = request.failure()?.errorText;
      item.failed = ++order;
      item.errorIndex = receipt.errors.length;
      receipt.errors.push(`Request failed: ${item.url} ${item.failure}`);
      receipt.requestFailures.push({ ...item });
    },
    requestfinished: request => { record(request).finished = ++order; },
    response: response => {
      const item = record(response.request());
      item.status = response.status();
      if (item.type === 'image') browserResponses.set(item.id, response);
      receipt.responses.push({ url: response.url(), status: response.status() });
      if (response.status() >= 400) receipt.errors.push(`HTTP ${response.status()}: ${response.url()}`);
      if (response.request().resourceType() === 'document') {
        documents.push(response.url());
      }
    },
  };
  for (const [event, listener] of Object.entries(listeners)) page.on(event, listener);
  monitors.set(receipt, {
    pending: () => Array.from(requests.values()).filter(item => !item.finished && !item.failed),
    generation: () => order,
  });
  return {
    receipt,
    documents,
    snapshot: () => Array.from(requests.values(), item => ({ ...item })),
    responseFor: item => browserResponses.get(item.id),
    stop: () => {
      monitors.delete(receipt);
      for (const [event, listener] of Object.entries(listeners)) page.off(event, listener);
    },
  };
}

function documentURL(value) {
  try {
    const url = new URL(value);
    url.hash = '';
    return url.href;
  } catch (_) { return null; }
}

// A cancellation is still an error unless the obsolete icon was naturally
// re-requested and fully loaded by the final document. API/decode probes must
// never manufacture that evidence; callers supply a pre-probe snapshot.
export function redirectIconRecoveries(browserName, requests, sources, finalURL, assets) {
  if (browserName !== 'firefox') return [];
  const final = documentURL(finalURL);
  if (!final) return [];
  const target = sources.find(source => documentURL(source.url) === final);
  const navigated = url => requests.some(item => item.type === 'document' && item.mainFrame
    && item.status === 200 && item.finished && !item.failure && documentURL(item.url) === url);
  if (!target || !navigated(final)) return [];
  return requests.flatMap(failed => {
    if (failed.failure !== 'NS_BINDING_ABORTED' || failed.type !== 'image'
      || !failed.mainFrame || !failed.started || !Number.isInteger(failed.errorIndex)) return [];
    const source = sources.find(source => documentURL(source.url) === documentURL(failed.referer)
      && documentURL(source.refresh) === final && documentURL(source.url) !== final
      && source.icons.includes(failed.url) && target.icons.includes(failed.url));
    if (!source || !navigated(documentURL(source.url))
      || new URL(source.url).origin !== new URL(final).origin
      || new URL(failed.url).origin !== new URL(final).origin
      || !assets.some(asset => asset.url === failed.url && asset.status === 200)) return [];
    const recovered = requests.find(item => item !== failed && item.url === failed.url
      && item.type === 'image' && item.mainFrame && documentURL(item.referer) === final
      && item.started > failed.failed && item.finished > item.started
      && item.status === 200 && !item.failure);
    return recovered ? [{ failed, recovered, source: source.url, target: final }] : [];
  });
}

export function assertClean(receipt) {
  if (receipt.errors.length) {
    const error = new Error(receipt.errors.join('\n'));
    error.receipt = receipt;
    throw error;
  }
}

// Sphinx finishes listing links before its summary fetches settle. Keep the
// original monitor active and reject errors before leaving the search page.
export async function waitForSearchCompletion(page, receipt, { timeout = 15_000 } = {}) {
  const state = monitors.get(receipt);
  if (!state) throw new Error('Search completion requires an active request monitor');
  if (!Number.isFinite(timeout) || timeout <= 0) throw new Error('Search deadline must be positive and finite');
  const until = performance.now() + timeout;
  let timer, expired;
  function deadlineError() {
    if (!expired) {
      const message = `Search completion deadline exceeded; pending requests: ${state.pending().map(item => item.url).join(', ') || 'browser settlement'}`;
      receipt.errors.push(message);
      expired = Object.assign(new Error(message), { receipt });
    }
    return expired;
  }
  async function settle() {
    await page.locator('#search-results').getByRole('heading', { name: 'Search Results', exact: true }).waitFor({ state: 'visible', timeout });
    let quietSince = performance.now(), generation = state.generation();
    while (performance.now() < until) {
      assertClean(receipt);
      // A load-state event can already be cached before summary fetches start,
      // and response headers do not mean that their bodies have completed.
      if (state.pending().length || generation !== state.generation()) {
        quietSince = performance.now();
        generation = state.generation();
      } else if (performance.now() - quietSince >= 500) {
        // Let body consumers and queued browser callbacks run before the final
        // error check. The monitor remains active through target navigation.
        await page.evaluate(() => new Promise(resolve => setTimeout(() => setTimeout(resolve, 0), 0)));
        assertClean(receipt);
        if (!state.pending().length && generation === state.generation()) return;
        quietSince = performance.now();
        generation = state.generation();
      }
      await delay(20);
    }
    throw deadlineError();
  }
  try {
    // The Node deadline also bounds a blocked page.evaluate/browser task queue.
    // This is not another attempt; any expiry preserves a failing receipt.
    return await Promise.race([
      new Promise((_, reject) => { timer = setTimeout(() => reject(deadlineError()), timeout); }),
      settle(),
    ]);
  } finally { clearTimeout(timer); }
}

export async function inspectRendering(page, receipt, renderTimeout = 10_000) {
  receipt.images = [];
  for (const image of await page.locator('img').all()) {
    await image.scrollIntoViewIfNeeded();
    const state = await image.evaluate(async img => {
      try { await img.decode(); } catch (_) { /* Report the source below. */ }
      return { url: img.currentSrc || img.src, complete: img.complete, width: img.naturalWidth };
    });
    receipt.images.push(state);
    if (!state.complete || state.width === 0) receipt.errors.push(`Broken image: ${state.url}`);
  }
  receipt.diagrams = await page.locator('.mermaid').count();
  for (const diagram of await page.locator('.mermaid').all()) {
    await diagram.scrollIntoViewIfNeeded();
    await diagram.locator('svg').waitFor({ state: 'attached', timeout: renderTimeout });
    if (await diagram.locator('.error-icon, .error-text').count()) {
      receipt.errors.push('Mermaid diagram rendered an error.');
    }
  }
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  await page.waitForLoadState('networkidle');
}

export async function auditDocument(page, url, request, { renderTimeout = 10_000 } = {}) {
  const { receipt, documents, snapshot, responseFor, stop } = monitor(page);
  receipt.url = url;
  try {
    const response = await page.goto(url, { waitUntil: 'load' });
    receipt.status = response?.status();
    if (receipt.status !== 200) receipt.errors.push(`Document did not return HTTP 200: ${url}`);
    await page.waitForLoadState('networkidle');
    const naturalRequests = snapshot(); // Before rendering, DOMParser or decode probes.
    await inspectRendering(page, receipt, renderTimeout);

    // Headless Chromium does not always request favicons. Explicitly check
    // declared assets and downloads, including links missing from the build.
    // An immediate meta refresh can discard the initial browser response body.
    // Fetch the observed navigation URLs through HTTP instead of racing CDP's
    // body buffer. The loopback server serves the same immutable staged files.
    const sources = await Promise.all(Array.from(new Set(documents), async url => {
      const response = await request.get(url);
      try {
        if (response.status() !== 200) receipt.errors.push(`Document source HTTP ${response.status()}: ${url}`);
        return { url: response.url(), html: await response.text() };
      } finally {
        await response.dispose();
      }
    }));
    // Include the entry HTML before a meta refresh replaces its DOM. This is
    // essential for detecting a broken favicon on the redirect itself.
    const discovery = await page.evaluate(sources => {
      const selector = 'img[src], source[src], script[src], link[rel~="stylesheet"], link[rel~="icon"], link[rel~="preload"], a[download]';
      const collect = (document, base) => Array.from(document.querySelectorAll(selector), element => {
        const source = element.getAttribute('src') || element.getAttribute('href');
        return source?.trim() ? new URL(source, base).href : null;
      });
      const missingIcons = [];
      const documentSources = [];
      const assets = [
        ...collect(document, document.baseURI),
        ...sources.filter(source => typeof source.html === 'string').flatMap(source => {
          const parsed = new DOMParser().parseFromString(source.html, 'text/html');
          if (!Array.from(parsed.querySelectorAll('link[rel~="icon"]')).some(
            icon => icon.getAttribute('href')?.trim(),
          )) missingIcons.push(source.url);
          const base = new URL(parsed.querySelector('base[href]')?.getAttribute('href') || source.url, source.url).href;
          const icons = Array.from(parsed.querySelectorAll('link[rel~="icon"][href]'), icon => new URL(icon.getAttribute('href'), base).href);
          const meta = Array.from(parsed.querySelectorAll('meta[http-equiv]')).find(meta => meta.getAttribute('http-equiv').toLowerCase() === 'refresh');
          const refresh = meta?.getAttribute('content')?.match(/^\s*0\s*;\s*url\s*=\s*(.+?)\s*$/i);
          const destination = refresh?.[1].replace(/^(['"])(.*)\1$/, '$2');
          documentSources.push({ url: source.url, icons, refresh: destination ? new URL(destination, base).href : null });
          return collect(parsed, base);
        }),
      ].filter(url => /^https?:/.test(url));
      return { assets, missingIcons, documentSources };
    }, sources);
    for (const source of discovery.missingIcons) receipt.errors.push(`Missing favicon link: ${source}`);
    receipt.assets = [];
    for (const asset of new Set(discovery.assets)) {
      const response = await request.get(asset);
      receipt.assets.push({ url: asset, status: response.status() });
      if (response.status() !== 200) receipt.errors.push(`Asset HTTP ${response.status()}: ${asset}`);
      await response.dispose();
    }
    receipt.finalURL = page.url();
    const recoveries = redirectIconRecoveries(page.context().browser().browserType().name(),
      naturalRequests, discovery.documentSources, receipt.finalURL, receipt.assets);
    const accepted = new Set();
    for (const recovery of recoveries) {
      let decoded = false;
      try {
        const response = responseFor(recovery.recovered);
        const mime = response.headers()['content-type']?.split(';')[0] || 'application/octet-stream';
        const data = `data:${mime};base64,${(await response.body()).toString('base64')}`;
        decoded = await page.evaluate(async data => {
          const image = new Image();
          image.src = data;
          try {
            await image.decode();
            return image.naturalWidth > 0 && image.naturalHeight > 0;
          } catch (_) { return false; }
        }, data);
      } catch (_) { /* Unavailable response bytes cannot justify an exception. */ }
      if (!decoded) {
        receipt.errors.push(`Recovered favicon response did not decode: ${recovery.failed.url}`);
        continue;
      }
      accepted.add(recovery.failed.errorIndex);
      receipt.redirectCancellations.push({ ...recovery, decoded, decodeSource: 'completed-browser-response' });
    }
    if (recoveries.length) await page.waitForLoadState('networkidle');
    receipt.errors = receipt.errors.filter((_error, index) => !accepted.has(index));
  } catch (error) {
    receipt.errors.push(`Inspection: ${error.message}`);
  } finally {
    stop();
  }
  assertClean(receipt);
  return receipt;
}
