"use strict";
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="opent1d-token"]').content;
const names = {"mmtt-sensitivity": "Paired meal-test assumptions", "m4-study-installed": "Synthetic secretion models", "m4-study-secure": "Historical secretion study"};
const cases = {"mmtt-sensitivity": [["complete", "Invented paired visit"], ["censored", "Invented paired visit with censored measurements"]], "m4-study-installed": [["fasting", "Fasting"], ["gastric_load_15g", "15 g initial gastric amount"]]};
const context = {"mmtt-sensitivity": "Whole-body total endogenous secretion, including basal, over observed 0–120 minutes (pmol). Change is follow-up minus baseline. Three required assumption variants; 128 perturbations with seed 117. Invented data only.", "m4-study-installed": "Both supplied sources · adult#001 · 240 minutes · 961 quarter-minute samples. The gastric amount is an initial condition, not a timed meal. Native runtimes must be prepared separately."};
let data = null, selected = null, draft = null, selectedPlan = null, currentReport = null, pending = false, watched = null, loaded = false;
let imageURL = null, parentDraft = null;
const handled = new Set();
function invalidatePlanView() { $("plan-inspector").classList.add("hidden"); $("plan-inspector").open = false; $("plan-details").textContent = ""; $("readiness").textContent = "Check this frozen plan with the current runtime selection before execution."; }
function element(tag, text, cls) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; }
function notice(message, error = false) { $("notice").textContent = message; $("notice").className = "notice" + (error ? " error" : ""); if (error) $("notice").focus(); }
async function request(url, body) {
  const options = {headers: {"X-OpenT1D-Token": token}, cache: "no-store"};
  if (body !== undefined) { options.method = "POST"; options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); }
  const response = await fetch(url, options);
  if (!response.ok) { const error = await response.json(); throw new Error(error.error || "Action refused"); }
  return response;
}
async function action(operation, arguments_ = {}, project = selected) {
  if (pending || data?.active) { notice("Another action is still running. Stop the run or wait for it to finish.", true); return; }
  pending = true; render();
  try {
    const response = await request("/api/actions", {request_id: crypto.randomUUID(), operation, project, arguments: arguments_});
    const job = await response.json(); watched = job.id; handled.delete(job.id);
    await refresh();
  } catch (error) { notice(error.message, true); }
  finally { pending = false; render(); }
}
function project() { return data?.projects.find(item => item.id === selected); }
function label(plan) { return project()?.labels[plan.id] || `${names[plan.task] || plan.task} · ${plan.slots.join(", ")}`; }
function options(select, values, chosen) { select.replaceChildren(...values.map(([value, text]) => { const node = element("option", text); node.value = value; return node; })); if (values.some(([value]) => value === chosen)) select.value = chosen; }
function updateTask() { const task = $("task").value; options($("example-case"), cases[task]); $("task-context").textContent = context[task]; }
async function refresh() {
  try {
    const previousRuntime = data?.runtime_attachment;
    data = await (await request("/api/state")).json();
    if (previousRuntime !== data.runtime_attachment) invalidatePlanView();
    if (!loaded) { for (const job of data.jobs) if (job.status !== "running") handled.add(job.id); loaded = true; }
    for (const job of data.jobs) if (job.id === watched && job.status !== "running" && !handled.has(job.id)) {
      handled.add(job.id); watched = null;
      if (job.status === "error") { notice(job.error, true); continue; }
      if (job.project && job.project !== selected) { selected = job.project; invalidatePlanView(); }
      const result = job.result;
      if (job.operation === "prepare") { draft = result; $("plan-name").value = `${names[result.task]} — ${cases[result.task].find(row => row[0] === result.case)[1]}`; notice("Inputs validated. Inspect the assumptions and freeze a plan before running."); }
      else if (job.operation === "freeze") { selectedPlan = result.plan; draft = null; invalidatePlanView(); notice("Plan frozen. The original inputs and assumptions are retained."); }
      else if (job.operation === "plan") { $("plan-details").textContent = JSON.stringify(result, null, 2); $("plan-inspector").classList.remove("hidden"); $("plan-inspector").open = true; }
      else if (job.operation === "check") { $("readiness").textContent = result.runtimes_ready ? "Ready for explicit execution. This check did not run a model or install dependencies." : "Native execution is unavailable with the current selection. Configure reviewed runtimes; an explicit run without them retains an admission failure and performs no setup."; notice(result.runtimes_ready ? "Readiness check passed." : "Readiness check found unavailable native runtimes.", !result.runtimes_ready); }
      else if (job.operation === "run") { notice(`Execution ${result.result.execution_status}; scientific evidence ${result.result.completeness}. Verify the saved report explicitly to inspect its conclusions.`, result.result.completeness !== "complete"); }
      else if (job.operation === "verify") { await showReport(result.report); notice("Saved analysis verified. This did not run the model again."); }
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
  $("project-list").replaceChildren(...data.projects.map(item => { const button = element("button", item.name, "project-choice" + (item.id === selected ? " selected" : "")); button.disabled = busy; button.onclick = () => { selected = item.id; selectedPlan = null; draft = null; currentReport = null; invalidatePlanView(); action("refresh", {}, item.id); }; return button; }));
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
  if (draft && draft.project === selected) {
    $("draft-status").textContent = "Supplied inputs validated; not yet frozen.";
    $("draft-details").textContent = JSON.stringify(draft.validation, null, 2);
    const oldParent = $("parent-plan").value;
    options($("parent-plan"), [["", "Original plan"], ...plans.filter(plan => plan.task === draft.task).map(plan => [plan.id, label(plan)])], oldParent);
    if (parentDraft !== draft.id) { parentDraft = draft.id; $("parent-plan").value = ""; if (draft.case === "gastric_load_15g") { const fasting = plans.find(plan => plan.task === draft.task && plan.slots.some(slot => slot.endsWith("/fasting"))); if (fasting) $("parent-plan").value = fasting.id; } }
  }
  $("runtime-status").textContent = data.runtime_attachment ? `Selected attachment: ${data.runtime_attachment}` : "No native runtime attachment selected. The paired meal-test task needs no simulator.";
  renderAttempts(chosen.info?.attempts || [], plans, busy);
  $("saved-report").classList.toggle("hidden", !currentReport || currentReport.project !== selected);
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
    if (result && attempt.id === (attempts.filter(item => item.plan === attempt.plan).at(-1)?.id)) { const retry = element("button", "Run a new attempt"); retry.disabled = busy || !["mmtt-sensitivity", "m4-study-installed"].includes(plan?.task); retry.onclick = () => action("run", {plan: attempt.plan, retry_of: attempt.id}); actions.append(retry); }
    row.append(actions); return row;
  }));
}
function renderMarkdown(text) {
  const container = $("report-text"); container.replaceChildren(); const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]; if (!line.trim()) continue;
    if (line.startsWith("|")) {
      const wrapper = element("div", undefined, "table-scroll"), table = element("table"); let first = true;
      while (i < lines.length && lines[i].startsWith("|")) { const cells = lines[i].split("|").slice(1, -1).map(value => value.trim()); if (!cells.every(value => /^[:\- ]+$/.test(value))) { const row = element("tr"); for (const value of cells) { const cell = element(first ? "th" : "td", value.replaceAll("**", "")); if (first) cell.scope = "col"; row.append(cell); } table.append(row); first = false; } i++; }
      i--; wrapper.append(table); container.append(wrapper);
    } else if (line.startsWith("#")) container.append(element("h3", line.replace(/^#+\s*/, "")));
    else container.append(element("p", line.replaceAll("**", "")));
  }
}
async function showReport(identity) {
  const record = data.reports.find(item => item.id === identity);
  if (!record) throw new Error("Verified report pointer is unavailable; refresh and verify again.");
  const markdown = await (await request(`/api/reports/${identity}/report.md`)).text();
  const hasFigure = record.files.includes("figure.svg");
  const nextImageURL = hasFigure ? URL.createObjectURL(await (await request(`/api/reports/${identity}/figure.svg`)).blob()) : null;
  renderMarkdown(markdown);
  if (imageURL) URL.revokeObjectURL(imageURL);
  imageURL = nextImageURL;
  $("report-figure").classList.toggle("hidden", !hasFigure);
  document.querySelector('[data-download="figure.svg"]').classList.toggle("hidden", !hasFigure);
  if (hasFigure) $("report-figure").src = imageURL;
  currentReport = record;
  $("report-context").textContent = `Verified ${new Date(record.verified_at).toLocaleString()} · attempt ${record.attempt.slice(0, 12)}`;
  $("report-completeness").textContent = record.completeness;
  $("report-completeness").className = "tag" + (record.completeness === "complete" ? "" : " warn");
  $("saved-report").classList.remove("hidden"); $("saved-report").scrollIntoView({behavior: "smooth", block: "start"});
}
$("create-project").onsubmit = event => { event.preventDefault(); action("create", {name: $("project-name").value}, null); };
$("open-project").onsubmit = event => { event.preventDefault(); action("open", {path: $("open-path").value}, null); };
$("prepare-form").onsubmit = event => { event.preventDefault(); draft = null; action("prepare", {task: $("task").value, case: $("example-case").value}); };
$("freeze-form").onsubmit = event => { event.preventDefault(); if (draft) action("freeze", {draft: draft.id, name: $("plan-name").value, parent: $("parent-plan").value || null}); };
$("task").onchange = updateTask;
$("plan-select").onchange = () => { selectedPlan = $("plan-select").value; invalidatePlanView(); render(); };
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
for (const button of document.querySelectorAll("[data-download]")) button.onclick = async () => { try { if (!currentReport) return; const response = await request(`/api/reports/${currentReport.id}/${button.dataset.download}`); const url = URL.createObjectURL(await response.blob()); const link = element("a"); link.href = url; link.download = button.dataset.download; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); } catch (error) { currentReport = null; render(); notice(error.message, true); } };
updateTask(); refresh(); setInterval(refresh, 1500);
