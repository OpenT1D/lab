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
  }
  emit() { this.notify(this); }
  get project() { return this.data?.projects.find(p => p.id === this.projectId); }
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
    this.busy = true; this.emit();
    try {
      const route = ['draft_create', 'draft_save'].includes(operation) ? '/api/drafts' : '/api/actions';
      let job = await this.request(route, { request_id: crypto.randomUUID(), operation, project, arguments: args });
      // POST may already be complete; the job reader includes full draft files.
      job = await this.request('/api/jobs/' + job.id);
      while (job.status === 'running') {
        await new Promise(resolve => setTimeout(resolve, 100));
        job = await this.request('/api/jobs/' + job.id);
      }
      if (job.status !== 'done') throw new Error(job.error || 'The action did not complete.');
      await this.refresh();
      // The controller publishes the result before its final journal cleanup.
      for (let i = 0; this.data?.active === job.id && i < 10; i++) {
        await new Promise(resolve => setTimeout(resolve, 50));
        await this.refresh();
      }
      return job.result;
    } finally { this.busy = false; this.emit(); }
  }
  accept(record, recover = false) {
    clearTimeout(this.timer); this.generation++; this.record = record;
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
    clearTimeout(this.timer); this.generation++; this.projectId = id; this.record = null; this.dirty = false; this.error = ''; this.emit();
    if (this.drafts.length) await this.loadDraft(this.drafts[0].id);
    return true;
  }
  async closeProject() {
    if (!await this.flush()) return false;
    this.generation++; this.projectId = null; this.record = null; this.error = ''; this.emit(); return true;
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
