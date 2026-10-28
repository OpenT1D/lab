// Deferred responses exercise the shipped durable report/download functions.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync("experiments/gui/static/app.js", "utf8");
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert(a >= 0 && b > a); return source.slice(a, b);
}
function harness() {
  const elements = new Map(), pending = [], clicks = [];
  const element = () => ({hidden: true, textContent: "", children: [], replaceChildren() { this.children = []; }, append(...items) { this.children.push(...items); }, click() { clicks.push(this.download); }});
  const $ = (id) => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const context = vm.createContext({$, document: {createElement: element}, Date, active: null,
    durableSelected: null, durableRequest: 0, durableSelection: 0, durableShown: null,
    durableLastReportCheck: 0, durablePending: false,
    URL: {revokeObjectURL() {}, createObjectURL() { return "blob:native"; }}, setTimeout() {},
    api(path) { return new Promise((resolve, reject) => pending.push({path, resolve, reject})); },
  });
  vm.runInContext(section('function durableNotice(message)', 'function durableControls()'), context);
  vm.runInContext(section('async function displayDurableReport()', 'async function refreshDurable()'), context);
  vm.runInContext(section('async function downloadDurable(name)', 'async function initDurable()'), context);
  function entry(id, reconstruction = "verified_snapshot", stamp = "one") { return {id, checked_at: stamp, integrity: "verified_snapshot", reconstruction, snapshot_job: "job-" + stamp, availability: "available", can_view_report: true, artifacts_sha256: {"report.json": "json", "report.md": "md"}}; }
  function choose(id, reconstruction, stamp) { context.durableSelected = entry(id, reconstruction, stamp); vm.runInContext('clearDurableResults()', context); return vm.runInContext('displayDurableReport()', context); }
  function reply(id, suffix, value, fail = false) { const i = pending.findIndex((request) => request.path.includes('/' + id + '/') && request.path.endsWith(suffix)); assert(i >= 0); const request = pending.splice(i, 1)[0]; (fail ? request.reject : request.resolve)(value); }
  function result(id, stamp = "one") { return {entry: entry(id, "verified_snapshot", stamp), native_report: {accepted_slots: 1, planned_slots: 2, accepted_source_scenarios: 2, planned_source_scenarios: 4, slots: [{cell: id, repeat: 2, accepted: false, attempts: [{status: "interrupted"}, {status: "failed"}]}]}}; }
  return {context, $, pending, clicks, choose, reply, result};
}
let checks = 0;
{
  const h = harness(), a = h.choose('a'), b = h.choose('b'); h.reply('b', 'report', h.result('b')); await b; h.reply('a', 'report', h.result('a')); await a;
  assert.match(h.$('durable-native-roster').children[0].textContent, /^b · repetition 2/);
  assert.equal(h.$('durable-results').hidden, false); checks++;
}
{
  const h = harness(), a = h.choose('a'); h.context.durableSelected.checked_at = 'two'; h.reply('a', 'report', h.result('a')); await a;
  assert.equal(h.$('durable-results').hidden, true); checks++;
}
{
  const h = harness(), a = h.choose('a'); h.reply('a', 'report', h.result('a', 'different-worker')); await a;
  assert.equal(h.$('durable-results').hidden, true); checks++;
}
{
  const h = harness(), a = h.choose('a'), b = h.choose('b'); h.reply('b', 'report', h.result('b')); await b; h.reply('a', 'report', new Error('stale error'), true); await a;
  assert.equal(h.$('durable-results').hidden, false); assert.equal(h.$('durable-notice').textContent, ''); checks++;
}
{
  const h = harness(), a = h.choose('a'); h.reply('a', 'report', h.result('a')); await a;
  const download = vm.runInContext('downloadDurable("report.md")', h.context); const b = h.choose('b'); h.reply('b', 'report', h.result('b')); await b; h.reply('a', 'report.md', {}); await download;
  assert.deepEqual(h.clicks, []); checks++;
}
{
  const h = harness(), a = h.choose('a'); h.reply('a', 'report', h.result('a')); await a;
  const download = vm.runInContext('downloadDurable("report.md")', h.context); h.reply('a', 'report.md', new Error('snapshot changed'), true); await download;
  assert.equal(h.$('durable-results').hidden, true); assert.equal(h.$('durable-notice').textContent, 'snapshot changed'); checks++;
}
{
  const h = harness(), a = h.choose('a'); h.reply('a', 'report', h.result('a')); await a;
  const download = vm.runInContext('downloadDurable("report.md")', h.context); await vm.runInContext('displayDurableReport()', h.context); h.reply('a', 'report.md', {}); await download;
  assert.deepEqual(h.clicks, ['report.md']); checks++;
}
{
  const h = harness(), a = h.choose('a'); h.reply('a', 'report', h.result('a')); await a;
  const download = vm.runInContext('downloadDurable("report.json")', h.context); h.context.active = {request: {entry_id: 'a'}}; h.reply('a', 'report.json', {}); await download;
  assert.deepEqual(h.clicks, []); checks++;
}
process.stdout.write(JSON.stringify({passed: true, checks}));
