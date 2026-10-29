import { test as base, expect } from '@playwright/test';
import { createServer } from 'node:http';
import { auditDocument } from './documentation-audit.mjs';

// Real disposable HTTP responses make the browser and explicit source/asset
// fetches observe identical fixtures, including an immediate meta refresh.
const test = base.extend({
  faultSite: async ({}, use) => {
    const routes = new Map([
      ['/lab/_static/icon.svg', { type: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg"/>' }],
    ]);
    const server = createServer((request, response) => {
      const route = routes.get(new URL(request.url, 'http://localhost').pathname);
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
    try {
      await use({ put, baseURL });
    } finally {
      server.closeAllConnections();
      await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    }
  },
});

const html = body => `<!doctype html><link rel="icon" href="_static/icon.svg"><title>Synthetic audit fixture</title>${body}`;
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
