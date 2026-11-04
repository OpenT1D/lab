"use strict";
// Navigation is presentation state. The SDK ledger remains authoritative.
globalThis.researchUI = (() => {
  let screen = "projects", epoch = 0;
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
  }
  function start(operation) { started.set(operation, {epoch, project: selected}); }
  function finish(operation) {
    const origin = started.get(operation);
    started.delete(operation);
    if (origin && origin.epoch === epoch) {
      if (["create", "open", "relocate"].includes(operation)) show("study");
      else if (["verify", "comparison_verify", "study_verify"].includes(operation) && origin.project === selected) show("results");
    }
  }
  function bind() {
    for (const name of ["projects", "study", "results"]) $("nav-" + name).onclick = () => show(name);
  }
  return {bind, render: paint, show, start, finish};
})();
