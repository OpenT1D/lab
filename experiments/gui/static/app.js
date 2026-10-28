"use strict";

const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="opent1d-token"]').content;
const activeStates = new Set(["queued", "running", "cancelling"]);
let session, configuration = null, ready = false, jobs = [], active = null, selected = null;
let shownReport = null, shownFigure = null, figureURL = null, picker = null, polling = false, lastReportCheck = 0, reportRequest = 0;
let uxStudySnapshot = null, uxGraphRequest = 0;

async function api(path, body, raw = false) {
  const options = {headers: {"X-OpenT1D-Token": token}};
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch("/api/v1/" + path, options);
  if (!response.ok) {
    let message = "The operation could not be completed.";
    try { message = (await response.json()).error || message; } catch (_) { /* keep safe fallback */ }
    throw new Error(message);
  }
  return raw ? response.blob() : response.json();
}

// Polling must retain the reader's position, including opened evidence details.
const retainedRenders = new WeakMap();
function renderRetainedContent(container, signature, render, identity = container.id, force = false) {
  const previous = retainedRenders.get(container);
  if (!force && previous && previous.signature === signature && previous.identity === identity) return;
  const sameIdentity = !previous || previous.identity === identity;
  const focused = document.activeElement;
  const ownsFocus = sameIdentity && !!focused && container.contains?.(focused);
  const focusKey = ownsFocus ? focused.dataset?.pollingKey : null;
  const focusedID = ownsFocus ? focused.id : null;
  const keyed = () => [...(container.querySelectorAll?.("[data-polling-key]") || [])];
  const oldNodes = keyed();
  const focusIndex = ownsFocus ? oldNodes.filter((node) => node.tagName !== "DETAILS").indexOf(focused) : -1;
  const opened = new Map(sameIdentity ? oldNodes.filter((node) => node.tagName === "DETAILS").map((node) => [node.dataset.pollingKey, node.open]) : []);
  render();
  retainedRenders.set(container, {signature, identity});
  const nextNodes = keyed();
  const focusableNodes = nextNodes.filter((node) => node.tagName !== "DETAILS");
  for (const node of nextNodes) if (node.tagName === "DETAILS" && opened.has(node.dataset.pollingKey)) node.open = opened.get(node.dataset.pollingKey);
  if (ownsFocus && !container.contains(focused)) {
    const target = focusableNodes.find((node) => node.dataset.pollingKey === focusKey)
      || (focusedID ? document.getElementById?.(focusedID) : null)
      || focusableNodes[Math.max(0, Math.min(focusIndex, focusableNodes.length - 1))];
    if (target && container.contains(target)) target.focus({preventScroll: true});
    else { container.tabIndex = -1; container.focus({preventScroll: true}); }
  }
}
// End retained polling helpers.

function notice(message) { const changed = $("notice").textContent !== message; $("notice").textContent = message; $("notice").hidden = !message; if (message && changed && typeof uxRevealError === "function") uxRevealError(message, $("notice")); }
function status(element, label, kind = "neutral") { element.textContent = label; element.className = "status " + kind; }
function invalidate() { configuration = null; ready = false; updateStudySummary(); updateReadiness(); updateControls(); if (typeof persistStudyDraft === "function") persistStudyDraft(); }
function updateStudySummary() { if ($("study-summary")) $("study-summary").textContent = "Models: " + [...$("sources").children].map(card => card.querySelector(".source-id").value || "Unnamed model").join(" vs "); }

function updateReadiness(result) {
  const desktop = typeof desktopApp !== "undefined" && desktopApp;
  if (result) $("study-status").open = true;
  if (ready) {
    status($("readiness-badge"), "Ready", "good");
    $("readiness-icon").textContent = "✓";
    $("readiness-heading").textContent = "Ready to run";
    $("readiness-detail").textContent = desktop ? "The configuration and included application components are ready." : "The configuration is valid and the required locked environments are available.";
    $("install-task").hidden = true;
  } else if (result && result.runtimes_ready === false) {
    status($("readiness-badge"), "Setup needed", "warning");
    $("readiness-icon").textContent = "↓";
    $("readiness-heading").textContent = desktop ? "Repair application components" : "Install the task environments";
    $("readiness-detail").textContent = desktop ? "An included component is missing or changed. Exit OpenT1D and run its installer again to repair it, then recheck this study." : "The study needs its locked native and observation environments. Installation is an explicit step.";
    $("install-task").hidden = desktop;
  } else {
    status($("readiness-badge"), "Not checked");
    $("readiness-icon").textContent = "○";
    $("readiness-heading").textContent = "Check before you run";
    $("readiness-detail").textContent = desktop ? "Validate the models and included components required by this study." : "Validate the sources and check the locked environments required by this study.";
    $("install-task").hidden = true;
  }
  $("runtime-details").replaceChildren();
  if (result && result.runtimes) {
    for (const runtime of result.runtimes) {
      const row = document.createElement("div"); row.className = "runtime-line";
      row.textContent = (runtime.ready ? "✓ " : "○ ") + (runtime.project || runtime.name || "Task environment");
      $("runtime-details").append(row);
    }
  }
}

function updateControls() {
  const busy = !!active || (typeof m3Pending !== "undefined" && m3Pending) || (typeof libraryPending !== "undefined" && libraryPending);
  $("study-form").querySelectorAll("input,button").forEach((item) => { item.disabled = busy; });
  $("run-study").disabled = busy || !ready;
  $("run-study").hidden = !ready;
  $("check-study").hidden = ready || !$("install-task").hidden;
  $("add-source").disabled = busy || $("sources").children.length >= 8;
  $("sources").querySelectorAll(".remove-source").forEach((item) => { item.disabled = busy || $("sources").children.length <= 2; });
  $("install-task").disabled = busy || !configuration;
  $("reconstruct-study").disabled = busy || !selected || selected.operation !== "run" || activeStates.has(selected.state);
  $("cancel-job").hidden = !busy;
  $("cancel-job").disabled = !!active && active.state === "cancelling";
  $("active-indicator").hidden = !busy;
  if (typeof libraryControls === "function") libraryControls();
  if (typeof campaignControls === "function") campaignControls();
  if (typeof durableControls === "function") durableControls();
  if (typeof m3Controls === "function") m3Controls();
}

function validateSourceID(input) {
  const message = !input.value ? "Enter a Source ID, for example model_1." : /^[a-z][a-z0-9_-]{0,63}$/.test(input.value) ? "" : "Source ID must start with a lowercase letter and contain only lowercase letters, numbers, underscores or hyphens (1–64 characters, no spaces). For example: model_1.";
  input.setCustomValidity(message);
  if (message) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
  return message;
}

function sourceCard(source) {
  const card = document.createElement("fieldset"); card.className = "source-card";
  card.innerHTML = '<div class="source-heading"><strong>Source</strong><button type="button" class="icon-button remove-source" aria-label="Remove source">×</button></div><div class="source-fields"><label>Source ID<input class="source-id" type="text" pattern="[a-z]([a-z0-9_]|-){0,63}" maxlength="64" required></label><label>Python model<div class="path-row"><input class="path-input model-path" type="text" required><button class="browse-button" data-kind="model" type="button">Browse</button></div></label><label>Model declaration<div class="path-row"><input class="path-input declaration-path" type="text" required><button class="browse-button" data-kind="declaration" type="button">Browse</button></div></label></div>';
  card.querySelector(".source-id").value = source.id;
  card.querySelector(".model-path").value = source.model;
  card.querySelector(".declaration-path").value = source.declaration;
  const heading = card.querySelector(".source-heading"), legend = document.createElement("legend"); legend.className = heading.className;
  while (heading.firstChild) legend.append(heading.firstChild); heading.replaceWith(legend);
  const note = document.createElement("p"); note.className = "field-note"; note.id = "model-id-format-" + (++sourceCard.serial);
  note.textContent = "Source ID: start with a lowercase letter; use lowercase letters, numbers, underscores or hyphens (1–64 characters, no spaces; for example model_1).";
  card.querySelector(".source-id").setAttribute("aria-describedby", note.id); card.append(note);
  const identity = card.querySelector(".source-id");
  identity.addEventListener("input", () => validateSourceID(identity));
  identity.addEventListener("invalid", () => validateSourceID(identity));
  card.querySelectorAll("input").forEach((input) => input.addEventListener("input", invalidate));
  card.querySelector(".remove-source").addEventListener("click", () => {
    card.remove(); numberSources(); invalidate();
  });
  card.querySelectorAll(".browse-button").forEach((button) => button.addEventListener("click", () => {
    const input = card.querySelector(button.dataset.kind === "model" ? ".model-path" : ".declaration-path");
    picker = {kind: button.dataset.kind, input, parent: null};
    $("file-dialog-title").textContent = "Select a " + (picker.kind === "model" ? "Python model" : "model declaration");
    $("file-dialog").showModal(); browse(input.value.includes("/") ? input.value.slice(0, input.value.lastIndexOf("/")) : "experiments/m4");
  }));
  $("sources").append(card);
}
sourceCard.serial = 0;

function numberSources() {
  const cards = [...$("sources").children];
  cards.forEach((card, i) => { card.querySelector(".source-heading strong").textContent = "Model " + String(i + 1).padStart(2, "0"); card.querySelector(".remove-source").setAttribute("aria-label", "Remove model " + (i + 1)); card.querySelectorAll(".browse-button").forEach(button => button.setAttribute("aria-label", "Choose " + (button.dataset.kind === "model" ? "Python model" : "declaration") + " file for model " + (i + 1))); });
  $("source-count").textContent = cards.length + " sources";
  updateStudySummary();
  updateControls();
}

function formConfig() {
  return {schema: session.defaults.schema,
    sources: [...$("sources").children].map((card) => ({id: card.querySelector(".source-id").value,
      model: card.querySelector(".model-path").value, declaration: card.querySelector(".declaration-path").value})),
    scenarios: [...document.querySelectorAll('input[name="scenario"]:checked')].map((input) => input.value),
    timeout_seconds: Number($("stage-budget").value), source_timeout_seconds: Number($("source-budget").value)};
}

async function browse(directory) {
  try {
    const files = await api("files?directory=" + encodeURIComponent(directory || ".") + "&kind=" + picker.kind);
    picker.parent = files.parent; $("directory-up").disabled = files.parent === null;
    $("file-directory").textContent = files.directory || session.workspace;
    $("file-list").replaceChildren();
    if (!files.entries.length) { const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = "No matching files in this directory."; $("file-list").append(empty); }
    for (const entry of files.entries) {
      const button = document.createElement("button"); button.type = "button"; button.className = "file-entry";
      button.textContent = (entry.kind === "directory" ? "▸ " : "  ") + entry.name;
      button.addEventListener("click", () => {
        if (entry.kind === "directory") browse(entry.path);
        else { picker.input.value = entry.path; $("file-dialog").close(); invalidate(); }
      });
      $("file-list").append(button);
    }
  } catch (error) { $("file-list").textContent = error.message; }
}

async function checkStudy(event) {
  if (event) event.preventDefault();
  if ((typeof libraryPending !== "undefined" && libraryPending) || !$("study-form").reportValidity()) return;
  notice(""); ready = false;
  try {
    configuration = await api("configurations", formConfig());
    await begin("configurations/" + configuration.id + "/check");
  } catch (error) { notice(error.message); updateControls(); }
}

async function begin(path) {
  if (typeof libraryPending !== "undefined" && libraryPending) return;
  notice("");
  active = await api(path, {}); selected = active; shownReport = null;
  observeInstall(active);
  updateActivity(active); updateControls(); await refresh();
}

function updateActivity(job) {
  const desktop = typeof desktopApp !== "undefined" && desktopApp;
  const elapsed = $("activity-elapsed");
  if (elapsed) { elapsed.hidden = !job; elapsed.textContent = job ? (job.state === "queued" ? "Waiting to start." : workspaceElapsed(job)) + (job.operation === "run" && activeStates.has(job.state) && (!job.phase || job.phase.phase === "executing") ? ". Native study running; per-model / condition progress is not reported." : "") : ""; }
  if (job && !["check", "install", "run", "reconstruct"].includes(job.operation)) {
    const busy = activeStates.has(job.state);
    status($("activity-badge"), busy ? "Another operation running" : "Idle", busy ? "pending" : "neutral");
    $("activity-detail").textContent = busy ? "Use View operation to open the ongoing task. One operation runs at a time." : "Your study configuration is retained. Open Results to review saved experiments and archives.";
    $("job-reference").textContent = "";
    if (elapsed) elapsed.hidden = true;
    return;
  }
  if (job && ["check", "install", "run", "reconstruct"].includes(job.operation)) $("study-status").open = true;
  if (!job) { status($("activity-badge"), "Idle"); return; }
  const labels = {check: "Checking study", install: desktop ? "Checking included components" : "Installing environments", run: "Running study", reconstruct: "Verifying reconstruction", library_index: "Reading archive metadata", library_verify: "Verifying saved archive evidence", campaign_check: "Checking campaign", campaign_install: desktop ? "Checking included campaign components" : "Installing campaign environments", campaign_run: "Running campaign", campaign_resume: "Resuming remaining campaign slots", campaign_reconstruct: "Verifying campaign reconstruction", durable_export: "Exporting the complete experiment", durable_register: "Verifying durable package bytes", durable_verify: "Rechecking durable package bytes", durable_reconstruct: "Verifying durable native reconstruction", durable_forensic: "Retaining raw M3 evidence", m3_fixture: "Preparing a synthetic M3 example", m3_check: "Checking M3 metadata", m3_run: "Running an M3 workflow", m3_reconstruct: "Verifying saved M3 analysis"};
  const setupNeeded = job.operation === "check" && job.result && job.result.runtimes_ready === false;
  const detail = setupNeeded ? (desktop ? "Configuration checked. Run the OpenT1D installer again to repair missing or changed components, then recheck the study." : "Configuration checked. Required environments are missing; install them explicitly before running.") : activeStates.has(job.state) ? (job.state === "cancelling" ? "Stopping the owned processes and preserving available evidence…" : (uxPhaseDetail(job) || labels[job.operation]))
    : job.state === "completed" ? (job.operation.startsWith("m3_") ? "M3 operation finished. Inspect readiness, execution, saved analysis and coverage separately below." : job.operation === "durable_forensic" ? "Raw files retained independently; no native reconstruction or complete-cohort claim." : job.operation.startsWith("durable_") ? "Durable archive operation finished. Inspect integrity, reconstruction and coverage below." : job.operation.startsWith("campaign_") ? "Campaign operation finished. Inspect coverage and verification below." : job.operation.startsWith("library_") ? "Archive operation finished. Inspect the library snapshot below." : job.operation === "check" ? "Study check finished." : job.operation === "install" ? (desktop ? "Included component check finished." : "Environment installation finished.") : job.operation === "reconstruct" ? "Native report reconstruction finished." : "Study execution finished. Inspect numerical acceptance below.")
    : job.state === "cancelled" ? "Operation cancelled. Available evidence is retained." : (job.error || (job.result && job.result.entry_error) || "The operation failed. Available evidence is retained.");
  status($("activity-badge"), setupNeeded ? "Setup needed" : job.state.replaceAll("_", " "), setupNeeded ? "warning" : job.state === "completed" ? "good" : job.state === "failed" ? "bad" : "pending");
  $("activity-detail").textContent = detail;
  $("job-reference").textContent = job.id.slice(0, 16) + " · " + (job.exit_code === null ? activeStates.has(job.state) ? "process active" : "no recorded exit code" : "exit " + job.exit_code);
  if (job.operation.startsWith("campaign_")) return;
  for (const id of ["step-config", "step-check", "step-run", "step-review"]) $(id).classList.remove("current");
  $(job.operation === "run" && activeStates.has(job.state) ? "step-run" : job.operation === "check" || job.operation === "install" ? "step-check" : "step-review").classList.add("current");
}

function renderHistory() {
  const desktop = typeof desktopApp !== "undefined" && desktopApp;
  updateWorkspaceSummary({jobs});
  const focusIdentity = document.activeElement?.dataset.historyJob;
  const focusContainer = document.activeElement?.parentElement?.id;
  $("history").replaceChildren(); $("overview-history").replaceChildren();
  if (!jobs.length) {
    const p = document.createElement("p"); p.className = "quiet"; p.textContent = "Your local operations will appear here."; $("history").append(p);
    const empty = document.createElement("p"); empty.className = "quiet overview-empty"; empty.textContent = "Your local operations will appear here. Start with an experiment or register a saved archive."; $("overview-history").append(empty);
  }
  const labels = {sampling_example:"Sampling example",sampling_freeze:"Sampling plan freeze",sampling_run:"Measurement-time comparison",sampling_reconstruct:"Sampling saved analysis",observation_example: "Invented meal-test example", observation_freeze: "Observation plan freeze", observation_run: "Paired secretion analysis", observation_reconstruct: "Observation saved analysis", check: "Study check", install: desktop ? "Application component check" : "Environment setup", run: "Initial load study", reconstruct: "Reconstruction", library_index: "Archive metadata", library_verify: "Archive verification", campaign_check: "Campaign check", campaign_install: desktop ? "Campaign component check" : "Campaign setup", campaign_run: "Campaign run", campaign_resume: "Campaign resume", campaign_reconstruct: "Campaign reconstruction", durable_export: "Durable archive export", durable_register: "Durable package registration", durable_verify: "Durable integrity check", durable_reconstruct: "Durable reconstruction", durable_forensic: "Raw M3 retention", m3_fixture: "Synthetic M3 example", m3_check: "M3 metadata check", m3_run: "M3 forecast / comparison", m3_reconstruct: "M3 saved analysis"};
  function historyButton(job, overview = false) {
    const button = document.createElement("button"); button.type = "button"; button.className = "history-job" + (selected && selected.id === job.id ? " current" : "");
    button.dataset.historyJob = job.id;
    const name = document.createElement("strong"), detail = document.createElement("small");
    name.textContent = labels[job.operation] || "Local operation";
    const date = new Date(job.created_at);
    detail.textContent = job.state.replaceAll("_", " ") + " · " + date.toLocaleString([], overview ? {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"} : {hour: "2-digit", minute: "2-digit"});
    button.setAttribute("aria-label", name.textContent + " · " + detail.textContent);
    button.append(name, detail);
    button.addEventListener("click", () => {
      selected = job; workspaceNavigate(workspaceJobView(job)); shownReport = null; $("results").hidden = true;
      updateActivity(job); updateControls(); displayReport();
      if (job.campaign_id) selectCampaignID(job.campaign_id);
      if (job.sampling_entry_id && typeof selectSamplingID === "function") selectSamplingID(job.sampling_entry_id);
      if (job.observation_entry_id && typeof selectObservationID === "function") selectObservationID(job.observation_entry_id);
      if (job.m3_entry_id) { m3FollowEntry = job.m3_entry_id; refreshM3(); }
      updateM3Activity(job); renderHistory();
    });
    return button;
  }
  for (const [index, job] of jobs.slice(0, 30).entries()) {
    $("history").append(historyButton(job));
    if (index < 6) $("overview-history").append(historyButton(job, true));
  }
  if (focusIdentity && ["history", "overview-history"].includes(focusContainer)) {
    [...$(focusContainer).children].find((button) => button.dataset.historyJob === focusIdentity)?.focus({preventScroll: true});
  }
}

async function displayReport() {
  if (!selected || !["run", "reconstruct"].includes(selected.operation) || activeStates.has(selected.state)) { $("results").hidden = true; return; }
  if (shownReport === selected.id + ":" + selected.verification && Date.now() - lastReportCheck < 5000) return;
  const identity = selected.id, request = ++reportRequest;
  const current = () => selected && selected.id === identity && request === reportRequest && !activeStates.has(selected.state);
  try {
    const report = await api("jobs/" + identity + "/report");
    if (!current()) return;
    lastReportCheck = Date.now();
    const graphSnapshot = {id: identity, digest: report.report_sha256, verification: report.verification};
    if (JSON.stringify(uxStudySnapshot) !== JSON.stringify(graphSnapshot) && $("study-graph-values")) $("study-graph-values").replaceChildren();
    uxStudySnapshot = graphSnapshot;
    $("results").hidden = false; shownReport = identity + ":" + report.verification;
    const unverified = ["changed_since_verification", "recorded_verification"].includes(report.verification);
    if (typeof uxRenderEvidence === "function") uxRenderEvidence("study-evidence-summary", "m4", report, report.verification, selected.state);
    status($("report-status"), unverified ? "Acceptance unverified" : report.passed ? "Numerically accepted" : "Failed / incomplete", unverified ? "warning" : report.passed ? "good" : "bad");
    const verificationLabels = {native_reader_verified: "Verified reconstruction", changed_since_verification: "Archive changed", recorded_verification: "Previously verified; recheck files"};
    status($("verification-status"), verificationLabels[report.verification] || "Reconstruction not requested", report.verification === "native_reader_verified" ? "good" : report.verification === "changed_since_verification" ? "bad" : "neutral");
    $("denominators").replaceChildren(); const d = report.denominators || {};
    for (const [label, accepted, planned] of [["Accepted sources", d.accepted_sources, d.sources], ["Accepted source / load cases", d.accepted_source_scenarios, d.source_scenarios], ["Accepted source pairs", d.accepted_pairs, d.pairs]]) {
      const box = document.createElement("div"); box.className = "metric"; const value = document.createElement("strong"), caption = document.createElement("span");
      value.textContent = (accepted ?? "—") + " / " + (planned ?? "—"); caption.textContent = label; box.append(value, caption); $("denominators").append(box);
    }
    $("source-results").replaceChildren();
    for (const [name, source] of Object.entries(report.sources || {})) {
      const row = document.createElement("tr");
      for (const value of [name, source.ancestry || "—", source.status || "unavailable", source.accepted ? "Accepted" : "Not accepted"]) { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); }
      $("source-results").append(row);
    }
    $("report-limitations").replaceChildren();
    for (const limit of report.limitations || []) { const li = document.createElement("li"); li.textContent = limit; $("report-limitations").append(li); }
    try {
      const figureKey = identity + ":" + report.report_sha256 + ":" + report.verification;
      if (shownFigure !== figureKey) {
        $("study-figure").hidden = true;
        const blob = await api("jobs/" + identity + "/figure.svg", undefined, true);
        if (!current()) return;
        if (figureURL) URL.revokeObjectURL(figureURL); figureURL = URL.createObjectURL(blob); $("study-figure").src = figureURL;
        shownFigure = figureKey;
      }
      $("study-figure").hidden = false;
    } catch (_) { if (!current()) return; $("study-figure").hidden = true; }
    updateControls();
  } catch (_) { if (current()) { $("results").hidden = true; uxStudySnapshot = null; if ($("study-graph-values")) $("study-graph-values").replaceChildren(); } }
}

async function refresh() {
  if (polling) return;
  polling = true;
  try {
    const previous = active; jobs = (await api("jobs")).jobs;
    active = jobs.find((job) => activeStates.has(job.state)) || null;
    if (selected) selected = jobs.find((job) => job.id === selected.id) || selected;
    if (previous && !active) {
      const finished = jobs.find((job) => job.id === previous.id);
      if (finished && finished.operation === "check") { ready = finished.state === "completed" && finished.result && finished.result.ready === true; updateReadiness(finished.result); }
      if (finished && finished.operation === "install" && finished.state === "completed" && configuration) {
        active = await api("configurations/" + configuration.id + "/check", {}); selected = active;
      }
      if (finished && finished.operation === "reconstruct" && finished.state === "completed") { selected = jobs.find((job) => job.id === finished.archive_job) || finished; shownReport = null; }
      if (finished && finished.operation.startsWith("campaign_")) await campaignJobFinished(finished);
    }
    jobs.forEach(observeInstall);
    if (typeof m3JobFinished === "function") for (const job of jobs) if (job.operation.startsWith("m3_")) await m3JobFinished(job);
    if (typeof updateM3Activity === "function") updateM3Activity(active || selected);
    if (active) updateActivity(active); else if (selected) updateActivity(selected);
    renderHistory(); updateControls(); await displayReport(); await refreshLibrary(); await refreshCampaigns(); if (typeof refreshDurable === "function") await refreshDurable(); if (typeof refreshM3 === "function") await refreshM3(); if (typeof refreshObservations === "function") await refreshObservations(); if (typeof refreshSampling === "function") await refreshSampling();
    if (typeof uxRefreshResults === "function") uxRefreshResults({jobs, m3: m3Entries, campaigns, durable: durableEntries, sampling: typeof samplingUI === "undefined" ? [] : samplingUI.state.entries, observations: typeof obsState === "undefined" ? [] : obsState.entries}, openOwnResult);
    updateCampaignStudyChoices();
  } catch (error) { notice(error.message); }
  finally { polling = false; }
}

async function download(name) {
  try { const blob = await api("jobs/" + selected.id + "/" + name, undefined, true); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  catch (error) { notice(error.message); }
}

async function openOwnResult(item) {
  if (item.kind === "study") {
    const job = jobs.find(value => value.id === item.id && value.operation === "run"); if (!job) return;
    selected = job; shownReport = null; workspaceNavigate("m4"); updateActivity(job); updateControls(); await displayReport();
    const target = $("results").hidden ? $("study-status") : $("results"); if (target.id === "study-status") target.open = true; target.tabIndex = -1; target.focus(); target.scrollIntoView({block: "start"});
  } else if (item.kind === "m3") {
    const entry = m3Entries.find(value => value.id === item.id); if (!entry) return;
    workspaceNavigate("m3"); selectM3(entry); $("m3-detail").tabIndex = -1; $("m3-detail").focus(); $("m3-detail").scrollIntoView({block: "start"});
  } else if (item.kind === "sampling") {
    workspaceNavigate("sampling"); await selectSamplingID(item.id);
    if (workspaceCurrentView !== "sampling" || samplingUI.state.entry?.id !== item.id) return;
    $("sam-result-title").focus({preventScroll:true}); $("sam-result-title").scrollIntoView({block:"start"});
  } else if (item.kind === "observations") {
    workspaceNavigate("observations"); await selectObservationID(item.id);
    if (workspaceCurrentView !== "observations" || observationUI.state.entry?.id !== item.id) return;
    $("obs-result-title").focus({preventScroll:true}); $("obs-result-title").scrollIntoView({block:"start"});
  } else if (item.kind === "campaign") {
    const entry = campaigns.find(value => value.id === item.id); if (!entry) return;
    workspaceNavigate("campaigns"); selectCampaign(entry); $("campaign-detail").tabIndex = -1; $("campaign-detail").focus(); $("campaign-detail").scrollIntoView({block: "start"});
  } else if (item.kind === "durable") {
    const entry = durableEntries.find(value => value.id === item.id); if (!entry) return;
    workspaceNavigate("durable"); selectDurable(entry); $("durable-detail").tabIndex = -1; $("durable-detail").focus(); $("durable-detail").scrollIntoView({block: "start"});
  }
}

function updateCampaignStudyChoices() {
  const target = $("campaign-study-choice"); if (!target) return;
  const records = new Map();
  if (configuration) records.set(configuration.id, {id: configuration.id, config: configuration.config || formConfig()});
  for (const job of jobs) if (job.configuration && !records.has(job.configuration)) records.set(job.configuration, {id: job.configuration, label: "Saved study · " + new Date(job.created_at).toLocaleString()});
  const entries = [...records.values()], key = JSON.stringify(entries.map(value => [value.id, value.config, value.label]));
  if (target.dataset.revision === key) return; target.dataset.revision = key;
  const value = target.value; target.replaceChildren(); const placeholder = document.createElement("option"); placeholder.value = ""; placeholder.textContent = "Choose a saved or current study"; target.append(placeholder);
  for (const record of entries) { const option = document.createElement("option"); option.value = record.id; option.textContent = record.label || (record.config.sources || []).map(model => model.id).join(" vs ") + " · " + record.id.slice(-8); target.append(option); }
  if (entries.some(record => record.id === value)) target.value = value;
  campaignControls();
}
async function useCampaignStudy() {
  if (active || campaignPending || libraryPending || m3Pending || durablePending || !$("campaign-study-choice").value) return;
  const identity = $("campaign-study-choice").value, revision = campaignDraftRevision;
  let applied = false;
  campaignPending = true; campaignControls(); campaignNotice("");
  try {
    const record = await api("configurations/" + identity); if (revision !== campaignDraftRevision) return;
    // A single repeat configuration is a new draft; no saved campaign is resumed.
    campaignCells = [campaignCellSnapshot(record, "cell_1")]; invalidateCampaign(); renderCampaignCells(); applied = true;
  } catch (error) { campaignNotice(error.message); }
  finally { campaignPending = false; campaignControls(); if (applied) $("campaign-repeats").focus(); }
}
async function loadGraphValues(kind) {
  const target = $(kind + "-graph-values"), request = ++uxGraphRequest;
  const own = kind === "study", identity = own ? selected?.id : librarySelected?.id;
  const digest = own ? uxStudySnapshot?.digest : librarySelected?.artifacts_sha256?.["report.json"];
  const revision = own ? JSON.stringify(uxStudySnapshot) : libraryRevision(librarySelected);
  const current = () => request === uxGraphRequest && (own ? selected?.id === identity && !$("results").hidden && JSON.stringify(uxStudySnapshot) === revision : librarySelected?.id === identity && !$("library-results").hidden && libraryRevision(librarySelected) === revision);
  if (!identity || !digest || !current()) return;
  target.textContent = "Loading the saved graph values…";
  try {
    const blob = await api(own ? "jobs/" + identity + "/report.json" : "library/entries/" + identity + "/artifacts/report.json", undefined, true);
    const bytes = await blob.arrayBuffer(), actual = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(value => value.toString(16).padStart(2, "0")).join("");
    if (!current()) return; if (actual !== digest) throw new Error("Saved graph values differ from the displayed report. Check saved analysis again.");
    uxRenderGraph(kind + "-graph-values", JSON.parse(new TextDecoder().decode(bytes)));
  } catch (error) { if (current()) target.textContent = error.message; }
}

$("study-form").addEventListener("submit", checkStudy);
$("run-study").addEventListener("click", () => begin("configurations/" + configuration.id + "/run").catch((error) => notice(error.message)));
$("install-task").addEventListener("click", () => begin("configurations/" + configuration.id + "/install").catch((error) => notice(error.message)));
$("cancel-job").addEventListener("click", () => api("jobs/" + active.id + "/cancel", {}).then(refresh).catch((error) => notice(error.message)));
$("reconstruct-study").addEventListener("click", () => begin("jobs/" + selected.id + "/reconstruct").catch((error) => notice(error.message)));
$("download-markdown").addEventListener("click", () => download("report.md"));
$("download-json").addEventListener("click", () => download("report.json"));
$("study-load-graph-data").addEventListener("click", () => loadGraphValues("study"));
$("library-load-graph-data").addEventListener("click", () => loadGraphValues("library"));
$("campaign-study-choice").addEventListener("change", campaignControls);
$("campaign-use-study").addEventListener("click", useCampaignStudy);
$("close-dialog").addEventListener("click", () => $("file-dialog").close());
$("directory-up").addEventListener("click", () => browse(picker.parent));
$("add-source").addEventListener("click", () => { let number = 3; const names = new Set([...$("sources").children].map((card) => card.querySelector(".source-id").value)); while (names.has("source_" + number)) number++; sourceCard({id: "source_" + number, model: "", declaration: ""}); numberSources(); invalidate(); });
document.querySelectorAll('input[name="scenario"],#stage-budget,#source-budget').forEach((input) => input.addEventListener("input", invalidate));
$("new-study").addEventListener("click", () => workspaceNavigate("m4"));

async function init() {
  $("library-show-hidden").addEventListener("change", renderLibraryList);
  $("archive-visibility").addEventListener("click", changeLibraryVisibility);
  $("archive-view-operation").addEventListener("click", () => { if (active) workspaceNavigate(workspaceJobView(active)); });
  try { session = await api("bootstrap"); session.defaults.sources.forEach(sourceCard); numberSources(); initializeStudyDraft(); jobs = session.jobs; renderHistory(); updateReadiness(); updateControls(); await refresh(); }
  catch (error) { notice(error.message); }
  const poll = async () => { await refresh(); setTimeout(poll, 1000); }; setTimeout(poll, 1000);
}

// Archive views use their own selection tokens. Study results keep their existing guards.
let libraryEntries = [], librarySelected = null, libraryRequest = 0, libraryFigureURL = null;
let librarySelection = 0, libraryListRequest = 0, libraryPending = false;
let libraryShown = null, libraryDirectory = "", libraryParent = null, libraryBrowseRequest = 0, libraryLastReportCheck = 0, libraryVerifyingID = null;

const libraryReportTasks = new Set(["m4-study-secure", "m3-forecast", "m3-compare", "m5-prognosis", "mmtt-sensitivity", "mmtt-sampling"]);
function libraryNotice(message) { const changed = $("library-notice").textContent !== message; $("library-notice").textContent = message; $("library-notice").hidden = !message; if (message && changed && typeof uxRevealError === "function") uxRevealError(message, $("library-notice")); }
function libraryBusy() { return !!active || libraryPending || libraryVerifyingID !== null || (typeof m3Pending !== "undefined" && m3Pending) || (typeof campaignPending !== "undefined" && campaignPending) || (typeof durablePending !== "undefined" && durablePending); }
function libraryRevision(entry) { return JSON.stringify([entry?.id, entry?.task, entry?.verification, entry?.verified_at, entry?.verified_job, entry?.artifacts_sha256, entry?.model_declaration_sha256, entry?.inventory_sha256, entry?.report_completeness, entry?.source_freshness, entry?.availability, entry?.can_view_report]); }
function libraryControls() {
  $("archive-register").disabled = libraryBusy();
  $("archive-verify").disabled = libraryBusy() || !librarySelected?.can_verify || !libraryReportTasks.has(librarySelected.task);
  const reason = $("archive-verify-reason");
  if (reason) {
    reason.textContent = libraryBusy() ? "Another operation is running or starting. Only one operation can run at a time; wait for it to finish or cancel it." : !librarySelected?.can_verify ? "This archive is unavailable for verification. Inspect its recorded error or availability above." : "";
    reason.hidden = !reason.textContent || !librarySelected || !libraryReportTasks.has(librarySelected.task);
  }
  const view = $("archive-view-operation"); if (view) view.hidden = !active || !librarySelected;
  if ($("archive-visibility")) $("archive-visibility").disabled = libraryBusy() || !librarySelected;
  const downloadable = librarySelected?.can_view_report && libraryShown === libraryRevision(librarySelected) && !$("library-results").hidden;
  for (const id of ["library-download-markdown", "library-download-json"]) $(id).disabled = !downloadable;
  $("library-download-svg").hidden = librarySelected?.task !== "m4-study-secure";
  $("library-download-svg").disabled = !downloadable || librarySelected?.task !== "m4-study-secure";
}
function clearLibraryResults() {
  ++libraryRequest; libraryShown = null; $("library-results").hidden = true; $("library-figure").hidden = true;
  $("library-m3-json").textContent = ""; $("library-m5-json").textContent = ""; $("library-m5-declaration").replaceChildren(); libraryControls();
  if ($("library-graph-values")) $("library-graph-values").replaceChildren();
}
function withdrawLibrarySnapshot(message) {
  clearLibraryResults();
  if (librarySelected) librarySelected = {...librarySelected, verification: "changed_since_verification", can_view_report: false, report_completeness: "unavailable"};
  libraryNotice(message); renderLibraryDetail();
}
async function changeLibraryVisibility() {
  if (!librarySelected || libraryBusy()) return;
  const identity = librarySelected.id, hidden = !librarySelected.hidden, selection = ++librarySelection;
  ++libraryListRequest; libraryPending = true; updateControls();
  try {
    const entry = await api("library/entries/" + identity + "/visibility", {hidden});
    if (librarySelected?.id === identity && librarySelection === selection) {
      librarySelected = entry; clearLibraryResults(); renderLibraryDetail();
      libraryNotice(hidden ? "Reference hidden; archive files were kept. Enable Show hidden references to restore it, or use Restore reference below." : "Reference restored. Check saved analysis explicitly when needed.");
    }
    await refreshLibrary();
  } catch (error) { if (librarySelection === selection) libraryNotice(error.message); }
  finally { libraryPending = false; updateControls(); }
}
function selectLibrary(entry) {
  ++librarySelection; librarySelected = entry; clearLibraryResults(); libraryNotice(""); renderLibraryList(); renderLibraryDetail(); displayLibraryReport();
  $("library-detail-title").focus({preventScroll: false});
  $("library-detail-title").scrollIntoView({block: "start", behavior: "instant"});
}
function libraryRecordedStatus(entry) { return entry.metadata?.native_report_status || entry.metadata?.recorded_status || "unavailable"; }
function renderLibraryList() {
  const task = $("library-task-filter").value, search = $("library-search").value.toLowerCase();
  const showHidden = $("library-show-hidden")?.checked === true;
  const visible = libraryEntries.filter((entry) => (showHidden || !entry.hidden) && (!task || entry.task === task) && [entry.path, entry.task, ...entry.tags, ...(entry.metadata?.models || []).map((m) => m.id)].join(" ").toLowerCase().includes(search));
  const signature = JSON.stringify([librarySelected?.id, visible.map((entry) => [entry.id, entry.path, entry.task, entry.tags, entry.hidden, entry.availability, entry.metadata_status, libraryRecordedStatus(entry)]), libraryEntries.length === 0]);
  renderRetainedContent($("library-list"), signature, () => {
  $("library-list").replaceChildren();
  if (!visible.length) { const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = libraryEntries.length ? "No registered archives match this filter." : "No directories registered yet."; $("library-list").append(empty); }
  for (const entry of visible) {
    const button = document.createElement("button"); button.type = "button"; button.className = "library-entry" + (librarySelected?.id === entry.id ? " current" : "");
    button.dataset.pollingKey = entry.id;
    const name = document.createElement("div"), title = document.createElement("strong"), subtitle = document.createElement("small"), badge = document.createElement("small");
    title.textContent = entry.path || "Archive root"; subtitle.textContent = entry.task + (entry.tags.length ? " · " + entry.tags.join(", ") : "");
    badge.textContent = (entry.hidden ? "Hidden reference · " : "") + (entry.availability === "unavailable" ? "Unavailable" : entry.metadata_status === "metadata_read" ? "Recorded " + libraryRecordedStatus(entry) : entry.metadata_status.replaceAll("_", " "));
    const context = document.createElement("small"); context.textContent = "Added " + (entry.created_at ? new Date(entry.created_at).toLocaleString() : "time not recorded") + " · Location " + (entry.root_id || "unavailable");
    name.append(title, subtitle, context); button.append(name, badge); button.addEventListener("click", () => { const current = libraryEntries.find((item) => item.id === entry.id); if (current) selectLibrary(current); }); $("library-list").append(button);
  }
  });
}
function renderLibraryDigests(checks) {
  const labels = {matched: "Supported recorded claims matched", mismatch: "Claimed files changed or missing", malformed: "Recorded claims invalid", unsupported: "Recorded claim schema unsupported", unavailable: "Recorded claims unavailable"};
  const kind = checks?.status === "matched" ? "good" : ["mismatch", "malformed"].includes(checks?.status) ? "bad" : "neutral";
  status($("library-digest-status"), labels[checks?.status] || "Recorded digest check unavailable", kind);
  $("library-digest-scope").textContent = "This metadata snapshot checked " + (checks?.checked_files ?? 0) + " supported recorded file claims. It does not cover all archive bytes, establish source authenticity or verify the native analysis.";
  renderRetainedContent($("library-digest-diagnostics"), JSON.stringify(checks), () => {
  $("library-digest-diagnostics").replaceChildren();
  for (const manifest of checks?.manifests || []) m3Row($("library-digest-diagnostics"), manifest.manifest + " · " + (labels[manifest.status] || "Unavailable"), ["Schema: " + (manifest.schema || "unavailable") + " · Claim base: " + (manifest.base ?? "unsupported") + " · Claim shape: " + (manifest.claim_shape ?? "unsupported") + " · Checked files: " + manifest.checked_files, "Missing / changed claims: " + JSON.stringify(manifest.mismatches || []), "Invalid / unsupported claims: " + JSON.stringify(manifest.errors || [])], manifest.manifest);
  if (!(checks?.manifests || []).length && checks?.mismatches?.length) m3Row($("library-digest-diagnostics"), "Recorded claim diagnostics", [JSON.stringify(checks.mismatches)]);
  }, librarySelected?.id);
}
function renderLibraryDetail() {
  const entry = librarySelected; $("library-detail").hidden = !entry; if (!entry) { libraryControls(); return; }
  $("library-detail-title").textContent = entry.path || "Archive root";
  if ($("archive-visibility")) $("archive-visibility").textContent = entry.hidden ? "Restore reference" : "Hide reference";
  if ($("library-location")) $("library-location").textContent = "Added " + (entry.created_at ? new Date(entry.created_at).toLocaleString() : "time not recorded") + " · Location " + (entry.root_id || "unavailable") + (entry.hidden ? " · Hidden reference" : "") + (entry.availability === "unavailable" ? ". To reconnect, add the existing archive from a currently enabled folder using Add saved results. An additional folder must be explicitly enabled at server startup." : "");
  status($("library-metadata-status"), "Metadata: " + entry.metadata_status.replaceAll("_", " "), entry.metadata_status === "metadata_read" ? "good" : "neutral");
  const meta = entry.metadata || {};
  $("library-metadata-summary").textContent = entry.task + " · " + (meta.protocol || "Protocol unavailable") + " · " + ((meta.models || []).map((m) => m.id).join(", ") || "Models unavailable") + (entry.indexed_at ? " · Snapshot read " + new Date(entry.indexed_at).toLocaleString() : "");
  const error = entry.availability_error || entry.verification_error || entry.metadata_error;
  $("library-error").textContent = error || ""; $("library-error").hidden = !error;
  status($("library-recorded-status"), "Recorded status: " + libraryRecordedStatus(entry));
  renderLibraryDigests(entry.hash_checks);
  const labels = {native_reader_verified: "Native analysis verified in snapshot", recorded_verification: "Previously verified; recheck", changed_since_verification: "Archive or snapshot changed", verification_failed: "Verification failed", verifying: "Verification in progress", not_requested: "Verification not requested"};
  status($("library-verification-status"), labels[entry.verification] || "Verification unavailable", entry.verification === "native_reader_verified" ? "good" : ["verification_failed", "changed_since_verification"].includes(entry.verification) ? "bad" : "neutral");
  status($("library-completeness"), "Report completeness: " + (libraryRecordedStatus(entry) === "interrupted" && entry.report_completeness === "failed" ? "incomplete (interrupted; numerical acceptance failed)" : entry.report_completeness), entry.report_completeness === "complete" ? "good" : "neutral");
  status($("library-freshness"), entry.source_freshness === "not_rechecked_since_worker" ? "Source not fully rechecked since worker" : "Source freshness unavailable");
  $("library-reader-scope").textContent = entry.reader_scope + (entry.verified_at ? " · Verification snapshot " + new Date(entry.verified_at).toLocaleString() : "");
  $("archive-verify").hidden = !libraryReportTasks.has(entry.task); libraryControls();
}
function validateLibraryM3(report, task) {
  const comparison = task === "m3-compare", schema = comparison ? "opent1d.m3.comparison/1" : "opent1d.m3.researcher/1";
  const analysis = comparison ? report?.common : report?.evaluation;
  const people = analysis?.people && Object.entries(analysis.people);
  if (report?.schema !== schema || !people || people.length < 1 || people.length > 128 || analysis.planned_people !== people.length || !Number.isSafeInteger(analysis.contributing_people) || analysis.contributing_people < 0 || analysis.contributing_people > people.length || typeof analysis.complete_cohort !== "boolean" || !analysis.equal_person_metrics) throw new Error("The native M3 report is incomplete, incompatible or exceeds the supported roster.");
  if (comparison && (!Array.isArray(report.candidate_order) || report.candidate_order.length < 2 || report.candidate_order.length > 8 || new Set(report.candidate_order).size !== report.candidate_order.length || !report.candidates || report.candidate_order.some((id) => typeof id !== "string" || !Object.hasOwn(report.candidates, id) || !report.candidates[id]?.coordinator))) throw new Error("The native M3 candidate roster is incompatible or exceeds the supported bound.");
  const methods = comparison ? [...report.candidate_order, "persistence"] : ["candidate", "persistence"];
  if (methods.some((method) => !Object.hasOwn(analysis.equal_person_metrics, method) || ["mae", "rmse", "bias"].some((field) => { const value = analysis.equal_person_metrics[method]?.[field]; return value !== null && !Number.isFinite(value); }))) throw new Error("The native M3 metric fields are incompatible.");
  if (comparison) {
    if (!Array.isArray(analysis.contrasts) || analysis.contrasts.length > 36) throw new Error("The native M3 contrast roster exceeds the supported bound.");
    for (const id of report.candidate_order) if (report.candidates[id].single_candidate) validateLibraryM3(report.candidates[id].single_candidate, "m3-forecast");
  }
  for (const [, person] of people) {
    const counts = comparison ? [person.planned_origins, person.common_scored] : [person.planned, person.attempted, person.not_attempted, person.forecastable, person.scored];
    if (counts.some((count) => !Number.isSafeInteger(count) || count < 0) || !Array.isArray(person.ineligibility_reasons) || typeof person.eligible_for_primary !== "boolean") throw new Error("The native M3 participant accounting is incompatible.");
  }
}
function validateLibraryM5(report, declaration) {
  const fail = () => { throw new Error("The native M5 report or declared provenance is incompatible with the fixed synthetic task."); };
  const object = (value) => value && typeof value === "object" && !Array.isArray(value);
  const exact = (value, keys) => object(value) && Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
  const text = (value, maximum = 500) => typeof value === "string" && value.trim().length > 0 && value.length <= maximum;
  const hash = (value) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  const amount = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1000;
  const runtime = (value) => exact(value, ["implementation", "python_version", "python_major_minor"]) && value.implementation === "CPython" && /^\d+\.\d+\.\d+$/.test(value.python_version) && value.python_version.startsWith(value.python_major_minor + ".") && value.python_major_minor === declaration?.runtime?.python_major_minor;
  const sameRuntime = (left, right) => object(left) && object(right) && ["implementation", "python_version", "python_major_minor"].every((key) => left[key] === right[key]);
  if (!object(report) || report.schema !== "m5-researcher-workflow/1" || report.claim !== "invented_pipeline_check_only" || report.human_execution_authorized !== false || report.treatment_effect_or_cure_estimated !== false || report.training_provenance !== "researcher_declared_not_independently_verified" || typeof report.candidate_execution_complete !== "boolean" || !["complete", "incomplete"].includes(report.comparison_status)) fail();
  if (!exact(declaration, ["schema", "model_id", "rights_basis", "input_schema", "output_unit", "source_sha256", "state_sha256", "runtime", "training"]) || declaration.schema !== "m5-prognostic-model/1" || typeof declaration.model_id !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(declaration.model_id) || !text(declaration.rights_basis) || declaration.input_schema !== "m5-landmark-input/1" || declaration.output_unit !== "U/day" || !hash(declaration.source_sha256) || !hash(declaration.state_sha256) || declaration.model_id !== report.model_id || declaration.source_sha256 !== report.source_sha256 || declaration.state_sha256 !== report.state_sha256 || !exact(declaration.runtime, ["python_major_minor", "dependencies"]) || typeof declaration.runtime.python_major_minor !== "string" || !/^\d+\.\d+$/.test(declaration.runtime.python_major_minor) || !Array.isArray(declaration.runtime.dependencies) || declaration.runtime.dependencies.length !== 0 || !exact(declaration.training, ["phase", "fixture_sha256", "participant_aliases"]) || declaration.training.phase !== "development_only" || !hash(declaration.training.fixture_sha256)) fail();
  if (!Array.isArray(report.people) || report.people.length !== 32 || report.roster_count !== 32 || report.development_roster_count !== 24 || report.evaluation_roster_count !== 8 || report.development_eligible_count !== 20 || report.evaluation_eligible_count !== 7 || report.excluded_count !== 5 || !Array.isArray(report.evaluation_predictions) || report.evaluation_predictions.length !== 7) fail();
  const aliases = new Set(), development = [], evaluation = [];
  for (const person of report.people) {
    if (!object(person) || !/^SYN0(?:0[1-9]|[12][0-9]|3[0-2])$/.test(person.alias) || aliases.has(person.alias) || person.split !== (Number(person.alias.slice(-3)) % 4 === 0 ? "evaluation" : "development") || typeof person.eligible !== "boolean" || !Array.isArray(person.issues) || person.issues.length > 8 || person.issues.some((issue) => !text(issue, 256)) || person.eligible !== (person.issues.length === 0) || !Array.isArray(person.intervening_infusion_days) || person.intervening_infusion_days.length > 32 || person.intervening_infusion_days.some((day) => !Number.isFinite(day) || day < 0 || day >= 365) || typeof person.y1_present !== "boolean" || typeof person.visit15_present !== "boolean") fail();
    aliases.add(person.alias);
    if (person.eligible) (person.split === "development" ? development : evaluation).push(person.alias);
  }
  if (development.length !== 20 || evaluation.length !== 7 || !Array.isArray(declaration.training.participant_aliases) || JSON.stringify(declaration.training.participant_aliases) !== JSON.stringify(development)) fail();
  let paired = 0, executionComplete = true;
  const predicted = new Set();
  for (const item of report.evaluation_predictions) {
    if (!object(item) || !evaluation.includes(item.alias) || predicted.has(item.alias) || !amount(item.observed_reported_insulin_mean_u_day) || !amount(item.baseline_prediction_u_day) || !Array.isArray(item.attempts) || item.attempts.length > 2) fail();
    predicted.add(item.alias);
    for (const [index, attempt] of item.attempts.entries()) {
      if (!exact(attempt, ["attempt", "status", "prediction_u_day", "runtime"]) || attempt.attempt !== index + 1 || !["completed", "timeout", "worker_failed", "invalid_output", "interrupted"].includes(attempt.status)) fail();
      if (attempt.status === "completed" ? !amount(attempt.prediction_u_day) || !runtime(attempt.runtime) || !sameRuntime(attempt.runtime, report.provenance?.host_runtime) : attempt.prediction_u_day !== null || attempt.runtime !== null) fail();
    }
    const attempts = item.attempts;
    const status = !attempts.length ? "not_attempted" : attempts.some((attempt) => attempt.status === "interrupted") ? "interrupted" : attempts.length < 2 ? "incomplete" : attempts.some((attempt) => attempt.status !== "completed") ? "failed" : attempts[0].prediction_u_day !== attempts[1].prediction_u_day || !sameRuntime(attempts[0].runtime, attempts[1].runtime) ? "not_reproducible" : "completed";
    if (item.candidate_status !== status || (status === "completed" ? item.candidate_prediction_u_day !== attempts[0].prediction_u_day : item.candidate_prediction_u_day !== null)) fail();
    if (status === "completed") paired++;
    if (attempts.length !== 2 || attempts.some((attempt) => attempt.status === "interrupted")) executionComplete = false;
  }
  if (report.paired_count !== paired || report.candidate_coverage !== paired / 7 || report.comparison_status !== (paired === 7 ? "complete" : "incomplete") || report.candidate_execution_complete !== executionComplete || report.metric !== "mean absolute error in reported insulin U/day" || !amount(report.baseline_mae_all_eligible_u_day)) fail();
  for (const key of ["baseline_mae_paired_u_day", "candidate_mae_paired_u_day", "mae_change_candidate_minus_baseline_u_day"]) {
    const value = report[key];
    if (paired === 0 ? value !== null : typeof value !== "number" || !Number.isFinite(value) || (key === "mae_change_candidate_minus_baseline_u_day" ? Math.abs(value) > 1000 : !amount(value))) fail();
  }
  if (!exact(report.provenance, ["schema", "git_revision", "host_runtime", "worker_timeout_seconds", "source_identity"]) || report.provenance.schema !== "m5-researcher-provenance/1" || report.provenance.source_identity !== "saved source bytes; git revision alone does not identify local edits" || !/^[0-9a-f]{40}$/.test(report.provenance.git_revision) || !runtime(report.provenance.host_runtime) || !Number.isFinite(report.provenance.worker_timeout_seconds) || report.provenance.worker_timeout_seconds <= 0 || report.provenance.worker_timeout_seconds > 60 || !hash(report.tooling_lock_sha256) || !exact(report.implementation_sha256, ["source-contract.py", "source-worker.py", "source-report.py", "source-run.py", "source-synthetic.py"]) || Object.values(report.implementation_sha256).some((value) => !hash(value))) fail();
}
function renderLibraryM5(report, declaration) {
  const target = (suffix) => $("library-m5-" + suffix);
  target("denominators").replaceChildren();
  for (const [value, label] of [[report.roster_count, "Planned invented participants"], [report.development_eligible_count + " / " + report.development_roster_count, "Eligible / planned development"], [report.evaluation_eligible_count + " / " + report.evaluation_roster_count, "Eligible / planned evaluation"], [report.paired_count + " / " + report.evaluation_eligible_count, "Reproducible evaluation pairs"], [report.candidate_coverage, "Native paired coverage"]]) m3Metric(target("denominators"), value, label);
  target("analysis-scope").textContent = "Invented software comparison only; no human prognosis, biological validity or treatment evidence. Comparison: " + report.comparison_status + "; prediction execution accounting: " + (report.candidate_execution_complete ? "complete" : "incomplete") + ". Paired metrics use the same successfully repeated participants. The full baseline covers all seven eligible evaluation participants and must not be compared with a candidate's smaller subset. " + (report.paired_count === 0 ? "No reproducible pairs: paired metrics are native null values, not zero. " : "") + "Negative paired difference means lower synthetic error on that subset; there is no advancement threshold. This interface computes no scientific metric.";
  target("errors").replaceChildren();
  for (const [label, value] of [["Baseline MAE — all 7 eligible evaluation participants", report.baseline_mae_all_eligible_u_day], ["Baseline MAE — same paired subset (" + report.paired_count + ")", report.baseline_mae_paired_u_day], ["Candidate MAE — same paired subset (" + report.paired_count + ")", report.candidate_mae_paired_u_day], ["Candidate minus baseline MAE — paired subset", report.mae_change_candidate_minus_baseline_u_day]]) {
    const row = document.createElement("tr"), heading = document.createElement("th"), cell = document.createElement("td"); heading.scope = "row"; heading.textContent = label; cell.textContent = m3Value(value); row.append(heading, cell); target("errors").append(row);
  }
  target("people").replaceChildren();
  for (const person of report.people) m3Row(target("people"), person.alias + " · " + person.split + " · " + (person.eligible ? "eligible" : "excluded"), ["Exclusion reasons: " + (person.issues.join(", ") || "none"), "Later infusions (days): " + (person.intervening_infusion_days.join(", ") || "none") + " · Y1 present: " + person.y1_present + " · V15 present: " + person.visit15_present, person.split === "development" ? "Development participant; no evaluation prediction attempts." : !person.eligible ? "Excluded evaluation participant; no prediction attempts planned." : "Eligible evaluation participant; both attempt positions retained below."]);
  target("attempts").replaceChildren();
  for (const item of report.evaluation_predictions) {
    const paragraphs = ["Observed reported insulin mean: " + item.observed_reported_insulin_mean_u_day + " U/day · Baseline: " + item.baseline_prediction_u_day + " U/day · Paired candidate: " + m3Value(item.candidate_prediction_u_day) + " U/day"];
    for (let index = 0; index < 2; index++) {
      const attempt = item.attempts[index];
      paragraphs.push("Attempt " + (index + 1) + ": " + (attempt?.status || "not_attempted") + " · Saved prediction: " + m3Value(attempt?.prediction_u_day) + " U/day · Runtime: " + (attempt?.runtime ? JSON.stringify(attempt.runtime) : "null"));
    }
    m3Row(target("attempts"), item.alias + " · " + item.candidate_status, paragraphs);
  }
  target("declaration").replaceChildren();
  m3Row(target("declaration"), declaration.model_id + " · supplier-declared provenance", ["Rights basis (self-attested): " + declaration.rights_basis, "Training (self-attested, not independently verified): " + JSON.stringify(declaration.training), "Source SHA-256: " + declaration.source_sha256 + " · Frozen state SHA-256: " + declaration.state_sha256, "Input contract: " + declaration.input_schema + " · Output unit: " + declaration.output_unit + " · Declared runtime: " + JSON.stringify(declaration.runtime), "Execution provenance: " + JSON.stringify(report.provenance), "Tooling lock SHA-256: " + report.tooling_lock_sha256 + " · Implementation SHA-256: " + JSON.stringify(report.implementation_sha256)]);
  target("json").textContent = JSON.stringify(report, null, 2);
}
async function displayLibraryReport() {
  if (!librarySelected?.can_view_report || !libraryReportTasks.has(librarySelected.task) || librarySelected.verification === "verifying" || librarySelected.id === libraryVerifyingID || (active?.operation === "library_verify" && active.request?.entry?.id === librarySelected.id)) { clearLibraryResults(); return; }
  const identity = librarySelected.id, revision = libraryRevision(librarySelected), selection = librarySelection;
  if (libraryShown === revision && Date.now() - libraryLastReportCheck < 5000) return;
  const request = ++libraryRequest;
  const current = () => libraryRevision(librarySelected) === revision && librarySelection === selection && libraryRequest === request && libraryVerifyingID !== identity;
  if (libraryShown !== revision) { $("library-results").hidden = true; $("library-figure").hidden = true; } libraryControls();
  try {
    const report = await api("library/entries/" + identity + "/report"); if (!current()) return;
    const task = librarySelected.task, m3 = task === "m3-forecast" || task === "m3-compare", m5 = task === "m5-prognosis", observation = task === "mmtt-sensitivity" || task === "mmtt-sampling", verified = report.verification === "native_reader_verified";
    $("library-m3-results").hidden = !m3; $("library-m4-results").hidden = task !== "m4-study-secure"; $("library-m5-results").hidden = !m5;
    if ($("library-observation-results")) $("library-observation-results").hidden = !observation;
    if (m3 || m5 || observation) {
      if (report.task !== librarySelected.task || report.verification !== librarySelected.verification || report.report_sha256 !== librarySelected.artifacts_sha256?.["report.json"] || report.report_completeness !== librarySelected.report_completeness || report.source_freshness !== librarySelected.source_freshness || report.verification_scope !== "verified_snapshot" || report.schema !== report.native_report?.schema) throw new Error("The report snapshot does not match the selected native library entry.");
      if (observation) {
        (task === "mmtt-sampling" ? samplingValidateNative : obsValidateNative)(report.native_report);
        renderRetainedContent($("library-observation-results"), report.report_sha256, () => (task === "mmtt-sampling" ? renderSamplingReport : renderObservationReport)(report.native_report, $("library-observation-results")), identity, !$("library-observation-results").children.length);
        const complete = report.native_report.coverage.complete_cohort;
        if (report.report_completeness !== (complete ? "complete" : "incomplete")) throw new Error("Observation snapshot coverage differs from native accounting.");
        status($("library-acceptance"), (verified ? "Verified snapshot: " : "Recorded snapshot: ") + (complete ? "complete synthetic calculation" : "incomplete synthetic calculation") + "; human validity remains separate", complete && verified ? "good" : "warning");
      } else if (m5) {
        if (!/^[0-9a-f]{64}$/.test(report.model_declaration_sha256) || report.model_declaration_sha256 !== librarySelected.model_declaration_sha256) throw new Error("The declared provenance does not match the selected M5 snapshot.");
        validateLibraryM5(report.native_report, report.model_declaration);
        const complete = report.native_report.comparison_status === "complete" && report.native_report.candidate_execution_complete;
        if (report.report_completeness !== (complete ? "complete" : "incomplete")) throw new Error("The M5 snapshot completeness differs from native accounting.");
        if (libraryShown !== revision) renderLibraryM5(report.native_report, report.model_declaration);
        status($("library-acceptance"), (verified ? "Verified snapshot: " : "Recorded snapshot: ") + (complete ? "complete synthetic comparison" : "incomplete synthetic comparison") + "; prognostic quality is a separate assessment", complete && verified ? "good" : "warning");
      } else {
        validateLibraryM3(report.native_report, report.task);
        // Rechecking the same bound bytes must preserve open rosters and keyboard focus.
        if (libraryShown !== revision) renderM3Native(report.native_report, "library-m3");
        const complete = (report.native_report.common || report.native_report.evaluation).complete_cohort;
        status($("library-acceptance"), (verified ? "Verified snapshot: " : "Recorded snapshot: ") + (complete ? "complete synthetic cohort" : "incomplete synthetic cohort") + "; prediction quality is a separate assessment", complete && verified ? "good" : "warning");
      }
    } else {
      status($("library-acceptance"), !verified ? "Acceptance unverified; saved snapshot only" : report.passed ? "Numerically accepted in verified snapshot" : "Failed / incomplete in verified snapshot", !verified ? "warning" : report.passed ? "good" : "bad");
      $("library-denominators").replaceChildren(); const d = report.denominators || {};
      for (const [label, accepted, planned] of [["Accepted sources", d.accepted_sources, d.sources], ["Accepted source / load cases", d.accepted_source_scenarios, d.source_scenarios], ["Accepted source pairs", d.accepted_pairs, d.pairs]]) m3Metric($("library-denominators"), (accepted ?? "—") + " / " + (planned ?? "—"), label);
      $("library-source-results").replaceChildren();
      for (const [name, source] of Object.entries(report.sources || {})) { const row = document.createElement("tr"); for (const value of [name, source.ancestry || "—", source.status || "unavailable", source.accepted ? "Accepted" : "Not accepted"]) { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); } $("library-source-results").append(row); }
      $("library-limitations").replaceChildren(); for (const limit of report.limitations || []) { const item = document.createElement("li"); item.textContent = limit; $("library-limitations").append(item); }
    }
    $("library-results").hidden = false; libraryShown = revision; libraryLastReportCheck = Date.now(); libraryControls();
    if ($("library-evidence-summary")) $("library-evidence-summary").hidden = observation;
    if (!observation && typeof uxRenderEvidence === "function") uxRenderEvidence("library-evidence-summary", m5 ? "m5" : m3 ? "m3" : "m4", report.native_report || report, report.verification);
    if (task === "m4-study-secure") try {
      const blob = await api("library/entries/" + identity + "/artifacts/figure.svg", undefined, true); if (!current()) return;
      if (libraryFigureURL) URL.revokeObjectURL(libraryFigureURL); libraryFigureURL = URL.createObjectURL(blob); $("library-figure").src = libraryFigureURL; $("library-figure").hidden = false;
    } catch (error) { if (current()) withdrawLibrarySnapshot(error.message); }
  } catch (error) { if (current()) withdrawLibrarySnapshot(error.message); }
}
async function refreshLibrary() {
  const request = ++libraryListRequest, selection = librarySelection;
  try {
    const entries = (await api("library/entries")).entries;
    if (request !== libraryListRequest || selection !== librarySelection) return;
    libraryEntries = entries;
    if (librarySelected) {
      const updated = entries.find((entry) => entry.id === librarySelected.id);
      if (libraryRevision(updated) !== libraryRevision(librarySelected)) clearLibraryResults();
      librarySelected = updated || null;
    }
    renderLibraryList(); renderLibraryDetail(); await displayLibraryReport();
  } catch (error) { if (request === libraryListRequest && selection === librarySelection) withdrawLibrarySnapshot(error.message); }
}
async function browseArchives(directory) {
  const root = $("archive-root").value, request = ++libraryBrowseRequest;
  const current = () => request === libraryBrowseRequest && $("archive-root").value === root;
  $("archive-select-directory").disabled = true;
  try {
    const listing = await api("library/files?root_id=" + encodeURIComponent(root) + "&directory=" + encodeURIComponent(directory)); if (!current()) return;
    libraryDirectory = listing.directory; libraryParent = listing.parent;
    $("archive-directory").textContent = listing.directory || "Archive root"; $("archive-directory-up").disabled = listing.parent === null;
    $("archive-directories").replaceChildren();
    for (const entry of listing.entries) { const button = document.createElement("button"); button.type = "button"; button.className = "file-entry"; button.textContent = "▸ " + entry.name; button.addEventListener("click", () => browseArchives(entry.path)); $("archive-directories").append(button); }
    if (!listing.entries.length) $("archive-directories").textContent = "No child directories. You can select this directory.";
    $("archive-select-directory").disabled = false;
  } catch (error) { if (current()) $("archive-directories").textContent = error.message; }
}
async function downloadLibrary(name) {
  const identity = librarySelected?.id, revision = libraryRevision(librarySelected), selection = librarySelection;
  if (!identity || !librarySelected.can_view_report || libraryShown !== revision || $("library-results").hidden || !["report.json", "report.md", ...(librarySelected.task === "m4-study-secure" ? ["figure.svg"] : [])].includes(name)) return;
  const current = () => librarySelected?.id === identity && libraryRevision(librarySelected) === revision && librarySelection === selection;
  try { const blob = await api("library/entries/" + identity + "/artifacts/" + name, undefined, true); if (!current()) return;
    const url = URL.createObjectURL(blob), link = document.createElement("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { if (current()) withdrawLibrarySnapshot(error.message); }
}
async function initLibrary() {
  try {
    const roots = (await api("library/roots")).roots;
    for (const root of roots) { const option = document.createElement("option"); option.value = root.id; option.textContent = root.name + " · " + root.directory; $("archive-root").append(option); }
    for (const option of $("archive-task").options) $("library-task-filter").append(option.cloneNode(true));
    await refreshLibrary();
  } catch (error) { libraryNotice(error.message); }
}
$("open-library").addEventListener("click", () => { workspaceNavigate("library"); });
$("archive-form").addEventListener("submit", async (event) => {
  event.preventDefault(); if (libraryBusy() || !$("archive-form").reportValidity()) return; libraryNotice(""); libraryPending = true; updateControls();
  try { const job = await api("library/entries", {root_id: $("archive-root").value, path: $("archive-path").value, task: $("archive-task").value, tags: $("archive-tags").value.split(",").map((t) => t.trim()).filter(Boolean)});
    active = job; selected = job; clearLibraryResults(); ++librarySelection; librarySelected = null; await refresh();
    const id = job.request?.entry?.id; if (id) { const entry = libraryEntries.find((e) => e.id === id); if (entry) selectLibrary(entry); }
  } catch (error) { libraryNotice(error.message); }
  finally { libraryPending = false; updateControls(); }
});
$("archive-verify").addEventListener("click", async () => {
  if (libraryBusy() || !librarySelected?.can_verify || !libraryReportTasks.has(librarySelected.task)) return; const identity = librarySelected.id; libraryVerifyingID = identity; libraryPending = true; clearLibraryResults(); libraryNotice(""); updateControls();
  try { const job = await api("library/entries/" + identity + "/verify", {}); active = job; selected = job; libraryVerifyingID = null; await refresh(); }
  catch (error) { libraryVerifyingID = null; if (librarySelected?.id === identity) libraryNotice(error.message); }
  finally { libraryPending = false; updateControls(); }
});
$("archive-browse").addEventListener("click", () => { $("archive-dialog").showModal(); browseArchives($("archive-path").value); });
$("archive-close-dialog").addEventListener("click", () => { ++libraryBrowseRequest; $("archive-dialog").close(); });
$("archive-directory-up").addEventListener("click", () => browseArchives(libraryParent || ""));
$("archive-select-directory").addEventListener("click", () => { $("archive-path").value = libraryDirectory; ++libraryBrowseRequest; $("archive-dialog").close(); });
$("archive-root").addEventListener("change", () => { ++libraryBrowseRequest; $("archive-path").value = ""; });
$("library-task-filter").addEventListener("change", renderLibraryList); $("library-search").addEventListener("input", renderLibraryList);
$("library-download-markdown").addEventListener("click", () => downloadLibrary("report.md")); $("library-download-json").addEventListener("click", () => downloadLibrary("report.json")); $("library-download-svg").addEventListener("click", () => downloadLibrary("figure.svg"));

// Campaign drafts, stored campaign selection and study readiness remain independent.
let campaignCells = [], campaignConfiguration = null, campaignPending = false, campaignDraftRevision = 0;
let campaigns = [], campaignSelected = null, campaignRequest = 0, campaignSelection = 0;
let campaignShown = null, campaignLastReportCheck = 0, campaignActionID = null, campaignListRequest = 0, campaignFollowID = null;
const observedInstallJobs = new Set();

function observeInstall(job) {
  if (!job || !["install", "campaign_install"].includes(job.operation) || observedInstallJobs.has(job.id)) return;
  observedInstallJobs.add(job.id);
  ready = false;
  if (campaignConfiguration) campaignConfiguration.ready = false;
  if (typeof m3Configuration !== "undefined" && m3Configuration) { m3Configuration.ready = false; renderM3Readiness(); }
  updateReadiness(); renderCampaignPlan();
}

function campaignNotice(message) { const changed = $("campaign-notice").textContent !== message; $("campaign-notice").textContent = message; $("campaign-notice").hidden = !message; if (message && changed && typeof uxRevealError === "function") uxRevealError(message, $("campaign-notice")); }
function invalidateCampaign() { ++campaignDraftRevision; campaignConfiguration = null; renderCampaignPlan(); campaignControls(); }
function campaignControls() {
  const busy = !!active || campaignPending || (typeof m3Pending !== "undefined" && m3Pending) || (typeof libraryPending !== "undefined" && libraryPending);
  $("campaign-form").querySelectorAll("input,select,button").forEach((element) => { element.disabled = busy || element.dataset.edgeDisabled === "true"; });
  $("campaign-use-study").disabled = busy || !$("campaign-study-choice").value;
  $("campaign-add-cell").disabled = busy || campaignCells.length >= 32;
  $("campaign-run").disabled = busy || !campaignConfiguration?.ready;
  $("campaign-install").disabled = busy || !campaignCells.length;
  $("campaign-check").disabled = busy || !campaignCells.length;
  $("campaign-check-saved").disabled = busy || !campaignSelected;
  $("campaign-resume").disabled = busy || !campaignSelected?.can_resume;
  $("campaign-reconstruct").disabled = busy || !campaignSelected;
  $("campaign-cell-id").disabled = busy || campaignCells.length >= 32;
}
function campaignCellSnapshot(record, id) {
  if (!record?.id || !Array.isArray(record.config?.sources) || !Array.isArray(record.config?.scenarios)) throw new Error("The study snapshot response is incomplete.");
  return {id, configuration_id: record.id, source_ids: record.config.sources.map((source) => source.id), scenarios: [...record.config.scenarios], timeout_seconds: record.config.timeout_seconds, source_timeout_seconds: record.config.source_timeout_seconds};
}
async function captureCampaignCell(replaceIndex = null) {
  if (active || campaignPending || (typeof libraryPending !== "undefined" && libraryPending) || !$("study-form").reportValidity()) return;
  const id = replaceIndex === null ? $("campaign-cell-id").value : campaignCells[replaceIndex]?.id;
  if (!/^[a-z][a-z0-9_-]{0,63}$/.test(id || "")) { campaignNotice("Choose a lowercase cell ID, beginning with a letter."); return; }
  if (replaceIndex === null && campaignCells.some((cell) => cell.id === id)) { campaignNotice("Each cell needs a unique ID."); return; }
  if (replaceIndex === null && campaignCells.length >= 32) return;
  const revision = campaignDraftRevision, captured = formConfig();
  campaignPending = true; campaignNotice(""); campaignControls();
  try {
    const record = await api("configurations", captured);
    if (campaignDraftRevision !== revision) return;
    const cell = campaignCellSnapshot(record, id);
    if (replaceIndex === null) campaignCells.push(cell); else campaignCells[replaceIndex] = cell;
    let next = 1; while (campaignCells.some((c) => c.id === "cell_" + next)) ++next;
    $("campaign-cell-id").value = "cell_" + next;
    invalidateCampaign(); renderCampaignCells(replaceIndex === null ? campaignCells.length - 1 : replaceIndex);
  } catch (error) { if (campaignDraftRevision === revision) campaignNotice(error.message); }
  finally { campaignPending = false; campaignControls(); }
}
function campaignMatrix() {
  const repeats = Number($("campaign-repeats").value), timeout = Number($("campaign-budget").value);
  if (!campaignCells.length || campaignCells.length > 32) throw new Error("Choose one to 32 study cells.");
  if (!Number.isInteger(repeats) || repeats < 1 || repeats > 8 || campaignCells.length * repeats > 128) throw new Error("Choose one to eight repetitions, with at most 128 total slots.");
  if (!Number.isInteger(timeout) || timeout < 1 || timeout > 10800) throw new Error("Choose a whole-study deadline from 1 to 10800 seconds.");
  const ids = new Set();
  for (const cell of campaignCells) { if (!/^[a-z][a-z0-9_-]{0,63}$/.test(cell.id) || ids.has(cell.id)) throw new Error("Cell IDs must be unique lowercase names."); ids.add(cell.id); }
  return {cells: campaignCells.map((cell) => ({id: cell.id, configuration_id: cell.configuration_id})), repeats, timeout_seconds: timeout};
}
function renderCampaignCells(focusIndex = null) {
  const inputs = [];
  $("campaign-cells").replaceChildren();
  if (!campaignCells.length) { const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = "Add the first study cell to build a matrix."; $("campaign-cells").append(empty); }
  campaignCells.forEach((cell, index) => {
    const row = document.createElement("div"); row.className = "campaign-cell";
    const heading = document.createElement("div"); heading.className = "campaign-cell-top";
    const label = document.createElement("label"), input = document.createElement("input"); label.textContent = "Cell " + (index + 1) + " ID"; input.type = "text"; input.value = cell.id; input.required = true; input.maxLength = 64; input.pattern = "[a-z]([a-z0-9_]|-){0,63}";
    input.addEventListener("input", () => { cell.id = input.value; invalidateCampaign(); }); label.append(input); heading.append(label); inputs.push(input);
    const summary = document.createElement("p"); summary.className = "campaign-cell-summary";
    const loads = {fasting: "0 g", gastric_load_15g: "15 g", gastric_load_30g: "30 g"};
    summary.textContent = cell.source_ids.join(", ") + " · Loads " + cell.scenarios.map((s) => loads[s] || s).join(", ") + " · Native budgets " + cell.timeout_seconds + " s / " + cell.source_timeout_seconds + " s";
    const buttons = document.createElement("div"); buttons.className = "campaign-cell-buttons";
    for (const [name, action, disabled] of [["Move up", () => { [campaignCells[index - 1], campaignCells[index]] = [cell, campaignCells[index - 1]]; }, index === 0], ["Move down", () => { [campaignCells[index + 1], campaignCells[index]] = [cell, campaignCells[index + 1]]; }, index === campaignCells.length - 1], ["Remove", () => campaignCells.splice(index, 1), false]]) {
      const button = document.createElement("button"); button.type = "button"; button.className = "button subtle"; button.textContent = name; button.dataset.edgeDisabled = String(disabled); button.disabled = disabled || !!active; button.setAttribute("aria-label", name + " cell " + (index + 1));
      button.addEventListener("click", () => { if (active || campaignPending || (typeof libraryPending !== "undefined" && libraryPending) || disabled) return; action(); invalidateCampaign(); renderCampaignCells(name === "Move up" ? index - 1 : name === "Move down" ? index + 1 : Math.min(index, campaignCells.length - 1)); }); buttons.append(button);
    }
    const replace = document.createElement("button"); replace.type = "button"; replace.className = "button subtle"; replace.textContent = "Replace from current study"; replace.setAttribute("aria-label", "Replace cell " + (index + 1) + " with current study snapshot"); replace.addEventListener("click", () => captureCampaignCell(index)); buttons.append(replace);
    row.append(heading, summary, buttons); $("campaign-cells").append(row);
  });
  campaignControls();
  if (focusIndex !== null) { if (inputs[focusIndex]) inputs[focusIndex].focus(); else $("campaign-cell-id").focus(); }
}
function renderCampaignPlan() {
  const repeats = Number($("campaign-repeats").value), slots = campaignCells.length * repeats;
  const cases = repeats * campaignCells.reduce((count, cell) => count + cell.source_ids.length * cell.scenarios.length, 0);
  $("campaign-plan").textContent = campaignCells.length + " cells × " + (Number.isInteger(repeats) ? repeats : "—") + " repetitions = " + (Number.isInteger(slots) ? slots : "—") + " planned slots · " + (Number.isInteger(cases) ? cases : "—") + " planned source / load cases.";
  const ready = campaignConfiguration?.ready === true;
  status($("campaign-readiness"), ready ? "Campaign ready" : "Campaign not checked", ready ? "good" : "neutral");
  $("campaign-readiness-detail").textContent = ready ? "This frozen matrix passed its explicit runtime check. Installed identities are verified again during execution." : (typeof desktopApp !== "undefined" && desktopApp) ? "Check the frozen matrix and included components before starting numerical work." : "Check the frozen matrix before starting numerical work. Installation does not replace this check.";
  $("campaign-config-reference").textContent = campaignConfiguration ? campaignConfiguration.id + " · Frozen matrix " + campaignConfiguration.matrix_sha256 : "Draft matrix; no stored campaign configuration selected.";
  $("campaign-check").textContent = campaignConfiguration ? "Recheck campaign" : "Check campaign";
}
async function prepareCampaign() {
  if (campaignConfiguration) return campaignConfiguration;
  const revision = campaignDraftRevision, body = campaignMatrix();
  const result = await api("campaigns/configurations", body);
  if (campaignDraftRevision !== revision) throw new Error("The draft matrix changed; check its new configuration.");
  campaignConfiguration = result; renderCampaignPlan(); return result;
}
async function startCampaignConfiguration(operation) {
  if (active || campaignPending || (typeof libraryPending !== "undefined" && libraryPending) || !$("campaign-form").reportValidity()) return;
  const selection = campaignSelection;
  campaignPending = true; campaignNotice(""); campaignControls();
  try {
    const configuration = await prepareCampaign();
    if (operation === "run" && configuration.ready !== true) throw new Error("Check the campaign before running it.");
    if (operation !== "run") configuration.ready = false;
    const job = await api("campaigns/configurations/" + configuration.id + "/" + operation, {});
    observeInstall(job);
    active = job; selected = job; if (job.campaign_id) { campaignActionID = job.campaign_id; if (campaignSelection === selection) campaignFollowID = job.campaign_id; }
    renderCampaignPlan(); updateActivity(job); updateControls(); await refresh();
  } catch (error) { campaignNotice(error.message); }
  finally { campaignPending = false; campaignControls(); }
}
async function campaignJobFinished(job) {
  const identity = campaignConfiguration?.id, revision = campaignDraftRevision;
  if (identity && job.campaign_configuration_id === identity) {
    try { const record = await api("campaigns/configurations/" + identity); if (campaignConfiguration?.id === identity && campaignDraftRevision === revision) { campaignConfiguration = record; renderCampaignPlan(); if (job.error) campaignNotice(job.error); } }
    catch (error) { if (campaignConfiguration?.id === identity) campaignNotice(error.message); }
  }
  if (campaignActionID && job.campaign_id === campaignActionID) { campaignActionID = null; clearCampaignResults(); }
}
function campaignRevision(entry) { return [entry.id, entry.last_job, entry.verification, entry.report_completeness, entry.status, entry.error || ""].join(":"); }
function clearCampaignResults() { ++campaignRequest; campaignShown = null; $("campaign-results").hidden = true; }
function selectCampaign(entry) { ++campaignSelection; campaignSelected = entry; clearCampaignResults(); renderCampaignList(); renderCampaignDetail(); displayCampaignReport(); }
function selectCampaignID(identity) { const entry = campaigns.find((item) => item.id === identity); if (entry) { selectCampaign(entry); workspaceNavigate("campaigns"); } }
function renderCampaignList() {
  const signature = JSON.stringify([campaignSelected?.id, campaigns.map((entry) => [entry.id, entry.status, entry.cells.length, entry.repeats, entry.accepted_slots, entry.planned_slots])]);
  renderRetainedContent($("campaign-list"), signature, () => {
  $("campaign-list").replaceChildren();
  if (!campaigns.length) { const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = "No campaigns started yet."; $("campaign-list").append(empty); }
  for (const entry of campaigns) {
    const button = document.createElement("button"); button.type = "button"; button.className = "library-entry" + (campaignSelected?.id === entry.id ? " current" : "");
    button.dataset.pollingKey = entry.id;
    const name = document.createElement("div"), title = document.createElement("strong"), detail = document.createElement("small"), count = document.createElement("small");
    title.textContent = entry.id; detail.textContent = entry.status + " · " + entry.cells.length + " cells · " + entry.repeats + " repetitions"; count.textContent = (entry.accepted_slots ?? "—") + " / " + entry.planned_slots + " accepted slots";
    name.append(title, detail); button.append(name, count); button.addEventListener("click", () => { const current = campaigns.find((item) => item.id === entry.id); if (current) selectCampaign(current); }); $("campaign-list").append(button);
  }
  });
}
function renderCampaignDetail() {
  const entry = campaignSelected; $("campaign-detail").hidden = !entry; if (!entry) return;
  $("campaign-detail-title").textContent = entry.id;
  const job = jobs.find((item) => item.id === entry.last_job);
  status($("campaign-process-status"), "Process: " + (job?.state || "recorded operation"), job?.state === "failed" ? "bad" : "neutral");
  if (campaignShown !== campaignRevision(entry)) status($("campaign-coverage-status"), "Recorded coverage: " + (entry.accepted_slots ?? "—") + " / " + entry.planned_slots);
  const labels = {native_reader_verified: "Verified snapshot", recorded_verification: "Previously verified; reconstruct again", changed_since_verification: "Saved evidence changed", verification_failed: "Reconstruction failed", verifying: "Reconstruction in progress", not_requested: "Reconstruction not requested"};
  status($("campaign-verification-status"), labels[entry.verification] || "Verification unavailable", entry.verification === "native_reader_verified" ? "good" : "neutral");
  $("campaign-detail-scope").textContent = "Frozen matrix " + entry.matrix_sha256 + " · Source files have not been fully rechecked since the recorded worker. Resume requires an explicit configuration check.";
  $("campaign-detail-error").textContent = entry.error || ""; $("campaign-detail-error").hidden = !entry.error;
  if (typeof uxRenderEvidence === "function") uxRenderEvidence("campaign-evidence-summary", "campaign", {accepted_slots: entry.accepted_slots, planned_slots: entry.planned_slots}, entry.verification, entry.status);
  campaignControls();
}
function renderCampaignRoster(report) {
  if (!Array.isArray(report.slots) || report.slots.length > 128 || !Array.isArray(report.sessions) || report.sessions.length > 4096) throw new Error("The campaign report exceeds the supported roster view.");
  $("campaign-slots").replaceChildren(); $("campaign-sessions").replaceChildren();
  let retained = 0;
  for (const slot of report.slots) {
    if (!Array.isArray(slot.attempts) || (retained += slot.attempts.length) > 16384) throw new Error("The campaign report exceeds the supported attempt view.");
    const details = document.createElement("details"), summary = document.createElement("summary"); details.className = "campaign-slot";
    details.dataset.pollingKey = "slot:" + slot.id; summary.dataset.pollingKey = details.dataset.pollingKey;
    const last = slot.attempts.at(-1), state = slot.accepted ? "Accepted" : last?.outcome?.status || "not_attempted";
    summary.textContent = slot.cell + " · Repetition " + slot.repeat + " · " + state.replaceAll("_", " ") + " · " + slot.attempts.length + " retained attempts · " + slot.planned_source_scenarios + " planned source / load cases"; details.append(summary);
    if (slot.accepted_attempt) { const accepted = document.createElement("p"); accepted.className = "field-note"; accepted.textContent = "Satisfied by session " + slot.accepted_attempt.session + ", attempt " + slot.accepted_attempt.attempt + ". This slot is skipped on resume."; details.append(accepted); }
    if (!slot.attempts.length) { const empty = document.createElement("p"); empty.className = "field-note"; empty.textContent = "No native attempt recorded; this slot remains in the planned denominator."; details.append(empty); }
    for (const attempt of slot.attempts) {
      const row = document.createElement("div"), heading = document.createElement("h5"), outcome = document.createElement("p"); row.className = "campaign-attempt";
      heading.textContent = "Session " + attempt.session + " · Attempt " + attempt.attempt;
      const value = attempt.outcome || {}; outcome.textContent = "Process: " + (value.status || "unavailable") + " · Exit: " + (value.exit_code ?? "not recorded") + " · " + (attempt.accepted ? "Complete native study accepted" : "Slot not accepted") + (value.error_type ? " · " + value.error_type : "") + (attempt.native_error_type ? " · Native reader: " + attempt.native_error_type : ""); row.append(heading, outcome);
      const native = attempt.native_report, note = document.createElement("p");
      if (native) {
        const d = native.denominators || {}; note.textContent = "Native saved report: " + native.status + " · Accepted sources " + (d.accepted_sources ?? "—") + "/" + (d.sources ?? "—") + " · Source / load cases " + (d.accepted_source_scenarios ?? "—") + "/" + (d.source_scenarios ?? "—") + " · Pairs " + (d.accepted_pairs ?? "—") + "/" + (d.pairs ?? "—"); row.append(note);
        const sources = document.createElement("ul"); for (const [identity, source] of Object.entries(native.sources || {})) { const item = document.createElement("li"); item.textContent = identity + " · " + (source.status || "unavailable") + " · " + (source.accepted ? "Accepted" : "Not accepted"); sources.append(item); } row.append(sources);
      } else { note.textContent = "Native report unavailable; planned cases and this attempt remain visible."; row.append(note); }
      const chain = document.createElement("details"), chainTitle = document.createElement("summary"), hashes = document.createElement("p"); chain.dataset.pollingKey = details.dataset.pollingKey + ":attempt:" + attempt.session + ":" + attempt.attempt; chainTitle.dataset.pollingKey = chain.dataset.pollingKey; chainTitle.textContent = "Attempt identity"; hashes.textContent = "Manifest: " + (attempt.manifest_sha256 || "unavailable") + " · Previous attempt: " + (attempt.previous_attempt_manifest_sha256 || "none") + " · Native manifest: " + (value.native_manifest_sha256 || "unavailable"); chain.append(chainTitle, hashes); row.append(chain); details.append(row);
    }
    $("campaign-slots").append(details);
  }
  for (const session of report.sessions) { const row = document.createElement("details"), heading = document.createElement("summary"), hash = document.createElement("code"), note = document.createElement("p"); row.className = "campaign-session"; row.dataset.pollingKey = "session:" + session.number; heading.dataset.pollingKey = row.dataset.pollingKey; heading.textContent = "Session " + session.number + " · " + session.status + " · " + session.scheduled_slots + " scheduled slots"; note.textContent = session.interruption_signal === null ? "No recorded interruption signal" : "Interruption signal: " + session.interruption_signal; hash.textContent = session.manifest_sha256; row.append(heading, note, hash); $("campaign-sessions").append(row); }
  return retained;
}
async function displayCampaignReport() {
  if (!campaignSelected?.can_view_report || campaignSelected.id === campaignActionID) { $("campaign-results").hidden = true; return; }
  const identity = campaignSelected.id, configID = campaignSelected.configuration_id, revision = campaignRevision(campaignSelected), selection = campaignSelection;
  if (campaignShown === revision && Date.now() - campaignLastReportCheck < 5000) return;
  const request = ++campaignRequest;
  const current = () => campaignSelected?.id === identity && campaignRevision(campaignSelected) === revision && campaignSelection === selection && campaignRequest === request && campaignActionID !== identity;
  if (campaignShown !== revision) $("campaign-results").hidden = true;
  try {
    const wrapper = await api("campaigns/" + identity + "/report"); if (!current()) return;
    if (wrapper.campaign_id !== identity || wrapper.configuration_id !== configID || wrapper.report?.schema !== "opent1d.maintained-campaign-report/1") throw new Error("The report does not match the selected maintained campaign.");
    const report = wrapper.report, verified = wrapper.verification === "native_reader_verified";
    renderRetainedContent($("campaign-results"), JSON.stringify([revision, wrapper]), () => {
    const retained = renderCampaignRoster(report);
    status($("campaign-coverage-status"), !verified ? "Coverage unverified; recorded snapshot" : report.passed === true ? "Complete accepted snapshot" : "Incomplete / failed snapshot", !verified ? "warning" : report.passed === true ? "good" : "bad");
    $("campaign-denominators").replaceChildren();
    for (const [caption, value] of [["Accepted complete slots", report.accepted_slots + " / " + report.planned_slots], ["Complete-slot source / load cases", report.accepted_source_scenarios + " / " + report.planned_source_scenarios], ["Retained attempts", retained]]) { const box = document.createElement("div"), number = document.createElement("strong"), label = document.createElement("span"); box.className = "metric"; number.textContent = value; label.textContent = caption; box.append(number, label); $("campaign-denominators").append(box); }
    $("campaign-interpretation").textContent = report.interpretation + " · Reconstruction attests a saved snapshot; the source archive has not been fully rechecked since that worker.";
    $("campaign-limitations").textContent = report.limitations;
    }, identity, campaignShown !== revision);
    $("campaign-results").hidden = false; campaignShown = revision; campaignLastReportCheck = Date.now();
  } catch (error) { if (current()) { campaignNotice(error.message); $("campaign-results").hidden = true; campaignShown = null; } }
}
async function refreshCampaigns() {
  const request = ++campaignListRequest;
  try {
    const result = await api("campaigns"); if (request !== campaignListRequest) return;
    if (!Array.isArray(result.campaigns) || result.campaigns.length > 128) throw new Error("The saved campaign list exceeds the supported view.");
    campaigns = result.campaigns;
    if (campaignSelected) { const updated = campaigns.find((entry) => entry.id === campaignSelected.id); if (!updated || campaignRevision(updated) !== campaignRevision(campaignSelected)) clearCampaignResults(); campaignSelected = updated || null; }
    if (campaignFollowID) { const entry = campaigns.find((item) => item.id === campaignFollowID); if (entry) { selectCampaign(entry); campaignFollowID = null; } }
    renderCampaignList(); renderCampaignDetail(); await displayCampaignReport();
  } catch (error) { if (request === campaignListRequest) campaignNotice(error.message); }
}
async function startSavedCampaign(operation) {
  if (active || campaignPending || (typeof libraryPending !== "undefined" && libraryPending) || !campaignSelected) return;
  const identity = campaignSelected.id, configID = campaignSelected.configuration_id;
  const selection = campaignSelection; campaignActionID = identity; clearCampaignResults(); campaignPending = true; campaignControls(); campaignNotice("");
  try {
    if (operation === "resume" && !campaignSelected.can_resume) throw new Error("Check this campaign configuration before resuming remaining slots.");
    const path = operation === "check" ? "campaigns/configurations/" + configID + "/check" : "campaigns/" + identity + "/" + operation;
    const job = await api(path, {}); active = job; selected = job;
    // A configuration check does not itself own a campaign resource.
    if (operation === "check") campaignActionID = null;
    updateActivity(job); updateControls(); await refresh();
  } catch (error) { if (campaignSelected?.id === identity && campaignSelection === selection) campaignNotice(error.message); campaignActionID = null; }
  finally { campaignPending = false; campaignControls(); }
}
async function downloadCampaign(name) {
  if (!campaignSelected || !["report.json", "report.md"].includes(name)) return;
  const identity = campaignSelected.id, revision = campaignRevision(campaignSelected), selection = campaignSelection;
  try { const blob = await api("campaigns/" + identity + "/artifacts/" + name, undefined, true); if (campaignSelected?.id !== identity || campaignRevision(campaignSelected) !== revision || campaignSelection !== selection || campaignActionID === identity) return;
    const url = URL.createObjectURL(blob), link = document.createElement("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { if (campaignSelected?.id === identity && campaignRevision(campaignSelected) === revision && campaignSelection === selection) campaignNotice(error.message); }
}
$("open-campaigns").addEventListener("click", () => workspaceNavigate("campaigns"));
$("campaign-add-cell").addEventListener("click", () => captureCampaignCell());
$("campaign-form").addEventListener("submit", (event) => { event.preventDefault(); startCampaignConfiguration("check"); });
$("campaign-install").addEventListener("click", () => startCampaignConfiguration("install"));
$("campaign-run").addEventListener("click", () => startCampaignConfiguration("run"));
$("campaign-repeats").addEventListener("input", invalidateCampaign); $("campaign-budget").addEventListener("input", invalidateCampaign);
$("campaign-check-saved").addEventListener("click", () => startSavedCampaign("check")); $("campaign-resume").addEventListener("click", () => startSavedCampaign("resume")); $("campaign-reconstruct").addEventListener("click", () => startSavedCampaign("reconstruct"));
$("campaign-download-markdown").addEventListener("click", () => downloadCampaign("report.md")); $("campaign-download-json").addEventListener("click", () => downloadCampaign("report.json"));


// Durable pointers attest owned snapshots; package integrity and coverage stay separate.
let durableSession = null, durableEntries = [], durableSelected = null, durablePending = false;
let durableRequest = 0, durableSelection = 0, durableListRequest = 0, durableBrowseRequest = 0, durableShown = null;
let durableDirectory = "", durableParent = null, durableLastReportCheck = 0;

function durableNotice(message) { const changed = $("durable-notice").textContent !== message; $("durable-notice").textContent = message; $("durable-notice").hidden = !message; if (message && changed && typeof uxRevealError === "function") uxRevealError(message, $("durable-notice")); }
function durableRevision(entry) { return [entry?.id, entry?.checked_at, entry?.integrity, entry?.reconstruction, entry?.snapshot_job, entry?.availability].join(":"); }
function clearDurableResults() { ++durableRequest; ++durableSelection; durableShown = null; $("durable-results").hidden = true; }
function durableControls() {
  const busy = !!active || durablePending || (typeof m3Pending !== "undefined" && m3Pending) || (typeof libraryPending !== "undefined" && libraryPending);
  $("durable-export-form").querySelectorAll("select,button").forEach((element) => { element.disabled = busy; });
  $("durable-export").disabled = busy || !durableSession?.can_export || !$("durable-source").value;
  $("durable-register-form").querySelectorAll("select,input,button").forEach((element) => { element.disabled = busy; });
  $("durable-verify").disabled = busy || !durableSelected?.can_verify;
  $("durable-reconstruct").disabled = busy || !durableSelected?.can_reconstruct;
}
function selectDurable(entry) { clearDurableResults(); durableSelected = entry; renderDurableList(); renderDurableDetail(); displayDurableReport(); }
function renderDurableList() {
  const signature = JSON.stringify([durableSelected?.id, durableEntries.map((entry) => [entry.id, entry.task, entry.path, entry.integrity, entry.complete])]);
  renderRetainedContent($("durable-list"), signature, () => {
  $("durable-list").replaceChildren();
  if (!durableEntries.length) { const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = "No durable packages registered."; $("durable-list").append(empty); }
  for (const entry of durableEntries) {
    const button = document.createElement("button"); button.type = "button"; button.className = "library-entry" + (durableSelected?.id === entry.id ? " current" : "");
    button.dataset.pollingKey = entry.id;
    const name = document.createElement("strong"), detail = document.createElement("small");
    name.textContent = (entry.task || "Package") + " · " + entry.path;
    detail.textContent = entry.integrity.replaceAll("_", " ") + " · " + (entry.complete === null ? "coverage unavailable" : entry.complete ? "recorded complete" : "recorded failed / incomplete");
    button.append(name, detail); button.addEventListener("click", () => { const current = durableEntries.find((item) => item.id === entry.id); if (current) selectDurable(current); }); $("durable-list").append(button);
  }
  });
}
function renderDurableDetail() {
  const entry = durableSelected; $("durable-detail").hidden = !entry;
  if (!entry) { durableControls(); return; }
  $("durable-detail-title").textContent = entry.task || "Saved package"; $("durable-directory").textContent = entry.directory;
  status($("durable-availability"), entry.availability === "available" ? "Directory available" : entry.availability === "awaiting_export" ? "Export in progress" : "Directory unavailable", entry.availability === "available" ? "neutral" : entry.availability === "awaiting_export" ? "pending" : "bad");
  const integrity = {verified_snapshot: "Package bytes verified", recorded_verification: "Bytes previously verified; recheck", checking: "Checking package bytes", verification_failed: "Package integrity failed", changed_since_verification: "Package changed / unavailable", not_requested: "Package bytes not verified"};
  const reconstruction = {verified_snapshot: "Native reconstruction verified", recorded_verification: "Reconstruction previously verified", checking: "Checking native reconstruction", reader_mismatch: "Compatible reader needed", verification_failed: "Reconstruction failed", changed_since_verification: "Reconstruction withdrawn", not_requested: "Reconstruction not requested"};
  status($("durable-integrity"), integrity[entry.integrity] || "Package bytes not verified", entry.integrity === "verified_snapshot" ? "good" : ["verification_failed", "changed_since_verification"].includes(entry.integrity) ? "bad" : "neutral");
  status($("durable-reconstruction"), reconstruction[entry.reconstruction] || "Reconstruction not requested", entry.reconstruction === "verified_snapshot" ? "good" : entry.reconstruction === "verification_failed" ? "bad" : "neutral");
  const verified = entry.reconstruction === "verified_snapshot";
  status($("durable-completeness"), entry.complete === null ? "Coverage unavailable" : (verified ? "Verified " : "Recorded ") + (entry.complete ? "complete coverage" : "failed / incomplete coverage"), entry.complete === false ? "bad" : verified && entry.complete ? "good" : "neutral");
  $("durable-scope").textContent = "Statuses describe the saved worker snapshot. Package files have not been rechecked since that operation. Byte consistency does not authenticate an experiment or establish model validity.";
  $("durable-reader").textContent = entry.reader_revision || "Reader identity unavailable until package verification.";
  $("durable-error").textContent = entry.error || entry.availability_error || ""; $("durable-error").hidden = !$("durable-error").textContent;
  if ($("durable-evidence-summary")) $("durable-evidence-summary").textContent = "Read-only saved package · bytes: " + entry.integrity.replaceAll("_", " ") + " · saved analysis: " + entry.reconstruction.replaceAll("_", " ") + " · coverage: " + (entry.complete === null ? "unavailable" : entry.complete ? "recorded complete" : "recorded incomplete");
  durableControls();
}
async function displayDurableReport() {
  if (!durableSelected?.can_view_report || durablePending || (active?.request?.entry_id === durableSelected.id)) { $("durable-results").hidden = true; return; }
  const identity = durableSelected.id, revision = durableRevision(durableSelected), request = ++durableRequest;
  if (durableShown === revision && Date.now() - durableLastReportCheck < 5000) return;
  const current = () => durableSelected?.id === identity && durableRevision(durableSelected) === revision && request === durableRequest && !durablePending && active?.request?.entry_id !== identity;
  try {
    const result = await api("durable/entries/" + identity + "/report"); if (!current() || durableRevision(result.entry) !== revision) return;
    const report = result.native_report;
    const analysis = report.common || report.evaluation;
    $("durable-native-counts").textContent = analysis ? "Contributing participants: " + analysis.contributing_people + " / " + analysis.planned_people + "; complete cohort: " + analysis.complete_cohort + ". Native support and criteria are unchanged." : report.denominators ? "Sources: " + report.denominators.accepted_sources + " / " + report.denominators.sources + "; source / load cases: " + report.denominators.accepted_source_scenarios + " / " + report.denominators.source_scenarios + "; source pairs: " + report.denominators.accepted_pairs + " / " + report.denominators.pairs + "." : "Accepted slots: " + report.accepted_slots + " / " + report.planned_slots + "; source / load cases: " + report.accepted_source_scenarios + " / " + report.planned_source_scenarios + ".";
    $("durable-native-roster").replaceChildren();
    if (analysis) {
      for (const [id, person] of Object.entries(analysis.people)) { const item = document.createElement("li"); item.textContent = id + " · " + (report.common ? person.common_scored + " / " + person.planned_origins + " shared scored origins · " + JSON.stringify(person.candidate_statuses) : person.scored + " / " + person.planned + " scored origins · " + person.execution_status + " · " + person.not_attempted + " unattempted") + " · " + (person.ineligibility_reasons.join(", ") || "primary contributor"); $("durable-native-roster").append(item); }
      if (report.candidate_order) for (const id of report.candidate_order) { const item = document.createElement("li"); item.textContent = id + " · " + report.candidates[id].coordinator.status + " · " + (report.candidates[id].missing_archive_reason || "sealed child retained"); $("durable-native-roster").append(item); }
    } else if (Array.isArray(report.slots)) for (const slot of report.slots) { const item = document.createElement("li"); item.textContent = slot.cell + " · repetition " + slot.repeat + " · " + (slot.accepted ? "accepted" : "not accepted") + " · " + (slot.attempts?.length || 0) + " retained attempts"; $("durable-native-roster").append(item); }
    else for (const [name, source] of Object.entries(report.sources || {})) { const item = document.createElement("li"); item.textContent = name + " · " + source.status + " · " + (source.accepted ? "accepted" : "not accepted"); $("durable-native-roster").append(item); }
    $("durable-download-svg").hidden = !result.entry.artifacts_sha256["figure.svg"];
    $("durable-results").hidden = false; durableShown = revision; durableLastReportCheck = Date.now();
  } catch (error) { if (current()) { durableNotice(error.message); clearDurableResults(); } }
}
async function refreshDurable() {
  const request = ++durableListRequest;
  const result = await api("durable/entries"); if (request !== durableListRequest) return;
  durableEntries = result.entries;
  if (durableSelected) { const next = durableEntries.find((entry) => entry.id === durableSelected.id); if (durableRevision(next) !== durableRevision(durableSelected)) clearDurableResults(); durableSelected = next || null; }
  const sourceResult = await api("durable/sources"); if (request !== durableListRequest) return;
    renderRetainedContent($("durable-source"), JSON.stringify(sourceResult.sources.map((source) => [source.kind, source.id, source.label])), () => {
      const value = $("durable-source").value; $("durable-source").replaceChildren(); const placeholder = document.createElement("option"); placeholder.value = ""; placeholder.textContent = "Choose a finished experiment"; $("durable-source").append(placeholder);
      for (const source of sourceResult.sources) { const option = document.createElement("option"); option.value = source.kind + ":" + source.id; option.textContent = source.label; $("durable-source").append(option); }
      if (sourceResult.sources.some((source) => source.kind + ":" + source.id === value)) $("durable-source").value = value;
    });
  renderDurableList(); renderDurableDetail(); await displayDurableReport();
}
async function startDurable(path, body) {
  if (active || durablePending || (typeof libraryPending !== "undefined" && libraryPending)) return;
  durablePending = true; clearDurableResults(); durableNotice(""); durableControls();
  try { const job = await api(path, body); active = job; selected = job; updateActivity(job); updateControls(); await refreshDurable(); const entry = durableEntries.find((value) => value.id === job.request?.entry_id); if (entry) selectDurable(entry); }
  catch (error) { durableNotice(error.message); }
  finally { durablePending = false; updateControls(); }
}
async function browseDurable(directory) {
  const root = $("durable-root").value, request = ++durableBrowseRequest;
  const current = () => request === durableBrowseRequest && $("durable-root").value === root;
  $("durable-select-directory").disabled = true;
  try {
    const listing = await api("library/files?root_id=" + encodeURIComponent(root) + "&directory=" + encodeURIComponent(directory)); if (!current()) return;
    durableDirectory = listing.directory; durableParent = listing.parent; $("durable-browse-directory").textContent = listing.directory || "Archive root"; $("durable-directory-up").disabled = listing.parent === null; $("durable-directories").replaceChildren();
    for (const entry of listing.entries) { const button = document.createElement("button"); button.type = "button"; button.className = "file-entry"; button.textContent = "▸ " + entry.name; button.addEventListener("click", () => browseDurable(entry.path)); $("durable-directories").append(button); }
    if (!listing.entries.length) $("durable-directories").textContent = "No child directories. You can select this directory.";
    $("durable-select-directory").disabled = false;
  } catch (error) { if (current()) $("durable-directories").textContent = error.message; }
}
async function downloadDurable(name) {
  if (!durableSelected?.can_view_report) return;
  const identity = durableSelected.id, revision = durableRevision(durableSelected), selection = durableSelection;
  const current = () => durableSelected?.id === identity && durableRevision(durableSelected) === revision && durableSelection === selection && !durablePending && active?.request?.entry_id !== identity;
  try { const blob = await api("durable/entries/" + identity + "/artifacts/" + name, undefined, true); if (!current()) return;
    const url = URL.createObjectURL(blob), link = document.createElement("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { if (current()) { durableNotice(error.message); clearDurableResults(); } }
}
async function initDurable() {
  try {
    durableSession = await api("durable/bootstrap"); status($("durable-store-status"), durableSession.can_export ? "Export folder ready" : "Export folder not configured", durableSession.can_export ? "good" : "neutral"); $("durable-store-path").textContent = durableSession.store || "";
    $("durable-store-detail").textContent = durableSession.store_error || (durableSession.can_export ? "New packages are saved here, outside your working folder. The original archive stays unchanged." : (typeof desktopApp !== "undefined" && desktopApp) ? "The archive folder is unavailable. Restore access to it and reopen OpenT1D." : "Choose an existing archive folder outside this checkout using --archive-store when starting the interface.");
    for (const root of durableSession.roots) { const option = document.createElement("option"); option.value = root.id; option.textContent = root.name + " · " + root.directory; $("durable-root").append(option); }
    await refreshDurable();
  } catch (error) { durableNotice(error.message); }
}
$("open-durable").addEventListener("click", () => workspaceNavigate("durable"));
$("durable-source").addEventListener("change", durableControls);
$("durable-export-form").addEventListener("submit", (event) => { event.preventDefault(); const [kind, id] = $("durable-source").value.split(":"); if (id) startDurable("durable/export", {kind, id}); });
$("durable-register-form").addEventListener("submit", (event) => { event.preventDefault(); startDurable("durable/register", {root_id: $("durable-root").value, path: $("durable-path").value}); });
$("durable-verify").addEventListener("click", () => { if (durableSelected) startDurable("durable/entries/" + durableSelected.id + "/verify", {}); });
$("durable-reconstruct").addEventListener("click", () => { if (durableSelected) startDurable("durable/entries/" + durableSelected.id + "/reconstruct", {}); });
$("durable-browse").addEventListener("click", () => { $("durable-dialog").showModal(); browseDurable($("durable-path").value); });
$("durable-close-dialog").addEventListener("click", () => { ++durableBrowseRequest; $("durable-dialog").close(); });
$("durable-directory-up").addEventListener("click", () => browseDurable(durableParent || ""));
$("durable-select-directory").addEventListener("click", () => { $("durable-path").value = durableDirectory; ++durableBrowseRequest; $("durable-dialog").close(); });
$("durable-root").addEventListener("change", () => { ++durableBrowseRequest; $("durable-path").value = ""; });
$("durable-download-markdown").addEventListener("click", () => downloadDurable("report.md")); $("durable-download-json").addEventListener("click", () => downloadDurable("report.json")); $("durable-download-svg").addEventListener("click", () => downloadDurable("figure.svg"));
// M3 intake, saved native evidence and asynchronous selections use independent identities.
let m3Session = null, m3Inputs = [], m3Input = null, m3Configuration = null, m3Pending = false;
let m3Draft = 0, m3InputRequest = 0, m3Entries = [], m3Selected = null, m3Selection = 0;
let m3Request = 0, m3ListRequest = 0, m3DetailRequest = 0, m3BrowseRequest = 0;
let m3Parent = null, m3Shown = null, m3LastReportCheck = 0, m3FollowEntry = null, m3FixtureJob = null;
const m3Checks = new Map(), m3Finished = new Set();

function m3Notice(message) { const changed = $("m3-notice").textContent !== message; $("m3-notice").textContent = message; $("m3-notice").hidden = !message; if (message && changed && typeof uxRevealError === "function") uxRevealError(message, $("m3-notice")); }
function m3TaskTitle(task) { return task === "m3-forecast" ? "Forecast against persistence" : "Frozen-predictor comparison"; }
function m3Busy() { return !!active || m3Pending || (typeof libraryPending !== "undefined" && libraryPending) || (typeof campaignPending !== "undefined" && campaignPending) || (typeof durablePending !== "undefined" && durablePending); }
function m3CandidateIDs() { return [...$("m3-candidates").querySelectorAll("input:checked")].map((input) => input.value); }
function m3DraftKey() { return JSON.stringify([m3Input?.id, $("m3-task").value, m3CandidateIDs(), Number($("m3-timeout").value)]); }
function m3Revision(entry) { return JSON.stringify([entry?.id, entry?.task, entry?.configuration_id, entry?.execution_state, entry?.sealed, entry?.verification, entry?.complete, entry?.report_completeness, entry?.can_view_report, entry?.last_job, entry?.snapshot_job, entry?.updated_at, entry?.artifacts_sha256]); }
function clearM3Results() { ++m3Selection; ++m3Request; m3Shown = null; $("m3-results").hidden = true; $("m3-markdown").textContent = ""; $("m3-json").textContent = ""; }
function withdrawM3Snapshot(message) { clearM3Results(); if (m3Selected) m3Selected = {...m3Selected, verification: "changed_since_verification", complete: null, can_view_report: false}; m3Notice(message); renderM3Detail(); }
function invalidateM3() { ++m3Draft; m3Configuration = null; renderM3Readiness(); m3Controls(); }
function clearM3Input() { ++m3InputRequest; m3Input = null; invalidateM3(); renderM3Candidates(); }
function m3Controls() {
  const busy = m3Busy();
  for (const id of ["m3-inspect-form", "m3-form"]) $(id).querySelectorAll("input,select,button").forEach((element) => { element.disabled = busy; });
  $("m3-fixture").disabled = busy;
  $("m3-inputs").querySelectorAll("button").forEach((element) => { element.disabled = busy; });
  $("m3-form").hidden = !m3Input;
  const picker = $("m3-input-picker"), hasInput = String(!!m3Input);
  if (picker.dataset.selected !== hasInput) { picker.open = !m3Input; picker.dataset.selected = hasInput; }
  const runnable = m3Configuration?.ready === true && m3Configuration?.draft_key === m3DraftKey();
  $("m3-check").hidden = runnable;
  $("m3-run").hidden = !runnable;
  $("m3-check").disabled = busy || !m3Input;
  $("m3-run").disabled = busy || m3Configuration?.ready !== true || m3Configuration?.draft_key !== m3DraftKey();
  const owned = active?.operation?.startsWith("m3_");
  $("m3-cancel").hidden = !owned; $("m3-cancel").disabled = !owned || active.state === "cancelling";
  $("m3-reconstruct").disabled = busy || !m3Selected?.can_reconstruct;
  const terminal = m3Selected && !activeStates.has(m3Selected.execution_state);
  $("m3-export").disabled = busy || !terminal || !m3Selected.sealed || !durableSession?.can_export;
  $("m3-retain").disabled = busy || !terminal || !durableSession?.can_export;
  for (const id of ["m3-download-json", "m3-download-markdown"]) $(id).disabled = busy || !m3Selected?.can_view_report || $("m3-results").hidden;
}
function renderM3Readiness(result) {
  const ready = m3Configuration?.ready === true && m3Configuration.draft_key === m3DraftKey();
  status($("m3-readiness"), ready ? "Frozen configuration ready" : result ? "Check did not establish readiness" : "Configuration not checked", ready ? "good" : result ? "warning" : "neutral");
  $("m3-readiness-detail").textContent = ready ? "This exact frozen configuration passed its explicit check. A run rechecks frozen identities before predictor execution. Observation validity and complete coverage are established separately." : "Freeze and check explicitly before running. Preparation copies synthetic observation bytes and records that access; a native metadata check does not inspect their content or execute a predictor.";
  $("m3-configuration-reference").textContent = m3Configuration ? m3Configuration.id + " · Frozen bytes " + m3Configuration.freeze_sha256 : "No checked frozen configuration selected.";
}
function renderM3Candidates() {
  $("m3-candidates").replaceChildren();
  if (!m3Input) { $("m3-input-summary").textContent = "Inspect a synthetic configuration to see its full planned roster and frozen predictors."; m3Controls(); return; }
  $("m3-input-summary").textContent = m3Input.planned_people + " planned participants · " + Object.entries(m3Input.planned_origins).map(([person, count]) => person + ": " + count + " planned origins").join("; ") + ". All original people, origins and input identities are retained.";
  m3Input.candidates.forEach((candidate, index) => {
    const card = document.createElement("div"), label = document.createElement("label"), input = document.createElement("input"), name = document.createElement("span"), detail = document.createElement("p"), identities = document.createElement("details"), summary = document.createElement("summary"), hashes = document.createElement("p");
    card.className = "m3-candidate"; input.type = "checkbox"; input.value = candidate.id; input.checked = $("m3-task").value === "m3-compare" || index === 0;
    input.setAttribute("aria-label", "Include frozen predictor " + candidate.id); name.textContent = candidate.id; label.append(input, name);
    detail.textContent = candidate.reference + " · " + candidate.rights + " · Training/settings: " + (candidate.training?.reference || "declared synthetic origin");
    summary.textContent = "Frozen source and settings identities"; hashes.textContent = "Source SHA-256: " + candidate.source_sha256 + " · Settings SHA-256: " + candidate.settings_sha256; identities.append(summary, hashes);
    input.addEventListener("change", () => { if (input.checked && $("m3-task").value === "m3-forecast") $("m3-candidates").querySelectorAll("input").forEach((other) => { if (other !== input) other.checked = false; }); invalidateM3(); });
    identities.append(detail); card.append(label, identities); $("m3-candidates").append(card);
  });
  m3Controls();
}
function chooseM3Input(input) {
  if (m3Busy()) return;
  ++m3InputRequest; m3Input = input; $("m3-root").value = input.root_id; $("m3-path").value = input.path;
  $("m3-task").value = input.task; invalidateM3(); renderM3Candidates(); m3Notice("");
  $("m3-check").focus();
}
function renderM3Inputs() {
  renderRetainedContent($("m3-inputs"), JSON.stringify(m3Inputs.map((input) => [input.id, input.task, input.path, input.created_at])), () => {
  $("m3-inputs").replaceChildren();
  for (const input of m3Inputs) {
    const button = document.createElement("button"); button.type = "button"; button.className = "button subtle";
    button.dataset.pollingKey = input.id;
    button.textContent = m3TaskTitle(input.task) + " · " + input.id.slice(-8) + (input.created_at ? " · " + new Date(input.created_at).toLocaleString() : ""); button.title = input.path; button.addEventListener("click", () => { const current = m3Inputs.find((item) => item.id === input.id); if (current) chooseM3Input(current); }); $("m3-inputs").append(button);
  }
  });
  m3Controls();
}
async function inspectM3(event) {
  if (event) event.preventDefault();
  if (m3Busy() || !$("m3-inspect-form").reportValidity()) return;
  const root = $("m3-root").value, path = $("m3-path").value, request = ++m3InputRequest;
  m3Pending = true; m3Input = null; invalidateM3(); renderM3Candidates(); updateControls(); m3Notice("");
  const current = () => request === m3InputRequest && $("m3-root").value === root && $("m3-path").value === path;
  try {
    const input = await api("m3/inspect", {root_id: root, path}); if (!current()) return;
    m3Input = input; $("m3-task").value = input.task; invalidateM3(); renderM3Candidates();
  } catch (error) { if (current()) m3Notice(error.message); }
  finally { m3Pending = false; updateControls(); }
}
function m3Intake() {
  if (!m3Input) throw new Error("Inspect a synthetic configuration first.");
  const task = $("m3-task").value, candidate_ids = m3CandidateIDs(), timeout_seconds = Number($("m3-timeout").value);
  if (!["m3-forecast", "m3-compare"].includes(task)) throw new Error("Choose a supported M3 workflow.");
  if (task === "m3-forecast" ? candidate_ids.length !== 1 : candidate_ids.length < 2 || candidate_ids.length > 8) throw new Error(task === "m3-forecast" ? "Choose exactly one frozen predictor." : "Choose two to eight frozen predictors.");
  if (!Number.isInteger(timeout_seconds) || timeout_seconds < 1 || timeout_seconds > 1800) throw new Error("Choose a participant-worker budget from 1 to 1800 seconds.");
  return {input_id: m3Input.id, task, candidate_ids, timeout_seconds};
}
async function startM3Configuration(operation) {
  if (m3Busy() || !$("m3-form").reportValidity()) return;
  const key = m3DraftKey(), draft = m3Draft; m3Pending = true; m3Notice(""); updateControls();
  try {
    if (operation === "check") {
      const body = m3Intake();
      if (!m3Configuration || m3Configuration.draft_key !== key) {
        const record = await api("m3/configurations", body);
        if (m3Draft !== draft || m3DraftKey() !== key) throw new Error("The input selection changed during preparation. Freeze and check the new selection.");
        m3Configuration = {...record, draft_key: key};
      }
      m3Configuration.ready = false; renderM3Readiness();
    } else if (operation !== "run" || m3Configuration?.ready !== true || m3Configuration.draft_key !== key) throw new Error("Check this exact frozen configuration before running.");
    const id = m3Configuration.id, job = await api("m3/configurations/" + id + "/" + operation, {});
    if (operation === "check") m3Checks.set(job.id, {id, key, draft});
    if (operation === "run") m3FollowEntry = job.m3_entry_id || job.request?.entry_id;
    active = job; selected = job; updateActivity(job); updateM3Activity(job); renderM3Readiness(); await refresh();
  } catch (error) { if (m3Draft === draft && m3DraftKey() === key) m3Notice(error.message); }
  finally { m3Pending = false; updateControls(); }
}
async function createM3Fixture() {
  if (m3Busy()) return;
  m3Pending = true; m3Notice(""); updateControls();
  try { const job = await api("m3/fixture", {}); m3FixtureJob = job.id; active = job; selected = job; updateActivity(job); updateM3Activity(job); await refresh(); }
  catch (error) { m3Notice(error.message); }
  finally { m3Pending = false; updateControls(); }
}
async function m3JobFinished(job) {
  if (!job || activeStates.has(job.state) || m3Finished.has(job.id)) return;
  m3Finished.add(job.id);
  if (m3Checks.has(job.id)) {
    const checked = m3Checks.get(job.id); m3Checks.delete(job.id);
    const current = () => m3Configuration?.id === checked.id && m3Draft === checked.draft && m3DraftKey() === checked.key;
    try { const configuration = await api("m3/configurations/" + checked.id); if (current()) { m3Configuration = {...configuration, ready: job.state === "completed" && configuration.ready === true, draft_key: checked.key}; renderM3Readiness(job.result || {}); } }
    catch (error) { if (current()) { m3Configuration.ready = false; renderM3Readiness({}); m3Notice(error.message); } }
  }
  if (job.id === m3FixtureJob) {
    m3FixtureJob = null;
    if (job.state === "completed" && job.result?.input_id) {
      const result = await api("m3/inputs"); m3Inputs = result.inputs; renderM3Inputs();
      const input = m3Inputs.find((record) => record.id === job.result.input_id);
      if (input && !active) { m3Input = input; $("m3-root").value = input.root_id; $("m3-path").value = input.path; $("m3-task").value = input.task; invalidateM3(); renderM3Candidates(); }
    }
  }
  updateM3Activity(job); m3Controls();
}
function m3CompletionDetail(job) {
  if (job.operation === "m3_fixture") return "Example inputs are ready. Check setup next; no predictor has run.";
  if (job.operation === "m3_check") return "Setup check finished. Review configuration readiness before running; no predictor has run.";
  if (job.operation === "m3_run") return "Forecast execution finished. Inspect execution, saved analysis and cohort coverage in the selected report.";
  if (job.operation === "m3_reconstruct") return "Saved-analysis check finished without rerunning a predictor. Inspect reconstruction and cohort coverage in the selected report.";
  return null;
}
function updateM3Activity(job) {
  if (!job?.operation?.startsWith("m3_") && job?.operation !== "durable_forensic") return;
  $("m3-activity").hidden = false;
  const labels = {m3_fixture: "Preparing invented observations and frozen example declarations", m3_check: "Checking frozen metadata and runtime readiness", m3_run: "Executing the frozen M3 workflow", m3_reconstruct: "Verifying saved analysis without predictor execution", durable_forensic: "Retaining available raw files outside your working folder"};
  status($("m3-activity-status"), job.state.replaceAll("_", " "), job.state === "failed" ? "bad" : job.state === "completed" ? "good" : "pending");
  if (job.state === "completed" && ["m3_fixture", "m3_check"].includes(job.operation)) status($("m3-activity-status"), job.operation === "m3_fixture" ? "Example ready" : "Setup checked", "good");
  $("m3-retention-receipt").hidden = true;
  if (job.operation === "durable_forensic" && job.state === "completed" && job.result?.native?.schema === "opent1d.m3-forensic-retention/1") { const receipt = job.result.native; $("m3-retention-receipt").textContent = "Raw evidence saved to " + receipt.output + ". " + (receipt.byte_copy_verified === true ? "The byte copy was checked. " : "") + "Receipt: " + receipt.receipt_identity + ". This is not a verified durable package; native reconstruction and cohort completeness are not established."; $("m3-retention-receipt").hidden = false; }
  $("m3-activity-detail").textContent = activeStates.has(job.state) ? job.state === "cancelling" ? "Stopping observed owned processes and preserving available evidence…" : (uxPhaseDetail(job) || labels[job.operation]) : job.state === "completed" ? job.operation === "durable_forensic" ? "Raw evidence retention finished. No native reconstruction or complete-cohort claim is made." : "Operation finished. Read execution, reconstruction and cohort coverage separately below." : job.error || "Operation did not complete. Available evidence is retained.";
  if (job.state === "completed" && m3CompletionDetail(job)) $("m3-activity-detail").textContent = m3CompletionDetail(job);
}
function selectM3(entry) { ++m3ListRequest; clearM3Results(); m3Selected = entry; renderM3List(); renderM3Detail(); displayM3Report(); }
function renderM3List() {
  const signature = JSON.stringify([m3Selected?.id, m3Entries.map((entry) => [entry.id, entry.task, entry.execution_state, entry.sealed])]);
  renderRetainedContent($("m3-list"), signature, () => {
  $("m3-list").replaceChildren();
  if (!m3Entries.length) { const empty = document.createElement("p"); empty.className = "quiet"; empty.textContent = "No M3 workflows started yet."; $("m3-list").append(empty); }
  for (const entry of m3Entries) {
    const button = document.createElement("button"), name = document.createElement("strong"), detail = document.createElement("small"); button.type = "button"; button.className = "library-entry" + (m3Selected?.id === entry.id ? " current" : "");
    button.dataset.pollingKey = entry.id;
    name.textContent = m3TaskTitle(entry.task) + " · " + entry.id; detail.textContent = (entry.execution_state || "unavailable") + " · " + (entry.sealed ? "sealed archive" : "unsealed raw evidence");
    button.append(name, detail); button.addEventListener("click", () => { const current = m3Entries.find((item) => item.id === entry.id); if (current) selectM3(current); }); $("m3-list").append(button);
  }
  });
}
function renderM3Detail() {
  const entry = m3Selected; $("m3-detail").hidden = !entry;
  if (!entry) { m3Controls(); return; }
  $("m3-detail-title").textContent = m3TaskTitle(entry.task) + " · " + entry.id;
  status($("m3-execution-status"), "Execution: " + (entry.execution_state || "unavailable"), entry.execution_state === "failed" ? "bad" : "neutral");
  const verification = {native_reader_verified: "Saved analysis verified", recorded_verification: "Previously verified; recheck", changed_since_verification: "Archive or snapshot changed", verification_failed: "Reconstruction failed", verifying: "Verifying saved analysis", not_requested: "Reconstruction not requested"};
  status($("m3-verification-status"), verification[entry.verification] || "Reconstruction not requested", entry.verification === "native_reader_verified" ? "good" : ["changed_since_verification", "verification_failed"].includes(entry.verification) ? "bad" : "neutral");
  const verified = entry.verification === "native_reader_verified";
  status($("m3-cohort-status"), entry.complete === null || entry.complete === undefined ? "Cohort coverage unavailable" : (verified ? "Verified snapshot: " : "Recorded: ") + (entry.complete ? "complete cohort" : "incomplete cohort"), entry.complete === false ? "warning" : verified && entry.complete ? "good" : "neutral");
  status($("m3-seal-status"), entry.sealed ? "Native archive sealed" : "Unsealed raw evidence", entry.sealed ? "neutral" : "warning");
  $("m3-detail-scope").textContent = "Statuses describe recorded execution and owned worker snapshots. Files have not been fully rechecked since that worker. A complete synthetic cohort is a coverage statement, not a prediction-quality threshold.";
  $("m3-detail-error").textContent = entry.error || ""; $("m3-detail-error").hidden = !entry.error;
  $("m3-progress").textContent = JSON.stringify(entry.progress || {execution_state: entry.execution_state, archive: entry.archive, sealed: entry.sealed}, null, 2);
  $("m3-retention-detail").textContent = !durableSession?.can_export ? ((typeof desktopApp !== "undefined" && desktopApp) ? "Restore access to the archive folder and reopen OpenT1D to enable export and raw retention." : "Configure an existing archive store outside this checkout at startup to enable export and raw retention.") : !entry.sealed ? "This unsealed attempt may have no reconstructible report. Retain all available raw files with a separate inventory and provenance receipt; this does not create a verified package." : "Durable export verifies native reconstruction first. Raw retention independently preserves all available bytes without a reconstructibility or verified-package claim.";
  m3Controls();
}
function m3Metric(container, value, caption) {
  const box = document.createElement("div"), number = document.createElement("strong"), label = document.createElement("span"); box.className = "metric"; number.textContent = value; label.textContent = caption; box.append(number, label); container.append(box);
}
function m3Row(container, summaryText, paragraphs, identity = summaryText) {
  const row = document.createElement("details"), summary = document.createElement("summary"); summary.textContent = summaryText; row.append(summary);
  row.dataset.pollingKey = (container.id || container.dataset?.pollingKey || "row") + ":" + identity; summary.dataset.pollingKey = row.dataset.pollingKey;
  for (const text of paragraphs) { const paragraph = document.createElement("p"); paragraph.textContent = text; row.append(paragraph); }
  container.append(row); return row;
}
function m3Value(value) { return value === null || value === undefined ? "null" : String(value); }
function m3MetricText(value) {
  if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) return "unavailable";
  return String(Number(value.toPrecision(4)));
}
function renderM3Native(report, prefix = "m3") {
  const target = (suffix) => $(prefix + "-" + suffix);
  const comparison = !!report.common, analysis = comparison ? report.common : report.evaluation;
  if (!analysis?.people || !analysis.equal_person_metrics || typeof analysis.complete_cohort !== "boolean") throw new Error("The native M3 report is incomplete or incompatible.");
  const people = Object.entries(analysis.people), planned = people.reduce((count, [, person]) => count + (comparison ? person.planned_origins : person.planned), 0), scored = people.reduce((count, [, person]) => count + (comparison ? person.common_scored : person.scored), 0);
  target("denominators").replaceChildren(); m3Metric(target("denominators"), analysis.contributing_people + " / " + analysis.planned_people, "Contributing / planned participants"); m3Metric(target("denominators"), planned, "Planned origins per candidate"); m3Metric(target("denominators"), scored, comparison ? "All-candidate shared scored origins" : "Candidate / persistence paired targets");
  target("analysis-scope").textContent = (analysis.complete_cohort ? "Complete planned synthetic cohort. " : "Incomplete planned synthetic cohort; partial aggregates remain labeled. ") + (comparison ? "Every displayed primary metric and contrast uses the native all-candidate/persistence support with equal participant weights. Unmatched child subsets are not ranked. " : "The candidate and persistence use identical causal windows and equal contributing-participant weights. ") + (analysis.null_reason ? "Null metrics: " + analysis.null_reason + ". " : "") + "Displayed error metrics and contrast summaries are rounded to four significant digits. Exact saved values remain in the original JSON report and native downloads; thresholds are unchanged. No new metrics or numerical criteria are calculated in this interface.";
  target("errors").replaceChildren();
  const methods = comparison ? [...report.candidate_order, "persistence"] : ["candidate", "persistence"];
  for (const method of methods) { const metrics = analysis.equal_person_metrics[method], row = document.createElement("tr"); for (const value of [method === "candidate" ? report.predictor?.id || method : method, m3MetricText(metrics?.mae), m3MetricText(metrics?.rmse), m3MetricText(metrics?.bias)]) { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); } target("errors").append(row); }
  target("contrasts").replaceChildren();
  const contrasts = comparison ? analysis.contrasts : [{left: report.predictor?.id || "candidate", right: "persistence", ...analysis.primary}];
  for (const contrast of contrasts || []) m3Row(target("contrasts"), contrast.left + " minus " + contrast.right + " · MAE difference " + m3MetricText(contrast.mean_person_mae_difference) + " mg/dL", ["Participant bootstrap 95%: " + JSON.stringify(contrast.participant_bootstrap_95) + ". This descriptive interval resamples people, not timestamps.", "Contributing participant differences: " + JSON.stringify(contrast.person_differences)], contrast.left + ":" + contrast.right);
  target("people").replaceChildren();
  for (const [id, person] of people) {
    const paragraphs = ["Primary eligibility: " + (person.eligible_for_primary ? "eligible" : "ineligible") + " · Reasons: " + (person.ineligibility_reasons.join(", ") || "none")];
    if (comparison) paragraphs.push("Candidate execution statuses: " + JSON.stringify(person.candidate_statuses), "Candidate scored origins: " + JSON.stringify(person.candidate_scored) + " · Common-support losses: " + JSON.stringify(person.common_support_losses), "Common scored span (minutes): " + m3Value(person.common_span_us === null ? null : person.common_span_us / 60000000), "Diagnostic errors on retained prefixes: " + JSON.stringify(person.diagnostic_error_metrics) + ". Failed prefixes do not become primary contributors.");
    else paragraphs.push("Execution: " + person.execution_status + " · Attempted " + person.attempted + "/" + person.planned + " · Unattempted " + person.not_attempted, "Forecastable " + person.forecastable + " · Scored " + person.scored + " · Prediction coverage " + m3Value(person.prediction_coverage) + " · Score coverage " + m3Value(person.score_coverage), "History exclusions: " + JSON.stringify(person.history_exclusions) + " · Scoring exclusions: " + JSON.stringify(person.scoring_exclusions) + " · Targets: " + JSON.stringify(person.target_status_counts), "Supervisor / worker errors: " + m3Value(person.execution?.error_type) + " / " + m3Value(person.execution?.worker_error_type));
    m3Row(target("people"), id + " · " + (comparison ? person.common_scored + "/" + person.planned_origins + " shared scored origins" : person.scored + "/" + person.planned + " scored origins") + " · " + (person.eligible_for_primary ? "primary contributor" : "not a primary contributor"), paragraphs, id);
  }
  target("candidate-results").replaceChildren();
  if (comparison) for (const id of report.candidate_order) {
    const candidate = report.candidates[id], child = candidate.single_candidate;
    const row = m3Row(target("candidate-results"), id + " · " + candidate.coordinator.status, ["Coordinator: " + JSON.stringify(candidate.coordinator), "Child archive: " + (candidate.missing_archive_reason || "sealed native report retained") + ". Native per-person not_attempted can mean zero validated records rather than no process launch.", "Original candidate-versus-persistence cohort: " + (child ? child.evaluation.contributing_people + "/" + child.evaluation.planned_people + " contributing participants; no ranking on these unmatched subsets" : "unavailable; raw diagnostics remain retained")], id);
    if (child) for (const [personID, person] of Object.entries(child.evaluation.people)) m3Row(row, personID + " · " + person.execution_status, ["Original child accounting: attempted " + person.attempted + "/" + person.planned + " · Unattempted " + person.not_attempted + " · Forecastable " + person.forecastable + " · Scored " + person.scored, "Primary eligibility: " + (person.eligible_for_primary ? "eligible" : "ineligible") + " · Reasons: " + person.ineligibility_reasons.join(", "), "Supervisor / worker errors: " + m3Value(person.execution?.error_type) + " / " + m3Value(person.execution?.worker_error_type)], personID);
  }
  else m3Row(target("candidate-results"), report.predictor?.id || "Frozen predictor", [report.predictor?.reference || "", "Declared rights: " + report.predictor?.rights + " · Source SHA-256: " + report.predictor?.source?.sha256 + " · Settings SHA-256: " + report.predictor?.settings?.sha256]);
  target("json").textContent = JSON.stringify(report, null, 2);
  if (prefix === "m3" && typeof uxRenderEvidence === "function") uxRenderEvidence("m3-evidence-summary", "m3", report, m3Selected?.verification, m3Selected?.execution_state);
}
async function displayM3Report() {
  if (!m3Selected?.can_view_report || m3Pending || active?.request?.entry_id === m3Selected.id || m3Selected.verification === "verifying") { $("m3-results").hidden = true; return; }
  const identity = m3Selected.id, revision = m3Revision(m3Selected), selection = m3Selection;
  if (m3Shown === revision && Date.now() - m3LastReportCheck < 5000) return;
  const request = ++m3Request;
  const current = () => m3Selected?.id === identity && m3Revision(m3Selected) === revision && m3Selection === selection && m3Request === request && !m3Pending && active?.request?.entry_id !== identity;
  try {
    const result = await api("m3/entries/" + identity + "/report"); if (!current()) return;
    if (result.entry_id !== identity || result.task !== m3Selected.task || result.configuration_id !== m3Selected.configuration_id || result.snapshot_job !== m3Selected.snapshot_job || result.verification !== m3Selected.verification || ["report.json", "report.md"].some((name) => result.artifacts_sha256?.[name] !== m3Selected.artifacts_sha256?.[name])) throw new Error("The report snapshot does not match the selected M3 entry.");
    const markdown = await api("m3/entries/" + identity + "/artifacts/report.md", undefined, true); if (!current()) return;
    const text = await markdown.text(); if (!current()) return;
    renderRetainedContent($("m3-results"), JSON.stringify([revision, result.report, text]), () => {
      renderM3Native(result.report); $("m3-markdown").textContent = text;
    }, identity, m3Shown !== revision);
    $("m3-results").hidden = false; m3Shown = revision; m3LastReportCheck = Date.now(); m3Controls();
  } catch (error) { if (current()) withdrawM3Snapshot(error.message); }
}
async function refreshM3() {
  const request = ++m3ListRequest;
  try {
    const result = await api("m3/entries"); if (request !== m3ListRequest) return;
    m3Entries = result.entries;
    if (m3Selected) { const entry = m3Entries.find((item) => item.id === m3Selected.id); if (m3Revision(entry) !== m3Revision(m3Selected)) clearM3Results(); m3Selected = entry || null; }
    if (m3FollowEntry) { const entry = m3Entries.find((item) => item.id === m3FollowEntry); if (entry) { clearM3Results(); m3Selected = entry; m3FollowEntry = null; } }
    renderM3List(); renderM3Detail();
    if (m3Selected) {
      const identity = m3Selected.id, selection = m3Selection, detailRequest = ++m3DetailRequest;
      const entry = await api("m3/entries/" + identity);
      if (request !== m3ListRequest || detailRequest !== m3DetailRequest || m3Selected?.id !== identity || selection !== m3Selection) return;
      if (m3Revision(entry) !== m3Revision(m3Selected)) clearM3Results(); m3Selected = entry; renderM3Detail();
    }
    await displayM3Report();
  } catch (error) { if (request === m3ListRequest) { m3Notice(error.message); clearM3Results(); m3Controls(); } }
}
async function startSavedM3(operation) {
  if (m3Busy() || !m3Selected) return;
  if (operation === "reconstruct" && !m3Selected.can_reconstruct || operation === "export" && !m3Selected.sealed) return;
  const identity = m3Selected.id, selection = m3Selection; m3Pending = true; clearM3Results(); m3Notice(""); updateControls();
  try {
    const job = operation === "export" ? await api("durable/export", {kind: "m3", id: identity}) : await api("m3/entries/" + identity + "/" + (operation === "reconstruct" ? "reconstruct" : "retain"), {});
    active = job; selected = job; updateActivity(job); updateM3Activity(job); await refresh();
  } catch (error) { if (m3Selected?.id === identity && m3Selection === selection + 1) m3Notice(error.message); }
  finally { m3Pending = false; updateControls(); }
}
async function downloadM3(name) {
  if (!m3Selected?.can_view_report || m3Busy() || !["report.json", "report.md"].includes(name)) return;
  const identity = m3Selected.id, revision = m3Revision(m3Selected), selection = m3Selection;
  const current = () => m3Selected?.id === identity && m3Revision(m3Selected) === revision && m3Selection === selection && !m3Busy();
  try { const blob = await api("m3/entries/" + identity + "/artifacts/" + name, undefined, true); if (!current()) return; const url = URL.createObjectURL(blob), link = document.createElement("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  catch (error) { if (current()) withdrawM3Snapshot(error.message); }
}
async function browseM3(directory) {
  const root = $("m3-root").value, request = ++m3BrowseRequest;
  const current = () => request === m3BrowseRequest && $("m3-root").value === root;
  try {
    const result = await api("m3/inputs/browse?root_id=" + encodeURIComponent(root) + "&directory=" + encodeURIComponent(directory)); if (!current()) return;
    m3Parent = result.parent; $("m3-directory-up").disabled = result.parent === null; $("m3-directory").textContent = result.directory || "Input root"; $("m3-files").replaceChildren();
    for (const entry of result.entries) { const button = document.createElement("button"); button.type = "button"; button.className = "file-entry"; button.textContent = (entry.kind === "directory" ? "▸ " : "") + entry.name; button.addEventListener("click", () => { if (entry.kind === "directory") browseM3(entry.path); else { $("m3-path").value = entry.path; clearM3Input(); ++m3BrowseRequest; $("m3-dialog").close(); } }); $("m3-files").append(button); }
    if (!result.entries.length) $("m3-files").textContent = "No matching configurations in this directory.";
  } catch (error) { if (current()) $("m3-files").textContent = error.message; }
}
async function initM3() {
  try {
    m3Session = await api("m3/bootstrap"); m3Inputs = m3Session.inputs;
    for (const root of m3Session.roots) { const option = document.createElement("option"); option.value = root.id; option.textContent = root.name + " · " + root.directory; $("m3-root").append(option); }
    renderM3Inputs(); renderM3Candidates(); renderM3Readiness(); await refreshM3();
  } catch (error) { m3Notice(error.message); }
}
$("open-m3").addEventListener("click", () => { workspaceNavigate("m3"); });
$("m3-fixture").addEventListener("click", createM3Fixture);
$("m3-inspect-form").addEventListener("submit", inspectM3);
$("m3-form").addEventListener("submit", (event) => { event.preventDefault(); startM3Configuration("check"); });
$("m3-run").addEventListener("click", () => startM3Configuration("run"));
$("m3-task").addEventListener("change", () => { invalidateM3(); renderM3Candidates(); });
$("m3-timeout").addEventListener("input", invalidateM3);
$("m3-path").addEventListener("input", clearM3Input);
$("m3-root").addEventListener("change", () => { ++m3BrowseRequest; $("m3-path").value = ""; clearM3Input(); });
$("m3-cancel").addEventListener("click", () => { if (active?.operation?.startsWith("m3_")) api("jobs/" + active.id + "/cancel", {}).then(refresh).catch((error) => m3Notice(error.message)); });
$("m3-reconstruct").addEventListener("click", () => startSavedM3("reconstruct"));
$("m3-export").addEventListener("click", () => startSavedM3("export"));
$("m3-retain").addEventListener("click", () => startSavedM3("retain"));
$("m3-download-json").addEventListener("click", () => downloadM3("report.json"));
$("m3-download-markdown").addEventListener("click", () => downloadM3("report.md"));
$("m3-browse").addEventListener("click", () => { $("m3-dialog").showModal(); const path = $("m3-path").value; browseM3(path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : ""); });
$("m3-close-dialog").addEventListener("click", () => { ++m3BrowseRequest; $("m3-dialog").close(); });
$("m3-directory-up").addEventListener("click", () => browseM3(m3Parent || ""));
$("m3-dialog").addEventListener("cancel", () => { ++m3BrowseRequest; });

renderCampaignPlan(); init(); initLibrary(); initDurable(); initM3();
