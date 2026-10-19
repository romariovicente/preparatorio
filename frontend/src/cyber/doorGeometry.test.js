import test from 'node:test';
import assert from 'node:assert/strict';
import {advanceCityPosition} from './simulation.js';
import {buildingColliders,doorPosition,doorLeafTransform,doorwayOccupied} from './doorGeometry.js';
const b={center:[10,0,0],width:12,depth:10,opening:3.2,style:'slide'};
test('closed doors stop walking; open doors permit entry while walls still block',()=>{
  const closed=buildingColliders(b,{open:false}),open=buildingColliders(b,{open:true});
  const p={x:10,y:0,z:5.6},dir={x:0,y:0,z:-1};
  assert.equal(advanceCityPosition(p,dir,.05,5,closed).z,p.z);
  assert.ok(advanceCityPosition(p,dir,.05,5,open).z<p.z);
  assert.equal(advanceCityPosition({...p,x:7},dir,.05,5,open).z,p.z);
});
test('door leaves move away from the aperture and doors cannot close on passengers',()=>{
  assert.deepEqual(doorPosition(b),[10,0,5]);
  const pose=doorLeafTransform(b,1,1);assert.ok(pose.x>2.4);assert.equal(pose.angle,0);
  assert.ok(Math.abs(doorLeafTransform({...b,style:'swing'},-1,1).angle-Math.PI/2)<1e-9);
  assert.equal(doorwayOccupied({a:{online:true,position:{x:10,y:0,z:5}}},b),true);
  assert.equal(doorwayOccupied({a:{online:true,position:{x:10,y:-6,z:5}}},b),false);
});
