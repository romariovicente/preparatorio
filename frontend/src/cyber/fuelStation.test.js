import test from 'node:test';
import assert from 'node:assert/strict';
import {PerspectiveCamera,Vector3} from 'three';
import {advanceCityPosition,applyCyberAction,createCyberState} from './simulation.js';
import {fuelStationArrivalCamera,fuelStationColliders,fuelStationPavement,fuelStationZone} from './fuelStation.js';

test('the fuel station route arrives on the apron and frames the avatar and canopy',()=>{
  const action={type:'TELEPORT',zoneId:fuelStationZone.id};
  const result=applyCyberAction(createCyberState(),action,{zones:[fuelStationZone],obstacles:fuelStationColliders});
  assert.equal(result.ok,true);
  const {x,y,z}=result.state.position;
  assert.deepEqual([x,y,z],fuelStationZone.approach);
  assert.ok(Math.abs(z-fuelStationZone.position[2])<fuelStationPavement.size[2]/2);
  const pose=fuelStationArrivalCamera(action,result.state.position);
  for(const aspect of [.65,1.33,1.8]){
    const camera=new PerspectiveCamera(50,aspect,.1,450);
    camera.position.fromArray(pose.position);
    camera.lookAt(...pose.target);
    camera.updateMatrixWorld();
    for(const point of [[x,y+1,z],[-55,5.17,96.46],[-55,.5,102]]){
      const screen=new Vector3(...point).project(camera);
      assert.ok(Math.abs(screen.x)<1&&Math.abs(screen.y)<1&&Math.abs(screen.z)<1);
    }
  }
  assert.equal(fuelStationArrivalCamera({type:'TELEPORT',zoneId:'mechanic-workshop'},result.state.position),null);
});

test('the lane stays open while the pump islands and shop block movement',()=>{
  function forward(x,z) {
    let position={x,y:0,z};
    for(let step=0;step<20;step++)position=advanceCityPosition(position,{x:0,z:1},.05,6,fuelStationColliders,2.35);
    return position.z;
  }
  assert.ok(Math.abs(forward(-55,96)-102)<.0001);
  assert.ok(forward(-60.5,95)<98);
  assert.ok(forward(-41.5,96)<102);
});
