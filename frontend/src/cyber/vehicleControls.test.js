import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCyberAction,createCyberState,DRIVE_VEHICLES} from './simulation.js';
test('car entry requires opening; engine requires closing; exit requires stopping and opening',()=>{
  let state={...createCyberState(),position:{...DRIVE_VEHICLES.car.position,x:23}};
  const action=type=>{const result=applyCyberAction(state,{type,vehicle:'car'});if(result.ok)state=result.state;return result;};
  assert.equal(action('DRIVE').ok,false);assert.equal(action('CAR_DOOR').ok,true);
  assert.equal(state.carControls.doorOpen,true);assert.equal(action('DRIVE').ok,true);
  assert.equal(action('CAR_ENGINE').ok,false);assert.equal(action('CAR_DOOR').ok,true);
  assert.equal(action('CAR_ENGINE').ok,true);assert.equal(state.carControls.engineOn,true);
  assert.equal(action('CAR_DOOR').ok,false);assert.equal(action('EXIT').ok,false);
  assert.equal(action('CAR_ENGINE').ok,true);assert.equal(action('EXIT').ok,false);
  assert.equal(action('CAR_DOOR').ok,true);assert.equal(action('EXIT').ok,true);assert.equal(state.mode,'foot');
  assert.deepEqual(DRIVE_VEHICLES.car.position,{x:20,y:0,z:44});
});
