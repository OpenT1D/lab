"use strict";
// Navigation is presentation state. The SDK ledger remains authoritative.
globalThis.researchUI = (() => {
  let screen = "projects", epoch = 0, nextAction = null;
  const started = new Map();
  function show(next, focus = true) {
    if (!["projects", "study", "results"].includes(next) || next !== "projects" && !project()) return;
    screen = next; epoch++;
    paint();
    if (focus) $("main").focus();
  }
  function paint() {
    const chosen = project();
    if (!chosen) screen = "projects";
    $("projects-screen").classList.toggle("hidden", screen !== "projects");
    $("welcome").classList.toggle("hidden", screen !== "projects");
    $("project-view").classList.toggle("hidden", screen === "projects" || !chosen);
    $("study-screen").classList.toggle("hidden", screen !== "study");
    $("results-screen").classList.toggle("hidden", screen !== "results");
    document.querySelector(".layout").classList.toggle("project-open", screen !== "projects");
    for (const name of ["projects", "study", "results"]) {
      const button = $("nav-" + name);
      button.disabled = name !== "projects" && !chosen;
      if (name === screen) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    }
    updateGuidance();
  }
  function start(operation) { started.set(operation, {epoch, project: selected}); }
  function finish(job) {
    const operation = job.operation;
    const origin = started.get(operation);
    started.delete(operation);
    if (origin && origin.epoch === epoch) {
      if (["create", "open", "relocate"].includes(operation)) show("study");
      else if (["verify", "comparison_verify", "study_verify"].includes(operation) && origin.project === selected && currentReport?.id === job.result.report) show("results");
    }
  }
  function projectStatus(item) {
    const active = data.jobs.find(job => job.id === data.active && job.project === item.id);
    if (active) return active.cancel_requested ? "Stop requested" : "Action in progress";
    if (!item.info) return "Open to inspect saved state";
    if (item.info.error) return "Project needs attention";
    const attempts = item.info.attempts || [];
    if (attempts.some(attempt => attempt.outcome === "unfinished")) return "Execution needs attention";
    const last = attempts.at(-1)?.outcome;
    if (last) return last.completeness === "complete" ? "Results available" : "Saved execution needs review";
    if ((data.drafts || []).some(record => record.project === item.id)) return "Study concept saved";
    return item.info.plans?.length ? "Frozen plans available" : "Prepare a study";
  }
  function guide(title, detail, label, run, step) {
    $("next-title").textContent = title; $("next-detail").textContent = detail;
    $("next-action").textContent = label;
    $("next-action").disabled = !run || pending || !!data?.active || data?.closing;
    nextAction = run;
    for (const name of ["approach", "inputs", "freeze", "run"]) {
      if (name === step) $("step-" + name).setAttribute("aria-current", "step"); else $("step-" + name).removeAttribute("aria-current");
    }
  }
  function updateGuidance() {
    if (!data) return;
    const chosen = project(), editing = globalThis.workbench?.state?.();
    const plan = chosen?.info?.plans?.find(item => item.id === selectedPlan);
    const openDraft = draft?.project === selected ? draft : null;
    const attempt = chosen?.info?.attempts?.filter(item => item.plan === selectedPlan).at(-1);
    $("research-identity").textContent = openDraft ? `Editable concept · saved revision ${openDraft.revision}. Existing frozen plans and results are preserved.` : plan ? `Frozen plan · ${label(plan)}. Original inputs and assumptions cannot be edited in place.` : "A saved concept can be corrected; a frozen plan is the exact version used for execution.";
    if (pending || data.active || data.closing) { guide("Action in progress", "The shared action status above shows progress. Screen navigation does not stop the action.", "Waiting for the action", null, "run"); return; }
    if (editing?.conflict) { guide("Resolve the saved-version conflict", "Your local edits are retained. Choose whether to reload the saved revision or keep your edits as a new concept.", "Review the conflict", () => $("reload-draft").focus(), "inputs"); return; }
    if (editing?.saving) { guide("Saving the concept", "Wait for the server to acknowledge this revision before continuing.", "Saving…", null, "inputs"); return; }
    if (editing?.uploadError) { guide("Correct the input file", editing.uploadError, "Inspect input files", () => { $("raw-inputs").open = true; $("raw-inputs").scrollIntoView({block: "start"}); }, "inputs"); return; }
    if (editing?.dirty || editing?.saveError) { guide("Save your changes", "The edited inputs must be saved before they can be checked or frozen.", "Save changes", () => $("save-draft").click(), "inputs"); return; }
    if (openDraft && !openDraft.frozen_plan) {
      const valid = editing ? editing.valid : openDraft.validation?.valid;
      guide(valid ? "Inspect and freeze this study" : "Check the saved inputs", valid ? "Review the assumptions below. Freezing retains this exact saved revision; it does not run the analysis." : "Validation checks this saved input version. Correct any reported problems before freezing.", valid ? "Freeze this plan" : "Check saved inputs", () => $(valid ? "freeze-draft" : "validate-draft").click(), "freeze"); return;
    }
    if (!plan) { guide("Choose an approach", "Choose a supported research task, then prepare a supplied synthetic example or add the admitted synthetic input files.", "Choose research task", () => $("task").focus(), "approach"); return; }
    if (attempt) { guide("Review the saved execution", "Inspect its outcome and completeness. A retry or a changed study preserves the original attempt.", "View results", () => show("results"), "run"); return; }
    const checked = planReadiness && planReadiness.project === selected && planReadiness.plan === selectedPlan && planReadiness.runtime_revision === data.runtime_revision && planReadiness.runtime_attachment === data.runtime_attachment;
    if (checked && !planReadiness.ready) { guide("Execution needs a reviewed runtime", "Inspect the runtime selection and check this plan again. No dependencies are installed by this interface.", "Review runtime selection", () => { $("runtime-controls").open = true; $("runtime-controls").scrollIntoView({block: "start"}); }, "run"); return; }
    guide(checked ? "Ready to execute this frozen plan" : "Check whether the plan can run", checked ? "Starting creates a new recorded attempt using the frozen inputs. It does not change the plan." : "Check the selected plan and current runtime before explicit execution.", checked ? "Start execution" : "Check this plan", () => $(checked ? "run-plan" : "check-plan").click(), "run");
  }
  function bind() {
    for (const name of ["projects", "study", "results"]) $("nav-" + name).onclick = () => show(name);
    $("next-action").onclick = () => nextAction?.();
  }
  return {bind, render: paint, show, start, finish, projectStatus, updateGuidance};
})();
