import test from 'node:test';
import assert from 'node:assert/strict';
import {entryVehicleCamera} from './vehicleCamera.js';
import {applyCyberAction,createCyberState,tickCyberState} from './simulation.js';

test('real Volvo DRIVE gets its entry camera even after commit replaces the simulation state',()=>{
  const simulation={current:{...createCyberState(),position:{x:23,y:0,z:-52.2},
    personalVehicles:{truck:{x:23,y:0,z:-52.2,sourceId:'volvo',heading:0,trailer:'none'}}}};
  const previousMode=simulation.current.mode,result=applyCyberAction(simulation.current,{type:'DRIVE',vehicle:'truck'});
  assert.equal(result.ok,true);
  simulation.current=result.state;
  assert.equal(simulation.current.mode,'truck');assert.equal(simulation.current.position.y,1.5);
  assert.deepEqual(entryVehicleCamera(previousMode,simulation.current),{position:[30,6.5,-69.2],target:[23,2.5,-52.2]});
  const next=tickCyberState(simulation.current,0);
  assert.equal(entryVehicleCamera(simulation.current.mode,next),null,'ordinary frames must not reset the chosen orbit');
});

test('car and motorcycle entry reuse their chase offsets and respect heading',()=>{
  for(const mode of ['car','mototaxi']){
    const pose=entryVehicleCamera('foot',{mode,position:{x:4,y:.7,z:10},heading:Math.PI/2});
    assert.ok(Math.abs(pose.position[0]+5)<1e-12);assert.equal(pose.position[1],3.6);
    assert.ok(Math.abs(pose.position[2]-6)<1e-12);assert.deepEqual(pose.target,[4,1.7,10]);
  }
});

test('same-mode, exit and invalid states cannot reposition the vehicle camera',()=>{
  const truck={mode:'truck',position:{x:23,y:1.5,z:-52.2},heading:0};
  assert.equal(entryVehicleCamera('truck',truck),null);
  assert.equal(entryVehicleCamera('truck',{...truck,mode:'foot'}),null);
  assert.equal(entryVehicleCamera('foot',{...truck,mode:'bus'}),null);
  for(const state of [null,undefined,{mode:'truck'}, {...truck,heading:NaN}, {...truck,heading:Infinity},
    {...truck,position:{x:NaN,y:1,z:2}}, {...truck,position:{x:1,y:Infinity,z:2}}, {...truck,position:{x:1,y:1,z:undefined}}]){
    assert.equal(entryVehicleCamera('foot',state),null);
  }
});
