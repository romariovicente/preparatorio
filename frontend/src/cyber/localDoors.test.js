import test from 'node:test';
import assert from 'node:assert/strict';
import {changeLocalDoor} from './localDoors.js';
import {buildingColliders,cityColliders} from './doorGeometry.js';

const hospital={id:'hospital',center:[48,0,-38],width:36,depth:24,height:4.2,opening:2.4};
test('offline public door changes the same state used by animation and walking collision, without changing its source',()=>{
  const original={};
  const opened=changeLocalDoor(original,hospital,{position:{x:48,y:0,z:-22.6}},1000);
  assert.equal(opened.ok,true);assert.equal(opened.doors.hospital.open,true);assert.deepEqual(original,{});
  const closedCount=buildingColliders(hospital,{}).length;
  assert.equal(cityColliders([], [hospital],opened.doors,1500).length,closedCount,'partial opening remains blocked');
  assert.equal(cityColliders([], [hospital],opened.doors,2200).length,closedCount-1,'completed opening permits the entrance');
  const closed=changeLocalDoor(opened.doors,hospital,{position:{x:48,y:0,z:-22.6}},2300);
  assert.equal(closed.doors.hospital.open,false);assert.equal(closed.doors.hospital.revision,2);
  assert.equal(cityColliders([], [hospital],closed.doors,2400).length,closedCount);
});
test('offline door refuses remote, other-floor and occupied closing attempts',()=>{
  for(const position of [{x:70,y:0,z:-22},{x:48,y:-6,z:-22}])assert.equal(changeLocalDoor({},hospital,{position}).ok,false);
  assert.equal(changeLocalDoor({},hospital,{position:{x:48,z:-22.6},mode:'car'}).ok,false);
  const doors={hospital:{open:true,revision:3}};
  assert.equal(changeLocalDoor(doors,hospital,{position:{x:48,z:-26}}).ok,false);
  assert.equal(changeLocalDoor(doors,hospital,{position:{x:48,z:-22.6},players:{visitor:{online:true,position:{x:48,z:-26}}}}).ok,false);
  assert.equal(doors.hospital.open,true);
});
