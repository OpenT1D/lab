import { test as base, expect } from '@playwright/test';
import { createServer } from 'node:http';
import { assertClean, auditDocument, monitor, waitForSearchCompletion } from './documentation-audit.mjs';

// Real disposable HTTP responses make the browser and explicit source/asset
// fetches observe identical fixtures, including an immediate meta refresh.
const test = base.extend({
  faultSite: async ({}, use) => {
    const routes = new Map([
      ['/lab/_static/icon.svg', { type: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg"/>' }],
    ]);
    const server = createServer((request, response) => {
      const route = routes.get(new URL(request.url, 'http://localhost').pathname);
      if (route?.handler) return route.handler(request, response);
      response.writeHead(route ? 200 : 404, { 'Content-Type': route?.type || 'text/html' });
      response.end(route?.body || 'Synthetic missing resource');
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const baseURL = `http://127.0.0.1:${server.address().port}/lab/`;
    const put = (name, body) => {
      const url = new URL(name, baseURL);
      routes.set(url.pathname, { type: 'text/html', body });
      return url.href;
    };
    const handle = (name, handler) => {
      const url = new URL(name, baseURL);
      routes.set(url.pathname, { handler });
      return url.href;
    };
    try {
      await use({ put, handle, baseURL });
    } finally {
      server.closeAllConnections();
      await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    }
  },
});

const html = body => `<!doctype html><link rel="icon" href="_static/icon.svg"><title>Synthetic audit fixture</title>${body}`;
// Like Sphinx, expose the result link and finished heading while a non-blocking
// summary fetch is still pending. Real HTTP latency makes an early click abort
// that request; no browser errors are intercepted or substituted.
function searchFixture(site, fault = 'healthy') {
  const state = { summaryFinished: false, targetRequested: false, targetBeforeSummary: false };
  const summary = site.handle('__search-summary.txt', (_request, response) => {
    response.writeHead(fault === 'missing summary' ? 404 : 200, { 'Content-Type': 'text/plain' });
    response.flushHeaders();
    const timer = setTimeout(() => {
      response.end('Delayed summary is complete');
    }, 800);
    response.on('finish', () => { state.summaryFinished = true; });
    response.on('close', () => clearTimeout(timer));
  });
  const target = site.handle('__search-target.html', (_request, response) => {
    state.targetRequested = true;
    state.targetBeforeSummary = !state.summaryFinished;
    response.writeHead(200, { 'Content-Type': 'text/html' });
    response.end(html(`<article><h1>Search target</h1></article>${fault === 'target asset' ? '<script src="__missing-target.js"></script>' : ''}`));
  });
  const lateFault = {
    'console error': 'console.error("delayed search console fault")',
    'JavaScript exception': 'throw new Error("delayed search page fault")',
  }[fault] || '';
  const source = site.put('__search.html', html(`
    <div id="search-results"><h2>Search Results</h2><a href="${target}">First result</a><p id="summary"></p></div>
    <script>
      fetch(${JSON.stringify(summary)}).then(response => response.text()).then(text => {
        document.getElementById('summary').textContent = text;
        ${lateFault}
      });
    </script>`));
  return { source, target, summary, state };
}

test('search waits for a delayed summary before opening a result', async ({ page, faultSite }, testInfo) => {
  const fixture = searchFixture(faultSite);
  const { receipt, stop } = monitor(page);
  try {
    await page.goto(fixture.source);
    await waitForSearchCompletion(page, receipt);
    const summaryBeforeClick = await page.locator('#summary').textContent();
    await page.getByRole('link', { name: 'First result' }).click();
    await expect(page).toHaveURL(fixture.target);
    await expect(page.locator('article h1')).toHaveText('Search target');
    await page.waitForLoadState('networkidle');
    assertClean(receipt);
    expect(summaryBeforeClick).toBe('Delayed summary is complete');
    expect(fixture.state).toEqual({ summaryFinished: true, targetRequested: true, targetBeforeSummary: false });
  } finally {
    stop();
    await testInfo.attach('delayed-search.json', { body: JSON.stringify({ ...fixture.state, ...receipt }), contentType: 'application/json' });
  }
});

for (const [fault, error] of [
  ['missing summary', /HTTP 404: .*__search-summary.txt/],
  ['console error', /Console: delayed search console fault/],
  ['JavaScript exception', /JavaScript: (?:Error: )?delayed search page fault/],
  ['aborted summary', /Request failed: .*__search-summary.txt/],
]) {
  test(`search preserves ${fault} while waiting for completion`, async ({ page, faultSite }, testInfo) => {
    const fixture = searchFixture(faultSite, fault);
    if (fault === 'aborted summary') await page.route('**/__search-summary.txt', route => route.abort('aborted'));
    const { receipt, stop } = monitor(page);
    try {
      await page.goto(fixture.source);
      await expect(waitForSearchCompletion(page, receipt)).rejects.toThrow(error);
      expect(receipt.errors.some(message => error.test(message))).toBe(true);
      if (fault === 'aborted summary') {
        const failed = receipt.requestFailures.find(item => item.url === fixture.summary);
        expect(failed?.type).toBe('fetch');
        expect(failed.failure).toBeTruthy();
        expect(receipt.errors).toContain(`Request failed: ${fixture.summary} ${failed.failure}`);
      }
      expect(fixture.state.targetRequested).toBe(false);
      expect(page.url()).toBe(fixture.source);
    } finally {
      stop();
      await testInfo.attach('search-fault.json', { body: JSON.stringify({ ...fixture.state, ...receipt }), contentType: 'application/json' });
    }
  });
}

test('search keeps monitoring asset errors after opening the result', async ({ page, faultSite }, testInfo) => {
  const fixture = searchFixture(faultSite, 'target asset');
  const { receipt, stop } = monitor(page);
  try {
    await page.goto(fixture.source);
    await waitForSearchCompletion(page, receipt);
    await page.getByRole('link', { name: 'First result' }).click();
    await expect(page).toHaveURL(fixture.target);
    await page.waitForLoadState('networkidle');
    expect(() => assertClean(receipt)).toThrow(/HTTP 404: .*__missing-target.js/);
    expect(fixture.state.targetBeforeSummary).toBe(false);
  } finally {
    stop();
    await testInfo.attach('search-target-fault.json', { body: JSON.stringify({ ...fixture.state, ...receipt }), contentType: 'application/json' });
  }
});

const cases = [
  ['missing image', '<img src="__missing-image.svg">', /HTTP 404: .*__missing-image.svg/],
  ['missing stylesheet', '<link rel="stylesheet" href="__missing-style.css">', /HTTP 404: .*__missing-style.css/],
  ['missing favicon', '<link rel="icon" href="/__missing-favicon.ico">', /Asset HTTP 404: .*__missing-favicon.ico/],
  ['console error', '<script>console.error("synthetic console fault")</script>', /Console: synthetic console fault/],
  ['JavaScript exception', '<script>throw new Error("synthetic page fault")</script>', /JavaScript: synthetic page fault/],
  ['unrendered diagram', '<pre class="mermaid">unrendered synthetic diagram</pre>', /Inspection: .*waitFor/s],
];

test('audit accepts a healthy control', async ({ page, request, faultSite }) => {
  const url = faultSite.put('__audit-control.html', html('<p>OK</p>'));
  const receipt = await auditDocument(page, url, request);
  expect(receipt.errors).toEqual([]);
});

for (const [name, body, error] of cases) {
  test(`audit rejects ${name}`, async ({ page, request, faultSite }) => {
    const url = faultSite.put('__audit-fault.html', html(body));
    await expect(auditDocument(page, url, request, { renderTimeout: 300 })).rejects.toThrow(error);
  });
}

test('audit rejects a failed network request', async ({ page, request, faultSite }) => {
  const url = faultSite.put('__audit-network.html', html('<script src="__aborted.js"></script>'));
  await page.route('**/__aborted.js', route => route.abort('failed'));
  await expect(auditDocument(page, url, request)).rejects.toThrow(/Request failed: .*__aborted.js/);
});

for (const [name, icon, error] of [
  ['missing', '<link rel="icon" href="/__missing-entry-icon.svg">', /Asset HTTP 404: .*__missing-entry-icon.svg/],
  ['absent', '', /Missing favicon link: .*__audit-entry.html/],
  ['empty', '<link rel="icon" href="">', /Missing favicon link: .*__audit-entry.html/],
  ['whitespace', '<link rel="icon" href="   ">', /Missing favicon link: .*__audit-entry.html/],
]) {
  test(`audit rejects ${name} favicon before meta refresh`, async ({ page, request, faultSite }) => {
    const target = faultSite.put('__audit-target.html', html('<p>Healthy redirect target</p>'));
    const url = faultSite.put('__audit-entry.html', `<!doctype html>${icon}<meta http-equiv="refresh" content="0; url=${target}">`);
    await expect(auditDocument(page, url, request)).rejects.toThrow(error);
    expect(page.url()).toBe(target);
  });
}

test('audit accepts a healthy meta-refresh entry', async ({ page, request, faultSite }) => {
  const target = faultSite.put('__audit-target.html', html('<p>Healthy redirect target</p>'));
  const url = faultSite.put('__audit-entry.html', html(`<meta http-equiv="refresh" content="0; url=${target}">`));
  const receipt = await auditDocument(page, url, request);
  expect(receipt.errors).toEqual([]);
  expect(page.url()).toBe(target);
});

// Let Firefox start its native, non-load-blocking favicon request before
// ending the streamed entry with a refresh. No synthetic image request.
function faviconRedirect(site, { iconStatus = 200, iconBody, finalIcon = true, extra = '', redirect = 'immediate', laterIconHealthy = false } = {}) {
  const icon = new URL('__redirect-icon.svg', site.baseURL).href;
  const source = new URL('__streamed-entry.html', site.baseURL).href;
  const target = site.put('__streamed-target.html', `<!doctype html>${finalIcon ? `<link rel="icon" href="${icon}">` : ''}<title>Redirect target</title><h1>Target</h1>${extra}`);
  const head = `<!doctype html><head><meta charset="utf-8"><link rel="icon" href="${icon}"></head><body><h1>Entry</h1><!--${'padding'.repeat(800)}-->`;
  const meta = redirect === 'absent' ? '' : `<meta http-equiv="refresh" content="${redirect === 'delayed' ? 60 : 0}; url=${redirect === 'wrong' ? `${site.baseURL}wrong-target.html` : target}">`;
  const navigate = redirect === 'immediate' ? '' : `<script>location.replace(${JSON.stringify(target)})</script>`;
  const tail = `${meta}${navigate}</body></html>`;
  let entry;
  let finalIconRequests = 0;
  site.handle('__streamed-entry.html', (_request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    if (entry) return response.end(head + tail);
    entry = response;
    response.write(head);
  });
  site.handle('__redirect-icon.svg', (request, response) => {
    if (request.headers.referer === source) {
      if (!entry.writableEnded) entry.end(tail);
      return;
    }
    response.writeHead(iconStatus, { 'Content-Type': 'image/svg+xml' });
    const healthy = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16"/></svg>';
    const laterRequest = request.headers.referer !== target || finalIconRequests++ > 0;
    response.end(laterIconHealthy && laterRequest ? healthy : (iconBody ?? healthy));
  });
  return { source, target, icon };
}

test('audit accepts a recovered Firefox favicon cancellation', async ({ browserName, page, request, faultSite }, testInfo) => {
  test.skip(browserName !== 'firefox', 'Firefox-specific cancellation regression.');
  const fixture = faviconRedirect(faultSite);
  const receipt = await auditDocument(page, fixture.source, request);
  await testInfo.attach('redirect-recovery.json', { body: JSON.stringify(receipt), contentType: 'application/json' });
  expect(page.url()).toBe(fixture.target);
  expect(receipt.errors).toEqual([]);
  expect(receipt.requestFailures).toHaveLength(1);
  expect(receipt.requestFailures[0]).toMatchObject({ url: fixture.icon, failure: 'NS_BINDING_ABORTED', referer: fixture.source });
  expect(receipt.redirectCancellations).toHaveLength(1);
  expect(receipt.redirectCancellations[0]).toMatchObject({ source: fixture.source, target: fixture.target, decoded: true, decodeSource: 'completed-browser-response' });
});

for (const [name, options] of [
  ['404 final icon', { iconStatus: 404 }],
  ['corrupt final icon', { iconBody: 'invalid SVG despite HTTP 200' }],
  ['corrupt browser bytes followed by a healthy probe', { iconBody: 'invalid SVG despite HTTP 200', laterIconHealthy: true }],
  ['missing final icon declaration', { finalIcon: false }],
]) {
  test(`audit preserves Firefox cancellation with ${name}`, async ({ browserName, page, request, faultSite }) => {
    test.skip(browserName !== 'firefox', 'Firefox-specific cancellation regression.');
    const fixture = faviconRedirect(faultSite, options);
    const error = await auditDocument(page, fixture.source, request).then(() => null, error => error);
    expect(error?.receipt).toBeTruthy();
    expect(error.receipt.requestFailures.some(item => item.failure === 'NS_BINDING_ABORTED' && item.url === fixture.icon)).toBe(true);
    expect(error.receipt.errors).toContain(`Request failed: ${fixture.icon} NS_BINDING_ABORTED`);
    expect(error.receipt.redirectCancellations).toEqual([]);
  });
}

test('audit preserves an aborted final icon even when its API probe succeeds', async ({ browserName, page, request, faultSite }) => {
  test.skip(browserName !== 'firefox', 'Firefox-specific cancellation regression.');
  const fixture = faviconRedirect(faultSite);
  await page.route('**/__redirect-icon.svg', async route => {
    if (route.request().headers().referer === fixture.target) await route.abort('aborted');
    else await route.continue();
  });
  const error = await auditDocument(page, fixture.source, request).then(() => null, error => error);
  expect(error?.receipt).toBeTruthy();
  expect(error.receipt.errors).toContain(`Request failed: ${fixture.icon} NS_BINDING_ABORTED`);
  expect(error.receipt.redirectCancellations).toEqual([]);
  expect(error.receipt.assets).toContainEqual({ url: fixture.icon, status: 200 });
});

test('audit preserves an unrelated aborted stylesheet after icon recovery', async ({ browserName, page, request, faultSite }) => {
  test.skip(browserName !== 'firefox', 'Firefox-specific cancellation regression.');
  const fixture = faviconRedirect(faultSite, { extra: '<link rel="stylesheet" href="__aborted.css">' });
  await page.route('**/__aborted.css', route => route.abort('aborted'));
  const error = await auditDocument(page, fixture.source, request).then(() => null, error => error);
  expect(error?.receipt).toBeTruthy();
  expect(error.receipt.errors.some(message => /Request failed: .*__aborted.css/.test(message))).toBe(true);
  expect(error.receipt.redirectCancellations).toHaveLength(1);
});

for (const redirect of ['absent', 'delayed', 'wrong']) {
  test(`audit preserves Firefox cancellation with ${redirect} immediate-meta evidence`, async ({ browserName, page, request, faultSite }) => {
    test.skip(browserName !== 'firefox', 'Firefox-specific cancellation regression.');
    const fixture = faviconRedirect(faultSite, { redirect });
    const error = await auditDocument(page, fixture.source, request).then(() => null, error => error);
    expect(error?.receipt).toBeTruthy();
    expect(error.receipt.finalURL).toBe(fixture.target);
    expect(error.receipt.errors).toContain(`Request failed: ${fixture.icon} NS_BINDING_ABORTED`);
    expect(error.receipt.redirectCancellations).toEqual([]);
  });
}
