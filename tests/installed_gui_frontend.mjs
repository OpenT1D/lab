import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
const sourcePath=process.argv[2];
const receiptPath=process.argv[3];
const source=fs.readFileSync(sourcePath,'utf8');
const draftSourcePath=process.argv[4];
const draftSource=fs.readFileSync(draftSourcePath,'utf8');
const comparisonSourcePath=process.argv[5];
const comparisonSource=fs.readFileSync(comparisonSourcePath,'utf8');
class Element {
 constructor(tag='div'){this.tag=tag;this.value='';this.children=[];this.textContent='';this.content='session-token';this.src='';this.open=false;this.hiddenClasses=new Set();const classes=this.hiddenClasses;this.classList={add(...names){for(const name of names)classes.add(name);},remove(...names){for(const name of names)classes.delete(name);},contains(name){return classes.has(name);},toggle(name,force){if(force===undefined)force=!classes.has(name);if(force)classes.add(name);else classes.delete(name);return force;}};}
 replaceChildren(...items){this.children=items;if(items.length&&items.every(item=>item.tag==='option'))this.value=items[0].value;}
 append(...items){this.children.push(...items);}
 setAttribute(name,value){this[name]=value;} removeAttribute(name){delete this[name];}
 focus(){} scrollIntoView(){}
}
function environment({concepts=false,comparisons=false}={}){
 const nodes=new Map(),byId=id=>{if(!nodes.has(id))nodes.set(id,new Element(['task','example-case','parent-plan','plan-select'].includes(id)?'select':'div'));return nodes.get(id);};byId('task').value='mmtt-sensitivity';
 const figureButton=new Element('button'),urlCalls=[];
 const backups=new Map();
 const context={document:{getElementById:byId,querySelector:query=>query.includes('opent1d-token')?{content:'session-token'}:figureButton,querySelectorAll:()=>[],createElement:tag=>{const node=new Element(tag);let id='';Object.defineProperty(node,'id',{get:()=>id,set:value=>{id=value;nodes.set(value,node);}});return node;}},fetch:()=>new Promise(()=>{}),setInterval(){},setTimeout(){},clearTimeout(){},addEventListener(){},localStorage:{setItem:(k,v)=>backups.set(k,v),getItem:k=>backups.get(k)||null,removeItem:k=>backups.delete(k)},TextDecoder,crypto:{randomUUID:()=> 'controlled-request'},URL:{createObjectURL(){const value='blob:controlled-'+urlCalls.length;urlCalls.push(['create',value]);return value;},revokeObjectURL(value){urlCalls.push(['revoke',value]);}},console};
 vm.createContext(context);if(concepts)vm.runInContext(draftSource,context,{filename:draftSourcePath});if(comparisons)vm.runInContext(comparisonSource,context,{filename:comparisonSourcePath});vm.runInContext(source,context,{filename:sourcePath});return {context,byId,figureButton,urlCalls,backups,run:code=>vm.runInContext(code,context)};
}
function base(){
 return {projects:[{id:'project',name:'Controlled project',path:'/project',labels:{},info:{plans:[{id:'fasting',task:'m4-study-installed',slots:['dalla_man/fasting','ultradian/fasting'],parent:null},{id:'mmtt-base',task:'mmtt-sensitivity',slots:['person/primary'],parent:null}],attempts:[]}}],jobs:[],active:null,closing:false,workspace:'/workspace',installation:{build_label:'controlled',source:{revision:'a'.repeat(40)}},runtime_attachment:'/attachment-A.json',runtime_revision:0};
}
function seed(e){e.run('data='+JSON.stringify(base())+';selected="project";selectedPlan="fasting";');}
const receipt={schema:'opent1d.gui-dom-agent-review/1',scope:'Controlled DOM with actual unmodified application JavaScript; not a real-browser or human usability check',source_path:sourcePath,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),draft_source_sha256:crypto.createHash('sha256').update(draftSource).digest('hex'),node:process.version,tests:{}};
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
 e.run('currentReport={id:"old",project:"project",attempt:"old-complete-attempt",completeness:"complete"};imageURL="blob:old";data.reports=[{id:"new",project:"project",valid:true,attempt:"new-incomplete-attempt",verified_at:"2026-10-29T12:00:00Z",completeness:"incomplete",files:["report.json","report.md","figure.svg"]}];');
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
 e.run('data.reports=[{id:"mmtt",project:"project",valid:true,attempt:"mmtt-attempt",verified_at:"2026-10-29T12:00:00Z",completeness:"complete",files:["report.json","report.md"]}];');
 e.context.fetch=async url=>{calls.push(url);return {ok:true,text:async()=> '# MMTT REPORT'};};await e.run('showReport("mmtt")');
 assert.deepEqual(calls,['/api/reports/mmtt/report.md']);assert.equal(e.run('currentReport.attempt'),'mmtt-attempt');assert.equal(e.byId('report-figure').classList.contains('hidden'),true);assert.equal(e.figureButton.classList.contains('hidden'),true);
 return {requests:calls,figure_hidden:true,figure_download_hidden:true};
});
await check('sampling_selection_explains_development_and_reference_scope',async()=>{
 const e=environment();e.byId('task').value='mmtt-sampling';e.run('updateTask();');
 assert.equal(e.byId('example-case').children.length,4);
 assert.match(e.byId('task-context').textContent,/Development-only selection/);
 assert.match(e.byId('task-context').textContent,/not biological truth/);
 return {four_controls:true,development_scope:true,reference_scope:true};
});
await check('sampling_children_use_scoped_authenticated_text_requests',async()=>{
 const e=environment(),calls=[];
 e.context.fetch=async(url,options)=>{calls.push({url,token:options.headers['X-OpenT1D-Token']});return {ok:true,text:async()=> '# Full schedule\n<script>untrusted()</script>'};};
 e.context.record={id:'a'.repeat(32),files:['report.md','report.json','studies/full/report.md','studies/full/report.json','../private.md']};
 e.run('currentReport=record;renderChildReports(record);');
 const children=e.byId('child-reports').children;
 assert.equal(children.length,2,'Only one admitted native schedule is rendered');
 assert.equal(children[1].children[0].textContent,'Schedule: full');
 await children[1].children[1].onclick();
 assert.deepEqual(calls,[{url:'/api/reports/'+('a'.repeat(32))+'/studies/full/report.md',token:'session-token'}]);
 const content=children[1].children.at(-1);
 assert.equal(content.children[0].textContent,'Full schedule');
 assert.equal(content.children[1].textContent,'<script>untrusted()</script>');
 assert.equal(content.children[1].tag,'p','Saved text is never executed as HTML');
 return {scoped_child_route:true,session_token:true,unsafe_name_not_rendered:true,html_inert:true};
});
await check('sampling_refusals_and_invalid_polls_withdraw_verified_content',async()=>{
 for(const button of [1,2,3]){
  const e=environment();seed(e);
  e.run('currentReport={id:"sampling",project:"project",valid:true,files:["report.md","report.json","studies/full/report.md","studies/full/report.json"]};renderChildReports(currentReport);render();');
  const child=e.byId('child-reports').children[1];
  e.context.fetch=async()=>({ok:true,text:async()=> '# Verified child content'});
  await child.children[1].onclick();
  assert.equal(child.children.at(-1).children[0].textContent,'Verified child content');
  e.context.fetch=async()=>({ok:false,json:async()=>({error:'Report directory changed'})});
  await child.children[button].onclick();
  assert.equal(e.run('currentReport'),null);
  assert.equal(e.byId('saved-report').classList.contains('hidden'),true);
  assert.equal(e.byId('child-reports').children.length,0);
  assert.equal(e.byId('notice').textContent,'Report directory changed');
 }
 const e=environment();seed(e);
 e.run('currentReport={id:"sampling",project:"project",valid:true};render();');
 const incoming=base();incoming.reports=[{id:'sampling',valid:true}];await poll(e,incoming);
 assert.equal(e.run('currentReport.id'),'sampling','Valid unchanged polls preserve the report');
 incoming.reports[0].valid=false;await poll(e,incoming);
 assert.equal(e.run('currentReport'),null);
 assert.equal(e.byId('saved-report').classList.contains('hidden'),true);
 return {read_and_both_download_refusals_withdraw:true,invalid_poll_withdraws:true,valid_poll_preserves:true};
});
const sharedSettings=JSON.parse(fs.readFileSync(new URL('../experiments/shared_contracts/fixtures/mmtt-settings.json',import.meta.url),'utf8'));
function concept({id='d'.repeat(32),parent=null}={}){
 const record={id,project:'project',task:'mmtt-sensitivity',name:'Own concept',parent,revision:1,files:{'package.json':'raw metadata','observations.csv':'\uFEFFa,b\r\n1,2\r\n','settings.json':JSON.stringify(sharedSettings)},history:[{revision:1,name:'Own concept',saved_at:'2026-10-30T12:00:00Z'}],validation:{valid:true,revision:1,application:'d'.repeat(64),content_sha256:'c'.repeat(64)},content_sha256:'c'.repeat(64),frozen_plan:null};return record;
}
function setupConcept(record=concept()){
 const e=environment({concepts:true});seed(e);
 e.run('data.installation.descriptor_sha256="'+('d'.repeat(64))+'";data.drafts=[];');
 if(record.parent)e.run('data.projects[0].info.plans.push({id:"'+record.parent+'",task:"mmtt-sensitivity",slots:["person/primary"]});');
 e.context.record=record;e.run('workbench.accept(record);');return e;
}
function savedResult(record,args){return {...record,...args,revision:record.revision+1,validation:null,history:[{revision:record.revision+1,name:args.name,saved_at:'2026-10-30T12:01:00Z'},...record.history]};}
await check('concept_autosave_preserves_untouched_bytes_and_live_controls',async()=>{
 const record=concept(),e=setupConcept(record),control=e.byId('assumption-draws');
 control.value='32';control.oninput();let sent;
 e.context.saveAction=async(operation,args)=>{sent={operation,args};return {status:'done',result:savedResult(record,args)};};e.run('action=saveAction;');
 await e.run('workbench.save();');
 assert.equal(sent.args.files['observations.csv'],record.files['observations.csv']);
 assert.equal(JSON.parse(sent.args.files['settings.json']).uncertainty.draws,32);
 assert.equal(e.byId('assumption-draws'),control,'Autosave must not replace a focused input');
 return {raw_bom_crlf_preserved:true,control_identity_preserved:true};
});
await check('pending_validation_cannot_replace_new_edits_or_clear_recovery',async()=>{
 const record=concept(),e=setupConcept(record);let finish;
 e.context.validationAction=()=>new Promise(resolve=>{finish=resolve;});e.run('action=validationAction;');
 const pending=e.run('workbench.validate();');
 const control=e.byId('assumption-draws');control.value='64';control.oninput();
 const result={...record,revision:2,validation:{...record.validation,revision:2}};
 finish({status:'done',result});await pending;
 assert.equal(e.byId('assumption-draws').value,'64');
 assert.equal(e.backups.size,1);
 assert.equal(e.byId('freeze-draft').disabled,true);
 assert.equal(e.run('draft.validation'),null);
 return {new_edits_retained:true,recovery_retained:true,old_validation_not_applied:true};
});
await check('pending_open_or_reload_cannot_replace_newer_local_edits',async()=>{
 for(const reload of [true,false]){
  const record=concept(),e=setupConcept(record);let finish;
  const loaded=reload?record:concept({id:'e'.repeat(32)});
  e.context.fetch=()=>new Promise(resolve=>{finish=resolve;});
  const pending=e.run('workbench.open("'+loaded.id+'",'+!reload+');');
  e.byId('assumption-draws').value='64';e.byId('assumption-draws').oninput();
  finish({ok:true,json:async()=>loaded});await pending;
  assert.equal(e.byId('assumption-draws').value,'64');
  assert.equal(e.run('draft.id'),record.id);
  assert.equal(e.byId('freeze-draft').disabled,true);assert.equal(e.backups.size,1);
  assert.match(e.byId('notice').textContent,/newer local edits/i);
 }
 return {reload_and_open_keep_newer_edits:true,old_validation_not_applied:true};
});
await check('pending_reload_cannot_discard_a_new_upload_still_being_read',async()=>{
 const record=concept(),e=setupConcept(record);let finishLoad,finishFile;
 e.context.fetch=()=>new Promise(resolve=>{finishLoad=resolve;});
 const loading=e.run('workbench.open("'+record.id+'",false);');
 const upload=e.byId('source-settings-json-upload');
 upload.files=[{size:12,arrayBuffer:()=>new Promise(resolve=>{finishFile=resolve;})}];
 const reading=upload.onchange();
 finishLoad({ok:true,json:async()=>record});await loading;
 assert.equal(e.byId('freeze-draft').disabled,true);
 const raw='{"new_upload":true}';finishFile(new TextEncoder().encode(raw).buffer);await reading;
 assert.equal(e.byId('source-settings-json').value,raw);
 assert.equal(e.backups.size,1);assert.equal(e.byId('freeze-draft').disabled,true);
 return {pending_file_choice_retained:true,completed_upload_retained:true};
});
await check('concept_picker_preserves_explicit_selection_across_polling',async()=>{
 const record=concept(),e=setupConcept(record),other={...concept({id:'e'.repeat(32)}),name:'Other concept'};
 e.context.incoming={...base(),drafts:[record,other]};
 e.run('data.drafts=incoming.drafts;workbench.render(data,project(),false);');
 e.byId('draft-select').value=other.id;
 e.run('workbench.render(data,project(),false);workbench.render(data,project(),false);');
 assert.equal(e.byId('draft-select').value,other.id);
 e.context.fetch=async()=>({ok:true,json:async()=>other});await e.byId('open-draft').onclick();
 assert.equal(e.run('draft.id'),other.id);
 return {explicit_picker_preserved:true,chosen_concept_opened:true};
});
await check('conflict_fork_retains_frozen_parent',async()=>{
 const record=concept({parent:'a'.repeat(64)}),e=setupConcept(record);let sent;
 e.context.createAction=async(operation,args)=>{sent=args;return {status:'done',result:{...concept({id:'e'.repeat(32),parent:args.parent}),name:args.name,files:args.files}};};e.run('action=createAction;');
 await e.byId('fork-draft').onclick();
 assert.equal(sent.parent,record.parent);
 assert.equal(e.run('draft.parent'),record.parent);
 return {parent_preserved:true};
});
await check('raw_large_seed_and_invalid_upload_cannot_silently_use_old_values',async()=>{
 const record=concept();record.files['settings.json']=record.files['settings.json'].replace('"seed":117','"seed":9007199254740993');
 const e=setupConcept(record);assert.match(e.byId('assumptions').children[0].textContent,/exact integer range/);
 e.byId('plan-name').value='Keep exact seed';e.byId('plan-name').oninput();let sent;
 e.context.saveAction=async(operation,args)=>{sent=args;return {status:'done',result:savedResult(record,args)};};e.run('action=saveAction;');
 await e.run('workbench.save();');assert.equal(sent.files['settings.json'],record.files['settings.json']);
 const valid=setupConcept();const upload=valid.byId('source-observations-csv-upload');
 upload.files=[{size:1,arrayBuffer:async()=>new Uint8Array([255]).buffer}];await upload.onchange();
 assert.equal(valid.byId('freeze-draft').disabled,true);assert.equal(valid.byId('validate-draft').disabled,true);
 return {large_seed_exact:true,invalid_utf8_blocks_freeze:true};
});
await check('late_save_response_does_not_replace_another_open_concept',async()=>{
 const record=concept(),e=setupConcept(record);let finish,args;
 e.byId('assumption-draws').value='64';e.byId('assumption-draws').oninput();
 e.context.saveAction=async(operation,value)=>{args=value;return new Promise(resolve=>{finish=resolve;});};e.run('action=saveAction;');
 const pending=e.run('workbench.save();');const other=concept({id:'e'.repeat(32)});e.context.other=other;e.run('workbench.accept(other);');
 finish({status:'done',result:savedResult(record,args)});await pending;
 assert.equal(e.run('draft.id'),other.id);
 return {late_old_save_ignored:true};
});
await check('newer_file_selection_and_raw_correction_win_over_old_reads',async()=>{
 const e=setupConcept(),upload=e.byId('source-package-json-upload'),area=e.byId('source-package-json');let finish;
 upload.files=[{size:10,arrayBuffer:()=>new Promise(resolve=>{finish=resolve;})}];const older=upload.onchange();
 upload.files=[{size:10,arrayBuffer:async()=>new TextEncoder().encode('{"newer":true}').buffer}];await upload.onchange();
 finish(new TextEncoder().encode('{"older":true}').buffer);await older;
 assert.equal(area.value,'{"newer":true}');
 upload.files=[{size:10,arrayBuffer:()=>new Promise(resolve=>{finish=resolve;})}];const pending=upload.onchange();
 area.value='{"corrected":true}';area.oninput();finish(new TextEncoder().encode('{"late":true}').buffer);await pending;
 assert.equal(area.value,'{"corrected":true}');
 return {latest_file_wins:true,raw_correction_wins:true};
});
await check('invalid_structured_value_never_reuses_old_valid_assumptions',async()=>{
 const record=concept(),e=setupConcept(record);let sent;
 const control=e.byId('assumption-draws');control.value='';control.oninput();
 assert.equal(e.byId('freeze-draft').disabled,true);
 e.context.saveAction=async(operation,args)=>{sent=args;return {status:'done',result:savedResult(record,args)};};e.run('action=saveAction;');
 await e.run('workbench.save();');assert.equal(JSON.parse(sent.files['settings.json']).uncertainty.draws,'');
 assert.equal(e.byId('freeze-draft').disabled,true);
 return {invalid_value_preserved_for_correction:true,old_validation_not_used:true};
});
await check('frozen_plan_inspection_displays_exact_large_integer_text',async()=>{
 const e=environment();seed(e);e.run('loaded=true;watched="exact-plan";');
 const incoming=base();incoming.jobs=[{id:'exact-plan',status:'done',operation:'plan',project:'project',result:{task:'mmtt-sensitivity',scientific_input:{seed:9007199254740993},scientific_input_text:'{"seed":9007199254740993}'}}];
 await poll(e,incoming);
 assert.match(e.byId('plan-details').textContent,/9007199254740993/);
 assert.doesNotMatch(e.byId('plan-details').textContent,/9007199254740992/);
 return {exact_native_integer_display:true};
});
await check('refused_autosave_keeps_edits_and_explicit_unsaved_status',async()=>{
 const e=setupConcept();e.byId('assumption-draws').value='64';e.byId('assumption-draws').oninput();
 e.context.refused=async()=>({status:'error',error:'Controlled unavailable storage'});e.run('action=refused;');
 await e.run('workbench.save();');
 assert.match(e.byId('draft-status').textContent,/Not saved/);
 assert.equal(e.backups.size,1);assert.equal(e.byId('assumption-draws').value,'64');
 assert.equal(e.byId('freeze-draft').disabled,true);
 return {unsaved_status_explicit:true,local_edits_retained:true};
});
await check('slow_prior_comparison_report_cannot_replace_new_verification',async()=>{
 const e=environment();seed(e);const state=base();
 state.reports=['A','B'].map(id=>({id,project:'project',comparison:'comparison-'+id,snapshot:{tip:'tip-'+id},verified_at:'2026-10-31T00:00:00Z',completeness:'complete',files:['report.md','report.json','comparison.csv'],valid:true}));
 const first={id:'JA',status:'running',operation:'comparison_verify',project:'project',arguments:{comparison:'comparison-A',at:null}};
 const doneA={...first,status:'done',result:{report:'A'}},doneB={id:'JB',status:'done',operation:'comparison_verify',project:'project',result:{report:'B'}};
 let releaseA,reportStarted,calls=0,stateCalls=0,background;
 const delay=new Promise(resolve=>{releaseA=resolve;}),started=new Promise(resolve=>{reportStarted=resolve;});
 e.context.setTimeout=fn=>fn();
 e.context.fetch=async url=>{
  if(url==='/api/actions')return {ok:true,json:async()=>++calls===1?first:doneB};
  if(url==='/api/state')return {ok:true,json:async()=>({...state,jobs:++stateCalls===1?[first]:calls===1?[doneA]:[doneA,doneB]})};
  if(url==='/api/jobs/JA'){background=e.run('refresh();');await started;return {ok:true,json:async()=>doneA};}
  if(url==='/api/reports/A/report.md'){reportStarted();await delay;return {ok:true,text:async()=> '# A'};}
  if(url==='/api/reports/B/report.md')return {ok:true,text:async()=> '# B'};
  throw Error(url);
 };
 e.run('loaded=true;');await e.run('action("comparison_verify",{comparison:"comparison-A",at:null});');
 await e.run('action("comparison_verify",{comparison:"comparison-B",at:null});');
 assert.equal(e.run('currentReport.id'),'B');releaseA();await background;
 assert.equal(e.run('currentReport.id'),'B');assert.match(e.byId('report-context').textContent,/tip-B/);
 return {new_report_and_download_identity_retained:true};
});
await check('older_report_download_refusal_cannot_withdraw_newer_report',async()=>{
 const e=environment();seed(e);e.run('currentReport={id:"B"};');
 e.context.old={id:'A'};e.run('reportRefused(new Error("old request failed"),old);');
 assert.equal(e.run('currentReport?.id'),'B');return {new_report_retained:true};
});
function setupComparisons(){const e=environment({comparisons:true});seed(e);e.run('data.projects[0].info.head={tip:"HEAD"};data.projects[0].info.comparisons=[{id:"A",name:"A",members:2},{id:"B",name:"B",members:3}];render();');return e;}
await check('invalid_displayed_copy_cannot_cancel_a_newer_report_load',async()=>{
 for(const kind of ['refusal','poll']){
  const e=environment();seed(e);const state=base();
  state.reports=['A','B'].map(id=>({id,project:'project',attempt:id,verified_at:'2026-10-31T00:00:00Z',completeness:'complete',files:['report.md','report.json'],valid:true}));
  e.context.state=state;e.run('data=state;currentReport=data.reports[0];loaded=true;');let finish;
  e.context.fetch=()=>new Promise(resolve=>{finish=resolve;});const loading=e.run('showReport("B");');
  if(kind==='refusal')e.run('reportRefused(new Error("Old copy failed"),currentReport);');
  else {const incoming={...state,reports:state.reports.map(r=>({...r,valid:r.id!=='A'}))};e.context.fetch=async()=>({ok:true,json:async()=>incoming});await e.run('refresh();');}
  finish({ok:true,text:async()=> '# B'});assert.equal(await loading,true);
  assert.equal(e.run('currentReport?.id'),'B');
 }
 return {old_refusal_and_invalid_poll_preserve_new_load:true};
});
function comparisonValue(){return {comparison:'A',changes_text:'A changes',variants:[{id:'a1',label:'A1',plan:'mmtt-base',selector:{variant:'nominal'}},{id:'a2',label:'A2',plan:'mmtt-base',selector:{variant:'volume-120'}}],attempts:{'mmtt-base':{status:'unattempted'}},baseline:'a1',snapshot:{tip:'HEAD'}};}
await check('comparison_selection_clears_previous_roster_status',async()=>{
 const e=setupComparisons();e.context.a=comparisonValue();e.run('action=async()=>({status:"done",result:a});');await e.byId('comparison-open').onclick();
 e.byId('comparison-select').value='B';e.byId('comparison-select').onchange();
 assert.doesNotMatch(e.byId('comparison-status').textContent,/2 planned members/);
 assert.match(e.byId('comparison-status').textContent,/inspect/i);return {old_snapshot_status_cleared:true};
});
await check('comparison_roster_and_explicit_baseline_survive_project_switch_and_refusal',async()=>{
 const e=setupComparisons();e.run('action=async()=>({status:"done",result:{options:[{selector:{variant:"nominal"},label:"nominal"},{selector:{variant:"volume-120"},label:"volume-120"}]}});');
 e.byId('comparison-plan').value='mmtt-base';e.byId('comparison-plan').onchange();await e.byId('comparison-options').onclick();
 e.byId('comparison-name').value='Unsaved roster';e.byId('comparison-question').value='Question';
 for(const variant of ['nominal','volume-120']){e.byId('comparison-selector').value=JSON.stringify({variant});e.byId('comparison-add').onclick();}
 e.byId('comparison-baseline').value='member-2';e.run('data.projects.push({...data.projects[0],id:"other"});selected="other";render();selected="project";render();');
 assert.equal(e.byId('comparison-roster').children.length,2);assert.equal(e.byId('comparison-baseline').value,'member-2');assert.equal(e.byId('comparison-name').value,'Unsaved roster');
 e.run('action=async()=>({status:"error",error:"Controlled conflict"});');await e.byId('comparison-form').onsubmit({preventDefault(){}});
 assert.equal(e.byId('comparison-roster').children.length,2);assert.equal(e.byId('comparison-baseline').value,'member-2');return {roster_metadata_baseline_retained:true};
});
await check('late_comparison_options_cannot_describe_another_plan',async()=>{
 const e=setupComparisons();let finish;e.context.optionsAction=()=>new Promise(resolve=>{finish=resolve;});e.run('action=optionsAction;');
 const pending=e.byId('comparison-options').onclick();e.byId('comparison-plan').value='mmtt-base';e.byId('comparison-plan').onchange();
 finish({status:'done',result:{options:[{selector:{source:'old'},label:'Old source'}]}});await pending;
 assert.equal(e.byId('comparison-selector').children.length,0);return {late_selector_ignored:true};
});
receipt.passed=Object.values(receipt.tests).every(value=>value.passed);fs.writeFileSync(receiptPath,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({passed:receipt.passed,source_sha256:receipt.source_sha256,tests:Object.fromEntries(Object.entries(receipt.tests).map(([name,value])=>[name,value.passed])),receipt:receiptPath}));if(!receipt.passed)process.exitCode=1;
