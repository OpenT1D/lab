import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
const sourcePath=process.argv[2];
const receiptPath=process.argv[3];
const source=fs.readFileSync(sourcePath,'utf8');
class Element {
 constructor(tag='div'){this.tag=tag;this.value='';this.children=[];this.textContent='';this.content='session-token';this.src='';this.open=false;this.hiddenClasses=new Set();const classes=this.hiddenClasses;this.classList={add(...names){for(const name of names)classes.add(name);},remove(...names){for(const name of names)classes.delete(name);},contains(name){return classes.has(name);},toggle(name,force){if(force===undefined)force=!classes.has(name);if(force)classes.add(name);else classes.delete(name);return force;}};}
 replaceChildren(...items){this.children=items;if(items.length&&items.every(item=>item.tag==='option'))this.value=items[0].value;}
 append(...items){this.children.push(...items);}
 focus(){} scrollIntoView(){}
}
function environment(){
 const nodes=new Map(),byId=id=>{if(!nodes.has(id))nodes.set(id,new Element(['task','example-case','parent-plan','plan-select'].includes(id)?'select':'div'));return nodes.get(id);};byId('task').value='mmtt-sensitivity';
 const figureButton=new Element('button'),urlCalls=[];
 const context={document:{getElementById:byId,querySelector:query=>query.includes('opent1d-token')?{content:'session-token'}:figureButton,querySelectorAll:()=>[],createElement:tag=>new Element(tag)},fetch:()=>new Promise(()=>{}),setInterval(){},setTimeout(){},crypto:{randomUUID:()=> 'controlled-request'},URL:{createObjectURL(){const value='blob:controlled-'+urlCalls.length;urlCalls.push(['create',value]);return value;},revokeObjectURL(value){urlCalls.push(['revoke',value]);}},console};
 vm.createContext(context);vm.runInContext(source,context,{filename:sourcePath});return {context,byId,figureButton,urlCalls,run:code=>vm.runInContext(code,context)};
}
function base(){
 return {projects:[{id:'project',name:'Controlled project',path:'/project',labels:{},info:{plans:[{id:'fasting',task:'m4-study-installed',slots:['dalla_man/fasting','ultradian/fasting'],parent:null},{id:'mmtt-base',task:'mmtt-sensitivity',slots:['person/primary'],parent:null}],attempts:[]}}],jobs:[],active:null,closing:false,workspace:'/workspace',installation:{build_label:'controlled',source:{revision:'a'.repeat(40)}},runtime_attachment:'/attachment-A.json',runtime_revision:0};
}
function seed(e){e.run('data='+JSON.stringify(base())+';selected="project";selectedPlan="fasting";');}
const receipt={schema:'opent1d.gui-dom-agent-review/1',scope:'Controlled DOM with actual unmodified application JavaScript; not a real-browser or human usability check',source_path:sourcePath,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),node:process.version,tests:{}};
async function check(name,fn){try{receipt.tests[name]={passed:true,observed:await fn()};}catch(error){receipt.tests[name]={passed:false,error:error.stack};}}
await check('explicit_parent_survives_repeated_render_and_new_drafts_reset',async()=>{
 const e=environment();seed(e);
 e.run('draft={id:"draft-15-a",project:"project",task:"m4-study-installed",case:"gastric_load_15g",validation:{}};render();');
 assert.equal(e.byId('parent-plan').value,'fasting');
 e.byId('parent-plan').value='';e.run('render();render();');
 assert.equal(e.byId('parent-plan').value,'','Explicit Original plan must survive background rendering');
 e.byId('parent-plan').value='fasting';e.run('render();');assert.equal(e.byId('parent-plan').value,'fasting');
 e.run('draft={id:"draft-mmtt",project:"project",task:"mmtt-sensitivity",case:"complete",validation:{}};render();');
 assert.equal(e.byId('parent-plan').value,'','Parent from another task must not carry into a new draft');
 e.run('draft={id:"draft-15-b",project:"project",task:"m4-study-installed",case:"gastric_load_15g",validation:{}};render();');
 assert.equal(e.byId('parent-plan').value,'fasting');
 return {initial_15g_default:'fasting',explicit_original_after_two_renders:'',explicit_parent_preserved:true,new_task_parent_reset:true,new_15g_draft_default_restored:true};
});
await check('remote_runtime_change_invalidates_but_unchanged_poll_preserves_view',async()=>{
 const e=environment();seed(e);
 function ready(){e.byId('readiness').textContent='Ready for explicit execution.';e.byId('plan-details').textContent='Old inspected assumptions';e.byId('plan-inspector').classList.remove('hidden');e.byId('plan-inspector').open=true;}
 ready();const incoming=base();incoming.runtime_attachment='/attachment-B.json';e.context.incoming=incoming;
 await e.run('fetch=async()=>({ok:true,json:async()=>incoming});refresh();');
 assert.equal(e.run('data.runtime_attachment'),'/attachment-B.json');
 assert.notEqual(e.byId('readiness').textContent,'Ready for explicit execution.');
 assert.equal(e.byId('plan-details').textContent,'');
 assert.equal(e.byId('plan-inspector').classList.contains('hidden'),true);
 ready();await e.run('refresh();');
 assert.equal(e.byId('readiness').textContent,'Ready for explicit execution.','An unchanged poll must preserve valid inspection/readiness');
 assert.equal(e.byId('plan-details').textContent,'Old inspected assumptions');
 e.context.incoming={...incoming,runtime_attachment:null};await e.run('refresh();');
 assert.notEqual(e.byId('readiness').textContent,'Ready for explicit execution.');
 return {external_A_to_B_invalidates:true,unchanged_B_poll_preserves:true,external_B_to_none_invalidates:true};
});
function checkedState({path='/attachment-A.json',revision=0,project='project',plan='fasting',ready=true}={}){
 const incoming=base();incoming.runtime_attachment=path;incoming.runtime_revision=revision;
 incoming.jobs=[{id:'check-A',status:'done',operation:'check',project,arguments:{plan},check_context:{project,plan,runtime_attachment:'/attachment-A.json',runtime_revision:0},result:{runtimes_ready:ready}}];return incoming;
}
async function poll(e,incoming){e.context.incoming=incoming;await e.run('fetch=async()=>({ok:true,json:async()=>incoming});refresh();');}
const readyText='Ready for explicit execution. This check did not run a model or install dependencies.';
await check('late_check_cannot_describe_a_different_runtime_plan_or_project',async()=>{
 const changes=[{path:'/attachment-B.json',revision:1},{path:null,revision:1},{revision:2},{revision:1},{plan:'mmtt-base'},{project:'other'}];
 for(const change of changes){for(const ready of [true,false]){
  const e=environment();seed(e);e.run('loaded=true;watched="check-A";');
  const incoming=checkedState({...change,ready});await poll(e,incoming);
  assert.notEqual(e.byId('readiness').textContent,readyText,JSON.stringify(change));
  assert.doesNotMatch(e.byId('readiness').textContent,/Native execution is unavailable/,'An old unavailable result must not describe the new selection either');
  assert.equal(e.run('selected'),'project','A stale check must not change the chosen project');
  assert.equal(e.run('selectedPlan'),'fasting','A stale check must not change the chosen plan');
 }}return {rejected_contexts:changes.length,both_ready_and_unavailable:true};
});
await check('same_path_reselection_invalidates_but_matching_check_is_displayed',async()=>{
 for(const ready of [true,false]){
  const e=environment();seed(e);e.run('loaded=true;watched="check-A";');await poll(e,checkedState({ready}));
  if(ready)assert.equal(e.byId('readiness').textContent,readyText);else assert.match(e.byId('readiness').textContent,/Native execution is unavailable/);
  const incoming=base();incoming.runtime_revision=1;await poll(e,incoming);
  assert.doesNotMatch(e.byId('readiness').textContent,/Ready for explicit execution|Native execution is unavailable/);
 }
 const e=environment();seed(e);e.run('loaded=true;watched="check-A";');
 const incoming=checkedState();incoming.runtime_attachment=null;incoming.jobs[0].check_context.runtime_attachment=null;await poll(e,incoming);assert.equal(e.byId('readiness').textContent,readyText,'A matching standard-library check needs no native attachment');
 return {matching_success_and_unavailable:true,same_path_reselection_invalidates:true,no_attachment_success:true};
});
await check('older_poll_cannot_roll_back_runtime_and_reapply_old_check',async()=>{
 const e=environment();seed(e);e.run('loaded=true;watched="check-A";');const responses=[];
 e.context.fetch=()=>new Promise(resolve=>responses.push(resolve));
 const older=e.run('refresh();'),newer=e.run('refresh();');
 const incoming=base();incoming.runtime_attachment='/attachment-B.json';incoming.runtime_revision=1;
 responses[1]({ok:true,json:async()=>incoming});await newer;
 responses[0]({ok:true,json:async()=>checkedState()});await older;
 assert.equal(e.run('data.runtime_attachment'),'/attachment-B.json');assert.equal(e.run('data.runtime_revision'),1);assert.notEqual(e.byId('readiness').textContent,readyText);
 return {newer_runtime_preserved:true,old_ready_rejected:true};
});
await check('slow_poll_still_updates_while_a_newer_poll_waits_and_revision_never_regresses',async()=>{
 const e=environment();seed(e);const responses=[];e.context.fetch=()=>new Promise(resolve=>responses.push(resolve));
 const first=e.run('refresh();'),second=e.run('refresh();');
 const newer=base();newer.runtime_attachment='/attachment-B.json';newer.runtime_revision=1;
 responses[0]({ok:true,json:async()=>newer});await first;
 assert.equal(e.run('data.runtime_attachment'),'/attachment-B.json','A slow poll must still update even when the next poll has started');
 responses[1]({ok:true,json:async()=>base()});await second;
 assert.equal(e.run('data.runtime_revision'),1,'A later client request may have an earlier server snapshot');
 return {slow_poll_progress:true,older_server_snapshot_rejected:true};
});
await check('rechecking_clears_previous_readiness_even_if_the_new_check_is_refused',async()=>{
 const e=environment();seed(e);e.byId('readiness').textContent=readyText;
 e.context.fetch=async()=>({ok:false,json:async()=>({error:'Controlled changed attachment'})});await e.run('action("check",{plan:"fasting"});');
 assert.notEqual(e.byId('readiness').textContent,readyText);assert.equal(e.byId('notice').textContent,'Controlled changed attachment');return {old_success_cleared:true};
});
await check('partial_m4_load_preserves_entire_old_report_then_success_commits_new_identity',async()=>{
 const e=environment();seed(e);
 e.run('currentReport={id:"old",project:"project",attempt:"old-complete-attempt",completeness:"complete"};imageURL="blob:old";data.reports=[{id:"new",project:"project",attempt:"new-incomplete-attempt",verified_at:"2026-10-29T12:00:00Z",completeness:"incomplete",files:["report.json","report.md","figure.svg"]}];');
 const oldHeading=new Element('h3');oldHeading.textContent='OLD COMPLETE REPORT';e.byId('report-text').append(oldHeading);e.byId('report-context').textContent='Verified old-complete-attempt';e.byId('report-completeness').textContent='complete';e.byId('report-figure').src='blob:old';
 function snapshot(){return {text:e.byId('report-text').children.map(n=>n.textContent),context:e.byId('report-context').textContent,completeness:e.byId('report-completeness').textContent,downloadAttempt:e.run('currentReport.attempt'),image:e.byId('report-figure').src,urlCalls:[...e.urlCalls]};}
 const before=snapshot();
 e.context.fetch=async url=>url.endsWith('/report.md')?{ok:true,text:async()=> '# NEW INCOMPLETE REPORT'}:{ok:false,json:async()=>({error:'Controlled figure unavailable'})};
 await assert.rejects(e.run('showReport("new")'),/Controlled figure unavailable/);
 assert.deepEqual(snapshot(),before,'Failed new figure fetch must not mix new Markdown with old report identity');
 e.context.fetch=async url=>url.endsWith('/report.md')?{ok:true,text:async()=> '# NEW INCOMPLETE REPORT'}:{ok:true,blob:async()=>({controlled:'svg'})};
 await e.run('showReport("new")');
 assert.deepEqual(e.byId('report-text').children.map(n=>n.textContent),['NEW INCOMPLETE REPORT']);
 assert.equal(e.run('currentReport.attempt'),'new-incomplete-attempt');assert.equal(e.byId('report-completeness').textContent,'incomplete');assert.match(e.byId('report-context').textContent,/new-incomple/);assert.equal(e.urlCalls.filter(v=>v[0]==='revoke'&&v[1]==='blob:old').length,1);
 return {partial_failure_old_snapshot_unchanged:true,successful_retry_new_content_identity_badge_downloads_consistent:true,old_image_revoked_after_success:true};
});
await check('mmtt_two_file_report_never_requests_figure',async()=>{
 const e=environment();seed(e);const calls=[];
 e.run('data.reports=[{id:"mmtt",project:"project",attempt:"mmtt-attempt",verified_at:"2026-10-29T12:00:00Z",completeness:"complete",files:["report.json","report.md"]}];');
 e.context.fetch=async url=>{calls.push(url);return {ok:true,text:async()=> '# MMTT REPORT'};};await e.run('showReport("mmtt")');
 assert.deepEqual(calls,['/api/reports/mmtt/report.md']);assert.equal(e.run('currentReport.attempt'),'mmtt-attempt');assert.equal(e.byId('report-figure').classList.contains('hidden'),true);assert.equal(e.figureButton.classList.contains('hidden'),true);
 return {requests:calls,figure_hidden:true,figure_download_hidden:true};
});
receipt.passed=Object.values(receipt.tests).every(value=>value.passed);fs.writeFileSync(receiptPath,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({passed:receipt.passed,source_sha256:receipt.source_sha256,tests:Object.fromEntries(Object.entries(receipt.tests).map(([name,value])=>[name,value.passed])),receipt:receiptPath}));if(!receipt.passed)process.exitCode=1;
