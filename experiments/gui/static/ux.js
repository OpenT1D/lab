"use strict";

// Presentation only: saved native values and existing route authorities stay separate.
function uxText(value, fallback = "Unavailable") {
  return value === null || value === undefined ? fallback : String(value).replaceAll("_", " ");
}
function uxAnalysisStatus(value) {
  return ({native_reader_verified: "snapshot checked", verified_snapshot: "snapshot checked", recorded_verification: "previously checked; recheck", not_requested: "not checked", verifying: "checking", checking: "checking", changed_since_verification: "changed; recheck", verification_failed: "check failed", reader_mismatch: "compatible reader needed"})[value] || "unavailable";
}
// MMTT labels describe local execution and saved-byte checks, never model validity.
function mmttDisplayName(record, fallback) {
  return typeof record?.display_name === "string" && record.display_name.trim()
    ? record.display_name.trim() : fallback;
}
function mmttVerificationLabel(value) {
  return ({native_reader_verified: "Saved report checked", recorded_verification: "Previously checked; check again", not_requested: "Saved report not checked", verifying: "Checking saved report", changed_since_verification: "Saved evidence changed; check again", verification_failed: "Saved report check failed"})[value] || "Saved report check unavailable";
}
function mmttExecutionLabel(entry) {
  const state = entry?.state;
  if (state === "completed") return "Analysis finished · " + ({complete: "results complete", incomplete: "results incomplete", unavailable: "results unavailable"}[entry.report_completeness] || "result completeness unknown");
  return ({queued: "Waiting to start", running: "Analysis running", cancelling: "Stopping analysis", cancelled: "Analysis cancelled", interrupted: "Analysis interrupted", interrupted_owner_unavailable: "Analysis interrupted; original process unavailable", unsealed_or_unavailable: "Analysis stopped; saved report unavailable", failed: "Execution failed"})[state] || "Execution status unavailable";
}
function uxEvidenceRows(kind, report, verification, execution) {
  const checked = ["native_reader_verified", "verified_snapshot"].includes(verification);
  const analysis = report.common || report.evaluation;
  let coverage = "Not available in this saved report";
  if (kind === "m5") coverage = report.paired_count + " / " + report.evaluation_eligible_count + " eligible evaluation participants with repeated paired predictions";
  else if (analysis) coverage = analysis.contributing_people + " / " + analysis.planned_people + " participants on the report's comparison support";
  else if (report.denominators) coverage = uxText(report.denominators.accepted_source_scenarios, "—") + " / " + uxText(report.denominators.source_scenarios, "—") + " model / condition cases passed numerical checks";
  else if (report.planned_slots !== undefined) coverage = uxText(report.accepted_slots, "—") + " / " + report.planned_slots + " planned repeats accepted";
  const rows = [["Execution", kind === "m5" ? (report.candidate_execution_complete ? "All planned prediction attempts accounted for" : "Incomplete prediction execution") : uxText(execution, "Not recorded separately in this report")], ["Comparison coverage", coverage], ["Saved analysis", checked ? "Checked in the recorded snapshot; coverage and model quality are separate" : verification === "recorded_verification" ? "Previously checked; check again for current verification" : ["changed_since_verification", "verification_failed"].includes(verification) ? "Verification unavailable or withdrawn; inspect the retained error" : "Not currently verified"]];
  if (kind === "m4" && report.status) rows.push(["Native report status", uxText(report.status)]);
  if (report.passed !== undefined) rows.push(["Numerical checks", report.passed ? "Passed in this saved report" : "Failed or incomplete in this saved report"]);
  return rows;
}
function uxRenderEvidence(id, kind, report, verification, execution) {
  const target = document.getElementById(id); if (!target) return;
  const rows = uxEvidenceRows(kind, report, verification, execution), key = JSON.stringify(rows);
  if (target.dataset.revision === key) return;
  target.dataset.revision = key;
  const list = document.createElement("dl");
  for (const [label, value] of rows) { const term = document.createElement("dt"), detail = document.createElement("dd"); term.textContent = label; detail.textContent = value; list.append(term, detail); }
  target.replaceChildren(list);
}
function uxActivityTime(entry, jobs) {
  const times = [entry.created_at, entry.updated_at, entry.verified_at, entry.checked_at];
  for (const job of jobs || []) if (job.id === entry.id || job.id === entry.last_job || job.id === entry.snapshot_job || job.archive_job === entry.id || job.request?.campaign_id === entry.id || job.request?.entry_id === entry.id || job.request?.entry?.id === entry.id) times.push(job.created_at, job.started_at, job.finished_at);
  const saved = times.filter(value => typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)).map(value => Date.parse(value)).filter(Number.isFinite);
  return saved.length ? Math.max(...saved) : null;
}
function uxResultItems(data) {
  const items = [], jobs = data.jobs || [];
  for (const job of jobs) if (job.operation === "run") items.push({kind: "study", id: job.id, label: "Insulin secretion", activity: uxActivityTime(job, jobs), state: job.state, detail: "Own workspace · execution " + uxText(job.state) + " · analysis " + uxAnalysisStatus(job.verification)});
  for (const entry of data.m3 || []) items.push({kind: "m3", id: entry.id, label: entry.task === "m3-compare" ? "Glucose model comparison" : "Glucose forecast", activity: uxActivityTime(entry, jobs), state: entry.execution_state, detail: "Own workspace · execution " + uxText(entry.execution_state) + " · analysis " + uxAnalysisStatus(entry.verification)});
  for (const [kind, label] of [["sampling", "Fewer measurement times"], ["observations", "Paired meal-test analysis"]]) for (const entry of data[kind] || []) {
    const name = mmttDisplayName(entry, label);
    items.push({kind, id: entry.id, label: name === label ? label : name + " · " + label, activity: uxActivityTime(entry, jobs), state: entry.state, detail: "Own workspace · " + mmttExecutionLabel(entry) + " · " + mmttVerificationLabel(entry.verification)});
  }
  for (const entry of data.campaigns || []) items.push({kind: "campaign", id: entry.id, label: "Repeated secretion study", activity: uxActivityTime(entry, jobs), state: entry.status, detail: "Own workspace · " + uxText(entry.accepted_slots, "—") + " / " + entry.planned_slots + " accepted repeats · " + uxAnalysisStatus(entry.verification)});
  for (const entry of data.durable || []) items.push({kind: "durable", id: entry.id, label: "Saved package · " + entry.path, activity: uxActivityTime(entry, jobs), state: entry.availability, detail: "Read-only package · bytes " + uxText(entry.integrity) + " · analysis " + uxText(entry.reconstruction)});
  for (const item of items) item.label += " · " + (item.activity === null ? "Time not recorded" : new Date(item.activity).toLocaleString()) + " · " + item.id.slice(-8);
  return items.sort((a, b) => ((b.activity ?? -Infinity) - (a.activity ?? -Infinity)) || 0);
}
function uxRefreshResults(data, open) {
  const target = document.getElementById("own-results-list"); if (!target) return;
  target.openResult = open;
  const items = uxResultItems(data), revision = JSON.stringify(items);
  if (target.dataset.revision === revision) return;
  const focused = document.activeElement;
  const ownsFocus = !!focused && target.contains(focused);
  const previousButtons = Array.from(target.children).filter(node => node.dataset.resultKey);
  const focusedButton = ownsFocus ? previousButtons.find(node => node.contains(focused)) : null;
  const focusKey = focusedButton?.dataset.resultKey;
  const focusIndex = previousButtons.indexOf(focusedButton);
  const restoreFocus = () => {
    if (!ownsFocus || target.contains(document.activeElement)) return;
    const buttons = Array.from(target.children).filter(node => node.dataset.resultKey);
    const button = buttons.find(node => node.dataset.resultKey === focusKey)
      || buttons[Math.max(0, Math.min(focusIndex, buttons.length - 1))];
    if (button) button.focus({preventScroll: true});
    else { target.tabIndex = -1; target.focus({preventScroll: true}); }
  };
  target.dataset.revision = revision;
  const old = new Map(Array.from(target.children).filter(node => node.dataset.resultKey).map(node => [node.dataset.resultKey, node]));
  const wanted = new Set(items.map(item => item.kind + ":" + item.id));
  for (const node of Array.from(target.children)) if (!wanted.has(node.dataset.resultKey)) node.remove();
  if (!items.length) {
    const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = "Your experiment results will appear here, including failed and interrupted attempts. Start an experiment or add an existing archive below."; target.append(empty); restoreFocus(); return;
  }
  for (const [index, item] of items.entries()) {
    const key = item.kind + ":" + item.id;
    let button = old.get(key);
    if (!button) {
      button = document.createElement("button"); button.type = "button"; button.className = "library-entry"; button.dataset.resultKey = key;
      const title = document.createElement("strong"), detail = document.createElement("small"); button.append(title, detail);
      button.addEventListener("click", () => target.openResult({kind: button.dataset.resultKind, id: button.dataset.resultId}));
    }
    button.dataset.resultKind = item.kind; button.dataset.resultId = item.id;
    button.children[0].textContent = item.label; button.children[1].textContent = item.detail;
    if (target.children[index] !== button) target.insertBefore(button, target.children[index] || null);
  }
  restoreFocus();
}
function uxRevealError(message, target) {
  const scope = target?.id || "notice";
  const id = scope === "m3-notice" ? (/predictor|candidate/i.test(message) ? "m3-candidates" : /budget|deadline|timeout/i.test(message) ? "m3-timeout" : "m3-input-picker") : scope === "campaign-notice" ? (/repeat|repetition/i.test(message) ? "campaign-repeats" : /budget|deadline|timeout/i.test(message) ? "campaign-budget" : "campaign-cell-id") : scope === "notice" ? (/scenario|condition/i.test(message) ? "study-form" : /source|model|declaration|frozen/i.test(message) ? "sources" : /budget|deadline|timeout/i.test(message) ? "stage-budget" : null) : null;
  const field = id && document.getElementById(id);
  if (field) { let parent = field.parentElement; while (parent) { if (parent.tagName === "DETAILS") parent.open = true; parent = parent.parentElement; } }
  if (target && message) { target.tabIndex = -1; target.focus({preventScroll: false}); }
}
function uxGraphSeries(report) {
  const series = [];
  const values = data => ({times_min: data?.times, glucose_mg_dl: data?.glucose, insulin_pmol_l: data?.insulin, cpeptide_pmol_l: data?.cpeptide});
  const declared = report.configuration?.sources?.map(source => [source.id, report.sources?.[source.id]]) || Object.entries(report.sources || {});
  const accepted = declared.filter(([, source]) => source?.accepted);
  const conditions = source => report.scenarios?.map(scene => [scene.id, source.curves?.[scene.id]]) || Object.entries(source.curves || {});
  for (const [model, source] of accepted) {
    for (const [condition, curves] of conditions(source)) series.push({label: model + " · " + condition, data: values(curves?.candidate)});
  }
  // The native SVG draws both controls from the first accepted model's saved curves.
  if (accepted.length) for (const [condition, curves] of conditions(accepted[0][1])) for (const [mode, label] of [["host_constant_basal", "Host constant basal"], ["bc008_reference", "BC-008 reference"]]) series.push({label: label + " · " + condition, data: values(curves?.[mode])});
  let count = 0;
  for (const {data} of series) {
    if (!["times_min", "glucose_mg_dl", "insulin_pmol_l", "cpeptide_pmol_l"].every(key => Array.isArray(data[key]) && data[key].length === data.times_min?.length && data[key].every(Number.isFinite))) throw new Error("Saved graph values are incomplete or incompatible. Download the original report for inspection.");
    count += data.times_min.length;
  }
  if (count > 50000) throw new Error("This graph contains too many values for the table view. Download the original JSON report.");
  return series;
}
function uxRenderGraph(id, report) {
  const target = document.getElementById(id); if (!target) return;
  const series = uxGraphSeries(report); target.replaceChildren();
  if (!series.length) { target.textContent = "No accepted model curves are present in this report. Inspect failed and incomplete cases in the retained source outcomes."; return; }
  for (const item of series) {
    const details = document.createElement("details"), summary = document.createElement("summary"), wrap = document.createElement("div"), table = document.createElement("table"), caption = document.createElement("caption"), head = document.createElement("thead"), header = document.createElement("tr"), body = document.createElement("tbody");
    summary.textContent = item.label + " · " + item.data.times_min.length + " saved time points";
    caption.textContent = item.label + ": original saved values, without interpolation or new analysis";
    for (const name of ["Time (min)", "Glucose (mg/dL)", "Insulin (pmol/L)", "C-peptide (pmol/L)"]) { const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = name; header.append(cell); }
    for (let i = 0; i < item.data.times_min.length; i++) { const row = document.createElement("tr"); for (const key of ["times_min", "glucose_mg_dl", "insulin_pmol_l", "cpeptide_pmol_l"]) { const cell = document.createElement("td"); cell.textContent = String(item.data[key][i]); row.append(cell); } body.append(row); }
    head.append(header); table.append(caption, head, body); wrap.className = "source-table-wrap"; wrap.append(table); details.append(summary, wrap); target.append(details);
  }
}

function uxPhaseDetail(job) {
  if (job?.state !== "running") return null;
  const phase = job.phase;
  if (phase?.schema !== "opent1d.packaged-admission/1") return null;
  if (phase.phase === "preparing") return "Checking configuration…";
  if (phase.phase === "auditing") return "Checking installed components…";
  if (phase.phase === "executing") return phase.operation === "reconstruct" ? "Checking saved analysis…" : "Running analysis…";
  return null;
}
