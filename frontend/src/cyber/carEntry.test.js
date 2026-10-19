import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCyberAction,createCyberState,tickCyberState,DRIVE_VEHICLES} from './simulation.js';
import {resolveCarSource} from './carInteraction.js';

test('context entry opens the correct car, keeps its base, then enters after the door animation',()=>{
  const original=JSON.stringify(DRIVE_VEHICLES),car=resolveCarSource('car');
  const initial={...createCyberState(),position:{x:car.position.x+3,y:0,z:car.position.z+2}};
  const far=applyCyberAction(createCyberState(),{type:'CAR_ENTER',carId:'car'});assert.equal(far.ok,false);
  assert.equal(applyCyberAction(initial,{type:'CAR_ENTER',carId:'car'},{carrying:true}).ok,false);
  const result=applyCyberAction(initial,{type:'CAR_ENTER',carId:'car'});assert.equal(result.ok,true);
  assert.equal(result.state.mode,'foot');assert.equal(result.state.carControls.doorOpen,true);
  assert.notEqual(result.state.personalVehicles.car.x,car.position.x);
  let state=result.state;for(let i=0;i<3;i++)state=tickCyberState(state,.5);
  assert.equal(state.mode,'car');assert.equal(state.carEntry,null);assert.equal(state.carControls.doorOpen,false);
  assert.equal(state.personalVehicles.car.sourceId,'car');assert.equal(JSON.stringify(DRIVE_VEHICLES),original);
  assert.equal(applyCyberAction(state,{type:'MOVE',position:{x:30,y:.45,z:44}}).ok,false);
  state=applyCyberAction(state,{type:'CAR_ENGINE'}).state;
  assert.equal(applyCyberAction(state,{type:'MOVE',position:{x:30,y:.45,z:44}}).ok,true);
  const parked=applyCyberAction(state,{type:'PARK'},{parking:[{id:'test',position:[24,0,44]}]});
  assert.equal(parked.ok,true);assert.equal(parked.state.carControls.engineOn,false);
  assert.deepEqual(parked.state.personalVehicles,{});
  assert.equal(parked.state.garage.car.sourceId,'car');
});
test('walking away cancels pending entry and returning to your own car reuses it',()=>{
  const initial={...createCyberState(),position:{x:23,y:0,z:46}};
  let state=applyCyberAction(initial,{type:'CAR_ENTER',carId:'car'}).state;
  state={...state,position:{x:0,y:0,z:0}};for(let i=0;i<3;i++)state=tickCyberState(state,.5);
  assert.equal(state.mode,'foot');assert.equal(state.carEntry,null);
  const originalCar={...state.personalVehicles.car};
  state={...state,position:{x:originalCar.x+3,y:0,z:originalCar.z}};
  state=applyCyberAction(state,{type:'CAR_ENTER',carId:'personal-car'}).state;
  assert.deepEqual(state.personalVehicles.car,originalCar);
});
