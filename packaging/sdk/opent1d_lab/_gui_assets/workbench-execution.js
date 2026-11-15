// Execution presentation delegates every mutation to the installed SDK controller.
const node = (tag, text, className) => {
  const value = document.createElement(tag);
  if (text !== undefined) value.textContent = text;
  if (className) value.className = className;
  return value;
};
const identified = (label, value) => { const p = node('p', undefined, 'execution-identity'); p.append(node('span', label + ': '), node('code', value)); return p; };

export function createExecutionView({ store, container, onResults }) {
  container.tabIndex = -1;
  const refresh = node('button', 'Refresh saved history', 'secondary'); refresh.id = 'refresh-study'; refresh.type = 'button';
  const title = node('h2', 'Analysis'), draftState = node('p', '', 'muted'); draftState.id = 'execution-draft-state';
  const empty = node('p', 'Review and freeze the saved study to prepare an analysis.', 'muted');
  const controls = node('div', undefined, 'execution-controls'), label = node('label', 'Frozen study'); label.htmlFor = 'execution-plan';
  const select = node('select'); select.id = 'execution-plan';
  const identity = identified('Frozen plan', ''); identity.id = 'execution-plan-identity';
  const explanation = node('p', 'The analysis uses the selected saved plan. Editing Study creates a new revision; frozen inputs and previous attempts remain available.', 'muted');
  const readiness = node('p', '', 'muted'); readiness.id = 'execution-readiness'; readiness.setAttribute('role', 'status');
  const actions = node('div', undefined, 'execution-actions');
  const check = node('button', 'Check readiness', 'secondary'); check.id = 'check-study'; check.type = 'button';
  const run = node('button', 'Run analysis', 'primary'); run.id = 'run-study'; run.type = 'button';
  const cancel = node('button', 'Cancel analysis', 'secondary'); cancel.id = 'cancel-study'; cancel.type = 'button';
  const status = node('div', undefined, 'execution-status'); status.id = 'execution-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const elapsed = node('p', '', 'muted'); elapsed.id = 'execution-elapsed'; elapsed.setAttribute('aria-live', 'off');
  const historyTitle = node('h3', 'Attempts'), history = node('div', undefined, 'execution-attempts'); history.id = 'execution-attempts';
  actions.append(check, run, cancel); controls.append(label, select, identity, explanation, readiness, actions);
  container.replaceChildren(title, refresh, draftState, empty, controls, status, elapsed, historyTitle, history);
  let planSignature = '', historySignature = '', statusSignature = '';
  const stopped = new Set();
  const perform = (fn, next = () => null) => async event => {
    const focused = event?.currentTarget === document.activeElement;
    if (focused) container.focus({ preventScroll: true });
    try { await fn(); } catch (error) { store.error = error.message; store.emit(); }
    finally {
      const target = next();
      if (focused && document.activeElement === container && target?.isConnected && !target.disabled) target.focus();
    }
  };
  const latestResult = () => history.querySelector('.execution-attempt button');
  refresh.onclick = perform(() => store.refreshProject(), () => refresh);
  select.onchange = () => store.selectPlan(select.value);
  check.onclick = perform(() => store.checkPlan(), () => store.ready ? run : check);
  run.onclick = perform(() => store.runPlan(), latestResult);
  cancel.onclick = perform(() => store.cancelRun(), () => cancel.hidden ? latestResult() : cancel);
  const planName = plan => store.project?.labels?.[plan.id] || plan.task;
  function renderAttempts() {
    const plans = store.plans, attempts = store.attempts.filter(attempt => plans.some(plan => plan.id === attempt.plan && ['mmtt-sensitivity', 'mmtt-sampling'].includes(plan.task)));
    const signature = JSON.stringify([attempts, plans, store.locked, store.ready, store.selectedPlanId]);
    if (signature === historySignature) return;
    historySignature = signature;
    historyTitle.hidden = !attempts.length;
    history.replaceChildren(...attempts.slice().reverse().map(attempt => {
      const plan = plans.find(value => value.id === attempt.plan), result = typeof attempt.outcome === 'object' ? attempt.outcome : null;
      const row = node('article', undefined, 'execution-attempt'); row.dataset.attempt = attempt.id;
      row.append(node('h4', `${planName(plan)} · attempt ${attempt.ordinal}`));
      const slots = Object.values(result?.slot_statuses || {}), complete = slots.filter(value => value === 'complete').length;
      row.append(node('p', result ? `${result.completeness} · execution ${result.execution_status} · ${complete}/${slots.length} planned slots complete` : 'Unfinished · no terminal outcome was observed. Saved inputs and partial evidence are retained.'));
      const details = node('details'); details.append(node('summary', 'Plan and attempt identities'), identified('Plan', attempt.plan), identified('Attempt', attempt.id));
      if (attempt.retry_of) details.append(identified('Retry of', attempt.retry_of));
      if (result) {
        details.append(node('p', `Payload: ${result.payload || 'unavailable'}`));
        if (result.error) details.append(node('p', result.error));
        if (slots.length) { const list = node('ul'); for (const [slot, value] of Object.entries(result.slot_statuses)) list.append(node('li', `${slot}: ${value}`)); details.append(list); }
      }
      row.append(details);
      const buttons = node('div', undefined, 'execution-actions');
      const inspect = node('button', 'Open results', 'secondary'); inspect.type = 'button'; inspect.disabled = store.locked; inspect.onclick = perform(() => onResults(attempt.id)); buttons.append(inspect);
      const latest = attempts.filter(value => value.plan === attempt.plan).at(-1);
      if (result && latest?.id === attempt.id) {
        const retry = node('button', 'Run a new attempt', 'secondary'); retry.type = 'button'; retry.disabled = store.locked;
        retry.onclick = perform(async () => { store.selectPlan(attempt.plan); if (!store.ready) await store.checkPlan(); if (store.ready) await store.runPlan(); }, latestResult); buttons.append(retry);
      }
      if (!result) {
        const recovery = node('div', undefined, 'attempt-recovery'), consent = node('label'), checkbox = node('input'); checkbox.type = 'checkbox'; checkbox.checked = stopped.has(attempt.id); checkbox.disabled = store.locked;
        consent.append(checkbox, document.createTextNode(' I have confirmed that the previous executor has stopped.'));
        const recover = node('button', 'Recover unfinished attempt', 'secondary'); recover.type = 'button'; recover.disabled = store.locked || !checkbox.checked;
        checkbox.onchange = () => { if (checkbox.checked) stopped.add(attempt.id); else stopped.delete(attempt.id); recover.disabled = store.locked || !checkbox.checked; };
        recover.onclick = perform(() => store.recoverAttempt(attempt.id, checkbox.checked), latestResult);
        recovery.append(node('p', 'Recovery records an interrupted outcome. It does not adopt or signal the previous process.', 'muted'), consent, recover); row.append(recovery);
      }
      row.append(buttons); return row;
    }));
  }
  function render() {
    const plans = store.plans.filter(plan => ['mmtt-sensitivity', 'mmtt-sampling'].includes(plan.task)), selected = store.selectedPlan;
    container.hidden = !store.project || (!store.record && !plans.length);
    refresh.disabled = store.locked;
    const record = store.record;
    draftState.textContent = record ? `Study revision ${record.revision}${store.dirty ? ' · unsaved edits' : record.frozen_plan ? ' · frozen' : record.validation?.valid === true ? ' · reviewed' : ' · draft'}` : 'No editable study is open.';
    empty.hidden = !!plans.length; controls.hidden = !plans.length;
    const signature = JSON.stringify([plans, store.project?.labels]);
    if (signature !== planSignature) {
      planSignature = signature;
      const placeholder = node('option', 'Choose a frozen study'); placeholder.value = '';
      select.replaceChildren(placeholder, ...plans.map(plan => { const option = node('option', `${planName(plan)} · ${plan.id.slice(0, 12)}`); option.value = plan.id; return option; }));
    }
    select.value = store.selectedPlanId || ''; select.disabled = store.locked;
    identity.querySelector('code').textContent = selected?.id || 'Choose a frozen study';
    const checked = store.readiness?.plan === store.selectedPlanId && store.readiness?.project === store.projectId;
    readiness.textContent = store.ready ? 'Ready to run · saved metadata and runtime checked.' : checked ? 'This plan is not ready. Inspect the reported error and check again.' : 'Check the selected frozen plan before running.';
    check.disabled = store.locked || !selected;
    const latest = store.attempts.filter(attempt => attempt.plan === store.selectedPlanId).at(-1);
    run.textContent = latest ? 'Run a new attempt' : 'Run analysis'; run.disabled = store.locked || !store.ready || !!latest && (typeof latest.outcome !== 'object' || !latest.outcome);
    const active = store.activeJob, own = active?.project === store.projectId;
    cancel.hidden = !own || !active.cancelable; cancel.disabled = !own || !active.cancelable || active.cancel_requested;
    cancel.textContent = active?.cancel_requested ? 'Cancellation requested' : 'Cancel analysis';
    const job = own ? active : store.lastAction?.project === store.projectId && store.lastAction.status === 'error' ? store.lastAction : null;
    elapsed.hidden = !job || job.status !== 'running'; elapsed.textContent = job ? `${job.elapsed_seconds || 0}s elapsed` : '';
    const nextStatus = JSON.stringify(job && [job.id, job.status, job.phase, job.cancel_requested, job.error]);
    if (nextStatus !== statusSignature) {
      statusSignature = nextStatus; status.replaceChildren();
      if (job) {
        status.append(node('strong', job.cancel_requested ? 'Stopping analysis' : job.status === 'error' ? 'Action refused or interrupted' : 'Action in progress'), node('p', job.error || job.phase || job.operation));
        if (job.arguments?.plan) status.append(identified('Plan', job.arguments.plan));
        status.append(identified('Action', job.id));
      }
    }
    status.hidden = !job; renderAttempts();
  }
  return { render };
}
