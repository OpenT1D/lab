// Exercise real presentation functions with observed timestamps and shared-lane states.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const app = fs.readFileSync("experiments/gui/static/app.js", "utf8");
const workspace = fs.readFileSync("experiments/gui/static/workspace.js", "utf8");
function section(source, start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert(a >= 0 && b > a); return source.slice(a, b);
}
const nodes = new Map(), focus = [], scroll = [], routes = [];
const $ = id => {
  if (!nodes.has(id)) nodes.set(id, {hidden: false, disabled: false, textContent: "", value: "", attributes: {},
    focus(options) { focus.push({id, options}); }, setCustomValidity(message) { this.validationMessage = message; },
    scrollIntoView(options) { scroll.push({id, options}); },
    setAttribute(key, value) { this.attributes[key] = value; }, removeAttribute(key) { delete this.attributes[key]; },
    classList: {remove() {}, add() {}},
  });
  return nodes.get(id);
};
const context = vm.createContext({$, Date, active: null, libraryPending: false, libraryVerifyingID: null,
  librarySelected: {task: "m4-study-secure", can_verify: true, can_view_report: false},
  libraryShown: null, libraryReportTasks: new Set(["m4-study-secure"]), librarySelection: 0,
  activeStates: new Set(["queued", "running", "cancelling"]),
  status(node, label) { node.textContent = label; },
  clearLibraryResults() {}, libraryNotice() {}, renderLibraryList() {}, renderLibraryDetail() {}, displayLibraryReport() {},
  libraryRevision() { return "revision"; },
  workspaceNavigate(view) { routes.push(view); },
});
vm.runInContext(fs.readFileSync("experiments/gui/static/ux.js", "utf8"), context);
vm.runInContext(section(workspace, "function workspaceElapsed(", "function updateWorkspaceSummary(")
  + section(workspace, "function workspaceJobView(", "function workspaceElapsed(")
  + section(app, "function validateSourceID(", "function sourceCard(")
  + section(app, "function updateActivity(", "function renderHistory(")
  + section(app, "function libraryBusy(", "function clearLibraryResults(")
  + section(app, "function selectLibrary(", "function renderLibraryList("), context);
const run = code => vm.runInContext(code, context);
let checks = 0;
assert.equal(run('workspaceElapsed({state:"running", started_at:"2026-10-13T09:00:00Z"}, Date.parse("2026-10-13T09:08:56Z"))'), "Elapsed computer time: 8m 56s"); checks++;
assert.equal(run('workspaceElapsed({state:"completed", started_at:"2026-10-13T09:00:00Z", finished_at:"2026-10-13T09:08:56Z"}, Date.parse("2026-10-14T09:00:00Z"))'), "Elapsed computer time: 8m 56s"); checks++;
for (const input of [{}, {state:"completed", started_at:"2026-10-13T09:00:00Z"}, {state:"running", started_at:"wrong"}, {state:"running", started_at:"2027-01-01"}]) {
  context.job = input; assert.equal(run("workspaceElapsed(job, Date.parse('2026-10-13'))"), "Elapsed computer time unavailable");
} checks++;
context.active = {operation: "run", state: "running", id: "job-test", exit_code: null, started_at: new Date().toISOString()};
run("updateActivity(active); libraryControls()");
assert.equal($("archive-verify").disabled, true); assert.equal($("archive-verify-reason").hidden, false);
assert($("archive-verify-reason").textContent.includes("Only one operation"));
assert.equal($("archive-view-operation").hidden, false); assert($("activity-elapsed").textContent.includes("per-model / condition progress is not reported")); checks++;
context.active = null; run("libraryControls()"); assert.equal($("archive-verify").disabled, false); assert.equal($("archive-verify-reason").hidden, true); assert.equal($("archive-view-operation").hidden, true); checks++;
context.job = {id:"job-archive", operation:"library_verify", state:"completed", exit_code:0};
run("updateActivity(job)"); assert.equal($("activity-badge").textContent, "Idle"); assert($("activity-detail").textContent.includes("Open Results")); assert(!$("activity-detail").textContent.includes("below")); checks++;
for (const value of ["INVALID MODEL", "1model", "model with spaces", "a".repeat(65), ""]) { const field = $("field"); field.value = value; run("validateSourceID($('field'))"); assert(field.validationMessage.includes("Source ID")); assert.equal(field.attributes["aria-invalid"], "true"); }
for (const value of ["dalla_man", "model-1", "a".repeat(64)]) { const field = $("field"); field.value = value; run("validateSourceID($('field'))"); assert.equal(field.validationMessage, ""); assert.equal(field.attributes["aria-invalid"], undefined); } checks++;
context.entry = {metadata:{recorded_status:"failed", native_report_status:"interrupted"}};
assert.equal(run("libraryRecordedStatus(entry)"), "interrupted"); run("selectLibrary(entry)"); assert.equal(focus.at(-1).id, "library-detail-title"); assert.equal(focus.at(-1).options.preventScroll, false); assert.equal(scroll.at(-1).id, "library-detail-title"); assert.equal(scroll.at(-1).options.block, "start"); checks++;
console.log(JSON.stringify({passed:true, checks}));
