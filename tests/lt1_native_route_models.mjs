/** Fixed invented state-machine fixture. No physiology, candidate or native acceptance. */
import {fixtureModules} from './lt1_diagnostic_fixture.mjs';
import {START,STATE} from '../experiments/lt1_diagnostic/protocol.mjs';
export function routeFixtureModules(plan){
 const base=fixtureModules(plan,{basal:1.2});
 class Cambridge extends base.Cambridge{
  constructor(...args){super(...args);this.initial=null;this.activeInitial=null;this.initialStateConsumed=false;}
  computeSteadyState(input,date){if(input.iir!==1.2||+date!==START)throw Error('invented steady-state contract');return Object.fromEntries(STATE.map((n,i)=>[n,i]));}
  setInitialState(value){this.initial={...value};}
  getInitialState(){return {...(this.initial??this.computeSteadyState({iir:1.2},new Date(START)))};}
  reset(...args){super.reset(...args);this.activeInitial=this.getInitialState();this.initialStateConsumed=this.initial!==null;}
  getState(){return this.time===0&&this.activeInitial?{...this.activeInitial}:super.getState();}
 }
 return {...base,Cambridge};
}
