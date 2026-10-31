"use strict";
globalThis.comparisons = (() => {
  let projectId = null, roster = [], available = [], loaded = null, optionEpoch = 0, openEpoch = 0, nextId = 1;
  const draftRosters = new Map();
  const optionValue = value => JSON.stringify(value);
  function keepRoster() {
    if (projectId) draftRosters.set(projectId, {roster, name: $("comparison-name").value, question: $("comparison-question").value, baseline: $("comparison-baseline").value});
  }
  function paintRoster() {
    $("comparison-roster").replaceChildren(...roster.map(member => {
      const row = element("div", undefined, "actions");
      const remove = element("button", "Remove " + member.label); remove.type = "button";
      remove.disabled = pending || !!data?.active;
      remove.onclick = () => { roster = roster.filter(m => m.id !== member.id); paintRoster(); render(); };
      row.append(element("span", member.label + " · " + member.plan.slice(0, 12) + " · " + optionValue(member.selector)), remove); return row;
    }));
    options($("comparison-baseline"), roster.map(m => [m.id, m.label]), $("comparison-baseline").value);
    keepRoster();
  }
  function accept(value, expectedProject, expectedId, epoch) {
    if (selected !== expectedProject || $("comparison-select").value !== expectedId || epoch !== openEpoch) return false;
    loaded = value;
    $("comparison-changes").textContent = value.changes_text;
    $("comparison-members").replaceChildren(...value.variants.map(member => {
      const attempt = value.attempts[member.plan];
      return element("p", `${member.label} · ${optionValue(member.selector)} · ${attempt.status} · ${attempt.completeness || "evidence not yet available"} · first attempt ${attempt.attempt || "unattempted"}`);
    }));
    $("comparison-status").textContent = `Frozen comparison · ${value.variants.length} planned members · baseline ${value.baseline} · snapshot ${value.snapshot.tip}. First attempts only.`;
    return true;
  }
  async function open() {
    const identity = $("comparison-select").value, expectedProject = selected, epoch = ++openEpoch;
    if (!identity) return;
    const job = await action("comparison_open", {comparison: identity, at: null});
    if (job?.status === "done") { accept(job.result, expectedProject, identity, epoch); render(); }
  }
  function renderState(incoming, chosen, busy) {
    if (projectId !== selected) {
      keepRoster(); projectId = selected; optionEpoch++; openEpoch++; loaded = null; available = [];
      const saved = draftRosters.get(projectId); roster = saved?.roster || [];
      $("comparison-name").value = saved?.name || ""; $("comparison-question").value = saved?.question || "";
      $("comparison-changes").textContent = ""; $("comparison-members").replaceChildren();
      $("comparison-status").textContent = "Freeze the complete roster before running any selected plan.";
      options($("comparison-selector"), []); paintRoster();
      if (saved?.baseline) $("comparison-baseline").value = saved.baseline;
    }
    const plans = chosen?.info?.plans || [], attempts = chosen?.info?.attempts || [];
    const unused = plans.filter(p => ["mmtt-sensitivity", "mmtt-sampling", "m4-study-installed"].includes(p.task) && !attempts.some(a => a.plan === p.id));
    const oldPlan = $("comparison-plan").value;
    options($("comparison-plan"), unused.map(p => [p.id, label(p)]), oldPlan);
    if ($("comparison-plan").value !== oldPlan) { available = []; optionEpoch++; options($("comparison-selector"), []); }
    const entries = chosen?.info?.comparisons || [];
    options($("comparison-select"), entries.map(c => [c.id, c.name + " · " + c.members + " members"]), $("comparison-select").value);
    const stale = loaded && (loaded.comparison !== $("comparison-select").value || loaded.snapshot.tip !== chosen?.info?.head?.tip);
    if (stale) $("comparison-status").textContent = "The saved ledger changed. Inspect the saved comparison again to refresh statuses. Earlier report snapshots remain reproducible.";
    $("comparison-options").disabled = busy || !unused.length;
    $("comparison-plan").disabled = busy || !unused.length;
    $("comparison-selector").disabled = busy || !available.length;
    $("comparison-select").disabled = busy || !entries.length;
    $("comparison-add").disabled = busy || !available.length || roster.length >= 16;
    $("comparison-freeze").disabled = busy || roster.length < 2;
    $("comparison-open").disabled = busy || !entries.length;
    $("comparison-next").disabled = busy || !loaded || stale || !Object.values(loaded.attempts).some(a => a.status === "unattempted") || attempts.some(a => a.outcome === "unfinished");
    $("comparison-verify").disabled = busy || !entries.length;
    $("comparison-replay").disabled = busy || !entries.length;
    for (const button of $("comparison-roster").children) for (const child of button.children) if (child.tagName === "BUTTON") child.disabled = busy;
  }
  function bind() {
    $("comparison-plan").onchange = () => { optionEpoch++; available = []; options($("comparison-selector"), []); render(); };
    $("comparison-options").onclick = async () => {
      const plan = $("comparison-plan").value, expectedProject = selected, epoch = ++optionEpoch;
      const job = await action("comparison_options", {plan});
      if (job?.status !== "done" || epoch !== optionEpoch || selected !== expectedProject || $("comparison-plan").value !== plan) return;
      available = job.result.options;
      options($("comparison-selector"), available.map(item => [optionValue(item.selector), item.label])); render();
    };
    $("comparison-add").onclick = () => {
      const plan = $("comparison-plan").value, choice = available.find(item => optionValue(item.selector) === $("comparison-selector").value);
      if (!choice || roster.length >= 16) return;
      const name = $("comparison-label").value.trim() || choice.label;
      if (roster.some(m => m.label === name || m.plan === plan && optionValue(m.selector) === optionValue(choice.selector))) { notice("Choose a unique member label and plan/variant combination.", true); return; }
      roster = [...roster, {id: "member-" + nextId++, label: name, plan, selector: choice.selector}];
      $("comparison-label").value = ""; paintRoster(); render();
    };
    $("comparison-form").onsubmit = async event => {
      event.preventDefault();
      if (roster.length < 2) return;
      const expectedProject = selected, submitted = roster;
      const definition = {schema: "opent1d.plan-comparison/1", name: $("comparison-name").value, question: $("comparison-question").value, baseline: $("comparison-baseline").value, variants: roster};
      const job = await action("comparison_freeze", {definition});
      if (job?.status === "done" && selected === expectedProject) {
        if (roster === submitted && $("comparison-name").value === definition.name && $("comparison-question").value === definition.question && $("comparison-baseline").value === definition.baseline) { roster = []; paintRoster(); }
        $("comparison-select").value = job.result.comparison; await open();
      }
    };
    $("comparison-select").onchange = () => { openEpoch++; loaded = null; $("comparison-members").replaceChildren(); $("comparison-changes").textContent = ""; $("comparison-status").textContent = "Inspect the selected comparison to read its frozen roster and snapshot."; withdrawReport(); render(); };
    $("comparison-open").onclick = open;
    $("comparison-next").onclick = async () => {
      if (!loaded) return;
      const expectedProject = selected, identity = loaded.comparison;
      const plan = loaded.variants.map(member => member.plan).find(key => loaded.attempts[key].status === "unattempted");
      if (!plan || loaded.snapshot.tip !== project()?.info?.head?.tip) return;
      await action("run", {plan, retry_of: null});
      if (selected === expectedProject && $("comparison-select").value === identity) await open();
    };
    $("comparison-verify").onclick = () => action("comparison_verify", {comparison: $("comparison-select").value, at: null});
    $("comparison-replay").onclick = () => action("comparison_verify", {comparison: $("comparison-select").value, at: $("comparison-tip").value.trim()});
    globalThis.addEventListener("beforeunload", event => { if (roster.length) { keepRoster(); event.preventDefault(); event.returnValue = ""; } });
  }
  return {render: renderState, bind};
})();
