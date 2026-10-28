// A saved study creates a fresh repeat draft and moves focus only after unlocking it.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const app = fs.readFileSync("experiments/gui/static/app.js", "utf8");
function section(start, end) { const a = app.indexOf(start), b = app.indexOf(end, a); assert(a >= 0 && b > a); return app.slice(a, b); }
let checks = 0;
function harness() {
  const nodes = new Map(), requests = [], focused = [], notices = [];
  const $ = id => { if (!nodes.has(id)) nodes.set(id, {value: "", disabled: false, focus() { if (!this.disabled) focused.push(id); }}); return nodes.get(id); };
  const context = vm.createContext({$, active: null, campaignPending: false, libraryPending: false, m3Pending: false, durablePending: false,
    campaignDraftRevision: 1, campaignCells: [{id: "unsaved-old", configuration_id: "old"}], campaignConfiguration: {id: "previous-campaign"},
    campaignControls() { $("campaign-repeats").disabled = context.campaignPending; },
    campaignNotice(message) { notices.push(message); }, invalidateCampaign() { context.campaignDraftRevision++; context.campaignConfiguration = null; }, renderCampaignCells() {},
    api(path) { return new Promise((resolve, reject) => requests.push({path, resolve, reject})); },
  });
  $("campaign-study-choice").value = "own-frozen-study";
  vm.runInContext(section("async function useCampaignStudy()", "async function loadGraphValues(") + section("function campaignCellSnapshot(", "async function captureCampaignCell("), context);
  const run = () => vm.runInContext("useCampaignStudy()", context);
  return {context, requests, focused, notices, $, run};
}
const saved = () => ({id: "own-frozen-study", ready: false, config: {sources: [{id: "second"}, {id: "first"}], scenarios: ["fasting"], timeout_seconds: 120, source_timeout_seconds: 240}});
{
  const h = harness(), operation = h.run(); assert.equal(h.requests[0].path, "configurations/own-frozen-study");
  assert.equal(h.$("campaign-repeats").disabled, true); assert.equal(h.focused.length, 0);
  h.requests[0].resolve(saved()); await operation;
  assert.equal(h.context.campaignPending, false); assert.equal(h.$("campaign-repeats").disabled, false);
  assert.deepEqual(h.focused, ["campaign-repeats"]);
  assert.equal(h.context.campaignConfiguration, null); assert.equal(h.context.campaignCells.length, 1);
  assert.equal(h.context.campaignCells[0].configuration_id, "own-frozen-study");
  assert.deepEqual([...h.context.campaignCells[0].source_ids], ["second", "first"]); checks++;
}
{
  const h = harness(), original = h.context.campaignCells, operation = h.run(); h.context.campaignDraftRevision++;
  h.requests[0].resolve(saved()); await operation;
  assert.equal(h.context.campaignCells, original); assert.equal(h.focused.length, 0); assert.equal(h.context.campaignPending, false); checks++;
}
{
  const h = harness(), original = h.context.campaignCells, operation = h.run(); h.requests[0].reject(new Error("Frozen source changed")); await operation;
  assert.equal(h.context.campaignCells, original); assert.equal(h.context.campaignPending, false); assert.equal(h.focused.length, 0);
  assert(h.notices.includes("Frozen source changed")); checks++;
}
{
  for (const key of ["active", "campaignPending", "libraryPending", "m3Pending", "durablePending"]) {
    const h = harness(); h.context[key] = key === "active" ? {state: "running"} : true; await h.run(); assert.equal(h.requests.length, 0, key);
  }
  const h = harness(); h.$("campaign-study-choice").value = ""; await h.run(); assert.equal(h.requests.length, 0); checks++;
}
{
  const h = harness(), original = h.context.campaignCells, operation = h.run(); h.requests[0].resolve({id: "own-frozen-study"}); await operation;
  assert.equal(h.context.campaignCells, original); assert.equal(h.context.campaignPending, false); assert.equal(h.focused.length, 0);
  assert(h.notices.some(message => message.includes("incomplete"))); checks++;
}
console.log(JSON.stringify({passed: true, checks, scope: "new repeat draft from owned frozen configuration; post-unlock focus, preserved source order, stale draft/error/busy guards"}));
