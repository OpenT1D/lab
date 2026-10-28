"use strict";

// One fixed observation task. All estimates, intervals and labels are native results.
const obsRateFields = [["k1_per_min", "k1: central → peripheral (min⁻¹)", true],
  ["k2_per_min", "k2: return (min⁻¹)", false], ["k3_per_min", "k3: removal (min⁻¹)", false],
  ["volume_l", "Whole-body volume (L)", false], ["initial_peripheral_factor", "Initial peripheral factor", false]];
function obsNumber(value) { return value === null || value === undefined ? "unavailable" : Number(value).toPrecision(8).replace(/(?:\.0+|(?:(\.\d*?)0+))(?=e|$)/, "$1"); }
function obsInterval(value) { return value === null || value === undefined ? "unavailable" : value.map(obsNumber).join(" to "); }
function obsElement(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function obsTable(target, caption, headers, rows) {
  const wrapper = obsElement("div", undefined, "obs-table-scroll"), table = document.createElement("table");
  table.append(obsElement("caption", caption));
  const head = document.createElement("thead"), tr = document.createElement("tr");
  for (const label of headers) { const th = obsElement("th", label); th.scope = "col"; tr.append(th); } head.append(tr); table.append(head);
  const body = document.createElement("tbody");
  for (const values of rows) { const row = document.createElement("tr"); for (const value of values) row.append(obsElement("td", String(value))); body.append(row); }
  table.append(body); wrapper.append(table); target.append(wrapper); return table;
}
function obsDetails(target, title, render, open = false) {
  const details = document.createElement("details"); details.className = "obs-person";
  details.append(obsElement("summary", title)); let rendered = false;
  const draw = () => { if (!rendered) { rendered = true; render(details); } };
  details.addEventListener("toggle", () => { if (details.open) draw(); });
  if (open) { details.open = true; draw(); } target.append(details); return details;
}
function obsValidateNative(report) {
  const fail = () => { throw new Error("The native observation report is incompatible or has incomplete accounting."); };
  if (!report || report.schema !== "opent1d.observation-analysis/1" || report.task !== "mmtt-sensitivity" || report.kind !== "synthetic" || report.human_evaluation !== false || !report.coverage || typeof report.coverage.complete_cohort !== "boolean" || !report.people || typeof report.people !== "object") fail();
  if (report.execution_status !== "completed") { if (report.coverage.complete_cohort || Object.keys(report.people).length) fail(); return report; }
  const settings = report.plan?.settings, people = Object.entries(report.people);
  if (!settings || settings.visit_order?.length !== 2 || !Array.isArray(settings.variants) || settings.variants.length < 2 || people.length !== report.coverage.planned_people || report.coverage.planned_visits !== 2 * people.length || report.coverage.planned_variant_pairs !== people.length * settings.variants.length) fail();
  for (const [, person] of people) {
    if (!["consistent within investigated assumptions", "assumption-dependent", "insufficiently determined"].includes(person.classification) || !person.references || !person.variants || Object.keys(person.variants).length !== settings.variants.length) fail();
    for (const definition of settings.variants) {
      const variant = person.variants[definition.id];
      if (!variant || variant.planned_draws !== settings.uncertainty.draws || !Number.isSafeInteger(variant.attempted_draws) || variant.completed_draws + variant.failed_draws !== variant.attempted_draws || variant.attempted_draws + variant.not_attempted_draws !== variant.planned_draws || !Array.isArray(variant.draws) || variant.draws.length !== variant.attempted_draws || !variant.point?.visits || !variant.visit_intervals_pmol) fail();
      for (const visit of settings.visit_order) if (!(visit in variant.point.visits) || !(visit in variant.visit_intervals_pmol)) fail();
    }
  }
  return report;
}
function renderObservationReport(report, target) {
  obsValidateNative(report); target.replaceChildren();
  const c = report.coverage, known = (value) => value === null ? "unknown" : String(value);
  target.append(obsElement("p", "Whole-body total endogenous secretion, including basal, over measured 0–120 minutes. Follow-up minus baseline, in pmol. No normalization.", "obs-scope"));
  target.append(obsElement("p", "Invented observations and engineering assumptions only. A secretion difference is not evidence of restored beta-cell function or a treatment effect. Human coverage and usability are untested.", "field-note"));
  target.append(obsElement("p", `${c.complete_people} / ${known(c.planned_people)} complete paired analyses; ${c.completed_variant_pairs} / ${known(c.planned_variant_pairs)} complete required variant pairs. Calculation completeness is separate from a resolved conclusion.`, "obs-scope"));
  if (report.execution_status !== "completed") {
    target.append(obsElement("p", report.fatal_error || "Atomic analysis attempt unavailable after interruption.", "notice"));
    obsTable(target, "Declared participants retained", ["Participant", "Allocation", "Attempt status"], (report.unavailable_participants || []).map(p => [p.id, p.allocation, p.status])); return;
  }
  const settings = report.plan.settings, order = settings.visit_order;
  obsDetails(target, "Frozen engineering assumptions", box => {
    obsTable(box, "All required variants", ["Variant", "Volume (L)", "Initial peripheral factor", "k1 / k2 / k3 (min⁻¹)", "Rationale"], settings.variants.map(v => [v.id, obsNumber(v.volume_l), obsNumber(v.initial_peripheral_factor), [v.k1_per_min, v.k2_per_min, v.k3_per_min].map(obsNumber).join(" / "), v.rationale]));
    const n = settings.uncertainty;
    box.append(obsElement("p", `${n.draws} frozen draws; independent SD ${obsNumber(n.independent_sd_pmol_l)} pmol/L; shared paired-offset SD ${obsNumber(n.paired_offset_sd_pmol_l)} pmol/L. Nominal central 95% perturbation intervals, conditional on each variant; no established human coverage.`, "field-note"));
  });
  if (report.import_errors.length) obsTable(target, "Package import failures", ["CSV record", "Reason"], report.import_errors.map(e => [e.row ?? "package", e.reason]));
  const labels = {age_years: "Age (years)", height_cm: "Height (cm)", weight_kg: "Weight (kg)", renal_context: "Renal context", population: "Population context", sex: "Declared sex"};
  for (const [id, person] of Object.entries(report.people)) obsDetails(target, `${id} · ${person.classification}`, box => {
    box.append(obsElement("p", `${person.status} calculation · ${person.allocation} allocation. An interval containing zero is unresolved; it does not establish absence of change. Variants are never averaged into a probability distribution.`, "obs-scope"));
    obsTable(box, "Paired total secretion", ["Variant", "Baseline (pmol)", "Follow-up (pmol)", "Change (pmol)", "Change interval (pmol)", "Direction", "Analysis"], settings.variants.map(({id}) => {
      const v = person.variants[id]; return [id, ...order.map(visit => obsNumber(v.point.visits[visit].estimate?.total_pmol)), obsNumber(v.paired_change_pmol), obsInterval(v.conditional_interval_pmol), v.direction, v.status];
    }));
    obsTable(box, "Per-visit uncertainty and boundaries", ["Variant", "Visit", "Total interval (pmol)", "Minimum rate (pmol/min)"], settings.variants.flatMap(({id}) => order.map(visit => [id, visit, obsInterval(person.variants[id].visit_intervals_pmol[visit]), obsNumber(person.variants[id].point.visits[visit].estimate?.minimum_rate_pmol_min)])));
    obsTable(box, "All uncertainty attempts", ["Variant", "Planned", "Attempted", "Completed", "Failed", "Not attempted"], settings.variants.map(({id}) => { const v = person.variants[id]; return [id, v.planned_draws, v.attempted_draws, v.completed_draws, v.failed_draws, v.not_attempted_draws]; }));
    obsDetails(box, "Visit context and measured references", detail => {
      obsTable(detail, "Declared participant context", ["Field", "Value"], Object.entries(person.context).map(([k,v]) => [labels[k] || k, String(v)]));
      obsTable(detail, "Separate concentration references and glucose stimulus", ["Visit", "C-peptide AUC (pmol·min/L)", "Mean C-peptide (pmol/L)", "Fasting glucose (mmol/L)", "Glucose AUC (mmol·min/L)"], order.map(visit => { const r = person.references[visit]; return [visit, obsNumber(r.cpeptide_auc_pmol_min_l), obsNumber(r.mean_cpeptide_pmol_l), obsNumber(r.fasting_glucose_mmol_l), obsNumber(r.glucose_auc_mmol_min_l)]; }));
      detail.append(obsElement("p", "C-peptide AUC is a concentration reference, not secreted amount. A different glucose stimulus may accompany a secretion difference.", "field-note"));
      for (const visit of order) {
        const r = person.references[visit], m = r.metadata;
        obsTable(detail, visit + " test context", ["Field", "Declaration"], [["Challenge",m.challenge_id],["Protocol",m.protocol],["Meal",m.meal],["Medication and insulin",m.medication_context],["Assay",m.assay.id],["C-peptide LOD (nmol/L)",m.assay.cpeptide_lod_nmol_l],["C-peptide LOQ (nmol/L)",m.assay.cpeptide_loq_nmol_l]]);
        obsTable(detail, visit + " measured observations", ["Time (min)", "C-peptide (pmol/L)", "Status", "Glucose (mmol/L)", "Status"], r.times_min.map((t,i) => [obsNumber(t),obsNumber(r.cpeptide_pmol_l[i]),r.cpeptide_status[i],obsNumber(r.glucose_mmol_l[i]),r.glucose_status[i]]));
        if (r.import_errors.length) obsTable(detail, visit + " import errors", ["CSV record", "Reason"], r.import_errors.map(e => [e.row ?? "visit",e.reason]));
      }
    });
    obsDetails(box, "Every failed or unavailable attempt", detail => {
      const rows = [];
      for (const {id} of settings.variants) {
        const v = person.variants[id];
        for (const [label, attempt] of [["point",v.point],...v.draws.map(d => ["draw "+d.index,d])]) for (const visit of order) { const value = attempt.visits[visit]; if (value.status !== "completed") rows.push([id,label,visit,value.reason || value.status]); }
        if (v.not_attempted_draws) rows.push([id,v.not_attempted_draws+" draws","both",v.not_attempted_reason]);
      }
      if (rows.length) obsTable(detail, "Complete failure record", ["Variant", "Attempt", "Visit", "Reason"], rows); else detail.append(obsElement("p", "No required attempts failed. Every successful draw remains in the full JSON."));
    });
  }, Object.keys(report.people).length <= 4);
  obsDetails(target, "Full native report and identities", detail => detail.append(obsElement("pre", JSON.stringify(report,null,2), "obs-native-json")));
}

function createObservationUI(options) {
  const $ = id => document.getElementById(id.replace(/^obs-/,options.prefix+"-"));
  const api = (path,...args) => observationAPI(path.replace(/^observations/,options.api),...args);
  const readPaths = () => Object.fromEntries(options.fields.map(k=>[k,$(k==="settings"?"obs-settings-path":"obs-"+k).value]));
  const readExtras = () => Object.fromEntries(options.fields.filter(k=>!["package","csv","settings"].includes(k)).map(k=>[k,$("obs-"+k).value]));
  const applyPaths = paths => {for(const key of options.fields)$(key==="settings"?"obs-settings-path":"obs-"+key).value=paths[key]||"";};
const obsState = {configs: [], entries: [], inspected: null, config: null, entry: null,
  pending: false, refreshing: false, followJob: null, handled: new Set(), selection: 0,
  draftRevision: 0, followDraftRevision: null, reportRequest: 0, shown: null, renderedHash: null, lastCheck: 0, browseTarget: null, directory: ".", fieldError: null};
function obsNotice(message) { $("obs-notice").textContent = message; $("obs-notice").hidden = !message; }
function obsClearFieldError() {
  const field = obsState.fieldError;
  if (field) { field.removeAttribute("aria-invalid"); field.removeAttribute("aria-describedby"); document.getElementById(field.id + "-error")?.remove(); }
  obsState.fieldError = null; $("obs-form-error").hidden = true; $("obs-form-error").replaceChildren();
}
function obsFieldFailure(field, message) { const error = new Error(message); error.field = field; throw error; }
function obsShowError(error) {
  if (!error.field) { obsNotice(error.message); $("obs-notice").scrollIntoView?.({block:"center"}); return; }
  obsClearFieldError(); const field = error.field; obsState.fieldError = field;
  field.setAttribute("aria-invalid","true"); field.setAttribute("aria-describedby",field.id + "-error");
  const message = obsElement("p",error.message,"obs-field-error"); message.id = field.id + "-error"; field.parentElement.append(message);
  const summary = $("obs-form-error"); summary.hidden = false; summary.append(obsElement("p",error.message));
  const link = obsElement("button","Review this field","button subtle"); link.type = "button";
  const reveal = () => { for (let p=field.parentElement;p;p=p.parentElement) if (p.tagName === "DETAILS") p.open=true; field.focus(); field.scrollIntoView?.({block:"center"}); };
  link.addEventListener("click",reveal); summary.append(link); reveal();
}
function obsDraftSummary(settings) {
  $("obs-settings-summary").textContent = `${settings.variants.length} required assumptions · ${settings.uncertainty.draws} uncertainty draws · ${settings.visit_order.join(" → ")}. Keep these supplied settings for a first example, or open the details to change them.`;
}
function obsBusy() { return obsState.pending || !!active; }
function obsEntryRevision(entry) { return JSON.stringify([entry?.id,entry?.artifacts_sha256,entry?.verification,entry?.report_completeness]); }
function obsControls() {
  const busy = obsBusy(), inspecting = !!obsState.inspected, readyPlan = obsState.config?.ready === true;
  for (const id of ["obs-example","obs-inspect"]) $(id).disabled = busy;
  $("obs-freeze").disabled = busy || !inspecting || readyPlan;
  $("obs-run").disabled = busy || !readyPlan;
  $("obs-use-plan").disabled = busy || !obsState.configs.some(c => c.id === $("obs-saved-plan").value && c.ready);
  $("obs-edit-plan").hidden = !readyPlan; $("obs-edit-plan").disabled = busy;
  $("obs-cancel").disabled = !active?.operation?.startsWith(options.operation + "_") || active.state === "cancelling";
  $("obs-reconstruct").disabled = busy || !obsState.entry?.archive_identity;
  for (const id of ["obs-download-md","obs-download-json"]) $(id).disabled = !obsState.entry?.artifacts_sha256?.["report.json"] || ["changed_since_verification","verification_failed"].includes(obsState.entry?.verification) || active?.operation === options.operation + "_reconstruct";
  $("obs-plan-state").textContent = readyPlan ? `Plan saved · ${obsState.config.planned_people} paired ${obsState.config.planned_people===1?"test":"tests"} · ${obsState.config.settings.variants.length} required assumptions. Ready to run. Edits create a separate plan.` : inspecting ? "Ready to validate and save this plan. Your original saved plans and reports stay unchanged." : "Prepare an example or inspect your files to begin.";
}
function obsInvalidate(pathsChanged = false) {
  obsState.draftRevision++; obsState.config = null;
  obsClearFieldError(); obsNotice("");
  if (!pathsChanged && obsState.inspected) $("obs-settings-summary").textContent = "Edited draft. Review your settings, then validate and freeze a new plan before running.";
  if (pathsChanged) { obsState.inspected = null; $("obs-plan-form").hidden = true; $("obs-validation").replaceChildren(); }
  obsControls();
}
function obsValidation(value) {
  const target = $("obs-validation"); target.replaceChildren();
  const affected = value.visits.filter(v=>v.missing_or_censored || !v.valid).length;
  target.append(obsElement("p", value.valid ? `${value.visits.length} visits loaded. ${affected ? affected + (affected===1?" visit contains":" visits contain") + " missing or censored observations; results may be incomplete." : "No missing or censored observations."}` : "Input invalid. Fix the listed records and inspect again; no estimation has run.", value.valid ? "field-note" : "notice"));
  obsDetails(target,"Review every input visit",box=>obsTable(box,"Complete declared visit coverage",["Participant","Visit","Parsed rows","Missing / censored","Import"],value.visits.map(v=>[v.participant_id,v.visit_id,v.rows,v.missing_or_censored,v.valid ? "valid" : "invalid"])),!!affected);
  const errors = [...value.errors.map(e=>["package",e.row??"—",e.reason]),...value.visits.flatMap(v=>v.errors.map(e=>[v.participant_id+" / "+v.visit_id,e.row??"—",e.reason]))];
  if (errors.length) obsTable(target,"All validation failures",["Scope","CSV record","Reason"],errors);
}
function obsRenderSettings(settings) {
  obsClearFieldError(); obsDraftSummary(settings);
  const target = $("obs-variants"); target.replaceChildren();
  for (const id of ["obs-baseline","obs-followup"]) { $(id).replaceChildren(); for (const visit of settings.visit_order) { const option=obsElement("option",visit); option.value=visit; $(id).append(option); } }
  $("obs-baseline").value=settings.visit_order[0]; $("obs-followup").value=settings.visit_order[1];
  for (const [index,variant] of settings.variants.entries()) {
    const box=obsElement("fieldset",undefined,"obs-variant"); box.dataset.index=index; box.dataset.variantId=variant.id; box.append(obsElement("legend",variant.id));
    const fields=obsElement("div",undefined,"obs-fields");
    for (const [key,label,zero] of obsRateFields) { const field=obsElement("label",label), input=document.createElement("input"); input.id=options.prefix+"-variant-"+index+"-"+key; input.type="number";input.step="any";input.min=zero?"0":String(Number.MIN_VALUE);input.required=true;input.value=variant[key];input.dataset.field=key;field.append(input);fields.append(field); }
    box.append(fields); const label=obsElement("label","Reason for this assumption"), rationale=document.createElement("textarea");rationale.id=options.prefix+"-variant-"+index+"-rationale";rationale.rows=2;rationale.maxLength=4096;rationale.required=true;rationale.value=variant.rationale;rationale.dataset.field="rationale";label.append(rationale);box.append(label);target.append(box);
  }
  const n=settings.uncertainty; $("obs-draws").value=n.draws;$("obs-seed").value=n.seed;$("obs-independent-sd").value=n.independent_sd_pmol_l;$("obs-shared-sd").value=n.paired_offset_sd_pmol_l;$("obs-plan-form").hidden=false;
}
function obsReadSettings() {
  const num=(node,label,zero=false)=>{const value=Number(node.value);if(!String(node.value).trim()||!Number.isFinite(value)||(zero?value<0:value<=0))obsFieldFailure(node,label+" must be a finite number "+(zero?"of zero or more.":"greater than zero."));return value;};
  const variants=[...$("obs-variants").querySelectorAll(".obs-variant")].map(box=>{const rationale=box.querySelector('[data-field="rationale"]');if(!rationale.value.trim()||rationale.value.length>4096)obsFieldFailure(rationale,box.dataset.variantId+": explain this assumption in 1–4096 characters.");const value={id:box.dataset.variantId,rationale:rationale.value};for(const [key,label,zero]of obsRateFields)value[key]=num(box.querySelector('[data-field="'+key+'"]'),box.dataset.variantId+": "+label,zero);return value;});
  const draws=num($("obs-draws"),"Uncertainty draws"),seed=num($("obs-seed"),"Repeatability seed",true);
  if(!Number.isSafeInteger(draws)||draws<32||draws>1024)obsFieldFailure($("obs-draws"),"Choose a whole number of uncertainty draws from 32 to 1024.");
  if(!Number.isSafeInteger(seed))obsFieldFailure($("obs-seed"),"Choose a whole-number repeatability seed from 0 to 9007199254740991.");
  const order=[$("obs-baseline").value,$("obs-followup").value];if(order[0]===order[1])obsFieldFailure($("obs-followup"),"Follow-up visit must differ from the baseline visit.");
  const name=$("obs-display-name");if(name.value.length>120||/[\x00-\x1f\x7f]/.test(name.value))obsFieldFailure(name,"Use an analysis name of at most 120 characters on one line.");
  return {schema:"opent1d.observation-analysis-settings/1",visit_order:order,variants,uncertainty:{draws,seed,independent_sd_pmol_l:num($("obs-independent-sd"),"Independent measurement SD (pmol/L)"),paired_offset_sd_pmol_l:num($("obs-shared-sd"),"Shared visit offset SD (pmol/L)",true),scope:"synthetic-engineering"}};
}
async function obsInspect(event) {
  event?.preventDefault();if(obsBusy())return;obsState.pending=true;obsNotice("");obsControls();
  const revision=obsState.draftRevision;
  try {const paths=readPaths();const result=await api("observations/inspect",paths);if(revision!==obsState.draftRevision)return;obsState.inspected=result;obsState.config=null;$("obs-display-name").value=result.display_name||options.label;obsRenderSettings(result.settings);$("obs-settings-details").open=false;obsValidation(result.validation);if(options.review)options.review(result);}
  catch(error){if(revision===obsState.draftRevision){obsState.inspected=null;obsState.config=null;$("obs-plan-form").hidden=true;obsNotice(error.message);}}
  finally{obsState.pending=false;obsControls();}
}
async function obsStart(path,body={}) {
  if(obsBusy())return;obsState.pending=true;obsNotice("");obsControls();
  try{const job=await api(path,body);active=job;selected=job;obsState.followJob=job.id;updateActivity(job);await refresh();}
  catch(error){obsNotice(error.message);}finally{obsState.pending=false;obsControls();}
}
async function obsFreeze(event) {
  event.preventDefault();if(obsBusy()||!obsState.inspected)return;obsState.pending=true;obsNotice("");obsClearFieldError();obsControls();
  const revision=obsState.draftRevision;
  try {const config=await api("observations/configurations",{package:$("obs-package").value,csv:$("obs-csv").value,...readExtras(),settings:obsReadSettings(),display_name:$("obs-display-name").value.trim(),input_sha256:obsState.inspected.input_sha256});if(revision!==obsState.draftRevision)return;obsState.config=config;obsState.followDraftRevision=revision;const job=await api("observations/configurations/"+config.id+"/freeze",{});active=job;selected=job;obsState.followJob=job.id;await refresh();}
  catch(error){obsState.config=null;obsShowError(error);}finally{obsState.pending=false;obsControls();}
}
function obsLists() {
  const choice=$("obs-saved-plan"), retained=choice.value, signature=JSON.stringify(obsState.configs.map(c=>[c.id,c.ready,c.state,c.display_name]));
  if(choice.dataset.revision!==signature){choice.replaceChildren(obsElement("option","Choose a saved plan"));choice.firstChild.value="";for(const c of obsState.configs){const option=obsElement("option",mmttDisplayName(c,options.label)+" · "+new Date(c.created_at).toLocaleString()+" · "+c.state+" · "+c.id.slice(-8));option.value=c.id;option.disabled=!c.ready;choice.append(option);}choice.value=retained;choice.dataset.revision=signature;}
  const list=$("obs-analysis-list"), revision=JSON.stringify(obsState.entries.map(e=>[e.id,e.state,e.verification,e.report_completeness,e.display_name]));
  if(list.dataset.revision!==revision){list.replaceChildren();if(!obsState.entries.length)list.append(obsElement("p","No analyses have run in this workspace.","quiet"));for(const entry of obsState.entries){const button=obsElement("button",undefined,"obs-analysis-row");button.type="button";button.dataset.entryId=entry.id;button.append(obsElement("strong",mmttDisplayName(entry,options.label) + " · "+new Date(entry.created_at).toLocaleString()),obsElement("small",mmttExecutionLabel(entry)+" · "+mmttVerificationLabel(entry.verification)));button.addEventListener("click",async()=>{await selectID(entry.id);if(obsState.entry?.id!==entry.id||document.getElementById(options.view+"-panel")?.hidden)return;$("obs-result-title").focus({preventScroll:true});$("obs-result-panel").scrollIntoView?.({block:"start"});});list.append(button);}list.dataset.revision=revision;}
  for(const button of list.querySelectorAll("button"))button.setAttribute("aria-current",String(button.dataset.entryId===obsState.entry?.id));
}
function selectID(ident, follow = false) {
  if(!follow)obsState.followJob=null;
  const entry=obsState.entries.find(e=>e.id===ident);if(!entry)return;
  const changed=obsState.entry?.id!==entry.id;obsState.entry=entry;
  if(changed){obsState.selection++;obsState.shown=null;obsState.renderedHash=null;$("obs-report").replaceChildren();}
  obsLists();obsControls();return obsShowReport();
}
function obsShowReport() {
  const key=obsState.selection+":"+obsEntryRevision(obsState.entry);
  if(obsState.reportFlight?.key===key)return obsState.reportFlight.promise;
  const flight={key,promise:null};obsState.reportFlight=flight;
  flight.promise=obsFetchReport().finally(()=>{if(obsState.reportFlight===flight)obsState.reportFlight=null;});
  return flight.promise;
}
async function obsFetchReport() {
  const entry=obsState.entry;$("obs-result-panel").hidden=!entry;if(!entry)return;
  $("obs-execution").textContent=mmttExecutionLabel(entry);
  $("obs-result-detail").textContent=mmttDisplayName(entry,options.label)+" · Saved plan "+entry.configuration_id.slice(-8)+" · "+new Date(entry.created_at).toLocaleString()+" · "+mmttVerificationLabel(entry.verification)+". Draft edits do not change this report. Display checks report bytes; other source bytes are checked by Check saved analysis.";
  if(["changed_since_verification","verification_failed"].includes(entry.verification)){obsState.shown=null;obsState.renderedHash=null;$("obs-report").replaceChildren(obsElement("p","Saved evidence verification failed or bytes changed. Restore unchanged evidence and check saved analysis.","notice"));return;}
  if(!entry.artifacts_sha256?.["report.json"]){obsState.shown=null;obsState.renderedHash=null;$("obs-report").replaceChildren(obsElement("p",entry.error||"No sealed report is available yet.","field-note"));return;}
  const revision=obsEntryRevision(entry),selection=obsState.selection;
  if(obsState.shown===revision&&Date.now()-obsState.lastCheck<5000)return;
  const request=++obsState.reportRequest;
  try{const wrapper=await api("observations/entries/"+entry.id+"/report");if(request!==obsState.reportRequest||selection!==obsState.selection||obsState.entry?.id!==entry.id||obsEntryRevision(obsState.entry)!==revision)return;
    if(wrapper.task!==options.task||wrapper.report_sha256!==entry.artifacts_sha256["report.json"]||wrapper.verification!==entry.verification||wrapper.report_completeness!==entry.report_completeness)throw new Error("The report snapshot differs from the selected paired analysis.");
    const content=entry.id+":"+wrapper.report_sha256;if(obsState.renderedHash!==content){options.render(wrapper.native_report,$("obs-report"));obsState.renderedHash=content;}obsState.shown=revision;obsState.lastCheck=Date.now();
  }catch(error){if(selection===obsState.selection&&obsEntryRevision(obsState.entry)===revision){$("obs-report").replaceChildren();obsState.shown=null;obsState.renderedHash=null;obsNotice(error.message);}}
}
function refreshLocal() {
  if(!obsState.refreshPromise)obsState.refreshPromise=obsRefreshOnce().finally(()=>{obsState.refreshPromise=null;});
  return obsState.refreshPromise;
}
async function obsRefreshOnce() {
  obsState.refreshing=true;
  try{const data=await api("observations/bootstrap");obsState.configs=data.configurations;obsState.entries=data.entries;
    if(!$("obs-case").children.length)for(const value of data.cases){const option=obsElement("option",options.cases[value]||value);option.value=value;$("obs-case").append(option);}
    if(obsState.entry)obsState.entry=obsState.entries.find(e=>e.id===obsState.entry.id)||obsState.entry;
    const job=jobs.find(j=>j.id===obsState.followJob);
    if(job && job.task===options.task){if(job[options.operation + "_entry_id"]&&obsState.entry?.id!==job[options.operation + "_entry_id"])selectID(job[options.operation + "_entry_id"],true);
      if(!activeStates.has(job.state)&&!obsState.handled.has(job.id)){obsState.handled.add(job.id);
        if(job.operation===options.operation + "_example"&&job.result?.input_paths){const paths=job.result.input_paths;applyPaths(paths);obsState.pending=false;await obsInspect();}
        if(job.operation===options.operation + "_freeze"&&obsState.followDraftRevision===obsState.draftRevision){obsState.config=obsState.configs.find(c=>c.id===job[options.operation + "_configuration_id"])||null;if(obsState.config){obsValidation(obsState.config.validation);if(!obsState.config.ready)obsNotice(obsState.config.error);}}
        const completedEntry=(job.result?.observation_entry||job.result?.sampling_entry)?.state==="completed";
        if(job.operation===options.operation + "_run"&&completedEntry&&job.result?.report_completeness==="incomplete")obsNotice("Analysis finished with incomplete results. Open the saved report to see every failure. Incomplete results do not establish absence of change.");
        if(job.state==="failed"&&!completedEntry)obsNotice(job.error||job.result?.entry_error||"Operation failed; available evidence is retained.");
      }
    }
    obsLists();await obsShowReport();obsControls();
  }catch(error){obsNotice(error.message);}finally{obsState.refreshing=false;}
}
async function obsDownload(name) {
  const entry=obsState.entry;if(!entry)return;
  const selection=obsState.selection,revision=obsEntryRevision(entry);
  try {
    const blob=await api("observations/entries/"+entry.id+"/artifacts/"+name,undefined,true);
    if(selection!==obsState.selection||obsEntryRevision(obsState.entry)!==revision)return;
    const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  } catch(error) {
    if(selection===obsState.selection&&obsEntryRevision(obsState.entry)===revision){obsState.shown=null;obsState.renderedHash=null;$("obs-report").replaceChildren();obsNotice(error.message);}
  }
}
async function obsBrowse(directory="."){
  try{const data=await api("observations/files?directory="+encodeURIComponent(directory));obsState.directory=data.directory||".";$("obs-file-directory").textContent=obsState.directory;$("obs-file-up").disabled=obsState.directory===".";$("obs-file-list").replaceChildren();
    for(const item of data.items){if(!item.directory&&!item.name.endsWith(obsState.browseTarget==="csv"?".csv":".json"))continue;const button=obsElement("button",(item.directory?"▸ ":"")+item.name,"file-entry");button.type="button";button.addEventListener("click",()=>{if(item.directory)obsBrowse(item.path);else{$(obsState.browseTarget==="settings"?"obs-settings-path":"obs-"+obsState.browseTarget).value=item.path;obsInvalidate(true);$("obs-file-dialog").close();}});$("obs-file-list").append(button);}
  }catch(error){obsNotice(error.message);}
}
document.getElementById(options.open).addEventListener("click",()=>workspaceNavigate(options.view));
$("obs-example").addEventListener("click",()=>obsStart("observations/example",{case:$("obs-case").value}));
$("obs-input-form").addEventListener("submit",obsInspect);$("obs-plan-form").addEventListener("submit",obsFreeze);
$("obs-plan-form").addEventListener("input",()=>obsInvalidate());
for(const id of options.fields.map(k=>k==="settings"?"obs-settings-path":"obs-"+k))$(id).addEventListener("input",()=>obsInvalidate(true));
$("obs-run").addEventListener("click",()=>{if(obsState.config)obsStart("observations/configurations/"+obsState.config.id+"/run");});
$("obs-cancel").addEventListener("click",async()=>{if(active?.operation?.startsWith(options.operation + "_")){try{await api("jobs/"+active.id+"/cancel",{});await refresh();}catch(error){obsNotice(error.message);}}});
$("obs-reconstruct").addEventListener("click",()=>{if(obsState.entry)obsStart("observations/entries/"+obsState.entry.id+"/reconstruct");});
$("obs-download-md").addEventListener("click",()=>obsDownload("report.md"));$("obs-download-json").addEventListener("click",()=>obsDownload("report.json"));
$("obs-saved-plan").addEventListener("change",obsControls);
$("obs-use-plan").addEventListener("click",()=>{
  const c=obsState.configs.find(v=>v.id===$("obs-saved-plan").value);if(!c?.ready||obsBusy())return;
  obsState.draftRevision++;obsNotice("");obsState.config=c;
  const hashes={"package.json":c.inputs_sha256?.["package.json"],"observations.csv":c.inputs_sha256?.["observations.csv"]};
  if(options.fields.includes("design"))hashes["design.json"]=c.inputs_sha256?.["design.json"];
  if(options.fields.includes("development_import"))hashes.development_import=c.development_identity;
  obsState.inspected={input_sha256:hashes,validation:c.validation,settings:c.settings};
  applyPaths(c.input_paths||c.source_paths);$("obs-display-name").value=mmttDisplayName(c,options.label);
  if(options.review)options.review(c);obsRenderSettings(c.settings);$("obs-settings-details").open=false;obsValidation(c.validation);obsControls();
});
$("obs-edit-plan").addEventListener("click",()=>{if(!obsState.config?.ready||obsBusy())return;obsInvalidate();$("obs-settings-details").open=true;$("obs-display-name").focus();});
document.querySelectorAll("[data-"+options.prefix+"-browse]").forEach(button=>button.addEventListener("click",()=>{obsState.browseTarget=button.dataset[options.prefix+"Browse"];$("obs-file-dialog").showModal();obsBrowse(".");}));
$("obs-file-close").addEventListener("click",()=>$("obs-file-dialog").close());
$("obs-file-up").addEventListener("click",()=>{const parts=obsState.directory.split("/");parts.pop();obsBrowse(parts.join("/")||".");});
refreshLocal();

return {state:obsState,refresh:refreshLocal,select:selectID,controls:obsControls,invalidate:obsInvalidate,show:obsShowReport,download:obsDownload,inspect:obsInspect,lists:obsLists};
}
const observationAPI = api;
const observationUI=createObservationUI({prefix:"obs",api:"observations",view:"observations",open:"open-observations",operation:"observation",task:"mmtt-sensitivity",label:"Paired analysis",fields:["package","csv","settings"],cases:{increase:"Consistent increase control","assumption-dependent":"Assumption-dependent control",unresolved:"Unresolved change control",censored:"Censored observation control"},render:renderObservationReport});
const obsState=observationUI.state;
function refreshObservations(){return observationUI.refresh();}
function selectObservationID(id){return observationUI.select(id);}

function obsControls(){return observationUI.controls();}
function obsInvalidate(value){return observationUI.invalidate(value);}
function obsShowReport(){return observationUI.show();}
function obsDownload(name){return observationUI.download(name);}
function obsInspect(){return observationUI.inspect();}
function obsLists(){return observationUI.lists();}
