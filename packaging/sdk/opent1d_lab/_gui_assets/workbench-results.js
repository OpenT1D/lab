// Presentation only: native readers own every scientific value and comparison.
import { approaches } from './workbench-store.js';

const supported = task => Object.hasOwn(approaches, task);
const node = (tag, text, className) => {
  const value = document.createElement(tag);
  if (text !== undefined) value.textContent = text;
  if (className) value.className = className;
  return value;
};
const short = value => value?.slice(0, 12) || 'unavailable';
const planLabel = (plan, project) => `${project?.labels?.[plan.id] || approaches[plan.task]?.label || plan.task} · ${short(plan.id)}`;
function choices(select, items, selected) {
  const signature = JSON.stringify(items);
  if (select.dataset.choices !== signature) {
    select.replaceChildren(...items.map(([value, label]) => { const option = node('option', label); option.value = value; return option; }));
    select.dataset.choices = signature;
  }
  if (selected !== undefined) select.value = selected;
  if (select.selectedIndex < 0 && items.length) select.selectedIndex = 0;
}
function table(headers, rows, caption) {
  const wrapper = node('div', undefined, 'results-table-scroll'), value = node('table');
  wrapper.tabIndex = 0; wrapper.setAttribute('role', 'region'); wrapper.setAttribute('aria-label', caption);
  value.append(node('caption', caption));
  const head = node('thead'), row = node('tr');
  for (const text of headers) { const cell = node('th', text); cell.scope = 'col'; row.append(cell); }
  head.append(row); value.append(head);
  const body = node('tbody');
  for (const cells of rows) { const row = node('tr'); for (const text of cells) row.append(node('td', text)); body.append(row); }
  value.append(body); wrapper.append(value); return wrapper;
}
function tableCells(line) {
  const cells = []; let start = 0, slashes = 0;
  for (let i = 0; i < line.length; i++) {
    if (line[i] === '|' && slashes % 2 === 0) { cells.push(line.slice(start, i)); start = i + 1; }
    slashes = line[i] === '\\' ? slashes + 1 : 0;
  }
  cells.push(line.slice(start));
  return cells.slice(1, -1).map(value => value.trim().replaceAll('\\|', '|').replaceAll('**', ''));
}
function markdown(text, container) {
  const nodes = [], lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]; if (!line.trim()) continue;
    if (line.startsWith('|')) {
      const rows = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        const cells = tableCells(lines[i]);
        if (!cells.every(value => /^[:\- ]+$/.test(value))) rows.push(cells);
        i++;
      }
      i--; if (rows.length) nodes.push(table(rows[0], rows.slice(1), 'Native report table'));
    } else if (line.startsWith('#')) nodes.push(node(line.startsWith('###') ? 'h4' : 'h3', line.replace(/^#+\s*/, '')));
    else nodes.push(node('p', line.replaceAll('**', '')));
  }
  container.replaceChildren(...nodes);
}

export function createResultsView({ store, container, showStudy = () => {}, beforeNavigate = () => store.flush() }) {
  let projectId = null, active = false, mode = 'attempts', pending = false, epoch = 0, reportEpoch = 0;
  let selectedAttempt = '', selectedPlan = '', selectedComparison = '', loadedComparison = null, available = [];
  let report = null, imageURL = null, roster = [], nextId = 1, attemptSignature = '', comparisonSignature = '';
  const refused = new Set(), draftCopies = new Map();
  const ui = {};
  container.classList.add('results-view');
  const element = (tag, id, text, className) => { const value = node(tag, text, className); if (id) { value.id = id; ui[id] = value; } return value; };
  const button = (id, text, action, primary = false) => {
    const value = element('button', id, text, primary ? 'primary' : 'secondary'); value.type = 'button'; value.onclick = action; return value;
  };
  const field = (id, label, tag = 'select') => {
    const wrapper = node('label', undefined, 'results-field'); wrapper.append(node('span', label));
    const control = element(tag, id); wrapper.append(control); return wrapper;
  };
  const heading = element('h2', 'results-heading', 'Results'); heading.tabIndex = -1;
  const intro = node('p', 'Inspect a saved attempt or a prospectively frozen comparison. Earlier attempts and all planned cases remain in the project.', 'muted');
  const modes = node('div', undefined, 'results-actions'); modes.setAttribute('aria-label', 'Result views');
  modes.append(button('results-attempts-mode', 'Saved attempts', () => setMode('attempts')), button('results-comparison-mode', 'Planned comparison', () => setMode('comparison')));
  const message = element('p', 'results-message', '', 'results-message'); message.setAttribute('role', 'status'); message.setAttribute('aria-live', 'polite'); message.hidden = true;
  const attemptsPanel = element('section', 'results-attempts'); attemptsPanel.setAttribute('aria-label', 'Saved attempts');
  const attemptFields = node('div', undefined, 'results-fields');
  attemptFields.append(field('results-plan', 'Frozen plan'), field('results-attempt', 'Saved attempt'));
  const attemptSummary = element('div', 'results-attempt-summary');
  const attemptActions = node('div', undefined, 'results-actions');
  const allowLabel = node('label', undefined, 'results-check');
  const allowFailed = element('input', 'results-allow-failed'); allowFailed.type = 'checkbox';
  allowLabel.append(allowFailed, node('span', 'Include incomplete native evidence'));
  attemptActions.append(button('results-verify', 'Verify saved report', verifyAttempt, true), button('results-back-study', 'Back to Study', () => showStudy()));
  attemptsPanel.append(attemptFields, attemptSummary, allowLabel, attemptActions);

  const comparisonPanel = element('section', 'results-comparison'); comparisonPanel.setAttribute('aria-label', 'Planned comparisons');
  comparisonPanel.append(node('p', 'Freeze a question and the full roster before any selected plan runs. Comparisons retain each plan’s first attempt; retries never replace it.', 'results-contract'));
  const comparisonFields = node('div', undefined, 'results-fields'); comparisonFields.append(field('results-comparison-select', 'Frozen comparison'));
  const comparisonActions = node('div', undefined, 'results-actions');
  comparisonActions.append(button('results-comparison-open', 'Inspect comparison', () => inspectComparison()), button('results-comparison-verify', 'Verify comparison report', () => verifyComparison(null), true), button('results-comparison-next', 'Run next planned analysis', runNext));
  const comparisonSummary = element('div', 'results-comparison-summary');
  const replay = node('details'); replay.append(node('summary', 'Reconstruct an earlier saved snapshot'));
  const replayField = field('results-comparison-tip', 'Saved ledger tip', 'input'); ui['results-comparison-tip'].maxLength = 64;
  replay.append(replayField, button('results-comparison-replay', 'Verify saved snapshot', () => verifyComparison(ui['results-comparison-tip'].value.trim())));
  const create = node('details'); create.append(node('summary', 'Plan a new comparison'));
  const form = element('form', 'results-comparison-form');
  const definitionFields = node('div', undefined, 'results-fields');
  definitionFields.append(field('results-comparison-name', 'Comparison name', 'input'), field('results-comparison-question', 'Research question', 'textarea'));
  for (const [id, max] of [['results-comparison-name', 100], ['results-comparison-question', 1000]]) { ui[id].required = true; ui[id].maxLength = max; ui[id].oninput = keepDraft; }
  const memberFields = node('div', undefined, 'results-fields');
  memberFields.append(field('results-member-plan', 'Unused frozen plan'));
  const memberActions = node('div', undefined, 'results-actions'); memberActions.append(button('results-member-options', 'Read available variants', loadOptions));
  const selectorFields = node('div', undefined, 'results-fields');
  selectorFields.append(field('results-member-selector', 'Native variant or schedule'), field('results-member-label', 'Member label (optional)', 'input'));
  ui['results-member-label'].maxLength = 100;
  memberActions.append(button('results-member-add', 'Add planned member', addMember));
  const rosterList = element('div', 'results-roster');
  const baselineField = field('results-comparison-baseline', 'Baseline member'); ui['results-comparison-baseline'].onchange = keepDraft;
  const rosterNote = element('p', 'results-roster-note', '', 'muted');
  const freeze = button('results-comparison-freeze', 'Freeze comparison', null, true); freeze.type = 'submit';
  form.append(definitionFields, memberFields, selectorFields, memberActions, rosterList, baselineField, rosterNote, freeze);
  form.onsubmit = freezeComparison; create.append(form);
  comparisonPanel.append(comparisonFields, comparisonActions, comparisonSummary, replay, create);

  const saved = element('section', 'results-report'); saved.setAttribute('aria-label', 'Verified native report'); saved.hidden = true;
  const reportTop = node('div', undefined, 'results-report-top'); reportTop.append(node('h3', 'Verified native report'), element('strong', 'results-report-completeness'));
  const context = element('p', 'results-report-context', '', 'muted');
  const exports = element('div', 'results-exports', undefined, 'results-actions'); exports.setAttribute('aria-label', 'Export verified evidence');
  const limits = element('p', 'results-limits', '', 'results-contract');
  const figure = element('img', 'results-figure'); figure.alt = 'Native report figure; corresponding values and limitations follow in the report.'; figure.hidden = true;
  const reportText = element('div', 'results-report-text', undefined, 'results-report-text');
  const children = element('div', 'results-child-reports');
  saved.append(reportTop, context, exports, limits, figure, reportText, children);
  container.replaceChildren(heading, intro, modes, message, attemptsPanel, comparisonPanel, saved);

  function plans() { return (store.plans || store.project?.info?.plans || []).filter(plan => supported(plan.task)); }
  function attempts() { const allowed = new Set(plans().map(plan => plan.id)); return (store.attempts || store.project?.info?.attempts || []).filter(attempt => allowed.has(attempt.plan)); }
  function busy() { return store.locked || pending; }
  function current(token) { return active && token.epoch === epoch && token.project === store.projectId; }
  function token() { return { epoch, project: store.projectId }; }
  function notice(text = '', error = false) {
    message.textContent = text; message.hidden = !text; message.classList.toggle('results-error', error);
    message.setAttribute('role', error ? 'alert' : 'status');
  }
  async function task(label, action) {
    if (busy()) return;
    const expected = token(); pending = true; notice(label); render();
    try { await action(expected); }
    catch (error) { if (current(expected)) notice(error.message || 'The action did not complete. Try again.', true); }
    finally { pending = false; render(); }
  }
  function withdraw() {
    reportEpoch++; report = null; saved.hidden = true; reportText.replaceChildren(); children.replaceChildren(); exports.replaceChildren();
    if (imageURL) URL.revokeObjectURL(imageURL); imageURL = null; figure.removeAttribute('src'); figure.hidden = true;
  }
  function setMode(next) {
    if (next === mode) return;
    mode = next; epoch++; withdraw(); notice(); render(); heading.focus();
  }
  function draftKey() { return `opent1d.comparison-draft/1:${store.data?.workspace}:${projectId}`; }
  function definition() {
    return { schema: 'opent1d.plan-comparison/1', name: ui['results-comparison-name'].value, question: ui['results-comparison-question'].value, baseline: ui['results-comparison-baseline'].value, variants: roster };
  }
  function keepDraft() {
    if (!projectId) return;
    const value = definition(); draftCopies.set(projectId, value);
    try { store.storage?.setItem(draftKey(), JSON.stringify(value)); } catch { /* The unsaved roster remains in this window. */ }
  }
  function restoreDraft() {
    let value = draftCopies.get(projectId);
    try { value ||= JSON.parse(store.storage?.getItem(draftKey()) || 'null'); } catch { /* Ignore unavailable optional recovery. */ }
    roster = Array.isArray(value?.variants) && value.variants.length <= 16 && value.variants.every(member => typeof member.id === 'string' && typeof member.label === 'string' && typeof member.plan === 'string' && member.selector && typeof member.selector === 'object') ? value.variants : [];
    nextId = 1; while (roster.some(member => member.id === 'member-' + nextId)) nextId++;
    ui['results-comparison-name'].value = typeof value?.name === 'string' ? value.name : '';
    ui['results-comparison-question'].value = typeof value?.question === 'string' ? value.question : '';
    paintRoster(value?.baseline);
  }
  function paintRoster(baseline = ui['results-comparison-baseline'].value) {
    ui['results-roster'].replaceChildren(...roster.map(member => {
      const row = node('div', undefined, 'results-roster-row'); row.append(node('p', `${member.label} · plan ${short(member.plan)} · ${JSON.stringify(member.selector)}`));
      const remove = button(null, 'Remove ' + member.label, () => { roster = roster.filter(item => item.id !== member.id); paintRoster(); keepDraft(); render(); });
      row.append(remove); return row;
    }));
    choices(ui['results-comparison-baseline'], roster.map(member => [member.id, member.label]), baseline);
  }
  function selectionChanged() { epoch++; attemptSignature = ''; withdraw(); notice(); allowFailed.checked = false; render(); }
  ui['results-plan'].onchange = () => { selectedPlan = ui['results-plan'].value; selectedAttempt = ''; selectionChanged(); };
  ui['results-attempt'].onchange = () => { selectedAttempt = ui['results-attempt'].value; selectionChanged(); };
  ui['results-comparison-select'].onchange = () => { selectedComparison = ui['results-comparison-select'].value; loadedComparison = null; comparisonSignature = ''; epoch++; withdraw(); notice(); render(); };
  ui['results-member-plan'].onchange = () => { available = []; choices(ui['results-member-selector'], []); render(); };

  function renderAttempts() {
    const list = plans(), all = attempts();
    choices(ui['results-plan'], [['', 'All frozen plans'], ...list.map(plan => [plan.id, planLabel(plan, store.project)])], selectedPlan);
    selectedPlan = ui['results-plan'].value;
    const visible = all.filter(attempt => !selectedPlan || attempt.plan === selectedPlan).slice().reverse();
    choices(ui['results-attempt'], visible.map(attempt => [attempt.id, `Attempt ${attempt.ordinal} · ${short(attempt.plan)} · ${attempt.outcome?.completeness || 'unfinished'}`]), selectedAttempt || visible[0]?.id);
    selectedAttempt = ui['results-attempt'].value;
    const attempt = all.find(item => item.id === selectedAttempt), outcome = typeof attempt?.outcome === 'object' ? attempt.outcome : null;
    const signature = JSON.stringify(attempt || [selectedPlan, list.length]);
    if (signature !== attemptSignature) {
      attemptSignature = signature; attemptSummary.replaceChildren();
      if (!attempt) {
        attemptSummary.append(node('p', selectedPlan ? 'No attempts for this frozen plan. Run it explicitly from Study.' : 'No saved attempts yet. Validate and freeze a Study, then run its analysis.', 'results-empty'));
      } else {
        const plan = list.find(item => item.id === attempt.plan);
        attemptSummary.append(node('h3', `Attempt ${attempt.ordinal} · ${outcome?.completeness || 'unfinished'}`), node('p', planLabel(plan, store.project), 'muted'));
        if (outcome) {
          const slots = Object.entries(outcome.slot_statuses || {}), complete = slots.filter(([, status]) => status === 'complete').length;
          attemptSummary.append(node('p', `Execution: ${outcome.execution_status}. Evidence: ${outcome.completeness}. ${complete}/${slots.length} planned slots complete.`));
          const details = node('details'); details.append(node('summary', 'All planned slots'), table(['Planned slot', 'Status'], slots, 'Complete planned slot accounting')); attemptSummary.append(details);
          if (outcome.payload !== 'native') attemptSummary.append(node('p', 'No admissible native report is available. The failure ledger and forensic files are retained in the project.', 'results-contract'));
          else if (outcome.completeness !== 'complete') attemptSummary.append(node('p', 'Incomplete evidence cannot support a complete conclusion. Include it explicitly to inspect the native failure and missing-case accounting.', 'results-contract'));
        } else attemptSummary.append(node('p', 'Unfinished or unobserved execution. No completed outcome has been recorded. Confirm the old executor has stopped before explicit CLI recovery.', 'results-contract'));
        const identity = node('details'); identity.append(node('summary', 'Frozen plan and attempt identities'), node('p', 'Plan: ' + attempt.plan), node('p', 'Attempt: ' + attempt.id));
        if (attempt.retry_of) identity.append(node('p', 'Retry of: ' + attempt.retry_of)); attemptSummary.append(identity);
      }
    }
    ui['results-plan'].disabled = busy() || !list.length; ui['results-attempt'].disabled = busy() || !visible.length;
    ui['results-verify'].disabled = busy() || !outcome || outcome.payload !== 'native';
    ui['results-verify'].textContent = outcome?.completeness === 'complete' ? 'Verify saved report' : 'Verify incomplete evidence';
    allowLabel.hidden = !outcome || outcome.payload !== 'native' || outcome.completeness === 'complete'; allowFailed.disabled = busy();
  }
  function renderComparisons() {
    const entries = (store.project?.info?.comparisons || []).filter(item => supported(item.task));
    choices(ui['results-comparison-select'], entries.map(item => [item.id, `${item.name} · ${item.members} planned members`]), selectedComparison);
    selectedComparison = ui['results-comparison-select'].value;
    const used = new Set(attempts().map(attempt => attempt.plan)), unused = plans().filter(plan => !used.has(plan.id));
    const previous = ui['results-member-plan'].value;
    choices(ui['results-member-plan'], unused.map(plan => [plan.id, planLabel(plan, store.project)]), previous);
    if (previous !== ui['results-member-plan'].value) { available = []; choices(ui['results-member-selector'], []); }
    const stale = !!loadedComparison && loadedComparison.snapshot.tip !== store.project?.info?.head?.tip;
    const signature = JSON.stringify([loadedComparison, stale, entries.length]);
    if (signature !== comparisonSignature) {
      comparisonSignature = signature; comparisonSummary.replaceChildren();
      if (!loadedComparison) comparisonSummary.append(node('p', entries.length ? 'Inspect a frozen comparison to read its question, full roster and first-attempt statuses.' : 'No frozen comparisons yet. Plan the complete comparison before running its member plans.', 'results-empty'));
      else {
        const value = loadedComparison;
        comparisonSummary.append(node('h3', value.name), node('p', value.question), node('p', `Frozen comparison · ${value.variants.length} planned members · baseline ${value.variants.find(member => member.id === value.baseline)?.label || value.baseline}. First attempts only.`, 'results-contract'));
        const rows = value.variants.map(member => { const attempt = value.attempts[member.plan]; return [member.label, JSON.stringify(member.selector), member.plan, attempt.status, attempt.completeness || 'evidence not yet available', attempt.attempt || 'unattempted']; });
        comparisonSummary.append(table(['Planned member', 'Native selector', 'Frozen plan', 'First-attempt execution', 'Evidence', 'First attempt'], rows, 'All planned comparison members'));
        const changes = node('details'); changes.append(node('summary', 'Changed fields from baseline'), node('pre', value.changes_text));
        comparisonSummary.append(changes, node('p', 'Saved ledger tip: ' + value.snapshot.tip, 'muted'));
        if (stale) comparisonSummary.append(node('p', 'The project ledger changed. Inspect the comparison again before running the next planned analysis. Earlier verified report snapshots remain reproducible.', 'results-contract'));
      }
    }
    for (const id of ['results-comparison-select', 'results-comparison-open', 'results-comparison-verify', 'results-comparison-replay']) ui[id].disabled = busy() || !entries.length;
    ui['results-comparison-next'].disabled = busy() || !loadedComparison || stale || !Object.values(loadedComparison.attempts).some(attempt => attempt.status === 'unattempted') || attempts().some(attempt => attempt.outcome === 'unfinished');
    ui['results-member-plan'].disabled = busy() || !unused.length; ui['results-member-options'].disabled = busy() || !unused.length;
    ui['results-member-selector'].disabled = busy() || !available.length; ui['results-member-add'].disabled = busy() || !available.length || roster.length >= 16;
    const attemptedMember = roster.some(member => used.has(member.plan));
    ui['results-comparison-freeze'].disabled = busy() || roster.length < 2 || attemptedMember;
    ui['results-roster-note'].textContent = attemptedMember ? 'A planned member has already been attempted. Remove it and derive a fresh frozen plan before freezing this comparison.' : `${roster.length}/16 planned members. Include every intended member; failed and unattempted cases stay in the denominator.`;
    for (const button of ui['results-roster'].querySelectorAll('button')) button.disabled = busy();
  }
  function render() {
    for (const item of store.data?.reports || []) if (!item.valid) refused.add(item.id);
    if (projectId !== store.projectId) {
      keepDraft(); projectId = store.projectId; epoch++; selectedPlan = ''; selectedAttempt = ''; selectedComparison = ''; loadedComparison = null; available = []; attemptSignature = ''; comparisonSignature = ''; withdraw(); notice();
      restoreDraft();
    }
    if (report && (!store.data?.reports?.some(item => item.id === report.id && item.valid) || refused.has(report.id))) { withdraw(); notice('This report copy is unavailable. Verify the saved evidence again.', true); }
    attemptsPanel.hidden = mode !== 'attempts'; comparisonPanel.hidden = mode !== 'comparison';
    for (const [id, value] of [['results-attempts-mode', 'attempts'], ['results-comparison-mode', 'comparison']]) ui[id].setAttribute('aria-pressed', String(mode === value));
    renderAttempts(); renderComparisons();
    for (const button of exports.querySelectorAll('button')) button.disabled = busy();
  }
  async function verifyAttempt() {
    const attempt = selectedAttempt, include = allowFailed.checked;
    await task('Verifying the saved native evidence…', async expected => {
      withdraw();
      const result = await store.action('verify', { attempt, allow_failed: include });
      if (current(expected) && mode === 'attempts' && selectedAttempt === attempt) await showReport(result.report, expected);
    });
  }
  async function loadOptions() {
    const plan = ui['results-member-plan'].value;
    await task('Reading native comparison options…', async expected => {
      const result = await store.action('comparison_options', { plan });
      if (!current(expected) || ui['results-member-plan'].value !== plan) return;
      available = result.options; choices(ui['results-member-selector'], available.map(item => [JSON.stringify(item.selector), item.label])); notice('Choose a native variant or schedule and add it to the planned roster.');
    });
  }
  function addMember() {
    if (busy()) return;
    const plan = ui['results-member-plan'].value, choice = available.find(item => JSON.stringify(item.selector) === ui['results-member-selector'].value);
    if (!choice || roster.length >= 16) return;
    const label = ui['results-member-label'].value.trim() || choice.label;
    if (roster.some(member => member.label === label || member.plan === plan && JSON.stringify(member.selector) === JSON.stringify(choice.selector))) { notice('Choose a unique member label and plan/variant combination.', true); return; }
    while (roster.some(member => member.id === 'member-' + nextId)) nextId++;
    roster = [...roster, { id: 'member-' + nextId++, label, plan, selector: choice.selector }];
    ui['results-member-label'].value = ''; paintRoster(); keepDraft(); notice(); render();
  }
  async function freezeComparison(event) {
    event.preventDefault();
    if (!form.reportValidity() || roster.length < 2) return;
    const submitted = JSON.stringify(definition()), value = JSON.parse(submitted);
    await task('Freezing the question and complete comparison roster…', async expected => {
      const result = await store.action('comparison_freeze', { definition: value });
      if (!current(expected)) return;
      if (JSON.stringify(definition()) === submitted) { roster = []; ui['results-comparison-name'].value = ''; ui['results-comparison-question'].value = ''; paintRoster(); keepDraft(); }
      selectedComparison = result.comparison; loadedComparison = null; withdraw(); render();
      const view = await store.action('comparison_open', { comparison: result.comparison, at: null });
      if (current(expected) && selectedComparison === result.comparison) { loadedComparison = view; notice('Comparison frozen before execution. Every planned member and each plan’s first attempt will be retained.'); }
    });
  }
  async function inspectComparison() {
    const comparison = selectedComparison;
    await task('Reading the frozen comparison…', async expected => {
      const result = await store.action('comparison_open', { comparison, at: null });
      if (current(expected) && selectedComparison === comparison) { loadedComparison = result; notice('Frozen question, full roster and first-attempt statuses read. No analysis was run.'); }
    });
  }
  async function verifyComparison(at) {
    if (at === '') { notice('Enter a saved ledger tip to reconstruct that exact snapshot.', true); return; }
    const comparison = selectedComparison;
    await task('Reconstructing all planned comparison evidence…', async expected => {
      withdraw();
      const result = await store.action('comparison_verify', { comparison, at });
      if (current(expected) && mode === 'comparison' && selectedComparison === comparison) await showReport(result.report, expected);
    });
  }
  async function runNext() {
    if (!loadedComparison || loadedComparison.snapshot.tip !== store.project?.info?.head?.tip) return;
    const comparison = selectedComparison, plan = loadedComparison.variants.map(member => member.plan).find(plan => loadedComparison.attempts[plan].status === 'unattempted');
    if (!plan) return;
    await task('Running the next planned analysis. Its first attempt will remain in this comparison…', async expected => {
      await store.action('run', { plan, retry_of: null });
      if (!current(expected) || selectedComparison !== comparison) return;
      const value = await store.action('comparison_open', { comparison, at: null });
      if (current(expected) && selectedComparison === comparison) { loadedComparison = value; notice('Planned attempt retained. Verify the comparison to reconstruct the current complete denominator.'); }
    });
  }
  async function fetchReport(record, name) {
    if (refused.has(record.id)) throw new Error('This report copy is unavailable. Verify the saved evidence again.');
    const path = `/api/reports/${record.id}/${name}`;
    const response = store.reportRequest ? await store.reportRequest(path) : await store.fetcher(path, { headers: { 'X-OpenT1D-Token': store.token }, cache: 'no-store' });
    if (!response.ok) { let value; try { value = await response.json(); } catch { /* Fixed fallback below. */ } throw new Error(value?.error || 'The verified report download was refused. Verify the saved evidence again.'); }
    return response;
  }
  function reportRefused(error, record) {
    refused.add(record.id);
    if (report?.id === record.id) { withdraw(); notice(error.message, true); }
  }
  function exportButton(record, name, label) {
    return button(null, label, async () => {
      const expected = token(), selectedReport = report?.id;
      try {
        const blob = await (await fetchReport(record, name)).blob();
        if (!current(expected) || report?.id !== selectedReport || refused.has(record.id)) return;
        const url = URL.createObjectURL(blob), link = node('a'); link.href = url; link.download = name.replaceAll('/', '-');
        link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); notice('Verified native ' + name + ' exported.');
      } catch (error) { if (current(expected)) reportRefused(error, record); }
    });
  }
  function nativeChildren(record) {
    children.replaceChildren();
    for (const name of record.files.filter(name => /^studies\/[a-z][a-z0-9_-]{0,63}\/report\.md$/.test(name))) {
      const details = node('details'), content = node('div', undefined, 'results-report-text'), actions = node('div', undefined, 'results-actions');
      details.append(node('summary', 'Native analysis · schedule ' + name.split('/')[1]));
      actions.append(button(null, 'Read native analysis', async () => {
        const expected = token();
        try { const text = await (await fetchReport(record, name)).text(); if (current(expected) && report?.id === record.id) markdown(text, content); }
        catch (error) { if (current(expected)) reportRefused(error, record); }
      }), exportButton(record, name, 'Export schedule report'), exportButton(record, name.replace(/\.md$/, '.json'), 'Export schedule JSON'));
      details.append(actions, content); children.append(details);
    }
  }
  async function showReport(identity, expected) {
    const issued = ++reportEpoch, record = store.data?.reports?.find(item => item.id === identity);
    if (!record || record.project !== projectId || !record.valid || refused.has(identity)) throw new Error('The verified report pointer is unavailable. Verify the saved evidence again.');
    let nextURL;
    try {
      const text = await (await fetchReport(record, 'report.md')).text();
      if (record.files.includes('figure.svg')) nextURL = URL.createObjectURL(await (await fetchReport(record, 'figure.svg')).blob());
      if (!current(expected) || issued !== reportEpoch || refused.has(identity) || !store.data?.reports?.some(item => item.id === identity && item.valid)) { if (nextURL) URL.revokeObjectURL(nextURL); return; }
      if (imageURL) URL.revokeObjectURL(imageURL); imageURL = nextURL || null;
      report = record; markdown(text, reportText); nativeChildren(record);
      ui['results-report-completeness'].textContent = record.completeness;
      context.textContent = `Verified ${new Date(record.verified_at).toLocaleString()} · ` + (record.comparison ? `comparison ${record.comparison} · saved ledger tip ${record.snapshot.tip}` : `attempt ${record.attempt} · frozen plan ${attempts().find(attempt => attempt.id === record.attempt)?.plan || 'unavailable'}`);
      const task = record.comparison ? loadedComparison?.task || (store.project?.info?.comparisons || []).find(item => item.id === record.comparison)?.task : plans().find(plan => plan.id === attempts().find(attempt => attempt.id === record.attempt)?.plan)?.task;
      limits.textContent = task === 'mmtt-sampling' ? 'Synthetic observations only. Full curves are references, not biological truth. Development-only schedule selection is frozen before evaluation. The native report retains all planned cases, exclusions and failures.' : 'Synthetic observations only. The endpoint is whole-body total endogenous secretion, including basal, over observed 0–120 minutes (pmol). Change is follow-up minus baseline. Assumption sensitivity does not establish biological validity or a clinical conclusion.';
      exports.replaceChildren(...[['report.md', 'Export report'], ['report.json', 'Export report JSON'], ['figure.svg', 'Export native figure'], ['comparison.csv', 'Export comparison table']].filter(([name]) => record.files.includes(name)).map(([name, label]) => exportButton(record, name, label)));
      figure.hidden = !imageURL; if (imageURL) figure.src = imageURL;
      saved.hidden = false; notice(record.completeness === 'complete' ? 'Saved native report verified. No analysis was rerun.' : 'Incomplete native evidence verified. Missing, failed and unattempted cases remain visible.');
    } catch (error) { if (nextURL && nextURL !== imageURL) URL.revokeObjectURL(nextURL); if (current(expected) && issued === reportEpoch) { refused.add(identity); withdraw(); throw error; } }
  }
  async function show(attemptId) {
    if (!await beforeNavigate()) return false;
    active = true; render();
    if (attemptId && attempts().some(attempt => attempt.id === attemptId)) { mode = 'attempts'; selectedPlan = ''; selectedAttempt = attemptId; selectionChanged(); }
    container.hidden = false; heading.focus(); return true;
  }
  function hide() { active = false; epoch++; withdraw(); container.hidden = true; }
  function destroy() { hide(); keepDraft(); container.replaceChildren(); }
  render();
  return { render, show, hide, destroy };
}
