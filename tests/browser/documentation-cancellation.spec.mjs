import { test, expect } from '@playwright/test';
import { redirectIconRecoveries } from './documentation-audit.mjs';

// Protocol counterexamples complement the native Firefox integration fixture.
function evidence() {
  const source = 'http://site.test/lab/index.html';
  const target = 'http://site.test/lab/docs/index.html';
  const icon = 'http://site.test/lab/_static/icon.svg';
  return {
    browser: 'firefox', finalURL: target,
    requests: [
      { url: source, type: 'document', mainFrame: true, status: 200, started: 1, finished: 2 },
      { url: icon, type: 'image', mainFrame: true, referer: source, started: 3, failed: 4, failure: 'NS_BINDING_ABORTED', errorIndex: 0 },
      { url: target, type: 'document', mainFrame: true, status: 200, started: 5, finished: 6 },
      { url: icon, type: 'image', mainFrame: true, referer: target, status: 200, started: 7, finished: 8 },
    ],
    sources: [{ url: source, icons: [icon], refresh: target }, { url: target, icons: [icon], refresh: null }],
    assets: [{ url: icon, status: 200 }],
  };
}
const classify = data => redirectIconRecoveries(data.browser, data.requests, data.sources, data.finalURL, data.assets);

test('favicon recovery correlates the exact failed and completed requests', () => {
  const data = evidence();
  const matches = classify(data);
  expect(matches).toHaveLength(1);
  expect(matches[0].failed).toBe(data.requests[1]);
  expect(matches[0].recovered).toBe(data.requests[3]);
});

test('a second failure for the same URL retains its separate error identity', () => {
  const data = evidence();
  data.requests.push({ ...data.requests[1], referer: data.finalURL, started: 9, failed: 10, errorIndex: 1 });
  expect(classify(data).map(match => match.failed.errorIndex)).toEqual([0]);
});

for (const [name, change] of [
  ['Chromium cancellation', data => { data.browser = 'chromium'; }],
  ['WebKit cancellation', data => { data.browser = 'webkit'; }],
  ['different failure code', data => { data.requests[1].failure = 'NS_ERROR_NET_RESET'; }],
  ['stylesheet failure', data => { data.requests[1].type = 'stylesheet'; }],
  ['iframe failure', data => { data.requests[1].mainFrame = false; }],
  ['final document failure', data => { data.requests[1].referer = data.finalURL; }],
  ['undeclared source icon', data => { data.sources[0].icons = []; }],
  ['undeclared final icon', data => { data.sources[1].icons = []; }],
  ['no immediate refresh', data => { data.sources[0].refresh = null; }],
  ['wrong refresh target', data => { data.sources[0].refresh = 'http://site.test/elsewhere'; }],
  ['unsuccessful final document', data => { data.requests[2].status = 404; }],
  ['uncompleted source document', data => { delete data.requests[0].finished; }],
  ['uncompleted final document', data => { delete data.requests[2].finished; }],
  ['source navigation in an iframe', data => { data.requests[0].mainFrame = false; }],
  ['in-place document change', data => { data.sources[0].url = data.finalURL; data.requests[1].referer = data.finalURL; }],
  ['cross-origin destination', data => {
    const target = 'http://other.test/final.html';
    data.finalURL = target; data.sources[0].refresh = target; data.sources[1].url = target;
    data.requests[2].url = target; data.requests[3].referer = target;
  }],
  ['cross-origin icon', data => {
    const icon = 'http://cdn.test/icon.svg';
    data.requests[1].url = icon; data.requests[3].url = icon;
    data.sources[0].icons = [icon]; data.sources[1].icons = [icon]; data.assets[0].url = icon;
  }],
  ['earlier cached image', data => { data.requests[3].started = 1; }],
  ['response headers without completion', data => { delete data.requests[3].finished; }],
  ['subsequently failed image', data => { data.requests[3].failure = 'NS_BINDING_ABORTED'; }],
  ['HTTP error for recovered image', data => { data.requests[3].status = 404; }],
  ['different final image URL', data => { data.requests[3].url += '?different'; }],
  ['different final referrer', data => { data.requests[3].referer = data.sources[0].url; }],
  ['iframe recovery', data => { data.requests[3].mainFrame = false; }],
  ['fetch recovery', data => { data.requests[3].type = 'fetch'; }],
  ['API success without browser recovery', data => { data.requests.pop(); }],
  ['failed explicit asset probe', data => { data.assets[0].status = 404; }],
]) {
  test(`favicon cancellation remains an error: ${name}`, () => {
    const data = evidence();
    change(data);
    expect(classify(data)).toEqual([]);
  });
}
