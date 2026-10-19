import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCyberAction,createCyberState,tickCyberState} from './simulation.js';
test('F exit stops engine, opens the door, waits for animation and leaves the owned car',()=>{
  const car={x:24,y:0,z:44,heading:Math.PI/2,sourceId:'car',wheelAngle:4};
  let state={...createCyberState(),mode:'car',heading:car.heading,position:{x:24,y:.45,z:44},sitting:true,personalVehicles:{car},carControls:{engineOn:true,doorOpen:false,windowsOpen:true}};
  const result=applyCyberAction(state,{type:'CAR_EXIT'});assert.equal(result.ok,true);state=result.state;
  assert.equal(state.mode,'car');assert.equal(state.carControls.engineOn,false);assert.equal(state.carControls.doorOpen,true);
  assert.equal(applyCyberAction(state,{type:'CAR_EXIT'}).ok,false);
  state=tickCyberState(state,.5);assert.equal(state.mode,'car');state=tickCyberState(tickCyberState(state,.5),.3);
  assert.equal(state.mode,'foot');assert.equal(state.position.y,0);assert.ok(Math.abs(state.position.z-41)<1e-9);
  assert.deepEqual(state.personalVehicles.car,car);assert.equal(state.carControls.windowsOpen,true);
});
test('side windows remain in the selected state through door and engine actions',()=>{
  let state={...createCyberState(),mode:'car',position:{x:20,y:.45,z:44},personalVehicles:{car:{x:20,y:0,z:44,sourceId:'car'}}};
  state=applyCyberAction(state,{type:'CAR_WINDOWS'}).state;assert.equal(state.carControls.windowsOpen,true);
  state=applyCyberAction(state,{type:'CAR_ENGINE'}).state;assert.equal(state.carControls.windowsOpen,true);
  state=applyCyberAction(state,{type:'CAR_ENGINE'}).state;state=applyCyberAction(state,{type:'CAR_DOOR'}).state;
  assert.equal(state.carControls.windowsOpen,true);assert.equal(applyCyberAction(createCyberState(),{type:'CAR_WINDOWS'}).ok,false);
});
