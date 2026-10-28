// Controlled replies exercise the shipped M3 frontend; native arithmetic stays in its readers.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync("experiments/gui/static/app.js", "utf8");
const start = source.indexOf("// M3 intake, saved native evidence"), end = source.indexOf('$("open-m3").addEventListener', start);
assert(start >= 0 && end > start);
let checks = 0;
function harness(mmttOnly = false) {
  const nodes = new Map(), pending = [], downloads = [];
  function element(name = "div") {
    return {name, textContent: "", children: [], dataset: {}, value: "", hidden: true, disabled: false, checked: false,
      replaceChildren() { this.children = []; }, append(...items) { this.children.push(...items); },
      addEventListener() {}, setAttribute(name, value) { this[name] = value; }, focus() {}, reportValidity() { return true; },
      querySelectorAll(selector) { const names = selector.split(",").map((part) => part.split(":")[0]); const items = this.children.flatMap((child) => [child, ...child.querySelectorAll(selector)]); return items.filter((child) => names.includes(child.name) && (!selector.includes(":checked") || child.checked)); },
      click() { downloads.push(this.download); },
    };
  }
  const $ = (id) => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  $("m3-task").value = "m3-compare"; $("m3-timeout").value = "120"; $("m3-root").value = "root"; $("m3-path").value = "comparison.json";
  const context = vm.createContext({$, Date, mmttOnly, active: null, selected: null, jobs: [], activeStates: new Set(["queued", "running", "cancelling"]), campaignPending: false, durablePending: false, durableSession: {can_export: true},
    document: {createElement: element}, URL: {createObjectURL: () => "blob:native", revokeObjectURL() {}}, setTimeout() {},
    updateActivity() {}, updateControls() {}, refresh: async () => {},
    status(node, label, kind = "neutral") { node.textContent = label; node.className = kind; },
    api(path, body) { return new Promise((resolve, reject) => pending.push({path, body: body === undefined ? undefined : JSON.parse(JSON.stringify(body)), resolve, reject})); },
  });
  vm.runInContext(source.slice(source.indexOf("// Polling must retain"), source.indexOf("// End retained polling helpers.")) + source.slice(start, end), context);
  const run = (code) => vm.runInContext(code, context), text = (node) => [node.textContent, ...node.children.map(text)].join(" ");
  function reply(path, value, fail = false) { const index = pending.findIndex((item) => item.path === path); assert(index >= 0, "Missing request " + path); const item = pending.splice(index, 1)[0]; (fail ? item.reject : item.resolve)(value); }
  function choose(id, verification = "native_reader_verified", task = "m3-compare") { context.entry = entry(id, verification, task); run("clearM3Results(); m3Selected = entry; renderM3Detail()"); return run("displayM3Report()"); }
  function input() { context.input = {id: "input-first", root_id: "root", path: "comparison.json", task: "m3-compare", planned_people: 2, planned_origins: {left: 801, right: 801}, candidates: [{id: "trend", reference: "invented trend", rights: "self-authored", training: {reference: "synthetic"}, source_sha256: "a", settings_sha256: "b"}, {id: "ridge", reference: "invented coefficients", rights: "self-authored", training: {reference: "synthetic"}, source_sha256: "c", settings_sha256: "d"}]}; run("m3Input = input; renderM3Candidates()"); }
  return {context, $, pending, downloads, run, reply, choose, input, text};
}
function entry(id, verification = "native_reader_verified", task = "m3-compare") { return {id, task, configuration_id: "config-" + id, execution_state: "failed", sealed: true, verification, complete: false, report_completeness: "incomplete", can_view_report: true, can_reconstruct: true, last_job: "job-" + id, snapshot_job: "snapshot-" + id, updated_at: "one", artifacts_sha256: {"report.json": "json", "report.md": "md"}}; }
function caseSummary(status = "failed") { return {execution_status: status, planned: 801, attempted: 321, not_attempted: 480, forecastable: 309, scored: 303, prediction_coverage: 309 / 801, score_coverage: 303 / 801, eligible_for_primary: false, ineligibility_reasons: ["execution_incomplete"], history_exclusions: {warmup: 12}, scoring_exclusions: {warmup: 12, target_outside: 6}, target_status_counts: {measured: 303}, execution: {error_type: "WorkerFailure", worker_error_type: "ValueError"}, candidate: {mae: 1}, persistence: {mae: 2}}; }
function nativeReport(task = "m3-compare") {
  const metrics = {mae: null, rmse: null, bias: null};
  if (task === "m3-forecast") return {schema: "opent1d.m3.researcher/1", predictor: {id: "trend", reference: "invented", rights: "self-authored", source: {sha256: "a"}, settings: {sha256: "b"}}, evaluation: {planned_people: 2, contributing_people: 0, complete_cohort: false, people: {left: caseSummary(), right: {...caseSummary("not_attempted"), attempted: 0, not_attempted: 801, forecastable: 0, scored: 0}}, equal_person_metrics: {candidate: metrics, persistence: metrics}, primary: {mean_person_mae_difference: null, participant_bootstrap_95: null, person_differences: {}}}};
  const person = {planned_origins: 801, candidate_statuses: {trend: "completed", ridge: "failed"}, candidate_scored: {trend: 770, ridge: 303}, common_scored: 303, common_span_us: 25 * 60 * 60000000, common_support_losses: {trend: 467, ridge: 0}, eligible_for_primary: false, ineligibility_reasons: ["incomplete_candidate:ridge"], diagnostic_error_metrics: {trend: {mae: 1}, ridge: {mae: 2}}};
  return {schema: "opent1d.m3.comparison/1", candidate_order: ["trend", "ridge"], common: {planned_people: 2, contributing_people: 0, complete_cohort: false, people: {left: person, right: {...person, candidate_statuses: {trend: "not_attempted", ridge: "not_attempted"}, common_scored: 0}}, equal_person_metrics: {trend: metrics, ridge: metrics, persistence: metrics}, contrasts: [{left: "trend", right: "ridge", mean_person_mae_difference: null, participant_bootstrap_95: null, person_differences: {}}], null_reason: "no eligible people on all-candidate support"}, candidates: {trend: {coordinator: {status: "finished", comparison_status: "failed"}, single_candidate: nativeReport("m3-forecast"), missing_archive_reason: null}, ridge: {coordinator: {status: "failed", comparison_status: "failed"}, single_candidate: null, missing_archive_reason: "no validated sealed child archive; retained raw artifacts are diagnostic only"}}};
}
function report(id, verification = "native_reader_verified", task = "m3-compare") { return {entry_id: id, task, configuration_id: "config-" + id, snapshot_job: "snapshot-" + id, verification, report_sha256: "json", artifacts_sha256: {"report.json": "json", "report.md": "md"}, complete: false, report: nativeReport(task)}; }
const tick = () => new Promise((resolve) => setImmediate(resolve));
async function finishReport(h, operation, id, verification = "native_reader_verified", task = "m3-compare") { h.reply("m3/entries/" + id + "/report", report(id, verification, task)); await tick(); h.reply("m3/entries/" + id + "/artifacts/report.md", {text: async () => "# Original native report\n"}); await operation; }
async function show(h, id, verification, task) { const operation = h.choose(id, verification, task); await finishReport(h, operation, id, verification, task); }

// The source page keeps native M3 polling; the MMTT application suppresses it.
{
  const h = harness(true), refresh = h.run("refreshM3()");
  assert.equal(h.pending.length, 0, "MMTT-only M3 refresh must not issue native requests");
  await refresh; checks++;
}
{
  const h = harness(); h.input();
  assert.deepEqual(JSON.parse(h.run("JSON.stringify(m3Intake())")), {input_id: "input-first", task: "m3-compare", candidate_ids: ["trend", "ridge"], timeout_seconds: 120});
  h.$("m3-task").value = "m3-forecast"; assert.throws(() => h.run("m3Intake()"), /exactly one/); h.run("renderM3Candidates()"); assert.equal(h.run("m3Intake().candidate_ids.length"), 1); checks++;
}
{
  const h = harness(); h.input(); h.$("m3-timeout").value = "1801"; assert.throws(() => h.run("m3Intake()"), /budget/); h.$("m3-timeout").value = "120.5"; assert.throws(() => h.run("m3Intake()"), /budget/); checks++;
}
{
  const h = harness(); h.input(); const operation = h.run("startM3Configuration('check')"); h.run("invalidateM3()"); h.reply("m3/configurations", {id: "late-freeze", freeze_sha256: "frozen"}); await operation;
  assert.equal(h.run("m3Configuration"), null); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(); h.input(); const operation = h.run("startM3Configuration('check')"); h.reply("m3/configurations", {id: "frozen", freeze_sha256: "identity", ready: false}); await tick();
  assert.equal(h.pending[0].path, "m3/configurations/frozen/check"); assert.deepEqual(h.pending[0].body, {}); const job = {id: "checked", operation: "m3_check", state: "completed", result: {}}; h.reply(h.pending[0].path, job); await operation;
  const finish = h.run("m3JobFinished(active)"); h.reply("m3/configurations/frozen", {id: "frozen", freeze_sha256: "identity", ready: true}); await finish;
  assert.equal(h.run("m3Configuration.ready"), true); h.context.active = null;
  const run = h.run("startM3Configuration('run')"); assert.equal(h.pending[0].path, "m3/configurations/frozen/run"); assert.deepEqual(h.pending[0].body, {}); h.reply(h.pending[0].path, {id: "run", operation: "m3_run", state: "queued", m3_entry_id: "new-run"}); await run;
  assert.equal(h.run("m3FollowEntry"), "new-run"); checks++;
}
{
  const h = harness(); h.input(); await h.run("startM3Configuration('run')"); assert.equal(h.pending.length, 0); assert.match(h.$("m3-notice").textContent, /Check/); checks++;
}
{
  const h = harness(); h.input(); h.run("m3Configuration = {id:'frozen', ready:true, draft_key:m3DraftKey()}"); h.$("m3-timeout").value = "121"; h.run("m3Controls()"); assert.equal(h.$("m3-run").disabled, true); checks++;
}
{
  const h = harness(); h.input(); h.context.active = {id: "m4", operation: "run", state: "running"}; await h.run("startM3Configuration('check')"); assert.equal(h.pending.length, 0); h.run("m3Controls()"); assert.equal(h.$("m3-fixture").disabled, true); assert.equal(h.$("m3-cancel").hidden, true); checks++;
}
{
  const h = harness(); h.input(); h.context.campaignPending = true; await h.run("createM3Fixture()"); assert.equal(h.pending.length, 0); h.context.campaignPending = false; h.context.durablePending = true; await h.run("createM3Fixture()"); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(), a = h.choose("a"), b = h.choose("b"); await finishReport(h, b, "b"); h.reply("m3/entries/a/report", report("a")); await a;
  assert.equal(h.$("m3-results").hidden, false); assert.match(h.$("m3-detail-title").textContent, /b/); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(), a = h.choose("a"), b = h.choose("b"); await finishReport(h, b, "b"); h.reply("m3/entries/a/report", new Error("stale failure"), true); await a;
  assert.equal(h.$("m3-results").hidden, false); assert.equal(h.$("m3-notice").textContent, ""); assert.equal(h.run("m3Selected.verification"), "native_reader_verified"); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.reply("m3/entries/a/report", report("a")); await tick(); const b = h.choose("b"); await finishReport(h, b, "b"); h.reply("m3/entries/a/artifacts/report.md", {text: async () => "OLD"}); await a;
  assert.equal(h.$("m3-markdown").textContent, "# Original native report\n"); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.run("m3Selected.snapshot_job = 'new-snapshot'"); h.reply("m3/entries/a/report", report("a")); await a;
  assert.equal(h.$("m3-results").hidden, true); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(), a = h.choose("a"), wrong = report("a"); wrong.artifacts_sha256["report.md"] = "changed"; h.reply("m3/entries/a/report", wrong); await a;
  assert.equal(h.$("m3-results").hidden, true); assert.equal(h.run("m3Selected.verification"), "changed_since_verification"); assert.match(h.$("m3-notice").textContent, /does not match/); checks++;
}
{
  const h = harness(); await show(h, "partial"); assert.equal(h.$("m3-people").children.length, 2); assert.equal(h.$("m3-candidate-results").children.length, 2);
  assert(h.text(h.$("m3-people")).includes("incomplete_candidate:ridge")); assert(h.text(h.$("m3-people")).includes("not_attempted")); assert(h.text(h.$("m3-candidate-results")).includes("no validated sealed child archive"));
  assert.equal(h.$("m3-denominators").children[1].children[0].textContent, 1602); assert(h.$("m3-analysis-scope").textContent.includes("Incomplete")); assert(h.$("m3-analysis-scope").textContent.includes("not ranked")); assert.equal(h.$("m3-errors").children[0].children[1].textContent, "unavailable"); checks++;
}
{
  const h = harness(); await show(h, "forecast", "recorded_verification", "m3-forecast"); assert.equal(h.$("m3-verification-status").textContent, "Previously verified; recheck"); assert.match(h.$("m3-cohort-status").textContent, /^Recorded:/);
  assert(h.text(h.$("m3-people")).includes("Unattempted 801")); assert(h.text(h.$("m3-people")).includes("WorkerFailure")); assert.equal(h.$("m3-errors").children.length, 2); checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadM3('report.json')"), b = h.choose("b"); await finishReport(h, b, "b"); h.reply("m3/entries/a/artifacts/report.json", {}); await download; assert.deepEqual(h.downloads, []); checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadM3('report.md')"); h.run("m3Selected.artifacts_sha256['report.md'] = 'changed'"); h.reply("m3/entries/a/artifacts/report.md", {}); await download; assert.deepEqual(h.downloads, []); checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadM3('report.md')"); h.reply("m3/entries/a/artifacts/report.md", new Error("cached Markdown changed"), true); await download;
  assert.equal(h.$("m3-results").hidden, true); assert.equal(h.run("m3Selected.verification"), "changed_since_verification"); assert.equal(h.$("m3-download-json").disabled, true); checks++;
}
{
  const h = harness(); h.context.entry = {...entry("raw"), sealed: false, can_reconstruct: false, can_view_report: false, verification: "not_requested", complete: null}; h.run("m3Selected = entry; renderM3Detail()");
  assert.equal(h.$("m3-reconstruct").disabled, true); assert.equal(h.$("m3-export").disabled, true); assert.equal(h.$("m3-retain").disabled, false); assert.match(h.$("m3-retention-detail").textContent, /does not create a verified package/);
  const retain = h.run("startSavedM3('retain')"); assert.equal(h.pending[0].path, "m3/entries/raw/retain"); assert.deepEqual(h.pending[0].body, {}); h.reply(h.pending[0].path, {id: "retain", operation: "durable_forensic", state: "queued"}); await retain; checks++;
}
{
  const h = harness(); h.context.job = {operation: "durable_forensic", state: "completed", result: {native: {schema: "opent1d.m3-forensic-retention/1", output: "/external/raw-copy", receipt_identity: "raw-identity", byte_copy_verified: true, integrity_verified: false, reconstruction_verified: false, complete: null}}}; h.run("updateM3Activity(job)");
  assert.equal(h.$("m3-retention-receipt").hidden, false); assert.match(h.$("m3-retention-receipt").textContent, /\/external\/raw-copy/); assert.match(h.$("m3-retention-receipt").textContent, /not a verified durable package/); checks++;
}
{
  const h = harness(); h.context.durableSession = {can_export: false}; h.context.entry = entry("a"); h.run("m3Selected = entry; renderM3Detail()"); assert.equal(h.$("m3-export").disabled, true); assert.equal(h.$("m3-retain").disabled, true); checks++;
}
{
  const h = harness(); h.input(); const inspect = h.run("inspectM3()"); h.$("m3-path").value = "new-config.json"; h.run("clearM3Input()"); h.reply("m3/inspect", h.context.input); await inspect; assert.equal(h.run("m3Input"), null); checks++;
}
{
  const h = harness(); h.input(); const operation = h.run("startM3Configuration('check')"); h.reply("m3/configurations", {id: "old", ready: false, freeze_sha256: "frozen"}); await tick(); h.reply("m3/configurations/old/check", {id: "job-old", operation: "m3_check", state: "completed"}); await operation;
  const finish = h.run("m3JobFinished(active)"); h.run("invalidateM3()"); h.reply("m3/configurations/old", {id: "old", ready: true}); await finish; assert.equal(h.run("m3Configuration"), null); checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadM3('report.md')"); await h.run("displayM3Report()"); h.reply("m3/entries/a/artifacts/report.md", {}); await download; assert.deepEqual(h.downloads, ["report.md"]); checks++;
}
{
  const h = harness(), old = h.choose("a"), b = h.choose("b"); await finishReport(h, b, "b"); const fresh = h.choose("a"); h.reply("m3/entries/a/report", report("a")); await old;
  assert.equal(h.$("m3-results").hidden, true); await finishReport(h, fresh, "a"); assert.equal(h.$("m3-results").hidden, false); checks++;
}
{
  const h = harness(); await show(h, "a"); const listing = h.run("refreshM3()"); h.context.next = entry("b"); h.run("selectM3(next)");
  h.reply("m3/entries", {entries: [entry("a")]}); await listing; assert.equal(h.run("m3Selected.id"), "b");
  const nextReport = h.pending.find((item) => item.path === "m3/entries/b/report"); assert(nextReport); h.reply(nextReport.path, new Error("end controlled selection"), true); await tick(); checks++;
}
{
  const h = harness(); h.context.entry = entry("a"); h.run("m3Selected = entry"); const listing = h.run("refreshM3()"); const changed = {...entry("a"), verification: "changed_since_verification", can_view_report: false, complete: null};
  h.reply("m3/entries", {entries: [changed]}); await tick(); h.reply("m3/entries/a", changed); await listing;
  assert.equal(h.$("m3-results").hidden, true); assert.equal(h.$("m3-download-json").disabled, true); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(); h.input(); h.context.entry = entry("a"); h.context.durableSession = {can_export: true}; h.run("m3Selected = entry; m3Pending = true; m3Controls()");
  assert.equal(h.$("m3-fixture").disabled, true); assert.equal(h.$("m3-reconstruct").disabled, true); assert.equal(h.$("m3-export").disabled, true); assert.equal(h.$("m3-retain").disabled, true); checks++;
}
{
  const h = harness(); h.input(); const inputs = h.run("m3CandidateIDs()"); assert.equal(inputs.length, 2); const checkboxes = h.$("m3-candidates").querySelectorAll("input");
  assert.equal(checkboxes[0]["aria-label"], "Include frozen predictor trend"); assert.equal(checkboxes[1]["aria-label"], "Include frozen predictor ridge"); checks++;
}
{
  const h = harness(), a = h.choose("a"), result = report("a"); result.artifacts_sha256 = {"report.md": "md", "report.json": "json"}; h.reply("m3/entries/a/report", result); await tick(); h.reply("m3/entries/a/artifacts/report.md", {text: async () => "# Native bytes"}); await a; assert.equal(h.$("m3-results").hidden, false); checks++;
}
{
  const h = harness(); h.run("m3Controls()");
  assert.equal(h.$("m3-form").hidden, true);
  assert.equal(h.$("m3-input-picker").open, true);
  h.input(); assert.equal(h.$("m3-form").hidden, false);
  assert.equal(h.$("m3-input-picker").open, false);
  h.$("m3-input-picker").open = true; h.run("m3Controls()");
  assert.equal(h.$("m3-input-picker").open, true);
  assert.equal(h.$("m3-check").hidden, false); assert.equal(h.$("m3-run").hidden, true);
  h.run("m3Configuration = {ready: true, draft_key: m3DraftKey()}; m3Controls()");
  assert.equal(h.$("m3-check").hidden, true); assert.equal(h.$("m3-run").hidden, false);
  h.run("invalidateM3()");
  assert.equal(h.$("m3-check").hidden, false); assert.equal(h.$("m3-run").hidden, true); checks++;
}
{
  const h = harness();
  for (const [operation, expected] of [["m3_fixture", /Example inputs are ready/], ["m3_check", /Review configuration readiness/]]) {
    h.context.active = {id: operation, operation, state: "completed"}; h.run("updateM3Activity(active)");
    assert.match(h.$("m3-activity-detail").textContent, expected); assert.match(h.$("m3-activity-detail").textContent, /no predictor has run/);
    const workspace = fs.readFileSync("experiments/gui/static/workspace.js", "utf8");
    h.context.document.getElementById = h.$;
    h.run("var workspaceObservedJob = active.id, workspaceActiveJob = null, workspaceOperationNames = {};");
    vm.runInContext(workspace.slice(workspace.indexOf("function workspaceMealTestOperation("), workspace.indexOf("async function workspaceOpenOperation(")), h.context);
    vm.runInContext(workspace.slice(workspace.indexOf("function updateWorkspaceSummary("), workspace.indexOf('document.getElementById("open-overview")')), h.context);
    h.run("updateWorkspaceSummary({jobs: [active]})");
    assert.match(h.$("workspace-operation-detail").textContent, expected);
  }
  assert.match(h.run("m3CompletionDetail({operation:'m3_run'})"), /Forecast execution finished/); checks++;
}
{
  const h = harness(), value = 0.35089467990270173;
  h.context.native = nativeReport(); h.context.native.common.equal_person_metrics.trend.mae = value;
  const original = JSON.stringify(h.context.native); h.run("renderM3Native(native)");
  assert.equal(h.$("m3-errors").children[0].children[1].textContent, "0.3509");
  assert.equal(JSON.stringify(h.context.native), original); assert.match(h.$("m3-json").textContent, /0.35089467990270173/);
  assert.equal(h.run("m3MetricText(-2.6987002753982092)"), "-2.699");
  assert.equal(h.run("m3MetricText(0)"), "0"); assert.equal(h.run("m3MetricText(1e-12)"), "1e-12");
  assert.equal(h.run("m3MetricText(Infinity)"), "unavailable"); checks++;
}
process.stdout.write(JSON.stringify({passed: true, checks, scope: "shipped M3 intake/readiness/roster/retention/async frontend functions; no browser or numerical execution"}));
