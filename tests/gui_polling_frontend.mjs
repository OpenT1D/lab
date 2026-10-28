// Polling regressions use DOM identity and focus, not just rendered text.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("experiments/gui/static/app.js", "utf8");
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert(a >= 0 && b > a, start); return source.slice(a, b);
}
const helpers = section("// Polling must retain", "// End retained polling helpers.");
let checks = 0;
function harness(code) {
  const nodes = new Map(), pending = [], selections = [];
  const document = {activeElement: null};
  function element(name = "div") {
    const listeners = new Map();
    return {name, tagName: name.toUpperCase(), dataset: {}, children: [], parentElement: null,
      textContent: "", value: "", hidden: true, disabled: false, open: false, replacements: 0,
      contains(node) { return node === this || this.children.some((child) => child.contains(node)); },
      replaceChildren(...items) {
        if (this.children.some((child) => child.contains(document.activeElement))) document.activeElement = document.body;
        for (const child of this.children) child.parentElement = null;
        this.children = []; this.replacements++; this.append(...items);
      },
      append(...items) { for (const child of items) { this.children.push(child); child.parentElement = this; } },
      addEventListener(name, callback) { listeners.set(name, callback); },
      click() { listeners.get("click")?.(); }, focus() { document.activeElement = this; },
      querySelectorAll(selector) {
        const descendants = this.children.flatMap((child) => [child, ...child.querySelectorAll("*")]);
        if (selector === "*") return descendants;
        if (selector === "[data-polling-key]") return descendants.filter((child) => child.dataset.pollingKey !== undefined);
        return descendants.filter((child) => selector.split(",").includes(child.name));
      },
    };
  }
  document.body = element("body"); document.activeElement = document.body;
  document.createElement = element;
  const $ = (id) => { if (!nodes.has(id)) { const node = element(id === "durable-source" ? "select" : "div"); node.id = id; nodes.set(id, node); document.body.append(node); } return nodes.get(id); };
  document.getElementById = $;
  const context = vm.createContext({$, document, Date, active: null,
    libraryEntries: [], librarySelected: null, campaigns: [], campaignSelected: null,
    durableEntries: [], durableSelected: null, durableListRequest: 0,
    m3Entries: [], m3Selected: null, m3Inputs: [], m3Pending: false,
    m3Shown: null, m3LastReportCheck: 0, m3Request: 0, m3Selection: 0,
    campaignShown: null, campaignLastReportCheck: 0, campaignRequest: 0, campaignSelection: 0, campaignActionID: null,
    selectLibrary(entry) { selections.push(entry); }, selectCampaign(entry) { selections.push(entry); },
    selectDurable(entry) { selections.push(entry); }, selectM3(entry) { selections.push(entry); }, chooseM3Input(entry) { selections.push(entry); },
    m3TaskTitle(task) { return task; }, m3Controls() {}, renderDurableDetail() {}, displayDurableReport: async () => {},
    status(node, text) { node.textContent = text; },
    withdrawM3Snapshot(message) { $("m3-results").hidden = true; $("m3-notice").textContent = message; },
    campaignNotice(message) { $("campaign-notice").textContent = message; },
    api(path) { return new Promise((resolve, reject) => pending.push({path, resolve, reject})); },
  });
  vm.runInContext(helpers + section("function libraryRecordedStatus(", "function renderLibraryList(") + code, context);
  const run = (code) => vm.runInContext(code, context);
  function reply(path, value, fail = false) {
    const index = pending.findIndex((item) => item.path === path); assert(index >= 0, path);
    const request = pending.splice(index, 1)[0]; (fail ? request.reject : request.resolve)(value);
  }
  return {$, context, document, pending, selections, run, reply};
}
const listCases = [
  {fn: "renderLibraryList", state: "libraryEntries", id: "library-list", end: "function renderLibraryDigests", field: "metadata_status",
    entry: (id) => ({id, path: id, task: "m4-study-secure", tags: [], availability: "available", metadata_status: "metadata_read", metadata: {recorded_status: "completed"}})},
  {fn: "renderCampaignList", state: "campaigns", id: "campaign-list", end: "function renderCampaignDetail", field: "status",
    entry: (id) => ({id, status: "completed", cells: [{}], repeats: 1, accepted_slots: 1, planned_slots: 1})},
  {fn: "renderDurableList", state: "durableEntries", id: "durable-list", end: "function renderDurableDetail", field: "integrity",
    entry: (id) => ({id, task: "m3-forecast", path: id, integrity: "verified_snapshot", complete: true})},
  {fn: "renderM3List", state: "m3Entries", id: "m3-list", end: "function renderM3Detail", field: "execution_state",
    entry: (id) => ({id, task: "m3-forecast", execution_state: "completed", sealed: true})},
  {fn: "renderM3Inputs", state: "m3Inputs", id: "m3-inputs", end: "async function inspectM3", field: "path",
    entry: (id) => ({id, task: "m3-forecast", path: id + ".json"})},
];
for (const spec of listCases) {
  const h = harness(section("function " + spec.fn + "()", spec.end));
  const first = spec.entry("first"), second = spec.entry("second"); h.context[spec.state] = [first, second]; h.run(spec.fn + "()");
  const container = h.$(spec.id), button = container.children[0]; button.focus();
  const latest = {...first, invisible_metadata: "new response object"}; h.context[spec.state] = [latest, {...second}]; h.run(spec.fn + "()");
  assert.equal(container.children[0], button, spec.fn + " retains DOM identity");
  assert.equal(h.document.activeElement, button, spec.fn + " retains keyboard focus");
  button.click(); assert.equal(h.selections[0], latest, spec.fn + " selects the latest response, not its stale closure"); checks++;
  h.context[spec.state] = [second, {...latest, [spec.field]: "changed"}]; h.run(spec.fn + "()");
  assert.equal(h.document.activeElement.dataset.pollingKey, "first", spec.fn + " restores focus across reorder/status changes");
  assert.equal(h.document.activeElement, container.children[1]); checks++;
  h.context[spec.state] = [second]; h.run(spec.fn + "()");
  assert.equal(h.document.activeElement, container.children[0], spec.fn + " supplies a neighbouring focus target on removal");
  h.context[spec.state] = []; h.run(spec.fn + "()"); assert.equal(h.document.activeElement, container); checks++;
}

// A native source select keeps its option objects when polling adds no new choices.
{
  const h = harness(section("function renderDurableList()", "function renderDurableDetail") + section("async function refreshDurable()", "async function startDurable"));
  const sources = [{kind: "m3", id: "first", label: "First experiment"}];
  async function refresh(next) {
    const operation = h.run("refreshDurable()"); h.reply("durable/entries", {entries: []});
    await new Promise((resolve) => setImmediate(resolve)); h.reply("durable/sources", {sources: next}); await operation;
  }
  await refresh(sources); const select = h.$("durable-source"), option = select.children[1]; select.value = "m3:first"; select.focus();
  await refresh(structuredClone(sources)); assert.equal(select.children[1], option); assert.equal(select.value, "m3:first"); assert.equal(h.document.activeElement, select); checks++;
  await refresh([...sources, {kind: "study", id: "second", label: "Second experiment"}]);
  assert.equal(select.children.length, 3); assert.equal(select.value, "m3:first"); assert.equal(h.document.activeElement, select); checks++;
}

const tick = () => new Promise((resolve) => setImmediate(resolve));
function nativeForecast(scored = 3) {
  const person = {planned: 3, attempted: 3, not_attempted: 0, forecastable: 3, scored,
    execution_status: "completed", eligible_for_primary: true, ineligibility_reasons: [], execution: {},
    history_exclusions: {}, scoring_exclusions: {}, target_status_counts: {}};
  return {predictor: {id: "example", source: {}, settings: {}}, evaluation: {planned_people: 1, contributing_people: 1, complete_cohort: true,
    people: {first: person}, equal_person_metrics: {candidate: {mae: 1, rmse: 1, bias: 0}, persistence: {mae: 2, rmse: 2, bias: 0}},
    primary: {mean_person_mae_difference: -1, participant_bootstrap_95: [-1, -1], person_differences: {first: -1}}}};
}
{
  const h = harness(section("function m3Revision(entry)", "function clearM3Results") + section("function m3Metric(", "async function refreshM3()"));
  h.$("m3-results").append(...["denominators", "analysis-scope", "errors", "contrasts", "people", "candidate-results", "json", "markdown"].map((suffix) => h.$("m3-" + suffix)));
  const selected = {id: "a", task: "m3-forecast", configuration_id: "config-a", snapshot_job: "snapshot-a", verification: "native_reader_verified", can_view_report: true, updated_at: "one", artifacts_sha256: {"report.json": "json", "report.md": "md"}};
  h.context.m3Selected = selected;
  async function finish(operation, scored = 3) {
    h.reply("m3/entries/a/report", {entry_id: "a", task: selected.task, configuration_id: selected.configuration_id, snapshot_job: selected.snapshot_job,
      verification: selected.verification, artifacts_sha256: selected.artifacts_sha256, report: nativeForecast(scored)});
    await tick(); h.reply("m3/entries/a/artifacts/report.md", {text: async () => "Original native report"}); await operation;
  }
  await finish(h.run("displayM3Report()"));
  const row = h.$("m3-people").children[0], summary = row.children[0]; row.open = true; summary.focus();
  h.context.m3LastReportCheck = 0; const same = h.run("displayM3Report()"); assert.equal(h.$("m3-results").hidden, false);
  await finish(same); assert.equal(h.$("m3-people").children[0], row); assert.equal(row.open, true); assert.equal(h.document.activeElement, summary); checks++;
  selected.updated_at = "two"; await finish(h.run("displayM3Report()"), 2);
  const updated = h.$("m3-people").children[0]; assert.notEqual(updated, row); assert.equal(updated.open, true); assert.equal(h.document.activeElement, updated.children[0]); checks++;
  h.context.m3LastReportCheck = 0; const rejected = h.run("displayM3Report()"); h.reply("m3/entries/a/report", new Error("Snapshot changed"), true); await rejected;
  assert.equal(h.$("m3-results").hidden, true); assert.equal(h.$("m3-notice").textContent, "Snapshot changed"); checks++;
}
function campaignReport(state = "completed") {
  return {campaign_id: "a", configuration_id: "config-a", verification: "native_reader_verified", report_sha256: "report-a",
    report: {schema: "opent1d.maintained-campaign-report/1", passed: true, accepted_slots: 1, planned_slots: 1, accepted_source_scenarios: 2, planned_source_scenarios: 2,
      interpretation: "Recorded native evidence", limitations: "Synthetic input",
      slots: [{id: "first--r001", cell: "first", repeat: 1, accepted: true, planned_source_scenarios: 2, attempts: [{session: 1, attempt: 1, accepted: true, outcome: {status: state}}]}],
      sessions: [{number: 1, status: state, scheduled_slots: 1, interruption_signal: null, manifest_sha256: "session"}]}};
}
{
  const h = harness(section("function campaignRevision(", "function selectCampaign(") + section("function renderCampaignRoster(", "async function refreshCampaigns()"));
  h.$("campaign-results").append(...["slots", "sessions", "denominators", "interpretation", "limitations"].map((suffix) => h.$("campaign-" + suffix)));
  h.context.campaignSelected = {id: "a", configuration_id: "config-a", last_job: "one", can_view_report: true, verification: "native_reader_verified"};
  async function finish(operation, state) { h.reply("campaigns/a/report", campaignReport(state)); await operation; }
  await finish(h.run("displayCampaignReport()")); const row = h.$("campaign-slots").children[0]; row.open = true; row.children[0].focus();
  h.context.campaignLastReportCheck = 0; const same = h.run("displayCampaignReport()"); assert.equal(h.$("campaign-results").hidden, false, "Rechecking retains a currently valid snapshot while the reply is pending");
  await finish(same); assert.equal(h.$("campaign-slots").children[0], row); assert.equal(row.open, true); assert.equal(h.document.activeElement, row.children[0]); checks++;
  h.context.campaignSelected.last_job = "two"; await finish(h.run("displayCampaignReport()"), "failed");
  const updated = h.$("campaign-slots").children[0]; assert.notEqual(updated, row); assert.equal(updated.open, true); assert.equal(h.document.activeElement, updated.children[0]); checks++;
  h.context.campaignLastReportCheck = 0; const rejected = h.run("displayCampaignReport()"); h.reply("campaigns/a/report", new Error("Snapshot changed"), true); await rejected;
  assert.equal(h.$("campaign-results").hidden, true); assert.equal(h.$("campaign-notice").textContent, "Snapshot changed"); checks++;
}
console.log(JSON.stringify({passed: true, checks, scope: "shipped polling lists, latest selections, focus recovery, source options and report disclosures; controlled DOM, no native model execution"}));
