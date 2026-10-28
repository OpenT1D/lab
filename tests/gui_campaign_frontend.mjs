// Exercise shipped campaign functions with controlled intake and deferred replies.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("experiments/gui/static/app.js", "utf8");
const start = source.indexOf("// Campaign drafts, stored campaign selection");
const end = source.indexOf('$("open-campaigns").addEventListener', start);
assert(start >= 0 && end > start);
let checks = 0;

function harness() {
  const nodes = new Map(), pending = [], downloads = [];
  function element(name = "div") {
    return {name, textContent: "", children: [], dataset: {}, value: "", hidden: true, disabled: false,
      replaceChildren() { this.children = []; }, append(...children) { this.children.push(...children); },
      addEventListener() {}, setAttribute() {}, scrollIntoView() {}, focus() {}, reportValidity() { return true; },
      querySelectorAll() { return this.children.flatMap((node) => [node, ...node.querySelectorAll()]).filter((node) => ["input", "button"].includes(node.name)); },
      click() { downloads.push(this.download); },
    };
  }
  const $ = (id) => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  $("campaign-repeats").value = "1"; $("campaign-budget").value = "3600"; $("campaign-cell-id").value = "cell_1";
  const study = {schema: "m4-secure-study-config/1", sources: [{id: "left", model: "left.py", declaration: "left.json"}, {id: "right", model: "right.py", declaration: "right.json"}], scenarios: ["fasting"], timeout_seconds: 600, source_timeout_seconds: 3600};
  const context = vm.createContext({$, Date, active: null, selected: null, jobs: [],
    configuration: {id: "original-study"}, ready: true, formConfig: () => structuredClone(study),
    document: {createElement: element}, setTimeout(callback) { callback(); },
    URL: {createObjectURL: () => "blob:download", revokeObjectURL() {}},
    updateActivity() {}, updateControls() {}, updateReadiness() {}, updateCampaignStudyChoices() {}, notice() {}, refresh: async () => {},
    status(node, text, kind) { node.textContent = text; node.className = kind; },
    api(path, body) { return new Promise((resolve, reject) => pending.push({path, body: body === undefined ? undefined : JSON.parse(JSON.stringify(body)), resolve, reject})); },
  });
  vm.runInContext(source.slice(source.indexOf("// Polling must retain"), source.indexOf("// End retained polling helpers.")) + source.slice(start, end), context);
  const run = (code) => vm.runInContext(code, context);
  function reply(path, value, fail = false) {
    const index = pending.findIndex((item) => item.path === path); assert(index >= 0, "Missing request " + path);
    const item = pending.splice(index, 1)[0]; (fail ? item.reject : item.resolve)(value);
  }
  function choose(id, verification = "native_reader_verified", lastJob = "job-first") {
    run("++campaignSelection; clearCampaignResults()");
    context.entry = {id, configuration_id: "config-" + id, verification, last_job: lastJob, report_completeness: "complete", status: "completed", error: null, can_view_report: true};
    run("campaignSelected = entry"); return run("displayCampaignReport()");
  }
  const text = (node) => [node.textContent, ...node.children.map(text)].join(" ");
  return {context, study, $, pending, downloads, run, reply, choose, text};
}
const cell = (id) => ({id, configuration_id: "snapshot-" + id, source_ids: ["left", "right"], scenarios: ["fasting"], timeout_seconds: 600, source_timeout_seconds: 3600});
function report(id, verification = "native_reader_verified", complete = true) {
  return {campaign_id: id, configuration_id: "config-" + id, verification, report_completeness: complete ? "complete" : "failed", report_sha256: id,
    report: {schema: "opent1d.maintained-campaign-report/1", status: complete ? "completed" : "failed", passed: complete,
      accepted_slots: complete ? 1 : 0, planned_slots: 1, accepted_source_scenarios: complete ? 2 : 0, planned_source_scenarios: 2,
      interpretation: "Execution and identity accounting only; no pooled metric", limitations: "Synthetic fixture",
      slots: [{id: id + "--r001", cell: id, repeat: 1, planned_source_scenarios: 2, accepted: complete,
        accepted_attempt: complete ? {session: 1, attempt: 1} : null,
        attempts: [{session: 1, attempt: 1, manifest_sha256: "frozen", previous_attempt_manifest_sha256: null,
          accepted: complete, native_error_type: null, outcome: {status: complete ? "completed" : "failed", exit_code: complete ? 0 : 1, error_type: complete ? null : "WorkerFailure", native_manifest_sha256: "native"}, native_report: null}]}],
      sessions: [{number: 1, status: complete ? "completed" : "failed", scheduled_slots: 1, interruption_signal: null, manifest_sha256: "session-frozen"}],
    }};
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
async function show(h, id, verification = "native_reader_verified") { const operation = h.choose(id, verification); h.reply("campaigns/" + id + "/report", report(id, verification)); await operation; }

{
  const h = harness(), operation = h.run("captureCampaignCell()");
  assert.deepEqual(h.pending[0].body, h.study);
  const frozen = structuredClone(h.study); h.reply("configurations", {id: "snapshot-first", config: frozen}); await operation;
  h.study.sources[0].id = "new-study-source"; h.study.scenarios.push("gastric_load_30g");
  assert.equal(h.run("campaignCells[0].source_ids[0]"), "left");
  assert.equal(h.run("campaignCells[0].scenarios.length"), 1);
  assert.equal(h.context.configuration.id, "original-study"); assert.equal(h.context.ready, true);
  assert.deepEqual(JSON.parse(h.run("JSON.stringify(campaignMatrix())")), {cells: [{id: "cell_1", configuration_id: "snapshot-first"}], repeats: 1, timeout_seconds: 3600}); checks++;
}
{
  const h = harness(), operation = h.run("captureCampaignCell()"); h.run("invalidateCampaign()");
  h.reply("configurations", {id: "late-snapshot", config: h.study}); await operation;
  assert.equal(h.run("campaignCells.length"), 0); checks++;
}
{
  const h = harness(); h.context.cells = [cell("first"), cell("second")]; h.run("campaignCells = cells");
  h.$("campaign-repeats").value = "3";
  assert.deepEqual(JSON.parse(h.run("JSON.stringify(campaignMatrix())")).cells, [{id: "first", configuration_id: "snapshot-first"}, {id: "second", configuration_id: "snapshot-second"}]);
  h.run("campaignCells[1].id = 'first'"); assert.throws(() => h.run("campaignMatrix()"), /unique/); checks++;
}
{
  const h = harness(); h.context.cells = Array.from({length: 32}, (_, i) => cell("cell_" + i)); h.run("campaignCells = cells");
  h.$("campaign-repeats").value = "8"; assert.throws(() => h.run("campaignMatrix()"), /128/);
  h.$("campaign-repeats").value = "4"; assert.equal(h.run("campaignMatrix().cells.length"), 32);
  h.$("campaign-budget").value = "0"; assert.throws(() => h.run("campaignMatrix()"), /deadline/); checks++;
}
{
  const h = harness(), old = h.choose("a"); await show(h, "b");
  h.reply("campaigns/a/report", report("a")); await old;
  assert(h.text(h.$("campaign-slots")).includes("b · Repetition"));
  assert(!h.text(h.$("campaign-slots")).includes("a · Repetition")); checks++;
}
{
  const h = harness(), old = h.choose("a"); await show(h, "b");
  h.reply("campaigns/a/report", new Error("stale report error"), true); await old;
  assert.equal(h.$("campaign-results").hidden, false); assert.equal(h.$("campaign-notice").textContent, ""); checks++;
}
{
  const h = harness(), old = h.choose("a"); await show(h, "b"); const fresh = h.choose("a");
  h.reply("campaigns/a/report", report("a")); await old;
  assert.equal(h.$("campaign-results").hidden, true);
  h.reply("campaigns/a/report", report("a")); await fresh; assert.equal(h.$("campaign-results").hidden, false); checks++;
}
{
  const h = harness(), operation = h.choose("a"); h.run("campaignSelected.last_job = 'job-new'");
  h.reply("campaigns/a/report", report("a")); await operation;
  assert.equal(h.$("campaign-results").hidden, true); checks++;
}
{
  const h = harness(); await show(h, "a", "recorded_verification");
  assert.equal(h.$("campaign-coverage-status").textContent, "Coverage unverified; recorded snapshot"); checks++;
}
{
  const h = harness(), operation = h.choose("failed"), saved = report("failed", "native_reader_verified", false);
  saved.report.slots.push({id: "pending--r001", cell: "pending", repeat: 1, planned_source_scenarios: 2, accepted: false, accepted_attempt: null, attempts: []});
  saved.report.planned_slots = 2; saved.report.planned_source_scenarios = 4;
  saved.report.slots[0].attempts.push({session: 2, attempt: 2, accepted: false, outcome: {status: "interrupted", exit_code: null, error_type: "WorkerInterruption"}, native_report: null});
  h.reply("campaigns/failed/report", saved); await operation;
  const rows = h.text(h.$("campaign-slots")); assert(rows.includes("WorkerFailure")); assert(rows.includes("WorkerInterruption")); assert(rows.includes("not attempted")); assert(rows.includes("Native report unavailable"));
  assert.equal(h.$("campaign-slots").children.length, 2); assert.equal(h.$("campaign-denominators").children[2].children[0].textContent, 2); checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadCampaign('report.json')");
  const b = h.choose("b"); h.reply("campaigns/a/artifacts/report.json", {name: "stale"}); await download;
  assert.deepEqual(h.downloads, []); h.reply("campaigns/b/report", report("b")); await b; checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadCampaign('report.md')");
  h.run("campaignSelected.last_job = 'job-reconstruct-new'"); h.reply("campaigns/a/artifacts/report.md", {name: "old revision"}); await download;
  assert.deepEqual(h.downloads, []); checks++;
}
{
  const h = harness(); await show(h, "a"); const download = h.run("downloadCampaign('report.md')"); const b = h.choose("b");
  h.reply("campaigns/a/artifacts/report.md", new Error("old download failed"), true); await download;
  assert.equal(h.$("campaign-notice").textContent, ""); h.reply("campaigns/b/report", report("b")); await b; checks++;
}
{
  const h = harness(), operation = h.choose("a"), wrong = report("a"); wrong.configuration_id = "other-matrix";
  h.reply("campaigns/a/report", wrong); await operation;
  assert.equal(h.$("campaign-results").hidden, true); assert(h.$("campaign-notice").textContent.includes("does not match")); checks++;
}
{
  const h = harness(); h.context.cells = [cell("first")]; h.run("campaignCells = cells");
  const operation = h.run("prepareCampaign()"); h.run("invalidateCampaign()");
  h.reply("campaigns/configurations", {id: "stale-preparation", ready: true});
  await assert.rejects(operation, /draft matrix changed/);
  assert.equal(h.run("campaignConfiguration"), null); checks++;
}
{
  const h = harness(); h.context.cells = [cell("first")]; h.run("campaignCells = cells");
  const operation = h.run("startCampaignConfiguration('check')");
  assert.deepEqual(h.pending[0].body, {cells: [{id: "first", configuration_id: "snapshot-first"}], repeats: 1, timeout_seconds: 3600});
  h.reply("campaigns/configurations", {id: "campaign-config-first", ready: false, matrix_sha256: "frozen"}); await tick();
  assert.equal(h.pending[0].path, "campaigns/configurations/campaign-config-first/check"); assert.deepEqual(h.pending[0].body, {});
  h.reply(h.pending[0].path, {id: "job-check", operation: "campaign_check", state: "queued"}); await operation;
  assert.equal(h.context.configuration.id, "original-study"); assert.equal(h.context.ready, true); checks++;
}
{
  const h = harness(); h.context.cells = [cell("first")]; h.run("campaignCells = cells");
  const operation = h.run("startCampaignConfiguration('run')");
  h.reply("campaigns/configurations", {id: "unchecked", ready: false, matrix_sha256: "frozen"}); await operation;
  assert.equal(h.pending.length, 0); assert(h.$("campaign-notice").textContent.includes("before running")); checks++;
}
{
  const h = harness(); h.context.entry = {id: "saved", configuration_id: "own-frozen-config", can_resume: false}; h.run("campaignSelected = entry");
  await h.run("startSavedCampaign('resume')"); assert.equal(h.pending.length, 0);
  assert(h.$("campaign-notice").textContent.includes("before resuming"));
  const check = h.run("startSavedCampaign('check')"); assert.equal(h.pending[0].path, "campaigns/configurations/own-frozen-config/check");
  h.reply(h.pending[0].path, {id: "job-check", operation: "campaign_check", state: "queued"}); await check; checks++;
}
{
  const h = harness(); h.context.entry = {id: "saved-failed", configuration_id: "unchecked", can_resume: false}; h.context.ready = false; h.run("campaignSelected = entry");
  const reconstruct = h.run("startSavedCampaign('reconstruct')");
  assert.equal(h.pending[0].path, "campaigns/saved-failed/reconstruct"); assert.deepEqual(h.pending[0].body, {});
  h.reply(h.pending[0].path, {id: "job-reconstruct", operation: "campaign_reconstruct", state: "queued"}); await reconstruct;
  assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(); h.context.cells = [cell("first")]; h.context.prepared = {id: "already-prepared", ready: true, matrix_sha256: "frozen"}; h.run("campaignCells = cells; campaignConfiguration = prepared");
  const install = h.run("startCampaignConfiguration('install')"); await tick();
  assert.equal(h.run("campaignConfiguration.ready"), false);
  assert.equal(h.pending[0].path, "campaigns/configurations/already-prepared/install");
  h.reply(h.pending[0].path, {id: "job-install", operation: "campaign_install", state: "completed"}); await install;
  assert.equal(h.pending.length, 0); assert.equal(h.run("campaignConfiguration.ready"), false);
  assert.equal(h.context.ready, false); assert.equal(h.context.configuration.id, "original-study");
  assert.equal(h.run("campaignConfiguration.id"), "already-prepared"); assert.equal(h.run("campaignCells.length"), 1); checks++;
}
{
  const h = harness(); h.context.cells = [cell("first")]; h.context.prepared = {id: "checked-campaign", ready: true, matrix_sha256: "frozen"};
  h.run("campaignCells = cells; campaignConfiguration = prepared");
  const beginStart = source.indexOf("async function begin(path)");
  const beginEnd = source.indexOf("function updateActivity(job)", beginStart);
  assert(beginStart >= 0 && beginEnd > beginStart); h.run(source.slice(beginStart, beginEnd));
  const install = h.run("begin('configurations/original-study/install')");
  h.reply("configurations/original-study/install", {id: "job-study-install", operation: "install", state: "queued"}); await install;
  assert.equal(h.context.ready, false); assert.equal(h.run("campaignConfiguration.ready"), false);
  assert.equal(h.context.configuration.id, "original-study"); assert.equal(h.run("campaignConfiguration.id"), "checked-campaign");
  assert.equal(h.run("campaignCells[0].configuration_id"), "snapshot-first"); checks++;
}
{
  const h = harness(); h.context.prepared = {id: "checked-campaign", ready: true}; h.run("campaignConfiguration = prepared");
  for (const [id, operation, state] of [["failed-study-install", "install", "failed"], ["cancelled-campaign-install", "campaign_install", "cancelled"]]) {
    h.context.job = {id, operation, state}; h.context.ready = true; h.run("campaignConfiguration.ready = true; observeInstall(job)");
    assert.equal(h.context.ready, false); assert.equal(h.run("campaignConfiguration.ready"), false);
    h.context.ready = true; h.run("campaignConfiguration.ready = true; observeInstall(job)");
    assert.equal(h.context.ready, true); assert.equal(h.run("campaignConfiguration.ready"), true);
  }
  h.context.job = {id: "normal-check", operation: "check", state: "completed"}; h.run("observeInstall(job)");
  assert.equal(h.context.ready, true); assert.equal(h.run("campaignConfiguration.ready"), true); checks++;
}
{
  const h = harness(); h.context.prepared = {id: "checked-campaign", ready: true}; h.run("campaignConfiguration = prepared");
  Object.assign(h.context, {polling: false, activeStates: new Set(["queued", "running", "cancelling"]), renderHistory() {}, displayReport: async () => {}, refreshLibrary: async () => {}, notice(message) { throw new Error(message); }});
  h.run("refreshCampaigns = async () => {}");
  const refreshStart = source.indexOf("async function refresh()");
  const refreshEnd = source.indexOf("async function download(name)", refreshStart);
  assert(refreshStart >= 0 && refreshEnd > refreshStart); h.run(source.slice(refreshStart, refreshEnd));
  const observed = {id: "job-install-from-another-view", operation: "install", state: "completed"};
  h.context.active = {id: observed.id, operation: "install", state: "running"};
  const first = h.run("refresh()"); h.reply("jobs", {jobs: [observed]}); await tick();
  assert.equal(h.pending[0].path, "configurations/original-study/check");
  const automaticCheck = {id: "job-separate-study-check", operation: "check", state: "queued"};
  h.reply(h.pending[0].path, automaticCheck); await first;
  assert.equal(h.pending.length, 0, "Only the existing separate study check is started");
  assert.equal(h.context.ready, false); assert.equal(h.run("campaignConfiguration.ready"), false);
  const again = h.run("refresh()"); h.reply("jobs", {jobs: [{...automaticCheck, state: "completed", result: {ready: true}}, observed]}); await again;
  assert.equal(h.context.ready, true, "The separate study check may restore study readiness");
  assert.equal(h.run("campaignConfiguration.ready"), false, "Campaign readiness requires its own check"); checks++;
}
console.log(JSON.stringify({checks, passed: true, scope: "controlled shipped-function campaign intake/roster/async checks; no browser or numerical execution"}));
