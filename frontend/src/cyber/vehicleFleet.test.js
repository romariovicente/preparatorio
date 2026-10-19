import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCyberAction,createCyberState,DRIVE_VEHICLES,saveCyberState,restoreCyberState} from './simulation.js';
import {resolveMotorcycle} from './motorcycleInteraction.js';

test('repeated summons and vehicle switches keep exactly one personal vehicle and preserve the sources',()=>{
  const originals=JSON.stringify(DRIVE_VEHICLES);let state=createCyberState();
  for(const vehicle of ['car','car','truck','mototaxi','car']){
    const result=applyCyberAction(state,{type:'SUMMON_VEHICLE',vehicle});assert.equal(result.ok,true,result.message);state=result.state;
    assert.deepEqual(Object.keys(state.personalVehicles),[vehicle]);
  }
  assert.equal(state.garage.mototaxi.sourceId,'mototaxi');assert.equal(JSON.stringify(DRIVE_VEHICLES),originals);
  assert.equal(applyCyberAction({...state,mode:'car'},{type:'SUMMON_VEHICLE',vehicle:'mototaxi'}).ok,false);
  assert.equal(applyCyberAction(state,{type:'SUMMON_VEHICLE',vehicle:'tractor'}).ok,false);
});
test('parking removes the personal vehicle and preserves its model in the saved garage',()=>{
  let state=applyCyberAction(createCyberState(),{type:'SUMMON_VEHICLE',vehicle:'car',sourceId:'hospital-suv'}).state;
  assert.equal(applyCyberAction(state,{type:'STORE_VEHICLE'},{parking:[{id:'far',position:[110,0,100]}]}).ok,false);
  const vehicle=state.personalVehicles.car;
  const result=applyCyberAction(state,{type:'STORE_VEHICLE'},{parking:[{id:'test',position:[vehicle.x,0,vehicle.z]}]});
  assert.equal(result.ok,true);assert.deepEqual(result.state.personalVehicles,{});assert.equal(result.state.garage.car.sourceId,'hospital-suv');
  let saved;const storage={setItem:(_,value)=>{saved=value;},getItem:()=>saved};
  assert.equal(saveCyberState(storage,result.state),true);assert.deepEqual(restoreCyberState(storage).garage,result.state.garage);
});
test('motorcycle entry reuses the summoned bike, engine gates movement, F-style exit stops the engine',()=>{
  const base=resolveMotorcycle('mototaxi');let state={...createCyberState(),position:{x:base.position.x+3,y:0,z:base.position.z}};
  state=applyCyberAction(state,{type:'SUMMON_VEHICLE',vehicle:'mototaxi'}).state;
  const bike={...state.personalVehicles.mototaxi};state={...state,position:{x:bike.x+1,y:0,z:bike.z}};
  const entry=applyCyberAction(state,{type:'MOTO_ENTER',motoId:'personal-moto'});assert.equal(entry.ok,true,entry.message);state=entry.state;
  assert.deepEqual(state.personalVehicles.mototaxi,bike);assert.equal(state.mode,'mototaxi');
  const move={type:'MOVE',position:{x:bike.x,y:.7,z:bike.z+1}};
  assert.equal(applyCyberAction(state,move).ok,false);state=applyCyberAction(state,{type:'MOTO_ENGINE'}).state;
  const moved=applyCyberAction(state,move);assert.equal(moved.ok,true);assert.equal(moved.state.personalVehicles.mototaxi.sourceId,bike.sourceId);
  state=applyCyberAction(moved.state,{type:'MOTO_EXIT'}).state;assert.equal(state.mode,'foot');assert.equal(state.motorcycleControls.engineOn,false);assert.equal(Object.keys(state.personalVehicles).length,1);
});
