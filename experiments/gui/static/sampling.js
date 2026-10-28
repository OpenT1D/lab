"use strict";

function samplingValidateNative(report){
  const fail=()=>{throw new Error("Incompatible native sampling report or incomplete accounting.");};
  if(!report||report.schema!=="opent1d.mmtt-sampling/1"||report.task!=="mmtt-sampling"||report.kind!=="synthetic"||report.human_evaluation!==false||!report.coverage||typeof report.coverage.complete_cohort!=="boolean"||report.plan?.schema!=="opent1d.mmtt-sampling-plan/1"||report.plan.human_execution_authorized!==false)fail();
  const d=report.plan.design,s=report.plan.settings,c=report.coverage;
  if(!d?.allocation||!d.subsets||!Array.isArray(s?.variants)||!report.schedules)fail();
  const people=Object.keys(d.allocation).length,schemes=Object.keys(d.subsets).length+1,pairs=people*s.variants.length*schemes;
  if(c.planned_schedules!==schemes||c.planned_people!==people||c.planned_variant_pairs!==pairs||c.planned_visit_points!==2*pairs||c.planned_draw_pairs!==pairs*s.uncertainty.draws||Object.keys(report.schedules).length!==schemes)fail();
  for(const [suffix,planned]of [["pair_points",pairs],["visit_points",2*pairs],["draw_pairs",c.planned_draw_pairs]]){
    const counts=["completed","failed","not_attempted","unavailable"].map(k=>c[k+"_"+suffix]);
    if(counts.some(n=>!Number.isSafeInteger(n)||n<0)||counts.reduce((a,b)=>a+b,0)!==planned)fail();
  }
  for(const value of Object.values(report.schedules))if(value.report)obsValidateNative(value.report);
  if(!Array.isArray(report.paired_comparisons)||report.paired_comparisons.length!==(schemes-1)*people*s.variants.length||!Array.isArray(report.visit_comparisons)||report.visit_comparisons.length!==2*report.paired_comparisons.length)fail();
  // Summary labels use the native classifications, never refit or classify intervals.
  const categories=["same_resolved_direction","direction_reversal","indeterminate","unavailable"];
  const sameKeys=(value,expected)=>value&&typeof value==="object"&&Object.keys(value).length===expected.length&&expected.every(k=>Object.hasOwn(value,k));
  if(!sameKeys(report.comparisons,["development","evaluation"]))fail();
  for(const [allocation,groups]of Object.entries(report.comparisons)){
    const count=Object.values(d.allocation).filter(value=>value===allocation).length;
    if(!sameKeys(groups,Object.keys(d.subsets)))fail();
    for(const variants of Object.values(groups)){
      if(!sameKeys(variants,s.variants.map(v=>v.id)))fail();
      for(const value of Object.values(variants)){
        const directions=value?.directions;
        if(!directions||directions.planned_count!==count||categories.some(k=>!Number.isSafeInteger(directions[k])||directions[k]<0)||categories.reduce((sum,k)=>sum+directions[k],0)!==count)fail();
        if(!Array.isArray(directions.rows)||directions.rows.length!==count||directions.rows.some(row=>!categories.includes(row.status))||categories.some(k=>directions.rows.filter(row=>row.status===k).length!==directions[k]))fail();
      }
    }
  }
  return report;
}

function samplingConclusionSummary(report,target){
  const design=report.plan.design, definitions=report.plan.settings.variants;
  const schedules=Object.entries(design.subsets).sort(([a,at],[b,bt])=>bt.length-at.length||a.localeCompare(b));
  const reversed=schedules.filter(([id])=>Object.values(report.comparisons).some(group=>definitions.some(v=>group[id][v.id].directions.direction_reversal>0)));
  const incomplete=Object.values(report.comparisons).some(group=>Object.values(group).some(variants=>Object.values(variants).some(v=>v.directions.unavailable>0||v.directions.indeterminate>0)));
  const summary=obsElement("section",undefined,"sampling-summary");
  summary.append(obsElement("h3","What changes with fewer measurements?"));
  let finding="All planned paired comparisons keep the same resolved direction under the tested assumptions.";
  if(reversed.length)finding="Direction reversals occur with "+reversed.map(([id,times])=>`${times.length} measurement times (${id})`).join("; ")+" under at least one tested assumption.";
  else if(incomplete)finding="Some comparisons cannot determine whether the direction is preserved. Review the unresolved and unavailable counts below.";
  summary.append(obsElement("p",finding,"obs-scope"));
  if(reversed.length&&incomplete)summary.append(obsElement("p","Some other comparisons are unresolved or unavailable; they do not count as agreement.","field-note"));
  summary.append(obsElement("p","These are synthetic comparisons with the full-curve reference. Matching direction does not establish agreement in the estimated amount or justify a clinical sampling schedule.","field-note"));
  for(const allocation of ["development","evaluation"]){
    const count=Object.values(design.allocation).filter(value=>value===allocation).length;
    const title=allocation==="development"?"Development examples":"Evaluation examples";
    const group=obsElement("section",undefined,"sampling-summary-group");
    group.append(obsElement("h4",`${title} · ${count} participants`));
    group.append(obsElement("p",`Each count is out of ${count} participant pairs for one assumption. The same people appear under each assumption; the rows are not independent samples.`,"field-note"));
    const table=obsTable(group,"Paired conclusions compared with the full reference",["Measurement schedule","Result under each assumption"],[
      [`Full reference\n${design.full_times_minutes.join(", ")} min`,"Reference analysis. Unavailable full-reference results are retained in the unavailable counts below."],
      ...schedules.map(([id,times])=>[`${times.length} measurement times (${id})\n${times.join(", ")} min`,definitions.map(({id:variant})=>{
        const d=report.comparisons[allocation][id][variant].directions;
        return `${variant}: ${d.same_resolved_direction}/${d.planned_count} same direction; ${d.direction_reversal}/${d.planned_count} reversed; ${d.indeterminate}/${d.planned_count} unresolved; ${d.unavailable}/${d.planned_count} unavailable`;
      }).join("\n")])
    ]);
    table.className="sampling-summary-table";
    summary.append(group);
  }
  summary.append(obsElement("p","Unresolved means at least one conditional interval does not resolve a direction, including two unresolved results. Unavailable means either analysis lacks the required result. Detailed intervals, endpoint differences and every failed attempt remain below.","field-note"));
  target.append(summary);
}

function renderSamplingReport(report,target) {
  samplingValidateNative(report);
  target.replaceChildren();
  const c=report.coverage;
  target.append(obsElement("p","Whole-body total secretion including basal over measured 0–120 minutes, in pmol. Paired change is follow-up minus baseline. Differences below are reduced minus full reference.","obs-scope"));
  target.append(obsElement("p","Invented controls only. The full curve is a reference analysis, not biological truth. No empirical equivalence margins, human validity or prospective blood-draw recommendation.","field-note"));
  target.append(obsElement("p",`${c.completed_variant_pairs} / ${c.planned_variant_pairs} required variant pairs complete; ${c.completed_draw_pairs} / ${c.planned_draw_pairs} perturbation pairs complete. Calculation ${c.complete_cohort?"complete":"incomplete"}.`,"obs-scope"));
  samplingConclusionSummary(report,target);
  const design=report.plan.design;
  obsDetails(target,"Execution details and complete denominators",box=>{
    obsTable(box,"Execution and all planned denominators",["Quantity","Count"],Object.entries(c).filter(([k])=>k!=="complete_cohort").map(([k,v])=>[k.replaceAll("_"," "),v]));
    obsTable(box,"Frozen raw observation subsets",["Schedule","Actual times (min)","Execution"],Object.entries({full:design.full_times_minutes,...design.subsets}).map(([id,times])=>[id,times.join(", "),report.schedules[id].status]));
  });
  for(const [allocation,schedules]of Object.entries(report.comparisons))obsDetails(target,allocation+" comparisons",box=>{
    box.append(obsElement("p","Precision is the sample SD of differences, not a confidence interval for bias. Both unresolved directions remain indeterminate. Linked visits are not independent participants.","field-note"));
    const rows=[],directions=[];
    for(const [schedule,variants]of Object.entries(schedules))for(const [variant,value]of Object.entries(variants)){
      for(const key of ["visit_totals","paired_changes"]){const m=value[key];rows.push([schedule,variant,key.replaceAll("_"," "),m.compared_count+" / "+m.planned_count,obsNumber(m.bias_pmol),obsNumber(m.mean_absolute_difference_pmol),obsNumber(m.precision_sample_sd_pmol),obsNumber(m.root_mean_square_difference_pmol),obsNumber(m.maximum_absolute_difference_pmol)]);}
      const d=value.directions;directions.push([schedule,variant,d.planned_count,d.same_resolved_direction,d.direction_reversal,d.indeterminate,d.unavailable]);
    }
    obsTable(box,"Absolute and signed endpoint differences (pmol)",["Schedule","Variant","Endpoint","Compared / planned","Bias","Mean absolute","Precision SD","RMS","Maximum absolute"],rows);
    obsTable(box,"Conditional paired-direction comparison",["Schedule","Variant","Planned","Same resolved","Reversal","Indeterminate","Unavailable"],directions);
  });
  obsDetails(target,"Every planned paired comparison",box=>obsTable(box,"Native paired changes and conditional intervals",["Allocation","Person","Schedule","Variant","Full change (pmol)","Reduced change (pmol)","Full interval (pmol)","Reduced interval (pmol)","Full direction","Reduced direction"],report.paired_comparisons.map(r=>[r.allocation,r.participant_id,r.schedule,r.variant,obsNumber(r.reference_change_pmol),obsNumber(r.reduced_change_pmol),obsInterval(r.reference_interval_pmol),obsInterval(r.reduced_interval_pmol),r.reference_direction??"unavailable",r.reduced_direction??"unavailable"])));
  obsDetails(target,"Every planned visit comparison",box=>obsTable(box,"Per-visit totals and failures",["Allocation","Person","Visit","Schedule","Variant","Full (pmol)","Reduced (pmol)","Difference (pmol)","Full status","Reduced status"],report.visit_comparisons.map(r=>[r.allocation,r.participant_id,r.visit,r.schedule,r.variant,obsNumber(r.reference_pmol),obsNumber(r.reduced_pmol),obsNumber(r.difference_pmol),r.reference_attempt?.status??"unavailable",r.reduced_attempt?.status??"unavailable"])));
  obsDetails(target,"Low values, assay limits and glucose context",box=>{
    obsTable(box,"All visits; no automatic clinical low-value threshold",["Schedule","Person","Visit","Minimum C-peptide (pmol/L)","Assay LOQ (pmol/L)","Censored","C-peptide AUC (pmol·min/L)","Glucose AUC (mmol·min/L)"],report.assay_and_glucose_context.map(r=>[r.schedule,r.participant_id,r.visit,obsNumber(r.minimum_observed_cpeptide_pmol_l),obsNumber(r.assay_loq_pmol_l),r.censored_samples??"unavailable",obsNumber(r.reference?.cpeptide_auc_pmol_min_l),obsNumber(r.reference?.glucose_auc_mmol_min_l)]));
    box.append(obsElement("p","C-peptide AUC remains a concentration reference. Each native schedule report below retains assay, protocol, medication, actual measured traces and all failed attempts.","field-note"));
  });
  for(const [id,record]of Object.entries(report.schedules))obsDetails(target,id+" · all native attempts and context",box=>{
    if(record.report){const child=obsElement("div");box.append(child);renderObservationReport(record.report,child);}else box.append(obsElement("p",record.error||record.status,"notice"));
  });
}

function samplingReview(value){
  const target=document.getElementById("sam-design-review");target.replaceChildren();if(!value.design)return;
  const d=value.design;
  obsTable(target,"Development-frozen schedules",["Schedule","Actual times (min)"],Object.entries({full:d.full_times_minutes,...d.subsets}).map(([k,v])=>[k,v.join(", ")]));
  target.append(obsElement("p","Selected using: "+d.selection_participants.join(", ")+". "+d.selection_rationale,"field-note"));
}
const samplingUI=createObservationUI({prefix:"sam",api:"sampling",view:"sampling",open:"open-sampling",operation:"sampling",task:"mmtt-sampling",label:"Sampling comparison",fields:["package","csv","settings","design","development_import"],cases:{"information-loss":"Constructed direction reversal",constant:"Constant control",incomplete:"Low / censored control","steep-response":"Boundary failure control"},render:renderSamplingReport,review:samplingReview});
function refreshSampling(){return samplingUI.refresh();}
function selectSamplingID(id){return samplingUI.select(id);}
