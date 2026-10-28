// Exercise the shipped unified-results UI with focus loss on moved DOM nodes.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("experiments/gui/static/ux.js", "utf8");
const app = fs.readFileSync("experiments/gui/static/app.js", "utf8");
let checks = 0;
function harness() {
  const nodes = new Map(), calls = [], document = {activeElement: null};
  function element(name = "div") {
    const events = new Map();
    return {name, tagName: name.toUpperCase(), id: "", dataset: {}, children: [], parentElement: null, textContent: "", open: false, mutations: 0,
      contains(node) { return node === this || this.children.some(child => child.contains(node)); },
      remove() {
        if (!this.parentElement) return;
        if (this.contains(document.activeElement)) document.activeElement = document.body;
        const parent = this.parentElement; parent.children.splice(parent.children.indexOf(this), 1); parent.mutations++; this.parentElement = null;
      },
      insertBefore(node, next) {
        node.remove(); const index = next === null ? this.children.length : this.children.indexOf(next); assert(index >= 0);
        this.children.splice(index, 0, node); node.parentElement = this; this.mutations++;
      },
      append(...items) { for (const item of items) this.insertBefore(item, null); },
      replaceChildren(...items) { for (const node of [...this.children]) node.remove(); this.append(...items); this.mutations++; },
      querySelectorAll(selector) {
        const all = this.children.flatMap(child => [child, ...child.querySelectorAll("*")]);
        return selector === "*" ? all : all.filter(child => child.dataset.pollingKey !== undefined);
      },
      addEventListener(name, fn) { events.set(name, fn); }, click() { events.get("click")?.(); }, focus() { document.activeElement = this; },
    };
  }
  document.body = element("body"); document.activeElement = document.body; document.createElement = element;
  const node = (id) => { if (!nodes.has(id)) { const target = element(); target.id = id; document.body.append(target); nodes.set(id, target); } return nodes.get(id); };
  document.getElementById = node;
  const context = vm.createContext({document, Date, $: node, librarySelected: {id: "archive-a"}, status(target, text) { target.textContent = text; }});
  vm.runInContext(source, context);
  const run = (code) => vm.runInContext(code, context);
  function refresh(data, callback = item => calls.push(item)) { context.data = data; context.open = callback; run("uxRefreshResults(data, open)"); }
  return {context, document, node, calls, run, refresh};
}
const job = (id, state = "completed", operation = "run") => ({id, state, operation, created_at: "2026-10-06T09:00:00Z", verification: "not_requested"});
const data = () => ({jobs: [job("first"), job("failed", "failed"), job("cancelled", "cancelled")],
  m3: [{id: "forecast-a", task: "m3-forecast", execution_state: "failed", verification: "not_requested"}, {id: "compare-a", task: "m3-compare", execution_state: "cancelled", verification: "recorded_verification"}],
  campaigns: [{id: "campaign-a", status: "failed", accepted_slots: 0, planned_slots: 2, verification: "not_requested"}],
  durable: [{id: "package-a", path: "saved-package-a", availability: "available", integrity: "verified_snapshot", reconstruction: "not_requested"}]});
{
  const h = harness(), input = data();
  for (const operation of ["check", "install", "reconstruct", "m3_fixture", "m3_check", "m3_run", "m3_reconstruct", "campaign_run", "library_index", "library_verify", "durable_export", "durable_forensic"]) input.jobs.push(job(operation, "completed", operation));
  h.context.data = input; const items = JSON.parse(h.run("JSON.stringify(uxResultItems(data))"));
  assert.deepEqual(items.map(item => item.kind + ":" + item.id), ["study:first", "study:failed", "study:cancelled", "m3:forecast-a", "m3:compare-a", "campaign:campaign-a", "durable:package-a"]);
  assert.equal(items.find(item => item.id === "failed").state, "failed"); assert.equal(items.find(item => item.id === "cancelled").state, "cancelled"); checks++;
}
{
  const h = harness(); h.context.data = data(); const items = JSON.parse(h.run("JSON.stringify(uxResultItems(data))"));
  assert(items.filter(item => item.kind !== "durable").every(item => item.detail.startsWith("Own workspace")));
  assert(items.find(item => item.kind === "durable").detail.startsWith("Read-only package"));
  assert(items.find(item => item.id === "forecast-a").label.startsWith("Glucose forecast")); assert(items.find(item => item.id === "compare-a").label.startsWith("Glucose model comparison")); checks++;
}
{
  const h = harness(), input = data(); h.refresh(input); const target = h.node("own-results-list"), button = target.children[0], mutations = target.mutations; button.focus();
  const newestCalls = []; h.refresh(structuredClone(input), item => newestCalls.push(item));
  assert.equal(target.children[0], button); assert.equal(target.mutations, mutations); assert.equal(h.document.activeElement, button);
  button.click(); assert.deepEqual(newestCalls.map(item => ({...item})), [{kind: "study", id: "first"}]); assert.equal(h.calls.length, 0, "An unchanged render still updates the opening callback"); checks++;
}
{
  const h = harness(), input = data(); h.refresh(input); const target = h.node("own-results-list"), focused = target.children[1]; focused.focus();
  input.jobs = [input.jobs[1], input.jobs[2], input.jobs[0]]; input.jobs[0].verification = "native_reader_verified"; h.refresh(input);
  assert.equal(target.children[0], focused, "Keyed row is retained while moved"); assert.equal(h.document.activeElement, focused, "Focus is restored after insertBefore removes it");
  assert(focused.children[1].textContent.includes("snapshot checked")); focused.click(); assert.equal(h.calls[0].id, "failed"); checks++;
}
{
  const h = harness(), input = {jobs: [job("first"), job("second"), job("third")]}; h.refresh(input); const target = h.node("own-results-list"); target.children[1].focus();
  input.jobs.splice(1, 1); h.refresh(input); assert.equal(h.document.activeElement.dataset.resultKey, "study:third", "Removed row chooses its nearest remaining position");
  h.refresh({}); assert.equal(target.children.length, 1); assert.equal(h.document.activeElement, target); assert.equal(target.tabIndex, -1); checks++;
}
{
  const h = harness(), input = data(); h.refresh(input); const search = h.node("library-search"); search.focus();
  input.jobs.reverse(); input.jobs[0].state = "failed"; h.refresh(input); assert.equal(h.document.activeElement, search, "Background results never steal focus from filters or other controls"); checks++;
}
{
  const h = harness(), input = {jobs: [job("shared-id")], m3: [{id: "shared-id", task: "m3-forecast", execution_state: "completed"}]}; h.refresh(input);
  const target = h.node("own-results-list"); assert.equal(target.children.length, 2); target.children[0].click(); target.children[1].click();
  assert.deepEqual(h.calls.map(item => ({...item})), [{kind: "study", id: "shared-id"}, {kind: "m3", id: "shared-id"}], "Each workflow keeps its route authority even when opaque IDs happen to match");
  input.jobs = [job("latest-id")]; h.refresh(input); target.children[0].click(); assert.equal(h.calls[2].id, "latest-id"); checks++;
}
{
  const h = harness(); h.refresh({}); const target = h.node("own-results-list"), empty = target.children[0], mutations = target.mutations;
  h.refresh({jobs: [job("check-only", "completed", "check")]}); assert.equal(target.children[0], empty); assert.equal(target.mutations, mutations); checks++;
}
function section(start, end) { const a = app.indexOf(start), b = app.indexOf(end, a); assert(a >= 0 && b > a); return app.slice(a, b); }
{
  const h = harness(); h.run(section("// Polling must retain", "// End retained polling helpers.") + section("function renderLibraryDigests(", "function renderLibraryDetail(") + section("function m3Row(", "function m3Value("));
  h.run("renderLibraryDigests(undefined)"); const target = h.node("library-digest-diagnostics"), mutations = target.mutations;
  assert.equal(target.children.length, 0); h.run("renderLibraryDigests(undefined)"); assert.equal(target.mutations, mutations); checks++;
}
{
  const h = harness(); h.run(section("// Polling must retain", "// End retained polling helpers.") + section("function renderLibraryDigests(", "function renderLibraryDetail(") + section("function m3Row(", "function m3Value("));
  const manifests = [{manifest: "manifest.json", status: "matched", checked_files: 2, schema: "synthetic", mismatches: [], errors: []}];
  h.context.checks = {status: "matched", checked_files: 2, manifests}; h.run("renderLibraryDigests(checks)");
  const target = h.node("library-digest-diagnostics"), row = target.children[0], summary = row.children[0]; row.open = true; summary.focus();
  h.context.checks = structuredClone(h.context.checks); h.run("renderLibraryDigests(checks)");
  assert.equal(target.children[0], row); assert.equal(row.open, true); assert.equal(h.document.activeElement, summary); checks++;
  h.context.checks.manifests[0].status = "mismatch"; h.run("renderLibraryDigests(checks)");
  const updated = target.children[0]; assert.notEqual(updated, row); assert.equal(updated.open, true); assert.equal(h.document.activeElement, updated.children[0]); checks++;
}
{
  const h = harness(), input = data();
  input.m3[0].updated_at = "2026-10-17T10:00:00Z"; input.campaigns[0].created_at = "2026-10-16T10:00:00Z";
  input.durable[0].created_at = "2026-10-15T10:00:00Z";
  input.jobs.push({...job("analysis", "completed", "m3_reconstruct"), request: {entry_id: "compare-a"}, finished_at: "2026-10-18T10:00:00Z"});
  h.context.data = input; const items = JSON.parse(h.run("JSON.stringify(uxResultItems(data))"));
  assert.deepEqual(items.slice(0, 4).map(item => item.id), ["compare-a", "forecast-a", "campaign-a", "package-a"]);
  assert(items.every(item => !item.label.includes("Time not recorded")));
  h.refresh(input); const button = h.node("own-results-list").children[1]; button.focus();
  input.m3[0].updated_at = "2026-10-19T10:00:00Z"; h.refresh(input);
  assert.equal(h.node("own-results-list").children[0], button); assert.equal(h.document.activeElement, button); checks++;
}
{
  const h = harness(); h.context.data = {m3: [{id: "legacy", task: "m3-compare", created_at: "invalid"}]};
  assert.match(h.run("uxResultItems(data)[0].label"), /Time not recorded/); checks++;
}
{
  const h = harness(), input = data();
  input.jobs[0].verified_at = "2026-10-17T12:00:00Z";
  input.jobs.push({...job("reader", "failed", "reconstruct"), archive_job: "failed", finished_at: "2026-10-18T12:00:00Z"});
  input.jobs.push({...job("campaign-reader", "completed", "campaign_reconstruct"), request: {campaign_id: "campaign-a"}, finished_at: "2026-10-19T12:00:00Z"});
  input.durable[0].checked_at = "2026-10-20T12:00:00Z";
  h.context.data = input;
  assert.deepEqual(JSON.parse(h.run("JSON.stringify(uxResultItems(data).slice(0,4).map(item=>item.id))")), ["package-a", "campaign-a", "failed", "first"]); checks++;
}
{
  const h = harness(), input = {
    sampling: [{id: "sample", display_name: "Low / censored control", state: "completed", report_completeness: "incomplete", verification: "not_requested"}],
    observations: [{id: "paired", display_name: "My <paired> comparison", state: "completed", report_completeness: "complete", verification: "native_reader_verified"}],
  };
  h.refresh(input); const target = h.node("own-results-list");
  assert.match(target.children[0].children[0].textContent, /Low \/ censored control · Fewer measurement times/);
  assert.match(target.children[0].children[1].textContent, /Analysis finished · results incomplete · Saved report not checked/);
  assert.match(target.children[1].children[0].textContent, /My <paired> comparison · Paired meal-test analysis/);
  assert.match(target.children[1].children[1].textContent, /results complete · Saved report checked/);
  assert.equal(target.children[1].children[0].children.length, 0, "Custom names remain text, never HTML");
  target.children[1].click(); assert.equal(h.calls[0].kind, "observations"); checks++;
}
{
  const h = harness(); h.context.data = {observations: [{id: "old", state: "completed"}], sampling: [{id: "unknown", state: "other"}]};
  const items = JSON.parse(h.run("JSON.stringify(uxResultItems(data))"));
  assert.match(items[0].label, /^Fewer measurement times/);
  assert.match(items[0].detail, /Execution status unavailable · Saved report check unavailable/);
  assert.match(items[1].label, /^Paired meal-test analysis/);
  assert.match(items[1].detail, /result completeness unknown/); checks++;
}
{
  const h = harness();
  const states = ["queued", "running", "cancelling", "cancelled", "interrupted", "interrupted_owner_unavailable", "unsealed_or_unavailable", "failed"];
  const labels = states.map(state => h.run(`mmttExecutionLabel({state: ${JSON.stringify(state)}})`));
  assert.equal(new Set(labels).size, states.length); assert(labels.every(label => !label.includes("finished")));
  const verification = ["native_reader_verified", "recorded_verification", "not_requested", "verifying", "changed_since_verification", "verification_failed", "unknown"];
  assert.equal(new Set(verification.map(value => h.run(`mmttVerificationLabel(${JSON.stringify(value)})`))).size, verification.length);
  checks++;
}
{
  const h = harness();
  h.context.job = {state:"running", phase:{schema:"opent1d.packaged-admission/1",phase:"auditing",operation:"run"}};
  assert.equal(h.run("uxPhaseDetail(job)"), "Checking installed components…");
  h.context.job.phase.phase = "executing";
  assert.equal(h.run("uxPhaseDetail(job)"), "Running analysis…");
  h.context.job.phase.operation = "reconstruct";
  assert.equal(h.run("uxPhaseDetail(job)"), "Checking saved analysis…"); checks++;
  for (const state of ["queued","cancelling","failed","completed"]) {
    h.context.job.state = state; assert.equal(h.run("uxPhaseDetail(job)"), null);
  } checks++;
  h.context.job.state = "running"; h.context.job.phase.schema = "unknown";
  assert.equal(h.run("uxPhaseDetail(job)"), null);
  delete h.context.job.phase;
  assert.equal(h.run("uxPhaseDetail(job)"), null); checks++;
}
console.log(JSON.stringify({passed: true, checks, scope: "unified owned results and read-only packages, passive operation exclusions, stable DOM, reordering/removal focus and retained digest disclosures"}));
