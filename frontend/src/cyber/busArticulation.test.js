import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BoxGeometry,Group,Mesh,MeshStandardMaterial,Vector3} from 'three';
import {animateBusRig,createBusRig,BRT_INTERACTIVE_URL,interactiveBusUrl} from './busArticulation.js';

test('bus axle spin, front steering, doors and rear section preserve pivots and loader cache',()=>{
  const source=new Group();source.add(new Mesh(new BoxGeometry(3,3,20),new MeshStandardMaterial()));
  const rear=new Group();rear.name='RearSection';rear.position.z=-1;source.add(rear);
  for(const axle of ['01','04'])for(const side of ['L','R']){
    const wheel=new Group();wheel.name=`Wheel_${axle}_${side}`;wheel.position.set(side==='L'?1:-1,.5,axle==='01'?8:-7);wheel.userData.steering_axle=axle==='01';
    wheel.add(new Mesh(new BoxGeometry(.2,1,1),new MeshStandardMaterial()));(axle==='04'?rear:source).add(wheel);
  }
  const door=new Group();door.name='Door_01_A';door.position.set(-1.5,0,8);source.add(door);
  const rig=createBusRig(source),before=rig.wheels.map(w=>w.node.getWorldPosition(new Vector3()));
  animateBusRig(rig,{wheelAngle:Math.PI/2,steeringAngle:.3,doorOpen:true},1);rig.outer.updateMatrixWorld(true);
  for(let i=0;i<rig.wheels.length;i++){
    const wheel=rig.wheels[i];assert.ok(wheel.node.getWorldPosition(new Vector3()).distanceTo(before[i])<1e-10);
    assert.ok(Math.abs(wheel.node.rotation.x-Math.PI/2)<1e-10);assert.ok(Math.abs(wheel.steering.rotation.y-(wheel.front?.3:0))<1e-10);
  }
  assert.equal(rig.doors[0].angle,-65*Math.PI/180);
  animateBusRig(rig,{wheelAngle:0,steeringAngle:0,doorOpen:false,articulationAngle:.2},1);
  assert.equal(rig.doors[0].angle,0);assert.ok(Math.abs(rig.rear.node.rotation.y-.2)<1e-10);
  assert.equal(source.getObjectByName('Wheel_01_L').rotation.x,0);assert.equal(source.getObjectByName('RearSection').rotation.y,0);
});
test('generated BRT GLB has the actual eight wheels, six hinges and five bellows',()=>{
  assert.equal(interactiveBusUrl({sourceId:'VEH_Bus_BRT_20261006',url:'old.glb'}),BRT_INTERACTIVE_URL);
  const bytes=readFileSync(new URL('../../public'+BRT_INTERACTIVE_URL,import.meta.url));
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const wheels=doc.nodes.filter(n=>/^Wheel_\d\d_[LR]$/.test(n.name));assert.equal(wheels.length,8);assert.equal(wheels.filter(n=>n.extras.steering_axle).length,2);
  assert.equal(doc.nodes.filter(n=>/^Door_\d\d_[AB]$/.test(n.name)).length,6);
  assert.ok(doc.nodes.some(n=>n.name==='RearSection'));assert.equal(doc.meshes.filter(m=>m.extras?.targetNames?.includes('ArticulationLeft')).length,5);
  assert.equal(doc.meshes.reduce((sum,m)=>sum+m.primitives.reduce((s,p)=>s+doc.accessors[p.indices].count/3,0),0),246699);
});
