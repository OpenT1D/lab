"use strict";
globalThis.workbench = (() => {
  const rosters = {
    "mmtt-sensitivity": ["package.json", "observations.csv", "settings.json"],
    "mmtt-sampling": ["package.json", "observations.csv", "settings.json", "design.json", "development-package.json", "development-observations.csv"],
    "m4-study-installed": ["config.json"],
  };
  let current = null, inputs = {}, invalidFiles = {}, fileEdits = {}, dirty = false, conflict = false, saving = false, saveError = null, timer = null, generation = 0, pickerSelection = null;
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const key = record => `opent1d.concept-recovery/1:${data.workspace}:${record.project}:${record.id}`;
  const json = name => JSON.parse(inputs[name].replace(/^\uFEFF/, ""));
  function snapshot() { return {files: {...inputs}, name: $("plan-name").value, parent: $("parent-plan").value || null}; }
  function backup() {
    if (!current) return;
    try { localStorage.setItem(key(current), JSON.stringify({revision: current.revision, ...snapshot()})); }
    catch { notice("Browser recovery storage is unavailable. Save this concept before leaving the page.", true); }
  }
  function clearBackup(record) { try { localStorage.removeItem(key(record)); } catch {} }
  function schedule() { clearTimeout(timer); if (!conflict) timer = setTimeout(() => save(), 800); }
  function changed(rebuild = false) {
    if (!current) return;
    dirty = true; saveError = null; invalidatePlanView(); backup(); schedule();
    if (rebuild) assumptions();
    status();
  }
  function valid() {
    const stamp = current?.validation;
    return !!stamp?.valid && stamp.revision === current.revision && stamp.content_sha256 === current.content_sha256
      && stamp.application === (current.current_application || data.installation.descriptor_sha256);
  }
  function status() {
    if (!current) return;
    const uploadErrors = Object.values(invalidFiles);
    $("draft-status").textContent = uploadErrors.length ? uploadErrors.join(" ") : saving ? "Saving concept…" : conflict ? "Local edits retained; a newer saved revision needs your choice." : saveError ? "Not saved. Local edits retained: " + saveError + " Retry Save concept or correct the inputs." : dirty ? "Unsaved changes — waiting to save." : `Saved revision ${current.revision} · ${current.frozen_plan ? "Plan frozen. Further edits derive from that plan." : valid() ? "Inputs validated. Ready to freeze." : "Validate saved inputs before freezing."}`;
    $("draft-conflict").classList.toggle("hidden", !conflict);
    $("draft-conflict").textContent = conflict ? "This concept changed in another tab. Reload the saved version to discard local edits, or keep your edits as a new concept. Neither choice overwrites the other tab's work." : "";
    $("fork-draft").classList.toggle("hidden", !conflict);
    const busy = pending || !!data?.active || data?.closing;
    const operation = pendingOperation || data?.jobs.find(job => job.id === data.active)?.operation;
    const editingLocked = busy && operation !== "draft_save";
    for (const input of document.querySelectorAll("#draft input, #draft textarea, #draft select")) input.disabled = editingLocked;
    $("prepare-supplied").disabled = busy || dirty || conflict;
    $("new-draft").disabled = busy || dirty || conflict;
    $("derive-plan").disabled = busy || dirty || conflict || !selectedPlan;
    $("save-draft").disabled = busy || conflict || !dirty;
    $("validate-draft").disabled = busy || conflict || !!uploadErrors.length;
    $("freeze-draft").disabled = busy || dirty || conflict || !!uploadErrors.length || !valid() || !!current.frozen_plan;
    $("restore-draft").disabled = busy || dirty || conflict;
    $("reload-draft").textContent = dirty || conflict ? "Reload saved version — discard local edits" : "Reload saved version";
    if (blocksRun()) { $("run-plan").disabled = true; $("check-plan").disabled = true; $("readiness").textContent = "An editable concept is open. Freeze it to run its saved assumptions, or return to the existing frozen plans."; }
  }
  function editor(name, value) {
    const box = element("fieldset"), legend = element("legend", name), id = "source-" + name.replaceAll(".", "-");
    const label = element("label", "Upload " + name); label.htmlFor = id + "-upload";
    const upload = element("input"); upload.type = "file"; upload.accept = name.endsWith(".csv") ? ".csv,text/csv" : ".json,application/json"; upload.id = id + "-upload";
    const areaLabel = element("label", "Raw " + name); areaLabel.htmlFor = id;
    const area = element("textarea"); area.id = id; area.rows = 8; area.spellcheck = false; area.value = value;
    area.oninput = () => { fileEdits[name] = (fileEdits[name] || 0) + 1; delete invalidFiles[name]; inputs[name] = area.value; changed(true); };
    upload.onchange = async () => {
      const selectedFile = upload.files[0], sequence = (fileEdits[name] || 0) + 1;
      fileEdits[name] = sequence;
      if (!selectedFile) { delete invalidFiles[name]; status(); return; }
      const stamp = generation, relevant = () => stamp === generation && fileEdits[name] === sequence;
      invalidFiles[name] = "Reading " + name + "…"; status();
      try {
        if (selectedFile.size > (name.endsWith(".csv") ? 512 : 128) * 1024) throw new Error("This file exceeds the concept byte limit.");
        const text = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(await selectedFile.arrayBuffer());
        if (!relevant()) return;
        delete invalidFiles[name]; inputs[name] = text; area.value = text; changed(true);
      } catch (error) { if (relevant()) { invalidFiles[name] = name + ": " + error.message + " Choose a valid file, edit its text, or reload the saved version."; status(); notice(error.message, true); } }
    };
    box.append(legend, label, upload, areaLabel, area); return box;
  }
  function control(container, label, value, update, {type = "number", step = "any", id} = {}) {
    const box = element("div"), text = element("label", label), input = element("input");
    input.type = type; if (type === "number") input.step = step; input.value = value; input.id = id || "assumption-" + label.toLowerCase().replace(/[^a-z0-9]+/g, "-"); text.htmlFor = input.id;
    input.oninput = () => {
      try {
        let value = input.value;
        const number = Number(value), invalid = type === "number" && (value === "" || !Number.isFinite(number) || (step === "1" && !Number.isSafeInteger(number)));
        if (type === "number" && !invalid) value = number;
        update(value);
        if (invalid) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
        changed();
      }
      catch (error) { input.setAttribute("aria-invalid", "true"); notice(error.message, true); }
    };
    box.append(text, input); container.append(box);
  }
  function changeJSON(name, apply) {
    fileEdits[name] = (fileEdits[name] || 0) + 1; delete invalidFiles[name];
    const value = json(name); apply(value); inputs[name] = JSON.stringify(value, null, 2) + "\n";
    const area = $("source-" + name.replaceAll(".", "-")); if (area) area.value = inputs[name];
  }
  function assumptions() {
    const target = $("assumptions"); target.replaceChildren();
    if (!current) return;
    try {
      if (current.task === "m4-study-installed") {
        const value = json("config.json"), box = element("fieldset"); box.append(element("legend", "Selected synthetic M4 study"));
        for (const name of ["timeout_seconds", "source_timeout_seconds"]) control(box, name.replaceAll("_", " "), value[name], v => changeJSON("config.json", s => { s[name] = v; }), {step: "1"});
        control(box, "Scenarios (JSON array)", arrayText(value.scenarios), text => changeJSON("config.json", s => { s.scenarios = arrayValue(text); }), {type: "text"});
        box.append(element("p", "The reviewed source pair and native runtime boundary remain fixed.", "muted")); target.append(box); return;
      }
      const settings = json("settings.json");
      if (typeof settings.uncertainty.seed === "number" && !Number.isSafeInteger(settings.uncertainty.seed)) throw new Error("This seed exceeds JavaScript's exact integer range. Use the raw settings editor; structured edits are disabled to preserve it.");
      const box = element("fieldset"); box.append(element("legend", "Shared paired-analysis assumptions"));
      const grid = element("div", undefined, "form-grid");
      for (const [name, label] of [["draws", "Uncertainty draws"], ["seed", "Random seed"], ["independent_sd_pmol_l", "Independent SD (pmol/L)"], ["paired_offset_sd_pmol_l", "Paired offset SD (pmol/L)"]]) {
        control(grid, label, settings.uncertainty[name], value => {
          changeJSON("settings.json", s => { s.uncertainty[name] = value; });
        }, {id: "assumption-" + name, step: ["draws", "seed"].includes(name) ? "1" : "any"});
      }
      box.append(grid);
      for (const variant of settings.variants) {
        const group = element("fieldset"); group.append(element("legend", "Required variant: " + variant.id));
        for (const [name, label] of [["id", "Variant ID"], ["rationale", "Engineering rationale"], ["k1_per_min", "k1 (1/min)"], ["k2_per_min", "k2 (1/min)"], ["k3_per_min", "k3 (1/min)"], ["volume_l", "Whole-body volume (L)"], ["initial_peripheral_factor", "Initial peripheral factor"]]) {
          const index = settings.variants.indexOf(variant);
          control(group, label, variant[name], value => {
            changeJSON("settings.json", s => { s.variants[index][name] = value; });
          }, {id: `variant-${index}-${name}`, type: ["id", "rationale"].includes(name) ? "text" : "number"});
        }
        box.append(group);
      }
      target.append(box);
      if (current.task === "mmtt-sampling") {
        const design = json("design.json"), group = element("fieldset"); group.append(element("legend", "Development-selected measurement schedules"));
        control(group, "Full actual times (minutes, JSON array)", arrayText(design.full_times_minutes), text => changeJSON("design.json", s => { s.full_times_minutes = arrayValue(text); }), {type: "text", id: "schedule-full"});
        for (const [name, times] of Object.entries(design.subsets)) control(group, name + " times (minutes, JSON array)", arrayText(times), text => changeJSON("design.json", s => { s.subsets[name] = arrayValue(text); }), {type: "text", id: "schedule-" + name});
        control(group, "Development selection rationale", design.selection_rationale, text => changeJSON("design.json", s => { s.selection_rationale = text; }), {type: "text", id: "selection-rationale"});
        group.append(element("p", "Allocation and selection participants are explicit in the design JSON. Supply matching development-only metadata and CSV; evaluation observations cannot select schedules.", "muted")); target.append(group);
      }
    } catch (error) { target.replaceChildren(element("p", "Structured controls unavailable: " + error.message + " Saved raw input remains editable below.", "context")); }
  }
  function arrayText(value) { return typeof value === "string" ? value : JSON.stringify(value); }
  function arrayValue(text) { try { return JSON.parse(text); } catch { return text; } }
  function paint() {
    $("plan-name").value = current.name;
    const plans = project()?.info?.plans || [];
    options($("parent-plan"), [["", "Original plan"], ...plans.filter(p => p.task === current.task).map(p => [p.id, label(p)])], current.parent || "");
    $("file-editors").replaceChildren(...Object.entries(inputs).map(([name, value]) => editor(name, value)));
    options($("draft-revision"), current.history.map(item => [String(item.revision), `Revision ${item.revision} · ${item.name} · ${new Date(item.saved_at).toLocaleString()}`]), String(current.revision));
    $("draft-details").textContent = JSON.stringify(current.validation || {validated: false}, null, 2);
    assumptions(); status();
  }
  function accept(record, {recover = false} = {}) {
    generation++; clearTimeout(timer); current = record; draft = record; inputs = {...record.files}; invalidFiles = {}; fileEdits = {}; dirty = false; conflict = false; saveError = null; pickerSelection = record.id;
    if (recover) {
      try {
        const saved = JSON.parse(localStorage.getItem(key(record)) || "null");
        if (saved) {
          inputs = saved.files; current = {...record, name: saved.name, parent: saved.parent}; draft = current;
          dirty = true; conflict = saved.revision !== record.revision;
        }
      } catch { notice("Browser recovery copy could not be read. The server's saved revision is open.", true); }
    }
    paint(); invalidatePlanView(); if (dirty && !conflict) schedule(); render();
  }
  async function open(identity, recover = true) {
    const stamp = ++generation, selectedProject = selected;
    try {
      const record = await (await request("/api/drafts/" + identity)).json();
      if (stamp !== generation || selectedProject !== selected || record.project !== selected) return;
      accept(record, {recover});
    } catch (error) { notice(error.message, true); }
  }
  async function save() {
    clearTimeout(timer);
    if (!current || !dirty || conflict || saving) return !dirty;
    if (pending || data?.active) { schedule(); return false; }
    saving = true; saveError = null; const record = current, values = snapshot(), stamp = generation; status();
    const job = await action("draft_save", {draft: record.id, revision: record.revision, ...values}, record.project);
    saving = false;
    if (stamp !== generation || current?.id !== record.id) return false;
    if (job?.status === "done") {
      const result = job.result;
      const unchanged = same(snapshot(), values);
      if ($("parent-plan").value === (values.parent || "")) $("parent-plan").value = result.parent || "";
      current = result; draft = result;
      if (unchanged) {
        clearBackup(record); dirty = false; conflict = false;
        options($("draft-revision"), result.history.map(item => [String(item.revision), `Revision ${item.revision} · ${item.name}`]), $("draft-revision").value);
        $("draft-details").textContent = JSON.stringify(result.validation || {validated: false}, null, 2);
        status();
      } else { dirty = true; backup(); schedule(); status(); }
      return !dirty;
    }
    conflict = /another tab/.test(job?.error || ""); saveError = job?.error || "The server did not confirm the save."; backup(); status(); return false;
  }
  async function validate() {
    if (!current || conflict || Object.keys(invalidFiles).length) return;
    if (dirty && !await save()) return;
    const record = current, values = snapshot(), stamp = generation;
    const job = await action("draft_validate", {draft: record.id, revision: record.revision}, record.project);
    if (job?.status === "done" && finishRevision(job.result, record, values, stamp) && !valid()) notice(current.validation.error, true);
  }
  function finishRevision(result, previous, values, stamp) {
    if (stamp !== generation || current?.id !== previous.id) return false;
    if (!same(snapshot(), values) || Object.keys(invalidFiles).length) {
      if ($("parent-plan").value === (values.parent || "")) $("parent-plan").value = result.parent || "";
      current = {...result, validation: null}; draft = current; dirty = true; conflict = false;
      backup(); schedule(); status(); return false;
    }
    clearBackup(previous); accept(result); return true;
  }
  function switchResult(result, stamp, previous, values) {
    if (stamp !== generation || (previous && (!current || current.id !== previous.id || !same(snapshot(), values)))) {
      notice("The new concept is saved separately. Your current local edits are retained."); return;
    }
    if (previous) clearBackup(previous);
    accept(result);
  }
  function close() { if (dirty) backup(); generation++; clearTimeout(timer); current = null; draft = null; inputs = {}; invalidFiles = {}; fileEdits = {}; dirty = false; conflict = false; saveError = null; }
  function blocksRun() { return !!current && (dirty || !current.frozen_plan); }
  function renderState(incoming, chosen, busy) {
    if (current && current.project !== selected) close();
    const entries = (incoming.drafts || []).filter(item => item.project === selected);
    const selectedDraft = $("draft-select").value;
    options($("draft-select"), [["", entries.length ? "Choose a saved concept" : "No saved concepts yet"], ...entries.map(item => [item.id, `${item.name} · revision ${item.revision}`])], pickerSelection ?? selectedDraft);
    pickerSelection = null;
    $("open-draft").disabled = busy || !entries.length; $("new-draft").disabled = busy;
    $("derive-plan").disabled = busy || !selectedPlan;
    $("draft-issues").classList.toggle("hidden", !(incoming.draft_issues || []).length);
    $("draft-issues").textContent = (incoming.draft_issues || []).map(item => "Saved concept unavailable: " + item.id + ". " + item.error).join("\n");
    if (current) {
      const saved = entries.find(item => item.id === current.id);
      if (saved && saved.revision !== current.revision && !saving && !pending) conflict = true;
      $("draft").classList.remove("hidden"); status();
    }
  }
  function bind() {
    $("new-draft").onclick = async () => {
      const task = $("task").value, files = Object.fromEntries(rosters[task].map(name => [name, ""]));
      const stamp = generation, previous = current, values = current ? snapshot() : null;
      const job = await action("draft_create", {task, name: "Own synthetic study", parent: null, files});
      if (job?.status === "done") { switchResult(job.result, stamp, previous, values); $("raw-inputs").open = true; $("plan-name").focus(); }
    };
    $("open-draft").onclick = () => $("draft-select").value ? open($("draft-select").value) : undefined;
    $("plan-name").oninput = () => changed(); $("parent-plan").onchange = () => changed();
    $("save-draft").onclick = save; $("validate-draft").onclick = validate;
    $("close-draft").onclick = () => { close(); render(); invalidatePlanView(); };
    $("reload-draft").onclick = () => { if (current) { clearBackup(current); open(current.id, false); } };
    $("fork-draft").onclick = async () => {
      if (!current) return;
      const values = snapshot(), task = current.task, previous = current, stamp = generation;
      const job = await action("draft_create", {task, name: values.name, parent: values.parent, files: values.files}, current.project);
      if (job?.status === "done") switchResult(job.result, stamp, previous, values);
    };
    $("restore-draft").onclick = async () => {
      if (!current || dirty || conflict) return;
      const previous = current, values = snapshot(), stamp = generation;
      const job = await action("draft_restore", {draft: current.id, revision: current.revision, selected: Number($("draft-revision").value)}, current.project);
      if (job?.status === "done") finishRevision(job.result, previous, values, stamp);
    };
    $("derive-plan").onclick = async () => { const stamp = generation, previous = current, values = current ? snapshot() : null; const job = await action("derive", {plan: selectedPlan}); if (job?.status === "done") { switchResult(job.result, stamp, previous, values); $("plan-name").focus(); } };
    globalThis.addEventListener("beforeunload", event => { if (dirty || saving) { backup(); event.preventDefault(); event.returnValue = ""; } });
    globalThis.addEventListener("keydown", event => { if (current && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); save(); } });
  }
  return {accept, open, save, validate, close, blocksRun, render: renderState, bind,
    async freeze() {
      if (!current || dirty || conflict || Object.keys(invalidFiles).length || !valid() || current.frozen_plan) { notice("Save and validate this concept before freezing.", true); return; }
      return action("freeze", {draft: current.id, revision: current.revision, name: current.name, parent: current.parent});
    },
  };
})();
