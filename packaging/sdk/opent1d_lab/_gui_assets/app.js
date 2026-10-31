"use strict";
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="opent1d-token"]').content;
const names = {"mmtt-sampling": "Fewer meal-test measurement times", "mmtt-sensitivity": "Paired meal-test assumptions", "m4-study-installed": "Synthetic secretion models", "m4-study-secure": "Historical secretion study"};
const cases = {"mmtt-sampling": [["information-loss", "Invented information loss"], ["constant", "Constant-input control"], ["incomplete", "Incomplete measurements"], ["steep-response", "Steep-response boundary control"]], "mmtt-sensitivity": [["complete", "Invented paired visit"], ["censored", "Invented paired visit with censored measurements"]], "m4-study-installed": [["fasting", "Fasting"], ["gastric_load_15g", "15 g initial gastric amount"]]};
const context = {"mmtt-sampling": "Compare full and reduced actual measurement times using the same estimator and assumptions. Development-only selection is frozen before analysis; evaluation results do not select schedules. Whole-body total secretion including basal over 0–120 minutes (pmol). Full curves are references, not biological truth. Invented data only.", "mmtt-sensitivity": "Whole-body total endogenous secretion, including basal, over observed 0–120 minutes (pmol). Change is follow-up minus baseline. Three required assumption variants; 128 perturbations with seed 117. Invented data only.", "m4-study-installed": "Both supplied sources · adult#001 · 240 minutes · 961 quarter-minute samples. The gastric amount is an initial condition, not a timed meal. Native runtimes must be prepared separately."};
let data = null, selected = null, draft = null, selectedPlan = null, currentReport = null, pending = false, pendingOperation = null, watched = null, loaded = false;
let imageURL = null, parentDraft = null, refreshIssued = 0, refreshApplied = 0, reportIssued = 0;
const handled = new Set();
const invalidReports = new Set();
function invalidatePlanView() { $("plan-inspector").classList.add("hidden"); $("plan-inspector").open = false; $("plan-details").textContent = ""; $("readiness").textContent = "Check this frozen plan with the current runtime selection before execution."; }
function element(tag, text, cls) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; }
function notice(message, error = false) { $("notice").textContent = message; $("notice").className = "notice" + (error ? " error" : ""); if (error) $("notice").focus(); }
function withdrawReport(cancelLoading = true) { if (cancelLoading) reportIssued++; currentReport = null; $("report-text").replaceChildren(); $("child-reports").replaceChildren(); if (imageURL) URL.revokeObjectURL(imageURL); imageURL = null; $("report-figure").src = ""; $("saved-report").classList.add("hidden"); }
function reportRefused(error, record = currentReport) { if (record?.id) invalidReports.add(record.id); const known = data?.reports?.find(item => item.id === record?.id); if (known) known.valid = false; if (record?.id !== currentReport?.id) return; withdrawReport(false); notice(error.message, true); }
async function request(url, body) {
  const options = {headers: {"X-OpenT1D-Token": token}, cache: "no-store"};
  if (body !== undefined) { options.method = "POST"; options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); }
  const response = await fetch(url, options);
  if (!response.ok) { const error = await response.json(); throw new Error(error.error || "Action refused"); }
  return response;
}
async function action(operation, arguments_ = {}, project = selected) {
  if (pending || data?.active) { notice("Another action is still running. Stop the run or wait for it to finish.", true); return; }
  if (operation === "check") invalidatePlanView();
  if (["verify", "comparison_verify", "study_verify"].includes(operation)) reportIssued++;
  pendingOperation = operation; pending = true; render();
  try {
    const route = ["draft_create", "draft_save"].includes(operation) ? "/api/drafts" : "/api/actions";
    const response = await request(route, {request_id: crypto.randomUUID(), operation, project, arguments: arguments_});
    const job = await response.json(); watched = job.id; handled.delete(job.id);
    await refresh();
    let finished = job;
    while (finished.status === "running") { await new Promise(resolve => setTimeout(resolve, 100)); finished = await (await request("/api/jobs/" + job.id)).json(); }
    await refresh();
    return finished;
  } catch (error) { notice(error.message, true); return {status: "error", error: error.message}; }
  finally { pending = false; pendingOperation = null; render(); }
}
function project() { return data?.projects.find(item => item.id === selected); }
function label(plan) { return project()?.labels[plan.id] || `${names[plan.task] || plan.task} · ${plan.slots.join(", ")}`; }
function options(select, values, chosen) { select.replaceChildren(...values.map(([value, text]) => { const node = element("option", text); node.value = value; return node; })); if (values.some(([value]) => value === chosen)) select.value = chosen; }
function updateTask() { const task = $("task").value; options($("example-case"), cases[task]); $("task-context").textContent = context[task]; }
async function refresh() {
  try {
    const issued = ++refreshIssued;
    const incoming = await (await request("/api/state")).json();
    for (const record of incoming.reports || []) if (!record.valid) invalidReports.add(record.id);
    for (const record of data?.reports || []) if (invalidReports.has(record.id)) record.valid = false;
    if (currentReport && invalidReports.has(currentReport.id)) withdrawReport(false);
    if (issued < refreshApplied || (data && incoming.runtime_revision < data.runtime_revision)) return;
    refreshApplied = issued;
    if (data?.runtime_revision !== incoming.runtime_revision || data?.runtime_attachment !== incoming.runtime_attachment) invalidatePlanView();
    for (const record of incoming.reports || []) if (invalidReports.has(record.id)) record.valid = false;
    data = incoming;
    if (currentReport && !data.reports?.some(record => record.id === currentReport.id && record.valid)) withdrawReport(false);
    if (!loaded) { for (const job of data.jobs) if (job.status !== "running") handled.add(job.id); loaded = true; }
    for (const job of data.jobs) if (job.id === watched && job.status !== "running" && !handled.has(job.id)) {
      handled.add(job.id); watched = null;
      if (job.status === "error") { notice(job.error, true); continue; }
      if (job.operation === "check") {
        const checked = job.check_context;
        if (!checked || checked.project !== selected || checked.plan !== selectedPlan || checked.runtime_revision !== data.runtime_revision || checked.runtime_attachment !== data.runtime_attachment) { notice("Readiness result belongs to an earlier selection. Check the current frozen plan again."); continue; }
      }
      if (job.project && job.project !== selected) { withdrawReport(); selected = job.project; invalidatePlanView(); }
      const result = job.result;
      if (job.operation === "prepare") { if (globalThis.workbench) await workbench.open(result.id, false); else { draft = result; $("plan-name").value = `${names[result.task]} — ${cases[result.task].find(row => row[0] === result.case)[1]}`; } notice(draft?.validation?.valid === false ? "Concept saved. Correct its validation errors before freezing." : "Inputs validated. Inspect the assumptions and freeze a plan before running."); }
      else if (job.operation.startsWith("draft_") || job.operation === "derive") { notice(job.operation === "draft_validate" ? "Validation finished. Inspect the saved concept and its diagnostics." : "Study concept saved. No frozen plan was changed."); }
      else if (job.operation === "freeze") { selectedPlan = result.plan; draft = null; globalThis.workbench?.close(); invalidatePlanView(); notice("Plan frozen. The original inputs and assumptions are retained."); }
      else if (job.operation === "plan") { if (typeof result.scientific_input_text === "string") { const metadata = {...result}; delete metadata.scientific_input; delete metadata.scientific_input_text; $("plan-details").textContent = JSON.stringify(metadata, null, 2) + "\n\nScientific inputs (exact saved JSON):\n" + result.scientific_input_text; } else $("plan-details").textContent = JSON.stringify(result, null, 2); $("plan-inspector").classList.remove("hidden"); $("plan-inspector").open = true; }
      else if (job.operation === "check") { $("readiness").textContent = result.runtimes_ready ? "Ready for explicit execution. This check did not run a model or install dependencies." : "Native execution is unavailable with the current selection. Configure reviewed runtimes; an explicit run without them retains an admission failure and performs no setup."; notice(result.runtimes_ready ? "Readiness check passed." : "Readiness check found unavailable native runtimes.", !result.runtimes_ready); }
      else if (job.operation === "run") { notice(`Execution ${result.result.execution_status}; scientific evidence ${result.result.completeness}. Verify the saved report explicitly to inspect its conclusions.`, result.result.completeness !== "complete"); }
      else if (job.operation === "verify") { if (await showReport(result.report)) notice("Saved analysis verified. This did not run the model again."); }
      else if (job.operation.startsWith("comparison_")) { if (job.operation === "comparison_verify") { if (await showReport(result.report)) notice("Comparison reconstructed from fixed native evidence. Every planned member is retained."); } else notice("Comparison metadata read or saved. No model was run."); }
      else if (job.operation.startsWith("study_")) { if (job.operation === "study_verify") { if (await showReport(result.report)) notice("Connected study verified. Known inputs, native failures and all planned cases are retained."); } else notice("Connected study metadata saved or read. Run each stage explicitly."); }
      else if (job.operation === "relocate") { selectedPlan = null; currentReport = null; notice("The complete project copy is open. Verify its saved reports before removing the original."); }
      else if (job.operation === "attach") { invalidatePlanView(); notice("Prepared dependencies verified and attached to this application."); }
      else if (job.operation === "select_attachment") { invalidatePlanView(); notice("Attachment selected. Check a frozen plan to validate it for this application."); }
      else if (job.operation === "clear_attachment") { invalidatePlanView(); notice("Runtime selection cleared. Saved reports remain readable."); }
      else { draft = null; selectedPlan = null; currentReport = null; invalidatePlanView(); notice("Saved project opened. No experiment was run."); }
    }
    render();
  } catch (error) { notice(error instanceof TypeError ? "Connection unavailable. Inspect the server terminal before assuming a run stopped. Reload this page after restarting the server." : error.message, true); }
}
function badge(text, status) { return element("span", text, "tag" + (status === "incomplete" || status === "unfinished" ? " warn" : status === "failed" ? " bad" : "")); }
function render() {
  if (!data) return;
  const busy = pending || !!data.active || data.closing;
  $("project-count").textContent = data.projects.length;
  $("project-list").replaceChildren(...data.projects.map(item => { const button = element("button", item.name, "project-choice" + (item.id === selected ? " selected" : "")); button.disabled = busy; button.onclick = () => { withdrawReport(); selected = item.id; selectedPlan = null; draft = null; invalidatePlanView(); action("refresh", {}, item.id); }; return button; }));
  const chosen = project();
  $("welcome").classList.toggle("hidden", !!chosen); $("project-view").classList.toggle("hidden", !chosen);
  const active = data.jobs.find(job => job.id === data.active);
  $("job").classList.toggle("hidden", !active && !data.closing);
  if (active) { $("job-title").textContent = active.cancel_requested ? "Stop requested" : "Action in progress"; $("job-detail").textContent = `${active.phase} · ${active.elapsed_seconds}s elapsed. Native phase progress is not estimated.`; }
  else if (data.closing) { $("job-title").textContent = "Server stopping"; $("job-detail").textContent = "Waiting for the SDK action and its process cleanup. Keep the terminal open."; }
  $("cancel-run").disabled = !active?.cancelable || active.cancel_requested;
  $("cancel-run").classList.toggle("hidden", !active?.cancelable);
  for (const button of document.querySelectorAll("form button, #refresh-project, #inspect-plan, #check-plan, #run-plan, #clear-runtime")) button.disabled = busy;
  $("stop-server").disabled = data.closing;
  $("application").textContent = `Internal SDK · ${data.installation.build_label} · ${data.installation.source.revision.slice(0, 8)}`;
  $("workspace-path").textContent = data.workspace;
  if (!chosen) return;
  $("selected-name").textContent = chosen.name; $("selected-path").textContent = chosen.path;
  const plans = chosen.info?.plans || [];
  if (!plans.some(plan => plan.id === selectedPlan)) { selectedPlan = plans[0]?.id || null; invalidatePlanView(); }
  options($("plan-select"), plans.length ? plans.map(plan => [plan.id, label(plan)]) : [["", "No frozen plans yet"]], selectedPlan);
  $("plan-select").disabled = busy || !plans.length;
  const selectedData = plans.find(plan => plan.id === selectedPlan);
  const parent = plans.find(plan => plan.id === selectedData?.parent);
  $("plan-parent").textContent = parent ? `Derived from: ${label(parent)}. The original plan is preserved.` : selectedData ? "Original frozen plan. Inputs cannot be edited in place." : "Prepare inputs and freeze the first plan.";
  for (const name of ["inspect-plan", "check-plan", "run-plan"]) $(name).disabled = busy || !selectedData;
  $("draft").classList.toggle("hidden", !draft || draft.project !== selected);
  if (draft && draft.project === selected && !globalThis.workbench) {
    $("draft-status").textContent = "Supplied inputs validated; not yet frozen.";
    $("draft-details").textContent = JSON.stringify(draft.validation, null, 2);
    const oldParent = $("parent-plan").value;
    options($("parent-plan"), [["", "Original plan"], ...plans.filter(plan => plan.task === draft.task).map(plan => [plan.id, label(plan)])], oldParent);
    if (parentDraft !== draft.id) { parentDraft = draft.id; $("parent-plan").value = ""; if (draft.case === "gastric_load_15g") { const fasting = plans.find(plan => plan.task === draft.task && plan.slots.some(slot => slot.endsWith("/fasting"))); if (fasting) $("parent-plan").value = fasting.id; } }
  }
  $("runtime-status").textContent = data.runtime_attachment ? `Selected attachment: ${data.runtime_attachment}` : "No native runtime attachment selected. Both meal-test tasks need no simulator.";
  renderAttempts(chosen.info?.attempts || [], plans, busy);
  $("saved-report").classList.toggle("hidden", !currentReport || currentReport.project !== selected);
  globalThis.workbench?.render(data, chosen, busy);
  globalThis.comparisons?.render(data, chosen, busy);
  globalThis.connected?.render(data, chosen, busy);
}
function renderAttempts(attempts, plans, busy) {
  if (!attempts.length) { $("attempt-list").replaceChildren(element("p", "No attempts yet. A run preserves its own outcome here.", "muted")); return; }
  $("attempt-list").replaceChildren(...attempts.slice().reverse().map(attempt => {
    const row = element("article", undefined, "attempt");
    const plan = plans.find(item => item.id === attempt.plan);
    const result = typeof attempt.outcome === "object" ? attempt.outcome : null;
    const top = element("div", undefined, "attempt-top"); top.append(element("h3", `${plan ? label(plan) : "Saved plan"} · attempt ${attempt.ordinal}`), badge(result?.completeness || "unfinished", result?.completeness || "unfinished"));
    row.append(top, element("p", result ? `Execution: ${result.execution_status} · payload: ${result.payload} · ${Object.values(result.slot_statuses).filter(v => v === "complete").length}/${Object.keys(result.slot_statuses).length} planned slots complete.` : "Unfinished or unobserved execution. Confirm the old executor has stopped before explicit CLI recovery."));
    const details = element("details"); details.append(element("summary", "Plan and attempt identities"), element("p", `Plan: ${attempt.plan}`), element("code", `Attempt: ${attempt.id}`)); if (attempt.retry_of) details.append(element("p", `Retry of: ${attempt.retry_of}`)); row.append(details);
    const actions = element("div", undefined, "actions");
    const verify = element("button", result?.completeness === "complete" ? "Verify saved report" : "Verify incomplete evidence");
    verify.disabled = busy || !result || result.payload !== "native";
    verify.onclick = () => action("verify", {attempt: attempt.id, allow_failed: $("allow-failed").checked}); actions.append(verify);
    if (result?.payload === "forensic") row.append(element("p", "No admissible native report. The original failure ledger and forensic files are retained.", "muted"));
    if (result && attempt.id === (attempts.filter(item => item.plan === attempt.plan).at(-1)?.id)) { const retry = element("button", "Run a new attempt"); retry.disabled = busy || !["mmtt-sensitivity", "mmtt-sampling", "m4-study-installed"].includes(plan?.task); retry.onclick = () => action("run", {plan: attempt.plan, retry_of: attempt.id}); actions.append(retry); }
    row.append(actions); return row;
  }));
}
function tableCells(line) {
  const cells = []; let start = 0, slashes = 0;
  for (let i = 0; i < line.length; i++) {
    if (line[i] === "|" && slashes % 2 === 0) { cells.push(line.slice(start, i)); start = i + 1; }
    slashes = line[i] === "\\" ? slashes + 1 : 0;
  }
  cells.push(line.slice(start));
  return cells.slice(1, -1).map(value => value.trim().replaceAll("\\|", "|"));
}
function renderMarkdown(text, container = $("report-text")) {
  container.replaceChildren(); const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]; if (!line.trim()) continue;
    if (line.startsWith("|")) {
      const wrapper = element("div", undefined, "table-scroll"), table = element("table"); let first = true;
      while (i < lines.length && lines[i].startsWith("|")) { const cells = tableCells(lines[i]); if (!cells.every(value => /^[:\- ]+$/.test(value))) { const row = element("tr"); for (const value of cells) { const cell = element(first ? "th" : "td", value.replaceAll("**", "")); if (first) cell.scope = "col"; row.append(cell); } table.append(row); first = false; } i++; }
      i--; wrapper.append(table); container.append(wrapper);
    } else if (line.startsWith("#")) container.append(element("h3", line.replace(/^#+\s*/, "")));
    else container.append(element("p", line.replaceAll("**", "")));
  }
}
async function downloadReport(record, name) {
  const response = await request(`/api/reports/${record.id}/${name}`);
  const url = URL.createObjectURL(await response.blob());
  const link = element("a"); link.href = url; link.download = name.replaceAll("/", "-"); link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderChildReports(record) {
  const container = $("child-reports"); container.replaceChildren();
  const reports = record.files.filter(name => /^studies\/[a-z][a-z0-9_-]{0,63}\/report\.md$/.test(name));
  container.classList.toggle("hidden", !reports.length);
  if (reports.length) container.append(element("h3", "Native analysis for each measurement schedule"));
  for (const name of reports) {
    const schedule = name.split("/")[1], details = element("details"), content = element("div", undefined, "report-text");
    details.append(element("summary", `Schedule: ${schedule}`));
    const view = element("button", "Read native analysis");
    view.onclick = async () => { try { const text = await (await request(`/api/reports/${record.id}/${name}`)).text(); if (currentReport?.id === record.id) renderMarkdown(text, content); } catch (error) { reportRefused(error, record); } };
    details.append(view);
    for (const extension of ["md", "json"]) {
      const download = element("button", extension === "md" ? "Download schedule report" : "Download schedule JSON");
      download.onclick = async () => { try { await downloadReport(record, name.replace(/\.md$/, "." + extension)); } catch (error) { reportRefused(error, record); } };
      details.append(download);
    }
    details.append(content); container.append(details);
  }
}
async function showReport(identity) {
  const issued = ++reportIssued;
  const record = data.reports.find(item => item.id === identity);
  if (!record) throw new Error("Verified report pointer is unavailable; refresh and verify again.");
  if (!record.valid || invalidReports.has(identity)) return false;
  if (record.study && globalThis.connected && connected.selection() !== record.study) return false;
  try {
  const markdown = await (await request(`/api/reports/${identity}/report.md`)).text();
  const hasFigure = record.files.includes("figure.svg");
  const nextImageURL = hasFigure ? URL.createObjectURL(await (await request(`/api/reports/${identity}/figure.svg`)).blob()) : null;
  if (issued !== reportIssued || selected !== record.project || invalidReports.has(identity) || !data.reports.some(item => item.id === identity && item.valid) || (record.study && globalThis.connected && connected.selection() !== record.study)) { if (nextImageURL) URL.revokeObjectURL(nextImageURL); return false; }
  renderMarkdown(markdown);
  renderChildReports(record);
  if (imageURL) URL.revokeObjectURL(imageURL);
  imageURL = nextImageURL;
  $("report-figure").classList.toggle("hidden", !hasFigure);
  document.querySelector('[data-download="figure.svg"]').classList.toggle("hidden", !hasFigure);
  $("download-comparison").classList.toggle("hidden", !record.files.includes("comparison.csv"));
  $("download-study").classList.toggle("hidden", !record.files.includes("study.csv"));
  if (hasFigure) $("report-figure").src = imageURL;
  currentReport = record;
  $("report-context").textContent = `Verified ${new Date(record.verified_at).toLocaleString()} · ` + (record.study ? `connected study ${record.study.slice(0, 12)} · snapshot ${record.snapshot.tip}` : record.comparison ? `comparison ${record.comparison.slice(0, 12)} · snapshot ${record.snapshot.tip}` : `attempt ${record.attempt.slice(0, 12)}`);
  $("report-completeness").textContent = record.completeness + (record.numerical_acceptance ? ` · point checks ${record.numerical_acceptance.status}` : "");
  $("report-completeness").className = "tag" + (record.completeness === "complete" && (!record.numerical_acceptance || record.numerical_acceptance.all_passed) ? "" : " warn");
  $("saved-report").classList.remove("hidden"); $("saved-report").scrollIntoView({behavior: "smooth", block: "start"});
  return true;
  } catch (error) { if (issued !== reportIssued || selected !== record.project || (record.study && globalThis.connected && connected.selection() !== record.study)) return false; throw error; }
}
$("create-project").onsubmit = event => { event.preventDefault(); action("create", {name: $("project-name").value}, null); };
$("open-project").onsubmit = event => { event.preventDefault(); action("open", {path: $("open-path").value}, null); };
$("prepare-form").onsubmit = event => { event.preventDefault(); draft = null; action("prepare", {task: $("task").value, case: $("example-case").value}); };
$("freeze-form").onsubmit = event => { event.preventDefault(); if (globalThis.workbench) workbench.freeze(); else if (draft) action("freeze", {draft: draft.id, revision: draft.revision, name: $("plan-name").value, parent: $("parent-plan").value || null}); };
$("task").onchange = updateTask;
$("plan-select").onchange = () => { selectedPlan = $("plan-select").value; globalThis.workbench?.close(); invalidatePlanView(); render(); };
$("refresh-project").onclick = () => action("refresh");
$("inspect-plan").onclick = () => action("plan", {plan: selectedPlan});
$("check-plan").onclick = () => action("check", {plan: selectedPlan});
$("run-plan").onclick = () => { const last = project()?.info?.attempts.filter(item => item.plan === selectedPlan).at(-1); action("run", {plan: selectedPlan, retry_of: last?.id || null}); };
$("select-runtime").onsubmit = event => { event.preventDefault(); action("select_attachment", {path: $("attachment-path").value}, null); };
$("attach-runtime").onsubmit = event => { event.preventDefault(); action("attach", {native_site: $("native-site").value, observer_site: $("observer-site").value}, null); };
$("clear-runtime").onclick = () => action("clear_attachment", {}, null);
$("relocate-form").onsubmit = event => { event.preventDefault(); action("relocate", {output: $("relocate-path").value}); };
$("cancel-run").onclick = async () => { try { if (data.active) await request(`/api/jobs/${data.active}/cancel`, {}); await refresh(); } catch (error) { notice(error.message, true); } };
$("stop-server").onclick = async () => { try { await request("/api/shutdown", {}); data.closing = true; render(); notice("Server stopping. Runs are cancelled through the SDK; project actions finish before exit. Keep the terminal open until it exits."); } catch (error) { notice(error.message, true); } };
for (const button of document.querySelectorAll("[data-download]")) button.onclick = async () => { const record = currentReport; try { if (record) await downloadReport(record, button.dataset.download); } catch (error) { reportRefused(error, record); } };
globalThis.workbench?.bind();
globalThis.comparisons?.bind();
globalThis.connected?.bind();
updateTask(); refresh(); setInterval(refresh, 1500);
