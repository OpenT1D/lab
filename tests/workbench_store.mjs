import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root=path.resolve(process.argv[2] || path.join(path.dirname(fileURLToPath(import.meta.url)), '../packaging/sdk/opent1d_lab/_gui_assets'));
const source=fs.readFileSync(path.join(root,'workbench-store.js'),'utf8');
const uiSource=fs.readFileSync(path.join(root,'workbench.js'),'utf8');
const {WorkbenchStore}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return{promise,resolve,reject}};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const record=(id='a'.repeat(32))=>({id,project:'project-a',task:'mmtt-sensitivity',revision:1,name:'Saved study',parent:null,files:{'package.json':'{}','observations.csv':'original','settings.json':'{}'}});
function create(fetcher=async()=>{throw new Error('unexpected request')}){
 const values=new Map(), storage={setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k)||null,removeItem:k=>values.delete(k)};
 const store=new WorkbenchStore({token:'synthetic-review-token',storage,fetcher});
 store.data={workspace:'/review-only-synthetic-workspace',projects:[{id:'project-a',name:'A'}],drafts:[],installation:{tasks:['mmtt-sensitivity']},active:null};store.projectId='project-a';store.accept(record());return{store,values};
}
const results=[];
async function check(name,fn){try{await fn();results.push({name,status:'pass'})}catch(e){results.push({name,status:'FAIL',error:e.message});}}

await check('control: loading a saved draft without concurrent edits succeeds',async()=>{
 const saved=record('b'.repeat(32));const {store}=create(async()=>({ok:true,json:async()=>saved}));
 assert.equal(await store.loadDraft(saved.id),true);assert.equal(store.record.id,saved.id);assert.equal(store.dirty,false);
});

await check('failed reload retains dirty status and recovery bytes',async()=>{
 const {store,values}=create(async()=>{throw new Error('simulated offline')});
 store.edit('Local unsaved question',store.files,false);assert.equal(values.size,1);
 await assert.rejects(store.reloadSaved(),/offline/);
 assert.equal(store.dirty,true,'unsaved text became clean after failed GET');
 assert.equal(values.size,1,'recovery copy was removed before replacement arrived');
});

await check('pending draft read does not replace text entered afterwards',async()=>{
 const read=deferred();const {store}=create(async()=>read.promise);
 const loading=store.loadDraft('b'.repeat(32));await tick();
 store.edit('New question after dismissing pending study picker',store.files,false);
 read.resolve({ok:true,json:async()=>record('b'.repeat(32))});await loading;
 assert.equal(store.name,'New question after dismissing pending study picker','late draft read accepted over newer local edits');
 assert.equal(store.dirty,true);
});

await check('control: editing during save keeps newer text dirty and permits a later save',async()=>{
 const waiting=deferred();const {store}=create();let savedValues;
 store.action=async(_op,values)=>{savedValues=values;return waiting.promise};
 store.edit('First edit',store.files,false);const saving=store.save();await tick();
 store.edit('Newer edit',store.files,false);waiting.resolve({...record(),revision:2,name:savedValues.name,files:savedValues.files});await saving;
 assert.equal(store.name,'Newer edit');assert.equal(store.dirty,true);clearTimeout(store.timer);
 store.action=async(_op,values)=>({...record(),revision:3,name:values.name,files:values.files});
 assert.equal(await store.save(),true);assert.equal(store.dirty,false);assert.equal(store.record.name,'Newer edit');
});

await check('normal upload works; a late file read does not overwrite newer manual edits',async()=>{
 for(const manual of [false,true]){
 const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{value:'',files:[],dataset:{},open:false,hidden:false,addEventListener(){},replaceChildren(){},append(){},removeAttribute(){},setAttribute(){},setCustomValidity(){},classList:{contains(){return false},toggle(){}}});return elements.get(id)};
 const context={console,TextDecoder,TextEncoder,setTimeout,clearTimeout,setInterval(){return 0},clearInterval(){},localStorage:null,WorkbenchStore:class{constructor(){this.record=record()}async refresh(){}},approaches:{},document:{getElementById:element,querySelector(){return{content:'test'}},querySelectorAll(){return[]},createElement(){return{}},addEventListener(){}},window:{addEventListener(){}}};
 vm.createContext(context);
 vm.runInContext(uiSource.replace(/^import[^\n]*\n/,'')+'\nglobalThis.probe={setEditor:(e)=>editor=e,getEditor:()=>editor};',context);
 context.probe.setEditor({id:'a'.repeat(32),files:{'observations.csv':'original'},dirty:false});
 element('input-file').value='observations.csv';element('files-dialog').open=true;
 const read=deferred();element('input-upload').files=[{size:12,arrayBuffer:()=>read.promise}];
 const upload=element('input-upload').onchange();
 if(manual){element('input-text').value='new manual text';element('input-text').oninput();}
 read.resolve(new TextEncoder().encode('older picked file').buffer);await upload;
 assert.equal(context.probe.getEditor().files['observations.csv'],manual?'new manual text':'older picked file',manual?'late upload replaced later textarea edits':'normal upload was incorrectly discarded');
 }
});

// The controller can publish done before journal cleanup releases its active id.
await check('done/active cleanup interleaving does not strand the next action',async()=>{
 let stateReads=0;const {store}=create(async(path)=>({ok:true,json:async()=>path==='/api/actions'?{id:'job'}:path.startsWith('/api/jobs/')?{id:'job',status:'done',result:{project:'project-a'}}:{...store.data,active:++stateReads===1?'job':null}}));
 await store.action('refresh',{});await tick();
 assert.equal(store.locked,false,'finished own action retained the active-job lock');
 assert.ok(stateReads>=2,'cleanup state was not observed');
 await store.action('refresh',{});
});

const passed=!results.some(x=>x.status==='FAIL');
console.log(JSON.stringify({schema:'opent1d.workbench-controlled-review/1',scope:'Actual unmodified WorkbenchStore and UI event handlers with controlled requests and a minimal DOM; not real-browser or human usability evidence',passed,node:process.version,sourceHashes:{store:createHash('sha256').update(source).digest('hex'),ui:createHash('sha256').update(uiSource).digest('hex')},results},null,2));
process.exitCode=passed?0:1;
