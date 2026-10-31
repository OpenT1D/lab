"use strict";
globalThis.connected = (() => {
  let projectId = null, loaded = null, epoch = 0;
  const concepts = new Map();
  function keep() {
    if (projectId) concepts.set(projectId, {name: $("connected-name").value, question: $("connected-question").value, observation_case: $("connected-case").value, forward_plan: $("connected-forward").value});
  }
  function clear() {
    epoch++; loaded = null;
    $("connected-stages").replaceChildren(); $("connected-details").textContent = "";
    $("connected-status").textContent = "Inspect a saved study or freeze a complete new study before execution.";
  }
  function accept(value, expectedProject, identity, issued) {
    if (selected !== expectedProject || $("connected-select").value !== identity || epoch !== issued || value.study !== identity) return false;
    loaded = value;
    $("connected-status").textContent = `${value.name} · ${value.next.reason} · snapshot ${value.snapshot.tip}. Fixed first attempts only.`;
    $("connected-stages").replaceChildren(...Object.entries(value.stages).map(([name, stage]) => element("p", `${name === "forward" ? "Known secretion and forward C-peptide" : "Full inverse and reduced sampling"}: ${stage.status} · evidence ${stage.completeness || "not available"} · first attempt ${stage.attempt || "unattempted"}`)));
    $("connected-details").textContent = JSON.stringify({protocol: value.protocol, planned: value.planned, forward_plan: value.forward_plan, intent: value.intent, bridge: value.bridge, sampling_plan: value.sampling_plan, comparison: value.comparison}, null, 2);
    return true;
  }
  async function open() {
    const identity = $("connected-select").value, expectedProject = selected, issued = ++epoch;
    if (!identity) return;
    const job = await action("study_open", {study: identity, at: null});
    if (job?.status === "done") { accept(job.result, expectedProject, identity, issued); render(); }
  }
  function renderState(incoming, chosen, busy) {
    let selectedForward = $("connected-forward").value;
    if (projectId !== selected) {
      keep(); projectId = selected; clear();
      options($("connected-select"), [], "");
      const saved = concepts.get(projectId);
      $("connected-name").value = saved?.name || "";
      $("connected-question").value = saved?.question || "";
      $("connected-case").value = saved?.observation_case || "complete";
      selectedForward = saved?.forward_plan || "";
    }
    const plans = chosen?.info?.plans || [], attempts = chosen?.info?.attempts || [];
    const forward = plans.filter(plan => plan.task === "m4-study-installed" && plan.slots.length === 4 && !attempts.some(a => a.plan === plan.id));
    const choices = forward.map(plan => [plan.id, label(plan)]);
    if (!chosen?.info && selectedForward) choices.push([selectedForward, "Selected forward plan · refresh project metadata"]);
    options($("connected-forward"), [["", "Create a new bounded M4 fasting / 15-g plan"], ...choices], selectedForward);
    const studies = chosen?.info?.studies || [], selectedStudy = $("connected-select").value;
    const studyChoices = studies.map(study => [study.id, study.name + " · " + study.observation_case]);
    if (!chosen?.info && selectedStudy) studyChoices.push([selectedStudy, "Selected study · refresh project metadata"]);
    if (chosen?.info && selectedStudy && !studies.some(study => study.id === selectedStudy)) { clear(); withdrawReport(); }
    options($("connected-select"), studyChoices, selectedStudy);
    const stale = loaded && (loaded.study !== $("connected-select").value || loaded.snapshot.tip !== chosen?.info?.head?.tip);
    if (stale) $("connected-status").textContent = "The project ledger changed. Inspect the study again before advancing. Earlier report snapshots remain reproducible.";
    if (!chosen?.info) $("connected-status").textContent = "Refresh project metadata before inspecting or advancing the selected study.";
    $("connected-forward").disabled = busy;
    $("connected-select").disabled = busy || !studies.length;
    $("connected-freeze").disabled = busy || !chosen?.info;
    for (const id of ["connected-open", "connected-verify", "connected-replay"]) $(id).disabled = busy || !studies.length;
    const unfinished = attempts.some(attempt => attempt.outcome === "unfinished");
    $("connected-next").disabled = busy || !chosen?.info || !loaded || stale || !["run", "materialize"].includes(loaded.next.action) || loaded.next.action === "run" && unfinished;
    if (!stale && loaded?.next.action === "run" && unfinished) $("connected-status").textContent = "Recover the unfinished project attempt explicitly before starting another execution.";
    $("connected-next").textContent = loaded?.next.action === "materialize" ? "Materialize or resume observations and plans" : loaded?.next.plan === loaded?.forward_plan ? "Run known secretion and forward observations" : "Run full inverse and reduced sampling";
    $("connected-forward-report").disabled = busy || !chosen?.info || !loaded || loaded.stages.forward.payload !== "native";
    $("connected-inverse-report").disabled = busy || !chosen?.info || !loaded || loaded.stages.inverse_sampling.payload !== "native";
  }
  function bind() {
    $("connected-form").onsubmit = async event => {
      event.preventDefault(); keep();
      const expectedProject = selected;
      const job = await action("study_freeze", {name: $("connected-name").value, question: $("connected-question").value, forward_plan: $("connected-forward").value || null, observation_case: $("connected-case").value});
      if (job?.status === "done" && selected === expectedProject) { clear(); withdrawReport(); $("connected-select").value = job.result.study; await open(); }
    };
    $("connected-select").onchange = () => { clear(); withdrawReport(); render(); };
    $("connected-open").onclick = open;
    $("connected-next").onclick = async () => {
      if (!loaded || loaded.snapshot.tip !== project()?.info?.head?.tip) return;
      const expectedProject = selected, identity = loaded.study, step = loaded.next;
      if (step.action === "run") await action("run", {plan: step.plan, retry_of: null});
      else if (step.action === "materialize") await action("study_materialize", {study: identity});
      else return;
      if (selected === expectedProject && $("connected-select").value === identity) await open();
    };
    $("connected-verify").onclick = () => action("study_verify", {study: $("connected-select").value, at: null});
    $("connected-replay").onclick = () => action("study_verify", {study: $("connected-select").value, at: $("connected-tip").value.trim()});
    for (const [id, name] of [["connected-forward-report", "forward"], ["connected-inverse-report", "inverse_sampling"]]) $(id).onclick = () => {
      const stage = loaded?.stages[name];
      if (stage?.payload === "native") return action("verify", {attempt: stage.attempt, allow_failed: $("allow-failed").checked});
    };
  }
  return {render: renderState, bind, selection: () => $("connected-select").value};
})();
