// Presentation state only. Projects, immutable revisions and validation belong
// to the existing installed GUI controller and public SDK services.
export const approaches = {
  'mmtt-sensitivity': { label: 'Compare paired responses', question: 'How do the two synthetic meal tests compare?', files: ['package.json', 'observations.csv', 'settings.json'] },
  'mmtt-sampling': { label: 'Compare measurement schedules', question: 'How do reduced measurement schedules affect the estimate?', files: ['package.json', 'observations.csv', 'settings.json', 'design.json', 'development-package.json', 'development-observations.csv'] },
};

export class WorkbenchStore {
  constructor({ token, fetcher = globalThis.fetch.bind(globalThis), storage = globalThis.localStorage, notify = () => {} }) {
    Object.assign(this, { token, fetcher, storage, notify });
    this.data = null; this.projectId = null; this.record = null; this.name = ''; this.files = {};
    this.dirty = false; this.saving = false; this.busy = false; this.conflict = false; this.error = '';
    this.generation = 0; this.epoch = 0; this.refreshSequence = 0; this.appliedRefresh = 0;
    this.selectedPlanId = null; this.ownedJob = null; this.lastAction = null; this.readiness = null;
  }
  emit() { this.notify(this); }
  get project() { return this.data?.projects.find(p => p.id === this.projectId); }
  get plans() { return this.project?.info?.plans || []; }
  get attempts() { return this.project?.info?.attempts || []; }
  get selectedPlan() { return this.plans.find(plan => plan.id === this.selectedPlanId); }
  get activeJob() { return this.ownedJob?.status === 'running' ? this.ownedJob : this.data?.jobs?.find(job => job.id === this.data.active); }
  get ready() { return this.readiness?.project === this.projectId && this.readiness?.plan === this.selectedPlanId && this.readiness?.runtime === this.data?.runtime_revision && this.readiness.result.metadata_valid === true && this.readiness.result.runtimes_ready === true; }
  get admitted() { return Object.keys(approaches).filter(task => this.data?.installation.tasks.includes(task)); }
  get drafts() { return (this.data?.drafts || []).filter(d => d.project === this.projectId && approaches[d.task]).sort((a, b) => b.saved_at.localeCompare(a.saved_at)); }
  get locked() { return this.busy || !!this.data?.active || !!this.data?.closing; }
  key(record = this.record) { return `opent1d.concept-recovery/1:${this.data.workspace}:${record.project}:${record.id}`; }
  backup() {
    if (!this.record) return;
    try { this.storage?.setItem(this.key(), JSON.stringify({ revision: this.record.revision, name: this.name, files: this.files, parent: this.record.parent || null })); }
    catch { this.error = 'Browser recovery is unavailable. Save your changes before leaving.'; }
  }
  clearBackup() { try { this.storage?.removeItem(this.key()); } catch { /* Server save remains authoritative. */ } }
  reportRequest(path) { return this.fetcher(path, { headers: { 'X-OpenT1D-Token': this.token }, cache: 'no-store' }); }
  async request(path, body) {
    const headers = { 'X-OpenT1D-Token': this.token };
    const options = { headers, cache: 'no-store' };
    if (body !== undefined) { options.method = 'POST'; headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
    const response = await this.fetcher(path, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'The request was refused.');
    return result;
  }
  async refresh() {
    const sequence = ++this.refreshSequence, incoming = await this.request('/api/state');
    if (sequence < this.appliedRefresh) return;
    this.appliedRefresh = sequence; this.data = incoming; this.emit();
  }
  async action(operation, args = {}, project = this.projectId) {
    if (this.locked) throw new Error('Another project action is running. Wait for it to finish.');
    this.busy = true; this.error = ''; this.emit();
    let job, failure;
    try {
      const route = ['draft_create', 'draft_save'].includes(operation) ? '/api/drafts' : '/api/actions';
      job = await this.request(route, { request_id: crypto.randomUUID(), operation, project, arguments: args });
      this.ownedJob = job; this.emit();
      // The job reader retains complete draft files and current SDK-owned phase.
      do {
        job = await this.request('/api/jobs/' + job.id);
        this.ownedJob = job; this.lastAction = job; this.emit();
        if (job.status === 'running') await new Promise(resolve => setTimeout(resolve, 150));
      } while (job.status === 'running');
      if (job.status !== 'done') failure = new Error(job.error || 'The action did not complete.');
    } catch (error) { failure = error; }
    try {
      // Refresh on refusal/interruption too: the ledger may contain a retained
      // unfinished attempt even when the GUI job did not produce a result.
      await this.refresh();
      for (let i = 0; job && this.data?.active === job.id && i < 20; i++) {
        await new Promise(resolve => setTimeout(resolve, 50));
        await this.refresh();
      }
    } catch (error) { failure ||= error; }
    finally { this.ownedJob = null; this.busy = false; this.emit(); }
    if (failure) {
      // A refused worker may have written a partial attempt before failing. The
      // controller intentionally drops its cached info, so read that ledger
      // explicitly after the terminal job has released the action slot.
      if (project && operation !== 'refresh' && !this.data?.active) {
        try { await this.action('refresh', {}, project); }
        catch (readError) { failure = new Error(failure.message + ' Project history could not be refreshed: ' + readError.message); }
      }
      if (job) this.lastAction = job;
      this.emit(); throw failure;
    }
    return job.result;
  }
  selectPlan(id) {
    if (id && !this.plans.some(plan => plan.id === id)) throw new Error('This frozen plan is unavailable. Refresh the project.');
    this.selectedPlanId = id || null; this.emit();
  }
  async refreshProject() {
    if (!this.projectId) return;
    return this.action('refresh');
  }
  async freeze() {
    if (!this.record || !await this.flush()) return null;
    const record = this.record, generation = this.generation, epoch = this.epoch;
    if (record.frozen_plan) { this.selectedPlanId = record.frozen_plan; this.emit(); return { plan: record.frozen_plan }; }
    if (record.validation?.valid !== true || record.validation.revision !== record.revision) throw new Error('Review this saved study revision before freezing.');
    const result = await this.action('freeze', { draft: record.id, revision: record.revision, name: this.name, parent: record.parent || null });
    const annotated = await this.request('/api/drafts/' + record.id);
    if (this.generation === generation && this.epoch === epoch && this.record?.id === record.id) this.accept(annotated);
    this.selectedPlanId = result.plan; this.readiness = null; this.emit(); return result;
  }
  async checkPlan() {
    const plan = this.selectedPlanId, project = this.projectId, runtime = this.data?.runtime_revision;
    if (!plan) return null;
    this.readiness = null;
    const result = await this.action('check', { plan });
    this.readiness = { plan, project, runtime, result }; this.emit(); return result;
  }
  async runPlan(plan = this.selectedPlanId) {
    if (!await this.flush()) return null;
    if (!plan || plan !== this.selectedPlanId || !this.ready) throw new Error('Check this frozen plan before running it.');
    const latest = this.attempts.filter(attempt => attempt.plan === plan).at(-1);
    if (latest && (typeof latest.outcome !== 'object' || !latest.outcome)) throw new Error('This plan has an unfinished attempt. Confirm that its previous executor stopped, then explicitly recover it before retrying.');
    return this.action('run', { plan, retry_of: latest?.id || null });
  }
  async cancelRun() {
    const job = this.activeJob;
    if (!job || job.project !== this.projectId || !job.cancelable || job.cancel_requested) return false;
    await this.request('/api/jobs/' + job.id + '/cancel', {});
    if (this.ownedJob?.id === job.id) this.ownedJob = { ...job, cancel_requested: true, phase: 'Stop requested; waiting for SDK cleanup' };
    this.emit(); await this.refresh(); return true;
  }
  async recoverAttempt(attempt, executionStopped) {
    if (executionStopped !== true) throw new Error('Confirm that the previous executor has stopped before recovering this attempt.');
    if (!this.attempts.some(item => item.id === attempt && (typeof item.outcome !== 'object' || !item.outcome))) throw new Error('This attempt is no longer unfinished. Refresh the project.');
    return this.action('recover', { attempt, execution_stopped: true });
  }
  accept(record, recover = false) {
    clearTimeout(this.timer); this.generation++;
    if (this.record?.id !== record.id || !this.selectedPlanId) this.selectedPlanId = record.frozen_plan || null;
    this.record = record;
    this.name = record.name; this.files = { ...record.files }; this.dirty = false; this.conflict = false; this.error = '';
    if (recover) {
      try {
        const saved = JSON.parse(this.storage?.getItem(this.key()) || 'null');
        if (saved && typeof saved.name === 'string' && saved.files && approaches[record.task].files.every(f => typeof saved.files[f] === 'string')) {
          this.name = saved.name; this.files = { ...saved.files }; this.dirty = true;
          this.conflict = saved.revision !== record.revision;
          this.error = this.conflict ? 'This study changed elsewhere. Your unsaved edits are retained. Reload the saved study or save your edits as a separate study.' : 'Recovered unsaved edits. Save to keep them in your workspace.';
        }
      } catch { this.error = 'The browser recovery copy could not be read. The saved study is open.'; }
    }
    this.emit();
  }
  async loadDraft(id, recover = true) {
    if (!await this.flush()) return false;
    const generation = ++this.generation, project = this.projectId, epoch = this.epoch;
    const record = await this.request('/api/drafts/' + id);
    if (generation !== this.generation || project !== this.projectId || record.project !== project) return false;
    if (epoch !== this.epoch) { this.error = 'Your newer edits are retained. Save them before opening another study.'; this.emit(); return false; }
    this.accept(record, recover); return true;
  }
  async openProject(id) {
    if (!await this.flush()) return false;
    if (!this.data.projects.some(p => p.id === id)) throw new Error('This project is no longer available.');
    clearTimeout(this.timer); this.generation++; this.projectId = id; this.record = null; this.selectedPlanId = null; this.readiness = null; this.dirty = false; this.error = ''; this.emit();
    if (!this.project.info && !this.locked) await this.refreshProject();
    if (this.drafts.length) await this.loadDraft(this.drafts[0].id);
    if (!this.record && !this.selectedPlanId) this.selectedPlanId = this.plans.filter(plan => approaches[plan.task]).at(-1)?.id || null;
    return true;
  }
  async closeProject() {
    if (!await this.flush()) return false;
    this.generation++; this.projectId = null; this.record = null; this.selectedPlanId = null; this.readiness = null; this.error = ''; this.emit(); return true;
  }
  async openPath(path) {
    if (!await this.flush()) return false;
    const result = await this.action('open', { path }, null);
    return this.openProject(result.project);
  }
  async createProject(name, { task = 'mmtt-sensitivity', mode = 'guided', example = 'complete' } = {}) {
    if (!await this.flush()) return false;
    const created = await this.action('create', { name }, null);
    this.projectId = created.project; this.record = null; this.emit();
    return this.createStudy(task, mode, example);
  }
  async createStudy(task, mode = 'guided', example = 'complete') {
    if (!this.admitted.includes(task)) throw new Error('This approach is unavailable in this application.');
    if (!await this.flush()) return false;
    const choice = approaches[task];
    const record = mode === 'empty'
      ? await this.action('draft_create', { task, name: 'Untitled study', parent: null, files: Object.fromEntries(choice.files.map(f => [f, ''])) })
      : await this.action('prepare', { task, case: example });
    this.accept(record);
    if (mode !== 'empty') { this.edit(choice.question, this.files, false); return this.save(); }
    return true;
  }
  edit(name = this.name, files = this.files, schedule = true) {
    if (!this.record) return;
    this.selectedPlanId = null; this.readiness = null;
    this.name = name; this.files = { ...files }; this.epoch++; this.dirty = true; this.error = '';
    this.backup(); clearTimeout(this.timer);
    if (schedule && !this.conflict) this.timer = setTimeout(() => this.save(), 800);
    this.emit();
  }
  async save() {
    clearTimeout(this.timer);
    if (this.savePromise) { await this.savePromise; return this.dirty && !this.conflict && !this.error ? this.save() : !this.dirty; }
    if (!this.record || !this.dirty) return true;
    if (this.conflict) return false;
    if (this.locked) { this.error = 'Wait for the current action, then save your changes.'; this.emit(); return false; }
    const record = this.record, epoch = this.epoch, generation = this.generation;
    const values = { draft: record.id, revision: record.revision, name: this.name, parent: record.parent || null, files: { ...this.files } };
    this.saving = true; this.emit();
    this.savePromise = (async () => {
      try {
        const result = await this.action('draft_save', values, record.project);
        if (generation !== this.generation || record.id !== this.record?.id) return false;
        this.record = result;
        if (epoch === this.epoch) { this.dirty = false; this.error = ''; this.clearBackup(); }
        else { this.backup(); this.timer = setTimeout(() => this.save(), 800); }
        return !this.dirty;
      } catch (error) {
        this.conflict = /another tab/.test(error.message); this.error = error.message; this.backup(); return false;
      } finally { this.saving = false; this.emit(); }
    })();
    try { return await this.savePromise; } finally { this.savePromise = null; }
  }
  async flush() {
    clearTimeout(this.timer);
    return this.dirty || this.saving ? this.save() : true;
  }
  async reloadSaved() {
    if (!this.record) return;
    const id = this.record.id, project = this.projectId, epoch = this.epoch, generation = ++this.generation;
    const result = await this.request('/api/drafts/' + id);
    if (this.generation !== generation || this.projectId !== project || this.record?.id !== id || this.epoch !== epoch) return false;
    this.clearBackup(); this.accept(result); return true;
  }
  async saveCopy() {
    const previous = this.record;
    const result = await this.action('draft_create', { task: previous.task, name: this.name, parent: previous.parent || null, files: this.files });
    this.clearBackup(); this.accept(result); return true;
  }
  async review() {
    if (!this.record || !await this.flush()) return null;
    const result = await this.action('draft_validate', { draft: this.record.id, revision: this.record.revision });
    this.accept(result); return result.validation;
  }
}
