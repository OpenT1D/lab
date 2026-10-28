// Navigation must preserve forms, checked state and native report visibility.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("experiments/gui/static/workspace.js", "utf8");
const ux = fs.readFileSync("experiments/gui/static/ux.js", "utf8");
let checks = 0;
function harness(hash = "") {
  const nodes = new Map(), events = new Map(), documentEvents = new Map(), pushes = [], focus = [];
  const node = (id) => {
    if (!nodes.has(id)) {
      const attrs = new Map(), listeners = new Map(), classes = new Set();
      nodes.set(id, {id, hidden: false, textContent: "", dataset: {}, value: "",
        classList: {toggle(name, value) { if (value) classes.add(name); else classes.delete(name); }, contains(name) { return classes.has(name); }},
        setAttribute(name, value) { attrs.set(name, value); }, removeAttribute(name) { attrs.delete(name); }, getAttribute(name) { return attrs.get(name); },
        addEventListener(name, callback) { listeners.set(name, callback); }, fire(name, event = {}) { return listeners.get(name)?.(event); },
        focus() { focus.push(id); },
        scrollTo(options) { this.scrolled = options; },
        scrollIntoView(options) { this.scrolled = options; },
      });
    }
    return nodes.get(id);
  };
  const go = node("overview-m3-card"); go.dataset.workspaceGo = "m3";
  const window = {innerWidth: 1440, location: {hash}, history: {pushState(_state, _title, target) { pushes.push(target); window.location.hash = target; }},
    addEventListener(name, callback) { events.set(name, callback); }, scrollTo() {},
  };
  const document = {getElementById: node, querySelectorAll: () => [go], body: {dataset: {}}, title: "", addEventListener(name, callback) { documentEvents.set(name, callback); }};
  const context = vm.createContext({document, window}); vm.runInContext(ux, context); vm.runInContext(source, context);
  const run = (code) => vm.runInContext(code, context);
  return {node, go, window, document, pushes, focus, events, documentEvents, run};
}
{
  const h = harness();
  assert.equal(h.document.body.dataset.workspaceView, "overview");
  assert.equal(h.node("m4-panel").hidden, true);
  assert.equal(h.node("open-overview").getAttribute("aria-current"), "page");
  assert.deepEqual(h.focus, []); assert.deepEqual(h.pushes, []); checks++;
}
{
  const h = harness("#m3");
  assert.equal(h.node("m3-panel").hidden, false); assert.equal(h.node("overview-panel").hidden, true);
  assert.equal(h.document.title, "OpenT1D · Glucose forecasts");
  assert.equal(h.node("workspace-skip").href, "#m3-title"); checks++;
}
{
  for (const route of ["#unknown", "#__proto__", "#toString"]) {
    const h = harness(route); assert.equal(h.document.body.dataset.workspaceView, "overview");
  }
  checks++;
}
{
  const h = harness("#m4"); h.node("source-input").value = "researcher-model.py";
  h.node("results").hidden = false; h.node("run-study").disabled = false;
  h.run('workspaceNavigate("campaigns")'); h.run('workspaceNavigate("m4")');
  assert.equal(h.node("source-input").value, "researcher-model.py");
  assert.equal(h.node("results").hidden, false); assert.equal(h.node("run-study").disabled, false);
  assert.equal(h.node("open-campaigns").getAttribute("aria-current"), undefined);
  assert.equal(h.node("new-study").getAttribute("aria-current"), "page");
  assert.deepEqual(h.focus, ["campaigns-title", "m4-title"]); checks++;
}
{
  const h = harness(); h.go.fire("click"); assert.equal(h.document.body.dataset.workspaceView, "m3");
  h.window.location.hash = "#library"; h.events.get("popstate")();
  assert.equal(h.node("archive-library").hidden, false); assert.equal(h.node("m3-panel").hidden, true);
  assert.deepEqual(h.pushes, ["#m3"]);
  h.window.location.hash = "#durable"; h.events.get("hashchange")();
  assert.equal(h.node("durable-panel").hidden, false); checks++;
}
{
  const h = harness("#m3"); let prevented = false;
  h.node("workspace-skip").fire("click", {preventDefault() { prevented = true; }});
  assert.equal(prevented, true); assert.deepEqual(h.focus, ["m3-title"]);
  assert.deepEqual(h.pushes, []); checks++;
}
{
  const h = harness();
  for (const [operation, expected] of [["run", "m4"], ["m3_run", "m3"], ["campaign_resume", "campaigns"], ["library_verify", "library"], ["durable_reconstruct", "durable"]]) {
    assert.equal(h.run(`workspaceJobView({operation: ${JSON.stringify(operation)}})`), expected);
  }
  checks++;
}
{
  const h = harness(); h.run('updateWorkspaceSummary({jobs: [{operation: "m3_run", state: "running"}]})');
  assert.equal(h.node("workspace-operation").hidden, false);
  h.run('workspaceNavigate("library")');
  assert.equal(h.node("workspace-operation").hidden, false);
  h.node("workspace-operation-open").fire("click"); assert.equal(h.document.body.dataset.workspaceView, "m3");
  h.run('updateWorkspaceSummary({jobs: [{operation: "m3_run", state: "cancelling"}]})');
  assert(h.node("workspace-operation-detail").textContent.includes("Stopping owned processes"));
  h.run('updateWorkspaceSummary({jobs: [{operation: "m3_run", state: "failed"}]})');
  assert.equal(h.node("workspace-operation").hidden, false);
  assert(h.node("workspace-operation-title").textContent.includes("failed"));
  checks++;
}
{
  const h = harness(); h.node("workspace-more").open = true;
  h.run('workspaceNavigate("campaigns")');
  assert.equal(h.node("workspace-more").open, false);
  const outer = {tagName: "DETAILS", open: false, parentElement: null};
  const inner = {tagName: "DETAILS", open: false, parentElement: outer};
  h.documentEvents.get("invalid")({target: {parentElement: inner}});
  assert.equal(inner.open, true); assert.equal(outer.open, true); checks++;
}

{
  const h = harness();
  h.run('updateWorkspaceSummary({jobs: [{id: "setup", operation: "library_index", state: "running"}]})');
  assert(h.node("workspace-operation-title").textContent.includes("Reading archive metadata"));
  assert(!h.node("workspace-operation-detail").textContent.includes("experiment is running"));
  h.run('updateWorkspaceSummary({jobs: [{id: "setup", operation: "library_index", state: "completed"}]})');
  assert.equal(h.node("workspace-operation").hidden, false);
  assert(h.node("workspace-operation-title").textContent.includes("completed")); checks++;
}
for (const [prefix, view, short, refresh, select] of [
  ["observation", "observations", "obs", "refreshObservations", "selectObservationID"],
  ["sampling", "sampling", "sam", "refreshSampling", "selectSamplingID"],
]) {
  const h = harness("#library");
  h.run(`var refreshed = 0, selected = null; async function ${refresh}() { refreshed++; } function ${select}(id) { selected = id; }`);
  const active = {id: "analysis", operation: prefix + "_run", state: "running", [prefix + "_entry_id"]: "saved-entry"};
  h.run(`updateWorkspaceSummary({jobs: [${JSON.stringify(active)}]})`);
  assert.equal(h.node("workspace-operation-open").textContent, "View progress");
  await h.node("workspace-operation-open").fire("click");
  assert.equal(h.document.body.dataset.workspaceView, view);
  assert.equal(h.focus.at(-1), short + "-cancel");
  assert.equal(h.node(short + "-cancel").tabIndex, undefined, "Opening progress preserves normal keyboard access to cancellation");
  assert.equal(h.run("refreshed"), 0);
  const finished = {...active, state: "failed", result: {observation_entry: {state: "completed", report_completeness: "incomplete"}}};
  h.run(`updateWorkspaceSummary({jobs: [${JSON.stringify(finished)}]})`);
  assert.equal(h.node("workspace-operation-title").textContent, "Analysis finished · results incomplete");
  assert.equal(h.node("workspace-operation-open").textContent, "View result");
  assert(h.node("workspace-operation-detail").textContent.includes("does not mean no change"));
  h.run('workspaceNavigate("library")');
  await h.node("workspace-operation-open").fire("click");
  assert.equal(h.run("refreshed"), 1); assert.equal(h.run("selected"), "saved-entry");
  assert.equal(h.focus.at(-1), short + "-result-title");
  assert.equal(h.node(short + "-result-title").scrolled.block, "start");
  h.run(`updateWorkspaceSummary({jobs: [${JSON.stringify({...active, state: "failed"})}]})`);
  assert.match(h.node("workspace-operation-title").textContent, /failed/);
  assert(!h.node("workspace-operation-title").textContent.includes("Analysis finished"));
  h.run(`updateWorkspaceSummary({jobs: [${JSON.stringify({...active, state: "cancelled", result: {observation_entry: {state: "interrupted", report_completeness: "incomplete"}}})}]})`);
  assert.match(h.node("workspace-operation-title").textContent, /cancelled/);
  assert(!h.node("workspace-operation-detail").textContent.includes("does not mean no change"));
  h.node(short + "-cancel").disabled = true;
  h.run(`updateWorkspaceSummary({jobs: [${JSON.stringify({...active, state: "cancelling"})}]})`);
  await h.node("workspace-operation-open").fire("click");
  assert.equal(h.focus.at(-1), "workspace-operation-title", "A disabled cancellation button cannot take focus, so keep progress reachable instead");
  checks++;
}
{
  const h = harness(); h.node("obs-plan-form").tagName = "FORM";
  h.run('updateWorkspaceSummary({jobs: [{id: "freeze", operation: "observation_freeze", state: "running"}]})');
  h.run('updateWorkspaceSummary({jobs: [{id: "freeze", operation: "observation_freeze", state: "completed"}]})');
  assert.equal(h.node("workspace-operation-open").textContent, "View setup");
  assert(h.node("workspace-operation-detail").textContent.includes("prepared setup"));
  await h.node("workspace-operation-open").fire("click");
  assert.equal(h.focus.at(-1), "obs-plan-form"); assert.equal(h.node("obs-plan-form").tabIndex, -1);
  checks++;
}
{
  const h = harness();
  h.run('var releaseRefresh, releaseReport, selected = null; function refreshSampling() { return new Promise(resolve => { releaseRefresh = resolve; }); } function selectSamplingID(id) { selected = id; return new Promise(resolve => { releaseReport = resolve; }); }');
  h.run('updateWorkspaceSummary({jobs: [{id: "run", operation: "sampling_run", state: "running"}]})');
  h.run('updateWorkspaceSummary({jobs: [{id: "run", operation: "sampling_run", state: "completed", sampling_entry_id: "saved"}]})');
  const opening = h.node("workspace-operation-open").fire("click");
  h.run('workspaceNavigate("library"); releaseRefresh()'); await opening;
  assert.equal(h.document.body.dataset.workspaceView, "library"); assert.equal(h.focus.at(-1), "library-title");
  assert.equal(h.run("selected"), null, "A late refresh never redirects a user who has moved on"); checks++;
  const rendered=h.node("workspace-operation-open").fire("click");
  h.run("releaseRefresh()");await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.run("selected"),"saved");
  assert.notEqual(h.focus.at(-1),"sam-result-title","Do not scroll until the report has given the page its final height");
  h.run("releaseReport()");await rendered;
  assert.equal(h.focus.at(-1),"sam-result-title");
}
console.log(JSON.stringify({passed: true, checks, scope: "shipped workspace navigation, retained UI state, keyboard focus, history and cross-view operation visibility"}));
