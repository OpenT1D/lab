// Exercise shipped draft persistence with a tab store and editable form boundary.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync("experiments/gui/static/draft.js", "utf8");
const defaults = {schema: "opent1d.m4.study/1", sources: [{id: "first", model: "one.py", declaration: "one.json"}, {id: "second", model: "two.py", declaration: "two.json"}], scenarios: ["fasting", "gastric_load_15g", "gastric_load_30g"], timeout_seconds: 600, source_timeout_seconds: 3600};
function harness(store = new Map(), scope = "a".repeat(64), denied = false) {
  const nodes = new Map(), events = new Map(), scenarios = defaults.scenarios.map(value => ({value, checked: true}));
  const $ = id => { if (!nodes.has(id)) nodes.set(id, {children: [], value: "", textContent: "", hidden: false, replaceChildren() { this.children = []; }, addEventListener(name, callback) { this[name] = callback; }}); return nodes.get(id); };
  const context = vm.createContext({$, session: {defaults: structuredClone(defaults), draft_scope: scope}, ready: true, configuration: {id: "old-frozen"},
    document: {querySelectorAll: () => scenarios}, window: {addEventListener: (name, callback) => events.set(name, callback)},
    sessionStorage: {getItem(key) { if (denied) throw Error("denied"); return store.get(key) ?? null; }, setItem(key, value) { if (denied) throw Error("denied"); store.set(key, value); }, removeItem(key) { if (denied) throw Error("denied"); store.delete(key); }},
    sourceCard(item) { $("sources").children.push(structuredClone(item)); }, numberSources() {},
    invalidate() { context.ready = false; context.configuration = null; vm.runInContext("persistStudyDraft()", context); },
    formConfig() { return {schema: defaults.schema, sources: $("sources").children, scenarios: scenarios.filter(item => item.checked).map(item => item.value), timeout_seconds: Number($("stage-budget").value), source_timeout_seconds: Number($("source-budget").value)}; },
  });
  $("sources").children = structuredClone(defaults.sources); $("stage-budget").value = 600; $("source-budget").value = 3600;
  vm.runInContext(source, context); const run = code => vm.runInContext(code, context);
  run("initializeStudyDraft()"); return {$, context, scenarios, events, run};
}
const store = new Map(), first = harness(store);
first.$("sources").children[0].id = "edited_model"; first.scenarios[2].checked = false; first.$("stage-budget").value = 321;
first.run("persistStudyDraft()");
assert.equal(store.size, 1); assert.match(first.$("study-draft-note").textContent, /Draft saved/);
const restored = harness(store);
assert.equal(restored.$("sources").children[0].id, "edited_model"); assert.equal(restored.scenarios[2].checked, false); assert.equal(restored.$("stage-budget").value, 321);
assert.equal(restored.context.ready, false); assert.equal(restored.context.configuration, null); assert.match(restored.$("study-draft-note").textContent, /Check setup again/);
assert.equal(harness(store, "b".repeat(64)).$("sources").children[0].id, "first", "Workspace scope isolates input restoration");
restored.$("reset-study-draft").click(); assert.equal(store.size, 0); assert.equal(restored.$("sources").children[0].id, "first"); assert.equal(restored.context.ready, false);
const raw = JSON.stringify({schema: "opent1d.m4-draft/1", configuration: defaults});
for (const invalid of ["{", "x".repeat(65537), JSON.stringify({...JSON.parse(raw), ready: true}), raw.replace('"fasting"', '"arbitrary"'), raw.replace('"timeout_seconds":600', '"timeout_seconds":1e99')]) {
  restored.context.raw = invalid; assert.throws(() => restored.run("validateStudyDraft(raw)"));
}
store.set("opent1d.m4-draft/1:" + "a".repeat(64), "{"); const malformed = harness(store);
assert.equal(malformed.$("sources").children[0].id, "first"); assert.match(malformed.$("study-draft-note").textContent, /could not be restored/);
const denied = harness(new Map(), "a".repeat(64), true); denied.run("persistStudyDraft()");
assert.match(denied.$("study-draft-note").textContent, /could not be saved/);
let prevented = false; const event = {preventDefault() { prevented = true; }}; denied.events.get("beforeunload")(event); assert(prevented); assert.equal(event.returnValue, "");
let savedPrevented = false; first.events.get("beforeunload")({preventDefault() { savedPrevented = true; }}); assert.equal(savedPrevented, false);
process.stdout.write(JSON.stringify({passed: true, scope: "draft reload, isolation, reset, bounded untrusted inputs, readiness invalidation and denied storage"}));
