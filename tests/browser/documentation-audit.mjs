// Listen before navigation, including the root entry's meta refresh. Keep
// failures from the earlier document even after the browser has redirected.
export function monitor(page) {
  const receipt = { errors: [], warnings: [], responses: [] };
  const documents = [];
  const listeners = {
    pageerror: error => receipt.errors.push(`JavaScript: ${error.message}`),
    console: message => {
      if (message.type() === 'error') receipt.errors.push(`Console: ${message.text()}`);
      if (message.type() === 'warning') receipt.warnings.push(message.text());
    },
    requestfailed: request => receipt.errors.push(
      `Request failed: ${request.url()} ${request.failure()?.errorText}`,
    ),
    response: response => {
      receipt.responses.push({ url: response.url(), status: response.status() });
      if (response.status() >= 400) receipt.errors.push(`HTTP ${response.status()}: ${response.url()}`);
      if (response.request().resourceType() === 'document') {
        documents.push(response.text().then(
          html => ({ url: response.url(), html }),
          error => ({ url: response.url(), error: error.message }),
        ));
      }
    },
  };
  for (const [event, listener] of Object.entries(listeners)) page.on(event, listener);
  return {
    receipt,
    documents,
    stop: () => {
      for (const [event, listener] of Object.entries(listeners)) page.off(event, listener);
    },
  };
}

export function assertClean(receipt) {
  if (receipt.errors.length) {
    const error = new Error(receipt.errors.join('\n'));
    error.receipt = receipt;
    throw error;
  }
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
  const { receipt, documents, stop } = monitor(page);
  receipt.url = url;
  try {
    const response = await page.goto(url, { waitUntil: 'load' });
    receipt.status = response?.status();
    if (receipt.status !== 200) receipt.errors.push(`Document did not return HTTP 200: ${url}`);
    await page.waitForLoadState('networkidle');
    await inspectRendering(page, receipt, renderTimeout);

    // Headless Chromium does not always request favicons. Explicitly check
    // declared assets and downloads, including links missing from the build.
    const sources = await Promise.all(documents);
    for (const source of sources) {
      if (source.error) receipt.errors.push(`Document body: ${source.url} ${source.error}`);
    }
    // Include the entry HTML before a meta refresh replaces its DOM. This is
    // essential for detecting a broken favicon on the redirect itself.
    const discovery = await page.evaluate(sources => {
      const selector = 'img[src], source[src], script[src], link[rel~="stylesheet"], link[rel~="icon"], link[rel~="preload"], a[download]';
      const collect = (document, base) => Array.from(document.querySelectorAll(selector), element => {
        const source = element.getAttribute('src') || element.getAttribute('href');
        return source ? new URL(source, base).href : null;
      });
      const missingIcons = [];
      const assets = [
        ...collect(document, document.baseURI),
        ...sources.filter(source => source.html).flatMap(source => {
          const parsed = new DOMParser().parseFromString(source.html, 'text/html');
          if (!parsed.querySelector('link[rel~="icon"][href]')) missingIcons.push(source.url);
          const base = new URL(parsed.querySelector('base[href]')?.getAttribute('href') || source.url, source.url).href;
          return collect(parsed, base);
        }),
      ].filter(url => /^https?:/.test(url));
      return { assets, missingIcons };
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
  } catch (error) {
    receipt.errors.push(`Inspection: ${error.message}`);
  } finally {
    stop();
  }
  assertClean(receipt);
  return receipt;
}
