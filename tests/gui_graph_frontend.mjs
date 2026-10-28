// Saved data, evidence scopes and digest/selection guards in shipped presentation code.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {webcrypto} from "node:crypto";

const ux = fs.readFileSync("experiments/gui/static/ux.js", "utf8");
const app = fs.readFileSync("experiments/gui/static/app.js", "utf8");
const loader = app.slice(app.indexOf("async function loadGraphValues("), app.indexOf('$("study-form").addEventListener'));
const nodes = new Map();
function element(name = "div") {
  return {tagName: name.toUpperCase(), children: [], dataset: {}, textContent: "", hidden: false,
    append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = items; this.textContent = ""; },
    focus() { document.activeElement = this; },
  };
}
const document = {activeElement: null, createElement: element,
  getElementById(id) { if (!nodes.has(id)) { const node = element(); node.id = id; nodes.set(id, node); } return nodes.get(id); },
};
let pending = [], rendered = [], checks = 0;
const context = vm.createContext({document, TextDecoder, Uint8Array, crypto: webcrypto, Blob,
  $: document.getElementById, selected: {id: "own-a"}, uxStudySnapshot: {id: "own-a", digest: "", verification: "native_reader_verified"}, uxGraphRequest: 0,
  librarySelected: null, libraryRevision: entry => JSON.stringify(entry),
  api(path) { return new Promise((resolve, reject) => pending.push({path, resolve, reject})); },
});
vm.runInContext(ux + loader, context);
const run = code => vm.runInContext(code, context);
const trajectory = () => ({times: [0, 5.25], glucose: [90.5, 112.125], insulin: [20, 35.1], cpeptide: [40, 65.5]});
function source(accepted = true) { return {accepted, curves: {fasting: {candidate: trajectory(), host_constant_basal: trajectory(), bc008_reference: trajectory()}}}; }
const report = {sources: {first: source(), second: source(), rejected: source(false)}};
context.report = report;
{
  const series = run("uxGraphSeries(report)");
  assert.equal(series.length, 4);
  assert.equal(series[0].data.times_min, report.sources.first.curves.fasting.candidate.times);
  assert.equal(series[0].data.glucose_mg_dl, report.sources.first.curves.fasting.candidate.glucose);
  run('uxRenderGraph("table", report)');
  const table = document.getElementById("table").children[0].children[1].children[0];
  assert.equal(table.children[2].children[1].children[1].textContent, "112.125");
  assert.equal(table.children[1].children[0].children[2].textContent, "Insulin (pmol/L)"); checks++;
}
{
  report.common_controls = {trajectories: {unmatched: {glucose_mg_dl: [999]}}};
  report.sources.second.curves.fasting.host_constant_basal.glucose[1] = 888;
  const series = run("uxGraphSeries(report)");
  assert.equal(series[2].data.glucose_mg_dl, report.sources.first.curves.fasting.host_constant_basal.glucose);
  assert.equal(series[2].data.glucose_mg_dl[1], 112.125); checks++;
  context.reordered = {...report, configuration: {sources: [{id: "second"}, {id: "first"}]}, scenarios: [{id: "fasting"}]};
  assert.equal(run("uxGraphSeries(reordered)")[2].data.glucose_mg_dl[1], 888);
}
{
  context.empty = {sources: {rejected: source(false)}};
  assert.equal(run("uxGraphSeries(empty)").length, 0);
  run('uxRenderGraph("empty", empty)'); assert(document.getElementById("empty").textContent.includes("No accepted")); checks++;
}
{
  for (const corrupt of [r => r.sources.first.curves.fasting.candidate.glucose.push(99), r => r.sources.first.curves.fasting.candidate.insulin[0] = NaN, r => delete r.sources.first.curves.fasting.bc008_reference]) {
    context.bad = structuredClone(report); corrupt(context.bad);
    assert.throws(() => run("uxGraphSeries(bad)"), /incomplete or incompatible/);
  }
  context.large = {sources: {first: source()}};
  for (const curve of Object.values(context.large.sources.first.curves.fasting)) for (const key of Object.keys(curve)) curve[key] = Array(17000).fill(1);
  assert.throws(() => run("uxGraphSeries(large)"), /too many/); checks++;
}
{
  const rows = run('uxEvidenceRows("m3", {evaluation: {contributing_people: 0, planned_people: 3}}, "native_reader_verified", "failed")');
  assert.equal(rows[0][1], "failed"); assert(rows[1][1].startsWith("0 / 3")); assert(rows[2][1].includes("quality are separate"));
  assert(run('uxEvidenceRows("m4", {passed: false}, "recorded_verification", "interrupted")')[2][1].includes("check again"));
  assert(!run('uxEvidenceRows("m4", {}, null, null)')[1][1].includes("undefined")); checks++;
  assert.equal(run('uxEvidenceRows("m4", {status: "complete", passed: true}, "native_reader_verified")')[0][1], "Not recorded separately in this report");
}
const bytes = new TextEncoder().encode(JSON.stringify(report));
const digest = [...new Uint8Array(await webcrypto.subtle.digest("SHA-256", bytes))].map(value => value.toString(16).padStart(2, "0")).join("");
context.uxRenderGraph = (id, saved) => rendered.push({id, saved});
context.uxStudySnapshot.digest = digest;
{
  const operation = run('loadGraphValues("study")');
  assert.equal(pending[0].path, "jobs/own-a/report.json"); pending.shift().resolve(new Blob([bytes])); await operation;
  assert.equal(rendered.length, 1); assert.equal(rendered[0].saved.sources.first.curves.fasting.candidate.glucose[1], 112.125); checks++;
}
{
  const operation = run('loadGraphValues("study")'); pending.shift().resolve(new Blob(["{}"])); await operation;
  assert.equal(rendered.length, 1); assert(document.getElementById("study-graph-values").textContent.includes("differ")); checks++;
}
{
  const operation = run('loadGraphValues("study")'); context.selected = {id: "own-b"}; pending.shift().resolve(new Blob([bytes])); await operation;
  assert.equal(rendered.length, 1);
  context.librarySelected = {id: "archive-a", artifacts_sha256: {"report.json": digest}};
  const archive = run('loadGraphValues("library")');
  assert.equal(pending[0].path, "library/entries/archive-a/artifacts/report.json");
  context.librarySelected.verification = "changed_since_verification"; pending.shift().resolve(new Blob([bytes])); await archive;
  assert.equal(rendered.length, 1); checks++;
}
{
  const details = element("details"); details.open = false;
  document.getElementById("m3-timeout").parentElement = details;
  run('uxRevealError("Invalid worker budget", document.getElementById("m3-notice"))');
  assert.equal(details.open, true); assert.equal(document.activeElement.id, "m3-notice"); checks++;
}
if (process.argv[2]) {
  context.retained = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const series = run("uxGraphSeries(retained)"); assert(series.length > 0);
  for (const item of series) assert(item.data.times_min.length > 0);
}
console.log(JSON.stringify({passed: true, checks, scope: "native graph keys, unchanged saved values and SVG control scope, bounded tables, separate evidence meanings, digest and selection guards"}));
