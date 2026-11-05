import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {generate,fixtureModules} from './lt1_diagnostic_fixture.mjs';
import {START,HORIZON,STEP,MINUTE,STATE,validatePlan,snapshot} from '../experiments/lt1_diagnostic/protocol.mjs';
import {ReleaseQueue,assembleWrapped,loadNative} from '../experiments/lt1_diagnostic/wrapped.mjs';
import {assembleDirect} from '../experiments/lt1_diagnostic/direct.mjs';
const plan=JSON.parse(readFileSync(new URL('../experiments/lt1_diagnostic/plan.json',import.meta.url)));

if (process.argv[2] === '--emit') {
  const selected = process.argv[3] ? JSON.parse(readFileSync(process.argv[3])) : plan;
  const generated=generate(selected);
  process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(generated).map(([m,v])=>[m,v.session]))));
} else {
  test('independent direct/wrapped constructions, raw calls, fractional events and reset', () => {
    const paths=generate(plan);
    assert.deepEqual(paths.direct.session,paths.wrapped.session);
    const control=paths.wrapped.session;
    assert.equal(control.status,'completed'); assert.equal(control.rows.length,32);
    assert.deepEqual(control.rows.slice(0,7).map(r=>r.time_ms),[0,60000,120000,150000,210000,240000,300000]);
    assert.deepEqual(control.rows.filter(r=>r.transition).map(r=>r.command_u_h),[1.2,1.2,1.2,1.7999999999999998,0.6,1]);
    assert.equal(control.rows.at(-1).transition,null);
    assert.equal(control.rows.at(-1).delivered_u_h,30);
    const at15=control.rows.find(r=>r.time_ms===900000);
    assert.equal(at15.raw_cgm_mg_dl,150); assert.equal(at15.transition.observation.glucose_mg_dl,60);
    assert.equal(at15.transition.observation.measured_ms,600000);
    assert.deepEqual(at15.transition.new_announcements,['invented-announcement']);
    for (const {built,session} of Object.values(paths)) {
      assert.equal(built.sensor.native.calls,32); assert.equal(built.pump.calls,32);
      assert.equal(built.patient.seed,105); assert.equal(built.sensor.native.seed,102); assert.equal(built.pump.seed,104);
      assert.equal(built.sim.meals[0].duration,1.5);
      const repeat=built.run(); assert.deepEqual(repeat,session);
      assert.equal(built.sessions.length,2); assert.notEqual(built.sessions[0].rows,built.sessions[1].rows);
      assert.ok(+built.controller.getNextUpdateTime(new Date(START+HORIZON))>START+HORIZON);
    }
  });

  test('release query is pure, time-aware and never regresses to a late older sample', () => {
    const queue=new ReleaseQueue([{measured_ms:STEP,available_ms:3*STEP}]);
    queue.advance(0,120); queue.advance(STEP,180); queue.advance(2*STEP,60);
    assert.deepEqual(queue.asOf(2*STEP),{measured_ms:2*STEP,available_ms:2*STEP,glucose_mg_dl:60});
    queue.advance(3*STEP,150);
    assert.equal(queue.asOf(3*STEP).measured_ms,3*STEP);
    assert.equal(queue.asOf(2*STEP).measured_ms,2*STEP);
    assert.equal(queue.asOf(3*STEP).measured_ms,3*STEP);
    assert.throws(()=>queue.asOf(4*STEP),/future-query/);
    assert.throws(()=>queue.advance(3*STEP,120),/generation-clock/);
    queue.reset(); assert.throws(()=>queue.asOf(0),/future-query/);
    assert.throws(()=>new ReleaseQueue([{measured_ms:STEP,available_ms:0}]),/release-clock/);
    assert.throws(()=>new ReleaseQueue([{measured_ms:STEP,available_ms:true}]),/number/);
  });

  test('simultaneous native/diagnostic errors retain first cause and complete prefix', () => {
    const paths=generate(plan,{failAfter:2,exporter:copy=>{copy.primary_error='overwritten';throw Error('fixture diagnostic failure');}});
    for (const {session} of Object.values(paths)) {
      assert.equal(session.status,'failed'); assert.equal(session.rows.length,3);
      assert.match(session.primary_error,/fixture primary failure/);
      assert.match(session.diagnostic_error,/fixture diagnostic failure/);
    }
    const bad=generate(plan,{badRaw:true});
    for (const {session} of Object.values(bad)) {
      assert.equal(session.status,'failed'); assert.equal(session.rows.length,0);
      assert.equal(session.diagnostic_tail.length,1);
      assert.deepEqual(session.diagnostic_tail[0].raw.CGM,{nonfinite:'NaN'});
    }
  });

  test('missing/double callbacks cannot become valid extra sampled updates', () => {
    for (const assemble of [assembleDirect,assembleWrapped]) {
      const built=assemble(fixtureModules(plan),plan); built.run();
      assert.throws(()=>built.controller.update(new Date(START+HORIZON),built.sensor.getOutput(),{}),/clock/);
      built.controller.reset();
      assert.throws(()=>built.controller.update(new Date(START+6*MINUTE),built.sensor.getOutput(),{}),/clock|missed/);
    }
  });

  test('failure before sensor reset cannot reuse previous-session diagnostics', () => {
    const paths=generate(plan);
    for (const {built,session} of Object.values(paths)) {
      assert.equal(session.status,'completed');
      assert.ok(built.sensor.last_generation);
      built.sim.runSimulation=()=>{throw Error('fixture solver reset failed before sensor reset');};
      const failed=built.run();
      assert.equal(failed.status,'failed');
      assert.match(failed.primary_error,/solver reset failed/);
      assert.deepEqual(failed.rows,[]); assert.deepEqual(failed.diagnostic_tail,[]);
      assert.equal(session.rows.length,32);
      assert.equal(built.sessions.length,2);
    }
  });

  test('raw diagnostic serialization failure cannot replace primary validation error', () => {
    for (const assemble of [assembleDirect,assembleWrapped]) {
      const built=assemble(fixtureModules(plan),plan);
      assert.equal(built.run().status,'completed');
      built.sim.runSimulation=()=>{
        const native={t:new Date(START),x:Object.fromEntries(STATE.map(k=>[k,0])),
          y:{Gp:NaN},s:{CGM:NaN},u:{iir:1.2,carbs:0,meal:0,exercise:0},c:{iir:1.2}};
        native.cycle=native;
        built.sim.callback(native);
      };
      const failed=built.run(()=>{throw Error('additional export failure');});
      assert.equal(failed.status,'failed'); assert.match(failed.primary_error,/number/);
      assert.match(failed.diagnostic_error,/circular/i);
      assert.match(failed.diagnostic_error,/additional export failure/);
      assert.deepEqual(failed.rows,[]);
    }
  });

  test('unsupported native duration, old seed, hidden inputs and wrong basal refuse', () => {
    for (const mutate of [p=>p.meals[0].duration_ms=30000,p=>p.seed=102,
      p=>p.profile='patient',p=>p.release_rules.push({measured_ms:0,available_ms:null})]) {
      const changed=snapshot(plan); mutate(changed); assert.throws(()=>validatePlan(changed));
    }
    for (const assemble of [assembleDirect,assembleWrapped]) {
      assert.throws(()=>assemble(fixtureModules(plan,{basal:2}),plan),/native-basal/);
      assert.throws(()=>assemble(fixtureModules(plan,{basal:Infinity}),plan),/number/);
    }
  });

  test('future actual meal changes cannot change the scripted pre-event controller prefix', () => {
    const later=snapshot(plan); later.meals[0].start_ms=15*MINUTE; later.meals[0].duration_ms=15*MINUTE;
    later.announcements[0].start_ms=15*MINUTE;
    const changed=snapshot(later); changed.meals[0].grams=80;
    const a=generate(later), b=generate(changed);
    for (const mode of ['direct','wrapped']) {
      assert.deepEqual(a[mode].session.rows.filter(r=>r.time_ms<15*MINUTE),b[mode].session.rows.filter(r=>r.time_ms<15*MINUTE));
    }
  });

  test('native loading remains closed regardless of supplied metadata', async () => {
    await assert.rejects(loadNative({native_execution:true,setup_receipt:'invented'}),/refused.*admission/);
  });
}
