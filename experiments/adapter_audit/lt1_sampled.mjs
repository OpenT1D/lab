/** audit-1 sampled kernel only. No native imports, setup or execution authority. */
const fields = (v, names) => {
  if (!v || typeof v !== 'object' || Array.isArray(v) ||
      Object.keys(v).sort().join() !== names.split(' ').sort().join()) throw Error('fields');
};
const finite = (v, minimum = 0) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v < minimum) throw Error('number');
  return v;
};

/** Released observation only; selecting/filtering raw samples belongs outside. */
export class SampledAudit1 {
  constructor(basal, horizon = 30) {
    finite(basal); finite(horizon);
    if (basal > 3 || !horizon || horizon % 5) throw Error('settings');
    this.basal = basal; this.horizon = horizon; this.reset();
  }
  reset() {
    this.previous = 120; this.source = -1; this.next = 0;
    this.callback = -1; this.rate = this.basal;
  }
  update(minute, observation = null) {
    finite(minute);
    if (minute <= this.callback || minute > this.horizon) throw Error('callback-clock');
    if (minute > this.next && this.next < this.horizon) throw Error('missed-tick');
    // Native off-grid callbacks and terminal diagnostics never consume a sample.
    if (minute !== this.next || minute === this.horizon) {
      if (observation !== null) throw Error('non-tick-observation');
      this.callback = minute;
      return {command_u_h: this.rate, transition: null};
    }
    fields(observation, 'measured_min available_min glucose_mg_dl');
    const {measured_min: measured, available_min: available, glucose_mg_dl: glucose} = observation;
    finite(measured); finite(available); finite(glucose);
    if (measured % 5 || measured > available || available > minute || measured < this.source ||
        (minute === 0 && (measured !== 0 || available !== 0))) throw Error('observation-clock');
    if (measured === this.source && (glucose !== this.last.glucose_mg_dl ||
        available !== this.last.available_min)) throw Error('changed-sample');
    const fresh = measured > this.source;
    const previous = this.previous;
    this.rate = fresh ? Math.min(3, Math.max(0, this.basal + 0.01 * (previous - 120))) : this.basal;
    if (fresh) { this.previous = glucose; this.source = measured; this.last = {...observation}; }
    this.next += 5; this.callback = minute;
    return {command_u_h: this.rate, transition: {
      time_min: minute, previous_mg_dl: previous, fresh, measured_min: measured,
    }};
  }
}
