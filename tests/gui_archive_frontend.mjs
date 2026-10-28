// Controlled replies exercise the shipped task-dispatched archive frontend.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync("experiments/gui/static/app.js", "utf8");
const start = source.indexOf("// Archive views use their own selection tokens."), end = source.indexOf('$("open-library").addEventListener', start);
const helpersStart = source.indexOf("function m3Metric("), helpersEnd = source.indexOf("async function displayM3Report()", helpersStart);
assert(start >= 0 && end > start && helpersStart >= 0 && helpersEnd > helpersStart);
let checks = 0;
function harness(mmttOnly = false) {
  const nodes = new Map(), pending = [], urls = [], downloads = [];
  function element(name = "div") {
    return {name, hidden: true, disabled: false, value: "", textContent: "", children: [], dataset: {},
      replaceChildren() { this.children = []; }, append(...items) { this.children.push(...items); }, addEventListener() {},
      click() { downloads.push(this.download); },
      set innerHTML(_) { throw new Error("Untrusted report text must never become HTML"); },
    };
  }
  const $ = (id) => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  const context = vm.createContext({$, document: {createElement: element}, Date, mmttOnly, active: null, m3Pending: false, campaignPending: false, durablePending: false,
    URL: {revokeObjectURL() {}, createObjectURL(blob) { urls.push(blob.name); return "blob:" + blob.name; }}, setTimeout() {},
    status(target, label, kind = "neutral") { target.textContent = label; target.className = kind; },
    api(path, body, raw) { return new Promise((resolve, reject) => pending.push({path, body, raw, resolve, reject})); },
  });
  vm.runInContext(source.slice(source.indexOf("// Polling must retain"), source.indexOf("// End retained polling helpers.")) + source.slice(start, end) + source.slice(helpersStart, helpersEnd), context);
  const run = (code) => vm.runInContext(code, context);
  const text = (node) => [node.textContent, ...node.children.map(text)].join(" ");
  function choose(id, verification = "native_reader_verified", task = "m4-study-secure", stamp = "first") {
    context.entry = entry(id, verification, task, stamp); run("++librarySelection; librarySelected = entry; clearLibraryResults(); renderLibraryDetail()");
    return run("displayLibraryReport()");
  }
  function reply(id, name, value, fail = false) {
    const index = pending.findIndex((p) => p.path.includes("/" + id + "/") && p.path.endsWith(name));
    assert(index >= 0, "missing pending " + id + "/" + name); const request = pending.splice(index, 1)[0]; (fail ? request.reject : request.resolve)(value);
  }
  function replyList(entries) { const index = pending.findIndex((p) => p.path === "library/entries"); assert(index >= 0); pending.splice(index, 1)[0].resolve({entries}); }
  return {context, $, pending, urls, downloads, choose, reply, replyList, run, text};
}
function entry(id, verification = "native_reader_verified", task = "m4-study-secure", stamp = "first") {
  return {id, task, path: id, tags: [], verification, verified_at: stamp, verified_job: "job-" + stamp,
    artifacts_sha256: {"report.json": "json-" + id, "report.md": "md-" + id}, model_declaration_sha256: task === "m5-prognosis" ? "d".repeat(64) : undefined, inventory_sha256: "source-" + id,
    source_freshness: "not_rechecked_since_worker", report_completeness: task === "m4-study-secure" ? "complete" : "incomplete",
    can_view_report: true, can_verify: true, availability: "available", metadata_status: "metadata_read", reader_scope: "Fixed native reader", metadata: {recorded_status: "failed", models: []},
    hash_checks: {status: "matched", checked_files: 34, scope: "recorded_hashes_only", mismatches: [], manifests: []}};
}
function m4Report(sourceName, verification = "native_reader_verified") {
  return {verification, passed: true, denominators: {sources: 2, accepted_sources: 2, source_scenarios: 6, accepted_source_scenarios: 6, pairs: 1, accepted_pairs: 1}, sources: {[sourceName]: {status: "completed", accepted: true}}, limitations: ["synthetic"]};
}
function person(status = "failed") {
  return {execution_status: status, planned: 801, attempted: status === "not_attempted" ? 0 : 321, not_attempted: status === "not_attempted" ? 801 : 480,
    forecastable: status === "not_attempted" ? 0 : 309, scored: status === "not_attempted" ? 0 : 303,
    prediction_coverage: null, score_coverage: null, eligible_for_primary: false, ineligibility_reasons: ["execution_incomplete"],
    history_exclusions: {warmup: 12}, scoring_exclusions: {warmup: 12, target_outside: 6}, target_status_counts: {measured: 303}, execution: {error_type: "WorkerFailure", worker_error_type: "ValueError"}};
}
function nativeReport(task = "m3-compare", complete = false) {
  const metrics = complete ? {mae: 1, rmse: 2, bias: -1} : {mae: null, rmse: null, bias: null};
  if (task === "m3-forecast") return {schema: "opent1d.m3.researcher/1", predictor: {id: "trend", reference: "invented", rights: "self-authored", source: {sha256: "source"}, settings: {sha256: "settings"}},
    evaluation: {planned_people: 2, contributing_people: complete ? 2 : 0, complete_cohort: complete, people: {left: person(), right: person("not_attempted")}, equal_person_metrics: {candidate: metrics, persistence: metrics}, primary: {mean_person_mae_difference: null, participant_bootstrap_95: null, person_differences: {}}}};
  const one = {planned_origins: 801, candidate_statuses: {trend: "completed", ridge: "failed"}, candidate_scored: {trend: 770, ridge: 303}, common_scored: 303, common_span_us: 25 * 60 * 60000000,
    common_support_losses: {trend: 467, ridge: 0}, eligible_for_primary: false, ineligibility_reasons: ["incomplete_candidate:ridge"], diagnostic_error_metrics: {trend: {mae: 1}, ridge: {mae: 2}}};
  return {schema: "opent1d.m3.comparison/1", candidate_order: ["trend", "ridge"], common: {planned_people: 2, contributing_people: complete ? 2 : 0, complete_cohort: complete,
    people: {left: one, right: {...one, candidate_statuses: {trend: "not_attempted", ridge: "not_attempted"}, common_scored: 0}}, equal_person_metrics: {trend: metrics, ridge: metrics, persistence: metrics},
    contrasts: [{left: "trend", right: "ridge", mean_person_mae_difference: null, participant_bootstrap_95: null, person_differences: {}}], null_reason: "no eligible people on all-candidate support"},
    candidates: {trend: {coordinator: {status: "finished", comparison_status: "failed"}, single_candidate: nativeReport("m3-forecast"), missing_archive_reason: null}, ridge: {coordinator: {status: "failed", comparison_status: "failed"}, single_candidate: null, missing_archive_reason: "no validated sealed child archive; raw evidence retained"}}};
}
function m3Report(id, task = "m3-compare", verification = "native_reader_verified", complete = false) {
  const native = nativeReport(task, complete);
  return {task, schema: native.schema, native_report: native, verification, verification_scope: "verified_snapshot", source_freshness: "not_rechecked_since_worker", report_completeness: complete ? "complete" : "incomplete", report_sha256: "json-" + id};
}
function m5Report(id, mode = "mixed", verification = "native_reader_verified") {
  const runtime = {implementation: "CPython", python_major_minor: "3.12", python_version: "3.12.9"};
  const people = Array.from({length: 32}, (_, i) => {
    const number = i + 1, eligible = ![1, 2, 3, 4, 5].includes(number);
    return {alias: "SYN" + String(number).padStart(3, "0"), split: number % 4 ? "development" : "evaluation", eligible, issues: eligible ? [] : ["fixed_exclusion_" + number], intervening_infusion_days: number === 8 ? [150] : [], y1_present: number !== 4, visit15_present: true};
  });
  const attempt = (index, status = "completed", prediction = 10) => ({attempt: index, status, prediction_u_day: status === "completed" ? prediction : null, runtime: status === "completed" ? {...runtime} : null});
  const predictions = people.filter((person) => person.eligible && person.split === "evaluation").map((person, i) => {
    let attempts = [attempt(1), attempt(2)], candidate_status = "completed";
    if (mode === "zero") { attempts = [attempt(1, "worker_failed"), attempt(2, "worker_failed")]; candidate_status = "failed"; }
    if (mode === "mixed") {
      if (i === 1) { attempts = [attempt(1), attempt(2, "timeout")]; candidate_status = "failed"; }
      if (i === 2) { attempts = [attempt(1), attempt(2, "completed", 11)]; candidate_status = "not_reproducible"; }
      if (i === 3) { attempts = [attempt(1, "invalid_output"), attempt(2, "worker_failed")]; candidate_status = "failed"; }
    }
    if (mode === "interrupted") {
      if (i === 0) { attempts = [attempt(1), attempt(2, "interrupted")]; candidate_status = "interrupted"; }
      else { attempts = []; candidate_status = "not_attempted"; }
    }
    if (mode === "missing-repeat") {
      if (i === 0) { attempts = [attempt(1)]; candidate_status = "incomplete"; }
      else { attempts = []; candidate_status = "not_attempted"; }
    }
    return {alias: person.alias, observed_reported_insulin_mean_u_day: 12, baseline_prediction_u_day: 14, candidate_prediction_u_day: candidate_status === "completed" ? 10 : null, candidate_status, attempts};
  });
  const paired_count = predictions.filter((item) => item.candidate_status === "completed").length;
  const native = {schema: "m5-researcher-workflow/1", claim: "invented_pipeline_check_only", human_execution_authorized: false, treatment_effect_or_cure_estimated: false,
    model_id: "frozen_example", source_sha256: "a".repeat(64), state_sha256: "b".repeat(64), training_provenance: "researcher_declared_not_independently_verified",
    roster_count: 32, development_roster_count: 24, evaluation_roster_count: 8, excluded_count: 5, development_eligible_count: 20, evaluation_eligible_count: 7,
    paired_count, candidate_coverage: paired_count / 7, comparison_status: paired_count === 7 ? "complete" : "incomplete", candidate_execution_complete: ["complete", "mixed", "zero"].includes(mode),
    metric: "mean absolute error in reported insulin U/day", baseline_mae_all_eligible_u_day: 3, baseline_mae_paired_u_day: paired_count ? 2 : null,
    candidate_mae_paired_u_day: paired_count ? 1 : null, mae_change_candidate_minus_baseline_u_day: paired_count ? -1 : null, people, evaluation_predictions: predictions,
    provenance: {schema: "m5-researcher-provenance/1", git_revision: "c".repeat(40), host_runtime: runtime, worker_timeout_seconds: 5, source_identity: "saved source bytes; git revision alone does not identify local edits"},
    tooling_lock_sha256: "e".repeat(64), implementation_sha256: Object.fromEntries(["source-contract.py", "source-worker.py", "source-report.py", "source-run.py", "source-synthetic.py"].map((key) => [key, "f".repeat(64)]))};
  return {task: "m5-prognosis", schema: native.schema, native_report: native, verification, verification_scope: "verified_snapshot", source_freshness: "not_rechecked_since_worker", report_completeness: mode === "complete" ? "complete" : "incomplete", report_sha256: "json-" + id, model_declaration_sha256: "d".repeat(64),
    model_declaration: {schema: "m5-prognostic-model/1", model_id: native.model_id, rights_basis: "Self-authored illustrative source and frozen state", input_schema: "m5-landmark-input/1", output_unit: "U/day", source_sha256: native.source_sha256, state_sha256: native.state_sha256, runtime: {python_major_minor: "3.12", dependencies: []}, training: {phase: "development_only", fixture_sha256: "e".repeat(64), participant_aliases: people.filter((person) => person.eligible && person.split === "development").map((person) => person.alias)}}};
}
async function showM5(h, id, mode = "mixed", verification = "native_reader_verified") {
  return showCustom(h, id, "m5-prognosis", verification, m5Report(id, mode, verification));
}
const tick = async () => { await Promise.resolve(); await Promise.resolve(); };
// Snippets receive the page's profile explicitly; the MMTT app never polls archives.
{
  const h = harness(true), refresh = h.run("refreshLibrary()");
  assert.equal(h.pending.length, 0, "MMTT-only library refresh must not issue native requests");
  await refresh; checks++;
}
async function showM4(h, id, verification = "native_reader_verified") {
  const operation = h.choose(id, verification); h.reply(id, "report", m4Report(id, verification)); await tick(); h.reply(id, "figure.svg", {name: id}); await operation;
}
async function showM3(h, id, task = "m3-compare", verification = "native_reader_verified") {
  const operation = h.choose(id, verification, task);
  h.reply(id, "report", m3Report(id, task, verification)); await operation;
}
async function showCustom(h, id, task, verification, report) {
  h.context.entry = {...entry(id, verification, task), report_completeness: report.report_completeness}; h.run("++librarySelection; librarySelected = entry; clearLibraryResults(); renderLibraryDetail()");
  const operation = h.run("displayLibraryReport()"); h.reply(id, "report", report); await operation;
}

// Preserve the existing seven asynchronous M4 regression cases.
{
  const h = harness(), a = h.choose("a"); await showM4(h, "b"); h.reply("a", "report", m4Report("STALE")); await a;
  assert.equal(h.$("library-source-results").children[0].children[0].textContent, "b"); assert.equal(h.$("library-figure").src, "blob:b"); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.reply("a", "report", m4Report("a")); await tick(); const b = h.choose("b"); assert.equal(h.$("library-results").hidden, true); assert.equal(h.$("library-figure").hidden, true);
  h.reply("b", "report", m4Report("b")); await tick(); h.reply("a", "figure.svg", {name: "STALE"}); await a; assert.equal(h.$("library-figure").hidden, true); h.reply("b", "figure.svg", {name: "b"}); await b; assert.deepEqual(h.urls, ["b"]); checks++;
}
{
  const h = harness(), a = h.choose("a"); await showM4(h, "b"); h.reply("a", "report", new Error("stale error"), true); await a; assert.equal(h.$("library-results").hidden, false); assert.equal(h.$("library-notice").textContent, ""); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.reply("a", "report", m4Report("a")); await tick(); await showM4(h, "b"); h.reply("a", "figure.svg", new Error("stale figure error"), true); await a; assert.equal(h.$("library-figure").hidden, false); assert.equal(h.$("library-figure").src, "blob:b"); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.run("librarySelected.verification = 'verification_failed'"); h.reply("a", "report", m4Report("stale")); await a; assert.equal(h.$("library-results").hidden, true); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(); await showM4(h, "a", "recorded_verification"); assert.equal(h.$("library-acceptance").textContent, "Acceptance unverified; saved snapshot only"); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.run("librarySelected.verified_at = 'new-worker'"); h.reply("a", "report", m4Report("stale worker")); await a; assert.equal(h.$("library-results").hidden, true); checks++;
}
// A current M4 artifact failure withdraws the whole verified snapshot.
{
  const h = harness(), current = h.choose("changed"); h.reply("changed", "report", m4Report("changed")); await tick();
  h.reply("changed", "figure.svg", new Error("Verified reconstructed artifact changed"), true); await current;
  assert.equal(h.$("library-results").hidden, true); assert.equal(h.$("library-figure").hidden, true);
  assert.equal(h.run("librarySelected.verification"), "changed_since_verification"); assert.equal(h.$("library-download-json").disabled, true); checks++;
}
// Periodic validation of unchanged bound M3 bytes preserves open participant details.
{
  const h = harness(); await showM3(h, "stable"); const first = h.$("library-m3-people").children[0]; first.open = true;
  h.run("libraryLastReportCheck = 0"); const recheck = h.run("displayLibraryReport()"); h.reply("stable", "report", m3Report("stable", "m3-compare")); await recheck;
  assert.equal(h.$("library-m3-people").children[0], first); assert.equal(first.open, true); checks++;
}
// Dispatch reports strictly and retain the native full failure accounting.
{
  const h = harness(); await showM3(h, "forecast", "m3-forecast"); assert.equal(h.$("library-m3-results").hidden, false); assert.equal(h.$("library-m4-results").hidden, true); assert.equal(h.$("library-download-svg").hidden, true); assert.equal(h.$("library-figure").hidden, true); assert.equal(h.pending.length, 0);
  assert.equal(h.$("library-m3-people").children.length, 2); assert(h.text(h.$("library-m3-people")).includes("Unattempted 801")); assert(h.text(h.$("library-m3-people")).includes("WorkerFailure")); assert.equal(h.$("library-m3-errors").children[0].children[1].textContent, "unavailable"); assert.match(h.$("library-acceptance").textContent, /incomplete synthetic cohort/); checks++;
}
{
  const h = harness(); await showM3(h, "compare"); assert.equal(h.$("library-m3-candidate-results").children.length, 2); assert(h.text(h.$("library-m3-candidate-results")).includes("no validated sealed child archive")); assert(h.text(h.$("library-m3-candidate-results")).includes("Unattempted 801")); assert(h.text(h.$("library-m3-people")).includes("not_attempted")); assert(h.text(h.$("library-m3-people")).includes("Common-support losses")); assert.equal(h.$("library-m3-denominators").children[1].children[0].textContent, 1602); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(); await showM3(h, "recorded", "m3-compare", "recorded_verification"); assert.match(h.$("library-verification-status").textContent, /Previously verified/); assert.match(h.$("library-acceptance").textContent, /^Recorded snapshot:/); assert.match(h.$("library-freshness").textContent, /not fully rechecked/); checks++;
}
{
  const h = harness(); await showCustom(h, "complete", "m3-forecast", "native_reader_verified", m3Report("complete", "m3-forecast", "native_reader_verified", true)); assert.match(h.$("library-acceptance").textContent, /complete synthetic cohort; prediction quality is a separate assessment/); assert.match(h.$("library-completeness").textContent, /complete/); assert.equal(h.$("library-m3-errors").children[0].children[1].textContent, "1"); checks++;
}
for (const task of ["m3-forecast", "m3-compare", "m4-study-secure", "m5-prognosis"]) {
  const h = harness(); h.context.entry = entry("task", "not_requested", task); h.run("librarySelected = entry; renderLibraryDetail()"); assert.equal(h.$("archive-verify").hidden, false); assert.equal(h.$("archive-verify").disabled, false); checks++;
}
for (const task of ["m4-study", "p1-controller"]) {
  const h = harness(); h.context.entry = entry("old", "recorded_verification", task); h.run("librarySelected = entry; renderLibraryDetail()"); await h.run("displayLibraryReport()"); assert.equal(h.$("archive-verify").hidden, true); assert.equal(h.$("archive-verify").disabled, true); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(), a = h.choose("a", "native_reader_verified", "m3-forecast"); await showM3(h, "b"); h.reply("a", "report", m3Report("a", "m3-forecast")); await a; assert.equal(h.$("library-m3-results").hidden, false); assert.match(h.$("library-detail-title").textContent, /^b$/); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(), a = h.choose("a", "native_reader_verified", "m3-compare"); await showM4(h, "b"); h.reply("a", "report", new Error("stale M3 error"), true); await a; assert.equal(h.$("library-m4-results").hidden, false); assert.equal(h.$("library-notice").textContent, ""); checks++;
}
{
  const h = harness(), a = h.choose("a"); h.reply("a", "report", m4Report("a")); await tick(); await showM3(h, "b"); h.reply("a", "figure.svg", {name: "OLD"}); await a; assert.equal(h.$("library-figure").hidden, true); assert.deepEqual(h.urls, []); checks++;
}
for (const field of ["task", "schema", "report_sha256", "verification", "source_freshness", "verification_scope", "report_completeness"]) {
  const h = harness(), a = h.choose("bad", "native_reader_verified", "m3-compare"), result = m3Report("bad"); result[field] = "mismatch"; h.reply("bad", "report", result); await a; assert.equal(h.$("library-results").hidden, true); assert.equal(h.run("librarySelected.can_view_report"), false); assert.equal(h.$("library-download-json").disabled, true); assert.match(h.$("library-notice").textContent, /does not match/); checks++;
}
{
  const h = harness(), a = h.choose("changed", "native_reader_verified", "m3-forecast"); h.run("librarySelected.artifacts_sha256['report.json'] = 'new'"); h.reply("changed", "report", m3Report("changed", "m3-forecast")); await a; assert.equal(h.$("library-results").hidden, true); checks++;
}
{
  const h = harness(); await showM3(h, "download"); await h.run("downloadLibrary('figure.svg')"); assert.equal(h.pending.length, 0); assert.equal(h.$("library-download-svg").disabled, true); checks++;
}
{
  const h = harness(); await showM3(h, "download"); const operation = h.run("downloadLibrary('report.md')"); h.reply("download", "report.md", {name: "native-md"}); await operation; assert.deepEqual(h.downloads, ["report.md"]); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const download = h.run("downloadLibrary('report.json')"); await showM3(h, "b"); h.reply("a", "report.json", {name: "stale"}); await download; assert.deepEqual(h.downloads, []); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const download = h.run("downloadLibrary('report.json')"); h.run("librarySelected.artifacts_sha256['report.md'] = 'changed'"); h.reply("a", "report.json", {name: "changed"}); await download; assert.deepEqual(h.downloads, []); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const download = h.run("downloadLibrary('report.md')"); h.reply("a", "report.md", new Error("Snapshot withdrawn after source change"), true); await download; assert.equal(h.$("library-results").hidden, true); assert.equal(h.run("librarySelected.verification"), "changed_since_verification"); assert.equal(h.$("library-download-json").disabled, true); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const list = h.run("refreshLibrary()"); const changed = {...entry("a", "changed_since_verification", "m3-compare"), can_view_report: false, report_completeness: "unavailable"}; h.replyList([changed]); await list; assert.equal(h.$("library-results").hidden, true); assert.equal(h.pending.length, 0); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const list = h.run("refreshLibrary()"); await showM3(h, "b"); h.replyList([entry("a")]); await list; assert.equal(h.run("librarySelected.id"), "b"); assert.equal(h.$("library-results").hidden, false); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const list = h.run("refreshLibrary()"); h.replyList([]); await list; assert.equal(h.run("librarySelected"), null); assert.equal(h.$("library-download-json").disabled, true); assert.equal(h.$("library-results").hidden, true); checks++;
}
for (const [state, label, kind] of [["matched", "Supported recorded claims matched", "good"], ["mismatch", "Claimed files changed or missing", "bad"], ["malformed", "Recorded claims invalid", "bad"], ["unsupported", "Recorded claim schema unsupported", "neutral"], ["unavailable", "Recorded claims unavailable", "neutral"]]) {
  const h = harness(); h.context.digest = {status: state, checked_files: 34, manifests: [{manifest: "<script>", schema: "unknown", base: null, claim_shape: null, status: state, checked_files: 0, errors: ["<img onerror='evil'>"], mismatches: ["missing.json"]}]}; h.run("renderLibraryDigests(digest)"); assert.equal(h.$("library-digest-status").textContent, label); assert.equal(h.$("library-digest-status").className, kind); assert(h.text(h.$("library-digest-diagnostics")).includes("<img onerror='evil'>")); assert.match(h.$("library-digest-scope").textContent, /does not cover all archive bytes/); checks++;
}
{
  const h = harness(), result = m3Report("xss", "m3-forecast"); result.native_report.predictor.id = "<img src=x onerror=evil()>"; result.native_report.predictor.reference = "<script>evil()</script>"; result.native_report.evaluation.people.left.execution.worker_error_type = "<svg onload=evil()>"; await showCustom(h, "xss", "m3-forecast", "native_reader_verified", result); assert(h.text(h.$("library-m3-errors")).includes("<img src=x")); assert(h.text(h.$("library-m3-people")).includes("<svg onload")); assert(h.text(h.$("library-m3-candidate-results")).includes("<script>")); checks++;
}
for (const mutate of [
  (r) => { r.common.people = Object.fromEntries(Array.from({length: 129}, (_, i) => ["person" + i, r.common.people.left])); r.common.planned_people = 129; },
  (r) => { r.candidate_order = Array.from({length: 9}, (_, i) => "candidate" + i); },
  (r) => { r.candidate_order = ["trend", "trend"]; },
  (r) => { r.common.people.left.planned_origins = -1; },
  (r) => { r.common.equal_person_metrics.trend.mae = Infinity; },
  (r) => { r.candidates.trend.single_candidate.evaluation.planned_people = 129; },
]) {
  const h = harness(), result = m3Report("bounded"); mutate(result.native_report); await showCustom(h, "bounded", "m3-compare", "native_reader_verified", result); assert.equal(h.$("library-results").hidden, true); assert.equal(h.run("librarySelected.can_view_report"), false); checks++;
}
for (const state of ["active", "m3Pending", "campaignPending", "durablePending", "libraryPending"]) {
  const h = harness(); h.context.entry = entry("busy", "not_requested", "m3-forecast"); h.run("librarySelected = entry"); if (state === "active") h.context.active = {operation: "run", state: "running"}; else if (state === "libraryPending") h.run("libraryPending = true"); else h.context[state] = true;
  h.run("libraryControls()"); assert.equal(h.$("archive-register").disabled, true); assert.equal(h.$("archive-verify").disabled, true); checks++;
}
{
  const h = harness(); await showM3(h, "a"); const a = h.choose("a", "native_reader_verified", "m3-compare"); const b = h.choose("b", "native_reader_verified", "m3-compare"); h.reply("b", "report", m3Report("b")); await b; const newA = h.choose("a", "native_reader_verified", "m3-compare"); h.reply("a", "report", m3Report("a")); await a; assert.equal(h.$("library-results").hidden, true); h.reply("a", "report", m3Report("a")); await newA; assert.equal(h.$("library-results").hidden, false); checks++;
}
// M5 remains an artifact-only, full-roster synthetic view with explicit paired support.
for (const mode of ["complete", "mixed", "zero", "interrupted", "missing-repeat"]) {
  const h = harness(); await showM5(h, mode, mode);
  assert.equal(h.$("library-results").hidden, false); assert.equal(h.$("library-m5-results").hidden, false); assert.equal(h.$("library-m3-results").hidden, true); assert.equal(h.$("library-m4-results").hidden, true);
  assert.equal(h.$("library-m5-people").children.length, 32); assert.equal(h.$("library-m5-attempts").children.length, 7); assert.equal(h.$("library-m5-errors").children.length, 4); assert.equal(h.$("library-download-svg").hidden, true); assert.equal(h.pending.length, 0);
  const people = h.text(h.$("library-m5-people")), attempts = h.text(h.$("library-m5-attempts")), scope = h.$("library-m5-analysis-scope").textContent;
  assert(people.includes("Development participant; no evaluation prediction attempts")); assert(people.includes("Excluded evaluation participant; no prediction attempts planned")); assert(people.includes("Later infusions (days): 150")); assert(attempts.includes("Attempt 1:")); assert(attempts.includes("Attempt 2:"));
  assert(h.text(h.$("library-m5-errors")).includes("all 7 eligible evaluation")); assert(h.text(h.$("library-m5-errors")).includes("same paired subset")); assert(scope.includes("no advancement threshold"));
  assert(h.text(h.$("library-m5-declaration")).includes("Rights basis (self-attested)")); assert(h.text(h.$("library-m5-declaration")).includes("development_only"));
  if (mode === "mixed") { assert(attempts.includes("not_reproducible")); assert(attempts.includes("timeout")); assert(attempts.includes("invalid_output")); assert(attempts.includes('"python_version":"3.12.9"')); assert.equal(h.$("library-m5-errors").children[3].children[1].textContent, "-1"); }
  if (mode === "zero") { assert(scope.includes("execution accounting: complete")); assert(scope.includes("No reproducible pairs")); assert.equal(h.$("library-m5-errors").children[1].children[1].textContent, "null"); assert.match(h.$("library-acceptance").textContent, /incomplete synthetic comparison/); }
  if (mode === "interrupted") { assert(attempts.includes("interrupted")); assert(attempts.includes("not_attempted")); assert(attempts.includes("Saved prediction: 10 U/day")); }
  if (mode === "missing-repeat") assert(attempts.includes("incomplete"));
  checks++;
}
{
  const h = harness(); await showM5(h, "recorded", "complete", "recorded_verification"); assert.match(h.$("library-acceptance").textContent, /^Recorded snapshot:/); assert.match(h.$("library-verification-status").textContent, /Previously verified/); assert.match(h.$("library-freshness").textContent, /not fully rechecked/); checks++;
}
{
  const h = harness(); await showM5(h, "stable"); const row = h.$("library-m5-people").children[0]; row.open = true; h.context.document.activeElement = row.children[0];
  h.run("libraryLastReportCheck = 0"); const recheck = h.run("displayLibraryReport()"); assert.equal(h.$("library-results").hidden, false); h.reply("stable", "report", m5Report("stable")); await recheck;
  assert.equal(h.$("library-m5-people").children[0], row); assert.equal(row.open, true); assert.equal(h.context.document.activeElement, row.children[0]); checks++;
}
for (const mutate of [
  (r) => { r.native_report.human_execution_authorized = true; },
  (r) => { r.native_report.treatment_effect_or_cure_estimated = true; },
  (r) => { r.native_report.claim = "human_results"; },
  (r) => { r.native_report.schema = "m5-other/1"; r.schema = r.native_report.schema; },
  (r) => { r.native_report.people.pop(); },
  (r) => { r.native_report.people[1].alias = r.native_report.people[0].alias; },
  (r) => { r.native_report.people[0].split = "evaluation"; },
  (r) => { r.native_report.development_eligible_count = 21; },
  (r) => { r.native_report.evaluation_predictions.push(r.native_report.evaluation_predictions[0]); },
  (r) => { r.native_report.evaluation_predictions[0].alias = "SYN001"; },
  (r) => { r.native_report.evaluation_predictions[0].attempts[0].attempt = true; },
  (r) => { r.native_report.evaluation_predictions[0].attempts[0].prediction_u_day = Infinity; },
  (r) => { r.native_report.evaluation_predictions[0].attempts[0].runtime.python_version = "3.12.8"; },
  (r) => { r.native_report.evaluation_predictions[0].candidate_status = "failed"; },
  (r) => { r.native_report.candidate_execution_complete = "true"; },
  (r) => { r.native_report.paired_count = 7; },
  (r) => { r.native_report.candidate_coverage = 1; },
  (r) => { r.native_report.baseline_mae_paired_u_day = null; },
  (r) => { r.model_declaration.source_sha256 = "e".repeat(64); },
  (r) => { r.model_declaration.state_sha256 = "e".repeat(64); },
  (r) => { r.model_declaration.model_id = "other"; },
  (r) => { r.model_declaration.model_id = true; r.native_report.model_id = true; },
  (r) => { r.model_declaration.runtime.python_major_minor = 3.12; },
  (r) => { r.native_report.implementation_sha256["unknown-file"] = r.native_report.implementation_sha256["source-run.py"]; delete r.native_report.implementation_sha256["source-run.py"]; },
  (r) => { r.native_report.provenance.schema = "unknown/1"; },
  (r) => { r.model_declaration.output_unit = "mg/dL"; },
  (r) => { r.model_declaration.rights_basis = ""; },
  (r) => { r.model_declaration.rights_basis = "x".repeat(501); },
  (r) => { r.model_declaration.training.phase = "evaluation"; },
  (r) => { r.model_declaration.training.participant_aliases[0] = "SYN008"; },
  (r) => { r.model_declaration.runtime.dependencies = ["numpy"]; },
  (r) => { r.model_declaration_sha256 = "a".repeat(64); },
]) {
  const h = harness(), report = m5Report("invalid"); mutate(report); await showCustom(h, "invalid", "m5-prognosis", "native_reader_verified", report); assert.equal(h.$("library-results").hidden, true); assert.equal(h.$("library-download-json").disabled, true); assert.equal(h.$("library-m5-declaration").children.length, 0); assert.equal(h.run("librarySelected.can_view_report"), false); checks++;
}
{
  const h = harness(), report = m5Report("zero-invalid", "zero"); report.native_report.candidate_mae_paired_u_day = 0; await showCustom(h, "zero-invalid", "m5-prognosis", "native_reader_verified", report); assert.equal(h.$("library-results").hidden, true); checks++;
}
{
  const h = harness(), report = m5Report("unit-label"); report.model_declaration.rights_basis = "<img onerror=evil()>"; await showCustom(h, "unit-label", "m5-prognosis", "native_reader_verified", report); assert(h.text(h.$("library-m5-declaration")).includes("<img onerror=evil()>")); checks++;
}
{
  const h = harness(); await showM5(h, "download"); await h.run("downloadLibrary('figure.svg')"); assert.equal(h.pending.length, 0);
  for (const name of ["report.json", "report.md"]) { const download = h.run("downloadLibrary('" + name + "')"); h.reply("download", name, {name: "native-" + name}); await download; }
  assert.deepEqual(h.downloads, ["report.json", "report.md"]); checks++;
}
{
  const h = harness(); await showM5(h, "a"); const download = h.run("downloadLibrary('report.md')"); await showM3(h, "b"); h.reply("a", "report.md", {name: "obsolete"}); await download; assert.deepEqual(h.downloads, []); assert.equal(h.$("library-results").hidden, false); checks++;
}
{
  const h = harness(); await showM5(h, "a"); const download = h.run("downloadLibrary('report.json')"); h.run("librarySelected.model_declaration_sha256 = 'changed'"); h.reply("a", "report.json", {name: "stale-declaration"}); await download; assert.deepEqual(h.downloads, []); checks++;
}
{
  const h = harness(); await showM5(h, "a"); const download = h.run("downloadLibrary('report.md')"); h.reply("a", "report.md", new Error("Current snapshot changed"), true); await download; assert.equal(h.$("library-results").hidden, true); assert.equal(h.$("library-m5-declaration").children.length, 0); assert.equal(h.$("library-m5-json").textContent, ""); checks++;
}
{
  const h = harness(), a = h.choose("a", "native_reader_verified", "m5-prognosis"); await showM3(h, "b"); h.reply("a", "report", m5Report("a")); await a; assert.equal(h.$("library-m3-results").hidden, false); assert.equal(h.$("library-results").hidden, false); checks++;
}
{
  const h = harness(), a = h.choose("a", "native_reader_verified", "m5-prognosis"); await showM4(h, "b"); h.reply("a", "report", new Error("Obsolete M5 error"), true); await a; assert.equal(h.$("library-m4-results").hidden, false); assert.equal(h.$("library-notice").textContent, ""); checks++;
}
{
  const h = harness(), a = h.choose("a", "native_reader_verified", "m3-forecast"); await showM5(h, "b"); h.reply("a", "report", m3Report("a", "m3-forecast")); await a; assert.equal(h.$("library-m5-results").hidden, false); checks++;
}
{
  const h = harness(); await showM5(h, "a"); const list = h.run("refreshLibrary()"); const changed = entry("a", "native_reader_verified", "m5-prognosis"); changed.model_declaration_sha256 = "c".repeat(64); h.replyList([changed]); await tick(); assert.equal(h.$("library-results").hidden, true); h.reply("a", "report", m5Report("a")); await list;
  assert.equal(h.$("library-results").hidden, true); assert.equal(h.$("library-m5-declaration").children.length, 0); assert.equal(h.$("library-download-json").disabled, true); checks++;
}
{
  const h = harness(); h.context.updateControls = () => {}; h.run("refreshLibrary = async () => {}");
  h.context.pointer = {...entry("old"), availability: "unavailable", can_verify: false, can_view_report: false};
  h.run("librarySelected = pointer; libraryEntries = [pointer]");
  const hide = h.run("changeLibraryVisibility()"); assert.equal(h.pending[0].body.hidden, true);
  h.reply("old", "visibility", {...h.context.pointer, hidden: true}); await hide;
  assert.equal(h.$("archive-visibility").textContent, "Restore reference"); assert.match(h.$("library-notice").textContent, /archive files were kept/);
  h.run("libraryEntries = [librarySelected]; renderLibraryList()"); assert.equal(h.$("library-list").children[0].name, "p");
  h.$("library-show-hidden").checked = true; h.run("renderLibraryList()"); assert.equal(h.$("library-list").children[0].name, "button");
  const restore = h.run("changeLibraryVisibility()"); assert.equal(h.pending[0].body.hidden, false);
  h.reply("old", "visibility", {...h.context.pointer, hidden: false}); await restore;
  assert.equal(h.$("archive-visibility").textContent, "Hide reference"); assert.equal(h.$("archive-verify").disabled, true); checks++;
}
// The two observation tasks have different native report schemas and validators.
for(const [task,schema,validator,renderer]of [
  ["mmtt-sensitivity","opent1d.observation-analysis/1","obsValidateNative","renderObservationReport"],
  ["mmtt-sampling","opent1d.mmtt-sampling/1","samplingValidateNative","renderSamplingReport"],
]){
  const h=harness(),calls=[];
  for(const name of ["obsValidateNative","samplingValidateNative"])
    h.context[name]=r=>{assert.equal(name,validator,"Wrong native report validator selected");assert.equal(r.schema,schema);calls.push(name);};
  for(const name of ["renderObservationReport","renderSamplingReport"])
    h.context[name]=(r,target)=>{assert.equal(name,renderer);target.append({textContent:r.schema,children:[]});calls.push(name);};
  const native={schema,coverage:{complete_cohort:false}}, id="observation-"+task;
  await showCustom(h,id,task,"native_reader_verified",{task,schema,native_report:native,verification:"native_reader_verified",verification_scope:"verified_snapshot",source_freshness:"not_rechecked_since_worker",report_completeness:"incomplete",report_sha256:"json-"+id});
  assert.deepEqual(calls,[validator,renderer]);assert.equal(h.$("library-results").hidden,false);assert(h.text(h.$("library-observation-results")).includes(schema));checks++;
}
process.stdout.write(JSON.stringify({checks, passed: true, scope: "controlled shipped archive/M3/M5 rendering, digest labels, roster bounds, snapshot withdrawal, async and M4 regression functions; no browser or scientific execution"}));
