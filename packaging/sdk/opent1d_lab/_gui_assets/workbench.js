import { WorkbenchStore, approaches } from '/workbench-store.js';

const $ = id => document.getElementById(id);
const desktop = globalThis.openT1DDesktop;
let desktopView;
if (desktop) {
  document.documentElement.classList.add('desktop', desktop.platform);
  document.querySelectorAll('a[href="/"]').forEach(a => { a.hidden = true; });
}
const parseSourceJSON = text => JSON.parse(text.replace(/^\uFEFF/, ''));
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const icon = (name, size) => { const n = node('img'); n.src = '/' + name; n.width = size; n.height = size; n.alt = ''; return n; };
let renderedRecord = null, creationMode = 'guided', editor = null, uploadGeneration = 0, stopped = false;
let recentSignature = '', executionView, resultsView, activeView = 'study', informationInvoker;
let storage; try { storage = localStorage; } catch { storage = null; }
const store = new WorkbenchStore({ token: document.querySelector('meta[name="opent1d-token"]').content, storage, notify: render });
const attempt = fn => async event => { event?.preventDefault?.(); try { await fn(event); } catch (error) { store.error = error.message; render(); } };
const closeDialogs = () => document.querySelectorAll('dialog[open]').forEach(d => d.close());
function options(select, values, chosen) {
  const signature = JSON.stringify(values);
  if (select.dataset.options !== signature) {
    select.replaceChildren(...values.map(([value, label]) => { const n = node('option', label); n.value = value; return n; }));
    select.dataset.options = signature;
  }
  if (chosen !== undefined) select.value = chosen;
}
function recentKey() { return 'opent1d.workbench-recents/1:' + store.data.workspace; }
function recents() { try { return JSON.parse(storage?.getItem(recentKey()) || '{}'); } catch { return {}; } }
function rememberProject() { try { storage?.setItem(recentKey(), JSON.stringify({ ...recents(), [store.projectId]: new Date().toISOString() })); } catch { /* Recent ordering is optional. */ } }
function relativeDate(value) {
  if (!value) return '';
  const date = new Date(value), today = new Date(), yesterday = new Date(); yesterday.setDate(today.getDate() - 1);
  return date.toDateString() === today.toDateString() ? 'Today' : date.toDateString() === yesterday.toDateString() ? 'Yesterday' : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
function showStudy() {
  activeView = 'study'; resultsView?.hide();
  if ($('results-tab')) $('results-tab').removeAttribute('aria-current');
  $('study-tab').setAttribute('aria-current', 'page'); $('tree-study').setAttribute('aria-current', 'page'); $('tree-results').removeAttribute('aria-current');
  $('tree-study').classList.add('active'); $('tree-results').classList.remove('active');
  for (const id of ['study-body', 'study-tab', 'close-study']) $(id).hidden = false;
  render();
  $('study-heading').focus();
}
async function openProject(id) { if (!await beforeNavigate()) return; if (await store.openProject(id)) { rememberProject(); showStudy(); } }
function renderRecents() {
  if (!store.data) return;
  const dates = recents(), projects = [...store.data.projects].sort((a, b) => (dates[b.id] || '').localeCompare(dates[a.id] || ''));
  const signature = JSON.stringify([projects.map(p => [p.id, p.name, p.path]), dates, store.locked]);
  if (signature === recentSignature) return;
  recentSignature = signature;
  const rows = projects.map(project => {
    const row = node('button', undefined, 'recent-project'); row.type = 'button'; row.disabled = store.locked;
    const copy = node('span', undefined, 'project-copy'); copy.append(node('strong', project.name), node('span', project.path));
    row.append(icon('wb-0-folder.svg', 22), copy, node('span', relativeDate(dates[project.id]), 'project-date'));
    row.title = project.path; row.onclick = attempt(() => openProject(project.id)); return row;
  });
  if (!rows.length) { const empty = node('div', undefined, 'empty-projects'); empty.append(node('p', 'No recent projects yet.'), node('p', 'Open a project or create your first study.')); rows.push(empty); }
  $('recent-projects').replaceChildren(...rows);
}
function inputSummary() {
  const files = store.files, observed = files['observations.csv']?.trim();
  $('observations-description').textContent = observed ? 'observations.csv · synthetic measurements' : 'Add your synthetic measurement files';
  $('observations-action').textContent = observed ? 'View' : 'Add';
  let settings; try { settings = parseSourceJSON(files['settings.json']); } catch { /* Raw text stays editable. */ }
  $('assumptions-description').textContent = settings?.variants ? `settings.json · ${settings.variants.length} assumption variants` : 'Add or review analysis settings';
  $('assumptions-action').textContent = settings ? 'Review' : 'Add';
}
function render() {
  if (stopped) return;
  const project = store.project, record = store.record, busy = store.locked;
  const view = project ? 'workspace' : 'startup';
  if (desktop && desktopView !== view) { desktopView = view; desktop.setView(view); }
  $('startup').hidden = !!project; $('workspace').hidden = !project;
  for (const id of ['new-project', 'start-empty', 'use-template', 'open-project']) $(id).disabled = !store.data || busy;
  $('quit-start').disabled = !store.data || busy;
  if (!project) { renderRecents(); }
  else {
    document.title = project.name + ' · OpenT1D'; $('project-title').textContent = project.name; $('tree-project-name').textContent = project.name;
    $('study-empty').hidden = !!record; $('study-form').hidden = !record;
    $('save-study').hidden = !store.dirty && !store.saving;
    $('save-study').disabled = busy || store.conflict || !store.dirty;
    $('save-state').textContent = store.saving ? 'Saving…' : store.dirty ? 'Unsaved changes' : '';
    $('menu-save').disabled = busy || !store.dirty || store.conflict;
    for (const id of ['all-projects', 'project-switcher', 'menu-projects', 'menu-studies', 'choose-study', 'create-study', 'another-study']) $(id).disabled = busy;
    if (record) {
      if (renderedRecord !== record.id || document.activeElement !== $('research-question')) $('research-question').value = store.name;
      renderedRecord = record.id;
      options($('approach'), store.admitted.map(task => [task, approaches[task].label]), record.task);
      $('research-question').disabled = busy && !store.saving;
      for (const id of ['approach', 'observations', 'assumptions', 'tree-observations', 'tree-assumptions', 'review-study']) $(id).disabled = busy;
      inputSummary();
    }
  }
  if (!project) document.title = 'OpenT1D';
  const skip = document.querySelector('.skip');
  if (skip) { skip.href = !project ? '#projects-heading' : activeView === 'results' ? '#results-heading' : '#study-heading'; skip.textContent = !project ? 'Skip to projects' : activeView === 'results' ? 'Skip to results' : 'Skip to study'; }
  const badge = document.querySelector('.draft-badge');
  if (badge) badge.textContent = record?.frozen_plan && !store.dirty ? 'Frozen' : record?.validation?.valid && !store.dirty ? 'Reviewed' : 'Draft';
  executionView?.render(); resultsView?.render();
  if (editor?.dirty) backupEditor();
  $('notice').hidden = !store.error; $('notice-text').textContent = store.error;
  $('retry-save').hidden = !store.dirty || store.conflict;
  $('reload-study').hidden = !store.conflict; $('save-copy').hidden = !store.conflict;
  for (const id of ['retry-save', 'reload-study', 'save-copy']) $(id).disabled = busy;
}
function newDialog(mode, task = store.record?.task || store.admitted[0]) {
  creationMode = mode; closeDialogs();
  const open = mode === 'open', study = ['study', 'switch'].includes(mode);
  $('project-dialog-title').textContent = open ? 'Open project' : study ? 'Create a study' : mode === 'template' ? 'Start from a template' : mode === 'empty' ? 'Start empty' : 'New project';
  $('project-dialog-description').textContent = open ? 'Choose the absolute folder path of an existing OpenT1D project.' : mode === 'empty' ? 'Create a project without supplied inputs. You can add synthetic files in Study.' : mode === 'switch' ? 'The current study is kept. This creates a separate study with the chosen approach.' : 'Choose an approach and start with an editable synthetic example.';
  $('project-name-label').textContent = open ? 'Project folder' : 'Project name';
  $('project-name-label').hidden = study; $('project-name').hidden = study; $('project-name').required = !study;
  $('project-name').maxLength = open ? 4096 : 100; $('project-name').value = ''; $('project-name').placeholder = open ? '/absolute/path/to/project' : 'My meal-test study';
  $('creation-options').hidden = open;
  options($('new-approach'), store.admitted.map(t => [t, approaches[t].label]), task);
  $('template-options').hidden = mode !== 'template'; updateTemplates();
  $('confirm-project').textContent = open ? 'Open project' : study ? 'Create study' : 'Create project';
  $('project-error').hidden = true; $('project-dialog').showModal();
}
function updateTemplates() {
  const sampling = $('new-approach').value === 'mmtt-sampling';
  options($('template-case'), sampling ? [['information-loss', 'Information-loss example'], ['constant', 'Constant-input control'], ['incomplete', 'Incomplete measurements'], ['steep-response', 'Steep-response boundary control']] : [['complete', 'Paired meal tests'], ['censored', 'Censored measurements']]);
}
function information(title, paragraphs, link = false, invoker = document.activeElement) {
  informationInvoker = invoker; $('freeze-study')?.remove();
  closeDialogs(); $('information-title').textContent = title;
  $('information-content').replaceChildren(...paragraphs.map(text => node('p', text)));
  if (link && !desktop) { const a = node('a', 'Open full laboratory'); a.href = '/'; $('information-content').append(a); }
  $('information-dialog').showModal();
}
function showStudies() {
  closeDialogs(); $('saved-studies').replaceChildren(...store.drafts.map(draft => {
    const b = node('button', draft.name); b.append(node('small', `${approaches[draft.task].label} · revision ${draft.revision}`));
    b.onclick = attempt(async () => { if (await store.loadDraft(draft.id)) { closeDialogs(); showStudy(); } }); return b;
  }));
  if (!store.drafts.length) $('saved-studies').append(node('p', 'No saved MMTT studies in this project.'));
  $('studies-dialog').showModal();
}
function unsafeNumber(value) {
  if (typeof value === 'number') return !Number.isFinite(value) || (Number.isInteger(value) && !Number.isSafeInteger(value));
  return value && typeof value === 'object' && Object.values(value).some(unsafeNumber);
}
function paintStructured() {
  const file = $('input-file').value;
  let settings, unsafe = false;
  try { settings = parseSourceJSON(editor.files[file]); unsafe = unsafeNumber(settings); }
  catch { /* Keep malformed raw text editable. */ }
  $('structured-settings').hidden = file !== 'settings.json' || !settings?.uncertainty || unsafe;
  $('structured-warning').hidden = file !== 'settings.json' || !unsafe;
  for (const id of ['draws', 'seed']) {
    $(id).disabled = $('structured-settings').hidden;
    $(id).required = !$(id).disabled;
    $(id).removeAttribute('aria-invalid');
    $(id).setCustomValidity('');
  }
  if (!$('structured-settings').hidden) { $('draws').value = settings.uncertainty.draws; $('seed').value = settings.uncertainty.seed; }
}
function paintEditor() {
  const file = $('input-file').value; $('input-text').value = editor.files[file]; $('input-upload').value = '';
  paintStructured();
}
function editInputs(kind) {
  if (!store.record || store.locked) return;
  closeDialogs(); editor = { id: store.record.id, files: { ...store.files }, dirty: false }; uploadGeneration++;
  const names = Object.keys(editor.files).filter(name => kind === 'assumptions' ? ['settings.json', 'design.json'].includes(name) : !['settings.json', 'design.json'].includes(name));
  options($('input-file'), names.map(name => [name, name]), kind === 'assumptions' ? 'settings.json' : 'observations.csv');
  $('files-title').textContent = kind === 'assumptions' ? 'Analysis assumptions' : 'Synthetic observations';
  $('file-error').hidden = true; paintEditor(); $('files-dialog').showModal();
}
async function quit() {
  if (desktop) { desktop.quit(); return; }
  if (!await beforeNavigate()) return;
  await store.request('/api/shutdown', {}); stopped = true; closeDialogs(); $('workspace').hidden = true; $('startup').hidden = false;
  $('recent-projects').replaceChildren(node('p', 'Application stopped. Your saved work is kept.'));
  for (const b of document.querySelectorAll('button')) b.disabled = true;
}

$('new-project').onclick = () => newDialog('guided'); $('start-empty').onclick = () => newDialog('empty');
$('use-template').onclick = () => newDialog('template');
$('open-project').onclick = desktop ? attempt(async () => {
  if (!await beforeNavigate()) return;
  const folder = await desktop.openProject();
  if (folder && await store.openPath(folder)) { rememberProject(); showStudy(); }
}) : () => newDialog('open');
$('new-approach').onchange = updateTemplates;
$('project-dialog-form').onsubmit = async event => {
  event.preventDefault(); $('confirm-project').disabled = true; $('project-error').hidden = true;
  try {
    const task = $('new-approach').value, mode = creationMode === 'empty' ? 'empty' : 'guided';
    const example = creationMode === 'template' ? $('template-case').value : task === 'mmtt-sampling' ? 'information-loss' : 'complete';
    let done;
    if (creationMode === 'open') done = await store.openPath($('project-name').value.trim());
    else if (['study', 'switch'].includes(creationMode)) done = await store.createStudy(task, mode, example);
    else done = await store.createProject($('project-name').value.trim(), { task, mode, example });
    if (done) { rememberProject(); closeDialogs(); showStudy(); }
    else { $('project-error').textContent = store.error || 'Save the current study before continuing.'; $('project-error').hidden = false; }
  } catch (error) { $('project-error').textContent = error.message; $('project-error').hidden = false; }
  finally { $('confirm-project').disabled = false; }
};
$('research-question').oninput = () => store.edit($('research-question').value);
$('save-study').onclick = attempt(() => store.save()); $('menu-save').onclick = attempt(async () => { await store.save(); closeDialogs(); });
$('approach').onchange = () => { const task = $('approach').value; $('approach').value = store.record.task; newDialog('switch', task); };
for (const id of ['observations', 'tree-observations']) $(id).onclick = () => editInputs('observations');
for (const id of ['assumptions', 'tree-assumptions']) $(id).onclick = () => editInputs('assumptions');
$('input-file').onchange = () => { uploadGeneration++; paintEditor(); };
$('input-text').oninput = () => { uploadGeneration++; editor.files[$('input-file').value] = $('input-text').value; editor.dirty = true; backupEditor(); paintStructured(); };
for (const id of ['draws', 'seed']) $(id).oninput = () => {
  uploadGeneration++;
  const value = $(id).value, number = Number(value);
  if (value === '' || !Number.isSafeInteger(number)) { $(id).setAttribute('aria-invalid', 'true'); $(id).setCustomValidity('Enter a whole number within the exact editor range.'); return; }
  $(id).removeAttribute('aria-invalid');
  $(id).setCustomValidity('');
  try { const settings = parseSourceJSON(editor.files['settings.json']); settings.uncertainty[id] = number; editor.files['settings.json'] = JSON.stringify(settings, null, 2) + '\n'; editor.dirty = true; backupEditor(); $('input-text').value = editor.files['settings.json']; }
  catch (error) { $(id).setCustomValidity('Correct the settings file before applying this edit.'); $('file-error').textContent = error.message; $('file-error').hidden = false; }
};
$('input-upload').onchange = async () => {
  const file = $('input-upload').files[0], name = $('input-file').value, generation = ++uploadGeneration, active = editor;
  if (!file) return;
  try {
    if (file.size > (name.endsWith('.csv') ? 512 : 128) * 1024) throw new Error('This file exceeds the study byte limit.');
    const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(await file.arrayBuffer());
    if (generation !== uploadGeneration || editor !== active || !$('files-dialog').open) return;
    editor.files[name] = text; editor.dirty = true; backupEditor(); paintEditor(); $('file-error').hidden = true;
  } catch (error) { if (generation === uploadGeneration) { $('file-error').textContent = error.message; $('file-error').hidden = false; } }
};
function applyEditor() {
  if (!editor) return true;
  if (!$('files-form').reportValidity() || editor.id !== store.record?.id) return false;
  store.edit(store.name, editor.files); editor = null; uploadGeneration++; closeDialogs(); return true;
}
$('files-form').onsubmit = event => { event.preventDefault(); applyEditor(); };
function backupEditor() {
  if (!editor?.dirty || editor.id !== store.record?.id) return;
  try { store.storage?.setItem(store.key(), JSON.stringify({ revision: store.record.revision, name: store.name, files: editor.files, parent: store.record.parent || null })); }
  catch { store.error = 'Browser recovery is unavailable. Apply and save your input changes before leaving.'; }
}
$('files-dialog').addEventListener('close', () => {
  if (editor?.dirty) { if (store.dirty) store.backup(); else store.clearBackup(); }
  editor = null; uploadGeneration++;
});
$('information-dialog').addEventListener('close', () => { if (informationInvoker?.isConnected && !informationInvoker.disabled) informationInvoker.focus(); });
async function beforeNavigate() {
  if (editor?.dirty && !applyEditor()) return false;
  if (!await store.flush()) return false;
  closeDialogs(); return true;
}
async function showResults(attemptId) {
  if (!resultsView) return;
  const opened = await resultsView.show(attemptId);
  if (opened === false) return;
  activeView = 'results'; $('study-body').hidden = true;
  $('study-tab').removeAttribute('aria-current'); $('tree-study').removeAttribute('aria-current'); $('tree-results').setAttribute('aria-current', 'page');
  $('tree-study').classList.remove('active'); $('tree-results').classList.add('active');
  if ($('results-tab')) { $('results-tab').hidden = false; $('results-tab').setAttribute('aria-current', 'page'); }
  if ($('close-results')) $('close-results').hidden = false;
  $('results-heading')?.focus(); render();
}
$('study-form').onsubmit = attempt(async () => {
  const invoker = $('review-study'), validation = await store.review(); if (!validation) return;
  information(validation.valid ? 'Review study' : 'Check the study inputs', validation.valid ? [store.name, `${approaches[store.record.task].label}. Saved revision ${store.record.revision}.`, 'The saved synthetic inputs passed the existing task validation. No analysis has been run.', store.record.frozen_plan ? 'This revision already has a preserved frozen plan.' : 'Freeze this reviewed revision to preserve its inputs. Running the analysis is a separate action.'] : [validation.error || 'The saved inputs need correction. Open observations or assumptions to edit them.'], false, invoker);
  if (validation.valid) {
    const button = node('button', store.record.frozen_plan ? 'Use frozen study' : 'Freeze study', 'primary'); button.id = 'freeze-study'; button.type = 'button';
    button.onclick = attempt(async () => {
      button.disabled = true;
      try { await store.freeze(); informationInvoker = $('check-study'); $('information-dialog').close(); showStudy(); $('check-study')?.focus(); }
      finally { button.disabled = false; }
    });
    $('information-dialog').querySelector('.dialog-actions').prepend(button);
  }
});
$('retry-save').onclick = attempt(() => store.save()); $('reload-study').onclick = attempt(() => store.reloadSaved()); $('save-copy').onclick = attempt(() => store.saveCopy());
$('dismiss-notice').onclick = () => { store.error = ''; render(); };
for (const id of ['all-projects', 'project-switcher', 'menu-projects']) $(id).onclick = attempt(async () => { if (await beforeNavigate() && await store.closeProject()) { resultsView?.hide(); closeDialogs(); $('projects-heading').focus(); } });
$('project-menu').onclick = () => $('actions-dialog').showModal(); $('menu-studies').onclick = attempt(async () => { if (await beforeNavigate()) showStudies(); }); $('choose-study').onclick = $('menu-studies').onclick;
$('create-study').onclick = () => newDialog('study'); $('another-study').onclick = () => newDialog('study');
for (const id of ['study-tab', 'tree-study']) $(id).onclick = showStudy;
$('close-study').onclick = attempt(async () => { if (await beforeNavigate()) { $('study-body').hidden = true; $('study-tab').hidden = true; $('close-study').hidden = true; $('tree-study').focus(); } });
for (const [button, target] of [['tree-project', 'project-children'], ['tree-inputs', 'input-children']]) $(button).onclick = () => { $(target).hidden = !$(target).hidden; $(button).setAttribute('aria-expanded', String(!$(target).hidden)); };
function explorer(show) { $('workbench').classList.toggle('explorer-hidden', !show); $('workbench').classList.toggle('mobile-explorer', show); $('toggle-explorer').setAttribute('aria-expanded', String(show)); $('show-project').setAttribute('aria-expanded', String(show)); }
$('toggle-explorer').onclick = () => explorer($('workbench').classList.contains('explorer-hidden'));
$('show-project').onclick = () => explorer(!matchMedia('(max-width:650px)').matches || !$('workbench').classList.contains('mobile-explorer'));
document.addEventListener('keydown', event => { if (event.key === 'Escape' && matchMedia('(max-width:650px)').matches && $('workbench').classList.contains('mobile-explorer')) { explorer(false); $('show-project').focus(); } });
$('workspace-settings').onclick = () => information('Workspace details', ['Project folder: ' + store.project.path, 'Workspace: ' + store.data.workspace], true);
$('tree-results').onclick = attempt(() => showResults());
if ($('results-tab')) $('results-tab').onclick = attempt(() => showResults());
if ($('close-results')) $('close-results').onclick = () => { resultsView?.hide(); $('results-tab').hidden = true; $('close-results').hidden = true; showStudy(); };
for (const id of ['quit-start', 'quit-workspace']) $(id).onclick = attempt(quit);
for (const b of document.querySelectorAll('.dialog-close')) b.onclick = () => b.closest('dialog').close();
async function saveCurrent() { if (applyEditor()) return store.save(); return false; }
document.addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); attempt(saveCurrent)(); } });
if (desktop) {
  desktop.onCommand(attempt(async command => {
    const buttons = { 'new-project': 'new-project', 'open-project': 'open-project', 'all-projects': 'all-projects', 'toggle-explorer': 'toggle-explorer' };
    if (editor?.dirty && ['new-project', 'open-project', 'all-projects'].includes(command)) {
      const choice = await desktop.confirmEditor();
      if (choice === 'cancel') return;
      if (choice === 'save') { if (!applyEditor() || !await store.flush()) return; }
      else { if (store.dirty) store.backup(); else store.clearBackup(); editor = null; uploadGeneration++; closeDialogs(); }
    }
    if (command === 'save') await saveCurrent();
    else if (buttons[command]) $(buttons[command]).click();
  }));
  desktop.onPrepareClose(async mode => {
    if (mode === 'discard') {
      if (store.savePromise) await store.savePromise;
      clearTimeout(store.timer); if (store.record) store.clearBackup();
      store.dirty = false; editor = null; uploadGeneration++; return { canClose: true };
    }
    if (store.locked && !store.saving) return { canClose: false, busy: true, message: 'A project action is still running. Quitting will stop it and retain the last saved study.' };
    if (editor?.dirty && mode !== 'save') return { canClose: false, message: 'The input editor has unapplied changes. Save them before quitting?' };
    if (mode === 'save' && !applyEditor()) return { canClose: false, message: 'Correct the highlighted input before saving and quitting.' };
    const canClose = await store.flush();
    return { canClose, message: canClose ? '' : store.error || 'The study could not be saved. Your unsaved changes are still open.' };
  });
}
window.addEventListener('beforeunload', event => { if (store.dirty || store.saving || editor?.dirty) { if (editor?.dirty) backupEditor(); else store.backup(); event.preventDefault(); event.returnValue = ''; } });
async function installWorkflow() {
  if (!$('execution-panel')?.tagName || !$('results-body')?.tagName) return;
  const [{ createExecutionView }, { createResultsView }] = await Promise.all([import('/workbench-execution.js'), import('/workbench-results.js')]);
  resultsView = createResultsView({ store, container: $('results-body'), showStudy, beforeNavigate, runPlan: async plan => {
    store.selectPlan(plan); showStudy(); await store.checkPlan();
    if (store.ready) await store.runPlan();
  } });
  executionView = createExecutionView({ store, container: $('execution-panel'), onResults: showResults });
  render();
}
attempt(installWorkflow)();
attempt(() => store.refresh())();
// Also observe actions started in another tab/the full laboratory. Rebuilding
// only changed recent lists preserves keyboard focus during these refreshes.
setInterval(() => { if (!stopped && !store.busy && document.visibilityState === 'visible') attempt(() => store.refresh())(); }, 2000);
