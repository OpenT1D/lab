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
      const saved = concepts.get(projectId);
      $("connected-name").value = saved?.name || "";
      $("connected-question").value = saved?.question || "";
      $("connected-case").value = saved?.observation_case || "complete";
      selectedForward = saved?.forward_plan || "";
    }
    const plans = chosen?.info?.plans || [], attempts = chosen?.info?.attempts || [];
    const forward = plans.filter(plan => plan.task === "m4-study-installed" && plan.slots.length === 4 && !attempts.some(a => a.plan === plan.id));
    options($("connected-forward"), [["", "Create a new bounded M4 fasting / 15-g plan"], ...forward.map(plan => [plan.id, label(plan)])], selectedForward);
    const studies = chosen?.info?.studies || [];
    options($("connected-select"), studies.map(study => [study.id, study.name + " · " + study.observation_case]), $("connected-select").value);
    const stale = loaded && (loaded.study !== $("connected-select").value || loaded.snapshot.tip !== chosen?.info?.head?.tip);
    if (stale) $("connected-status").textContent = "The project ledger changed. Inspect the study again before advancing. Earlier report snapshots remain reproducible.";
    $("connected-forward").disabled = busy;
    $("connected-select").disabled = busy || !studies.length;
    $("connected-freeze").disabled = busy;
    for (const id of ["connected-open", "connected-verify", "connected-replay"]) $(id).disabled = busy || !studies.length;
    $("connected-next").disabled = busy || !loaded || stale || !["run", "materialize"].includes(loaded.next.action);
    $("connected-next").textContent = loaded?.next.action === "materialize" ? "Materialize or resume observations and plans" : loaded?.next.plan === loaded?.forward_plan ? "Run known secretion and forward observations" : "Run full inverse and reduced sampling";
    $("connected-forward-report").disabled = busy || !loaded || loaded.stages.forward.payload !== "native";
    $("connected-inverse-report").disabled = busy || !loaded || loaded.stages.inverse_sampling.payload !== "native";
  }
  function bind() {
    $("connected-form").onsubmit = async event => {
      event.preventDefault(); keep();
      const expectedProject = selected;
      const job = await action("study_freeze", {name: $("connected-name").value, question: $("connected-question").value, forward_plan: $("connected-forward").value || null, observation_case: $("connected-case").value});
      if (job?.status === "done" && selected === expectedProject) { $("connected-select").value = job.result.study; await open(); }
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
