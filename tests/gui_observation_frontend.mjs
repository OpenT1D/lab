// Native calculations are supplied by Python; this harness exercises shipped presentation code.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const reports = JSON.parse(fs.readFileSync(0, "utf8"));
const source = fs.readFileSync("experiments/gui/static/observations.js", "utf8");
const uxSource = fs.readFileSync("experiments/gui/static/ux.js", "utf8");
function harness() {
  const nodes = new Map(), pending = [], downloads = [];
  function element(name = "div") {
    return {name, tagName: name.toUpperCase(), textContent: "", children: [], dataset: {}, value: "", hidden: false, disabled: false, events: {},
      set innerHTML(value) { throw new Error("Unsafe HTML assignment: " + value); },
      get firstChild() { return this.children[0]; },
      replaceChildren(...items) { this.children = []; this.textContent = ""; this.append(...items); },
      append(...items) { this.children.push(...items); for (const item of items) item.parentElement = this; },
      addEventListener(event, fn) { this.events[event] = fn; },
      setAttribute(name, value) { this[name] = value; },
      removeAttribute(name) { delete this[name]; },
      remove() { if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this); },
      focus() { context.document.activeElement = this; },
      scrollIntoView() { this.scrolled = true; },
      querySelectorAll(selector) { return this.children.flatMap(child => [child, ...child.querySelectorAll(selector)]).filter(child => selector.startsWith('[data-field=') ? child.dataset.field === selector.slice(13,-2) : selector === ".obs-variant" ? child.className === "obs-variant" : child.name === selector); },
      querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
      click() { downloads.push(this.download); },
    };
  }
  const $ = id => {
    for (const root of nodes.values()) { const found=[root,...root.querySelectorAll("input"),...root.querySelectorAll("p"),...root.querySelectorAll("textarea")].find(n=>n.id===id); if(found)return found; }
    if (!nodes.has(id)) { const node=element(); node.id=id; nodes.set(id,node); } return nodes.get(id);
  };
  const context = vm.createContext({$, Date, active: null, selected: null, jobs: [], activeStates: new Set(["queued", "running", "cancelling"]),
    document: {createElement: element,getElementById:$,querySelectorAll:()=>[]}, URL: {createObjectURL: () => "blob:test", revokeObjectURL() {}}, setTimeout() {},
    updateActivity() {}, refresh: async () => {}, labels: {},
    api(path, body) { return new Promise((resolve, reject) => pending.push({path, body, resolve, reject})); },
  });
  vm.runInContext(uxSource, context); vm.runInContext(source, context);
  const run = code => vm.runInContext(code, context);
  const text = node => [node.textContent, ...node.children.map(text)].join(" ");
  function reply(path, value, fail = false) { const index = pending.findIndex(p => p.path === path); assert(index >= 0, path); const p = pending.splice(index, 1)[0]; (fail ? p.reject : p.resolve)(value); }
  function choose(id, verification = "not_requested") {
    context.entry = {id, configuration_id: "plan-" + id, created_at: "2026-10-18T10:00:00Z", verification, state: "completed", report_completeness: "complete", artifacts_sha256: {"report.json": "native"}};
    run("obsState.entry=entry;obsState.selection++;obsState.shown=null");
    return run("obsShowReport()");
  }
  const wrapper = (report, verification = "not_requested") => ({task: "mmtt-sensitivity", report_sha256: "native", verification, report_completeness: "complete", native_report: report});
  return {$, context, pending, downloads, run, text, reply, choose, wrapper};
}
const labels = {increase: "consistent within investigated assumptions", "assumption-dependent": "assumption-dependent", unresolved: "insufficiently determined", censored: "insufficiently determined"};
for (const [name, report] of Object.entries(reports)) {
  const h = harness(), original = JSON.stringify(report);
  h.context.report = report; h.run('renderObservationReport(report,$("result"))');
  function expand(node) { if (node.name === "details") { node.open = true; node.events.toggle(); } for (const child of node.children) expand(child); }
  expand(h.$("result"));
  const text = h.text(h.$("result"));
  assert(text.includes(labels[name])); assert(text.includes("not secreted amount"));
  assert(text.includes("Medication and insulin")); assert(text.includes("C-peptide LOQ"));
  assert(text.includes("128")); assert(text.includes("zero is unresolved"));
  if (name === "increase") { assert(text.includes("5722.08")); assert(text.includes("2861.04")); assert(text.includes("24000")); assert(text.includes("660")); }
  if (name === "censored") { assert(text.includes("below_loq")); assert(text.includes("unavailable")); assert(text.includes("Complete failure record")); }
  assert.equal(JSON.stringify(report), original);
  const invalid = structuredClone(report); invalid.people["invented-01"].variants.nominal.attempted_draws++;
  h.context.invalid = invalid; assert.throws(() => h.run("obsValidateNative(invalid)"), /accounting/);
}
{
  const h = harness(), r = structuredClone(reports.increase), malicious = '<img src=x onerror="alert(1)">';
  r.people[malicious] = r.people["invented-01"]; delete r.people["invented-01"];
  h.context.report = r; h.run('renderObservationReport(report,$("result"))');
  assert(h.text(h.$("result")).includes(malicious));
  h.run('obsState.inspected={};obsState.config={ready:true,planned_people:1,settings:{variants:[{},{}]}};obsControls()'); assert.equal(h.$("obs-run").disabled, false);
  h.run("obsInvalidate()"); assert.equal(h.$("obs-run").disabled, true);
  h.run('obsInvalidate(true)'); assert.equal(h.run("obsState.inspected"), null);
}
{
  const h = harness(), first = h.choose("first"), second = h.choose("second");
  h.reply("observations/entries/second/report", h.wrapper(reports.increase)); await second;
  const children = h.$("obs-report").children;
  h.reply("observations/entries/first/report", h.wrapper(reports.censored)); await first;
  assert.equal(h.$("obs-report").children, children); assert.equal(h.run("obsState.entry.id"), "second");
  const download = h.run("obsDownload('report.json')");
  h.run("obsState.selection++"); h.reply("observations/entries/second/artifacts/report.json", {}); await download;
  assert.deepEqual(h.downloads, []);
}
{
  const h = harness(), first = h.choose("first");
  h.reply("observations/entries/first/report", h.wrapper(reports.increase)); await first;
  const retained = h.$("obs-report").children;
  h.run("obsState.entry.verification='native_reader_verified'"); const checked = h.run("obsShowReport()");
  h.reply("observations/entries/first/report", h.wrapper(reports.increase, "native_reader_verified")); await checked;
  assert.equal(h.$("obs-report").children, retained);
  h.run("obsState.entry.verification='changed_since_verification';obsShowReport()");
  assert(h.text(h.$("obs-report")).includes("bytes changed"));
  h.run("obsState.entry.verification='native_reader_verified'"); const restored = h.run("obsShowReport()");
  h.reply("observations/entries/first/report", h.wrapper(reports.increase, "native_reader_verified")); await restored;
  assert(h.text(h.$("obs-report")).includes("5722.08"));
}
{
  const h = harness(); const inspection = h.run("obsInspect()");
  h.run("obsInvalidate(true)"); h.reply("observations/inspect", {}); await inspection;
  assert.equal(h.run("obsState.inspected"), null);
  h.context.active = {operation: "m3_run", state: "running"}; h.run("obsControls()");
  assert(h.$("obs-example").disabled); assert(h.$("obs-cancel").disabled);
}
{
  const h = harness(); h.context.entries = [
    {id:"old",configuration_id:"plan-old",created_at:"2026-10-18T10:00:00Z",verification:"not_requested",state:"completed",report_completeness:"complete",artifacts_sha256:{"report.json":"native"}},
    {id:"chosen",configuration_id:"plan-chosen",created_at:"2026-10-18T10:00:00Z",verification:"not_requested",state:"completed",report_completeness:"complete",artifacts_sha256:{"report.json":"native"}},
  ];
  h.run("obsState.entries=entries;obsState.followJob='finished';selectObservationID('chosen')");
  assert.equal(h.run("obsState.followJob"), null);
  h.reply("observations/entries/chosen/report", h.wrapper(reports.increase));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.run("obsState.entry.id"), "chosen");
}
// Polling cannot supersede a pending selection render and let navigation scroll early.
{
  const h=harness(), first=h.choose("waiting");
  h.run("obsState.entries=[entry]");
  const selected=h.run("selectObservationID('waiting')"), poll=h.run("obsShowReport()");
  assert.equal(selected,poll);
  assert.equal(h.pending.filter(p=>p.path==="observations/entries/waiting/report").length,1);
  let resolved=false;selected.then(()=>{resolved=true;});
  await new Promise(resolve=>setImmediate(resolve));assert.equal(resolved,false);
  h.reply("observations/entries/waiting/report",h.wrapper(reports.increase));
  await Promise.all([first,selected,poll]);assert.equal(resolved,true);
  assert(h.text(h.$("obs-report")).includes("5722.08"));
}
// A saved plan can be changed without inspecting again or losing the edited fields.
// Exercise the shipped controller for both tasks, including the sampling input identities.
for (const prefix of ["obs","sam"]) {
  const h=harness();
  if(prefix==="sam")h.run('globalThis.sampleUI=createObservationUI({prefix:"sam",api:"sampling",operation:"sampling",task:"mmtt-sampling",open:"open-sampling",label:"Sampling comparison",fields:["package","csv","settings","design","development_import"],cases:{},render(){}})');
  const state=prefix==="obs"?"obsState":"sampleUI.state",route=prefix==="obs"?"observations":"sampling";
  const settings=structuredClone(reports.increase.plan.settings);
  h.context.config={id:"original",display_name:"Saved example",ready:true,state:"ready",planned_people:1,created_at:"2026-10-19T10:00:00Z",settings,validation:{valid:true,errors:[],visits:[]},input_paths:{package:"saved/package.json",csv:"saved/observations.csv",settings:"saved/settings.json",design:"saved/design.json",development_import:"saved/development"},inputs_sha256:{"package.json":"p","observations.csv":"c","design.json":"d"},development_identity:{"manifest.json":"development"}};
  const original=JSON.stringify(h.context.config);
  h.run(state+".configs=[config]");h.$(prefix+"-saved-plan").value="original";
  h.$(prefix+"-use-plan").events.click();
  assert.equal(h.$(prefix+"-run").disabled,false);
  assert.equal(h.$(prefix+"-settings-details").open,false);
  h.$(prefix+"-edit-plan").events.click();
  assert.equal(h.$(prefix+"-freeze").disabled,false);
  assert.equal(h.$(prefix+"-run").disabled,true);
  const volume=h.$(prefix+"-variants").querySelector('[data-field="volume_l"]');
  volume.value="5";
  h.$(prefix+"-display-name").value="Changed volume";
  h.$(prefix+"-plan-form").events.input();
  const freeze=h.$(prefix+"-plan-form").events.submit({preventDefault(){}});
  const request=h.pending.find(p=>p.path===route+"/configurations");
  assert.equal(request.body.settings.variants[0].volume_l,5);
  assert.equal(request.body.display_name,"Changed volume");
  assert.equal(request.body.input_sha256["package.json"],"p");
  if(prefix==="sam"){assert.equal(request.body.input_sha256["design.json"],"d");assert.equal(request.body.input_sha256.development_import["manifest.json"],"development");}
  assert.equal(JSON.stringify(h.context.config),original);
  assert(!h.pending.some(p=>p.path===route+"/inspect"));
  h.reply(route+"/configurations",{id:"new-plan"});await new Promise(resolve=>setImmediate(resolve));
  h.reply(route+"/configurations/new-plan/freeze",{id:"freeze-new",state:"running"});await freeze;
}
// Navigation can await an existing refresh, and incomplete native results retain
// their explanation even when the worker exits nonzero. Real failures remain failures.
for (const prefix of ["obs","sam"]) {
  const h=harness(), route=prefix==="obs"?"observations":"sampling", operation=prefix==="obs"?"observation":"sampling", task=prefix==="obs"?"mmtt-sensitivity":"mmtt-sampling";
  if(prefix==="sam")h.run('globalThis.sampleUI=createObservationUI({prefix:"sam",api:"sampling",operation:"sampling",task:"mmtt-sampling",open:"open-sampling",label:"Sampling comparison",fields:["package","csv","settings","design","development_import"],cases:{},render(){}})');
  const ui=prefix==="obs"?"observationUI":"sampleUI";
  assert(h.run(ui+".refresh()==="+ui+".refresh()"));
  const first=h.run(ui+".refresh()");h.reply(route+"/bootstrap",{configurations:[],entries:[],cases:[]});await first;
  h.context.jobs=[{id:"incomplete",task,operation:operation+"_run",state:"failed",result:{report_completeness:"incomplete",observation_entry:{state:"completed"}}}];
  h.run(ui+".state.followJob='incomplete'");
  const incomplete=h.run(ui+".refresh()");h.reply(route+"/bootstrap",{configurations:[],entries:[],cases:[]});await incomplete;
  assert(h.$(prefix+"-notice").textContent.startsWith("Analysis finished with incomplete results."));
  h.context.jobs=[{id:"failed",task,operation:operation+"_run",state:"failed",error:"Worker stopped unexpectedly",result:{report_completeness:"incomplete",observation_entry:{state:"failed"}}}];
  h.run(ui+".state.followJob='failed'");
  const failed=h.run(ui+".refresh()");h.reply(route+"/bootstrap",{configurations:[],entries:[],cases:[]});await failed;
  assert.equal(h.$(prefix+"-notice").textContent,"Worker stopped unexpectedly");
}
// A hidden invalid field opens its details and receives focus plus a specific error.
{
  const h=harness();h.context.settings=structuredClone(reports.increase.plan.settings);
  h.$("obs-settings-details").tagName="DETAILS";h.$("obs-settings-details").append(h.$("obs-variants"));
  const inspection=h.run("obsInspect()");h.reply("observations/inspect",{settings:h.context.settings,input_sha256:{"package.json":"p","observations.csv":"c"},validation:{valid:true,errors:[],visits:[]}});await inspection;
  const volume=h.$("obs-variants").querySelector('[data-field="volume_l"]');volume.value="0";
  await h.$("obs-plan-form").events.submit({preventDefault(){}});
  assert.equal(h.context.document.activeElement,volume);assert.equal(volume["aria-invalid"],"true");
  assert.equal(h.$("obs-settings-details").open,true);
  assert(h.text(h.$("obs-form-error")).includes("nominal: Whole-body volume (L) must be a finite number greater than zero."));
  assert(!h.pending.some(p=>p.path==="observations/configurations"));
  volume.value="5";h.$("obs-plan-form").events.input();
  assert.equal(volume["aria-invalid"],undefined);assert.equal(h.$("obs-form-error").hidden,true);
  assert.equal(h.$("obs-freeze").disabled,false);
}
process.stdout.write(JSON.stringify({passed: true, scope: "Native display, escaping, saved-plan edits, field error recovery, readiness, retained details, stale responses and download selection; controlled DOM only"}));
