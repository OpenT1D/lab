"use strict";

const desktopApp = document.querySelector?.('meta[name="opent1d-profile"]')?.content === "desktop";
const workspaceMMTTOnly = document.querySelector?.('meta[name="opent1d-capabilities"]')?.content === "mmtt-sensitivity,mmtt-sampling";

// Navigation only changes presentation; the native workflows retain their state.
const workspaceViews = {
  overview: {panel: "overview-panel", title: "overview-title", label: "Start", nav: "open-overview"},
  m4: {panel: "m4-panel", title: "m4-title", label: "Insulin secretion", nav: "new-study"},
  m3: {panel: "m3-panel", title: "m3-title", label: "Glucose forecasts", nav: "open-m3"},
  sampling: {panel:"sampling-panel",title:"sampling-title",label:"Fewer measurement times",nav:"open-sampling"},
  observations: {panel: "observations-panel", title: "observations-title", label: "Meal-test analysis", nav: "open-observations"},
  campaigns: {panel: "campaigns-panel", title: "campaigns-title", label: "Repeat experiments", nav: "open-campaigns"},
  library: {panel: "archive-library", title: "library-title", label: "Results", nav: "open-library"},
  durable: {panel: "durable-panel", title: "durable-title", label: "Export / open archives", nav: "open-durable"},
};
let workspaceCurrentView = null;
let workspaceActiveJob = null;
let workspaceObservedJob = null;
const workspaceOperationNames = {sampling_example:"Preparing sampling example",sampling_freeze:"Freezing sampling plan",sampling_run:"Comparing measurement times",sampling_reconstruct:"Checking sampling analysis",observation_example:"Preparing invented meal tests",observation_freeze:"Validating and freezing observation plan",observation_run:"Running paired secretion analysis",observation_reconstruct:"Checking saved observation analysis",check:"Checking study setup",install:desktopApp ? "Checking included components" : "Installing task environments",run:"Running secretion experiment",reconstruct:"Checking saved study analysis",m3_fixture:"Preparing synthetic inputs",m3_check:"Checking forecast setup",m3_run:"Running forecast experiment",m3_reconstruct:"Checking saved forecast analysis",campaign_check:"Checking repeat setup",campaign_install:desktopApp ? "Checking included components" : "Installing repeat environments",campaign_run:"Running repeated experiments",campaign_resume:"Resuming remaining repeats",campaign_reconstruct:"Checking saved repeat analysis",library_index:"Reading archive metadata",library_verify:"Checking saved archive analysis",durable_export:"Exporting the saved experiment",durable_register:"Checking archive package bytes",durable_verify:"Checking archive package bytes",durable_reconstruct:"Checking saved package analysis",durable_forensic:"Retaining available raw evidence"};

function workspaceNavigate(view, {focus = true, remember = true} = {}) {
  if (workspaceMMTTOnly && !["overview", "observations", "sampling"].includes(view)) view = "overview";
  if (!Object.hasOwn(workspaceViews, view)) view = "overview";
  const destination = workspaceViews[view];
  for (const [key, entry] of Object.entries(workspaceViews)) {
    document.getElementById(entry.panel).hidden = key !== view;
    const button = document.getElementById(entry.nav);
    button.classList.toggle("selected", key === view);
    if (key === view) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  document.getElementById("workspace-location").textContent = destination.label;
  document.getElementById("workspace-skip").href = "#" + destination.title;
  document.title = "OpenT1D · " + destination.label;
  document.body.dataset.workspaceView = view;
  if (remember && window.location.hash !== "#" + view) window.history.pushState(null, "", "#" + view);
  if (workspaceCurrentView !== view) window.scrollTo({top: 0, behavior: "instant"});
  workspaceCurrentView = view;
  workspaceRevealNavigation();
  if (focus) document.getElementById(destination.title).focus({preventScroll: true});
}

function workspaceRevealNavigation() {
  const menu = document.getElementById("workspace-more");
  menu.open = false;
}

function workspaceJobView(job) {
  if (job.operation.startsWith("sampling_")) return "sampling";
  if (job.operation.startsWith("observation_")) return "observations";
  if (job.operation.startsWith("m3_")) return "m3";
  if (job.operation.startsWith("campaign_")) return "campaigns";
  if (job.operation.startsWith("library_")) return "library";
  if (job.operation.startsWith("durable_")) return "durable";
  return "m4";
}

function workspaceElapsed(job, now = Date.now()) {
  const start = typeof job.started_at === "string" ? Date.parse(job.started_at) : NaN;
  const end = typeof job.finished_at === "string" ? Date.parse(job.finished_at) : ["running", "cancelling"].includes(job.state) ? now : NaN;
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return "Elapsed computer time unavailable";
  const seconds = Math.floor((end - start) / 1000);
  return "Elapsed computer time: " + Math.floor(seconds / 60) + "m " + String(seconds % 60).padStart(2, "0") + "s";
}

function workspaceMealTestOperation(job) {
  return ["sampling", "observation"].find(prefix => job.operation.startsWith(prefix + "_")) || null;
}

async function workspaceOpenOperation() {
  const job = workspaceActiveJob;
  if (!job) return;
  const view = workspaceJobView(job), prefix = workspaceMealTestOperation(job);
  workspaceNavigate(view, {focus: !prefix});
  if (!prefix) return;
  const terminal = !["queued", "running", "cancelling"].includes(job.state);
  const id = job[prefix + "_entry_id"];
  let target;
  if (terminal && id) {
    if (prefix === "sampling" && typeof refreshSampling === "function") await refreshSampling();
    if (prefix === "observation" && typeof refreshObservations === "function") await refreshObservations();
    if (workspaceCurrentView !== view) return;
    if (prefix === "sampling" && typeof selectSamplingID === "function") await selectSamplingID(id);
    if (prefix === "observation" && typeof selectObservationID === "function") await selectObservationID(id);
    if (workspaceCurrentView !== view) return;
    const ui = prefix === "sampling" ? (typeof samplingUI === "undefined" ? null : samplingUI) : (typeof observationUI === "undefined" ? null : observationUI);
    if (ui && ui.state.entry?.id !== id) return;
    target = document.getElementById((prefix === "sampling" ? "sam" : "obs") + "-result-title");
  } else if (terminal) {
    const form = document.getElementById((prefix === "sampling" ? "sam" : "obs") + "-plan-form");
    target = form && !form.hidden ? form : document.getElementById(workspaceViews[view].title);
  } else {
    const cancel = document.getElementById((prefix === "sampling" ? "sam" : "obs") + "-cancel");
    target = cancel?.disabled ? document.getElementById("workspace-operation-title") : cancel;
  }
  if (target) {
    if (target.tagName === "FORM" || target.id === "workspace-operation-title") target.tabIndex = -1;
    target.focus({preventScroll: true});
    target.scrollIntoView?.({block: "start", behavior: "instant"});
  }
}

function updateWorkspaceSummary({jobs}) {
  const running = jobs.find((job) => ["queued", "running", "cancelling"].includes(job.state));
  if (running) workspaceObservedJob = running.id;
  workspaceActiveJob = running || jobs.find(job => job.id === workspaceObservedJob) || null;
  const strip = document.getElementById("workspace-operation");
  strip.hidden = !workspaceActiveJob;
  if (workspaceActiveJob) {
    const job = workspaceActiveJob, terminal = !["queued", "running", "cancelling"].includes(job.state);
    const label = workspaceOperationNames[job.operation] || "Local operation";
    const setupMissing = job.result?.runtimes_ready === false;
    let title = terminal ? label + " · " + (setupMissing ? (desktopApp ? "repair needed" : "installation needed") : job.state) : label;
    if (job.state === "completed" && job.operation === "m3_fixture") title = "Example inputs ready";
    if (job.state === "completed" && job.operation === "m3_check") title = "Forecast setup check finished";
    const mealPrefix = workspaceMealTestOperation(job);
    const mealEntry = mealPrefix && (job.result?.observation_entry || job.result?.sampling_entry);
    if (mealPrefix && job.operation === mealPrefix + "_run" && mealEntry?.state === "completed") title = mmttExecutionLabel(mealEntry);
    let detail = job.state === "cancelling"
      ? "Stopping owned processes and retaining available evidence."
      : terminal ? setupMissing ? (desktopApp ? "Your configuration is retained. Run the OpenT1D installer again to repair missing or changed components." : "Your configuration is retained. Open the study to install its missing environments.") : "Open the result to review its saved evidence." : "This operation continues when you switch views. Open it for progress or cancellation.";
    if (job.state === "running") detail = uxPhaseDetail(job) || detail;
    if (!terminal) detail += " " + (job.state === "queued" ? "Waiting to start." : workspaceElapsed(job) + ".") + (job.operation === "run" && (!job.phase || job.phase.phase === "executing") ? " Per-model / condition progress is not reported by this runner." : "");
    if (mealPrefix && terminal && !job[mealPrefix + "_entry_id"]) detail = job.state === "completed" ? "Open the prepared setup to review the inputs and continue." : "Open the setup to review this operation and correct any reported problem.";
    if (mealPrefix && terminal && mealEntry?.state === "completed" && mealEntry.report_completeness === "incomplete") detail = "Some required results are missing or could not be calculated. Open the retained report to review each affected observation; this does not mean no change.";
    if (mealPrefix && terminal && job.operation === mealPrefix + "_reconstruct" && job.state === "completed") {
      title = "Saved report checked";
      detail = "The saved inputs and report reproduce. Result completeness and validity in people are separate questions.";
    }
    if (job.state === "completed" && typeof m3CompletionDetail === "function") detail = m3CompletionDetail(job) || detail;
    const heading = document.getElementById("workspace-operation-title"), description = document.getElementById("workspace-operation-detail");
    if (heading.textContent !== title) heading.textContent = title;
    if (description.textContent !== detail) description.textContent = detail;
    const spinner = strip.querySelector?.(".spinner"); if (spinner) spinner.hidden = terminal;
    document.getElementById("workspace-operation-open").textContent = mealPrefix ? terminal ? job[mealPrefix + "_entry_id"] ? "View result" : "View setup" : "View progress" : "View operation";
  }

}

document.getElementById("open-overview").addEventListener("click", () => workspaceNavigate("overview"));
document.getElementById("workspace-brand").addEventListener("click", (event) => {
  event.preventDefault(); workspaceNavigate("overview");
});
document.querySelectorAll("[data-workspace-go]").forEach((button) => {
  button.addEventListener("click", () => workspaceNavigate(button.dataset.workspaceGo));
});
document.getElementById("workspace-operation-open").addEventListener("click", workspaceOpenOperation);
document.getElementById("workspace-skip").addEventListener("click", (event) => {
  event.preventDefault(); document.getElementById(workspaceViews[workspaceCurrentView].title).focus();
});
window.addEventListener("popstate", () => workspaceNavigate(window.location.hash.slice(1), {remember: false}));
window.addEventListener("hashchange", () => workspaceNavigate(window.location.hash.slice(1), {remember: false}));
document.addEventListener("invalid", (event) => {
  let parent = event.target.parentElement;
  while (parent) { if (parent.tagName === "DETAILS") parent.open = true; parent = parent.parentElement; }
}, true);
workspaceNavigate(window.location.hash.slice(1), {focus: false, remember: false});

if (workspaceMMTTOnly) {
  for (const id of ["open-m3", "new-study"]) document.getElementById(id).closest("article").hidden = true;
  document.getElementById("open-library").hidden = true;
  document.getElementById("workspace-more").hidden = true;
  document.querySelector(".start-intro").textContent = "Explore two synthetic paired meal-test questions and keep their saved analyses.";
}

if (desktopApp) {
  document.getElementById("install-task").textContent = "Recheck application components";
  document.getElementById("campaign-install").textContent = "Check included components";
  document.getElementById("campaign-setup-note").textContent = "All required components are included. Check the campaign before running. Editing, replacing or reordering cells creates a new frozen matrix.";
  const exit = document.createElement("button"); exit.type = "button"; exit.className = "nav-item"; exit.textContent = "Exit OpenT1D";
  exit.addEventListener("click", async () => {
    if (!window.confirm("Exit OpenT1D? Any running analysis will be cancelled and its available results retained.")) return;
    exit.disabled = true;
    try {
      const response = await fetch("/api/desktop/shutdown", {method: "POST", headers: {"Content-Type":"application/json", "X-OpenT1D-Token":document.querySelector('meta[name="opent1d-token"]').content}, body:"{}"});
      if (!response.ok) throw new Error("Shutdown failed. Please try again.");
      document.getElementById("workspace-main").textContent = "OpenT1D is closing. You can close this tab. Your saved analyses are kept.";
    } catch (error) { exit.disabled = false; window.alert(error.message); }
  });
  document.getElementById("workspace-navigation").append(exit);
}
