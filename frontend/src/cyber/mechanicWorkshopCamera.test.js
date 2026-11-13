import test from 'node:test';
import assert from 'node:assert/strict';
import {PerspectiveCamera,Vector3} from 'three';
import {applyCyberAction,createCyberState} from './simulation.js';
import {mechanicWorkshopZone,workshopArrivalCamera} from './mechanicWorkshop.js';

test('the workshop route frames the facade and the player immediately on arrival',()=>{
  const action={type:'TELEPORT',zoneId:mechanicWorkshopZone.id};
  const result=applyCyberAction(createCyberState(),action,{zones:[mechanicWorkshopZone]});
  assert.equal(result.ok,true);
  const pose=workshopArrivalCamera(action,result.state.position);
  assert.deepEqual(pose.target,[-60,1,0]);
  for(const aspect of [.65,1.8]){
    const camera=new PerspectiveCamera(45,aspect,.1,400);
    camera.position.fromArray(pose.position);
    camera.lookAt(...pose.target);
    camera.updateMatrixWorld();
    for(const worldPoint of [[-51,3.6,3],[-60,.1,0],[-51,2,-1],[-51,2,7]]){
      const screen=new Vector3(...worldPoint).project(camera);
      assert.ok(Math.abs(screen.x)<1&&Math.abs(screen.y)<1&&Math.abs(screen.z)<1,
        `Expected ${worldPoint} in view at aspect ${aspect}, got ${screen.toArray()}`);
    }
  }
});

test('other teleports and ordinary actions do not change the workshop camera',()=>{
  const player={x:0,y:0,z:0};
  assert.equal(workshopArrivalCamera({type:'TELEPORT',zoneId:'hospital'},player),null);
  assert.equal(workshopArrivalCamera({type:'DRIVE',zoneId:mechanicWorkshopZone.id},player),null);
});
