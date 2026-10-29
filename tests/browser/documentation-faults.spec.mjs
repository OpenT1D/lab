import { test, expect } from '@playwright/test';
import { auditDocument } from './documentation-audit.mjs';

const html = body => `<!doctype html><link rel="icon" href="_static/icon.svg"><title>Synthetic audit fixture</title>${body}`;

const cases = [
  ['missing image', '<img src="__missing-image.svg">', /HTTP 404: .*__missing-image.svg/],
  ['missing stylesheet', '<link rel="stylesheet" href="__missing-style.css">', /HTTP 404: .*__missing-style.css/],
  ['missing favicon', '<link rel="icon" href="/__missing-favicon.ico">', /Asset HTTP 404: .*__missing-favicon.ico/],
  ['console error', '<script>console.error("synthetic console fault")</script>', /Console: synthetic console fault/],
  ['JavaScript exception', '<script>throw new Error("synthetic page fault")</script>', /JavaScript: synthetic page fault/],
  ['unrendered diagram', '<pre class="mermaid">unrendered synthetic diagram</pre>', /Inspection: .*waitFor/s],
];

test('audit accepts a healthy control', async ({ page, request, baseURL }) => {
  const url = new URL('__audit-control.html', baseURL).href;
  await page.route(url, route => route.fulfill({ contentType: 'text/html', body: html('<p>OK</p>') }));
  const receipt = await auditDocument(page, url, request);
  expect(receipt.errors).toEqual([]);
});

for (const [name, body, error] of cases) {
  test(`audit rejects ${name}`, async ({ page, request, baseURL }) => {
    const url = new URL('__audit-fault.html', baseURL).href;
    await page.route(url, route => route.fulfill({ contentType: 'text/html', body: html(body) }));
    await expect(auditDocument(page, url, request, { renderTimeout: 300 })).rejects.toThrow(error);
  });
}

test('audit rejects a failed network request', async ({ page, request, baseURL }) => {
  const url = new URL('__audit-network.html', baseURL).href;
  await page.route(url, route => route.fulfill({ contentType: 'text/html', body: html('<script src="__aborted.js"></script>') }));
  await page.route('**/__aborted.js', route => route.abort('failed'));
  await expect(auditDocument(page, url, request)).rejects.toThrow(/Request failed: .*__aborted.js/);
});

test('audit rejects a missing favicon on a meta-refresh entry', async ({ page, request, baseURL }) => {
  const url = new URL('__audit-entry.html', baseURL).href;
  await page.route(url, route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><link rel="icon" href="/__missing-entry-icon.svg"><meta http-equiv="refresh" content="0; url=docs/index.html">' }));
  await expect(auditDocument(page, url, request)).rejects.toThrow(/Asset HTTP 404: .*__missing-entry-icon.svg/);
  expect(page.url()).toBe(new URL('docs/index.html', baseURL).href);
});

test('audit rejects an absent favicon declaration before meta refresh', async ({ page, request, baseURL }) => {
  const url = new URL('__audit-no-icon.html', baseURL).href;
  await page.route(url, route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><meta http-equiv="refresh" content="0; url=docs/index.html">' }));
  await expect(auditDocument(page, url, request)).rejects.toThrow(/Missing favicon link: .*__audit-no-icon.html/);
  expect(page.url()).toBe(new URL('docs/index.html', baseURL).href);
});

for (const [name, href] of [['empty', ''], ['whitespace', '   ']]) {
  test(`audit rejects an ${name} favicon href before meta refresh`, async ({ page, request, baseURL }) => {
    const url = new URL('__audit-empty-icon.html', baseURL).href;
    await page.route(url, route => route.fulfill({ contentType: 'text/html', body: `<!doctype html><link rel="icon" href="${href}"><meta http-equiv="refresh" content="0; url=docs/index.html">` }));
    await expect(auditDocument(page, url, request)).rejects.toThrow(/Missing favicon link: .*__audit-empty-icon.html/);
  });
}
