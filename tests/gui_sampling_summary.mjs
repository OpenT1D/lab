// Native Python reports are the input; these checks exercise the shipped renderer.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const reports = JSON.parse(fs.readFileSync(0, "utf8"));
const common = fs.readFileSync("experiments/gui/static/observations.js", "utf8").split("function createObservationUI(")[0];
const sampling = fs.readFileSync("experiments/gui/static/sampling.js", "utf8");
function node(tag = "div") {
  return {tag, children: [], textContent: "", events: {},
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; this.textContent = ""; },
    addEventListener(event, fn) { this.events[event] = fn; },
    setAttribute(key, value) { this[key] = value; },
    set innerHTML(value) { throw new Error("Unsafe HTML assignment: " + value); },
  };
}
const text = el => [el.textContent, ...el.children.map(text)].join(" ");
const descendants = el => [el, ...el.children.flatMap(descendants)];
function render(report) {
  const target = node(), context = vm.createContext({report, target,
    document: {createElement: node}, createObservationUI() { return {}; },
  });
  vm.runInContext(common + "\n" + sampling, context);
  vm.runInContext("renderSamplingReport(report,target)", context);
  return {target, context};
}

for (const [name, report] of Object.entries(reports)) {
  const original = JSON.stringify(report), {target} = render(report);
  const summary = target.children.find(el => el.className === "sampling-summary");
  assert(summary, name);
  const visible = text(summary);
  assert(visible.includes("Development examples · 2 participants"));
  assert(visible.includes("Evaluation examples · 3 participants"));
  assert(visible.includes("same people appear under each assumption"));
  assert(visible.includes("not independent samples"));
  assert(visible.includes("Matching direction does not establish agreement"));
  const tables = descendants(summary).filter(el => el.tag === "table");
  assert.equal(tables.length, 2);
  for (const table of tables) {
    const body = table.children.find(el => el.tag === "tbody");
    assert.equal(body.children.length, 4, "Full reference plus all three frozen subsets");
    assert(text(body.children[0]).includes("Full reference"));
    assert(text(body.children[1]).includes("5 measurement times"));
    assert(text(body.children[2]).includes("4 measurement times"));
    assert(text(body.children[3]).includes("3 measurement times"));
  }
  if (name === "information-loss") {
    assert(visible.includes("Direction reversals occur with 3 measurement times (three-times)"));
    assert(text(tables[0]).includes("nominal: 0/2 same direction; 2/2 reversed; 0/2 unresolved; 0/2 unavailable"));
    assert(text(tables[1]).includes("nominal: 0/3 same direction; 3/3 reversed; 0/3 unresolved; 0/3 unavailable"));
    assert(!visible.includes("9/9"), "Assumption variants must not inflate the participant count");
  } else if (name === "constant") {
    assert(visible.includes("All planned paired comparisons keep the same resolved direction"));
    assert(text(tables[1]).includes("nominal: 3/3 same direction; 0/3 reversed; 0/3 unresolved; 0/3 unavailable"));
  } else if (name === "unresolved") {
    assert(visible.includes("Some comparisons cannot determine whether the direction is preserved"));
    assert(text(tables[1]).includes("nominal: 0/3 same direction; 0/3 reversed; 3/3 unresolved; 0/3 unavailable"));
    assert(!visible.includes("All planned paired comparisons keep"));
  } else {
    assert(visible.includes("Some other comparisons are unresolved or unavailable"));
    assert(text(tables[1]).includes("2/3 unavailable"));
    assert(text(target).includes("Calculation incomplete"));
  }
  const details = target.children.filter(el => el.tag === "details");
  assert(details.length > 5);
  assert(details.every(el => !el.open), "Technical tables start collapsed");
  assert(!text(target).includes("attempted draw pairs"));
  function expand(el) {
    if (el.tag === "details") { el.open = true; el.events.toggle(); }
    for (const child of el.children) expand(child);
  }
  expand(target);
  const full = text(target);
  assert(full.includes("Execution and all planned denominators"));
  assert(full.includes("Absolute and signed endpoint differences"));
  assert(full.includes("Every planned paired comparison"));
  assert(full.includes("Conditional paired-direction comparison"));
  assert(full.includes("C-peptide AUC remains a concentration reference"));
  if (name === "incomplete") assert(full.includes("below_loq"));
  assert.equal(JSON.stringify(report), original, "Presentation must not mutate the native report");
}

for (const mutate of [
  r => { r.comparisons.evaluation["three-times"].nominal.directions.direction_reversal = -1; },
  r => { r.comparisons.evaluation["three-times"].nominal.directions.planned_count = 9; },
  r => { r.comparisons.evaluation["three-times"].nominal.directions.rows[0].status = "same_resolved_direction"; },
  r => { delete r.comparisons.evaluation["three-times"].nominal; },
  r => { delete r.comparisons.evaluation; },
]) {
  const broken = structuredClone(reports["information-loss"]); mutate(broken);
  assert.throws(() => render(broken), /accounting/);
}
process.stdout.write(JSON.stringify({passed: true, scope: "Native sampling conclusions, separate allocations and assumptions, complete failure details, and rejected malformed summary counts"}));
